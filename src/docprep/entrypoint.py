from __future__ import annotations

import logging
import time
from pathlib import Path

from docprep.config import PipelineConfig
from docprep.paths.docling_convert import convert_standard, convert_vlm
from docprep.paths.vlm_fallback import convert_with_fallback
from docprep.providers import get_provider
from docprep.quality import should_escalate
from docprep.result import ConversionResult
from docprep.router import ProcessingPath, UnsupportedFormatError, classify
from docprep.utils.images import get_page_count
from docprep.utils.mime import detect_mime

logger = logging.getLogger(__name__)


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

    if path == ProcessingPath.SCANNED:
        logger.info("Routing %s through VLM pipeline (scanned/image content)", source.name)
        markdown = convert_vlm(source, config)
        pipeline_used = "vlm"
    else:
        logger.info("Routing %s through standard pipeline (%s)", source.name, path.value)
        markdown = convert_standard(source, config)
        pipeline_used = "standard"

    escalated = False
    if (
        config.fallback_enabled
        and config.fallback_provider
        and should_escalate(markdown, page_count, config)
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
            provider = get_provider(config.fallback_provider, api_key)
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
