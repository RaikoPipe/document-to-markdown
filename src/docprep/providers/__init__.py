from __future__ import annotations

from docprep.config import PipelineConfig
from docprep.providers.base import VLMProvider


def get_provider(name: str, api_key: str, config: PipelineConfig | None = None) -> VLMProvider:
    providers = {
        "mistral": ("docprep.providers.mistral", "MistralProvider"),
        "openai": ("docprep.providers.openai", "OpenAIProvider"),
        "gemini": ("docprep.providers.gemini", "GeminiProvider"),
        "anthropic": ("docprep.providers.anthropic", "AnthropicProvider"),
        "ollama": ("docprep.providers.ollama", "OllamaProvider"),
    }

    entry = providers.get(name)
    if entry is None:
        raise ValueError(f"Unknown provider: {name}. Available: {list(providers.keys())}")

    module_path, class_name = entry
    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)

    if name == "ollama":
        if config is None:
            raise ValueError("Ollama provider requires a PipelineConfig (for model and base_url)")
        model = config.fallback_model
        base_url = config.fallback_base_url
        if not model:
            raise ValueError(
                "Ollama provider requires fallback.model (set via YAML fallback.model, "
                "DOCPREP_FALLBACK_MODEL, or --vlm-preset)."
            )
        if not base_url:
            raise ValueError(
                "Ollama provider requires fallback.base_url (set via YAML fallback.base_url "
                "or DOCPREP_FALLBACK_BASE_URL)."
            )
        return cls(api_key=api_key, model=model, base_url=base_url)

    return cls(api_key=api_key)


__all__ = ["get_provider", "VLMProvider"]
