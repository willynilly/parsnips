import sys
from pathlib import Path
from typing import Generator, cast

import libcst as cst
from libcst import CSTNode
from libcst.metadata import CodePosition, CodeRange, MetadataWrapper, PositionProvider

from parsnips.extractors.parsnips_extractor import ParsnipsExtractor
from parsnips.models.parsnips_fragment import ParsnipsFragment


class LibCSTExtractor(ParsnipsExtractor):
        
    def get_fragment_type(self) -> str:
        return 'libcst.cst'
    
    def get_supported_languages(self) -> list[str]:
        return ['python']

    def get_file_fragments_generator(
        self,
        file_path: Path,
        repo_root: str,
    ) -> Generator[ParsnipsFragment, None, None]:
        
        source: str = ''
        try:
            source = file_path.read_text(encoding="utf-8")
            wrapper = MetadataWrapper(cst.parse_module(source))
        except Exception as e:
            self.logger.error(f"LibCSTExtractor error: Cannot load file {file_path.resolve()}: {e}")
            sys.exit(1)
        metadata = wrapper.resolve(PositionProvider)
        traversal_counter = 0
        source_path = str(file_path.relative_to(repo_root))

        def walk(node: CSTNode, parent_fragment_id: str | None = None) -> Generator[ParsnipsFragment, None, None]:
            nonlocal traversal_counter
            traversal_counter += 1
            fragment_id = f"{source_path}::{traversal_counter}"
            pos = cast(CodeRange, metadata[node])
            start = cast(CodePosition, pos.start)
            end = cast(CodePosition, pos.end)
                        
            start_offset = self._get_offset(source, start.line, start.column)
            end_offset = self._get_offset(source, end.line, end.column)
            node_text = source[start_offset:end_offset]

            node_type = type(node).__name__

            depends_on_fragment_ids = [parent_fragment_id] if parent_fragment_id else []

            yield ParsnipsFragment.model_validate_or_exit({
                "fragment_id": fragment_id,
                "depends_on_fragment_ids": depends_on_fragment_ids,
                "node_type": node_type,
                "text": node_text,
                
                "start_line_number": pos.start.line,
                "start_col_offset": pos.start.column,
                "end_line_number": pos.end.line,
                "end_col_offset": pos.end.column,

                "file_swhid_without_qualifiers": self._create_file_swhid_without_qualifiers(file_path=file_path),
                "file_swhid_with_qualifiers": None,

                "source_path": source_path,
                "source_filename": file_path.name
            })

            for child in node.children:
                if isinstance(child, CSTNode):
                    yield from walk(child, parent_fragment_id=fragment_id)

        return walk(wrapper.module)
    
    def _get_offset(self, source: str, line: int, column: int) -> int:
        lines = source.splitlines(keepends=True)
        return sum(len(lines[i]) for i in range(line - 1)) + column

