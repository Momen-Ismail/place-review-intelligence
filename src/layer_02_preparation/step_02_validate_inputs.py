"""Validate the restaurant profile and menu catalog."""

from typing import Any


def validate_profile(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError("restaurant_profile.json must contain one JSON object.")
    if not str(value.get("restaurant_name") or "").strip():
        raise ValueError("restaurant_profile.json is missing 'restaurant_name'.")
    topics = value.get("topics")
    if not isinstance(topics, list):
        raise ValueError("restaurant_profile.json must contain 'topics' as a list.")
    seen: set[str] = set()
    for index, topic in enumerate(topics, start=1):
        if not isinstance(topic, dict):
            raise ValueError(f"Topic {index} must be a JSON object.")
        name = str(topic.get("name") or "").strip()
        if not name:
            raise ValueError(f"Topic {index} has no name.")
        if name.casefold() in seen:
            raise ValueError(f"Duplicate topic name: {name}")
        seen.add(name.casefold())
        if not isinstance(topic.get("aliases"), list):
            raise ValueError(f"Topic '{name}' must have an aliases list.")
    return value


def validate_menu(value: Any) -> list[dict]:
    """Validate legacy list catalogs and source-aware catalog snapshots."""
    if isinstance(value, dict):
        value = value.get("items")
    if not isinstance(value, list) or not value:
        raise ValueError(
            "menu_catalog.json must contain a non-empty JSON list or an object "
            "with a non-empty 'items' list."
        )
    required = {"category", "name", "english_name", "price_eur", "aliases"}
    seen: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Menu item {index} must be a JSON object.")
        missing = required - item.keys()
        if missing:
            raise ValueError(f"Menu item {index} is missing: {', '.join(sorted(missing))}")
        name = str(item["name"]).strip()
        if not name or name.casefold() in seen:
            raise ValueError(f"Invalid or duplicate menu item name at position {index}: {name}")
        seen.add(name.casefold())
        if not isinstance(item["aliases"], list):
            raise ValueError(f"Menu item '{name}' must have an aliases list.")
    return value
