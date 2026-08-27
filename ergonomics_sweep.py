#!/usr/bin/env python3
"""Neck-length (drop) sweep for the fridge-side display mount.

Renders one SVG with several candidate neck lengths side by side, each showing the display in
BOTH landscape and portrait against fixed anthropometric reference bands, so the drop can be
chosen by comparing pictures rather than by arguing about numbers.

Reference-only. Feed the chosen value to generate_bracket.py with --neck-length, or let the
generator derive it with --fridge-height / --screen-centre-height.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
from generate_bracket import DISPLAY, BracketParams

LOG = logging.getLogger("ergonomics")

MM_PER_INCH = 25.4

# Dreyfuss/ANSUR-style stature ratios. One home for each fact; every height below is derived.
EYE_RATIO = 0.936
SHOULDER_RATIO = 0.818
ELBOW_RATIO = 0.630


@dataclass(frozen=True)
class Person:
    label: str
    stature_mm: float

    @property
    def eye(self) -> float:
        return self.stature_mm * EYE_RATIO

    @property
    def shoulder(self) -> float:
        return self.stature_mm * SHOULDER_RATIO

    @property
    def elbow(self) -> float:
        return self.stature_mm * ELBOW_RATIO


def feet_inches(feet: int, inches: float) -> float:
    return (feet * 12 + inches) * MM_PER_INCH


SHORT = Person("5'1\"", feet_inches(5, 1))
TALL = Person("6'4\"", feet_inches(6, 4))

# LG side-by-side, US: LRSXS2706 is 70.5 in tall. Verified on lg.com 2026-08-24.
LG_FRIDGE_HEIGHT_MM = 70.5 * MM_PER_INCH
LG_FRIDGE_DEPTH_MM = 33.5 * MM_PER_INCH


def screen_centre_height(fridge_height: float, neck_len: float, body_h: float) -> float:
    """VESA centre = body centre, so the screen centre is the body centre in both orientations."""
    return fridge_height - neck_len - body_h / 2.0


def neck_for_screen_centre(fridge_height: float, target_centre: float, body_h: float) -> float:
    return fridge_height - target_centre - body_h / 2.0


def _text(x: float, y: float, s: str, size: float = 10.0, anchor: str = "middle",
          fill: str = "#111", weight: str = "normal") -> str:
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">{s}</text>')


def render(path: Path, necks: Sequence[float], params: BracketParams, fridge_height: float) -> None:
    scale = 0.30
    panel_w = 330.0
    margin_l, margin_t = 216.0, 96.0
    ceiling_mm = 2050.0
    canvas_h = margin_t + ceiling_mm * scale + 132.0
    canvas_w = margin_l + panel_w * len(necks) + 40.0

    def y(v_mm: float) -> float:
        """Height above the floor -> SVG y."""
        return margin_t + (ceiling_mm - v_mm) * scale

    comfort_low = max(SHORT.elbow, TALL.elbow)
    comfort_high = min(SHORT.eye, TALL.eye)
    LOG.info("Comfortable standing touch band shared by %s and %s: %.0f-%.0f mm above the floor",
             SHORT.label, TALL.label, comfort_low, comfort_high)

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w:.0f}" height="{canvas_h:.0f}" '
        f'viewBox="0 0 {canvas_w:.0f} {canvas_h:.0f}">',
        f'<rect width="{canvas_w:.0f}" height="{canvas_h:.0f}" fill="#fbfbf9"/>',
        f'<rect x="0" y="0" width="{canvas_w:.0f}" height="30" fill="#b00020"/>',
        _text(canvas_w / 2, 21, "REFERENCE ONLY — mounting-height study, not a fabrication drawing",
              size=13, fill="#fff", weight="bold"),
        _text(40, 54, "Display mounting height vs. neck (drop) length", size=15,
              anchor="start", weight="bold"),
        _text(40, 71,
              f"LG side-by-side {fridge_height / MM_PER_INCH:.1f}\" ({fridge_height:.0f} mm) tall · "
              f"body {params.body_w:.0f} x {params.body_h:.0f} mm · screen centre = VESA centre = body centre, "
              f"so it is identical in both orientations",
              size=10, anchor="start", fill="#555"),
    ]

    # --- reference bands, drawn full width behind the panels -------------------------
    out.append(f'<rect x="{margin_l - 96:.0f}" y="{y(comfort_high):.2f}" width="{canvas_w - margin_l + 60:.0f}" '
               f'height="{(comfort_high - comfort_low) * scale:.2f}" fill="#2e9e5b" fill-opacity="0.12"/>')
    for person, colour in ((SHORT, "#1a5fb4"), (TALL, "#8b5e00")):
        out.append(f'<line x1="{margin_l - 96:.0f}" y1="{y(person.eye):.2f}" x2="{canvas_w - 36:.0f}" '
                   f'y2="{y(person.eye):.2f}" stroke="{colour}" stroke-width="1" stroke-dasharray="7 4"/>')
        out.append(_text(margin_l - 100, y(person.eye) - 3, f"{person.label} eye {person.eye:.0f}",
                         size=9, anchor="end", fill=colour))
        out.append(f'<line x1="{margin_l - 96:.0f}" y1="{y(person.elbow):.2f}" x2="{canvas_w - 36:.0f}" '
                   f'y2="{y(person.elbow):.2f}" stroke="{colour}" stroke-width="0.8" stroke-dasharray="2 4"/>')
        out.append(_text(margin_l - 100, y(person.elbow) - 3, f"{person.label} elbow {person.elbow:.0f}",
                         size=9, anchor="end", fill=colour))
    out.append(_text(margin_l - 100, y((comfort_low + comfort_high) / 2) + 4,
                     f"comfortable touch", size=9, anchor="end", fill="#2e9e5b", weight="bold"))
    out.append(_text(margin_l - 100, y((comfort_low + comfort_high) / 2) + 15,
                     f"{comfort_low:.0f}-{comfort_high:.0f} mm", size=9, anchor="end", fill="#2e9e5b"))
    out.append(f'<line x1="{margin_l - 110:.0f}" y1="{y(0):.2f}" x2="{canvas_w - 30:.0f}" y2="{y(0):.2f}" '
               f'stroke="#333" stroke-width="1.4"/>')

    # --- one panel per candidate neck length -----------------------------------------
    for index, neck in enumerate(necks):
        px = margin_l + index * panel_w
        centre = screen_centre_height(fridge_height, neck, params.body_h)
        body_top = fridge_height - neck
        fridge_px = LG_FRIDGE_DEPTH_MM * scale

        out.append(f'<rect x="{px:.2f}" y="{y(fridge_height):.2f}" width="{fridge_px:.2f}" '
                   f'height="{fridge_height * scale:.2f}" fill="#dfe3e6" stroke="#8a9199" stroke-width="1"/>')
        out.append(_text(px + fridge_px / 2, y(fridge_height * 0.12), "LG side-by-side", size=9, fill="#6a737b"))
        out.append(_text(px + fridge_px / 2, y(fridge_height * 0.12) + 12, "(side panel, face on)",
                         size=8, fill="#8a9199"))

        # bracket: arm hooked over the top, neck, body
        arm_px = params.arm_len * scale
        out.append(f'<rect x="{px + fridge_px / 2 - arm_px / 2:.2f}" y="{y(fridge_height) - 5:.2f}" '
                   f'width="{arm_px:.2f}" height="5" fill="#9a5b00"/>')
        out.append(f'<rect x="{px + fridge_px / 2 - params.neck_w * scale / 2:.2f}" y="{y(fridge_height):.2f}" '
                   f'width="{params.neck_w * scale:.2f}" height="{neck * scale:.2f}" fill="#9a5b00" '
                   f'fill-opacity="0.5"/>')
        out.append(f'<rect x="{px + fridge_px / 2 - params.body_w * scale / 2:.2f}" y="{y(body_top):.2f}" '
                   f'width="{params.body_w * scale:.2f}" height="{params.body_h * scale:.2f}" fill="#9a5b00" '
                   f'fill-opacity="0.5" stroke="#5d3600" stroke-width="0.8"/>')

        # portrait outline first, landscape solid on top
        for label, w_mm, h_mm, style in (
            ("portrait", DISPLAY.height, DISPLAY.width,
             'fill="none" stroke="#b00020" stroke-width="1.4" stroke-dasharray="6 4"'),
            ("landscape", DISPLAY.width, DISPLAY.height, 'fill="#2b2b2b" fill-opacity="0.85" stroke="#000"'),
        ):
            out.append(f'<rect x="{px + fridge_px / 2 - w_mm * scale / 2:.2f}" '
                       f'y="{y(centre + h_mm / 2):.2f}" width="{w_mm * scale:.2f}" '
                       f'height="{h_mm * scale:.2f}" {style}/>')
            LOG.debug("neck=%.0f %s: top=%.0f centre=%.0f bottom=%.0f mm",
                      neck, label, centre + h_mm / 2, centre, centre - h_mm / 2)

        out.append(f'<line x1="{px + 6:.2f}" y1="{y(centre):.2f}" x2="{px + fridge_px - 6:.2f}" '
                   f'y2="{y(centre):.2f}" stroke="#e8e8e2" stroke-width="1"/>')

        # panel caption
        landscape_top, landscape_bot = centre + DISPLAY.height / 2, centre - DISPLAY.height / 2
        portrait_top, portrait_bot = centre + DISPLAY.width / 2, centre - DISPLAY.width / 2
        out.append(_text(px + fridge_px / 2, y(fridge_height) - 30, f"neck {neck:.0f} mm",
                         size=13, weight="bold"))
        out.append(_text(px + fridge_px / 2, y(fridge_height) - 16,
                         f"screen centre {centre:.0f} mm", size=10, fill="#2e9e5b", weight="bold"))
        lines = [
            f"landscape  {landscape_bot:.0f} – {landscape_top:.0f} mm",
            f"portrait   {portrait_bot:.0f} – {portrait_top:.0f} mm",
            ("portrait top ABOVE fridge" if portrait_top > fridge_height
             else f"portrait top {fridge_height - portrait_top:.0f} mm below fridge top"),
            ("centre in comfort band" if comfort_low <= centre <= comfort_high
             else f"centre {abs(centre - comfort_high):.0f} mm above band"
             if centre > comfort_high else f"centre {abs(comfort_low - centre):.0f} mm below band"),
        ]
        for i, line in enumerate(lines):
            colour = "#b00020" if ("ABOVE" in line or "above band" in line or "below band" in line) else "#444"
            out.append(_text(px + fridge_px / 2, y(0) + 22 + i * 13, line, size=9, fill=colour))

    # --- silhouettes -----------------------------------------------------------------
    for person, colour, offset in ((SHORT, "#1a5fb4", -132.0), (TALL, "#8b5e00", -108.0)):
        sx = margin_l + offset
        head_r = person.stature_mm * 0.043 * scale
        out.append(f'<line x1="{sx:.2f}" y1="{y(0):.2f}" x2="{sx:.2f}" y2="{y(person.stature_mm):.2f}" '
                   f'stroke="{colour}" stroke-width="2.4" stroke-opacity="0.55"/>')
        out.append(f'<circle cx="{sx:.2f}" cy="{y(person.stature_mm) + head_r:.2f}" r="{head_r:.2f}" '
                   f'fill="none" stroke="{colour}" stroke-width="2" stroke-opacity="0.55"/>')
        out.append(_text(sx, y(person.stature_mm) - 8, person.label, size=9, fill=colour, weight="bold"))

    out.append(_text(40, canvas_h - 52,
                     "Solid black = landscape. Dashed red = portrait. Green band = heights comfortable for BOTH "
                     "statures (taller person's elbow to shorter person's eye).",
                     size=9.5, anchor="start", fill="#333"))
    out.append(_text(40, canvas_h - 36,
                     "Screen centre = VESA centre = body centre, so it does not move between orientations — "
                     "one drop serves both. Portrait simply extends further above and below it.",
                     size=9.5, anchor="start", fill="#333"))
    out.append(_text(40, canvas_h - 20,
                     "Eye/elbow heights derived from stature (eye 0.936, elbow 0.630). Fridge height is the "
                     "published LG figure — measure yours before committing.",
                     size=9.5, anchor="start", fill="#777"))
    out.append("</svg>")

    path.write_text("\n".join(out), encoding="utf-8")
    LOG.info("Wrote %s (%d panels)", path, len(necks))


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render a neck-length (drop) sweep against standing ergonomics.")
    p.add_argument("--necks", type=float, nargs="+", default=[150.0, 230.0, 310.0, 390.0],
                   help="candidate neck lengths in mm, one panel each")
    p.add_argument("--fridge-height", type=float, default=LG_FRIDGE_HEIGHT_MM,
                   help="MEASURE yours; default is LG's published 70.5 in")
    p.add_argument("--body-height", type=float, default=BracketParams().body_h)
    p.add_argument("--body-width", type=float, default=BracketParams().body_w)
    p.add_argument("--out", type=Path, default=Path("ergonomics_sweep.svg"))
    p.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = p.parse_args(argv)
    configure_logging(args.log_level)

    params = BracketParams(body_h=args.body_height, body_w=args.body_width)
    LOG.info("Fridge height %.0f mm; sweeping necks %s", args.fridge_height,
             [f"{n:.0f}" for n in args.necks])
    for neck in args.necks:
        centre = screen_centre_height(args.fridge_height, neck, params.body_h)
        LOG.info("neck %6.1f mm -> screen centre %.0f mm; landscape %.0f-%.0f; portrait %.0f-%.0f",
                 neck, centre, centre - DISPLAY.height / 2, centre + DISPLAY.height / 2,
                 centre - DISPLAY.width / 2, centre + DISPLAY.width / 2)
    render(args.out, args.necks, params, args.fridge_height)
    return 0


if __name__ == "__main__":
    sys.exit(main())
