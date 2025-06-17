import json
import os
import sys
import unicodedata
from pathlib import Path

import regex

from parsnips.swhid import Swhid


class ParsnipsSearch:

    def __init__(self,  
                 context_qualifiers: dict | None = None,
                 repo_root: str | None = None,  
                 normalize_search=False, 
                 strict=False):
        self.context_qualifiers = context_qualifiers
        self.repo_root = repo_root
        self.normalize_search = normalize_search
        self.strict = strict
    
    def normalize_unicode(self, text):
        """Apply Unicode normalization (NFC) to text."""
        return unicodedata.normalize("NFC", text)
    
    

    def search(self, path, pattern):
        results = {}

        # Precompile pattern optionally normalized
        if self.normalize_search:
            pattern = self.normalize_unicode(pattern)

        try:
            regex_compiled = regex.compile(pattern)
        except regex.error as e:
            print(f"Invalid regular expression: {e}", file=sys.stderr)
            sys.exit(1)

        # Determine starting directory
        if path.is_file():
            start_dir = path.parent
        elif path.is_dir():
            start_dir = path
        else:
            print(f"Invalid path: {path}", file=sys.stderr)
            sys.exit(1)

        found_parsnips = False

        for root, dirs, files in os.walk(start_dir, topdown=True):
            for d in dirs:
                if d == '.parsnips':
                    found_parsnips = True
                    parsnips_dir = Path(root) / d
                    for p_root, _, p_files in os.walk(parsnips_dir, topdown=True):
                        for file in p_files:
                            if file == "node_metadata.json":
                                full_path = Path(p_root) / file
                                try:
                                    with open(full_path, encoding='utf-8') as f:
                                        metadata = json.load(f)

                                    text = metadata.get("text", "")
                                    text_to_search = self.normalize_unicode(text) if self.normalize_search else text

                                    if regex_compiled.search(text_to_search):
                                        rel_path = os.path.relpath(full_path, start=Path.cwd())
                                        metadata_str = json.dumps(metadata, sort_keys=True, ensure_ascii=False)
                                        node_swhid_without_qualifiers = Swhid.compute_content_swhid(metadata_str)

                                        # Compute fully qualified SWHID if context is available
                                        if self.context_qualifiers and self.repo_root:
                                            path_qual = os.path.relpath(full_path, start=self.repo_root)
                                            node_swhid_with_qualifiers = (
                                                f"{node_swhid_without_qualifiers}"
                                                f";anchor={self.context_qualifiers['anchor']}"
                                                f";path=/{path_qual}"
                                            )
                                        else:
                                            node_swhid_with_qualifiers = None

                                        results[rel_path] = {
                                            "node_swhid_without_qualifiers": node_swhid_without_qualifiers,
                                            "node_swhid_with_qualifiers": node_swhid_with_qualifiers,
                                            "node_metadata": metadata
                                        }

                                except Exception as e:
                                    print(f"Error reading {full_path}: {e}", file=sys.stderr)

        if self.strict and not found_parsnips:
            print("Error: No .parsnips directories found.", file=sys.stderr)
            sys.exit(1)

        return results
