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
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)

def _fallback_place_id(item: dict[str, Any]) -> str:
    """
    Normally Google gives us placeId.

    This fallback is only used if placeId is unexpectedly missing.
    """
    raw = item.get('cid') or item.get('fid') or item.get('url') or item.get('title') or 'unknown-place'
    return 'fallback_' + hashlib.sha1(str(raw).encode('utf-8')).hexdigest()[:20]

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
    location = item.get('location') or {}
    place_id = item.get('placeId') or _fallback_place_id(item)
    return {'place_id': place_id, 'cid': item.get('cid'), 'fid': item.get('fid'), 'kgmid': item.get('kgmid'), 'business_profile_id': item.get('businessProfileId'), 'title': item.get('title'), 'category': item.get('categoryName'), 'categories_json': _json(item.get('categories') or []), 'address': item.get('address'), 'neighborhood': item.get('neighborhood'), 'street': item.get('street'), 'city': item.get('city'), 'state': item.get('state'), 'country_code': item.get('countryCode'), 'postal_code': item.get('postalCode'), 'latitude': location.get('lat'), 'longitude': location.get('lng'), 'total_score': item.get('totalScore'), 'reviews_count': item.get('reviewsCount'), 'price': item.get('price'), 'google_maps_url': item.get('url'), 'input_url': item.get('inputStartUrl'), 'image_url': item.get('imageUrl'), 'hotel_stars': item.get('hotelStars'), 'permanently_closed': item.get('permanentlyClosed'), 'temporarily_closed': item.get('temporarilyClosed'), 'is_advertisement': item.get('isAdvertisement'), 'updated_at': item.get('scrapedAt') or datetime.now(timezone.utc).isoformat()}

def normalize_review(item: dict[str, Any]) -> dict[str, Any]:
    """
    Extract and standardize information about ONE review.
    """
    place_id = item.get('placeId') or _fallback_place_id(item)
    review_id = item.get('reviewId')
    if not review_id:
        seed = '|'.join([str(place_id), str(item.get('publishedAtDate') or item.get('publishAt') or ''), str(item.get('stars') or ''), str(item.get('text') or ''), str(item.get('reviewUrl') or '')])
        review_id = 'fallback_' + hashlib.sha1(seed.encode('utf-8')).hexdigest()
    return {'review_id': review_id, 'place_id': place_id, 'source': item.get('reviewOrigin') or 'Google', 'reviewer_id': item.get('reviewerId'), 'reviewer_name': item.get('name'), 'reviewer_url': item.get('reviewerUrl'), 'reviewer_number_of_reviews': item.get('reviewerNumberOfReviews'), 'reviewer_photo_url': item.get('reviewerPhotoUrl'), 'is_local_guide': item.get('isLocalGuide'), 'review_url': item.get('reviewUrl'), 'rating': item.get('stars'), 'text_original': item.get('text'), 'text_translated': item.get('textTranslated'), 'published_at': item.get('publishedAtDate'), 'published_relative': item.get('publishAt'), 'visited_in': item.get('visitedIn'), 'original_language': item.get('originalLanguage'), 'translated_language': item.get('translatedLanguage'), 'likes_count': item.get('likesCount') or 0, 'owner_response_text': item.get('responseFromOwnerText'), 'owner_response_date': item.get('responseFromOwnerDate'), 'review_context_json': _json(item.get('reviewContext') or {}), 'detailed_ratings_json': _json(item.get('reviewDetailedRating') or {}), 'review_images_json': _json(item.get('reviewImageUrls') or []), 'scraped_at': item.get('scrapedAt') or datetime.now(timezone.utc).isoformat(), 'raw_json': _json(item)}

def normalize_items(items: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
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
        places_by_id[place['place_id']] = place
        reviews_by_id[review['review_id']] = review
    return (list(places_by_id.values()), list(reviews_by_id.values()))
