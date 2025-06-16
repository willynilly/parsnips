import ast
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

import asttokens


class ParsnipsExtractor:
    def __init__(self, logger, strict=False):
        self.logger = logger
        self.strict = strict

    def process(self, input_path: Path):
        if input_path.is_file():
            self._process_file(input_path, force_parsnips_dir=True)
        elif input_path.is_dir():
            self._process_directory(input_path)
        else:
            self.logger.error(f"Invalid path: {input_path}")
            self._abort()

    def _process_directory(self, directory: Path):
        for root, dirs, files in os.walk(directory, topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if d != '.parsnips']
            py_files = [f for f in files if f.endswith('.py')]

            if py_files:
                parsnips_dir = Path(root) / '.parsnips'
                if parsnips_dir.exists():
                    try:
                        shutil.rmtree(parsnips_dir)
                        self.logger.info(f"Deleted existing {parsnips_dir}")
                    except Exception as e:
                        self.logger.error(f"Failed to delete {parsnips_dir}: {e}")
                        self._abort()
                parsnips_dir.mkdir(exist_ok=True)

                for py_file in py_files:
                    self._process_file(Path(root) / py_file, parsnips_dir)

    def _process_file(self, file_path: Path, output_dir=None, force_parsnips_dir=False):
        self.logger.info(f"Parsnips extracting: `{file_path}`")
        parent_dir = file_path.parent

        if force_parsnips_dir:
            output_dir = parent_dir / '.parsnips'
            if not output_dir.exists():
                output_dir.mkdir(exist_ok=True)
        else:
            output_dir = output_dir or parent_dir

        try:
            code = file_path.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            self._abort()

        try:
            atok = asttokens.ASTTokens(code, parse=True)
        except SyntaxError as e:
            self.logger.error(f"Syntax error in {file_path}: {e}")
            self._abort()
        except Exception as e:
            self.logger.error(f"AST parsing failed for {file_path}: {e}")
            self._abort()

        file_swhid = self.compute_swhid(code)
        out_path = output_dir / f"parsnips__{file_path.stem}__{file_path.suffix.lstrip('.')}"
        out_path.mkdir(exist_ok=True)

        self.traversal_counter = 0
        self._extract_node(atok, atok.tree, out_path, file_swhid, parent_lineno=0)

    def compute_swhid(self, content_string):
        content_bytes = content_string.encode("utf-8")
        digest = hashlib.blake2s(content_bytes, digest_size=32).hexdigest()
        swhid = f"swh:1:cnt:{digest}"
        return swhid

    def _extract_node(self, atok, node, parent_path, file_swhid, parent_lineno):
        self.traversal_counter += 1

        lineno = getattr(node, 'lineno', None)
        effective_lineno = lineno if lineno is not None else parent_lineno
        col_offset = getattr(node, 'col_offset', 0)
        traversal_index = self.traversal_counter

        node_type = type(node).__name__
        node_label = self._get_node_label(atok, node)
        safe_label = self._sanitize_label(node_label)
        folder_name = f"L{effective_lineno}C{col_offset}T{traversal_index}__{node_type}__{safe_label}"
        node_path = parent_path / folder_name
        node_path.mkdir(exist_ok=True)

        try:
            node_text = atok.get_text(node)
        except Exception:
            node_text = "<source unavailable>"

        metadata = {
            'type': node_type,
            'label': node_label,
            'text': node_text,
            'lineno': lineno,
            'effective_lineno': effective_lineno,
            'col_offset': col_offset,
            'file_swhid': file_swhid
        }

        with (node_path / 'node_metadata.json').open('w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)

        for child in ast.iter_child_nodes(node):
            self._extract_node(atok, child, node_path, file_swhid, parent_lineno=effective_lineno)

    def _get_node_label(self, atok, node):
        if isinstance(node, ast.FunctionDef):
            return node.name
        elif isinstance(node, ast.AsyncFunctionDef):
            return node.name
        elif isinstance(node, ast.ClassDef):
            return node.name
        elif isinstance(node, ast.arg):
            return node.arg
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Import):
            return 'import'
        elif isinstance(node, ast.ImportFrom):
            return f'from_{node.module or "unknown"}'
        elif isinstance(node, ast.Assign):
            targets = [re.sub(r'\s+', '', atok.get_text(t)) for t in node.targets]
            return '_'.join(targets)
        elif isinstance(node, ast.Lambda):
            return 'lambda'
        elif isinstance(node, ast.Constant):
            return str(node.value)
        else:
            return 'node'

    def _sanitize_label(self, label: str) -> str:
        return re.sub(r'[^A-Za-z0-9_-]', '_', label)

    def _abort(self):
        if self.strict:
            raise RuntimeError("Strict mode abort triggered")
