import logging
import sys
from pathlib import Path

from parsnips.models.config.parsnips_config import ParsnipsConfig


class LoggerFactory:
    
    @staticmethod
    def setup_logger(parsnips_config: ParsnipsConfig) -> logging.Logger:
        logger = logging.getLogger("parsnips")
        if parsnips_config.log.log_level:
            logger.setLevel(parsnips_config.log.log_level.to_logging_level())
        else:
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
