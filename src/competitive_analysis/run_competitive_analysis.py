"""Build the evidence-based four-restaurant competitive comparison JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.competitive_analysis.data_loader import ROOT, load_all, load_json
from src.competitive_analysis.menu_comparison import (
    comparable_prices, digital_footprint, dish_favourite_signals, kitchen_bar,
    menu_summary, tasting_shortlist,
)
from src.competitive_analysis.period_comparison import (
    build_restaurant_periods, common_periods, observed_leaders,
)


CONFIG_PATH = ROOT / "businesses/restaurants/competitive_config.json"
OUTPUT_DIR = ROOT / "output/competitive/restaurants"
OUTPUT_PATH = OUTPUT_DIR / "competitive_analysis_results.json"


def data_quality(data: dict) -> dict:
    dq = data["layer_05"]["data_quality"]
    reviews = data["prepared"]["reviews"]
    dates = sorted(str(row.get("published_at") or "") for row in reviews if row.get("published_at"))
    catalog = data["menu_items"]
    source_register = data["source_register"]["sources"]
    return {
        "reviews_collected": dq["total_reviews"], "written_reviews": dq["reviews_with_text"],
        "earliest_review_date": dates[0][:10] if dates else None, "latest_review_date": dates[-1][:10] if dates else None,
        "language_coverage_known_count": dq["original_language_known_count"],
        "english_written_reviews": dq["english_written_reviews"],
        "non_english_written_reviews": dq["non_english_written_reviews"],
        "translated_non_english_reviews": dq["translated_non_english_reviews"],
        "non_english_translation_coverage_pct": dq["non_english_translation_coverage_pct"],
        "usable_analysis_text_reviews": dq["usable_analysis_text_reviews"],
        "usable_analysis_text_coverage_pct": dq["usable_analysis_text_coverage_pct"],
        "duplicate_review_ids": dq["duplicate_review_ids"], "invalid_records": dq["invalid_review_count"],
        "menu_items": len(catalog), "menu_priced_items": sum(row.get("price_eur") is not None for row in catalog),
        "menu_source_completeness": "partial_public_snapshot" if data["slug"] == "al_safa" else "stored_public_snapshot",
        "profile_source_quality": "high" if any(row["confidence"] == "high" and row["source_type"].startswith("official") for row in source_register) else "medium",
    }


def common_vs_concentrated_issues(period_results: dict) -> dict:
    issue_map = {}
    for slug, row in period_results.items():
        for topic in row["low_score_comparison"]["top_negative_topics"]:
            if topic["count"]:
                issue_map.setdefault(topic["topic"], {})[slug] = {"count": topic["count"], "share_pct": topic["share_of_written_reviews_pct"], "evidence_level": topic["evidence_level"]}
    common = [{"topic": topic, "restaurants": values} for topic, values in issue_map.items() if len(values) >= 3]
    concentrated = []
    for topic, values in issue_map.items():
        if len(values) < 2: continue
        ranked = sorted(values.items(), key=lambda pair: pair[1]["share_pct"], reverse=True)
        if ranked[0][1]["count"] >= 5 and ranked[0][1]["share_pct"] >= ranked[1][1]["share_pct"] * 1.5:
            concentrated.append({"topic": topic, "restaurant": ranked[0][0], **ranked[0][1]})
    return {"common_market_issues": common, "especially_concentrated": concentrated}


def build() -> dict:
    config = load_json(CONFIG_PATH)
    restaurants = load_all(config)
    boundaries = common_periods(config["comparison_cutoff_date"])
    periods = build_restaurant_periods(restaurants, boundaries)
    full_cutoff = {"start": None, "end": config["comparison_cutoff_date"], "duration_days": None}
    tasting = {slug: tasting_shortlist(slug, data, full_cutoff, boundaries["recent_90d"]) for slug, data in restaurants.items()}
    result = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "comparison_cutoff_date": config["comparison_cutoff_date"],
            "formal_comparison_set": config["comparison_restaurants"],
            "excluded_from_formal_comparison": ["aleppo_rose"],
            "methodology": "Existing five-layer restaurant methodology plus a separate cross-restaurant comparison; this is not Layer 06.",
            "interpretation_guardrail": "Observed comparison, not proof that one restaurant is universally better.",
        },
        "common_period_boundaries": boundaries,
        "minimum_evidence_thresholds": config["minimum_evidence_thresholds"],
        "restaurant_layer_05_inputs": {slug: data["paths"]["layer_05"] for slug, data in restaurants.items()},
        "restaurant_comparisons": periods,
        "observed_leaders": observed_leaders(periods, config["minimum_evidence_thresholds"]),
        "low_score_comparison": {
            "restaurants": {slug: row["low_score_comparison"] for slug, row in periods.items()},
            **common_vs_concentrated_issues(periods),
        },
        "owner_response_benchmark": {
            slug: {
                "overall_from_layer_05": data["layer_05"]["owner_response_analysis"]["overall"],
                "recent_90d_common_window": periods[slug]["periods"]["recent_90d"],
                "low_score_through_cutoff": periods[slug]["low_score_comparison"]["owner_response_rate_pct"],
            } for slug, data in restaurants.items()
        },
        "dish_favourite_signals": {
            slug: dish_favourite_signals(data, full_cutoff)
            for slug, data in restaurants.items()
        },
        "competitor_tasting_shortlist": tasting,
        "menu_comparison": {slug: menu_summary(data) for slug, data in restaurants.items()},
        "comparable_price_basket": comparable_prices(restaurants),
        "digital_service_footprint": {slug: digital_footprint(data) for slug, data in restaurants.items()},
        "kitchen_bar_comparison": {slug: kitchen_bar(data, periods[slug]["recent_90d_topics"]) for slug, data in restaurants.items()},
        "source_registers": {slug: data["source_register"] for slug, data in restaurants.items()},
        "data_quality": {slug: data_quality(data) for slug, data in restaurants.items()},
    }
    return result


def run() -> dict:
    result = build()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Competitive restaurants: {', '.join(result['metadata']['formal_comparison_set'])}")
    print(f"Cutoff: {result['metadata']['comparison_cutoff_date']}")
    print(f"Output: {OUTPUT_PATH}")
    return result


if __name__ == "__main__":
    run()
