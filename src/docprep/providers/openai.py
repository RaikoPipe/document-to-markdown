from __future__ import annotations

from docprep.providers.base import CONVERSION_SYSTEM_PROMPT, VLMProvider


class OpenAIProvider(VLMProvider):

    def __init__(self, api_key: str):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)

    @property
    def name(self) -> str:
        return "openai"

    def convert_image(self, image_data: bytes, mime_type: str) -> str:
        b64 = self._encode_image_b64(image_data)
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": CONVERSION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                        },
                    ],
                },
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""
