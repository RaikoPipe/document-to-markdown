from __future__ import annotations

from pathlib import Path

from docprep.config import PipelineConfig


def test_defaults():
    config = PipelineConfig()
    assert config.vlm_preset == "granite_docling"
    assert config.ocr_languages == ["en"]
    assert config.quality_min_chars_per_page == 50
    assert config.fallback_enabled is True
    assert config.fallback_provider is None


def test_from_yaml(tmp_path: Path):
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        """
pipeline:
  vlm_preset: custom_model
  ocr_languages: [en, de]
quality_gate:
  min_text_density: 100
  max_garbled_ratio: 0.05
fallback:
  enabled: false
  provider: openai
  max_pages: 25
  timeout_seconds: 60
"""
    )
    config = PipelineConfig.from_yaml(yaml_path)
    assert config.vlm_preset == "custom_model"
    assert config.ocr_languages == ["en", "de"]
    assert config.quality_min_chars_per_page == 100
    assert config.quality_max_garbled_ratio == 0.05
    assert config.fallback_enabled is False
    assert config.fallback_provider == "openai"
    assert config.fallback_max_pages == 25
    assert config.fallback_timeout_seconds == 60


def test_from_sources_cli_overrides(tmp_path: Path):
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        """
fallback:
  provider: openai
"""
    )
    config = PipelineConfig.from_sources(
        cli_overrides={"fallback_provider": "mistral"},
        yaml_path=yaml_path,
    )
    assert config.fallback_provider == "mistral"


def test_from_sources_no_yaml():
    config = PipelineConfig.from_sources(cli_overrides={"vlm_preset": "test"})
    assert config.vlm_preset == "test"


def test_get_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    config = PipelineConfig(fallback_provider="openai")
    assert config.get_api_key() == "sk-test-123"


def test_get_api_key_no_provider():
    config = PipelineConfig()
    assert config.get_api_key() is None
