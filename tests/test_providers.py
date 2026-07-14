from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

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
