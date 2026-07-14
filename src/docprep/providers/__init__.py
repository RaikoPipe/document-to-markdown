from __future__ import annotations

from docprep.providers.base import VLMProvider


def get_provider(name: str, api_key: str) -> VLMProvider:
    providers = {
        "mistral": ("docprep.providers.mistral", "MistralProvider"),
        "openai": ("docprep.providers.openai", "OpenAIProvider"),
        "gemini": ("docprep.providers.gemini", "GeminiProvider"),
        "anthropic": ("docprep.providers.anthropic", "AnthropicProvider"),
    }

    entry = providers.get(name)
    if entry is None:
        raise ValueError(f"Unknown provider: {name}. Available: {list(providers.keys())}")

    module_path, class_name = entry
    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(api_key=api_key)


__all__ = ["get_provider", "VLMProvider"]
