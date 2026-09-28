"""Source-aware menu, price-basket, digital, kitchen/bar, and tasting views."""

from __future__ import annotations

from datetime import date

from src.common.evidence import evidence_level
from src.layer_04_text_analysis.step_02_dish_analysis import analyze_dishes_with_evidence
from src.layer_04_text_analysis.step_03_rankings import build_dish_rankings
from src.competitive_analysis.period_comparison import reviews_in_period


PRICE_MATCHES = {
    "Hummus": {
        "al_assiel": ("Hummus", "high"), "olivenzweig": ("Hummus", "high"),
        "al_safa": ("Hummus", "high"), "beit_fayrouz": ("Hummus", "high"),
    },
    "Tabbouleh": {
        "al_assiel": ("Tabbouleh", "high"), "olivenzweig": ("Tabouleh", "high"),
        "al_safa": ("Tabule", "high"), "beit_fayrouz": ("Tabbouleh", "high"),
    },
    "Fattoush": {
        "al_assiel": ("Fattoush", "high"), "olivenzweig": ("Fattoush", "high"),
        "beit_fayrouz": ("Fattoush", "high"),
    },
    "Falafel Plate": {
        "al_assiel": ("Falafel Teller", "high"), "olivenzweig": ("Falafel-Teller", "high"),
        "al_safa": ("Falafel Teller", "medium"), "beit_fayrouz": ("Falafel Teller", "high"),
    },
    "Shish Taouk / Chicken Grill": {
        "al_assiel": ("Shish Taouk", "high"), "olivenzweig": ("Shish Tawook", "high"),
        "al_safa": ("Hähnchen Teller mit Beilage", "medium"), "beit_fayrouz": ("Schisch Taouk Teller", "high"),
    },
    "Mixed Grill": {
        "al_assiel": ("Gemischte Grillplatte", "high"), "olivenzweig": ("Gemischter Grillteller 1 Person", "high"),
        "al_safa": ("Gemischter Grillteller mit Beilage", "medium"), "beit_fayrouz": ("Gemischter Grillteller", "high"),
    },
    "Lamb Chops": {
        "al_assiel": ("Lammkoteletts", "high"), "olivenzweig": ("Lammkotelett", "high"),
        "beit_fayrouz": ("Lammkotelett Teller", "high"),
    },
    "Dorade": {
        "al_assiel": ("Gegrillte / frittiert Dorade Fisch", "medium"), "olivenzweig": ("Gegrillter Fisch Dorade", "high"),
        "al_safa": ("Dorade mit Reis", "high"), "beit_fayrouz": ("Dorade", "high"),
    },
    "Shawarma": {
        "al_assiel": ("Shawarma Sandwich", "high"), "al_safa": ("Döner Sandwich", "low"),
        "beit_fayrouz": ("Schawarma Kalb Sandwich", "high"),
    },
    "Tea": {"al_assiel": ("Tee", "medium"), "olivenzweig": ("Schwarztee", "medium")},
    "Soft Drink": {"al_assiel": ("Cola", "medium"), "olivenzweig": ("Coca-Cola 0.2l", "medium"), "al_safa": ("Soft Drink 0.33l", "medium"), "beit_fayrouz": ("Fritz-Kola 0.33l", "medium")},
}


NORMALIZED_GROUPS = (
    "Starters", "Salads", "Grill / Meat Mains", "Other Main Dishes",
    "Breakfast", "Brunch", "Desserts", "Drinks / Bar", "Sharing Platters",
    "Sandwiches", "Vegetarian / Vegan", "Sides", "Kids", "Specials",
)


def _normalized_groups(category: str) -> set[str]:
    """Map a source category to transparent, non-exclusive comparison groups.

    The source category is never replaced. A category can contribute to more
    than one group (for example ``Breakfast & Vegan``), so normalized group
    counts must not be summed to recover the menu total.
    """
    value = category.casefold()
    groups: set[str] = set()
    if any(token in value for token in ("starter", "appetizer", "mezza", "vorspeise")):
        groups.add("Starters")
    if "salad" in value:
        groups.add("Salads")
    if any(token in value for token in ("grill", "smoked meat", "chicken", "fish")):
        groups.add("Grill / Meat Mains")
    if any(token in value for token in ("main", "oriental dish", "burger", "soup")):
        groups.add("Other Main Dishes")
    if "breakfast" in value or "frühstück" in value:
        groups.add("Breakfast")
    if "brunch" in value:
        groups.add("Brunch")
    if "dessert" in value or "sweet" in value:
        groups.add("Desserts")
    if any(token in value for token in (
        "drink", "tea", "coffee", "mocktail", "milkshake", "iced tea",
        "cocktail", "juice", "bar",
    )):
        groups.add("Drinks / Bar")
    if "sharing" in value or "platter" in value or "platte" in value:
        groups.add("Sharing Platters")
    if ("sandwich" in value or "shawarma" in value) and value != "warm starters & sandwiches":
        groups.add("Sandwiches")
    if "vegetarian" in value or "vegan" in value:
        groups.add("Vegetarian / Vegan")
    if "side" in value or "beilage" in value:
        groups.add("Sides")
    if "kids" in value or "children" in value:
        groups.add("Kids")
    if "special" in value:
        groups.add("Specials")
    return groups


def _availability(available, basis: str, *, observed: bool = False, **details) -> dict:
    if available is True:
        status = "observed" if observed else "confirmed"
    elif available is False:
        status = "confirmed"
    else:
        status = "unknown"
    return {"available": available, "availability_status": status, "basis": basis, **details}


def _feature_availability(features: dict, key: str, basis: str | None = None) -> dict:
    value = features.get(key)
    return _availability(value, basis or f"profile.features.{key}")


def menu_summary(data: dict) -> dict:
    items = data["menu_items"]
    category_counts: dict[str, int] = {}
    normalized = {group: {"item_count": 0, "original_categories": set()} for group in NORMALIZED_GROUPS}
    for row in items:
        category = row["category"]
        category_counts[category] = category_counts.get(category, 0) + 1
        item_groups = _normalized_groups(category)
        if data.get("slug") == "beit_fayrouz" and category == "Grill & Main Dishes":
            # Every captured item in this mixed source category is a grill,
            # meat, chicken, or fish main. Assign one primary group so the
            # same eight items are not visually double-counted as other mains.
            item_groups = {"Grill / Meat Mains"}
        if data.get("slug") == "olivenzweig" and category == "Extra Sides":
            item_groups = {"Sides"}
        if data.get("slug") == "olivenzweig" and category == "Kids & Desserts":
            item_groups = {"Desserts"} if any(
                token in row["name"].casefold() for token in ("eiscreme", "sweet", "dessert")
            ) else {"Kids"}
        tags = {tag.casefold() for tag in row.get("dietary_tags", [])}
        if tags & {"vegetarian", "vegan"}:
            item_groups.add("Vegetarian / Vegan")
        name = row["name"].casefold()
        if category.casefold() == "warm starters & sandwiches" and name in {"toschka", "maria"}:
            item_groups.add("Sandwiches")
        if any(token in name for token in ("für 2", "für zwei", "für 4", "für vier", "family", "sharing")):
            item_groups.add("Sharing Platters")
        for group in item_groups:
            normalized[group]["item_count"] += 1
            normalized[group]["original_categories"].add(category)
    normalized_output = {
        group: {
            "item_count": block["item_count"],
            "original_categories": sorted(block["original_categories"]),
            "availability_status": "observed" if block["item_count"] else "unknown",
            "classification_mode": "overlapping" if group in {"Sharing Platters", "Vegetarian / Vegan"} else "primary",
        }
        for group, block in normalized.items()
    }
    priced = sum(row.get("price_eur") is not None for row in items)
    vegetarian_tags = sum(
        bool({tag.casefold() for tag in row.get("dietary_tags", [])} & {"vegetarian", "vegan"})
        for row in items
    )
    vegetarian_category_signal = any(
        "vegetarian" in category.casefold() or "vegan" in category.casefold()
        for category in category_counts
    )
    profile = data["profile"]
    features = profile.get("features", {})
    breakfast_count = normalized_output["Breakfast"]["item_count"]
    brunch_count = normalized_output["Brunch"]["item_count"]
    sharing_count = normalized_output["Sharing Platters"]["item_count"]
    family_feature = features.get("family_bundles")
    if family_feature is True:
        family = _availability(True, "profile.features.family_bundles")
    elif sharing_count:
        family = _availability(True, "captured sharing-platter category", observed=True)
    else:
        family = _availability(None, "family/group positioning alone does not establish a bundle")
    if features.get("breakfast") is True:
        breakfast = _availability(True, "profile.features.breakfast")
    elif breakfast_count:
        breakfast = _availability(True, "captured breakfast category", observed=True)
    else:
        breakfast = _availability(None, "not established by captured sources")
    if features.get("weekend_brunch") is True:
        brunch = _availability(True, "profile.features.weekend_brunch")
    elif brunch_count:
        brunch = _availability(True, "captured brunch category", observed=True)
    else:
        brunch = _availability(None, "breakfast is not treated as brunch evidence")
    vegetarian = _availability(
        True if vegetarian_tags or vegetarian_category_signal else None,
        "explicit dietary tags" if vegetarian_tags else (
            "captured vegetarian/vegan category" if vegetarian_category_signal
            else "not established by captured sources"
        ),
        observed=not bool(vegetarian_tags),
        explicitly_tagged_item_count=vegetarian_tags,
        category_based_signal=vegetarian_category_signal,
    )
    buffet_value = features.get("buffet")
    buffet_basis = "profile.features.buffet"
    if buffet_value is None and isinstance(profile.get("buffet"), dict):
        buffet_value = profile["buffet"].get("available")
        buffet_basis = "profile.buffet.available"
    payment_methods = features.get("payment_methods")
    payment_available = True if payment_methods else (True if features.get("card_payment") is True else None)
    payment_basis = "profile.features.payment_methods" if payment_methods else (
        "profile.features.card_payment" if features.get("card_payment") is True
        else "not established by captured sources"
    )
    availability = {
        "vegetarian_vegan": vegetarian,
        "family_bundles": family,
        "breakfast": breakfast,
        "brunch": brunch,
        "catering": _feature_availability(features, "catering"),
        "events": _feature_availability(features, "events"),
        "shisha": _feature_availability(features, "shisha"),
        "buffet": _availability(buffet_value, buffet_basis),
        "parking": _feature_availability(features, "parking_available"),
        "reservations": _feature_availability(features, "reservations"),
        "payment": _availability(payment_available, payment_basis, payment_methods=payment_methods),
        "delivery": _feature_availability(features, "delivery"),
    }
    return {
        "menu_item_count": len(items), "category_count": len(category_counts),
        "categories": sorted(category_counts),
        "original_category_counts": dict(sorted(category_counts.items())),
        "normalized_comparison_groups": normalized_output,
        "classification_mode": "overlapping",
        "classification_warning": "Primary menu groups are separated where possible; Sharing Platters and Vegetarian / Vegan are overlapping attributes. Never sum normalized group counts to reconstruct the menu total.",
        "priced_items": priced, "price_coverage_pct": round(priced / len(items) * 100, 2) if items else 0.0,
        "starters": normalized_output["Starters"]["item_count"],
        "grills": normalized_output["Grill / Meat Mains"]["item_count"],
        "main_dishes": normalized_output["Other Main Dishes"]["item_count"],
        "breakfast_brunch": breakfast_count + brunch_count,
        "dessert": normalized_output["Desserts"]["item_count"],
        "drinks": normalized_output["Drinks / Bar"]["item_count"],
        "mocktails": sum("mocktail" in row["category"].casefold() for row in items),
        "sharing_platters": sharing_count,
        "vegetarian_tagged_items": vegetarian_tags,
        "family_bundles": family,
        "premium_anchors_over_30_eur": sum((row.get("price_eur") or 0) >= 30 for row in items),
        "value_items_under_10_eur": sum((row.get("price_eur") or 999) < 10 for row in items),
        "signature_or_platform_signaled_items": sum(bool(row.get("platform_signals")) for row in items),
        "breakfast_available": breakfast,
        "brunch_available": brunch,
        "vegetarian_vegan_availability": vegetarian,
        "availability": availability,
        "buffet": availability["buffet"], "brunch": brunch,
        "shisha": availability["shisha"], "catering": availability["catering"], "events": availability["events"],
        "source_aware_note": "Counts reflect the stored September 2026 catalog snapshot, not an assertion of permanent completeness.",
        "normalized_groups_note": "Groups are non-exclusive comparison views; original source categories remain available and group totals must not be summed.",
    }


def comparable_prices(restaurants: dict) -> list[dict]:
    rows = []
    for basket, mappings in PRICE_MATCHES.items():
        for slug, (name, confidence) in mappings.items():
            item = next((row for row in restaurants[slug]["menu_items"] if row["name"] == name), None)
            if not item: continue
            rows.append({
                "comparison_item": basket, "restaurant": slug, "matched_item": name,
                "price": item.get("price_eur"), "currency": item.get("currency", "EUR"),
                "source": item.get("source") or "validated_local_baseline_menu",
                "source_date": item.get("source_date") or "not recorded (pre-existing baseline)",
                "match_confidence": confidence,
                "notes": "Portion/service-format differences may remain; no match is treated as identical unless confidence is high.",
            })
    return rows


def digital_footprint(data: dict) -> dict:
    p = data["profile"]; f = p.get("features", {})
    summary = menu_summary(data)
    return {
        "official_website": p.get("website"), "menu_urls": p.get("menu_urls", []),
        "menu_completeness": "stored_snapshot_with_prices" if data["menu_items"] else "unknown",
        "google_presence": bool(p.get("google_maps_url")), "online_reservation": _feature_availability(f, "reservations"),
        "delivery": _feature_availability(f, "delivery"), "takeaway": _feature_availability(f, "takeaway"),
        "catering": _feature_availability(f, "catering"), "events": _feature_availability(f, "events"),
        "social_media": p.get("social_links", []),
        "opening_hours": p.get("opening_hours"), "payment": f.get("payment_methods"),
        "payment_availability": summary["availability"]["payment"],
        "parking": _feature_availability(f, "parking_available"),
        "outdoor_seating": _feature_availability(f, "outdoor_seating"),
        "breakfast_brunch_buffet": {
            "breakfast": summary["breakfast_available"],
            "brunch": summary["brunch_available"],
            "buffet": summary["availability"]["buffet"],
        },
        "bar_drinks": _feature_availability(f, "bar_drinks"), "shisha": _feature_availability(f, "shisha"),
    }


def kitchen_bar(data: dict, recent_topics: list[dict]) -> dict:
    menu = menu_summary(data)
    def topic(name): return next((row for row in recent_topics if row["internal_topic"] == name), None)
    return {
        "food_review_attention": topic("Food"), "drink_review_attention": topic("Drinks"),
        "food_menu_size": menu["menu_item_count"] - menu["drinks"], "drink_menu_size": menu["drinks"],
        "signature_drinks": [row["name"] for row in data["menu_items"] if "Drinks / Bar" in _normalized_groups(row["category"]) and row.get("platform_signals")],
        "mocktail_program_item_count": menu["mocktails"],
        "guardrail": "Review attention is not sales and no revenue inference is made.",
    }


def _analysis_menu(items: list[dict]) -> list[dict]:
    """Return one canonical row per dish name for review-text matching.

    A captured menu can legitimately list the same item in its main and brunch
    sections at different prices. Those rows remain in menu counts, but feeding
    exact duplicate canonical names to the matcher would create false ambiguity.
    The first (main-menu) observation is therefore used for text matching only.
    """
    seen: set[str] = set()
    result = []
    for row in items:
        key = row["name"].casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def tasting_shortlist(slug: str, data: dict, cutoff_period: dict, recent_period: dict) -> list[dict]:
    all_rows = reviews_in_period(data["prepared"]["reviews"], cutoff_period)
    recent_rows = reviews_in_period(data["prepared"]["reviews"], recent_period)
    analysis_menu = _analysis_menu(data["menu_items"])
    dishes, *_ = analyze_dishes_with_evidence(all_rows, analysis_menu)
    recent, *_ = analyze_dishes_with_evidence(recent_rows, analysis_menu)
    by_recent = {row["dish"]: row for row in recent}
    by_menu = {row["name"]: row for row in analysis_menu}
    candidates = []
    for row in dishes:
        menu = by_menu[row["dish"]]; signal = menu.get("platform_signals", [])
        recent_count = by_recent.get(row["dish"], {}).get("reviews_mentioning", 0)
        if not row["reviews_mentioning"] and not signal: continue
        score = row["positive_reviews"] * 3 + row["reviews_mentioning"] + recent_count * 2 + (3 if signal else 0)
        reasons = []
        if row["reviews_mentioning"]: reasons.append("Google review discussion")
        if row["positive_reviews"]: reasons.append("positive Google review mentions")
        if recent_count: reasons.append("recent Google review mentions")
        if signal: reasons.append("separate platform/signature signal")
        candidates.append((score, {
            "restaurant": slug, "dish": row["dish"], "reason_selected": "; ".join(reasons),
            "google_review_mentions": row["reviews_mentioning"], "positive_mentions": row["positive_reviews"],
            "positive_share_pct": round(row["positive_reviews"] / row["reviews_mentioning"] * 100, 2) if row["reviews_mentioning"] else 0.0,
            "negative_mentions": row["negative_reviews"], "recent_mentions": recent_count,
            "platform_signal": signal or None, "menu_price": menu.get("price_eur"), "currency": menu.get("currency", "EUR"),
            "evidence_level": evidence_level(row["reviews_mentioning"]),
            "interpretation": "Field-research candidate; not a best-seller or most-ordered claim.",
        }))
    return [row for _score, row in sorted(candidates, key=lambda pair: pair[0], reverse=True)[:5]]


def dish_favourite_signals(data: dict, cutoff_period: dict) -> dict:
    """Reuse existing dish ranking logic after enforcing the common cutoff."""
    rows = reviews_in_period(data["prepared"]["reviews"], cutoff_period)
    dishes, *_ = analyze_dishes_with_evidence(rows, _analysis_menu(data["menu_items"]))
    rankings = build_dish_rankings(dishes)
    return {
        "through_cutoff": cutoff_period["end"],
        "most_discussed": rankings.get("most_discussed_dishes", [])[:10],
        "most_positively_discussed": rankings.get("most_praised_dishes", [])[:10],
        "negatively_discussed": rankings.get("most_criticized_dishes", [])[:10],
        "terminology": "Customer favourite signals, not sales or ordering data.",
    }
