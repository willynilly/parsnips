
from pathlib import Path

from pydantic import Field, field_validator

from parsnips.models.parsnips_base_model import ParsnipsBaseModel


class ParsnipsFragment(ParsnipsBaseModel):
    fragment_id: str | None = None
    depends_on_fragment_ids: list[str] = Field(default_factory=list)
    node_type: str | None = None
    text: str | None = None
    start_line_number: int | None = None # 1-based
    start_col_offset: int | None = None # 0-based
    end_line_number: int | None = None # 1-based
    end_col_offset: int | None = None # 0-based
    start_byte: int | None = None
    end_byte: int | None = None
    swhid: str | None = None
    source_path: Path | None = None # path relative to the repo root
    
    @field_validator("source_path", mode="after")
    def must_be_relative(cls, v: Path | None) -> Path | None:
        if v is not None and v.is_absolute():
            raise ValueError("source_path must be relative")
        return v


