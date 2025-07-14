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
            source_bytes: bytes = file_path.read_bytes()
            source = source_bytes.decode("utf-8")
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

            start_byte: int = self._get_byte_offset(source=source, line=start.line, column=start.column)
            end_byte: int = self._get_byte_offset(source=source, line=end.line, column=end.column) - 1
            
            node_text = source_bytes[start_byte:(end_byte + 1)].decode("utf-8")

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
                "start_byte": start_byte, # inclusive byte index starting at 0
                "end_byte": end_byte, # inclusive byte index (like SWHID)

                "swhid": self._create_swhid(file_path=file_path, start_byte=start_byte, end_byte=end_byte),

                "source_path": source_path
            })

            for child in node.children:
                if isinstance(child, CSTNode):
                    yield from walk(child, parent_fragment_id=fragment_id)

        return walk(wrapper.module)
    
    def _get_byte_offset(self, source: str, line: int, column: int) -> int:
        # Split lines with line endings preserved so offsets match the original source
        lines = source.splitlines(keepends=True)

        # Handle edge case: LibCST may give a line number that is one past the actual file
        if line > len(lines):
            self.logger.debug(f"Line {line} out of range. Falling back to EOF.")
            return len(source.encode("utf-8"))

        line_prefix = ''.join(lines[:line - 1]) + lines[line - 1][:column]
        return len(line_prefix.encode("utf-8"))







