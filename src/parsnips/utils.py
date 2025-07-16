import importlib
import sys
from argparse import Namespace
from pathlib import Path
from typing import Generator

from same_version.extractors.citation_cff_extractor import CitationCffExtractor


def get_parsnips_cli_version() -> str:
    cli_args = Namespace()
    cli_args.citation_cff_path = Path(__file__).parent.parent.parent / 'CITATION.cff'
    return CitationCffExtractor(cli_args=cli_args).extract_version() or ""

def concat_generators(generators: list[Generator[dict, None, None]]) -> Generator[dict, None, None]:
    for g in generators:
        yield from g

def load_class(path: str) -> type:
    module_path, _, class_name = path.rpartition(".")
    if not module_path or not class_name:
        raise ValueError(f"Invalid class path: '{path}'")
    
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not isinstance(cls, type):
        raise TypeError(f"{class_name} is not a class in module {module_path}")
    
    return cls

def get_parser_script_command() -> str:
    command = Path(sys.argv[0]).name # get the command without the full path
    return command 

def get_parser_script_arguments() -> list[str]:
    return sys.argv[1:] # get all of the sys.argv values after the command

def load_gitignore_patterns(file_path: Path | None = None) -> list[str]:
    if file_path is None:
        file_path = Path('.gitignore')
    patterns: list[str] = []
    if file_path.exists():
        with open(file_path, "r") as f:
            patterns = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
    return patterns
