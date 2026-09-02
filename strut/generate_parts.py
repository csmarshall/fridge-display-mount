#!/usr/bin/env python3
"""Emit one DXF per cut part, in the form SendCutSend's uploader actually accepts.

Their rules, carried over from the hook design where they were established against the live app:
  - millimetres ($INSUNITS = 4)
  - a single layer (0)
  - every contour CLOSED
  - a bend marked by ONE DASHED LINE on the bend centre, spanning the bend length. A SOLID line
    there would be read as a cut and would slice the part in half.
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path
from typing import Sequence

import ezdxf

from concept_sheet import Assembly
import bom as B

LOG = logging.getLogger("parts")


def _doc():
    d = ezdxf.new("R2010", setup=True)
    d.header["$INSUNITS"] = 4                       # millimetres
    if "DASHED" not in d.linetypes:
        d.linetypes.add("DASHED", pattern=[6.0, 4.0, -2.0])
    return d


def _rect(msp, x0, y0, w, h, r=0.0):
    """Closed rectangle, optionally with rounded ends on the short axis."""
    if r <= 0:
        msp.add_lwpolyline([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)],
                           close=True)
        return
    b = math.tan(math.pi / 8)                        # 90 deg arc as a polyline bulge
    pts = [(x0 + r, y0, 0), (x0 + w - r, y0, b), (x0 + w, y0 + r, 0),
           (x0 + w, y0 + h - r, b), (x0 + w - r, y0 + h, 0), (x0 + r, y0 + h, b),
           (x0, y0 + h - r, 0), (x0, y0 + r, b)]
    msp.add_lwpolyline(pts, format="xyb", close=True)


def _slot(msp, cx, cy, length, width):
    r = width / 2.0
    _rect(msp, cx - length / 2.0, cy - r, length, width, r)


def part_clamp(a: Assembly, bd: float):
    d = _doc(); msp = d.modelspace()
    w, h = a.clamp_leg + a.clamp_short - bd, a.clamp_width
    _rect(msp, 0, 0, w, h)
    for sgn in (-1, 1):
        cy = h / 2.0 + sgn * a.strut_spacing / 2.0
        s = 8.38                                     # square hole for the elevator shoulder
        _rect(msp, a.clamp_leg * 0.55 - s / 2, cy - s / 2, s, s)
    msp.add_line((a.clamp_leg - bd / 2.0, 0.0), (a.clamp_leg - bd / 2.0, h),
                 dxfattribs={"linetype": "DASHED"})
    return d, w, h, 1


def part_foot(a: Assembly, bd: float):
    d = _doc(); msp = d.modelspace()
    w, h = a.foot_leg + a.foot_rise - bd, a.foot_width
    _rect(msp, 0, 0, w, h)
    _slot(msp, a.foot_leg * 0.55, h / 2.0, a.slot_len, a.plate_bolt_dia + 0.6)
    msp.add_line((a.foot_leg - bd / 2.0, 0.0), (a.foot_leg - bd / 2.0, h),
                 dxfattribs={"linetype": "DASHED"})
    return d, w, h, 1


def part_plate(a: Assembly, bd: float):
    d = _doc(); msp = d.modelspace()
    w, h = a.plate_w, a.plate_h
    _rect(msp, 0, 0, w, h)
    cx, cy = w / 2.0, h / 2.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            msp.add_circle((cx + sx * a.vesa / 2, cy + sy * a.vesa / 2),
                           a.vesa_hole_dia / 2.0)
            msp.add_circle((cx + sx * a.plate_bolt_dx / 2, cy + sy * a.plate_bolt_dy / 2),
                           a.plate_bolt_dia / 2.0)
    for sgn in (1, -1):
        _rect(msp, cx - a.vent_wid / 2, cy + sgn * a.vent_r - a.vent_len / 2,
              a.vent_wid, a.vent_len, a.vent_wid / 2.0)
    return d, w, h, 0


def part_strip(a: Assembly, bd: float):
    d = _doc(); msp = d.modelspace()
    w, h = 20.0, a.plate_bolt_dy + 2 * a.plate_edge
    _rect(msp, 0, 0, w, h)
    for sgn in (-1, 1):
        msp.add_circle((w / 2.0, h / 2.0 + sgn * a.plate_bolt_dy / 2.0),
                       a.plate_bolt_dia / 2.0)
    return d, w, h, 0


BUILDERS = {"A": ("clamp_bar", part_clamp), "B": ("foot", part_foot),
            "C": ("plate", part_plate), "D": ("backing_strip", part_strip)}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", type=Path, default=Path("dxf"))
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args(argv)
    logging.basicConfig(level=args.log_level,
                        format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    a = Assembly()
    bd = B.bend_deduction(a)
    args.outdir.mkdir(parents=True, exist_ok=True)
    fab = {f.tag: f for f in B.fabricated(a, True)}
    for tag, (nm, fn) in BUILDERS.items():
        doc, w, h, bends = fn(a, bd)
        p = args.outdir / f"{tag}_{nm}.dxf"
        doc.saveas(p)
        f = fab[tag]
        ok = abs(w - f.flat_w) < 0.01 and abs(h - f.flat_h) < 0.01
        LOG.info("%s  %-14s %8.2f x %7.2f  %d bend  qty %d  %s",
                 tag, nm, w, h, bends, f.qty,
                 "matches the BOM" if ok else f"MISMATCH vs BOM {f.flat_w:.2f}x{f.flat_h:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
