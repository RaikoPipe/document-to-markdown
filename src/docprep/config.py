from __future__ import annotations

import dataclasses
import os
from pathlib import Path

import yaml


@dataclasses.dataclass
class PipelineConfig:
    vlm_preset: str = "granite_docling"
    ocr_languages: list[str] = dataclasses.field(default_factory=lambda: ["en"])

    quality_min_chars_per_page: int = 50
    quality_max_garbled_ratio: float = 0.20

    fallback_enabled: bool = True
    fallback_provider: str | None = None
    fallback_max_pages: int = 50
    fallback_timeout_seconds: int = 30

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
        if "max_pages" in fb:
            kwargs["fallback_max_pages"] = fb["max_pages"]
        if "timeout_seconds" in fb:
            kwargs["fallback_timeout_seconds"] = fb["timeout_seconds"]

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
        }
        env_var = env_map.get(provider)
        if env_var:
            return os.environ.get(env_var)
        return None
