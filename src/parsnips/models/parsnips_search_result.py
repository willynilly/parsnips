

from parsnips.models.parsnips_base_model import ParsnipsBaseModel
from parsnips.models.parsnips_fragment import ParsnipsFragment


class ParsnipsSearchResult(ParsnipsBaseModel):
    search_text: str
    search_used_regex: bool
    search_used_unicode: bool
    search_regex_match_groups: dict | None
    node_swhid: str
    node_metadata: ParsnipsFragment