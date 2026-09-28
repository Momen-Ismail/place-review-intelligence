"""Review-flow and owner-response metrics for management reporting."""

from __future__ import annotations

from collections import Counter
from statistics import mean, median

from src.common.periods import public_period, review_periods


def _pct(value, total):
    return round(value / total * 100, 2) if total else 0.0


def _round(value):
    return round(float(value), 3)


def _has_response(review: dict) -> bool:
    return bool(str(review.get("owner_response_text") or "").strip() or review.get("owner_response_date"))


def _rating(review: dict) -> int | None:
    try:
        value = int(round(float(review.get("rating"))))
        return value if 1 <= value <= 5 else None
    except (TypeError, ValueError):
        return None


def _gap_metrics(rows: list[tuple[dict, object]]) -> dict:
    timestamps = sorted(timestamp for _review, timestamp in rows)
    gaps = [
        (current - previous).total_seconds() / 86400
        for previous, current in zip(timestamps, timestamps[1:])
    ]
    return {
        "average_days_between_reviews": _round(mean(gaps)) if gaps else None,
        "median_days_between_reviews": _round(median(gaps)) if gaps else None,
        "shortest_gap_days": _round(min(gaps)) if gaps else None,
        "longest_gap_days": _round(max(gaps)) if gaps else None,
    }


def _cadence_period(period: dict) -> dict:
    count = len(period["rows"])
    days = float(period["duration_days"])
    return {
        **public_period(period),
        "review_count": count,
        "reviews_per_week": _round(count / days * 7) if days else None,
        "reviews_per_30_days": _round(count / days * 30) if days else None,
        **_gap_metrics(period["rows"]),
    }


def review_cadence_analysis(reviews: list[dict]) -> dict:
    periods = review_periods(reviews)
    if not periods:
        return {"calculation_note": "No valid review timestamps.", "periods": {}, "monthly_review_volume": [], "comparisons": {}}
    metrics = {name: _cadence_period(period) for name, period in periods.items()}
    monthly = Counter(timestamp.strftime("%Y-%m") for period in [periods["all_time"]] for _review, timestamp in period["rows"])

    def change(first, second, field):
        left, right = metrics[first].get(field), metrics[second].get(field)
        return round(left - right, 3) if left is not None and right is not None else None

    def pct_change(first, second, field):
        left, right = metrics[first].get(field), metrics[second].get(field)
        return round((left - right) / right * 100, 2) if left is not None and right else None

    return {
        "calculation_note": (
            "Rolling windows are anchored to the newest review. Gap statistics use actual consecutive "
            "review timestamps inside each period; reviews/week uses the period's calendar duration."
        ),
        "periods": metrics,
        "monthly_review_volume": [
            {"month": month, "review_count": count} for month, count in sorted(monthly.items())
        ],
        "comparisons": {
            "recent_30d_vs_previous_30d_review_count_change": change("recent_30d", "previous_30d", "review_count"),
            "recent_30d_vs_previous_30d_reviews_per_week_change": change("recent_30d", "previous_30d", "reviews_per_week"),
            "recent_30d_vs_previous_30d_frequency_change_pct": pct_change("recent_30d", "previous_30d", "reviews_per_week"),
            "recent_90d_vs_previous_90d_review_count_change": change("recent_90d", "previous_90d", "review_count"),
            "recent_90d_vs_previous_90d_reviews_per_week_change": change("recent_90d", "previous_90d", "reviews_per_week"),
        },
    }


def _response_segment(rows: list[tuple[dict, object]], include_period=True) -> dict:
    reviews = [review for review, _timestamp in rows]
    responses = sum(_has_response(review) for review in reviews)
    low = [review for review in reviews if (_rating(review) or 9) <= 2]
    low_responses = sum(_has_response(review) for review in low)
    result = {
        "review_count": len(reviews),
        "responses": responses,
        "no_response": len(reviews) - responses,
        "response_rate_pct": _pct(responses, len(reviews)),
        "low_score_review_count": len(low),
        "low_score_responses": low_responses,
        "low_score_without_response": len(low) - low_responses,
        "low_score_response_rate_pct": _pct(low_responses, len(low)),
    }
    return result


def _response_delays(reviews: list[dict]) -> dict:
    from src.common.periods import parse_timestamp

    delays = []
    for review in reviews:
        published = parse_timestamp(review.get("published_at"))
        responded = parse_timestamp(review.get("owner_response_date"))
        if not published or not responded:
            continue
        delay = (responded - published).total_seconds() / 86400
        if delay >= 0:
            delays.append(delay)
    return {
        "responses_with_valid_delay": len(delays),
        "average_response_delay_days": _round(mean(delays)) if delays else None,
        "median_response_delay_days": _round(median(delays)) if delays else None,
        "minimum_response_delay_days": _round(min(delays)) if delays else None,
        "maximum_response_delay_days": _round(max(delays)) if delays else None,
        "same_day_response_count": sum(delay < 1 for delay in delays),
        "within_1_day_count": sum(delay <= 1 for delay in delays),
        "within_3_days_count": sum(delay <= 3 for delay in delays),
        "over_7_days_count": sum(delay > 7 for delay in delays),
    }


def owner_response_analysis(reviews: list[dict]) -> dict:
    periods = review_periods(reviews)
    all_rows = periods.get("all_time", {}).get("rows", [])
    overall = _response_segment(all_rows)
    by_rating = []
    for star in range(5, 0, -1):
        rows = [row for row in all_rows if _rating(row[0]) == star]
        values = _response_segment(rows)
        by_rating.append({"rating": star, "total_reviews": values.pop("review_count"), **values})
    period_rows = {}
    for name, period in periods.items():
        if name == "all_time":
            continue
        period_rows[name] = {**public_period(period), **_response_segment(period["rows"])}
    low_reviews = []
    from src.common.periods import parse_timestamp
    for review, _timestamp in all_rows:
        rating = _rating(review)
        if rating is None or rating > 2:
            continue
        published = parse_timestamp(review.get("published_at"))
        response_date = parse_timestamp(review.get("owner_response_date"))
        delay = (response_date - published).total_seconds() / 86400 if published and response_date else None
        low_reviews.append({
            "review_id": review.get("review_id"),
            "rating": rating,
            "published_at": review.get("published_at"),
            "has_owner_response": _has_response(review),
            "owner_response_date": review.get("owner_response_date"),
            "response_delay_days": _round(delay) if delay is not None and delay >= 0 else None,
        })
    return {
        "response_definition": "Owner response is present when response text or an owner response date exists.",
        "overall": {
            "total_reviews": overall["review_count"],
            "reviews_with_owner_response": overall["responses"],
            "reviews_without_owner_response": overall["no_response"],
            "owner_response_rate_pct": overall["response_rate_pct"],
        },
        "by_star_rating": by_rating,
        "low_score": {
            "definition": "1-2 stars",
            "low_score_reviews": overall["low_score_review_count"],
            "low_score_responses": overall["low_score_responses"],
            "low_score_without_response": overall["low_score_without_response"],
            "low_score_response_rate_pct": overall["low_score_response_rate_pct"],
        },
        "periods": period_rows,
        "response_delay": _response_delays([row[0] for row in all_rows]),
        "low_score_follow_up": low_reviews,
    }
