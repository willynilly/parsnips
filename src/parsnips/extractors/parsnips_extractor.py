import json
import logging
import os
from pathlib import Path
from typing import Generator

from parsnips.models.config.extraction_config import ExtractionConfig
from parsnips.models.config.parsnips_config import ParsnipsConfig
from parsnips.models.extraction import Extraction
from parsnips.models.parsnips_fragment import ParsnipsFragment
from parsnips.models.swhid.content_swhid import ParsnipsContentSwhid
from parsnips.utils import get_parsnips_cli_version


class ParsnipsExtractor:

    def __init__(self, parsnips_config: ParsnipsConfig, extraction_config: ExtractionConfig, repo_root: Path | None = None):
        self.parsnips_config = parsnips_config
        self.extraction_config = extraction_config
        self.source_file_language = extraction_config.language
        self.logger = logging.getLogger("parsnips")
        self.strict = parsnips_config.strict
        self.raw_repo_root = Path(repo_root).resolve() if repo_root else None
        self.file_fragment_generators = []
    
    def get_fragment_type(self) -> str:
        raise NotImplementedError
    
    def get_supported_languages(self) -> list[str]:
        raise NotImplementedError

    def extract(self, input_path: Path) -> Extraction:

        supported_languages = [language.casefold() for language in self.get_supported_languages()]
        source_file_language = self._get_normalized_source_file_language()
        
        if source_file_language not in supported_languages:
            self.logger.error(f"Unsupported language: {source_file_language}")
            exit(1)

        input_path = Path(input_path).resolve()
        if self.raw_repo_root is None:
            self.repo_root: Path = input_path if input_path.is_dir() else input_path.parent
        else:
            self.repo_root: Path = self.raw_repo_root

        if input_path.is_file():
            fragment_generator: Generator[ParsnipsFragment, None, None] = self._process_file(input_path)
        elif input_path.is_dir():
            fragment_generator: Generator[ParsnipsFragment, None, None] = self._process_directory(input_path)
        else:
            self.logger.error(f"Invalid path: {input_path}")
            self._abort()

        extraction = Extraction(extraction_config=self.extraction_config, fragment_type=self.get_fragment_type(), fragment_generator=fragment_generator)
        return extraction

    def _get_normalized_source_file_language(self) -> str:
        return self.source_file_language.casefold()
    
    # @staticmethod
    # def save(parsnips_config:ParsnipsConfig, extractions: list[Extraction], repo_root: Path):
    #     output_path: Path = repo_root / "parsnips.json"
    #     parsnips_cli_version = get_parsnips_cli_version()

    #     with open(output_path, "w", encoding="utf-8") as f:
            
    #         f.write('{\n')
    #         f.write(f'  "parsnips_protocol_version": {json.dumps(parsnips_config.parsnips_protocol_version)},\n')
    #         f.write(f'  "parsnips_cli_version": {json.dumps(parsnips_cli_version)},\n')
    #         f.write(f'  "strict": {json.dumps(parsnips_config.strict)},\n')

    #         # f.write(f'  "fragment_type": {json.dumps(fragment_type)},\n')
            
    #         # if len(source_file_languages) == 0:
    #         #     f.write('  "source_file_languages": [],\n')
    #         # else:
    #         #     source_file_languages_lines = json.dumps(source_file_languages or [], indent=2)[1:-1]
    #         #     source_file_languages_lines = "".join(["  " + p + "\n" for p in source_file_languages_lines.splitlines()])
    #         #     f.write('  "source_file_languages": [')
    #         #     f.write(f'{source_file_languages_lines}')
    #         #     f.write('  ],\n')
            
    #         # if len(source_file_whitelist_regex_patterns_by_language_map.keys()) == 0:
    #         #     f.write('  "source_file_whitelist_regex_patterns_by_language_map": {},\n')
    #         # else:
    #         #     f.write('  "source_file_whitelist_regex_patterns_by_language_map": {\n')
    #         #     first_lang = True
    #         #     for k, v in source_file_whitelist_regex_patterns_by_language_map.items():
    #         #         if not first_lang:
    #         #             f.write(',\n')
    #         #         if isinstance(v, list) and len(v) == 0:
    #         #             f.write(f'    {json.dumps(k)}: []')
    #         #         else:
    #         #             f.write(f'    {json.dumps(k)}: [\n')
    #         #             first_regex = True
    #         #             for regex_pattern in v:
    #         #                 if not first_regex:
    #         #                     f.write(',\n')
    #         #                 f.write(f'      {json.dumps(regex_pattern)}')
    #         #                 first_regex = False
    #         #             f.write('\n    ]')
    #         #         first_lang = False
    #         #     f.write('\n  },\n')

    #         # f.write('  "parser_script": {\n')
    #         # f.write(f'    "command": {json.dumps(parser_script_command)},\n')
    #         # f.write(f'    "version": {json.dumps(parser_script_version)},\n')
            
    #         # if len(parser_script_arguments) == 0:
    #         #     f.write('    "arguments": []\n')
    #         # else:
    #         #     parser_script_arg_lines = json.dumps(parser_script_arguments or [], indent=2)[1:-1]
    #         #     parser_script_arg_lines = "".join(["    " + p + "\n" for p in parser_script_arg_lines.splitlines()])
    #         #     f.write('    "arguments": [')
    #         #     f.write(f'{parser_script_arg_lines}')
    #         #     f.write('    ]\n')
            
    #         # f.write('  },\n')
    #         first_extraction: bool = True
    #         has_extraction: bool = False
    #         for extraction in extractions:
    #             has_extraction = True
    #             if first_extraction:
    #                 f.write('  "extractions": [\n')
    #             else:
    #                 f.write(',\n')

    #             f.write('{\n')
                
    #             f.write(f'  "fragment_type": {json.dumps(extraction.fragment_type)},\n')
    #             f.write(f'  "config": {json.dumps(extraction.extraction_config.model_dump())},\n')

    #             first_fragment = True
    #             has_fragment = False
    #             for fragment in extraction.fragment_generator:
    #                 has_fragment = True
    #                 if first_fragment:
    #                     f.write('     "fragments": [\n')
    #                 else:
    #                     f.write(',\n')
    #                 frag_lines = fragment.to_pretty_json(ensure_ascii=False, indent=2)[1:-1]
    #                 frag_lines = "".join(["    " + p + "\n" for p in frag_lines.splitlines()])
    #                 f.write("    {" + frag_lines + "    }")
    #                 first_fragment = False
    #             if has_fragment:
    #                 f.write('\n  ]\n')
    #             else:
    #                 f.write('     "fragments": []\n')
    #             f.write('}\n')
    #             first_extraction = False
    #         if has_extraction:
    #             f.write('\n  ]\n')
    #         else:
    #             f.write('  "extractions": []\n')
    #         f.write('}\n')



    @staticmethod
    def save(parsnips_config: ParsnipsConfig, extractions: list[Extraction], repo_root: Path):
        output_path: Path = repo_root / "parsnips.json"
        parsnips_cli_version = get_parsnips_cli_version()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write('{\n')
            f.write(f'  "parsnips_protocol_version": {json.dumps(parsnips_config.parsnips_protocol_version)},\n')
            f.write(f'  "parsnips_cli_version": {json.dumps(parsnips_cli_version)},\n')
            f.write(f'  "strict": {json.dumps(parsnips_config.strict)},\n')

            has_extraction = False
            first_extraction = True

            for extraction in extractions:
                if not has_extraction:
                    f.write('  "extractions": [\n')

                if not first_extraction:
                    f.write(',\n')

                f.write('    {\n')

                # fragment_type
                f.write(f'      "fragment_type": {json.dumps(extraction.fragment_type)},\n')

                # config
                config_json = json.dumps(extraction.extraction_config.model_dump(), indent=2)
                config_lines = config_json.splitlines()
                f.write('      "config": {\n')
                for line in config_lines[1:-1]:
                    f.write(f'        {line}\n')
                f.write('      },\n')

                # fragments
                first_fragment = True
                has_fragment = False

                for fragment in extraction.fragment_generator:
                    if not has_fragment:
                        f.write('      "fragments": [\n')

                    if not first_fragment:
                        f.write(',\n')

                    frag_json = fragment.to_pretty_json(indent=2, ensure_ascii=False)
                    indented_json = ''.join(f'        {line}\n' for line in frag_json.splitlines())
                    indented_json = indented_json.rstrip('\n')
                    f.write(indented_json)

                    first_fragment = False
                    has_fragment = True

                if has_fragment:
                    f.write('\n      ]\n')
                else:
                    f.write('      "fragments": []\n')

                f.write('    }')

                has_extraction = True
                first_extraction = False

            if has_extraction:
                f.write('\n  ]\n')
            else:
                f.write('  "extractions": []\n')

            f.write('}\n')

    
    def _is_ignored(self, file_path: Path) -> bool:
        return self.extraction_config.is_ignored(file_path=file_path)

    def _process_directory(self, directory: Path) -> Generator[ParsnipsFragment, None, None]:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(self.repo_root)

                if self._is_ignored(rel_path):
                    self.logger.info(f"Ignored: {rel_path}")
                    continue

                yield from self._process_file(full_path)
    
    def _process_file(self, file_path: Path) -> Generator[ParsnipsFragment, None, None]:
        
        rel_path = file_path.relative_to(self.repo_root)
        if self._is_ignored(rel_path):
            self.logger.info(f"Ignored: {rel_path}")
            return
    
        self.logger.info(f"Extracting: {file_path}")
        try:
            file_swhid:str = str(ParsnipsContentSwhid.from_file(file_path))
            file_fragments_generator: Generator[ParsnipsFragment, None, None] = self.get_file_fragments_generator(file_path=file_path, repo_root=self.repo_root, file_swhid=file_swhid)
            yield from file_fragments_generator
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")
            self._abort()

    def get_file_fragments_generator(self, file_path: Path, repo_root: Path, file_swhid: str) -> Generator[ParsnipsFragment, None, None]:
        raise NotImplementedError
    
    def _abort(self):
        if self.strict:
            raise RuntimeError("Strict mode abort triggered")
