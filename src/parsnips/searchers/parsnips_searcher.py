import bisect
import logging
import sys
from pathlib import Path

import ijson
import regex

from parsnips.models.config.parsnips_config import ParsnipsConfig
from parsnips.models.file_range import FileRange
from parsnips.models.swhid.content_swhid import ParsnipsContentSwhid
from parsnips.models.swhid.swhid_context_qualifiers import SwhidContextQualifiers
from parsnips.pretty_json_dumper import PrettyJsonDumper
from parsnips.utils import get_parsnips_cli_version


class ParsnipsSearcher:

    def __init__(self, parsnips_config: ParsnipsConfig, swhid_context_qualifiers:SwhidContextQualifiers | None = None):
        self.parsnips_config = parsnips_config
        self.parsnips_cli_verison = get_parsnips_cli_version()
        self.logger = logging.getLogger('parsnips')
        self.swhid_context_qualifiers = swhid_context_qualifiers
        self.use_unicode = parsnips_config.search.use_unicode
        self.use_regex = parsnips_config.search.use_regex
        self.strict = parsnips_config.strict

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

    
    def search(self, parsnips_file_path: Path, search_text: str | None, file_range: FileRange | None = None):
        if not parsnips_file_path.exists():
            self.logger.error(f"Missing parsnips.json at {parsnips_file_path}")
            if self.strict:
                sys.exit(1)
            return {}

        # when the search text is missing, treat it as if the user search for the empty string
        if search_text is None:
            search_text = ''

        try:
            if search_text == '':
                # accept any node text
                pattern = regex.compile(r'^.*$')
            else:
                pattern = search_text if self.use_regex else regex.escape(search_text)
            regex_compiled = regex.compile(pattern)
        except regex.error as e:
            self.logger.error(f"Invalid regex: {e}")
            sys.exit(1)

        results = {}
        line_offsets = self._build_line_offsets(parsnips_file_path)

        try:
            with open(parsnips_file_path, 'rb') as f:
                fragment = {}
                parser = ijson.parse(f)
                start_offset = None
                list_fields = ["depends_on_fragment_ids"]
                active_list_key = None

                for prefix, event, value in parser:
                    if prefix.endswith('.fragments.item') and event == 'start_map':
                        fragment = {}
                        start_offset = f.tell()

                    elif prefix.endswith('.fragments.item') and event == 'end_map':
                        end_offset = f.tell()
                        start_line = self._byte_offset_to_line(start_offset, line_offsets)
                        end_line = self._byte_offset_to_line(end_offset, line_offsets)

                                            # Only match if in range (if specified)
                        if file_range and file_range.is_complete():
                            fragment_range = FileRange.model_validate({
                                "start_line_number": fragment.get("start_line_number"),
                                "end_line_number": fragment.get("end_line_number"),
                                "start_col_offset": fragment.get("start_col_offset"),
                                "end_col_offset": fragment.get("end_col_offset")
                            })

                            if not fragment_range.is_complete() or not fragment_range.is_within(file_range):
                                fragment = {}
                                active_list_key = None
                                continue  # Skip this fragment

                        text = fragment.get("text", "")
                        if self.use_unicode:
                            text = self.normalize_unicode(text)

                        match = regex_compiled.search(text)
                        if match:
                            metadata_str = PrettyJsonDumper.dumps(fragment)
                            node_swhid = str(ParsnipsContentSwhid.from_string(metadata_str))

                            qualified_swhid = None
                            if self.swhid_context_qualifiers:
                                qualified_swhid = node_swhid
                                qualifiers = [f"anchor={self.swhid_context_qualifiers.anchor}"]
                                qualifiers.append(f"path=/{parsnips_file_path.name}")
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

                    # elif '.fragments.item.' in prefix:
                    #     parts = prefix.split('.')
                    #     key = parts[-1]

                    #     if key in list_fields:
                    #         if event == 'start_array':
                    #             fragment[key] = []
                    #             active_list_key = key
                    #         elif event == 'end_array':
                    #             active_list_key = None
                    #         elif active_list_key == key:
                    #             fragment.setdefault(key, []).append(value)
                    #         elif event == 'null':
                    #             fragment[key] = []
                    #         else:
                    #             fragment.setdefault(key, []).append(value)
                    #     else:
                    #         fragment[key] = value

                    elif '.fragments.item.' in prefix:
                        parts = prefix.split('.')
                        if parts[-1] == 'item' and parts[-2] in list_fields:
                            key = parts[-2]
                        else:
                            key = parts[-1]

                        if key in list_fields:
                            if event == 'start_array':
                                fragment[key] = []
                                active_list_key = key
                            elif event == 'end_array':
                                active_list_key = None
                            elif event == 'null':
                                fragment[key] = []
                            elif active_list_key == key:
                                fragment.setdefault(key, []).append(value)
                        else:
                            fragment[key] = value


        except Exception as e:
            self.logger.error(f"Streaming parse failed for {parsnips_file_path}: {e}")
            if self.strict:
                sys.exit(1)

        return results

