"""Shared evidence thresholds used by analysis and reporting."""


def evidence_level(review_count: int) -> str:
    if review_count <= 0:
        return "none"
    if review_count >= 15:
        return "high"
    if review_count >= 5:
        return "medium"
    return "low"
