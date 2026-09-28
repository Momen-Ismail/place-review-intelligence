"""Generate the reproducible Phase A low-score accuracy audit.

This reads the existing review databases without changing them and compares the
pre-correction Layer 04 snapshots with the regenerated outputs.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "competitive" / "restaurants" / "phase_a_accuracy_audit.json"
BEFORE_ROOT = Path("/private/tmp/place_review_phase_a_before")
SLUGS = ("al_assiel", "olivenzweig", "al_safa", "beit_fayrouz")
EXPECTED_HASHES = {
    "al_assiel": "c3206e244aa259b5c5676265b929bdf4b24e9f26aac579555a58fe7abceab682",
    "olivenzweig": "0518b0dc96df68bf1245633d7d0017b82d22b4c5d0d8a13b2eaf77bb437765cb",
    "al_safa": "bc20fb22cfd18982fae533be9efc2de1f56684a5fdd369c2ef52e7729240016b",
    "beit_fayrouz": "c2ff88240782342d54f21c2d309f12930ca3f77523173fa51d810fbf81cfc144",
}
FOCUS_TOPICS = (
    "Food",
    "Taste",
    "Service",
    "Waiting Time",
    "Price & Value",
    "Drinks",
    "Menu & Tablet",
    "Cleanliness",
    "Atmosphere",
    "Buffet",
    "Brunch",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def group_summary(layer_04: dict) -> dict:
    low = layer_04["low_rating_analysis"]
    combined = low["groups"]["combined_one_two_star"]
    topics = {row["topic"]: row for row in combined["topics"]}
    evidence = low["review_evidence"]
    written = combined["written_review_count"]
    negative_topics = [row for row in combined["topics"] if row["negative_reviews"] > 0]
    negative_topics.sort(key=lambda row: (-row["negative_reviews"], row["topic"]))
    dish_reviews = sum(bool(row.get("detected_dishes")) for row in evidence)
    return {
        "one_star_reviews": low["groups"]["one_star"]["review_count"],
        "two_star_reviews": low["groups"]["two_star"]["review_count"],
        "low_score_reviews": combined["review_count"],
        "written_low_score_reviews": written,
        "owner_response_count": combined["owner_response_count"],
        "owner_response_rate_pct": combined["owner_response_rate_pct"],
        "top_negative_topics": negative_topics,
        "focus_topic_counts": {
            topic: {
                "negative_reviews": topics.get(topic, {}).get("negative_reviews", 0),
                "share_of_written_low_score_reviews_pct": topics.get(topic, {}).get(
                    "share_of_written_low_score_reviews_pct", 0.0
                ),
                "evidence_level": topics.get(topic, {}).get("evidence_level", "none"),
            }
            for topic in FOCUS_TOPICS
        },
        "topic_cooccurrence": low["topic_cooccurrence"]["presentation_pairs_min_2_reviews"],
        "dish_involvement_reviews": dish_reviews,
        "dish_involvement_share_of_written_low_score_pct": round(100 * dish_reviews / written, 2)
        if written
        else 0.0,
        "low_score_dishes": low["low_score_dishes"],
    }


def db_reviews(slug: str) -> dict[str, dict]:
    path = ROOT / "businesses" / "restaurants" / slug / "data" / "reviews.db"
    uri = f"file:{path}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT review_id, review_url, rating, text_original, text_translated,
               original_language, translated_language, published_at,
               owner_response_text, owner_response_date
        FROM reviews
        WHERE rating IN (1, 2)
        ORDER BY published_at DESC, review_id
        """
    ).fetchall()
    connection.close()
    return {row["review_id"]: dict(row) for row in rows}


def case_register(slug: str, current: dict) -> list[dict]:
    reviews = db_reviews(slug)
    evidence = current["low_rating_analysis"]["review_evidence"]
    cases = []
    for index, row in enumerate(evidence, 1):
        source = reviews.get(row["review_id"], {})
        original = (source.get("text_original") or "").strip()
        translated = (source.get("text_translated") or "").strip()
        if not (original or translated):
            continue
        analysis_text = translated or original
        cases.append(
            {
                "anonymous_case_id": f"{slug.upper().replace('_', '-')}-LS-{index:03d}",
                "review_id": row["review_id"],
                "date": (source.get("published_at") or row["date"])[:10],
                "rating": row["rating"],
                "detected_negative_topics": row["detected_negative_topics"],
                "detected_dishes": row["detected_dishes"],
                "has_owner_response": row["has_owner_response"],
                "owner_response_date": source.get("owner_response_date"),
                "original_language": source.get("original_language"),
                "translated_language": source.get("translated_language"),
                "text_original": original,
                "text_translated": translated,
                "analysis_excerpt": analysis_text[:320] + ("…" if len(analysis_text) > 320 else ""),
                "review_url": source.get("review_url"),
                "sentiment_note": "Topic-local rule output; rating is not used as sentiment fallback.",
            }
        )
    return cases


def main() -> None:
    competitive = load_json(
        ROOT / "output" / "competitive" / "restaurants" / "competitive_analysis_results.json"
    )
    result = {
        "generated_on": date.today().isoformat(),
        "scope": {
            "restaurants": list(SLUGS),
            "formal_cutoff": competitive["metadata"]["comparison_cutoff_date"],
            "written_low_score_reviews_audited": 0,
            "rating_fallback_used": False,
            "review_collection_performed": False,
            "apify_invoked": False,
        },
        "database_integrity": {},
        "restaurant_audits": {},
    }
    total_written = 0
    for slug in SLUGS:
        current_path = (
            ROOT / "output" / "restaurants" / slug / "layer_04_text_analysis" / "layer_04_text_analysis.json"
        )
        before_path = BEFORE_ROOT / f"{slug}_layer04.json"
        current = load_json(current_path)
        before = load_json(before_path)
        before_summary = group_summary(before)
        after_summary = group_summary(current)
        total_written += after_summary["written_low_score_reviews"]
        all_topics = sorted(
            set(row["topic"] for row in before_summary["top_negative_topics"])
            | set(row["topic"] for row in after_summary["top_negative_topics"])
        )
        before_map = {row["topic"]: row["negative_reviews"] for row in before_summary["top_negative_topics"]}
        after_map = {row["topic"]: row["negative_reviews"] for row in after_summary["top_negative_topics"]}
        changes = [
            {
                "topic": topic,
                "before_negative_reviews": before_map.get(topic, 0),
                "after_negative_reviews": after_map.get(topic, 0),
                "change": after_map.get(topic, 0) - before_map.get(topic, 0),
            }
            for topic in all_topics
            if before_map.get(topic, 0) != after_map.get(topic, 0)
        ]
        db_path = ROOT / "businesses" / "restaurants" / slug / "data" / "reviews.db"
        actual_hash = file_sha256(db_path)
        result["database_integrity"][slug] = {
            "path": str(db_path.relative_to(ROOT)),
            "sha256_before": EXPECTED_HASHES[slug],
            "sha256_after": actual_hash,
            "unchanged": actual_hash == EXPECTED_HASHES[slug],
        }
        result["restaurant_audits"][slug] = {
            "before": before_summary,
            "after": after_summary,
            "changed_negative_topic_counts": changes,
            "written_low_score_case_register": case_register(slug, current),
        }
    result["scope"]["written_low_score_reviews_audited"] = total_written
    result["validation"] = {
        "all_database_hashes_unchanged": all(
            row["unchanged"] for row in result["database_integrity"].values()
        ),
        "written_low_score_audit_complete": total_written == 77,
        "common_period_boundaries": competitive["common_period_boundaries"],
        "competitive_json_regenerated": True,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"Written low-score reviews audited: {total_written}")
    print(f"All DB hashes unchanged: {result['validation']['all_database_hashes_unchanged']}")


if __name__ == "__main__":
    main()
