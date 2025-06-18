import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path

from parsnips.extractor import ParsnipsExtractor
from parsnips.searcher import ParsnipsSearcher
from parsnips.swh_context import SWHContext


def main():
    parser = argparse.ArgumentParser(description='Parsnips AST extractor and search tool.')
    parser.add_argument('path', nargs='?', default='.', help='Path to file or directory (default: current directory)')
    parser.add_argument('-c', '--clean', action='store_true', help='Recursively delete all .parsnips folders')
    parser.add_argument('-s', '--search', type=str, help='Regular expression to search within node texts')
    parser.add_argument('-u', '--unicode', action='store_true', help='Normalize search pattern and source code (Unicode NFC)')
    parser.add_argument('-r', '--regex', action='store_true', help='Interpret the search string as a regular expression')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress logs to stdout')
    parser.add_argument('-l', '--logfile', type=str, help='Write logs to specified JSON file')
    parser.add_argument('--strict', action='store_true', help='Abort on first error or missing .parsnips folder')
    parser.add_argument('--repo-url', type=str, help='Repository origin URL (required for context SWHID generation)')
    parser.add_argument('--commit', type=str, help='Commit SHA (if known)')
    parser.add_argument('--release-name', type=str, help='Release name (annotated tag)')
    parser.add_argument('--ref-name', type=str, help='Reference name (branch name or lightweight tag)')
    parser.add_argument('--repo-root', type=str, help='Path to the root of the local repo for relative path resolution. Defaults to current working directory.')

    
    args = parser.parse_args()
    
    # setup logger
    logger = logging.getLogger("parsnips")
    logger.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    if not args.quiet:
        logger.addHandler(stream_handler)

    if args.logfile:
        file_handler = logging.FileHandler(args.logfile, mode='w', encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        logger.addHandler(file_handler)

    
    input_path = Path(args.path)
    if not input_path.exists():
        logger.error(f"Invalid path: {input_path}")
        sys.exit(1)

    if args.clean:
        root_path = input_path if input_path.is_dir() else input_path.parent
        parsnips_dir = root_path / '.parsnips'
        if parsnips_dir.exists():
            try:
                shutil.rmtree(parsnips_dir)
                logger.info(f"Deleted: {parsnips_dir}")
            except Exception as e:
                logger.warning(f"Failed to delete {parsnips_dir}: {e}")
        else:
            logger.info(f"No .parsnips directory found at: {parsnips_dir}")
        sys.exit(0)


    if args.search:
        context_qualifiers: dict | None = None

        if args.repo_url:
            swh_ctx = SWHContext(
                repo_url=args.repo_url,
                commit=args.commit,
                release_name=args.release_name,
                ref_name=args.ref_name
            )
            try:
                context_qualifiers = swh_ctx.get_context_qualifiers()
            except Exception as e:
                logger.error(f"Failed to resolve anchor: {e}")
                sys.exit(1)

        repo_root = args.repo_root or os.getcwd()

        searcher = ParsnipsSearcher(logger=logger, strict=args.strict, use_unicode=args.unicode, use_regex=args.regex, context_qualifiers=context_qualifiers, repo_root=repo_root)
        results = searcher.search(path=input_path, search_text=args.search)
        print(json.dumps(results, indent=2, sort_keys=True, ensure_ascii=False))
        sys.exit(0)

    

    extractor = ParsnipsExtractor(logger=logger, strict=args.strict)
    extractor.process(input_path)
    logger.info("Parsnips extraction complete.")

if __name__ == '__main__':
    main()
