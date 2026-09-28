"""Build the evidence-led Al Assiel management presentation."""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import unicodedata
from urllib.parse import urlsplit
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYER_05_JSON = ROOT / "output/restaurants/al_assiel/layer_05_reporting/layer_05_analysis_results.json"
LAYER_04_JSON = ROOT / "output/restaurants/al_assiel/layer_04_text_analysis/layer_04_text_analysis.json"
PROFILE_JSON = ROOT / "businesses/restaurants/al_assiel/inputs/restaurant_profile.json"
REVIEWS_DB = ROOT / "businesses/restaurants/al_assiel/data/reviews.db"
SOURCE_TEX = ROOT / "presentation/manager_presentation.tex"
OUTPUT_DIR = ROOT / "output/restaurants/al_assiel/presentation"
ASSET_DIR = OUTPUT_DIR / "assets"
RENDER_DIR = ASSET_DIR / "rendered_slides"
DATA_TEX = OUTPUT_DIR / "presentation_data.tex"
QUOTE_MANIFEST = ASSET_DIR / "quote_manifest.json"
FINAL_PDF = OUTPUT_DIR / "al_assiel_review_intelligence_presentation.pdf"
APPENDIX_TEX = OUTPUT_DIR / "presentation_appendix.tex"
EXPECTED_SLIDES = 0  # Determined from the main source plus generated appendix.


def require(mapping: dict, key: str):
    if key not in mapping:
        raise KeyError(f"Required analysis section or field is missing: {key}")
    return mapping[key]


def fmt(value, decimals: int = 1) -> str:
    if value is None:
        return "--"
    return f"{float(value):.{decimals}f}"


def tex_escape(value) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def macro(lines: list[str], name: str, value) -> None:
    lines.append(rf"\newcommand{{\{name}}}{{{tex_escape(value)}}}")


def raw_macro(lines: list[str], name: str, value: str) -> None:
    lines.append(rf"\newcommand{{\{name}}}{{{value}}}")


def find_topic(rows: list[dict], name: str) -> dict:
    return next((row for row in rows if row.get("topic") == name), {})


def find_category(rows: list[dict], name: str) -> dict:
    return next((row for row in rows if row.get("category") == name), {})


def find_dish(rows: list[dict], name: str) -> dict:
    return next((row for row in rows if row.get("dish") == name), {})


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = "".join(char for char in text if unicodedata.category(char) != "Cf")
    text = text.replace("–", "-").replace("—", "-").replace("‑", "-")
    return re.sub(r"\s+", " ", text).strip()


def evidence_level(count: int) -> str:
    if count <= 0:
        return "None"
    if count <= 4:
        return "Low"
    if count <= 14:
        return "Medium"
    return "High"


def load_reviews_read_only() -> dict[str, dict]:
    connection = sqlite3.connect(f"file:{REVIEWS_DB}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    rows = connection.execute(
        """SELECT review_id, review_url, rating, published_at, original_language,
                  text_original, text_translated, owner_response_text,
                  owner_response_date FROM reviews"""
    ).fetchall()
    connection.close()
    return {row["review_id"]: dict(row) for row in rows}


LANGUAGE_NAMES = {"de": "German", "ar": "Arabic", "fr": "French", "nl": "Dutch", "en": "English"}


QUOTE_SPECS = [
    {"name": "RecentFood", "kind": "topic", "item": "Food", "sentiment": "negative", "contains": ["stale"], "recent": True, "max_rating": 2, "group": "recent"},
    {"name": "RecentService", "kind": "topic", "item": "Service", "sentiment": "negative", "contains": ["overwhelmed"], "recent": True, "max_rating": 2, "group": "recent"},
    {"name": "RecentTaste", "kind": "topic", "item": "Taste", "sentiment": "negative", "contains": ["too dry"], "recent": True, "max_rating": 2, "group": "recent"},
    {"name": "RecentMenu", "kind": "topic", "item": "Menu & Tablet", "sentiment": "negative", "contains": ["confusing"], "recent": True, "max_rating": 2, "group": "recent"},
    {"name": "StrengthFood", "kind": "topic", "item": "Food", "sentiment": "positive", "contains": ["high quality"], "min_rating": 4, "group": "strengths"},
    {"name": "StrengthService", "kind": "topic", "item": "Staff Friendliness", "sentiment": "positive", "contains": ["friendly", "attentive"], "min_rating": 4, "group": "strengths"},
    {"name": "StrengthAtmosphere", "kind": "topic", "item": "Atmosphere", "sentiment": "positive", "contains": ["pleasant and cozy"], "min_rating": 4, "group": "strengths"},
    {"name": "ServiceWait", "kind": "topic", "item": "Service", "sentiment": "negative", "contains": ["wait a very long time"], "max_rating": 2, "group": "service_negative"},
    {"name": "ServiceUnresponsive", "kind": "topic", "item": "Service", "sentiment": "negative", "contains": ["unresponsive"], "max_rating": 2, "group": "service_negative"},
    {"name": "ServiceOverwhelmed", "kind": "topic", "item": "Service", "sentiment": "negative", "contains": ["overwhelmed"], "max_rating": 2, "group": "service_negative"},
    {"name": "ServicePositive", "kind": "topic", "item": "Service", "sentiment": "positive", "contains": ["excellent, attentive, and friendly"], "min_rating": 4},
    {"name": "PriceHigh", "kind": "topic", "item": "Price & Value", "sentiment": "negative", "contains": ["far too expensive"], "group": "price_negative"},
    {"name": "PriceBuffet", "kind": "topic", "item": "Price & Value", "sentiment": "negative", "contains": ["poor quality", "unnecessarily expensive"], "group": "price_negative"},
    {"name": "PricePositive", "kind": "topic", "item": "Price & Value", "sentiment": "positive", "contains": ["value for money"], "min_rating": 4},
    {"name": "FoodStale", "kind": "topic", "item": "Food", "sentiment": "negative", "contains": ["terrible and very stale"], "group": "food_negative"},
    {"name": "FoodUnappealing", "kind": "topic", "item": "Food", "sentiment": "negative", "contains": ["completely unappealing"], "group": "food_negative"},
    {"name": "FoodFresh", "kind": "topic", "item": "Food", "sentiment": "positive", "contains": ["freshly prepared, flavorful"], "recent": True, "min_rating": 4, "group": "food_positive"},
    {"name": "TasteDry", "kind": "topic", "item": "Taste", "sentiment": "negative", "contains": ["too dry"], "group": "taste_negative"},
    {"name": "TasteUnappealing", "kind": "topic", "item": "Taste", "sentiment": "negative", "contains": ["completely unappealing"], "group": "taste_negative"},
    {"name": "TastePositive", "kind": "topic", "item": "Taste", "sentiment": "positive", "contains": ["tastes amazing"], "min_rating": 4},
    {"name": "AtmosphereRecent", "kind": "topic", "item": "Atmosphere", "sentiment": "positive", "contains": ["oriental vibes"], "recent": True, "min_rating": 4},
    {"name": "BuffetPositive", "kind": "topic", "item": "Buffet", "sentiment": "positive", "contains": ["wonderful brunch buffet"], "min_rating": 4, "group": "buffet"},
    {"name": "BuffetNegative", "kind": "topic", "item": "Buffet", "sentiment": "negative", "contains": ["poor quality"], "group": "buffet"},
    {"name": "BuffetNeutral", "kind": "topic", "item": "Buffet", "sentiment": "neutral", "contains": ["concept was changed"], "group": "buffet"},
    {"name": "DrinkPositive", "kind": "topic", "item": "Drinks", "sentiment": "positive", "contains": ["fantastic mint lemonade"], "min_rating": 4, "group": "drinks"},
    {"name": "DrinkWrong", "kind": "topic", "item": "Drinks", "sentiment": "negative", "contains": ["wrong drink"], "recent": True, "max_rating": 2, "group": "drinks"},
    {"name": "DrinkPresentation", "kind": "topic", "item": "Drinks", "sentiment": "neutral", "contains": ["glasses with garnishes"], "recent": True, "max_rating": 2, "group": "drinks"},
    {"name": "DishMansaf", "kind": "dish", "item": "Jordanisches Mansaf", "sentiment": "positive", "contains": ["it was delicious"], "group": "dishes"},
    {"name": "DishTabbouleh", "kind": "dish", "item": "Tabbouleh", "sentiment": "positive", "contains": ["very good"], "group": "dishes"},
    {"name": "DishMixedGrill", "kind": "dish", "item": "Gemischte Grillplatte", "sentiment": "negative", "contains": ["wings", "burnt"], "group": "dishes"},
    {"name": "WaitingTime", "kind": "topic", "item": "Waiting Time", "sentiment": "negative", "contains": ["wait a very long time"], "max_rating": 2},
    {"name": "MenuTablet", "kind": "topic", "item": "Menu & Tablet", "sentiment": "negative", "contains": ["extremely confusing"], "max_rating": 2},
]


def make_excerpt(clause: str, focus_terms: list[str], max_words: int = 18) -> str:
    clean = normalize_text(clause).lstrip(" ,.;:")
    words = clean.split()
    if len(words) <= max_words:
        return ("... " + clean) if clean and clean[0].islower() else clean
    lower_words = [re.sub(r"[^a-z0-9€]+", "", word.lower()) for word in words]
    focus_index = 0
    for term in focus_terms:
        first = re.sub(r"[^a-z0-9€]+", "", term.lower().split()[0])
        if first in lower_words:
            focus_index = lower_words.index(first)
            break
    start = max(0, min(focus_index - 5, len(words) - max_words))
    excerpt = " ".join(words[start:start + max_words])
    if start:
        excerpt = "... " + excerpt
    if start + max_words < len(words):
        excerpt += " ..."
    return excerpt


def select_quotes(layer_04: dict, reviews: dict[str, dict], recent_start: datetime) -> dict[str, dict]:
    selected: dict[str, dict] = {}
    used_by_group: dict[str, set[str]] = defaultdict(set)
    evidence_rows = {"topic": layer_04["topic_match_evidence"], "dish": layer_04["dish_match_evidence"]}
    item_fields = {"topic": "topic", "dish": "dish_or_family"}

    for spec in QUOTE_SPECS:
        candidates = []
        for evidence in evidence_rows[spec["kind"]]:
            if evidence.get(item_fields[spec["kind"]]) != spec["item"] or evidence.get("sentiment") != spec["sentiment"]:
                continue
            review = reviews.get(evidence.get("review_id"))
            if not review:
                continue
            rating = float(review["rating"])
            published = datetime.fromisoformat(review["published_at"])
            if spec.get("recent") and published < recent_start:
                continue
            if "max_rating" in spec and rating > spec["max_rating"]:
                continue
            if "min_rating" in spec and rating < spec["min_rating"]:
                continue
            clause = normalize_text(evidence.get("matched_clause"))
            terms = [term.lower() for term in spec.get("contains", [])]
            if terms and not all(term in clause.lower() for term in terms):
                continue
            source_text = review["text_translated"] if evidence.get("text_variant_used") == "translated" else review["text_original"]
            if not source_text:
                continue
            if clause not in normalize_text(source_text):
                raise ValueError(f"Quote evidence is not present in review text: {spec['name']}")
            score = 100 * len(terms) - abs(len(clause.split()) - 12) + published.timestamp() / 10**10
            candidates.append((score, evidence, review, published))

        if not candidates:
            raise ValueError(f"No evidence-backed quote satisfies specification: {spec['name']}")
        candidates.sort(key=lambda row: row[0], reverse=True)
        group = spec.get("group")
        available = [row for row in candidates if not group or row[1]["review_id"] not in used_by_group[group]]
        _, evidence, review, published = (available or candidates)[0]
        if group:
            used_by_group[group].add(evidence["review_id"])

        language = review.get("original_language") or "unknown"
        translated = evidence.get("text_variant_used") == "translated" and language != "en"
        metadata = f"{int(float(review['rating']))}-star | {published.strftime('%b %Y')}"
        if translated:
            metadata += f" | Translated from {LANGUAGE_NAMES.get(language, language)}"
        selected[spec["name"]] = {
            "text": make_excerpt(evidence["matched_clause"], spec.get("contains", [])),
            "metadata": metadata,
            "rating": int(float(review["rating"])),
            "date": published.date().isoformat(),
            "language": language,
            "translated": translated,
            "source_kind": spec["kind"],
            "source_item": spec["item"],
            "sentiment": spec["sentiment"],
            "review_url": normalize_text(review.get("review_url")),
        }
    return selected


def validate_analysis(layer_05: dict, layer_04: dict, profile: dict, reviews: dict[str, dict]) -> None:
    for section in (
        "overall_performance", "trends", "structured_ratings", "topics", "rating_drivers",
        "satisfaction_vs_dissatisfaction", "business_priorities", "emerging_insights",
        "review_cadence", "owner_response_analysis", "low_rating_analysis",
        "buffet_analysis", "dish_rankings", "menu_analysis", "menu_management_insights",
        "menu_optimization_goal", "future_favourites_method", "menu_activation_experiments",
        "bar_drinks_analysis", "kitchen_bar_overview", "customer_journey",
        "management_baseline", "management_observations", "context", "languages", "data_quality",
    ):
        require(layer_05, section)
    require(layer_04, "topic_match_evidence")
    require(layer_04, "dish_match_evidence")
    if not reviews:
        raise ValueError("No reviews were read from the read-only database")
    if not profile.get("buffet", {}).get("available"):
        raise ValueError("The presentation expects the maintained buffet profile fact")
    overall = layer_05["overall_performance"]
    if sum(int(row["count"]) for row in overall["rating_distribution"]) != int(overall["google_review_count"]):
        raise ValueError("Rating distribution does not sum to the Google review count")
    if int(overall["written_reviews"]) > int(overall["google_review_count"]):
        raise ValueError("Written review count exceeds total reviews")
    monthly = layer_05["trends"]["monthly"]
    if not monthly or not monthly[0].get("is_partial_month") or not monthly[-1].get("is_partial_month"):
        raise ValueError("First and latest dataset months must be marked partial")
    if not {"Food", "Service", "Atmosphere"}.issubset({row["category"] for row in layer_05["structured_ratings"]}):
        raise ValueError("Required structured rating category is missing")
    if len(layer_05["business_priorities"]["priorities"]) < 5:
        raise ValueError("At least five business priorities are required")
    buffet = layer_05["buffet_analysis"]
    if sum(int(buffet["overall_sentiment"][key]) for key in ("positive", "negative", "neutral")) != int(buffet["reviews_mentioning_buffet"]):
        raise ValueError("Buffet sentiment does not sum to buffet mentions")
    if not layer_05["dish_rankings"]["insufficient_qualified_dishes_for_comparative_ranking"]:
        raise ValueError("Current dish slide assumes insufficient comparative evidence")
    bar_totals = layer_05["bar_drinks_analysis"]["menu_attention"]["totals"]
    if int(bar_totals["total_drink_items"]) != 34:
        raise ValueError("Drink-menu total changed; review the Bar & Drinks slide")
    if layer_05["menu_optimization_goal"].get("classification") != "internal_management_goal":
        raise ValueError("Menu optimization goal must remain an internal management goal")


def add_topic_macros(lines: list[str], topics: list[dict]) -> None:
    names = {
        "Food": "FoodTopic", "Service": "ServiceTopic", "Taste": "TasteTopic",
        "Staff Friendliness": "FriendlinessTopic", "Atmosphere": "AtmosphereTopic",
        "Price & Value": "PriceTopic", "Buffet": "BuffetTopic",
        "Staff Attentiveness": "AttentivenessTopic", "Cleanliness": "CleanlinessTopic",
        "Food Presentation": "PresentationTopic", "Freshness": "FreshnessTopic",
        "Food Quality": "FoodQualityTopic", "Food Temperature": "TemperatureTopic",
        "Portion Size": "PortionTopic", "Drinks": "DrinksTopic",
        "Waiting Time": "WaitingTopic", "Menu & Tablet": "MenuTopic", "Parking": "ParkingTopic",
    }
    for topic_name, prefix in names.items():
        row = find_topic(topics, topic_name)
        if not row:
            raise KeyError(f"Topic missing from Layer 05: {topic_name}")
        macro(lines, prefix + "Mentions", row["reviews_mentioning"])
        macro(lines, prefix + "Positive", row["positive_reviews"])
        macro(lines, prefix + "Negative", row["negative_reviews"])
        macro(lines, prefix + "Neutral", row["neutral_reviews"])
        macro(lines, prefix + "NegativePct", fmt(row["negative_pct"], 1))
        macro(lines, prefix + "Evidence", row["evidence_level"].title())
        macro(lines, prefix + "NegativeEvidence", evidence_level(int(row["negative_reviews"])))


def add_recent_low_rating_macros(lines: list[str], layer_04: dict, reviews: dict[str, dict], recent_start: datetime) -> None:
    recent_low_ids = {
        review_id for review_id, row in reviews.items()
        if float(row["rating"]) <= 2 and datetime.fromisoformat(row["published_at"]) >= recent_start
    }
    macro(lines, "RecentLowRatingReviews", len(recent_low_ids))
    for topic, prefix in (("Food", "RecentLowFood"), ("Service", "RecentLowService"), ("Taste", "RecentLowTaste"), ("Menu & Tablet", "RecentLowMenu"), ("Parking", "RecentLowParking")):
        supported = {
            row["review_id"] for row in layer_04["topic_match_evidence"]
            if row["topic"] == topic and row["sentiment"] == "negative" and row["review_id"] in recent_low_ids
        }
        macro(lines, prefix, len(supported))


def topic_summary_for_period(
    layer_04: dict,
    reviews: dict[str, dict],
    start: datetime,
    end: datetime | None,
) -> dict:
    review_ids = {
        review_id for review_id, row in reviews.items()
        if datetime.fromisoformat(row["published_at"]) >= start
        and (end is None or datetime.fromisoformat(row["published_at"]) < end)
    }
    written_ids = {
        review_id for review_id in review_ids
        if normalize_text(reviews[review_id].get("text_original"))
        or normalize_text(reviews[review_id].get("text_translated"))
    }
    by_topic: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in layer_04["topic_match_evidence"]:
        if row["review_id"] in review_ids:
            by_topic[row["topic"]][row["sentiment"]].add(row["review_id"])
    topics = {}
    for topic, sentiments in by_topic.items():
        mentioned = set().union(*sentiments.values()) if sentiments else set()
        positive = len(sentiments["positive"])
        negative = len(sentiments["negative"])
        neutral = len(sentiments["neutral"])
        topics[topic] = {
            "mentions": len(mentioned),
            "coverage_pct": len(mentioned) / len(written_ids) * 100 if written_ids else 0,
            "positive": positive,
            "positive_coverage_pct": positive / len(written_ids) * 100 if written_ids else 0,
            "positive_evidence": evidence_level(positive),
            "negative": negative,
            "negative_coverage_pct": negative / len(written_ids) * 100 if written_ids else 0,
            "negative_evidence": evidence_level(negative),
            "neutral": neutral,
        }
    return {
        "review_ids": review_ids,
        "written_reviews": len(written_ids),
        "low_score_reviews": sum(float(reviews[review_id]["rating"]) <= 2 for review_id in review_ids),
        "topics": topics,
    }


def truncate_words(value: str, limit: int = 28) -> str:
    clean = normalize_text(value)
    if any(unicodedata.category(char).startswith("L") and ord(char) > 0x024F for char in clean):
        return "Original-language excerpt available at source; no English analysis translation is available."
    clean = "".join(char for char in clean if unicodedata.category(char) not in {"So", "Cs"})
    words = clean.split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit]) + " ..."


def build_case_records(layer_04: dict, reviews: dict[str, dict]) -> dict[str, dict]:
    topic_map: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    dish_map: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in layer_04["topic_match_evidence"]:
        topic_map[row["review_id"]][row["sentiment"]].add(row["topic"])
    for row in layer_04["dish_match_evidence"]:
        dish_map[row["review_id"]][row["sentiment"]].add(row["dish_or_family"])

    records = {}
    for review_id, review in reviews.items():
        language = review.get("original_language") or "unknown"
        translated = bool(normalize_text(review.get("text_translated"))) and language != "en"
        analysis_text = review.get("text_translated") or review.get("text_original") or ""
        written = bool(normalize_text(review.get("text_original")) or normalize_text(review.get("text_translated")))
        topics = topic_map[review_id]
        dishes = set().union(*dish_map[review_id].values()) if dish_map[review_id] else set()
        all_topics = set().union(*topics.values()) if topics else set()
        records[review_id] = {
            **review,
            "date": datetime.fromisoformat(review["published_at"]),
            "written": written,
            "translated": translated,
            "language_label": LANGUAGE_NAMES.get(language, language.title()),
            "excerpt": truncate_words(analysis_text, 27) if written else "No written review text available.",
            "positive_topics": sorted(topics["positive"]),
            "negative_topics": sorted(topics["negative"]),
            "neutral_topics": sorted(topics["neutral"]),
            "all_topics": sorted(all_topics),
            "dishes": sorted(dishes),
        }
    return records


def case_period(date: datetime, trend_summary: dict) -> str:
    recent_30 = datetime.fromisoformat(trend_summary["recent_30d_start"])
    recent_90 = datetime.fromisoformat(trend_summary["recent_90d_start"])
    from datetime import timedelta
    previous_90 = recent_90 - timedelta(days=90)
    if date >= recent_30:
        return "latest 30d"
    if date >= recent_90:
        return "recent 90d"
    if date >= previous_90:
        return "previous 90d"
    return "historical"


def join_or_none(values: list[str], limit: int = 4) -> str:
    if not values:
        return "none detected"
    shown = values[:limit]
    suffix = f" +{len(values) - limit}" if len(values) > limit else ""
    return ", ".join(shown) + suffix


def owner_for_case(record: dict) -> str:
    topics = set(record["negative_topics"])
    if topics & {"Food", "Taste", "Buffet", "Freshness", "Food Quality", "Food Temperature"}:
        return "Kitchen & Buffet Quality"
    if topics & {"Service", "Waiting Time", "Staff Communication", "Staff Attentiveness", "Parking"}:
        return "Guest Experience"
    if topics & {"Menu & Tablet", "Drinks", "Price & Value"}:
        return "Menu, Bar & Offers"
    return "Reputation & Data"


def href_for_review(record: dict) -> str:
    url = normalize_text(record.get("review_url"))
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return r"{\color{Gray}\fontsize{5.8}{6.8}\selectfont Original review link unavailable in source data}"
    tex_url = url.replace("%", r"\%").replace("#", r"\#").replace("_", r"\_")
    return rf"\href{{{tex_url}}}{{\color{{Teal}}\fontsize{{6.1}}{{7.2}}\selectfont\bfseries Open original review $\rightarrow$}}"


def case_card_tex(case_id: str, record: dict, period: str | None = None, operational: bool = False) -> str:
    meta = [
        record["date"].strftime("%d %b %Y"),
        f"{int(float(record['rating']))}-star",
        "written" if record["written"] else "no text",
        record["language_label"],
        "translation yes" if record["translated"] else "translation not needed" if record.get("original_language") == "en" else "translation no",
        "owner response yes" if normalize_text(record.get("owner_response_text")) else "owner response no",
    ]
    if period:
        meta.insert(2, period)
    topics = (
        f"Negative: {join_or_none(record['negative_topics'])}; "
        f"Positive: {join_or_none(record['positive_topics'])}; "
        f"Neutral: {join_or_none(record['neutral_topics'])}."
    )
    flags = (
        f"Items: {join_or_none(record['dishes'])}; "
        f"buffet {'yes' if 'Buffet' in record['all_topics'] else 'no'}; "
        f"drinks {'yes' if 'Drinks' in record['all_topics'] else 'no'}; "
        f"menu/tablet {'yes' if 'Menu & Tablet' in record['all_topics'] else 'no'}; "
        f"service {'yes' if 'Service' in record['all_topics'] else 'no'}; "
        f"price/value {'yes' if 'Price & Value' in record['all_topics'] else 'no'}."
    )
    if operational:
        response_date = (normalize_text(record.get("owner_response_date"))[:10] or "--")
        owner = owner_for_case(record).replace("Kitchen & Buffet Quality", "Kitchen & Buffet").replace("Guest Experience", "Guest Exp.").replace("Menu, Bar & Offers", "Menu/Bar & Offers")
        flags = (
            f"Items: {join_or_none(record['dishes'])} | buffet {'yes' if 'Buffet' in record['all_topics'] else 'no'} | "
            f"drinks {'yes' if 'Drinks' in record['all_topics'] else 'no'} | menu {'yes' if 'Menu & Tablet' in record['all_topics'] else 'no'} | "
            f"service {'yes' if 'Service' in record['all_topics'] else 'no'} | value {'yes' if 'Price & Value' in record['all_topics'] else 'no'}. "
            f"Owner: {owner}; public target 48h; response {response_date}; check detected issues; "
            "closure OPEN (resolution data unavailable)."
        )
    card_macro = "opcasecard" if operational else "casecard"
    excerpt = truncate_words(record["excerpt"], 16 if operational else 27)
    return (
        rf"\{card_macro}{{{tex_escape(case_id)}}}{{{tex_escape(' | '.join(meta))}}}"
        rf"{{{tex_escape(topics)}}}{{{tex_escape(flags)}}}{{{tex_escape(excerpt)}}}"
        rf"{{{href_for_review(record)}}}"
    )


def frame_with_cards(
    lines: list[str],
    title: str,
    appendix_label: str,
    anchor: str,
    back_target: str,
    back_label: str,
    cards: list[str],
) -> None:
    lines.extend([
        rf"\begin{{frame}}{{{tex_escape(title)}}}",
        rf"  \hypertarget{{{anchor}}}{{}}\appendixhead{{{tex_escape(appendix_label)}}}",
        "  " + "\n  ".join(cards),
        rf"  \vfill\backbutton{{{back_target}}}{{{tex_escape(back_label)}}}",
        r"\end{frame}",
        "",
    ])


def generate_appendix(layer_05: dict, layer_04: dict, reviews: dict[str, dict]) -> int:
    records = build_case_records(layer_04, reviews)
    trend = layer_05["trends"]["summary"]
    recent_start = datetime.fromisoformat(trend["recent_30d_start"])
    previous_start = datetime.fromisoformat(layer_05["review_cadence"]["periods"]["previous_30d"]["start"])
    recent = sorted((r for r in records.values() if r["date"] >= recent_start), key=lambda r: r["date"], reverse=True)
    previous = sorted((r for r in records.values() if previous_start <= r["date"] < recent_start), key=lambda r: r["date"], reverse=True)
    low = sorted((r for r in records.values() if float(r["rating"]) <= 2), key=lambda r: r["date"], reverse=True)
    if (len(recent), len(previous), len(low)) != (14, 6, 30):
        raise ValueError(f"Case register counts changed: latest={len(recent)}, previous={len(previous)}, low={len(low)}")

    lines = ["% Generated by presentation/build_presentation.py. Do not edit manually."]
    lines.extend([
        r"\begin{frame}{Appendix O - Monthly trend evidence}",
        r"  \hypertarget{a-trend}{}\appendixhead{O - Trends}",
        r"  {\color{Gray}\fontsize{6.3}{7.5}\selectfont Dataset \EarliestReviewDate\ to \LatestReviewDate. Dec 2024 and Sep 2026 are partial; all middle months are complete.}",
        r"  \vspace{0.08cm}\begin{columns}[T,onlytextwidth]\column{0.33\textwidth}\smallcapslabel{Average rating}\par\begin{tikzpicture}\begin{axis}[width=4.65cm,height=3.85cm,xmin=-.5,xmax=21.5,ymin=2.4,ymax=5.15,monthly axis ticks,x tick label style={font=\fontsize{4.6}{5.5}\selectfont,rotate=35,anchor=east},ytick={3,4,5},yticklabel style={font=\tiny},grid=major,grid style={LightGray}]\addplot[Navy,thick,mark=*,mark size=1pt] table[x=index,y=average,col sep=comma]{assets/monthly_trend.csv};\addplot[Gold,only marks,mark=*,mark size=3pt] table[x=index,y=average,col sep=comma]{assets/monthly_partial.csv};\end{axis}\end{tikzpicture}\column{0.33\textwidth}\smallcapslabel{Review volume}\par\begin{tikzpicture}\begin{axis}[ybar,bar width=3pt,width=4.65cm,height=3.85cm,xmin=-.5,xmax=21.5,ymin=0,ymax=24,monthly axis ticks,x tick label style={font=\fontsize{4.6}{5.5}\selectfont,rotate=35,anchor=east},ytick={0,10,20},yticklabel style={font=\tiny},grid=major,grid style={LightGray}]\addplot[fill=Teal,draw=Teal] table[x=index,y=reviews,col sep=comma]{assets/review_volume.csv};\end{axis}\end{tikzpicture}\column{0.33\textwidth}\smallcapslabel{Low-score volume}\par\begin{tikzpicture}\begin{axis}[ybar,bar width=3pt,width=4.65cm,height=3.85cm,xmin=-.5,xmax=21.5,ymin=0,ymax=6,monthly axis ticks,x tick label style={font=\fontsize{4.6}{5.5}\selectfont,rotate=35,anchor=east},ytick={0,2,4,6},yticklabel style={font=\tiny},grid=major,grid style={LightGray}]\addplot[fill=Red,draw=Red] table[x=index,y=low_scores,col sep=comma]{assets/monthly_trend.csv};\end{axis}\end{tikzpicture}\end{columns}",
        r"  \vfill\implication{Read rating with volume and low-score counts; partial months are not comparable as full-month totals.}\par\vspace{0.07cm}\backbutton{m-trend}{Back to Performance Trends}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix A1 - Latest 30 days: detailed comparison}",
        r"  \hypertarget{a-latest-summary}{}\appendixhead{A1 - Latest 30 Days Summary}",
        r"  {\color{Gray}\fontsize{6.5}{7.7}\selectfont Latest 30 days: \RecentThirtyStart\ to \LatestReviewDate. Previous 30 days: \PreviousThirtyStart\ to \RecentThirtyStart.}",
        r"  \vspace{0.10cm}\begin{columns}[T,onlytextwidth]",
        r"    \column{0.43\textwidth}\smallcapslabel{Period scoreboard}\par\vspace{0.07cm}{\fontsize{7.6}{9.1}\selectfont Latest: \RecentThirtyReviews\ reviews / \RecentThirtyWritten\ written / avg. \RecentThirtyAverage\ / \RecentThirtyNegativePct\% negative / \RecentThirtyLowScores\ low-score / \OwnerRecentThirtyRate\% response.\par\vspace{0.10cm}Previous: \PreviousThirtyReviews\ reviews / \PreviousThirtyWritten\ written / avg. \PreviousThirtyAverage\ / \PreviousThirtyNegativePct\% negative / \PreviousThirtyLowScores\ low-score / \OwnerPreviousThirtyRate\% response.\par\vspace{0.10cm}Food, Service, Taste, Drinks, Buffet and Menu/Tablet are compared at right; counts are unique reviews, not phrase counts.}",
        r"    \column{0.53\textwidth}\begin{tikzpicture}\begin{axis}[ybar,bar width=4pt,width=7.6cm,height=4.35cm,symbolic x coords={Food,Service,Taste,Drinks,Buffet,Menu & Tablet,Atmosphere,Staff Friendliness,Staff Communication,Parking},xtick=data,xticklabels={Food,Service,Taste,Drinks,Buffet,Menu,Atmosphere,Friendliness,Communication,Parking},x tick label style={font=\fontsize{5.3}{6.3}\selectfont,rotate=30,anchor=east},ytick={0,1,2,3,4,5,6},yticklabel style={font=\scriptsize},legend style={font=\fontsize{5.8}{6.8}\selectfont,at={(0.5,1.02)},anchor=south,legend columns=2,draw=none},grid=major,grid style={LightGray}]\addplot[fill=Teal,draw=Teal] table[x=topic,y=recent_mentions,col sep=comma]{assets/last_30d_topics.csv};\addplot[fill=Gray!50,draw=Gray] table[x=topic,y=previous_mentions,col sep=comma]{assets/last_30d_topics.csv};\legend{Latest,Previous}\end{axis}\end{tikzpicture}",
        r"  \end{columns}\vfill\backbutton{m-lastmonth}{Back to Last-Month Performance}\quad\tealbutton{a-latest-register}{Open all 14 cases}",
        r"\end{frame}", "",
    ])
    for page, start in enumerate(range(0, len(recent), 2), 2):
        cards = [case_card_tex(f"L{i+1:02d}", record) for i, record in enumerate(recent[start:start+2], start)]
        frame_with_cards(lines, f"Appendix A{page} - Latest 30-day case register", f"A{page} - Cases {start+1}-{min(start+2, len(recent))} of 14", "a-latest-register" if start == 0 else f"a-latest-{page}", "m-lastmonth", "Back to Last-Month Performance", cards)
    for page, start in enumerate(range(0, len(previous), 2), 1):
        cards = [case_card_tex(f"P{i+1:02d}", record) for i, record in enumerate(previous[start:start+2], start)]
        frame_with_cards(lines, f"Appendix B{page} - Previous 30-day case register", f"B{page} - Cases {start+1}-{min(start+2, len(previous))} of 6", "a-previous-register" if start == 0 else f"a-previous-{page}", "m-lastmonth", "Back to Last-Month Performance", cards)

    for page, start in enumerate(range(0, len(low), 2), 1):
        cards = [case_card_tex(f"C{i+1:02d}", record, case_period(record["date"], trend), operational=True) for i, record in enumerate(low[start:start+2], start)]
        frame_with_cards(lines, f"Appendix C{page} - Bad-review case register", f"C{page} - Cases {start+1}-{min(start+2, len(low))} of 30", "a-bad-register" if start == 0 else f"a-bad-{page}", "m-badscale", "Back to Bad Reviews", cards)

    lines.extend([
        r"\begin{frame}{Appendix D1 - Bad-review patterns by operational area}",
        r"  \hypertarget{a-bad-patterns}{}\appendixhead{D1 - Pattern Analysis}",
        r"  \begin{columns}[T,onlytextwidth]\column{0.58\textwidth}\begin{tikzpicture}\begin{axis}[xbar,width=8.05cm,height=5.0cm,xmin=0,xmax=10,symbolic y coords={Buffet,Drinks,Menu,Taste,Price,Food,Service},ytick=data,yticklabels={Buffet,Drinks,Menu/Tablet,Taste,Price/Value,Food,Service},y tick label style={font=\fontsize{6.2}{7.2}\selectfont},xtick={0,2,4,6,8,10},xticklabel style={font=\scriptsize},xlabel={Negative low-score reviews},xlabel style={font=\scriptsize},grid=major,grid style={LightGray}]\addplot[fill=Red,draw=Red] coordinates {(\LowBuffetCount,Buffet) (\LowDrinksCount,Drinks) (\LowMenuCount,Menu) (\LowTasteCount,Taste) (\LowPriceCount,Price) (\LowFoodCount,Food) (\LowServiceCount,Service)};\end{axis}\end{tikzpicture}\column{0.38\textwidth}{\fontsize{7.3}{8.7}\selectfont Service \LowServiceCount\ (\LowServicePct\%, \LowServiceEvidence); Food \LowFoodCount\ (\LowFoodPct\%, \LowFoodEvidence); Price/Value \LowPriceCount\ (\LowPricePct\%, \LowPriceEvidence); Taste \LowTasteCount\ (\LowTastePct\%, \LowTasteEvidence); Menu/Tablet \LowMenuCount; Drinks \LowDrinksCount; Buffet \LowBuffetCount.\par\vspace{0.14cm}\textbf{Interpretation:} Service is the clearest repeated operational area. Food and Price/Value are repeated but smaller. One-off topics remain investigation signals.}",
        r"  \end{columns}\vfill\backbutton{m-badpatterns}{Back to Bad-Review Patterns}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix D2 - Bad-review co-occurrence and recent shift}",
        r"  \hypertarget{a-bad-cooccurrence}{}\appendixhead{D2 - Co-occurrence and Timing}",
        r"  \begin{columns}[T,onlytextwidth]\column{0.52\textwidth}\smallcapslabel{Repeated combinations}\par\vspace{0.09cm}\evidenceitem{\LowPairOneName}{\LowPairOneCount\ cases | \LowPairOneShare\%}{\badge{PaleGold}{REPEATED}}\evidenceitem{\LowPairTwoName}{\LowPairTwoCount\ cases | \LowPairTwoShare\%}{\badge{PaleGold}{REPEATED}}\vspace{0.12cm}{\fontsize{7.2}{8.6}\selectfont All other pairings occur once. Co-occurrence is useful for investigation, not proof of causality. Day/time and shift data are not available.}\column{0.44\textwidth}\smallcapslabel{Recent 90d vs historical}\par\vspace{0.08cm}{\fontsize{7.4}{8.8}\selectfont Food: \LowRecentFoodHistorical\ $\rightarrow$ \LowRecentFoodRecent\ (+\LowRecentFoodChange\ pp; recent evidence weighted by support)\\Taste: \LowRecentTasteHistorical\ $\rightarrow$ \LowRecentTasteRecent\ (+\LowRecentTasteChange\ pp)\\Service: \LowRecentServiceHistorical\ $\rightarrow$ \LowRecentServiceRecent\ (\LowRecentServiceChange\ pp)\\Price/Value: \LowRecentPriceHistorical\ $\rightarrow$ \LowRecentPriceRecent\ (\LowRecentPriceChange\ pp)\par\vspace{0.15cm}\textbf{Period:} recent 90d \RecentNinetyStart\ to \LatestReviewDate; historical \EarliestReviewDate\ to \RecentNinetyStart.}",
        r"  \end{columns}\vfill\backbutton{m-badpatterns}{Back to Bad-Review Patterns}",
        r"\end{frame}", "",
    ])

    def evidence_pages(title: str, label: str, anchor: str, back: str, back_label: str, topics: set[str], sentiments: set[str]) -> None:
        ids = set()
        for row in layer_04["topic_match_evidence"]:
            if row["topic"] in topics and row["sentiment"] in sentiments:
                ids.add(row["review_id"])
        selected = sorted((records[i] for i in ids), key=lambda r: r["date"], reverse=True)
        for page, start in enumerate(range(0, len(selected), 2), 1):
            cards = [case_card_tex(f"{label}{i+1:02d}", record, case_period(record["date"], trend)) for i, record in enumerate(selected[start:start+2], start)]
            frame_with_cards(lines, f"Appendix {label}{page} - {title}", f"{label}{page} - {title}", anchor if start == 0 else f"{anchor}-{page}", back, back_label, cards)

    evidence_pages("Service negative evidence", "E", "a-service", "m-service", "Back to Service", {"Service"}, {"negative"})
    evidence_pages("Food and Taste negative evidence", "F", "a-food", "m-food", "Back to Food/Taste", {"Food", "Taste", "Freshness", "Food Quality", "Food Temperature"}, {"negative"})
    evidence_pages("Bar and Drinks negative/neutral evidence", "G", "a-bar", "m-bar", "Back to Bar/Drinks", {"Drinks"}, {"negative", "neutral"})
    evidence_pages("Buffet negative/neutral evidence", "H", "a-buffet", "m-buffet", "Back to Buffet", {"Buffet"}, {"negative", "neutral"})
    evidence_pages("Menu and Tablet complaint evidence", "I", "a-menu", "m-menu", "Back to Menu & Ordering", {"Menu & Tablet"}, {"negative", "neutral"})

    dishes = layer_05["dishes"]
    dish_evidence = defaultdict(list)
    for row in layer_04["dish_match_evidence"]:
        dish_evidence[row["dish_or_family"]].append(row)
    for page, start in enumerate(range(0, len(dishes), 3), 1):
        cards = []
        for row in dishes[start:start+3]:
            evidence = sorted(dish_evidence[row["dish"]], key=lambda e: records[e["review_id"]]["date"], reverse=True)
            example = evidence[0] if evidence else None
            latest = records[example["review_id"]] if example else None
            link = href_for_review(latest) if latest else r"{\color{Gray}\fontsize{5.8}{6.8}\selectfont Original review link unavailable in source data}"
            excerpt = truncate_words(example.get("matched_clause", "No excerpt available."), 22) if example else "No excerpt available."
            detail = (
                f"Category: {row['category']} | mentions {row['reviews_mentioning']} | positive {row['positive_reviews']} | "
                f"negative {row['negative_reviews']} | neutral {row['neutral_reviews']} | whole-review avg. {row['average_overall_rating']:.2f} | "
                f"evidence {row['evidence_level']} | latest {latest['date'].strftime('%d %b %Y') if latest else 'unclear'}"
            )
            cards.append(rf"\dishcard{{{tex_escape(row['dish'])}}}{{{tex_escape(detail)}}}{{{tex_escape(excerpt)}}}{{{link}}}")
        frame_with_cards(lines, f"Appendix J{page} - All dishes/items mentioned", f"J{page} - Dishes {start+1}-{min(start+3, len(dishes))} of {len(dishes)}", "a-dishes" if start == 0 else f"a-dishes-{page}", "m-dishes", "Back to Dishes Mentioned", cards)

    lines.extend([
        r"\begin{frame}{Appendix K - Owner-response period evidence}",
        r"  \hypertarget{a-owner}{}\appendixhead{K - Owner Response}",
        r"  \begin{columns}[T,onlytextwidth]\column{0.58\textwidth}\begin{tikzpicture}\begin{axis}[ybar,bar width=17pt,width=8.3cm,height=4.65cm,ymin=0,ymax=16,symbolic x coords={0,1,2},xtick=data,xticklabels={Historical,Previous 90d,Recent 90d},x tick label style={font=\fontsize{6.2}{7.2}\selectfont},ytick={0,5,10,15},legend style={font=\fontsize{5.8}{6.8}\selectfont,at={(0.5,1.02)},anchor=south,legend columns=2,draw=none},grid=major,grid style={LightGray}]\addplot[fill=Gold,draw=Gold] table[x=index,y=rate,col sep=comma]{assets/owner_response_periods.csv};\addplot[fill=Red,draw=Red] table[x=index,y=low_score_rate,col sep=comma]{assets/owner_response_periods.csv};\legend{All reviews,Low-score}\end{axis}\end{tikzpicture}\column{0.38\textwidth}{\fontsize{7.4}{8.9}\selectfont Overall response: \OwnerOverallRate\% (\OwnerOverallResponses\ reviews). Latest 30d: \OwnerRecentThirtyRate\%. Recent 90d: \OwnerRecentNinetyRate\%. Low-score: \LowScoreResponseRate\%; \LowScoreUnanswered/\LowScoreReviews\ unanswered. Average delay among answered reviews: \OwnerAverageDelay\ days; median \OwnerMedianDelay\ days.\par\vspace{0.15cm}\textbf{Action:} acknowledge every review; give every low-score case an owner, response target, internal check and closure status.}",
        r"  \end{columns}\vfill\backbutton{m-owner}{Back to Review Flow}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix L - Provenance and management observations}",
        r"  \hypertarget{a-observations}{}\appendixhead{L - Provenance}",
        r"  \begin{columns}[T,onlytextwidth]\column{0.48\textwidth}\sourceReview\par\vspace{0.06cm}{\fontsize{7.3}{8.7}\selectfont Drinks/bar has low observable review attention. Menu/tablet confusion appears in review evidence. Response and topic metrics are customer/data evidence.}\par\vspace{0.14cm}\sourceInternal\par\vspace{0.06cm}{\fontsize{7.3}{8.7}\selectfont Parking visibility, static menu, manual favourites, no weekly offers/bundles, and current welcome/menu guidance are management observations supplied by the business.}\par\vspace{0.14cm}\sourceExperiment\par\vspace{0.06cm}{\fontsize{7.3}{8.7}\selectfont Welcome gesture, featured item, bundle, drink feature and richer dish media are proposed tests.}\column{0.48\textwidth}\sourceData\par\vspace{0.06cm}{\fontsize{7.3}{8.7}\selectfont POS orders, revenue, margin, returns, day/time and offer uptake are required before menu removal or redesign decisions.}\par\vspace{0.14cm}\badge{PaleTeal}{MANAGEMENT ACTION}\par\vspace{0.06cm}{\fontsize{7.3}{8.7}\selectfont Buffet needs dedicated feedback and quality monitoring.}\par\vspace{0.14cm}\badge{PaleGold}{MEASUREMENT PRINCIPLE}\par\vspace{0.06cm}{\fontsize{7.3}{8.7}\selectfont Lifetime rating moves slowly; weekly control should use rolling 30d and 90d indicators.}",
        r"  \end{columns}\vfill\backbutton{m-observations}{Back to Management Observations}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix M1 - Week 1 immediate action checklist}",
        r"  \hypertarget{a-actions}{}\appendixhead{M1 - Immediate Actions}",
        r"  \begin{columns}[T,onlytextwidth]\column{0.48\textwidth}\smallcapslabel{Today / next 48 hours}\par\vspace{0.06cm}\begin{itemize}\setlength\itemsep{0.07cm}\fontsize{7.8}{9.3}\selectfont\item Assign response owner and backup\item Log all recent low-score cases\item Approve the response rule\item Reply individually to open recent reviews\item Brief Guest Experience and Kitchen leads\item Confirm profile and parking information\end{itemize}\column{0.48\textwidth}\smallcapslabel{Plan this week}\par\vspace{0.06cm}\begin{itemize}\setlength\itemsep{0.07cm}\fontsize{7.8}{9.3}\selectfont\item Start rolling KPI dashboard\item Define POS export fields\item Assign competitor/market visits\item Select comparable dishes and venues\item Prepare one welcome, offer and bundle test\item Capture owners, dates and success measures\end{itemize}\end{columns}",
        r"  \vfill\backbutton{m-actions}{Back to Action Plan}\quad\tealbutton{a-market-scan}{Open market scan assignment}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix M2 - Week 2 data and hypothesis setup}",
        r"  \hypertarget{a-week2}{}\appendixhead{M2 - Week 2}",
        r"  \begin{columns}[T,onlytextwidth]\column{0.48\textwidth}\smallcapslabel{POS/data work}\par\vspace{0.06cm}\begin{itemize}\setlength\itemsep{0.08cm}\fontsize{8}{9.5}\selectfont\item Export item-level POS/order data\item Clean item/category names\item Add orders, revenue, margin, returns and time\item Match review-attention names to POS items\item Document gaps and owners\end{itemize}\column{0.48\textwidth}\smallcapslabel{Prepare - do not redesign yet}\par\vspace{0.06cm}\begin{itemize}\setlength\itemsep{0.08cm}\fontsize{8}{9.5}\selectfont\item Draft menu-navigation hypotheses\item Define favourite-selection method\item Select first controlled tests\item Define offer/bundle measures\item Agree evidence threshold and decision date\end{itemize}\end{columns}\vfill\colorbox{PaleGold}{\parbox{0.965\linewidth}{\fontsize{7.5}{8.9}\selectfont Week 2 does not complete menu redesign or update favourites. Those decisions wait for clean POS economics plus review evidence.}}\par\vspace{0.07cm}\backbutton{m-actions}{Back to Action Plan}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix M3 - Weeks 3-4: test, review, decide}",
        r"  \hypertarget{a-tests}{}\appendixhead{M3 - Controlled Tests}",
        r"  \begin{columns}[T,onlytextwidth]\column{0.48\textwidth}\smallcapslabel{Week 3 - small tests}\par\vspace{0.06cm}\begin{itemize}\setlength\itemsep{0.08cm}\fontsize{8}{9.5}\selectfont\item One featured food item\item One drink feature or bundle\item One welcome gesture\item Proactive menu/buffet/drink guidance\item Capture eligible orders, uptake, margin and feedback\end{itemize}\column{0.48\textwidth}\smallcapslabel{Week 4 - review and decide}\par\vspace{0.06cm}\begin{itemize}\setlength\itemsep{0.08cm}\fontsize{8}{9.5}\selectfont\item Review rolling 30d/90d and open cases\item Compare uptake, margin and staff burden\item Stop, adjust or scale each test\item Schedule next buffet feedback cycle\item Update menu/favourites only when evidence is ready\end{itemize}\end{columns}\vfill\backbutton{m-actions}{Back to Action Plan}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix M4 - Competitor and market tasting assignment}",
        r"  \hypertarget{a-market-scan}{}\appendixhead{M4 - Market Scan}",
        r"  \begin{columns}[T,onlytextwidth]\column{0.48\textwidth}\smallcapslabel{Visit and observe}\par\vspace{0.06cm}\begin{itemize}\setlength\itemsep{0.07cm}\fontsize{7.8}{9.3}\selectfont\item Taste comparable dishes\item Observe food and drink presentation\item Identify famous/popular dishes as presented\item Compare menu structure and buffet offer\item Observe service, welcome and guidance\item Note pricing, offers and bundles\end{itemize}\column{0.48\textwidth}\smallcapslabel{Bring to weekly review}\par\vspace{0.06cm}\begin{itemize}\setlength\itemsep{0.07cm}\fontsize{7.8}{9.3}\selectfont\item Venue/date and assigned staff\item Comparable items and price notes\item Photos/notes where appropriate\item What appears transferable\item What should not be copied\item One test hypothesis with owner and metric\end{itemize}\end{columns}\vfill\colorbox{PaleTeal}{\parbox{0.965\linewidth}{\fontsize{7.5}{8.9}\selectfont Immediate: schedule and assign the first visit. Long term: repeat a light market scan monthly or quarterly and review findings with POS/review evidence.}}\par\vspace{0.07cm}\backbutton{m-actions}{Back to Action Plan}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix M5 - Four workstreams and escalation}",
        r"  \hypertarget{a-workstreams}{}\appendixhead{M5 - Ownership}",
        r"  {\setlength{\tabcolsep}{2pt}\fontsize{6.6}{7.9}\selectfont\begin{tabular}{p{2.6cm}p{2.2cm}p{4.15cm}p{2.25cm}p{2.3cm}}\toprule\textbf{Workstream} & \textbf{Owner} & \textbf{Responsibilities / deliverables} & \textbf{Weekly KPIs} & \textbf{Escalation question}\\\midrule Reputation \& Data & Admin/marketing or manager & Reviews, responses, case log, dashboard, evidence tracking & Response, delay, open cases & Any case overdue or data missing?\\Guest Experience & Service lead & Welcome, menu guidance, waiting, communication, buffet service & Service negatives, waiting, feedback & Repeating shift or journey failure?\\Kitchen \& Buffet Quality & Kitchen lead & Food cases, dish quality, freshness, consistency, buffet checks & Food/Taste negatives, buffet sentiment & Same dish/process/holding issue?\\Menu, Bar \& Offers & Manager + assigned owner & POS analysis, menu hypotheses, favourites method, offers, drinks, media & Uptake, margin, complaints, mentions & Enough evidence to change or scale?\\\bottomrule\end{tabular}}\par\vspace{0.15cm}\colorbox{PaleGold}{\parbox{0.965\linewidth}{\fontsize{7.4}{8.8}\selectfont Delegate ownership, not accountability. The manager reviews progress, evidence, blockers and next dates every week.}}\par\vspace{0.07cm}\backbutton{m-delegation}{Back to Delegation}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix M6 - Low-score response and closure process}",
        r"  \hypertarget{a-response-process}{}\appendixhead{M6 - Response Process}",
        r"  \begin{columns}[T,onlytextwidth]\column{0.52\textwidth}\begin{enumerate}\setlength\itemsep{0.08cm}\fontsize{8}{9.5}\selectfont\item Log the review and anonymous case ID.\item Assign workstream owner and 48-hour response target.\item Acknowledge the experience without arguing.\item Reference the specific issue accurately.\item Run the internal operational check.\item Record public-response date and internal action.\item Close only when the check/action is documented.\end{enumerate}\column{0.42\textwidth}\colorbox{PaleRed}{\parbox{0.90\linewidth}{\fontsize{7.8}{9.3}\selectfont\bfseries Do not:\par copy generic replies\par reveal personal information\par promise unverified fixes\par debate publicly\par mark closed without evidence}}\par\vspace{0.16cm}{\fontsize{7.2}{8.6}\selectfont Day/time, shift and internal-resolution data are currently unavailable; capture them in the case log.}\end{columns}\vfill\backbutton{m-owner}{Back to Review Flow}\quad\backbutton{m-badcases}{Back to Operational Cases}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix M7 - POS fields and decision matrix}",
        r"  \hypertarget{a-pos}{}\appendixhead{M7 - POS / Menu Decision Support}",
        r"  \begin{columns}[T,onlytextwidth]\column{0.46\textwidth}\sourceData\par\vspace{0.06cm}\begin{itemize}\setlength\itemsep{0.06cm}\fontsize{7.6}{9.1}\selectfont\item Item and category\item Orders and repeat orders\item Revenue and contribution margin\item Discounts, cancellations and returns\item Day/time and recent trend\item Offer/bundle participation\item Review-attention match\end{itemize}\column{0.50\textwidth}{\fontsize{7.3}{8.7}\selectfont\textbf{High order / high attention:} protect and highlight.\par\vspace{0.09cm}\textbf{High order / low attention:} sells but may not be memorable; improve storytelling.\par\vspace{0.09cm}\textbf{Low order / high attention:} niche or polarizing; investigate.\par\vspace{0.09cm}\textbf{Low order / low attention:} candidate for simplification only after margin and operational check.}\end{columns}\vfill\backbutton{m-menu}{Back to Menu \& Ordering}",
        r"\end{frame}", "",
        r"\begin{frame}{Appendix N - KPI definitions and review cadence}",
        r"  \hypertarget{a-kpi}{}\appendixhead{N - KPI Control}",
        r"  {\setlength{\tabcolsep}{2pt}\fontsize{6.6}{7.9}\selectfont\begin{tabular}{p{2.7cm}p{6.0cm}p{2.0cm}p{2.2cm}}\toprule\textbf{KPI} & \textbf{Definition} & \textbf{Cadence} & \textbf{Owner}\\\midrule New reviews / average & Count and mean rating in rolling 30d/90d & Weekly & Reputation \& Data\\Negative share / low-score & 1-2 star share and count & Weekly & Manager\\Owner / bad-review response & Share answered; low-score answered within target & Weekly & Response owner\\Response delay / open cases & Days to public response; cases without closure & Weekly & Reputation \& Data\\Operational negatives & Service, Food/Taste, Menu, Drinks, Buffet signals & Weekly & Workstream leads\\Experiment uptake & Eligible orders, uptake, revenue, margin, feedback & Weekly & Menu/Bar owner\\\bottomrule\end{tabular}}\par\vspace{0.14cm}\colorbox{PaleGold}{\parbox{0.965\linewidth}{\fontsize{7.4}{8.8}\selectfont Current 30d baseline: \RecentThirtyPerWeek\ reviews/week; \RecentThirtyAverage\ average; \RecentThirtyNegativePct\% negative; \OwnerRecentThirtyRate\% owner response. Lifetime Google rating moves slowly; use rolling 30d for fast control and rolling 90d for stability.}}\par\vspace{0.07cm}\backbutton{m-kpi}{Back to KPI Tracking}",
        r"\end{frame}", "",
    ])
    APPENDIX_TEX.write_text("\n".join(lines), encoding="utf-8")
    return len(re.findall(r"\\begin\{frame\}", "\n".join(lines)))


def generate_data(
    layer_05: dict,
    layer_04: dict,
    profile: dict,
    reviews: dict[str, dict],
    quotes: dict[str, dict],
) -> None:
    overall = layer_05["overall_performance"]
    trend_summary = layer_05["trends"]["summary"]
    satisfaction = layer_05["satisfaction_vs_dissatisfaction"]
    priorities = layer_05["business_priorities"]["priorities"]
    emerging = layer_05["emerging_insights"]
    buffet = layer_05["buffet_analysis"]
    dish_rankings = layer_05["dish_rankings"]
    quality = layer_05["data_quality"]
    lines = ["% Generated by presentation/build_presentation.py. Do not edit manually."]

    macro(lines, "GoogleRating", fmt(overall["google_rating"], 1))
    macro(lines, "TotalReviews", overall["google_review_count"])
    macro(lines, "CollectedAverage", fmt(overall["collected_average_rating"], 3))
    macro(lines, "WrittenReviews", overall["written_reviews"])
    macro(lines, "WrittenCoverage", fmt(overall["written_review_coverage_pct"], 1))
    groups = {row["rating_group"]: row for row in overall["rating_groups"]}
    positive = groups["Positive 4-5 stars"]
    negative = groups["Negative 1-2 stars"]
    macro(lines, "PositiveRatingCount", positive["count"])
    macro(lines, "PositiveRatingPct", fmt(positive["share_pct_of_valid_ratings"], 1))
    macro(lines, "NegativeRatingCount", negative["count"])
    macro(lines, "NegativeRatingPct", fmt(negative["share_pct_of_valid_ratings"], 1))
    distribution = {int(row["rating"]): row for row in overall["rating_distribution"]}
    star_words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
    for star in range(1, 6):
        macro(lines, f"Rating{star_words[star]}Count", distribution[star]["count"])
        macro(lines, f"Rating{star_words[star]}Pct", fmt(distribution[star]["pct"], 1))

    trend_fields = {
        "RecentThirtyReviews": ("recent_30d_reviews", 0), "RecentThirtyAverage": ("recent_30d_average", 2),
        "PreviousThirtyReviews": ("previous_30d_reviews", 0), "PreviousThirtyAverage": ("previous_30d_average", 2),
        "RecentNinetyReviews": ("recent_90d_reviews", 0), "RecentNinetyAverage": ("recent_90d_average", 2),
        "PreviousNinetyReviews": ("previous_90d_reviews", 0), "PreviousNinetyAverage": ("previous_90d_average", 2),
        "HistoricalReviews": ("historical_before_recent_90d_reviews", 0), "HistoricalAverage": ("historical_before_recent_90d_average", 2),
        "RecentVsHistoricalDelta": ("rating_change_recent_90d_vs_historical", 2),
        "RecentThirtyNegativePct": ("recent_30d_negative_pct", 1),
        "PreviousThirtyNegativePct": ("previous_30d_negative_pct", 1),
        "RecentThirtyNegativeDeltaAbs": ("negative_pct_change_recent_30d_vs_previous_30d", 2),
        "RecentThirtyDelta": ("rating_change_recent_30d_vs_previous_30d", 2),
        "RecentNegativePct": ("recent_90d_negative_pct", 1),
        "PreviousNinetyNegativePct": ("previous_90d_negative_pct", 1),
        "RecentNinetyDelta": ("rating_change_recent_90d_vs_previous_90d", 2),
        "HistoricalNegativePct": ("historical_before_recent_90d_negative_pct", 1),
    }
    for name, (key, decimals) in trend_fields.items():
        value = trend_summary[key]
        if name == "RecentThirtyNegativeDeltaAbs":
            value = abs(value)
        macro(lines, name, fmt(value, decimals) if decimals else int(value))
    latest = datetime.fromisoformat(trend_summary["latest_review_date"])
    earliest = datetime.fromisoformat(trend_summary["oldest_review_date"])
    recent_start = datetime.fromisoformat(trend_summary["recent_90d_start"])
    macro(lines, "LatestReviewDate", latest.strftime("%d %b %Y"))
    macro(lines, "EarliestReviewDate", earliest.strftime("%d %b %Y"))
    macro(lines, "RecentNinetyStart", recent_start.strftime("%d %b %Y"))

    cadence = layer_05["review_cadence"]
    recent_30 = cadence["periods"]["recent_30d"]
    previous_30 = cadence["periods"]["previous_30d"]
    macro(lines, "RecentThirtyPerWeek", fmt(recent_30["reviews_per_week"], 2))
    macro(lines, "RecentThirtyGap", fmt(recent_30["average_days_between_reviews"], 2))
    macro(lines, "PreviousThirtyPerWeek", fmt(previous_30["reviews_per_week"], 2))
    macro(lines, "PreviousThirtyGap", fmt(previous_30["average_days_between_reviews"], 2))
    macro(lines, "CadenceFrequencyChange", fmt(cadence["comparisons"]["recent_30d_vs_previous_30d_frequency_change_pct"], 1))
    recent_30_start = datetime.fromisoformat(recent_30["start"])
    previous_30_start = datetime.fromisoformat(previous_30["start"])
    recent_30_topics = topic_summary_for_period(layer_04, reviews, recent_30_start, None)
    previous_30_topics = topic_summary_for_period(layer_04, reviews, previous_30_start, recent_30_start)
    macro(lines, "RecentThirtyStart", recent_30_start.strftime("%d %b %Y"))
    macro(lines, "PreviousThirtyStart", previous_30_start.strftime("%d %b %Y"))
    macro(lines, "RecentThirtyWritten", recent_30_topics["written_reviews"])
    macro(lines, "PreviousThirtyWritten", previous_30_topics["written_reviews"])
    selected_period_topics = {
        "Food": "ThirtyFood", "Service": "ThirtyService", "Taste": "ThirtyTaste",
        "Drinks": "ThirtyDrinks", "Buffet": "ThirtyBuffet", "Menu & Tablet": "ThirtyMenu",
        "Atmosphere": "ThirtyAtmosphere", "Staff Friendliness": "ThirtyFriendliness",
        "Staff Communication": "ThirtyCommunication", "Parking": "ThirtyParking",
    }
    for period_name, summary in (("Recent", recent_30_topics), ("Previous", previous_30_topics)):
        for topic, prefix in selected_period_topics.items():
            row = summary["topics"].get(topic, {})
            macro(lines, period_name + prefix + "Mentions", row.get("mentions", 0))
            macro(lines, period_name + prefix + "Coverage", fmt(row.get("coverage_pct", 0), 1))
            macro(lines, period_name + prefix + "Positive", row.get("positive", 0))
            macro(lines, period_name + prefix + "PositiveCoverage", fmt(row.get("positive_coverage_pct", 0), 1))
            macro(lines, period_name + prefix + "PositiveEvidence", row.get("positive_evidence", "None"))
            macro(lines, period_name + prefix + "Negative", row.get("negative", 0))
            macro(lines, period_name + prefix + "NegativeCoverage", fmt(row.get("negative_coverage_pct", 0), 1))
            macro(lines, period_name + prefix + "NegativeEvidence", row.get("negative_evidence", "None"))
            macro(lines, period_name + prefix + "Neutral", row.get("neutral", 0))
    rank_words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}
    for sentiment in ("positive", "negative"):
        ranked = sorted(
            ((row[sentiment], topic, row) for topic, row in recent_30_topics["topics"].items() if row[sentiment]),
            key=lambda item: (-item[0], item[1]),
        )
        for index, (count, topic, row) in enumerate(ranked[:6], 1):
            prefix = "RecentTopPositive" if sentiment == "positive" else "RecentTopNegative"
            word = rank_words[index]
            macro(lines, prefix + word + "Name", topic)
            macro(lines, prefix + word + "Count", count)
            macro(lines, prefix + word + "Pct", fmt(row[f"{sentiment}_coverage_pct"], 1))
            macro(lines, prefix + word + "Evidence", row[f"{sentiment}_evidence"])

    owner = layer_05["owner_response_analysis"]
    owner_by_star = {int(row["rating"]): row for row in owner["by_star_rating"]}
    macro(lines, "OwnerOverallRate", fmt(owner["overall"]["owner_response_rate_pct"], 2))
    macro(lines, "OwnerOverallResponses", owner["overall"]["reviews_with_owner_response"])
    macro(lines, "OwnerRecentThirtyRate", fmt(owner["periods"]["recent_30d"]["response_rate_pct"], 1))
    macro(lines, "OwnerPreviousThirtyRate", fmt(owner["periods"]["previous_30d"]["response_rate_pct"], 1))
    macro(lines, "OwnerRecentNinetyRate", fmt(owner["periods"]["recent_90d"]["response_rate_pct"], 1))
    macro(lines, "OwnerHistoricalRate", fmt(owner["periods"]["historical_before_recent_90d"]["response_rate_pct"], 2))
    macro(lines, "LowScoreResponseRate", fmt(owner["low_score"]["low_score_response_rate_pct"], 2))
    macro(lines, "LowScoreUnanswered", owner["low_score"]["low_score_without_response"])
    macro(lines, "RecentThirtyLowScores", owner["periods"]["recent_30d"]["low_score_review_count"])
    macro(lines, "PreviousThirtyLowScores", owner["periods"]["previous_30d"]["low_score_review_count"])
    macro(lines, "RecentThirtyLowScoreResponseRate", fmt(owner["periods"]["recent_30d"]["low_score_response_rate_pct"], 1))
    macro(lines, "PreviousThirtyLowScoreResponseRate", fmt(owner["periods"]["previous_30d"]["low_score_response_rate_pct"], 1))
    macro(lines, "OneStarResponseRate", fmt(owner_by_star[1]["response_rate_pct"], 1))
    macro(lines, "TwoStarResponseRate", fmt(owner_by_star[2]["response_rate_pct"], 1))
    macro(lines, "OwnerAverageDelay", fmt(owner["response_delay"]["average_response_delay_days"], 1))
    macro(lines, "OwnerMedianDelay", fmt(owner["response_delay"]["median_response_delay_days"], 1))

    low = layer_05["low_rating_analysis"]
    one_star = low["groups"]["one_star"]
    two_star = low["groups"]["two_star"]
    combined_low = low["groups"]["combined_one_two_star"]
    for prefix, row in (("OneStar", one_star), ("TwoStar", two_star), ("LowScore", combined_low)):
        macro(lines, prefix + "Reviews", row["review_count"])
        macro(lines, prefix + "Share", fmt(row["share_of_all_reviews_pct"], 2))
        macro(lines, prefix + "Written", row["written_review_count"])
        macro(lines, prefix + "WrittenCoverage", fmt(row["written_review_count"] / row["review_count"] * 100, 1))
        macro(lines, prefix + "Responses", row["owner_response_count"])
    macro(lines, "HistoricalLowScores", low["period_comparison"]["historical_low_score_review_count"])
    macro(lines, "RecentLowScores", low["period_comparison"]["recent_90d_low_score_review_count"])
    low_topics = {row["topic"]: row for row in combined_low["topics"]}
    for topic, prefix in (
        ("Service", "LowService"), ("Food", "LowFood"),
        ("Price & Value", "LowPrice"), ("Taste", "LowTaste"),
        ("Menu & Tablet", "LowMenu"), ("Drinks", "LowDrinks"), ("Buffet", "LowBuffet"),
    ):
        row = low_topics[topic]
        macro(lines, prefix + "Count", row["negative_reviews"])
        macro(lines, prefix + "Pct", fmt(row["share_of_low_score_reviews_pct"], 1))
        macro(lines, prefix + "Evidence", row["evidence_level"].title())
    period_low_topics = {row["topic"]: row for row in low["period_comparison"]["topics"]}
    for topic, prefix in (("Food", "LowRecentFood"), ("Taste", "LowRecentTaste"), ("Service", "LowRecentService"), ("Price & Value", "LowRecentPrice")):
        row = period_low_topics[topic]
        macro(lines, prefix + "Historical", row["historical_low_score_reviews"])
        macro(lines, prefix + "Recent", row["recent_low_score_reviews"])
        macro(lines, prefix + "Change", fmt(row["change_in_coverage_pct_points"], 1))
    pairs = low["topic_cooccurrence"]["presentation_pairs_min_2_reviews"]
    pair_words = {1: "One", 2: "Two"}
    for index, row in enumerate(pairs[:2], 1):
        word = pair_words[index]
        macro(lines, f"LowPair{word}Name", row["topic_pair"])
        macro(lines, f"LowPair{word}Count", row["reviews_where_both_present"])
        macro(lines, f"LowPair{word}Share", fmt(row["share_of_low_score_reviews_pct"], 1))

    for category in ("Service", "Food", "Atmosphere"):
        row = find_category(layer_05["structured_ratings"], category)
        if not row:
            raise KeyError(f"Structured rating missing: {category}")
        macro(lines, f"{category}Rating", fmt(row["average_rating"], 2))
        macro(lines, f"{category}Coverage", fmt(row["coverage_pct"], 1))

    add_topic_macros(lines, layer_05["topics"])
    add_recent_low_rating_macros(lines, layer_04, reviews, recent_start)
    period_topics = {row["topic"]: row for row in layer_05["topic_period_comparison"]}
    for topic, prefix in (("Service", "ServicePeriod"), ("Food", "FoodPeriod"), ("Taste", "TastePeriod")):
        periods = period_topics[topic]["periods"]
        for period_key, period_label in (("historical", "Historical"), ("recent_90d", "Recent")):
            row = periods[period_key]
            macro(lines, prefix + period_label + "Mentions", row["reviews_mentioning_topic"])
            macro(lines, prefix + period_label + "Coverage", fmt(row["mention_coverage_pct_of_written_reviews"], 1))
            macro(lines, prefix + period_label + "Positive", row["positive_reviews"])
            macro(lines, prefix + period_label + "Negative", row["negative_reviews"])
            macro(lines, prefix + period_label + "Neutral", row["neutral_reviews"])
            macro(lines, prefix + period_label + "NegativeShare", fmt(row["negative_share_of_topic_reviews_pct"], 1))
            macro(lines, prefix + period_label + "Evidence", row["evidence_level"].title())
            macro(lines, prefix + period_label + "NegativeEvidence", evidence_level(int(row["negative_reviews"])))
    strengths = satisfaction["strengths"][:5]
    index_words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
    for index, row in enumerate(strengths, 1):
        word = index_words[index]
        macro(lines, f"Strength{word}Name", row["topic"])
        macro(lines, f"Strength{word}Count", row["positive_reviews"])
        macro(lines, f"Strength{word}Width", fmt(row["positive_reviews"] / strengths[0]["positive_reviews"] * 3.8, 2))
    for index, row in enumerate(priorities[:5], 1):
        word = index_words[index]
        macro(lines, f"Priority{word}Name", row["topic"])
        macro(lines, f"Priority{word}Negatives", row["negative_reviews"])
        macro(lines, f"Priority{word}Share", fmt(row["negative_share_pct"], 1))
        macro(lines, f"Priority{word}Evidence", row["evidence"].title())
        macro(lines, f"Priority{word}Recent", fmt(row.get("raw_recent_change"), 1))

    atmosphere = find_topic(emerging["emerging_strengths"], "Atmosphere")
    food_signal = find_topic(emerging["emerging_complaints"], "Food")
    service_signal = find_topic(emerging["emerging_complaints"], "Service")
    mixed = find_topic(emerging["mixed_emerging_signals"], "Taste")
    for label, row in (("AtmosphereSignal", atmosphere), ("FoodSignal", food_signal), ("ServiceSignal", service_signal)):
        if not row:
            raise KeyError(f"Emerging signal missing: {label}")
        macro(lines, f"{label}Reviews", row["recent_reviews"])
        macro(lines, f"{label}Change", fmt(row["change_pct_points"], 1))
        macro(lines, f"{label}Evidence", row["evidence_level"].title())
    if not mixed:
        raise KeyError("Mixed Taste signal missing")
    macro(lines, "TastePositiveRecent", mixed["positive_recent_reviews"])
    macro(lines, "TastePositiveEvidence", mixed["positive_evidence_level"].title())
    macro(lines, "TasteNegativeRecent", mixed["negative_recent_reviews"])
    macro(lines, "TasteNegativeEvidence", mixed["negative_evidence_level"].title())

    buffet_sentiment = buffet["overall_sentiment"]
    macro(lines, "BuffetReviews", buffet["reviews_mentioning_buffet"])
    macro(lines, "BuffetCoverage", fmt(buffet["mention_coverage_pct_of_written_reviews"], 1))
    macro(lines, "BuffetPositiveCount", buffet_sentiment["positive"])
    macro(lines, "BuffetPositivePct", fmt(buffet_sentiment["positive_pct"], 1))
    macro(lines, "BuffetNegativeCount", buffet_sentiment["negative"])
    macro(lines, "BuffetNegativePct", fmt(buffet_sentiment["negative_pct"], 1))
    macro(lines, "BuffetNeutralCount", buffet_sentiment["neutral"])
    macro(lines, "BuffetNeutralPct", fmt(100 - buffet_sentiment["positive_pct"] - buffet_sentiment["negative_pct"], 1))
    for name in ("quality", "variety", "freshness", "value", "replenishment", "waiting_queue"):
        macro(lines, f"Buffet{name.title().replace('_', '')}Reviews", buffet[name]["reviews"])
    for key, prefix in (("historical_before_recent_90d", "BuffetHistorical"), ("recent_90d", "BuffetRecent")):
        row = buffet["period_comparison"][key]
        macro(lines, prefix + "Mentions", row["mentions"])
        macro(lines, prefix + "Coverage", fmt(row["mention_coverage_pct_of_written_reviews"], 1))
        macro(lines, prefix + "Positive", row["positive"])
        macro(lines, prefix + "Negative", row["negative"])
        macro(lines, prefix + "Neutral", row["neutral"])
        macro(lines, prefix + "Average", fmt(row["average_review_rating_when_mentioned"], 2))
        macro(lines, prefix + "Evidence", row["evidence_level"].title())
    buffet_profile = profile["buffet"]
    macro(lines, "BuffetDays", "Saturday and Sunday")
    macro(lines, "BuffetStart", buffet_profile["start_time"])
    macro(lines, "BuffetEnd", "20:00-21:00")

    bar = layer_05["bar_drinks_analysis"]
    bar_overall = bar["overall_review_evidence"]
    bar_totals = bar["menu_attention"]["totals"]
    macro(lines, "DrinkMentions", bar_overall["topic_mentions"])
    macro(lines, "DrinkCoverage", fmt(bar_overall["written_review_coverage_pct"], 2))
    macro(lines, "DrinkPositive", bar_overall["positive"])
    macro(lines, "DrinkNegative", bar_overall["negative"])
    macro(lines, "DrinkNeutral", bar_overall["neutral"])
    macro(lines, "DrinkAverage", fmt(bar_overall["average_overall_review_rating_when_mentioned"], 2))
    macro(lines, "DrinkEvidence", bar_overall["topic_evidence_level"].title())
    macro(lines, "DrinkMenuItems", bar_totals["total_drink_items"])
    macro(lines, "DrinkItemsMentioned", bar_totals["drink_items_with_observable_review_mentions"])
    macro(lines, "DrinkItemsUnmentioned", bar_totals["drink_items_with_no_observable_review_mentions"])
    macro(lines, "DrinkMenuCoverage", fmt(bar_totals["pct_drink_items_with_review_attention"], 2))
    for category, prefix in (("Cold Drinks", "ColdDrinks"), ("Hot Drinks", "HotDrinks"), ("Cocktails & Juices", "Cocktails")):
        row = next(item for item in bar["menu_attention"]["categories"] if item["category"] == category)
        macro(lines, prefix + "Items", row["total_menu_items"])
        macro(lines, prefix + "Mentioned", row["items_with_review_mentions"])
    for key, prefix in (("historical", "DrinkHistorical"), ("recent_90d", "DrinkRecent")):
        row = bar["period_comparison"][key]
        macro(lines, prefix + "Mentions", row["mentions"])
        macro(lines, prefix + "Coverage", fmt(row["mention_coverage_pct_of_written_reviews"], 1))
        macro(lines, prefix + "Positive", row["positive"])
        macro(lines, prefix + "Negative", row["negative"])
        macro(lines, prefix + "Neutral", row["neutral"])
        macro(lines, prefix + "Average", fmt(row["average_overall_review_rating_when_mentioned"], 2))
        macro(lines, prefix + "Evidence", row["topic_evidence_level"].title())

    kitchen_bar = layer_05["kitchen_bar_overview"]
    for key, prefix in (("kitchen", "Kitchen"), ("bar", "Bar")):
        row = kitchen_bar[key]
        macro(lines, prefix + "Attention", row["summed_topic_review_mentions_non_unique"])
        macro(lines, prefix + "Positive", row["summed_positive_non_unique"])
        macro(lines, prefix + "Negative", row["summed_negative_non_unique"])
        macro(lines, prefix + "Neutral", row["summed_neutral_non_unique"])
        macro(lines, prefix + "MenuItems", row["menu_items"])
        macro(lines, prefix + "ItemsMentioned", row["items_with_review_attention"])
        macro(lines, prefix + "MenuCoverage", fmt(row["review_attention_coverage_pct"], 2))
        macro(lines, prefix + "Evidence", row["evidence_level"].title())

    menu = layer_05["menu_analysis"]
    menu_summary = menu["summary"]
    macro(lines, "MenuItems", menu_summary["total_menu_items"])
    macro(lines, "MenuItemsMentioned", menu_summary["items_with_at_least_one_review_mention"])
    macro(lines, "MenuItemsUnmentioned", menu_summary["items_with_no_review_mentions"])
    macro(lines, "MenuAttentionCoverage", fmt(menu_summary["pct_items_with_review_attention"], 2))
    menu_insights = layer_05["menu_management_insights"]
    number_words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
    for index, row in enumerate(menu_insights["categories_with_strongest_review_attention"][:5], 1):
        word = number_words[index]
        macro(lines, f"MenuCategory{word}Name", row["category"])
        macro(lines, f"MenuCategory{word}Mentions", row["total_review_mentions"])
        macro(lines, f"MenuCategory{word}Items", row["total_items"])
        macro(lines, f"MenuCategory{word}Mentioned", row["items_mentioned"])
    management_menu = layer_05["management_observations"]["menu"]
    macro(lines, "MenuStatic", str(bool(management_menu["menu_considered_static"]["value"])).lower())
    macro(lines, "FavouritesManual", str(bool(management_menu["favourites_manually_selected"]["value"])).lower())
    macro(lines, "FavouritesNotUpdated", str(bool(management_menu["favourites_not_regularly_updated"]["value"])).lower())
    macro(lines, "WeeklyOffersAvailable", str(bool(management_menu["weekly_offers_available"]["value"])).lower())
    macro(lines, "BundlesAvailable", str(bool(management_menu["food_drink_bundles_available"]["value"])).lower())

    macro(lines, "DishRatingThreshold", dish_rankings["minimum_mentions_for_rating_rank"])
    qualified = dish_rankings["qualified_dishes_by_rating"]
    mansaf = find_dish(qualified, "Jordanisches Mansaf")
    tabbouleh = find_dish(qualified, "Tabbouleh")
    mixed_grill = find_dish(dish_rankings["most_criticized_dishes"], "Gemischte Grillplatte")
    for label, row in (("Mansaf", mansaf), ("Tabbouleh", tabbouleh), ("MixedGrill", mixed_grill)):
        if not row:
            raise KeyError(f"Dish evidence missing: {label}")
        macro(lines, f"{label}Mentions", row["reviews_mentioning"])
        macro(lines, f"{label}ReviewAverage", fmt(row["average_overall_rating"], 1))
        macro(lines, f"{label}Positive", row["positive_reviews"])
        macro(lines, f"{label}Negative", row["negative_reviews"])
        macro(lines, f"{label}Evidence", row["evidence_level"].title())
    for index, row in enumerate(menu_insights["most_discussed_menu_items"][:5], 1):
        word = number_words[index]
        macro(lines, f"DiscussedDish{word}Name", row["item"])
        macro(lines, f"DiscussedDish{word}Mentions", row["review_mentions"])
        macro(lines, f"DiscussedDish{word}Positive", row["positive_dish_reviews"])
        macro(lines, f"DiscussedDish{word}Negative", row["negative_dish_reviews"])

    quality_fields = {
        "EnglishWritten": "english_written_reviews", "NonEnglishWritten": "non_english_written_reviews",
        "TranslatedNonEnglish": "translated_non_english_reviews", "TranslationCoverage": "non_english_translation_coverage_pct",
        "UsableTextReviews": "usable_analysis_text_reviews", "UsableTextCoverage": "usable_analysis_text_coverage_pct",
        "DuplicateReviewIds": "duplicate_review_ids", "InvalidReviews": "invalid_review_count",
    }
    for name, key in quality_fields.items():
        macro(lines, name, fmt(quality[key], 1) if "Coverage" in name else quality[key])
    for quote_name, quote in quotes.items():
        macro(lines, f"Quote{quote_name}Text", quote["text"])
        link = href_for_review(quote)
        raw_macro(lines, f"Quote{quote_name}Meta", tex_escape(quote["metadata"]) + r"\quad " + link)

    monthly = layer_05["trends"]["monthly"]
    tick_indexes = sorted(set(list(range(0, len(monthly), 3)) + [len(monthly) - 1]))
    tick_labels = ",".join("{" + datetime.strptime(monthly[i]["month"], "%Y-%m").strftime("%b %y") + "}" for i in tick_indexes)
    lines.append(rf"\pgfplotsset{{monthly axis ticks/.style={{xtick={{{','.join(map(str, tick_indexes))}}},xticklabels={{{tick_labels}}}}}}}")
    DATA_TEX.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with (ASSET_DIR / "monthly_trend.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["index", "average", "reviews", "negative_pct", "low_scores"])
        for index, row in enumerate(monthly):
            low_scores = round(row["reviews"] * row["negative_pct"] / 100)
            writer.writerow([index, row["average_rating"], row["reviews"], row["negative_pct"], low_scores])
    with (ASSET_DIR / "monthly_partial.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["index", "average"])
        for index, row in enumerate(monthly):
            if row["is_partial_month"]: writer.writerow([index, row["average_rating"]])
    month_index = {row["month"]: index for index, row in enumerate(monthly)}
    for category in ("Food", "Service", "Atmosphere"):
        path = ASSET_DIR / f"structured_{category.lower()}.csv"
        rows = [row for row in layer_05["trends"]["structured"] if row["category"] == category]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle); writer.writerow(["index", "average", "reviews", "evidence"])
            for row in rows:
                writer.writerow([month_index[row["month"]], row["average_rating"], row["reviews"], row["evidence_level"]])
    with (ASSET_DIR / "review_volume.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["index", "reviews"])
        for row in cadence["monthly_review_volume"]:
            writer.writerow([month_index[row["month"]], row["review_count"]])
    with (ASSET_DIR / "owner_response_periods.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["index", "rate", "reviews", "low_score_rate"])
        for index, key in enumerate(("historical_before_recent_90d", "previous_90d", "recent_90d")):
            row = owner["periods"][key]
            writer.writerow([index, row["response_rate_pct"], row["review_count"], row["low_score_response_rate_pct"]])
    with (ASSET_DIR / "last_30d_topics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["topic", "recent_mentions", "recent_positive", "recent_negative", "previous_mentions", "previous_positive", "previous_negative"])
        for topic in selected_period_topics:
            recent_row = recent_30_topics["topics"].get(topic, {})
            previous_row = previous_30_topics["topics"].get(topic, {})
            writer.writerow([
                topic, recent_row.get("mentions", 0), recent_row.get("positive", 0), recent_row.get("negative", 0),
                previous_row.get("mentions", 0), previous_row.get("positive", 0), previous_row.get("negative", 0),
            ])
    with (ASSET_DIR / "low_score_topics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["topic", "negative_reviews", "evidence"])
        for row in combined_low["topics"]:
            if int(row["negative_reviews"]) > 0:
                writer.writerow([row["topic"], row["negative_reviews"], row["evidence_level"]])
    with (ASSET_DIR / "bar_periods.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["index", "positive_pct", "neutral_pct", "negative_pct", "mentions"])
        for index, key in enumerate(("historical", "recent_90d")):
            row = bar["period_comparison"][key]; total = row["mentions"] or 1
            writer.writerow([index, row["positive"] / total * 100, row["neutral"] / total * 100,
                             row["negative"] / total * 100, row["mentions"]])
    with (ASSET_DIR / "buffet_periods.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["index", "positive_pct", "neutral_pct", "negative_pct", "mentions"])
        for index, key in enumerate(("historical_before_recent_90d", "recent_90d")):
            row = buffet["period_comparison"][key]
            writer.writerow([index, row["positive_pct"], row["neutral_pct"], row["negative_pct"], row["mentions"]])
    with (ASSET_DIR / "period_rating_comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["period", "average", "negative_pct", "reviews"])
        writer.writerow(["Historical", trend_summary["historical_before_recent_90d_average"], trend_summary["historical_before_recent_90d_negative_pct"], trend_summary["historical_before_recent_90d_reviews"]])
        writer.writerow(["Previous90", trend_summary["previous_90d_average"], trend_summary["previous_90d_negative_pct"], trend_summary["previous_90d_reviews"]])
        writer.writerow(["Recent90", trend_summary["recent_90d_average"], trend_summary["recent_90d_negative_pct"], trend_summary["recent_90d_reviews"]])
    with (ASSET_DIR / "menu_category_attention.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["category", "mentions", "items", "mentioned"])
        for row in menu_insights["categories_with_strongest_review_attention"][:5]:
            writer.writerow([row["category"], row["total_review_mentions"], row["total_items"], row["items_mentioned"]])
    with (ASSET_DIR / "dish_mentions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["dish", "mentions", "positive", "negative", "neutral"])
        for row in layer_05["dishes"]:
            writer.writerow([row["dish"], row["reviews_mentioning"], row["positive_reviews"], row["negative_reviews"], row["neutral_reviews"]])
    with (ASSET_DIR / "buffet_sentiment.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(["sentiment", "count"])
        for sentiment in ("positive", "neutral", "negative"):
            writer.writerow([sentiment.title(), buffet_sentiment[sentiment]])
    manifest = {
        "generated_at_utc": datetime.now().astimezone().isoformat(),
        "privacy": "Anonymous excerpts and public original-review URLs only; no reviewer names, IDs, profile URLs, or photos.",
        "quotes": quotes,
    }
    QUOTE_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compile_pdf() -> tuple[str, list[str]]:
    compiler = shutil.which("latexmk") or shutil.which("lualatex")
    if not compiler:
        raise RuntimeError("LuaLaTeX is unavailable. Install a TeX distribution containing lualatex or latexmk.")
    with tempfile.TemporaryDirectory(prefix="al_assiel_presentation_") as build_dir:
        build = Path(build_dir); tex_cache = build / "tex-cache"; tex_cache.mkdir()
        environment = os.environ.copy(); environment["TEXMFVAR"] = str(tex_cache); environment["TEXMFCACHE"] = str(tex_cache)
        if Path(compiler).name == "latexmk":
            command = [compiler, "-lualatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-outdir={build}", str(SOURCE_TEX)]
            compiler_name = "latexmk with LuaLaTeX"
        else:
            command = [compiler, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-output-directory={build}", str(SOURCE_TEX)]
            compiler_name = "LuaLaTeX"
        result = subprocess.run(command, cwd=OUTPUT_DIR, env=environment, text=True, capture_output=True)
        log = build / "manager_presentation.log"
        if result.returncode:
            detail = log.read_text(errors="replace")[-7000:] if log.exists() else result.stdout[-7000:] + result.stderr[-2000:]
            raise RuntimeError(f"LaTeX compilation failed:\n{detail}")
        built_pdf = build / "manager_presentation.pdf"
        if not built_pdf.exists():
            raise RuntimeError("LaTeX completed without producing manager_presentation.pdf")
        warnings = [line.strip() for line in log.read_text(errors="replace").splitlines() if "Overfull" in line] if log.exists() else []
        shutil.copy2(built_pdf, FINAL_PDF)
    return compiler_name, warnings


def combined_source() -> str:
    return SOURCE_TEX.read_text(encoding="utf-8") + "\n" + APPENDIX_TEX.read_text(encoding="utf-8")


def validate_internal_links() -> tuple[int, int]:
    source = combined_source()
    targets = set(re.findall(r"\\hypertarget\{([^}]+)\}", source))
    chapter_targets = re.findall(
        r"(?m)^\\chapterdivider\{[^{}]*\}\{[^{}]*\}\{[^{}]*\}\{[^{}]*\}\{[^{}]*\}\{([^{}]+)\}\{[^{}]*\}",
        source,
    )
    targets.update(chapter_targets)
    literal_links = re.findall(r"\\hyperlink\{([^}]+)\}", source)
    macro_links = re.findall(r"\\(?:navlink|backlink|goldbutton|tealbutton|redbutton|backbutton)\{([^}]+)\}", source)
    chapter_links = [target + "-content" for target in chapter_targets]
    links = [target for target in literal_links + macro_links + chapter_links if "#" not in target]
    missing = sorted(set(links) - targets)
    if missing:
        raise ValueError(f"Presentation contains unresolved internal link targets: {', '.join(missing)}")
    explicit_frames = len(re.findall(r"(?m)^\\begin\{frame\}", source))
    chapter_frames = len(re.findall(r"(?m)^\\chapterdivider\{", source))
    frame_count = explicit_frames + chapter_frames
    if frame_count < 60:
        raise ValueError(f"Detailed deck unexpectedly contains only {frame_count} frames")
    return len(links), frame_count


def validate_external_links() -> int:
    source = combined_source()
    urls = re.findall(r"\\href\{((?:\\.|[^{}])+)\}", source)
    invalid = []
    for url in urls:
        clean_url = url.replace(r"\%", "%").replace(r"\#", "#").replace(r"\_", "_")
        parsed = urlsplit(clean_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            invalid.append(clean_url)
    if invalid:
        raise ValueError(f"Presentation contains invalid external review links: {invalid[:3]}")
    return len(urls)


def render_pdf(expected_slides: int) -> tuple[str, int]:
    pdftoppm = shutil.which("pdftoppm")
    ghostscript = shutil.which("gs")
    if not pdftoppm and not ghostscript:
        raise RuntimeError("Poppler pdftoppm or Ghostscript is required to render PDF pages for QA")
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    for old_slide in RENDER_DIR.glob("slide-*.png"):
        old_slide.unlink()
    if pdftoppm:
        command = [pdftoppm, "-png", "-r", "150", str(FINAL_PDF), str(RENDER_DIR / "slide")]
        renderer_name = "Poppler pdftoppm"
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(f"PDF rendering failed:\n{result.stderr[-3000:]}")
    else:
        renderer_name = "Ghostscript (isolated pages)"
        for page in range(1, expected_slides + 1):
            command = [
                ghostscript, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dShowAnnots=false",
                f"-dFirstPage={page}", f"-dLastPage={page}", "-sDEVICE=png16m", "-r150",
                f"-sOutputFile={RENDER_DIR / f'slide-{page:02d}.png'}", str(FINAL_PDF),
            ]
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            if result.returncode:
                raise RuntimeError(f"PDF page {page} rendering failed:\n{result.stderr[-3000:]}")
    count = len(list(RENDER_DIR.glob("slide-*.png")))
    if count != expected_slides:
        raise RuntimeError(f"Expected {expected_slides} rendered slides, found {count}")
    return renderer_name, count


def main() -> None:
    for source in (LAYER_05_JSON, LAYER_04_JSON, PROFILE_JSON, REVIEWS_DB, SOURCE_TEX):
        if not source.exists():
            raise SystemExit(f"Required presentation source not found: {source}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True); ASSET_DIR.mkdir(parents=True, exist_ok=True)
    try:
        layer_05 = json.loads(LAYER_05_JSON.read_text(encoding="utf-8"))
        layer_04 = json.loads(LAYER_04_JSON.read_text(encoding="utf-8"))
        profile = json.loads(PROFILE_JSON.read_text(encoding="utf-8"))
        reviews = load_reviews_read_only()
        validate_analysis(layer_05, layer_04, profile, reviews)
        recent_start = datetime.fromisoformat(layer_05["trends"]["summary"]["recent_90d_start"])
        quotes = select_quotes(layer_04, reviews, recent_start)
        generate_data(layer_05, layer_04, profile, reviews, quotes)
        appendix_slides = generate_appendix(layer_05, layer_04, reviews)
        internal_links, slide_count = validate_internal_links()
        external_links = validate_external_links()
        compiler, warnings = compile_pdf()
        renderer, rendered = render_pdf(slide_count)
    except (KeyError, RuntimeError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        raise SystemExit(f"Presentation build failed:\n{exc}") from exc
    print(f"Validated quotes: {len(quotes)}")
    print(f"Validated internal links: {internal_links}")
    print(f"Validated original-review links: {external_links}")
    print(f"Generated appendix slides: {appendix_slides}")
    print(f"Compiler: {compiler}")
    print(f"Renderer: {renderer}")
    print(f"Rendered slides: {rendered}")
    print(f"LaTeX overfull warnings: {len(warnings)}")
    for warning in warnings:
        print(f"  {warning}")
    print(f"PDF: {FINAL_PDF}")


if __name__ == "__main__":
    main()
