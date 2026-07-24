from __future__ import annotations

import logging
from pathlib import Path

from docling.backend.msexcel_backend import MsExcelBackendOptions
from docling.backend.mspowerpoint_backend import MsPowerpointBackendOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    PdfPipelineOptions,
    VlmConvertOptions,
    VlmPipelineOptions,
)
from docling.document_converter import (
    DocumentConverter,
    ExcelFormatOption,
    PdfFormatOption,
    PowerpointFormatOption,
    WordFormatOption,
)
from docling.models.factories import get_picture_description_factory
from docling.pipeline.vlm_pipeline import VlmPipeline
from docling_core.types.doc import ImageRefMode

from docprep.config import PipelineConfig
from docprep.models.two_stage_model import TwoStagePictureModel
from docprep.models.two_stage_options import TwoStagePictureOptions

logger = logging.getLogger(__name__)

_two_stage_registered = False


def _ensure_two_stage_registered() -> None:
    """Register TwoStagePictureModel with the docling factory once.

    Registers on both allow_external_plugins=True and False instances,
    since the pipeline may use either depending on configuration.
    """
    global _two_stage_registered
    if _two_stage_registered:
        return
    for allow_external in (True, False):
        factory = get_picture_description_factory(
            allow_external_plugins=allow_external,
        )
        try:
            factory.register(
                TwoStagePictureModel,
                plugin_name="docprep",
                plugin_module_name="docprep.models.two_stage_model",
            )
        except ValueError:
            pass  # already registered
    _two_stage_registered = True


def _build_picture_description_options(
    config: PipelineConfig,
) -> TwoStagePictureOptions | None:
    """Build TwoStagePictureOptions from the fallback VLM endpoint config.

    Returns None if no usable endpoint is configured.
    """
    if not config.fallback_provider or not config.fallback_model or not config.fallback_base_url:
        return None

    api_key = config.get_api_key()
    if not api_key:
        return None

    _ensure_two_stage_registered()

    base_url = config.fallback_base_url.rstrip("/")
    chat_url = f"{base_url}/chat/completions"

    return TwoStagePictureOptions(
        url=chat_url,
        headers={"Authorization": f"Bearer {api_key}"},
        params={"model": config.fallback_model},
        judge_prompt=config.picture_judge_prompt,
        ocr_prompt=config.picture_ocr_prompt,
        interpret_prompt=config.picture_interpret_prompt,
        timeout=config.picture_description_timeout,
        concurrency=config.picture_description_concurrency,
        picture_area_threshold=config.picture_area_threshold,
    )


def _build_pipeline_options(config: PipelineConfig) -> PdfPipelineOptions:
    """Build PdfPipelineOptions, enabling picture description when configured."""
    pipeline_kwargs: dict = {
        "do_ocr": True,
        "ocr_options": EasyOcrOptions(lang=config.ocr_languages),
    }

    if config.describe_images:
        desc_options = _build_picture_description_options(config)
        if desc_options is not None:
            pipeline_kwargs["enable_remote_services"] = True
            pipeline_kwargs["do_picture_description"] = True
            pipeline_kwargs["picture_description_options"] = desc_options
            logger.info(
                "Picture description enabled via %s (model=%s)",
                config.fallback_provider,
                config.fallback_model,
            )
        else:
            logger.warning(
                "describe_images=True but no VLM endpoint configured "
                "(need fallback.provider, fallback.model, fallback.base_url, and API key); "
                "images will not be described."
            )

    return PdfPipelineOptions(**pipeline_kwargs)


def _export_markdown(result, config: PipelineConfig) -> str:
    """Export a DoclingDocument to markdown.

    When picture description is enabled (and an endpoint was configured),
    emit text descriptions only — suppress base64 images.
    Otherwise, embed images as base64 or leave placeholders per config.
    """
    describing = (
        config.describe_images
        and config.fallback_provider
        and config.fallback_model
        and config.fallback_base_url
        and config.get_api_key() is not None
    )

    if describing:
        return result.document.export_to_markdown(
            image_mode=ImageRefMode.PLACEHOLDER,
            image_placeholder="",
            traverse_pictures=True,
            mark_meta=True,
        )
    if config.embed_images:
        return result.document.export_to_markdown(
            image_mode=ImageRefMode.EMBEDDED,
            traverse_pictures=True,
        )
    return result.document.export_to_markdown()


def convert_standard(source: Path, config: PipelineConfig) -> str:
    """Path A (native PDF) and Path B (office formats) via Docling standard pipeline."""
    pipeline_options = _build_pipeline_options(config)
    excel_backend_options = MsExcelBackendOptions(
        render_chart_images=config.render_chart_images,
    )
    pptx_backend_options = MsPowerpointBackendOptions(
        render_chart_images=config.render_chart_images,
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            InputFormat.XLSX: ExcelFormatOption(
                pipeline_options=pipeline_options,
                backend_options=excel_backend_options,
            ),
            InputFormat.PPTX: PowerpointFormatOption(
                pipeline_options=pipeline_options,
                backend_options=pptx_backend_options,
            ),
            InputFormat.DOCX: WordFormatOption(
                pipeline_options=pipeline_options,
            ),
        }
    )
    result = converter.convert(source=str(source))
    return _export_markdown(result, config)


def convert_vlm(source: Path, config: PipelineConfig) -> str:
    """Path C (scanned/image documents) via Docling VLM pipeline."""
    vlm_options = VlmConvertOptions.from_preset(config.vlm_preset)
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=VlmPipeline,
                pipeline_options=VlmPipelineOptions(vlm_options=vlm_options),
            ),
        }
    )
    result = converter.convert(source=str(source))
    return _export_markdown(result, config)
