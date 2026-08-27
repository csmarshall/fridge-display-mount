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


# --- Fridge palette --------------------------------------------------------------------------
# ONE home for what the appliance looks like. "#dfe3e6" was hardcoded in ten separate modules,
# so recolouring the fridge was a ten-file edit and drift was guaranteed.
#
# Taken from a photograph of the actual unit (2026-08-27), NOT from a spec sheet. The Samsung
# RS23A500ASR's "ASR" suffix is Fingerprint Resistant Stainless Steel, which describes the DOORS
# only. The SIDE PANEL — the face this whole bracket hangs on — is a dark, matte, near-black
# charcoal. Earlier revisions of these drawings showed it as pale grey, which was wrong.
#
# TUNE HERE. These are eyeballed from a photo under kitchen lighting, not measured colour values.
# If a drawing looks wrong against the real appliance, change these and every sheet follows.
FRIDGE_SIDE = "#3a3734"          # dark matte charcoal side panel — the mounting face
FRIDGE_SIDE_EDGE = "#1f1d1b"     # its outline
FRIDGE_TOP = "#43403c"           # the top, catching more light than the vertical side
FRIDGE_HINGE_COVER = "#1c1c1c"   # the black plastic hinge cover
FRIDGE_DOOR = "#b3b7b9"          # stainless door face, flat fallback
FRIDGE_DOOR_EDGE = "#717577"     # its outline
FRIDGE_DOOR_HI = "#c9cdcf"       # brushed highlight
FRIDGE_DOOR_LO = "#989ca0"       # brushed shadow

# Annotation ink for anything drawn ON TOP of the fridge. The sheets were built when the fridge
# was pale, so they annotate it in near-black; on a charcoal panel that is invisible. Any label
# that lands on the appliance must use these instead.
ON_FRIDGE_INK = "#eef1f2"
ON_FRIDGE_MUTED = "#b0b6b9"

_STAINLESS_ID = "brushedSteel"


def stainless_defs(vertical: bool = False) -> str:
    """A <defs> block for a brushed-stainless fill, referenced via STAINLESS_FILL.

    Stainless reads as metal because of the banding across the brush direction, not because of
    its average colour — a flat grey rectangle just looks like grey plastic.
    """
    x2, y2 = ("0%", "100%") if vertical else ("100%", "0%")
    return (f'<defs><linearGradient id="{_STAINLESS_ID}" x1="0%" y1="0%" x2="{x2}" y2="{y2}">'
            f'<stop offset="0%" stop-color="{FRIDGE_DOOR_HI}"/>'
            f'<stop offset="38%" stop-color="{FRIDGE_DOOR}"/>'
            f'<stop offset="52%" stop-color="{FRIDGE_DOOR_HI}"/>'
            f'<stop offset="100%" stop-color="{FRIDGE_DOOR_LO}"/>'
            f'</linearGradient></defs>')


STAINLESS_FILL = f"url(#{_STAINLESS_ID})"
