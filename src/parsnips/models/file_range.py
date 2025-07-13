from __future__ import annotations

from parsnips.models.parsnips_base_model import ParsnipsBaseModel


class FileRange(ParsnipsBaseModel):
    start_line_number: int | None
    end_line_number: int | None
    start_col_offset: int | None
    end_col_offset: int | None

    def is_complete(self) -> bool:
        return self.start_line_number is not None and self.end_line_number is not None and self.start_col_offset is not None and self.end_col_offset is not None and self.start_line_number <= self.end_line_number and self.start_col_offset <= self.end_col_offset

    def is_within(self, other: "FileRange") -> bool:
        if not self.is_complete() or not other.is_complete():
            return False

        self_start = (self.start_line_number, self.start_col_offset)
        self_end = (self.end_line_number, self.end_col_offset)
        other_start = (other.start_line_number, other.start_col_offset)
        other_end = (other.end_line_number, other.end_col_offset)

        return other_start <= self_start and self_end <= other_end
