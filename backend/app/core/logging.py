from __future__ import annotations

import logging
import sys


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging() -> None:
    """Ensure the application uses a consistent log format and quiet Azure SDK noise."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stderr, force=True)
    logging.getLogger("azure").setLevel(logging.WARNING)
