#!/usr/bin/env python3
"""23.8in vs 27in, both in PORTRAIT, on the counter-depth side panel.

Same view as orientation_compare: looking straight at the side panel, horizontal axis is the
fridge's depth. In portrait the display's WIDTH runs front-to-back, so it is the smaller dimension
and both panels clear the door's sweep comfortably. Reference-only.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
from generate_bracket import DISPLAYS, MM_PER_INCH, BracketParams, set_display
import generate_bracket as G

LOG = logging.getLogger("displays")

DOOR_SWEEP_IN = 2.5
COMFORT_LOW, COMFORT_HIGH = 1216.0, 1450.0


def _esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _t(x, y, s, size=10.0, anchor="middle", fill="#111", weight="normal", rotate=0.0):
    tr = f' transform="rotate({rotate:.1f} {x:.1f} {y:.1f})"' if rotate else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"{tr}>'
            f'{_esc(s)}</text>')


def render(path: Path, p: BracketParams, neck: float) -> None:
    sc = 0.295
    depth, height = p.fridge_depth, p.fridge_height
    door = DOOR_SWEEP_IN * MM_PER_INCH
    usable = depth - door
    screen_c = height - neck - p.body_h / 2.0
    centre = door + usable / 2.0

    panel_w = depth * sc + 300
    W, H = 120 + panel_w * 2, 215 + height * sc + 200

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
           f'viewBox="0 0 {W:.0f} {H:.0f}">',
           f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfbf9"/>',
           f'<rect x="0" y="0" width="{W:.0f}" height="32" fill="#b00020"/>',
           _t(W/2, 22, "REFERENCE ONLY — 23.8 in vs 27 in, both portrait", 14, fill="#fff", weight="bold"),
           _t(40, 60, "Which panel, in portrait, on the counter-depth side", 18, anchor="start", weight="bold"),
           _t(40, 82, f"Same view as before: horizontal axis is the fridge's depth. In portrait the "
                      f"display's WIDTH runs front-to-back, so both fit the {usable:.0f} mm window easily.",
              11, anchor="start", fill="#555"),
           _t(40, 99, f"Neck {neck:.0f} mm puts the screen centre at {screen_c:.0f} mm for either panel — "
                      f"the VESA centre does not move.", 11, anchor="start", fill="#555")]

    for idx, key in enumerate(("23.8", "27")):
        set_display(key)
        d = G.DISPLAY
        dw, dh = d.height, d.width          # portrait: width across the panel, length up it
        ox, oy = 70 + idx * panel_w, 215.0

        def X(mm): return ox + mm * sc
        def Y(mm): return oy + (height - mm) * sc

        top, bot = screen_c + dh/2, screen_c - dh/2
        clear_top = height - top
        body_hide = (dw - p.body_w) / 2.0

        out.append(_t(X(depth/2), oy - 62, f'{key} in', 16, weight="bold", fill="#1a5fb4"))
        out.append(_t(X(depth/2), oy - 44, f"{dw:.1f} wide x {dh:.1f} tall, {d.mass_kg:.2f} kg",
                      10.5, fill="#555"))
        out.append(_t(X(depth/2), oy - 28, f"{usable - dw:.0f} mm spare in the window",
                      11, fill="#2e9e5b", weight="bold"))

        out.append(f'<rect x="{X(0):.1f}" y="{Y(height):.1f}" width="{depth*sc:.1f}" '
                   f'height="{height*sc:.1f}" fill="#dfe3e6" stroke="#8a9199" stroke-width="1.4"/>')
        out.append(_t(X(depth/2), Y(height*0.09), "SIDE PANEL", 10.5, fill="#6a737b"))
        out.append(_t(X(6), Y(height) + 16, "FRONT", 9, anchor="start", fill="#6a737b", weight="bold"))
        out.append(_t(X(depth-6), Y(height) + 16, "BACK", 9, anchor="end", fill="#6a737b", weight="bold"))

        out.append(f'<rect x="{X(0):.1f}" y="{Y(height):.1f}" width="{door*sc:.1f}" '
                   f'height="{height*sc:.1f}" fill="#b00020" fill-opacity="0.15" '
                   f'stroke="#b00020" stroke-width="1" stroke-dasharray="4 3"/>')
        out.append(_t(X(door/2), Y(height*0.62), f"door sweep {door:.0f}", 8.5, fill="#b00020",
                      weight="bold", rotate=-90))

        out.append(f'<rect x="{X(0):.1f}" y="{Y(height) - p.hinge_cover_proud*sc:.1f}" '
                   f'width="{110.0*sc:.1f}" height="{p.hinge_cover_proud*sc:.1f}" '
                   f'fill="#8a9199" stroke="#5c6368" stroke-width="1"/>')

        # bracket arm + body
        out.append(f'<rect x="{X(centre - p.neck_w/2):.1f}" '
                   f'y="{Y(height) - p.arm_pad*sc - 4:.1f}" '
                   f'width="{p.neck_w*sc:.1f}" height="4" fill="#9a5b00"/>')
        out.append(_t(X(centre), Y(height) - 18, f"arm {p.neck_w:.0f}", 8.5, fill="#5d3600", weight="bold"))
        out.append(f'<rect x="{X(centre - p.body_w/2):.1f}" y="{Y(height - neck):.1f}" '
                   f'width="{p.body_w*sc:.1f}" height="{p.body_h*sc:.1f}" fill="#9a5b00" '
                   f'fill-opacity="0.45" stroke="#5d3600" stroke-width="1"/>')

        # display
        out.append(f'<rect x="{X(centre - dw/2):.1f}" y="{Y(top):.1f}" width="{dw*sc:.1f}" '
                   f'height="{dh*sc:.1f}" fill="#2b2b2b" fill-opacity="0.88" stroke="#000" '
                   f'stroke-width="1.2"/>')
        out.append(_t(X(centre), Y(screen_c) - 4, f"{dw:.0f}", 11, fill="#fff", weight="bold"))
        out.append(_t(X(centre), Y(screen_c) + 12, f"x {dh:.0f}", 11, fill="#fff", weight="bold"))

        # comfort band + callouts
        out.append(f'<rect x="{X(0) - 40:.1f}" y="{Y(COMFORT_HIGH):.1f}" width="32" '
                   f'height="{(COMFORT_HIGH-COMFORT_LOW)*sc:.1f}" fill="#2e9e5b" fill-opacity="0.18"/>')
        out.append(_t(X(0) - 24, Y((COMFORT_LOW+COMFORT_HIGH)/2), "comfort", 8, fill="#2e9e5b",
                      weight="bold", rotate=-90))
        rx = X(depth) + 12
        for yy, txt, c in ((top, f"top {top:.0f}", "#666"),
                           (screen_c, f"screen centre {screen_c:.0f}", "#111"),
                           (bot, f"bottom {bot:.0f}", "#666")):
            out.append(_t(rx, Y(yy) + 4, txt, 9, anchor="start", fill=c,
                          weight="bold" if c == "#111" else "normal"))
        out.append(_t(rx, Y(height) + 4, f"{clear_top:.0f} mm below the fridge top", 8.5,
                      anchor="start", fill="#8a9199"))
        out.append(_t(rx, Y(bot) + 20, f"plate hidden by {body_hide:.0f} mm/side", 8.5,
                      anchor="start", fill="#5d3600"))
        LOG.info("%s in portrait: %.1f wide (%.0f spare), top %.0f, bottom %.0f, plate hidden %.1f/side",
                 key, dw, usable - dw, top, bot, body_hide)

    fy = 215 + height*sc + 40
    notes = [
        ("#2e9e5b", "Both fit portrait comfortably. The 27 in is 42 mm wider front-to-back and "
                    "still leaves 179 mm of the window spare."),
        ("#5d3600", "The 27 in HIDES THE PLATE BETTER: 367 mm wide against the 310 mm body gives "
                    "28.7 mm of overhang per side, versus 7.3 mm on the 23.8 in."),
        ("#1a5fb4", "Identical bracket either way — same rear box, same VESA, same fan radius. "
                    "The DXF is geometrically identical; only the load case changes."),
        ("#b00020", "The 27 in hangs 1 kg heavier and reaches 97 mm from the fridge top down to "
                    "1016 mm. Magnet safety factor 6.4x versus 7.2x — both ample."),
    ]
    for i, (c, n) in enumerate(notes):
        out.append(f'<rect x="60" y="{fy + i*26 - 10:.0f}" width="11" height="11" fill="{c}"/>')
        out.append(_t(80, fy + i*26, n, 10.5, anchor="start", fill="#333"))
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="23.8 vs 27 inch in portrait on the side panel.")
    ap.add_argument("--neck", type=float, default=262.0)
    ap.add_argument("--out", type=Path, default=Path("display_compare.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams(), a.neck)
    return 0


if __name__ == "__main__":
    sys.exit(main())
