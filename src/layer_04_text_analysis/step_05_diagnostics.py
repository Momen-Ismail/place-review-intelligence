"""Period, low-score, buffet, and menu diagnostics built from review evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from src.common.evidence import evidence_level
from src.common.periods import public_period, review_periods
from src.common.text_utils import analyze_mention_sentiment, get_analysis_text


BUSINESS_AREAS = {
    "service": {"Service", "Staff Friendliness", "Staff Attentiveness", "Staff Professionalism", "Staff Communication", "Waiting Time", "Hospitality"},
    "food": {"Food", "Taste", "Food Quality", "Freshness", "Food Temperature", "Food Variety", "Food Presentation", "Meat Quality", "Portion Size", "Authenticity"},
    "value": {"Price & Value"},
    "menu_ordering": {"Menu & Tablet", "Reservations", "Takeaway", "Card Payment"},
    "drinks": {"Drinks"},
    "environment": {"Atmosphere", "Comfort", "Cleanliness", "Terrace & Outdoor Seating", "Indoor Seating", "Noise"},
    "access_convenience": {"Parking", "Family & Groups", "Vegetarian & Vegan"},
    "buffet": {"Buffet"},
}


def _pct(value, total):
    return round(value / total * 100, 2) if total else None


def _rating(review):
    try:
        return float(review.get("rating"))
    except (TypeError, ValueError):
        return None


def _has_response(review):
    return bool(str(review.get("owner_response_text") or "").strip() or review.get("owner_response_date"))


def _business_area(topic):
    return next((area for area, topics in BUSINESS_AREAS.items() if topic in topics), "other")


def _topic_index(topic_evidence):
    index = defaultdict(dict)
    for row in topic_evidence:
        index[row["review_id"]].setdefault(row["topic"], row["sentiment"])
    return index


def _dish_index(dish_evidence):
    index = defaultdict(dict)
    for row in dish_evidence:
        key = (row["dish_or_family"], row.get("match_type", "item"))
        index[row["review_id"]].setdefault(key, row["sentiment"])
    return index


def _topic_period_stats(period, topic, index):
    rows = period["rows"]
    reviews = [review for review, _timestamp in rows]
    written = [review for review in reviews if get_analysis_text(review)]
    hits = [(review, index.get(review.get("review_id"), {}).get(topic)) for review in reviews]
    hits = [(review, sentiment) for review, sentiment in hits if sentiment]
    counts = Counter(sentiment for _review, sentiment in hits)
    ratings = [_rating(review) for review, _sentiment in hits]
    ratings = [rating for rating in ratings if rating is not None]
    mentioned = len(hits)
    return {
        **public_period(period),
        "reviews_in_period": len(reviews),
        "written_reviews_in_period": len(written),
        "reviews_mentioning_topic": mentioned,
        "mention_coverage_pct_of_written_reviews": _pct(mentioned, len(written)),
        "positive_reviews": counts["positive"],
        "positive_share_of_topic_reviews_pct": _pct(counts["positive"], mentioned),
        "negative_reviews": counts["negative"],
        "negative_share_of_topic_reviews_pct": _pct(counts["negative"], mentioned),
        "neutral_reviews": counts["neutral"],
        "neutral_share_of_topic_reviews_pct": _pct(counts["neutral"], mentioned),
        "average_review_rating_when_mentioned": round(mean(ratings), 3) if ratings else None,
        "evidence_level": evidence_level(mentioned),
    }


def _change(left, right):
    return round(left - right, 2) if left is not None and right is not None else None


def topic_period_comparison(reviews, topic_evidence, topic_definitions):
    periods = review_periods(reviews)
    if not periods:
        return []
    index = _topic_index(topic_evidence)
    rows = []
    for definition in topic_definitions:
        topic = definition["name"]
        stats = {
            "historical": _topic_period_stats(periods["historical_before_recent_90d"], topic, index),
            "previous_90d": _topic_period_stats(periods["previous_90d"], topic, index),
            "recent_90d": _topic_period_stats(periods["recent_90d"], topic, index),
        }
        if not any(value["reviews_mentioning_topic"] for value in stats.values()):
            continue
        historical, previous, recent = stats["historical"], stats["previous_90d"], stats["recent_90d"]
        rows.append({
            "topic": topic,
            "business_area": _business_area(topic),
            "periods": stats,
            "recent_vs_historical_mention_change_pp": _change(recent["mention_coverage_pct_of_written_reviews"], historical["mention_coverage_pct_of_written_reviews"]),
            "recent_vs_historical_positive_share_change_pp": _change(recent["positive_share_of_topic_reviews_pct"], historical["positive_share_of_topic_reviews_pct"]),
            "recent_vs_historical_negative_share_change_pp": _change(recent["negative_share_of_topic_reviews_pct"], historical["negative_share_of_topic_reviews_pct"]),
            "recent_vs_previous90_negative_share_change_pp": _change(recent["negative_share_of_topic_reviews_pct"], previous["negative_share_of_topic_reviews_pct"]),
        })
    return rows


def _low_group(reviews, index, stars):
    members = [review for review in reviews if _rating(review) in stars]
    written = [review for review in members if get_analysis_text(review)]
    responses = sum(_has_response(review) for review in members)
    topic_counts = defaultdict(Counter)
    for review in members:
        for topic, sentiment in index.get(review.get("review_id"), {}).items():
            topic_counts[topic][sentiment] += 1
    topics = []
    for topic, counts in topic_counts.items():
        negative = counts["negative"]
        topics.append({
            "topic": topic,
            "negative_reviews": negative,
            "share_of_low_score_reviews_pct": _pct(negative, len(members)),
            "share_of_written_low_score_reviews_pct": _pct(negative, len(written)),
            "positive_reviews": counts["positive"],
            "neutral_reviews": counts["neutral"],
            "evidence_level": evidence_level(negative),
        })
    topics.sort(key=lambda row: (row["negative_reviews"], row["positive_reviews"]), reverse=True)
    return {
        "review_count": len(members),
        "share_of_all_reviews_pct": _pct(len(members), len(reviews)),
        "written_review_count": len(written),
        "owner_response_count": responses,
        "owner_response_rate_pct": _pct(responses, len(members)),
        "topics": topics,
    }


def _low_period_topic_stats(period, index):
    low = [review for review, _timestamp in period["rows"] if (_rating(review) or 9) <= 2]
    counts = Counter()
    for review in low:
        counts.update(topic for topic, sentiment in index.get(review.get("review_id"), {}).items() if sentiment == "negative")
    return low, counts


def low_rating_analysis(reviews, topic_evidence, dish_evidence):
    index = _topic_index(topic_evidence)
    dish_index = _dish_index(dish_evidence)
    periods = review_periods(reviews)
    historical_low, historical_counts = _low_period_topic_stats(periods["historical_before_recent_90d"], index)
    recent_low, recent_counts = _low_period_topic_stats(periods["recent_90d"], index)
    comparison = []
    for topic in sorted(set(historical_counts) | set(recent_counts)):
        old_count, new_count = historical_counts[topic], recent_counts[topic]
        old_pct, new_pct = _pct(old_count, len(historical_low)), _pct(new_count, len(recent_low))
        change = _change(new_pct, old_pct)
        if old_count == 0 and new_count >= 2:
            classification = "possible new complaint theme"
        elif old_count and new_count >= 2 and (change or 0) >= 5:
            classification = "complaint becoming more common"
        elif old_count and new_count:
            classification = "persistent complaint theme"
        elif old_count >= 2 and new_count == 0:
            classification = "complaint less visible recently"
        else:
            classification = "limited evidence"
        comparison.append({
            "topic": topic,
            "historical_low_score_reviews": old_count,
            "historical_coverage_pct": old_pct,
            "recent_low_score_reviews": new_count,
            "recent_coverage_pct": new_pct,
            "change_in_coverage_pct_points": change,
            "evidence_level": evidence_level(new_count),
            "classification": classification,
        })
    comparison.sort(key=lambda row: ((row["change_in_coverage_pct_points"] or -999), row["recent_low_score_reviews"]), reverse=True)

    combined = [review for review in reviews if (_rating(review) or 9) <= 2]
    pair_counts = Counter()
    for review in combined:
        topics = sorted(topic for topic, sentiment in index.get(review.get("review_id"), {}).items() if sentiment == "negative")
        for left_index, left in enumerate(topics):
            for right in topics[left_index + 1:]:
                pair_counts[(left, right)] += 1
    raw_pairs = [{
        "topic_pair": f"{left} + {right}", "topics": [left, right],
        "reviews_where_both_present": count,
        "share_of_low_score_reviews_pct": _pct(count, len(combined)),
    } for (left, right), count in pair_counts.most_common()]

    dish_rows = defaultdict(lambda: {"review_ids": set(), "negative_review_ids": set(), "match_types": set()})
    for review in combined:
        review_id = review.get("review_id")
        for (dish, match_type), sentiment in dish_index.get(review_id, {}).items():
            dish_rows[dish]["review_ids"].add(review_id)
            dish_rows[dish]["match_types"].add(match_type)
            if sentiment == "negative":
                dish_rows[dish]["negative_review_ids"].add(review_id)
    low_dishes = [{
        "dish": dish,
        "match_type": "ambiguous_family" if "ambiguous_family" in values["match_types"] else "menu_item",
        "reviews_mentioning": len(values["review_ids"]),
        "negative_dish_sentiment_count": len(values["negative_review_ids"]),
        "review_ids": sorted(values["review_ids"]),
    } for dish, values in dish_rows.items()]
    low_dishes.sort(key=lambda row: (row["negative_dish_sentiment_count"], row["reviews_mentioning"]), reverse=True)

    evidence = []
    for review in combined:
        review_id = review.get("review_id")
        negative_topics = sorted(topic for topic, sentiment in index.get(review_id, {}).items() if sentiment == "negative")
        dishes = sorted({dish for dish, _match_type in dish_index.get(review_id, {})})
        evidence.append({
            "review_id": review_id,
            "rating": int(_rating(review)),
            "date": review.get("published_at"),
            "detected_negative_topics": negative_topics,
            "detected_dishes": dishes,
            "has_owner_response": _has_response(review),
        })
    evidence.sort(key=lambda row: row["date"] or "", reverse=True)
    return {
        "definition": "Low score means 1-2 stars. Topic sentiment remains clause-based and is not inferred from stars.",
        "groups": {
            "one_star": _low_group(reviews, index, {1}),
            "two_star": _low_group(reviews, index, {2}),
            "combined_one_two_star": _low_group(reviews, index, {1, 2}),
        },
        "period_comparison": {
            "historical_low_score_review_count": len(historical_low),
            "recent_90d_low_score_review_count": len(recent_low),
            "topics": comparison,
        },
        "topic_cooccurrence": {"raw_pairs": raw_pairs, "presentation_pairs_min_2_reviews": [row for row in raw_pairs if row["reviews_where_both_present"] >= 2]},
        "low_score_dishes": low_dishes,
        "review_evidence": evidence,
    }


BUFFET_ALIASES = ["buffet", "büfett", "بوفيه"]
BUFFET_ASPECTS = {
    "quality": (["quality", "poor quality", "high quality", "نوعية", "جودة"], {"poor quality": "negative", "high quality": "positive"}),
    "variety": (["variety", "selection", "choice", "auswahl", "vielfalt", "تنوع"], {}),
    "freshness": (["fresh", "not fresh", "frisch", "nicht frisch", "طازج", "غير طازج"], {"fresh": "positive", "frisch": "positive", "طازج": "positive", "not fresh": "negative", "nicht frisch": "negative", "غير طازج": "negative"}),
    "replenishment": (["empty", "refill", "refilled", "replenished", "nachgefüllt", "leer", "فاضي", "تعبئة"], {"empty": "negative", "leer": "negative", "فاضي": "negative", "refilled": "positive", "replenished": "positive", "nachgefüllt": "positive"}),
    "value": (["value", "price", "expensive", "worth", "preis", "teuer", "سعر", "غالي"], {"expensive": "negative", "teuer": "negative", "غالي": "negative", "worth": "positive"}),
    "waiting_queue": (["wait", "queue", "slow", "warte", "schlange", "انتظار", "طابور"], {"slow": "negative", "wait": "negative", "queue": "negative", "warte": "negative", "انتظار": "negative"}),
}


def _combine_sentiments(values):
    if "negative" in values:
        return "negative"
    if "positive" in values:
        return "positive"
    return "neutral"


def _sentiment_summary(values):
    counts = Counter(values)
    count = len(values)
    return {
        "reviews": count,
        "positive": counts["positive"], "positive_pct": _pct(counts["positive"], count),
        "negative": counts["negative"], "negative_pct": _pct(counts["negative"], count),
        "neutral": counts["neutral"], "neutral_pct": _pct(counts["neutral"], count),
        "evidence_level": evidence_level(count),
    }


def buffet_deep_analysis(reviews):
    review_hits = {}
    for review in reviews:
        text = get_analysis_text(review)
        if not text:
            continue
        buffet = analyze_mention_sentiment(text, BUFFET_ALIASES)
        if not buffet["evidence"]:
            continue
        aspects = defaultdict(list)
        for local in buffet["evidence"]:
            clause = local["matched_clause"]
            for name, (aliases, polarity) in BUFFET_ASPECTS.items():
                result = analyze_mention_sentiment(clause, aliases, polarity)
                if result["evidence"]:
                    aspects[name].append(result["sentiment"])
        review_hits[review.get("review_id")] = {
            "sentiment": buffet["sentiment"],
            "aspects": {name: _combine_sentiments(values) for name, values in aspects.items()},
        }
    written = sum(bool(get_analysis_text(review)) for review in reviews)
    overall_values = [value["sentiment"] for value in review_hits.values()]
    ratings = [_rating(review) for review in reviews if review.get("review_id") in review_hits]
    ratings = [rating for rating in ratings if rating is not None]
    result = {
        "reviews_mentioning_buffet": len(review_hits),
        "mention_coverage_pct_of_written_reviews": _pct(len(review_hits), written),
        "average_review_rating_when_mentioned": round(mean(ratings), 3) if ratings else None,
        "overall_sentiment": _sentiment_summary(overall_values),
    }
    for aspect in BUFFET_ASPECTS:
        result[aspect] = _sentiment_summary([value["aspects"][aspect] for value in review_hits.values() if aspect in value["aspects"]])

    periods = review_periods(reviews)
    period_rows = {}
    for label in ("historical_before_recent_90d", "previous_90d", "recent_90d"):
        period = periods[label]
        members = [review for review, _timestamp in period["rows"]]
        written_members = [review for review in members if get_analysis_text(review)]
        hits = [review_hits[review.get("review_id")] for review in members if review.get("review_id") in review_hits]
        sentiments = [hit["sentiment"] for hit in hits]
        member_ratings = [_rating(review) for review in members if review.get("review_id") in review_hits]
        member_ratings = [rating for rating in member_ratings if rating is not None]
        period_rows[label] = {
            **public_period(period),
            "reviews_in_period": len(members),
            "written_reviews_in_period": len(written_members),
            "mentions": len(hits),
            "mention_coverage_pct_of_written_reviews": _pct(len(hits), len(written_members)),
            **_sentiment_summary(sentiments),
            "average_review_rating_when_mentioned": round(mean(member_ratings), 3) if member_ratings else None,
        }
    result["period_comparison"] = period_rows

    subtopic_periods = {}
    for aspect in BUFFET_ASPECTS:
        aspect_periods = {}
        for label in ("historical_before_recent_90d", "previous_90d", "recent_90d"):
            members = [review for review, _timestamp in periods[label]["rows"]]
            values = [review_hits[review.get("review_id")]["aspects"][aspect] for review in members
                      if review.get("review_id") in review_hits and aspect in review_hits[review.get("review_id")]["aspects"]]
            aspect_periods[label] = _sentiment_summary(values)
        subtopic_periods[aspect] = aspect_periods
    result["subtopic_period_comparison"] = subtopic_periods
    result["review_set"] = [{
        "review_id": review.get("review_id"),
        "rating": _rating(review),
        "date": review.get("published_at"),
        "sentiment": review_hits[review.get("review_id")]["sentiment"],
        "buffet_subtopics": sorted(review_hits[review.get("review_id")]["aspects"]),
        "has_owner_response": _has_response(review),
    } for review in reviews if review.get("review_id") in review_hits]
    return result


def menu_review_attention(dishes, dish_categories, ambiguous_families):
    item_rows = []
    for row in dishes:
        mentions = row["reviews_mentioning"]
        item_rows.append({
            "item": row["dish"], "english_name": row.get("english_name"),
            "category": row["menu_category"], "price_eur": row.get("price_eur"),
            "review_mentions": mentions,
            "positive_dish_reviews": row["positive_reviews"],
            "negative_dish_reviews": row["negative_reviews"],
            "neutral_dish_reviews": row["neutral_reviews"],
            "average_overall_review_rating_when_mentioned": row["average_review_rating_when_mentioned"],
            "evidence_level": row["evidence_level"],
            "review_attention_status": "review attention observed" if mentions else "no observable review mentions",
        })
    mentioned = sum(row["review_mentions"] > 0 for row in item_rows)
    categories = [{
        "category": row["menu_category"],
        "total_items": row["menu_items"],
        "items_mentioned": row["mentioned_menu_items"],
        "items_not_mentioned": row["menu_items"] - row["mentioned_menu_items"],
        "total_review_mentions": row["dish_review_mentions"],
        "positive_dish_mentions": row["positive_reviews"],
        "negative_dish_mentions": row["negative_reviews"],
    } for row in dish_categories]
    discussed = sorted((row for row in item_rows if row["review_mentions"]), key=lambda row: (row["review_mentions"], row["positive_dish_reviews"]), reverse=True)
    positive = sorted((row for row in item_rows if row["positive_dish_reviews"]), key=lambda row: (row["positive_dish_reviews"], row["review_mentions"]), reverse=True)
    return {
        "interpretation_note": "Review attention is not sales or order volume. Zero mentions are labelled no observable review mentions.",
        "summary": {
            "total_menu_items": len(item_rows),
            "total_categories": len(categories),
            "items_with_at_least_one_review_mention": mentioned,
            "items_with_no_review_mentions": len(item_rows) - mentioned,
            "pct_items_with_review_attention": round(mentioned / len(item_rows) * 100, 2) if item_rows else 0.0,
            "pct_items_without_review_attention": round((len(item_rows) - mentioned) / len(item_rows) * 100, 2) if item_rows else 0.0,
        },
        "categories": categories,
        "items": item_rows,
        "items_with_no_observable_review_mentions": [row for row in item_rows if not row["review_mentions"]],
        "ambiguous_dish_families": ambiguous_families,
        "customer_favourite_signals": {
            "terminology_note": "Observable review discussion only; do not interpret as best sellers or most ordered.",
            "most_discussed": discussed[:10],
            "most_positively_discussed": positive[:10],
        },
    }
