#!/usr/bin/env python3
"""The two cut parts of the hook+feet design, in SendCutSend's accepted form.

Same rules as every other DXF here: millimetres ($INSUNITS = 4), one layer, every
contour closed, and a bend marked by ONE DASHED line spanning only the material it
crosses. A solid line there would be read as a cut.
"""
from __future__ import annotations

import logging
import math
import sys
from pathlib import Path

import ezdxf

from concept_sheet import IN, Assembly
from hybrid import Hybrid

LOG = logging.getLogger("hyb")


def build(h: Hybrid, a: Assembly):
    d = ezdxf.new("R2010", setup=True)
    d.header["$INSUNITS"] = 4
    if "DASHED" not in d.linetypes:
        d.linetypes.add("DASHED", pattern=[6.0, 4.0, -2.0])
    msp = d.modelspace()
    bd = h.bend_deduction
    L, W = h.flat_len, h.body_w
    arm_end = h.arm_reach - bd / 2.0                 # bend centre
    neck_end = h.arm_reach + h.neck - bd             # where the body starts
    aw, cx = h.arm_w / 2.0, W / 2.0

    # ONE closed outline: narrow arm+neck, then the wider body. A stepped rectangle.
    msp.add_lwpolyline([
        (0.0, cx - aw), (neck_end, cx - aw), (neck_end, 0.0), (L, 0.0),
        (L, W), (neck_end, W), (neck_end, cx + aw), (0.0, cx + aw),
    ], close=True)

    # bend marker, spanning only the material it crosses
    msp.add_line((arm_end, cx - aw), (arm_end, cx + aw), dxfattribs={"linetype": "DASHED"})

    body_top_flat = neck_end
    vesa_flat = body_top_flat + h.body / 2.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            msp.add_circle((vesa_flat + sy * a.vesa / 2.0, cx + sx * a.vesa / 2.0),
                           a.vesa_hole_dia / 2.0)
    for sgn in (1, -1):
        vy = vesa_flat + sgn * a.vent_r
        r = a.vent_wid / 2.0
        b = math.tan(math.pi / 8)
        x0, y0, ww, hh = vy - a.vent_len / 2.0, cx - r, a.vent_len, a.vent_wid
        msp.add_lwpolyline([(x0 + r, y0, 0), (x0 + ww - r, y0, b), (x0 + ww, y0 + r, 0),
                            (x0 + ww, y0 + hh - r, b), (x0 + ww - r, y0 + hh, 0),
                            (x0 + r, y0 + hh, b), (x0, y0 + hh - r, 0), (x0, y0 + r, b)],
                           format="xyb", close=True)

    bolt_flat = L - h.bolt_edge_margin
    for sx in (-1, 1):
        msp.add_circle((bolt_flat, cx + sx * h.strut_spacing / 2.0), a.plate_bolt_dia / 2.0)
    return d, L, W, bolt_flat


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    h, a = Hybrid(), Assembly()
    Path("dxf").mkdir(exist_ok=True)

    doc, L, W, bolt = build(h, a)
    doc.saveas("dxf/H_hook_plate.dxf")
    LOG.info(f"dxf/H_hook_plate.dxf  {L:.2f} x {W:.0f}, 1 bend")
    LOG.info(f"  strut bolts at flat {bolt:.2f}, {L - bolt:.2f} from the bottom edge")
    LOG.info(f"  needs >= {a.plate_edge:.2f} -> {'OK' if L - bolt >= a.plate_edge else 'FAIL'}")
    LOG.info(f"  bolt to strut-spacing {h.strut_spacing:.0f}, plate {W:.0f} wide -> "
             f"{(W - h.strut_spacing) / 2:.1f} mm of plate outboard of each hole")

    # No foot DXF here on purpose. Moving the strut bolts off the magnets landed them on the
    # clamped-strut design's own spacing, so the FOOT and LOWER CLAMP of that design are the
    # fallback kit unchanged -- see generate_parts.py, B_foot.dxf and A_clamp_bar.dxf.
    LOG.info(f"  magnet-to-bolt clearance {h.magnet_to_bolt:.2f}, needs "
             f">= {h.magnet_to_bolt_needed:.2f} -> "
             f"{'OK' if h.magnet_to_bolt >= h.magnet_to_bolt_needed else 'FAIL'}")
    LOG.info(f"  foot + lower clamp are the clamp design's parts, {a.foot_width:.2f} wide, "
             f"NOT new")
    return 0


if __name__ == "__main__":
    sys.exit(main())
