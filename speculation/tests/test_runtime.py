from contextlib import contextmanager
import os
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from recallspec.core import Config, RetrievalIndex
from recallspec.runtime import before_update, propose


class Rows:
    def __init__(self, rows): self.rows = rows
    def __getitem__(self, index):
        i, sl = index
        return self.rows[i][sl]


def runner(ids, rows, native=None):
    return NS(input_batch=NS(req_ids=ids, num_tokens_no_spec=list(map(len, rows)),
                            token_ids_cpu=Rows(rows)),
              drafter=NS(propose=lambda *a, **kw: native if native is not None else [[] for _ in ids]),
              requests={rid: NS(num_prompt_tokens=3, lora_request=None, mm_features=[],
                                prompt_embeds=None) for rid in ids},
              use_async_scheduling=False, parallel_config=NS(tensor_parallel_size=1),
              max_model_len=100,
              _recallspec_index=RetrievalIndex(Config(key_lengths=(3,), draft_tokens=4)))


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"RECALLSPEC_MODE": "gated"})
        self.env.start()
    def tearDown(self): self.env.stop()
    def scheduler(self, drafts=None, finished=()):
        return NS(scheduled_spec_decode_tokens=drafts or {}, finished_req_ids=finished,
                  num_scheduled_tokens={"a": 1})

    def test_query_before_batch_commit(self):
        r = runner(["a", "b"], [[1, 2, 3, 4, 5, 6, 7], [1, 2, 3]])
        self.assertEqual(propose(r, self.scheduler(), [[7], [3]], 4, None), [[], []])
        r.input_batch.req_ids = ["b"]
        r.input_batch.num_tokens_no_spec = [3]
        r.input_batch.token_ids_cpu = Rows([[1, 2, 3]])
        r.drafter.propose = lambda *a, **kw: [[]]
        self.assertEqual(propose(r, self.scheduler(), [[3]], 4, None), [[4, 5, 6, 7]])

    def test_native_priority(self):
        r = runner(["b"], [[1, 2, 3]], native=[[99]])
        r._recallspec_index = RetrievalIndex(Config(key_lengths=(3,), draft_tokens=4,
                                                   shared_first=False))
        r._recallspec_index.commit("a", [1, 2, 3, 4, 5, 6, 7], 3)
        self.assertEqual(propose(r, self.scheduler(), [[3]], 4, None), [[99]])
        self.assertFalse(r._recallspec_index.pending)

    def test_long_shared_context_priority(self):
        r = runner(["b"], [[1, 2, 3]], native=[[99]])
        r._recallspec_index.commit("a", [1, 2, 3, 4, 5, 6, 7], 3)
        self.assertEqual(propose(r, self.scheduler(), [[3]], 4, None), [[4, 5, 6, 7]])

    def test_real_scheduled_prefix_feedback(self):
        r = runner(["b"], [[1, 2, 3, 4, 99]])
        i = r._recallspec_index
        i.commit("a", [1, 2, 3, 4, 5, 6, 7], 3)
        i.lookup("b", [1, 2, 3], 4)
        propose(r, self.scheduler({"b": [4, 5]}), [[4, 99]], 4, None)
        self.assertEqual(i.stats["verified_tokens"], 2)
        self.assertEqual(i.stats["accepted_tokens"], 1)

    def test_finish_and_reuse_id(self):
        r = runner(["a"], [[1, 2, 3, 4, 5, 6, 7]])
        propose(r, self.scheduler(), [[7]], 4, None)
        before_update(r, self.scheduler(finished=["a"]))
        self.assertFalse(r._recallspec_index.cursors)
        self.assertTrue(r._recallspec_index.entries)

    def test_unscheduled_is_not_finished(self):
        r = runner(["a"], [[1, 2, 3, 4, 5, 6, 7]])
        propose(r, self.scheduler(), [[7]], 4, None)
        before_update(r, self.scheduler())
        self.assertIn("a", r._recallspec_index.cursors)

    def test_native_mode_no_index(self):
        r = runner(["a"], [[1, 2, 3]])
        del r._recallspec_index
        with patch.dict(os.environ, {"RECALLSPEC_MODE": "native"}):
            self.assertEqual(propose(r, self.scheduler(), [[3]], 4, None), [[]])
        self.assertFalse(hasattr(r, "_recallspec_index"))

    def test_unsupported_fails_explicitly(self):
        r = runner(["a"], [[1, 2, 3]])
        r.use_async_scheduling = True
        with self.assertRaises(RuntimeError):
            propose(r, self.scheduler(), [[3]], 4, None)


if __name__ == "__main__": unittest.main()
