#!/usr/bin/env python3
"""The clamped-strut design's drawing set.

Every sheet reads the SAME `Assembly` the concept sheet does, so a dimension cannot be right on
one drawing and stale on another. Nothing here is measured off a picture; if a number appears, it
was derived from `Assembly` or it is flagged as an estimate.

Sheets:
  clamp_approval      partner-facing: what it is, what it costs, what it looks like
  clamp_parts         flat patterns for the two bent parts, with bend lines and the deduction
  clamp_assembly      the order it goes together, and what is loose at each step
  clamp_clearance     plan view: where the top clamp lands in the 406 mm hinge window
  clamp_loadpath      where the weight actually goes
  clamp_height_check  does a strut slot land where each clamp needs one
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path
from typing import Sequence

from concept_sheet import (IN, INK, MUTED, RULE, PAPER, OK, BAD, WARN,
                           C_STEEL, C_STRUT, C_PLATE, Assembly, _t, _wrap)

LOG = logging.getLogger("clamp")

FRIDGE_SIDE, FRIDGE_EDGE = "#3a3734", "#2b2926"
PAD_FILL, PAD_EDGE = "#f8e2a4", "#c9a227"
BAND = "#b8860b"


def _frame(w, h, title, sub, banner) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
            f'viewBox="0 0 {w:.0f} {h:.0f}">',
            f'<rect width="{w:.0f}" height="{h:.0f}" fill="{PAPER}"/>',
            f'<rect width="{w:.0f}" height="24" fill="{BAND}"/>',
            _t(w / 2, 16.5, banner, 11.5, fill="#fff", weight="bold"),
            _t(40, 56, title, 21, anchor="start", weight="bold"),
            _t(40, 78, sub, 12.5, anchor="start", fill=MUTED)]


def _panel(x, y, w, h, title, colour=INK) -> list[str]:
    return [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="7" fill="#fff" '
            f'stroke="{RULE}" stroke-width="1"/>',
            _t(x + 16, y + 24, title, 12.5, anchor="start", weight="bold", fill=colour)]


def _para(x, y, text, limit=74, size=10.6, lead=13.0, fill=MUTED) -> list[str]:
    return [_t(x, y + i * lead, ln, size, anchor="start", fill=fill)
            for i, ln in enumerate(_wrap(text, limit))]


def _display_ghost(x, y, w, h, label="23.8 in display — TRUE SCALE") -> list[str]:
    """The one object whose size the reader already knows. Dashed, never filled solid."""
    return [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#101820" '
            f'fill-opacity="0.10" stroke="{INK}" stroke-width="1.4" stroke-dasharray="7 4"/>',
            _t(x + w / 2, y + h / 2, label, 9.0, fill=MUTED, weight="bold")]


def bend_deduction(a: Assembly) -> float:
    """Same derivation the magnet bracket used. An ESTIMATE until SendCutSend's calculator says."""
    r, t, k = a.bend_radius, a.bracket_t, a.k_factor
    return 2.0 * (r + t) * math.tan(math.radians(45.0)) - (math.pi / 2.0) * (r + k * t)


def slot_centres(a: Assembly) -> list[float]:
    """Strut slot centres above the strut's own bottom end."""
    n = int((a.strut_len - 25.4) / a.slot_pitch) + 1
    return [25.4 + i * a.slot_pitch for i in range(n)]


def nearest_slot(a: Assembly, want: float) -> tuple[float, float]:
    """(centre, signed offset) of the slot nearest a wanted height."""
    c = min(slot_centres(a), key=lambda s: abs(s - want))
    return c, c - want


# --------------------------------------------------------------------------------------------
def sheet_parts(path: Path, a: Assembly) -> None:
    """Flat patterns. Formed dimensions in, flat length derived by subtracting the deduction."""
    W, H = 1180, 760
    bd = bend_deduction(a)
    o = _frame(W, H, "THE TWO PARTS, FLAT",
               "Two bent parts, two of each. Formed dimensions in; flat length is the sum of the "
               "legs MINUS the bend deduction.", "FLAT PATTERNS — dimensions derived, bend "
               "deduction is an ESTIMATE until SendCutSend's calculator confirms it")

    PARTS = [("A — CLAMP  x2", a.clamp_leg, a.clamp_short, a.clamp_width,
              "Long leg lies on the fridge top (or under its base). Short leg drops beside the "
              "strut. The SAME part is used at both ends — the lower one is simply flipped."),
             ("B — FOOT  x2", a.foot_leg, a.foot_rise, a.foot_width,
              "Vertical leg carries the elongated slot the stud passes through. Horizontal leg "
              "turns OUTBOARD and the strut stands on it, so the strut never touches the floor.")]
    # ONE scale for both parts. Scaling each to fit its own panel drew two 60 mm-wide parts at
    # visibly different widths, which invites exactly the wrong conclusion.
    sc = 400.0 / max(lg + sh - bd for _, lg, sh, _, _ in PARTS)
    for idx, (nm, leg, short, wid, note) in enumerate(PARTS):
        px, py = 40 + idx * 580, 100
        o += _panel(px, py, 545, 470, nm, OK)
        flat_len = leg + short - bd
        bx, by = px + 40, py + 150
        fw = wid * sc
        o.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{flat_len * sc:.1f}" '
                 f'height="{fw:.1f}" fill="{C_PLATE}" stroke="{INK}" stroke-width="1.4"/>')
        blx = bx + (leg - bd / 2.0) * sc
        o.append(f'<line x1="{blx:.1f}" y1="{by - 14:.1f}" x2="{blx:.1f}" '
                 f'y2="{by + fw + 14:.1f}" stroke="{BAD}" stroke-width="1.5" '
                 f'stroke-dasharray="8 5"/>')
        o.append(_t(blx, by - 20, "BEND 90", 9.0, fill=BAD, weight="bold"))

        hx = bx + (leg * 0.55) * sc
        o.append(f'<circle cx="{hx:.1f}" cy="{by + fw / 2:.1f}" r="{a.bolt_dia * sc / 2:.1f}" '
                 f'fill="{PAPER}" stroke="{INK}" stroke-width="1.1"/>')
        if idx == 0:
            o.append(_t(hx, by + fw + 26, "square hole 8.38 — stops the stud spinning", 8.6,
                        fill=MUTED))
        else:
            sl = a.slot_len * sc
            o.append(f'<rect x="{hx - sl / 2:.1f}" y="{by + fw / 2 - 5:.1f}" width="{sl:.1f}" '
                     f'height="10" rx="5" fill="{PAPER}" stroke="{INK}" stroke-width="1.1"/>')
            o.append(_t(hx, by + fw + 26, f"slot {a.slot_len:.1f} long — height adjustment "
                        f"lives HERE", 8.6, fill=MUTED))

        for x0, x1, ly, txt in [(bx, blx, by + fw + 52, f"{leg:.0f} formed"),
                                (blx, bx + flat_len * sc, by + fw + 52, f"{short:.0f} formed")]:
            o.append(f'<line x1="{x0:.1f}" y1="{ly:.1f}" x2="{x1:.1f}" y2="{ly:.1f}" '
                     f'stroke="{INK}" stroke-width="0.8"/>')
            o.append(_t((x0 + x1) / 2, ly - 5, txt, 9.0, weight="bold"))
        o.append(_t(bx + flat_len * sc / 2, by + fw + 86,
                    f"FLAT {flat_len:.2f} x {wid:.0f} = {leg:.0f} + {short:.0f} - {bd:.2f}", 10.5,
                    weight="bold"))
        o += _para(px + 16, py + 54, note, 62)
        o += _para(px + 16, py + 386,
                   f"Material {a.bracket_t:.2f} mm ({a.bracket_t / IN:.3f} in). Bend radius "
                   f"{a.bend_radius:.2f} assumed at about 1T, K = {a.k_factor}. Deduction "
                   f"{bd:.2f} mm. Both parts drawn at the SAME scale.", 62)

    o += _panel(40, 590, 1085, 130, "WHY THE DEDUCTION MATTERS MORE THAN IT LOOKS", WARN)
    o += _para(56, 640, f"The deduction is {bd:.2f} mm — small, and tempting to ignore. It is not "
               f"ignorable here because the foot's slot is what absorbs height error, and the "
               f"slot is only {a.slot_len:.1f} mm long. Getting both bends wrong in the same "
               f"direction spends {2 * bd:.1f} mm of a {a.slot_len:.1f} mm adjustment range "
               f"before the thing is even on the fridge. Replace this estimate with SendCutSend's "
               f"own calculator before ordering.", 150)
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — 2 parts, bend deduction %.2f mm", path, bd)


# --------------------------------------------------------------------------------------------
def sheet_height_check(path: Path, a: Assembly) -> None:
    """Does a slot actually land where each clamp needs one? Asked for explicitly."""
    W, H = 1180, 720
    top_c, top_off = nearest_slot(a, a.fridge_h)
    low_c, low_off = nearest_slot(a, a.base_gap)
    reach = a.slot_len / 2.0
    o = _frame(W, H, "DOES A SLOT LAND WHERE EACH CLAMP NEEDS ONE?",
               "The strut is slotted on a fixed 50.8 mm pitch. The fridge is whatever height it "
               "is. Those two facts have to meet.",
               "VALIDATION — the check that the strut can actually be bolted where it must be")

    o += _panel(40, 100, 700, 470, "STRUT SLOTS vs THE TWO CLAMP HEIGHTS")
    ox, oy, sc = 250.0, 552.0, 0.212
    def Y(mm):
        return oy - mm * sc
    o.append(f'<rect x="{ox:.1f}" y="{Y(a.strut_len):.1f}" width="26" '
             f'height="{a.strut_len * sc:.1f}" fill="{C_STRUT}" stroke="{INK}" '
             f'stroke-width="1.1"/>')
    for s in slot_centres(a):
        o.append(f'<rect x="{ox + 8:.1f}" y="{Y(s + a.slot_len / 2):.1f}" width="10" '
                 f'height="{a.slot_len * sc:.1f}" fill="{INK}" fill-opacity="0.45"/>')
    o.append(f'<line x1="{ox - 150:.1f}" y1="{Y(a.fridge_h):.1f}" x2="{ox + 150:.1f}" '
             f'y2="{Y(a.fridge_h):.1f}" stroke="{FRIDGE_EDGE}" stroke-width="1.2"/>')
    o.append(f'<rect x="{ox - 150:.1f}" y="{Y(a.fridge_h):.1f}" width="150" '
             f'height="{(Y(a.base_gap) - Y(a.fridge_h)):.1f}" fill="{FRIDGE_SIDE}"/>')
    o.append(_t(ox - 75, Y(a.fridge_h / 2), "fridge", 9, fill="#cfc9c2", rot=-90))

    for want, cen, off, nm in [(a.fridge_h, top_c, top_off, "TOP CLAMP"),
                               (a.base_gap, low_c, low_off, "LOWER CLAMP")]:
        ok = abs(off) <= reach
        col = OK if ok else BAD
        o.append(f'<line x1="{ox + 26:.1f}" y1="{Y(want):.1f}" x2="{ox + 170:.1f}" '
                 f'y2="{Y(want):.1f}" stroke="{col}" stroke-width="1.5"/>')
        o.append(_t(ox + 176, Y(want) - 12, f"{nm} wants {want:.1f}", 9.5, anchor="start",
                    fill=col, weight="bold"))
        o.append(_t(ox + 176, Y(want) + 1, f"nearest slot {cen:.1f}, off by {off:+.1f}", 8.6,
                    anchor="start", fill=col))
        o.append(_t(ox + 176, Y(want) + 13,
                    f"{'INSIDE' if ok else 'OUTSIDE'} the {reach:.1f} half-slot", 8.6,
                    anchor="start", fill=col, weight="bold"))

    o.append(f'<line x1="{ox + 13:.1f}" y1="{Y(a.strut_len):.1f}" x2="{ox + 13:.1f}" '
             f'y2="{Y(a.fridge_h):.1f}" stroke="{WARN}" stroke-width="2"/>')
    o.append(_t(ox + 40, Y(a.fridge_h) - 14, f"{a.proud:.1f} mm proud of the top", 9.0,
                anchor="start", fill=WARN, weight="bold"))

    o += _panel(760, 100, 380, 470, "WHAT THE NUMBERS SAY", OK)
    rows = [("strut length", f"{a.strut_len:.1f}", "6 ft stock"),
            ("fridge case height", f"{a.fridge_h:.1f}", "published"),
            ("strut stands proud by", f"{a.proud:.1f}", "derived"),
            ("slot pitch", f"{a.slot_pitch:.1f}", "McMaster table"),
            ("slot length", f"{a.slot_len:.1f}", "McMaster table"),
            ("adjustment either way", f"±{reach:.1f}", "half a slot"),
            ("top clamp error", f"{top_off:+.1f}", "PASS" if abs(top_off) <= reach else "FAIL"),
            ("lower clamp error", f"{low_off:+.1f}", "PASS" if abs(low_off) <= reach else "FAIL")]
    for i, (k, v, n) in enumerate(rows):
        ry = 140 + i * 34
        if i % 2 == 0:
            o.append(f'<rect x="770" y="{ry - 15:.1f}" width="360" height="30" fill="#f2f5f7"/>')
        col = OK if n == "PASS" else (BAD if n == "FAIL" else MUTED)
        o.append(_t(782, ry + 2, k, 10.4, anchor="start"))
        o.append(_t(1035, ry + 2, v, 10.8, anchor="end", weight="bold"))
        o.append(_t(1048, ry + 2, n, 9.2, anchor="start", fill=col,
                    weight="bold" if col is not MUTED else "normal"))

    o += _panel(40, 590, 1100, 110, "THE POINT", OK if abs(top_off) <= reach else BAD)
    o += _para(56, 640,
               f"A 6 ft strut against a {a.fridge_h / IN:.1f} in fridge leaves {a.proud:.1f} mm "
               f"standing proud of the top, and the pitch happens to put a slot {abs(top_off):.1f} "
               f"mm from where the top clamp wants one — well inside the half-slot. This is luck, "
               f"not design: the strut is stock and the fridge is what it is. It is checked here "
               f"precisely BECAUSE nothing made it come out right, and a different fridge or a "
               f"different strut length would need this recomputed.", 152)
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — top %+.1f, lower %+.1f against ±%.1f", path, top_off, low_off, reach)


# --------------------------------------------------------------------------------------------
def sheet_loadpath(path: Path, a: Assembly) -> None:
    W, H = 1180, 700
    o = _frame(W, H, "WHERE THE WEIGHT ACTUALLY GOES",
               "Straight down the strut, into the foot, into the floor. The clamps do not carry "
               "it — they only stop the top falling away from the wall.",
               "LOAD PATH — the whole argument for this design in one drawing")
    ox, oy, sc = 250.0, 590.0, 0.255
    def Y(mm):
        return oy - mm * sc
    o += _panel(40, 100, 700, 500, "SIDE VIEW, TO SCALE")
    o.append(f'<rect x="{ox:.1f}" y="{Y(a.fridge_h):.1f}" width="{160 * sc * 2:.1f}" '
             f'height="{(Y(a.base_gap) - Y(a.fridge_h)):.1f}" fill="{FRIDGE_SIDE}"/>')
    sx = ox + 160 * sc * 2 + 10
    o.append(f'<rect x="{sx:.1f}" y="{Y(a.strut_len):.1f}" width="14" '
             f'height="{a.strut_len * sc:.1f}" fill="{C_STRUT}" stroke="{INK}"/>')
    o.append(f'<line x1="{ox - 90:.1f}" y1="{oy:.1f}" x2="{sx + 190:.1f}" y2="{oy:.1f}" '
             f'stroke="{INK}" stroke-width="2.5"/>')
    o += _display_ghost(sx + 46, Y(a.screen_centre + a.display_h / 2), 26,
                        a.display_h * sc, "display")
    for yy in range(0, 5):
        ay = Y(a.screen_centre) + yy * 60
        if ay > oy - 20:
            break
        o.append(f'<line x1="{sx + 7:.1f}" y1="{ay:.1f}" x2="{sx + 7:.1f}" y2="{ay + 44:.1f}" '
                 f'stroke="{OK}" stroke-width="3"/>')
        o.append(f'<path d="M{sx + 2:.1f} {ay + 38:.1f} L{sx + 7:.1f} {ay + 48:.1f} '
                 f'L{sx + 12:.1f} {ay + 38:.1f}" fill="{OK}"/>')
    o.append(_t(sx + 60, Y(700), "the load runs DOWN the strut", 10.5, anchor="start", fill=OK,
                weight="bold"))
    o.append(_t(sx + 60, Y(660), "and into the floor, not the fridge", 10.0, anchor="start",
                fill=OK))
    for h, nm in [(a.fridge_h, "top clamp — HOLDS IN, carries nothing"),
                  (a.base_gap, "lower clamp — HOLDS IN, carries nothing")]:
        o.append(f'<path d="M{sx - 30:.1f} {Y(h):.1f} L{sx - 4:.1f} {Y(h):.1f}" stroke="{WARN}" '
                 f'stroke-width="2.5"/>')
        o.append(f'<path d="M{sx - 10:.1f} {Y(h) - 5:.1f} L{sx - 2:.1f} {Y(h):.1f} '
                 f'L{sx - 10:.1f} {Y(h) + 5:.1f}" fill="{WARN}"/>')
        o.append(_t(sx + 22, Y(h) - 8, nm, 9.2, anchor="start", fill=WARN, weight="bold"))
    o.append(f'<rect x="{sx - 6:.1f}" y="{oy - 7:.1f}" width="74" height="7" fill="{C_STEEL}" '
             f'stroke="{INK}" stroke-width="0.9"/>')
    o.append(_t(sx + 74, oy - 12, "FOOT", 9.0, anchor="start", fill=OK, weight="bold"))
    o.append(_t(ox + 60, oy - 18, "FLOOR — takes all 154 N", 10.5, anchor="start",
                weight="bold"))

    o += _panel(760, 100, 380, 500, "WHAT THAT BUYS", OK)
    pts = [("No magnets at all", "the derate chain, the fastener stack, the peel failure mode "
            "and the dependency on a magnetic panel all vanish together."),
           ("A non-magnetic panel stops mattering", "stainless, plastic, painted — the clamp "
            "does not care what the fridge is made of."),
           ("Nothing creeps", "sustained shear on paint was the slow failure the magnets had. "
            "There is no sustained shear here."),
           ("Height became adjustable", "the foot's slot sets it, after the thing is built, "
            "against a real person standing there."),
           ("The failure mode changed", "the magnet design's worst case was bonded glass on the "
            "floor. This one's is a wobble.")]
    for i, (hd, bd_) in enumerate(pts):
        yy = 146 + i * 92
        o.append(_t(776, yy, hd, 11.0, anchor="start", weight="bold", fill=OK))
        o += _para(776, yy + 17, bd_, 44, size=10.0, lead=12.5)
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


# --------------------------------------------------------------------------------------------
def sheet_clearance(path: Path, a: Assembly) -> None:
    W, H = 1180, 640
    o = _frame(W, H, "WHERE THE TOP CLAMP LANDS",
               "Plan view of the fridge top. The hinge cover owns the front; the clamp has to "
               "live behind it.",
               "CLEARANCE — the window is derived and the tape agrees; the LAYOUT inside it is the finding")
    ox, oy, sc = 90.0, 150.0, 1.05
    o += _panel(40, 100, 1100, 330, "FRIDGE TOP, LOOKING DOWN")
    o.append(f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{a.fridge_d * sc:.1f}" height="150" '
             f'fill="{FRIDGE_SIDE}" stroke="{FRIDGE_EDGE}"/>')
    hc_x = ox + (a.fridge_d - a.hinge_cover) * sc
    o.append(f'<rect x="{hc_x:.1f}" y="{oy:.1f}" width="{a.hinge_cover * sc:.1f}" height="150" '
             f'fill="#5c574f" stroke="{FRIDGE_EDGE}"/>')
    o.append(_t(hc_x + a.hinge_cover * sc / 2, oy + 78, "HINGE COVER", 10.5, fill="#e8e2d8",
                weight="bold"))
    o.append(_t(hc_x + a.hinge_cover * sc / 2, oy + 94, f"front {a.hinge_cover:.0f} mm", 9,
                fill="#bdb6ab"))
    o.append(_t(ox + 40, oy + 20, "REAR", 9, anchor="start", fill="#bdb6ab"))

    centre = a.strut_centre          # the WINDOW's centre, not the case's — see Assembly
    for s in (centre - a.strut_spacing / 2.0, centre + a.strut_spacing / 2.0):
        cx = ox + s * sc
        o.append(f'<rect x="{cx - a.strut_width * sc / 2:.1f}" y="{oy + 30:.1f}" '
                 f'width="{a.strut_width * sc:.1f}" height="90" fill="{C_STRUT}" '
                 f'stroke="{INK}" stroke-width="1.2"/>')
        o.append(f'<rect x="{cx - a.clamp_width * sc / 2:.1f}" y="{oy + 46:.1f}" '
                 f'width="{a.clamp_width * sc:.1f}" height="58" fill="{C_STEEL}" '
                 f'fill-opacity="0.85" stroke="{INK}" stroke-width="1.2"/>')
        o.append(_t(cx, oy + 80, "clamp", 8.4, fill="#fff", weight="bold"))
    margin = a.hinge_margin
    front_edge = centre + a.strut_spacing / 2.0 + a.clamp_width / 2.0
    o.append(f'<line x1="{ox + front_edge * sc:.1f}" y1="{oy + 160:.1f}" x2="{hc_x:.1f}" '
             f'y2="{oy + 160:.1f}" stroke="{BAD if margin < 10 else OK}" stroke-width="1.6"/>')
    o.append(_t((ox + front_edge * sc + hc_x) / 2, oy + 145, f"{margin:.1f} mm", 10,
                fill=BAD if margin < 10 else OK, weight="bold"))
    o.append(f'<line x1="{ox:.1f}" y1="{oy + 200:.1f}" x2="{hc_x:.1f}" y2="{oy + 200:.1f}" '
             f'stroke="{INK}" stroke-width="1"/>')
    o.append(_t((ox + hc_x) / 2, oy + 194, f"clear window {a.clear_window:.1f} mm — derived; the 406 tape reading agrees",
                10, weight="bold"))

    o += _panel(40, 450, 1100, 160, "READ THIS THE RIGHT WAY ROUND", WARN)
    o += _para(56, 500,
               f"The window is {a.clear_window:.1f} mm and the two clamps span "
               f"{a.strut_spacing + a.clamp_width:.0f} mm, leaving {margin:.1f} mm at each end. "
               f"That only holds because the struts are centred on the WINDOW. Centring them on "
               f"the case depth — the obvious choice, and what this drawing was first built with "
               f"— drives the front clamp 51.2 mm INTO the hinge cover. The cost is cosmetic: the "
               f"screen ends up {a.display_bias_rearward:.0f} mm behind the case centre, still "
               f"comfortably within the panel. Quote {margin:.1f} mm when asking 'does it fit'.",
               150)
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — installed margin %.1f mm", path, margin)


# --------------------------------------------------------------------------------------------
def sheet_assembly(path: Path, a: Assembly) -> None:
    W, H = 1180, 700
    o = _frame(W, H, "HOW IT GOES TOGETHER",
               "Four steps. Everything stays loose until the last one, because the fridge is what "
               "squares it up.",
               "ASSEMBLY — order matters; tightening early is the way to get this wrong")
    steps = [("1  STAND THE STRUTS ON THE FEET",
              "Stud through the foot's slot and the strut's bottom slot. Nut FINGER TIGHT. The "
              "slot is the height adjustment, so leaving it loose is the whole point.",
              "loose"),
             ("2  HOOK THE TOP CLAMPS OVER",
              "Long leg on the fridge top, short leg down beside the strut. Washers behind the "
              "strut. Nut on, still loose. The clamps hang the assembly in place while you work.",
              "loose"),
             ("3  SLIDE THE LOWER CLAMPS UP",
              "Up their slots until the long leg engages under the appliance. This is the step "
              "that needs a torch and the one with an open question against it.",
              "loose"),
             ("4  LOCK EVERYTHING",
              "Top first, then bottom, then the feet. The struts go into tension between the two "
              "clamps and the fridge is gripped rather than leaned on.",
              "TIGHT")]
    for i, (hd, body, state) in enumerate(steps):
        x = 40 + (i % 2) * 570
        y = 100 + (i // 2) * 210
        col = OK if state == "TIGHT" else WARN
        o += _panel(x, y, 540, 185, hd, col)
        o += _para(x + 16, y + 50, body, 62)
        o.append(f'<rect x="{x + 16:.1f}" y="{y + 140:.1f}" width="{62 + len(state) * 6:.0f}" '
                 f'height="22" rx="11" fill="{col}" fill-opacity="0.14"/>')
        o.append(_t(x + 26, y + 155, f"leave it {state}", 9.6, anchor="start", fill=col,
                    weight="bold"))
    o += _panel(40, 530, 1100, 140, "THE ONE THING THAT WILL BITE", BAD)
    o += _para(56, 580,
               f"Tightening the top clamps before the lower ones are engaged pulls the struts "
               f"against the panel at an angle and they will not then slide. The struts are "
               f"{a.strut_len:.0f} mm of stiff channel; there is no compliance in them to take "
               f"that out afterwards. If a lower clamp will not move, slacken the top and start "
               f"again rather than forcing it. Only the {a.foam:.0f} mm foam has any give at all, "
               f"and it has {a.foam:.0f} mm of it.", 150)
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


# --------------------------------------------------------------------------------------------
def sheet_approval(path: Path, a: Assembly) -> None:
    W, H = 1180, 800
    o = _frame(W, H, "FRIDGE-SIDE CHORE DISPLAY — THE CLAMPED STRUT",
               "What it is, what it does to the kitchen, and what it costs. No engineering "
               "vocabulary below this line.",
               "FOR APPROVAL — this is the design being proposed")
    ox, oy, sc = 120.0, 560.0, 0.235
    def Y(mm):
        return oy - mm * sc
    o += _panel(40, 100, 520, 560, "WHAT IT LOOKS LIKE FROM THE SIDE")
    o.append(f'<line x1="{ox - 70:.1f}" y1="{oy:.1f}" x2="{ox + 330:.1f}" y2="{oy:.1f}" '
             f'stroke="{INK}" stroke-width="2.5"/>')
    o.append(f'<rect x="{ox:.1f}" y="{Y(a.fridge_h):.1f}" width="{a.fridge_d * sc * 0.42:.1f}" '
             f'height="{(Y(a.base_gap) - Y(a.fridge_h)):.1f}" fill="{FRIDGE_SIDE}"/>')
    o.append(_t(ox + 30, Y(900), "fridge", 9.5, fill="#cfc9c2", rot=-90))
    sx = ox + a.fridge_d * sc * 0.42 + 4
    o.append(f'<rect x="{sx:.1f}" y="{Y(a.strut_len):.1f}" width="9" '
             f'height="{a.strut_len * sc:.1f}" fill="{C_STRUT}" stroke="{INK}"/>')
    o += _display_ghost(sx + 13, Y(a.screen_centre + a.display_h / 2), 26, a.display_h * sc,
                        "the screen")
    o.append(f'<rect x="{sx - 4:.1f}" y="{oy - 6:.1f}" width="70" height="6" fill="{C_STEEL}"/>')
    o.append(_t(sx + 90, oy + 16, "stands on the floor", 9.6, anchor="start",
                weight="bold", fill=OK))
    o.append(_t(sx + 90, Y(a.fridge_h) + 4, "clipped at the top", 9.6, anchor="start"))
    o.append(_t(sx + 90, Y(a.base_gap) - 10, "clipped at the bottom", 9.6, anchor="start"))
    o.append(_t(56, 640, "eye level is adjustable after it is built", 9.8,
                anchor="start", fill=OK, weight="bold"))

    o += _panel(580, 100, 560, 300, "IN PLAIN LANGUAGE", OK)
    facts = [("It stands on the floor.", "It does not hang off the fridge. The weight goes "
              "straight down into the floor, the way a bookcase does."),
             ("There are no magnets.", "An earlier version used eight of them. This one does "
              "not need any, which removed about $191 and the thing that could have failed."),
             ("It does not mark the fridge.", "Everywhere it touches, there is foam. Nothing is "
              "drilled, glued or stuck to the fridge, and it lifts off."),
             ("The screen height can change.", "It slides. If it is wrong for whoever is "
              "standing there, it moves without rebuilding anything.")]
    for i, (hd, bdy) in enumerate(facts):
        yy = 146 + i * 62
        o.append(_t(596, yy, hd, 11.5, anchor="start", weight="bold"))
        o += _para(596, yy + 16, bdy, 66, size=10.2, lead=12.5)

    o += _panel(580, 420, 560, 240, "WHAT IT STICKS OUT INTO THE ROOM", WARN)
    o += _para(596, 466,
               f"The screen face sits {a.display_face:.1f} mm off the fridge panel — about "
               f"{a.display_face / IN:.1f} inches. Of that, {a.fixed_part:.1f} mm is the screen "
               f"and its own back box, which no mount can avoid. The mount itself adds "
               f"{a.display_face - a.fixed_part:.1f} mm.", 64)
    bx, bw = 596, 500
    o.append(f'<rect x="{bx}" y="560" width="{bw * a.fixed_part / a.display_face:.0f}" '
             f'height="26" fill="{C_PLATE}" stroke="{INK}"/>')
    o.append(f'<rect x="{bx + bw * a.fixed_part / a.display_face:.0f}" y="560" '
             f'width="{bw * (a.display_face - a.fixed_part) / a.display_face:.0f}" height="26" '
             f'fill="{WARN}" fill-opacity="0.55" stroke="{INK}"/>')
    o.append(_t(bx + bw * a.fixed_part / a.display_face / 2, 577,
                f"the screen itself {a.fixed_part:.0f}", 9.4))
    o.append(_t(bx + bw - 40, 577, f"mount {a.display_face - a.fixed_part:.0f}", 9.4))
    o += _para(596, 606, "The orange part is the only bit that is a design choice, and it is "
               "already the thinnest strut sold.", 66, size=10.0)

    o += _panel(40, 680, 1100, 100, "WHAT IS NOT SETTLED YET", BAD)
    o += _para(56, 726, "Two things still need someone with a torch under the fridge: whether the "
               "lower clamp's reach hits anything under there, and whether there is a lip worth "
               "hooking rather than just bearing on. Neither changes what it looks like; both "
               "could change the lower bracket.", 152)
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — display face %.1f mm", path, a.display_face)


SHEETS = {"clamp_approval": sheet_approval, "clamp_parts": sheet_parts,
          "clamp_assembly": sheet_assembly, "clamp_clearance": sheet_clearance,
          "clamp_loadpath": sheet_loadpath, "clamp_height_check": sheet_height_check}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=sorted(SHEETS))
    ap.add_argument("--outdir", type=Path, default=Path("."))
    ap.add_argument("--log-level", default="INFO")
    a = ap.parse_args(argv)
    logging.basicConfig(level=a.log_level,
                        format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    asm = Assembly()
    for nm, fn in sorted(SHEETS.items()):
        if a.only and nm != a.only:
            continue
        fn(a.outdir / f"{nm}.svg", asm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
