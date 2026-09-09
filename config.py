from pathlib import Path
import os

from dotenv import load_dotenv


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

# Main project folder.
# Example:
# place-review-intelligence/
BASE_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------
# ENVIRONMENT VARIABLES
# ---------------------------------------------------------

# Load private settings from:
# place-review-intelligence/.env
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


# ---------------------------------------------------------
# APIFY SETTINGS
# ---------------------------------------------------------

# Your private Apify API token.
# This will come from the .env file.
APIFY_TOKEN = os.getenv(
    "APIFY_TOKEN",
    "",
).strip()


# Apify Actor used to collect Google Maps reviews.
#
# If APIFY_ACTOR_ID is not specified in .env,
# this Actor will be used automatically.
APIFY_ACTOR_ID = os.getenv(
    "APIFY_ACTOR_ID",
    "compass/google-maps-reviews-scraper",
).strip()


# ---------------------------------------------------------
# DATA PATHS
# ---------------------------------------------------------

BUSINESS_TYPE = "restaurants"

BUSINESS_NAME = "al_assiel"

BUSINESS_DIR = (
    BASE_DIR
    / "businesses"
    / BUSINESS_TYPE
    / BUSINESS_NAME
)

DATA_DIR = BUSINESS_DIR / "data"

DATABASE_PATH = DATA_DIR / "reviews.db"

EXPORT_DIR = DATA_DIR / "exports"

ANALYSIS_DIR = BUSINESS_DIR / "analysis"

REPORTS_DIR = BUSINESS_DIR / "reports"


# ---------------------------------------------------------
# MAKE SURE REQUIRED FOLDERS EXIST
# ---------------------------------------------------------

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

EXPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

ANALYSIS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

REPORTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)
