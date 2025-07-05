from __future__ import annotations

from pathlib import Path

from parsnips.models.config.extractor_script_config import ExtractorScriptConfig
from parsnips.models.parsnips_base_model import ParsnipsBaseModel
from parsnips.models.patterns.pattern_set import PatternSet


class ExtractionConfig(ParsnipsBaseModel):
    language: str
    extractor_python_class: str | None # only applies if the extractor script is parsnips
    extractor_script: ExtractorScriptConfig
    include_patterns: PatternSet
    exclude_patterns: PatternSet # takes precedence over include_patterns

    def is_ignored(self, file_path: Path) -> bool:
        return self.exclude_patterns.any_matches(value=file_path) or not self.include_patterns.any_matches(value=file_path)


