"""Write the combined Layer 05 JSON output."""

from pathlib import Path

from src.common.json_utils import save_json


def export_analysis_json(path: Path | str, analysis: dict) -> None:
    save_json(path, analysis)
