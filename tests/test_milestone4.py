import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
import scoring
import stylometry
from app import app


class StylometryTests(unittest.TestCase):
    def test_sentence_length_spread_is_coefficient_of_variation(self):
        text = "One two. One two three four."
        self.assertAlmostEqual(
            stylometry.sentence_length_spread(text),
            math.sqrt(2) / 3,
        )

    def test_sentence_length_spread_handles_one_sentence(self):
        self.assertEqual(stylometry.sentence_length_spread("Only one sentence."), 0.0)

    def test_type_token_ratio_handles_empty_text(self):
        self.assertAlmostEqual(stylometry.type_token_ratio("red blue red"), 2 / 3)
        self.assertEqual(stylometry.type_token_ratio("!!!"), 0.0)

    def test_punctuation_density_is_fraction_of_characters(self):
        self.assertAlmostEqual(stylometry.punctuation_density("Hi, there!"), 0.2)
        self.assertEqual(stylometry.punctuation_density(""), 0.0)

    def test_style_signal_is_bounded_and_neutral_without_words(self):
        self.assertEqual(stylometry.style_signal("..."), 0.5)
        score = stylometry.style_signal(
            "The system works well. It handles most cases correctly and provides good results."
        )
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


class ScoringIntegrationTests(unittest.TestCase):
    def test_equal_weight_average_treats_disagreement_as_uncertainty(self):
        self.assertAlmostEqual(scoring.combine_signals(0.9, 0.1), 0.5)

    def test_submit_returns_and_logs_both_signals_and_combined_score(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_path = log_dir / "audit.jsonl"
            with (
                patch.object(config, "LOG_DIR", log_dir),
                patch.object(config, "AUDIT_LOG", log_path),
                patch("detector.model_signal", return_value=0.8),
                patch("stylometry.style_signal", return_value=0.2),
            ):
                response = app.test_client().post(
                    "/submit",
                    json={"text": "A sufficiently long example text.", "creator_id": "test"},
                )

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["model_score"], 0.8)
            self.assertEqual(payload["style_score"], 0.2)
            self.assertAlmostEqual(payload["combined_score"], 0.5)
            self.assertEqual(payload["confidence"], 0.0)
            self.assertEqual(
                payload["label"],
                "Pending Milestone 5: no label assigned yet.",
            )

            entry = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(entry["content_id"], payload["content_id"])
            self.assertEqual(entry["model_score"], 0.8)
            self.assertEqual(entry["style_score"], 0.2)
            self.assertAlmostEqual(entry["combined_score"], 0.5)


if __name__ == "__main__":
    unittest.main()
