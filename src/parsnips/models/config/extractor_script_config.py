from __future__ import annotations

from typing import Dict, List

from parsnips.models.parsnips_base_model import ParsnipsBaseModel


class ExtractorScriptConfig(ParsnipsBaseModel):
    name: str
    version: str
    command: List[str]
    settings: Dict[str, str]
