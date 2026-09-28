"""Analyze Google-provided Food, Service, and Atmosphere ratings."""

from src.layer_03_numerical_analysis._calculations import (
    structured_category_distribution,
    structured_category_ratings,
)


def analyze_structured_ratings(reviews: list[dict]) -> dict:
    return {
        "structured_category_ratings": structured_category_ratings(reviews),
        "structured_category_distribution": structured_category_distribution(reviews),
    }
