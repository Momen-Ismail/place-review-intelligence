from typing import Any

from apify_client import ApifyClient

from config import APIFY_TOKEN, APIFY_ACTOR_ID


class ApifyGoogleReviewsCollector:
    def __init__(
        self,
        token: str | None = None,
        actor_id: str | None = None,
    ):
        self.token = (token or APIFY_TOKEN).strip()
        self.actor_id = (actor_id or APIFY_ACTOR_ID).strip()

        if not self.token:
            raise ValueError(
                "APIFY_TOKEN is missing. Copy .env.example to .env and add your token."
            )

        if not self.actor_id:
            raise ValueError(
                "APIFY_ACTOR_ID is missing."
            )

        self.client = ApifyClient(self.token)

    def collect(
        self,
        urls: list[str],
        max_reviews: int | None = None,
        sort: str = "newest",
        language: str = "en",
        include_personal_data: bool = True,
    ) -> list[dict[str, Any]]:

        # Remove empty URLs and extra spaces.
        urls = [url.strip() for url in urls if url and url.strip()]

        if not urls:
            raise ValueError(
                "At least one Google Maps URL is required."
            )

        valid_sorts = {
            "newest",
            "mostRelevant",
            "highestRanking",
            "lowestRanking",
        }

        if sort not in valid_sorts:
            raise ValueError(
                f"Invalid sort '{sort}'. "
                f"Choose one of: {sorted(valid_sorts)}"
            )

        # None means: collect all available reviews.
        if max_reviews is not None and max_reviews < 1:
            raise ValueError(
                "max_reviews must be at least 1, "
                "or None to collect all available reviews."
            )

        run_input: dict[str, Any] = {
            "startUrls": [{"url": url} for url in urls],

            # How Google Maps reviews should be ordered.
            "reviewsSort": sort,

            # Google Maps/interface language.
            # Reviews in other languages are still collected.
            "language": language,

            # Collect reviews originating from Google.
            "reviewsOrigin": "google",

            # Disabled by default because we do not need
            # reviewer personal information for our analysis.
            "personalData": include_personal_data,
        }

        # Apify interprets the absence of maxReviews
        # as no explicit review limit.
        if max_reviews is not None:
            run_input["maxReviews"] = max_reviews

        # Start the Apify Actor and wait for it to finish.
        run = self.client.actor(
            self.actor_id
        ).call(
            run_input=run_input
        )

        if run is None:
            raise RuntimeError(
                "The Apify Actor did not return a run result."
            )

        # Every Actor run stores its results in an Apify dataset.
        dataset_id = run.default_dataset_id

        if not dataset_id:
            raise RuntimeError(
                "The Apify Actor run did not return a dataset ID."
            )

        # Read all review records returned by Apify.
        items = self.client.dataset(
            dataset_id
        ).iterate_items(
            clean=True
        )

        return list(items)