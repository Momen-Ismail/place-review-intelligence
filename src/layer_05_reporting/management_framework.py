"""Human-input validation and management-facing framework builders."""

from __future__ import annotations

from src.common.evidence import evidence_level


ALLOWED_CLASSIFICATIONS = {"internal_observation", "proposed_experiment"}
DRINK_MENU_CATEGORIES = ("Cold Drinks", "Hot Drinks", "Cocktails & Juices")
KITCHEN_TOPICS = ("Food", "Taste", "Food Quality", "Freshness")


def validate_management_observations(value) -> dict:
    if not isinstance(value, dict):
        raise ValueError("management_observations.json must contain one JSON object")
    metadata = value.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("source_type") != "human_maintained_internal_input":
        raise ValueError("management_observations.json must identify itself as human-maintained internal input")
    if metadata.get("review_derived") is not False:
        raise ValueError("management_observations.json must explicitly set review_derived to false")
    for section, entries in value.items():
        if section == "metadata":
            continue
        if not isinstance(entries, dict):
            raise ValueError(f"Management observation section '{section}' must be an object")
        for key, item in entries.items():
            if not isinstance(item, dict) or "value" not in item:
                raise ValueError(f"Management observation '{section}.{key}' must contain a value")
            if item.get("classification") not in ALLOWED_CLASSIFICATIONS:
                raise ValueError(f"Management observation '{section}.{key}' has an invalid classification")
    return value


def _topic(text, name):
    row = next((item for item in text["topics"] if item["topic"] == name), None)
    if not row:
        return None
    return {
        "source_type": "customer_review_evidence",
        "topic": name,
        "topic_mentions": row["reviews_mentioning"],
        "topic_evidence_level": evidence_level(row["reviews_mentioning"]),
        "positive_reviews": row["positive_reviews"],
        "negative_count": row["negative_reviews"],
        "negative_issue_evidence_level": evidence_level(row["negative_reviews"]),
        "neutral_reviews": row["neutral_reviews"],
        "negative_share_of_topic_reviews_pct": row["negative_share_of_topic_reviews_pct"],
        "negative_coverage_pct_of_written_reviews": row["negative_coverage_pct_of_written_reviews"],
    }


def _observation(observations, section, key):
    value = observations.get(section, {}).get(key)
    if not value:
        return None
    return {"source_type": value["classification"], "observation_key": key, "value": value["value"], "note": value.get("note")}


def _stage(name, customer=None, observations=None, actions=None):
    return {
        "stage": name,
        "customer_evidence": [row for row in (customer or []) if row],
        "management_observations": [row for row in (observations or []) if row],
        "potential_actions": [row for row in (actions or []) if row],
    }


def issue_evidence_summary(
    topic_mentions,
    negative_count,
    negative_share=None,
    negative_coverage=None,
    coverage_field="negative_coverage_pct_of_written_reviews",
):
    """Keep topic evidence separate from evidence supporting a negative issue."""
    result = {
        "topic_mentions": topic_mentions,
        "topic_evidence_level": evidence_level(topic_mentions),
        "negative_count": negative_count,
        "negative_issue_evidence_level": evidence_level(negative_count),
        "negative_share_of_topic_reviews_pct": negative_share,
    }
    result[coverage_field] = negative_coverage
    return result


def _category_attention(row):
    total = row.get("total_items", row.get("total_menu_items", 0))
    mentioned = row.get("items_mentioned", row.get("items_with_review_mentions", 0))
    coverage = round(mentioned / total * 100, 2) if total else 0.0
    if mentioned == 0:
        status = "no observable review mentions"
    elif coverage < 25:
        status = "limited observable review attention"
    else:
        status = "observable review attention"
    return {**row, "review_attention_coverage_pct": coverage, "review_attention_status": status}


def build_bar_drinks_analysis(text):
    """Build a management view of review attention around drinks and the bar offer."""
    topic = next((row for row in text.get("topics", []) if row["topic"] == "Drinks"), None) or {}
    comparisons = {row["topic"]: row for row in text.get("topic_period_comparison", [])}
    period_source = comparisons.get("Drinks", {}).get("periods", {})
    overall_mentions = topic.get("reviews_mentioning", 0)
    overall_negative = topic.get("negative_reviews", 0)
    overall = {
        "source_type": "customer_review_evidence",
        **issue_evidence_summary(
            overall_mentions,
            overall_negative,
            topic.get("negative_share_of_topic_reviews_pct"),
            topic.get("negative_coverage_pct_of_written_reviews"),
        ),
        "written_review_coverage_pct": topic.get("mention_coverage_pct_of_written_reviews"),
        "positive": topic.get("positive_reviews", 0),
        "positive_evidence_level": evidence_level(topic.get("positive_reviews", 0)),
        "negative": overall_negative,
        "neutral": topic.get("neutral_reviews", 0),
        "neutral_evidence_level": evidence_level(topic.get("neutral_reviews", 0)),
        "average_overall_review_rating_when_mentioned": topic.get("average_review_rating_when_mentioned"),
    }
    periods = {}
    for label in ("historical", "previous_90d", "recent_90d"):
        row = period_source.get(label, {})
        mentions = row.get("reviews_mentioning_topic", 0)
        negative = row.get("negative_reviews", 0)
        periods[label] = {
            "source_type": "customer_review_evidence",
            "period": row.get("period", label),
            "mentions": mentions,
            "mention_coverage_pct_of_written_reviews": row.get("mention_coverage_pct_of_written_reviews"),
            "positive": row.get("positive_reviews", 0),
            "positive_evidence_level": evidence_level(row.get("positive_reviews", 0)),
            "negative": negative,
            "neutral": row.get("neutral_reviews", 0),
            "neutral_evidence_level": evidence_level(row.get("neutral_reviews", 0)),
            "average_overall_review_rating_when_mentioned": row.get("average_review_rating_when_mentioned"),
            "topic_evidence_level": evidence_level(mentions),
            "negative_issue_evidence_level": evidence_level(negative),
        }

    category_map = {row["category"]: row for row in text.get("menu_analysis", {}).get("categories", [])}
    categories = []
    for category in DRINK_MENU_CATEGORIES:
        source = category_map.get(category, {})
        total = source.get("total_items", 0)
        mentioned = source.get("items_mentioned", 0)
        categories.append(_category_attention({
            "category": category,
            "total_menu_items": total,
            "items_with_review_mentions": mentioned,
            "items_without_observable_review_mentions": max(total - mentioned, 0),
            "item_level_review_mentions": source.get("total_review_mentions", 0),
            "positive_dish_item_mentions": source.get("positive_dish_mentions", 0),
            "negative_dish_item_mentions": source.get("negative_dish_mentions", 0),
        }))
    total_items = sum(row["total_menu_items"] for row in categories)
    mentioned_items = sum(row["items_with_review_mentions"] for row in categories)
    menu_totals = {
        "total_drink_items": total_items,
        "drink_items_with_observable_review_mentions": mentioned_items,
        "drink_items_with_no_observable_review_mentions": total_items - mentioned_items,
        "pct_drink_items_with_review_attention": round(mentioned_items / total_items * 100, 2) if total_items else 0.0,
        "item_level_review_mentions": sum(row["item_level_review_mentions"] for row in categories),
        "positive_dish_item_mentions": sum(row["positive_dish_item_mentions"] for row in categories),
        "negative_dish_item_mentions": sum(row["negative_dish_item_mentions"] for row in categories),
    }
    return {
        "source_type": "customer_review_evidence",
        "terminology_note": "Review attention is not sales.",
        "comparison_note": "This is a review-attention comparison, not a revenue or sales comparison.",
        "interpretation_note": (
            "Low review attention does not measure sales, but because the restaurant operates a bar/drinks offering, "
            "the low level of observable customer discussion is a management signal worth investigating."
        ),
        "overall_review_evidence": overall,
        "period_comparison": periods,
        "menu_attention": {"categories": categories, "totals": menu_totals},
        "management_question": {
            "classification": "management_question",
            "question": "Why does the bar/drinks offering receive so little observable review attention compared with the food experience?",
            "possible_investigation_areas": [
                "customer awareness", "visibility on menu", "staff recommendation behavior", "drink presentation",
                "signature drinks", "pricing/value", "bundling", "drink-menu complexity",
            ],
            "interpretation_guardrail": "These are questions and hypotheses only; none is stated as a proven cause.",
        },
    }


def build_kitchen_bar_overview(text, bar_drinks_analysis=None):
    """Compare observable review attention without treating it as sales demand."""
    bar = bar_drinks_analysis or build_bar_drinks_analysis(text)
    topics = {row["topic"]: row for row in text.get("topics", [])}
    menu_categories = text.get("menu_analysis", {}).get("categories", [])

    def topic_rows(names):
        rows = []
        for name in names:
            row = topics.get(name)
            if not row:
                continue
            rows.append({
                "topic": name, "mentions": row["reviews_mentioning"],
                "positive": row["positive_reviews"], "negative": row["negative_reviews"],
                "neutral": row["neutral_reviews"],
                "topic_evidence_level": evidence_level(row["reviews_mentioning"]),
                "negative_issue_evidence_level": evidence_level(row["negative_reviews"]),
            })
        return rows

    def area(label, names, categories):
        rows = topic_rows(names)
        total_items = sum(row["total_items"] for row in categories)
        mentioned_items = sum(row["items_mentioned"] for row in categories)
        mentions = sum(row["mentions"] for row in rows)
        return {
            "area": label,
            "review_topics": rows,
            "summed_topic_review_mentions_non_unique": mentions,
            "summed_positive_non_unique": sum(row["positive"] for row in rows),
            "summed_negative_non_unique": sum(row["negative"] for row in rows),
            "summed_neutral_non_unique": sum(row["neutral"] for row in rows),
            "menu_items": total_items,
            "items_with_review_attention": mentioned_items,
            "review_attention_coverage_pct": round(mentioned_items / total_items * 100, 2) if total_items else 0.0,
            "evidence_level": evidence_level(mentions),
            "evidence_scope": "summed review-topic attention",
            "negative_issue_evidence_level": evidence_level(sum(row["negative"] for row in rows)),
        }

    drink_set = set(DRINK_MENU_CATEGORIES)
    kitchen_categories = [row for row in menu_categories if row["category"] not in drink_set]
    bar_categories = [row for row in menu_categories if row["category"] in drink_set]
    return {
        "terminology_note": "This is a review-attention comparison, not a revenue or sales comparison.",
        "aggregation_note": "Topic totals are summed, non-unique attention counts because one review can mention multiple topics.",
        "kitchen": area("kitchen", KITCHEN_TOPICS, kitchen_categories),
        "bar": area("bar_drinks", ("Drinks",), bar_categories),
        "bar_interpretation_note": bar["interpretation_note"],
    }


def build_menu_management_insights(text):
    menu = text["menu_analysis"]
    favourites = text["customer_favourite_signals"]
    categories = [_category_attention(row) for row in menu["categories"]]
    strongest = sorted(
        (row for row in categories if row["items_mentioned"]),
        key=lambda row: (row["total_review_mentions"], row["items_mentioned"], row["review_attention_coverage_pct"]),
        reverse=True,
    )
    weak_or_none = sorted(
        (row for row in categories if row["review_attention_status"] != "observable review attention"),
        key=lambda row: (row["items_mentioned"] > 0, row["review_attention_coverage_pct"], row["total_review_mentions"]),
    )
    negative_items = sorted(
        (row for row in menu["items"] if row["negative_dish_reviews"] > 0),
        key=lambda row: (row["negative_dish_reviews"], row["review_mentions"]),
        reverse=True,
    )
    return {
        "source_type": "customer_review_evidence",
        "interpretation_note": (
            "Menu review attention is not order volume or sales. Items with zero attention are described only as having "
            "no observable review mentions and should be investigated with actual POS/order data."
        ),
        "weak_attention_rule": "Limited means some observable mentions but fewer than 25% of category items mentioned.",
        "most_discussed_menu_items": favourites.get("most_discussed", []),
        "most_positively_discussed_menu_items": favourites.get("most_positively_discussed", []),
        "negatively_discussed_items": negative_items,
        "category_review_attention": categories,
        "categories_with_strongest_review_attention": strongest[:5],
        "categories_with_weak_or_no_review_attention": weak_or_none,
        "items_with_no_observable_review_mentions": menu["items_with_no_observable_review_mentions"],
    }


def build_menu_optimization_goal():
    return {
        "classification": "internal_management_goal",
        "review_derived": False,
        "goal": (
            "The menu should be reviewed using actual order/POS data together with review-attention data to identify "
            "which items customers frequently order, which items contribute value, which items receive little demand, "
            "and where the menu can be simplified."
        ),
        "recommended_future_inputs": [
            "item-level order count", "item revenue", "item gross margin if available",
            "item cancellation/return rate if available", "item-level time trend", "category sales share",
            "drink sales share", "food sales share",
        ],
        "future_process": [
            {"step": 1, "action": "Analyze actual order/POS data."},
            {"step": 2, "action": "Compare order frequency with review attention."},
            {"step": 3, "action": "Classify items", "segments": [
                "high-order / high-attention items", "high-order / low-attention items",
                "low-order / high-attention items", "low-order / low-attention items",
            ]},
            {"step": 4, "action": "Use the result", "possible_uses": [
                "simplify menu structure", "remove or reconsider low-value items", "update Favourite section",
                "improve category order", "create clearer recommendations", "test bundles", "test weekly offers",
                "highlight proven popular dishes",
            ]},
        ],
        "scope_guardrail": "No sales analysis is implemented because no sales/POS dataset has been provided.",
    }


def build_future_favourites_method():
    return {
        "classification": "future_method_requiring_pos_data",
        "definitive_ranking_generated": False,
        "signals_once_pos_data_exists": [
            "order frequency", "repeat order frequency if available", "positive review attention", "gross margin", "recent trend",
        ],
        "current_allowed_review_labels": ["Most discussed", "Most positively discussed"],
        "prohibited_without_pos_data": ["Best seller", "Most ordered"],
    }


def build_menu_activation_experiments(observations):
    experiments = [
        "weekly featured dish", "food + drink bundle", "buffet promotion",
        "rotating customer-favourite highlight", "bar/drink feature of the week",
        "visual/video dish promotion", 'simplified "Recommended" section',
    ]
    return {
        "source_type": "proposed_experiment",
        "current_internal_observations": [
            _observation(observations, "menu", "weekly_offers_available"),
            _observation(observations, "menu", "food_drink_bundles_available"),
            _observation(observations, "menu", "menu_should_influence_customer_choice_more"),
        ],
        "experiments": [{"name": name, "classification": "proposed_experiment", "proven_recommendation": False}
                        for name in experiments],
    }


def build_customer_journey(prepared, numerical, text, observations, kitchen_bar_overview=None):
    features = prepared.get("profile", {}).get("features", {})
    cadence = numerical["review_cadence"]["periods"]["recent_30d"]
    response = numerical["owner_response_analysis"]
    menu_summary = text["menu_analysis"]["summary"]
    kitchen_bar = kitchen_bar_overview or build_kitchen_bar_overview(text)
    return {
        "evidence_source_note": (
            "Customer-review evidence, profile facts, internal observations, internal management goals, and proposed experiments remain explicitly separated. "
            "No stage implies causality."
        ),
        "stages": [
            _stage("discovery_google_profile", [
                {"source_type": "restaurant_profile_fact", "metric": "parking_available", "value": features.get("parking_available")},
                _topic(text, "Parking"),
            ], [_observation(observations, "google_profile_reputation", "parking_available_but_not_promoted_in_profile")], [
                {"source_type": "proposed_experiment", "action": "Verify current profile visibility and test clearer parking information."}
            ]),
            _stage("arrival", [_topic(text, "Parking"), _topic(text, "Family & Groups")], [
                _observation(observations, "customer_experience", "welcome_process_needs_review")
            ]),
            _stage("welcome", [_topic(text, "Hospitality"), _topic(text, "Staff Friendliness")], [
                _observation(observations, "customer_experience", "welcome_process_needs_review")
            ], [_observation(observations, "customer_experience", "complimentary_welcome_appetizer_or_small_gesture_test_proposed")]),
            _stage("menu_discovery", [
                _topic(text, "Menu & Tablet"),
                {"source_type": "customer_review_evidence", "metric": "pct_menu_items_with_review_attention", "value": menu_summary["pct_items_with_review_attention"]},
            ], [
                _observation(observations, "menu", "menu_considered_static"),
                _observation(observations, "menu", "favourites_manually_selected"),
                _observation(observations, "menu", "favourites_not_regularly_updated"),
                _observation(observations, "menu", "weekly_offers_available"),
                _observation(observations, "menu", "food_drink_bundles_available"),
                _observation(observations, "menu", "menu_should_influence_customer_choice_more"),
            ], [_observation(observations, "customer_experience", "proactive_menu_guidance_proposed")]),
            _stage("order", [_topic(text, "Reservations"), _topic(text, "Takeaway")], [], [
                {"source_type": "internal_management_goal", "action": "Add actual POS/order data before drawing demand or sales conclusions."},
                {"source_type": "proposed_experiment", "action": "Test whether proactive guidance improves menu confidence; measure before scaling."}
            ]),
            _stage("wait", [_topic(text, "Waiting Time"), _topic(text, "Staff Communication")]),
            _stage("food_drink_experience", [
                {"source_type": "customer_review_evidence", "business_area": "kitchen", **kitchen_bar["kitchen"]},
                {"source_type": "customer_review_evidence", "business_area": "bar_drinks", **kitchen_bar["bar"]},
                _topic(text, "Buffet"),
            ], [], [_observation(observations, "media", "dish_video_or_richer_media_test_proposed")]),
            _stage("payment", [_topic(text, "Card Payment")]),
            _stage("post_visit_review", [{
                "source_type": "review_flow_metric", "period": "recent_30d",
                "review_count": cadence["review_count"], "reviews_per_week": cadence["reviews_per_week"],
                "average_days_between_reviews": cadence["average_days_between_reviews"],
            }]),
            _stage("owner_follow_up", [{
                "source_type": "owner_response_metric",
                "overall_response_rate_pct": response["overall"]["owner_response_rate_pct"],
                "low_score_response_rate_pct": response["low_score"]["low_score_response_rate_pct"],
                "recent_90d_response_rate_pct": response["periods"]["recent_90d"]["response_rate_pct"],
            }], [_observation(observations, "google_profile_reputation", "owner_review_response_process_needs_improvement")]),
        ],
    }


def build_management_baseline(numerical, text, bar_drinks_analysis=None):
    trend = numerical["rating_trend_summary"]
    summary = numerical["summary"]
    cadence = numerical["review_cadence"]["periods"]
    response = numerical["owner_response_analysis"]
    comparison = {row["topic"]: row for row in text["topic_period_comparison"]}

    def recent_topic(name):
        recent = comparison.get(name, {}).get("periods", {}).get("recent_90d", {})
        negative_count = recent.get("negative_reviews", 0)
        return issue_evidence_summary(
            recent.get("reviews_mentioning_topic", 0),
            negative_count,
            recent.get("negative_share_of_topic_reviews_pct"),
            (
                round(recent.get("negative_reviews", 0) / recent["written_reviews_in_period"] * 100, 2)
                if recent.get("written_reviews_in_period") else None
            ),
            coverage_field="negative_coverage_pct_of_recent_written_reviews",
        )

    buffet_recent = text["buffet_analysis"]["period_comparison"]["recent_90d"]
    bar = bar_drinks_analysis or build_bar_drinks_analysis(text)
    menu_summary = text["menu_analysis"]["summary"]
    drink_totals = bar["menu_attention"]["totals"]
    return {
        "purpose": "Current baseline for a later four-week action plan; no improvement targets are set here.",
        "ratings": {
            "google_rating": summary["google_overall_rating"],
            "collected_average_rating": summary["collected_average_rating"],
            "recent_30d_average_rating": trend["recent_30d_average"],
            "previous_30d_average_rating": trend["previous_30d_average"],
            "recent_90d_average_rating": trend["recent_90d_average"],
            "historical_average_rating": trend["historical_before_recent_90d_average"],
            "recent_30d_negative_share_pct": trend["recent_30d_negative_pct"],
            "recent_90d_negative_share_pct": trend["recent_90d_negative_pct"],
            "historical_negative_share_pct": trend["historical_before_recent_90d_negative_pct"],
        },
        "review_flow": {
            "recent_30d_review_count": cadence["recent_30d"]["review_count"],
            "recent_30d_reviews_per_week": cadence["recent_30d"]["reviews_per_week"],
            "recent_30d_average_days_between_reviews": cadence["recent_30d"]["average_days_between_reviews"],
            "previous_30d_review_count": cadence["previous_30d"]["review_count"],
            "previous_30d_reviews_per_week": cadence["previous_30d"]["reviews_per_week"],
        },
        "reputation_management": {
            "overall_owner_response_rate_pct": response["overall"]["owner_response_rate_pct"],
            "recent_30d_owner_response_rate_pct": response["periods"]["recent_30d"]["response_rate_pct"],
            "recent_90d_owner_response_rate_pct": response["periods"]["recent_90d"]["response_rate_pct"],
            "low_score_owner_response_rate_pct": response["low_score"]["low_score_response_rate_pct"],
        },
        "customer_issues_recent_90d": {
            "service": recent_topic("Service"), "food": recent_topic("Food"),
            "price_value": recent_topic("Price & Value"), "taste": recent_topic("Taste"),
        },
        "menu": {
            "total_menu_items": menu_summary["total_menu_items"],
            "pct_menu_items_with_review_attention": menu_summary["pct_items_with_review_attention"],
        },
        "drinks": {
            "total_drink_related_menu_items": drink_totals["total_drink_items"],
            "pct_drink_items_with_review_attention": drink_totals["pct_drink_items_with_review_attention"],
            "total_drinks_topic_mentions": bar["overall_review_evidence"]["topic_mentions"],
            "recent_90d_drinks_mentions": bar["period_comparison"]["recent_90d"]["mentions"],
        },
        "buffet_recent_90d": {
            "mentions": buffet_recent["mentions"],
            "mention_coverage_pct_of_written_reviews": buffet_recent["mention_coverage_pct_of_written_reviews"],
            "positive": buffet_recent["positive"], "negative": buffet_recent["negative"], "neutral": buffet_recent["neutral"],
            "evidence_level": buffet_recent["evidence_level"],
        },
    }
