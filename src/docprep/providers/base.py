from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from pathlib import Path


CONVERSION_SYSTEM_PROMPT = (
    "Convert this document page to Markdown. "
    "Preserve all headings, tables, lists, and reading order. "
    "Describe any charts or figures in detail. "
    "Output only the Markdown content, no commentary."
)


class VLMProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def convert_image(self, image_data: bytes, mime_type: str) -> str:
        """Convert a single page image to markdown."""
        ...

    def convert_document(self, source: Path) -> str:
        """Convert a full document. Default: render to images and convert each."""
        from docprep.utils.images import pdf_to_images

        images = pdf_to_images(source)
        pages = []
        for img_bytes, mime in images:
            page_md = self.convert_image(img_bytes, mime)
            pages.append(page_md)
        return "\n\n---\n\n".join(pages)

    @staticmethod
    def _encode_image_b64(image_data: bytes) -> str:
        return base64.b64encode(image_data).decode("utf-8")
