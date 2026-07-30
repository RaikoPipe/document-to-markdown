from __future__ import annotations

from docprep.providers.base import CONVERSION_SYSTEM_PROMPT, VLMProvider


class AnthropicProvider(VLMProvider):

    def __init__(self, api_key: str):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)

    @property
    def name(self) -> str:
        return "anthropic"

    def convert_image(self, image_data: bytes, mime_type: str) -> str:
        b64 = self._encode_image_b64(image_data)
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=CONVERSION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64,
                            },
                        },
                    ],
                },
            ],
        )
        return response.content[0].text if response.content else ""
