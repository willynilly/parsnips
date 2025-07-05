from __future__ import annotations

import regex as re
from pydantic import BaseModel, field_validator


class Regex(BaseModel):
    pattern: str

    @field_validator("pattern")
    @classmethod
    def validate_regex(cls, v: str) -> str:
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
        return v

    def compiled(self) -> re.Pattern:
        return re.compile(self.pattern)

    def match(self, text: str) -> re.Match | None:
        return self.compiled().match(text)
