from __future__ import annotations

from typing import Any


class ParsnipsFragment:

    def __init__(self, **kwargs):
        self._from_dict(kwargs)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ParsnipsFragment:
        fragment: ParsnipsFragment = ParsnipsFragment()
        fragment._from_dict(d=d)
        return fragment

        
    def _from_dict(self, d: dict[str, Any]):
        self.fragment_id: str | None = d.get('fragment_id', None)
        self.depends_on_fragment_ids: list[str] = d.get('depends_on_fragment_ids', [])
        self.type: str | None = d.get('type', None)
        self.label: str | None = d.get('label', None)
        self.text: str | None = d.get('text', None)
        self.lineno: str | None = d.get('lineno', None)
        self.effective_lineno: str | None = d.get('effective_lineno', None)
        self.col_offset: str | None = d.get('col_offset', None)
        self.file_swhid: str | None = d.get('file_swhid', None)
        self.source_path: str | None = d.get('source_path', None)
        self.source_filename: str | None = d.get('source_filename', None)

    def to_dict(self) -> dict[str, Any]:
        d: dict = {
            "fragment_id": self.fragment_id,
            "depends_on_fragment_ids": self.depends_on_fragment_ids,
            "type": self.type,
            "label": self.label,
            "text": self.text,
            "lineno": self.lineno,
            "effective_lineno": self.effective_lineno,
            "col_offset": self.col_offset,
            "file_swhid": self.file_swhid,
            "source_path": self.source_path,
            "source_filename": self.source_filename
        }
        return d
    
    def is_valid(self):
        d = self.to_dict()
        for k, v in d:
            if v is None:
                return False
            if k == "depends_on_fragment_ids":
                if type(v) is not list[str]:
                    return False
            else:
                if not isinstance(v, str):
                    return False
        return True