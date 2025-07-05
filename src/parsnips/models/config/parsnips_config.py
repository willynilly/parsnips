from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar, Union

from parsnips.models.config.extract_config import ExtractConfig
from parsnips.models.config.extraction_config import ExtractionConfig
from parsnips.models.config.extractor_script_config import ExtractorScriptConfig
from parsnips.models.config.log_config import LogConfig
from parsnips.models.config.search_config import SearchConfig
from parsnips.models.parsnips_base_model import ParsnipsBaseModel
from parsnips.models.patterns.glob import Glob
from parsnips.models.patterns.pattern_set import PatternSet
from parsnips.utils import (
    get_parser_script_arguments,
    get_parser_script_command,
    get_parsnips_cli_version,
)


class ParsnipsConfig(ParsnipsBaseModel):
    DEFAULT_PARSNIPS_PROTOCOL_VERSION: ClassVar[str] = "3.0.0"

    parsnips_protocol_version: str
    strict: bool # abort on first error
    repo_root: Path | None
    log: LogConfig
    search: SearchConfig
    extract: ExtractConfig

    @classmethod
    def from_json_file(cls, path: Union[str, Path]) -> ParsnipsConfig:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)
    
    @classmethod
    def from_default(cls, language: str = 'python', glob_include_patterns: list[str] = ['*.py'], repo_root: Path | None = None) -> ParsnipsConfig:
        parsnips_protocol_version = cls.DEFAULT_PARSNIPS_PROTOCOL_VERSION
        strict: bool = True

        # configure logging        
        log_config: LogConfig = LogConfig(quiet=False, filename=None)

        # configure searching
        searcher_python_class: str = "parsnips.searchers.parsnips_searcher.ParsnipsSearcher"
        use_unicode: bool = False
        use_regex: bool = False
        repo_url: str | None = None
        commit: str | None = None
        release_name: str | None = None
        ref_name: str | None = None
        search_config: SearchConfig = SearchConfig(searcher_python_class=searcher_python_class, 
                                            use_unicode=use_unicode,
                                            use_regex=use_regex,
                                            repo_url=repo_url,
                                            commit=commit,
                                            release_name=release_name,
                                            ref_name=ref_name)
        
        extractor_python_class: str = "parsnips.extractors.tree_sitter_extractor.TreeSitterExtractor"
        command: list[str] = [get_parser_script_command()] + get_parser_script_arguments()
        settings: dict = {}
        extractor_script: ExtractorScriptConfig = ExtractorScriptConfig(name="parsnips", version=get_parsnips_cli_version(), command=command, settings=settings)
        exclude_patterns: PatternSet = PatternSet(regex=[], glob=[])
        include_patterns: PatternSet = PatternSet(regex=[], glob=[Glob(pattern=pattern) for pattern in glob_include_patterns])
        extraction_config: ExtractionConfig = ExtractionConfig(language=language, extractor_python_class=extractor_python_class, extractor_script=extractor_script, include_patterns=include_patterns, exclude_patterns=exclude_patterns)
        extractions: list[ExtractionConfig] = [extraction_config]
        extract_config: ExtractConfig = ExtractConfig(extractions=extractions)

        config = ParsnipsConfig(parsnips_protocol_version=parsnips_protocol_version, strict=strict, repo_root=repo_root, log=log_config, search=search_config, extract=extract_config)
        return config