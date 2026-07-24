from __future__ import annotations

import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Type, Union

from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import ApiImageRequestResult
from docling.exceptions import OperationNotAllowed
from docling.models.picture_description_base_model import PictureDescriptionBaseModel
from docling.utils.api_image_request import api_image_request
from PIL import Image

from docprep.models.two_stage_options import TwoStagePictureOptions

logger = logging.getLogger(__name__)

_TEXT_ONLY = "text_only"
_NEEDS_INTERPRETATION = "needs_interpretation"


class TwoStagePictureModel(PictureDescriptionBaseModel):
    """Two-stage picture processing: judge → OCR or interpret.

    Stage 1: send each image to the VLM with a judge prompt that classifies
    the image as "text_only" or "needs_interpretation".
    Stage 2: send the image again with either an OCR prompt (text_only) or
    a full interpretation prompt (needs_interpretation / ambiguous).
    Ambiguous judge responses default to interpretation (safe — no
    information lost).
    """

    def __init__(
        self,
        enabled: bool,
        enable_remote_services: bool,
        artifacts_path: Optional[Union[Path, str]],
        options: TwoStagePictureOptions,
        accelerator_options: AcceleratorOptions,
    ):
        super().__init__(
            enabled=enabled,
            enable_remote_services=enable_remote_services,
            artifacts_path=artifacts_path,
            options=options,
            accelerator_options=accelerator_options,
        )
        self.options: TwoStagePictureOptions
        self.concurrency = self.options.concurrency

        if self.enabled:
            if not enable_remote_services:
                raise OperationNotAllowed(
                    "Connections to remote services is only allowed when set "
                    "explicitly. pipeline_options.enable_remote_services=True."
                )

    @classmethod
    def get_options_type(cls) -> Type[TwoStagePictureOptions]:
        return TwoStagePictureOptions

    def _annotate_images(
        self, images: Iterable[Image.Image]
    ) -> Iterable[str | ApiImageRequestResult]:
        """Process each image through the two-stage judge→OCR/interpret flow."""

        def _process_image(image: Image.Image) -> str:
            # Stage 1: judge
            judge_result = api_image_request(
                image=image,
                prompt=self.options.judge_prompt,
                url=self.options.url,
                timeout=self.options.timeout,
                headers=self.options.headers,
                **self.options.params,
            )
            label = (judge_result.text or "").strip().lower()

            if _NEEDS_INTERPRETATION in label:
                stage2_prompt = self.options.interpret_prompt
                logger.debug("Image classified as needs_interpretation")
            elif _TEXT_ONLY in label:
                stage2_prompt = self.options.ocr_prompt
                logger.debug("Image classified as text_only")
            else:
                # Ambiguous — default to interpretation (safe)
                stage2_prompt = self.options.interpret_prompt
                logger.warning(
                    "Judge response was ambiguous (%r); defaulting to interpretation.",
                    judge_result.text,
                )

            # Stage 2: OCR or interpret
            result = api_image_request(
                image=image,
                prompt=stage2_prompt,
                url=self.options.url,
                timeout=self.options.timeout,
                headers=self.options.headers,
                **self.options.params,
            )
            return result.text or ""

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            yield from executor.map(_process_image, images)
