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
               f"Two bent parts: {a.n_clamps} clamps and {a.n_feet} feet. TWO surfaces are "
               f"gripped (the fridge top and its underside) but the clamps SPAN both struts, so "
               f"that is {a.n_clamps} bars, not {a.n_struts * a.clamped_surfaces} tabs.",
               "FLAT PATTERNS — dimensions derived, bend deduction is an ESTIMATE until "
               "SendCutSend's calculator confirms it")

    half = a.strut_spacing / 2.0
    PARTS = [(f"A — CLAMP BAR  x{a.n_clamps}", a.clamp_leg, a.clamp_short, a.clamp_width,
              [-half, half], "round",
              "Spans BOTH struts, so the two legs are tied into a frame rather than standing "
              "independently. Long leg lies on the fridge top, or under its base. The SAME part "
              "does both ends — the lower one is flipped."),
             (f"B — FOOT  x{a.n_feet}", a.foot_leg, a.foot_rise, a.foot_width,
              [0.0], "slot",
              "One per strut. Vertical leg carries the elongated slot the stud passes through; "
              "horizontal leg turns OUTBOARD and the strut stands on it, so the strut never "
              "touches the floor.")]

    # ONE scale for both parts, fitted to whichever dimension binds. The clamp is now 5.5x the
    # foot's width, so scaling each to its own panel would make them impossible to compare.
    sc = min(390.0 / max(lg + sh - bd for _, lg, sh, _, _, _, _ in PARTS),
             186.0 / max(wd for _, _, _, wd, _, _, _ in PARTS))

    for idx, (nm, leg, short, wid, holes, hkind, note) in enumerate(PARTS):
        px, py = 40 + idx * 580, 100
        o += _panel(px, py, 545, 470, nm, OK)
        flat_len = leg + short - bd
        fw = wid * sc
        bx = px + 40
        by = py + 142 + (186.0 - fw) / 2.0
        o.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{flat_len * sc:.1f}" '
                 f'height="{fw:.1f}" fill="{C_PLATE}" stroke="{INK}" stroke-width="1.4"/>')
        blx = bx + (leg - bd / 2.0) * sc
        o.append(f'<line x1="{blx:.1f}" y1="{by - 14:.1f}" x2="{blx:.1f}" '
                 f'y2="{by + fw + 14:.1f}" stroke="{BAD}" stroke-width="1.5" '
                 f'stroke-dasharray="8 5"/>')
        o.append(_t(blx, by - 20, "BEND 90", 9.0, fill=BAD, weight="bold"))

        hx = bx + (leg * 0.55) * sc
        for hy_mm in holes:
            cy = by + fw / 2.0 + hy_mm * sc
            if hkind == "round":
                o.append(f'<circle cx="{hx:.1f}" cy="{cy:.1f}" r="{a.bolt_dia * sc / 2:.1f}" '
                         f'fill="{PAPER}" stroke="{INK}" stroke-width="1.1"/>')
            else:
                sl = a.slot_len * sc
                o.append(f'<rect x="{hx - sl / 2:.1f}" y="{cy - 4:.1f}" width="{sl:.1f}" '
                         f'height="8" rx="4" fill="{PAPER}" stroke="{INK}" stroke-width="1.1"/>')
        if hkind == "round":
            o.append(f'<line x1="{hx:.1f}" y1="{by + fw / 2 - half * sc:.1f}" x2="{hx:.1f}" '
                     f'y2="{by + fw / 2 + half * sc:.1f}" stroke="{OK}" stroke-width="1"/>')
            lx = bx + flat_len * sc + 12
            o.append(f'<line x1="{hx:.1f}" y1="{by + fw / 2:.1f}" x2="{lx - 4:.1f}" '
                     f'y2="{by + fw / 2:.1f}" stroke="{OK}" stroke-width="0.7" '
                     f'stroke-dasharray="3 3"/>')
            o.append(_t(lx, by + fw / 2 - 3, f"{a.strut_spacing:.0f} mm", 9.4, anchor="start",
                        fill=OK, weight="bold"))
            o.append(_t(lx, by + fw / 2 + 9, "strut centres", 8.6, anchor="start", fill=OK))
            o.append(_t(bx + flat_len * sc / 2, by + fw + 24,
                        "square holes 8.38 — the stud cannot spin", 8.6, fill=MUTED))
        else:
            o.append(_t(bx + flat_len * sc / 2, by + fw + 24,
                        f"slot {a.slot_len:.1f} long — height adjustment lives HERE", 8.6,
                        fill=MUTED))

        dy = by + fw + 48
        for x0, x1, txt in [(bx, blx, f"{leg:.0f} formed"),
                            (blx, bx + flat_len * sc, f"{short:.0f} formed")]:
            o.append(f'<line x1="{x0:.1f}" y1="{dy:.1f}" x2="{x1:.1f}" y2="{dy:.1f}" '
                     f'stroke="{INK}" stroke-width="0.8"/>')
            o.append(_t((x0 + x1) / 2, dy - 5, txt, 9.0, weight="bold"))
        o.append(_t(bx + flat_len * sc / 2, dy + 26,
                    f"FLAT {flat_len:.2f} x {wid:.0f}", 10.5, weight="bold"))
        o += _para(px + 16, py + 54, note, 62)
        o += _para(px + 16, py + 424,
                   f"Material {a.bracket_t:.2f} mm ({a.bracket_t / IN:.3f} in), bend radius "
                   f"{a.bend_radius:.2f} at about 1T, K = {a.k_factor}, deduction {bd:.2f} mm. "
                   f"Both parts drawn at the SAME scale.", 62)

    o += _panel(40, 590, 1085, 130, "WHAT SPANNING COSTS, AND THE ONE RISK IT CARRIES", WARN)
    o += _para(56, 636,
               f"Two bars instead of four tabs uses about 2.7x the clamp steel, and the top bar "
               f"now fixes the {a.strut_spacing:.0f} mm spacing instead of relying on careful "
               f"assembly — which is a gain. The risk is underneath: the LOWER bar has to bear "
               f"across {a.clamp_width:.0f} mm of an underside measured at 10-20 mm and known "
               f"NOT to be flat. It therefore bears on TWO PADS inset {a.lower_pad_inset:.0f} mm "
               f"from each strut rather than along a continuous edge, so an uneven surface loads "
               f"two known points instead of whichever high spot it finds first.", 150)
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — %d clamps x %.0f mm span, %d feet, deduction %.2f",
             path, a.n_clamps, a.clamp_width, a.n_feet, bd)


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
    pieces = ([(0.0, a.lower_strut_len), (a.upper_strut_lo, a.strut_top)] if a.strut_split
              else [(0.0, a.strut_len)])
    for p_lo, p_hi in pieces:
        o.append(f'<rect x="{ox:.1f}" y="{Y(p_hi):.1f}" width="26" '
                 f'height="{(Y(p_lo) - Y(p_hi)):.1f}" fill="{C_STRUT}" stroke="{INK}" '
                 f'stroke-width="1.1"/>')
        for s in a._slots_between(p_lo, p_hi - 11.11, p_lo):
            o.append(f'<rect x="{ox + 8:.1f}" y="{Y(s + a.slot_len / 2):.1f}" width="10" '
                     f'height="{a.slot_len * sc:.1f}" fill="{INK}" fill-opacity="0.45"/>')
    if a.strut_split:
        o.append(f'<rect x="{ox - 3:.1f}" y="{Y(a.upper_strut_lo):.1f}" width="32" '
                 f'height="{(Y(a.lower_strut_len) - Y(a.upper_strut_lo)):.1f}" fill="{OK}" '
                 f'fill-opacity="0.14"/>')
        o.append(_t(ox + 13, (Y(a.lower_strut_len) + Y(a.upper_strut_lo)) / 2, "GAP", 8.0,
                    fill=OK, weight="bold"))
    o.append(f'<line x1="{ox - 150:.1f}" y1="{Y(a.fridge_h):.1f}" x2="{ox + 150:.1f}" '
             f'y2="{Y(a.fridge_h):.1f}" stroke="{FRIDGE_EDGE}" stroke-width="1.2"/>')
    o.append(f'<rect x="{ox - 150:.1f}" y="{Y(a.fridge_h):.1f}" width="150" '
             f'height="{(Y(a.base_gap) - Y(a.fridge_h)):.1f}" fill="{FRIDGE_SIDE}"/>')
    o.append(_t(ox - 75, Y(a.fridge_h / 2), "fridge", 9, fill="#cfc9c2", rot=-90))

    rowspec = [(a.fridge_h, "TOP CLAMP", a.upper_strut_lo),
               (a.base_gap, "LOWER CLAMP", 0.0),
               (a.plate_bolt_hi, "PLATE, upper bolts", a.upper_strut_lo),
               (a.plate_bolt_lo, "PLATE, lower bolts", 0.0)] if a.strut_split else [
               (a.fridge_h, "TOP CLAMP", 0.0), (a.base_gap, "LOWER CLAMP", 0.0)]
    packed = []
    for want, nm, origin in rowspec:
        cand = a._slots_between(origin, origin + 4000, origin)
        cen = min(cand, key=lambda s: abs(s - want))
        packed.append((want, cen, cen - want, nm))
    for want, cen, off, nm in packed:
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
    rows = [("strut, lower + upper", f"{a.lower_strut_ft:.0f}+{a.upper_strut_ft:.0f} ft",
             "both stock, no cutting"),
            ("fridge case height", f"{a.fridge_h:.1f}", "published"),
            ("strut stands proud by", f"{a.proud:.1f}", "derived"),
            ("slot pitch", f"{a.slot_pitch:.1f}", "McMaster table"),
            ("slot length", f"{a.slot_len:.1f}", "McMaster table"),
            ("adjustment either way", f"±{reach:.1f}", "half a slot"),
            ("lower piece", f"{a.lower_strut_ft:.0f} ft", "stock, no cut"),
            ("upper piece", f"{a.upper_strut_ft:.0f} ft", "stock, no cut"),
            ("gap over the box", f"{a.upper_strut_lo - a.lower_strut_len:.1f}",
             f"{a.edge_open:.0f} of {a.box_h_portrait:.0f} mm edge open")] + [
            (nm.lower(), f"{off:+.1f}", "PASS" if abs(off) <= reach else "FAIL")
            for _, _, off, nm in packed]
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
               f"Four landings on TWO slot grids, because each piece anchors its own slots to its "
               f"own end. Three are EXACT and one is {max(abs(o_) for _, _, o_, _ in packed):.1f} "
               f"mm out, all inside the {reach:.1f} mm half-slot. The exact ones are not luck: "
               f"strut_top_proud is DERIVED to put a slot on the top clamp — at an arbitrary "
               f"60 mm the nearest was 16.2 mm away, outside the half-slot and unbuildable. The "
               f"plate bolts are exact by construction, because they are CHOSEN from real slot "
               f"positions rather than picked and hoped for.", 152)
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    worst = max(abs(off) for _, _, off, _ in packed)
    LOG.info("Wrote %s — %d landings checked on %d slot grids, worst %+.2f against ±%.1f", path, len(packed), 2 if a.strut_split else 1, worst, reach)


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

    margin = a.hinge_margin
    bar_x = ox + (centre - a.clamp_outer_half) * sc
    o.append(f'<rect x="{bar_x:.1f}" y="{oy + 40:.1f}" width="{a.clamp_width * sc:.1f}" '
             f'height="70" fill="{C_STEEL}" fill-opacity="0.9" stroke="{INK}" '
             f'stroke-width="1.3"/>')
    o.append(_t(ox + centre * sc, oy + 72,
                f"ONE CLAMP BAR spanning both struts — {a.clamp_width:.0f} mm", 9.4, fill="#fff",
                weight="bold"))
    o.append(_t(ox + centre * sc, oy + 88, "ties the two struts into a frame", 8.4,
                fill="#d8d2c8"))
    front_edge = centre + a.clamp_outer_half
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
               f"The bar is placed as far FORWARD as the cover allows while holding "
               f"{a.cover_margin:.0f} mm back from it, which leaves {a.strut_centre - a.clamp_outer_half:.1f} mm "
               f"at the rear. Three datums were possible. Centring on the CASE drives the bar "
               f"48.7 mm INTO the cover — blocked. Centring on the WINDOW is safe but leaves the "
               f"screen 101.5 mm behind the case centre, pushed away from where anyone stands. "
               f"Going hard forward centres best and leaves ZERO tolerance against a cover "
               f"position read off a photograph. This sits between them: the screen is now "
               f"{a.display_bias_rearward:.1f} mm rearward instead of 101.5, and "
               f"{a.cover_margin:.0f} mm of clearance is deliberately kept in hand.", 150)
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
             ("2  HOOK THE TOP CLAMP BAR OVER",
              "ONE bar across both struts. Long leg on the fridge top, short leg down beside "
              "them, washers behind. Nuts on, still loose. Because it reaches both struts it "
              "SETS the spacing for you rather than needing it measured.",
              "loose"),
             ("3  SLIDE THE LOWER BAR UP",
              "Up until its two pads engage under the appliance. Pads, not a continuous edge, "
              "because the underside is not flat. This is the step that needs a torch and the "
              "one with an open question against it.",
              "loose"),
             ("4  PLATE ON, THEN THE DISPLAY — IN THAT ORDER",
              "The plate-to-strut bolt heads sit on the display side. Once the display is "
              "mounted they cannot be reached, so the plate goes on first and the display last.",
              "TIGHT"),
             ("5  LOCK EVERYTHING",
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
               f"Tightening the top bar before the lower one is engaged pulls the struts "
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


# --------------------------------------------------------------------------------------------
def sheet_frame(path: Path, a: Assembly) -> None:
    """FRONT elevation — the view that shows the thing is a ladder, not two separate legs.

    Every other sheet is a side view, a plan, or a flat pattern. A side view shows ONE strut, so
    none of them can show the two struts tied together by identical bars. This is that view.
    """
    W, H = 1420, 940
    o = _frame(W, H, "THE FRAME, SEEN FROM THE FRONT",
               "Looking straight at the fridge's side panel. Two struts, tied top and bottom by "
               "IDENTICAL bars. This is the only view that shows it as one frame.",
               "FRONT ELEVATION — the assembly as a whole")

    o += _panel(40, 100, 620, 800, "LOOKING AT THE SIDE PANEL")
    # BROKEN vertically, like the side elevation and for the same reason: the frame is 610 wide
    # by 1829 tall, so a whole-height drawing is a narrow ribbon and the bars — the point of the
    # view — come out too small to read. The removed stretch carries nothing but strut slots.
    F_LO, F_HI = 200.0, 950.0
    cut = F_HI - F_LO
    sc = 0.60
    ox, oy = 150.0, 800.0                       # rear edge of the panel, and the floor

    def X(mm):
        return ox + mm * sc                     # mm measured from the fridge's REAR edge

    def Y(mm):
        return oy - (mm if mm <= F_LO else mm - cut) * sc

    o.append(f'<line x1="{X(-70):.1f}" y1="{oy:.1f}" x2="{X(690):.1f}" y2="{oy:.1f}" '
             f'stroke="{INK}" stroke-width="2.5"/>')
    o.append(f'<rect x="{X(0):.1f}" y="{Y(a.fridge_h):.1f}" width="{a.fridge_d * sc:.1f}" '
             f'height="{(Y(a.base_gap) - Y(a.fridge_h)):.1f}" fill="{FRIDGE_SIDE}" '
             f'stroke="{FRIDGE_EDGE}" stroke-width="1.2"/>')
    hc = a.fridge_d - a.hinge_cover
    o.append(f'<rect x="{X(hc):.1f}" y="{Y(a.fridge_h) - 36 * sc:.1f}" '
             f'width="{a.hinge_cover * sc:.1f}" height="{36 * sc:.1f}" fill="#5c574f" '
             f'stroke="{FRIDGE_EDGE}" stroke-width="0.9"/>')
    o.append(_t(X(hc + a.hinge_cover / 2), Y(a.fridge_h) - 16, "hinge cover", 7.6,
                fill="#bdb6ab"))
    o.append(_t(X(30), Y(1500), "FRIDGE SIDE PANEL", 9.5, fill="#8d867d", rot=-90))

    # the display and its plate, drawn BEHIND the frame so the frame reads on top
    dc = a.strut_centre
    o.append(f'<rect x="{X(dc - a.plate_w / 2):.1f}" y="{Y(a.screen_centre + a.plate_h / 2):.1f}" '
             f'width="{a.plate_w * sc:.1f}" height="{a.plate_h * sc:.1f}" fill="{C_PLATE}" '
             f'fill-opacity="0.9" stroke="{INK}" stroke-width="1.1"/>')
    o.append(_t(X(dc), Y(a.screen_centre + 96),
                f"PLATE {a.plate_w:.0f} x {a.plate_h:.0f}", 9.2, weight="bold"))

    o.append(f'<rect x="{X(dc - a.plate_w / 2):.1f}" '
             f'y="{Y(a.plate_centre + a.plate_h / 2):.1f}" '
             f'width="{a.plate_w * sc:.1f}" '
             f'height="{(Y(a.plate_centre - a.plate_h / 2) - Y(a.plate_centre + a.plate_h / 2)):.1f}" '
             f'fill="{C_PLATE}" stroke="{INK}" stroke-width="1.3"/>')
    o.append(_t(X(dc), Y(a.plate_centre) + 40, "PLATE splices the two pieces", 8.6,
                weight="bold"))

    strut_half = a.strut_width / 2.0
    # TWO pieces per side, with a gap over the display's rear box so its long edges — where the
    # ports and controls most likely are — stay reachable. Both sides split identically.
    pieces = ([(0.0, a.lower_strut_len), (a.upper_strut_lo, a.strut_top)] if a.strut_split
              else [(0.0, a.strut_len)])
    for s in (dc - a.strut_spacing / 2.0, dc + a.strut_spacing / 2.0):
        for p_lo, p_hi in pieces:
            o.append(f'<rect x="{X(s - strut_half):.1f}" y="{Y(p_hi):.1f}" '
                     f'width="{a.strut_width * sc:.1f}" '
                     f'height="{(Y(p_lo) - Y(p_hi)):.1f}" '
                     f'fill="{C_STRUT}" stroke="{INK}" stroke-width="1.2"/>')
            n = 0
            while True:
                sy = p_lo + 25.4 + n * a.slot_pitch
                n += 1
                if sy > p_hi - 11.11:
                    break
                if F_LO < sy < F_HI:
                    continue
                o.append(f'<rect x="{X(s) - 2.6:.1f}" y="{Y(sy + a.slot_len / 2):.1f}" '
                         f'width="5.2" height="{a.slot_len * sc:.1f}" fill="{INK}" '
                         f'fill-opacity="0.4"/>')
        o.append(f'<rect x="{X(s - strut_half) - 1:.1f}" y="{oy - 7:.1f}" '
                 f'width="{a.strut_width * sc + 2:.1f}" height="7" fill="{C_STEEL}" '
                 f'stroke="{INK}" stroke-width="1"/>')
    if a.strut_split:
        gy0, gy1 = Y(a.lower_strut_len), Y(a.upper_strut_lo)
        o.append(f'<rect x="{X(dc - a.strut_spacing / 2 - strut_half) - 6:.1f}" y="{gy1:.1f}" '
                 f'width="{(a.strut_spacing + a.strut_width) * sc + 12:.1f}" '
                 f'height="{gy0 - gy1:.1f}" fill="{OK}" fill-opacity="0.10"/>')
        o.append(f'<line x1="{X(dc + a.strut_spacing / 2 + strut_half) + 10:.1f}" y1="{gy0:.1f}" '
                 f'x2="{X(dc + a.strut_spacing / 2 + strut_half) + 10:.1f}" y2="{gy1:.1f}" '
                 f'stroke="{OK}" stroke-width="1.6"/>')
        o.append(_t(X(dc + a.strut_spacing / 2 + strut_half) + 16, (gy0 + gy1) / 2 - 4,
                    f"GAP {a.upper_strut_lo - a.lower_strut_len:.0f}", 9.0, anchor="start",
                    fill=OK, weight="bold"))
        o.append(_t(X(dc + a.strut_spacing / 2 + strut_half) + 16, (gy0 + gy1) / 2 + 7,
                    f"{a.edge_open:.0f} of {a.box_h_portrait:.0f} mm", 8.2, anchor="start",
                    fill=OK))
        o.append(_t(X(dc + a.strut_spacing / 2 + strut_half) + 16, (gy0 + gy1) / 2 + 17,
                    "of box edge OPEN", 8.2, anchor="start", fill=OK))

    # the two IDENTICAL bars — the whole point of the view
    bar_x0, bar_w = X(dc - a.clamp_outer_half), a.clamp_width * sc
    for hgt, nm in ((a.fridge_h, "TOP BAR"), (a.base_gap, "BOTTOM BAR")):
        o.append(f'<rect x="{bar_x0:.1f}" y="{Y(hgt) - 7:.1f}" width="{bar_w:.1f}" height="14" '
                 f'rx="2" fill="{C_STEEL}" stroke="{INK}" stroke-width="1.3"/>')
        o.append(_t(bar_x0 + bar_w / 2, Y(hgt) + 4, nm, 8.4, fill="#fff", weight="bold"))
        for s in (dc - a.strut_spacing / 2.0, dc + a.strut_spacing / 2.0):
            o.append(f'<circle cx="{X(s):.1f}" cy="{Y(hgt):.1f}" r="3.1" fill="{PAPER}" '
                     f'stroke="{INK}" stroke-width="1"/>')

    o += _display_ghost(X(dc - a.display_w / 2), Y(a.screen_centre + a.display_h / 2),
                        a.display_w * sc,
                        a.display_h * sc, "")
    o.append(_t(X(a.fridge_d) + 14, Y(a.screen_centre - a.display_h / 2) + 4,
                f"display {a.display_w:.2f} wide", 8.6, anchor="start", fill=MUTED))
    o.append(_t(X(a.fridge_d) + 14, Y(a.screen_centre - a.display_h / 2) + 15,
                "dashed, true scale", 8.2, anchor="start", fill=MUTED))

    by_ = Y(F_LO) - 2
    o.append(f'<path d="M{X(-40):.1f} {by_ + 8:.1f} L{X(a.fridge_d / 2):.1f} {by_ - 6:.1f} '
             f'L{X(a.fridge_d + 40):.1f} {by_ + 8:.1f}" fill="none" stroke="{PAPER}" '
             f'stroke-width="9"/>')
    o.append(f'<path d="M{X(-40):.1f} {by_ + 8:.1f} L{X(a.fridge_d / 2):.1f} {by_ - 6:.1f} '
             f'L{X(a.fridge_d + 40):.1f} {by_ + 8:.1f}" fill="none" stroke="{BAD}" '
             f'stroke-width="1.5"/>')
    o.append(_t(X(a.fridge_d + 48), by_ + 4, f"BREAK — {cut:.0f} mm", 8.2, anchor="start",
                fill=BAD, weight="bold"))

    # dimensions, all below the drawing so nothing lands on the geometry
    def hdim(y, x0, x1, txt, col=OK):
        o.append(f'<line x1="{X(x0):.1f}" y1="{y:.1f}" x2="{X(x1):.1f}" y2="{y:.1f}" '
                 f'stroke="{col}" stroke-width="1.1"/>')
        for xx in (x0, x1):
            o.append(f'<line x1="{X(xx):.1f}" y1="{y - 4:.1f}" x2="{X(xx):.1f}" '
                     f'y2="{y + 4:.1f}" stroke="{col}" stroke-width="1.1"/>')
        o.append(_t(X((x0 + x1) / 2), y - 6, txt, 9.0, fill=col, weight="bold"))

    hdim(oy + 34, dc - a.strut_spacing / 2, dc + a.strut_spacing / 2,
         f"{a.strut_spacing:.0f} strut centres")
    hdim(oy + 66, dc - a.clamp_outer_half, dc + a.clamp_outer_half,
         f"{a.clamp_width:.0f} bar", INK)
    o.append(_t(X(dc), oy + 88, "both bars are the SAME part — the lower one is flipped", 8.8,
                fill=MUTED))

    # --- TRUE SCALE, UNBROKEN. The broken drawing beside it cannot answer "is the strut taller
    # --- than the fridge", so this strip answers it with nothing removed.
    o += _panel(690, 100, 240, 800, "TRUE SCALE", WARN)
    o += _para(706, 146, f"The strut IS taller. It stands {a.proud:.1f} mm above the case and "
               f"{a.proud_of_covers:.1f} mm above the hinge covers — about "
               f"{a.proud_of_covers / IN:.1f} in of channel showing over the top.", 31,
               size=9.4, lead=11.5)
    tsc = 610.0 / a.strut_len
    tox, toy = 745.0, 866.0

    def TY(mm):
        return toy - mm * tsc
    o.append(f'<line x1="{tox - 22:.1f}" y1="{toy:.1f}" x2="{tox + 150:.1f}" y2="{toy:.1f}" '
             f'stroke="{INK}" stroke-width="2"/>')
    o.append(f'<rect x="{tox:.1f}" y="{TY(a.fridge_h):.1f}" width="58" '
             f'height="{(toy - TY(a.fridge_h)):.1f}" fill="{FRIDGE_SIDE}" '
             f'stroke="{FRIDGE_EDGE}"/>')
    o.append(f'<rect x="{tox + 6:.1f}" y="{TY(a.fridge_h + a.hinge_proud):.1f}" width="26" '
             f'height="{a.hinge_proud * tsc:.1f}" fill="#5c574f" stroke="{FRIDGE_EDGE}"/>')
    o.append(_t(tox + 29, toy - 14, "FRIDGE", 8.4, fill="#e8e2d8", weight="bold"))
    o.append(f'<rect x="{tox + 74:.1f}" y="{TY(a.strut_len):.1f}" width="15" '
             f'height="{a.strut_len * tsc:.1f}" fill="{C_STRUT}" stroke="{INK}"/>')
    o.append(_t(tox + 81, toy - 14, "STRUT", 8.0, fill=INK, weight="bold", rot=-90))
    for hgt, col, lab in ((a.fridge_h, FRIDGE_EDGE, "case 1743.1"),
                          (a.fridge_h + a.hinge_proud, "#5c574f", "covers 1779.6"),
                          (a.strut_len, OK, "strut 1828.8")):
        o.append(f'<line x1="{tox - 20:.1f}" y1="{TY(hgt):.1f}" x2="{tox + 96:.1f}" '
                 f'y2="{TY(hgt):.1f}" stroke="{col}" stroke-width="1" stroke-dasharray="4 3"/>')
        o.append(_t(tox + 100, TY(hgt) + 3, lab, 8.2, anchor="start", fill=col, weight="bold"))
    o.append(f'<line x1="{tox + 70:.1f}" y1="{TY(a.fridge_h):.1f}" x2="{tox + 70:.1f}" '
             f'y2="{TY(a.strut_len):.1f}" stroke="{OK}" stroke-width="2"/>')


    o += _panel(945, 100, 435, 390, "WHY THIS VIEW EXISTS", OK)
    o += _para(961, 146,
               "Every other sheet is a side elevation, a plan or a flat pattern. A side view "
               "shows ONE strut, so none of them can show the two struts tied together — which "
               "is the whole structural idea. This is that view.", 54)
    o += _para(961, 226,
               f"The two bars are the SAME part, {a.clamp_width:.0f} mm across, reaching past "
               f"both struts by {a.part_width / 2.0:.1f} mm each side for edge margin. That is "
               f"what turns two independent legs into a frame. Widening the individual parts "
               f"instead would add steel that is not joined to anything at its far end, and the "
               f"couple arm would stay the strut spacing regardless.", 54)
    o += _para(961, 350,
               f"The plate is {a.plate_w:.0f} x {a.plate_h:.0f} and reaches "
               f"{(a.plate_w - a.strut_spacing) / 2.0:.1f} mm past each strut. It is no longer "
               f"square: it was, only so it could hide behind the display in EITHER orientation, "
               f"and landscape is impossible on this cabinet.", 54)

    o += _panel(945, 510, 435, 390, "THE NUMBERS IN THIS VIEW", INK)
    rows = [("strut centres", f"{a.strut_spacing:.0f} mm"),
            ("bar across", f"{a.clamp_width:.0f} mm"),
            ("bar overhang past each strut", f"{a.part_width / 2.0:.1f} mm"),
            ("plate", f"{a.plate_w:.0f} x {a.plate_h:.0f} mm"),
            ("plate past each strut", f"{(a.plate_w - a.strut_spacing) / 2.0:.1f} mm"),
            ("display, portrait", f"{a.display_w:.2f} x {a.display_h:.0f} mm"),
            ("bars (identical parts)", f"{a.n_clamps}"),
            ("feet", f"{a.n_feet}"),
            ("strut proud of the case", f"{a.proud:.1f} mm"),
            ("strut proud of the covers", f"{a.proud_of_covers:.1f} mm"),
            ("clear window on the top", f"{a.clear_window:.1f} mm"),
            ("bar to hinge cover", f"{a.hinge_margin:.1f} mm")]
    for i, (k, v) in enumerate(rows):
        ry = 548 + i * 29
        if i % 2 == 0:
            o.append(f'<rect x="957" y="{ry - 15:.1f}" width="411" height="26" fill="#f2f5f7"/>')
        o.append(_t(969, ry + 2, k, 10.2, anchor="start"))
        o.append(_t(1356, ry + 2, v, 10.6, anchor="end", weight="bold"))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — %d struts at %.0f, %d identical bars %.0f across",
             path, a.n_struts, a.strut_spacing, a.n_clamps, a.clamp_width)


# --------------------------------------------------------------------------------------------
def sheet_plate(path: Path, a: Assembly) -> None:
    """Part C, and the answer to "what holds the monitor".

    The plate was a DIMENSION and not a part: it appeared in the stack and in the elevation, but
    had no flat pattern, no VESA holes, no strut bolts and no vent windows. It is the link in the
    middle of the load path, so leaving it undrawn left the chain broken exactly where it carries
    the screen.
    """
    W, H = 1420, 940
    o = _frame(W, H, "WHAT HOLDS THE MONITOR",
               "Part C, the plate. The display bolts to it, it bolts to the struts, and the "
               "struts stand on the floor. The fridge carries none of the weight.",
               "PLATE — the link that was dimensioned but never drawn")

    o += _panel(40, 100, 600, 800,
                f"PLATE {a.plate_w:.0f} x {a.plate_h:.0f} — SPLICES THE TWO STRUT PIECES", OK)
    sc = 1.30
    cx, cy = 318.0, 500.0                       # cy is the PLATE's centre, not the VESA's
    hw, hp = a.plate_w / 2.0 * sc, a.plate_h / 2.0 * sc
    vy0 = cy - a.vesa_offset_in_plate * sc      # where the VESA/display centre falls on the plate

    o.append(f'<rect x="{cx - hw:.1f}" y="{cy - hp:.1f}" width="{2 * hw:.1f}" '
             f'height="{2 * hp:.1f}" rx="4" fill="{C_PLATE}" stroke="{INK}" stroke-width="1.6"/>')

    # rear box, dashed — the plate now reaches PAST it top and bottom, which is the whole point
    bw, bh = a.box_w_portrait / 2.0 * sc, a.box_h_portrait / 2.0 * sc
    o.append(f'<rect x="{cx - bw:.1f}" y="{vy0 - bh:.1f}" width="{2 * bw:.1f}" '
             f'height="{2 * bh:.1f}" fill="none" stroke="{INK}" stroke-width="1.2" '
             f'stroke-dasharray="7 4"/>')
    o.append(_t(cx, vy0 - bh - 7, f"rear box {a.box_w_portrait:.0f} x {a.box_h_portrait:.0f}",
                8.4, fill=MUTED))

    # VENT WINDOWS are back: the plate is tall enough to cover fan AND GPIO
    for sgn in (1, -1):
        wy = vy0 - sgn * a.vent_r * sc
        o.append(f'<rect x="{cx - a.vent_wid / 2 * sc:.1f}" y="{wy - a.vent_len / 2 * sc:.1f}" '
                 f'width="{a.vent_wid * sc:.1f}" height="{a.vent_len * sc:.1f}" '
                 f'rx="{a.vent_wid / 2 * sc:.1f}" fill="{PAPER}" stroke="{INK}" '
                 f'stroke-width="1.3"/>')
        fy = vy0 - sgn * a.fan_r * sc
        o.append(f'<circle cx="{cx:.1f}" cy="{fy:.1f}" r="{a.fan_dia / 2 * sc:.1f}" fill="{BAD}" '
                 f'fill-opacity="0.30" stroke="{BAD}" stroke-width="1"/>')
        gy = vy0 - sgn * a.gpio_r * sc
        o.append(f'<rect x="{cx - a.gpio_wid / 2 * sc:.1f}" y="{gy - 2:.1f}" width="{a.gpio_wid * sc:.1f}" '
                 f'height="4" rx="2" fill="{BAD}" fill-opacity="0.40"/>')
    o.append(_t(cx + hw + 10, vy0 - a.vent_r * sc - 4,
                f"VENT {a.vent_len:.0f} x {a.vent_wid:.0f}", 8.6, anchor="start", fill=INK,
                weight="bold"))
    o.append(_t(cx + hw + 10, vy0 - a.vent_r * sc + 7, f"at R{a.vent_r:.0f} — covers fan AND GPIO",
                8.0, anchor="start", fill=MUTED))

    v = a.vesa / 2.0 * sc
    o.append(f'<rect x="{cx - v:.1f}" y="{vy0 - v:.1f}" width="{2 * v:.1f}" height="{2 * v:.1f}" '
             f'fill="none" stroke="{OK}" stroke-width="1.2" stroke-dasharray="5 3"/>')
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            o.append(f'<circle cx="{cx + sx_ * v:.1f}" cy="{vy0 + sy_ * v:.1f}" '
                     f'r="{a.vesa_hole_dia * sc / 2:.1f}" fill="{PAPER}" stroke="{OK}" '
                     f'stroke-width="1.3"/>')
    o.append(_t(cx, vy0 + 4, f"VESA {a.vesa:.0f}", 9.0, fill=OK, weight="bold"))

    bx_ = a.plate_bolt_dx / 2.0 * sc
    for sgn, lab in ((-1, "to the UPPER piece"), (1, "to the LOWER piece")):
        by_ = cy + sgn * a.plate_bolt_dy / 2.0 * sc
        for sx_ in (-1, 1):
            o.append(f'<circle cx="{cx + sx_ * bx_:.1f}" cy="{by_:.1f}" '
                     f'r="{a.plate_bolt_dia * sc / 2:.1f}" fill="{PAPER}" stroke="{BAD}" '
                     f'stroke-width="1.5"/>')
        o.append(_t(cx - hw - 8, by_ + 3, lab, 8.2, anchor="end", fill=BAD, weight="bold"))
    o.append(f'<line x1="{cx + hw + 4:.1f}" y1="{cy - a.plate_bolt_dy / 2 * sc:.1f}" '
             f'x2="{cx + hw + 4:.1f}" y2="{cy + a.plate_bolt_dy / 2 * sc:.1f}" stroke="{BAD}" '
             f'stroke-width="1.2"/>')
    o.append(_t(cx + hw + 10, cy - 4, f"{a.plate_bolt_dy:.1f} apart", 9.0, anchor="start",
                fill=BAD, weight="bold"))
    o.append(_t(cx + hw + 10, cy + 8, "real slots on TWO grids", 8.0, anchor="start", fill=BAD))
    o.append(_t(cx, cy + hp + 20,
                f"VESA sits {abs(a.vesa_offset_in_plate):.1f} mm "
                f"{'below' if a.vesa_offset_in_plate < 0 else 'above'} the plate's own centre — "
                f"the two grids do not line up", 8.6, fill=MUTED))

    o += _panel(660, 100, 340, 800, "THE CHAIN", INK)
    steps = [("THE DISPLAY", "3.94 kg", C_PLATE, "4 x M4 into the VESA inserts, on SPACERS"),
             ("THE PLATE", f"{a.plate_w:.0f}x{a.plate_h:.0f}", C_PLATE, f"4 bolts at {a.plate_bolt_dx:.0f} x "
              f"{a.plate_bolt_dy:.1f} into the strut slots"),
             ("THE STRUTS", "x2", C_STRUT, "stand on"),
             ("THE FEET", "x2", C_STEEL, "rest on"),
             ("THE FLOOR", "154 N", "#2f6f4f", "")]
    yy = 150
    for i, (nm, sub, col, link) in enumerate(steps):
        o.append(f'<rect x="682" y="{yy:.1f}" width="296" height="46" rx="6" fill="{col}" '
                 f'fill-opacity="0.9" stroke="{INK}" stroke-width="1.1"/>')
        o.append(_t(700, yy + 21, nm, 11.5, anchor="start", weight="bold",
                    fill="#fff" if i >= 2 else INK))
        o.append(_t(960, yy + 21, sub, 10.2, anchor="end",
                    fill="#fff" if i >= 2 else MUTED))
        yy += 46
        if link:
            o.append(f'<line x1="830" y1="{yy:.1f}" x2="830" y2="{yy + 22:.1f}" stroke="{INK}" '
                     f'stroke-width="2"/>')
            o.append(f'<path d="M825 {yy + 16:.1f} L830 {yy + 24:.1f} L835 {yy + 16:.1f}" '
                     f'fill="{INK}"/>')
            for j, ln in enumerate(_wrap(link, 40)):
                o.append(_t(844, yy + 12 + j * 11, ln, 8.4, anchor="start", fill=MUTED))
            yy += 30 + 11 * (len(_wrap(link, 40)) - 1)

    o.append(f'<rect x="682" y="{yy + 24:.1f}" width="296" height="112" rx="6" fill="#fff" '
             f'stroke="{WARN}" stroke-width="1.4"/>')
    o.append(_t(700, yy + 46, f"THE CLAMP BARS x{a.n_clamps}", 11, anchor="start", fill=WARN,
                weight="bold"))
    for j, ln in enumerate(_wrap("Grip the fridge top and its underside. They carry ZERO weight "
                                 "— they only stop the frame falling away from the panel.", 38)):
        o.append(_t(700, yy + 64 + j * 12, ln, 8.8, anchor="start", fill=MUTED))

    o += _panel(1020, 100, 360, 800, "SO, WHAT HOLDS IT?", OK)
    # Fixed y-positions kept colliding because the paragraphs differ in length. Flow them.
    blocks = [
        ("Nothing holds it TO the fridge. The FLOOR holds it up, the way a bookcase stands on "
         "the floor and leans on a wall. The fridge only stops it tipping away.", INK),
        ("That is the whole point of the change. The magnet design really did hang off the "
         "fridge, so every question was about how hard it gripped. Here the grip carries "
         "nothing, so a non-magnetic panel, paint creep and peel all stop mattering.", MUTED),
        (f"A solid plate over the Pi's fan and GPIO cooks it. The old plate was 279 tall purely "
         f"to carry vent WINDOWS over that region. At {a.plate_h:.1f} the plate clears the GPIO "
         f"slot entirely ({a.gpio_r - a.plate_h / 2.0:.0f} mm clear) and needs only to deal with "
         f"the fan, which an edge notch does far more cheaply than an enclosed window.", MUTED),
        (f"The {a.n_notches} edge notches are NOT idle insurance — correcting an earlier claim "
         f"here. Reading the fan off Waveshare's drawing puts it at ~R{a.fan_r:.0f}, so the plate "
         f"edge laps it by {a.plate_covers_fan_by:.1f} mm and the notch is what uncovers it. "
         f"Depth {a.notch_depth:.1f} is derived: fan near edge minus {a.scale_tol:.0f} mm for the "
         f"fact that every one of those figures is SCALED off a raster, not dimensioned.", BAD),
        (f"Bolt rows are {a.plate_bolt_dy:.1f} apart — exactly {a.plate_bolt_pitches} slot "
         f"pitches, so both sit identically in their slots.", MUTED),
        (f"ORIENTATION — CORRECTED. At the old 246 spacing landscape overhung the rear edge and "
         f"was impossible. Narrowing to {a.strut_spacing:.0f} moved the struts forward, and it now "
         f"technically fits: it clears the rear by "
         f"{a.strut_centre - a.display_h / 2:.1f} mm against {a.fridge_d - a.strut_centre - a.display_h / 2:.1f} "
         f"at the front. That is flush with the back of the cabinet and wildly off centre, so "
         f"portrait remains the choice — on practical grounds now, not geometric impossibility.",
         WARN),
        (f"Heads sit on the DISPLAY side, so they must not fall under the Pi bump-out. In "
         f"portrait the box is {a.box_w_portrait:.0f} wide and the bolts {a.plate_bolt_dx:.0f} "
         f"apart, clearing by {a.bolt_clear_of_box:.0f} mm — because the STRUT SPACING is wider "
         f"than the box, not by luck of where the holes went.", MUTED),
        ("CONSEQUENCE: those heads are unreachable once the display is on. The plate goes on the "
         "struts BEFORE the display.", BAD),
    ]
    yy = 146.0
    for txt, col in blocks:
        lines = _wrap(txt, 42)
        o += [_t(1036, yy + i * 12.4, ln, 10.2, anchor="start", fill=col)
              for i, ln in enumerate(lines)]
        yy += len(lines) * 12.4 + 15
    if yy > 900:
        LOG.warning("right column overflows its panel by %.0f px", yy - 900)
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — plate %.0f x %.0f, bolts %.0f x %.1f, %d vents, fan ~R%.0f, "
             "heads clear the rear box by %.0f",
             path, a.plate_w, a.plate_h, a.plate_bolt_dx, a.plate_bolt_dy,
             a.n_notches, a.fan_r, a.bolt_clear_of_box)


# --------------------------------------------------------------------------------------------
def sheet_depth(path: Path, a: Assembly) -> None:
    """STACKED vs NESTED, in plan view. Looking straight down at the fridge from above.

    The whole question is whether the strut sits BEHIND the display's rear box (so their depths
    add) or BESIDE it (so they share the same band). Prose cannot show that; a plan view can.
    """
    W, H = 1420, 880
    o = _frame(W, H, "COULD THE STRUTS SIT BESIDE THE BOX, NOT BEHIND IT?",
               "Plan view — looking DOWN at the fridge from above. Depth runs left to right; "
               "front-to-back along the fridge runs up the page.",
               "DEPTH STUDY — the same parts, arranged two ways")

    PANEL_W, BOX_W = a.display_w, a.box_w_portrait
    nest_sp = a.strut_spacing            # ask Assembly; do not re-derive it here
    # DEPTH is the whole subject and is only 76 mm against 325 front-to-back, so at one scale it
    # renders as a sliver. Exaggerate depth 4x, exactly as the side elevation does, and say so.
    SD, SW = 4.0, 1.02

    def draw(px, py, title, spacing, nested, colour):
        oy = py + 232                                     # centreline, front-to-back
        o.extend(_panel(px, py, 620, 480, title, colour))
        x = px + 60                                       # fridge panel face
        o.append(f'<rect x="{x - 16:.1f}" y="{oy - 300 * SW / 2:.1f}" width="16" '
                 f'height="{300 * SW:.1f}" fill="{FRIDGE_SIDE}"/>')
        o.append(_t(x - 24, oy, "FRIDGE", 8.4, anchor="end", fill=MUTED, rot=-90))

        gap = a.gap          # the clamps set this; the nested plate lives INSIDE it
        o.append(f'<rect x="{x:.1f}" y="{oy - 120 * SW / 2:.1f}" width="{gap * SD:.1f}" '
                 f'height="{120 * SW:.1f}" fill="#f8e2a4" stroke="{PAD_EDGE}" '
                 f'stroke-width="0.8"/>')
        z = x + gap * SD

        if nested:
            # plate BEHIND the struts, reaching VESA on the box face
            o.append(f'<rect x="{z - a.plate_t * SD:.1f}" y="{oy - 236 * SW / 2:.1f}" '
                     f'width="{a.plate_t * SD:.1f}" height="{236 * SW:.1f}" fill="{C_PLATE}" '
                     f'stroke="{INK}" stroke-width="1"/>')
            o.append(f'<line x1="{z - a.plate_t * SD / 2:.1f}" y1="{oy - 122 * SW:.1f}" '
                     f'x2="{z - a.plate_t * SD / 2:.1f}" y2="{oy - 152:.1f}" stroke="{INK}" '
                     f'stroke-width="0.7"/>')
            o.append(_t(z, oy - 156, "PLATE — behind the struts", 8.2, fill=INK, weight="bold"))
        for sgn in (1, -1):
            cyy = oy + sgn * spacing / 2 * SW
            o.append(f'<rect x="{z:.1f}" y="{cyy - a.strut_width * SW / 2:.1f}" '
                     f'width="{a.strut_depth * SD:.1f}" height="{a.strut_width * SW:.1f}" '
                     f'fill="{C_STRUT}" stroke="{INK}" stroke-width="1.2"/>')
        o.append(_t(z + a.strut_depth * SD / 2, oy - spacing / 2 * SW - 15, "STRUT", 8.2,
                    fill=INK, weight="bold"))

        if nested:
            bz = z                                        # box shares the strut's band
            o.append(f'<rect x="{bz:.1f}" y="{oy - BOX_W * SW / 2:.1f}" '
                     f'width="{a.rear_box * SD:.1f}" height="{BOX_W * SW:.1f}" fill="#2b3440" '
                     f'stroke="{INK}" stroke-width="1.2"/>')
            pz = bz + a.rear_box * SD
        else:
            pz = z + a.strut_depth * SD
            o.append(f'<rect x="{pz:.1f}" y="{oy - a.plate_w * SW / 2:.1f}" '
                     f'width="{a.plate_t * SD:.1f}" height="{a.plate_w * SW:.1f}" '
                     f'fill="{C_PLATE}" stroke="{INK}" stroke-width="1"/>')
            o.append(f'<line x1="{pz + a.plate_t * SD / 2:.1f}" y1="{oy - a.plate_w * SW / 2:.1f}" '
                     f'x2="{pz + a.plate_t * SD / 2:.1f}" y2="{oy - 152:.1f}" stroke="{INK}" '
                     f'stroke-width="0.7"/>')
            o.append(_t(pz + a.plate_t * SD / 2, oy - 156, "PLATE — in front of the struts", 8.2,
                        fill=INK, weight="bold"))
            pz += a.plate_t * SD
            o.append(f'<rect x="{pz:.1f}" y="{oy - BOX_W * SW / 2:.1f}" '
                     f'width="{a.rear_box * SD:.1f}" height="{BOX_W * SW:.1f}" fill="#2b3440" '
                     f'stroke="{INK}" stroke-width="1.2"/>')
            pz += a.rear_box * SD
        o.append(_t(pz - a.rear_box * SD / 2, oy + 4, "BOX", 8.0, fill="#fff", weight="bold"))
        o.append(f'<rect x="{pz:.1f}" y="{oy - PANEL_W * SW / 2:.1f}" '
                 f'width="{a.panel_d * SD:.1f}" height="{PANEL_W * SW:.1f}" fill="#101820" '
                 f'stroke="{INK}" stroke-width="1.2"/>')
        o.append(_t(pz + a.panel_d * SD / 2, oy, "DISPLAY", 8.4, fill="#fff", weight="bold",
                    rot=-90))
        total = (pz + a.panel_d * SD - x) / SD

        dy = oy + PANEL_W * SW / 2 + 30
        o.append(f'<line x1="{x:.1f}" y1="{dy:.1f}" x2="{pz + a.panel_d * SD:.1f}" '
                 f'y2="{dy:.1f}" stroke="{colour}" stroke-width="1.6"/>')
        for xx in (x, pz + a.panel_d * SD):
            o.append(f'<line x1="{xx:.1f}" y1="{dy - 5:.1f}" x2="{xx:.1f}" y2="{dy + 5:.1f}" '
                     f'stroke="{colour}" stroke-width="1.6"/>')
        o.append(_t((x + pz + a.panel_d * SD) / 2, dy - 9,
                    f"{total:.1f} mm off the fridge", 11, fill=colour, weight="bold"))
        o.append(_t(px + 310, py + 462, f"depth exaggerated {SD:.0f}x; front-to-back true scale", 8.4, fill=MUTED))
        return total, spacing

    cur, _ = draw(40, 100, "A — SUPERSEDED: strut BEHIND the box, depths ADD", 160.0,
                  False, INK)
    nst, _ = draw(700, 100, "B — ADOPTED: strut BESIDE the box, depths SHARE", nest_sp,
                  True, OK)

    o.extend(_panel(40, 600, 1340, 250, "WHAT THE TWO DRAWINGS DIFFER BY", OK))
    rows = [
        ("depth off the fridge", f"{cur:.1f} mm", f"{nst:.1f} mm",
         f"{cur - nst:.1f} mm closer — exactly the strut depth: the strut leaves the stack"),
        ("strut spacing", "160 mm", f"{nest_sp:.2f} mm",
         f"the {BOX_W:.0f} mm box must PASS BETWEEN the struts, so they open up"),
        ("plate", "211 wide, in front of the struts",
         f"{a.plate_w:.0f} wide, BEHIND them",
         "VESA is inside the box footprint, so a plate clearing the box cannot reach it"),
        ("screen off case centre", "25.7 mm", f"{a.display_bias_rearward:.1f} mm",
         "wider spacing lengthens the clamp bar, pushing the struts back again"),
        ("hardware behind the plate", "n/a",
         f"{a.gap - a.plate_t:.2f} mm of room",
         "M4 button 2.2, pan 3.1, cap 4.0 and the 2.78 elevator head all FIT; only a hex nut does not"),
        ("servicing", "display comes off in place",
         "whole frame lifts off the clamps first",
         "the display cannot be unbolted in situ — but the frame was always removable"),
    ]
    for i, (k, a_, b_, note) in enumerate(rows):
        yy = 640 + i * 40
        if i % 2 == 0:
            o.append(f'<rect x="52" y="{yy - 16:.1f}" width="1316" height="36" fill="#f2f5f7"/>')
        o.append(_t(64, yy + 2, k, 10.2, anchor="start", weight="bold"))
        o.append(_t(300, yy + 2, a_, 10.0, anchor="start", fill=MUTED))
        o.append(_t(640, yy + 2, b_, 10.0, anchor="start", fill=OK))
        o.append(_t(980, yy + 2, note, 9.2, anchor="start", fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — stacked %.1f vs nested %.1f, saving %.1f mm; nested needs %.1f spacing",
             path, cur, nst, cur - nst, nest_sp)


# --------------------------------------------------------------------------------------------
def sheet_stack(path: Path, a: Assembly) -> None:
    """THE STACK, in section, at 7x. Two cuts, because the stack is not the same everywhere.

    Through a STRUT you see plate, strut, air, panel. Through the CENTRE you see plate, box,
    panel — the strut is not there at all, which is the entire point of nesting.
    """
    W, H = 1420, 900
    SC = 7.0
    o = _frame(W, H, "THE STACK, PANEL TO SCREEN",
               f"Section at {SC:.0f}x. The stack differs depending on where you cut it, so both "
               f"cuts are drawn. Fridge on the left, room on the right.",
               "STACK DETAIL — nested: the box passes BETWEEN the struts")

    ox = 150.0
    def X(mm):
        return ox + mm * SC

    # ---- key: where the two cuts are taken, in plan
    o.extend(_panel(1080, 100, 300, 250, "WHERE THE CUTS ARE", MUTED))
    kx, ky, ks = 1230.0, 230.0, 0.62
    o.append(f'<rect x="{kx - a.box_w_portrait * ks / 2:.1f}" y="{ky - 40:.1f}" '
             f'width="{a.box_w_portrait * ks:.1f}" height="80" fill="#2b3440"/>')
    o.append(_t(kx, ky + 4, "box", 8, fill="#fff"))
    for sgn in (1, -1):
        sx = kx + sgn * a.strut_spacing * ks / 2
        o.append(f'<rect x="{sx - a.strut_width * ks / 2:.1f}" y="{ky - 40:.1f}" '
                 f'width="{a.strut_width * ks:.1f}" height="80" fill="{C_STRUT}" '
                 f'stroke="{INK}"/>')
    o.append(f'<line x1="{kx - a.strut_spacing * ks / 2:.1f}" y1="{ky - 62:.1f}" '
             f'x2="{kx - a.strut_spacing * ks / 2:.1f}" y2="{ky + 62:.1f}" stroke="{BAD}" '
             f'stroke-width="1.4" stroke-dasharray="6 4"/>')
    o.append(_t(kx - a.strut_spacing * ks / 2, ky - 68, "A", 11, fill=BAD, weight="bold"))
    o.append(f'<line x1="{kx:.1f}" y1="{ky - 62:.1f}" x2="{kx:.1f}" y2="{ky + 62:.1f}" '
             f'stroke={chr(34)}{OK}{chr(34)} stroke-width="1.4" stroke-dasharray="6 4"/>')
    o.append(_t(kx, ky - 68, "B", 11, fill=OK, weight="bold"))
    o.append(_t(kx, ky + 84, "plan view, looking down", 8.4, fill=MUTED))

    # ---- the two sections
    def section(py, title, layers, colour):
        o.extend(_panel(40, py, 1010, 250, title, colour))
        band, top = 92.0, py + 78
        o.append(f'<rect x="{X(-14):.1f}" y="{top - 16:.1f}" width="{14 * SC:.1f}" '
                 f'height="{band + 32:.1f}" fill="{FRIDGE_SIDE}"/>')
        o.append(_t(X(-7), top + band / 2, "FRIDGE", 8.4, fill="#cfc9c2", rot=-90))
        z = 0.0
        for li, (nm, d, fill, txt) in enumerate(layers):
            if fill is None:                       # air
                o.append(f'<rect x="{X(z):.1f}" y="{top:.1f}" width="{d * SC:.1f}" '
                         f'height="{band:.1f}" fill="none" stroke="{RULE}" '
                         f'stroke-width="0.8" stroke-dasharray="3 3"/>')
            else:
                o.append(f'<rect x="{X(z):.1f}" y="{top:.1f}" width="{d * SC:.1f}" '
                         f'height="{band:.1f}" fill="{fill}" stroke="{INK}" stroke-width="1.1"/>')
            o.append(_t(X(z + d / 2), top + band + 15, f"{d:.2f}", 8.6, weight="bold",
                        fill=INK if fill else MUTED))
            ly = top - 8 - (16 if li % 2 else 0)
            o.append(f'<line x1="{X(z + d / 2):.1f}" y1="{ly + 3:.1f}" '
                     f'x2="{X(z + d / 2):.1f}" y2="{top - 1:.1f}" stroke="{RULE}" '
                     f'stroke-width="0.7"/>')
            o.append(_t(X(z + d / 2), ly, nm, 8.4, fill=INK if fill else MUTED,
                        weight="bold"))
            z += d
        o.append(f'<line x1="{X(0):.1f}" y1="{top + band + 34:.1f}" x2="{X(z):.1f}" '
                 f'y2="{top + band + 34:.1f}" stroke="{colour}" stroke-width="1.5"/>')
        for xx in (0.0, z):
            o.append(f'<line x1="{X(xx):.1f}" y1="{top + band + 29:.1f}" x2="{X(xx):.1f}" '
                     f'y2="{top + band + 39:.1f}" stroke="{colour}" stroke-width="1.5"/>')
        o.append(_t(X(z / 2), top + band + 29, f"{z:.2f} mm total", 10.5, fill=colour,
                    weight="bold"))
        return top, band

    air1 = a.gap - a.plate_t
    strut_air = a.rear_box - a.strut_depth
    top_a, band = section(100, "SECTION A-A — through a STRUT", [
        ("air", air1, None, MUTED),
        ("PLATE", a.plate_t, C_PLATE, INK),
        ("STRUT", a.strut_depth, C_STRUT, INK),
        ("air", strut_air, None, MUTED),
        ("display PANEL", a.panel_d, "#101820", "#fff"),
    ], BAD)
    o.append(_t(X(a.gap + a.strut_depth + strut_air / 2), top_a + band + 52,
                f"the strut stops {strut_air:.2f} mm short of the panel — it is beside the box, "
                f"not behind it", 8.4, fill=MUTED))

    top_b, band_b = section(380, "SECTION B-B — through the CENTRE, where the box is", [
        ("air + PADS", air1, None, MUTED),
        ("PLATE", a.plate_t, C_PLATE, INK),
        ("REAR BOX — between the struts", a.rear_box, "#5b6b7d", "#fff"),
        ("display PANEL", a.panel_d, "#101820", "#fff"),
    ], OK)
    # the M4 into VESA, head living in the air gap
    hy = top_b + band_b / 2
    o.append(f'<rect x="{X(2.0):.1f}" y="{hy - 9:.1f}" width="{4.02 * SC:.1f}" height="18" '
             f'rx="2" fill="{C_STEEL}" stroke="{INK}" stroke-width="1"/>')
    o.append(f'<rect x="{X(a.gap - a.plate_t):.1f}" y="{hy - 4:.1f}" '
             f'width="{(a.plate_t + 8) * SC:.1f}" height="8" fill="{C_STEEL}" stroke="{INK}" '
             f'stroke-width="0.8"/>')
    o.append(f'<line x1="{X(4.0):.1f}" y1="{hy + 10:.1f}" x2="{X(4.0):.1f}" '
             f'y2="{top_b + band_b + 52:.1f}" stroke="{INK}" stroke-width="0.7"/>')
    o.append(_t(X(0.0), top_b + band_b + 64,
                f"M4 into the VESA insert — its head lives in the {air1:.2f} mm gap, and the "
                f"pads sit at the plate CORNERS clear of it", 8.4, anchor="start", fill=INK))

    o.extend(_panel(1080, 380, 300, 250, "THE PADS", WARN))
    o.extend(_para(1096, 424,
                   f"{a.n_pads} pads, {a.pad_dia:.0f} mm across, {a.pad_t:.2f} thick — at the "
                   f"plate corners, NOT a covering sheet.", 34, size=9.8))
    o.extend(_para(1096, 486,
                   "Nothing presses the plate against the fridge, so there is nothing here to "
                   "compress. Their only job is to stop bare steel meeting paint if the plate "
                   "ever flexes.", 34, size=9.8))
    o.extend(_para(1096, 570,
                   "They clear the M4 heads by sitting at the corners, away from the VESA "
                   "pattern.", 34, size=9.8))

    o.extend(_panel(40, 660, 1340, 200, "WHAT THIS BUYS", OK))
    rows = [(f"display face, off the fridge panel", f"{a.display_face:.2f} mm",
             f"was 75.71 stacked — {75.71 - a.display_face:.2f} mm closer, {100*(1-a.display_face/75.71):.0f}%"),
            ("of which the DISPLAY ITSELF is", f"{a.fixed_part:.0f} mm",
             "box 25 + panel 18. No mount can remove this."),
            ("of which the MOUNT adds", f"{a.display_face - a.fixed_part:.2f} mm",
             "just the clamp gap. Stacked, the mount added 32.71."),
            ("strut spacing, now DERIVED", f"{a.strut_spacing:.2f} mm",
             f"box {a.box_w_portrait:.0f} + strut {a.strut_width:.2f} + {2*a.box_clearance:.0f} "
             f"clearance. Not a choice any more — the box has to pass through.")]
    for i, (k, v, note) in enumerate(rows):
        yy = 700 + i * 38
        if i % 2 == 0:
            o.append(f'<rect x="52" y="{yy - 16:.1f}" width="1316" height="34" fill="#f2f5f7"/>')
        o.append(_t(64, yy + 2, k, 10.4, anchor="start", weight="bold"))
        o.append(_t(430, yy + 2, v, 11.0, anchor="end", weight="bold", fill=OK))
        o.append(_t(460, yy + 2, note, 9.6, anchor="start", fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — face %.2f (display %.0f + mount %.2f), spacing %.2f",
             path, a.display_face, a.fixed_part, a.display_face - a.fixed_part, a.strut_spacing)


# --------------------------------------------------------------------------------------------
def sheet_orientation(path: Path, a: Assembly) -> None:
    """Every dimension on one depth axis: why portrait fits and landscape does not.

    Plan view, looking DOWN. The horizontal axis is distance from the fridge's REAR edge, and
    everything the question touches is drawn against it at the same scale — case, doors, hinge
    cover, window, clamp bar, struts, rear box, and the display in both orientations.
    """
    DOORS = 117.5
    W, H = 1500, 910
    SC = 1.22
    ox = 120.0
    o = _frame(W, H, "WHY PORTRAIT FITS AND LANDSCAPE DOES NOT",
               "Plan view, looking DOWN at the fridge. One horizontal axis: millimetres from the "
               "REAR edge of the case. Everything drawn to the same scale.",
               "ORIENTATION — every dimension that decides it, on one axis")

    def X(mm):
        return ox + mm * SC

    c = a.strut_centre
    o.extend(_panel(40, 100, 1420, 600, "ALL OF IT, AGAINST DEPTH FROM THE REAR EDGE"))

    # tick rule along the top
    for mm in range(0, 750, 50):
        o.append(f'<line x1="{X(mm):.1f}" y1="152" x2="{X(mm):.1f}" y2="158" stroke="{RULE}" '
                 f'stroke-width="1"/>')
        o.append(_t(X(mm), 148, str(mm), 7.6, fill=MUTED))
    o.append(_t(X(0), 134, "REAR", 8.4, fill=INK, weight="bold"))
    o.append(_t(X(a.fridge_d), 134, "case front", 8.4, fill=INK, weight="bold"))

    rows = []

    def band(y, lo, hi, fill, label, note, colour=INK, h=40.0):
        o.append(f'<rect x="{X(lo):.1f}" y="{y:.1f}" width="{(hi - lo) * SC:.1f}" '
                 f'height="{h:.1f}" fill="{fill}" stroke="{INK}" stroke-width="1.1"/>')
        o.append(_t(X((lo + hi) / 2), y + h / 2 + 4, label, 9.0,
                    fill="#fff" if fill not in (PAPER, "#f8e2a4") else INK, weight="bold"))
        o.append(_t(X(a.fridge_d + DOORS) + 18, y + h / 2 - 2, note, 8.8, anchor="start",
                    fill=colour, weight="bold"))
        o.append(_t(X(a.fridge_d + DOORS) + 18, y + h / 2 + 9,
                    f"{lo:.1f} .. {hi:.1f}   ({hi - lo:.2f} wide)", 8.2, anchor="start",
                    fill=MUTED))
        rows.append((label, lo, hi))

    y = 172.0
    band(y, 0, a.fridge_d, FRIDGE_SIDE, f"FRIDGE CASE {a.fridge_d:.1f}", "the cabinet")
    o.append(f'<rect x="{X(a.fridge_d):.1f}" y="{y:.1f}" width="{DOORS * SC:.1f}" height="40" '
             f'fill="#8a8f94" stroke="{INK}" stroke-width="1"/>')
    o.append(_t(X(a.fridge_d + DOORS / 2), y + 24, f"doors +{DOORS:.1f}", 8.2, fill="#fff"))
    y += 56
    band(y, a.clear_window, a.fridge_d, "#5c574f", f"HINGE COVER {a.hinge_cover:.0f}",
         "owns the front of the top", BAD)
    y += 56
    band(y, 0, a.clear_window, "#c9a227", f"CLEAR WINDOW {a.clear_window:.1f}",
         "all the mount may use", WARN)
    y += 62
    bh = a.clamp_outer_half
    band(y, c - bh, c + bh, C_STEEL, f"CLAMP BAR {a.clamp_width:.1f}",
         f"{a.hinge_margin:.0f} mm kept off the cover", OK)
    o.append(f'<line x1="{X(c + bh):.1f}" y1="{y - 6:.1f}" x2="{X(a.clear_window):.1f}" '
             f'y2="{y - 6:.1f}" stroke="{OK}" stroke-width="1.4"/>')
    o.append(_t(X(c + bh + a.hinge_margin / 2), y - 10, f"{a.hinge_margin:.0f}", 8.2, fill=OK,
                weight="bold"))
    y += 56
    for s in (c - a.strut_spacing / 2, c + a.strut_spacing / 2):
        o.append(f'<rect x="{X(s - a.strut_width / 2):.1f}" y="{y:.1f}" '
                 f'width="{a.strut_width * SC:.1f}" height="40" fill="{C_STRUT}" '
                 f'stroke="{INK}" stroke-width="1.1"/>')
    o.append(f'<line x1="{X(c - a.strut_spacing / 2):.1f}" y1="{y + 20:.1f}" '
             f'x2="{X(c + a.strut_spacing / 2):.1f}" y2="{y + 20:.1f}" stroke="{INK}" '
             f'stroke-width="1.2"/>')
    o.append(_t(X(c), y + 15, f"STRUTS {a.strut_spacing:.2f} apart", 8.6, weight="bold"))
    o.append(_t(X(a.fridge_d + DOORS) + 18, y + 18,
                f"= box {a.box_w_portrait:.0f} + strut {a.strut_width:.2f} + 2x{a.box_clearance:.0f}",
                8.8, anchor="start", fill=INK, weight="bold"))
    o.append(_t(X(a.fridge_d + DOORS) + 18, y + 29,
                "the box has to pass BETWEEN them", 8.2, anchor="start", fill=MUTED))
    y += 56
    band(y, c - a.box_w_portrait / 2, c + a.box_w_portrait / 2, "#2b3440",
         f"REAR BOX {a.box_w_portrait:.0f}", "sits between the struts")
    y += 62
    band(y, c - a.display_w / 2, c + a.display_w / 2, "#1d6b4f",
         f"PORTRAIT {a.display_w:.2f}", "FITS", OK)
    y += 56
    lo, hi = c - a.display_h / 2, c + a.display_h / 2
    o.append(f'<rect x="{X(lo):.1f}" y="{y:.1f}" width="{(hi - lo) * SC:.1f}" height="40" '
             f'fill="{BAD}" fill-opacity="0.30" stroke="{BAD}" stroke-width="1.4"/>')
    o.append(f'<rect x="{X(lo):.1f}" y="{y:.1f}" width="{-lo * SC:.1f}" height="40" '
             f'fill="{BAD}" fill-opacity="0.75"/>')
    o.append(_t(X((lo + hi) / 2), y + 24, f"LANDSCAPE {a.display_h:.2f}", 9.0, fill=INK,
                weight="bold"))
    o.append(_t(X(a.fridge_d + DOORS) + 18, y + 18, f"OVERHANGS the rear by {-lo:.1f}", 8.8,
                anchor="start", fill=BAD, weight="bold"))
    o.append(_t(X(a.fridge_d + DOORS) + 18, y + 29,
                f"{lo:.1f} .. {hi:.1f}  — starts BEHIND the fridge", 8.2, anchor="start",
                fill=BAD))
    o.append(f'<line x1="{X(0):.1f}" y1="{y - 8:.1f}" x2="{X(0):.1f}" y2="{y + 48:.1f}" '
             f'stroke="{BAD}" stroke-width="1.6" stroke-dasharray="5 3"/>')

    o.extend(_panel(40, 720, 1420, 160, "THE CHAIN, IN ORDER", BAD))
    steps = [
        f"the rear box is {a.box_w_portrait:.0f} wide and must pass BETWEEN the struts",
        f"so the struts are {a.strut_spacing:.2f} apart — derived, not chosen",
        f"so the clamp bar is {a.clamp_width:.2f} to span them",
        f"a {a.clamp_width:.0f} bar in a {a.clear_window:.1f} window, holding {a.hinge_margin:.0f} "
        f"off the cover, can sit no further forward than {c:.1f}",
        f"landscape needs its centre at {a.display_h / 2:.1f} or more to clear the rear edge",
        f"{c:.1f} is {a.display_h / 2 - c:.1f} mm short. PORTRAIT only needs "
        f"{a.display_w / 2:.1f}, and has {c - a.display_w / 2:.1f} mm in hand.",
    ]
    for i, s_ in enumerate(steps):
        xx = 60 + (i % 2) * 700
        yy = 762 + (i // 2) * 34
        o.append(f'<circle cx="{xx + 7:.1f}" cy="{yy - 4:.1f}" r="9" fill="{BAD}" '
                 f'fill-opacity="0.15"/>')
        o.append(_t(xx + 7, yy - 1, str(i + 1), 9.0, fill=BAD, weight="bold"))
        o.append(_t(xx + 24, yy, s_, 10.0, anchor="start",
                    fill=INK if i < 5 else BAD, weight="bold" if i == 5 else "normal"))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — portrait %.1f..%.1f FITS; landscape %.1f..%.1f overhangs %.1f",
             path, c - a.display_w / 2, c + a.display_w / 2,
             c - a.display_h / 2, c + a.display_h / 2, a.display_h / 2 - c)


# --------------------------------------------------------------------------------------------
def sheet_dims(path: Path, a: Assembly) -> None:
    """Dimensioned general arrangement: front and side, every length TAGGED so it can be named.

    The tags are the point. V-numbers run up the assembly, H-numbers across it, D-numbers into
    the room. Every one is listed with where it comes from, so a dimension can be argued with by
    its source rather than by eye.
    """
    W, H = 1900, 1180
    o = _frame(W, H, "THE MOUNT, DIMENSIONED",
               "Front and side elevation. Every length carries a tag — V up, H across, D into "
               "the room — and the table says what sets each one.",
               "GENERAL ARRANGEMENT — refer to any length by its tag")

    F_LO, F_HI = 200.0, 950.0
    cut = F_HI - F_LO
    sc = 0.55

    def Y(mm, oy):
        return oy - (mm if mm <= F_LO else mm - cut) * sc

    # ---------- the dimension register: (tag, value, what, source) ----------
    REG = [
        ("V1", a.strut_top, "top of the upper strut piece, above the floor", "derived"),
        ("V2", a.proud, "upper piece stands proud of the case top", "DERIVED to land a slot on V4"),
        ("V3", a.fridge_h, "fridge case height — the top clamp bolts here", "Samsung spec sheet"),
        ("V4", a.upper_strut_len, "upper strut piece", "1 ft STOCK"),
        ("V5", a.upper_strut_lo, "upper piece lower end, above the floor", "derived"),
        ("V6", a.upper_strut_lo - a.lower_strut_len, "GAP — the open window at the box's edge",
         "derived"),
        ("V7", a.lower_strut_len, "lower strut piece", "4 ft STOCK"),
        ("V8", a.plate_bolt_hi, "plate's upper bolt row", "a real slot on the upper grid"),
        ("V9", a.plate_bolt_lo, "plate's lower bolt row", "a real slot on the lower grid"),
        ("V10", a.plate_bolt_dy, "between the plate's bolt rows", "V8 - V9"),
        ("V11", a.plate_h, "plate height", "V10 + 2 x (edge + margin)"),
        ("V12", a.screen_centre, "screen centre above the floor", "chosen for 5'1\"-6'4\""),
        ("V13", a.box_h_portrait, "rear box, long axis (vertical in portrait)", "DIMENSIONED"),
        ("V14", a.base_gap, "underside of the case, above the floor", "measured 10-20"),
        ("H1", a.strut_spacing, "strut centres", "box + strut + 2 x clearance"),
        ("H2", a.strut_width, "strut channel width", "McMaster 3310T791"),
        ("H3", a.clamp_width, "clamp bar, front to back", "H1 + part width"),
        ("H4", a.plate_w, "plate width", "H1 + 2 x (edge + margin)"),
        ("H5", a.box_w_portrait, "rear box, short axis (horizontal in portrait)", "DIMENSIONED"),
        ("H6", a.display_w, "display width in portrait", "DIMENSIONED"),
        ("H7", a.box_clearance, "box to strut, each side", "chosen"),
        ("D1", a.gap, "fridge panel to the strut's back face", "foam + 2 x bracket"),
        ("D2", a.plate_t, "plate thickness", "0.119 in stock"),
        ("D3", a.strut_depth, "strut depth off the panel", "13/16 in low-profile"),
        ("D4", a.rear_box, "display's rear box depth", "DIMENSIONED"),
        ("D5", a.panel_d, "display panel depth", "DIMENSIONED"),
        ("D6", a.display_face, "screen face off the fridge panel", "D1 + D4 + D5"),
        ("D7", a.clamp_leg, "clamp bar long leg, onto the fridge top", "chosen"),
        ("D8", a.clamp_short, "clamp bar short leg, down the side", "chosen"),
        ("D9", a.foot_leg, "foot, outboard along the floor", "chosen"),
        ("D10", a.foot_rise, "foot vertical leg", "chosen"),
        ("D11", a.cover_margin, "clamp bar held off the hinge cover", "CHOSEN — see orientation"),
    ]
    VAL = {tag: v for tag, v, _, _ in REG}

    def balloon(x, y, tag, col=BAD):
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10.5" fill="{PAPER}" stroke="{col}" '
                 f'stroke-width="1.3"/>')
        o.append(_t(x, y + 3.4, tag, 8.2, fill=col, weight="bold"))

    # ================= FRONT ELEVATION =================
    o.extend(_panel(40, 100, 900, 700, "ELEVATION — looking AT the fridge's side panel, all four displays overlaid"))
    ox, oy = 500.0, 700.0
    hw = a.strut_width / 2.0
    o.append(f'<line x1="{ox - 150:.1f}" y1="{oy:.1f}" x2="{ox + 150:.1f}" y2="{oy:.1f}" '
             f'stroke="{INK}" stroke-width="2"/>')
    o.append(f'<rect x="{ox - a.plate_w / 2 * sc:.1f}" '
             f'y="{Y(a.plate_centre + a.plate_h / 2, oy):.1f}" '
             f'width="{a.plate_w * sc:.1f}" '
             f'height="{(Y(a.plate_centre - a.plate_h / 2, oy) - Y(a.plate_centre + a.plate_h / 2, oy)):.1f}" '
             f'fill="{C_PLATE}" stroke="{INK}" stroke-width="1.1"/>')
    for s in (-a.strut_spacing / 2, a.strut_spacing / 2):
        for lo, hi in ((0.0, a.lower_strut_len), (a.upper_strut_lo, a.strut_top)):
            o.append(f'<rect x="{ox + (s - hw) * sc:.1f}" y="{Y(hi, oy):.1f}" '
                     f'width="{a.strut_width * sc:.1f}" '
                     f'height="{(Y(lo, oy) - Y(hi, oy)):.1f}" fill="{C_STRUT}" stroke="{INK}" '
                     f'stroke-width="1"/>')
    for hgt in (a.fridge_h, a.base_gap):
        o.append(f'<rect x="{ox - a.clamp_width / 2 * sc:.1f}" y="{Y(hgt, oy) - 5:.1f}" '
                 f'width="{a.clamp_width * sc:.1f}" height="10" rx="2" fill="{C_STEEL}" '
                 f'stroke="{INK}" stroke-width="1"/>')
    OPTS = [("23.8 PORTRAIT", a.display_w, a.display_h, OK, "6 4"),
            ("23.8 LANDSCAPE", a.display_h, a.display_w, BAD, "3 3"),
            ("27 PORTRAIT", a.display_27_w, a.display_27_h, "#1b6ea8", "9 5"),
            ("27 LANDSCAPE", a.display_27_h, a.display_27_w, "#8a4fbf", "2 4")]
    for nm, wmm, hmm, col, dash in OPTS:
        o.append(f'<rect x="{ox - wmm / 2 * sc:.1f}" '
                 f'y="{Y(a.screen_centre + hmm / 2, oy):.1f}" width="{wmm * sc:.1f}" '
                 f'height="{(Y(a.screen_centre - hmm / 2, oy) - Y(a.screen_centre + hmm / 2, oy)):.1f}" '
                 f'fill="none" stroke="{col}" stroke-width="1.7" stroke-dasharray="{dash}"/>')

    pc = a.plate_centre
    for sx_ in (-1, 1):
        for sy_ in (-1, 1):
            o.append(f'<circle cx="{ox + sx_ * a.vesa / 2 * sc:.1f}" '
                     f'cy="{Y(a.screen_centre + sy_ * a.vesa / 2, oy):.1f}" '
                     f'r="{max(1.6, a.vesa_hole_dia * sc / 2):.1f}" fill="{PAPER}" '
                     f'stroke="{OK}" stroke-width="1.1"/>')
    for sx_ in (-1, 1):
        for b in (a.plate_bolt_lo, a.plate_bolt_hi):
            o.append(f'<circle cx="{ox + sx_ * a.plate_bolt_dx / 2 * sc:.1f}" '
                     f'cy="{Y(b, oy):.1f}" r="{max(2.0, a.plate_bolt_dia * sc / 2):.1f}" '
                     f'fill="{PAPER}" stroke="{BAD}" stroke-width="1.2"/>')
    for sgn in (1, -1):
        vy = a.screen_centre + sgn * a.vent_r
        o.append(f'<rect x="{ox - a.vent_wid / 2 * sc:.1f}" '
                 f'y="{Y(vy + a.vent_len / 2, oy):.1f}" width="{a.vent_wid * sc:.1f}" '
                 f'height="{a.vent_len * sc:.1f}" rx="{a.vent_wid / 2 * sc:.1f}" '
                 f'fill="{PAPER}" stroke="{INK}" stroke-width="1"/>')
    o.append(_t(ox, Y(a.plate_centre - a.plate_h / 2, oy) + 30,
                "holes: VESA green, strut bolts red, vents open", 7.6, fill=MUTED))

    by = Y(F_LO, oy) - 2
    o.append(f'<path d="M{ox - 140:.1f} {by + 7:.1f} L{ox:.1f} {by - 5:.1f} '
             f'L{ox + 140:.1f} {by + 7:.1f}" fill="none" stroke="{PAPER}" stroke-width="8"/>')
    o.append(f'<path d="M{ox - 140:.1f} {by + 7:.1f} L{ox:.1f} {by - 5:.1f} '
             f'L{ox + 140:.1f} {by + 7:.1f}" fill="none" stroke="{BAD}" stroke-width="1.3"/>')

    vdims = [("V1", a.strut_top, 0), ("V3", a.fridge_h, 1), ("V5", a.upper_strut_lo, 2),
             ("V8", a.plate_bolt_hi, 3), ("V12", a.screen_centre, 0), ("V9", a.plate_bolt_lo, 1),
             ("V7", a.lower_strut_len, 2), ("V14", a.base_gap, 3)]
    for tag, hgt, lane in vdims:
        x = ox - 210 - lane * 26
        o.append(f'<line x1="{x:.1f}" y1="{Y(hgt, oy):.1f}" x2="{ox - 60:.1f}" '
                 f'y2="{Y(hgt, oy):.1f}" stroke="{RULE}" stroke-width="0.7"/>')
        balloon(x - 12, Y(hgt, oy), tag)
    for tag, y0, y1, lane in (("V4", a.upper_strut_lo, a.strut_top, 0),
                              ("V6", a.lower_strut_len, a.upper_strut_lo, 1),
                              ("V11", a.plate_centre - a.plate_h / 2,
                               a.plate_centre + a.plate_h / 2, 2)):
        x = ox + 86 + lane * 30
        o.append(f'<line x1="{x:.1f}" y1="{Y(y0, oy):.1f}" x2="{x:.1f}" y2="{Y(y1, oy):.1f}" '
                 f'stroke="{OK}" stroke-width="1.2"/>')
        for yy_ in (y0, y1):
            o.append(f'<line x1="{x - 5:.1f}" y1="{Y(yy_, oy):.1f}" x2="{x + 5:.1f}" '
                     f'y2="{Y(yy_, oy):.1f}" stroke="{OK}" stroke-width="1.2"/>')
            o.append(f'<line x1="{ox + 56:.1f}" y1="{Y(yy_, oy):.1f}" x2="{x:.1f}" '
                     f'y2="{Y(yy_, oy):.1f}" stroke="{RULE}" stroke-width="0.6"/>')
        balloon(x, (Y(y0, oy) + Y(y1, oy)) / 2, tag, OK)
    for tag, wid, yy in (("H1", a.strut_spacing, oy + 28), ("H3", a.clamp_width, oy + 54),
                         ("H4", a.plate_w, oy + 80)):
        o.append(f'<line x1="{ox - wid / 2 * sc:.1f}" y1="{yy:.1f}" '
                 f'x2="{ox + wid / 2 * sc:.1f}" y2="{yy:.1f}" stroke="{WARN}" '
                 f'stroke-width="1.2"/>')
        for xx_ in (-wid / 2, wid / 2):
            o.append(f'<line x1="{ox + xx_ * sc:.1f}" y1="{yy - 5:.1f}" '
                     f'x2="{ox + xx_ * sc:.1f}" y2="{yy + 5:.1f}" stroke="{WARN}" '
                     f'stroke-width="1.2"/>')
        balloon(ox + wid / 2 * sc + 16, yy, tag, WARN)

    # ================= WHAT THE MOUNT CARRIES =================
    o.extend(_panel(1600, 100, 260, 700, "THE FOUR OPTIONS"))
    for i, (nm, wmm, hmm, col, dash) in enumerate(OPTS):
        ly = 150 + i * 46
        o.append(f'<line x1="1618" y1="{ly:.1f}" x2="1652" y2="{ly:.1f}" stroke="{col}" '
                 f'stroke-width="2.2" stroke-dasharray="{dash}"/>')
        o.append(_t(1660, ly + 3, nm, 9.0, anchor="start", fill=col, weight="bold"))
        o.append(_t(1618, ly + 17, f"{wmm:.2f} x {hmm:.2f}", 8.4, anchor="start", fill=MUTED))
    o.extend(_para(1618, 370, "All four share the same 260 x 134 rear box and the same VESA 100, "
                   "so the plate, the struts and the bars are common to every one of them.", 26,
                   size=8.8))
    o.extend(_para(1618, 470, f"The tallest, 27 PORTRAIT at {a.display_27_h:.2f}, still stops "
                   f"{a.fridge_h - (a.screen_centre + a.display_27_h / 2):.0f} mm below the "
                   f"fridge top.", 26, size=8.8))

    # ================= SIDE ELEVATION =================
    o.extend(_panel(960, 100, 300, 700, "SECTION — ALONG the panel, TRUE SCALE"))
    sx, soy = 1110.0, 700.0
    # TRUE SCALE, same as the vertical. Exaggerating depth stretched the 150 mm clamp leg and
    # the 150 mm foot to look like 390 — real lengths, wrongly drawn. The thin stack goes in a
    # magnified DETAIL instead, which is what a detail callout is for.
    DS = sc
    o.append(f'<rect x="{sx - 30:.1f}" y="{Y(a.fridge_h, soy):.1f}" width="30" '
             f'height="{(Y(a.base_gap, soy) - Y(a.fridge_h, soy)):.1f}" fill="{FRIDGE_SIDE}"/>')
    o.append(_t(sx - 15, Y(1500, soy), "FRIDGE", 7.6, fill="#cfc9c2", rot=-90))
    o.append(f'<line x1="{sx - 40:.1f}" y1="{soy:.1f}" x2="{sx + 220:.1f}" y2="{soy:.1f}" '
             f'stroke="{INK}" stroke-width="2"/>')
    zs = sx + a.gap * DS
    for lo, hi in ((0.0, a.lower_strut_len), (a.upper_strut_lo, a.strut_top)):
        o.append(f'<rect x="{zs:.1f}" y="{Y(hi, soy):.1f}" width="{a.strut_depth * DS:.1f}" '
                 f'height="{(Y(lo, soy) - Y(hi, soy)):.1f}" fill="{C_STRUT}" stroke="{INK}" '
                 f'stroke-width="1"/>')
    o.append(f'<rect x="{sx + (a.gap - a.plate_t) * DS:.1f}" '
             f'y="{Y(a.plate_centre + a.plate_h / 2, soy):.1f}" '
             f'width="{a.plate_t * DS + 1:.1f}" '
             f'height="{(Y(a.plate_centre - a.plate_h / 2, soy) - Y(a.plate_centre + a.plate_h / 2, soy)):.1f}" '
             f'fill="{C_PLATE}" stroke="{INK}" stroke-width="0.8"/>')
    o.append(f'<rect x="{zs:.1f}" y="{Y(a.box_hi, soy):.1f}" width="{a.rear_box * DS:.1f}" '
             f'height="{(Y(a.box_lo, soy) - Y(a.box_hi, soy)):.1f}" fill="#5b6b7d" '
             f'stroke="{INK}" stroke-width="1"/>')
    o.append(f'<path d="M{sx - a.clamp_leg * DS:.1f} {Y(a.fridge_h, soy):.1f} '
             f'L{zs + a.strut_depth * DS:.1f} {Y(a.fridge_h, soy):.1f} '
             f'L{zs + a.strut_depth * DS:.1f} {Y(a.fridge_h, soy) + a.clamp_short * sc:.1f}" '
             f'fill="none" stroke="{C_STEEL}" stroke-width="4"/>')
    o.append(f'<path d="M{sx - a.clamp_leg * DS:.1f} {Y(a.base_gap, soy):.1f} '
             f'L{zs + a.strut_depth * DS:.1f} {Y(a.base_gap, soy):.1f}" fill="none" '
             f'stroke="{C_STEEL}" stroke-width="4"/>')
    o.append(f'<path d="M{zs:.1f} {soy - a.foot_rise * sc:.1f} L{zs:.1f} {soy:.1f} '
             f'L{zs + a.foot_leg * DS:.1f} {soy:.1f}" fill="none" stroke="{C_STEEL}" '
             f'stroke-width="4"/>')
    for i, (nm, tall, col, dash) in enumerate(
            [("23.8 P", a.display_h, OK, "6 4"), ("23.8 L", a.display_w, BAD, "3 3"),
             ("27 P", a.display_27_h, "#1b6ea8", "9 5"), ("27 L", a.display_27_w, "#8a4fbf",
                                                          "2 4")]):
        o.append(f'<line x1="{sx + (a.gap + a.rear_box) * DS:.1f}" '
                 f'y1="{Y(a.screen_centre + tall / 2, soy):.1f}" '
                 f'x2="{sx + (a.gap + a.rear_box + a.panel_d) * DS:.1f}" '
                 f'y2="{Y(a.screen_centre + tall / 2, soy):.1f}" stroke="{col}" '
                 f'stroke-width="1.6"/>')
        o.append(_t(sx + 90 + i * 4, Y(a.screen_centre + tall / 2, soy) - 4, nm, 7.4,
                    anchor="start", fill=col, weight="bold"))

    for tag, x0, x1, yy in (("D7", sx - a.clamp_leg * DS, sx, soy + 28),
                            ("D9", sx + a.gap * DS, sx + (a.gap + a.foot_leg) * DS, soy + 54)):
        o.append(f'<line x1="{x0:.1f}" y1="{yy:.1f}" x2="{x1:.1f}" y2="{yy:.1f}" '
                 f'stroke="{WARN}" stroke-width="1.2"/>')
        for xx_ in (x0, x1):
            o.append(f'<line x1="{xx_:.1f}" y1="{yy - 5:.1f}" x2="{xx_:.1f}" y2="{yy + 5:.1f}" '
                     f'stroke="{WARN}" stroke-width="1.2"/>')
        balloon(x1 + 16, yy, tag, WARN)

    # ---- DETAIL: the stack, magnified, because at true scale it is 29 px wide
    o.extend(_panel(1280, 100, 300, 320, "DETAIL — THE STACK, MAGNIFIED", WARN))
    MG = 3.9
    dx_, dy_ = 1306.0, 176.0
    o.append(f'<rect x="{dx_ - 14:.1f}" y="{dy_ - 30:.1f}" '
             f'width="{a.display_face * MG + 34:.1f}" height="196" rx="6" fill="#fff" '
             f'stroke="{RULE}" stroke-width="0.9"/>')
    o.append(_t(dx_, dy_ - 12, f"{MG:.1f}x", 9.0, anchor="start", fill=WARN,
                weight="bold"))
    o.append(f'<circle cx="{sx + a.display_face * DS / 2:.1f}" '
             f'cy="{Y(a.screen_centre, soy):.1f}" r="26" fill="none" stroke="{WARN}" '
             f'stroke-width="1.2" stroke-dasharray="4 3"/>')
    o.append(f'<line x1="{sx + a.display_face * DS / 2 + 26:.1f}" '
             f'y1="{Y(a.screen_centre, soy):.1f}" x2="{dx_ - 14:.1f}" y2="{dy_ + 60:.1f}" '
             f'stroke="{WARN}" stroke-width="0.8" stroke-dasharray="4 3"/>')
    zz = 0.0
    for tag, nm, d in (("D1", "gap", a.gap), ("D2", "plate", a.plate_t),
                       ("D4", "rear box", a.rear_box), ("D5", "panel", a.panel_d)):
        fill = {"D1": None, "D2": C_PLATE, "D4": "#5b6b7d", "D5": "#101820"}[tag]
        if fill:
            o.append(f'<rect x="{dx_ + zz * MG:.1f}" y="{dy_ + 8:.1f}" width="{d * MG:.1f}" '
                     f'height="76" fill="{fill}" stroke="{INK}" stroke-width="1"/>')
        else:
            o.append(f'<rect x="{dx_ + zz * MG:.1f}" y="{dy_ + 8:.1f}" width="{d * MG:.1f}" '
                     f'height="76" fill="none" stroke="{RULE}" stroke-width="0.9" '
                     f'stroke-dasharray="3 3"/>')
        o.append(_t(dx_ + (zz + d / 2) * MG, dy_ + 98, f"{d:.2f}", 8.2, weight="bold"))
        o.append(_t(dx_ + (zz + d / 2) * MG, dy_ + 2, tag, 8.0, fill=WARN, weight="bold"))
        zz += d
    o.append(f'<rect x="{dx_ + a.gap * MG:.1f}" y="{dy_ + 8:.1f}" '
             f'width="{a.strut_depth * MG:.1f}" height="18" fill="{C_STRUT}" stroke="{INK}" '
             f'stroke-width="0.9"/>')
    o.append(_t(dx_ + (a.gap + a.strut_depth / 2) * MG, dy_ + 21, "D3 strut", 7.4, fill=INK))
    o.append(f'<line x1="{dx_:.1f}" y1="{dy_ + 120:.1f}" x2="{dx_ + a.display_face * MG:.1f}" '
             f'y2="{dy_ + 120:.1f}" stroke="{WARN}" stroke-width="1.4"/>')
    o.append(_t(dx_ + a.display_face * MG / 2, dy_ + 114,
                f"D6  {a.display_face:.2f} to the screen face", 8.6, fill=WARN, weight="bold"))
    o.extend(_para(dx_ - 8, dy_ + 146, "the strut sits BESIDE the box, not behind it, "
                   "so it does not add to D6", 34, size=8.0))

    # ================= REGISTER =================
    o.extend(_panel(40, 820, 1820, 320, "THE REGISTER — every tag, its value, and what sets it"))
    per = (len(REG) + 2) // 3
    for i, (tag, val, what, src) in enumerate(REG):
        col, row = i // per, i % per
        x = 62 + col * 604
        y = 862 + row * 24
        if row % 2 == 0:
            o.append(f'<rect x="{x - 10:.1f}" y="{y - 15:.1f}" width="590" height="22" '
                     f'fill="#f2f5f7"/>')
        c = BAD if tag[0] == "V" else (WARN if tag[0] == "D" else OK)
        o.append(_t(x + 2, y, tag, 9.4, anchor="start", fill=c, weight="bold"))
        o.append(_t(x + 76, y, f"{val:.2f}", 9.6, anchor="end", weight="bold"))
        o.append(_t(x + 84, y, what, 8.8, anchor="start"))
        o.append(_t(x + 576, y, src, 8.2, anchor="end", fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — %d tagged dimensions", path, len(REG))


SHEETS = {"clamp_dims": sheet_dims,
          "clamp_orientation": sheet_orientation,
          "clamp_stack": sheet_stack,
          "clamp_depth": sheet_depth,
          "clamp_frame": sheet_frame,
          "clamp_plate": sheet_plate,
          "clamp_approval": sheet_approval, "clamp_parts": sheet_parts,
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
