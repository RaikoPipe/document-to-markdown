from __future__ import annotations

import dataclasses
import os
from pathlib import Path

import yaml


@dataclasses.dataclass
class PipelineConfig:
    vlm_preset: str = "granite_docling"
    ocr_languages: list[str] = dataclasses.field(default_factory=lambda: ["en"])

    embed_images: bool = True
    render_chart_images: bool = True

    describe_images: bool = True
    picture_judge_prompt: str = (
        "Look at this image and classify it as one of: "
        '"text_only" (the image contains only text that can be OCR\'d, '
        "e.g. a scanned document page or text screenshot) "
        'or "needs_interpretation" (the image contains charts, diagrams, '
        "figures, photos, logos, or other visual elements that require "
        "visual understanding beyond text extraction). "
        "Respond with only the label, nothing else."
    )
    picture_ocr_prompt: str = (
        "Extract all text from this image. Preserve reading order, "
        "headings, and list structure. Output only the extracted text, "
        "no commentary."
    )
    picture_interpret_prompt: str = (
        "Convert this image to Markdown. Preserve all text, tables, and "
        "reading order. Describe any charts or figures in detail. "
        "Output only the Markdown content, no commentary."
    )
    picture_description_timeout: float = 60.0
    picture_description_concurrency: int = 1
    picture_area_threshold: float = 0.01

    quality_min_chars_per_page: int = 50
    quality_max_garbled_ratio: float = 0.20

    fallback_enabled: bool = True
    fallback_provider: str | None = None
    fallback_model: str | None = None
    fallback_base_url: str | None = None
    fallback_max_pages: int = 50
    fallback_timeout_seconds: int = 30

    mineru_enabled: bool = False
    mineru_backend: str = "hybrid-engine"
    mineru_effort: str = "medium"
    mineru_language: str = "ch"
    mineru_parse_method: str = "auto"
    mineru_formula_enable: bool = True
    mineru_table_enable: bool = True
    mineru_image_analysis: bool = True
    mineru_api_url: str | None = None
    mineru_server_url: str | None = None
    mineru_start_page_id: int = 0
    mineru_end_page_id: int | None = None
    mineru_timeout_seconds: int = 600
    mineru_strip_images: bool = True

    @classmethod
    def from_yaml(cls, path: Path) -> PipelineConfig:
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return cls._from_raw(raw)

    @classmethod
    def _from_raw(cls, raw: dict) -> PipelineConfig:
        kwargs: dict = {}
        pipeline = raw.get("pipeline", {})
        if "vlm_preset" in pipeline:
            kwargs["vlm_preset"] = pipeline["vlm_preset"]
        if "ocr_languages" in pipeline:
            kwargs["ocr_languages"] = pipeline["ocr_languages"]
        if "embed_images" in pipeline:
            kwargs["embed_images"] = pipeline["embed_images"]
        if "render_chart_images" in pipeline:
            kwargs["render_chart_images"] = pipeline["render_chart_images"]
        if "describe_images" in pipeline:
            kwargs["describe_images"] = pipeline["describe_images"]
        if "picture_judge_prompt" in pipeline:
            kwargs["picture_judge_prompt"] = pipeline["picture_judge_prompt"]
        if "picture_ocr_prompt" in pipeline:
            kwargs["picture_ocr_prompt"] = pipeline["picture_ocr_prompt"]
        if "picture_interpret_prompt" in pipeline:
            kwargs["picture_interpret_prompt"] = pipeline["picture_interpret_prompt"]
        if "picture_description_timeout" in pipeline:
            kwargs["picture_description_timeout"] = pipeline["picture_description_timeout"]
        if "picture_description_concurrency" in pipeline:
            kwargs["picture_description_concurrency"] = pipeline["picture_description_concurrency"]
        if "picture_area_threshold" in pipeline:
            kwargs["picture_area_threshold"] = pipeline["picture_area_threshold"]

        qg = raw.get("quality_gate", {})
        if "min_text_density" in qg:
            kwargs["quality_min_chars_per_page"] = qg["min_text_density"]
        if "max_garbled_ratio" in qg:
            kwargs["quality_max_garbled_ratio"] = qg["max_garbled_ratio"]

        fb = raw.get("fallback", {})
        if "enabled" in fb:
            kwargs["fallback_enabled"] = fb["enabled"]
        if "provider" in fb:
            kwargs["fallback_provider"] = fb["provider"]
        if "model" in fb:
            kwargs["fallback_model"] = fb["model"]
        if "base_url" in fb:
            kwargs["fallback_base_url"] = fb["base_url"]
        if "max_pages" in fb:
            kwargs["fallback_max_pages"] = fb["max_pages"]
        if "timeout_seconds" in fb:
            kwargs["fallback_timeout_seconds"] = fb["timeout_seconds"]

        mu = raw.get("mineru", {})
        if "enabled" in mu:
            kwargs["mineru_enabled"] = mu["enabled"]
        if "backend" in mu:
            kwargs["mineru_backend"] = mu["backend"]
        if "effort" in mu:
            kwargs["mineru_effort"] = mu["effort"]
        if "language" in mu:
            kwargs["mineru_language"] = mu["language"]
        if "parse_method" in mu:
            kwargs["mineru_parse_method"] = mu["parse_method"]
        if "formula_enable" in mu:
            kwargs["mineru_formula_enable"] = mu["formula_enable"]
        if "table_enable" in mu:
            kwargs["mineru_table_enable"] = mu["table_enable"]
        if "image_analysis" in mu:
            kwargs["mineru_image_analysis"] = mu["image_analysis"]
        if "api_url" in mu:
            kwargs["mineru_api_url"] = mu["api_url"]
        if "server_url" in mu:
            kwargs["mineru_server_url"] = mu["server_url"]
        if "start_page_id" in mu:
            kwargs["mineru_start_page_id"] = mu["start_page_id"]
        if "end_page_id" in mu:
            kwargs["mineru_end_page_id"] = mu["end_page_id"]
        if "timeout_seconds" in mu:
            kwargs["mineru_timeout_seconds"] = mu["timeout_seconds"]
        if "strip_images" in mu:
            kwargs["mineru_strip_images"] = mu["strip_images"]

        return cls(**kwargs)

    @classmethod
    def from_sources(
        cls,
        cli_overrides: dict | None = None,
        yaml_path: Path | None = None,
    ) -> PipelineConfig:
        config = cls()

        if yaml_path and yaml_path.exists():
            config = cls.from_yaml(yaml_path)

        env_provider = os.environ.get("DOCPREP_FALLBACK_PROVIDER")
        if env_provider:
            config.fallback_provider = env_provider

        env_model = os.environ.get("DOCPREP_FALLBACK_MODEL")
        if env_model:
            config.fallback_model = env_model

        env_base_url = os.environ.get("DOCPREP_FALLBACK_BASE_URL")
        if env_base_url:
            config.fallback_base_url = env_base_url

        env_mineru_api_url = os.environ.get("DOCPREP_MINERU_API_URL")
        if env_mineru_api_url:
            config.mineru_api_url = env_mineru_api_url

        env_mineru_server_url = os.environ.get("DOCPREP_MINERU_SERVER_URL")
        if env_mineru_server_url:
            config.mineru_server_url = env_mineru_server_url

        env_mineru_backend = os.environ.get("DOCPREP_MINERU_BACKEND")
        if env_mineru_backend:
            config.mineru_backend = env_mineru_backend

        if cli_overrides:
            for key, value in cli_overrides.items():
                if value is not None and hasattr(config, key):
                    setattr(config, key, value)

        return config

    def get_api_key(self, provider: str | None = None) -> str | None:
        provider = provider or self.fallback_provider
        if not provider:
            return None
        env_map = {
            "mistral": "MISTRAL_API_KEY",
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "ollama": "OLLAMA_API_KEY",
        }
        env_var = env_map.get(provider)
        if env_var:
            return os.environ.get(env_var)
        return None
