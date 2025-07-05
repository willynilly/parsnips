from __future__ import annotations

from typing import List

from parsnips.models.config.extraction_config import ExtractionConfig
from parsnips.models.parsnips_base_model import ParsnipsBaseModel


class ExtractConfig(ParsnipsBaseModel):
    extractions: List[ExtractionConfig]
