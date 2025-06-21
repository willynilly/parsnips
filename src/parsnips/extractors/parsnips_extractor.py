import json
import os
import sys
from pathlib import Path
from typing import Generator

import pathspec

from parsnips.extractors.parsnips_fragment import ParsnipsFragment
from parsnips.swhid import Swhid


class ParsnipsExtractor:

    def __init__(self, parsnips_version: str, logger, strict=False, repo_root: Path | None = None):
        self.ignore_spec = None
        self.parsnips_version = parsnips_version
        self.sys_argv = [arg for arg in sys.argv]
        self.logger = logger
        self.strict = strict
        self.raw_repo_root = Path(repo_root).resolve() if repo_root else None
        self.file_fragment_generators = []

    def process(self, input_path: Path, args=None):
        input_path = Path(input_path).resolve()
        if self.raw_repo_root is None:
            self.repo_root: Path = input_path if input_path.is_dir() else input_path.parent
        else:
            self.repo_root: Path = self.raw_repo_root

        self.ignore_spec = self._load_ignore_file()

        if input_path.is_file():
            fragment_generator: Generator[ParsnipsFragment, None, None] = self._process_file(input_path)
        elif input_path.is_dir():
            fragment_generator: Generator[ParsnipsFragment, None, None] = self._process_directory(input_path)
        else:
            self.logger.error(f"Invalid path: {input_path}")
            self._abort()

       
        output_path: Path = self.repo_root / "parsnips.json"
        fragment_type: str = self.get_fragment_type()
        parser_script_command: str = self.get_parser_script_command()
        parser_script_version: str = self.get_parser_script_version()
        parser_script_arguments: list[str] = self.get_parser_script_arguments()
        self._stream_fragments_to_file(output_path=output_path, 
                                       fragment_type=fragment_type,
                                       parsnips_version=self.parsnips_version,
                                       parser_script_command = parser_script_command,
                                       parser_script_version=parser_script_version,
                                       parser_script_arguments=parser_script_arguments,
                                       fragment_generator=fragment_generator)

    def get_parser_script_command(self) -> str:
        command = Path(self.sys_argv[0]).name # get the command without the full path
        return command 
    
    def get_parser_script_version(self) -> str:
        command: str = self.get_parser_script_command()
        if command == 'parsnips':
            return self.parsnips_version
        else:
            raise NotImplementedError
    
    def get_parser_script_arguments(self) -> list[str]:
        return self.sys_argv[1:] # get all of the sys.argv values after the command
        
    def get_fragment_type(self) -> str:
        raise NotImplementedError

    def _stream_fragments_to_file(
        self,
        output_path: Path,
        fragment_type: str,
        parsnips_version: str,
        parser_script_command: str,
        parser_script_version: str,
        parser_script_arguments: list[str],
        fragment_generator: Generator[ParsnipsFragment, None, None],
    ):
        with open(output_path, "w", encoding="utf-8") as f:
            parser_script_arg_lines = json.dumps(parser_script_arguments or [], indent=2)[1:-1]
            parser_script_arg_lines = "".join(["    " + p + "\n" for p in parser_script_arg_lines.splitlines()])

            
            f.write('{\n')
            f.write(f'  "parsnips_version": "{parsnips_version}",\n')
            f.write(f'  "fragment_type": "{fragment_type}",\n')
            f.write('  "parser_script": {\n')
            f.write(f'    "command": "{parser_script_command}",\n')
            f.write(f'    "version": "{parser_script_version}",\n')
            f.write('    "arguments": [')
            f.write(f'{parser_script_arg_lines}')
            f.write('    ]\n')
            f.write('  },\n')
            first = True
            has_fragment = False
            for fragment in fragment_generator:
                has_fragment = True
                if first:
                    f.write('  "fragments": [\n')
                if not first:
                    f.write(',\n')
                frag_lines = json.dumps(fragment.to_dict(), ensure_ascii=False, indent=2)[1:-1]
                frag_lines = "".join(["    " + p + "\n" for p in frag_lines.splitlines()])
                f.write("    {" + frag_lines + "    }")
                first = False
            if has_fragment:
                f.write('\n  ]\n')
            else:
                f.write('  "fragments": []\n')
            f.write('}\n')


    # def _process_directory(self, directory: Path) -> Generator[ParsnipsFragment, None, None]:
    #     for root, dirs, files in os.walk(directory):
    #         dirs[:] = [d for d in dirs if d != "__pycache__"]
    #         for file in files:
    #             full_path = Path(root) / file
    #             if file.endswith(".py"):
    #                 yield from self._process_file(full_path)

    def _process_directory(self, directory: Path) -> Generator[ParsnipsFragment, None, None]:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(self.repo_root)

                if not file.endswith(".py"):
                    continue
                
                assert self.ignore_spec is not None
                if self.ignore_spec.match_file(str(rel_path)):
                    self.logger.debug(f"Ignored by .parsnipsignore: {rel_path}")
                    continue

                yield from self._process_file(full_path)


    def _process_file(self, file_path: Path) -> Generator[ParsnipsFragment, None, None]:
        
        rel_path = file_path.relative_to(self.repo_root)
        if self.ignore_spec and self.ignore_spec.match_file(str(rel_path)):
            self.logger.debug(f"Ignored by .parsnipsignore: {rel_path}")
            return
    
        self.logger.info(f"Processing: {file_path}")
        try:
            code = file_path.read_text(encoding="utf-8")
            self.source = code
            file_swhid = Swhid.compute_content_swhid(code)
            file_fragments_generator: Generator[ParsnipsFragment, None, None] = self.get_file_fragments_generator(file_path=file_path, repo_root=self.repo_root, file_swhid=file_swhid, source=code)
            yield from file_fragments_generator
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")
            self._abort()

    def get_file_fragments_generator(self, file_path: Path, repo_root: Path, file_swhid: str, source: str) -> Generator[ParsnipsFragment, None, None]:
        raise NotImplementedError

    def _load_ignore_file(self) -> pathspec.PathSpec:
        ignore_file = self.repo_root / ".parsnipsignore"
        if ignore_file.exists():
            with open(ignore_file, "r", encoding="utf-8") as f:
                return pathspec.PathSpec.from_lines("gitwildmatch", f)
        return pathspec.PathSpec.from_lines("gitwildmatch", [])

    
    def _abort(self):
        if self.strict:
            raise RuntimeError("Strict mode abort triggered")
