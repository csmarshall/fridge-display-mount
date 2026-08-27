#!/usr/bin/env python3
"""Why the corner radius, the foam pad and the arm magnets are all one problem.

Three panels, side elevation, looking along the fridge's top front edge:
  1. what the foam has to absorb  2. why the pad cannot simply be thicker  3. the way out

Vertical scale is exaggerated — a few mm of corner lift is invisible at true scale.

This sheet used to carry a CROWN term as well: the original brief's fridge had a formed
steel wrapper that domes. The Samsung's top was straightedged and photographed FLAT, so
the crown term is gone and the pad budget is the corner radius alone.
Reference-only.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging, FRIDGE_SIDE, FRIDGE_SIDE_EDGE, ON_FRIDGE_INK, ON_FRIDGE_MUTED, MAGNET_EDGE, MAGNET_FILL, PAD_EDGE, PAD_FILL
from generate_bracket import MATERIAL, BracketParams, flat_gap

LOG = logging.getLogger("pad")

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

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
           f'viewBox="0 0 {W:.0f} {H:.0f}">',
           f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfbf9"/>',
           f'<rect x="0" y="0" width="{W:.0f}" height="32" fill="#b00020"/>',
           _t(W/2, 22, "REFERENCE ONLY — why the corner radius, the foam pad and the arm magnets are one problem",
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

    # fridge top surface — flat, so this is a straight line
    pts = [(x(i), y(0.0))
           for i in range(0, int(reach) + 1, 2)]
    surf = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    out.append(f'<path d="M {pts[0][0]:.1f} {pts[0][1] + SLAB_PX:.1f} L {surf} '
               f'L {pts[-1][0]:.1f} {pts[-1][1] + SLAB_PX:.1f} Z" '
               f'fill="{FRIDGE_SIDE}" stroke="{FRIDGE_SIDE_EDGE}" stroke-width="1.4"/>')
    out.append(_t(x(reach/2), y(0) + 34, "FRIDGE TOP — domed for rigidity", 9.5, fill=ON_FRIDGE_INK))
    out.append(_t(x(reach/2), y(0) + 48, f"(dome shown {VEXAG:.0f}x exaggerated)", 8.5, fill=ON_FRIDGE_MUTED))

    # rigid arm: straight, touching at the inboard tip, lifted at the bend end
    arm_tip_y = y(0.0)
    arm_root_y = y(gap_corner)
    out.append(f'<line x1="{x(0):.1f}" y1="{arm_root_y:.1f}" x2="{x(reach):.1f}" y2="{arm_tip_y:.1f}" '
               f'stroke="#5d3600" stroke-width="8" stroke-linecap="round"/>')
    out.append(_t(x(reach/2), arm_root_y - 30, f"RIGID {MATERIAL.name.upper()} ARM", 10.5, fill="#5d3600", weight="bold"))
    out.append(_t(x(reach/2), arm_root_y - 17, "it cannot bend to follow the dome", 9, fill="#5d3600"))

    # foam wedge
    wedge = pts + [(x(reach), arm_tip_y), (x(0), arm_root_y)]
    poly = " ".join(f"{a:.1f},{b:.1f}" for a, b in wedge)
    out.append(f'<polygon points="{poly}" fill="{PAD_FILL}" fill-opacity="0.85" stroke="{PAD_EDGE}" '
               f'stroke-width="1"/>')
    # At 0.40 of the reach the sloped arm line passes through this text. The wedge is
    # thickest at the ROOT, so label it there, where there is height for it.
    out.append(_t(x(reach*0.17), arm_root_y + 34, "FOAM fills this wedge", 10,
                  fill="#8a6a10", weight="bold"))

    # total gap dimension, left of the bend end
    out.append(f'<line x1="{x(-22):.1f}" y1="{y(0):.1f}" x2="{x(-22):.1f}" y2="{arm_root_y:.1f}" '
               f'stroke="#b00020" stroke-width="1.5"/>')
    for yy in (y(0), arm_root_y):
        out.append(f'<line x1="{x(-28):.1f}" y1="{yy:.1f}" x2="{x(-16):.1f}" y2="{yy:.1f}" '
                   f'stroke="#b00020" stroke-width="1.5"/>')
    out.append(_t(x(-34), (y(0)+arm_root_y)/2 - 4, "total gap", 10, anchor="end",
                  fill="#b00020", weight="bold"))
    out.append(_t(x(-34), (y(0)+arm_root_y)/2 + 10, f"{gap_corner:.2f} mm",
                  10, anchor="end", fill="#b00020"))

    # the two contributions, right of the tip
    rx = x(reach) + 26
    out.append(f'<line x1="{rx:.1f}" y1="{y(0.0):.1f}" x2="{rx:.1f}" '
               f'y2="{y(gap_corner):.1f}" stroke="#c0169a" stroke-width="1.5"/>')
    out.append(f'<line x1="{x(reach):.1f}" y1="{y(0):.1f}" x2="{rx+6:.1f}" y2="{y(0):.1f}" '
               f'stroke="#8a9199" stroke-width="0.7" stroke-dasharray="3 2"/>')
    out.append(_t(rx + 12, y(gap_corner/2) - 8,
                  f"corner-radius lift  {gap_corner:.2f} mm", 10, anchor="start",
                  fill="#c0169a", weight="bold"))
    out.append(_t(rx + 12, y(gap_corner/2) + 6,
                  "grows if the fridge corner radius is large", 9, anchor="start", fill="#c0169a"))

    out.append(_t(40, oy + SLAB_PX + 46,
                  f"The whole budget is {gap_corner:.2f} mm, against a {pad:.2f} mm pad. "
                  f"That is the whole budget.", 11.5, anchor="start", fill="#111", weight="bold"))
    # y=470 sat directly on the section-2 heading. Move it up under panel 1 where it belongs.
    out.append(_t(40, 442, "The fridge top is FLAT — straightedged and photographed "
                  "2026-08-27. Only the corner radius spends the pad budget.",
                  10.5, anchor="start", fill="#6a737b"))

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
    # The arm SHOULD sit higher when the pad is thicker — that is the whole point of the middle
    # panel. But `base` was the same for all three while the arm rose off it, so the tallest case
    # pushed its arm and its "arm" caption up into the section header. Reserve headroom for the
    # WORST case across all panels, so every panel shares one datum and none of them collides.
    s2 = 9.0
    max_stand = max(max(padh, magh) for _, _, padh, magh, _ in cases)
    base_y = py0 + 74 + max_stand * s2
    for i, (title, colour, padh, magh, note) in enumerate(cases):
        bx = 90.0 + i * cw
        base = base_y
        out.append(_t(bx + 130, py0, title, 11.5, anchor="middle", fill=colour, weight="bold"))
        # steel
        out.append(f'<rect x="{bx:.1f}" y="{base:.1f}" width="260" height="16" fill="{FRIDGE_SIDE}" '
                   f'stroke="#8a9199" stroke-width="1.2"/>')
        out.append(_t(bx + 130, base + 30, "fridge steel", 9, fill="#6a737b"))
        stand = max(padh, magh)
        army = base - stand * s2 - 10
        # foam block
        out.append(f'<rect x="{bx + 20:.1f}" y="{base - padh*s2:.1f}" width="120" '
                   f'height="{padh*s2:.1f}" fill="{PAD_FILL}" fill-opacity="0.85" stroke="{PAD_EDGE}"/>')
        out.append(_t(bx + 80, base - padh*s2/2 + 4, f"foam {padh:.2f}", 9, fill="#6b5008", weight="bold"))
        # magnet block
        out.append(f'<rect x="{bx + 165:.1f}" y="{base - magh*s2:.1f}" width="70" '
                   f'height="{magh*s2:.1f}" fill="#c0169a" fill-opacity="0.35" stroke="#c0169a"/>')
        out.append(_t(bx + 200, base - magh*s2/2 + 4, f"magnet {magh:.2f}", 9, fill="#8c1070", weight="bold"))
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
    out.append(_t(40, py1, "3 — The way out, if the corner radius measures ugly", 13, anchor="start", weight="bold"))
    lines = [
        ("Keep the arm magnets", "#5d3600",
         f"pad locked to the stock size that matches the {p.arm_magnet_standoff:.2f} mm "
         f"magnet, currently {pad:.2f} mm  ->  the arm magnets must reach steel"),
        ("Drop the arm magnets", "#2e9e5b",
         "pad thickness becomes free  ->  3/8 in foam tolerates a far larger corner radius, "
         "8.5 mm at 180 mm"),
    ]
    for i, (label, colour, txt) in enumerate(lines):
        yy = py1 + 30 + i * 42
        out.append(f'<rect x="60" y="{yy-14:.0f}" width="12" height="12" fill="{colour}"/>')
        out.append(_t(82, yy - 3, label, 11.5, anchor="start", fill=colour, weight="bold"))
        out.append(_t(82, yy + 14, txt, 10, anchor="start", fill="#333"))
    out.append(_t(60, py1 + 122,
                  "The arm magnets are anti-jostle only — zero credit in the load path. They are "
                  "costing you pad tolerance, not strength.",
                  10.5, anchor="start", fill="#555"))
    out.append(_t(60, py1 + 139,
                  "The top measured flat, so none of this bites: keep the magnets.",
                  10.5, anchor="start", fill="#111", weight="bold"))
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    LOG.info("Wrote %s (corner lift %.2f mm vs pad %.2f mm, margin %.2fx)",
             path, gap_corner, pad, pad / gap_corner)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Draw the corner-radius / foam / arm-magnet interaction.")
    ap.add_argument("--out", type=Path, default=Path("pad_explainer.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
