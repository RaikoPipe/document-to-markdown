from __future__ import annotations

import asyncio
import logging
import re
import tempfile
from pathlib import Path

from docprep.config import PipelineConfig

logger = logging.getLogger(__name__)


def convert_mineru(source: Path, config: PipelineConfig) -> str:
    """Path M: convert via MinerU SDK (pipeline / vlm-engine / hybrid-engine).

    MinerU handles PDF, image, DOCX, PPTX, and XLSX natively and performs OCR
    on scanned pages and image inputs (PP-OCRv6 for the pipeline backend;
    native VLM OCR for vlm/hybrid backends). Image markdown references are
    stripped by default since MinerU already OCRs/interprets image content.
    """
    out_dir = Path(tempfile.mkdtemp(prefix="mineru_"))
    logger.info(
        "MinerU convert: source=%s backend=%s effort=%s lang=%s out=%s",
        source.name,
        config.mineru_backend,
        config.mineru_effort,
        config.mineru_language,
        out_dir,
    )
    try:
        asyncio.run(_run_mineru(source, out_dir, config))
        md_path = _find_markdown(out_dir)
        markdown = md_path.read_text(encoding="utf-8")
    finally:
        # Leave out_dir in place for debugging; caller may clean up.
        pass

    if config.mineru_strip_images:
        markdown = _strip_image_references(markdown)
    return markdown


async def _run_mineru(source: Path, out_dir: Path, config: PipelineConfig) -> None:
    """Invoke MinerU via the official SDK (demo/demo.py surface)."""
    from mineru.cli import api_client as _api_client
    from mineru.utils.guess_suffix_or_lang import guess_suffix_by_path

    supported = _api_client.SUPPORTED_INPUT_SUFFIXES if hasattr(
        _api_client, "SUPPORTED_INPUT_SUFFIXES"
    ) else None
    if supported is not None and guess_suffix_by_path(source) not in supported:
        raise ValueError(f"MinerU does not support input: {source.name}")

    form_data = _api_client.build_parse_request_form_data(
        lang_list=[config.mineru_language],
        backend=config.mineru_backend,
        effort=config.mineru_effort,
        parse_method=config.mineru_parse_method,
        formula_enable=config.mineru_formula_enable,
        table_enable=config.mineru_table_enable,
        image_analysis=config.mineru_image_analysis,
        server_url=config.mineru_server_url,
        start_page_id=config.mineru_start_page_id,
        end_page_id=config.mineru_end_page_id,
        return_md=True,
        return_middle_json=False,
        return_model_output=False,
        return_content_list=False,
        return_images=True,
        response_format_zip=True,
        return_original_file=False,
    )
    upload_assets = [
        _api_client.UploadAsset(path=source.resolve(), upload_name=source.name)
    ]

    local_server: _api_client.LocalAPIServer | None = None
    result_zip_path: Path | None = None

    async with _api_client.httpx.AsyncClient(
        timeout=_api_client.build_http_timeout(),
        follow_redirects=True,
    ) as http_client:
        try:
            if config.mineru_api_url:
                server_health = await _api_client.fetch_server_health(
                    http_client,
                    _api_client.normalize_base_url(config.mineru_api_url),
                )
            else:
                local_server = _api_client.LocalAPIServer()
                base_url = local_server.start()
                logger.info("Started local mineru-api: %s", base_url)
                server_health = await _api_client.wait_for_local_api_ready(
                    http_client,
                    local_server,
                )

            logger.info("Using MinerU API: %s", server_health.base_url)
            submit_response = await _api_client.submit_parse_task(
                base_url=server_health.base_url,
                upload_assets=upload_assets,
                form_data=form_data,
            )
            logger.info("MinerU task_id: %s", submit_response.task_id)

            await _api_client.wait_for_task_result(
                client=http_client,
                submit_response=submit_response,
                task_label=source.name,
                status_snapshot_callback=_log_status,
            )
            result_zip_path = await _api_client.download_result_zip(
                client=http_client,
                submit_response=submit_response,
                task_label=source.name,
            )
        finally:
            if local_server is not None:
                local_server.stop()

    if result_zip_path is None:
        raise RuntimeError("MinerU did not produce a result zip")
    try:
        _api_client.safe_extract_zip(result_zip_path, out_dir)
    finally:
        result_zip_path.unlink(missing_ok=True)
    logger.info("Extracted MinerU result to: %s", out_dir)


def _log_status(snapshot) -> None:
    if snapshot.queued_ahead is not None:
        logger.info("MinerU status: %s (queued_ahead=%s)", snapshot.status, snapshot.queued_ahead)
    else:
        logger.info("MinerU status: %s", snapshot.status)


def _find_markdown(out_dir: Path) -> Path:
    candidates = sorted(out_dir.rglob("*.md"))
    if not candidates:
        raise RuntimeError(f"MinerU produced no markdown in {out_dir}")
    return candidates[0]


_IMG_LINE_RE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$", re.MULTILINE)
_INLINE_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")


def _strip_image_references(markdown: str) -> str:
    """Remove standalone image lines and inline image refs; keep captions."""
    markdown = _IMG_LINE_RE.sub("", markdown)
    markdown = _INLINE_IMG_RE.sub("", markdown)
    # Collapse runs of blank lines left behind by removed image lines.
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip() + "\n"