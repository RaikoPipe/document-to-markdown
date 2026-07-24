from __future__ import annotations

from docprep.config import PipelineConfig
from docprep.quality import should_escalate

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_empty_string():
    assert should_escalate("", None, PipelineConfig()) is True


def test_whitespace_only():
    assert should_escalate("   \n\n  ", None, PipelineConfig()) is True


def test_none_input():
    assert should_escalate(None, None, PipelineConfig()) is True


def test_good_output():
    md = "# Title\n\nThis is a paragraph with enough content.\n" * 5
    assert should_escalate(md, 1, PipelineConfig()) is False


def test_low_density():
    config = PipelineConfig(quality_min_chars_per_page=50)
    assert should_escalate("Short", 1, config) is True


def test_low_density_many_pages():
    config = PipelineConfig(quality_min_chars_per_page=50)
    assert should_escalate("x" * 100, 10, config) is True


def test_no_page_count_skips_density():
    config = PipelineConfig(quality_min_chars_per_page=50)
    assert should_escalate("Short text", None, config) is False


def test_garbled_output():
    config = PipelineConfig(quality_max_garbled_ratio=0.20)
    garbled = "\x00\x01\x02\x03\x04" * 20 + "abc"
    assert should_escalate(garbled, None, config) is True


def test_acceptable_non_ascii():
    config = PipelineConfig(quality_max_garbled_ratio=0.20)
    text = "Hëllo wörld — this is fine unicode" * 10
    assert should_escalate(text, 1, config) is False


def test_office_format_skips_density():
    """Office formats should not trigger density check (page count is unreliable)."""
    config = PipelineConfig(quality_min_chars_per_page=50)
    # 100 chars / 708 "pages" = 0.14 chars/page — would fail for PDFs
    assert should_escalate("x" * 100, 708, config, mime_type=XLSX_MIME) is False


def test_pdf_low_density_still_escalates():
    """PDFs should still trigger density check."""
    config = PipelineConfig(quality_min_chars_per_page=50)
    assert should_escalate("x" * 100, 10, config, mime_type="application/pdf") is True


def test_office_format_garbled_still_escalates():
    """Office formats should still trigger garbled-ratio check."""
    config = PipelineConfig(quality_max_garbled_ratio=0.20)
    garbled = "\x00\x01\x02\x03\x04" * 20 + "abc"
    assert should_escalate(garbled, 708, config, mime_type=XLSX_MIME) is True


def test_office_format_empty_still_escalates():
    """Empty output should escalate regardless of format."""
    assert should_escalate("", 708, PipelineConfig(), mime_type=XLSX_MIME) is True
