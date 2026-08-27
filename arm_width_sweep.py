#!/usr/bin/env python3
"""Arm/neck width study for the fridge-side display mount.

Arm width runs FRONT-TO-BACK along the fridge top, the same direction as the body width. That
makes it the lever that resists twisting about the vertical spine axis at the hook: a touch press
near the outer screen edge tries to lift one end of the arm off the fridge top and press the other
in. The couple force at the bend line is M_torsion / arm_width, so width buys margin directly.

This matters most in the fallback case the brief demands the design survive: a NON-MAGNETIC
(304 stainless) side panel, where the body magnets contribute nothing and the arm is the only
restraint. Renders a plan view of the fridge top per candidate width.

Reference-only.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
from generate_bracket import (
    DISPLAY,
    LBF_PER_KG,
    MATERIAL,
    MM_PER_INCH,
    BracketParams,
    derive_flat,
)

LOG = logging.getLogger("armwidth")

# The fridge lives in BracketParams — one home. This sheet used to carry its own 33.5 in depth
# copied from a different fridge's spec page, which is 241 mm deeper than the actual counter-depth Samsung and
# made the arm look far better supported than it is.
_FP = BracketParams()
FRIDGE_DEPTH_MM = _FP.fridge_depth                    # 609.6 mm, Samsung RS23A500ASR cabinet
# The hinge cover was MEASURED from the photo on 2026-08-27, so it is no longer an estimate.
# The rear step-down still is — it remains a pre-order checklist item.
HINGE_CAP_ZONE_MM = FRIDGE_DEPTH_MM - _FP.hinge_cover_from_rear
REAR_STEPDOWN_ZONE_MM = 110.0


def bracket_mass_kg(params: BracketParams, neck_w: float) -> float:
    """Plate mass at a given neck/arm width, openings deducted, derived from the flat pattern."""
    trial = BracketParams(**{**params.__dict__, "neck_w": neck_w})
    flat = derive_flat(trial)
    import math

    area = (
        trial.body_w * trial.body_h
        + neck_w * (flat.neck_flat + flat.arm_flat)
        - math.pi * (trial.center_open_dia / 2.0) ** 2
        - 4.0 * trial.window_long * trial.window_short
    )
    return area * MATERIAL.thickness * MATERIAL.density_g_cc / 1e6


def _text(x: float, y: float, s: str, size: float = 10.0, anchor: str = "middle",
          fill: str = "#111", weight: str = "normal") -> str:
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">{s}</text>')


def render(path: Path, widths: Sequence[float], params: BracketParams, arm_magnet_pull_lbf: float) -> None:
    scale = 0.42
    panel_w = 300.0
    margin_l, margin_t = 70.0, 146.0
    canvas_w = margin_l + panel_w * len(widths) + 30.0
    canvas_h = margin_t + FRIDGE_DEPTH_MM * scale + 176.0

    torsion_in_lbf = params.press_force_lbf * (params.torsion_arm / MM_PER_INCH)
    clear_window = FRIDGE_DEPTH_MM - HINGE_CAP_ZONE_MM - REAR_STEPDOWN_ZONE_MM

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w:.0f}" height="{canvas_h:.0f}" '
        f'viewBox="0 0 {canvas_w:.0f} {canvas_h:.0f}">',
        f'<rect width="{canvas_w:.0f}" height="{canvas_h:.0f}" fill="#fbfbf9"/>',
        f'<rect x="0" y="0" width="{canvas_w:.0f}" height="30" fill="#b00020"/>',
        _text(canvas_w / 2, 21, "REFERENCE ONLY — arm width study, not a fabrication drawing",
              size=13, fill="#fff", weight="bold"),
        _text(40, 54, "Arm / neck width — plan view, looking DOWN on the fridge top", size=15,
              anchor="start", weight="bold"),
        _text(40, 72,
              f"Touch press {params.press_force_lbf:.0f} lbf at {params.torsion_arm:.0f} mm = "
              f"{torsion_in_lbf:.1f} in·lbf about the vertical spine. At the hook that is a couple "
              f"across the arm width: one end lifts, the other presses in.",
              size=10, anchor="start", fill="#555"),
        _text(40, 88,
              f"Lift demand = {torsion_in_lbf:.1f} in·lbf / arm width. Hold-down = half the assembly "
              f"weight + one arm retention magnet. Governing case is a NON-MAGNETIC panel, where the "
              f"body magnets contribute nothing.",
              size=10, anchor="start", fill="#555"),
    ]

    for index, width in enumerate(widths):
        px = margin_l + index * panel_w
        mass = bracket_mass_kg(params, width)
        total_lbf = DISPLAY.weight_lbf + mass * LBF_PER_KG
        lift_demand = torsion_in_lbf / (width / MM_PER_INCH)
        holddown = total_lbf / 2.0 + arm_magnet_pull_lbf
        margin = holddown / lift_demand
        fits = width <= clear_window

        depth_px = FRIDGE_DEPTH_MM * scale
        out.append(f'<rect x="{px:.2f}" y="{margin_t:.2f}" width="{panel_w - 40:.2f}" '
                   f'height="{depth_px:.2f}" fill="#dfe3e6" stroke="#8a9199" stroke-width="1"/>')
        for zone, label, y0 in ((HINGE_CAP_ZONE_MM, "hinge caps", 0.0),
                                (REAR_STEPDOWN_ZONE_MM, "cable / waterline step-down",
                                 FRIDGE_DEPTH_MM - REAR_STEPDOWN_ZONE_MM)):
            out.append(f'<rect x="{px:.2f}" y="{margin_t + y0 * scale:.2f}" width="{panel_w - 40:.2f}" '
                       f'height="{zone * scale:.2f}" fill="#b00020" fill-opacity="0.10" '
                       f'stroke="#b00020" stroke-width="0.6" stroke-dasharray="4 3"/>')
            if index == 0:
                out.append(_text(px + 6, margin_t + (y0 + zone / 2) * scale, label, size=8,
                                 anchor="start", fill="#b00020"))

        # The arm: reaches params.arm_len inboard from the side edge (left of each panel).
        arm_y0 = margin_t + (FRIDGE_DEPTH_MM - width) / 2.0 * scale
        out.append(f'<rect x="{px:.2f}" y="{arm_y0:.2f}" width="{params.arm_len * scale:.2f}" '
                   f'height="{width * scale:.2f}" fill="#9a5b00" fill-opacity="0.55" '
                   f'stroke="#5d3600" stroke-width="1"/>')
        out.append(f'<line x1="{px:.2f}" y1="{arm_y0:.2f}" x2="{px:.2f}" '
                   f'y2="{arm_y0 + width * scale:.2f}" stroke="#b00020" stroke-width="3"/>')
        if index == 0:
            out.append(_text(px + params.arm_len * scale + 8, margin_t + depth_px / 2 + 3,
                             "red = bend line on the top edge", size=8, anchor="start", fill="#b00020"))

        out.append(_text(px + (panel_w - 40) / 2, margin_t - 34, f"arm width {width:.0f} mm",
                         size=13, weight="bold"))
        colour = "#2e9e5b" if margin >= 1.5 and fits else ("#b00020" if margin < 1.0 or not fits else "#b8860b")
        out.append(_text(px + (panel_w - 40) / 2, margin_t - 18,
                         f"margin {margin:.2f}x" + ("" if fits else "  — TOO DEEP"),
                         size=11, weight="bold", fill=colour))

        lines = [
            f"lift demand   {lift_demand:5.2f} lbf",
            f"hold-down     {holddown:5.2f} lbf",
            f"bracket mass  {mass:5.2f} kg",
            f"bend length   {width / MM_PER_INCH:5.2f} in",
            (f"fits the {clear_window:.0f} mm clear window" if fits
             else f"exceeds the {clear_window:.0f} mm clear window"),
        ]
        for i, line in enumerate(lines):
            out.append(_text(px + (panel_w - 40) / 2, margin_t + depth_px + 24 + i * 14, line,
                             size=9.5, fill="#b00020" if "exceeds" in line else "#444"))
        LOG.info("width %5.0f mm: lift %.2f lbf vs hold-down %.2f lbf (margin %.2fx), mass %.2f kg, fits=%s",
                 width, lift_demand, holddown, margin, mass, fits)

    footer_y = canvas_h - 58
    out.append(_text(40, footer_y,
                     f"Clear window between keep-outs is {clear_window:.0f} mm on a "
                     f"{FRIDGE_DEPTH_MM:.0f} mm deep counter-depth top — the hinge cover is MEASURED; the rear step-down is still an ESTIMATE and is on the "
                     f"pre-order measurement checklist.", size=9.5, anchor="start", fill="#333"))
    out.append(_text(40, footer_y + 15,
                     "With working magnets on the body this case never arises — they carry the torsion. "
                     "This is the fallback: 304 stainless panel, or a magnet that lets go.",
                     size=9.5, anchor="start", fill="#333"))
    out.append(_text(40, footer_y + 30,
                     f"Arm magnet hold-down assumed {arm_magnet_pull_lbf:.1f} lbf (one magnet, already "
                     f"derated {params.magnet_derate * 100:.0f}% for thin painted sheet). Arm width does not "
                     f"widen the sheet: the body is already {params.body_w:.0f} mm.",
                     size=9.5, anchor="start", fill="#777"))
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    LOG.info("Wrote %s (%d widths)", path, len(widths))


def main(argv: Sequence[str] | None = None) -> int:
    defaults = BracketParams()
    p = argparse.ArgumentParser(description="Render an arm/neck width study in plan view.")
    p.add_argument("--widths", type=float, nargs="+", default=[130.0, 190.0, 250.0, 300.0])
    p.add_argument("--arm-magnet-rated-pull", type=float, default=13.2,
                   help="rated pull of ONE arm magnet in lbf, before derating (O36 rubber pot ~6 kg)")
    p.add_argument("--out", type=Path, default=Path("arm_width_sweep.svg"))
    p.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = p.parse_args(argv)
    configure_logging(args.log_level)

    derated = args.arm_magnet_rated_pull * defaults.magnet_derate
    LOG.info("Arm magnet: %.1f lbf rated -> %.2f lbf derated hold-down per magnet",
             args.arm_magnet_rated_pull, derated)
    render(args.out, args.widths, defaults, derated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
