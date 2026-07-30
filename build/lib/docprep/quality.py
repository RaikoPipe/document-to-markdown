from __future__ import annotations

from docprep.config import PipelineConfig


def should_escalate(
    markdown: str,
    page_count: int | None,
    config: PipelineConfig,
    mime_type: str | None = None,
) -> bool:
    """Return True if conversion output is too poor to use and should fall back to VLM API.

    The chars/page density check is only applied to PDFs (and unknown formats
    where mime_type is None, conservatively). For office formats (XLSX, PPTX,
    DOCX, etc.), pymupdf's "page count" does not represent real pages and would
    cause false escalations. The garbled-ratio and empty-output checks always apply.
    """
    if not markdown or not markdown.strip():
        return True

    stripped = markdown.strip()

    if (
        mime_type in (None, "application/pdf")
        and page_count
        and page_count > 0
    ):
        chars_per_page = len(stripped) / page_count
        if chars_per_page < config.quality_min_chars_per_page:
            return True

    if len(stripped) > 0:
        printable = sum(1 for c in stripped if c.isprintable() or c in "\n\t")
        garbled_ratio = 1.0 - (printable / len(stripped))
        if garbled_ratio > config.quality_max_garbled_ratio:
            return True

    return False
