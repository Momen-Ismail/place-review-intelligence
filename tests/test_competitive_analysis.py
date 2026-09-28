"""Regression and comparability tests for the competitive extension."""

from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import run_all
from src.competitive_analysis.data_loader import ROOT, load_all, load_json
from src.competitive_analysis.period_comparison import (
    CORE_TOPIC_NAMES,
    common_periods,
    observed_leaders,
    reviews_in_period,
)


CONFIG = load_json(ROOT / "businesses/restaurants/competitive_config.json")
SLUGS = CONFIG["comparison_restaurants"]


class CompetitiveAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.restaurants = load_all(CONFIG)
        cls.result = load_json(ROOT / "output/competitive/restaurants/competitive_analysis_results.json")

    def test_restaurant_databases_are_isolated(self):
        paths = [ROOT / "businesses/restaurants" / slug / "data/reviews.db" for slug in SLUGS]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all(path.exists() for path in paths))
        place_ids = []
        for path in paths:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                ids = {row[0] for row in connection.execute("SELECT DISTINCT place_id FROM reviews")}
                self.assertEqual(len(ids), 1)
                place_ids.extend(ids)
            finally:
                connection.close()
        self.assertEqual(len(place_ids), len(set(place_ids)))

    def test_common_cutoff_excludes_later_competitor_reviews(self):
        period = {"start": None, "end": "2026-09-03", "duration_days": None}
        excluded_some = False
        for slug in ("olivenzweig", "al_safa", "beit_fayrouz"):
            reviews = self.restaurants[slug]["prepared"]["reviews"]
            kept = reviews_in_period(reviews, period)
            self.assertTrue(all(str(row["published_at"])[:10] <= "2026-09-03" for row in kept))
            excluded_some |= len(kept) < len(reviews)
        self.assertTrue(excluded_some)
        for slug in SLUGS:
            self.assertEqual(self.result["dish_favourite_signals"][slug]["through_cutoff"], "2026-09-03")

    def test_same_period_boundaries_for_every_restaurant(self):
        expected = common_periods("2026-09-03")
        self.assertEqual(self.result["common_period_boundaries"], expected)
        for slug in SLUGS:
            for name, boundary in expected.items():
                actual = self.result["restaurant_comparisons"][slug]["periods"][name]
                self.assertEqual((actual["start"], actual["end"]), (boundary["start"], boundary["end"]))

    def test_topic_metrics_use_same_core_definitions(self):
        baseline = {row["name"]: row["aliases"] for row in self.restaurants["al_assiel"]["profile"]["topics"]}
        for slug in SLUGS[1:]:
            current = {row["name"]: row["aliases"] for row in self.restaurants[slug]["profile"]["topics"]}
            for name in CORE_TOPIC_NAMES:
                self.assertEqual(current[name], baseline[name], f"{slug}: {name}")

    def test_dish_aliases_remain_restaurant_specific(self):
        catalogs = {slug: self.restaurants[slug]["menu_items"] for slug in SLUGS}
        self.assertNotEqual(
            {(row["name"], tuple(row["aliases"])) for row in catalogs["al_assiel"]},
            {(row["name"], tuple(row["aliases"])) for row in catalogs["olivenzweig"]},
        )
        self.assertTrue(any(row["name"] == "Schawarma Kalb Sandwich" for row in catalogs["beit_fayrouz"]))
        self.assertFalse(any(row["name"] == "Schawarma Kalb Sandwich" for row in catalogs["al_assiel"]))

    def test_platform_popularity_not_mixed_with_google_sentiment(self):
        signaled = [row for row in self.restaurants["beit_fayrouz"]["menu_items"] if row.get("platform_signals")]
        self.assertTrue(signaled)
        for row in self.result["competitor_tasting_shortlist"]["beit_fayrouz"]:
            self.assertIn("platform_signal", row)
            self.assertIn("google_review_mentions", row)
        for row in self.result["restaurant_comparisons"]["beit_fayrouz"]["recent_90d_topics"]:
            self.assertNotIn("platform_signal", row)

    def test_menu_price_conflicts_preserve_source_and_date(self):
        al_safa_sources = self.restaurants["al_safa"]["source_register"]["sources"]
        self.assertTrue(any(row.get("conflicts") for row in al_safa_sources))
        self.assertTrue(any(row["source_type"] == "supplied_physical_menu" and row["confidence"] == "medium" for row in al_safa_sources))
        for slug in SLUGS[1:]:
            for row in self.restaurants[slug]["menu_items"]:
                self.assertIn("source", row)
                self.assertIn("source_date", row)

    def test_al_assiel_drinks_bar_count_is_validated_34(self):
        menu = self.result["menu_comparison"]["al_assiel"]
        self.assertEqual(menu["normalized_comparison_groups"]["Drinks / Bar"]["item_count"], 34)
        self.assertEqual(self.result["kitchen_bar_comparison"]["al_assiel"]["drink_menu_size"], 34)

    def test_cocktails_and_juices_is_in_drinks_bar(self):
        drinks = self.result["menu_comparison"]["al_assiel"]["normalized_comparison_groups"]["Drinks / Bar"]
        self.assertIn("Cocktails & Juices", drinks["original_categories"])

    def test_olivenzweig_grill_and_smoked_meat_are_main_food(self):
        menu = self.result["menu_comparison"]["olivenzweig"]
        group = menu["normalized_comparison_groups"]["Grill / Meat Mains"]
        self.assertGreater(group["item_count"], 0)
        self.assertIn("Grill", group["original_categories"])
        self.assertIn("Smoked Meat", group["original_categories"])

    def test_olivenzweig_sides_and_kids_are_not_other_mains(self):
        groups = self.result["menu_comparison"]["olivenzweig"]["normalized_comparison_groups"]
        self.assertEqual(groups["Sides"]["item_count"], 5)
        self.assertEqual(groups["Kids"]["item_count"], 1)
        self.assertNotIn("Extra Sides", groups["Other Main Dishes"]["original_categories"])
        self.assertNotIn("Kids & Desserts", groups["Other Main Dishes"]["original_categories"])

    def test_beit_mixed_source_category_is_not_double_counted(self):
        menu = self.result["menu_comparison"]["beit_fayrouz"]
        groups = menu["normalized_comparison_groups"]
        self.assertEqual(groups["Grill / Meat Mains"]["item_count"], 8)
        self.assertEqual(groups["Other Main Dishes"]["item_count"], 0)
        self.assertEqual(menu["classification_mode"], "overlapping")
        self.assertIn("Never sum", menu["classification_warning"])

    def test_breakfast_does_not_automatically_imply_brunch(self):
        beit = self.result["menu_comparison"]["beit_fayrouz"]
        self.assertTrue(beit["breakfast_available"]["available"])
        self.assertEqual(beit["brunch_available"]["availability_status"], "unknown")
        self.assertIsNone(beit["brunch_available"]["available"])

    def test_missing_vegetarian_tags_do_not_mean_no_availability(self):
        al_assiel = self.result["menu_comparison"]["al_assiel"]["vegetarian_vegan_availability"]
        self.assertEqual(al_assiel["explicitly_tagged_item_count"], 0)
        self.assertTrue(al_assiel["category_based_signal"])
        self.assertTrue(al_assiel["available"])
        self.assertEqual(al_assiel["availability_status"], "observed")

    def test_pdf_does_not_silently_overwrite_newer_price(self):
        soft_drink = next(row for row in self.restaurants["al_safa"]["menu_items"] if row["name"] == "Soft Drink 0.33l")
        self.assertEqual(soft_drink["price_eur"], 2.00)
        self.assertTrue(any(row["price_eur"] == 2.80 for row in soft_drink["price_observations"]))
        self.assertTrue(soft_drink["price_conflicts"])
        pdf = next(row for row in self.restaurants["al_safa"]["source_register"]["sources"] if row["source_type"] == "supplied_research")
        self.assertEqual(pdf["confidence"], "medium")
        self.assertEqual(pdf["source_snapshot_date"], "2026-09-20")

    def test_comparable_item_mapping_has_confidence(self):
        rows = self.result["comparable_price_basket"]
        self.assertTrue(rows)
        self.assertTrue(all(row["match_confidence"] in {"low", "medium", "high"} for row in rows))

    def test_insufficient_sample_cannot_produce_leader(self):
        comparison = {}
        for slug in SLUGS:
            comparison[slug] = {
                "periods": {"recent_90d": {"review_count": 4, "average_rating": 5.0, "owner_response_rate_pct": 100.0, "low_score_share_pct": 0.0}},
                "recent_90d_topics": [],
            }
        leaders = observed_leaders(comparison, CONFIG["minimum_evidence_thresholds"])
        self.assertIsNone(leaders["highest_observed_recent_rating"]["leader"])
        self.assertEqual(leaders["highest_observed_recent_rating"]["note"], "insufficient comparable evidence")

    def test_low_score_comparison_preserves_count_percentage_evidence(self):
        for slug, row in self.result["low_score_comparison"]["restaurants"].items():
            self.assertIn("count", row)
            self.assertIn("share_pct", row)
            self.assertIn("evidence_level", row)
            self.assertGreaterEqual(row["share_pct"], 0)
            self.assertLessEqual(row["share_pct"], 100)

    def test_existing_al_assiel_metrics_remain_stable(self):
        layer05 = self.restaurants["al_assiel"]["layer_05"]
        overall = layer05["overall_performance"]
        self.assertEqual(overall["collected_reviews"], 298)
        self.assertEqual(overall["written_reviews"], 220)
        self.assertEqual(overall["google_rating"], 4.5)
        self.assertEqual(overall["google_review_count"], 298)
        db_path = ROOT / "businesses/restaurants/al_assiel/data/reviews.db"
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            exact_average = connection.execute("SELECT AVG(rating) FROM reviews").fetchone()[0]
        finally:
            connection.close()
        self.assertAlmostEqual(exact_average, 4.483221, places=6)

    def test_normal_analysis_rerun_does_not_call_apify(self):
        with patch.object(sys, "argv", ["run_all.py"]), \
             patch("src.layer_02_preparation.run_layer_02.run"), \
             patch("src.layer_03_numerical_analysis.run_layer_03.run"), \
             patch("src.layer_04_text_analysis.run_layer_04.run"), \
             patch("src.layer_05_reporting.run_layer_05.run"), \
             patch("src.layer_01_collection.step_01_fetch_google_reviews.ApifyGoogleReviewsCollector.collect", side_effect=AssertionError("Apify must not run")):
            run_all.main()


if __name__ == "__main__":
    unittest.main()
