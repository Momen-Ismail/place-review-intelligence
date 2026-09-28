"""Compact, transparent business insights derived from Layer 04 evidence."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from src.common.evidence import evidence_level
from src.common.text_utils import analyze_mention_sentiment, get_analysis_text, normalize_text
from src.layer_04_text_analysis.step_02_dish_analysis import item_aliases


def _pct(value, total):
    return round(value / total * 100, 2) if total else 0.0


def _date(review):
    try:
        return datetime.fromisoformat(str(review.get("published_at")).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _json_dict(value):
    if isinstance(value, dict): return value
    try: return json.loads(value) if value else {}
    except (TypeError, ValueError, json.JSONDecodeError): return {}


def data_quality(reviews, menu_items, ambiguous_rows, unmapped_rows):
    total = len(reviews)
    text = [r for r in reviews if get_analysis_text(r)]
    ids = [r.get("review_id") for r in reviews if r.get("review_id")]
    known_language = sum(bool(str(r.get("original_language") or "").strip()) for r in text)
    english_written = sum(str(r.get("original_language") or "").strip().lower() == "en" for r in text)
    non_english = [r for r in text if str(r.get("original_language") or "").strip().lower() != "en"]
    translated_non_english = sum(bool(str(r.get("text_translated") or "").strip()) for r in non_english)
    usable_analysis_text = sum(bool(get_analysis_text(r)) for r in reviews)
    def structured_coverage(category):
        count = 0
        for review in reviews:
            detailed = _json_dict(review.get("detailed_ratings_json"))
            count += any(str(key).lower() == category for key in detailed)
        return _pct(count, total)
    invalid = sum(
        not r.get("review_id") or not isinstance(r, dict)
        or (r.get("rating") is not None and not str(r.get("rating")).replace(".", "", 1).isdigit())
        for r in reviews
    )
    return {
        "total_reviews": total, "reviews_with_text": len(text), "reviews_without_text": total - len(text),
        "written_text_coverage_pct": _pct(len(text), total),
        "missing_rating_count": sum(r.get("rating") is None for r in reviews),
        "missing_date_count": sum(not r.get("published_at") for r in reviews),
        "original_language_known_count": known_language,
        "english_written_reviews": english_written,
        "non_english_written_reviews": len(non_english),
        "translated_non_english_reviews": translated_non_english,
        "non_english_translation_coverage_pct": _pct(translated_non_english, len(non_english)),
        "usable_analysis_text_reviews": usable_analysis_text,
        "usable_analysis_text_coverage_pct": _pct(usable_analysis_text, total),
        "structured_food_coverage_pct": structured_coverage("food"),
        "structured_service_coverage_pct": structured_coverage("service"),
        "structured_atmosphere_coverage_pct": structured_coverage("atmosphere"),
        "ambiguous_dish_mentions": sum(row.get("total_mentions", 0) for row in ambiguous_rows),
        "unmapped_dish_count": len(unmapped_rows),
        "duplicate_review_ids": len(ids) - len(set(ids)), "invalid_review_count": invalid,
    }


def find_unmapped_dishes(reviews, menu_items):
    known = {normalize_text(alias) for item in menu_items for alias in item_aliases(item)}
    counts = Counter()
    for review in reviews:
        context = _json_dict(review.get("review_context_json"))
        values = context.get("Recommended dishes") or context.get("Recommended Dishes") or []
        if isinstance(values, str): values = [part.strip() for part in values.split(",")]
        if not isinstance(values, list): values = [values]
        for value in values:
            name = str(value).strip()
            normalized = normalize_text(name)
            if normalized and normalized not in known:
                counts[name] += 1
    return [
        {"name": name, "source": "google_recommended_dishes", "reviews_or_mentions": count}
        for name, count in counts.most_common()
    ]


def buffet_analysis(reviews):
    buffet_aliases = ["buffet", "büfett", "بوفيه"]
    aspects = {
        "quality": (["quality", "poor quality", "high quality", "نوعية", "جودة"], {"poor quality": "negative", "high quality": "positive"}),
        "variety": (["variety", "selection", "choice", "auswahl", "vielfalt", "تنوع"], {}),
        "freshness": (["fresh", "not fresh", "frisch", "nicht frisch", "طازج", "غير طازج"], {"fresh": "positive", "frisch": "positive", "طازج": "positive", "not fresh": "negative", "nicht frisch": "negative", "غير طازج": "negative"}),
        "replenishment": (["empty", "refill", "refilled", "replenished", "nachgefüllt", "leer", "فاضي", "تعبئة"], {"empty": "negative", "leer": "negative", "فاضي": "negative", "refilled": "positive", "replenished": "positive", "nachgefüllt": "positive"}),
        "value": (["value", "price", "expensive", "worth", "preis", "teuer", "سعر", "غالي"], {"expensive": "negative", "teuer": "negative", "غالي": "negative", "worth": "positive"}),
        "waiting_queue": (["wait", "queue", "slow", "warte", "schlange", "انتظار", "طابور"], {"slow": "negative", "wait": "negative", "queue": "negative", "warte": "negative", "انتظار": "negative"}),
    }
    overall = []
    aspect_hits = defaultdict(list)
    for review in reviews:
        text = get_analysis_text(review)
        if not text: continue
        buffet = analyze_mention_sentiment(text, buffet_aliases)
        if not buffet["evidence"]: continue
        overall.append(buffet["sentiment"])
        for local in buffet["evidence"]:
            clause = local["matched_clause"]
            for name, (aliases, polarity) in aspects.items():
                result = analyze_mention_sentiment(clause, aliases, polarity)
                if result["evidence"]:
                    aspect_hits[name].append(result["sentiment"])
    written = sum(bool(get_analysis_text(r)) for r in reviews)
    def summarize(values):
        counts = Counter(values); count = len(values)
        return {"reviews": count, "positive": counts["positive"], "negative": counts["negative"],
                "neutral": counts["neutral"], "positive_pct": _pct(counts["positive"], count),
                "negative_pct": _pct(counts["negative"], count), "evidence_level": evidence_level(count)}
    result = {"reviews_mentioning_buffet": len(overall),
              "mention_coverage_pct_of_written_reviews": _pct(len(overall), written),
              "overall_sentiment": summarize(overall)}
    result.update({name: summarize(aspect_hits[name]) for name in aspects})
    return result


def _evidence_index(topic_evidence):
    result = defaultdict(dict)
    for row in topic_evidence:
        result[row["review_id"]].setdefault(row["topic"], row["sentiment"])
    return result


def rating_drivers(reviews, topic_evidence):
    index = _evidence_index(topic_evidence)
    groups = {
        "one_star_causes": ({1}, "negative"), "two_star_causes": ({2}, "negative"),
        "low_rating_causes": ({1, 2}, "negative"), "four_star_drivers": ({4}, "positive"),
        "five_star_drivers": ({5}, "positive"), "high_rating_drivers": ({4, 5}, "positive"),
    }
    output = {}
    for label, (stars, sentiment) in groups.items():
        members = [r for r in reviews if r.get("rating") is not None and int(float(r["rating"])) in stars]
        counts = Counter()
        for review in members:
            counts.update(topic for topic, value in index.get(review.get("review_id"), {}).items() if value == sentiment)
        output[label] = [
            {"topic": topic, "reviews": count, "share_within_rating_group_pct": _pct(count, len(members)),
             "sentiment": sentiment, "evidence_level": evidence_level(count)}
            for topic, count in counts.most_common() if count > 0
        ]
    return output


def emerging_insights(reviews, topic_evidence):
    dated = [(r, _date(r)) for r in reviews if _date(r) and get_analysis_text(r)]
    if not dated: return {"method": "recent 90 days vs earlier reviews", "emerging_complaints": [], "emerging_strengths": [], "mixed_emerging_signals": []}
    newest = max(date for _r, date in dated); cutoff = newest - timedelta(days=89)
    recent = [r for r, date in dated if date >= cutoff]; historical = [r for r, date in dated if date < cutoff]
    index = _evidence_index(topic_evidence)
    output = {"method": "recent 90 days vs earlier written reviews; at least 2 recent review mentions and a 5 percentage-point increase",
              "recent_reviews": len(recent), "historical_reviews": len(historical), "emerging_complaints": [], "emerging_strengths": []}
    for sentiment, label in (("negative", "emerging_complaints"), ("positive", "emerging_strengths")):
        recent_counts, historical_counts = Counter(), Counter()
        for review in recent: recent_counts.update(t for t, s in index.get(review.get("review_id"), {}).items() if s == sentiment)
        for review in historical: historical_counts.update(t for t, s in index.get(review.get("review_id"), {}).items() if s == sentiment)
        for topic, count in recent_counts.items():
            recent_pct = _pct(count, len(recent)); old_count = historical_counts[topic]; old_pct = _pct(old_count, len(historical)); change = round(recent_pct - old_pct, 2)
            if count >= 2 and change >= 5:
                level = evidence_level(count)
                noun = "complaint" if sentiment == "negative" else "strength"
                signal_label = f"possible emerging {noun}" if level == "low" else f"emerging {noun}"
                evidence_note = (
                    f"Low evidence: supported by {count} recent reviews; treat as a possible signal."
                    if level == "low"
                    else f"Supported by {count} recent reviews ({level} evidence)."
                )
                output[label].append({"topic": topic, "recent_reviews": count, "historical_reviews": old_count,
                    "recent_coverage_pct": recent_pct, "historical_coverage_pct": old_pct,
                    "change_pct_points": change, "evidence_level": level,
                    "signal_label": signal_label, "evidence_note": evidence_note})
        output[label].sort(key=lambda row: (row["change_pct_points"], row["recent_reviews"]), reverse=True)
    complaints = {row["topic"]: row for row in output["emerging_complaints"]}
    strengths = {row["topic"]: row for row in output["emerging_strengths"]}
    output["mixed_emerging_signals"] = []
    for topic in sorted(complaints.keys() & strengths.keys()):
        negative = complaints[topic]
        positive = strengths[topic]
        output["mixed_emerging_signals"].append({
            "topic": topic,
            "signal_label": "mixed / polarizing signal",
            "negative_recent_reviews": negative["recent_reviews"],
            "negative_historical_reviews": negative["historical_reviews"],
            "negative_change_pct_points": negative["change_pct_points"],
            "negative_evidence_level": negative["evidence_level"],
            "positive_recent_reviews": positive["recent_reviews"],
            "positive_historical_reviews": positive["historical_reviews"],
            "positive_change_pct_points": positive["change_pct_points"],
            "positive_evidence_level": positive["evidence_level"],
            "interpretation": "Both positive and negative recent signals increased; do not interpret this topic as a simple strength or complaint.",
        })
    return output


def satisfaction_comparison(topics, emerging):
    strengths = [r for r in topics if r["positive_reviews"] > 0]
    weaknesses = [r for r in topics if r["negative_reviews"] > 0]
    strengths.sort(key=lambda r: (r["positive_reviews"], r["reviews_mentioning"]), reverse=True)
    weaknesses.sort(key=lambda r: (r["negative_reviews"], r["reviews_mentioning"]), reverse=True)
    return {
        "strengths": [{"topic": r["topic"], "positive_reviews": r["positive_reviews"], "evidence_level": evidence_level(r["positive_reviews"])} for r in strengths[:10]],
        "weaknesses": [{"topic": r["topic"], "negative_reviews": r["negative_reviews"], "evidence_level": evidence_level(r["negative_reviews"])} for r in weaknesses[:10]],
    }


def business_priorities(topics, emerging):
    recent_signals = {r["topic"]: r for r in emerging.get("emerging_complaints", [])}
    weight = {"low": 0.5, "medium": 0.8, "high": 1.0}
    candidates = []
    for row in topics:
        negative_reviews = row["negative_reviews"]
        if negative_reviews < 2:
            continue
        recent_signal = recent_signals.get(row["topic"])
        change = recent_signal["change_pct_points"] if recent_signal else 0.0
        recent_level = recent_signal["evidence_level"] if recent_signal else "none"
        recent_weight = weight.get(recent_level, 0.0)
        negative_share = row["negative_share_of_topic_reviews_pct"]
        negative_coverage = row["negative_coverage_pct_of_written_reviews"]
        level = evidence_level(negative_reviews)
        components = {
            "negative_review_component": float(negative_reviews),
            "negative_share_component": round(negative_share / 5, 3),
            "negative_coverage_component": negative_coverage,
            "weighted_recent_deterioration_component": round(max(change, 0) / 4 * recent_weight, 3),
        }
        subtotal = sum(components.values())
        score = subtotal * weight[level]
        reason = (
            f"Qualifies with {negative_reviews} negative reviews; {negative_share:.2f}% of topic reviews "
            f"and {negative_coverage:.2f}% of written reviews are negative"
        )
        if change > 0:
            reason += f"; recent negative coverage rose {change:.2f} points ({recent_level} evidence, weight {recent_weight})"
        candidates.append({
            "topic": row["topic"], "priority_score": round(score, 2), "reason": reason,
            "negative_reviews": negative_reviews, "negative_share_pct": negative_share,
            "negative_coverage_pct_of_written_reviews": negative_coverage,
            "raw_recent_change": change or None,
            "recent_signal_evidence": recent_level,
            "recent_signal_weight": recent_weight,
            **components, "component_subtotal": round(subtotal, 3),
            "evidence": level, "evidence_weight": weight[level],
        })
    candidates.sort(key=lambda row: row["priority_score"], reverse=True)
    for rank, row in enumerate(candidates, 1): row["priority_rank"] = rank
    return {"formula": "(negative reviews + negative share pct / 5 + negative coverage pct of written reviews + (max(raw recent negative change, 0) / 4 x recent-signal evidence weight)) x negative-evidence weight; evidence weights: none 0, low .5, medium .8, high 1.0; requires at least 2 negative reviews",
            "priorities": candidates}
