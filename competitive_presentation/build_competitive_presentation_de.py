"""Build the German localization of the approved competitive report."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

from competitive_presentation.build_competitive_presentation import (
    SKILL_DIR,
    find_node,
    validate_percent_point_axis,
)
from competitive_presentation.build_pdf import build as build_pdf
from competitive_presentation.prepare_presentation_data import build as prepare_data
from localization.de import EVIDENCE_DE, EXACT_DE, PHRASE_DE, REVIEW_TEXT_DE_BY_ID, TOPIC_DE


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output/competitive/restaurants/presentation_de"
FINAL_PDF = OUTPUT_DIR / "al_assiel_competitive_intelligence_de.pdf"
FINAL_PPTX = OUTPUT_DIR / "al_assiel_competitive_intelligence_de.pptx"
QA_DIR = OUTPUT_DIR / "qa"
PACKAGE_PDF = ROOT / "output/final_manager_package/04_Al_Assiel_Competitive_Intelligence_DE.pdf"
ENGLISH_PDF = ROOT / "output/final_manager_package/02_Al_Assiel_Competitive_Intelligence.pdf"
APPROVED_ENGLISH_SHA256 = "05e52843cef8e105f38d13b473418baa3d26dd924efb6244cfb84206a9a12181"

OPEN_REVIEW_DE = "Originalbewertung öffnen →"
UNAVAILABLE_REVIEW_DE = "Link zur Originalbewertung in den Quelldaten nicht verfügbar"
BACK_DE = "← Zurück zur Ausgangsfolie"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def localize_case_excerpts(data: dict) -> None:
    for slug in data["display_order"]:
        for case in data["restaurants"][slug]["recent_low_score_cases"]:
            if case.get("original_language") == "de" and str(case.get("text_original") or "").strip():
                case["analysis_excerpt"] = case["text_original"]
            elif case["review_id"] in REVIEW_TEXT_DE_BY_ID:
                case["analysis_excerpt"] = REVIEW_TEXT_DE_BY_ID[case["review_id"]]


def write_locale_module(path: Path) -> None:
    exact = {**EXACT_DE, **TOPIC_DE, **EVIDENCE_DE}
    pairs = sorted(
        [*TOPIC_DE.items(), *EVIDENCE_DE.items(), *PHRASE_DE],
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
    source = (
        "const exact = new Map(Object.entries(" + json.dumps(exact, ensure_ascii=False) + "));\n"
        "const phrases = " + json.dumps(pairs, ensure_ascii=False) + ";\n"
        "export function translateDe(value) {\n"
        "  const text = String(value ?? '');\n"
        "  if (/^https?:\\/\\//i.test(text)) return text;\n"
        "  if (exact.has(text)) return exact.get(text);\n"
        "  let result = text;\n"
        "  for (const [english, german] of phrases) {\n"
        "    const escaped = english.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');\n"
        "    const left = /^[A-Za-z0-9_]/.test(english) ? '(?<![A-Za-z0-9_])' : '';\n"
        "    const right = /[A-Za-z0-9_]$/.test(english) ? '(?![A-Za-z0-9_])' : '';\n"
        "    result = result.replace(new RegExp(left + escaped + right, 'g'), german);\n"
        "  }\n"
        "  return result;\n"
        "}\n"
    )
    path.write_text(source, encoding="utf-8")


def localized_deck_source() -> str:
    source = (HERE / "deck_source.mjs.txt").read_text(encoding="utf-8")
    source = source.replace(
        'import { Presentation, PresentationFile } from "@oai/artifact-tool";',
        'import { Presentation, PresentationFile } from "@oai/artifact-tool";\nimport { translateDe } from "./locale_de.mjs";',
    )
    source = source.replace('shape.text = String(text ?? "");', 'shape.text = translateDe(String(text ?? ""));')
    source = source.replace(
        'slideMeta.push({ page, title, chapter, kind: opts.kind ?? "main", appendix: opts.appendix ?? null });',
        'slideMeta.push({ page, title: translateDe(title), chapter: translateDe(chapter), kind: opts.kind ?? "main", appendix: opts.appendix ?? null });',
    )
    source = source.replace(
        'function addLink(slide, label, pos, targetKey = null, targetPage = null, url = null, back = false, metadata = {}) {\n  writeText',
        'function addLink(slide, label, pos, targetKey = null, targetPage = null, url = null, back = false, metadata = {}) {\n  label = translateDe(label);\n  writeText',
    )
    source = source.replace(
        '    categories,\n    series,',
        '    categories: categories.map(translateDe),\n    series: series.map(item => ({ ...item, name: translateDe(item.name) })),',
    )
    source = source.replace('"Open original review →"', json.dumps(OPEN_REVIEW_DE, ensure_ascii=False))
    source = source.replace('"Original review link unavailable in source data"', json.dumps(UNAVAILABLE_REVIEW_DE, ensure_ascii=False))
    return source


def validate_layouts_de(slides_dir: Path) -> dict:
    out_of_bounds = []
    undersized = []
    overlap_pages: dict[int, list[str]] = {31: [], 32: []}
    for path in sorted(slides_dir.glob("slide-*.layout.json")):
        layout = json.loads(path.read_text(encoding="utf-8"))
        page = int(layout["slide"]["slide"])
        elements = layout.get("elements", [])
        for element in elements:
            bbox = element.get("bbox")
            if bbox and (bbox[0] < -0.1 or bbox[1] < -0.1 or bbox[0] + bbox[2] > 1280.1 or bbox[1] + bbox[3] > 720.1):
                out_of_bounds.append((page, bbox, element.get("textPreview")))
            style = element.get("resolvedTextStyle", {})
            scale = style.get("autoFitScale")
            size = element.get("resolvedFontSize")
            if scale is not None and scale < 0.82 and size is not None and size < 14:
                undersized.append((page, scale, size, element.get("textPreview")))
        if page in overlap_pages:
            token = "Beispiel-Leitplanke" if page == 31 else "Kandidaten für Feldforschung"
            callout = next((e for e in elements if token in str(e.get("text", ""))), None)
            if callout:
                left, top, width, height = callout["bbox"]
                for element in elements:
                    if element is callout or not element.get("text") or not element.get("bbox"):
                        continue
                    ol, ot, ow, oh = element["bbox"]
                    if left < ol + ow and left + width > ol and top < ot + oh and top + height > ot:
                        overlap_pages[page].append(str(element.get("textPreview")))
    if out_of_bounds or undersized or any(overlap_pages.values()):
        raise RuntimeError(
            f"German layout validation failed: {len(out_of_bounds)} out of bounds; "
            f"{len(undersized)} undersized; overlaps={overlap_pages}"
        )
    return {"layout_pages_checked": 67, "out_of_bounds": 0, "undersized": 0, "overlaps": 0}


def validate_percent_point_axis_de(pptx_path: Path) -> dict:
    with zipfile.ZipFile(pptx_path) as archive:
        charts = [
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.startswith("ppt/slides/charts/chart") and name.endswith(".xml")
        ]
    matches = [
        xml for xml in charts
        if '<c:max val="100"' in xml and '<c:min val="0"' in xml
        and '<c:numFmt formatCode="0\\%"' in xml
    ]
    if len(matches) != 1 or '<c:numFmt formatCode="0%"' in matches[0]:
        raise RuntimeError("German recent-share chart does not preserve the literal 0-100% axis")
    return {"page_8_percentage_point_axis_validated": True}


def main() -> None:
    english_hash = sha256(ENGLISH_PDF)
    if english_hash != APPROVED_ENGLISH_SHA256:
        raise RuntimeError(f"Approved English competitive PDF hash mismatch: {english_hash}")

    scratch = Path(tempfile.gettempdir()) / "codex-presentations" / "german-localization" / "competitive" / "tmp"
    slides_dir = scratch / "slides"
    data_path = scratch / "presentation_data_de.json"
    build_mjs = scratch / "build_de.mjs"
    locale_mjs = scratch / "locale_de.mjs"
    link_manifest = scratch / "link_manifest_de.json"
    slide_list = scratch / "slide_list_de.json"
    review_audit = scratch / "review_link_audit_de.json"
    scratch.mkdir(parents=True, exist_ok=True)
    slides_dir.mkdir(parents=True, exist_ok=True)

    prepare_data(data_path)
    data = json.loads(data_path.read_text(encoding="utf-8"))
    localize_case_excerpts(data)
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_mjs.write_text(localized_deck_source(), encoding="utf-8")
    write_locale_module(locale_mjs)

    node = find_node()
    setup = SKILL_DIR / "container_tools" / "setup_artifact_tool_workspace.mjs"
    run([str(node), str(setup), "--workspace", str(scratch)])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PACKAGE_PDF.parent.mkdir(parents=True, exist_ok=True)
    run([str(node), str(build_mjs), str(data_path), str(slides_dir), str(FINAL_PPTX), str(link_manifest), str(slide_list), str(review_audit)])

    layout_result = validate_layouts_de(slides_dir)
    axis_result = validate_percent_point_axis_de(FINAL_PPTX)
    result = build_pdf(
        slides_dir, link_manifest, slide_list, review_audit, FINAL_PDF, QA_DIR,
        review_labels=(OPEN_REVIEW_DE, UNAVAILABLE_REVIEW_DE), back_label=BACK_DE,
    )
    result.update(layout_result)
    result.update(axis_result)
    shutil.copy2(FINAL_PDF, PACKAGE_PDF)
    if sha256(ENGLISH_PDF) != english_hash:
        raise RuntimeError("Approved English competitive PDF changed during German build")
    (QA_DIR / "build_validation_de.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"German competitive PDF: {FINAL_PDF}")
    print(f"Package PDF: {PACKAGE_PDF}")
    print(f"Pages: {result['page_count']}; internal links: {result['internal_links']}; external links: {result['external_links']}")
    print("Validation: PASS")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"German competitive build failed:\n{exc}") from exc
