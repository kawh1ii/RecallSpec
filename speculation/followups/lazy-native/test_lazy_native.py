from unittest.mock import Mock

from recallspec.runtime import propose
from test_runtime import RuntimeTests, runner


class LazyNativeTests(RuntimeTests):
    def test_only_uncovered_rows_reach_native(self):
        r = runner(["hit", "miss"], [[1, 2, 3], [7, 8, 9]])
        r._recallspec_index.commit("history", [1, 2, 3, 4, 5, 6, 7], 3)
        r.drafter.propose = Mock(return_value=[[], [10]])
        result = propose(r, self.scheduler(), [[3], [9]], 4, None)
        self.assertEqual(result, [[4, 5, 6, 7], [10]])
        self.assertEqual(r.drafter.propose.call_args.args[1], [[], [9]])

    def test_full_hit_skips_native(self):
        r = runner(["hit", "unscheduled"], [[1, 2, 3], [7, 8, 9]])
        r._recallspec_index.commit("history", [1, 2, 3, 4, 5, 6, 7], 3)
        r.drafter.propose = Mock(side_effect=AssertionError("native call should be skipped"))
        self.assertEqual(propose(r, self.scheduler(), [[3], []], 4, None), [[4, 5, 6, 7], []])
        r.drafter.propose.assert_not_called()
