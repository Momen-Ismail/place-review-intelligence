"""Calculate monthly and recent-versus-historical rating trends."""

from src.layer_03_numerical_analysis._time_calculations import (
    monthly_rating_trend,
    monthly_structured_category_trends,
    rating_trend_summary,
)


def analyze_time_trends(reviews: list[dict]) -> dict:
    return {
        "monthly_rating_trend": monthly_rating_trend(reviews),
        "rating_trend_summary": rating_trend_summary(reviews),
        "structured_category_trends": monthly_structured_category_trends(reviews),
    }
