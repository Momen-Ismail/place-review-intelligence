"""Run Layer 02: load, validate, and prepare reviews for analysis."""

import time

from config import (
    DATABASE_PATH,
    MENU_CATALOG_PATH,
    PREPARED_REVIEWS_PATH,
    RESTAURANT_PROFILE_PATH,
)
from src.common.json_utils import load_json, save_json
from src.layer_02_preparation.step_01_load_reviews import load_reviews
from src.layer_02_preparation.step_02_validate_inputs import (
    validate_menu,
    validate_profile,
)
from src.layer_02_preparation.step_03_prepare_review_text import prepare_reviews


def run() -> dict:
    started = time.perf_counter()
    print("Layer 02 — Preparation")
    print(f"Database: {DATABASE_PATH}")
    print(f"Profile:  {RESTAURANT_PROFILE_PATH}")
    print(f"Menu:     {MENU_CATALOG_PATH}")
    place, reviews = load_reviews()
    profile = validate_profile(load_json(RESTAURANT_PROFILE_PATH))
    menu = validate_menu(load_json(MENU_CATALOG_PATH))
    prepared_reviews = prepare_reviews(reviews)
    result = {
        "place": place,
        "profile": profile,
        "menu_catalog": menu,
        "review_count": len(prepared_reviews),
        "reviews": prepared_reviews,
    }
    save_json(PREPARED_REVIEWS_PATH, result)
    print(f"Reviews loaded: {len(prepared_reviews)}")
    print(f"Output: {PREPARED_REVIEWS_PATH}")
    print(f"Layer 02 complete in {time.perf_counter() - started:.2f}s")
    return result


def main() -> None:
    try:
        run()
    except Exception as exc:
        raise SystemExit(f"Layer 02 failed:\n{exc}") from exc


if __name__ == "__main__":
    main()
