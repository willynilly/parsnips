import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import unicodedata
from pathlib import Path

import regex

from parsnips.extractor import ParsnipsExtractor


def normalize_unicode(text):
    """Apply Unicode normalization (NFC) to text."""
    return unicodedata.normalize("NFC", text)

def compute_swhid(content_string):
    content_bytes = content_string.encode("utf-8")
    digest = hashlib.blake2s(content_bytes, digest_size=32).hexdigest()
    swhid = f"swh:1:cnt:{digest}"
    return swhid

def search_parsnips(path, pattern, strict=False, normalize_search=False):
    results = {}
    
    # Precompile pattern optionally normalized
    if normalize_search:
        pattern = normalize_unicode(pattern)

    try:
        regex_compiled = regex.compile(pattern)
    except regex.error as e:
        print(f"Invalid regular expression: {e}", file=sys.stderr)
        sys.exit(1)


    if path.is_file():
        start_dir = path.parent
    elif path.is_dir():
        start_dir = path
    else:
        print(f"Invalid path: {path}", file=sys.stderr)
        sys.exit(1)

    found_parsnips = False

    for root, dirs, files in os.walk(start_dir, topdown=True):
        for d in dirs:
            if d == '.parsnips':
                found_parsnips = True
                parsnips_dir = Path(root) / d
                for p_root, _, p_files in os.walk(parsnips_dir, topdown=True):
                    for file in p_files:
                        if file == "node_metadata.json":
                            full_path = Path(p_root) / file
                            try:
                                with open(full_path, encoding='utf-8') as f:
                                    metadata = json.load(f)
                                text = metadata.get("text", "")
                                text_to_search = normalize_unicode(text) if normalize_search else text
                                if regex_compiled.search(text_to_search):
                                    rel_path = os.path.relpath(full_path, start=Path.cwd())
                                    metadata_str = json.dumps(metadata, sort_keys=True, ensure_ascii=False)
                                    node_swhid = compute_swhid(metadata_str)
                                    results[rel_path] = {
                                        "node_swhid": node_swhid,
                                        "node_metadata": metadata
                                    }
                            except Exception as e:
                                print(f"Error reading {full_path}: {e}", file=sys.stderr)

    if strict and not found_parsnips:
        print("Error: No .parsnips directories found.", file=sys.stderr)
        sys.exit(1)

    return results

def main():
    parser = argparse.ArgumentParser(description='Parsnips AST extractor and search tool.')
    parser.add_argument('path', nargs='?', default='.', help='Path to file or directory (default: current directory)')
    parser.add_argument('-c', '--clean', action='store_true', help='Recursively delete all .parsnips folders')
    parser.add_argument('-s', '--search', type=str, help='Regular expression to search within node texts')
    parser.add_argument('-n', '--normalize-search', action='store_true', help='Apply Unicode normalization (NFC) to both the search pattern and node text before regex matching. This only applies to search operations and does not affect extraction. Extraction always preserves exact byte content for archival integrity.')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress logs to stdout')
    parser.add_argument('-l', '--logfile', type=str, help='Write logs to specified JSON file')
    parser.add_argument('--strict', action='store_true', help='Abort on first error or missing .parsnips folder')

    args = parser.parse_args()
    input_path = Path(args.path)

    if args.clean:
        for root, dirs, _ in os.walk(input_path, topdown=True):
            for d in dirs:
                if d == '.parsnips':
                    parsnips_dir = Path(root) / d
                    try:
                        shutil.rmtree(parsnips_dir)
                        print(f"Deleted: {parsnips_dir}")
                    except Exception as e:
                        print(f"Failed to delete {parsnips_dir}: {e}", file=sys.stderr)
        sys.exit(0)

    if args.search:
        results = search_parsnips(input_path, args.search, strict=args.strict, normalize_search=args.normalize_search)
        print(json.dumps(results, indent=2, sort_keys=True, ensure_ascii=False))
        sys.exit(0)

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

    extractor = ParsnipsExtractor(logger=logger, strict=args.strict)
    extractor.process(input_path)
    logger.info("Parsnips extraction complete.")

if __name__ == '__main__':
    main()
