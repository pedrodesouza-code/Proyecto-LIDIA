from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def evento(logger: logging.Logger, **values) -> None:
    values.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    logger.info(json.dumps(values, default=str, sort_keys=True))
