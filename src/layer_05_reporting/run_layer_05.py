"""Run Layer 05: combine prior results and create JSON and Excel reports."""

import time

from config import (
    FINAL_ANALYSIS_PATH,
    FINAL_EXCEL_PATH,
    MANAGEMENT_OBSERVATIONS_PATH,
    NUMERICAL_ANALYSIS_PATH,
    PREPARED_REVIEWS_PATH,
    TEXT_ANALYSIS_PATH,
)
from src.common.json_utils import load_json
from src.layer_05_reporting.step_01_combine_results import combine_results
from src.layer_05_reporting.step_02_export_json import export_analysis_json
from src.layer_05_reporting.step_03_export_excel import export_analysis_excel
from src.layer_05_reporting.management_framework import validate_management_observations


def run() -> dict:
    started = time.perf_counter()
    print("Layer 05 — Reporting")
    print(f"Numerical input: {NUMERICAL_ANALYSIS_PATH}")
    print(f"Text input:      {TEXT_ANALYSIS_PATH}")
    prepared = load_json(PREPARED_REVIEWS_PATH)
    numerical = load_json(NUMERICAL_ANALYSIS_PATH)
    text = load_json(TEXT_ANALYSIS_PATH)
    management_observations = validate_management_observations(load_json(MANAGEMENT_OBSERVATIONS_PATH))
    result = combine_results(prepared, numerical, text, management_observations)
    export_analysis_json(FINAL_ANALYSIS_PATH, result)
    export_analysis_excel(FINAL_EXCEL_PATH, result, prepared)
    print(f"Reviews reported: {prepared['review_count']}")
    print(f"JSON output: {FINAL_ANALYSIS_PATH}")
    print(f"Excel output: {FINAL_EXCEL_PATH}")
    print(f"Layer 05 complete in {time.perf_counter() - started:.2f}s")
    return result


def main() -> None:
    try:
        run()
    except Exception as exc:
        raise SystemExit(f"Layer 05 failed:\n{exc}") from exc


if __name__ == "__main__":
    main()
