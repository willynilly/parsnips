from __future__ import annotations

import logging
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_str(cls, value: str) -> LogLevel:
        value_upper = value.upper()
        try:
            return cls[value_upper]
        except KeyError:
            raise ValueError(f"Invalid log level: {value}. Must be one of: {list(cls.__members__)}")

    def to_logging_level(self) -> int:
        """Returns the corresponding logging module level (e.g. logging.INFO)"""
        return {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }[self]