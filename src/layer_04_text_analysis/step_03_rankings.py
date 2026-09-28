"""Build transparent topic and dish rankings from calculated evidence."""

MINIMUM_DISH_REVIEWS_FOR_RATING_RANK = 5
MINIMUM_TOPIC_REVIEWS_FOR_RATING_RANK = 5


def build_topic_rankings(topics: list[dict]) -> dict[str, list[dict]]:
    active = [dict(row) for row in topics if row.get("reviews_mentioning", 0) > 0]
    with_ratings = [
        row for row in active
        if row.get("reviews_mentioning", 0) >= MINIMUM_TOPIC_REVIEWS_FOR_RATING_RANK
        and row.get("average_review_rating_when_mentioned") is not None
    ]
    return {
        "minimum_mentions_for_rating_rank": MINIMUM_TOPIC_REVIEWS_FOR_RATING_RANK,
        "most_discussed_topics": sorted(
            active,
            key=lambda row: (row.get("reviews_mentioning", 0), row.get("total_mentions", 0)),
            reverse=True,
        ),
        "highest_positive_coverage_topics": sorted(
            [row for row in active if row.get("positive_reviews", 0) > 0],
            key=lambda row: (row.get("positive_reviews", 0), row.get("reviews_mentioning", 0)),
            reverse=True,
        ),
        "highest_negative_coverage_topics": sorted(
            [row for row in active if row.get("negative_reviews", 0) > 0],
            key=lambda row: (row.get("negative_reviews", 0), row.get("reviews_mentioning", 0)),
            reverse=True,
        ),
        "highest_rating_when_mentioned": sorted(
            with_ratings,
            key=lambda row: (row["average_review_rating_when_mentioned"], row["reviews_mentioning"]),
            reverse=True,
        ),
        "lowest_rating_when_mentioned": sorted(
            with_ratings,
            key=lambda row: (row["average_review_rating_when_mentioned"], -row["reviews_mentioning"]),
        ),
    }


def build_dish_rankings(dishes: list[dict]) -> dict:
    active = [dict(row) for row in dishes if row.get("reviews_mentioning", 0) > 0]
    qualified = [
        row
        for row in active
        if row.get("reviews_mentioning", 0) >= MINIMUM_DISH_REVIEWS_FOR_RATING_RANK
        and row.get("average_review_rating_when_mentioned") is not None
    ]
    qualified_by_rating = sorted(
        qualified,
        key=lambda row: (row["average_review_rating_when_mentioned"], row["reviews_mentioning"]),
        reverse=True,
    )
    result = {
        "minimum_mentions_for_rating_rank": MINIMUM_DISH_REVIEWS_FOR_RATING_RANK,
        "minimum_qualified_dishes_for_comparative_ranking": 3,
        "insufficient_qualified_dishes_for_comparative_ranking": len(qualified) < 3,
        "qualified_dishes_by_rating": qualified_by_rating,
        "most_discussed_dishes": sorted(
            active,
            key=lambda row: (row.get("reviews_mentioning", 0), row.get("total_mentions", 0)),
            reverse=True,
        ),
        "most_praised_dishes": sorted(
            [row for row in active if row.get("positive_reviews", 0) > 0],
            key=lambda row: (row.get("positive_reviews", 0), row.get("reviews_mentioning", 0)),
            reverse=True,
        ),
        "most_criticized_dishes": sorted(
            [row for row in active if row.get("negative_reviews", 0) > 0],
            key=lambda row: (row.get("negative_reviews", 0), row.get("reviews_mentioning", 0)),
            reverse=True,
        ),
    }
    if len(qualified) >= 3:
        result["highest_rated_qualified_dishes"] = qualified_by_rating
        result["lowest_rated_qualified_dishes"] = sorted(
            qualified,
            key=lambda row: (row["average_review_rating_when_mentioned"], -row["reviews_mentioning"]),
        )
    return result
