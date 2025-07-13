from __future__ import annotations

from pathlib import Path

from parsnips.models.parsnips_base_model import ParsnipsBaseModel


class LogConfig(ParsnipsBaseModel):
    quiet: bool
    file_path: Path | None