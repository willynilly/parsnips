import logging
import sys
from pathlib import Path

import ijson
import regex

from parsnips.models.config.parsnips_config import ParsnipsConfig
from parsnips.models.file_range import FileRange
from parsnips.models.parsnips_fragment import ParsnipsFragment
from parsnips.models.parsnips_search_result import ParsnipsSearchResult
from parsnips.models.parsnips_search_results import ParsnipsSearchResults
from parsnips.models.swhid.swhid_context_qualifiers import SwhidContextQualifiers
from parsnips.utils import get_parsnips_cli_version


class ParsnipsSearcher:

    def __init__(self, parsnips_config: ParsnipsConfig):
        self.parsnips_config = parsnips_config
        self.parsnips_cli_verison = get_parsnips_cli_version()
        self.logger = logging.getLogger('parsnips')
        self.strict = parsnips_config.strict
        
        self.swhid_context_qualifiers: SwhidContextQualifiers | None = None
        if self.parsnips_config.search.swh.repo_url:
            try:
                self.logger.info('Searching Software Heritage Archive for SWHID context qualifiers...')
                self.swhid_context_qualifiers = parsnips_config.search.swh.find_swhid_context_qualifiers()        
            except ValueError as e:
                msg: str = f"SWHID context qualifiers not found in Software Heritage Archive: {e}"
                if self.strict:
                    self.logger.error(msg=msg)
                    sys.exit(1)
                else:
                    self.logger.warning(msg=msg)

        self.use_unicode = parsnips_config.search.use_unicode
        self.use_regex = parsnips_config.search.use_regex

    def normalize_unicode(self, text) -> str:
        import unicodedata
        return unicodedata.normalize("NFC", text)

    def search(self, parsnips_file_path: Path, search_text: str | None, file_range: FileRange | None = None) -> ParsnipsSearchResults:
        results: ParsnipsSearchResults = ParsnipsSearchResults()
        if not parsnips_file_path.exists():
            self.logger.error(f"Missing parsnips.json at {parsnips_file_path}")
            if self.strict:
                sys.exit(1)
            return results

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
            
        try:
            with open(parsnips_file_path, 'rb') as f:
                fragment: dict = {}
                parser = ijson.parse(f)
                list_fields = ["depends_on_fragment_ids"]
                active_list_key = None

                for prefix, event, value in parser:
                    if prefix.endswith('.fragments.item') and event == 'start_map':
                        fragment = {}

                    elif prefix.endswith('.fragments.item') and event == 'end_map':
                        
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
                        
                        parsnips_fragment: ParsnipsFragment = ParsnipsFragment.model_validate(fragment)

                        text: str = parsnips_fragment.text or ""
                        if self.use_unicode:
                            text = self.normalize_unicode(text)

                        match = regex_compiled.search(text)
                        if match:
                            node_swhid: str = parsnips_fragment.swhid or ''
                            if node_swhid == '':
                                self.logger.error(f'Missing SWHID for fragment: {parsnips_fragment}')
                                sys.exit(1)
                            if self.swhid_context_qualifiers and self.swhid_context_qualifiers.anchor:
                                qualifiers: list[str] = []
                                qualifiers.append(f"anchor={self.swhid_context_qualifiers.anchor}")
                                qualifiers.append(f"path=/{parsnips_fragment.source_path}")
                                node_swhid +=  ";" + ";".join(qualifiers)

                            frag_id = fragment.get("fragment_id")
                            if frag_id is not None:
                                result: ParsnipsSearchResult = ParsnipsSearchResult(
                                    search_text=search_text,
                                    search_used_regex=self.use_regex,
                                    search_used_unicode=self.use_unicode,
                                    search_regex_match_groups=match.groupdict() or None,
                                    node_swhid=node_swhid,
                                    node_metadata=parsnips_fragment
                                )
                                results.results[str(frag_id)] = result

                        fragment = {}
                        active_list_key = None

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

