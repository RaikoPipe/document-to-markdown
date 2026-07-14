from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def native_pdf(tmp_path: Path) -> Path:
    """Create a minimal PDF with selectable text."""
    path = tmp_path / "native.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello, this is a test document with native text content.\n" * 10)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def scanned_pdf(tmp_path: Path) -> Path:
    """Create a minimal PDF that looks like a scan (image, no text)."""
    path = tmp_path / "scanned.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    img_rect = pymupdf.Rect(0, 0, page.rect.width, page.rect.height)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 100), 1)
    pix.set_rect(pix.irect, (200, 200, 200))
    page.insert_image(img_rect, pixmap=pix)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def plain_text_file(tmp_path: Path) -> Path:
    path = tmp_path / "test.txt"
    path.write_text("This is a plain text test file.\nLine two.\n")
    return path


@pytest.fixture
def png_image(tmp_path: Path) -> Path:
    """Create a minimal PNG image."""
    path = tmp_path / "test.png"
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 100), 1)
    pix.set_rect(pix.irect, (128, 128, 128))
    pix.save(str(path))
    return path
