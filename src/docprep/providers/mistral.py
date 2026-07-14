from __future__ import annotations

import base64
from pathlib import Path

from docprep.providers.base import VLMProvider


class MistralProvider(VLMProvider):

    def __init__(self, api_key: str):
        from mistralai import Mistral

        self.client = Mistral(api_key=api_key)

    @property
    def name(self) -> str:
        return "mistral"

    def convert_document(self, source: Path) -> str:
        """Mistral has a dedicated OCR API that handles documents directly."""
        with open(source, "rb") as f:
            doc_data = base64.b64encode(f.read()).decode("utf-8")

        suffix = source.suffix.lower()
        doc_type = "document_url"
        if suffix in (".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp", ".gif"):
            doc_type = "image_url"

        response = self.client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": doc_type,
                doc_type: f"data:application/octet-stream;base64,{doc_data}",
            },
        )
        pages = [page.markdown for page in response.pages if page.markdown]
        return "\n\n---\n\n".join(pages)

    def convert_image(self, image_data: bytes, mime_type: str) -> str:
        b64 = self._encode_image_b64(image_data)
        response = self.client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "image_url",
                "image_url": f"data:{mime_type};base64,{b64}",
            },
        )
        pages = [page.markdown for page in response.pages if page.markdown]
        return "\n\n".join(pages)
