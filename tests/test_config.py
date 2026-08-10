from __future__ import annotations

from pathlib import Path

from docprep.config import PipelineConfig


def test_defaults():
    config = PipelineConfig()
    assert config.vlm_preset == "granite_docling"
    assert config.ocr_languages == ["en"]
    assert config.embed_images is True
    assert config.render_chart_images is True
    assert config.describe_images is True
    assert "text_only" in config.picture_judge_prompt
    assert "Extract all text" in config.picture_ocr_prompt
    assert "Convert this image to Markdown" in config.picture_interpret_prompt
    assert config.picture_description_timeout == 60.0
    assert config.picture_description_concurrency == 1
    assert config.picture_area_threshold == 0.01
    assert config.quality_min_chars_per_page == 50
    assert config.fallback_enabled is True
    assert config.fallback_provider is None
    assert config.mineru_enabled is False
    assert config.mineru_backend == "hybrid-engine"
    assert config.mineru_strip_images is True


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


def test_from_yaml_image_options(tmp_path: Path):
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        """
pipeline:
  embed_images: false
  render_chart_images: false
"""
    )
    config = PipelineConfig.from_yaml(yaml_path)
    assert config.embed_images is False
    assert config.render_chart_images is False


def test_from_yaml_picture_description(tmp_path: Path):
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        """
pipeline:
  describe_images: true
  picture_judge_prompt: "Is this text or a chart?"
  picture_ocr_prompt: "OCR this text."
  picture_interpret_prompt: "Describe this chart."
  picture_description_timeout: 120
  picture_description_concurrency: 4
  picture_area_threshold: 0.02
"""
    )
    config = PipelineConfig.from_yaml(yaml_path)
    assert config.describe_images is True
    assert config.picture_judge_prompt == "Is this text or a chart?"
    assert config.picture_ocr_prompt == "OCR this text."
    assert config.picture_interpret_prompt == "Describe this chart."
    assert config.picture_description_timeout == 120
    assert config.picture_description_concurrency == 4
    assert config.picture_area_threshold == 0.02


def test_from_yaml_describe_images_disabled(tmp_path: Path):
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        """
pipeline:
  describe_images: false
"""
    )
    config = PipelineConfig.from_yaml(yaml_path)
    assert config.describe_images is False


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


def test_from_yaml_fallback_model_and_base_url(tmp_path: Path):
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        """
fallback:
  provider: ollama
  model: llama3.2-vision
  base_url: http://localhost:11434/v1
"""
    )
    config = PipelineConfig.from_yaml(yaml_path)
    assert config.fallback_provider == "ollama"
    assert config.fallback_model == "llama3.2-vision"
    assert config.fallback_base_url == "http://localhost:11434/v1"


def test_from_sources_env_overrides(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DOCPREP_FALLBACK_MODEL", "qwen2.5-vl")
    monkeypatch.setenv("DOCPREP_FALLBACK_BASE_URL", "http://remote:11434/v1")
    config = PipelineConfig.from_sources()
    assert config.fallback_model == "qwen2.5-vl"
    assert config.fallback_base_url == "http://remote:11434/v1"


def test_get_api_key_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "ollama-secret")
    config = PipelineConfig(fallback_provider="ollama")
    assert config.get_api_key() == "ollama-secret"


def test_get_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    config = PipelineConfig(fallback_provider="openai")
    assert config.get_api_key() == "sk-test-123"


def test_get_api_key_no_provider():
    config = PipelineConfig()
    assert config.get_api_key() is None
