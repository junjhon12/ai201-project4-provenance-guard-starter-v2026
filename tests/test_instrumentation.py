"""Unit tests for the Unit 9 run instrumentation (no model required)."""

import tempfile
import unittest
from pathlib import Path

import config
import instrumentation


class InstrumentationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_log_dir = config.LOG_DIR
        self._old_run_log = config.RUN_LOG
        config.LOG_DIR = Path(self._tmp.name)
        config.RUN_LOG = config.LOG_DIR / "runs.jsonl"

    def tearDown(self):
        config.LOG_DIR = self._old_log_dir
        config.RUN_LOG = self._old_run_log
        self._tmp.cleanup()

    def test_record_shape_and_read_back(self):
        instrumentation.record_run(
            request_id="req-1",
            event="decision",
            endpoint="/submit",
            creator_id="writer",
            input={"chars": 40, "words": 8, "preview": "hello"},
            output={"guess": "unsure", "combined_score": 0.5},
            duration_ms=123.4567,
            stages={"model_ms": 100.0, "style_ms": 1.0},
            status="decided",
        )
        entries = instrumentation.read_runs()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        for field in (
            "timestamp",
            "request_id",
            "event",
            "endpoint",
            "creator_id",
            "input",
            "output",
            "duration_ms",
            "stages",
            "status",
            "error",
        ):
            self.assertIn(field, entry)
        self.assertEqual(entry["duration_ms"], 123.457)
        self.assertIsNone(entry["error"])

    def test_summary_counts_and_latency(self):
        for i in range(3):
            instrumentation.record_run(
                request_id=f"d{i}",
                event="decision",
                endpoint="/submit",
                duration_ms=100.0,
                stages={"model_ms": 90.0},
            )
        instrumentation.record_run(
            request_id="r1",
            event="rejected",
            endpoint="/submit",
            duration_ms=5.0,
            status="rejected",
            error="empty_text",
        )
        summary = instrumentation.summarize_runs()
        self.assertEqual(summary["total_runs"], 4)
        self.assertEqual(summary["decisions"], 3)
        self.assertEqual(summary["rejections"], 1)
        self.assertEqual(summary["error_counts"], {"empty_text": 1})
        self.assertEqual(summary["decision_latency_ms"]["average"], 100.0)
        self.assertEqual(summary["stage_average_ms"]["model_ms"], 90.0)
        self.assertEqual(summary["compute_seconds_per_decision"], 0.1)

    def test_malformed_line_is_skipped(self):
        instrumentation.record_run(
            request_id="ok",
            event="decision",
            endpoint="/submit",
            duration_ms=1.0,
        )
        with config.RUN_LOG.open("a", encoding="utf-8") as handle:
            handle.write("{not json}\n")
        self.assertEqual(len(instrumentation.read_runs()), 1)


if __name__ == "__main__":
    unittest.main()
