from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator, cast, get_args

from tree_sitter_language_pack import SupportedLanguage, get_parser

from parsnips.extractors.parsnips_extractor import ParsnipsExtractor, ParsnipsFragment


class TreeSitterExtractor(ParsnipsExtractor):
    
    def get_fragment_type(self) -> str:
        return 'tree-sitter-language-pack'
    
    def get_supported_languages(self) -> list[str]:
        return list(get_args(SupportedLanguage))
        
    def get_file_fragments_generator(
        self,
        file_path: Path,
        repo_root: str,
    ) -> Generator[ParsnipsFragment, None, None]:
        
        source: str = ''
        try:
            source = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"TreeSitterExtractor error: Cannot load file {file_path.resolve()}: {e}")
            sys.exit(1)

        source_file_language = self._get_normalized_source_file_language()
        parser = get_parser(cast(SupportedLanguage, source_file_language))
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

            start_point = node.start_point  # (row, column) for start of fragment
            end_point = node.end_point # (row, column) for end of fragment 

            start_line_number = start_point[0] + 1 # Tree-sitter uses 0-based lines
            start_col_offset = start_point[1]
            end_line_number = end_point[0] + 1
            end_col_offset = end_point[1]

            depends_on_fragment_ids = [parent_fragment_id] if parent_fragment_id else []

            yield ParsnipsFragment.model_validate({
                "fragment_id": fragment_id,
                "depends_on_fragment_ids": depends_on_fragment_ids,
                "node_type": node_type,
                "text": node_text,

                "start_line_number": start_line_number,
                "start_col_offset": start_col_offset,
                "end_line_number": end_line_number,
                "end_col_offset": end_col_offset,

                "file_swhid_without_qualifiers": self._create_file_swhid_without_qualifiers(file_path=file_path),
                "file_swhid_with_qualifiers": None,
                
                "source_path": source_path
            })

            for child in node.children:
                yield from walk(child, parent_fragment_id=fragment_id)

        yield from walk(tree.root_node)    
