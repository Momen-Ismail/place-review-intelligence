from __future__ import annotations
import json
from collections import Counter, defaultdict
from typing import Any
import pandas as pd
from src.common.evidence import evidence_level

def _percentage(numerator: int | float, denominator: int | float) -> float:
    """
    Safely calculate a percentage.
    """
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, 2)

def _safe_average(series: pd.Series) -> float | None:
    """
    Safely calculate an average from a pandas Series.
    """
    if series.empty:
        return None
    value = series.mean()
    if pd.isna(value):
        return None
    return round(float(value), 3)

def _safe_json_dict(value: Any) -> dict:
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

def _prepare_rating_dataframe(reviews: list[dict]) -> pd.DataFrame:
    """
    Create a clean dataframe containing:

        published_at
        rating

    Invalid dates or ratings are removed.
    """
    if not reviews:
        return pd.DataFrame()
    df = pd.DataFrame(reviews)
    if 'published_at' not in df.columns or 'rating' not in df.columns:
        return pd.DataFrame()
    df = df[['published_at', 'rating']].copy()
    df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True)
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df = df.dropna(subset=['published_at', 'rating'])
    df = df[(df['rating'] >= 1) & (df['rating'] <= 5)]
    return df

def monthly_rating_trend(reviews: list[dict]) -> list[dict]:
    """
    Analyze overall restaurant ratings month by month.

    For every month calculate:

        review volume
        share of all collected reviews
        average rating

        5-star count/share
        4-star count/share
        3-star count/share
        2-star count/share
        1-star count/share

        positive 4-5 star count/share
        neutral 3-star count/share
        negative 1-2 star count/share

        month-over-month average-rating change
    """
    df = _prepare_rating_dataframe(reviews)
    if df.empty:
        return []
    df['month'] = df['published_at'].dt.strftime('%Y-%m')
    earliest_timestamp = df['published_at'].min()
    earliest_month = earliest_timestamp.strftime('%Y-%m')
    earliest_month_is_partial = earliest_timestamp.day > 1
    latest_timestamp = df['published_at'].max()
    latest_month = latest_timestamp.strftime('%Y-%m')
    latest_month_is_partial = latest_timestamp.day < latest_timestamp.days_in_month
    total_valid_reviews = len(df)
    rows = []
    for month, group in df.groupby('month', sort=True):
        count = len(group)
        star_counts = Counter((int(round(rating)) for rating in group['rating']))
        positive = star_counts[5] + star_counts[4]
        neutral = star_counts[3]
        negative = star_counts[2] + star_counts[1]
        is_partial = (
            (month == earliest_month and earliest_month_is_partial)
            or (month == latest_month and latest_month_is_partial)
        )
        rows.append({'month': month, 'review_count': count, 'share_of_all_valid_reviews_pct': _percentage(count, total_valid_reviews), 'average_rating': _safe_average(group['rating']), '5_star_count': star_counts[5], '5_star_pct': _percentage(star_counts[5], count), '4_star_count': star_counts[4], '4_star_pct': _percentage(star_counts[4], count), '3_star_count': star_counts[3], '3_star_pct': _percentage(star_counts[3], count), '2_star_count': star_counts[2], '2_star_pct': _percentage(star_counts[2], count), '1_star_count': star_counts[1], '1_star_pct': _percentage(star_counts[1], count), 'positive_4_5_star_count': positive, 'positive_4_5_star_pct': _percentage(positive, count), 'neutral_3_star_count': neutral, 'neutral_3_star_pct': _percentage(neutral, count), 'negative_1_2_star_count': negative, 'negative_1_2_star_pct': _percentage(negative, count), 'evidence_level': evidence_level(count), 'is_partial_month': is_partial})
    previous_average = None
    for row in rows:
        current_average = row['average_rating']
        if previous_average is not None and current_average is not None:
            row['rating_change_vs_previous_month'] = round(current_average - previous_average, 3)
        else:
            row['rating_change_vs_previous_month'] = None
        previous_average = current_average
    return rows

def _period_statistics(df: pd.DataFrame) -> dict:
    """
    Calculate rating statistics for one time period.
    """
    if df.empty:
        return {'review_count': 0, 'average_rating': None, 'positive_count': 0, 'positive_pct': 0.0, 'neutral_count': 0, 'neutral_pct': 0.0, 'negative_count': 0, 'negative_pct': 0.0}
    count = len(df)
    positive = int((df['rating'] >= 4).sum())
    neutral = int((df['rating'] == 3).sum())
    negative = int((df['rating'] <= 2).sum())
    return {'review_count': count, 'average_rating': _safe_average(df['rating']), 'positive_count': positive, 'positive_pct': _percentage(positive, count), 'neutral_count': neutral, 'neutral_pct': _percentage(neutral, count), 'negative_count': negative, 'negative_pct': _percentage(negative, count)}

def rating_trend_summary(reviews: list[dict]) -> dict:
    """
    Produce a compact recent-vs-historical trend summary.

    Comparisons:

        latest 30 days
        previous 30 days

        latest 90 days
        previous 90 days

        historical reviews before the latest 90 days

    The newest review date is used as the anchor,
    not today's date.

    This is important because the database may later
    be analyzed without having been freshly collected.
    """
    df = _prepare_rating_dataframe(reviews)
    if df.empty:
        return {}
    newest = df['published_at'].max()
    oldest = df['published_at'].min()
    recent_30_start = newest - pd.Timedelta(days=29)
    previous_30_start = recent_30_start - pd.Timedelta(days=30)
    recent_30 = df[df['published_at'] >= recent_30_start]
    previous_30 = df[(df['published_at'] >= previous_30_start) & (df['published_at'] < recent_30_start)]
    recent_90_start = newest - pd.Timedelta(days=89)
    previous_90_start = recent_90_start - pd.Timedelta(days=90)
    recent_90 = df[df['published_at'] >= recent_90_start]
    previous_90 = df[(df['published_at'] >= previous_90_start) & (df['published_at'] < recent_90_start)]
    historical_before_90 = df[df['published_at'] < recent_90_start]
    recent_30_stats = _period_statistics(recent_30)
    previous_30_stats = _period_statistics(previous_30)
    recent_90_stats = _period_statistics(recent_90)
    previous_90_stats = _period_statistics(previous_90)
    historical_stats = _period_statistics(historical_before_90)

    def rating_delta(first: dict, second: dict) -> float | None:
        first_average = first['average_rating']
        second_average = second['average_rating']
        if first_average is None or second_average is None:
            return None
        return round(first_average - second_average, 3)

    def percentage_delta(first: dict, second: dict, field: str) -> float | None:
        if first['review_count'] == 0 or second['review_count'] == 0:
            return None
        return round(first[field] - second[field], 2)
    return {'oldest_review_date': oldest.isoformat(), 'latest_review_date': newest.isoformat(), 'valid_reviews_used': len(df), 'recent_30d_start': recent_30_start.isoformat(), 'recent_30d_reviews': recent_30_stats['review_count'], 'recent_30d_average': recent_30_stats['average_rating'], 'recent_30d_positive_pct': recent_30_stats['positive_pct'], 'recent_30d_negative_pct': recent_30_stats['negative_pct'], 'previous_30d_reviews': previous_30_stats['review_count'], 'previous_30d_average': previous_30_stats['average_rating'], 'previous_30d_positive_pct': previous_30_stats['positive_pct'], 'previous_30d_negative_pct': previous_30_stats['negative_pct'], 'rating_change_recent_30d_vs_previous_30d': rating_delta(recent_30_stats, previous_30_stats), 'positive_pct_change_recent_30d_vs_previous_30d': percentage_delta(recent_30_stats, previous_30_stats, 'positive_pct'), 'negative_pct_change_recent_30d_vs_previous_30d': percentage_delta(recent_30_stats, previous_30_stats, 'negative_pct'), 'recent_90d_start': recent_90_start.isoformat(), 'recent_90d_reviews': recent_90_stats['review_count'], 'recent_90d_average': recent_90_stats['average_rating'], 'recent_90d_positive_pct': recent_90_stats['positive_pct'], 'recent_90d_negative_pct': recent_90_stats['negative_pct'], 'previous_90d_reviews': previous_90_stats['review_count'], 'previous_90d_average': previous_90_stats['average_rating'], 'previous_90d_positive_pct': previous_90_stats['positive_pct'], 'previous_90d_negative_pct': previous_90_stats['negative_pct'], 'rating_change_recent_90d_vs_previous_90d': rating_delta(recent_90_stats, previous_90_stats), 'positive_pct_change_recent_90d_vs_previous_90d': percentage_delta(recent_90_stats, previous_90_stats, 'positive_pct'), 'negative_pct_change_recent_90d_vs_previous_90d': percentage_delta(recent_90_stats, previous_90_stats, 'negative_pct'), 'historical_before_recent_90d_reviews': historical_stats['review_count'], 'historical_before_recent_90d_average': historical_stats['average_rating'], 'historical_before_recent_90d_positive_pct': historical_stats['positive_pct'], 'historical_before_recent_90d_negative_pct': historical_stats['negative_pct'], 'rating_change_recent_90d_vs_historical': rating_delta(recent_90_stats, historical_stats), 'positive_pct_change_recent_90d_vs_historical': percentage_delta(recent_90_stats, historical_stats, 'positive_pct'), 'negative_pct_change_recent_90d_vs_historical': percentage_delta(recent_90_stats, historical_stats, 'negative_pct')}

def monthly_structured_category_trends(reviews: list[dict]) -> list[dict]:
    """
    Track Google structured ratings over time.

    Typical categories:

        Food
        Service
        Atmosphere

    For each month/category:

        reviews providing the rating
        coverage of that month's reviews
        average category rating

        5-star / 4-star / 3-star / 2-star / 1-star counts

        positive 4-5 share
        neutral 3-star share
        negative 1-2 share

        month-over-month category rating change
    """
    if not reviews:
        return []
    monthly_review_counts = Counter()
    valid_dates = []
    for review in reviews:
        published = pd.to_datetime(review.get('published_at'), errors='coerce', utc=True)
        if pd.isna(published):
            continue
        valid_dates.append(published)
        month = published.strftime('%Y-%m')
        monthly_review_counts[month] += 1
    if not valid_dates:
        return []
    earliest_timestamp = min(valid_dates)
    latest_timestamp = max(valid_dates)
    earliest_month = earliest_timestamp.strftime('%Y-%m')
    latest_month = latest_timestamp.strftime('%Y-%m')
    earliest_month_is_partial = earliest_timestamp.day > 1
    latest_month_is_partial = latest_timestamp.day < latest_timestamp.days_in_month
    rows = []
    for review in reviews:
        published = pd.to_datetime(review.get('published_at'), errors='coerce', utc=True)
        if pd.isna(published):
            continue
        ratings = _safe_json_dict(review.get('detailed_ratings_json'))
        if not ratings:
            continue
        month = published.strftime('%Y-%m')
        for category, value in ratings.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            if not 1 <= numeric <= 5:
                continue
            rows.append({'month': month, 'category': str(category), 'rating': numeric})
    if not rows:
        return []
    df = pd.DataFrame(rows)
    result_rows = []
    for (month, category), group in df.groupby(['month', 'category'], sort=True):
        rating_count = len(group)
        month_total_reviews = monthly_review_counts[month]
        star_counts = Counter((int(round(rating)) for rating in group['rating']))
        positive = star_counts[5] + star_counts[4]
        neutral = star_counts[3]
        negative = star_counts[2] + star_counts[1]
        is_partial = (
            (month == earliest_month and earliest_month_is_partial)
            or (month == latest_month and latest_month_is_partial)
        )
        result_rows.append({'month': month, 'category': category, 'month_total_reviews': month_total_reviews, 'review_count': rating_count, 'reviews_with_category_rating': rating_count, 'category_rating_coverage_pct_of_month_reviews': _percentage(rating_count, month_total_reviews), 'average_category_rating': _safe_average(group['rating']), '5_star_count': star_counts[5], '4_star_count': star_counts[4], '3_star_count': star_counts[3], '2_star_count': star_counts[2], '1_star_count': star_counts[1], 'positive_4_5_count': positive, 'positive_4_5_share_pct': _percentage(positive, rating_count), 'neutral_3_count': neutral, 'neutral_3_share_pct': _percentage(neutral, rating_count), 'negative_1_2_count': negative, 'negative_1_2_share_pct': _percentage(negative, rating_count), 'evidence_level': evidence_level(rating_count), 'is_partial_month': is_partial})
    previous_rating_by_category = {}
    for row in result_rows:
        category = row['category']
        current_average = row['average_category_rating']
        previous_average = previous_rating_by_category.get(category)
        if previous_average is not None and current_average is not None:
            row['rating_change_vs_previous_available_month'] = round(current_average - previous_average, 3)
        else:
            row['rating_change_vs_previous_available_month'] = None
        if current_average is not None:
            previous_rating_by_category[category] = current_average
    return result_rows
