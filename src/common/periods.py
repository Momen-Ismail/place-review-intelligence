"""Shared, deterministic review-period helpers.

All rolling windows are anchored to the newest valid review timestamp so an
older snapshot remains reproducible when it is analyzed later.
"""

from __future__ import annotations

from datetime import datetime, timedelta


def parse_timestamp(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def dated_reviews(reviews: list[dict]) -> list[tuple[dict, datetime]]:
    rows = []
    for review in reviews:
        timestamp = parse_timestamp(review.get("published_at"))
        if timestamp is not None:
            rows.append((review, timestamp))
    return sorted(rows, key=lambda row: row[1])


def review_periods(reviews: list[dict]) -> dict[str, dict]:
    """Return the standard management comparison windows and their reviews."""
    rows = dated_reviews(reviews)
    if not rows:
        return {}
    oldest = rows[0][1]
    newest = rows[-1][1]
    recent_30_start = newest - timedelta(days=29)
    previous_30_start = recent_30_start - timedelta(days=30)
    recent_90_start = newest - timedelta(days=89)
    previous_90_start = recent_90_start - timedelta(days=90)

    def period(name, start, end, duration_days, predicate):
        return {
            "period": name,
            "start": start,
            "end": end,
            "duration_days": duration_days,
            "rows": [row for row in rows if predicate(row[1])],
        }

    all_time_days = max((newest - oldest).total_seconds() / 86400 + 1, 1)
    historical_days = max((recent_90_start - oldest).total_seconds() / 86400, 0)
    return {
        "all_time": period("all_time", oldest, newest, all_time_days, lambda value: True),
        "recent_30d": period("recent_30d", recent_30_start, newest, 30, lambda value: value >= recent_30_start),
        "previous_30d": period(
            "previous_30d", previous_30_start, recent_30_start, 30,
            lambda value: previous_30_start <= value < recent_30_start,
        ),
        "recent_90d": period("recent_90d", recent_90_start, newest, 90, lambda value: value >= recent_90_start),
        "previous_90d": period(
            "previous_90d", previous_90_start, recent_90_start, 90,
            lambda value: previous_90_start <= value < recent_90_start,
        ),
        "historical_before_recent_90d": period(
            "historical_before_recent_90d", oldest, recent_90_start, historical_days,
            lambda value: value < recent_90_start,
        ),
    }


def public_period(period: dict) -> dict:
    """Remove internal review objects from a period descriptor."""
    return {
        "period": period["period"],
        "start": period["start"].isoformat(),
        "end": period["end"].isoformat(),
        "duration_days": round(float(period["duration_days"]), 3),
    }
