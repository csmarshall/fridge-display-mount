#!/usr/bin/env python3
"""SKETCH: what the bottom of the hook design would look like IF the hook proves unstable.

This is deliberately not a fabrication package. The only thing that has to be right NOW is the
PLATE, because the plate gets cut now and the holes cannot be added later. Everything below the
plate is a contingency Charles would build and secure in place himself, and it is drawn to show
the arrangement and the clearances, not to be sent to a cutter.

Two views: the bottom end looking AT the side panel, and the same end looking ALONG it.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from concept_sheet import (IN, INK, MUTED, RULE, PAPER, OK, BAD, WARN,
                           C_STEEL, C_STRUT, C_PLATE, Assembly, _t, _wrap)
import json

from hybrid import PLATE_JSON, Hybrid, costed, structural

LOG = logging.getLogger("sketch")
BAND = "#1b6ea8"
FLOOR = "#b9a184"
FRIDGE = "#3a3734"


def _para(x, y, text, limit=74, size=10.4, lead=13.0, fill=MUTED, weight="normal"):
    return [_t(x, y + i * lead, ln, size, anchor="start", fill=fill, weight=weight)
            for i, ln in enumerate(_wrap(text, limit))]


def _panel(x, y, w, h, title, colour=INK):
    return [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="7" fill="#fff" '
            f'stroke="{RULE}" stroke-width="1"/>',
            _t(x + 16, y + 24, title, 12.5, anchor="start", weight="bold", fill=colour)]


def render(path: Path, h: Hybrid, a: Assembly) -> None:
    W, H = 1560, 1080
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<rect width="{W}" height="26" fill="{BAND}"/>',
         _t(W / 2, 18, "SKETCH — CONTINGENCY ONLY. Not a fabrication drawing; nothing here "
                       "is cut unless the hook proves unstable.", 11.5, fill="#fff",
            weight="bold"),
         _t(40, 60, "IF THE HOOK NEEDS HELP — THE BOTTOM END", 21, anchor="start",
            weight="bold"),
         _t(40, 82, "The hook carries the display on its own. This is the support that gets "
                    "added underneath it only if that turns out to be too lively.", 12.5,
            anchor="start", fill=MUTED)]

    # ---------------------------------------------------------------- the one thing that is real
    o.extend(_panel(40, 104, 1480, 128, "THE ONLY PART OF THIS THAT HAS TO BE RIGHT NOW", BAD))
    rows = sorted(h.bolt_rows)
    o.extend(_para(56, 152,
                   f"Four Ø8.5 holes in the plate: two rows at {a.strut_spacing:.2f} centres, "
                   f"{rows[0]:.2f} and {rows[-1]:.2f} above its bottom edge, bracketing the VESA. "
                   f"They cost nothing to add and cannot be added once the plate is cut. "
                   f"Everything else on this sheet is bought or cut later, and only if needed.",
                   176, size=11.0, lead=15.0, fill=INK))
    o.extend(_para(56, 190,
                   f"They sit at {a.strut_spacing:.2f}, NOT the hook's 246 mm magnet spacing. "
                   f"At 246 a bolt centre falls 14.27 mm from a magnet centre against a "
                   f"{h.magnet_disc / 2:.2f} mm disc radius — the plate could take magnets "
                   f"or struts, never both. The rows are the lowest and highest slots of a "
                   f"{h.strut_ft:.0f} ft strut that clear every magnet face, window and hole — "
                   f"the hook generator checks that and refuses to write otherwise.",
                   176, size=11.0, lead=15.0))

    # This is a detail of the BOTTOM END, so it is cropped to it. Showing the whole
    # appliance made the two parts the sheet is about a 60 px sliver on the floor.
    sc = 1.5
    base = 862.0                     # floor line in svg y
    view_top_mm = 320.0              # crop height; the fridge continues above

    def Y(mm):
        return base - mm * sc

    def crop_break(x0, x1, yy, fill):
        """Zigzag along the top of a cropped body, so the crop reads as a crop."""
        n, amp = 26, 7.0
        pts = " ".join(f"{x0 + (x1 - x0) * i / n:.1f},{yy + (amp if i % 2 else -amp):.1f}"
                       for i in range(n + 1))
        return (f'<polyline points="{pts}" fill="none" stroke="{PAPER}" stroke-width="7"/>'
                f'<polyline points="{pts}" fill="none" stroke="{fill}" stroke-width="2.4"/>')


    def floor_and_labels(px, pw, cx, items):
        """Floor line, then a label column on the right with leaders. No two labels collide."""
        out = [f'<line x1="{px + 20:.1f}" y1="{base:.1f}" x2="{px + pw - 210:.1f}" '
               f'y2="{base:.1f}" stroke="{INK}" stroke-width="2"/>',
               f'<rect x="{px + 20:.1f}" y="{base:.1f}" width="{pw - 230:.1f}" height="30" '
               f'fill="{FLOOR}" opacity="0.32"/>']
        lx = px + pw - 196
        for k, (lab, yy, col, txt) in enumerate(items):
            ly = 430 + k * 118
            # dogleg, and every segment stays LEFT of the text column -- a leader that runs
            # diagonally to the label ends up drawn straight through the words.
            out.append(f'<path d="M{cx:.1f} {yy:.1f} L{lx - 26:.1f} {yy:.1f} '
                       f'L{lx - 26:.1f} {ly - 4:.1f} L{lx - 8:.1f} {ly - 4:.1f}" fill="none" '
                       f'stroke="{col}" stroke-width="1"/>')
            out.append(_t(lx, ly, lab, 10.8, anchor="start", fill=col, weight="bold"))
            out.extend(_para(lx, ly + 15, txt, 25, size=9.3, lead=11.5))
        return out

    # ================================================================= looking AT the side panel
    o.extend(_panel(40, 240, 720, 700,
                    "LOOKING AT THE SIDE PANEL — the face the display hangs on"))
    cx1 = 300.0

    def X1(mm):
        return cx1 + mm * sc

    o.append(f'<rect x="{X1(-145):.1f}" y="{Y(view_top_mm):.1f}" width="{290 * sc:.1f}" '
             f'height="{(Y(a.base_gap) - Y(view_top_mm)):.1f}" fill="{FRIDGE}"/>')
    o.append(crop_break(X1(-145), X1(145), Y(view_top_mm), FRIDGE))
    o.append(_t(cx1, Y(view_top_mm) + 34, "FRIDGE — side panel, continues above", 10.0,
                fill="#cfd4d8", weight="bold"))
    hw = a.strut_width / 2.0
    for s_ in (-a.strut_spacing / 2, a.strut_spacing / 2):
        o.append(f'<rect x="{X1(s_ - hw):.1f}" y="{Y(view_top_mm - 30):.1f}" '
                 f'width="{a.strut_width * sc:.1f}" '
                 f'height="{(Y(a.base_gap + 95) - Y(view_top_mm - 30)):.1f}" fill="{C_STRUT}" '
                 f'stroke="{INK}" stroke-width="0.9"/>')
    o.append(f'<rect x="{X1(-a.clamp_width / 2):.1f}" y="{Y(a.base_gap) - 6:.1f}" '
             f'width="{a.clamp_width * sc:.1f}" height="12" rx="2" fill="{C_STEEL}" '
             f'stroke="{INK}" stroke-width="0.9"/>')
    for s_ in (-a.strut_spacing / 2, a.strut_spacing / 2):
        o.append(f'<rect x="{X1(s_ - a.foot_width / 2):.1f}" y="{base - 11:.1f}" '
                 f'width="{a.foot_width * sc:.1f}" height="11" fill="{WARN}" stroke="{INK}" '
                 f'stroke-width="1"/>')
    o.extend(floor_and_labels(40, 720, X1(a.clamp_width / 2), [
        ("LOWER CLAMP  x1", Y(a.base_gap), OK,
         f"one piece, {a.clamp_width:.0f} wide, spanning both struts. One bolt through it "
         f"picks up the foot too."),
        (f"FOOT  x{a.n_feet}", base - 5, WARN,
         f"one per strut, {a.foot_width:.0f} wide. Shares the lower clamp\u2019s bolts — "
         f"clamp leg, foot leg, strut web, nut. Unchanged part."),
    ]))
    o.append(f'<line x1="{X1(-a.strut_spacing / 2):.1f}" y1="{base + 48:.1f}" '
             f'x2="{X1(a.strut_spacing / 2):.1f}" y2="{base + 48:.1f}" stroke="{INK}" '
             f'stroke-width="1.2"/>')
    for xx in (X1(-a.strut_spacing / 2), X1(a.strut_spacing / 2)):
        o.append(f'<line x1="{xx:.1f}" y1="{base + 43:.1f}" x2="{xx:.1f}" y2="{base + 53:.1f}" '
                 f'stroke="{INK}" stroke-width="1.2"/>')
    o.append(_t(cx1, base + 44, f"strut centres {a.strut_spacing:.2f}", 9.8, weight="bold"))

    # ================================================================== looking ALONG the panel
    o.extend(_panel(800, 240, 720, 700, "LOOKING ALONG IT — how it secures"))
    cx2 = 1035.0

    def X2(mm):
        return cx2 + mm * sc

    o.append(f'<rect x="{X2(30):.1f}" y="{Y(view_top_mm):.1f}" width="{130 * sc:.1f}" '
             f'height="{(Y(a.base_gap) - Y(view_top_mm)):.1f}" fill="{FRIDGE}"/>')
    o.append(crop_break(X2(30), X2(160), Y(view_top_mm), FRIDGE))
    o.append(_t(X2(95), Y(view_top_mm) + 34, "FRIDGE, continues above", 10.0, fill="#cfd4d8",
                weight="bold"))
    o.append(f'<rect x="{X2(0):.1f}" y="{Y(view_top_mm - 30):.1f}" '
             f'width="{a.strut_depth * sc:.1f}" '
             f'height="{(Y(a.base_gap + 95) - Y(view_top_mm - 30)):.1f}" fill="{C_STRUT}" '
             f'stroke="{INK}" stroke-width="0.9"/>')
    # lower clamp: long leg UNDER the fridge, short leg down beside the strut
    o.append(f'<rect x="{X2(0):.1f}" y="{Y(a.base_gap) - 6:.1f}" '
             f'width="{a.clamp_leg * sc:.1f}" height="12" fill="{C_STEEL}" stroke="{INK}" '
             f'stroke-width="0.9"/>')
    # The short leg runs UP the side alongside the strut -- the lower clamp is the top clamp
    # FLIPPED. It had been drawn running DOWN, which put it through the floor and made the
    # elevator bolts look like they anchored into the floor rather than through the strut.
    o.append(f'<rect x="{X2(-7):.1f}" '
             f'y="{Y(a.base_gap) - 6 - a.clamp_short * sc:.1f}" width="7" '
             f'height="{a.clamp_short * sc:.1f}" fill="{C_STEEL}" stroke="{INK}" '
             f'stroke-width="0.9"/>')
    # the bolt, THROUGH clamp leg + foot leg + strut web, nutted inside the channel
    bz = Y(a.base_gap) - 6 - a.clamp_short * sc * 0.55
    o.append(f'<line x1="{X2(-11):.1f}" y1="{bz:.1f}" x2="{X2(a.strut_depth + 6):.1f}" '
             f'y2="{bz:.1f}" stroke="{BAD}" stroke-width="2.2"/>')
    # to the LEFT of the bolt: everything right of X2(30) is the dark fridge block
    o.append(_t(X2(-16), bz - 4, "ELEVATOR BOLT", 9.0, anchor="end", fill=BAD, weight="bold"))
    o.append(_t(X2(-16), bz + 7, "through clamp leg + foot leg + web,", 8.4, anchor="end",
                fill=BAD))
    o.append(_t(X2(-16), bz + 17, "nut INSIDE the channel", 8.4, anchor="end", fill=BAD))
    # foot: rise beside the strut, long leg OUTBOARD onto the floor
    o.append(f'<rect x="{X2(-a.foot_leg):.1f}" y="{base - 11:.1f}" '
             f'width="{a.foot_leg * sc:.1f}" height="11" fill="{WARN}" stroke="{INK}" '
             f'stroke-width="1"/>')
    o.append(f'<rect x="{X2(0):.1f}" y="{base - a.foot_rise * sc:.1f}" width="8" '
             f'height="{a.foot_rise * sc:.1f}" fill="{WARN}" stroke="{INK}" stroke-width="1"/>')
    o.extend(floor_and_labels(800, 720, X2(a.clamp_leg), [
        (f"CLAMP LEG {a.clamp_leg:.0f}, UNDER the fridge", Y(a.base_gap), OK,
         "slides into the toe space and is secured there. The appliance's own 229 lb is what "
         "it pulls against."),
        (f"FOOT LEG {a.foot_leg:.0f}, OUTBOARD", base - 6, WARN,
         "turns away from the fridge onto the floor — it is what stops the bottom "
         "kicking out."),
    ]))
    o.append(f'<line x1="{X2(30):.1f}" y1="{Y(a.base_gap):.1f}" x2="{X2(166):.1f}" '
             f'y2="{Y(a.base_gap):.1f}" stroke="{BAD}" stroke-width="0.9" '
             f'stroke-dasharray="5 4"/>')
    o.append(_t(X2(166), Y(a.base_gap) + 16, f"underside {a.base_gap:.0f}", 9.0,
                anchor="start", fill=BAD))

    # ------------------------------------------------------------------------------ read this
    o.extend(_panel(40, 960, 1480, 92, "WHAT THIS SKETCH IS FOR", BAND))
    o.extend(_para(56, 1004,
                   "It is the fallback. The hook is the design; this gets built only if the "
                   "hook is too lively in use. Because the bolt holes had to move off the "
                   f"magnets, they landed on the clamped-strut design's {a.strut_spacing:.2f} "
                   f"spacing — so the FOOT and LOWER CLAMP are that design's parts "
                   f"unchanged. The contingency needs no new part designed, only cut.",
                   184, size=10.8, lead=15.0, fill=INK))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("hybrid_sketch.svg"))
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(message)s")
    h = Hybrid.from_plate_json()
    hook = json.loads(PLATE_JSON.read_text(encoding="utf-8"))
    render(args.out, h, Assembly())
    render_overview(args.out.with_name('hybrid_overview.svg'), h, Assembly(), hook)
    return 0




# ==============================================================================================
NOW = "#1b6ea8"          # bought and cut in the first order
LATER = "#c8791a"        # bought ONLY if the arm + magnets prove too lively


def render_overview(path: Path, h: Hybrid, a: Assembly, hook: dict) -> None:
    """The whole third design, colour-split by WHEN it gets bought.

    The point of the sheet is the split, not the geometry: everything blue is in the first order
    whatever happens, everything amber is a later purchase that may never happen.
    """
    W, H = 1560, 1120
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<rect width="{W}" height="26" fill="{NOW}"/>',
         f'<rect x="{W/2:.0f}" width="{W/2:.0f}" height="26" fill="{LATER}"/>',
         _t(W / 4, 18, "BUY NOW — the arm + magnets design", 11.5, fill="#fff",
            weight="bold"),
         _t(3 * W / 4, 18, "BUY ONLY IF THAT IS TOO LIVELY — the support",
            11.5, fill="#fff", weight="bold"),
         _t(40, 60, "THE THIRD DESIGN — ONE PLATE, TWO WAYS TO HOLD IT UP", 21,
            anchor="start", weight="bold"),
         _t(40, 82, "The arm hooks over the fridge top and the magnets hold it flat. If that is "
                    "not steady enough in use, struts drop from the same plate to the floor. "
                    "Nothing about the plate changes.", 12.5, anchor="start", fill=MUTED)]

    sc = 0.42
    base = 952.0

    def Y(mm):
        return base - mm * sc

    # ------------------------------------------------------------------ full elevation, at left
    o.extend(_panel(40, 104, 640, 906,
                    "THE WHOLE THING — looking at the side panel, true scale"))
    ox = 272.0

    def X(mm):
        return ox + mm * sc

    o.append(f'<line x1="{X(-190):.1f}" y1="{base:.1f}" x2="{X(700):.1f}" y2="{base:.1f}" '
             f'stroke="{INK}" stroke-width="2"/>')
    o.append(f'<rect x="{X(-190):.1f}" y="{base:.1f}" width="{890 * sc:.1f}" height="26" '
             f'fill="{FLOOR}" opacity="0.32"/>')
    # fridge case + hinge cover
    o.append(f'<rect x="{X(0):.1f}" y="{Y(a.fridge_h):.1f}" width="{a.fridge_d * sc:.1f}" '
             f'height="{(base - Y(a.fridge_h)):.1f}" fill="{FRIDGE}"/>')
    o.append(f'<rect x="{X(a.clear_window):.1f}" y="{Y(a.fridge_h + 36.5):.1f}" '
             f'width="{a.hinge_cover * sc:.1f}" height="{36.5 * sc:.1f}" fill="#4c4842"/>')
    # clear of the neck, which runs to c + arm_w/2
    o.append(_t(X(a.fridge_d - 14), Y(a.fridge_h) + 32, "SAMSUNG RS23A500ASR", 9.6,
                anchor="end", fill="#cfd4d8", weight="bold"))
    o.append(_t(X(a.fridge_d - 14), Y(a.fridge_h) + 45, "counter-depth, 610 deep",
                8.6, anchor="end", fill="#9aa1a7"))
    o.append(_t(X(a.clear_window + a.hinge_cover / 2), Y(a.fridge_h + 36.5) - 6, "hinge cover",
                8.4, fill=MUTED))

    c = a.strut_centre
    # ---- LATER: struts, feet, lower clamp
    for s_ in (c - a.strut_spacing / 2, c + a.strut_spacing / 2):
        o.append(f'<rect x="{X(s_ - a.strut_width / 2):.1f}" y="{Y(h.strut_len):.1f}" '
                 f'width="{a.strut_width * sc:.1f}" '
                 f'height="{(base - Y(h.strut_len)):.1f}" fill="#e8dcc9" stroke="{LATER}" '
                 f'stroke-width="1.4"/>')
        o.append(f'<rect x="{X(s_ - a.foot_width / 2):.1f}" y="{base - 8:.1f}" '
                 f'width="{a.foot_width * sc:.1f}" height="8" fill="{LATER}"/>')
    o.append(f'<rect x="{X(c - a.clamp_width / 2):.1f}" y="{Y(a.base_gap) - 5:.1f}" '
             f'width="{a.clamp_width * sc:.1f}" height="9" fill="{LATER}"/>')

    # ---- NOW: the bracket -- arm over the top, neck down, body behind the display
    aw = a.bracket_t * sc + 2.2
    o.append(f'<rect x="{X(c - h.arm_w / 2):.1f}" y="{Y(a.fridge_h) - aw:.1f}" '
             f'width="{h.arm_w * sc:.1f}" height="{aw:.1f}" fill="{NOW}"/>')
    # The NECK is seen face-on in this view, so it is arm_w wide -- not a hairline. It stops at
    # the TOP of the body, not at the body's bottom edge.
    body_top = h.body_bottom + h.body
    o.append(f'<rect x="{X(c - h.arm_w / 2):.1f}" y="{Y(a.fridge_h):.1f}" '
             f'width="{h.arm_w * sc:.1f}" '
             f'height="{(Y(body_top) - Y(a.fridge_h)):.1f}" fill="{NOW}" opacity="0.55"/>')
    o.append(f'<rect x="{X(c - h.body_w / 2):.1f}" y="{Y(h.body_bottom + h.body):.1f}" '
             f'width="{h.body_w * sc:.1f}" height="{h.body * sc:.1f}" fill="{NOW}" '
             f'opacity="0.30" stroke="{NOW}" stroke-width="1.4"/>')
    # the display, dashed, for scale
    o.append(f'<rect x="{X(c - a.display_w / 2):.1f}" '
             f'y="{Y(a.screen_centre + a.display_h / 2):.1f}" '
             f'width="{a.display_w * sc:.1f}" height="{a.display_h * sc:.1f}" rx="3" '
             f'fill="none" stroke="{INK}" stroke-width="1.2" stroke-dasharray="7 5"/>')
    o.append(_t(X(c), Y(a.screen_centre) + 4, "display, 24 in portrait", 9.0, fill=INK))

    # plate bottom and strut top are only 43 mm apart, so they go on OPPOSITE sides
    LEVELS = [(a.fridge_h, f"fridge top {a.fridge_h:.0f}", "left", MUTED),
              (h.body_bottom, f"plate bottom {h.body_bottom:.0f}", "left", NOW),
              (h.strut_len, f"strut top {h.strut_len:.0f} \u2014 {h.strut_ft:.0f} ft stock", "right", LATER)]
    for mm, lab, side, col in LEVELS:
        o.append(f'<line x1="{X(-190):.1f}" y1="{Y(mm):.1f}" x2="{X(a.fridge_d + 120):.1f}" '
                 f'y2="{Y(mm):.1f}" stroke="{col}" stroke-width="0.6" '
                 f'stroke-dasharray="4 4"/>')
        if side == "left":
            o.append(_t(X(-188), Y(mm) - 5, lab, 8.8, anchor="start", fill=col))
        else:
            o.append(_t(X(a.fridge_d + 118), Y(mm) + 12, lab, 8.8, anchor="end", fill=col))
    # the two bolt rows, drawn across both struts, and a callout off the upper one
    bolt_rows = sorted(h.bolt_rows)
    for r in bolt_rows:
        yy = Y(h.body_bottom + r)
        o.append(f'<line x1="{X(c - a.strut_spacing / 2 - 14):.1f}" y1="{yy:.1f}" '
                 f'x2="{X(c + a.strut_spacing / 2 + 14):.1f}" y2="{yy:.1f}" stroke="{BAD}" '
                 f'stroke-width="2.2"/>')
    ox_lbl = X(a.fridge_d + 16)
    o.append(f'<path d="M{X(c + a.strut_spacing / 2 + 16):.1f} {Y(h.body_bottom + bolt_rows[-1]):.1f} '
             f'L{ox_lbl - 6:.1f} {Y(h.body_bottom + bolt_rows[-1]) + 4:.1f}" fill="none" '
             f'stroke="{BAD}" stroke-width="0.9"/>')
    ly = Y(h.body_bottom + bolt_rows[-1]) + 7
    o.append(_t(ox_lbl, ly, f"{len(bolt_rows)} bolt rows, {bolt_rows[0]:.0f} and {bolt_rows[-1]:.0f}", 9.0,
                anchor="start", fill=BAD, weight="bold"))
    o.append(_t(ox_lbl, ly + 12, "above the plate edge,", 8.6, anchor="start", fill=BAD))
    o.append(_t(ox_lbl, ly + 23, "bracketing the VESA —", 8.6, anchor="start", fill=BAD))
    o.append(_t(ox_lbl, ly + 34, "the plate is a beam", 8.6, anchor="start", fill=BAD))
    o.append(_t(ox_lbl, ly + 45, "between them", 8.6, anchor="start", fill=BAD))

    # ------------------------------------------------------------------------ what you buy when
    o.extend(_panel(700, 104, 820, 470, "WHAT YOU BUY, AND WHEN", INK))
    rows_now, rows_later, total_now, total_later = [], [], 0.0, 0.0
    for nm, src, cost, note in costed(h):
        later = any(k in nm for k in ("STRUT", "FOOT", "LOWER CLAMP"))
        if "MAGNET" in nm:
            later = False
        (rows_later if later else rows_now).append((nm, cost, note))
        if cost:
            if later:
                total_later += cost
            else:
                total_now += cost
    yy = 148.0
    for head, rows, col, tot, blurb in (
            ("IN THE FIRST ORDER", rows_now, NOW, total_now,
             "the plate is cut once and cannot be changed afterwards"),
            ("ONLY IF THE ARM IS TOO LIVELY", rows_later, LATER, total_later,
             "ordinary stock and two cut parts, orderable any time later")):
        o.append(_t(716, yy, head, 12.0, anchor="start", weight="bold", fill=col))
        o.extend(_para(716, yy + 15, blurb, 84, size=9.4))
        yy += 34
        for nm, cost, note in rows:
            o.append(_t(730, yy, nm, 10.4, anchor="start", weight="bold"))
            o.append(_t(1160, yy, "optional" if cost is None else f"${cost:.2f}", 10.2,
                        anchor="end", fill=MUTED if cost is None else INK, weight="bold"))
            o.extend(_para(1180, yy - 3, note, 44, size=8.6, lead=10.0)[:2])
            yy += 34
        o.append(f'<line x1="716" y1="{yy - 12:.1f}" x2="1500" y2="{yy - 12:.1f}" '
                 f'stroke="{RULE}" stroke-width="0.8"/>')
        o.append(_t(730, yy + 6, "subtotal", 10.4, anchor="start", fill=col, weight="bold"))
        o.append(_t(1160, yy + 6, f"${tot:.2f}", 12.0, anchor="end", fill=col, weight="bold"))
        yy += 44

    # ------------------------------------------------------------------------- the one caveat
    o.extend(_panel(700, 596, 820, 408, "THE ONE THING THE FIRST ORDER HAS TO GET RIGHT", BAD))
    s2 = structural(h, "struts", hook["engineering"]["plate_mass_kg"])
    o.extend(_para(716, 644,
                   f"Four Ø8.5 holes in the plate: two rows at {a.strut_spacing:.2f} centres, "
                   f"{bolt_rows[0]:.2f} and {bolt_rows[-1]:.2f} above its bottom edge. If the struts are "
                   f"never bought they are four unused holes hidden behind the display. If they "
                   f"are bought and the holes are not there, the plate is scrap.", 88, size=10.6,
                   lead=14.0, fill=INK))
    o.extend(_para(716, 718,
                   f"They are NOT at the hook's 246 mm magnet spacing. At 246 a bolt centre "
                   f"lands {14.27:.2f} mm from a magnet centre against a "
                   f"{h.magnet_disc / 2:.2f} mm disc — the bolts would sit UNDER the "
                   f"magnets and the plate could do one job or the other, never both. The plate "
                   f"is the HOOK GENERATOR's output with these holes added; it checks every bolt "
                   f"against every magnet face, window and hole and refuses to write otherwise.",
                   88, size=10.6, lead=14.0))
    o.extend(_para(716, 806,
                   f"{h.strut_ft:.0f} ft struts, not 4. A 4 ft strut put ONE slot row 17.7 mm "
                   f"above the plate edge and the plate cantilevered 144 mm to the VESA: 0.876 mm "
                   f"of screen-edge movement under a 5 lb press, four times the feel-rigid band. "
                   f"{h.strut_ft:.0f} ft puts {len(h.candidate_rows)} rows inside the plate; the "
                   f"lowest and highest clear ones bracket the VESA and the same press now moves "
                   f"the edge {s2.screen_edge_mm:.3f} mm. The strut stands "
                   f"{h.strut_above_plate:.0f} mm above the plate, behind the display. If the "
                   f"mounting height moves, the rows are re-picked and the generator refuses if "
                   f"they no longer bracket.", 88, size=10.6, lead=14.0))
    o.extend(_para(716, 894,
                   "The foot and lower clamp are the clamped-strut design's parts, unchanged — "
                   "nothing new gets designed for the fallback, only cut.", 88, size=10.6,
                   lead=14.0, fill=OK))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — $%.2f now, $%.2f only if needed", path, total_now, total_later)


if __name__ == "__main__":
    sys.exit(main())
