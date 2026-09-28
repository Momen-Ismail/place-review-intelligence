"""Ingest the supplied 2026 competitor research without collecting reviews.

The PDF is a dated research snapshot, not an instruction source.  It is used
to complete/cross-check local menu and profile inputs while preserving newer
or higher-authority observations and recording conflicts explicitly.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PDF_NAME = "Al_Assiel_Bonn_Competitor_Intelligence_Report_2026.pdf"
PDF_SHA256 = "0bb673506e50bf94a8b48b6f1bbbb7707d5c550e0480fc0723f04f48cbae4bca"
PDF_SNAPSHOT_DATE = "2026-09-20"
INGESTED_AT = "2026-09-23"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_record(used_for: list[str], pages: list[int], conflicts: list[str] | None = None) -> dict:
    return {
        "source_name": "Supplied competitive-intelligence PDF",
        "source_type": "supplied_research",
        "url": None,
        "document_name": PDF_NAME,
        "document_sha256": PDF_SHA256,
        "source_snapshot_date": PDF_SNAPSHOT_DATE,
        "retrieved_at": INGESTED_AT,
        "used_for": used_for,
        "page_references": pages,
        "confidence": "medium",
        "authority_level": "supporting",
        "notes": "User-supplied synthesized research; used below current official/owned/Google/current-platform sources.",
        "conflicts": conflicts or [],
    }


def upsert_pdf_source(register: dict, row: dict) -> None:
    register["sources"] = [
        source for source in register.get("sources", [])
        if source.get("source_type") != "supplied_research"
    ] + [row]


def menu_item(category: str, name: str, price: float | None, *, brunch: bool = False,
              aliases: tuple[str, ...] = (), tags: tuple[str, ...] = ()) -> dict:
    source = "official_brunch_menu_2026_09_21" if brunch else "official_menu_2026_09_21"
    return {
        "category": category,
        "name": name,
        "english_name": name,
        "description": None,
        "price_eur": price,
        "price": price,
        "currency": "EUR",
        "dietary_tags": list(tags),
        "platform_signals": [],
        "aliases": list(dict.fromkeys(aliases)),
        "source": source,
        "source_date": "2026-09-21",
        "source_confidence": "high",
        "source_support": [{
            "source": "supplied_competitive_intelligence_pdf",
            "snapshot_date": PDF_SNAPSHOT_DATE,
            "confidence": "medium",
        }],
    }


def olivenzweig_items() -> list[dict]:
    rows: list[dict] = []

    def add(category, values, *, brunch=False):
        for name, price in values:
            rows.append(menu_item(category, name, price, brunch=brunch))

    add("Salads", [
        ("Fattoush", 9.50), ("Auberginen Fattoush", 9.50),
        ("Tabouleh", 9.50), ("Orientalischer Salat", 9.50),
    ])
    add("Cold Starters", [
        ("Hummus", 7.90), ("Hummus Beiruty", 7.90), ("Mutabbal", 7.90),
        ("Baba Ghanoush", 7.90), ("Muhammara", 7.90), ("Yalangi (5 Stk.)", 8.50),
        ("Frittierter Blumenkohl Tahini-Dip", 8.90),
        ("Gebratene Auberginen mit Tahini Dip", 8.90), ("Harak Osbao", 12.90),
        ("Knoblauchcreme", 4.90), ("Mixed Pickles", 4.90),
        ("Vorspeise (5 Platte)", 24.90),
    ])
    add("Warm Starters & Sandwiches", [
        ("Hummus mit Fleisch", 14.00), ("Hähnchenflügel im Tontopf", 12.90),
        ("Käse-Sambousek (4)", 8.90), ("Spinat-Sambousek (4)", 7.90),
        ("Fleisch-Sambousek (4)", 8.90), ("M'sakhan Röllchen (3)", 9.90),
        ("Frittierte Kibbeh (3)", 9.90), ("Gegrillte Kibbeh (1)", 5.90),
        ("Gebratene Hähnchenleber", 9.90), ("Toschka", 13.90),
        ("Maria", 12.90), ("French fries", 5.90),
        ("Scharfe Kartoffeln", 7.90), ("Falafel-Teller", 11.90),
    ])
    add("Grill", [
        ("Aleppo Kebab", 18.90), ("Kirsch Kebab", 24.90),
        ("Ka'b Elghazal Kebab", 24.90), ("Shish Tawook", 19.90),
        ("Gegrillte Lammspieße", 24.90), ("Lammkotelett", 28.90),
        ("Gemischter Grillteller 1 Person", 28.50),
        ("Gemischter Grillteller 2 Personen", 55.90),
        ("Gegrilltes Hähnchen", 16.90), ("Gegrillter Fisch Dorade", 29.50),
    ])
    add("Smoked Meat", [
        ("Lammhaxe", 29.90), ("Lammnacken", 38.50), ("Rinderkotelett", 34.50),
        ("Lammschulter für 2", 69.50), ("Geräucherte Platte für 2", 69.50),
        ("Geräucherte Platte für 4", 120.00),
    ])
    add("Extra Sides", [
        ("Süßkartoffel", 6.90), ("French fries (Beilage)", 5.90), ("Reis", 5.90),
        ("Knoblauchcreme (Beilage)", 4.90), ("Brot (4 Stk.)", 3.00),
    ])
    add("Kids & Desserts", [
        ("Crispy chicken (3 Stück)", 12.90), ("Arabische Eiscreme", 4.90),
        ("Daily sweets", None),
    ])
    add("Tea", [
        ("Schwarztee", 4.20), ("Frischeminz-Schwarztee", 4.20),
        ("Kardamom-Schwarztee", 4.20), ("Zimt Orangen Schwarztee", 3.70),
        ("Ingwer-Zitronen-Schwarztee", 4.90), ("Rosen Schwarztee", 4.20),
        ("Grüner Tee", 4.90), ("Kamillentee", 4.90),
        ("Frischer Minztee", 4.90), ("Frischer Ingwertee", 4.90),
    ])
    add("Coffee", [
        ("Espresso", 3.70), ("Doppio", 4.50), ("Arabisch Kaffee", 3.70),
        ("Kaffee Creme", 4.90), ("Cappuccino", 4.90), ("Schokochino", 4.90),
        ("Latte Macchiato", 4.90),
    ])
    add("Cold Drinks", [
        ("Coca-Cola 0.2l", 3.50), ("Coca-Cola Zero 0.2l", 3.50),
        ("Fanta 0.2l", 3.50), ("Sprite 0.2l", 3.50), ("Ayran", 3.50),
        ("Ginger Ale 0.2l", 4.20), ("Wasser 0.2l", 3.50), ("Wasser 0.7l", 7.90),
        ("Orangensaft", 4.90), ("Apfelsaft", 4.90), ("Mangosaft", 4.90),
        ("Ananassaft", 4.90), ("Fritz-Apfelschorle", 4.20),
        ("Bitburger Alkoholfrei", 4.90), ("Weissbräu Alkoholfrei", 4.90),
    ])
    add("Home-made Iced Tea", [
        ("Himbeere Limette", 5.90), ("Mango Maracuja", 5.90),
        ("Apfel Limette", 5.90), ("Zitrone Limette", 5.90),
        ("Wassermelone Limette", 5.90),
    ])
    add("Mocktails", [
        ("Mojito Classic", 7.90), ("Mojito Strawberry", 7.90),
        ("Mojito Mango", 7.90), ("Hugo", 7.90), ("Swimmingpool", 7.90),
        ("Ipanema", 7.90), ("Polo", 7.90),
    ])
    add("Milkshakes", [
        ("Erdbeer-Milkshake", 8.90), ("Vanille-Milkshake", 8.90),
        ("Schoko-Milkshake", 8.90), ("Pisto-Milkshake", 8.90),
    ])
    add("Weekend Brunch", [
        ("Frühstücksteller für eine Person", 20.00),
        ("Frühstücksteller für zwei Personen", 38.00), ("Wintersuppe", 6.50),
        ("Foul", 11.90), ("Hummus", 8.90), ("Falafel", 9.50),
        ("Eier mit Avocado", 11.90), ("Omelett", 6.90), ("Labneh", 6.00),
        ("Gemüseteller", 4.90), ("Käseteller", 9.90), ("Shakshuka", 11.90),
        ("Muhammara", 7.90), ("Fatteh", 13.90), ("Manakish mit Fleisch", 6.00),
        ("Manakish mit Käse", 3.90), ("Manakish mit Zaatar", 3.90),
        ("Gemischter Manakish-Teller", 25.00), ("Mamounieh", 4.90),
        ("Sahlab", 4.90), ("Ayran", 2.90), ("Tee mit frischer Minze", 4.70),
        ("Schwarzer Tee", 3.70), ("Frischer Orangensaft", 5.90),
        ("Ayran mit Minze", 3.50), ("Kaffee mit Kardamom", 3.50),
    ], brunch=True)

    aliases = {
        "Fattoush": ["fattush", "فتوش"], "Tabouleh": ["tabbouleh", "tabouli", "تبولة"],
        "Hummus": ["humus", "houmous", "حمص"], "Mutabbal": ["moutabal", "متبل"],
        "Baba Ghanoush": ["baba ganoush", "بابا غنوج"],
        "Shish Tawook": ["shish taouk", "chicken skewer"],
        "Lammkotelett": ["lamb chops", "lamb chop"],
        "Gemischter Grillteller 1 Person": ["mixed grill platter", "mixed grill"],
        "Gegrillter Fisch Dorade": ["dorade", "sea bream"],
        "Falafel-Teller": ["falafel plate", "falafel platter"],
        "Arabische Eiscreme": ["arabic ice cream"], "Schwarztee": ["black tea", "tea"],
        "Pisto-Milkshake": ["pistachio milkshake", "pisto milkshake"],
        "Frühstücksteller für eine Person": ["breakfast platter for one", "brunch platter"],
        "Frühstücksteller für zwei Personen": ["breakfast platter for two", "brunch for two"],
    }
    vegetarian = {
        "Fattoush", "Auberginen Fattoush", "Tabouleh", "Orientalischer Salat",
        "Hummus", "Hummus Beiruty", "Mutabbal", "Baba Ghanoush", "Muhammara",
        "Yalangi (5 Stk.)", "Frittierter Blumenkohl Tahini-Dip",
        "Gebratene Auberginen mit Tahini Dip", "Harak Osbao", "Mixed Pickles",
        "Spinat-Sambousek (4)", "French fries", "Scharfe Kartoffeln", "Falafel-Teller",
        "Foul", "Falafel", "Eier mit Avocado", "Omelett", "Labneh", "Gemüseteller",
        "Käseteller", "Shakshuka", "Fatteh", "Manakish mit Käse", "Manakish mit Zaatar",
        "Gemischter Manakish-Teller", "Mamounieh",
    }
    vegan = {
        "Hummus", "Hummus Beiruty", "Baba Ghanoush", "Muhammara", "Yalangi (5 Stk.)",
        "Frittierter Blumenkohl Tahini-Dip", "Harak Osbao", "Mixed Pickles",
        "Spinat-Sambousek (4)", "French fries", "Scharfe Kartoffeln", "Falafel-Teller",
        "Foul", "Falafel", "Manakish mit Zaatar",
    }
    for row in rows:
        row["aliases"] = list(dict.fromkeys(row["aliases"] + aliases.get(row["name"], [])))
        if row["name"] in vegetarian:
            row["dietary_tags"] = ["vegan"] if row["name"] in vegan else ["vegetarian"]
    for row in rows:
        if row["name"] in {"Frühstücksteller für eine Person", "Frühstücksteller für zwei Personen"}:
            row["platform_signals"] = ["official_signature_positioning"]
    seen_names: set[str] = set()
    for row in rows:
        original_name = row["name"]
        key = original_name.casefold()
        if key in seen_names:
            row["original_name"] = original_name
            row["name"] = f"{original_name} (Weekend Brunch)"
            row["english_name"] = row["name"]
            row["aliases"] = [f"weekend brunch {original_name}"]
            row["canonicalization_note"] = "Analytical key disambiguated; the printed menu name is preserved in original_name."
        seen_names.add(key)
    assert len(rows) == 128, len(rows)
    return rows


def enrich_olivenzweig() -> tuple[int, int, int, int]:
    base = ROOT / "businesses/restaurants/olivenzweig/inputs"
    catalog = load(base / "menu_catalog.json")
    before_items = len(catalog["items"])
    before_categories = len({row["category"] for row in catalog["items"]})
    catalog["items"] = olivenzweig_items()
    catalog["categories"] = sorted({row["category"] for row in catalog["items"]})
    catalog["snapshot_date"] = "2026-09-21"
    catalog["source_completion"] = {
        "supporting_document": PDF_NAME,
        "supporting_document_snapshot_date": PDF_SNAPSHOT_DATE,
        "note": "Full official main (102) and weekend-brunch (26) menu inventory cross-checked against supplied research PDF.",
    }
    save(base / "menu_catalog.json", catalog)

    register = load(base / "source_register.json")
    upsert_pdf_source(register, source_record(
        ["menu/profile cross-check", "main-menu completeness", "weekend-brunch completeness", "pricing/positioning notes"],
        list(range(11, 17)),
        ["Official-site footer/hour wording conflicts remain governed by the newer official source register."],
    ))
    save(base / "source_register.json", register)
    save(base / "source_snapshots/competitive_intelligence_pdf_2026_09_20.json", {
        "restaurant": "Olivenzweig Restaurant",
        "document": PDF_NAME,
        "document_sha256": PDF_SHA256,
        "snapshot_date": PDF_SNAPSHOT_DATE,
        "ingested_at": INGESTED_AT,
        "page_references": list(range(11, 17)),
        "captured_counts": {"main_menu_entries": 102, "weekend_brunch_entries": 26, "total_entries": 128},
        "profile_cross_check": {"weekend_brunch": "Saturday and Sunday, 12:00-16:00", "positioning": "Levantine sit-down; mezze, grill, smoked meat, broad non-alcoholic drinks"},
        "authority_note": "Supporting synthesized research; current official sources retain priority.",
    })
    refresh_snapshot(base)
    return before_items, before_categories, len(catalog["items"]), len(catalog["categories"])


def al_safa_new_items() -> list[dict]:
    def row(category, name, price, source, *, aliases=(), conflict=None):
        value = {
            "category": category, "name": name, "english_name": name, "description": None,
            "price_eur": price, "price": price, "currency": "EUR", "dietary_tags": [],
            "platform_signals": [], "aliases": list(aliases), "source": source,
            "source_date": "2026-04-27" if source == "speisekarte_de_menu_2026_04_27" else "date_not_stated",
            "source_confidence": "medium",
            "source_support": [{"source": "supplied_competitive_intelligence_pdf", "snapshot_date": PDF_SNAPSHOT_DATE, "confidence": "medium"}],
        }
        if conflict:
            value["price_conflict"] = conflict
        return value
    return [
        row("Sandwiches", "Türkische Pizza mit Salat", 6.00, "speisekarte_de_menu_2026_04_27", aliases=("turkish pizza",), conflict={"supplied_physical_menu_price_eur": 5.00, "resolution": "newer dated public listing retained"}),
        row("Main Dishes", "Gefüllte Auberginen", 6.50, "supplied_physical_menu_date_unknown", aliases=("stuffed eggplant",)),
        row("Main Dishes", "Bohnen", 7.50, "speisekarte_de_menu_2026_04_27", aliases=("beans",)),
        row("Grill", "Lammteller - 2 Lammspieße", 15.00, "speisekarte_de_menu_2026_04_27", aliases=("lamb plate", "lamb skewers")),
        row("Chicken", "Hähnchenkeule - 2 ohne Knochen", 13.50, "speisekarte_de_menu_2026_04_27", aliases=("boneless chicken thigh",)),
        row("Grill", "Lammkoteletts - 4 Stück", 17.00, "speisekarte_de_menu_2026_04_27", aliases=("lamb chops",), conflict={"supplied_physical_menu_price_eur": 16.50, "resolution": "newer dated public listing retained"}),
        row("Main Dishes", "Okra", None, "speisekarte_de_menu_2026_04_27", aliases=("okra stew",)),
        row("Chicken", "Chicken Nuggets mit Pommes", None, "speisekarte_de_menu_2026_04_27", aliases=("chicken nuggets",)),
        row("Sandwiches", "Hamburger mit Salat", None, "speisekarte_de_menu_2026_04_27", aliases=("hamburger",)),
        row("Chicken", "Hähnchen mit Kartoffeln", None, "speisekarte_de_menu_2026_04_27", aliases=("chicken with potatoes",)),
        row("Main Dishes", "Koba Teller", None, "speisekarte_de_menu_2026_04_27", aliases=("kibbeh plate",)),
        row("Main Dishes", "Dolma (nur samstags)", None, "speisekarte_de_menu_2026_04_27", aliases=("dolma", "stuffed vegetables")),
        row("Grill", "Gemischter Al Safa Teller", 40.00, "supplied_physical_menu_date_unknown", aliases=("al safa mixed plate", "mixed offal grill")),
    ]


def enrich_al_safa() -> tuple[int, int, int, int]:
    base = ROOT / "businesses/restaurants/al_safa/inputs"
    catalog = load(base / "menu_catalog.json")
    before_items = len(catalog["items"])
    before_categories = len({row["category"] for row in catalog["items"]})
    for row in catalog["items"]:
        support = row.setdefault("source_support", [])
        if not any(entry.get("source") == "supplied_competitive_intelligence_pdf" for entry in support):
            support.append({
                "source": "supplied_competitive_intelligence_pdf",
                "snapshot_date": PDF_SNAPSHOT_DATE,
                "confidence": "medium",
                "note": "Retained when not contradicted by higher-priority/newer evidence; catalog remains a captured union, not a complete official menu.",
            })
    by_name = {row["name"]: row for row in catalog["items"]}
    price_observations = {
        "Falafel Teller": (10.00, "supplied physical menu; date not stated"),
        "Linsensuppe": (5.50, "supplied physical menu; date not stated"),
        "Döner Sandwich": (7.00, "supplied physical menu; date not stated"),
        "Döner Teller mit Beilage": (11.00, "supplied physical menu; date not stated"),
        "Gemischter Grillteller mit Beilage": (16.50, "supplied physical menu; date not stated"),
        "Dorade mit Reis": (18.50, "supplied physical menu; date not stated"),
        "Soft Drink 0.33l": (2.80, "dated public listing 2026-04-27"),
        "Sac Kawerma": (16.00, "dated public listing 2026-04-27"),
        "Kosi Lammhaxe": (20.00, "dated public listing 2026-04-27"),
    }
    for name, (observed_price, source_note) in price_observations.items():
        if name not in by_name:
            continue
        current = by_name[name]
        observations = current.setdefault("price_observations", [])
        observation = {
            "price_eur": observed_price,
            "source": source_note,
            "captured_in": PDF_NAME,
            "pdf_snapshot_date": PDF_SNAPSHOT_DATE,
        }
        if observation not in observations:
            observations.append(observation)
        if current.get("price_eur") != observed_price:
            conflict = {
                "retained_price_eur": current.get("price_eur"),
                "alternate_price_eur": observed_price,
                "resolution": "Existing 2026-09-21 source observation retained; PDF evidence preserved separately rather than silently overwriting it.",
            }
            conflicts = current.setdefault("price_conflicts", [])
            if conflict not in conflicts:
                conflicts.append(conflict)
    existing_names = {row["name"] for row in catalog["items"]}
    catalog["items"].extend(row for row in al_safa_new_items() if row["name"] not in existing_names)
    catalog["categories"] = sorted({row["category"] for row in catalog["items"]})
    catalog["source_completion"] = {
        "supporting_document": PDF_NAME,
        "supporting_document_snapshot_date": PDF_SNAPSHOT_DATE,
        "note": "Captured union of the existing 2026-09-21 public snapshot, 24-item dated public listing, and selected physical-menu evidence; conflicts remain item-level.",
    }
    save(base / "menu_catalog.json", catalog)

    profile = load(base / "restaurant_profile.json")
    profile["website"] = "https://alsafarestaurant.com/"
    profile["menu_urls"] = ["https://www.speisekarte.de/bonn/restaurant/al_safa_restaurant/speisekarte"]
    profile["features"].update({
        "reservations": True,
        "payment_methods": ["cash"],
        "wheelchair_accessible_seating": True,
        "family_groups": True,
        "bar_drinks": None,
    })
    profile["distinctive_offer"] = [
        "family-oriented, high-volume value positioning (supporting supplied research)",
        "generous portions and complimentary items noted in supplied research",
        "grill, daily dishes, and a large mixed Al Safa platter",
    ]
    save(base / "restaurant_profile.json", profile)

    register = load(base / "source_register.json")
    register["sources"] = [
        row for row in register["sources"]
        if row.get("source_name") not in {"Al Safa official website", "Speisekarte.de Al Safa menu"}
    ]
    register["sources"][0].update({
        "source_name": "Legacy Al Safa public menu snapshot",
        "source_type": "secondary_restaurant_menu_snapshot",
        "confidence": "low",
        "authority_level": "low",
        "notes": "Ownership/current maintenance of alsafa-restaurant.eu was not established; retained as a dated catalog observation, not treated as the official site.",
    })
    register["sources"].insert(0, {
        "source_name": "Al Safa official website",
        "source_type": "official_restaurant_website",
        "url": "https://alsafarestaurant.com/",
        "retrieved_at": PDF_SNAPSHOT_DATE,
        "used_for": ["identity", "since-1998 positioning"],
        "confidence": "medium", "authority_level": "high",
        "notes": "Minimal site; no complete crawlable menu represented in the supplied research.", "conflicts": [],
    })
    register["sources"].insert(1, {
        "source_name": "Speisekarte.de Al Safa menu",
        "source_type": "current_menu_listing",
        "url": "https://www.speisekarte.de/bonn/restaurant/al_safa_restaurant/speisekarte",
        "retrieved_at": PDF_SNAPSHOT_DATE,
        "source_snapshot_date": "2026-04-27",
        "used_for": ["24 current public menu entries", "selected visible prices", "reservations/services cross-check"],
        "confidence": "medium", "authority_level": "medium",
        "notes": "Public listing is explicitly dated 2026-04-27 and omits prices for several items.",
        "conflicts": ["Some prices differ from the undated physical-menu extraction; the dated public value is preferred when both are present."],
    })
    for row in register["sources"]:
        if row.get("source_type") == "supplied_physical_menu":
            row.update({
                "retrieved_at": INGESTED_AT, "used_for": ["selected physical-menu prices and item cross-check"],
                "confidence": "medium", "authority_level": "supporting",
                "notes": "Physical-menu observations embedded in the supplied research PDF; menu date not stated.",
                "conflicts": ["Türkische Pizza: physical €5.00 vs dated public listing €6.00.", "Lammkoteletts: physical €16.50 vs dated public listing €17.00."],
            })
    upsert_pdf_source(register, source_record(
        ["profile correction", "24-entry public-menu cross-check", "10 physical-menu price observations", "positioning/service notes"],
        [21, 22],
        ["Türkische Pizza €5 physical vs €6 dated public listing; €6 retained.", "Lammkoteletts €16.50 physical vs €17 dated public listing; €17 retained."],
    ))
    save(base / "source_register.json", register)
    save(base / "source_snapshots/competitive_intelligence_pdf_2026_09_20.json", {
        "restaurant": "Al Safa Restaurant", "document": PDF_NAME,
        "document_sha256": PDF_SHA256, "snapshot_date": PDF_SNAPSHOT_DATE,
        "ingested_at": INGESTED_AT, "page_references": [21, 22],
        "captured_counts": {"dated_public_listing_entries": 24, "physical_menu_price_observations": 10},
        "profile_cross_check": {
            "official_website": "https://alsafarestaurant.com/", "hours": "daily around 12:00-23:00",
            "services": ["terrace/outdoor seating", "takeaway", "dine-in", "reservations", "wheelchair-accessible seating"],
            "payment": "cash payment reported by a current listing",
            "positioning": "family-oriented, high-volume/value competitor",
        },
        "conflicts": [
            {"item": "Türkische Pizza", "physical_price_eur": 5.00, "dated_public_price_eur": 6.00, "resolution": "dated public price retained"},
            {"item": "Lammkoteletts", "physical_price_eur": 16.50, "dated_public_price_eur": 17.00, "resolution": "dated public price retained"},
        ],
        "authority_note": "Supporting synthesized research; no value silently overwrites a newer/higher-authority observation.",
    })
    refresh_snapshot(base)
    return before_items, before_categories, len(catalog["items"]), len(catalog["categories"])


def enrich_al_assiel() -> None:
    base = ROOT / "businesses/restaurants/al_assiel/inputs"
    profile = load(base / "restaurant_profile.json")
    profile.setdefault("features", {}).update({
        "breakfast": True,
        "catering": True,
        "events": True,
        "bar_drinks": True,
    })
    profile["website"] = profile.get("website") or "https://www.alassiel.de/"
    profile["menu_urls"] = profile.get("menu_urls") or ["https://www.alassiel.de/"]
    profile["profile_enrichment"] = {
        "source": PDF_NAME,
        "source_snapshot_date": PDF_SNAPSHOT_DATE,
        "confidence": "medium",
        "note": "Breakfast, catering/events, website, and bar/drinks were cross-checked; validated menu catalog and review analysis were not changed.",
    }
    save(base / "restaurant_profile.json", profile)
    register_path = base / "source_register.json"
    if register_path.exists():
        register = load(register_path)
    else:
        register = {
            "restaurant": "Al Assiel Restaurant & Shisha Lounge",
            "snapshot_date": INGESTED_AT,
            "sources": [{
                "source_name": "Existing validated local Al Assiel inputs",
                "source_type": "validated_project_input", "url": None, "retrieved_at": None,
                "used_for": ["baseline profile", "validated 118-item menu catalog"],
                "confidence": "high", "authority_level": "high",
                "notes": "Pre-existing baseline remains unchanged by the PDF ingestion.", "conflicts": [],
            }],
        }
    upsert_pdf_source(register, source_record(
        ["profile/menu cross-check only", "catering and events evidence", "drink-category cross-check"],
        list(range(4, 11)),
        ["PDF's broader captured inventory is not substituted for the validated local 118-item catalog.", "Validated comparison drink count remains Cold Drinks 15 + Hot Drinks 10 + Cocktails & Juices 9 = 34."],
    ))
    save(register_path, register)
    save(base / "source_snapshots/competitive_intelligence_pdf_2026_09_20.json", {
        "restaurant": "Al Assiel Restaurant & Shisha Lounge", "document": PDF_NAME,
        "document_sha256": PDF_SHA256, "snapshot_date": PDF_SNAPSHOT_DATE,
        "ingested_at": INGESTED_AT, "page_references": list(range(4, 11)),
        "use": "cross-check only; validated local profile and 118-item catalog were not changed",
        "validated_comparison_drink_categories": {"Cold Drinks": 15, "Hot Drinks": 10, "Cocktails & Juices": 9, "Drinks / Bar": 34},
        "authority_note": "Supporting synthesized research; current official/owned local inputs retain priority.",
    })


def refresh_snapshot(base: Path) -> None:
    profile = load(base / "restaurant_profile.json")
    catalog = load(base / "menu_catalog.json")
    items = catalog["items"]
    register = load(base / "source_register.json")
    save(base / "source_snapshots/current_web_extract.json", {
        "restaurant": profile["restaurant_name"], "snapshot_date": profile.get("snapshot_date"),
        "profile_claims": {
            "address": profile["address"], "opening_hours": profile["opening_hours"],
            "features": profile["features"], "distinctive_offer": profile["distinctive_offer"],
        },
        "menu_summary": {
            "categories": sorted({row["category"] for row in items}),
            "item_count": len(items), "priced_items": sum(row.get("price_eur") is not None for row in items),
        },
        "source_urls": [row["url"] for row in register["sources"] if row.get("url")],
        "refresh_note": "Local September 2026 snapshot; source priority and item-level conflicts remain explicit.",
    })


def main() -> None:
    olive = enrich_olivenzweig()
    safa = enrich_al_safa()
    enrich_al_assiel()
    print(f"Olivenzweig items/categories: {olive[0]}/{olive[1]} -> {olive[2]}/{olive[3]}")
    print(f"Al Safa items/categories: {safa[0]}/{safa[1]} -> {safa[2]}/{safa[3]}")
    print("Al Assiel validated menu unchanged; PDF source registered for cross-check only")


if __name__ == "__main__":
    main()
