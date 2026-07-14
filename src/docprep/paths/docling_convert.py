from __future__ import annotations

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    PdfFormatOption,
    PdfPipelineOptions,
    VlmConvertOptions,
    VlmPipelineOptions,
)
from docling.document_converter import DocumentConverter
from docling.pipeline.vlm_pipeline import VlmPipeline

from docprep.config import PipelineConfig


def convert_standard(source: Path, config: PipelineConfig) -> str:
    """Path A (native PDF) and Path B (office formats) via Docling standard pipeline."""
    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        ocr_options=EasyOcrOptions(lang=config.ocr_languages),
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )
    result = converter.convert(source=str(source))
    return result.document.export_to_markdown()


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
    return result.document.export_to_markdown()
