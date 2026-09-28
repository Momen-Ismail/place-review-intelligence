"""Written-review topic analysis with explainable local sentiment."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from src.common.evidence import evidence_level
from src.common.text_utils import (
    NEGATIVE_TERMS,
    POSITIVE_TERMS,
    analyze_mention_sentiment,
    count_alias_occurrences,
    get_named_text_variants,
    normalize_text,
)


# Shared multilingual/business-rule extensions. These are applied by topic
# name to every restaurant, so recurring low-score language is handled without
# hardcoding review IDs or using star ratings as sentiment fallback.
TOPIC_ALIAS_EXTENSIONS = {
    "Food": {
        "neutral": ["meat", "chicken", "burger", "shawarma", "doner", "döner", "kebab", "fries", "salad"],
        "negative": ["spoiled food", "rotten food", "stale food", "disgusting food", "food poisoning", "hair in food", "undercooked food"],
    },
    "Taste": {
        "neutral": ["tasted", "tastes", "flavored", "flavoured"],
        "negative": ["tasted bad", "didn't taste good", "did not taste good", "not tasty", "no taste", "no flavor", "no flavour", "don't like the food", "do not like the food", "doesn't resemble shawarma", "does not resemble shawarma"],
    },
    "Food Quality": {
        "negative": ["spoiled", "rotten", "stale", "rancid", "disgusting", "disgusting food", "hair in food", "hair in it", "flies", "undercooked", "raw inside", "burnt", "charred", "greasy", "bone fragments", "tendons", "food poisoning"],
    },
    "Freshness": {
        "negative": ["spoiled", "rotten", "stale", "rancid", "old food", "wasn't fresh", "was not fresh", "not fresh"],
    },
    "Food Temperature": {
        "negative": ["ice cold", "arrived cold", "food was cold", "almost cold", "served cold", "then it's cold", "then it is cold", "it was cold"],
    },
    "Food Variety": {
        "negative": ["selection was limited", "very limited selection", "limited variety", "only one salad", "not enough choice"],
    },
    "Meat Quality": {
        "neutral": ["meat", "chicken", "lamb", "kebab"],
        "negative": ["dry meat", "raw meat", "raw inside", "burnt chicken", "charred chicken", "greasy meat", "bone fragments", "tendons", "old lamb"],
    },
    "Buffet Replenishment": {
        "negative": ["always empty", "food was empty", "hardly ever refilled", "never refilled", "not refilled", "nothing left"],
    },
    "Waiting Time": {
        "negative": ["took forever", "takes a long time", "long time to arrive", "food hadn't arrived", "food had not arrived", "still hadn't arrived", "still had not arrived", "orders to arrive", "waited over an hour", "waited two hours", "waiting for an hour and a half"],
    },
    "Service": {
        "neutral": ["manager", "cashier", "counter staff", "head waiter", "cook", "owner"],
        "negative": ["poor customer service", "bad service", "service was an outrage", "service was a problem", "organization needs improvement"],
    },
    "Staff Friendliness": {
        "negative": ["rude", "disrespectful", "not polite", "didn't greet", "did not greet", "yelled", "shouted", "insulting", "sexist", "racist", "harassed", "harasses"],
    },
    "Staff Attentiveness": {
        "negative": ["ignored", "forgotten", "never came", "no waiter", "no one asked", "not cleared", "not offered", "wouldn't come to the table", "would not come to the table"],
    },
    "Hospitality": {
        "negative": ["asked to leave", "treated us", "treated me", "disrespectful treatment", "different hospitality", "not welcome"],
    },
    "Reservations": {
        "negative": ["cancelled a reservation", "canceled a reservation", "reservation was cancelled", "reservation was canceled", "despite having a reservation"],
    },
    "Drinks": {
        "negative": ["wrong drink", "drinks never received", "drink never arrived", "drink was missing", "no drinks"],
    },
    "Menu & Tablet": {
        "negative": ["wrong order", "wrong side", "wrong sides", "dish was forgotten", "order was forgotten", "confusing ordering"],
    },
    "Portion Size": {
        "negative": ["small portion", "small portions", "portions were small", "portions have gotten smaller", "not enough to eat", "didn't get enough", "did not get enough", "smallest i've ever seen"],
    },
    "Cleanliness": {
        "neutral": ["toilet", "toilets", "restroom"],
        "negative": ["hair in food", "flies", "food under my feet", "food under the table", "hygiene absolutely zero", "want to throw up"],
    },
    "Card Payment": {
        "negative": ["cash only", "pay in cash", "paid in cash", "refused to accept our card", "card payments were not accepted", "doesn't accept card payments", "does not accept card payments", "couldn't pay by card", "could not pay by card", "go to the bank", "receipt"],
    },
    "Price & Value": {
        "negative": ["rip off", "rip-off", "rip me off", "overcharged", "charged twice", "also charged me", "incorrect payment", "payment was incorrect", "wrong change", "less change", "price was far too high", "far too high"],
    },
}


def _pct(value: int | float, total: int | float) -> float:
    return round(value / total * 100, 2) if total else 0.0


def _rating(review: dict) -> float | None:
    try:
        return float(review.get("rating"))
    except (TypeError, ValueError):
        return None


def _month(review: dict) -> str:
    value = str(review.get("published_at") or "")
    return value[:7] if len(value) >= 7 else "unknown"


def topic_aliases(topic: dict) -> tuple[list[str], dict[str, str]]:
    """Accept plain aliases plus optional positive/negative/neutral lists."""
    aliases: list[str] = []
    polarity: dict[str, str] = {}
    configured = topic.get("aliases", [])
    groups = configured if isinstance(configured, dict) else {"neutral": configured}
    extensions = TOPIC_ALIAS_EXTENSIONS.get(topic.get("name"), {})
    for sentiment in ("neutral", "positive", "negative"):
        values = list(groups.get(sentiment, []))
        values += topic.get(f"{sentiment}_aliases", [])
        values += extensions.get(sentiment, [])
        if topic.get("name") == "Takeaway":
            values = [value for value in values if normalize_text(value) != "to go"]
        if topic.get("name") == "Indoor Seating":
            values = [value for value in values if normalize_text(value) != "inside"]
        if topic.get("name") == "Terrace & Outdoor Seating":
            values = [value for value in values if normalize_text(value) != "outside"]
        for alias in values:
            alias = str(alias)
            aliases.append(alias)
            if sentiment != "neutral":
                polarity[normalize_text(alias)] = sentiment

    positive = {normalize_text(term) for term in POSITIVE_TERMS}
    negative = {normalize_text(term) for term in NEGATIVE_TERMS}
    for alias in aliases:
        normalized = normalize_text(alias)
        if normalized in positive:
            polarity[normalized] = "positive"
        if normalized in negative:
            polarity[normalized] = "negative"
    return list(dict.fromkeys(aliases)), polarity


def match_topic_review(review: dict, topic: dict, prepared_aliases=None) -> dict | None:
    aliases, polarity = prepared_aliases or topic_aliases(topic)
    best = None
    for variant_name, text in get_named_text_variants(review):
        count = count_alias_occurrences(text, aliases)
        if not count:
            continue
        analysis = analyze_mention_sentiment(text, aliases, polarity)
        score = (count, sum(len(x["matched_aliases"]) for x in analysis["evidence"]))
        if best is None or score > best["score"]:
            best = {
                "score": score,
                "mention_count": count,
                "text_variant_used": variant_name,
                "text": text,
                "sentiment": analysis["sentiment"],
                "local_evidence": analysis["evidence"],
            }
    return best


def analyze_topics_with_evidence(
    reviews: list[dict], topic_definitions: list[dict]
) -> tuple[list[dict], list[dict], list[dict]]:
    written = sum(bool(get_named_text_variants(review)) for review in reviews)
    monthly_written = Counter(
        _month(review) for review in reviews if get_named_text_variants(review)
    )
    rows, trends, audit = [], [], []
    for topic in topic_definitions:
        name = topic["name"]
        prepared_aliases = topic_aliases(topic)
        hits = []
        monthly = defaultdict(list)
        for review in reviews:
            match = match_topic_review(review, topic, prepared_aliases)
            if not match:
                continue
            rating = _rating(review)
            hit = {"review": review, "rating": rating, **match}
            hits.append(hit)
            monthly[_month(review)].append(hit)
            for local in match["local_evidence"]:
                for alias in local["matched_aliases"]:
                    audit.append(
                        {
                            "review_id": review.get("review_id"),
                            "topic": name,
                            "matched_alias": alias,
                            "text_variant_used": match["text_variant_used"],
                            "matched_clause": local["matched_clause"],
                            "positive_terms": local["positive_terms"],
                            "negative_terms": local["negative_terms"],
                            "sentiment": match["sentiment"],
                        }
                    )
        counts = Counter(hit["sentiment"] for hit in hits)
        ratings = [hit["rating"] for hit in hits if hit["rating"] is not None]
        mentioned = len(hits)
        rows.append(
            {
                "topic": name,
                "reviews_mentioning": mentioned,
                "mention_coverage_pct_of_written_reviews": _pct(mentioned, written),
                "total_mentions": sum(hit["mention_count"] for hit in hits),
                "positive_reviews": counts["positive"],
                "positive_share_of_topic_reviews_pct": _pct(counts["positive"], mentioned),
                "negative_reviews": counts["negative"],
                "negative_coverage_pct_of_written_reviews": _pct(counts["negative"], written),
                "negative_share_of_topic_reviews_pct": _pct(counts["negative"], mentioned),
                "neutral_reviews": counts["neutral"],
                "neutral_share_of_topic_reviews_pct": _pct(counts["neutral"], mentioned),
                "average_review_rating_when_mentioned": round(mean(ratings), 3) if ratings else None,
                "evidence_level": evidence_level(mentioned),
            }
        )
        for month, month_hits in sorted(monthly.items()):
            month_counts = Counter(hit["sentiment"] for hit in month_hits)
            month_ratings = [hit["rating"] for hit in month_hits if hit["rating"] is not None]
            count = len(month_hits)
            trends.append(
                {
                    "month": month,
                    "topic": name,
                    "reviews_mentioning": count,
                    "mention_coverage_pct_of_month_written_reviews": _pct(count, monthly_written[month]),
                    "positive_share_of_topic_reviews_pct": _pct(month_counts["positive"], count),
                    "negative_share_of_topic_reviews_pct": _pct(month_counts["negative"], count),
                    "average_review_rating_when_mentioned": round(mean(month_ratings), 3) if month_ratings else None,
                    "evidence_level": evidence_level(count),
                }
            )
    rows.sort(key=lambda row: (row["reviews_mentioning"], row["total_mentions"]), reverse=True)
    return rows, trends, audit


def analyze_topics(reviews: list[dict], topic_definitions: list[dict]) -> tuple[list[dict], list[dict]]:
    rows, trends, _audit = analyze_topics_with_evidence(reviews, topic_definitions)
    return rows, trends
