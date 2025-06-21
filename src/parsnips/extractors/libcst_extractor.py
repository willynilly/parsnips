from pathlib import Path
from typing import Generator, cast

import libcst as cst
from libcst import CSTNode
from libcst.metadata import CodePosition, CodeRange, MetadataWrapper, PositionProvider

from parsnips.extractors.parsnips_extractor import ParsnipsExtractor
from parsnips.extractors.parsnips_fragment import ParsnipsFragment


class LibCSTExtractor(ParsnipsExtractor):
        
    def get_fragment_type(self) -> str:
        return 'libcst.cst'

    def get_file_fragments_generator(
        self,
        file_path: Path,
        repo_root: str,
        file_swhid: str,
        source: str,
    ) -> Generator[ParsnipsFragment, None, None]:
        
        wrapper = MetadataWrapper(cst.parse_module(source))
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

            yield ParsnipsFragment.from_dict({
                "fragment_id": fragment_id,
                "depends_on_fragment_ids": depends_on_fragment_ids,
                "type": node_type,
                "label": node_type,
                "text": node_text,
                "lineno": pos.start.line,
                "effective_lineno": pos.start.line,
                "col_offset": pos.start.column,
                "file_swhid": file_swhid,
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

