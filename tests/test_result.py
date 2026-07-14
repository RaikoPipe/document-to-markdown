from __future__ import annotations

from pathlib import Path

from docprep.result import ConversionResult


def test_conversion_result():
    result = ConversionResult(
        source_path=Path("test.pdf"),
        markdown="# Hello",
        format_detected="application/pdf",
        pipeline_used="standard",
        page_count=1,
        escalated=False,
        processing_time_seconds=0.5,
    )
    assert result.markdown == "# Hello"
    assert result.warnings == []


def test_to_dict():
    result = ConversionResult(
        source_path=Path("test.pdf"),
        markdown="content",
        format_detected="application/pdf",
        pipeline_used="standard",
        page_count=3,
        escalated=True,
        processing_time_seconds=1.2,
        warnings=["escalated"],
    )
    d = result.to_dict()
    assert d["source_path"] == "test.pdf"
    assert d["page_count"] == 3
    assert d["escalated"] is True
    assert d["warnings"] == ["escalated"]
