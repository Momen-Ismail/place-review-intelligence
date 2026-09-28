"""Analyze structured context, languages, responses, photos, and likes."""

from src.layer_03_numerical_analysis._calculations import (
    context_distributions,
    engagement_summary,
    language_distribution,
)


def analyze_review_context(reviews: list[dict]) -> dict:
    context_summary, context_values = context_distributions(reviews)
    return {
        "context_summary": context_summary,
        "context_values": context_values,
        "languages": language_distribution(reviews),
        "engagement": engagement_summary(reviews),
    }
