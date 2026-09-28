"""Calculate overall ratings, rating distributions, and rating groups."""

from src.layer_03_numerical_analysis._calculations import (
    overall_summary,
    rating_distribution,
    rating_group_summary,
)


def analyze_overall_ratings(place: dict, reviews: list[dict]) -> dict:
    return {
        "summary": overall_summary(place, reviews),
        "rating_distribution": rating_distribution(reviews),
        "rating_groups": rating_group_summary(reviews),
    }
