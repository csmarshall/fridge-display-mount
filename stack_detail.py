#!/usr/bin/env python3
"""The fastener sandwich at one magnet, in section: fridge | magnet | plate | washer | nut.

This exists because the stud length is the one dimension that goes WRONG when the plate gets
thicker, and nothing else in the drawing set would show it. The magnet's stud is a fixed 1/2 in;
everything it has to pass through is not.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
import generate_bracket as G
from generate_bracket import MATERIAL, BracketParams

LOG = logging.getLogger("stack")

IN = 25.4
INK, MUTED, RULE = "#14181c", "#6b757e", "#c9d1d8"
OK, BAD, WARN = "#0a8f6f", "#b00020", "#b8860b"

STUD_LEN = 0.5 * IN            # 3506K67: male 5/16"-18 x 1/2" stud
WASHER_T = 1.27                # 18-8 stainless 5/16 flat washer
NYLOC_H = 0.330 * IN           # 5/16"-18 nylon-insert locknut
HEXNUT_H = 0.266 * IN          # 5/16"-18 standard hex nut


def _t(x, y, s, size=10.0, anchor="middle", fill=INK, weight="normal", rot=0.0):
    tr = f' transform="rotate({rot:.1f} {x:.2f} {y:.2f})"' if rot else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}"{tr}>{s}</text>')


def render(path: Path, p: BracketParams) -> None:
    t = MATERIAL.thickness
    s = 13.0                              # px per mm — this is a detail, draw it big
    ox, oy = 300.0, 210.0
    W, H = 1180.0, 800.0

    options = [
        ("washer + nylon-insert locknut", WASHER_T, NYLOC_H, "nyloc"),
        ("nylon-insert locknut, no washer", 0.0, NYLOC_H, "nyloc"),
        ("washer + standard hex nut", WASHER_T, HEXNUT_H, "hex"),
        ("standard hex nut, no washer", 0.0, HEXNUT_H, "hex"),
    ]

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfcfd"/>',
         _t(40, 46, "THE FASTENER SANDWICH AT ONE MAGNET", 19, anchor="start", weight="bold"),
         _t(40, 70, "Section through a single magnet position. The stud is a fixed "
                    f"{STUD_LEN:.2f} mm ({STUD_LEN/IN:.3f} in); "
                    "everything it passes through is not.", 12, anchor="start", fill=MUTED),
         _t(40, 92, f"Plate is {t:.2f} mm ({MATERIAL.thickness_in:.3f} in). Change the plate "
                    f"thickness and this drawing changes with it — that is the point of it.",
            12, anchor="start", fill=MUTED)]

    # ---- the section itself ----------------------------------------------------------------
    y0 = oy
    bar_h = 92.0
    layers = [
        ("FRIDGE panel", 0.9, "#dfe3e6", "painted appliance sheet"),
        (f"MAGNET {p.magnet_standoff:.2f} mm", p.magnet_standoff, "#e7b6dd",
         f"O{p.magnet_disc_dia:.1f} pot, {p.magnet_rated_pull_lbf:.0f} lbf rated"),
        (f"PLATE {t:.2f} mm", t, "#b9c2c9", f"{MATERIAL.name}"),
        (f"washer {WASHER_T:.2f} mm", WASHER_T, "#cdd5db", "optional — see below"),
        (f"nut {NYLOC_H:.2f} mm", NYLOC_H, "#9aa6ae", "nylon-insert locknut"),
    ]
    x = ox
    for name, thick, fill, note in layers:
        w = max(thick * s, 14.0)
        o.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{bar_h:.1f}" '
                 f'fill="{fill}" stroke="{INK}" stroke-width="1.2"/>')
        # A 1.27 mm washer is 16 px wide and its label is 60 — horizontal labels on narrow
        # layers CANNOT avoid colliding. Rotate 45 deg on a leader so each runs away from its
        # own layer rather than across its neighbour's.
        lx, ly = x + w / 2.0, y0 + bar_h + 16
        o.append(f'<line x1="{lx:.1f}" y1="{y0 + bar_h + 2:.1f}" x2="{lx:.1f}" '
                 f'y2="{ly - 3:.1f}" stroke="{MUTED}" stroke-width="0.8"/>')
        head, rest = name.split()[0], " ".join(name.split()[1:])
        o.append(_t(lx, ly, head, 10.5, anchor="end", weight="bold", rot=-45))
        if rest:
            o.append(_t(lx + 12, ly + 12, rest, 9.5, anchor="end", fill=MUTED, rot=-45))
        x += w
    stack_end = x

    # the stud, drawn as it actually reaches
    stud_x0 = ox + (0.9 + p.magnet_standoff) * s
    o.append(f'<rect x="{stud_x0:.1f}" y="{y0 + bar_h/2 - 9:.1f}" '
             f'width="{STUD_LEN * s:.1f}" height="18" fill="#8a6a10" fill-opacity="0.55" '
             f'stroke="#5d3600" stroke-width="1.4"/>')
    o.append(_t(stud_x0 + STUD_LEN * s / 2.0, y0 + bar_h/2 + 5,
                f"STUD {STUD_LEN:.2f} mm", 10, fill="#3d2b00", weight="bold"))
    stud_end = stud_x0 + STUD_LEN * s
    o.append(f'<line x1="{stud_end:.1f}" y1="{y0 - 22:.1f}" x2="{stud_end:.1f}" '
             f'y2="{y0 + bar_h + 44:.1f}" stroke="{BAD}" stroke-width="1.6" '
             f'stroke-dasharray="6 4"/>')
    o.append(_t(stud_end - 6, y0 - 30, "stud ends here", 9.5, anchor="end", fill=BAD,
                weight="bold"))
    o.append(f'<line x1="{stack_end:.1f}" y1="{y0 - 22:.1f}" x2="{stack_end:.1f}" '
             f'y2="{y0 + bar_h + 44:.1f}" stroke="{INK}" stroke-width="1.2" '
             f'stroke-dasharray="3 3"/>')
    o.append(_t(stack_end + 6, y0 - 12, "stack ends here", 9.5, anchor="start", fill=INK))

    # ---- the four options ------------------------------------------------------------------
    ty = y0 + bar_h + 132
    o.append(_t(40, ty, "WILL THE NUT FULLY ENGAGE?", 14, anchor="start", weight="bold"))
    o.append(_t(40, ty + 20, "The stud has to pass the plate and still fill the nut. "
                             "Anything negative means it does not.", 11, anchor="start",
               fill=MUTED))
    best = None
    for i, (name, wsh, nut, kind) in enumerate(options):
        need = t + wsh + nut
        slack = STUD_LEN - need
        good = slack >= 0
        if good and best is None:
            best = name
        ry = ty + 52 + i * 30
        col = OK if good else BAD
        o.append(f'<rect x="40" y="{ry-17:.1f}" width="{W-80:.1f}" height="26" '
                 f'fill="{"#eef7f2" if good else "#fdf0f1"}" rx="3"/>')
        o.append(_t(56, ry, name, 12, anchor="start", weight="bold" if good else "normal"))
        o.append(_t(560, ry, f"needs {need:.2f} mm", 11.5, anchor="end", fill=MUTED))
        o.append(_t(700, ry, f"{slack:+.2f} mm", 12.5, anchor="end", fill=col, weight="bold"))
        o.append(_t(720, ry, "engages fully" if good else "STUD TOO SHORT", 11.5,
                   anchor="start", fill=col, weight="bold"))
    fy = ty + 52 + len(options) * 30 + 26
    o.append(f'<rect x="40" y="{fy-18:.1f}" width="{W-80:.1f}" height="54" fill="#fff" '
             f'stroke="{OK if best else BAD}" stroke-width="1.6" rx="4"/>')
    o.append(_t(56, fy + 2, f"USE: {best}" if best else
               "NO STANDARD NUT FITS — the stud is too short for this plate", 13,
               anchor="start", weight="bold", fill=OK if best else BAD))
    o.append(_t(56, fy + 22,
                f"The stud is fixed at {STUD_LEN:.2f} mm, so every millimetre of plate comes "
                f"straight off the thread available to the nut.", 11, anchor="start", fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — plate %.2f mm, stud %.2f mm, workable option: %s",
             path, t, STUD_LEN, best or "NONE")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("stack_detail.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
