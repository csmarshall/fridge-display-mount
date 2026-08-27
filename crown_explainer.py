#!/usr/bin/env python3
"""Why the crown, the corner radius, the foam pad and the arm magnets are all one problem.

Three panels, side elevation, looking along the fridge's top front edge:
  1. what the foam has to absorb  2. why the pad cannot simply be thicker  3. the way out

Vertical scale is exaggerated — a 3 mm crown across a 130 mm arm is invisible at true scale.
Reference-only.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
from generate_bracket import MATERIAL, BracketParams, crown_rise_at, flat_gap

LOG = logging.getLogger("crown")

VEXAG = 14.0  # vertical exaggeration; horizontal is true scale


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _t(x, y, s, size=10.0, anchor="middle", fill="#111", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">'
            f'{_esc(s)}</text>')


def render(path: Path, p: BracketParams) -> None:
    W, H = 1280.0, 940.0
    hs = 1.25                      # horizontal scale, px per mm
    reach = p.arm_len
    pad = p.arm_pad
    gap_corner = flat_gap(p.fridge_corner_radius_max, MATERIAL.bend_radius)
    crown_at_tip = crown_rise_at(reach, p.fridge_top_width, p.crown_rise)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
           f'viewBox="0 0 {W:.0f} {H:.0f}">',
           f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfbf9"/>',
           f'<rect x="0" y="0" width="{W:.0f}" height="32" fill="#b00020"/>',
           _t(W/2, 22, "REFERENCE ONLY — why crown, corner radius, foam and arm magnets are one problem",
              14, fill="#fff", weight="bold"),
           _t(40, 60, "The foam has ONE budget, and two things spend it", 18, anchor="start", weight="bold"),
           _t(40, 82, f"Side elevation along the fridge's top edge. Horizontal is true scale; "
                      f"VERTICAL IS EXAGGERATED {VEXAG:.0f}x so gaps of a few mm are visible.",
              11, anchor="start", fill="#555")]

    # ---------------- panel 1 : what the foam absorbs ----------------------------
    ox, oy = 150.0, 300.0
    SLAB_PX = 58.0   # fridge drawn as a fixed-depth slab; exaggerating its thickness would
                     # make it read as a wall rather than a surface

    def x(mm): return ox + mm * hs
    def y(mm): return oy - mm * VEXAG      # mm above the corner datum

    out.append(_t(40, 150, "1 — What the foam has to absorb", 13, anchor="start", weight="bold"))
    out.append(_t(40, 168, "The arm is rigid. The fridge top is domed. The two cannot touch "
                           "everywhere, and the foam is what bridges the difference.",
                  10.5, anchor="start", fill="#555"))

    # fridge top surface, rising inboard along the crown parabola
    pts = [(x(i), y(crown_rise_at(float(i), p.fridge_top_width, p.crown_rise)))
           for i in range(0, int(reach) + 1, 2)]
    surf = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    out.append(f'<path d="M {pts[0][0]:.1f} {pts[0][1] + SLAB_PX:.1f} L {surf} '
               f'L {pts[-1][0]:.1f} {pts[-1][1] + SLAB_PX:.1f} Z" '
               f'fill="#dfe3e6" stroke="#8a9199" stroke-width="1.4"/>')
    out.append(_t(x(reach/2), y(0) + 34, "FRIDGE TOP — domed for rigidity", 9.5, fill="#6a737b"))
    out.append(_t(x(reach/2), y(0) + 48, f"(dome shown {VEXAG:.0f}x exaggerated)", 8.5, fill="#8a9199"))

    # rigid arm: straight, touching at the inboard tip, lifted at the bend end
    arm_tip_y = y(crown_at_tip)
    arm_root_y = y(crown_at_tip + gap_corner)
    out.append(f'<line x1="{x(0):.1f}" y1="{arm_root_y:.1f}" x2="{x(reach):.1f}" y2="{arm_tip_y:.1f}" '
               f'stroke="#5d3600" stroke-width="8" stroke-linecap="round"/>')
    out.append(_t(x(reach/2), arm_root_y - 30, f"RIGID {MATERIAL.name.upper()} ARM", 10.5, fill="#5d3600", weight="bold"))
    out.append(_t(x(reach/2), arm_root_y - 17, "it cannot bend to follow the dome", 9, fill="#5d3600"))

    # foam wedge
    wedge = pts + [(x(reach), arm_tip_y), (x(0), arm_root_y)]
    poly = " ".join(f"{a:.1f},{b:.1f}" for a, b in wedge)
    out.append(f'<polygon points="{poly}" fill="#f2c14e" fill-opacity="0.85" stroke="#a8830f" '
               f'stroke-width="1"/>')
    out.append(_t(x(reach*0.40), arm_root_y + 30, "FOAM fills this wedge", 10,
                  fill="#8a6a10", weight="bold"))

    # total gap dimension, left of the bend end
    out.append(f'<line x1="{x(-22):.1f}" y1="{y(0):.1f}" x2="{x(-22):.1f}" y2="{arm_root_y:.1f}" '
               f'stroke="#b00020" stroke-width="1.5"/>')
    for yy in (y(0), arm_root_y):
        out.append(f'<line x1="{x(-28):.1f}" y1="{yy:.1f}" x2="{x(-16):.1f}" y2="{yy:.1f}" '
                   f'stroke="#b00020" stroke-width="1.5"/>')
    out.append(_t(x(-34), (y(0)+arm_root_y)/2 - 4, "total gap", 10, anchor="end",
                  fill="#b00020", weight="bold"))
    out.append(_t(x(-34), (y(0)+arm_root_y)/2 + 10, f"{crown_at_tip + gap_corner:.2f} mm",
                  10, anchor="end", fill="#b00020"))

    # the two contributions, right of the tip
    rx = x(reach) + 26
    out.append(f'<line x1="{rx:.1f}" y1="{y(0):.1f}" x2="{rx:.1f}" y2="{y(crown_at_tip):.1f}" '
               f'stroke="#1a5fb4" stroke-width="1.5"/>')
    out.append(f'<line x1="{rx:.1f}" y1="{y(crown_at_tip):.1f}" x2="{rx:.1f}" '
               f'y2="{y(crown_at_tip+gap_corner):.1f}" stroke="#c0169a" stroke-width="1.5"/>')
    out.append(f'<line x1="{x(reach):.1f}" y1="{y(0):.1f}" x2="{rx+6:.1f}" y2="{y(0):.1f}" '
               f'stroke="#8a9199" stroke-width="0.7" stroke-dasharray="3 2"/>')
    out.append(_t(rx + 12, y(crown_at_tip/2) + 4, f"crown rise  {crown_at_tip:.2f} mm",
                  10, anchor="start", fill="#1a5fb4", weight="bold"))
    out.append(_t(rx + 12, y(crown_at_tip/2) + 18, "grows if the arm reaches further inboard",
                  9, anchor="start", fill="#1a5fb4"))
    out.append(_t(rx + 12, y(crown_at_tip + gap_corner/2) - 8,
                  f"corner-radius lift  {gap_corner:.2f} mm", 10, anchor="start",
                  fill="#c0169a", weight="bold"))
    out.append(_t(rx + 12, y(crown_at_tip + gap_corner/2) + 6,
                  "grows if the fridge corner radius is large", 9, anchor="start", fill="#c0169a"))

    out.append(_t(40, oy + SLAB_PX + 46,
                  f"They STACK: {crown_at_tip:.2f} + {gap_corner:.2f} = "
                  f"{crown_at_tip + gap_corner:.2f} mm, against a {pad:.2f} mm pad. "
                  f"That is the whole budget.", 11.5, anchor="start", fill="#111", weight="bold"))
    out.append(_t(40, 470, f"Crown is currently modelled as {p.crown_rise:.2f} mm — "
                  f"ASSUMED, not measured on the Samsung. Measure before trusting this sum.",
                  10.5, anchor="start", fill="#b00020", weight="bold"))

    # ---------------- panel 2 : why the pad can't just be thicker -----------------
    py0 = 500.0
    out.append(_t(40, py0 - 26, "2 — So why not just use thicker foam? Because the arm magnet has to touch steel",
                  13, anchor="start", weight="bold"))
    mag = p.arm_magnet_standoff        # the magnet's OWN height, not the pad's
    cases = [
        ("pad = magnet height", "#2e9e5b", mag, mag, "CORRECT — foam bears the load,\nmagnet reaches the steel"),
        ("pad THICKER than magnet", "#b00020", mag + 3.5, mag, "magnet is held off the steel.\nIt grips nothing."),
        ("pad THINNER than magnet", "#b00020", mag - 3.0, mag, "magnet holds the arm up.\nFoam does nothing, and the\nrigid magnet line-loads the sheet."),
    ]
    cw = 390.0
    for i, (title, colour, padh, magh, note) in enumerate(cases):
        bx = 90.0 + i * cw
        base = py0 + 120
        s2 = 9.0
        out.append(_t(bx + 130, py0, title, 11.5, anchor="middle", fill=colour, weight="bold"))
        # steel
        out.append(f'<rect x="{bx:.1f}" y="{base:.1f}" width="260" height="16" fill="#dfe3e6" '
                   f'stroke="#8a9199" stroke-width="1.2"/>')
        out.append(_t(bx + 130, base + 30, "fridge steel", 9, fill="#6a737b"))
        stand = max(padh, magh)
        army = base - stand * s2 - 10
        # foam block
        out.append(f'<rect x="{bx + 20:.1f}" y="{base - padh*s2:.1f}" width="120" '
                   f'height="{padh*s2:.1f}" fill="#f2c14e" fill-opacity="0.85" stroke="#a8830f"/>')
        out.append(_t(bx + 80, base - padh*s2/2 + 4, f"foam {padh:.2f}", 9, fill="#6b5008", weight="bold"))
        # magnet block
        out.append(f'<rect x="{bx + 165:.1f}" y="{base - magh*s2:.1f}" width="70" '
                   f'height="{magh*s2:.1f}" fill="#c0169a" fill-opacity="0.35" stroke="#c0169a"/>')
        out.append(_t(bx + 200, base - magh*s2/2 + 4, f"magnet {magh:.0f}", 9, fill="#8c1070", weight="bold"))
        # arm plate across the top
        out.append(f'<rect x="{bx + 10:.1f}" y="{army:.1f}" width="240" height="10" fill="#5d3600"/>')
        out.append(_t(bx + 130, army - 6, "arm", 8.5, fill="#5d3600"))
        # gaps
        if padh > magh:
            out.append(f'<rect x="{bx + 165:.1f}" y="{base - padh*s2:.1f}" width="70" '
                       f'height="{(padh-magh)*s2:.1f}" fill="none" stroke="#b00020" '
                       f'stroke-width="1.4" stroke-dasharray="3 2"/>')
        if magh > padh:
            out.append(f'<rect x="{bx + 20:.1f}" y="{base - magh*s2:.1f}" width="120" '
                       f'height="{(magh-padh)*s2:.1f}" fill="none" stroke="#b00020" '
                       f'stroke-width="1.4" stroke-dasharray="3 2"/>')
        for j, line in enumerate(note.split("\n")):
            out.append(_t(bx + 130, base + 50 + j*13, line, 9.5, fill=colour))

    # ---------------- panel 3 : the way out ---------------------------------------
    py1 = 790.0
    out.append(_t(40, py1, "3 — The way out, if your crown measures ugly", 13, anchor="start", weight="bold"))
    lines = [
        ("Keep the arm magnets", "#5d3600",
         f"pad locked to the stock size that matches the {p.arm_magnet_standoff:.2f} mm "
         f"magnet, currently {pad:.2f} mm  ->  the arm magnets must reach steel"),
        ("Drop the arm magnets", "#2e9e5b",
         "pad thickness becomes free  ->  3/8 in foam tolerates 11.0 mm of crown at 130 mm reach, "
         "8.5 mm at 180 mm"),
    ]
    for i, (label, colour, txt) in enumerate(lines):
        yy = py1 + 30 + i * 42
        out.append(f'<rect x="60" y="{yy-14:.0f}" width="12" height="12" fill="{colour}"/>')
        out.append(_t(82, yy - 3, label, 11.5, anchor="start", fill=colour, weight="bold"))
        out.append(_t(82, yy + 14, txt, 10, anchor="start", fill="#333"))
    out.append(_t(60, py1 + 122,
                  "The arm magnets are anti-jostle only — zero credit in the load path. They are "
                  "costing you crown tolerance, not strength.",
                  10.5, anchor="start", fill="#555"))
    out.append(_t(60, py1 + 139,
                  "Measure the crown first. Under ~4 mm and none of this matters: keep the magnets.",
                  10.5, anchor="start", fill="#111", weight="bold"))
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    LOG.info("Wrote %s (crown at tip %.2f mm, corner lift %.2f mm, total %.2f vs pad %.2f)",
             path, crown_at_tip, gap_corner, crown_at_tip + gap_corner, pad)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Draw the crown / foam / arm-magnet interaction.")
    ap.add_argument("--out", type=Path, default=Path("crown_explainer.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
