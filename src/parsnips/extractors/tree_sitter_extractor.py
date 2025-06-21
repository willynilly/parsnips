from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Generator, cast, get_args

import pkg_resources
from tree_sitter_language_pack import SupportedLanguage, get_parser

from parsnips.extractors.parsnips_extractor import ParsnipsExtractor, ParsnipsFragment


class TreeSitterExtractor(ParsnipsExtractor):
    
    _source_file_extensions_by_language_map: dict[str, list[str]] = {}

    def get_fragment_type(self) -> str:
        return 'tree-sitter-language-pack'
        
    # def get_file_fragments_generator(
    #     self,
    #     file_path: Path,
    #     repo_root: str,
    #     file_swhid: str,
    #     source: str,
    # ) -> Generator[ParsnipsFragment, None, None]:
    #     raise NotImplementedError


    def get_file_fragments_generator(
        self,
        file_path: Path,
        repo_root: str,
        file_swhid: str,
        source: str,
    ) -> Generator[ParsnipsFragment, None, None]:
        
        SUPPORTED_LANGUAGES = get_args(SupportedLanguage)

        languages_for_file: list[str] = self._get_languages_for_file(file_path)
        if len(languages_for_file) == 0:
            return
        for language_for_file in languages_for_file:
            if language_for_file not in SUPPORTED_LANGUAGES:
                self.logger.error(f"Unsupported language: {language_for_file}")
                exit(1)

            parser = get_parser(cast(SupportedLanguage, language_for_file))
            tree = parser.parse(bytes(source, "utf8"))

            source_path = str(file_path.relative_to(repo_root))
            traversal_counter = 0

            def walk(node, parent_fragment_id: str | None = None) -> Generator[ParsnipsFragment, None, None]:
                nonlocal traversal_counter
                traversal_counter += 1
                fragment_id = f"{source_path}::{traversal_counter}"

                start_byte = node.start_byte
                end_byte = node.end_byte
                node_text = source[start_byte:end_byte]
                node_type = node.type

                start_point = node.start_point  # (row, column)
                lineno = start_point[0] + 1  # Tree-sitter uses 0-based lines
                col_offset = start_point[1]

                depends_on_fragment_ids = [parent_fragment_id] if parent_fragment_id else []

                yield ParsnipsFragment.from_dict({
                    "fragment_id": fragment_id,
                    "depends_on_fragment_ids": depends_on_fragment_ids,
                    "type": node_type,
                    "label": node_type,
                    "text": node_text,
                    "lineno": lineno,
                    "effective_lineno": lineno,
                    "col_offset": col_offset,
                    "file_swhid": file_swhid,
                    "source_path": source_path,
                    "source_filename": file_path.name
                })

                for child in node.children:
                    yield from walk(child, parent_fragment_id=fragment_id)

            yield from walk(tree.root_node)

    def _get_languages_for_file(self, file_path: Path) -> list[str]:
        ext = file_path.suffix.lstrip(".")
        map = self._get_normalized_source_file_extensions_by_language_map()
        languages_for_file: list[str] = []
        for source_file_language in self._get_normalized_source_file_languages():
            extensions = map.get(source_file_language, [])
            if ext in extensions:
                languages_for_file.append(source_file_language)
        return languages_for_file        
        
    
    @classmethod
    def get_source_file_extensions_by_language_map(cls) -> dict[str, list[str]]:
        logger = logging.getLogger("parsnips")

        if cls._source_file_extensions_by_language_map is None:
            base: str | None = pkg_resources.get_distribution("tree_sitter_language_pack").location
            if base is None:
                logger.error("Cannot find location of tree_sitter_language_pack distribution.")
                sys.exit(1)

            srcs = os.path.join(str(base), "tree_sitter_language_pack", "sources")
            mapping: dict[str, list[str]] = {}  # Example: mapping["python"] -> ["py"]

            for lang in os.listdir(srcs):
                meta = os.path.join(srcs, lang, "tree-sitter.json")
                if os.path.isfile(meta):
                    with open(meta, "r", encoding="utf-8") as f:
                        try:
                            data = json.load(f)
                            exts = data.get("file-types", [])
                            mapping[lang] = exts
                        except json.JSONDecodeError:
                            logger.error(f'Error decoding JSON for {meta}')
                            sys.exit(1)
            cls._source_file_extensions_by_language_map = mapping

        return cls._source_file_extensions_by_language_map

