#!/usr/bin/env python3
"""Thickness study for the fridge-side display mount.

Strength is NOT the deciding factor — the plate is enormously overbuilt at every thickness
SendCutSend offers. Stiffness is. What a user actually perceives is how far the screen edge moves
when they press it, and that scales as 1/t^3, so it changes dramatically across the range while the
safety factors stay comfortable throughout.

Renders a table and an annotated chart. Reference-only.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
from generate_bracket import DISPLAY, MATERIAL, MM_PER_INCH, BracketParams

LOG = logging.getLogger("thickness")

E_5052_MPA = 70_300.0  # Young's modulus, N/mm^2
N_PER_LBF = 4.4482216

# Live SendCutSend quotes, same part, qty 1, cutting only. Pulled 2026-08-25.
QUOTED_PRICE_USD = {0.100: 59.38, 0.125: 61.54, 0.187: 131.49, 0.250: 127.79}

# Powder coat adds this per side, so it lands on the magnet pads. Masking is NOT offered.
POWDER_PER_SIDE_IN = (0.002, 0.005)


@dataclass(frozen=True)
class Result:
    thickness_in: float
    thickness_mm: float
    neck_psi: float
    neck_sf: float
    body_psi: float
    body_sf: float
    magnet_deflection_mm: float
    screen_edge_movement_mm: float
    mass_kg: float
    countersink_depth_mm: float
    countersink_limit_mm: float
    price_usd: float | None

    @property
    def countersink_ok(self) -> bool:
        return self.countersink_depth_mm <= self.countersink_limit_mm


def evaluate(thickness_in: float, params: BracketParams) -> Result:
    t = thickness_in * MM_PER_INCH

    # Torsion from a touch press at the outer screen edge, reacted by the magnet pairs.
    torsion_in_lbf = params.press_force_lbf * (params.torsion_arm / MM_PER_INCH)
    force_per_magnet_lbf = torsion_in_lbf / (params.magnet_spacing_x / MM_PER_INCH) / 2.0

    # Plate area scales nothing but mass; openings deducted the same way the generator does.
    area_mm2 = (
        params.body_w * params.body_h
        + params.neck_w * (params.neck_len + params.arm_len)
        - math.pi * (params.center_open_dia / 2.0) ** 2
        - 4.0 * params.window_long * params.window_short
    )
    mass_kg = area_mm2 * t * MATERIAL.density_g_cc / 1e6

    # Neck bending at the bend root, from the overturning moment of the hung display.
    weight_lbf = DISPLAY.weight_lbf
    bracket_lbf = mass_kg * 2.2046226218
    cg = params.magnet_standoff + t + params.spacer_len + DISPLAY.centroid_from_box_face()
    bracket_cg = params.magnet_standoff + t / 2.0
    overturning_in_lbf = (weight_lbf * cg + bracket_lbf * bracket_cg) / MM_PER_INCH
    neck_z_in3 = (params.neck_w / MM_PER_INCH) * (t / MM_PER_INCH) ** 2 / 6.0
    neck_psi = overturning_in_lbf / neck_z_in3

    # Body plate in its weak axis, VESA screw out to magnet. Effective strip = one magnet disc.
    lever_in = (params.magnet_spacing_x / 2.0 - params.vesa / 2.0) / MM_PER_INCH
    body_z_in3 = (params.magnet_disc_dia / MM_PER_INCH) * (t / MM_PER_INCH) ** 2 / 6.0
    body_psi = force_per_magnet_lbf * lever_in / body_z_in3

    # Out-of-plane deflection at the magnet, cantilever from the VESA screw. Conservative: the real
    # plate is supported at four magnets and loaded at four VESA points, so it is stiffer than this.
    force_n = force_per_magnet_lbf * N_PER_LBF
    lever_mm = params.magnet_spacing_x / 2.0 - params.vesa / 2.0
    second_moment = params.magnet_disc_dia * t ** 3 / 12.0
    deflection_mm = force_n * lever_mm ** 3 / (3.0 * E_5052_MPA * second_moment)
    # Geometric amplification out to where the finger actually is.
    screen_edge_mm = deflection_mm * (params.torsion_arm / (params.magnet_spacing_x / 2.0))

    csk_major_mm = 0.315 * MM_PER_INCH  # their M4 90 deg countersink
    csk_depth = (csk_major_mm - params.vesa_hole_dia) / 2.0  # 90 deg => half-angle 45 => depth = dr

    return Result(
        thickness_in=thickness_in,
        thickness_mm=t,
        neck_psi=neck_psi,
        neck_sf=MATERIAL.yield_psi / neck_psi,
        body_psi=body_psi,
        body_sf=MATERIAL.yield_psi / body_psi,
        magnet_deflection_mm=deflection_mm,
        screen_edge_movement_mm=screen_edge_mm,
        mass_kg=mass_kg,
        countersink_depth_mm=csk_depth,
        countersink_limit_mm=0.6 * t,
        price_usd=QUOTED_PRICE_USD.get(round(thickness_in, 3)),
    )


def _esc(s: str) -> str:
    """XML-escape label text. A bare '<' in a label makes the whole SVG unparseable."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _text(x: float, y: float, s: str, size: float = 10.0, anchor: str = "middle",
          fill: str = "#111", weight: str = "normal") -> str:
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">'
            f'{_esc(s)}</text>')


def render(path: Path, results: Sequence[Result], chosen_in: float) -> None:
    margin_l, margin_t = 96.0, 132.0
    plot_w, plot_h = 620.0, 300.0
    width, height = margin_l + plot_w + 300.0, margin_t + plot_h + 300.0

    xs = [r.thickness_in for r in results]
    x_min, x_max = min(xs), max(xs)
    y_max = max(r.screen_edge_movement_mm for r in results)

    def px(v: float) -> float:
        return margin_l + (v - x_min) / (x_max - x_min) * plot_w

    def py(v: float) -> float:
        return margin_t + plot_h - (v / y_max) * plot_h

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}">',
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="#fbfbf9"/>',
        f'<rect x="0" y="0" width="{width:.0f}" height="32" fill="#b00020"/>',
        _text(width / 2, 22, "REFERENCE ONLY — thickness study, not a fabrication drawing",
              size=14, fill="#fff", weight="bold"),
        _text(40, 58, "How much the screen edge moves when you press it", size=16,
              anchor="start", weight="bold"),
        _text(40, 78, "5052-H32. Strength is never the limit — safety factors stay above 15x across "
                      "the whole range. Stiffness is what you feel, and it scales as 1/t³.",
              size=10.5, anchor="start", fill="#555"),
        _text(40, 95, f"Load case: {BracketParams().press_force_lbf:.0f} lb pressed at the outer "
                      f"screen edge, {BracketParams().torsion_arm:.0f} mm off centre. Cantilever "
                      f"model from the VESA screw to the magnet — conservative; the real plate is "
                      f"stiffer.",
              size=10.5, anchor="start", fill="#555"),
    ]

    # a "feels solid" band: below ~0.2 mm of screen-edge movement reads as rigid
    solid_mm = 0.20
    out.append(f'<rect x="{margin_l:.2f}" y="{py(solid_mm):.2f}" width="{plot_w:.2f}" '
               f'height="{margin_t + plot_h - py(solid_mm):.2f}" fill="#2e9e5b" fill-opacity="0.10"/>')
    out.append(_text(margin_l + plot_w - 6, py(solid_mm) + 16, "feels rigid  (< 0.2 mm)", size=9,
                     anchor="end", fill="#2e9e5b", weight="bold"))

    out.append(f'<line x1="{margin_l:.2f}" y1="{margin_t + plot_h:.2f}" x2="{margin_l + plot_w:.2f}" '
               f'y2="{margin_t + plot_h:.2f}" stroke="#333" stroke-width="1.2"/>')
    out.append(f'<line x1="{margin_l:.2f}" y1="{margin_t:.2f}" x2="{margin_l:.2f}" '
               f'y2="{margin_t + plot_h:.2f}" stroke="#333" stroke-width="1.2"/>')
    out.append(_text(margin_l - 60, margin_t + plot_h / 2, "screen edge", size=9.5, fill="#555"))
    out.append(_text(margin_l - 60, margin_t + plot_h / 2 + 12, "movement (mm)", size=9.5, fill="#555"))

    pts = " ".join(f"{px(r.thickness_in):.2f},{py(r.screen_edge_movement_mm):.2f}" for r in results)
    out.append(f'<polyline points="{pts}" fill="none" stroke="#1a5fb4" stroke-width="2.4"/>')

    for r in results:
        x, y = px(r.thickness_in), py(r.screen_edge_movement_mm)
        chosen = abs(r.thickness_in - chosen_in) < 1e-9
        out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{6 if chosen else 4}" '
                   f'fill="{"#b00020" if chosen else "#1a5fb4"}" stroke="#fff" stroke-width="1.5"/>')
        out.append(_text(x, y - 14, f"{r.screen_edge_movement_mm:.2f}", size=9,
                         fill="#b00020" if chosen else "#1a5fb4", weight="bold"))
        label = f'{r.thickness_in:.3f}"'
        out.append(_text(x, margin_t + plot_h + 18, label, size=9.5,
                         weight="bold" if chosen else "normal"))
        if r.price_usd:
            out.append(_text(x, margin_t + plot_h + 33, f"${r.price_usd:.0f}", size=9, fill="#2e9e5b"))
        if chosen:
            out.append(f'<line x1="{x:.2f}" y1="{y + 10:.2f}" x2="{x:.2f}" '
                       f'y2="{margin_t + plot_h:.2f}" stroke="#b00020" stroke-width="1" '
                       f'stroke-dasharray="3 3"/>')

    out.append(_text(margin_l + plot_w / 2, margin_t + plot_h + 56,
                     "plate thickness (inches), with the quoted cut price where known",
                     size=10, fill="#555"))

    # table
    ty = margin_t + plot_h + 96
    headers = ["thickness", "mass", "screen move", "neck SF", "weak-axis SF", "M4 c'sink", "cut price"]
    cols = [margin_l, margin_l + 110, margin_l + 190, margin_l + 310, margin_l + 400, margin_l + 520, margin_l + 620]
    for c, h in zip(cols, headers):
        out.append(_text(c, ty, h, size=9.5, anchor="start", weight="bold", fill="#444"))
    out.append(f'<line x1="{margin_l:.0f}" y1="{ty + 6:.0f}" x2="{margin_l + 700:.0f}" '
               f'y2="{ty + 6:.0f}" stroke="#ccc"/>')
    for i, r in enumerate(results):
        row = ty + 22 + i * 16
        chosen = abs(r.thickness_in - chosen_in) < 1e-9
        colour = "#b00020" if chosen else "#333"
        weight = "bold" if chosen else "normal"
        vals = [
            f'{r.thickness_in:.3f}" ({r.thickness_mm:.2f} mm)',
            f"{r.mass_kg:.2f} kg",
            f"{r.screen_edge_movement_mm:.2f} mm",
            f"{r.neck_sf:.0f}x",
            f"{r.body_sf:.0f}x",
            "fits" if r.countersink_ok else "TOO DEEP",
            f"${r.price_usd:.2f}" if r.price_usd else "—",
        ]
        for c, v in zip(cols, vals):
            fill = "#b00020" if (v == "TOO DEEP") else colour
            out.append(_text(c, row, v, size=9.5, anchor="start", fill=fill, weight=weight))

    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Strength and stiffness vs plate thickness.")
    p.add_argument("--thicknesses", type=float, nargs="+",
                   default=[0.080, 0.100, 0.125, 0.187, 0.250])
    p.add_argument("--chosen", type=float, default=0.187)
    p.add_argument("--out", type=Path, default=Path("thickness_study.svg"))
    p.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = p.parse_args(argv)
    configure_logging(args.log_level)

    params = BracketParams()
    results = [evaluate(t, params) for t in args.thicknesses]
    LOG.info("%-22s %8s %13s %9s %13s %11s", "thickness", "mass", "screen move", "neck SF",
             "weak-axis SF", "M4 c'sink")
    for r in results:
        LOG.info('%-22s %7.2fkg %10.2f mm %8.0fx %12.0fx %11s',
                 f'{r.thickness_in:.3f}" ({r.thickness_mm:.2f} mm)', r.mass_kg,
                 r.screen_edge_movement_mm, r.neck_sf, r.body_sf,
                 "fits" if r.countersink_ok else "TOO DEEP")
    render(args.out, results, args.chosen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
