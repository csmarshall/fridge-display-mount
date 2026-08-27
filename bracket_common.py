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


MM_PER_IN = 25.4
N_PER_LBF = 4.4482216
KG_PER_LB = 0.45359237


def mm_in(mm: float, dp: int = 0) -> str:
    """'310 mm (12.2 in)'. Every length a human reads should carry both systems."""
    return f"{mm:.{dp}f} mm ({mm / MM_PER_IN:.2f} in)"


def in_mm(inches: float, dp: int = 3) -> str:
    """'0.119 in (3.02 mm)' — for values whose NATIVE unit is imperial, like sheet gauge."""
    return f"{inches:.{dp}f} in ({inches * MM_PER_IN:.2f} mm)"


def lbf_n(lbf: float, dp: int = 1) -> str:
    """'16.9 lbf (75 N)'. Force, not torque — lb-ft would be a moment."""
    return f"{lbf:.{dp}f} lbf ({lbf * N_PER_LBF:.0f} N)"


def kg_lb(kg: float, dp: int = 2) -> str:
    """'3.71 kg (8.2 lb)' — mass, so pounds-mass rather than pounds-force."""
    return f"{kg:.{dp}f} kg ({kg / KG_PER_LB:.1f} lb)"


def area_cm2_in2(cm2: float) -> str:
    return f"{cm2:.0f} cm² ({cm2 / 6.4516:.0f} in²)"
