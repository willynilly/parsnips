# main.py
import argparse
import logging
import os
import sys
from pathlib import Path

from parsnips.extractors.libcst_extractor import LibCSTExtractor
from parsnips.extractors.parsnips_extractor import ParsnipsExtractor
from parsnips.models.config.parsnips_config import ParsnipsConfig
from parsnips.models.config.swh_search_config import SwhSearchConfig
from parsnips.models.extraction import Extraction
from parsnips.models.swhid.swhid_context_qualifiers import SwhidContextQualifiers
from parsnips.pretty_json_dumper import PrettyJsonDumper
from parsnips.searchers.parsnips_searcher import ParsnipsSearcher
from parsnips.utils import get_parsnips_cli_version, load_class

PARSNIPS_CLI_VERSION: str = get_parsnips_cli_version()

def main():
    parser = argparse.ArgumentParser(description="Parsnips CST and AST extractor and search tool.")
    parser.add_argument("path", nargs="?", default=".", help="Path to file or directory to search or extract (default: current directory)")
    parser.add_argument("-d", "--delete", action="store_true", help="Deletes parsnips.json")
    parser.add_argument("-s", "--search", type=str, help="Target string to search within node texts")
    parser.add_argument("-r", "--regex", action="store_true", help="Interpret the target string as a regular expression")
    parser.add_argument("-u", "--unicode", action="store_true", help="Normalize target string and source text")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress logs to stdout")
    parser.add_argument('-l', '--language', type=str, help='Source code language for extraction')
    parser.add_argument('-i', '--include', type=str, nargs="+", help='Glob patterns for source code files.')
    parser.add_argument('-g', '--logfile', type=str, help='Path to JSON logfile (if already exists, appends, unless strict, which errors)')
    parser.add_argument("-v", "--version", action="store_true", help="Shows version")
    parser.add_argument('-c', "--config", type=str, default="parsnips-config.json", help="The configuration JSON file (default: parsnips-config.json).")
    parser.add_argument("--strict", action="store_true", help="Abort on first error")
    parser.add_argument("--repo-url", type=str)
    parser.add_argument("--commit", type=str)
    parser.add_argument("--release-name", type=str)
    parser.add_argument("--ref-name", type=str)
    parser.add_argument("--repo-root", type=str)
    parser.add_argument("--extractor-class", type=str, help='Class path to Python extractor class to be used for all extractions')
    parser.add_argument("--searcher-class", type=str, help="Class path to Python extractor class to be used for all extractions")


    args = parser.parse_args()

    if args.version:
        print('Parsnips v' + PARSNIPS_CLI_VERSION)
        sys.exit(0)

    input_path = Path(args.path)
    if not input_path.exists():
        print(f"Invalid path: {input_path}")
        sys.exit(1)
    root_path: Path = input_path if input_path.is_dir() else input_path.parent
    

    # if args.config is parsnips-config.json and parsnips-config.json does not exist, 
    # then create a default parsnips-config.json
    repo_root: Path | None = None
    if args.config == 'parsnips-config.json' and not (root_path / 'parsnips-config.json').exists():
        language: str = args.language if args.language else 'python'
        glob_include_patterns: list[str] = args.include if args.include else ['*.py']
        repo_root = root_path
        default_config: ParsnipsConfig = ParsnipsConfig.from_default(language=language, 
                                                                     glob_include_patterns=glob_include_patterns, 
                                                                     repo_root=repo_root)
        with open(str(root_path / 'parsnips-config.json'), "w") as f:
            f.write(default_config.model_dump_json(indent=2))

    # load the config file
    parsnips_config_path: Path = Path(args.config)
    if not parsnips_config_path.exists():
        print(f'Missing configuration file: {parsnips_config_path}')
        sys.exit(1)
    else:
        parsnips_config: ParsnipsConfig = ParsnipsConfig.from_json_file(parsnips_config_path)

    # make CLI arguments take precedence over configuration file.
    # so update the parsnips_config to use the CLI arguments if provided
    if args.strict:
        parsnips_config.strict = True
    if args.quiet:
        parsnips_config.log.quiet = True
    if args.logfile:
        parsnips_config.log.filename = args.logfile
    if args.regex:
        parsnips_config.search.use_regex = True
    if args.unicode:
        parsnips_config.search.use_unicode = True
    if (args.language and not args.include) or (args.include and not args.language):
        print('Invalid source code settings: --language and --include settings must be specified together.')
        sys.exit(1)
    if args.language and args.include:
        # use default extraction for the singular language
        default_config: ParsnipsConfig = ParsnipsConfig.from_default(language=args.language, glob_include_patterns=args.include, repo_root=root_path)
        parsnips_config.extract = default_config.extract
    if args.repo_url:
        parsnips_config.search.repo_url = args.repo_url
    if args.commit:
        parsnips_config.search.commit = args.commit
    if args.release_name:
        parsnips_config.search.release_name = args.release_name
    if args.ref_name:
        parsnips_config.search.ref_name = args.ref_name
    if args.repo_root:
        parsnips_config.repo_root = Path(args.repo_root)
    if args.searcher_class:
        parsnips_config.search.searcher_python_class = args.searcher_class
    if args.extractor_class:
        # if an extractor_class is specified, apply it all extractions
        for extraction_config in parsnips_config.extract.extractions:
            extraction_config.extractor_python_class = args.extractor_class
    


    logger = logging.getLogger("parsnips")
    logger.setLevel(logging.INFO)
    if not parsnips_config.log.quiet:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)
    logfile: Path | None = parsnips_config.log.filename
    if logfile:
        log_mode: str = "w"
        if not logfile.name.endswith('.json'):
            logger.error(f"Invalid log file: {logfile} must end with .json")
            sys.exit(1)
        if logfile.exists():
            msg = f"Log file aleady exists: {logfile}"
            if args.strict:
                logger.error(msg)
                sys.exit(1)
            else:
                logger.warning(msg)
                logger.info(f"Appending to log file: {logfile}")
                log_mode = "a"
        file_handler = logging.FileHandler(logfile, mode=log_mode, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        logger.addHandler(file_handler)

    if args.delete:
        parsnips_file = root_path / 'parsnips.json'
        if parsnips_file.exists():
            try:
                os.remove(parsnips_file)
                logger.info(f"Deleted: {parsnips_file}")
            except Exception as e:
                logger.warning(f"Failed to delete: {parsnips_file} {e}")
        else:
            logger.info(f"No {parsnips_file} found.")
        sys.exit(0)

    if args.search:
        # search a parsnips.json file

        swhid_context_qualifiers: SwhidContextQualifiers | None = None
        if parsnips_config.search.repo_url:
            swh_search_config = SwhSearchConfig(
                repo_url=parsnips_config.search.repo_url,
                commit=parsnips_config.search.commit,
                release_name=parsnips_config.search.release_name,
                ref_name=parsnips_config.search.ref_name,
            )
            swhid_context_qualifiers = swh_search_config.find_swhid_context_qualifiers()

        if parsnips_config.search.searcher_python_class:
            searcher_class: type = load_class(parsnips_config.search.searcher_python_class)
        else:
            searcher_class: type = ParsnipsSearcher
        
        if not issubclass(searcher_class, ParsnipsSearcher):
            logger.error(f"Invalid searcher class: {searcher_class} should be a subclass of ParsnipsSearcher v{PARSNIPS_CLI_VERSION}")
            exit(1)

        logger.info(f"Using searcher class: {searcher_class}")

        searcher = searcher_class(
            parsnips_cli_version=PARSNIPS_CLI_VERSION,
            swhid_context_qualifiers=swhid_context_qualifiers,
            repo_root=parsnips_config.repo_root or os.getcwd(),
            use_unicode=parsnips_config.search.use_unicode,
            use_regex=args.regex,
            strict=parsnips_config.strict
        )
        results = searcher.search(input_path, args.search)
        print(PrettyJsonDumper.dumps(results))
    else:
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

            repo_root = parsnips_config.repo_root if parsnips_config.repo_root else None
            extractor = extractor_class(
                parsnips_config=parsnips_config,
                extraction_config=extraction_config,
                repo_root=repo_root
            )

            extraction: Extraction = extractor.extract(input_path)
            extractions.append(extraction)

        raw_repo_root: Path | None = parsnips_config.repo_root if parsnips_config.repo_root else None
        resolved_input_path = Path(input_path).resolve()
        if raw_repo_root is None:
            repo_root = resolved_input_path if resolved_input_path.is_dir() else resolved_input_path.parent
        else:
            repo_root = raw_repo_root
        
        ParsnipsExtractor.save(parsnips_config=parsnips_config, extractions=extractions, repo_root=repo_root)
        logger.info("Extraction complete. Saved to parsnips.json.")


if __name__ == "__main__":
    main()
