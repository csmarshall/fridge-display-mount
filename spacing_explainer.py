#!/usr/bin/env python3
"""Why a bigger magnet runs out of plate: the magnet-spacing floor, drawn.

Spacing is centre-to-centre between opposite corner magnets. A bigger disc needs a bigger inset
from the edge, so BOTH spacings shrink as the disc grows. The 240 mm floor is what stops it.
"""
from __future__ import annotations
import argparse, logging, sys
from pathlib import Path
from typing import Sequence
from bracket_common import LOG_LEVELS, configure_logging
import generate_bracket as G
from generate_bracket import BracketParams, MATERIAL

LOG = logging.getLogger("spacing")
INK, MUTED, RULE = "#14181c", "#6b757e", "#c9d1d8"
OK, BAD, DIM = "#0a8f6f", "#b00020", "#0a8f6f"


def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def T(x, y, s, size=10, anchor="middle", fill=INK, weight="normal", rot=0.0):
    tr = f' transform="rotate({rot:.1f} {x:.1f} {y:.1f})"' if rot else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"'
            f'{tr}>{esc(s)}</text>')


def panel(ox, oy, s, p, od, margin, title, sub):
    """One plate with its corner magnets and both spacing dimensions."""
    inset = od / 2 + margin
    spx, spy = p.body_w - 2 * inset, p.body_h - 2 * inset
    floor = p.min_magnet_spacing
    def X(v): return ox + v * s
    def Y(v): return oy + (p.body_h - v) * s
    o = [T(ox, oy - 40, title, 13.5, anchor="start", weight="bold"),
         T(ox, oy - 24, sub, 9.5, anchor="start", fill=MUTED),
         f'<rect x="{X(0):.1f}" y="{Y(p.body_h):.1f}" width="{p.body_w*s:.1f}" '
         f'height="{p.body_h*s:.1f}" rx="{p.outer_fillet*s:.1f}" fill="#f4f6f8" stroke="{INK}" '
         f'stroke-width="1.5"/>']
    # the four corner magnets
    for cx, cy in ((inset, inset), (p.body_w-inset, inset),
                   (inset, p.body_h-inset), (p.body_w-inset, p.body_h-inset)):
        o.append(f'<circle cx="{X(cx):.1f}" cy="{Y(cy):.1f}" r="{od/2*s:.1f}" fill="#7d868d" '
                 f'fill-opacity="0.30" stroke="#5b646b" stroke-width="1.4"/>')
        o.append(f'<circle cx="{X(cx):.1f}" cy="{Y(cy):.1f}" r="2" fill="{INK}"/>')
    def bar(x0, x1, y, val, vertical=False):
        col = OK if val >= floor else BAD
        if vertical:
            o.append(f'<line x1="{y:.1f}" y1="{x0:.1f}" x2="{y:.1f}" y2="{x1:.1f}" '
                     f'stroke="{col}" stroke-width="2"/>')
            for yy in (x0, x1):
                o.append(f'<line x1="{y-5:.1f}" y1="{yy:.1f}" x2="{y+5:.1f}" y2="{yy:.1f}" '
                         f'stroke="{col}" stroke-width="2"/>')
        else:
            o.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" '
                     f'stroke="{col}" stroke-width="2"/>')
            for xx in (x0, x1):
                o.append(f'<line x1="{xx:.1f}" y1="{y-5:.1f}" x2="{xx:.1f}" y2="{y+5:.1f}" '
                         f'stroke="{col}" stroke-width="2"/>')
    # X spacing, drawn across the bottom pair
    ybar = Y(0) + 34
    bar(X(inset), X(p.body_w-inset), ybar, spx)
    o.append(T((X(inset)+X(p.body_w-inset))/2, ybar - 8,
               f"X spacing {spx:.0f}", 11.5, fill=OK if spx >= floor else BAD, weight="bold"))
    # the floor drawn to scale, directly beneath, so the shortfall is visible
    fx0 = (X(inset)+X(p.body_w-inset))/2 - floor*s/2
    o.append(f'<line x1="{fx0:.1f}" y1="{ybar+16:.1f}" x2="{fx0+floor*s:.1f}" y2="{ybar+16:.1f}" '
             f'stroke="{MUTED}" stroke-width="2" stroke-dasharray="5 4"/>')
    o.append(T((X(inset)+X(p.body_w-inset))/2, ybar + 30, f"floor {floor:.0f}", 9.5, fill=MUTED))
    # Y spacing, down the left
    xbar = X(0) - 40
    bar(Y(p.body_h-inset), Y(inset), xbar, spy, vertical=True)
    o.append(T(xbar - 9, (Y(inset)+Y(p.body_h-inset))/2, f"Y spacing {spy:.0f}", 11.5,
               fill=OK if spy >= floor else BAD, weight="bold", rot=-90))
    fy0 = (Y(inset)+Y(p.body_h-inset))/2 - floor*s/2
    o.append(f'<line x1="{xbar-20:.1f}" y1="{fy0:.1f}" x2="{xbar-20:.1f}" y2="{fy0+floor*s:.1f}" '
             f'stroke="{MUTED}" stroke-width="2" stroke-dasharray="5 4"/>')
    o.append(T(xbar - 28, (Y(inset)+Y(p.body_h-inset))/2, f"floor {floor:.0f}", 9.5,
               fill=MUTED, rot=-90))
    # verdict
    vy = Y(0) + 96
    bad = [n for n, v in (("X", spx), ("Y", spy)) if v < floor]
    if bad:
        short = min(spx, spy)
        o.append(T(ox, vy, f"FAILS — {bad[0]} spacing short by {floor-short:.2f} mm",
                   12.5, anchor="start", weight="bold", fill=BAD))
    else:
        o.append(T(ox, vy, "PASSES — both spacings clear the floor", 12.5,
                   anchor="start", weight="bold", fill=OK))
    o.append(T(ox, vy + 17, f"disc O{od:.2f}  ·  edge margin {margin:.2f}  ·  inset {inset:.2f} mm",
               9.5, anchor="start", fill=MUTED))
    return "".join(o)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Draw why the big magnet does not fit.")
    ap.add_argument("--out", type=Path, default=Path("spacing_explainer.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    p = BracketParams()
    IN = 25.4
    cases = [((1+21/32)*IN, 8.0, "3506K66  O42.07", "the part we built on, 8 mm edge margin"),
             ((1+57/64)*IN, 8.0, "3506K67  O48.02", "same 8 mm margin"),
             ((1+57/64)*IN, MATERIAL.min_edge_distance, "3506K67  O48.02",
              f"pushed to the {MATERIAL.min_edge_distance:.2f} mm minimum margin")]
    s = 0.78
    pw = p.body_w * s
    gap = 118.0
    W = 96 + len(cases)*(pw+gap)
    H = p.body_h*s + 330
    oy = 148.0
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}"><rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/>',
         f'<rect x="24" y="22" width="{W-48:.0f}" height="46" fill="{INK}" rx="3"/>',
         T(46, 52, "MAGNET SPACING — WHY THE BIGGER DISC RUNS OUT OF PLATE", 17,
           anchor="start", fill="#fff", weight="bold")]
    for k, (od, m, title, sub) in enumerate(cases):
        o.append(panel(80 + k*(pw+gap), oy, s, p, od, m, title, sub))
    o.append(T(80, H-40, "Spacing is centre-to-centre between opposite corner magnets. A bigger "
                         "disc needs a bigger inset from the edge,", 11, anchor="start"))
    o.append(T(80, H-21, f"so BOTH spacings shrink as the disc grows. The plate is "
                         f"{p.body_w:.0f} wide but only {p.body_h:.0f} tall, so Y always runs out first.",
               11, anchor="start"))
    o.append("</svg>")
    a.out.write_text("\n".join(o), encoding="utf-8")
    for od, m, title, _ in cases:
        i = od/2+m
        LOG.info("%-18s margin %5.2f -> inset %5.2f  X %6.2f  Y %6.2f  %s", title, m, i,
                 p.body_w-2*i, p.body_h-2*i,
                 "OK" if min(p.body_w-2*i, p.body_h-2*i) >= p.min_magnet_spacing else "FAIL")
    LOG.info("Wrote %s", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
