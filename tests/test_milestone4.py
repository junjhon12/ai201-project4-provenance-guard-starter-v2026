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
            self.assertEqual(payload["guess"], "unsure")
            self.assertEqual(payload["confidence"], 0.0)
            self.assertEqual(
                payload["label"],
                "We can't tell from these signals whether this text was written by a person or with AI.",
            )

            entry = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(entry["content_id"], payload["content_id"])
            self.assertEqual(entry["guess"], "unsure")
            self.assertEqual(entry["model_score"], 0.8)
            self.assertEqual(entry["style_score"], 0.2)
            self.assertAlmostEqual(entry["combined_score"], 0.5)
            self.assertEqual(entry["label"], payload["label"])

    def test_log_returns_three_decisions_with_all_required_audit_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_path = log_dir / "audit.jsonl"
            with (
                patch.object(config, "LOG_DIR", log_dir),
                patch.object(config, "AUDIT_LOG", log_path),
                patch("detector.model_signal", return_value=0.8),
                patch("stylometry.style_signal", return_value=0.2),
            ):
                client = app.test_client()
                responses = [
                    client.post(
                        "/submit",
                        json={
                            "text": f"A sufficiently long example text {index}.",
                            "creator_id": "audit-shape-test",
                        },
                    )
                    for index in range(3)
                ]
                logged = client.get("/log").get_json()
                health = client.get("/health").get_json()

            self.assertTrue(all(response.status_code == 200 for response in responses))
            self.assertTrue(health["rate_limiting"])
            self.assertEqual(logged["count"], 3)
            required_fields = {
                "timestamp",
                "content_id",
                "creator_id",
                "guess",
                "model_score",
                "style_score",
                "combined_score",
                "label",
                "status",
            }
            for entry in logged["entries"]:
                self.assertTrue(required_fields.issubset(entry))
                self.assertEqual(entry["status"], "decided")


class Milestone5Tests(unittest.TestCase):
    def test_score_to_label_covers_configured_boundaries(self):
        self.assertEqual(
            scoring.score_to_label(config.HUMAN_THRESHOLD),
            ("human", "Our signals suggest this text was probably written by a person."),
        )
        self.assertEqual(
            scoring.score_to_label(
                (config.HUMAN_THRESHOLD + config.AI_THRESHOLD) / 2
            ),
            (
                "unsure",
                "We can't tell from these signals whether this text was written by a person or with AI.",
            ),
        )
        self.assertEqual(
            scoring.score_to_label(config.AI_THRESHOLD),
            (
                "ai",
                "Our signals suggest this text may have been written with AI, but this is not proof.",
            ),
        )

    def test_label_ranges_report_inclusive_and_exclusive_boundaries(self):
        self.assertEqual(
            scoring.label_ranges(),
            [
                (
                    "high-confidence human",
                    f"0.00 – {config.HUMAN_THRESHOLD:.2f} (inclusive)",
                ),
                (
                    "unsure",
                    f"> {config.HUMAN_THRESHOLD:.2f} and < {config.AI_THRESHOLD:.2f}",
                ),
                (
                    "high-confidence AI",
                    f"{config.AI_THRESHOLD:.2f} – 1.00 (inclusive)",
                ),
            ],
        )

    def test_submit_can_reach_and_log_all_three_labels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_path = log_dir / "audit.jsonl"
            with (
                patch.object(config, "LOG_DIR", log_dir),
                patch.object(config, "AUDIT_LOG", log_path),
                patch("detector.model_signal", side_effect=[0.1, 0.5, 0.9]),
                patch("stylometry.style_signal", side_effect=[0.1, 0.5, 0.9]),
            ):
                client = app.test_client()
                results = [
                    client.post(
                        "/submit",
                        json={
                            "text": f"A sufficiently long example text {index}.",
                            "creator_id": "label-test",
                        },
                    ).get_json()
                    for index in range(3)
                ]

            self.assertEqual(
                [result["guess"] for result in results],
                ["human", "unsure", "ai"],
            )
            logged = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([entry["guess"] for entry in logged], ["human", "unsure", "ai"])
            self.assertEqual(
                [entry["label"] for entry in logged],
                [result["label"] for result in results],
            )

    def test_appeal_appends_under_review_entry_and_get_log_shows_both(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_path = log_dir / "audit.jsonl"
            with (
                patch.object(config, "LOG_DIR", log_dir),
                patch.object(config, "AUDIT_LOG", log_path),
                patch("detector.model_signal", return_value=0.8),
                patch("stylometry.style_signal", return_value=0.8),
            ):
                client = app.test_client()
                submission = client.post(
                    "/submit",
                    json={
                        "text": "A sufficiently long example text.",
                        "creator_id": "appeal-test",
                    },
                ).get_json()
                response = client.post(
                    "/appeal",
                    json={
                        "content_id": submission["content_id"],
                        "reasoning": "I wrote this text myself.",
                    },
                )
                logged = client.get("/log").get_json()["entries"]

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.get_json(),
                {
                    "content_id": submission["content_id"],
                    "status": "under_review",
                    "message": "Your appeal has been received for review.",
                },
            )
            self.assertEqual(len(logged), 2)
            self.assertEqual(logged[0]["status"], "decided")
            self.assertEqual(logged[0]["guess"], submission["guess"])
            self.assertEqual(logged[0]["label"], submission["label"])
            self.assertEqual(logged[1]["event"], "appeal")
            self.assertEqual(logged[1]["status"], "under_review")
            self.assertEqual(logged[1]["creator_id"], "appeal-test")
            self.assertEqual(logged[1]["reasoning"], "I wrote this text myself.")

    def test_appeal_rejects_invalid_fields_and_unknown_content(self):
        client = app.test_client()
        invalid_requests = [
            ({"content_id": "content", "reasoning": "reason"}, 404),
            ({"content_id": " ", "reasoning": "reason"}, 400),
            ({"content_id": "content", "reasoning": " "}, 400),
            ({"content_id": 1, "reasoning": "reason"}, 400),
            ({"content_id": "content", "reasoning": 1}, 400),
        ]
        for payload, expected_status in invalid_requests:
            with self.subTest(payload=payload):
                response = client.post("/appeal", json=payload)
                self.assertEqual(response.status_code, expected_status)
                self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
