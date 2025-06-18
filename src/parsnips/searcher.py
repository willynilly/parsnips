import json
import os
import sys
import unicodedata
from pathlib import Path

import regex

from parsnips.swhid import Swhid


class ParsnipsSearcher:

    def __init__(self,
                 logger,
                 context_qualifiers: dict | None = None,
                 repo_root: str | None = None,  
                 use_unicode=False,
                 use_regex=False, 
                 strict=False):
        self.logger = logger
        self.context_qualifiers = context_qualifiers
        self.repo_root = repo_root
        self.use_unicode = use_unicode
        self.use_regex = use_regex
        self.strict = strict
    
    def normalize_unicode(self, text):
        """Apply Unicode normalization (NFC) to text."""
        return unicodedata.normalize("NFC", text)
    
    
    def search(self, path: Path, search_text:str):
        results = {}

        if self.use_unicode:
            search_text = self.normalize_unicode(search_text)

        if self.use_regex:
            pattern = search_text
        else:
            pattern = regex.escape(search_text)

        try:
            regex_compiled = regex.compile(pattern)
        except regex.error as e:
            self.logger.error(f"Invalid regular expression: {e}")
            sys.exit(1)

        # Determine starting directory
        if path.is_file():
            start_dir = path.parent
        elif path.is_dir():
            start_dir = path
        else:
            self.logger.error(f"Invalid path: {path}")
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
                                    text_to_search = self.normalize_unicode(text) if self.use_unicode else text

                                    match = regex_compiled.search(text_to_search)
                                    if match:
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

                                        # Extract named capture groups (or None)
                                        regex_match_groups = match.groupdict() or None

                                        results[rel_path] = {
                                            "search_text": search_text, # either a literal or a regex pattern
                                            "search_used_regex": self.use_regex,
                                            "search_used_unicode": self.use_unicode,
                                            "search_regex_match_groups": regex_match_groups,
                                            "node_swhid_without_qualifiers": node_swhid_without_qualifiers,
                                            "node_swhid_with_qualifiers": node_swhid_with_qualifiers,
                                            "node_metadata": metadata
                                        }


                                except Exception as e:
                                    msg = f"Error reading {full_path}: {e}"
                                    if self.strict:
                                        self.logger.error(msg)
                                        sys.exit(1)
                                    else:
                                        self.logger.warning(msg)

        if self.strict and not found_parsnips:
            self.logger.error("Error: No .parsnips directories found.")
            sys.exit(1)

        return results
