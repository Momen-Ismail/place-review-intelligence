"""Central configuration for the active business and all project paths."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "").strip()
APIFY_ACTOR_ID = os.getenv(
    "APIFY_ACTOR_ID", "compass/google-maps-reviews-scraper"
).strip()

BUSINESS_TYPE = "restaurants"
# Keep Al Assiel as the default while allowing the unchanged five-layer
# pipeline to run against one explicitly selected, isolated restaurant.
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "al_assiel").strip() or "al_assiel"

BUSINESS_DIR = BASE_DIR / "businesses" / BUSINESS_TYPE / BUSINESS_NAME
INPUT_DIR = BUSINESS_DIR / "inputs"
DATA_DIR = BUSINESS_DIR / "data"
DATABASE_PATH = DATA_DIR / "reviews.db"

OUTPUT_DIR = BASE_DIR / "output" / BUSINESS_TYPE / BUSINESS_NAME
LAYER_01_OUTPUT_DIR = OUTPUT_DIR / "layer_01_collection"
LAYER_02_OUTPUT_DIR = OUTPUT_DIR / "layer_02_preparation"
LAYER_03_OUTPUT_DIR = OUTPUT_DIR / "layer_03_numerical_analysis"
LAYER_04_OUTPUT_DIR = OUTPUT_DIR / "layer_04_text_analysis"
LAYER_05_OUTPUT_DIR = OUTPUT_DIR / "layer_05_reporting"

# Backward-compatible name used by the collection CLI.
EXPORT_DIR = LAYER_01_OUTPUT_DIR

RESTAURANT_PROFILE_PATH = INPUT_DIR / "restaurant_profile.json"
MENU_CATALOG_PATH = INPUT_DIR / "menu_catalog.json"
MANAGEMENT_OBSERVATIONS_PATH = INPUT_DIR / "management_observations.json"
PREPARED_REVIEWS_PATH = LAYER_02_OUTPUT_DIR / "layer_02_prepared_reviews.json"
NUMERICAL_ANALYSIS_PATH = (
    LAYER_03_OUTPUT_DIR / "layer_03_numerical_analysis.json"
)
TEXT_ANALYSIS_PATH = LAYER_04_OUTPUT_DIR / "layer_04_text_analysis.json"
FINAL_ANALYSIS_PATH = LAYER_05_OUTPUT_DIR / "layer_05_analysis_results.json"
FINAL_EXCEL_PATH = LAYER_05_OUTPUT_DIR / "layer_05_restaurant_analysis.xlsx"
COLLECTION_SUMMARY_PATH = LAYER_01_OUTPUT_DIR / "layer_01_collection_summary.json"
COLLECTION_SNAPSHOT_PATH = DATA_DIR / "collection_snapshot.json"

for directory in (
    INPUT_DIR,
    DATA_DIR,
    LAYER_01_OUTPUT_DIR,
    LAYER_02_OUTPUT_DIR,
    LAYER_03_OUTPUT_DIR,
    LAYER_04_OUTPUT_DIR,
    LAYER_05_OUTPUT_DIR,
):
    directory.mkdir(parents=True, exist_ok=True)
