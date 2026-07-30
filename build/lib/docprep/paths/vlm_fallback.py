from __future__ import annotations

from pathlib import Path

from docprep.config import PipelineConfig
from docprep.providers.base import VLMProvider


def convert_with_fallback(
    source: Path,
    provider: VLMProvider,
    config: PipelineConfig,
) -> str:
    """Path D: convert document using a Vision LLM API provider."""
    return provider.convert_document(source)
