"""Read the collection database safely in query-only mode."""

import sqlite3
from pathlib import Path
from typing import Any

REQUIRED_COLUMNS = {
    "places": {"place_id", "title", "total_score", "reviews_count"},
    "reviews": {
        "review_id",
        "place_id",
        "rating",
        "text_original",
        "text_translated",
        "published_at",
        "original_language",
        "review_context_json",
        "detailed_ratings_json",
        "review_images_json",
        "owner_response_text",
        "likes_count",
    },
}


def _validate_database_schema(connection: sqlite3.Connection) -> None:
    tables = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    missing_tables = REQUIRED_COLUMNS.keys() - tables
    if missing_tables:
        raise ValueError(
            "Review database is missing table(s): "
            + ", ".join(sorted(missing_tables))
        )
    for table, required in REQUIRED_COLUMNS.items():
        existing = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})")
        }
        missing = required - existing
        if missing:
            raise ValueError(
                f"Review database table '{table}' is missing column(s): "
                + ", ".join(sorted(missing))
            )


def load_place_and_reviews(
    database_path: Path | str,
    place_id: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Review database was not found:\n{path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Review database is empty:\n{path}")

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        _validate_database_schema(connection)
        if place_id:
            place = connection.execute(
                "SELECT * FROM places WHERE place_id = ?", (place_id,)
            ).fetchone()
            if place is None:
                raise ValueError(f"Place not found: {place_id}")
        else:
            places = connection.execute("SELECT * FROM places ORDER BY title").fetchall()
            if not places:
                raise ValueError("The review database contains no places.")
            if len(places) > 1:
                raise ValueError(
                    f"The database contains {len(places)} places; specify place_id."
                )
            place = places[0]

        reviews = connection.execute(
            """
            SELECT * FROM reviews
            WHERE place_id = ?
            ORDER BY published_at IS NULL, published_at, review_id
            """,
            (place["place_id"],),
        ).fetchall()
        return dict(place), [dict(review) for review in reviews]
    finally:
        connection.close()
