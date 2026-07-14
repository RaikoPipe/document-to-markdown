from __future__ import annotations

from enum import Enum
from pathlib import Path

import pymupdf

from docprep.utils.mime import detect_mime


class ProcessingPath(str, Enum):
    NATIVE_PDF = "native_pdf"
    OFFICE = "office"
    SCANNED = "scanned"
    UNSUPPORTED = "unsupported"


OFFICE_MIMES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/epub+zip",
    "text/html",
    "text/csv",
    "text/plain",
    "text/xml",
    "text/markdown",
}

IMAGE_MIMES = {
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/webp",
    "image/bmp",
    "image/gif",
}


class UnsupportedFormatError(Exception):
    def __init__(self, mime_type: str, file_path: Path):
        self.mime_type = mime_type
        self.file_path = file_path
        super().__init__(f"Unsupported format '{mime_type}' for file: {file_path}")


def classify(file_path: Path) -> ProcessingPath:
    mime = detect_mime(file_path)

    if mime in OFFICE_MIMES:
        return ProcessingPath.OFFICE
    if mime == "application/pdf":
        return _classify_pdf(file_path)
    if mime in IMAGE_MIMES:
        return ProcessingPath.SCANNED
    return ProcessingPath.UNSUPPORTED


def _classify_pdf(file_path: Path, sample_size: int = 5) -> ProcessingPath:
    """Probe first N pages to determine if PDF is native text or scanned."""
    doc = pymupdf.open(str(file_path))
    total_pages = len(doc)
    sample_count = min(sample_size, total_pages)

    scanned_pages = 0
    for i in range(sample_count):
        page = doc[i]
        text = page.get_text().strip()
        images = page.get_images()
        page_area = page.rect.width * page.rect.height

        has_substantial_text = len(text) > 20
        has_images = len(images) > 0

        if not has_substantial_text and (has_images or page_area > 0):
            scanned_pages += 1

    doc.close()

    if sample_count == 0:
        return ProcessingPath.NATIVE_PDF

    if scanned_pages > sample_count * 0.5:
        return ProcessingPath.SCANNED
    return ProcessingPath.NATIVE_PDF
