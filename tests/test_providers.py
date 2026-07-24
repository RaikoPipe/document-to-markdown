from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from docprep.config import PipelineConfig
from docprep.providers import get_provider


def test_get_provider_unknown():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("not_real", "key")


@patch("docprep.providers.mistral.Mistral")
def test_mistral_provider_init(mock_cls):
    provider = get_provider("mistral", "test-key")
    assert provider.name == "mistral"
    mock_cls.assert_called_once_with(api_key="test-key")


@patch("docprep.providers.openai.OpenAI")
def test_openai_provider_init(mock_cls):
    provider = get_provider("openai", "test-key")
    assert provider.name == "openai"
    mock_cls.assert_called_once_with(api_key="test-key")


@patch("docprep.providers.openai.OpenAI")
def test_openai_convert_image(mock_cls):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="# Result"))]
    )

    provider = get_provider("openai", "test-key")
    result = provider.convert_image(b"\x89PNG\r\n", "image/png")
    assert result == "# Result"
    mock_client.chat.completions.create.assert_called_once()


@patch("docprep.providers.ollama.OpenAI")
def test_ollama_provider_init(mock_cls):
    config = PipelineConfig(
        fallback_model="llama3.2-vision",
        fallback_base_url="http://localhost:11434/v1",
    )
    provider = get_provider("ollama", "test-key", config)
    assert provider.name == "ollama"
    assert provider.model == "llama3.2-vision"
    mock_cls.assert_called_once_with(
        api_key="test-key", base_url="http://localhost:11434/v1"
    )


@patch("docprep.providers.ollama.OpenAI")
def test_ollama_convert_image(mock_cls):
    mock_client = MagicMock()
    mock_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="# Ollama Result"))]
    )

    config = PipelineConfig(
        fallback_model="llama3.2-vision",
        fallback_base_url="http://localhost:11434/v1",
    )
    provider = get_provider("ollama", "test-key", config)
    result = provider.convert_image(b"\x89PNG\r\n", "image/png")
    assert result == "# Ollama Result"

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "llama3.2-vision"


def test_ollama_requires_config():
    with pytest.raises(ValueError, match="requires a PipelineConfig"):
        get_provider("ollama", "test-key")


def test_ollama_requires_model():
    config = PipelineConfig(fallback_base_url="http://localhost:11434/v1")
    with pytest.raises(ValueError, match="requires fallback.model"):
        get_provider("ollama", "test-key", config)


def test_ollama_requires_base_url():
    config = PipelineConfig(fallback_model="llama3.2-vision")
    with pytest.raises(ValueError, match="requires fallback.base_url"):
        get_provider("ollama", "test-key", config)
