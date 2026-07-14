from __future__ import annotations

from docprep.providers.base import CONVERSION_SYSTEM_PROMPT, VLMProvider


class GeminiProvider(VLMProvider):

    def __init__(self, api_key: str):
        from google import genai

        self.client = genai.Client(api_key=api_key)

    @property
    def name(self) -> str:
        return "gemini"

    def convert_image(self, image_data: bytes, mime_type: str) -> str:
        from google.genai import types

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=image_data, mime_type=mime_type),
                        types.Part.from_text(CONVERSION_SYSTEM_PROMPT),
                    ]
                )
            ],
        )
        return response.text or ""
