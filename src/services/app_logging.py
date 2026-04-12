from __future__ import annotations

import logging
from pathlib import Path


def configure_app_logging(root_dir: Path) -> Path:
    root_dir.mkdir(parents=True, exist_ok=True)
    log_file = root_dir / "glance.log"
    logger = logging.getLogger("glance")
    if not any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename) == log_file
        for handler in logger.handlers
    ):
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S%z",
            )
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return log_file
