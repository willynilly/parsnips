from __future__ import annotations

from pathlib import Path

from pydantic import field_validator

from parsnips.loggers.log_level import LogLevel
from parsnips.models.parsnips_base_model import ParsnipsBaseModel


class LogConfig(ParsnipsBaseModel):
    quiet: bool
    file_path: Path | None
    log_level: LogLevel | None = None

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v):
        if v is None:
            return None
        if isinstance(v, LogLevel):
            return v
        return LogLevel.from_str(v)
