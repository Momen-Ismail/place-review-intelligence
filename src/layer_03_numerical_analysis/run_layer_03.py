"""Run Layer 03 using the prepared Layer 02 data."""

import time
from datetime import datetime, timezone

from config import NUMERICAL_ANALYSIS_PATH, PREPARED_REVIEWS_PATH
from src.common.json_utils import load_json, save_json
from src.layer_03_numerical_analysis.step_01_overall_ratings import (
    analyze_overall_ratings,
)
from src.layer_03_numerical_analysis.step_02_structured_ratings import (
    analyze_structured_ratings,
)
from src.layer_03_numerical_analysis.step_03_review_context import (
    analyze_review_context,
)
from src.layer_03_numerical_analysis.step_04_time_trends import analyze_time_trends
from src.layer_03_numerical_analysis.step_05_management_metrics import (
    owner_response_analysis,
    review_cadence_analysis,
)


def run() -> dict:
    started = time.perf_counter()
    print("Layer 03 — Numerical Analysis")
    print(f"Input: {PREPARED_REVIEWS_PATH}")
    prepared = load_json(PREPARED_REVIEWS_PATH)
    reviews = prepared["reviews"]
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "place": prepared["place"],
        **analyze_overall_ratings(prepared["place"], reviews),
        **analyze_structured_ratings(reviews),
        **analyze_review_context(reviews),
        **analyze_time_trends(reviews),
        "review_cadence": review_cadence_analysis(reviews),
        "owner_response_analysis": owner_response_analysis(reviews),
    }
    save_json(NUMERICAL_ANALYSIS_PATH, result)
    print(f"Reviews analyzed: {len(reviews)}")
    print(f"Output: {NUMERICAL_ANALYSIS_PATH}")
    print(f"Layer 03 complete in {time.perf_counter() - started:.2f}s")
    return result


def main() -> None:
    try:
        run()
    except Exception as exc:
        raise SystemExit(f"Layer 03 failed:\n{exc}") from exc


if __name__ == "__main__":
    main()
