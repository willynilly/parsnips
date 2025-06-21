import importlib
from argparse import Namespace
from pathlib import Path
from typing import Generator

from same_version.extractors.citation_cff_extractor import CitationCffExtractor


def get_parsnips_version() -> str:
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

