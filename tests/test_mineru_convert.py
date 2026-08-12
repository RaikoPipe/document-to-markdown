from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from docprep.config import PipelineConfig
from docprep.paths.mineru_convert import _strip_image_references, convert_mineru


def test_config_defaults_mineru():
    config = PipelineConfig()
    assert config.mineru_enabled is False
    assert config.mineru_backend == "hybrid-engine"
    assert config.mineru_effort == "medium"
    assert config.mineru_language == "ch"
    assert config.mineru_parse_method == "auto"
    assert config.mineru_formula_enable is True
    assert config.mineru_table_enable is True
    assert config.mineru_image_analysis is True
    assert config.mineru_api_url is None
    assert config.mineru_server_url is None
    assert config.mineru_start_page_id == 0
    assert config.mineru_end_page_id is None
    assert config.mineru_timeout_seconds == 600
    assert config.mineru_strip_images is True


def test_config_from_yaml_mineru(tmp_path: Path):
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        """
mineru:
  enabled: true
  backend: pipeline
  effort: high
  language: korean
  parse_method: ocr
  formula_enable: false
  table_enable: false
  image_analysis: false
  api_url: http://localhost:8000
  server_url: http://localhost:30000
  start_page_id: 2
  end_page_id: 10
  timeout_seconds: 120
  strip_images: false
"""
    )
    config = PipelineConfig.from_yaml(yaml_path)
    assert config.mineru_enabled is True
    assert config.mineru_backend == "pipeline"
    assert config.mineru_effort == "high"
    assert config.mineru_language == "korean"
    assert config.mineru_parse_method == "ocr"
    assert config.mineru_formula_enable is False
    assert config.mineru_table_enable is False
    assert config.mineru_image_analysis is False
    assert config.mineru_api_url == "http://localhost:8000"
    assert config.mineru_server_url == "http://localhost:30000"
    assert config.mineru_start_page_id == 2
    assert config.mineru_end_page_id == 10
    assert config.mineru_timeout_seconds == 120
    assert config.mineru_strip_images is False


def test_config_env_overrides_mineru(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DOCPREP_MINERU_API_URL", "http://remote:8000")
    monkeypatch.setenv("DOCPREP_MINERU_SERVER_URL", "http://remote:30000")
    monkeypatch.setenv("DOCPREP_MINERU_BACKEND", "vlm-engine")
    config = PipelineConfig.from_sources()
    assert config.mineru_api_url == "http://remote:8000"
    assert config.mineru_server_url == "http://remote:30000"
    assert config.mineru_backend == "vlm-engine"


def test_strip_image_references_removes_standalone_lines():
    md = (
        "# Title\n\n"
        "![alt](./images/foo.png)\n\n"
        "Some text here.\n\n"
        "![bar](images/baz.jpg)\n\n"
        "More text.\n"
    )
    out = _strip_image_references(md)
    assert "![alt]" not in out
    assert "![bar]" not in out
    assert "Some text here." in out
    assert "More text." in out
    # no triple blank lines
    assert "\n\n\n" not in out


def test_strip_image_references_removes_inline():
    md = "Paragraph with ![inline](images/x.png) embedded image."
    out = _strip_image_references(md)
    assert "![inline]" not in out
    assert "Paragraph with" in out
    assert "embedded image." in out


def test_strip_image_references_keeps_captions():
    md = "![alt](images/foo.png)\n\n*Figure 1: A chart.*\n\nBody text."
    out = _strip_image_references(md)
    assert "*Figure 1: A chart.*" in out
    assert "Body text." in out


@patch("docprep.paths.mineru_convert._run_mineru")
@patch("docprep.paths.mineru_convert._find_markdown")
def test_convert_mineru_strip_default(mock_find, mock_run, tmp_path: Path):
    mock_find.return_value = MagicMock(
        read_text=MagicMock(return_value="# H\n\n![x](images/a.png)\n\nBody."),
    )

    source = tmp_path / "doc.pdf"
    source.write_bytes(b"%PDF-1.4 fake")
    config = PipelineConfig(mineru_enabled=True, mineru_backend="hybrid-engine")

    import asyncio

    mock_run.return_value = asyncio.sleep(0)

    markdown = convert_mineru(source, config)
    assert "![x]" not in markdown
    assert "# H" in markdown
    assert "Body." in markdown


@patch("docprep.paths.mineru_convert._run_mineru")
@patch("docprep.paths.mineru_convert._find_markdown")
def test_convert_mineru_strip_disabled(mock_find, mock_run, tmp_path: Path):
    mock_find.return_value = MagicMock(
        read_text=MagicMock(return_value="# H\n\n![x](images/a.png)\n\nBody."),
    )

    source = tmp_path / "doc.pdf"
    source.write_bytes(b"%PDF-1.4 fake")
    config = PipelineConfig(
        mineru_enabled=True,
        mineru_backend="vlm-engine",
        mineru_strip_images=False,
    )

    import asyncio

    mock_run.return_value = asyncio.sleep(0)

    markdown = convert_mineru(source, config)
    assert "![x](images/a.png)" in markdown