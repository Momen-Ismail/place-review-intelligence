"""Exact common-window review, topic, response, and low-score metrics."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from itertools import combinations
from statistics import mean, median

from src.common.evidence import evidence_level
from src.layer_04_text_analysis.step_01_topic_analysis import (
    analyze_topics_with_evidence,
    match_topic_review,
)
from src.layer_04_text_analysis.step_02_dish_analysis import analyze_dishes_with_evidence


CORE_TOPIC_NAMES = [
    "Food", "Taste", "Food Quality", "Food Variety", "Freshness", "Food Temperature",
    "Food Presentation", "Meat Quality", "Portion Size", "Authenticity", "Service",
    "Staff Friendliness", "Staff Attentiveness", "Staff Professionalism", "Staff Communication",
    "Waiting Time", "Hospitality", "Price & Value", "Atmosphere", "Comfort", "Cleanliness",
    "Noise", "Terrace & Outdoor Seating", "Indoor Seating", "Drinks", "Menu & Tablet",
    "Parking", "Reservations", "Takeaway", "Card Payment", "Family & Groups", "Vegetarian & Vegan",
]

DISPLAY_TOPIC_NAMES = {
    "Menu & Tablet": "Menu / Ordering",
    "Terrace & Outdoor Seating": "Terrace / Outdoor Seating",
    "Family & Groups": "Family / Groups",
    "Vegetarian & Vegan": "Vegetarian / Vegan",
}


def _date(value) -> date | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        return None


def common_periods(cutoff: str) -> dict[str, dict]:
    end = date.fromisoformat(cutoff)
    recent_30_start = end - timedelta(days=29)
    previous_30_end = recent_30_start - timedelta(days=1)
    previous_30_start = previous_30_end - timedelta(days=29)
    recent_90_start = end - timedelta(days=89)
    previous_90_end = recent_90_start - timedelta(days=1)
    previous_90_start = previous_90_end - timedelta(days=89)
    return {
        "latest_30d": {"start": recent_30_start.isoformat(), "end": end.isoformat(), "duration_days": 30},
        "previous_30d": {"start": previous_30_start.isoformat(), "end": previous_30_end.isoformat(), "duration_days": 30},
        "recent_90d": {"start": recent_90_start.isoformat(), "end": end.isoformat(), "duration_days": 90},
        "previous_90d": {"start": previous_90_start.isoformat(), "end": previous_90_end.isoformat(), "duration_days": 90},
        "historical": {"start": None, "end": (previous_90_start - timedelta(days=1)).isoformat(), "duration_days": None},
    }


def reviews_in_period(reviews: list[dict], period: dict) -> list[dict]:
    start = date.fromisoformat(period["start"]) if period.get("start") else None
    end = date.fromisoformat(period["end"]) if period.get("end") else None
    rows = []
    for review in reviews:
        current = _date(review.get("published_at"))
        if current and (start is None or current >= start) and (end is None or current <= end):
            rows.append(review)
    return rows


def _rating(review):
    try:
        value = int(round(float(review.get("rating"))))
        return value if 1 <= value <= 5 else None
    except (TypeError, ValueError):
        return None


def _written(review):
    return bool(str(review.get("analysis_text") or review.get("text_translated") or review.get("text_original") or "").strip())


def _has_response(review):
    return bool(str(review.get("owner_response_text") or "").strip() or review.get("owner_response_date"))


def _pct(value, total):
    return round(value / total * 100, 2) if total else 0.0


def period_metrics(rows: list[dict], period: dict) -> dict:
    ratings = [_rating(row) for row in rows]
    ratings = [value for value in ratings if value is not None]
    distribution = Counter(ratings)
    written = sum(_written(row) for row in rows)
    responses = sum(_has_response(row) for row in rows)
    low = [row for row in rows if (_rating(row) or 9) <= 2]
    low_responses = sum(_has_response(row) for row in low)
    delays = []
    for row in rows:
        published = row.get("published_at"); responded = row.get("owner_response_date")
        if not (published and responded):
            continue
        try:
            p = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
            r = datetime.fromisoformat(str(responded).replace("Z", "+00:00"))
            gap = (r - p).total_seconds() / 86400
            if gap >= 0: delays.append(gap)
        except ValueError:
            pass
    days = period.get("duration_days")
    return {
        "start": period.get("start"), "end": period.get("end"), "review_count": len(rows),
        "reviews_per_week": round(len(rows) / days * 7, 3) if days else None,
        "average_rating": round(mean(ratings), 3) if ratings else None,
        "rating_distribution": {str(star): distribution[star] for star in range(5, 0, -1)},
        "five_star_count": distribution[5], "five_star_share_pct": _pct(distribution[5], len(ratings)),
        "low_score_count": len(low), "low_score_share_pct": _pct(len(low), len(ratings)),
        "written_reviews": written, "written_review_share_pct": _pct(written, len(rows)),
        "owner_responses": responses, "owner_response_rate_pct": _pct(responses, len(rows)),
        "low_score_responses": low_responses,
        "bad_review_response_rate_pct": _pct(low_responses, len(low)),
        "unanswered_low_score_count": len(low) - low_responses,
        "response_delays_with_data": len(delays),
        "median_response_delay_days": round(median(delays), 3) if delays else None,
        "evidence_level": evidence_level(len(rows)),
    }


def exact_topic_metrics(rows: list[dict], topic_definitions: list[dict]) -> list[dict]:
    wanted = [row for row in topic_definitions if row["name"] in CORE_TOPIC_NAMES]
    topics, _trends, _audit = analyze_topics_with_evidence(rows, wanted)
    result = []
    for row in topics:
        result.append({
            "topic": DISPLAY_TOPIC_NAMES.get(row["topic"], row["topic"]),
            "internal_topic": row["topic"], "count": row["reviews_mentioning"],
            "share_of_written_reviews_pct": row["mention_coverage_pct_of_written_reviews"],
            "positive_count": row["positive_reviews"],
            "positive_share_pct": row["positive_share_of_topic_reviews_pct"],
            "negative_count": row["negative_reviews"],
            "negative_share_pct": row["negative_share_of_topic_reviews_pct"],
            "neutral_count": row["neutral_reviews"],
            "average_whole_review_rating": row["average_review_rating_when_mentioned"],
            "evidence_level": row["evidence_level"],
            "positive_evidence_level": evidence_level(row["positive_reviews"]),
            "negative_evidence_level": evidence_level(row["negative_reviews"]),
        })
    return result


def trend_comparison(period_values: dict) -> dict:
    recent = period_values["recent_90d"]; previous = period_values["previous_90d"]; historical = period_values["historical"]
    def delta(field, older):
        left, right = recent.get(field), older.get(field)
        return round(left - right, 3) if left is not None and right is not None else None
    return {
        "recent_90d_vs_previous_90d": {
            "average_rating_change": delta("average_rating", previous),
            "low_score_share_change_pp": delta("low_score_share_pct", previous),
            "review_count_change": recent["review_count"] - previous["review_count"],
        },
        "recent_90d_vs_historical": {
            "average_rating_change": delta("average_rating", historical),
            "low_score_share_change_pp": delta("low_score_share_pct", historical),
        },
    }


def low_score_analysis(rows: list[dict], topics: list[dict], menu_items: list[dict]) -> dict:
    low = [row for row in rows if (_rating(row) or 9) <= 2]
    topic_rows = exact_topic_metrics(low, topics)
    present = []
    definitions = [row for row in topics if row["name"] in CORE_TOPIC_NAMES]
    for review in low:
        names = [row["name"] for row in definitions if match_topic_review(review, row)]
        present.extend(tuple(sorted(pair)) for pair in combinations(set(names), 2))
    cooccurrence = Counter(present)
    dishes, _cats, _trends, ambiguous, _audit = analyze_dishes_with_evidence(low, menu_items)
    return {
        "definition": "1-2 star Google reviews published on or before the common cutoff",
        "count": len(low), "share_pct": _pct(len(low), len(rows)), "evidence_level": evidence_level(len(low)),
        "top_negative_topics": sorted(
            [row for row in topic_rows if row["count"]],
            key=lambda row: (row["count"], row["negative_count"]), reverse=True,
        )[:10],
        "topic_cooccurrence": [
            {"topic_a": pair[0], "topic_b": pair[1], "review_count": count, "evidence_level": evidence_level(count)}
            for pair, count in cooccurrence.most_common(10)
        ],
        "dishes_involved": [
            {"dish": row["dish"], "count": row["reviews_mentioning"], "negative_count": row["negative_reviews"], "evidence_level": row["evidence_level"]}
            for row in sorted(dishes, key=lambda row: (row["reviews_mentioning"], row["negative_reviews"]), reverse=True)
            if row["reviews_mentioning"]
        ][:10],
        "ambiguous_dish_families": ambiguous,
        "menu_involvement": next((row for row in topic_rows if row["internal_topic"] == "Menu & Tablet"), None),
        "drinks_involvement": next((row for row in topic_rows if row["internal_topic"] == "Drinks"), None),
        "owner_response_rate_pct": _pct(sum(_has_response(row) for row in low), len(low)),
        "unanswered_count": sum(not _has_response(row) for row in low),
    }


def build_restaurant_periods(restaurants: dict, boundaries: dict) -> dict:
    result = {}
    for slug, data in restaurants.items():
        reviews = data["prepared"]["reviews"]
        period_rows = {name: reviews_in_period(reviews, period) for name, period in boundaries.items()}
        values = {name: period_metrics(period_rows[name], period) for name, period in boundaries.items()}
        result[slug] = {
            "periods": values,
            "trend": trend_comparison(values),
            "recent_90d_topics": exact_topic_metrics(period_rows["recent_90d"], data["profile"]["topics"]),
            "latest_30d_topics": exact_topic_metrics(period_rows["latest_30d"], data["profile"]["topics"]),
            "low_score_comparison": low_score_analysis(
                [row for row in reviews if (_date(row.get("published_at")) or date.max) <= date.fromisoformat(boundaries["recent_90d"]["end"])],
                data["profile"]["topics"], data["menu_items"],
            ),
        }
    return result


def observed_leaders(comparison: dict, thresholds: dict) -> dict:
    recent = {slug: row["periods"]["recent_90d"] for slug, row in comparison.items()}
    def leader(metric, minimum_field, minimum):
        qualified = [(slug, row[metric], row[minimum_field]) for slug, row in recent.items() if row[minimum_field] >= minimum and row[metric] is not None]
        if not qualified:
            return {"leader": None, "note": "insufficient comparable evidence", "qualified": []}
        best = max(qualified, key=lambda row: row[1])
        if sum(value == best[1] for _slug, value, _sample in qualified) > 1:
            return {
                "leader": None,
                "note": "no unique observed leader (tie)",
                "qualified": [{"restaurant": s, "value": v, "sample_size": n} for s, v, n in qualified],
            }
        return {"leader": best[0], "value": best[1], "sample_size": best[2], "qualified": [{"restaurant": s, "value": v, "sample_size": n} for s, v, n in qualified]}
    result = {
        "highest_observed_recent_rating": leader("average_rating", "review_count", thresholds["leader_overall_reviews"]),
        "highest_review_volume": leader("review_count", "review_count", thresholds["leader_overall_reviews"]),
        "highest_owner_response_rate": leader("owner_response_rate_pct", "review_count", thresholds["leader_response_reviews"]),
        "lowest_observed_negative_share": None,
    }
    qualified_low = [(slug, row["low_score_share_pct"], row["review_count"]) for slug, row in recent.items() if row["review_count"] >= thresholds["leader_overall_reviews"]]
    result["lowest_observed_negative_share"] = ({"leader": min(qualified_low, key=lambda row: row[1])[0], "value": min(qualified_low, key=lambda row: row[1])[1], "sample_size": min(qualified_low, key=lambda row: row[1])[2]} if qualified_low else {"leader": None, "note": "insufficient comparable evidence"})
    for topic in ("Food", "Service", "Price & Value"):
        candidates = []
        for slug, row in comparison.items():
            match = next((x for x in row["recent_90d_topics"] if x["internal_topic"] == topic), None)
            if match and match["count"] >= thresholds["leader_topic_mentions"] and match["positive_count"] >= thresholds["leader_topic_positive_reviews"]:
                candidates.append((slug, match))
        key = f"strongest_observed_{topic.lower().replace(' & ', '_').replace(' ', '_')}_sentiment"
        if not candidates:
            result[key] = {"leader": None, "note": "insufficient comparable evidence", "qualified": []}
        else:
            slug, match = max(candidates, key=lambda pair: (pair[1]["positive_share_pct"], pair[1]["positive_count"]))
            result[key] = {"leader": slug, "value": match["positive_share_pct"], "mentions": match["count"], "positive_count": match["positive_count"]}
    return result
