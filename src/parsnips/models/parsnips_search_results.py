

from pydantic import Field

from parsnips.models.parsnips_base_model import ParsnipsBaseModel
from parsnips.models.parsnips_search_result import ParsnipsSearchResult


class ParsnipsSearchResults(ParsnipsBaseModel):
    results: dict[str, ParsnipsSearchResult] = Field(default_factory=dict)