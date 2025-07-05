from typing import Generator

from parsnips.models.config.extraction_config import ExtractionConfig
from parsnips.models.parsnips_base_model import ParsnipsBaseModel
from parsnips.models.parsnips_fragment import ParsnipsFragment


class Extraction(ParsnipsBaseModel):
    extraction_config: ExtractionConfig
    fragment_type: str
    fragment_generator: Generator[ParsnipsFragment, None, None]