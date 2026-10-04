"""Assemble rendered slide images into a linked PDF and validate it."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from urllib.parse import urlparse

import pypdfium2 as pdfium
from PIL import Image, ImageChops, ImageDraw
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link


SLIDE_W = 1280.0
SLIDE_H = 720.0


def _slide_images(slides_dir: Path) -> list[Path]:
    return sorted(slides_dir.glob("slide-*.png"))


def _pdf_rect(rect: dict, page_width: float, page_height: float) -> tuple[float, float, float, float]:
    x0 = rect["left"] / SLIDE_W * page_width
    x1 = (rect["left"] + rect["width"]) / SLIDE_W * page_width
    y0 = (SLIDE_H - rect["top"] - rect["height"]) / SLIDE_H * page_height
    y1 = (SLIDE_H - rect["top"]) / SLIDE_H * page_height
    return (x0, y0, x1, y1)


def _valid_public_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _validate_review_audit(
    slides_dir: Path,
    links: list[dict],
    audit_path: Path,
    review_labels: tuple[str, str] = (
        "Open original review →",
        "Original review link unavailable in source data",
    ),
) -> tuple[list[dict], dict]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if not audit:
        raise RuntimeError("Review-link audit is empty")

    linked = [row for row in audit if row.get("status") == "linked"]
    unavailable = [row for row in audit if row.get("status") == "unavailable"]
    if len(linked) + len(unavailable) != len(audit):
        raise RuntimeError("Review-link audit contains an unknown status")
    if any(not _valid_public_url(row.get("url")) for row in linked):
        raise RuntimeError("A linked review does not have a valid public HTTP(S) URL")
    if any(row.get("url") is not None for row in unavailable):
        raise RuntimeError("An unavailable review-link row unexpectedly contains a URL")

    placeholder_tokens = ("placeholder", "example.com", "localhost", "127.0.0.1")
    placeholder_urls = [row["url"] for row in linked if any(token in row["url"].lower() for token in placeholder_tokens)]
    if placeholder_urls:
        raise RuntimeError(f"Placeholder review URLs found: {placeholder_urls}")

    review_links = [row for row in links if row.get("kind") == "original_review"]
    expected_manifest = Counter((int(row["page"]), row["case_id"], row["url"]) for row in linked)
    actual_manifest = Counter((int(row["page"]), row.get("caseId"), row.get("url")) for row in review_links)
    if expected_manifest != actual_manifest:
        raise RuntimeError("Visible review-link audit does not match the external-link manifest")

    for page in sorted({int(row["page"]) for row in audit}):
        layout_path = slides_dir / f"slide-{page:02d}.layout.json"
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        previews = [str(element.get("textPreview", "")) for element in layout.get("elements", [])]
        for label in review_labels:
            expected = sum(1 for row in audit if int(row["page"]) == page and row["label"] == label)
            visible = sum(1 for text in previews if label in text)
            if expected != visible:
                raise RuntimeError(
                    f"Page {page} visible label count for {label!r} is {visible}; expected {expected}"
                )

    return audit, {
        "quoted_reviews": len(audit),
        "valid_original_review_links": len(linked),
        "reviews_without_source_url": len(unavailable),
        "placeholder_review_urls": 0,
        "review_link_label_validation": True,
    }


def build(
    slides_dir: Path,
    link_manifest_path: Path,
    slide_list_path: Path,
    review_audit_path: Path,
    output_pdf: Path,
    qa_dir: Path,
    *,
    review_labels: tuple[str, str] = (
        "Open original review →",
        "Original review link unavailable in source data",
    ),
    back_label: str = "← Back to source slide",
) -> dict:
    images = _slide_images(slides_dir)
    slides = json.loads(slide_list_path.read_text(encoding="utf-8"))
    links = json.loads(link_manifest_path.read_text(encoding="utf-8"))
    review_audit, review_validation = _validate_review_audit(
        slides_dir, links, review_audit_path, review_labels
    )
    if len(images) != len(slides):
        raise RuntimeError(f"Rendered images ({len(images)}) != slide list ({len(slides)})")
    if not images:
        raise RuntimeError("No rendered slides were found")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    base_pdf = qa_dir / "unlinked_slides.pdf"
    rgb_images = [Image.open(image).convert("RGB") for image in images]
    rgb_images[0].save(base_pdf, "PDF", save_all=True, append_images=rgb_images[1:], resolution=144.0)
    for image in rgb_images:
        image.close()

    reader = PdfReader(base_pdf)
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    internal_count = 0
    external_count = 0
    for item in links:
        page_index = int(item["page"]) - 1
        if not 0 <= page_index < len(writer.pages):
            raise RuntimeError(f"Invalid source page in link: {item}")
        page = writer.pages[page_index]
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        rect = _pdf_rect(item["rect"], page_width, page_height)
        if item.get("url"):
            if not item["url"].startswith(("http://", "https://")):
                raise RuntimeError(f"Invalid external URL: {item['url']}")
            annotation = Link(rect=rect, url=item["url"], border=[0, 0, 0])
            external_count += 1
        else:
            target_index = int(item["targetPage"]) - 1
            if not 0 <= target_index < len(writer.pages):
                raise RuntimeError(f"Invalid internal target: {item}")
            annotation = Link(rect=rect, target_page_index=target_index, border=[0, 0, 0])
            internal_count += 1
        writer.add_annotation(page_number=page_index, annotation=annotation)
    with output_pdf.open("wb") as handle:
        writer.write(handle)

    final_reader = PdfReader(output_pdf)
    if len(final_reader.pages) != len(images):
        raise RuntimeError("Final PDF page count mismatch")
    annotation_count = sum(len(page.get("/Annots", [])) for page in final_reader.pages)
    if annotation_count != len(links):
        raise RuntimeError(f"PDF annotations ({annotation_count}) != manifest links ({len(links)})")
    pdf_uris = []
    for page_number, page in enumerate(final_reader.pages, 1):
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            action = annotation.get("/A")
            if action is not None:
                action = action.get_object()
            if action and str(action.get("/S")) == "/URI":
                pdf_uris.append((page_number, str(action.get("/URI"))))
    expected_review_uris = Counter((int(row["page"]), row["url"]) for row in review_audit if row["status"] == "linked")
    actual_review_uris = Counter(pdf_uris)
    if actual_review_uris != expected_review_uris:
        raise RuntimeError("Final PDF URI annotations do not match the validated review URLs")

    rendered_dir = qa_dir / "rendered_pages"
    rendered_dir.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(str(output_pdf))
    rendered_paths = []
    for index in range(len(pdf)):
        bitmap = pdf[index].render(scale=1.0)
        image = bitmap.to_pil().convert("RGB")
        out = rendered_dir / f"page-{index + 1:03d}.png"
        image.save(out)
        rendered_paths.append(out)
    pdf.close()

    # Automated visual sanity: all pages must contain substantial non-white content.
    blank_pages = []
    for index, image_path in enumerate(rendered_paths, 1):
        image = Image.open(image_path).convert("RGB")
        white = Image.new("RGB", image.size, "white")
        bbox = ImageChops.difference(image, white).getbbox()
        if bbox is None or (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) < image.width * image.height * 0.04:
            blank_pages.append(index)
        image.close()
    if blank_pages:
        raise RuntimeError(f"Blank or near-blank rendered pages: {blank_pages}")

    thumb_w, thumb_h, cols = 320, 180, 4
    rows = (len(rendered_paths) + cols - 1) // cols
    montage = Image.new("RGB", (thumb_w * cols, thumb_h * rows), "#D9DEE5")
    draw = ImageDraw.Draw(montage)
    for index, image_path in enumerate(rendered_paths):
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        x = (index % cols) * thumb_w
        y = (index // cols) * thumb_h
        montage.paste(image, (x, y))
        draw.rectangle((x + 3, y + 3, x + 46, y + 24), fill="#0B1F33")
        draw.text((x + 10, y + 7), str(index + 1), fill="white")
        image.close()
    montage_path = qa_dir / "all_pages_montage.png"
    montage.save(montage_path)

    result = {
        "pdf": str(output_pdf),
        "page_count": len(images),
        "internal_links": internal_count,
        "external_links": external_count,
        "back_links": sum(1 for row in links if row.get("label") == back_label),
        "total_annotations": annotation_count,
        "all_pages_rendered": len(rendered_paths),
        "blank_pages": blank_pages,
        "montage": str(montage_path),
        "status": "PASS",
        **review_validation,
    }
    (qa_dir / "pdf_validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--slides-dir", type=Path, required=True)
    parser.add_argument("--link-manifest", type=Path, required=True)
    parser.add_argument("--slide-list", type=Path, required=True)
    parser.add_argument("--review-audit", type=Path, required=True)
    parser.add_argument("--output-pdf", type=Path, required=True)
    parser.add_argument("--qa-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.slides_dir, args.link_manifest, args.slide_list, args.review_audit, args.output_pdf, args.qa_dir), indent=2))
