from __future__ import annotations
import json
from collections import Counter, defaultdict
from statistics import mean
from typing import Any

def safe_json_dict(value: Any) -> dict:
    """
    Safely convert a JSON value into a dictionary.
    """
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        result = json.loads(value)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return {}

def safe_json_list(value: Any) -> list:
    """
    Safely convert a JSON value into a list.
    """
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        result = json.loads(value)
        if isinstance(result, list):
            return result
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return []

def numeric_value(value: Any) -> float | None:
    """
    Safely convert a value into a number.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _percentage(numerator: int | float, denominator: int | float) -> float:
    """
    Safely calculate percentage.
    """
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, 2)

def _average(values: list[int | float]) -> float | None:
    """
    Return rounded arithmetic mean.
    """
    if not values:
        return None
    return round(mean(values), 3)

def _review_rating(review: dict) -> float | None:
    """
    Return one review's overall star rating.
    """
    return numeric_value(review.get('rating'))

def _valid_review_ratings(reviews: list[dict]) -> list[float]:
    """
    Return all valid overall review ratings.
    """
    ratings = []
    for review in reviews:
        rating = _review_rating(review)
        if rating is not None:
            ratings.append(rating)
    return ratings

def overall_summary(place: dict, reviews: list[dict]) -> dict:
    """
    Basic high-level restaurant statistics.
    """
    total_reviews = len(reviews)
    ratings = _valid_review_ratings(reviews)
    valid_rating_count = len(ratings)
    google_review_count = numeric_value(place.get('reviews_count'))
    collection_coverage = None
    if google_review_count and google_review_count > 0:
        collection_coverage = _percentage(total_reviews, google_review_count)
    return {'place_name': place.get('title'), 'category': place.get('category'), 'google_overall_rating': numeric_value(place.get('total_score')), 'google_review_count': place.get('reviews_count'), 'collected_reviews': total_reviews, 'valid_rating_reviews': valid_rating_count, 'missing_rating_reviews': total_reviews - valid_rating_count, 'collected_average_rating': _average(ratings), 'collection_coverage_pct': collection_coverage, 'minimum_collected_rating': min(ratings) if ratings else None, 'maximum_collected_rating': max(ratings) if ratings else None}

def rating_distribution(reviews: list[dict]) -> list[dict]:
    """
    Calculate exact 1-5 star distribution.

    Every row includes:

        count
        percentage of all reviews
        percentage of reviews with valid ratings
    """
    total_reviews = len(reviews)
    ratings = _valid_review_ratings(reviews)
    valid_rating_count = len(ratings)
    counts = Counter()
    for rating in ratings:
        star = int(round(rating))
        if 1 <= star <= 5:
            counts[star] += 1
    result = []
    for star in [5, 4, 3, 2, 1]:
        count = counts[star]
        result.append({'rating': star, 'count': count, 'percentage_of_all_reviews': _percentage(count, total_reviews), 'percentage_of_valid_rating_reviews': _percentage(count, valid_rating_count)})
    return result

def rating_group_summary(reviews: list[dict]) -> list[dict]:
    """
    Group star ratings into:

        Positive = 4-5 stars
        Neutral  = 3 stars
        Negative = 1-2 stars
    """
    total_reviews = len(reviews)
    ratings = _valid_review_ratings(reviews)
    valid_rating_count = len(ratings)
    positive = sum((1 for rating in ratings if rating >= 4))
    neutral = sum((1 for rating in ratings if rating > 2 and rating < 4))
    negative = sum((1 for rating in ratings if rating <= 2))
    groups = [('Positive 4-5 stars', positive), ('Neutral 3 stars', neutral), ('Negative 1-2 stars', negative)]
    return [{'rating_group': name, 'count': count, 'coverage_pct_of_all_reviews': _percentage(count, total_reviews), 'share_pct_of_valid_ratings': _percentage(count, valid_rating_count)} for name, count in groups]

def structured_category_ratings(reviews: list[dict]) -> list[dict]:
    """
    Analyze Google structured detailed ratings.

    Typical examples:

        Food
        Service
        Atmosphere

    IMPORTANT:

    This is NOT written-text mention analysis.

    Example:

        Service structured rating:
            160 reviews

    may be different from:

        Reviews mentioning Service in text:
            210 reviews

    The text calculation belongs to topics.py.
    """
    total_reviews = len(reviews)
    category_values = defaultdict(list)
    overall_ratings = defaultdict(list)
    category_star_counts = defaultdict(Counter)
    for review in reviews:
        detailed = safe_json_dict(review.get('detailed_ratings_json'))
        overall_rating = _review_rating(review)
        for category, value in detailed.items():
            category_rating = numeric_value(value)
            if category_rating is None:
                continue
            category_values[category].append(category_rating)
            star = int(round(category_rating))
            if 1 <= star <= 5:
                category_star_counts[category][star] += 1
            if overall_rating is not None:
                overall_ratings[category].append(overall_rating)
    result = []
    for category in sorted(category_values):
        values = category_values[category]
        rating_count = len(values)
        related_overall = overall_ratings[category]
        star_counts = category_star_counts[category]
        result.append({'category': category, 'average_category_rating': _average(values), 'reviews_with_category_rating': rating_count, 'category_rating_coverage_pct_of_all_reviews': _percentage(rating_count, total_reviews), 'average_overall_review_rating_when_category_rated': _average(related_overall), 'category_5_star_count': star_counts[5], 'category_4_star_count': star_counts[4], 'category_3_star_count': star_counts[3], 'category_2_star_count': star_counts[2], 'category_1_star_count': star_counts[1], 'category_5_star_share_pct': _percentage(star_counts[5], rating_count), 'category_4_star_share_pct': _percentage(star_counts[4], rating_count), 'category_3_star_share_pct': _percentage(star_counts[3], rating_count), 'category_2_star_share_pct': _percentage(star_counts[2], rating_count), 'category_1_star_share_pct': _percentage(star_counts[1], rating_count), 'positive_category_ratings': star_counts[5] + star_counts[4], 'positive_category_rating_share_pct': _percentage(star_counts[5] + star_counts[4], rating_count), 'negative_category_ratings': star_counts[1] + star_counts[2], 'negative_category_rating_share_pct': _percentage(star_counts[1] + star_counts[2], rating_count)})
    return result

def structured_category_distribution(reviews: list[dict]) -> list[dict]:
    """
    Produce one row per:

        category
        star rating

    Example:

        Food | 5 | 100 reviews | 65%
        Food | 4 | 30 reviews  | 20%
        ...
    """
    total_reviews = len(reviews)
    category_counts = defaultdict(Counter)
    category_totals = Counter()
    for review in reviews:
        detailed = safe_json_dict(review.get('detailed_ratings_json'))
        for category, value in detailed.items():
            numeric = numeric_value(value)
            if numeric is None:
                continue
            star = int(round(numeric))
            if not 1 <= star <= 5:
                continue
            category_counts[category][star] += 1
            category_totals[category] += 1
    rows = []
    for category in sorted(category_totals):
        category_total = category_totals[category]
        for star in [5, 4, 3, 2, 1]:
            count = category_counts[category][star]
            rows.append({'category': category, 'rating': star, 'count': count, 'pct_of_category_ratings': _percentage(count, category_total), 'pct_of_all_reviews': _percentage(count, total_reviews)})
    return rows
MULTI_SELECT_CONTEXT_FIELDS = {'Group size', 'Parking options', 'Recommended dishes', 'Seating type', 'Vegetarian offerings'}

def _context_selections(field: str, value: Any) -> list[str]:
    """Split only known Google multi-select fields, never arbitrary comments."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, dict):
        return [json.dumps(value, ensure_ascii=False)]
    text = str(value).strip()
    if not text:
        return []
    if field in MULTI_SELECT_CONTEXT_FIELDS:
        return [part.strip() for part in text.split(',') if part.strip()]
    return [text]

def context_distributions(reviews: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Analyze structured Google review context.

    Examples:

        Meal type
        Price per person
        Wait time
        Group size
        Parking space
        Noise level
        Vegetarian recommendation
        Vegetarian offerings

    Returns:

        context_summary_rows
        context_value_rows
    """
    total_reviews = len(reviews)
    field_entries = defaultdict(list)
    for review in reviews:
        context = safe_json_dict(review.get('review_context_json'))
        overall_rating = _review_rating(review)
        for field, value in context.items():
            if value is None:
                continue
            for selection in _context_selections(str(field), value):
                field_entries[field].append({'value': selection, 'rating': overall_rating, 'review_id': review.get('review_id')})
    summary_rows = []
    value_rows = []
    for field in sorted(field_entries):
        entries = field_entries[field]
        response_count = len({entry['review_id'] for entry in entries})
        selection_count = len(entries)
        is_multi_select = field in MULTI_SELECT_CONTEXT_FIELDS
        values = [entry['value'] for entry in entries]
        value_counter = Counter(values)
        rating_by_review = {entry['review_id']: entry['rating'] for entry in entries if entry['rating'] is not None}
        associated_ratings = list(rating_by_review.values())
        summary_rows.append({'field': field, 'reviews_with_value': response_count, 'coverage_pct_of_all_reviews': _percentage(response_count, total_reviews), 'distinct_values': len(value_counter), 'total_selections': selection_count, 'average_overall_review_rating_when_field_present': _average(associated_ratings)})
        for value, count in value_counter.most_common():
            matching_entries = [entry for entry in entries if entry['value'] == value]
            ratings = [entry['rating'] for entry in matching_entries if entry['rating'] is not None]
            positive = sum((1 for rating in ratings if rating >= 4))
            neutral = sum((1 for rating in ratings if rating > 2 and rating < 4))
            negative = sum((1 for rating in ratings if rating <= 2))
            row = {'field': field, 'value': value, 'count': count,
                   'pct_of_responding_reviews': _percentage(count, response_count),
                   'average_overall_review_rating': _average(ratings),
                   'is_multi_select': is_multi_select}
            if is_multi_select:
                row['pct_of_field_selections'] = _percentage(count, selection_count)
            value_rows.append(row)
    return (summary_rows, value_rows)

def language_distribution(reviews: list[dict]) -> list[dict]:
    """
    Analyze the original review language.

    Includes review count, coverage, text availability
    and average rating by language.
    """
    total_reviews = len(reviews)
    language_reviews = defaultdict(list)
    for review in reviews:
        has_text = bool(str(review.get('text_original') or '').strip() or str(review.get('text_translated') or '').strip())
        language = review.get('original_language') or ('unknown_language' if has_text else 'no_text')
        language = str(language).strip()
        if not language:
            language = 'unknown_language' if has_text else 'no_text'
        language_reviews[language].append(review)
    rows = []
    for language, items in language_reviews.items():
        count = len(items)
        ratings = _valid_review_ratings(items)
        written_count = 0
        for review in items:
            original = str(review.get('text_original') or '').strip()
            translated = str(review.get('text_translated') or '').strip()
            if original or translated:
                written_count += 1
        rows.append({'language': language, 'count': count, 'percentage_of_all_reviews': _percentage(count, total_reviews), 'reviews_with_text': written_count, 'text_coverage_pct_within_language': _percentage(written_count, count), 'average_review_rating': _average(ratings)})
    rows.sort(key=lambda row: row['count'], reverse=True)
    return rows

def engagement_summary(reviews: list[dict]) -> dict:
    """
    Analyze:

        written review coverage
        owner responses
        review photos
        likes
    """
    total_reviews = len(reviews)
    owner_response_count = 0
    reviews_with_photos = 0
    reviews_with_text = 0
    likes = []
    ratings_with_response = []
    ratings_without_response = []
    ratings_with_photos = []
    ratings_without_photos = []
    for review in reviews:
        rating = _review_rating(review)
        response = str(review.get('owner_response_text') or '').strip()
        if response:
            owner_response_count += 1
            if rating is not None:
                ratings_with_response.append(rating)
        elif rating is not None:
            ratings_without_response.append(rating)
        images = safe_json_list(review.get('review_images_json'))
        if images:
            reviews_with_photos += 1
            if rating is not None:
                ratings_with_photos.append(rating)
        elif rating is not None:
            ratings_without_photos.append(rating)
        original = str(review.get('text_original') or '').strip()
        translated = str(review.get('text_translated') or '').strip()
        if original or translated:
            reviews_with_text += 1
        like_value = numeric_value(review.get('likes_count'))
        if like_value is not None:
            likes.append(like_value)
    return {'total_reviews': total_reviews, 'reviews_with_text': reviews_with_text, 'text_coverage_pct': _percentage(reviews_with_text, total_reviews), 'reviews_without_text': total_reviews - reviews_with_text, 'owner_response_count': owner_response_count, 'owner_response_rate_pct': _percentage(owner_response_count, total_reviews), 'average_rating_of_reviews_with_owner_response': _average(ratings_with_response), 'average_rating_of_reviews_without_owner_response': _average(ratings_without_response), 'reviews_with_photos': reviews_with_photos, 'reviews_with_photos_pct': _percentage(reviews_with_photos, total_reviews), 'average_rating_of_reviews_with_photos': _average(ratings_with_photos), 'average_rating_of_reviews_without_photos': _average(ratings_without_photos), 'total_likes': int(sum(likes)) if likes else 0, 'average_likes': _average(likes) if likes else 0.0, 'maximum_likes': int(max(likes)) if likes else 0, 'reviews_with_at_least_one_like': sum((1 for like in likes if like > 0)), 'reviews_with_at_least_one_like_pct': _percentage(sum((1 for like in likes if like > 0)), total_reviews)}
