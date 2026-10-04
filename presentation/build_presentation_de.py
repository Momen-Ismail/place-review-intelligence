"""Build the German localization of the validated Al Assiel management report."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from localization.de import QUOTE_DE, REVIEW_TEXT_DE_BY_ID, localize_tex, translate_de
from presentation import build_presentation as en


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output/restaurants/al_assiel/presentation_de"
ASSET_DIR = OUTPUT_DIR / "assets"
RENDER_DIR = ASSET_DIR / "rendered_slides"
QA_DIR = OUTPUT_DIR / "qa"
SOURCE_TEX = OUTPUT_DIR / "manager_presentation_de.tex"
DATA_TEX = OUTPUT_DIR / "presentation_data.tex"
APPENDIX_TEX = OUTPUT_DIR / "presentation_appendix.tex"
QUOTE_MANIFEST = ASSET_DIR / "quote_manifest.json"
FINAL_PDF = OUTPUT_DIR / "al_assiel_review_intelligence_presentation_de.pdf"
PACKAGE_PDF = ROOT / "output/final_manager_package/03_Al_Assiel_Management_Review_DE.pdf"
ENGLISH_PDF = ROOT / "output/final_manager_package/01_Al_Assiel_Management_Review.pdf"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def german_review_text(record: dict) -> str:
    if record.get("original_language") == "de" and en.normalize_text(record.get("text_original")):
        original = record["text_original"]
        if original.strip() != "Original-language excerpt available at source; no English analysis translation is available.":
            return original
        return translate_de(original.strip())
    manual = REVIEW_TEXT_DE_BY_ID.get(record["review_id"])
    if manual:
        return manual
    return translate_de(record.get("text_translated") or record.get("text_original") or "")


def truncate_german_words(value: str, limit: int = 28) -> str:
    """Truncate German copy while omitting non-Latin fragments safely."""
    clean = en.normalize_text(value).replace("الأصيل", "Al Assiel")
    clean = "".join(
        " " if unicodedata.category(char).startswith("L") and ord(char) > 0x024F else char
        for char in clean
    )
    clean = "".join(char for char in clean if unicodedata.category(char) not in {"So", "Cs"})
    words = clean.split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit]) + " ..."


def build_case_records_de(layer_04: dict, reviews: dict[str, dict]) -> dict[str, dict]:
    records = ORIGINAL_BUILD_CASE_RECORDS(layer_04, reviews)
    for review_id, record in records.items():
        if record["written"]:
            record["excerpt"] = truncate_german_words(german_review_text(reviews[review_id]), 27)
        record["language_label"] = {
            "de": "Deutsch", "ar": "Arabisch", "fr": "Französisch",
            "nl": "Niederländisch", "en": "Englisch",
        }.get(record.get("original_language"), "Unbekannt")
    return records


ORIGINAL_BUILD_CASE_RECORDS = en.build_case_records


def review_excerpt_replacements(reviews: dict[str, dict]) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for record in reviews.values():
        english = record.get("text_translated") or record.get("text_original") or ""
        german = QUOTE_DE.get(english, german_review_text(record))
        if english and german:
            if english.strip() == german.strip():
                continue
            for limit in (22, 27):
                replacements[en.tex_escape(en.truncate_words(english, limit))] = en.tex_escape(
                    truncate_german_words(german, limit)
                )
    return replacements


def localize_csv_assets() -> None:
    for path in ASSET_DIR.glob("*.csv"):
        rows = list(csv.reader(path.open(encoding="utf-8")))
        localized = [rows[0]] if rows else []
        translatable_values = {"Historical", "Previous90", "Recent90", "Positive", "Neutral", "Negative"}
        for row in rows[1:]:
            localized.append([
                translate_de(cell) if cell in translatable_values else cell
                for cell in row
            ])
        with path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows(localized)


def compile_pdf() -> tuple[str, list[str]]:
    compiler = shutil.which("latexmk") or shutil.which("lualatex")
    if not compiler:
        raise RuntimeError("LuaLaTeX is required to build the German management report")
    with tempfile.TemporaryDirectory(prefix="al_assiel_management_de_") as build_dir:
        build = Path(build_dir)
        tex_cache = build / "tex-cache"
        tex_cache.mkdir()
        environment = os.environ.copy()
        environment["TEXMFVAR"] = str(tex_cache)
        environment["TEXMFCACHE"] = str(tex_cache)
        if Path(compiler).name == "latexmk":
            command = [compiler, "-lualatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-outdir={build}", str(SOURCE_TEX)]
            compiler_name = "latexmk with LuaLaTeX"
        else:
            command = [compiler, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", f"-output-directory={build}", str(SOURCE_TEX)]
            compiler_name = "LuaLaTeX"
        result = subprocess.run(command, cwd=OUTPUT_DIR, env=environment, text=True, capture_output=True)
        log = build / "manager_presentation_de.log"
        if result.returncode:
            detail = log.read_text(errors="replace")[-7000:] if log.exists() else result.stdout[-7000:] + result.stderr[-2000:]
            raise RuntimeError(f"German LaTeX compilation failed:\n{detail}")
        built_pdf = build / "manager_presentation_de.pdf"
        if not built_pdf.exists():
            raise RuntimeError("German LaTeX build did not produce a PDF")
        warnings = [line.strip() for line in log.read_text(errors="replace").splitlines() if "Overfull" in line] if log.exists() else []
        QA_DIR.mkdir(parents=True, exist_ok=True)
        if log.exists():
            shutil.copy2(log, QA_DIR / "manager_presentation_de.log")
        shutil.copy2(built_pdf, FINAL_PDF)
    return compiler_name, warnings


def main() -> None:
    english_hash = sha256(ENGLISH_PDF)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    PACKAGE_PDF.parent.mkdir(parents=True, exist_ok=True)

    layer_05 = json.loads(en.LAYER_05_JSON.read_text(encoding="utf-8"))
    layer_04 = json.loads(en.LAYER_04_JSON.read_text(encoding="utf-8"))
    profile = json.loads(en.PROFILE_JSON.read_text(encoding="utf-8"))
    reviews = en.load_reviews_read_only()
    en.validate_analysis(layer_05, layer_04, profile, reviews)
    recent_start = en.datetime.fromisoformat(layer_05["trends"]["summary"]["recent_90d_start"])
    quotes = en.select_quotes(layer_04, reviews, recent_start)
    for quote in quotes.values():
        quote["text"] = QUOTE_DE.get(quote["text"], translate_de(quote["text"]))
        quote["metadata"] = translate_de(quote["metadata"])

    original_constants = {
        name: getattr(en, name) for name in (
            "OUTPUT_DIR", "ASSET_DIR", "RENDER_DIR", "DATA_TEX", "QUOTE_MANIFEST",
            "FINAL_PDF", "APPENDIX_TEX", "SOURCE_TEX", "build_case_records",
        )
    }
    try:
        en.OUTPUT_DIR = OUTPUT_DIR
        en.ASSET_DIR = ASSET_DIR
        en.RENDER_DIR = RENDER_DIR
        en.DATA_TEX = DATA_TEX
        en.QUOTE_MANIFEST = QUOTE_MANIFEST
        en.FINAL_PDF = FINAL_PDF
        en.APPENDIX_TEX = APPENDIX_TEX
        en.SOURCE_TEX = SOURCE_TEX
        en.build_case_records = build_case_records_de

        en.generate_data(layer_05, layer_04, profile, reviews, quotes)
        appendix_slides = en.generate_appendix(layer_05, layer_04, reviews)
        replacements = review_excerpt_replacements(reviews)
        DATA_TEX.write_text(localize_tex(DATA_TEX.read_text(encoding="utf-8"), replacements), encoding="utf-8")
        APPENDIX_TEX.write_text(localize_tex(APPENDIX_TEX.read_text(encoding="utf-8"), replacements), encoding="utf-8")
        SOURCE_TEX.write_text(localize_tex(en.ROOT.joinpath("presentation/manager_presentation.tex").read_text(encoding="utf-8")), encoding="utf-8")
        SOURCE_TEX.write_text(
            SOURCE_TEX.read_text(encoding="utf-8")
            .replace(
                "symbolic x coords={Positive,Neutral,Negative},xtick=data,",
                "symbolic x coords={Positive,Neutral,Negative},xtick=data,xticklabels={Positiv,Neutral,Negativ},",
            )
            .replace(r"\fontsize{7.7}{9.2}\selectfont\itshape", r"\fontsize{7.1}{8.2}\selectfont\itshape")
            .replace(r"\fontsize{5.9}{7}\selectfont", r"\fontsize{5.4}{6.2}\selectfont"),
            encoding="utf-8",
        )

        internal_links, slide_count = en.validate_internal_links()
        external_links = en.validate_external_links()
        compiler, warnings = compile_pdf()
        renderer, rendered = en.render_pdf(slide_count)
        shutil.copy2(FINAL_PDF, PACKAGE_PDF)
    finally:
        for name, value in original_constants.items():
            setattr(en, name, value)

    if sha256(ENGLISH_PDF) != english_hash:
        raise RuntimeError("Approved English management PDF changed during German build")
    print(f"German management PDF: {FINAL_PDF}")
    print(f"Package PDF: {PACKAGE_PDF}")
    print(f"Slides: {slide_count}; rendered: {rendered}; appendix: {appendix_slides}")
    print(f"Internal links: {internal_links}; external links: {external_links}")
    print(f"Compiler: {compiler}; renderer: {renderer}; overfull warnings: {len(warnings)}")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, RuntimeError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        raise SystemExit(f"German management build failed:\n{exc}") from exc
