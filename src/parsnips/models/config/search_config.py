from __future__ import annotations

from parsnips.models.config.swh_search_config import SwhSearchConfig
from parsnips.models.file_range import FileRange
from parsnips.models.parsnips_base_model import ParsnipsBaseModel
from parsnips.models.patterns.pattern_set import PatternSet


class SearchConfig(ParsnipsBaseModel):
    searcher_python_class: str
    use_unicode: bool
    use_regex: bool
    swh: SwhSearchConfig
    include_patterns: PatternSet
    exclude_patterns: PatternSet # takes precedence over include_patterns
    file_range: FileRange | None = None
    search_text: str | None = None