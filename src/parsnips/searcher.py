import bisect
import sys
from pathlib import Path

import ijson
import regex

from parsnips.pretty_json_dumper import PrettyJsonDumper
from parsnips.swhid import Swhid


class ParsnipsSearcher:

    def __init__(self, logger, context_qualifiers=None, repo_root=None, use_unicode=False, use_regex=False, strict=False):
        self.logger = logger
        self.context_qualifiers = context_qualifiers
        self.repo_root = repo_root
        self.use_unicode = use_unicode
        self.use_regex = use_regex
        self.strict = strict

    def normalize_unicode(self, text):
        import unicodedata
        return unicodedata.normalize("NFC", text)

    def _build_line_offsets(self, file_path):
        offsets = []
        offset = 0
        with open(file_path, 'rb') as f:
            for line in f:
                offsets.append(offset)
                offset += len(line)
        return offsets

    def _byte_offset_to_line(self, byte_offset, line_offsets):
        return bisect.bisect_right(line_offsets, byte_offset)

    def search(self, path: Path, search_text: str):
        parsnips_file = path / "parsnips.json" if path.is_dir() else path
        if not parsnips_file.exists():
            self.logger.error(f"Missing parsnips.json at {parsnips_file}")
            if self.strict:
                sys.exit(1)
            return {}

        try:
            pattern = search_text if self.use_regex else regex.escape(search_text)
            regex_compiled = regex.compile(pattern)
        except regex.error as e:
            self.logger.error(f"Invalid regex: {e}")
            sys.exit(1)

        results = {}
        line_offsets = self._build_line_offsets(parsnips_file)

        try:
            with open(parsnips_file, 'rb') as f:
                fragment = {}
                parser = ijson.parse(f)
                start_offset = None
                list_fields = ["depends_on_fragment_ids"]
                active_list_key = None

                for prefix, event, value in parser:
                    if prefix == 'fragments.item' and event == 'start_map':
                        fragment = {}
                        start_offset = f.tell()
                    elif prefix == 'fragments.item' and event == 'end_map':
                        end_offset = f.tell()
                        start_line = self._byte_offset_to_line(start_offset, line_offsets)
                        end_line = self._byte_offset_to_line(end_offset, line_offsets)

                        text = fragment.get("text", "")
                        if self.use_unicode:
                            text = self.normalize_unicode(text)

                        match = regex_compiled.search(text)
                        if match:
                            metadata_str = PrettyJsonDumper.dumps(fragment)
                            node_swhid = Swhid.compute_content_swhid(metadata_str)

                            qualified_swhid = None
                            if self.context_qualifiers:
                                qualified_swhid = node_swhid
                                qualifiers = [f"anchor={self.context_qualifiers['anchor']}"]
                                qualifiers.append(f"path=/{parsnips_file.name}")
                                qualifiers.append(f"lines={start_line}..{end_line}")
                                qualified_swhid += ";" + ";".join(qualifiers)

                            frag_id = fragment.get("fragment_id")
                            if frag_id is not None:
                                results[str(frag_id)] = {
                                    "search_text": search_text,
                                    "search_used_regex": self.use_regex,
                                    "search_used_unicode": self.use_unicode,
                                    "search_regex_match_groups": match.groupdict() or None,
                                    "node_swhid_without_qualifiers": node_swhid,
                                    "node_swhid_with_qualifiers": qualified_swhid,
                                    "node_metadata": fragment
                                }
                        fragment = {}
                        active_list_key = None
                    elif prefix.startswith('fragments.item.'):
                        parts = prefix.split('.')
                        if parts[-1] == 'item' and len(parts) >= 4:
                            key = parts[-2]
                            if key in list_fields:
                                fragment.setdefault(key, []).append(value)
                        elif len(parts) >= 3:
                            key = parts[2]
                            if key in list_fields:
                                if event == 'start_array':
                                    fragment[key] = []
                                    active_list_key = key
                                elif event == 'end_array':
                                    active_list_key = None
                                elif event == 'number' and active_list_key == key:
                                    fragment.setdefault(key, []).append(value)
                                elif event == 'null':
                                    fragment[key] = []
                            else:
                                fragment[key] = value
        except Exception as e:
            self.logger.error(f"Streaming parse failed for {parsnips_file}: {e}")
            if self.strict:
                sys.exit(1)

        return results
