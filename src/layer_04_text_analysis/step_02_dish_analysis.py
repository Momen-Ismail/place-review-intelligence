"""Menu-item and ambiguous dish-family analysis."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from statistics import mean

from src.common.evidence import evidence_level
from src.common.text_utils import (
    analyze_mention_sentiment,
    get_named_text_variants,
    normalize_text,
    split_clauses,
    split_sentences,
)

DISH_FAMILY_ALIASES = {
    "kibbeh": ["kibbeh", "kibbe", "كبة"],
    "shawarma": ["shawarma", "schawarma", "شاورما"],
    "falafel": ["falafel", "فلافل"],
    "burger": ["burger", "hamburger"],
    "doner": ["doner", "döner", "doner kebab", "döner kebab"],
    "kebab": ["kebab", "kabob"],
}


def _pct(value, total):
    return round(value / total * 100, 2) if total else 0.0


def _rating(review):
    try:
        return float(review.get("rating"))
    except (TypeError, ValueError):
        return None


def _month(review):
    value = str(review.get("published_at") or "")
    return value[:7] if len(value) >= 7 else "unknown"


def item_aliases(item: dict) -> list[str]:
    values = [item.get("name"), item.get("english_name"), *item.get("aliases", [])]
    result, seen = [], set()
    for value in values:
        normalized = normalize_text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(str(value))
    return result


def dish_families(menu_items: list[dict]) -> dict[str, dict]:
    """Build configured generic families against the current menu catalog."""
    result = {}
    for token, configured_aliases in DISH_FAMILY_ALIASES.items():
        normalized_family_aliases = {normalize_text(alias) for alias in configured_aliases}
        indexes = {
            index for index, item in enumerate(menu_items)
            if any(
                re.search(rf"(?<!\w){re.escape(alias).replace(chr(92) + ' ', chr(92) + 's+')}(?!\w)", value)
                for alias in normalized_family_aliases
                for value in (normalize_text(item.get("name")), normalize_text(item.get("english_name")))
            )
        }
        if len(indexes) < 2:
            continue
        exact_plain = any(
            normalize_text(menu_items[i].get("name")) in normalized_family_aliases
            or normalize_text(menu_items[i].get("english_name")) in normalized_family_aliases
            for i in indexes
        )
        if exact_plain:
            continue
        aliases = {normalize_text(alias) for alias in configured_aliases}
        result[token] = {
            "dish_family": token,
            "candidate_menu_items": sorted(menu_items[i]["name"] for i in indexes),
            "item_indexes": sorted(indexes),
            "aliases": sorted(aliases, key=len, reverse=True),
        }
    return result


def ambiguous_family_aliases(menu_items: list[dict]) -> dict[str, list[str]]:
    return {
        alias: family["candidate_menu_items"]
        for family in dish_families(menu_items).values()
        for alias in family["aliases"]
    }


def _records(menu_items):
    families = dish_families(menu_items)
    family_aliases = {alias for family in families.values() for alias in family["aliases"]}
    records = []
    owners = defaultdict(set)
    item_values = {}
    for index, item in enumerate(menu_items):
        values = {normalize_text(value) for value in item_aliases(item)}
        item_values[index] = values
        for value in values:
            owners[value].add(index)
    for index, values in item_values.items():
        official = {normalize_text(menu_items[index].get("name")), normalize_text(menu_items[index].get("english_name"))}
        for alias in values:
            if len(owners[alias]) > 1 or (alias in family_aliases and alias not in official):
                continue
            records.append({"kind": "item", "key": index, "alias": alias})
    for key, family in families.items():
        for alias in family["aliases"]:
            records.append({"kind": "family", "key": key, "alias": alias})
    records.sort(key=lambda row: (len(row["alias"]), len(row["alias"].split())), reverse=True)
    return records, families


def _match_text(text, records):
    normalized = normalize_text(text)
    candidates = []
    for record in records:
        escaped = re.escape(record["alias"]).replace("\\ ", "\\s+")
        pattern = rf"(?<!\w){escaped}(?!\w)"
        for match in re.finditer(pattern, normalized):
            candidates.append({**record, "start": match.start(), "end": match.end(), "length": match.end() - match.start()})
    candidates.sort(key=lambda row: (row["length"], len(row["alias"].split()), -row["start"]), reverse=True)
    accepted = []
    for candidate in candidates:
        if any(not (candidate["end"] <= old["start"] or candidate["start"] >= old["end"]) for old in accepted):
            continue
        accepted.append(candidate)
    grouped = defaultdict(lambda: {"count": 0, "aliases": [], "matches": []})
    for match in accepted:
        key = (match["kind"], match["key"])
        grouped[key]["count"] += 1
        grouped[key]["aliases"].append(match["alias"])
        grouped[key]["matches"].append(match)
    return dict(grouped)


def match_review_dishes(review: dict, menu_items: list[dict]) -> dict:
    records, families = _records(menu_items)
    best = {"matches": {}, "variant": "", "text": "", "score": (0, 0, 0)}
    for variant, text in get_named_text_variants(review):
        matches = _match_text(text, records)
        score = (len(matches), sum(v["count"] for v in matches.values()), sum(len(a) for v in matches.values() for a in v["aliases"]))
        if score > best["score"]:
            best = {"matches": matches, "variant": variant, "text": text, "score": score}
    best["families"] = families
    return best


def _local_evidence(text, aliases):
    analysis = analyze_mention_sentiment(text, aliases)
    return analysis["sentiment"], analysis["evidence"]


def analyze_dishes_with_evidence(reviews, menu_items):
    written = sum(bool(get_named_text_variants(r)) for r in reviews)
    prepared = []
    records, families = _records(menu_items)
    for review in reviews:
        best = {"matches": {}, "variant": "", "text": "", "score": (0, 0, 0)}
        for variant, text in get_named_text_variants(review):
            matches = _match_text(text, records)
            score = (len(matches), sum(v["count"] for v in matches.values()), sum(len(a) for v in matches.values() for a in v["aliases"]))
            if score > best["score"]:
                best = {"matches": matches, "variant": variant, "text": text, "score": score}
        prepared.append((review, best))

    audit, dish_rows, trends = [], [], []
    for index, item in enumerate(menu_items):
        hits, monthly = [], defaultdict(list)
        for review, best in prepared:
            info = best["matches"].get(("item", index))
            if not info:
                continue
            aliases = list(dict.fromkeys(info["aliases"]))
            sentiment, local = _local_evidence(best["text"], aliases)
            hit = {"review": review, "info": info, "sentiment": sentiment, "rating": _rating(review)}
            hits.append(hit); monthly[_month(review)].append(hit)
            official = {normalize_text(item.get("name")), normalize_text(item.get("english_name"))}
            for evidence in local:
                audit.append({
                    "review_id": review.get("review_id"), "dish_or_family": item.get("name"),
                    "match_type": "exact_item" if any(a in official for a in evidence["matched_aliases"]) else "specific_alias",
                    "matched_alias": " | ".join(evidence["matched_aliases"]), "text_variant_used": best["variant"],
                    "matched_clause": evidence["matched_clause"], "positive_terms": evidence["positive_terms"],
                    "negative_terms": evidence["negative_terms"], "sentiment": sentiment,
                })
        counts = Counter(h["sentiment"] for h in hits); count = len(hits)
        ratings = [h["rating"] for h in hits if h["rating"] is not None]
        dish_rows.append({
            "menu_category": item.get("category"), "dish": item.get("name"), "english_name": item.get("english_name"),
            "price_eur": item.get("price_eur"), "reviews_mentioning": count,
            "mention_coverage_pct_of_written_reviews": _pct(count, written), "total_mentions": sum(h["info"]["count"] for h in hits),
            "positive_reviews": counts["positive"], "positive_share_of_dish_reviews_pct": _pct(counts["positive"], count),
            "negative_reviews": counts["negative"], "negative_share_of_dish_reviews_pct": _pct(counts["negative"], count),
            "neutral_reviews": counts["neutral"], "neutral_share_of_dish_reviews_pct": _pct(counts["neutral"], count),
            "average_review_rating_when_mentioned": round(mean(ratings), 3) if ratings else None,
            "evidence_level": evidence_level(count),
        })
        for month, month_hits in monthly.items():
            mc = Counter(h["sentiment"] for h in month_hits); n = len(month_hits)
            trends.append({"month": month, "dish": item.get("name"), "menu_category": item.get("category"),
                "reviews_mentioning": n, "positive_share_pct": _pct(mc["positive"], n),
                "negative_share_pct": _pct(mc["negative"], n), "evidence_level": evidence_level(n)})

    family_rows = []
    for key, family in families.items():
        hits = []
        for review, best in prepared:
            info = best["matches"].get(("family", key))
            if not info: continue
            aliases = list(dict.fromkeys(info["aliases"])); sentiment, local = _local_evidence(best["text"], aliases)
            hits.append((info, sentiment))
            for evidence in local:
                audit.append({"review_id": review.get("review_id"), "dish_or_family": key, "match_type": "ambiguous_family",
                    "matched_alias": " | ".join(evidence["matched_aliases"]), "text_variant_used": best["variant"],
                    "matched_clause": evidence["matched_clause"], "positive_terms": evidence["positive_terms"],
                    "negative_terms": evidence["negative_terms"], "sentiment": sentiment})
        if hits:
            counts = Counter(sentiment for _info, sentiment in hits)
            family_rows.append({"dish_family": key, "candidate_menu_items": family["candidate_menu_items"],
                "reviews_mentioning": len(hits), "total_mentions": sum(info["count"] for info, _ in hits),
                "positive_reviews": counts["positive"], "negative_reviews": counts["negative"], "neutral_reviews": counts["neutral"],
                "evidence_level": evidence_level(len(hits))})

    category_rows = []
    for category in sorted({item.get("category") or "Unknown" for item in menu_items}):
        members = [row for row in dish_rows if (row["menu_category"] or "Unknown") == category]
        category_rows.append({"menu_category": category, "menu_items": len(members),
            "mentioned_menu_items": sum(row["reviews_mentioning"] > 0 for row in members),
            "dish_review_mentions": sum(row["reviews_mentioning"] for row in members),
            "positive_reviews": sum(row["positive_reviews"] for row in members),
            "negative_reviews": sum(row["negative_reviews"] for row in members)})
    dish_rows.sort(key=lambda r: (r["reviews_mentioning"], r["total_mentions"]), reverse=True)
    family_rows.sort(key=lambda r: r["reviews_mentioning"], reverse=True)
    return dish_rows, category_rows, trends, family_rows, audit


def analyze_dishes(reviews, menu_items):
    dishes, categories, trends, _families, _audit = analyze_dishes_with_evidence(reviews, menu_items)
    return dishes, categories, trends


def analyze_ambiguous_dish_families(reviews, menu_items):
    _dishes, _categories, _trends, families, _audit = analyze_dishes_with_evidence(reviews, menu_items)
    return families
