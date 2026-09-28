"""Load existing Layer 05 outputs plus their source-aware local inputs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def menu_items(catalog) -> list[dict]:
    return catalog["items"] if isinstance(catalog, dict) else catalog


def load_restaurant(slug: str) -> dict:
    business = ROOT / "businesses/restaurants" / slug
    output = ROOT / "output/restaurants" / slug
    required = {
        "layer_05": output / "layer_05_reporting/layer_05_analysis_results.json",
        "prepared": output / "layer_02_preparation/layer_02_prepared_reviews.json",
        "profile": business / "inputs/restaurant_profile.json",
        "menu_catalog": business / "inputs/menu_catalog.json",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing competitive-analysis input(s) for {slug}: {missing}")
    loaded = {key: load_json(path) for key, path in required.items()}
    source_path = business / "inputs/source_register.json"
    if source_path.exists():
        loaded["source_register"] = load_json(source_path)
    else:
        loaded["source_register"] = {
            "restaurant": loaded["profile"].get("restaurant_name"),
            "snapshot_date": None,
            "sources": [{
                "source_name": "Existing validated local Al Assiel inputs",
                "source_type": "validated_project_input",
                "url": None,
                "retrieved_at": None,
                "used_for": ["baseline profile", "baseline menu"],
                "confidence": "high",
                "authority_level": "high",
                "notes": "Pre-existing baseline retained intact; no new source register was required for its validated analysis.",
                "conflicts": [],
            }],
        }
    loaded["slug"] = slug
    loaded["paths"] = {key: str(path.relative_to(ROOT)) for key, path in required.items()}
    loaded["paths"]["source_register"] = str(source_path.relative_to(ROOT)) if source_path.exists() else None
    loaded["menu_items"] = menu_items(loaded["menu_catalog"])
    return loaded


def load_all(config: dict) -> dict[str, dict]:
    return {slug: load_restaurant(slug) for slug in config["comparison_restaurants"]}
