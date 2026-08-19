from __future__ import annotations

import logging
import time
from pathlib import Path

from docprep.config import PipelineConfig
from docprep.paths.docling_convert import convert_standard, convert_vlm
from docprep.paths.mineru_convert import convert_mineru
from docprep.paths.vlm_fallback import convert_with_fallback
from docprep.providers import get_provider
from docprep.quality import should_escalate
from docprep.result import ConversionResult
from docprep.router import (
    IMAGE_MIMES,
    ProcessingPath,
    UnsupportedFormatError,
    classify,
)
from docprep.utils.images import get_page_count
from docprep.utils.mime import detect_mime

logger = logging.getLogger(__name__)

# MinerU accepts PDF, images, and the OOXML office formats (DOCX/PPTX/XLSX).
# Legacy MS office (.doc/.xls/.ppt), EPUB, HTML, CSV, text, XML, Markdown fall
# back to Docling even when mineru_enabled=True.
_MINERU_SUPPORTED_MIMES = IMAGE_MIMES | {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def convert(
    source: str | Path,
    config: PipelineConfig | None = None,
) -> ConversionResult:
    config = config or PipelineConfig()
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    start = time.monotonic()
    warnings: list[str] = []
    mime_type = detect_mime(source)

    path = classify(source)
    if path == ProcessingPath.UNSUPPORTED:
        raise UnsupportedFormatError(mime_type, source)

    page_count = get_page_count(source)

    mineru_eligible = config.mineru_enabled and mime_type in _MINERU_SUPPORTED_MIMES
    if mineru_eligible:
        logger.info("Routing %s through MinerU (backend=%s)", source.name, config.mineru_backend)
        markdown = convert_mineru(source, config)
        pipeline_used = f"mineru:{config.mineru_backend}"
    elif config.mineru_enabled and not mineru_eligible:
        logger.info(
            "MinerU enabled but %s (mime=%s) unsupported; falling back to Docling (%s)",
            source.name,
            mime_type,
            path.value,
        )
        warnings.append(
            f"MinerU does not support {mime_type}; converted via Docling {path.value} instead"
        )
        if path == ProcessingPath.SCANNED:
            markdown = convert_vlm(source, config)
            pipeline_used = "vlm"
        else:
            markdown = convert_standard(source, config)
            pipeline_used = "standard"
    elif path == ProcessingPath.SCANNED:
        logger.info("Routing %s through VLM pipeline (scanned/image content)", source.name)
        markdown = convert_vlm(source, config)
        pipeline_used = "vlm"
    else:
        logger.info("Routing %s through standard pipeline (%s)", source.name, path.value)
        markdown = convert_standard(source, config)
        pipeline_used = "standard"

    escalated = False
    skip_escalation = pipeline_used.startswith("mineru:") and config.mineru_backend in (
        "vlm-engine",
        "hybrid-engine",
    )
    if (
        not skip_escalation
        and config.fallback_enabled
        and config.fallback_provider
        and should_escalate(markdown, page_count, config, mime_type)
    ):
        api_key = config.get_api_key()
        if api_key:
            logger.info(
                "Quality gate failed, escalating to %s",
                config.fallback_provider,
            )
            warnings.append(
                f"Primary conversion ({pipeline_used}) produced low-quality output; "
                f"escalated to {config.fallback_provider}"
            )
            provider = get_provider(config.fallback_provider, api_key, config)
            markdown = convert_with_fallback(source, provider, config)
            pipeline_used = config.fallback_provider
            escalated = True
        else:
            warnings.append(
                f"Quality gate failed but no API key found for {config.fallback_provider}"
            )

    return ConversionResult(
        source_path=source,
        markdown=markdown,
        format_detected=mime_type,
        pipeline_used=pipeline_used,
        page_count=page_count,
        escalated=escalated,
        processing_time_seconds=time.monotonic() - start,
        warnings=warnings,
    )
