"""Small helpers for reliable UTF-8 JSON input and output."""

import json
from pathlib import Path
from typing import Any


def load_json(path: Path | str) -> Any:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Required JSON file was not found:\n{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: "
            f"{exc.msg}"
        ) from exc


def save_json(path: Path | str, value: Any) -> None:
    """Write atomically so an interrupted run cannot leave partial JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)
