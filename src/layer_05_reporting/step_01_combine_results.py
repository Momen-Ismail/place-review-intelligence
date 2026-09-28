"""Create the compact business-facing Layer 05 result."""

from datetime import datetime, timezone

from src.layer_05_reporting.management_framework import (
    build_bar_drinks_analysis,
    build_customer_journey,
    build_future_favourites_method,
    build_kitchen_bar_overview,
    build_management_baseline,
    build_menu_activation_experiments,
    build_menu_management_insights,
    build_menu_optimization_goal,
)


def _topic(row):
    return {
        "topic": row["topic"], "reviews_mentioning": row["reviews_mentioning"],
        "pct_of_written_reviews": row["mention_coverage_pct_of_written_reviews"],
        "total_mentions": row["total_mentions"], "positive_reviews": row["positive_reviews"],
        "positive_pct": row["positive_share_of_topic_reviews_pct"], "negative_reviews": row["negative_reviews"],
        "negative_pct": row["negative_share_of_topic_reviews_pct"], "neutral_reviews": row["neutral_reviews"],
        "neutral_pct": row["neutral_share_of_topic_reviews_pct"],
        "average_overall_rating": row["average_review_rating_when_mentioned"], "evidence_level": row["evidence_level"],
    }


def _dish(row):
    return {
        "dish": row["dish"], "category": row["menu_category"], "price_eur": row["price_eur"],
        "reviews_mentioning": row["reviews_mentioning"], "pct_of_written_reviews": row["mention_coverage_pct_of_written_reviews"],
        "positive_reviews": row["positive_reviews"], "positive_pct": row["positive_share_of_dish_reviews_pct"],
        "negative_reviews": row["negative_reviews"], "negative_pct": row["negative_share_of_dish_reviews_pct"],
        "neutral_reviews": row["neutral_reviews"], "average_overall_rating": row["average_review_rating_when_mentioned"],
        "evidence_level": row["evidence_level"],
    }


def _ranking(rankings, mapper):
    return {
        key: ([mapper(row) for row in value[:10]] if isinstance(value, list) else value)
        for key, value in rankings.items()
    }


def combine_results(prepared: dict, numerical: dict, text: dict, management_observations: dict) -> dict:
    summary = numerical["summary"]
    ratings = [
        {"rating": row["rating"], "count": row["count"], "pct": row["percentage_of_valid_rating_reviews"]}
        for row in numerical["rating_distribution"]
    ]
    structured = []
    for row in numerical["structured_category_ratings"]:
        structured.append({
            "category": row["category"], "average_rating": row["average_category_rating"],
            "reviews_rating_category": row["reviews_with_category_rating"],
            "coverage_pct": row["category_rating_coverage_pct_of_all_reviews"],
            "5_star_pct": row["category_5_star_share_pct"], "4_star_pct": row["category_4_star_share_pct"],
            "3_star_pct": row["category_3_star_share_pct"], "2_star_pct": row["category_2_star_share_pct"],
            "1_star_pct": row["category_1_star_share_pct"],
            "positive_pct": row["positive_category_rating_share_pct"], "negative_pct": row["negative_category_rating_share_pct"],
        })
    monthly = [{
        "month": row["month"], "reviews": row["review_count"], "average_rating": row["average_rating"],
        "positive_pct": row["positive_4_5_star_pct"], "negative_pct": row["negative_1_2_star_pct"],
        "change_vs_previous_month": row["rating_change_vs_previous_month"], "evidence_level": row["evidence_level"],
        "is_partial_month": row["is_partial_month"],
    } for row in numerical["monthly_rating_trend"]]
    mixed_signals = text["emerging_insights"].get("mixed_emerging_signals", [])
    mixed_topics = {row["topic"] for row in mixed_signals}
    management_emerging = {
        **{key: value for key, value in text["emerging_insights"].items()
           if key not in {"emerging_complaints", "emerging_strengths", "mixed_emerging_signals"}},
        "emerging_complaints": [row for row in text["emerging_insights"]["emerging_complaints"] if row["topic"] not in mixed_topics],
        "emerging_strengths": [row for row in text["emerging_insights"]["emerging_strengths"] if row["topic"] not in mixed_topics],
        "mixed_emerging_signals": mixed_signals,
    }
    recent_labels = {
        row["topic"]: f"negative +{row['change_pct_points']:.2f} pp"
        for row in text["emerging_insights"]["emerging_complaints"]
    }
    recent_labels.update({
        row["topic"]: f"positive +{row['change_pct_points']:.2f} pp"
        for row in text["emerging_insights"]["emerging_strengths"]
        if row["topic"] not in recent_labels
    })
    recent_labels.update({row["topic"]: "mixed / polarizing signal" for row in mixed_signals})
    topic_rows = []
    for row in text["topics"]:
        if not row["reviews_mentioning"]: continue
        clean = _topic(row); clean["recent_trend"] = recent_labels.get(row["topic"], "not surfaced")
        topic_rows.append(clean)
    dish_rows = [_dish(row) for row in text["dishes"] if row["reviews_mentioning"]]
    important_topics = {row["topic"] for row in text["topics"] if row["reviews_mentioning"] >= 15}
    topic_trends = [row for row in text["topic_trends"] if row["topic"] in important_topics]
    structured_trends = [{
        "month": row["month"], "category": row["category"],
        "reviews": row["reviews_with_category_rating"],
        "coverage_pct": row["category_rating_coverage_pct_of_month_reviews"],
        "average_rating": row["average_category_rating"],
        "positive_pct": row["positive_4_5_share_pct"], "negative_pct": row["negative_1_2_share_pct"],
        "change_vs_previous_available_month": row["rating_change_vs_previous_available_month"],
        "evidence_level": row["evidence_level"], "is_partial_month": row["is_partial_month"],
    } for row in numerical["structured_category_trends"]]
    context_values = []
    for row in numerical["context_values"]:
        clean = {"field": row["field"], "value": row["value"], "reviews_or_selections": row["count"],
                 "pct_of_responding_reviews": row["pct_of_responding_reviews"],
                 "average_rating": row["average_overall_review_rating"]}
        if "pct_of_field_selections" in row:
            clean["pct_of_selections"] = row["pct_of_field_selections"]
        context_values.append(clean)
    bar_drinks = build_bar_drinks_analysis(text)
    kitchen_bar = build_kitchen_bar_overview(text, bar_drinks)
    menu_management = build_menu_management_insights(text)
    menu_optimization = build_menu_optimization_goal()
    favourites_method = build_future_favourites_method()
    activation_experiments = build_menu_activation_experiments(management_observations)
    return {
        "metadata": {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "analysis_version": "4.0",
                     "profile_reference": "inputs/restaurant_profile.json", "menu_reference": "inputs/menu_catalog.json",
                     "management_observations_reference": "inputs/management_observations.json"},
        "restaurant": {"name": summary["place_name"], "category": summary["category"]},
        "data_quality": text["data_quality"],
        "overall_performance": {
            "google_rating": summary["google_overall_rating"], "google_review_count": summary["google_review_count"],
            "collected_reviews": summary["collected_reviews"], "collected_average_rating": summary["collected_average_rating"],
            "written_reviews": text["data_quality"]["reviews_with_text"],
            "written_review_coverage_pct": text["data_quality"]["written_text_coverage_pct"],
            "rating_distribution": ratings, "rating_groups": numerical["rating_groups"],
        },
        "review_cadence": numerical["review_cadence"],
        "owner_response_analysis": numerical["owner_response_analysis"],
        "structured_ratings": structured,
        "trends": {"summary": numerical["rating_trend_summary"], "monthly": monthly,
                   "structured": structured_trends},
        "topic_period_comparison": text["topic_period_comparison"],
        "low_rating_analysis": text["low_rating_analysis"],
        "topics": topic_rows, "topic_rankings": _ranking(text["topic_rankings"], _topic),
        "topic_trends": topic_trends,
        "dishes": dish_rows, "dish_rankings": _ranking(text["dish_rankings"], _dish),
        "dish_categories": text["dish_categories"],
        "ambiguous_dish_families": text["ambiguous_dish_families"], "unmapped_dishes": text["unmapped_dishes"],
        "buffet_analysis": text["buffet_analysis"],
        "menu_analysis": text["menu_analysis"],
        "customer_favourite_signals": text["customer_favourite_signals"],
        "bar_drinks_analysis": bar_drinks,
        "kitchen_bar_overview": kitchen_bar,
        "menu_management_insights": menu_management,
        "menu_optimization_goal": menu_optimization,
        "future_favourites_method": favourites_method,
        "menu_activation_experiments": activation_experiments,
        "rating_drivers": {key: value[:10] for key, value in text["rating_drivers"].items()},
        "satisfaction_vs_dissatisfaction": text["satisfaction_vs_dissatisfaction"],
        "emerging_insights": management_emerging, "business_priorities": text["business_priorities"],
        "management_observations": management_observations,
        "customer_journey": build_customer_journey(prepared, numerical, text, management_observations, kitchen_bar),
        "management_baseline": build_management_baseline(numerical, text, bar_drinks),
        "context": {"summary": numerical["context_summary"], "values": context_values},
        "languages": [{"language": row["language"], "reviews": row["count"],
                       "pct_of_reviews": row["percentage_of_all_reviews"],
                       "average_rating": row["average_review_rating"],
                       "reviews_with_text": row["reviews_with_text"]}
                      for row in numerical["languages"]],
        "structured_vs_written_note": "Google structured ratings and written-review topics are separate evidence sources and are not merged into one score.",
    }
