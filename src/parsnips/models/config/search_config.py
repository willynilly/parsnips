from __future__ import annotations

from parsnips.models.parsnips_base_model import ParsnipsBaseModel


class SearchConfig(ParsnipsBaseModel):
    searcher_python_class: str
    use_unicode: bool
    use_regex: bool
    repo_url: str | None
    commit: str | None
    release_name: str | None
    ref_name: str | None