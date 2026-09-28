"""Create source-aware September 2026 competitor input snapshots.

This is intentionally data-only scaffolding: it reuses the existing restaurant
pipeline and does not collect reviews or alter any SQLite database.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RETRIEVED = "2026-09-21"

MAPS = {
    "olivenzweig": "https://www.google.com/maps/place/Olivenzweig+Restaurant/@50.7359368,7.0950361,17z/data=!4m8!3m7!1s0x47bee1801c84e23d:0xd66d4911494975e3!8m2!3d50.7359368!4d7.0950361!9m1!1b1!16s%2Fg%2F11y5vj5vwp",
    "al_safa": "https://www.google.com/maps/place/Al+Safa+Restaurant/@50.6848367,7.1569974,17z/data=!4m8!3m7!1s0x47bee46d93a79a23:0x591d8b3a13468bfd!8m2!3d50.6848367!4d7.1569974!9m1!1b1!16s%2Fg%2F11cn2tr8qd",
    "beit_fayrouz": "https://www.google.com/maps/place/Beit+Fayrouz+Restaurant/@50.6851301,7.1533365,17z/data=!4m8!3m7!1s0x47bee51e12748a15:0xb6bfc21bcfbce636!8m2!3d50.6851301!4d7.1533365!9m1!1b1!16s%2Fg%2F11nc0xvtdy",
}


def item(category, name, price, aliases=(), description=None, *, source, tags=(), signal=None):
    return {
        "category": category,
        "name": name,
        "english_name": name,
        "description": description,
        "price_eur": price,
        "price": price,
        "currency": "EUR",
        "dietary_tags": list(tags),
        "platform_signals": list(signal or []),
        "aliases": list(dict.fromkeys(aliases)),
        "source": source,
        "source_date": RETRIEVED,
        "source_confidence": "high" if "official" in source else "medium",
    }


def source(name, kind, url, used_for, confidence, notes=None, conflicts=None):
    return {
        "source_name": name,
        "source_type": kind,
        "url": url,
        "retrieved_at": RETRIEVED,
        "used_for": used_for,
        "confidence": confidence,
        "authority_level": confidence,
        "notes": notes,
        "conflicts": conflicts or [],
    }


def save(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def management_observations():
    return {
        "metadata": {
            "source_type": "human_maintained_internal_input",
            "review_derived": False,
            "purpose": "No competitor internal observations supplied; section retained for pipeline compatibility.",
        }
    }


def common_topics(optional=()):
    baseline = json.loads(
        (ROOT / "businesses/restaurants/al_assiel/inputs/restaurant_profile.json").read_text(encoding="utf-8")
    )["topics"]
    optional_names = {"Buffet", "Buffet Variety", "Buffet Replenishment", "Shisha"}
    rows = [deepcopy(row) for row in baseline if row["name"] not in optional_names]
    by_name = {row["name"]: row for row in baseline}
    for name in optional:
        if name in by_name:
            rows.append(deepcopy(by_name[name]))
        elif name == "Brunch":
            rows.append({"name": "Brunch", "aliases": ["brunch", "brunch menu", "brunch buffet", "frühstück", "fruehstueck"]})
    return rows


def profile(name, address, concept, features, hours, meals, sources, optional_topics=(), distinctive=()):
    return {
        "restaurant_name": name,
        "business_type": "restaurant",
        "concept": concept,
        "address": address,
        "google_maps_url": sources["maps"],
        "categories_cuisine": sources["cuisine"],
        "opening_hours": hours,
        "meals": meals,
        "service_modes": [key for key in ("dine_in", "takeaway", "delivery") if features.get(key) is True],
        "features": features,
        "website": sources.get("website"),
        "menu_urls": sources.get("menu_urls", []),
        "delivery_platform_urls": sources.get("delivery_urls", []),
        "social_links": sources.get("social_links", []),
        "distinctive_offer": list(distinctive),
        "snapshot_date": RETRIEVED,
        "unknown_fields_policy": "null means not established by the stored sources",
        "analysis_settings": {
            "use_all_reviews_as_primary_denominator": True,
            "also_report_written_review_coverage": True,
            "calculate_positive_coverage": True,
            "calculate_negative_coverage": True,
            "calculate_neutral_coverage": True,
            "calculate_total_mentions": True,
            "calculate_reviews_mentioning": True,
            "calculate_average_rating_when_mentioned": True,
            "calculate_monthly_trends": True,
            "calculate_recent_trends": True,
            "keep_structured_and_text_metrics_separate": True,
        },
        "analysis_objectives": ["Apply the validated five-layer review-analysis methodology for fair competitor comparison."],
        "topics": common_topics(optional_topics),
    }


def build_olivenzweig():
    key = "olivenzweig"
    official_menu = "official_menu_2026_09_21"
    brunch_menu = "official_brunch_menu_2026_09_21"
    rows = [
        item("Salads", "Fattoush", 9.50, ["fattush", "فتوش"], source=official_menu, tags=["vegetarian"]),
        item("Salads", "Auberginen Fattoush", 9.50, ["eggplant fattoush"], source=official_menu, tags=["vegetarian"]),
        item("Salads", "Tabouleh", 9.50, ["tabbouleh", "tabouli", "تبولة"], source=official_menu, tags=["vegetarian"]),
        item("Salads", "Orientalischer Salat", 9.50, ["oriental salad"], source=official_menu, tags=["vegetarian"]),
        item("Cold Starters", "Hummus", 7.90, ["humus", "houmous", "حمص"], source=official_menu, tags=["vegan"]),
        item("Cold Starters", "Hummus Beiruty", 7.90, ["beiruti hummus"], source=official_menu, tags=["vegan"]),
        item("Cold Starters", "Mutabbal", 7.90, ["moutabal", "متبل"], source=official_menu, tags=["vegetarian"]),
        item("Cold Starters", "Baba Ghanoush", 7.90, ["baba ganoush", "بابا غنوج"], source=official_menu, tags=["vegan"]),
        item("Cold Starters", "Muhammara", 7.90, ["muhamara", "محمرة"], source=official_menu, tags=["vegan"]),
        item("Cold Starters", "Yalangi", 8.50, ["stuffed vine leaves", "yalanji"], source=official_menu, tags=["vegan"]),
        item("Warm Starters", "Frittierter Blumenkohl", 8.90, ["fried cauliflower"], source=official_menu, tags=["vegetarian"]),
        item("Warm Starters", "Gebratene Hähnchenleber", 9.90, ["chicken liver"], source=official_menu),
        item("Warm Starters", "Toschka", None, ["toshka"], source=official_menu),
        item("Warm Starters", "Scharfe Kartoffeln", 7.90, ["batata harra", "spicy potatoes"], source=official_menu, tags=["vegan"]),
        item("Warm Starters", "Falafel-Teller", 11.90, ["falafel plate", "falafel platter"], source=official_menu, tags=["vegan"]),
        item("Grill", "Aleppo Kebab", 18.90, ["halabi kebab", "kebab halabi"], source=official_menu),
        item("Grill", "Kirsch Kebab", 24.90, ["cherry kebab"], source=official_menu),
        item("Grill", "Ka'b Elghazal Kebab", 24.90, ["kab elghazal"], source=official_menu),
        item("Grill", "Shish Tawook", 19.90, ["shish taouk", "chicken skewer"], source=official_menu),
        item("Grill", "Gegrillte Lammspieße", 24.90, ["lamb skewers"], source=official_menu),
        item("Grill", "Lammkotelett", 28.90, ["lamb chops", "lamb chop"], source=official_menu),
        item("Grill", "Gemischter Grillteller 1 Person", 28.50, ["mixed grill platter", "mixed grill"], source=official_menu),
        item("Sharing Platters", "Gemischter Grillteller 2 Personen", 55.90, ["mixed grill for two", "sharing grill"], source=official_menu),
        item("Grill", "Gegrilltes Hähnchen", 16.90, ["grilled half chicken", "half chicken"], source=official_menu),
        item("Grill", "Gegrillter Fisch Dorade", 29.50, ["dorade", "sea bream"], source=official_menu),
        item("Smoked Meat", "Lammhaxe", 29.90, ["lamb shank"], source=official_menu),
        item("Smoked Meat", "Lammnacken", 38.50, ["lamb neck"], source=official_menu),
        item("Smoked Meat", "Rinderkotelett", 34.50, ["beef chop"], source=official_menu),
        item("Smoked Meat", "Lammschulter für 2", 69.50, ["lamb shoulder", "smoked lamb shoulder"], source=official_menu),
        item("Sharing Platters", "Geräucherte Platte für 2", 69.50, ["smoked platter for two"], source=official_menu),
        item("Sharing Platters", "Geräucherte Platte für 4", 120.00, ["smoked platter for four"], source=official_menu),
        item("Desserts", "Arabische Eiscreme", 4.90, ["arabic ice cream"], source=official_menu),
        item("Tea", "Schwarztee", 4.20, ["black tea", "tea"], source=official_menu),
        item("Tea", "Frischer Minztee", 4.90, ["fresh mint tea", "mint tea"], source=official_menu),
        item("Coffee", "Arabisch Kaffee", 3.70, ["arabic coffee"], source=official_menu),
        item("Coffee", "Cappuccino", 4.90, [], source=official_menu),
        item("Cold Drinks", "Coca-Cola 0.2l", 3.50, ["coca cola", "cola", "coke"], source=official_menu),
        item("Cold Drinks", "Ayran", 3.50, ["ayran"], source=official_menu),
        item("Home-made Iced Tea", "Mango Maracuja Eistee", 5.90, ["mango passionfruit iced tea"], source=official_menu),
        item("Home-made Iced Tea", "Himbeere Limette Eistee", 5.90, ["raspberry lime iced tea"], source=official_menu),
        item("Mocktails", "Mojito Classic", 7.90, ["virgin mojito", "mojito"], source=official_menu),
        item("Mocktails", "Ipanema", 7.90, [], source=official_menu),
        item("Milkshakes", "Pistazien-Milkshake", 8.90, ["pistachio milkshake", "pisto milkshake"], source=official_menu),
        item("Weekend Brunch", "Frühstücksteller für eine Person", 20.00, ["breakfast platter for one", "brunch platter"], source=brunch_menu, signal=["official_signature_positioning"]),
        item("Weekend Brunch", "Frühstücksteller für zwei Personen", 38.00, ["breakfast platter for two", "brunch for two"], source=brunch_menu, signal=["official_sharing_positioning"]),
        item("Weekend Brunch", "Foul", 11.90, ["ful", "fava beans"], source=brunch_menu, tags=["vegan"]),
        item("Weekend Brunch", "Shakshuka", 11.90, ["shakshouka"], source=brunch_menu, tags=["vegetarian"]),
        item("Weekend Brunch", "Fatteh", 13.90, ["fatte", "فتة"], source=brunch_menu, tags=["vegetarian"]),
        item("Weekend Brunch", "Gemischter Manakish-Teller", 25.00, ["mixed manakish platter"], source=brunch_menu, tags=["vegetarian"]),
    ]
    profile_sources = {
        "maps": MAPS[key], "cuisine": ["Oriental", "Levantine", "Middle Eastern"],
        "website": "https://www.olivenzweig-restaurant.de/",
        "menu_urls": ["https://www.olivenzweig-restaurant.de/unser-menu/", "https://www.olivenzweig-restaurant.de/brunch-menu/"],
        "delivery_urls": ["https://www.olivenzweigrestaurant-bonn.de/"],
    }
    prof = profile(
        "Olivenzweig Restaurant", "Budapester Str. 11, 53111 Bonn", "Oriental restaurant",
        {"dine_in": True, "takeaway": True, "delivery": True, "reservations": True,
         "outdoor_seating": None, "indoor_seating": True, "parking_available": True,
         "parking_note": "Paid parking listed at Berliner Platz 2", "payment_methods": None,
         "halal_positioning": None, "weekend_brunch": True, "buffet": False,
         "catering": True, "events": True, "bar_drinks": True, "family_groups": True},
        {"monday": "closed", "tuesday_thursday_sunday": "12:00-00:00", "friday_saturday": "12:00-01:00", "kitchen_closes": "one hour before venue close"},
        ["lunch", "dinner", "weekend brunch"], profile_sources, optional_topics=["Brunch"],
        distinctive=["weekend brunch", "smoked meat", "premium sharing platters", "broad non-alcoholic drinks range", "catering and events"],
    )
    sources = [
        source("Olivenzweig official home", "official_restaurant_website", profile_sources["website"], ["identity", "positioning", "address"], "high"),
        source("Olivenzweig official menu", "official_owned_menu", profile_sources["menu_urls"][0], ["menu", "prices", "drinks", "opening hours"], "high", conflicts=["Delivery menu has some different item prices; official dine-in menu retained separately."]),
        source("Olivenzweig official brunch menu", "official_owned_menu", profile_sources["menu_urls"][1], ["weekend brunch", "prices", "hours"], "high"),
        source("Olivenzweig official services", "official_restaurant_website", "https://www.olivenzweig-restaurant.de/dienstleistungen/", ["catering", "events", "corporate lunch"], "high"),
        source("Olivenzweig official reservations", "official_restaurant_website", "https://www.olivenzweig-restaurant.de/reservierungen/", ["reservations"], "high"),
        source("Olivenzweig official contact", "official_restaurant_website", "https://www.olivenzweig-restaurant.de/kontakt/", ["address", "parking", "opening hours"], "high", conflicts=["Some official page footers say daily while the same site also states Monday is closed; Monday retained as closed with conflict flagged."]),
        source("Olivenzweig delivery menu", "delivery_platform", profile_sources["delivery_urls"][0], ["delivery availability", "cross-check menu"], "medium", conflicts=["Delivery prices differ from official dine-in menu on some items."]),
        source("Google Maps target", "google_business_maps", MAPS[key], ["review collection", "map identity"], "high"),
        source("Supplied competitive-intelligence PDF", "supplied_research", None, ["intended profile/menu cross-check"], "unavailable", notes="Referenced in the brief but no PDF file was present in the workspace or attachment directory; not used."),
    ]
    return prof, rows, sources


def build_al_safa():
    key = "al_safa"; public = "al_safa_current_public_website_2026_09_21"
    rows = [
        item("Starters", "Kleine Vorspeise", 9.00, ["small appetizer platter", "small mezze"], source=public),
        item("Starters", "Safa Vorspeise", 12.50, ["safa appetizer", "safa mezze"], source=public),
        item("Starters", "Hummus", 4.00, ["humus", "houmous", "حمص"], source=public, tags=["vegan"]),
        item("Starters", "Tabule", 4.00, ["tabbouleh", "tabouleh", "تبولة"], source=public, tags=["vegan"]),
        item("Starters", "Auberginenpaste", 4.00, ["moutabal", "mutabbal", "eggplant dip"], source=public, tags=["vegetarian"]),
        item("Starters", "Gefüllte Weinblätter", 4.50, ["stuffed vine leaves", "yalanji"], source=public, tags=["vegan"]),
        item("Starters", "Falafel Teller", 7.50, ["falafel plate", "falafel platter"], source=public, tags=["vegan"]),
        item("Starters", "Asia-Teller", 10.00, ["large falafel plate"], source=public, tags=["vegan"]),
        item("Starters", "Halloumi Teller", 8.50, ["halloumi plate"], source=public, tags=["vegetarian"]),
        item("Sandwiches", "Döner Sandwich", 5.00, ["doner sandwich", "shawarma sandwich"], source=public),
        item("Sandwiches", "Dürüm", 5.00, ["durum", "wrap"], source=public),
        item("Sandwiches", "Falafel Sandwich", 4.00, ["falafel wrap"], source=public, tags=["vegan"]),
        item("Sandwiches", "Halloumi Sandwich", 4.00, ["halloumi wrap"], source=public, tags=["vegetarian"]),
        item("Main Dishes", "Reisteller", 5.00, ["rice plate"], source=public, tags=["vegetarian"]),
        item("Main Dishes", "Biryani", 6.00, ["chicken biryani"], source=public),
        item("Main Dishes", "Sac Kawerma", 13.00, ["sac kavurma", "sac kawarma"], source=public),
        item("Main Dishes", "Kosi Lammhaxe", 15.00, ["quzi", "qoozi", "lamb shank"], source=public),
        item("Main Dishes", "Lammgulasch", 7.00, ["lamb stew"], source=public),
        item("Soups", "Linsensuppe", 4.50, ["lentil soup"], source=public, tags=["vegetarian"]),
        item("Main Dishes", "Döner Teller mit Salat", 7.50, ["doner plate"], source=public),
        item("Main Dishes", "Döner Teller mit Beilage", 10.00, ["doner platter", "shawarma plate"], source=public),
        item("Grill", "Hähnchen Teller", 11.00, ["chicken skewer plate", "shish taouk"], source=public),
        item("Grill", "Hähnchen Teller mit Beilage", 13.50, ["chicken grill with rice", "shish taouk plate"], source=public),
        item("Grill", "Gemischter Grillteller", 12.00, ["mixed grill", "mixed grill plate"], source=public),
        item("Grill", "Gemischter Grillteller mit Beilage", 14.50, ["mixed grill platter"], source=public),
        item("Fish", "Dorade", 13.00, ["dorado", "sea bream"], source=public),
        item("Fish", "Dorade mit Reis", 15.50, ["dorade with rice", "sea bream with rice"], source=public),
        item("Chicken", "Halbes Hähnchen", 6.00, ["half chicken", "grilled half chicken"], source=public),
        item("Drinks", "Soft Drink 0.33l", 2.00, ["cola", "coca cola", "fanta", "sprite"], source=public),
        item("Drinks", "Ayran 0.25l", 2.00, ["ayran"], source=public),
        item("Drinks", "Frischer Orangensaft", 3.00, ["fresh orange juice", "orange juice"], source=public),
        item("Desserts", "Baklava", 1.00, ["baklawa"], source=public),
        item("Desserts", "Knafeh", 4.50, ["kunafa", "kanafeh", "كنافة"], source=public),
    ]
    website = "https://alsafa-restaurant.eu/"
    prof_sources = {"maps": MAPS[key], "cuisine": ["Oriental", "Middle Eastern"], "website": website,
                    "menu_urls": [website, "https://weur-cdn.speisekarte.menu/storage/media/companies_menu_pdf/114136566/al-safa-bonn-speisekarte.pdf"], "delivery_urls": []}
    prof = profile(
        "Al Safa Restaurant", "Alte Bahnhofstr. 32, 53173 Bonn", "Oriental restaurant",
        {"dine_in": True, "takeaway": True, "delivery": None, "reservations": None,
         "outdoor_seating": True, "indoor_seating": True, "parking_available": None,
         "payment_methods": None, "halal_positioning": None, "buffet": None,
         "catering": None, "events": None, "bar_drinks": False, "family_groups": None},
        {day: "12:00-23:00" for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")},
        ["lunch", "dinner"], prof_sources,
        distinctive=["complimentary starter stated on public website", "broad value-oriented grill and main-dish menu"],
    )
    sources = [
        source("Al Safa Bonn public website/menu", "restaurant_website", website, ["menu", "prices", "distinctive offer"], "medium", notes="Current public page; ownership/current maintenance could not be independently established.", conflicts=["Brief says the official current menu is incomplete; treat prices as a public listing snapshot, not a guaranteed complete current menu."]),
        source("Al Safa physical-menu snapshot", "supplied_physical_menu", None, ["intended menu/price cross-check"], "unavailable", notes="Referenced by the brief/supplied research, but the referenced competitive PDF was not present; prices were not merged or invented."),
        source("Speisekarte.menu PDF mirror", "menu_aggregator_pdf", prof_sources["menu_urls"][1], ["secondary menu availability"], "low", conflicts=["Snapshot date and currentness are not authoritative; not used to overwrite public website prices."]),
        source("Restaurant Guru Al Safa Bonn", "reputable_listing", "https://de.restaurantguru.com/al-safa-Bonn", ["hours", "terrace description", "profile cross-check"], "low"),
        source("Online Tischreservierung listing", "booking_listing", "https://www.online-tischreservierung.de/restaurant/index/Nordrhein-Westfalen/Bonn/T%C3%BCrkisch/aab8o4e09k/Al%20Safa%20Restaurant%20%28Orientalische%20K%C3%BCche%29/", ["address", "hours"], "medium"),
        source("Google Maps target", "google_business_maps", MAPS[key], ["review collection", "map identity"], "high"),
        source("Supplied competitive-intelligence PDF", "supplied_research", None, ["intended profile/menu cross-check"], "unavailable", notes="Referenced in the brief but no PDF file was present in the workspace or attachment directory; not used."),
    ]
    return prof, rows, sources


def build_beit_fayrouz():
    key = "beit_fayrouz"; deliver = "lieferando_menu_2026_09_21"; uber = "uber_eats_2026_09_21"
    rows = [
        item("Breakfast", "Frühstück für 2 Personen", 24.90, ["breakfast for two"], source=deliver, tags=["vegetarian"]),
        item("Breakfast", "Foul Medammas", 9.50, ["foul", "ful", "fava beans"], source=deliver, tags=["vegetarian"]),
        item("Breakfast", "Falafel Teller", 10.00, ["falafel plate", "falafel platter"], source=deliver, tags=["vegan"]),
        item("Breakfast", "Shakshuka", 13.00, ["shakshouka"], source=deliver),
        item("Mezza & Starters", "Hummus", 7.90, ["humus", "houmous", "حمص"], source=deliver, tags=["vegan"]),
        item("Mezza & Starters", "Moutabal", 7.90, ["mutabbal", "متبل"], source=deliver, tags=["vegan"]),
        item("Mezza & Starters", "Baba Ghanoush", 7.90, ["baba ganoush", "بابا غنوج"], source=deliver, tags=["vegan"]),
        item("Mezza & Starters", "Labneh mit Knoblauch", 7.90, ["garlic labneh"], source=deliver, tags=["vegetarian"]),
        item("Mezza & Starters", "Hummus mit Fleisch", 8.90, ["hummus with meat", "meat hummus"], source=deliver, signal=["uber_eats_recommended_variant_at_8.40"]),
        item("Mezza & Starters", "Schawarma Hummus", 8.90, ["shawarma hummus"], source=deliver),
        item("Mezza & Starters", "Gebackene Kibbeh", 7.90, ["baked kibbeh", "kibbeh"], source=deliver),
        item("Mezza & Starters", "Falafel Portion", 7.90, ["falafel"], source=deliver, tags=["vegan"]),
        item("Grill & Main Dishes", "Kebab Teller", 14.90, ["kebab plate", "kebab platter"], source=deliver, signal=["uber_eats_category_signal"]),
        item("Sharing Platters", "Familienplatte für 2", 46.90, ["family platter for two", "family grill"], source=deliver),
        item("Grill & Main Dishes", "Lammspieße Teller", 16.90, ["lamb skewers plate"], source=deliver),
        item("Sharing Platters", "Schawarma & Grill Platte", 24.90, ["shawarma and grill platter"], source=deliver),
        item("Grill & Main Dishes", "Dorade", 24.90, ["dorado", "sea bream"], source=deliver),
        item("Grill & Main Dishes", "Halbes Hähnchen", 11.90, ["half chicken", "grilled half chicken"], source=deliver),
        item("Grill & Main Dishes", "Ganzes Hähnchen", 20.90, ["whole chicken", "grilled chicken"], source=deliver),
        item("Grill & Main Dishes", "Schisch Taouk Teller", 14.90, ["shish taouk", "shish tawook", "chicken skewer plate"], source=deliver, signal=["uber_eats_recommended_at_13.30"]),
        item("Grill & Main Dishes", "Lammkotelett Teller", 20.90, ["lamb chops", "lamb chop plate"], source=deliver),
        item("Grill & Main Dishes", "Gemischter Grillteller", 24.90, ["mixed grill", "mixed grill platter"], source=deliver, signal=["uber_eats_recommended_at_24.00"]),
        item("Sandwiches", "Kebab Sandwich", 8.90, ["kebab wrap"], source=deliver),
        item("Sandwiches", "Aleppo Kebab Sandwich", 9.90, ["halabi kebab sandwich"], source=deliver),
        item("Sandwiches", "Schisch Taouk Sandwich", 9.90, ["shish taouk wrap", "chicken skewer sandwich"], source=deliver),
        item("Sandwiches", "Schawarma Kalb Sandwich", 6.65, ["veal shawarma sandwich", "shawarma sandwich"], source=uber, signal=["uber_eats_recommended"]),
        item("Specials", "Lammleber", 13.90, ["lamb liver"], source=deliver),
        item("Specials", "Lammauflauf", 16.90, ["lamb casserole", "lamb stew"], source=deliver),
        item("Salads", "Fattoush", 8.90, ["fattush", "فتوش"], source=deliver, tags=["vegan"]),
        item("Salads", "Tabbouleh", 7.90, ["tabouleh", "tabouli", "تبولة"], source=deliver, tags=["vegan"]),
        item("Salads", "Rucola Salat", 6.90, ["rocket salad", "arugula salad"], source=deliver, tags=["vegan"]),
        item("Salads", "Fattoush Beit Fayrouz", 9.90, ["eggplant fattoush"], source=deliver, tags=["vegan"]),
        item("Drinks", "Fritz-Kola 0.33l", 2.50, ["fritz kola", "cola"], source=deliver),
        item("Drinks", "Sprite 0.33l", 2.50, ["sprite"], source=deliver),
    ]
    menu_url = "https://www.lieferando.de/speisekarte/beit-fayrouz"
    uber_url = "https://www.ubereats.com/de/store/beit-fayrouz-restaurant/NglP3wZEUH-5reilsPP94Q?isMatchbox=true"
    prof_sources = {"maps": MAPS[key], "cuisine": ["Syrian", "Lebanese", "Arabic", "Halal (platform category)"],
                    "website": None, "menu_urls": [menu_url, uber_url], "delivery_urls": [menu_url, uber_url]}
    prof = profile(
        "Beit Fayrouz Restaurant", "Villichgasse 1, 53177 Bonn", "Syrian/Lebanese restaurant",
        {"dine_in": True, "takeaway": True, "delivery": True, "reservations": None,
         "outdoor_seating": None, "indoor_seating": True, "parking_available": None,
         "payment_methods": None, "halal_positioning": "Supported as an Uber Eats category only",
         "breakfast": True, "buffet": False, "catering": None, "events": None,
         "bar_drinks": False, "family_groups": True},
        {day: "11:00-23:45 (Uber Eats service hours; venue hours not independently verified)" for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")},
        ["breakfast", "lunch", "dinner"], prof_sources,
        distinctive=["breakfast menu", "family sharing platter", "delivery platform recommended-item signals"],
    )
    sources = [
        source("Beit Fayrouz Lieferando", "delivery_platform_menu", menu_url, ["address", "menu", "current prices", "delivery"], "medium", conflicts=["An older/localized Lieferando crawl showed different prices; German current snapshot dated 2026-09-21 is used for catalog prices and conflict is retained."]),
        source("Beit Fayrouz Uber Eats", "delivery_platform_menu", uber_url, ["address", "menu cross-check", "delivery", "service hours", "platform recommended-item signals", "platform halal category"], "medium", notes="Platform recommendations and platform ratings are stored separately and are never treated as Google sentiment or sales.", conflicts=["Several prices differ from Lieferando; Uber values are retained in platform_signals/notes, not silently substituted."]),
        source("Google Maps target", "google_business_maps", MAPS[key], ["review collection", "map identity"], "high"),
        source("Opening announcement listing", "reputable_listing", "https://www.neueroeffnung.info/bonn/beit-fayrouz-restaurant", ["address", "opening context", "secondary venue hours"], "low", conflicts=["Listing venue hours 12:00-24:00 differ from Uber Eats delivery hours 11:00-23:45."]),
    ]
    return prof, rows, sources


def main():
    builders = {
        "olivenzweig": build_olivenzweig,
        "al_safa": build_al_safa,
        "beit_fayrouz": build_beit_fayrouz,
    }
    for slug, builder in builders.items():
        prof, items, sources = builder()
        base = ROOT / "businesses/restaurants" / slug
        inputs = base / "inputs"
        categories = sorted({row["category"] for row in items})
        catalog = {
            "restaurant": prof["restaurant_name"],
            "snapshot_date": RETRIEVED,
            "source": "See source_register.json and each item source field",
            "categories": categories,
            "items": items,
            "price_conflict_policy": "Conflicting prices remain source-specific and are not silently merged.",
        }
        save(inputs / "restaurant_profile.json", prof)
        save(inputs / "menu_catalog.json", catalog)
        save(inputs / "source_register.json", {"restaurant": prof["restaurant_name"], "snapshot_date": RETRIEVED, "sources": sources})
        save(inputs / "management_observations.json", management_observations())
        save(inputs / "source_snapshots/current_web_extract.json", {
            "restaurant": prof["restaurant_name"],
            "snapshot_date": RETRIEVED,
            "profile_claims": {
                "address": prof["address"], "opening_hours": prof["opening_hours"],
                "features": prof["features"], "distinctive_offer": prof["distinctive_offer"],
            },
            "menu_summary": {"categories": categories, "item_count": len(items), "priced_items": sum(row["price_eur"] is not None for row in items)},
            "source_urls": [row["url"] for row in sources if row["url"]],
            "refresh_note": "Local September 2026 snapshot for reproducibility; future work must refresh changed menus, prices, hours, and services.",
        })
        (base / "data").mkdir(parents=True, exist_ok=True)
        print(f"{slug}: {len(categories)} categories, {len(items)} items")
    # Apply the dated, source-aware enrichment after the reproducible base
    # snapshots are written. This never touches review databases or collection.
    from ingest_competitor_research_pdf import main as ingest_competitor_pdf
    ingest_competitor_pdf()


if __name__ == "__main__":
    main()
