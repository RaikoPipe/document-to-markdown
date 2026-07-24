from __future__ import annotations

from typing import Any, ClassVar, Literal

from docling.datamodel.pipeline_options import PictureDescriptionBaseOptions
from pydantic import AnyUrl, Field


class TwoStagePictureOptions(PictureDescriptionBaseOptions):
    """Options for two-stage picture processing: judge → OCR or interpret.

    Stage 1 sends each image to the VLM with a judge prompt that classifies
    the image as "text_only" or "needs_interpretation".
    Stage 2 sends the image again with either an OCR prompt (text_only) or
    a full interpretation prompt (needs_interpretation / ambiguous).
    """

    kind: ClassVar[Literal["two_stage"]] = "two_stage"

    url: AnyUrl = Field(
        default=AnyUrl("http://localhost:11434/v1/chat/completions"),
        description="OpenAI-compatible chat completions endpoint.",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers (e.g. Authorization).",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra parameters merged into the API request body (e.g. model, temperature).",
    )
    timeout: float = Field(default=60.0, description="Timeout per API call in seconds.")
    concurrency: int = Field(default=1, ge=1, description="Max concurrent API requests.")

    judge_prompt: str = Field(
        default=(
            "Look at this image and classify it as one of: "
            '"text_only" (the image contains only text that can be OCR\'d, '
            "e.g. a scanned document page or text screenshot) "
            'or "needs_interpretation" (the image contains charts, diagrams, '
            "figures, photos, logos, or other visual elements that require "
            "visual understanding beyond text extraction). "
            "Respond with only the label, nothing else."
        ),
        description="Stage 1 prompt: classify the image.",
    )

    ocr_prompt: str = Field(
        default=(
            "Extract all text from this image. Preserve reading order, "
            "headings, and list structure. Output only the extracted text, "
            "no commentary."
        ),
        description="Stage 2 prompt for images classified as text_only.",
    )

    interpret_prompt: str = Field(
        default=(
            "Convert this image to Markdown. Preserve all text, tables, and "
            "reading order. Describe any charts or figures in detail. "
            "Output only the Markdown content, no commentary."
        ),
        description="Stage 2 prompt for images that need visual interpretation.",
    )
