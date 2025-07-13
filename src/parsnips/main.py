# main.py
import argparse
import logging
import os
import sys
from pathlib import Path

from parsnips.extractors.libcst_extractor import LibCSTExtractor
from parsnips.extractors.parsnips_extractor import ParsnipsExtractor
from parsnips.models.config.parsnips_config import ParsnipsConfig
from parsnips.models.extraction import Extraction
from parsnips.models.file_range import FileRange
from parsnips.models.patterns.glob import Glob
from parsnips.models.patterns.pattern_set import PatternSet
from parsnips.models.swhid.swhid_context_qualifiers import SwhidContextQualifiers
from parsnips.pretty_json_dumper import PrettyJsonDumper
from parsnips.searchers.parsnips_searcher import ParsnipsSearcher
from parsnips.utils import (
    get_parsnips_cli_version,
    load_class,
)

PARSNIPS_CLI_VERSION: str = get_parsnips_cli_version()

def main():
    
    args: argparse.Namespace = get_args()

    if args.version:
        show_parsnips_cli_version()
        sys.exit(0)
    
    parsnips_config: ParsnipsConfig = setup_parsnips_config(args=args)
    
    logger: logging.Logger = setup_logger(parsnips_config=parsnips_config)

    parsnips_file_path: Path = get_parsnips_file_path(args=args)


    if args.delete:
        delete_parsnips(parsnips_file_path=parsnips_file_path, logger=logger)
        sys.exit(0)

    if args.search:
        search_parsnips(parsnips_file_path=parsnips_file_path, parsnips_config=parsnips_config, logger=logger)
    else:
        extract_parsnips(parsnips_file_path=parsnips_file_path, parsnips_config=parsnips_config, logger=logger)

def search_parsnips(parsnips_file_path: Path, parsnips_config: ParsnipsConfig, logger: logging.Logger):
    # search a parsnips.json file

    swhid_context_qualifiers: SwhidContextQualifiers | None = None
    if parsnips_config.search.swh.repo_url:
        swhid_context_qualifiers = parsnips_config.search.swh.find_swhid_context_qualifiers()

    if parsnips_config.search.searcher_python_class:
        searcher_class: type = load_class(parsnips_config.search.searcher_python_class)
    else:
        searcher_class: type = ParsnipsSearcher
    
    if not issubclass(searcher_class, ParsnipsSearcher):
        logger.error(f"Invalid searcher class: {searcher_class} should be a subclass of ParsnipsSearcher v{PARSNIPS_CLI_VERSION}")
        exit(1)

    logger.info(f"Using searcher class: {searcher_class}")

    searcher = searcher_class(
        parsnips_config=parsnips_config,
        swhid_context_qualifiers=swhid_context_qualifiers,
    )
    results = searcher.search(parsnips_file_path=parsnips_file_path, search_text=parsnips_config.search.search_text, file_range=parsnips_config.search.file_range)
    print(PrettyJsonDumper.dumps(results))

def extract_parsnips(parsnips_file_path: Path, parsnips_config: ParsnipsConfig, logger: logging.Logger):
    # create parsnips.json
    extractions: list[Extraction] = []
    for extraction_config in parsnips_config.extract.extractions:

        if extraction_config.extractor_python_class:
            extractor_class: type = load_class(extraction_config.extractor_python_class)
        else:
            extractor_class: type = LibCSTExtractor 

        if not issubclass(extractor_class, ParsnipsExtractor) or extractor_class is ParsnipsExtractor:
            logger.error(f"Invalid extractor class: {extractor_class} should be a strict subclass of ParsnipsExtractor v{PARSNIPS_CLI_VERSION}")
            exit(1)

        logger.info(f"Using extractor class: {extractor_class}")

        extractor = extractor_class(
            parsnips_file_path=parsnips_file_path,
            parsnips_config=parsnips_config,
            extraction_config=extraction_config
        )

        extraction: Extraction = extractor.extract()
        extractions.append(extraction)
    
    ParsnipsExtractor.save(parsnips_file_path=parsnips_file_path, parsnips_config=parsnips_config, extractions=extractions)
    logger.info("Extraction complete. Saved to parsnips.json.")

def get_parsnips_file_path(args: argparse.Namespace) -> Path:
    parsnips_file_path: Path = Path("parsnips.json") 
    return parsnips_file_path

def get_parsnips_config_file_path(args: argparse.Namespace) -> Path:
    parsnips_config_file_path: Path = Path('parsnips-config.json')    
    return parsnips_config_file_path

def delete_parsnips(parsnips_file_path: Path | None, logger: logging.Logger):
    if parsnips_file_path and parsnips_file_path.exists():
        try:
            os.remove(parsnips_file_path)
            logger.info(f"Deleted: {parsnips_file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete: {parsnips_file_path} {e}")
    else:
        logger.info(f"No {parsnips_file_path} found.")

def get_args():
    parser = argparse.ArgumentParser(description="Parsnips CST and AST extractor and search tool.")
    parser.add_argument("-d", "--delete", action="store_true", help="Deletes parsnips.json")
    parser.add_argument("-s", "--search", type=str, help="Target string to search within node texts")
    parser.add_argument("-r", "--regex", action="store_true", help="Interpret the target string as a regular expression")
    parser.add_argument("-u", "--unicode", action="store_true", help="Normalize target string and source text")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress logs to stdout")
    parser.add_argument('-l', '--language', type=str, help='Source code language for extraction')
    parser.add_argument('-i', '--include', type=str, nargs="+", help='Glob patterns for source code files to include in search or extraction.')
    parser.add_argument('-e', '--exclude', type=str, nargs="+", help='Glob patterns for source code files to exclude in search or extraction.')
    parser.add_argument('-g', '--log', type=str, help='Path to JSON log file (if already exists, appends, unless strict, which errors)')
    parser.add_argument("-v", "--version", action="store_true", help="Shows version")
    parser.add_argument("--strict", action="store_true", help="Abort on first error")
    parser.add_argument("--start-line-number", type=int, help="Search start line number in target file (1-indexed)")
    parser.add_argument("--start-col-offset", type=int, help="Search start column offset in target file (0-indexed)")
    parser.add_argument("--end-line-number", type=int, help="Search end line number in target file (1-indexed)")
    parser.add_argument("--end-col-offset", type=int, help="Search end column offset in target file (0-indexed)")
    parser.add_argument("--repo-url", type=str)
    parser.add_argument("--commit", type=str)
    parser.add_argument("--release-name", type=str)
    parser.add_argument("--ref-name", type=str)
    parser.add_argument("--repo-root", type=str)
    parser.add_argument("--visit", type=str)
    parser.add_argument("--extractor-class", type=str, help='Class path to Python extractor class to be used for all extractions')
    parser.add_argument("--searcher-class", type=str, help="Class path to Python extractor class to be used for all extractions")
    args: argparse.Namespace = parser.parse_args()
    return args

def show_parsnips_cli_version():
    print('Parsnips v' + PARSNIPS_CLI_VERSION)

def setup_logger(parsnips_config: ParsnipsConfig) -> logging.Logger:
    logger = logging.getLogger("parsnips")
    logger.setLevel(logging.INFO)
    if not parsnips_config.log.quiet:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)
    logfile: Path | None = parsnips_config.log.file_path
    if logfile:
        log_mode: str = "w"
        if not logfile.name.endswith('.json'):
            logger.error(f"Invalid log file: {logfile} must end with .json")
            sys.exit(1)
        if logfile.exists():
            msg = f"Log file aleady exists: {logfile}"
            if parsnips_config.strict:
                logger.error(msg)
                sys.exit(1)
            else:
                logger.warning(msg)
                logger.info(f"Appending to log file: {logfile}")
                log_mode = "a"
        file_handler = logging.FileHandler(logfile, mode=log_mode, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        logger.addHandler(file_handler)
    return logger

def setup_parsnips_config(args: argparse.Namespace) -> ParsnipsConfig:
    # if parsnips-config.json does not exist, 
    # create a default parsnips-config.json
    parnsips_config_file_path: Path = get_parsnips_config_file_path(args=args)
    if not parnsips_config_file_path.exists():
        language: str = args.language if args.language else 'python'
        glob_include_patterns: list[str] = args.include if args.include else ['*.py']
        glob_exclude_patterns: list[str] = args.exclude if args.exclude else []

        default_config: ParsnipsConfig = ParsnipsConfig.from_default(language=language, 
                                                                     glob_include_patterns=glob_include_patterns,
                                                                     glob_exclude_patterns=glob_exclude_patterns)
        with open(str(parnsips_config_file_path), "w") as f:
            f.write(default_config.model_dump_json(indent=2))

    # load the config file
    if not parnsips_config_file_path.exists():
        print(f'Missing configuration file: {parnsips_config_file_path}')
        sys.exit(1)
    else:
        parsnips_config: ParsnipsConfig = ParsnipsConfig.from_json_file(parnsips_config_file_path)

    # make CLI arguments take precedence over configuration file.
    # so update the parsnips_config to use the CLI arguments if provided
    if args.strict:
        parsnips_config.strict = True
    if args.quiet:
        parsnips_config.log.quiet = True
    if args.log:
        parsnips_config.log.file_path = args.log
    if args.search:
        parsnips_config.search.search_text = args.search
    if args.regex:
        parsnips_config.search.use_regex = True
    if args.unicode:
        parsnips_config.search.use_unicode = True
    if (args.language and not args.include) or (args.include and not args.language):
        print('Invalid source code settings: --language and --include settings must be specified together.')
        sys.exit(1)
    if args.language and args.include:
        # use default extraction for the singular language
        default_config: ParsnipsConfig = ParsnipsConfig.from_default(language=args.language, glob_include_patterns=args.include)
        parsnips_config.extract = default_config.extract
    if args.repo_url:
        parsnips_config.search.swh.repo_url = args.repo_url
    if args.commit:
        parsnips_config.search.swh.commit = args.commit
    if args.release_name:
        parsnips_config.search.swh.release_name = args.release_name
    if args.ref_name:
        parsnips_config.search.swh.ref_name = args.ref_name
    if args.visit:
        parsnips_config.search.swh.visit = args.visit
    if args.searcher_class:
        parsnips_config.search.searcher_python_class = args.searcher_class
    if args.exclude:
        exclude_patterns: PatternSet = PatternSet(regex=[], glob=[Glob(pattern=pattern) for pattern in glob_exclude_patterns])
        parsnips_config.search.exclude_patterns = exclude_patterns
        for extraction_config in parsnips_config.extract.extractions:
            extraction_config.exclude_patterns = exclude_patterns
    if args.include:
        include_patterns: PatternSet = PatternSet(regex=[], glob=[Glob(pattern=pattern) for pattern in glob_include_patterns])
        parsnips_config.search.include_patterns = include_patterns
        for extraction_config in parsnips_config.extract.extractions:
            extraction_config.include_patterns = include_patterns

    if args.extractor_class:
        # if an extractor_class is specified, apply it all extractions
        for extraction_config in parsnips_config.extract.extractions:
            extraction_config.extractor_python_class = args.extractor_class

    file_range_properties: list[str] = ['start_line_number', 'end_line_number', 'start_col_offset', 'end_col_offset']
    if any([p in args for p in file_range_properties]):
        if not all([p in args for p in file_range_properties]):
            print('Invalid source code settings: if any of the following properties are set, then all of them must be set: --start-line-number, --end-line-number, --start-col-offset, --end-col-offset')
            sys.exit(1)
        file_range: FileRange = FileRange(start_line_number=args.start_line_number,
                                      start_col_offset=args.start_col_offset,
                                      end_line_number=args.end_line_number,
                                      end_col_offset=args.end_col_offset) 
        parsnips_config.search.file_range = file_range

    return parsnips_config


if __name__ == "__main__":
    main()
