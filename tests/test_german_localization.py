"""Regression checks for the German presentation localization layer."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from localization.de import localize_tex, translate_de


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "output/final_manager_package"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class GermanLocalizationTests(unittest.TestCase):
    def test_core_management_terms_are_localized(self) -> None:
        self.assertEqual(translate_de("Low"), "Niedrig")
        self.assertEqual(translate_de("Food Quality"), "Speisenqualität")
        self.assertEqual(translate_de("Open original review →"), "Originalbewertung öffnen →")

    def test_urls_and_numeric_values_are_preserved(self) -> None:
        url = "https://example.test/review?id=298&rating=4.5"
        self.assertEqual(translate_de(url), url)
        translated = translate_de("Recent rating: 4.5 from 298 reviews")
        self.assertIn("4.5", translated)
        self.assertIn("298", translated)

    def test_tex_commands_and_identifiers_are_not_corrupted(self) -> None:
        source = (
            r"\hypersetup{pdfhighlight=/N} "
            r"\newcommand{\RecentThirtyAverage}{3.93} "
            r"Dish Dishes All reviews"
        )
        localized = localize_tex(source)
        self.assertIn("pdfhighlight", localized)
        self.assertIn(r"\RecentThirtyAverage", localized)
        self.assertIn("Gericht", localized)
        self.assertIn("Gerichte", localized)
        self.assertIn("Alle Bewertungen", localized)
        self.assertNotIn("pdfhochlight", localized)
        self.assertNotIn("Gerichtes", localized)
        self.assertNotIn("Allee", localized)

    def test_known_generated_copy_leaks_are_localized(self) -> None:
        source = (
            r"CHAPTER 4 | 3.27/week | Latest 30d cadence | "
            r"Delicious appetizer platter and delectable desserts, followed by Arabic mocha. | "
            r"Burgers \& Western Dishes"
        )
        localized = localize_tex(source)
        self.assertIn("KAPITEL 4", localized)
        self.assertIn("3.27/Woche", localized)
        self.assertIn("Frequenz", localized)
        self.assertIn("Vorspeisenplatte", localized)
        self.assertIn(r"Burger \& westliche Gerichte", localized)
        for leak in ("CHAPTER", "/week", "cadence", "appetizer platter", "Western Dishes"):
            self.assertNotIn(leak, localized)

    def test_approved_english_competitive_pdf_is_unchanged(self) -> None:
        path = PACKAGE / "02_Al_Assiel_Competitive_Intelligence.pdf"
        if not path.exists():
            self.skipTest("Final manager package is not present")
        self.assertEqual(
            sha256(path),
            "05e52843cef8e105f38d13b473418baa3d26dd924efb6244cfb84206a9a12181",
        )

    def test_german_pdf_page_counts_match_english(self) -> None:
        try:
            from pypdf import PdfReader
        except ImportError:
            self.skipTest("pypdf is not installed")
        pairs = [
            ("01_Al_Assiel_Management_Review.pdf", "03_Al_Assiel_Management_Review_DE.pdf", 106),
            ("02_Al_Assiel_Competitive_Intelligence.pdf", "04_Al_Assiel_Competitive_Intelligence_DE.pdf", 67),
        ]
        if not all((PACKAGE / name).exists() for pair in pairs for name in pair[:2]):
            self.skipTest("Final manager package is not present")
        for english, german, expected in pairs:
            self.assertEqual(len(PdfReader(PACKAGE / english).pages), expected)
            self.assertEqual(len(PdfReader(PACKAGE / german).pages), expected)

    def test_competitive_layout_has_no_boundary_replacement_corruption(self) -> None:
        slides = (
            Path(tempfile.gettempdir())
            / "codex-presentations/german-localization/competitive/tmp/slides"
        )
        layouts = sorted(slides.glob("slide-*.layout.json"))
        if not layouts:
            self.skipTest("German competitive layout QA files are not present")
        text = "\n".join(
            str(element.get("text") or "")
            for path in layouts
            for element in json.loads(path.read_text(encoding="utf-8")).get("elements", [])
        )
        for corrupted in ("Lieferundo", "invenbisry", "aggregabisr", "pdfhochlight"):
            self.assertNotIn(corrupted, text)


if __name__ == "__main__":
    unittest.main()
