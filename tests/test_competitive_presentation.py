"""Regression tests for competitive-presentation data semantics."""

from __future__ import annotations

import unittest
import json
import zipfile
from pathlib import Path

from competitive_presentation.prepare_presentation_data import (
    presentation_digital_footprint,
    topic_trends,
)


ROOT = Path(__file__).resolve().parents[1]


class CompetitivePresentationTests(unittest.TestCase):
    def test_page_31_guardrail_has_no_text_overlap(self):
        validation = json.loads(
            (ROOT / "output/competitive/restaurants/presentation/qa/build_validation.json").read_text()
        )
        self.assertEqual(validation["page_31_guardrail_overlaps"], 0)

    def test_percentage_point_axis_uses_literal_percent_sign(self):
        pptx = ROOT / "output/competitive/restaurants/presentation/al_assiel_competitive_intelligence.pptx"
        with zipfile.ZipFile(pptx) as archive:
            charts = [
                archive.read(name).decode("utf-8")
                for name in archive.namelist()
                if name.startswith("ppt/slides/charts/chart") and name.endswith(".xml")
            ]
        chart = next(xml for xml in charts if "5-star share" in xml and "1–2-star share" in xml)
        self.assertIn('<c:max val="100"', chart)
        self.assertIn('<c:numFmt formatCode="0\\%"', chart)
        self.assertNotIn('<c:numFmt formatCode="0%"', chart)

    def test_page_32_disclaimer_has_no_text_overlap(self):
        validation = json.loads(
            (ROOT / "output/competitive/restaurants/presentation/qa/build_validation.json").read_text()
        )
        self.assertEqual(validation["page_32_disclaimer_overlaps"], 0)

    def test_google_presence_uses_validated_review_dataset(self):
        competitive = {
            "digital_service_footprint": {
                slug: {"google_presence": False, "delivery": {"status": "unknown"}}
                for slug in ("al_assiel", "olivenzweig", "al_safa", "beit_fayrouz")
            }
        }
        footprint = presentation_digital_footprint(competitive)
        self.assertTrue(footprint["al_assiel"]["google_presence"])
        self.assertIn("validated Google review collection", footprint["al_assiel"]["google_presence_basis"])
        self.assertEqual(footprint["al_assiel"]["delivery"], {"status": "unknown"})
        self.assertFalse(competitive["digital_service_footprint"]["al_assiel"]["google_presence"])

    def test_zero_topic_mentions_are_missing_not_zero_sentiment(self):
        layer_04 = {
            "topic_trends": [
                {
                    "month": "2026-01",
                    "topic": "Food",
                    "reviews_mentioning": 0,
                    "positive_share_of_topic_reviews_pct": 0.0,
                    "negative_share_of_topic_reviews_pct": 0.0,
                    "evidence_level": "low",
                },
                {
                    "month": "2026-02",
                    "topic": "Food",
                    "reviews_mentioning": 2,
                    "positive_share_of_topic_reviews_pct": 0.0,
                    "negative_share_of_topic_reviews_pct": 100.0,
                    "evidence_level": "low",
                },
            ]
        }

        food = topic_trends(layer_04)["Food"]
        self.assertEqual(food[0]["mentions"], 0)
        self.assertIsNone(food[0]["positive_share_pct"])
        self.assertIsNone(food[0]["negative_share_pct"])
        self.assertEqual(food[0]["evidence_level"], "none")
        self.assertEqual(food[1]["mentions"], 2)
        self.assertEqual(food[1]["positive_share_pct"], 0.0)
        self.assertEqual(food[1]["negative_share_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
