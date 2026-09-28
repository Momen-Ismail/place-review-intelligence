"""Paths and metadata for human-readable collection exports."""

from datetime import datetime, timezone
from pathlib import Path

from config import COLLECTION_SUMMARY_PATH, EXPORT_DIR
from src.common.json_utils import save_json


def export_paths(base_name: str, place_count: int) -> tuple[Path, Path]:
    stem = "reviews" if place_count == 1 else f"{base_name}_reviews"
    return EXPORT_DIR / f"{stem}.csv", EXPORT_DIR / f"{stem}.xlsx"


def save_collection_summary(
    place_count: int,
    returned_reviews: int,
    inserted_reviews: int,
    updated_reviews: int,
) -> None:
    save_json(
        COLLECTION_SUMMARY_PATH,
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "places_processed": place_count,
            "reviews_returned": returned_reviews,
            "reviews_inserted": inserted_reviews,
            "reviews_updated": updated_reviews,
        },
    )


def save_database_summary(rows: list) -> None:
    """Describe the currently stored collection without contacting Apify."""
    save_json(
        COLLECTION_SUMMARY_PATH,
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "existing reviews.db",
            "places": [
                {
                    "place_id": row["place_id"],
                    "title": row["title"],
                    "stored_reviews": row["stored_reviews"],
                    "stored_average_rating": row["stored_avg_rating"],
                }
                for row in rows
            ],
        },
    )
