"""Prepare a compact, cutoff-consistent data pack for the competitive deck."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SLUGS = ("al_assiel", "olivenzweig", "al_safa", "beit_fayrouz")
DISPLAY = {
    "al_assiel": "Al Assiel",
    "olivenzweig": "Olivenzweig",
    "al_safa": "Al Safa",
    "beit_fayrouz": "Beit Fayrouz",
}
CUTOFF = "2026-09-03"
MONTHS = [f"2026-{month:02d}" for month in range(1, 10)]
TOPIC_TREND_MONTHS = [f"2026-{month:02d}" for month in range(1, 9)]
TREND_TOPICS = ("Food", "Service", "Taste", "Price & Value")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_level(count: int) -> str:
    if count <= 0:
        return "none"
    if count <= 4:
        return "low"
    if count <= 14:
        return "medium"
    return "high"


def monthly_review_metrics(slug: str) -> list[dict]:
    db_path = ROOT / "businesses" / "restaurants" / slug / "data" / "reviews.db"
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT published_at, rating, owner_response_text
        FROM reviews
        WHERE substr(published_at, 1, 10) <= ?
          AND substr(published_at, 1, 7) BETWEEN '2026-01' AND '2026-09'
        ORDER BY published_at
        """,
        (CUTOFF,),
    ).fetchall()
    connection.close()
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        grouped[row["published_at"][:7]].append(row)
    output = []
    for month in MONTHS:
        values = grouped.get(month, [])
        ratings = [float(row["rating"]) for row in values if row["rating"] is not None]
        low = sum(rating <= 2 for rating in ratings)
        responses = sum(bool((row["owner_response_text"] or "").strip()) for row in values)
        output.append(
            {
                "month": month,
                "review_count": len(ratings),
                "average_rating": round(sum(ratings) / len(ratings), 3) if ratings else None,
                "low_score_count": low,
                "low_score_share_pct": round(100 * low / len(ratings), 2) if ratings else None,
                "owner_response_count": responses,
                "owner_response_rate_pct": round(100 * responses / len(ratings), 2) if ratings else None,
                "evidence_level": evidence_level(len(ratings)),
                "is_partial_month": month == "2026-09",
            }
        )
    return output


def topic_trends(layer_04: dict) -> dict[str, list[dict]]:
    index = {(row["month"], row["topic"]): row for row in layer_04["topic_trends"]}
    result: dict[str, list[dict]] = {}
    for topic in TREND_TOPICS:
        result[topic] = []
        for month in TOPIC_TREND_MONTHS:
            row = index.get((month, topic))
            mentions = row["reviews_mentioning"] if row else 0
            result[topic].append(
                {
                    "month": month,
                    "mentions": mentions,
                    "positive_share_pct": row["positive_share_of_topic_reviews_pct"] if row and mentions > 0 else None,
                    "negative_share_pct": row["negative_share_of_topic_reviews_pct"] if row and mentions > 0 else None,
                    "evidence_level": row["evidence_level"] if row and mentions > 0 else "none",
                }
            )
    return result


def compact_topics(rows: list[dict], wanted: tuple[str, ...]) -> dict[str, dict]:
    by_topic = {row["topic"]: row for row in rows}
    return {topic: by_topic.get(topic, {"topic": topic, "count": 0, "positive_count": 0, "negative_count": 0,
                                       "neutral_count": 0, "positive_share_pct": 0.0, "negative_share_pct": 0.0,
                                       "share_of_written_reviews_pct": 0.0, "evidence_level": "none"})
            for topic in wanted}


def presentation_digital_footprint(competitive: dict) -> dict:
    """Confirm Google presence from stored review datasets without inferring other services."""
    footprint = deepcopy(competitive["digital_service_footprint"])
    for slug in SLUGS:
        db_path = ROOT / "businesses" / "restaurants" / slug / "data" / "reviews.db"
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            review_count, place_identity_count = connection.execute(
                "SELECT COUNT(*), COUNT(DISTINCT place_id) FROM reviews"
            ).fetchone()
        finally:
            connection.close()
        if review_count > 0 and place_identity_count > 0:
            footprint[slug]["google_presence"] = True
            footprint[slug]["google_presence_basis"] = (
                "validated Google review collection and stored Google Maps place identity"
            )
    return footprint


def build(output_path: Path) -> None:
    competitive = load(ROOT / "output/competitive/restaurants/competitive_analysis_results.json")
    audit = load(ROOT / "output/competitive/restaurants/phase_a_accuracy_audit.json")
    digital_footprint = presentation_digital_footprint(competitive)
    restaurants = {}
    service_topics = (
        "Service", "Staff Friendliness", "Staff Attentiveness", "Staff Professionalism",
        "Staff Communication", "Waiting Time", "Hospitality",
    )
    food_topics = (
        "Food", "Taste", "Food Quality", "Freshness", "Food Temperature", "Food Presentation",
        "Food Variety", "Meat Quality", "Authenticity", "Portion Size",
    )
    for slug in SLUGS:
        base = ROOT / "output" / "restaurants" / slug
        layer_03 = load(base / "layer_03_numerical_analysis/layer_03_numerical_analysis.json")
        layer_04 = load(base / "layer_04_text_analysis/layer_04_text_analysis.json")
        layer_05 = load(base / "layer_05_reporting/layer_05_analysis_results.json")
        comp = competitive["restaurant_comparisons"][slug]
        cases = audit["restaurant_audits"][slug]["written_low_score_case_register"]
        recent_cases = [case for case in cases if "2026-06-06" <= case["date"] <= CUTOFF]
        current_topics = {row["topic"]: row for row in layer_04["topics"]}
        restaurants[slug] = {
            "display_name": DISPLAY[slug],
            "summary": layer_03["summary"],
            "periods": comp["periods"],
            "trend": comp["trend"],
            "recent_90d_topics": compact_topics(comp["recent_90d_topics"], service_topics + food_topics + ("Price & Value", "Drinks", "Cleanliness", "Atmosphere", "Buffet", "Brunch")),
            "latest_30d_topics": compact_topics(comp["latest_30d_topics"], ("Food", "Service", "Taste", "Price & Value")),
            "all_time_topics": {topic: current_topics.get(topic) for topic in service_topics + food_topics + ("Price & Value", "Drinks", "Cleanliness", "Atmosphere", "Buffet", "Brunch")},
            "monthly": monthly_review_metrics(slug),
            "topic_trends": topic_trends(layer_04),
            "low_score": audit["restaurant_audits"][slug]["after"],
            "low_score_before": audit["restaurant_audits"][slug]["before"],
            "low_score_changes": audit["restaurant_audits"][slug]["changed_negative_topic_counts"],
            "recent_low_score_cases": recent_cases,
            "all_written_low_score_cases": cases,
            "owner_response": competitive["owner_response_benchmark"][slug],
            "owner_response_full": layer_03["owner_response_analysis"],
            "menu": competitive["menu_comparison"][slug],
            "kitchen_bar": competitive["kitchen_bar_comparison"][slug],
            "dish_signals": competitive["dish_favourite_signals"][slug],
            "tasting_shortlist": competitive["competitor_tasting_shortlist"][slug],
            "digital_footprint": digital_footprint[slug],
            "layer_05_headlines": layer_05.get("executive_summary", layer_05.get("management_summary", {})),
        }
    result = {
        "metadata": competitive["metadata"],
        "common_period_boundaries": competitive["common_period_boundaries"],
        "minimum_evidence_thresholds": competitive["minimum_evidence_thresholds"],
        "data_quality": competitive["data_quality"],
        "observed_leaders": competitive["observed_leaders"],
        "low_score_comparison": competitive["low_score_comparison"],
        "menu_comparison": competitive["menu_comparison"],
        "comparable_price_basket": competitive["comparable_price_basket"],
        "dish_favourite_signals": competitive["dish_favourite_signals"],
        "tasting_shortlist": competitive["competitor_tasting_shortlist"],
        "digital_service_footprint": digital_footprint,
        "kitchen_bar_comparison": competitive["kitchen_bar_comparison"],
        "owner_response_benchmark": competitive["owner_response_benchmark"],
        "source_registers": competitive["source_registers"],
        "audit": audit,
        "restaurants": restaurants,
        "display_order": list(SLUGS),
        "display_names": DISPLAY,
        "chart_months": MONTHS,
        "topic_trend_months": TOPIC_TREND_MONTHS,
        "validation_facts": {
            "formal_restaurants": list(SLUGS),
            "excluded": ["aleppo_rose"],
            "cutoff": CUTOFF,
            "written_low_score_reviews_audited": sum(
                restaurant["low_score"]["written_low_score_reviews"] for restaurant in restaurants.values()
            ),
            "db_hashes_unchanged": all(
                row["unchanged"] for row in audit["database_integrity"].values()
            ),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared presentation data: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
