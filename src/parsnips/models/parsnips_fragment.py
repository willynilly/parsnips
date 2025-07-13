
from parsnips.models.parsnips_base_model import ParsnipsBaseModel


class ParsnipsFragment(ParsnipsBaseModel):
    fragment_id: str | None = None
    depends_on_fragment_ids: list[str] = []
    node_type: str | None = None
    text: str | None = None
    start_line_number: int | None = None # 1-based
    start_col_offset: int | None = None # 0-based
    end_line_number: int | None = None # 1-based
    end_col_offset: int | None = None # 0-based
    file_swhid_without_qualifiers: str | None = None
    file_swhid_with_qualifiers: str | None = None
    source_path: str | None = None
    source_filename: str | None = None

    def is_valid(self) -> bool:
        for k, v in self.model_dump().items():
            if v is None:
                return False
            if k == "depends_on_fragment_ids":
                if not all(isinstance(item, str) for item in v):
                    return False
            elif not isinstance(v, str):
                return False
        return True
