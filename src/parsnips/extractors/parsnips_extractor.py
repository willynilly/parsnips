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


class ParsnipsExtractorError(RuntimeError):
    pass

class ParsnipsExtractor:

    VCS_ROOT_FOLDERS: list[str] = ['.git', # Git 
                                    '.svn', # Subversion
                                    '.hg', # Mercurial
                                    '.bzr' # Bazaar
                                  ]

    def __init__(self, parsnips_file_path: Path, parsnips_config: ParsnipsConfig, extraction_config: ExtractionConfig):
        self.parsnips_file_path = parsnips_file_path
        self.parsnips_config = parsnips_config
        self.extraction_config = extraction_config
        self.source_file_language = extraction_config.language
        self.logger = logging.getLogger("parsnips")
        self.strict = parsnips_config.strict
        self.file_fragment_generators = []

        self.repo_root: Path = Path(self.parsnips_file_path.parent).resolve() # the absolute path to the local repo directory
        
        # make sure the repo root is a root folder
        # it must contain a subfolder for a recognized CVS (e.g., like .git subfolder for a Git repo)
        if not any([(self.repo_root / folder).is_dir() for folder in self.VCS_ROOT_FOLDERS]):
            msg: str = f'Repo root is not a root folder for any known VCS: {self.repo_root}'
            if self.strict:
                self.logger.error(msg)
                self._abort()
            else:
                self.logger.warning(msg)

    
    def get_fragment_type(self) -> str:
        raise NotImplementedError
    
    def get_supported_languages(self) -> list[str]:
        raise NotImplementedError

    def extract(self) -> Extraction:

        supported_languages = [language.casefold() for language in self.get_supported_languages()]
        source_file_language = self._get_normalized_source_file_language()
        
        if source_file_language not in supported_languages:
            self.logger.error(f"Unsupported language: {source_file_language}")
            self._abort()

        if self.repo_root.is_dir():
            fragment_generator: Generator[ParsnipsFragment, None, None] = self._process_directory(directory=self.repo_root)
        else:
            self.logger.error(f"Invalid repo root: {self.repo_root}")
            self._abort()

        extraction = Extraction(extraction_config=self.extraction_config, fragment_type=self.get_fragment_type(), fragment_generator=fragment_generator)
        return extraction

    def _get_normalized_source_file_language(self) -> str:
        return self.source_file_language.casefold()
    
    @staticmethod
    def save(parsnips_file_path: Path, parsnips_config: ParsnipsConfig, extractions: list[Extraction]):
        logger = logging.getLogger("parsnips")
        if parsnips_file_path.exists():
            logger.info("parsnips.json already exists. Overwriting it.")
        parsnips_cli_version = get_parsnips_cli_version()

        with open(parsnips_file_path, "w", encoding="utf-8") as f:
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

                    frag_json: str = fragment.to_pretty_json()
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
                    self.logger.debug(f"Skipped: {rel_path}")
                    continue

                yield from self._process_file(full_path)
    
    def _process_file(self, file_path: Path) -> Generator[ParsnipsFragment, None, None]:
        
        rel_path = file_path.relative_to(self.repo_root)
        if self._is_ignored(rel_path):
            self.logger.info(f"Ignored: {rel_path}")
            return
    
        self.logger.info(f"Extracting: {file_path}")
        try:
            file_fragments_generator: Generator[ParsnipsFragment, None, None] = self.get_file_fragments_generator(file_path=file_path, repo_root=self.repo_root)
            yield from file_fragments_generator
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")
            self._abort()

    def _create_swhid(self, file_path: Path, start_byte: int, end_byte: int) -> str:
        swhid:str = str(ParsnipsContentSwhid.from_file(file_path)) + f";bytes={start_byte}-{end_byte}"
        return swhid


    def get_file_fragments_generator(self, file_path: Path, repo_root: Path) -> Generator[ParsnipsFragment, None, None]:
        raise NotImplementedError
    
    def _abort(self):
        raise ParsnipsExtractorError("Abort extraction.")
