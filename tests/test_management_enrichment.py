import json
import unittest
from pathlib import Path

from src.layer_03_numerical_analysis.step_05_management_metrics import (
    owner_response_analysis,
    review_cadence_analysis,
)
from src.layer_04_text_analysis.step_05_diagnostics import (
    buffet_deep_analysis,
    low_rating_analysis,
    menu_review_attention,
    topic_period_comparison,
)
from src.layer_05_reporting.management_framework import (
    DRINK_MENU_CATEGORIES,
    build_bar_drinks_analysis,
    build_customer_journey,
    build_menu_activation_experiments,
    build_menu_optimization_goal,
    issue_evidence_summary,
    validate_management_observations,
)


ROOT = Path(__file__).resolve().parents[1]


def review(review_id, date, rating=5, text="text", response_text="", response_date=None):
    return {
        "review_id": review_id,
        "published_at": date,
        "rating": rating,
        "text_original": text,
        "text_translated": "",
        "original_language": "en",
        "owner_response_text": response_text,
        "owner_response_date": response_date,
    }


class ReviewCadenceTests(unittest.TestCase):
    def test_known_review_cadence_and_actual_gaps(self):
        reviews = [
            review("a", "2025-01-01T00:00:00Z"),
            review("b", "2025-01-03T00:00:00Z"),
            review("c", "2025-01-08T00:00:00Z"),
        ]
        result = review_cadence_analysis(reviews)["periods"]["all_time"]
        self.assertEqual(result["review_count"], 3)
        self.assertEqual(result["average_days_between_reviews"], 3.5)
        self.assertEqual(result["median_days_between_reviews"], 3.5)
        self.assertEqual(result["shortest_gap_days"], 2.0)
        self.assertEqual(result["longest_gap_days"], 5.0)

    def test_recent_previous_counts_are_timestamp_based(self):
        reviews = [
            review("old", "2025-01-01T00:00:00Z"),
            review("previous", "2025-02-05T00:00:00Z"),
            review("recent1", "2025-03-01T00:00:00Z"),
            review("recent2", "2025-03-10T00:00:00Z"),
        ]
        periods = review_cadence_analysis(reviews)["periods"]
        self.assertEqual(periods["recent_30d"]["review_count"], 2)
        self.assertEqual(periods["previous_30d"]["review_count"], 1)


class OwnerResponseTests(unittest.TestCase):
    def setUp(self):
        self.reviews = [
            review("1", "2025-01-01T00:00:00Z", 1),
            review("2", "2025-01-02T00:00:00Z", 2, response_text="Thanks", response_date="2025-01-03T00:00:00Z"),
            review("3", "2025-01-03T00:00:00Z", 5, response_text="Thanks", response_date="2025-01-03T12:00:00Z"),
            review("4", "2025-01-04T00:00:00Z", 5),
        ]

    def test_owner_and_low_score_response_rates(self):
        result = owner_response_analysis(self.reviews)
        self.assertEqual(result["overall"]["owner_response_rate_pct"], 50.0)
        self.assertEqual(result["low_score"]["low_score_response_rate_pct"], 50.0)

    def test_response_delay_statistics(self):
        delay = owner_response_analysis(self.reviews)["response_delay"]
        self.assertEqual(delay["responses_with_valid_delay"], 2)
        self.assertEqual(delay["average_response_delay_days"], 0.75)
        self.assertEqual(delay["median_response_delay_days"], 0.75)
        self.assertEqual(delay["minimum_response_delay_days"], 0.5)
        self.assertEqual(delay["maximum_response_delay_days"], 1.0)


class PeriodAndLowScoreTests(unittest.TestCase):
    def test_topic_period_comparison(self):
        reviews = [
            review("old", "2024-01-01T00:00:00Z", 2),
            review("new", "2025-01-01T00:00:00Z", 1),
        ]
        evidence = [
            {"review_id": "old", "topic": "Service", "sentiment": "negative"},
            {"review_id": "new", "topic": "Service", "sentiment": "negative"},
        ]
        result = topic_period_comparison(reviews, evidence, [{"name": "Service"}])[0]
        self.assertEqual(result["periods"]["historical"]["negative_reviews"], 1)
        self.assertEqual(result["periods"]["recent_90d"]["negative_reviews"], 1)
        self.assertEqual(result["recent_vs_historical_negative_share_change_pp"], 0.0)

    def test_zero_denominator_change_is_null(self):
        reviews = [review("new", "2025-01-01T00:00:00Z", 1)]
        evidence = [{"review_id": "new", "topic": "Service", "sentiment": "negative"}]
        result = topic_period_comparison(reviews, evidence, [{"name": "Service"}])[0]
        self.assertIsNone(result["recent_vs_historical_negative_share_change_pp"])
        self.assertIsNone(result["recent_vs_previous90_negative_share_change_pp"])

    def test_low_score_topic_counts_include_positive_and_neutral(self):
        reviews = [review("1", "2025-01-01T00:00:00Z", 1), review("2", "2025-01-02T00:00:00Z", 2)]
        evidence = [
            {"review_id": "1", "topic": "Service", "sentiment": "negative"},
            {"review_id": "2", "topic": "Food", "sentiment": "positive"},
            {"review_id": "2", "topic": "Atmosphere", "sentiment": "neutral"},
        ]
        result = low_rating_analysis(reviews, evidence, [])
        topics = {row["topic"]: row for row in result["groups"]["combined_one_two_star"]["topics"]}
        self.assertEqual(topics["Service"]["negative_reviews"], 1)
        self.assertEqual(topics["Food"]["positive_reviews"], 1)
        self.assertEqual(topics["Atmosphere"]["neutral_reviews"], 1)

    def test_cooccurrence_counts_each_review_once(self):
        reviews = [review("1", "2025-01-01T00:00:00Z", 1)]
        evidence = [
            {"review_id": "1", "topic": "Food", "sentiment": "negative"},
            {"review_id": "1", "topic": "Food", "sentiment": "negative"},
            {"review_id": "1", "topic": "Taste", "sentiment": "negative"},
        ]
        pairs = low_rating_analysis(reviews, evidence, [])["topic_cooccurrence"]["raw_pairs"]
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["reviews_where_both_present"], 1)


class BuffetAndMenuTests(unittest.TestCase):
    def test_buffet_subtopic_requires_buffet_local_context(self):
        reviews = [review("1", "2025-01-01T00:00:00Z", 2, "The a la carte food was fresh, but the buffet was empty.")]
        result = buffet_deep_analysis(reviews)
        self.assertEqual(result["freshness"]["reviews"], 0)
        self.assertEqual(result["freshness"]["evidence_level"], "none")
        self.assertEqual(result["replenishment"]["negative"], 1)

    def test_zero_menu_mentions_use_review_attention_language(self):
        dishes = [{
            "dish": "Dish", "english_name": "Dish", "menu_category": "Mains", "price_eur": 10,
            "reviews_mentioning": 0, "positive_reviews": 0, "negative_reviews": 0, "neutral_reviews": 0,
            "average_review_rating_when_mentioned": None, "evidence_level": "none",
        }]
        categories = [{"menu_category": "Mains", "menu_items": 1, "mentioned_menu_items": 0,
                       "dish_review_mentions": 0, "positive_reviews": 0, "negative_reviews": 0}]
        result = menu_review_attention(dishes, categories, [])
        self.assertEqual(result["items"][0]["review_attention_status"], "no observable review mentions")
        self.assertNotIn("never ordered", json.dumps(result).lower())


class ManagementEvidenceAndBarTests(unittest.TestCase):
    def setUp(self):
        self.text = json.loads((
            ROOT / "output/restaurants/al_assiel/layer_04_text_analysis/layer_04_text_analysis.json"
        ).read_text())

    def test_negative_issue_evidence_is_separate_from_topic_evidence(self):
        food = issue_evidence_summary(17, 3, 17.65, 14.29)
        parking = issue_evidence_summary(5, 2, 40.0, 9.52)
        no_negative = issue_evidence_summary(20, 0, 0.0, 0.0)
        self.assertEqual(food["topic_evidence_level"], "high")
        self.assertEqual(food["negative_issue_evidence_level"], "low")
        self.assertEqual(parking["topic_evidence_level"], "medium")
        self.assertEqual(parking["negative_issue_evidence_level"], "low")
        self.assertEqual(no_negative["negative_issue_evidence_level"], "none")

    def test_drink_menu_category_aggregation(self):
        bar = build_bar_drinks_analysis(self.text)
        categories = bar["menu_attention"]["categories"]
        self.assertEqual({row["category"] for row in categories}, set(DRINK_MENU_CATEGORIES))
        expected = sum(row["total_menu_items"] for row in categories)
        self.assertEqual(bar["menu_attention"]["totals"]["total_drink_items"], expected)
        self.assertEqual(expected, 34)

    def test_bar_terminology_and_zero_attention_are_not_sales_claims(self):
        bar = build_bar_drinks_analysis(self.text)
        self.assertIn("not sales", bar["terminology_note"].lower())
        self.assertIn("not a revenue or sales comparison", bar["comparison_note"].lower())
        statuses = " ".join(row["review_attention_status"] for row in bar["menu_attention"]["categories"])
        self.assertNotIn("not ordered", statuses.lower())
        self.assertIn("no observable review mentions", statuses.lower())

    def test_menu_goal_and_activation_classifications(self):
        goal = build_menu_optimization_goal()
        self.assertEqual(goal["classification"], "internal_management_goal")
        self.assertFalse(goal["review_derived"])
        observations = validate_management_observations(json.loads((
            ROOT / "businesses/restaurants/al_assiel/inputs/management_observations.json"
        ).read_text()))
        experiments = build_menu_activation_experiments(observations)["experiments"]
        self.assertTrue(all(row["classification"] == "proposed_experiment" for row in experiments))
        names = {row["name"] for row in experiments}
        self.assertIn("weekly featured dish", names)
        self.assertIn("food + drink bundle", names)
        self.assertIn("visual/video dish promotion", names)


class ManagementInputAndJourneyTests(unittest.TestCase):
    def test_human_management_input_loads_safely(self):
        path = ROOT / "businesses/restaurants/al_assiel/inputs/management_observations.json"
        value = validate_management_observations(json.loads(path.read_text()))
        self.assertFalse(value["metadata"]["review_derived"])
        self.assertEqual(value["media"]["dish_video_or_richer_media_test_proposed"]["classification"], "proposed_experiment")

    def test_customer_journey_preserves_source_distinction(self):
        observations = validate_management_observations(json.loads(
            (ROOT / "businesses/restaurants/al_assiel/inputs/management_observations.json").read_text()
        ))
        topic_names = ["Parking", "Family & Groups", "Hospitality", "Staff Friendliness", "Menu & Tablet",
                       "Reservations", "Takeaway", "Waiting Time", "Staff Communication", "Food", "Taste",
                       "Drinks", "Buffet", "Card Payment"]
        topics = [{"topic": name, "reviews_mentioning": 1, "positive_reviews": 1, "negative_reviews": 0,
                   "neutral_reviews": 0, "negative_share_of_topic_reviews_pct": 0.0,
                   "negative_coverage_pct_of_written_reviews": 0.0, "evidence_level": "low"}
                  for name in topic_names]
        numerical = {
            "review_cadence": {"periods": {"recent_30d": {"review_count": 2, "reviews_per_week": 0.5, "average_days_between_reviews": 4}}},
            "owner_response_analysis": {"overall": {"owner_response_rate_pct": 10}, "low_score": {"low_score_response_rate_pct": 5},
                                        "periods": {"recent_90d": {"response_rate_pct": 0}}},
        }
        text = {"topics": topics, "menu_analysis": {
            "summary": {"pct_items_with_review_attention": 12}, "categories": []
        }}
        journey = build_customer_journey({"profile": {"features": {"parking_available": True}}}, numerical, text, observations)
        discovery = journey["stages"][0]
        self.assertIn("restaurant_profile_fact", {row["source_type"] for row in discovery["customer_evidence"]})
        self.assertIn("internal_observation", {row["source_type"] for row in discovery["management_observations"]})
        self.assertIn("proposed_experiment", {row["source_type"] for row in discovery["potential_actions"]})


class StableOutputTests(unittest.TestCase):
    def test_stable_core_values(self):
        path = ROOT / "output/restaurants/al_assiel/layer_05_reporting/layer_05_analysis_results.json"
        analysis = json.loads(path.read_text())
        overall = analysis["overall_performance"]
        self.assertEqual(overall["google_review_count"], 298)
        self.assertEqual(overall["written_reviews"], 220)
        self.assertEqual(overall["google_rating"], 4.5)
        self.assertAlmostEqual(overall["collected_average_rating"], 4.483221, places=3)


if __name__ == "__main__":
    unittest.main()
