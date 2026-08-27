#!/usr/bin/env python3
"""Plan view of the fridge top: where the arm and the hinge cover meet, or miss.

Looking DOWN on the mounting-side corner of the fridge top. This is the only view in which the
arm/cover clearance is a real, dimensioned thing — the side elevation shows the cover but not the
arm's width, and the frontal elevation shows neither in the right direction.

The governing dimension is `plate_from_rear`. Slide the plate forward and the arm's front edge
walks into the cover; slide it back and it does not. Everything else is fixed.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
import generate_bracket as G
from generate_bracket import BracketParams

LOG = logging.getLogger("hinge")

INK, MUTED, RULE = "#14181c", "#6b757e", "#c9d1d8"
DIM, BAD, OK = "#0a8f6f", "#b00020", "#2e9e5b"
BRACKET, COVER = "#2b3036", "#9aa6ae"

CASE_D = 609.6          # counter-depth case, front to back
DOOR_PROJ = 117.5       # doors stand this far forward of the case


def _t(x, y, s, size=10.0, anchor="middle", fill=INK, weight="normal", rot=0.0):
    tr = f' transform="rotate({rot:.1f} {x:.2f} {y:.2f})"' if rot else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}"{tr}>{s}</text>')


def render(path: Path, p: BracketParams) -> dict:
    """Plan view. x = front-to-back (0 at the REAR), y = inboard from the mounting edge."""
    s = 1.28                                   # px per mm
    inboard_shown = 320.0
    ox, oy = 96.0, 150.0
    W = ox + (CASE_D + DOOR_PROJ) * s + 210.0
    H = oy + inboard_shown * s + 250.0

    def X(mm): return ox + mm * s
    def Y(mm): return oy + mm * s

    arm_rear = p.plate_from_rear + (p.body_h - p.neck_w) / 2.0
    arm_front = arm_rear + p.neck_w
    cover_rear = p.hinge_cover_from_rear
    gap = cover_rear - arm_front
    overlap = max(0.0, -gap)
    # The overlap is a rectangle: how far the arm runs past the cover's rear edge, by how much of
    # the cover's inboard extent the arm actually shares. Both start at the mounting edge, so the
    # shared inboard width is simply the narrower of the two.
    shared_inboard = min(p.neck_w and inboard_shown, p.hinge_cover_inboard, p.arm_len)
    overlap_area = overlap * shared_inboard / 100.0        # cm^2

    BANNER_H = 34.0
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfcfd"/>',
         f'<rect width="{W:.0f}" height="26" fill="#b00020"/>',
         f'<text x="{W/2:.0f}" y="18" font-family="Helvetica,Arial,sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#fff">REFERENCE ONLY — clearance study, not a fabrication drawing</text>',
         _t(ox, 42, "FRIDGE TOP IN PLAN — does the arm meet the hinge cover?", 16,
            anchor="start", weight="bold"),
         _t(ox, 64, "Looking down on the mounting-side corner. The ONLY thing that decides this "
                    "is how far forward the plate sits.", 11, anchor="start", fill=MUTED),
         _t(ox, 82, f"Hinge cover position MEASURED 2026-08-27. Its inboard reach "
                    f"({p.hinge_cover_inboard:.0f} mm) is ASSUMED — it does not change the answer.",
            10, anchor="start", fill=MUTED)]

    # ---- the top surface ------------------------------------------------------------------
    o.append(f'<rect x="{X(0):.1f}" y="{Y(0):.1f}" width="{CASE_D*s:.1f}" '
             f'height="{inboard_shown*s:.1f}" fill="#eef2f5" stroke="{INK}" stroke-width="1.4"/>')
    o.append(f'<rect x="{X(CASE_D):.1f}" y="{Y(0):.1f}" width="{DOOR_PROJ*s:.1f}" '
             f'height="{inboard_shown*s:.1f}" fill="#e3e9ee" stroke="{RULE}" stroke-width="1"/>')
    o.append(_t(X(CASE_D + DOOR_PROJ/2), Y(inboard_shown) + 22, "door", 8.5, fill=MUTED))
    o.append(_t(X(6), Y(14), "REAR", 9.5, anchor="start", fill=MUTED, weight="bold"))
    o.append(_t(X(CASE_D - 6), Y(14), "FRONT", 9.5, anchor="end", fill=MUTED, weight="bold"))
    o.append(_t(ox - 14, Y(inboard_shown/2), "inboard from the mounting edge →", 9.5,
                anchor="middle", fill=MUTED, rot=-90))

    # ---- thirds. The panel is 24 in deep, so thirds are 8 in, and the split turns out to be
    # meaningful rather than arbitrary: rear third free, middle third arm, front third hinge.
    col = CASE_D / 3.0
    for i in range(1, 3):
        o.append(f'<line x1="{X(i*col):.1f}" y1="{Y(-8):.1f}" x2="{X(i*col):.1f}" '
                 f'y2="{Y(inboard_shown + 8):.1f}" stroke="#8e6bd6" stroke-width="1.1" '
                 f'stroke-dasharray="4 4" opacity="0.9"/>')
    for i, nm in enumerate(("REAR THIRD", "MIDDLE THIRD", "FRONT THIRD")):
        o.append(_t(X((i + 0.5) * col), Y(inboard_shown) - 12, nm, 9.0, fill="#6b4fae",
                    weight="bold"))
        o.append(_t(X((i + 0.5) * col), Y(inboard_shown) - 1,
                    f'{col:.0f} mm / {col/25.4:.0f} in', 7.8, fill="#8e6bd6"))

    # ---- the hinge cover ------------------------------------------------------------------
    o.append(f'<rect x="{X(cover_rear):.1f}" y="{Y(0):.1f}" '
             f'width="{(CASE_D + DOOR_PROJ - cover_rear)*s:.1f}" '
             f'height="{p.hinge_cover_inboard*s:.1f}" fill="{COVER}" fill-opacity="0.65" '
             f'stroke="{INK}" stroke-width="1.2"/>')
    o.append(_t(X((cover_rear + CASE_D)/2), Y(p.hinge_cover_inboard/2) + 4, "HINGE COVER",
                10.5, weight="bold", fill="#2b3036"))
    o.append(_t(X((cover_rear + CASE_D)/2), Y(p.hinge_cover_inboard/2) + 18,
                "lifts off / removable", 8.2, fill="#3d474e"))

    # ---- the arm ---------------------------------------------------------------------------
    o.append(f'<rect x="{X(arm_rear):.1f}" y="{Y(0):.1f}" width="{p.neck_w*s:.1f}" '
             f'height="{p.arm_len*s:.1f}" fill="{BRACKET}" fill-opacity="0.86" '
             f'stroke="{INK}" stroke-width="1.4"/>')
    o.append(_t(X(arm_rear + p.neck_w/2), Y(p.arm_len/2) - 4, "ARM", 11, weight="bold", fill="#fff"))
    o.append(_t(X(arm_rear + p.neck_w/2), Y(p.arm_len/2) + 12,
                f"{p.neck_w:.0f} × {p.arm_len:.0f}", 8.6, fill="#cfd8de"))

    # ---- the intersection, drawn dashed whether or not it exists ---------------------------
    band_c = BAD if overlap > 0 else OK
    if overlap > 0:
        o.append(f'<rect x="{X(cover_rear):.1f}" y="{Y(0):.1f}" width="{overlap*s:.1f}" '
                 f'height="{shared_inboard*s:.1f}" fill="{BAD}" fill-opacity="0.30" '
                 f'stroke="{BAD}" stroke-width="1.8" stroke-dasharray="7 4"/>')
        verdict = (f"THEY INTERSECT: {overlap:.0f} × {shared_inboard:.0f} mm "
                   f"= {overlap_area:.0f} cm² of overlap")
    else:
        o.append(f'<rect x="{X(arm_front):.1f}" y="{Y(0):.1f}" width="{max(gap,0.6)*s:.1f}" '
                 f'height="{shared_inboard*s:.1f}" fill="{OK}" fill-opacity="0.22" '
                 f'stroke="{OK}" stroke-width="1.8" stroke-dasharray="7 4"/>')
        verdict = f"NO INTERSECTION — {gap:.1f} mm of clear air between them"

    # dashed guides down both faces of the meeting
    # NB: named guide_c, not col — `col` is the third-of-the-panel width and this loop used to
    # clobber it with a colour string.
    for xm, guide_c in ((arm_front, INK), (cover_rear, "#2b3036")):
        o.append(f'<line x1="{X(xm):.1f}" y1="{Y(-26):.1f}" x2="{X(xm):.1f}" '
                 f'y2="{Y(inboard_shown + 60):.1f}" stroke="{guide_c}" stroke-width="1" '
                 f'stroke-dasharray="6 4" opacity="0.85"/>')

    # ---- fine measurement guides -----------------------------------------------------------
    def dim(x0, x1, y, label, colour=DIM):
        a, b = sorted((X(x0), X(x1)))
        out = [f'<line x1="{a:.1f}" y1="{y:.1f}" x2="{b:.1f}" y2="{y:.1f}" stroke="{colour}" '
               f'stroke-width="0.9"/>']
        for xx in (a, b):
            out.append(f'<line x1="{xx:.1f}" y1="{y-5:.1f}" x2="{xx:.1f}" y2="{y+5:.1f}" '
                       f'stroke="{colour}" stroke-width="0.9"/>')
        # A 6 mm span is ~8 px wide, so a centred label lands on top of its own witness lines.
        # Below a legible width, throw it to the right on a leader instead.
        if b - a < 46:
            out.append(f'<line x1="{b:.1f}" y1="{y:.1f}" x2="{b+26:.1f}" y2="{y:.1f}" '
                       f'stroke="{colour}" stroke-width="0.9"/>')
            out.append(_t(b + 31, y + 3.4, label, 9.0, anchor="start", fill=colour, weight="bold"))
        else:
            out.append(_t((a+b)/2, y - 7, label, 9.0, fill=colour, weight="bold"))
        return "".join(out)

    yb = Y(inboard_shown) + 46
    o.append(dim(0, arm_rear, yb, f"ARM set back {arm_rear:.0f}"))
    o.append(dim(arm_rear, arm_front, yb, f"arm width {p.neck_w:.0f}", INK))
    o.append(dim(arm_front, cover_rear, yb + 34,
                 (f"OVERLAP {overlap:.0f}" if overlap > 0 else f"gap {gap:.1f}"), band_c))
    o.append(dim(0, cover_rear, yb + 68, f"clear window {cover_rear:.0f}"))
    o.append(dim(0, CASE_D, yb + 102, f"case depth {CASE_D:.0f} / 24 in"))
    o.append(_t(ox, yb + 140,
                f"The arm is {p.neck_w:.0f} mm in a {col:.0f} mm column: "
                f"{col - p.neck_w:.1f} mm of total slack, "
                f"{(col - p.neck_w)/2:.1f} mm each side. "
                f"That is the whole margin — it is arithmetic, not an allowance.",
                10.0, anchor="start", fill=MUTED))

    o.append(f'<rect x="{ox:.1f}" y="{H-92:.1f}" width="{W-2*ox+150:.1f}" height="56" '
             f'fill="#fff" stroke="{band_c}" stroke-width="1.6" rx="4"/>')
    o.append(_t(ox + 16, H - 62, verdict, 13, anchor="start", weight="bold", fill=band_c))
    o.append(_t(ox + 16, H - 44,
                f"plate_from_rear = {p.plate_from_rear:.0f} mm. Every {abs(gap):.0f} mm forward "
                f"from here starts an overlap; the cover lifts off, so it is recoverable either way.",
                9.6, anchor="start", fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — arm %.0f-%.0f, cover from %.0f, %s %.0f mm",
             path, arm_rear, arm_front, cover_rear,
             "OVERLAP" if overlap > 0 else "gap", overlap if overlap > 0 else gap)
    return {"arm_rear": arm_rear, "arm_front": arm_front, "cover_rear": cover_rear,
            "gap": gap, "overlap": overlap, "overlap_area_cm2": overlap_area}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("hinge_clearance.svg"))
    ap.add_argument("--plate-from-rear", type=float, default=None,
                    help="override how far forward the plate sits, mm from the rear edge")
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    kw = {} if a.plate_from_rear is None else {"plate_from_rear": a.plate_from_rear}
    render(a.out, BracketParams(**kw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
