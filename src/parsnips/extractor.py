# extractor.py
import ast
import os
import re
from pathlib import Path

import asttokens
import pathspec

from parsnips.pretty_json_dumper import PrettyJsonDumper
from parsnips.swhid import Swhid


class ParsnipsExtractor:

    PARSNIPS_VERSION: str = '3.0.0'

    def __init__(self, logger, strict=False, repo_root: Path | None = None):
        self.logger = logger
        self.strict = strict
        self.raw_repo_root = Path(repo_root).resolve() if repo_root else None
        self.fragments = []

    def process(self, input_path: Path, args=None):
        input_path = Path(input_path).resolve()
        if self.raw_repo_root is None:
            self.repo_root: Path = input_path if input_path.is_dir() else input_path.parent
        else:
            self.repo_root: Path = self.raw_repo_root

        if input_path.is_file():
            self._process_file(input_path, parent_fragment_id=None)
        elif input_path.is_dir():
            self._process_directory(input_path)
        else:
            self.logger.error(f"Invalid path: {input_path}")
            self._abort()

        # Write output to parsnips.json
        output = {
            "parsnips_version": self.PARSNIPS_VERSION,
            "fragment_type": "python.ast",
            "parser_script": {
                "command": "parsnips",
                "version": self.PARSNIPS_VERSION,
                "arguments": args or {}
            },
            "fragments": self.fragments
        }
        with open(self.repo_root / "parsnips.json", "w", encoding="utf-8") as f:
            PrettyJsonDumper.dump(output, f)

    def _load_ignore_spec(self) -> pathspec.PathSpec | None:
        ignore_file = self.repo_root / ".parsnipsignore"
        if ignore_file.exists():
            patterns = ignore_file.read_text(encoding='utf-8').splitlines()
            return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        return None

    def _process_directory(self, directory: Path):
        ignore_spec = self._load_ignore_spec()
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d != "__pycache__" and d != ".parsnips"]
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(self.repo_root)
                if file.endswith(".py") and (not ignore_spec or not ignore_spec.match_file(str(rel_path))):
                    self._process_file(full_path)

    def _process_file(self, file_path: Path, parent_fragment_id=None):
        self.logger.info(f"Processing: {file_path}")
        try:
            code = file_path.read_text(encoding="utf-8")
            atok = asttokens.ASTTokens(code, parse=True)
            file_swhid = Swhid.compute_content_swhid(code)
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")
            self._abort()

        self.traversal_counter = 0
        self._extract_node(atok, atok.tree, file_swhid, parent_fragment_id=None, file_path=file_path)

    def _extract_node(self, atok, node, file_swhid, parent_fragment_id, file_path):
        self.traversal_counter += 1
        traversal_id = self.traversal_counter
        source_path = str(file_path.relative_to(self.repo_root))
        fragment_id = f"{source_path}::{traversal_id}"
        

        lineno = getattr(node, "lineno", None)
        effective_lineno = lineno if lineno is not None else 0
        col_offset = getattr(node, "col_offset", 0)
        node_type = type(node).__name__
        node_label = self._get_node_label(atok, node)
        try:
            node_text = atok.get_text(node)
        except Exception:
            node_text = "<source unavailable>"

        fragment = {
            "fragment_id": fragment_id,
            "depends_on_fragment_ids": [parent_fragment_id] if parent_fragment_id else [],
            "type": node_type,
            "label": node_label,
            "text": node_text,
            "lineno": lineno,
            "effective_lineno": effective_lineno,
            "col_offset": col_offset,
            "file_swhid": file_swhid,
            "source_path": source_path,
            "source_filename": file_path.name
        }

        self.fragments.append(fragment)

        for child in ast.iter_child_nodes(node):
            self._extract_node(atok, child, file_swhid, parent_fragment_id=fragment_id, file_path=file_path)

    def _get_node_label(self, atok, node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return node.name
        elif isinstance(node, ast.arg):
            return node.arg
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Import):
            return "import"
        elif isinstance(node, ast.ImportFrom):
            return f"from_{node.module or 'unknown'}"
        elif isinstance(node, ast.Assign):
            targets = [re.sub(r"\\s+", "", atok.get_text(t)) for t in node.targets]
            return "_".join(targets)
        elif isinstance(node, ast.Lambda):
            return "lambda"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        else:
            return "node"

    def _abort(self):
        if self.strict:
            raise RuntimeError("Strict mode abort triggered")
