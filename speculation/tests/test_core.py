import unittest
from recallspec.core import Config, RetrievalIndex


def make(**kwargs):
    return RetrievalIndex(Config(key_lengths=(3, 2), draft_tokens=4, **kwargs))


class IndexTests(unittest.TestCase):
    def populate(self, index, source="a"):
        index.commit(source, [1, 2, 3, 4, 5, 6, 7], 3)

    def test_generated_only(self):
        i = make()
        i.commit("a", list(range(20)), 16)
        self.assertEqual(i.lookup("b", [13, 14, 15], 4), [16, 17, 18, 19])
        self.assertEqual(i.lookup("b", [0, 1, 2], 4), [])

    def test_no_incomplete_continuation(self):
        i = make()
        i.commit("a", [1, 2, 3, 4, 5], 3)
        self.assertEqual(i.lookup("b", [1, 2, 3], 4), [])
        i.commit("a", [1, 2, 3, 4, 5, 6, 7], 3)
        self.assertEqual(i.lookup("b", [1, 2, 3], 4), [4, 5, 6, 7])

    def test_self_exclusion(self):
        i = make(); self.populate(i)
        self.assertEqual(i.lookup("a", [1, 2, 3], 4), [])

    def test_sources_fallback_and_limit(self):
        i = make()
        for source, last in (("a", 7), ("b", 8), ("c", 9)):
            i.commit(source, [1, 2, 3, 4, 5, 6, last], 3)
        self.assertEqual([e.source for e in i.entries[(1, 2, 3)]], ["b", "c"])
        self.assertEqual(i.lookup("c", [1, 2, 3], 4), [4, 5, 6, 8])

    def test_capacity_always_bounded(self):
        i = make(max_keys=3)
        i.commit("a", list(range(100)), 3)
        self.assertLessEqual(len(i.entries), 3)
        self.assertGreater(i.stats["evictions"], 0)

    def test_ttl_is_write_based(self):
        i = make(ttl_steps=2); self.populate(i)
        i.tick(); self.assertTrue(i.lookup("b", [1, 2, 3], 4))
        i.tick(); self.assertEqual(i.lookup("b", [1, 2, 3], 4), [])

    def test_prompt_boundary_change_rejected(self):
        i = make(); self.populate(i)
        with self.assertRaises(ValueError):
            i.commit("a", list(range(10)), 4)

    def test_rollback_rejected(self):
        i = make(); self.populate(i)
        with self.assertRaises(ValueError):
            i.commit("a", [1, 2, 3], 3)

    def test_finish_preserves_cache_cleans_cursor_and_pending(self):
        i = make(); self.populate(i)
        i.lookup("b", [1, 2, 3], 4)
        i.finish("a"); i.finish("b")
        self.assertFalse(i.cursors); self.assertFalse(i.pending)
        self.assertTrue(i.entries)
        i.commit("a", [9, 8, 7], 3)

    def test_no_reindex_on_replay(self):
        i = make(); self.populate(i)
        count = i.stats["insertions"]; self.populate(i)
        self.assertEqual(i.stats["insertions"], count)

    def test_work_cap(self):
        i = make(max_updates_per_request=2)
        i.commit("a", list(range(100)), 3)
        self.assertLessEqual(i.stats["insertions"], 4)
        self.assertGreater(i.stats["skipped_windows"], 0)

    def test_scheduled_prefix_not_proposed_length(self):
        i = make(); self.populate(i); i.lookup("b", [1, 2, 3], 4)
        self.assertEqual(i.feedback("b", [4, 5], [4, 99])["accepted"], 1)
        self.assertEqual(i.stats["verified_tokens"], 2)
        self.assertEqual(i.stats["accepted_tokens"], 1)

    def test_unscheduled_not_rejection(self):
        i = make(); self.populate(i); i.lookup("b", [1, 2, 3], 4)
        self.assertIsNone(i.feedback("b", [], [99]))
        self.assertEqual(i.stats["verified_proposals"], 0)

    def test_empty_sample_not_rejection(self):
        i = make(); self.populate(i); i.lookup("b", [1, 2, 3], 4)
        self.assertIsNone(i.feedback("b", [4, 5, 6, 7], []))
        self.assertEqual(i.stats["verified_proposals"], 0)

    def test_wrong_draft_rejected(self):
        i = make(); self.populate(i); i.lookup("b", [1, 2, 3], 4)
        with self.assertRaises(ValueError):
            i.feedback("b", [99], [99, 8])

    def test_wrong_accepted_prefix_rejected(self):
        i = make(); self.populate(i); i.lookup("b", [1, 2, 3], 4)
        with self.assertRaises(ValueError):
            i.feedback("b", [4, 5], [99, 88])

    def test_gate_cooldown_then_probe(self):
        i = make(cooldown_steps=3); self.populate(i)
        for _ in range(2):
            i.lookup("b", [1, 2, 3], 4); i.feedback("b", [4, 5, 6, 7], [99])
        # Both 3- and 2-token keys are candidates; block both explicitly.
        for e in i.entries[(2, 3)]:
            e.blocked_until = i.step + 3
        self.assertEqual(i.lookup("b", [1, 2, 3], 4), [])
        for _ in range(3): i.tick()
        self.assertTrue(i.lookup("b", [1, 2, 3], 4))

    def test_gate_ablation(self):
        i = make(gate=False); self.populate(i)
        for _ in range(4):
            self.assertTrue(i.lookup("b", [1, 2, 3], 4))
            i.feedback("b", [4, 5, 6, 7], [99])
        self.assertEqual(i.stats["gate_blocks"], 0)

    def test_full_acceptance_includes_bonus(self):
        i = make(); self.populate(i); i.lookup("b", [1, 2, 3], 4)
        self.assertEqual(i.feedback("b", [4, 5, 6, 7], [4, 5, 6, 7, 8])["accepted"], 4)

    def test_cap_and_clear(self):
        i = make(); self.populate(i)
        self.assertEqual(i.lookup("b", [1, 2, 3], 2), [4, 5])
        i.clear()
        self.assertFalse(i.entries); self.assertFalse(i.cursors); self.assertFalse(i.pending)

    def test_config(self):
        for kwargs in ({"max_keys": 0}, {"ttl_steps": -1}, {"key_lengths": ()},
                       {"key_lengths": (2, 2)}, {"min_accepted": 9}):
            with self.assertRaises(ValueError): Config(**kwargs)


if __name__ == "__main__":
    unittest.main()
