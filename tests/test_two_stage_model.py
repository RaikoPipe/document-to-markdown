from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from docprep.models.two_stage_model import TwoStagePictureModel
from docprep.models.two_stage_options import TwoStagePictureOptions


def _make_options(**overrides) -> TwoStagePictureOptions:
    defaults = dict(
        url="http://localhost:11434/v1/chat/completions",
        headers={"Authorization": "Bearer test"},
        params={"model": "glm-ocr"},
    )
    defaults.update(overrides)
    return TwoStagePictureOptions(**defaults)


def _make_model(options):
    return TwoStagePictureModel(
        enabled=True,
        enable_remote_services=True,
        artifacts_path=None,
        options=options,
        accelerator_options=MagicMock(),
    )


def _mock_api_result(text: str):
    """Create a mock ApiImageRequestResult."""
    m = MagicMock()
    m.text = text
    return m


@patch("docprep.models.two_stage_model.api_image_request")
def test_text_only_routes_to_ocr(mock_api):
    """Judge says text_only → stage 2 uses ocr_prompt."""
    mock_api.side_effect = [
        _mock_api_result("text_only"),
        _mock_api_result("# OCR'd text content"),
    ]
    options = _make_options(
        judge_prompt="judge?",
        ocr_prompt="OCR this",
        interpret_prompt="Interpret this",
    )
    model = _make_model(options)

    images = [MagicMock()]
    results = list(model._annotate_images(images))

    assert results == ["# OCR'd text content"]
    assert mock_api.call_count == 2
    # Stage 1: judge prompt
    assert mock_api.call_args_list[0].kwargs["prompt"] == "judge?"
    # Stage 2: OCR prompt
    assert mock_api.call_args_list[1].kwargs["prompt"] == "OCR this"


@patch("docprep.models.two_stage_model.api_image_request")
def test_needs_interpretation_routes_to_interpret(mock_api):
    """Judge says needs_interpretation → stage 2 uses interpret_prompt."""
    mock_api.side_effect = [
        _mock_api_result("needs_interpretation"),
        _mock_api_result("## Chart description"),
    ]
    options = _make_options(
        judge_prompt="judge?",
        ocr_prompt="OCR this",
        interpret_prompt="Interpret this",
    )
    model = _make_model(options)

    images = [MagicMock()]
    results = list(model._annotate_images(images))

    assert results == ["## Chart description"]
    assert mock_api.call_count == 2
    assert mock_api.call_args_list[0].kwargs["prompt"] == "judge?"
    assert mock_api.call_args_list[1].kwargs["prompt"] == "Interpret this"


@patch("docprep.models.two_stage_model.api_image_request")
def test_ambiguous_defaults_to_interpret(mock_api):
    """Ambiguous judge response → defaults to interpret_prompt."""
    mock_api.side_effect = [
        _mock_api_result("I'm not sure"),
        _mock_api_result("## Interpreted content"),
    ]
    options = _make_options(
        judge_prompt="judge?",
        ocr_prompt="OCR this",
        interpret_prompt="Interpret this",
    )
    model = _make_model(options)

    images = [MagicMock()]
    results = list(model._annotate_images(images))

    assert results == ["## Interpreted content"]
    assert mock_api.call_count == 2
    assert mock_api.call_args_list[1].kwargs["prompt"] == "Interpret this"


@patch("docprep.models.two_stage_model.api_image_request")
def test_multiple_images(mock_api):
    """Multiple images each go through judge → OCR/interpret."""
    mock_api.side_effect = [
        _mock_api_result("text_only"),
        _mock_api_result("text 1"),
        _mock_api_result("needs_interpretation"),
        _mock_api_result("chart 2"),
    ]
    options = _make_options(concurrency=1)
    model = _make_model(options)

    images = [MagicMock(), MagicMock()]
    results = list(model._annotate_images(images))

    assert results == ["text 1", "chart 2"]
    assert mock_api.call_count == 4


def test_get_options_type():
    assert TwoStagePictureModel.get_options_type() is TwoStagePictureOptions


def test_init_requires_enable_remote_services():
    options = _make_options()
    from docling.exceptions import OperationNotAllowed

    with pytest.raises(OperationNotAllowed):
        TwoStagePictureModel(
            enabled=True,
            enable_remote_services=False,
            artifacts_path=None,
            options=options,
            accelerator_options=MagicMock(),
        )
