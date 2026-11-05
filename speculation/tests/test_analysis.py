import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("analysis", Path(__file__).resolve().parents[1] / "tools/analyze.py")
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class TraceAnalysisTests(unittest.TestCase):
    def test_external_and_internal_request_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            events = [
                {"event": "schedule", "requests": {"0-1234abcd": 1}},
                {"event": "schedule", "requests": {"8-a0b1c2d3": 9}},
                {"event": "propose", "feedback": [{"request_id": "8-a0b1c2d3",
                  "source": "shared", "scheduled": 8, "accepted": 7}],
                  "native_ns": 1000, "total_ns": 3000, "stats": {}, "keys": 2},
            ]
            (path / "worker.jsonl").write_text("\n".join(map(json.dumps, events)))
            result = analysis.trace_summary(path, [{"kind": "repeat", "batch": 1,
                      "outputs": [{"request_id": "8"}]}])
            self.assertEqual(result["repeat/b1"]["target_steps"], 1)
            self.assertEqual(result["repeat/b1"]["shared_accepted"], 7)
            self.assertEqual(result["matched_requests"], 1)

    def test_missing_id_is_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "worker.jsonl").write_text(json.dumps({"event": "schedule", "requests": {"0-1234abcd": 1}}))
            with self.assertRaises(ValueError):
                analysis.trace_summary(path, [{"kind": "general", "batch": 1,
                    "outputs": [{"request_id": "8"}]}])


if __name__ == "__main__": unittest.main()
