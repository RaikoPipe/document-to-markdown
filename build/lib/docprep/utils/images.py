from __future__ import annotations

from pathlib import Path

import pymupdf


def pdf_to_images(pdf_path: Path, dpi: int = 200) -> list[tuple[bytes, str]]:
    """Render each PDF page to a PNG image. Returns list of (image_bytes, mime_type)."""
    doc = pymupdf.open(str(pdf_path))
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        images.append((pix.tobytes("png"), "image/png"))
    doc.close()
    return images


def get_page_count(file_path: Path) -> int | None:
    """Return page count for PDFs, None for other formats."""
    try:
        doc = pymupdf.open(str(file_path))
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return None
