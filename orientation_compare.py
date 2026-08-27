#!/usr/bin/env python3
"""Landscape vs portrait on a COUNTER-DEPTH side panel.

Looking straight at the fridge's side panel — the plane the display hangs in. The horizontal axis
is the fridge's DEPTH (front to back), which on a counter-depth cabinet is only 610 mm. That is the
constraint nobody sees coming: a 555 mm landscape display has to fit between the door's swing at the
front and the wall at the back.

Reference-only.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging, FRIDGE_SIDE, FRIDGE_SIDE_EDGE
from generate_bracket import DISPLAY, MM_PER_INCH, BracketParams

LOG = logging.getLogger("orient")

DOOR_SWEEP_IN = 2.5   # Samsung: allow 2.5" on the hinge side, handle may make contact
REAR_CLEAR_IN = 1.0   # Samsung: allow 1" minimum at the rear for air circulation
COMFORT_LOW, COMFORT_HIGH = 1216.0, 1450.0


def _esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _t(x, y, s, size=10.0, anchor="middle", fill="#111", weight="normal", rotate=0.0):
    tr = f' transform="rotate({rotate:.1f} {x:.1f} {y:.1f})"' if rotate else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"{tr}>'
            f'{_esc(s)}</text>')


def render(path: Path, p: BracketParams) -> None:
    sc = 0.30
    depth, height = p.fridge_depth, p.fridge_height
    door = DOOR_SWEEP_IN * MM_PER_INCH
    rear = REAR_CLEAR_IN * MM_PER_INCH
    usable = depth - door

    panel_w = depth * sc + 260
    W = 120 + panel_w * 2
    H = 205 + height * sc + 210

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
           f'viewBox="0 0 {W:.0f} {H:.0f}">',
           f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfbf9"/>',
           f'<rect x="0" y="0" width="{W:.0f}" height="32" fill="#b00020"/>',
           _t(W/2, 22, "REFERENCE ONLY — orientation study on a counter-depth side panel",
              14, fill="#fff", weight="bold"),
           _t(40, 60, "Landscape vs portrait — looking straight at the side panel", 18,
              anchor="start", weight="bold"),
           _t(40, 82, f"Horizontal axis is the fridge's DEPTH. Samsung RS23A500ASR is COUNTER-DEPTH: "
                      f"the cabinet is only {depth:.0f} mm front to back.", 11, anchor="start", fill="#555"),
           _t(40, 99, f"The door sweeps the front {door:.0f} mm when it opens (Samsung's own "
                      f"2.5 in hinge-side clearance), so that strip is unusable.",
              11, anchor="start", fill="#555")]

    for idx, (name, dw, dh) in enumerate((("LANDSCAPE", DISPLAY.width, DISPLAY.height),
                                          ("PORTRAIT", DISPLAY.height, DISPLAY.width))):
        ox = 70 + idx * panel_w
        oy = 205.0

        def X(mm): return ox + mm * sc          # mm from cabinet FRONT
        def Y(mm): return oy + (height - mm) * sc   # mm above the floor

        fits = dw <= usable
        col = "#2e9e5b" if fits else "#b00020"
        out.append(_t(ox + depth*sc/2, oy - 62, name, 15, weight="bold", fill=col))
        out.append(_t(ox + depth*sc/2, oy - 45,
                      f"{dw:.0f} mm display in a {usable:.0f} mm window", 10.5, fill="#555"))
        out.append(_t(ox + depth*sc/2, oy - 29,
                      ("FITS — " + format(usable-dw, '.0f') + " mm spare") if fits
                      else ("DOES NOT FIT — over by " + format(dw-usable, '.0f') + " mm"),
                      12, fill=col, weight="bold"))

        # cabinet
        out.append(f'<rect x="{X(0):.1f}" y="{Y(height):.1f}" width="{depth*sc:.1f}" '
                   f'height="{height*sc:.1f}" fill="{FRIDGE_SIDE}" stroke="{FRIDGE_SIDE_EDGE}" stroke-width="1.4"/>')
        out.append(_t(X(depth/2), Y(height*0.12), "SIDE PANEL", 11, fill="#6a737b"))
        out.append(_t(X(depth/2), Y(height*0.12) + 15, f"{depth:.0f} mm deep x {height:.0f} mm tall",
                      9, fill="#8a9199"))
        out.append(_t(X(6), Y(height) + 16, "FRONT", 9, anchor="start", fill="#6a737b", weight="bold"))
        out.append(_t(X(depth-6), Y(height) + 16, "BACK", 9, anchor="end", fill="#6a737b", weight="bold"))

        # door sweep keep-out
        out.append(f'<rect x="{X(0):.1f}" y="{Y(height):.1f}" width="{door*sc:.1f}" '
                   f'height="{height*sc:.1f}" fill="#b00020" fill-opacity="0.15" '
                   f'stroke="#b00020" stroke-width="1" stroke-dasharray="4 3"/>')
        out.append(_t(X(door/2), Y(height*0.55), f"door sweep {door:.0f}", 8.5, fill="#b00020",
                      weight="bold", rotate=-90))

        # hinge cover, top front
        hc_depth = 110.0
        out.append(f'<rect x="{X(0):.1f}" y="{Y(height) - p.hinge_cover_proud*sc:.1f}" '
                   f'width="{hc_depth*sc:.1f}" height="{p.hinge_cover_proud*sc:.1f}" '
                   f'fill="#8a9199" stroke="#5c6368" stroke-width="1"/>')
        out.append(_t(X(hc_depth) + 8, Y(height) - p.hinge_cover_proud*sc - 2,
                      f"hinge cover, {p.hinge_cover_proud:.0f} mm proud", 8.5, anchor="start",
                      fill="#5c6368"))

        # bracket: arm on top, body on the panel, centred in the usable window
        centre = door + usable / 2.0
        arm0, arm1 = centre - p.neck_w/2, centre + p.neck_w/2
        out.append(f'<rect x="{X(arm0):.1f}" y="{Y(height) - p.arm_pad*sc - 4:.1f}" '
                   f'width="{p.neck_w*sc:.1f}" height="4" fill="#9a5b00"/>')
        # Was at Y(height) - 18, the same band as the hinge-cover callout, so the two stacked.
        # The arm label belongs BELOW its own bar, where nothing else is drawn.
        out.append(_t(X(centre), Y(height) + 13, f"arm {p.neck_w:.0f} mm", 8.5, fill="#5d3600",
                      weight="bold"))

        body_top = height - p.neck_len
        out.append(f'<rect x="{X(centre - p.body_w/2):.1f}" y="{Y(body_top):.1f}" '
                   f'width="{p.body_w*sc:.1f}" height="{p.body_h*sc:.1f}" fill="#9a5b00" '
                   f'fill-opacity="0.45" stroke="#5d3600" stroke-width="1"/>')

        # display
        screen_c = height - p.neck_len - p.body_h/2
        out.append(f'<rect x="{X(centre - dw/2):.1f}" y="{Y(screen_c + dh/2):.1f}" '
                   f'width="{dw*sc:.1f}" height="{dh*sc:.1f}" fill="#2b2b2b" fill-opacity="0.88" '
                   f'stroke="#000" stroke-width="1.2"/>')
        out.append(_t(X(centre), Y(screen_c), f"{dw:.0f} x {dh:.0f}", 10, fill="#fff", weight="bold"))

        # overflow callouts
        if not fits:
            over_front = door - (centre - dw/2)
            out.append(f'<rect x="{X(centre - dw/2):.1f}" y="{Y(screen_c + dh/2):.1f}" '
                       f'width="{over_front*sc:.1f}" height="{dh*sc:.1f}" fill="#b00020" '
                       f'fill-opacity="0.45" stroke="#b00020" stroke-width="1.4"/>')
            # Right-anchored at the door edge, this ran left into the comfort-band pill that
            # sits at X(0) - 42. Anchor it INSIDE the red overhang instead, which is its subject.
            out.append(_t(X(centre - dw/2) + 6, Y(screen_c), "into the", 9, anchor="start",
                          fill="#b00020", weight="bold"))
            out.append(_t(X(centre - dw/2) + 6, Y(screen_c) + 12, "door's path", 9, anchor="start",
                          fill="#b00020", weight="bold"))

        # comfort band
        out.append(f'<rect x="{X(0) - 42:.1f}" y="{Y(COMFORT_HIGH):.1f}" width="34" '
                   f'height="{(COMFORT_HIGH-COMFORT_LOW)*sc:.1f}" fill="#2e9e5b" fill-opacity="0.18"/>')
        out.append(_t(X(0) - 25, Y((COMFORT_LOW+COMFORT_HIGH)/2), "comfort", 8, fill="#2e9e5b",
                      weight="bold", rotate=-90))
        out.append(_t(X(depth) + 10, Y(screen_c) + 4, f"screen centre {screen_c:.0f} mm",
                      9, anchor="start", fill="#111"))
        out.append(_t(X(depth) + 10, Y(screen_c + dh/2) + 4, f"top {screen_c + dh/2:.0f}",
                      8.5, anchor="start", fill="#666"))
        out.append(_t(X(depth) + 10, Y(screen_c - dh/2) + 4, f"bottom {screen_c - dh/2:.0f}",
                      8.5, anchor="start", fill="#666"))

    fy = 205 + height*sc + 46
    notes = [
        ("#b00020", "LANDSCAPE does not fit. The 555 mm display is 9 mm wider than the usable "
                    "window, and centring it puts its front edge inside the arc the door sweeps."),
        ("#2e9e5b", "PORTRAIT fits with 221 mm to spare — and the brief already noted portrait is "
                    "mechanically better: the touch-torsion arm drops from 278 mm to 162 mm."),
        ("#555", "The 63.5 mm front keep-out is Samsung's own 2.5 in hinge-side clearance figure. "
                 "VERIFY IT: open the door fully and measure how far it sweeps past the side panel."),
        ("#555", "Hinge cover footprint is drawn indicatively. Measure how far back it extends — "
                 "it further narrows where the arm can land."),
    ]
    for i, (c, n) in enumerate(notes):
        out.append(f'<rect x="60" y="{fy + i*26 - 10:.0f}" width="11" height="11" fill="{c}"/>')
        out.append(_t(80, fy + i*26, n, 10.5, anchor="start", fill="#333"))
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    LOG.info("Wrote %s — usable window %.1f mm; landscape %.2f, portrait %.2f",
             path, usable, DISPLAY.width, DISPLAY.height)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Landscape vs portrait on the counter-depth side panel.")
    ap.add_argument("--out", type=Path, default=Path("orientation_compare.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
