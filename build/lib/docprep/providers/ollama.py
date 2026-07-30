from __future__ import annotations

from docprep.providers.base import CONVERSION_SYSTEM_PROMPT, VLMProvider


class OllamaProvider(VLMProvider):
    """VLM provider backed by an OpenAI-compatible Ollama endpoint."""

    def __init__(self, api_key: str, model: str, base_url: str):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    @property
    def name(self) -> str:
        return "ollama"

    def convert_image(self, image_data: bytes, mime_type: str) -> str:
        b64 = self._encode_image_b64(image_data)
        response = self.client.chat.completions.create(
            model=self.model,
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
