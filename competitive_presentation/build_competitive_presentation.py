"""One-command build for the standalone competitive-intelligence report."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from build_pdf import build as build_pdf
from prepare_presentation_data import build as prepare_data


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output" / "competitive" / "restaurants" / "presentation"
FINAL_PDF = OUTPUT_DIR / "al_assiel_competitive_intelligence.pdf"
FINAL_PPTX = OUTPUT_DIR / "al_assiel_competitive_intelligence.pptx"
QA_DIR = OUTPUT_DIR / "qa"
EXISTING_MANAGEMENT_PDF = ROOT / "output" / "restaurants" / "al_assiel" / "presentation" / "al_assiel_review_intelligence_presentation.pdf"
SKILL_DIR = Path("/Users/momenismail/.codex/plugins/cache/openai-primary-runtime/presentations/26.630.12135/skills/presentations")


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_node() -> Path:
    candidates = [
        shutil.which("node"),
        "/Applications/Codex.app/Contents/Resources/cua_node/bin/node",
        "/Applications/RStudio.app/Contents/Resources/app/bin/node/bin/node",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise RuntimeError("Node.js runtime not found; @oai/artifact-tool cannot run")


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def validate_layouts(slides_dir: Path) -> dict:
    out_of_bounds = []
    undersized_autofit = []
    page_31_overlaps = []
    page_32_overlaps = []
    al_assiel_google_presence_confirmed = False
    layout_files = sorted(slides_dir.glob("slide-*.layout.json"))
    for path in layout_files:
        layout = json.loads(path.read_text(encoding="utf-8"))
        page = layout["slide"]["slide"]
        for element in layout.get("elements", []):
            bbox = element.get("bbox")
            if bbox and (
                bbox[0] < -0.1
                or bbox[1] < -0.1
                or bbox[0] + bbox[2] > 1280.1
                or bbox[1] + bbox[3] > 720.1
            ):
                out_of_bounds.append({"page": page, "bbox": bbox, "text": element.get("textPreview")})
            style = element.get("resolvedTextStyle", {})
            scale = style.get("autoFitScale")
            size = element.get("resolvedFontSize")
            if scale is not None and scale < 0.9 and size is not None and size < 16:
                undersized_autofit.append(
                    {"page": page, "scale": scale, "font_size": size, "text": element.get("textPreview")}
                )
        if page in {31, 32}:
            elements = layout.get("elements", [])
            target_text = "Example guardrail" if page == 31 else "Field-research candidates"
            callout = next(
                (element for element in elements if target_text in element.get("text", "")),
                None,
            )
            if callout is None:
                raise RuntimeError(f"Page {page} callout was not found")
            left, top, width, height = callout["bbox"]
            for element in elements:
                if element is callout or not element.get("text") or not element.get("bbox"):
                    continue
                other_left, other_top, other_width, other_height = element["bbox"]
                overlaps = (
                    left < other_left + other_width
                    and left + width > other_left
                    and top < other_top + other_height
                    and top + height > other_top
                )
                if overlaps:
                    (page_31_overlaps if page == 31 else page_32_overlaps).append(element.get("textPreview"))
        if page == 60:
            elements = layout.get("elements", [])
            google_label = next(
                (element for element in elements if element.get("text", "") == "Google Presence"),
                None,
            )
            if google_label is None:
                raise RuntimeError("Page 60 Google Presence row was not found")
            row_top = google_label["bbox"][1]
            al_assiel_google_presence_confirmed = any(
                element.get("text", "").lower() == "confirmed"
                and 285 <= element.get("bbox", [0])[0] < 520
                and abs(element.get("bbox", [0, 0])[1] - row_top) <= 8
                for element in elements
            )
    if (
        out_of_bounds
        or undersized_autofit
        or page_31_overlaps
        or page_32_overlaps
        or not al_assiel_google_presence_confirmed
    ):
        raise RuntimeError(
            f"Layout validation failed: {len(out_of_bounds)} out-of-bounds; "
            f"{len(undersized_autofit)} auto-shrunk below 16 pt; "
            f"{len(page_31_overlaps)} page-31 guardrail overlaps; "
            f"{len(page_32_overlaps)} page-32 disclaimer overlaps; "
            f"Al Assiel Google Presence confirmed={al_assiel_google_presence_confirmed}"
        )
    return {
        "layout_pages_checked": len(layout_files),
        "out_of_bounds_elements": 0,
        "auto_shrunk_body_under_16": 0,
        "page_31_guardrail_overlaps": 0,
        "page_32_disclaimer_overlaps": 0,
        "al_assiel_google_presence_confirmed": True,
    }


def validate_percent_point_axis(pptx_path: Path) -> dict:
    with zipfile.ZipFile(pptx_path) as archive:
        chart_xml = [
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.startswith("ppt/slides/charts/chart") and name.endswith(".xml")
        ]
    matches = [xml for xml in chart_xml if "5-star share" in xml and "1–2-star share" in xml]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one recent-share chart; found {len(matches)}")
    xml = matches[0]
    if '<c:max val="100"' not in xml or '<c:min val="0"' not in xml:
        raise RuntimeError("Recent-share chart axis is not fixed to 0–100 percentage points")
    if '<c:numFmt formatCode="0\\%"' not in xml:
        raise RuntimeError("Recent-share chart does not use a literal percent-sign axis format")
    if '<c:numFmt formatCode="0%"' in xml:
        raise RuntimeError("Recent-share chart still uses the percent-multiplying formatter")
    return {
        "page_8_percentage_point_axis_validated": True,
        "page_8_axis_labels_expected": ["0%", "20%", "40%", "60%", "80%", "100%"],
    }


def main() -> None:
    before_management_hash = sha256(EXISTING_MANAGEMENT_PDF)
    run([sys.executable, str(ROOT / "scripts" / "generate_phase_a_accuracy_audit.py")])

    scratch = Path(tempfile.gettempdir()) / "codex-presentations" / "manual-20260923" / "competitive-intelligence" / "tmp"
    slides_dir = scratch / "slides"
    data_path = scratch / "presentation_data.json"
    build_mjs = scratch / "build.mjs"
    link_manifest = scratch / "link_manifest.json"
    slide_list = scratch / "slide_list.json"
    review_audit = scratch / "review_link_audit.json"
    scratch.mkdir(parents=True, exist_ok=True)
    slides_dir.mkdir(parents=True, exist_ok=True)
    prepare_data(data_path)

    node = find_node()
    setup = SKILL_DIR / "container_tools" / "setup_artifact_tool_workspace.mjs"
    run([str(node), str(setup), "--workspace", str(scratch)])
    shutil.copyfile(HERE / "deck_source.mjs.txt", build_mjs)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run(
        [
            str(node),
            str(build_mjs),
            str(data_path),
            str(slides_dir),
            str(FINAL_PPTX),
            str(link_manifest),
            str(slide_list),
            str(review_audit),
        ]
    )

    layout_validation = validate_layouts(slides_dir)
    percent_axis_validation = validate_percent_point_axis(FINAL_PPTX)
    result = build_pdf(slides_dir, link_manifest, slide_list, review_audit, FINAL_PDF, QA_DIR)
    result.update(layout_validation)
    result.update(percent_axis_validation)
    after_management_hash = sha256(EXISTING_MANAGEMENT_PDF)
    if before_management_hash != after_management_hash:
        raise RuntimeError("Existing Al Assiel management PDF changed during build")
    result["existing_management_pdf_unchanged"] = True
    result["pptx"] = str(FINAL_PPTX)
    result["slide_list"] = json.loads(slide_list.read_text(encoding="utf-8"))
    (QA_DIR / "build_validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Final PDF: {FINAL_PDF}")
    print(f"Final PPTX: {FINAL_PPTX}")
    print(f"Pages: {result['page_count']}")
    print(f"Internal links: {result['internal_links']}")
    print(f"External review links: {result['external_links']}")
    print(f"Quoted reviews: {result['quoted_reviews']}")
    print(f"Unavailable source URLs: {result['reviews_without_source_url']}")
    print("Validation: PASS")


if __name__ == "__main__":
    main()
