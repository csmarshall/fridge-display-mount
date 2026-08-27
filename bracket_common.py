"""Shared logging configuration and file-format constants for the bracket toolchain.

Kept in one place so generate_bracket.py and audit_dxf.py emit identical log lines and
agree on what a compliant DXF looks like.
"""

from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
LOG_DATEFMT = "%Y-%m-%dT%H:%M:%S%z"
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

# SendCutSend 2D upload requirements: everything on layer 0, drawing units millimetres.
REQUIRED_LAYER = "0"
INSUNITS_MILLIMETERS = 4


def configure_logging(level_name: str) -> None:
    """Install the shared handler on the root logger. Idempotent within a process."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFMT))
    root.addHandler(handler)
    root.setLevel(getattr(logging, level_name.upper()))
    # ezdxf narrates every dictionary it creates at INFO; that is not our operational log.
    logging.getLogger("ezdxf").setLevel(logging.WARNING)
