import json
import unittest
from pathlib import Path

from src.common.evidence import evidence_level
from src.common.text_utils import analyze_mention_sentiment
from src.layer_03_numerical_analysis._time_calculations import monthly_rating_trend, monthly_structured_category_trends
from src.layer_04_text_analysis.step_01_topic_analysis import match_topic_review
from src.layer_04_text_analysis.step_02_dish_analysis import analyze_dishes_with_evidence, match_review_dishes
from src.layer_04_text_analysis.step_03_rankings import build_dish_rankings, build_topic_rankings
from src.layer_04_text_analysis.step_04_business_insights import (
    business_priorities, data_quality, emerging_insights, satisfaction_comparison,
)


ROOT = Path(__file__).resolve().parents[1]
MENU = json.loads((ROOT / "businesses/restaurants/al_assiel/inputs/menu_catalog.json").read_text())


def review(text, rating=1):
    return {"review_id": "test", "text_translated": text, "text_original": "", "rating": rating}


def topic(name, aliases, **extra):
    return {"name": name, "aliases": aliases, **extra}


class TopicSentimentTests(unittest.TestCase):
    def assert_topic(self, text, definition, expected):
        result = match_topic_review(review(text), definition)
        self.assertIsNotNone(result)
        self.assertEqual(result["sentiment"], expected)

    def test_contrast_food_positive_service_negative(self):
        self.assert_topic("Food was excellent but service was slow.", topic("Food", ["food"]), "positive")
        self.assert_topic("Food was excellent but service was slow.", topic("Service", ["service"]), "negative")

    def test_card_payment_neutral_even_one_star(self):
        self.assert_topic("Card payment is accepted.", topic("Card Payment", ["card payment"]), "neutral")

    def test_tasteless_alias_is_negative(self):
        self.assert_topic("The food was tasteless.", topic("Taste", ["taste", "tasteless"]), "negative")

    def test_unclear_communication_is_negative(self):
        self.assert_topic("The waiter spoke unclearly.", topic("Communication", ["waiter", "unclearly"]), "negative")

    def test_long_wait_is_negative(self):
        self.assert_topic("We waited a very long time.", topic("Waiting", ["waited"]), "negative")

    def test_clear_explanation_is_positive(self):
        self.assert_topic("The waiter explained everything clearly.", topic("Communication", ["explained"]), "positive")

    def test_negation(self):
        self.assertEqual(analyze_mention_sentiment("The food was not good", ["food"])["sentiment"], "negative")
        self.assertEqual(analyze_mention_sentiment("The food was not bad", ["food"])["sentiment"], "positive")

    def test_spoiled_burger_is_food_negative(self):
        self.assert_topic("The burger was spoiled.", topic("Food", ["food"]), "negative")
        self.assert_topic("The burger was spoiled.", topic("Food Quality", ["food quality"]), "negative")

    def test_dislike_food_is_food_and_taste_negative(self):
        text = "I don't like the food."
        self.assert_topic(text, topic("Food", ["food"]), "negative")
        self.assert_topic(text, topic("Taste", ["taste"]), "negative")

    def test_disgusting_hair_and_empty_food_are_negative(self):
        text = "The food is disgusting and there was hair in it. The food is always empty and never refilled."
        self.assert_topic(text, topic("Food", ["food"]), "negative")
        self.assert_topic(text, topic("Food Quality", ["food quality"]), "negative")
        self.assert_topic(text, topic("Buffet Replenishment", ["refill"]), "negative")

    def test_wrong_drink_is_drinks_negative(self):
        self.assert_topic("We received the wrong drink.", topic("Drinks", ["drink"]), "negative")

    def test_explicit_wait_duration_is_negative(self):
        self.assert_topic("We waited 65 minutes.", topic("Waiting Time", ["waited"]), "negative")

    def test_ambiguous_inside_and_to_go_phrases_do_not_create_topics(self):
        self.assertIsNone(match_topic_review(review("The fish was raw inside."), topic("Indoor Seating", ["inside", "indoor seating"])))
        self.assertIsNone(match_topic_review(review("We had to go to the bank."), topic("Takeaway", ["to go", "takeaway"])))

    def test_cold_drink_is_not_automatically_negative(self):
        self.assert_topic("The cold drink was good.", topic("Drinks", ["drink"]), "positive")

    def test_low_star_does_not_override_local_neutral_topic(self):
        result = match_topic_review(review("Card payment is accepted.", 1), topic("Card Payment", ["card payment"]))
        self.assertEqual(result["sentiment"], "neutral")


class DishMatchingTests(unittest.TestCase):
    def names(self, text):
        result = match_review_dishes(review(text, 5), MENU)
        items = {MENU[key]["name"] for kind, key in result["matches"] if kind == "item"}
        families = {key for kind, key in result["matches"] if kind == "family"}
        return items, families

    def test_specific_hummus_wins(self):
        items, _ = self.names("Hummus with Pesto was excellent.")
        self.assertIn("Hummus mit Pesto", items); self.assertNotIn("Hummus", items)

    def test_generic_kibbeh_is_ambiguous(self):
        items, families = self.names("kibbeh was good")
        self.assertIn("kibbeh", families); self.assertNotIn("Frittierte Kibbeh", items); self.assertNotIn("Gegrillte Kibbeh", items)

    def test_generic_shawarma_is_ambiguous(self):
        items, families = self.names("shawarma was excellent")
        self.assertIn("shawarma", families); self.assertNotIn("Shawarma Arabi", items)

    def test_specific_shawarma_sandwich(self):
        items, families = self.names("shawarma sandwich was excellent")
        self.assertIn("Shawarma Sandwich", items); self.assertNotIn("shawarma", families)

    def test_generic_falafel_is_ambiguous(self):
        items, families = self.names("falafel was excellent")
        self.assertIn("falafel", families); self.assertNotIn("Falafel Sandwich", items)

    def test_specific_falafel_plate(self):
        items, families = self.names("falafel plate was excellent")
        self.assertIn("Falafel Teller", items); self.assertNotIn("falafel", families)

    def test_generic_burger_spoilage_is_dish_family_negative(self):
        _dishes, _categories, _trends, families, audit = analyze_dishes_with_evidence(
            [review("The burger was spoiled.")], MENU
        )
        burger = next(row for row in families if row["dish_family"] == "burger")
        self.assertEqual(burger["negative_reviews"], 1)
        self.assertTrue(any(row["dish_or_family"] == "burger" and row["sentiment"] == "negative" for row in audit))

    def test_shawarma_bad_taste_is_dish_local_negative(self):
        _dishes, _categories, _trends, families, _audit = analyze_dishes_with_evidence(
            [review("The shawarma didn't taste good.")], MENU
        )
        shawarma = next(row for row in families if row["dish_family"] == "shawarma")
        self.assertEqual(shawarma["negative_reviews"], 1)


class RankingTests(unittest.TestCase):
    def test_low_evidence_topic_not_rating_ranked(self):
        row = {"topic": "Rare", "reviews_mentioning": 1, "total_mentions": 1, "positive_reviews": 0,
               "negative_reviews": 1, "average_review_rating_when_mentioned": 1.0}
        self.assertEqual(build_topic_rankings([row])["lowest_rating_when_mentioned"], [])

    def test_zero_negative_dish_not_criticized(self):
        row = {"dish": "Dish", "reviews_mentioning": 8, "total_mentions": 8, "positive_reviews": 2,
               "negative_reviews": 0, "average_review_rating_when_mentioned": 4.0}
        self.assertEqual(build_dish_rankings([row])["most_criticized_dishes"], [])

    def test_zero_positive_topic_not_positive_ranked(self):
        row = {"topic": "Topic", "reviews_mentioning": 8, "total_mentions": 8, "positive_reviews": 0,
               "negative_reviews": 2, "average_review_rating_when_mentioned": 3.0}
        self.assertEqual(build_topic_rankings([row])["highest_positive_coverage_topics"], [])

    def test_priority_requires_repeated_negative_evidence_not_volume(self):
        popular_positive = {"topic": "Popular", "reviews_mentioning": 200, "negative_reviews": 2,
                            "negative_share_of_topic_reviews_pct": 1.0,
                            "negative_coverage_pct_of_written_reviews": 0.91}
        repeated_problem = {"topic": "Problem", "reviews_mentioning": 10, "negative_reviews": 4,
                            "negative_share_of_topic_reviews_pct": 40.0,
                            "negative_coverage_pct_of_written_reviews": 1.82}
        result = business_priorities([popular_positive, repeated_problem], {"emerging_complaints": []})
        self.assertEqual([row["topic"] for row in result["priorities"]], ["Problem", "Popular"])

    def test_two_qualified_dishes_are_not_called_highest_and_lowest(self):
        dishes = [
            {"dish": "A", "reviews_mentioning": 6, "total_mentions": 6, "positive_reviews": 3,
             "negative_reviews": 0, "average_review_rating_when_mentioned": 5.0},
            {"dish": "B", "reviews_mentioning": 5, "total_mentions": 5, "positive_reviews": 2,
             "negative_reviews": 1, "average_review_rating_when_mentioned": 4.0},
        ]
        result = build_dish_rankings(dishes)
        self.assertTrue(result["insufficient_qualified_dishes_for_comparative_ranking"])
        self.assertNotIn("highest_rated_qualified_dishes", result)
        self.assertNotIn("lowest_rated_qualified_dishes", result)
        self.assertEqual([row["dish"] for row in result["qualified_dishes_by_rating"]], ["A", "B"])


class EvidenceAndQualityTests(unittest.TestCase):
    def test_zero_evidence_is_none_and_sentiment_evidence_is_specific(self):
        self.assertEqual(evidence_level(0), "none")
        result = satisfaction_comparison([
            {"topic": "Taste", "reviews_mentioning": 100, "positive_reviews": 20,
             "negative_reviews": 2, "evidence_level": "high"}
        ], {})
        self.assertEqual(result["strengths"][0]["evidence_level"], "high")
        self.assertEqual(result["weaknesses"][0]["evidence_level"], "low")

    def test_recent_priority_component_is_evidence_weighted(self):
        topic_row = {"topic": "Food", "reviews_mentioning": 20, "negative_reviews": 5,
                     "negative_share_of_topic_reviews_pct": 25.0,
                     "negative_coverage_pct_of_written_reviews": 2.0}
        emerging = {"emerging_complaints": [{"topic": "Food", "change_pct_points": 12.0,
                                               "evidence_level": "low"}]}
        row = business_priorities([topic_row], emerging)["priorities"][0]
        self.assertEqual(row["raw_recent_change"], 12.0)
        self.assertEqual(row["recent_signal_weight"], 0.5)
        self.assertEqual(row["weighted_recent_deterioration_component"], 1.5)

    def test_translation_coverage_uses_non_english_reviews(self):
        reviews = [
            {"review_id": "1", "text_original": "Hello", "text_translated": "", "original_language": "en", "rating": 5, "published_at": "2025-01-01"},
            {"review_id": "2", "text_original": "Gut", "text_translated": "Good", "original_language": "de", "rating": 5, "published_at": "2025-01-02"},
            {"review_id": "3", "text_original": "Bon", "text_translated": "", "original_language": "fr", "rating": 4, "published_at": "2025-01-03"},
            {"review_id": "4", "text_original": "", "text_translated": "", "original_language": "", "rating": 4, "published_at": "2025-01-04"},
        ]
        result = data_quality(reviews, [], [], [])
        self.assertEqual(result["english_written_reviews"], 1)
        self.assertEqual(result["non_english_written_reviews"], 2)
        self.assertEqual(result["translated_non_english_reviews"], 1)
        self.assertEqual(result["non_english_translation_coverage_pct"], 50.0)
        self.assertEqual(result["usable_analysis_text_coverage_pct"], 75.0)

    def test_first_and_last_dataset_months_are_partial(self):
        reviews = [
            {"published_at": "2024-12-24T12:00:00Z", "rating": 5, "detailed_ratings_json": '{"Food": 5}'},
            {"published_at": "2025-01-15T12:00:00Z", "rating": 4, "detailed_ratings_json": '{"Food": 4}'},
        ]
        overall = monthly_rating_trend(reviews)
        structured = monthly_structured_category_trends(reviews)
        self.assertTrue(overall[0]["is_partial_month"] and overall[-1]["is_partial_month"])
        self.assertTrue(structured[0]["is_partial_month"] and structured[-1]["is_partial_month"])

    def test_positive_and_negative_emergence_becomes_mixed(self):
        reviews = []
        evidence = []
        for index in range(10):
            reviews.append({"review_id": f"old{index}", "published_at": "2024-01-01T00:00:00Z", "text_original": "text"})
        for index, sentiment in enumerate(("positive", "positive", "negative", "negative")):
            review_id = f"new{index}"
            reviews.append({"review_id": review_id, "published_at": "2025-04-01T00:00:00Z", "text_original": "taste"})
            evidence.append({"review_id": review_id, "topic": "Taste", "sentiment": sentiment})
        result = emerging_insights(reviews, evidence)
        self.assertEqual(result["mixed_emerging_signals"][0]["topic"], "Taste")
        self.assertEqual(result["mixed_emerging_signals"][0]["signal_label"], "mixed / polarizing signal")


if __name__ == "__main__":
    unittest.main()
