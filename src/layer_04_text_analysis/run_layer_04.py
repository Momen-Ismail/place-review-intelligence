"""Run Layer 04 topic, dish, sentiment, and ranking analysis."""

import time
from datetime import datetime, timezone

from config import PREPARED_REVIEWS_PATH, TEXT_ANALYSIS_PATH
from src.common.json_utils import load_json, save_json
from src.layer_04_text_analysis.step_01_topic_analysis import analyze_topics_with_evidence
from src.layer_04_text_analysis.step_02_dish_analysis import (
    analyze_dishes_with_evidence,
)
from src.layer_04_text_analysis.step_03_rankings import (
    build_dish_rankings,
    build_topic_rankings,
)
from src.layer_04_text_analysis.step_04_business_insights import (
    business_priorities,
    data_quality,
    emerging_insights,
    find_unmapped_dishes,
    rating_drivers,
    satisfaction_comparison,
)
from src.layer_04_text_analysis.step_05_diagnostics import (
    buffet_deep_analysis,
    low_rating_analysis,
    menu_review_attention,
    topic_period_comparison,
)


def run() -> dict:
    started = time.perf_counter()
    print("Layer 04 — Text Analysis")
    print(f"Input: {PREPARED_REVIEWS_PATH}")
    prepared = load_json(PREPARED_REVIEWS_PATH)
    reviews = prepared["reviews"]
    topics, topic_trends, topic_evidence = analyze_topics_with_evidence(
        reviews, prepared["profile"]["topics"]
    )
    dishes, dish_categories, dish_trends, ambiguous, dish_evidence = analyze_dishes_with_evidence(
        reviews, prepared["menu_catalog"]
    )
    unmapped = find_unmapped_dishes(reviews, prepared["menu_catalog"])
    emerging = emerging_insights(reviews, topic_evidence)
    topic_comparison = topic_period_comparison(reviews, topic_evidence, prepared["profile"]["topics"])
    low_ratings = low_rating_analysis(reviews, topic_evidence, dish_evidence)
    buffet = buffet_deep_analysis(reviews)
    menu = menu_review_attention(dishes, dish_categories, ambiguous)
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sentiment_method": "explicit alias polarity plus local clause sentiment and negation; no star-rating fallback",
        "topics": topics,
        "topic_rankings": build_topic_rankings(topics),
        "topic_trends": topic_trends,
        "dishes": dishes,
        "ambiguous_dish_families": ambiguous,
        "unmapped_dishes": unmapped,
        "dish_rankings": build_dish_rankings(dishes),
        "dish_categories": dish_categories,
        "dish_trends": dish_trends,
        "topic_period_comparison": topic_comparison,
        "low_rating_analysis": low_ratings,
        "buffet_analysis": buffet,
        "menu_analysis": {key: value for key, value in menu.items() if key != "customer_favourite_signals"},
        "customer_favourite_signals": menu["customer_favourite_signals"],
        "rating_drivers": rating_drivers(reviews, topic_evidence),
        "satisfaction_vs_dissatisfaction": satisfaction_comparison(topics, emerging),
        "emerging_insights": emerging,
        "business_priorities": business_priorities(topics, emerging),
        "data_quality": data_quality(reviews, prepared["menu_catalog"], ambiguous, unmapped),
        "topic_match_evidence": topic_evidence,
        "dish_match_evidence": dish_evidence,
    }
    save_json(TEXT_ANALYSIS_PATH, result)
    print(f"Reviews analyzed: {len(reviews)}")
    print(f"Output: {TEXT_ANALYSIS_PATH}")
    print(f"Layer 04 complete in {time.perf_counter() - started:.2f}s")
    return result


def main() -> None:
    try:
        run()
    except Exception as exc:
        raise SystemExit(f"Layer 04 failed:\n{exc}") from exc


if __name__ == "__main__":
    main()
