"""Central logging setup for Agent Zero CLI."""

import logging
import os
from pathlib import Path

LOG_FILE = Path("logs") / "agentzero.log"


def setup_logging(force: bool = False) -> None:
    """Configure logging handlers (console + optional debug file)."""

    root = logging.getLogger()
    if root.handlers and not force:
        return

    is_debug = os.environ.get("AGENTZERO_DEBUG", "0").lower() in ("1", "true", "yes")
    level = logging.DEBUG if is_debug else logging.INFO
    root.setLevel(level)

    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    if level == logging.DEBUG:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
