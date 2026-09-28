"""Create the inspectable review records consumed by Layers 03 and 04."""

from src.common.text_utils import get_analysis_text, get_text_variants, normalize_text


def prepare_reviews(reviews: list[dict]) -> list[dict]:
    prepared = []
    for review in reviews:
        row = {key: value for key, value in review.items() if key != "raw_json"}
        analysis_text = get_analysis_text(review)
        row["analysis_text"] = analysis_text
        row["normalized_analysis_text"] = normalize_text(analysis_text)
        row["text_variants"] = get_text_variants(review)
        prepared.append(row)
    return prepared
