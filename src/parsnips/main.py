
import argparse
import logging
import json
import os
import sys
from pathlib import Path
import shutil
from parsnips.extractor import ParsnipsExtractor

class JsonLogHandler(logging.Handler):
    def __init__(self, log_path):
        super().__init__()
        self.log_path = log_path
        self.logs = []

    def emit(self, record):
        log_entry = {
            "level": record.levelname,
            "path": getattr(record, "pathname", ""),
            "message": record.getMessage()
        }
        self.logs.append(log_entry)

    def close(self):
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=4)
        super().close()

def clean_parsnips(path):
    for root, dirs, files in os.walk(path, topdown=True):
        for dir in dirs:
            if dir == '.parsnips':
                target = Path(root) / dir
                try:
                    shutil.rmtree(target)
                    print(f"Deleted {target}")
                except Exception as e:
                    print(f"Failed to delete {target}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Parsnips: AST-based SWHID extractor")
    parser.add_argument("path", type=str, nargs='?', default=".", help="File or directory to process")
    parser.add_argument("--quiet", action="store_true", help="Suppress all output")
    parser.add_argument("--log", type=str, help="Log file for structured logging")
    parser.add_argument("--clean", action="store_true", help="Clean all .parsnips folders")
    parser.add_argument("--strict", action="store_true", help="Fail immediately on any error or warning")
    args = parser.parse_args()

    path = Path(args.path)

    # Setup logging
    logger = logging.getLogger("parsnips")
    logger.setLevel(logging.INFO)
    handlers = []

    if not args.quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        handlers.append(console_handler)

    if args.log:
        json_handler = JsonLogHandler(args.log)
        logger.addHandler(json_handler)
        handlers.append(json_handler)

    if args.clean:
        clean_parsnips(path)
        sys.exit(0)

    extractor = ParsnipsExtractor(logger, strict=args.strict)

    try:
        extractor.process(path)
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)

    for h in handlers:
        if hasattr(h, "close"):
            h.close()

if __name__ == "__main__":
    main()
