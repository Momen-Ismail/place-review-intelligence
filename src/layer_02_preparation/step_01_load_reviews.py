"""Load the selected place and reviews without modifying SQLite."""

from config import DATABASE_PATH
from src.common.data_loader import load_place_and_reviews


def load_reviews() -> tuple[dict, list[dict]]:
    return load_place_and_reviews(DATABASE_PATH)
