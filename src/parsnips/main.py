# main.py
import argparse
import logging
import os
import sys
from pathlib import Path

from parsnips.extractor import ParsnipsExtractor
from parsnips.pretty_json_dumper import PrettyJsonDumper
from parsnips.searcher import ParsnipsSearcher
from parsnips.swh_context import SWHContext


def main():
    parser = argparse.ArgumentParser(description="Parsnips AST extractor and search tool.")
    parser.add_argument("path", nargs="?", default=".", help="Path to file or directory (default: current directory)")
    parser.add_argument("-c", "--clean", action="store_true", help="Deletes parsnips.json")
    parser.add_argument("-s", "--search", type=str, help="Regular expression to search within node texts")
    parser.add_argument("-r", "--regex", action="store_true", help="Interpret the search string as a regular expression")
    parser.add_argument("-u", "--unicode", action="store_true", help="Normalize search input and source text")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress logs to stdout")
    parser.add_argument('-l', '--logfile', type=str, help='Write logs to specified JSON file (if already exists, appends, unless strict, which errors)')
    parser.add_argument("--strict", action="store_true", help="Abort on first error")
    parser.add_argument("--repo-url", type=str)
    parser.add_argument("--commit", type=str)
    parser.add_argument("--release-name", type=str)
    parser.add_argument("--ref-name", type=str)
    parser.add_argument("--repo-root", type=str)

    args = parser.parse_args()

    logger = logging.getLogger("parsnips")
    logger.setLevel(logging.INFO)
    if not args.quiet:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(handler)

    if args.logfile:
        log_mode: str = "w"
        if not args.logfile.endswith('.json'):
            logger.error(f"Invalid log file: {args.logfile} must end with .json")
            sys.exit(1)
        if Path(args.logfile).exists():
            msg = f"Log file aleady exists: {args.logfile}"
            if args.strict:
                logger.error(msg)
                sys.exit(1)
            else:
                logger.warning(msg)
                logger.info(f"Appending to log file: {args.logfile}")
                log_mode = "a"
        file_handler = logging.FileHandler(args.logfile, mode=log_mode, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        logger.addHandler(file_handler)

    input_path = Path(args.path)
    if not input_path.exists():
        logger.error(f"Invalid path: {input_path}")
        sys.exit(1)

    if args.clean:
        root_path = input_path if input_path.is_dir() else input_path.parent
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
        context_qualifiers = None
        if args.repo_url:
            swh_ctx = SWHContext(
                repo_url=args.repo_url,
                commit=args.commit,
                release_name=args.release_name,
                ref_name=args.ref_name,
            )
            context_qualifiers = swh_ctx.get_context_qualifiers()

        searcher = ParsnipsSearcher(
            logger=logger,
            context_qualifiers=context_qualifiers,
            repo_root=args.repo_root or os.getcwd(),
            use_unicode=args.unicode,
            use_regex=args.regex,
            strict=args.strict
        )
        results = searcher.search(input_path, args.search)
        print(PrettyJsonDumper.dumps(results))
    else:
        extractor = ParsnipsExtractor(
            logger=logger,
            strict=args.strict,
            repo_root=args.repo_root
        )
        extractor.process(input_path, args=vars(args))
        logger.info("Extraction complete. Saved to parsnips.json.")


if __name__ == "__main__":
    main()
