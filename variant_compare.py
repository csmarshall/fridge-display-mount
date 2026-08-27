#!/usr/bin/env python3
"""Side-by-side of the two arm-reach variants, drawn on the fridge's top corner.

The two variants differ in ONE dimension: how far the arm reaches inboard across the top of the
fridge. Everything from the bend downward — neck, body, holes, vents, magnets — is identical.
This draws that one difference at scale instead of describing it.

Reference-only.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging, FRIDGE_SIDE, FRIDGE_SIDE_EDGE
from generate_bracket import MATERIAL, BracketParams, crown_rise_at, flat_gap

LOG = logging.getLogger("variants")

REACH_A, REACH_B = 130.0, 180.0


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _text(x: float, y: float, s: str, size: float = 10.0, anchor: str = "middle",
          fill: str = "#111", weight: str = "normal") -> str:
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">'
            f'{_esc(s)}</text>')


def render(path: Path, params: BracketParams) -> None:
    # The fridge's top corner is the origin: the top surface runs LEFT (inboard) and the side
    # panel drops DOWN, so the fridge solid occupies the lower-left quadrant.
    scale = 1.35
    margin_l, margin_t = 540.0, 175.0
    top_span, side_span = 295.0, 195.0
    width, height = 1180.0, 700.0

    def sx(v: float) -> float:
        """v = mm inboard across the fridge top; 0 is the top corner, positive is inboard."""
        return margin_l - v * scale

    def sy(v: float) -> float:
        """v = mm down the side panel from the top corner."""
        return margin_t + v * scale

    rf = params.fridge_corner_radius
    pad = params.arm_pad
    t = MATERIAL.thickness

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}">',
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="#fbfbf9"/>',
        f'<rect x="0" y="0" width="{width:.0f}" height="32" fill="#b00020"/>',
        _text(width / 2, 22, "REFERENCE ONLY — variant comparison", size=14, fill="#fff", weight="bold"),
        _text(40, 58, "The only difference between the two variants", size=17, anchor="start", weight="bold"),
        _text(40, 78, "Looking at the fridge's top corner from the side. Everything below the bend — "
                      "neck, body, VESA, vents, magnets, holes — is IDENTICAL.",
              size=11, anchor="start", fill="#555"),
        _text(40, 96, "Only the arm's reach inboard across the top changes: 130 mm (A) or 180 mm (B).",
              size=11, anchor="start", fill="#555"),
    ]

    # --- the fridge: top surface (with crown) and side panel -------------------------
    crown_pts = []
    for i in range(0, int(top_span) + 1, 4):
        rise = crown_rise_at(float(i), params.fridge_top_width, params.crown_rise)
        crown_pts.append((sx(float(i)), sy(0) - rise * scale))
    body = " ".join(f"{x:.2f},{y:.2f}" for x, y in crown_pts)
    out.append(f'<path d="M {sx(top_span):.2f} {sy(side_span):.2f} L {sx(top_span):.2f} '
               f'{crown_pts[-1][1]:.2f} L {body} L {sx(rf):.2f} {sy(0):.2f} '
               f'A {rf * scale:.2f} {rf * scale:.2f} 0 0 1 {sx(0):.2f} {sy(rf):.2f} '
               f'L {sx(0):.2f} {sy(side_span):.2f} Z" fill="{FRIDGE_SIDE}" stroke="{FRIDGE_SIDE_EDGE}" stroke-width="1.4"/>')
    out.append(_text(sx(top_span / 2), sy(side_span * 0.55), "REFRIGERATOR", size=12, fill="#6a737b"))
    out.append(_text(sx(top_span / 2), sy(side_span * 0.55) + 16,
                     f"top crowned {params.crown_rise:.0f} mm · corner R{rf:.0f} mm", size=9, fill="#8a9199"))
    out.append(_text(sx(top_span) - 8, sy(-14), "← inboard, across the fridge top", size=9.5,
                     anchor="start", fill="#8a9199"))

    # --- the bracket, common part ----------------------------------------------------
    def draw_arm(reach: float, colour: str, opacity: float, dash: str | None) -> str:
        d = (f'M {sx(reach):.2f} {sy(-pad - t):.2f} '
             f'L {sx(-params.magnet_standoff - t):.2f} {sy(-pad - t):.2f} '
             f'L {sx(-params.magnet_standoff - t):.2f} {sy(side_span):.2f} '
             f'L {sx(-params.magnet_standoff):.2f} {sy(side_span):.2f} '
             f'L {sx(-params.magnet_standoff):.2f} {sy(-pad):.2f} '
             f'L {sx(reach):.2f} {sy(-pad):.2f} Z')
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        return (f'<path d="{d}" fill="{colour}" fill-opacity="{opacity}" stroke="#5d3600" '
                f'stroke-width="1.3"{extra}/>')

    # B first (longer), then A on top, so the extra 50 mm reads as an addition
    out.append(draw_arm(REACH_B, "#e8a33d", 0.45, "7 4"))
    out.append(draw_arm(REACH_A, "#9a5b00", 0.75, None))

    # the sponge pad under the arm
    out.append(f'<rect x="{sx(REACH_B):.2f}" y="{sy(-pad):.2f}" '
               f'width="{(REACH_B + params.magnet_standoff) * scale:.2f}" height="{pad * scale:.2f}" '
               f'fill="#f2c14e" fill-opacity="0.55" stroke="#a8830f" stroke-width="0.8"/>')

    # --- the extra 50 mm, called out -------------------------------------------------
    out.append(f'<rect x="{sx(REACH_B):.2f}" y="{sy(-pad - t) - 4:.2f}" '
               f'width="{(REACH_B - REACH_A) * scale:.2f}" height="{(pad + t) * scale + 8:.2f}" '
               f'fill="#b00020" fill-opacity="0.16" stroke="#b00020" stroke-width="1" '
               f'stroke-dasharray="4 3"/>')
    mid = sx((REACH_A + REACH_B) / 2)
    out.append(f'<line x1="{mid:.2f}" y1="{sy(-pad - t) - 8:.2f}" x2="{mid:.2f}" '
               f'y2="{sy(-pad - t) - 30:.2f}" stroke="#b00020" stroke-width="1"/>')
    out.append(_text(mid, sy(-pad - t) - 36, "this 50 mm is the whole difference",
                     size=11.5, fill="#b00020", weight="bold", anchor="middle"))

    # --- dimensions ------------------------------------------------------------------
    dim_y = sy(side_span) + 40
    for reach, label, colour, off in ((REACH_A, "A — reach 130", "#5d3600", 0),
                                      (REACH_B, "B — reach 180", "#b00020", 28)):
        y = dim_y + off
        out.append(f'<line x1="{sx(0):.2f}" y1="{y:.2f}" x2="{sx(reach):.2f}" y2="{y:.2f}" '
                   f'stroke="{colour}" stroke-width="1.2"/>')
        for x in (sx(0), sx(reach)):
            out.append(f'<line x1="{x:.2f}" y1="{y - 5:.2f}" x2="{x:.2f}" y2="{y + 5:.2f}" '
                       f'stroke="{colour}" stroke-width="1.2"/>')
        out.append(_text(sx(reach / 2), y - 8, f"{label} mm", size=10, fill=colour, weight="bold"))

    # --- what it buys / costs --------------------------------------------------------
    cx = 640.0
    rows = []
    for reach, name in ((REACH_A, "A · reach 130"), (REACH_B, "B · reach 180")):
        crown = crown_rise_at(reach, params.fridge_top_width, params.crown_rise)
        budget = flat_gap(params.fridge_corner_radius_max, MATERIAL.bend_radius) + crown
        covered = 0.0
        for cand in range(3, 61):
            if pad >= (flat_gap(float(cand), MATERIAL.bend_radius) + crown) * 1.2:
                covered = float(cand)
            else:
                break
        rows.append((name, reach, crown, pad / budget, covered))
        LOG.info("%s: crown under arm %.2f mm, pad margin %.2fx, covers R_f up to %.0f mm",
                 name, crown, pad / budget, covered)

    out.append(_text(cx, 150, "What the extra 50 mm changes", size=13, anchor="start", weight="bold"))
    headers = ("", "footprint on top", "crown ridden", "pad margin", "covers R_f to", "flat length")
    colx = [cx, cx + 120, cx + 250, cx + 360, cx + 460, cx + 580]
    for c, h in zip(colx, headers):
        out.append(_text(c, 178, h, size=9.5, anchor="start", weight="bold", fill="#444"))
    out.append(f'<line x1="{cx:.0f}" y1="184" x2="{cx + 500:.0f}" y2="184" stroke="#ccc"/>')
    flats = {REACH_A: 730.9, REACH_B: 780.9}
    for i, (name, reach, crown, margin, covered) in enumerate(rows):
        y = 206 + i * 22
        colour = "#5d3600" if reach == REACH_A else "#b00020"
        vals = (name, f"{reach:.0f} mm", f"{crown:.2f} mm", f"{margin:.2f}x",
                f"{covered:.0f} mm", f"{flats[reach]:.1f} mm")
        for c, v in zip(colx, vals):
            out.append(_text(c, y, v, size=10, anchor="start", fill=colour))

    notes = [
        "B's longer arm sits further across the crowned top, so it rides more of the dome",
        "and its sponge pad has less spare compression — 1.43x versus 1.59x.",
        "",
        "B buys: 50 mm more bearing footprint, so the bracket is harder to rock fore-and-aft.",
        "B costs: 50 mm more sheet, 0.12 kg, and it stops working sooner if your fridge's",
        "corner radius measures large (17 mm vs 19 mm before the pad runs out).",
        "",
        "Neither changes a single hole, the bend position, the body, or how the display mounts.",
    ]
    for i, n in enumerate(notes):
        out.append(_text(cx, 285 + i * 17, n, size=10.5, anchor="start",
                         fill="#b00020" if n.startswith("B costs") else "#333"))

    out.append(_text(cx, 470, "How to choose", size=13, anchor="start", weight="bold"))
    rules = [
        ("measure R_f > 17 mm", "A — B's pad can't cover it"),
        ("R_f <= 17 and crown <= 3 mm", "B — the extra footprint is free"),
        ("crown > 5 mm", "A — shorter arm rides less dome"),
        ("still unsure", "A — more margin, less sheet"),
    ]
    for i, (cond, pick) in enumerate(rules):
        y = 498 + i * 22
        out.append(_text(cx, y, cond, size=10.5, anchor="start", fill="#555"))
        out.append(_text(cx + 260, y, "->", size=10.5, anchor="start", fill="#888"))
        out.append(_text(cx + 290, y, pick, size=10.5, anchor="start", fill="#111", weight="bold"))

    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Draw the difference between the two arm-reach variants.")
    p.add_argument("--out", type=Path, default=Path("variant_compare.svg"))
    p.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = p.parse_args(argv)
    configure_logging(args.log_level)
    render(args.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
