from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any


def _json(value: Any) -> str:
    """
    Convert Python objects such as dictionaries and lists
    into JSON text so they can later be stored in SQLite.

    ensure_ascii=False keeps Arabic, German, etc. readable.
    """
    return json.dumps(
        value if value is not None else {},
        ensure_ascii=False,
        default=str,
    )


def _fallback_place_id(item: dict[str, Any]) -> str:
    """
    Normally Google gives us placeId.

    This fallback is only used if placeId is unexpectedly missing.
    """
    raw = (
        item.get("cid")
        or item.get("fid")
        or item.get("url")
        or item.get("title")
        or "unknown-place"
    )

    return (
        "fallback_"
        + hashlib.sha1(
            str(raw).encode("utf-8")
        ).hexdigest()[:20]
    )


def normalize_place(item: dict[str, Any]) -> dict[str, Any]:
    """
    Extract and standardize information about the PLACE itself.

    Examples:
    restaurant
    hotel
    gym
    clinic
    supermarket
    attraction
    """

    location = item.get("location") or {}

    place_id = (
        item.get("placeId")
        or _fallback_place_id(item)
    )

    return {
        # Main identifiers
        "place_id": place_id,
        "cid": item.get("cid"),
        "fid": item.get("fid"),
        "kgmid": item.get("kgmid"),
        "business_profile_id": item.get("businessProfileId"),

        # Place name and category
        "title": item.get("title"),
        "category": item.get("categoryName"),
        "categories_json": _json(
            item.get("categories") or []
        ),

        # Address
        "address": item.get("address"),
        "neighborhood": item.get("neighborhood"),
        "street": item.get("street"),
        "city": item.get("city"),
        "state": item.get("state"),
        "country_code": item.get("countryCode"),
        "postal_code": item.get("postalCode"),

        # Geographic coordinates
        "latitude": location.get("lat"),
        "longitude": location.get("lng"),

        # Google Maps rating information
        "total_score": item.get("totalScore"),
        "reviews_count": item.get("reviewsCount"),

        # Price level
        "price": item.get("price"),

        # Google Maps URLs
        "google_maps_url": item.get("url"),
        "input_url": item.get("inputStartUrl"),

        # Main image of the place
        "image_url": item.get("imageUrl"),

        # Useful for hotels
        "hotel_stars": item.get("hotelStars"),

        # Business status
        "permanently_closed": item.get(
            "permanentlyClosed"
        ),
        "temporarily_closed": item.get(
            "temporarilyClosed"
        ),

        # Whether Google marked this as an advertisement
        "is_advertisement": item.get(
            "isAdvertisement"
        ),

        # When we last collected this information
        "updated_at": (
            item.get("scrapedAt")
            or datetime.now(
                timezone.utc
            ).isoformat()
        ),
    }


def normalize_review(item: dict[str, Any]) -> dict[str, Any]:
    """
    Extract and standardize information about ONE review.
    """

    place_id = (
        item.get("placeId")
        or _fallback_place_id(item)
    )

    review_id = item.get("reviewId")

    # Google normally provides reviewId.
    # This fallback protects us if it is ever missing.
    if not review_id:
        seed = "|".join(
            [
                str(place_id),
                str(
                    item.get("publishedAtDate")
                    or item.get("publishAt")
                    or ""
                ),
                str(item.get("stars") or ""),
                str(item.get("text") or ""),
                str(item.get("reviewUrl") or ""),
            ]
        )

        review_id = (
            "fallback_"
            + hashlib.sha1(
                seed.encode("utf-8")
            ).hexdigest()
        )

    return {
        # Identifiers
        "review_id": review_id,
        "place_id": place_id,

        # Review source
        "source": (
            item.get("reviewOrigin")
            or "Google"
        ),

        # Reviewer Google profile information
        "reviewer_id": item.get("reviewerId"),
        "reviewer_name": item.get("name"),
        "reviewer_url": item.get("reviewerUrl"),
        "reviewer_number_of_reviews": item.get(
            "reviewerNumberOfReviews"
        ),
        "reviewer_photo_url": item.get(
            "reviewerPhotoUrl"
        ),
        "is_local_guide": item.get(
            "isLocalGuide"
        ),
        
        # Direct Google URL for this specific review
        "review_url": item.get("reviewUrl"),

        # Main 1-5 star rating
        "rating": item.get("stars"),

        # Full review text
        "text_original": item.get("text"),

        # Google's translated version if available
        "text_translated": item.get(
            "textTranslated"
        ),

        # Exact publication timestamp
        "published_at": item.get(
            "publishedAtDate"
        ),

        # Google display text such as:
        # "3 months ago"
        "published_relative": item.get(
            "publishAt"
        ),

        # If Google knows when the customer visited
        # Example: "January 2025"
        "visited_in": item.get("visitedIn"),

        # Languages
        "original_language": item.get(
            "originalLanguage"
        ),
        "translated_language": item.get(
            "translatedLanguage"
        ),

        # Helpful / like count
        "likes_count": (
            item.get("likesCount")
            or 0
        ),

        # Business owner's response
        "owner_response_text": item.get(
            "responseFromOwnerText"
        ),

        "owner_response_date": item.get(
            "responseFromOwnerDate"
        ),

        # Extra review information such as:
        # Meal type
        # Price per person
        # Parking
        # Noise level
        # Reservation
        # Visit type
        "review_context_json": _json(
            item.get("reviewContext") or {}
        ),

        # Detailed category ratings such as:
        # Food
        # Service
        # Atmosphere
        "detailed_ratings_json": _json(
            item.get(
                "reviewDetailedRating"
            )
            or {}
        ),

        # URLs of photos attached to this review
        "review_images_json": _json(
            item.get("reviewImageUrls") or []
        ),

        # When WE collected the review
        "scraped_at": (
            item.get("scrapedAt")
            or datetime.now(
                timezone.utc
            ).isoformat()
        ),

        # IMPORTANT:
        # Preserve the complete original Apify record.
        #
        # If Apify contains a field we have not explicitly
        # modeled above, we do NOT lose it.
        "raw_json": _json(item),
    }


def normalize_items(
    items: list[dict[str, Any]],
) -> tuple[list[dict], list[dict]]:
    """
    Normalize a complete Apify dataset.

    One place can have thousands of reviews.

    We store the place only once, while each review
    is stored separately.
    """

    places_by_id: dict[str, dict] = {}
    reviews_by_id: dict[str, dict] = {}

    for item in items:
        place = normalize_place(item)
        review = normalize_review(item)

        # Same place appears inside every review record,
        # so this keeps only one place record.
        places_by_id[
            place["place_id"]
        ] = place

        # review_id prevents duplicates.
        reviews_by_id[
            review["review_id"]
        ] = review

    return (
        list(places_by_id.values()),
        list(reviews_by_id.values()),
    )