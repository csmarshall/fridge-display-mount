#!/usr/bin/env python3
"""The fabrication package: joints, parts and bill of materials.

Every sheet here renders from `bom.py`, which derives from the same `Assembly` the drawings use.
No quantity or dimension is typed in twice.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from concept_sheet import (IN, INK, MUTED, RULE, PAPER, OK, BAD, WARN,
                           C_STEEL, C_STRUT, C_PLATE, Assembly, _t, _wrap)
import bom as B

LOG = logging.getLogger("package")
BAND = "#b8860b"
FRIDGE_SIDE = "#3a3734"


def _frame(w, h, title, sub, banner):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
            f'viewBox="0 0 {w:.0f} {h:.0f}">',
            f'<rect width="{w:.0f}" height="{h:.0f}" fill="{PAPER}"/>',
            f'<rect width="{w:.0f}" height="24" fill="{BAND}"/>',
            _t(w / 2, 16.5, banner, 11.5, fill="#fff", weight="bold"),
            _t(40, 56, title, 21, anchor="start", weight="bold"),
            _t(40, 78, sub, 12.5, anchor="start", fill=MUTED)]


def _panel(x, y, w, h, title, colour=INK):
    return [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="7" fill="#fff" '
            f'stroke="{RULE}" stroke-width="1"/>',
            _t(x + 16, y + 24, title, 12.5, anchor="start", weight="bold", fill=colour)]


def _para(x, y, text, limit=74, size=10.6, lead=13.0, fill=MUTED):
    return [_t(x, y + i * lead, ln, size, anchor="start", fill=fill)
            for i, ln in enumerate(_wrap(text, limit))]


# --------------------------------------------------------------------------------------------
def sheet_joints(path: Path, a: Assembly, strips: bool = True) -> None:
    """Every bolted joint, drawn as a stack. What is clamped, by what, and how long a bolt."""
    W, H = 1500, 1000
    o = _frame(W, H, "EVERY JOINT, AS A STACK",
               "Each bolted joint in the mount, layer by layer, at 6x. The grip decides the bolt "
               "length, and the bolt length is the thing most often got wrong.",
               "FASTENER SANDWICHES — one per joint")
    SC = 15.0

    JOINTS = [
        ("J1", "CLAMP BAR to STRUT", OK,
         [("elevator head", B.ELEV_HEAD, C_STEEL), ("CLAMP BAR", a.bracket_t, C_PLATE),
          ("washer", B.WASHER_T, "#8a949e"), ("strut web", B.WEB, C_STRUT),
          ("channel nut", B.NUT_H, C_STEEL)],
         "the square shoulder sits in the bar's square hole, so the bolt cannot spin"),
        ("J2", "FOOT to STRUT", OK,
         [("elevator head", B.ELEV_HEAD, C_STEEL), ("FOOT", a.bracket_t, C_PLATE),
          ("washer", B.WASHER_T, "#8a949e"), ("strut web", B.WEB, C_STRUT),
          ("channel nut", B.NUT_H, C_STEEL)],
         "through the foot's SLOT, which is the height adjustment — leave it loose until last"),
        ("J3", "PLATE to STRUT" + (" — SANDWICHED" if strips else ""), BAD,
         ([("elevator head", B.ELEV_HEAD, C_STEEL), ("PLATE", a.plate_t, C_PLATE),
           ("strut web", B.WEB, C_STRUT)]
          + ([("BACKING STRIP", a.bracket_t, WARN)] if strips else [])
          + [("hex nut", B.NUT_H, C_STEEL)]),
         ("the strip spans the strut gap and picks up both pieces, so the web is sandwiched "
          "between plate and strip" if strips else
          "no strip: the plate alone spans the strut gap")),
        ("J4", "DISPLAY to PLATE", "#1b6ea8",
         [("M4 button head", B.M4_HEAD, C_STEEL), ("PLATE", a.plate_t, C_PLATE),
          ("VESA insert", 8.0, "#2b3440")],
         "threads into the display's own inserts — depth unverified, on the pre-order list"),
    ]
    for i, (tag, nm, col, layers, note) in enumerate(JOINTS):
        px, py = 40 + (i % 2) * 730, 100 + (i // 2) * 440
        o.extend(_panel(px, py, 700, 420, f"{tag}   {nm}", col))
        ox, band = px + 40, 104.0
        top = py + 130
        # a 1.78 mm layer is 27 px at this scale and its name is 60 px wide, so the names go in
        # an evenly spread row above with leaders down to the layer each belongs to
        z = 0.0
        grip = 0.0
        centres = []
        for j, (lname, d, fill) in enumerate(layers):
            x0 = ox + z * SC
            o.append(f'<rect x="{x0:.1f}" y="{top:.1f}" width="{d * SC:.1f}" '
                     f'height="{band:.1f}" fill="{fill}" stroke="{INK}" stroke-width="1.1"/>')
            centres.append((x0 + d * SC / 2, lname, d))
            z += d
            if 0 < j < len(layers) - 1:
                grip += d
        span = z * SC
        for j, (cxx, lname, d) in enumerate(centres):
            lx = ox + (j + 0.5) * span / len(centres)
            ly = top - 46 + (j % 2) * 15
            o.append(f'<path d="M{cxx:.1f} {top - 3:.1f} L{cxx:.1f} {ly + 12:.1f} '
                     f'L{lx:.1f} {ly + 6:.1f}" fill="none" stroke="{RULE}" '
                     f'stroke-width="0.8"/>')
            o.append(_t(lx, ly, lname, 8.6, weight="bold"))
            o.append(_t(lx, ly + 11, f"{d:.2f}", 8.2, fill=MUTED))
        gx0 = ox + layers[0][1] * SC
        gx1 = ox + (z - layers[-1][1]) * SC
        o.append(f'<line x1="{gx0:.1f}" y1="{top + band + 40:.1f}" x2="{gx1:.1f}" '
                 f'y2="{top + band + 40:.1f}" stroke="{col}" stroke-width="1.6"/>')
        for xx in (gx0, gx1):
            o.append(f'<line x1="{xx:.1f}" y1="{top + band + 35:.1f}" x2="{xx:.1f}" '
                     f'y2="{top + band + 45:.1f}" stroke="{col}" stroke-width="1.6"/>')
        o.append(_t((gx0 + gx1) / 2, top + band + 34, f"GRIP {grip:.2f}", 10.0, fill=col,
                    weight="bold"))
        if tag != "J4":
            need = grip + layers[-1][1] + 3.0
            pick = next((L for L in (12.7, 15.88, 19.05, 22.23, 25.4) if L >= need), 25.4)
            o.append(_t(ox, top + band + 74,
                        f"bolt: grip {grip:.2f} + nut {layers[-1][1]:.2f} + 3 run-out = "
                        f"{need:.2f}  ->  {pick / IN:.3g} in ({pick:.2f})", 10.0, anchor="start",
                        fill=col, weight="bold"))
        o.extend(_para(px + 16, py + 330, note, 76, size=10.0))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — %d joints", path, len(JOINTS))


# --------------------------------------------------------------------------------------------
def sheet_bom(path: Path, a: Assembly, strips: bool = True) -> None:
    fab = B.fabricated(a, strips)
    hw = B.hardware(a, strips)
    s = B.summary(a, strips)
    W = 1500
    H = 250 + (len(fab) + len(hw)) * 26 + 220
    o = _frame(W, H, "BILL OF MATERIALS",
               f"{s['fab_parts']} cut parts in {s['fab_kinds']} shapes, "
               f"{s['hw_pieces']} bought pieces on {s['hw_lines']} lines. Everything derived "
               f"from the same model as the drawings.",
               "BOM — nothing here is typed twice")

    y = 120.0
    o.extend(_panel(40, y, 1420, 60 + len(fab) * 26,
                    "CUT PARTS — 0.119 in (3.02 mm) A36/1008 mild steel, textured black", OK))
    y += 48
    for h, x, an in (("", 64, "start"), ("part", 92, "start"), ("qty", 330, "end"),
                     ("flat size", 460, "end"), ("bends", 520, "end"),
                     ("features", 540, "start"), ("cm2", 1440, "end")):
        o.append(_t(x, y, h, 8.6, anchor=an, fill=MUTED, weight="bold"))
    y += 8
    for i, f in enumerate(fab):
        y += 26
        if i % 2 == 0:
            o.append(f'<rect x="52" y="{y - 17:.1f}" width="1396" height="24" fill="#f2f5f7"/>')
        o.append(_t(64, y, f.tag, 10.0, anchor="start", fill=OK, weight="bold"))
        o.append(_t(92, y, f.name, 10.2, anchor="start", weight="bold"))
        o.append(_t(330, y, f"x{f.qty}", 10.0, anchor="end"))
        o.append(_t(460, y, f"{f.flat_w:.2f} x {f.flat_h:.2f}", 10.0, anchor="end"))
        o.append(_t(520, y, str(f.bends), 10.0, anchor="end"))
        o.append(_t(540, y, f.features[:68], 8.8, anchor="start", fill=MUTED))
        o.append(_t(1440, y, f"{f.area_cm2 * f.qty:.0f}", 9.6, anchor="end", fill=MUTED))
    y += 52

    o.extend(_panel(40, y, 1420, 60 + len(hw) * 26, "BOUGHT", INK))
    y += 48
    for h, x, an in (("", 64, "start"), ("item", 92, "start"), ("qty", 330, "end"),
                     ("spec", 350, "start"), ("source", 1180, "start"),
                     ("part no", 1300, "start"), ("cost", 1440, "end")):
        o.append(_t(x, y, h, 8.6, anchor=an, fill=MUTED, weight="bold"))
    y += 8
    for i, b in enumerate(hw):
        y += 26
        if i % 2 == 0:
            o.append(f'<rect x="52" y="{y - 17:.1f}" width="1396" height="24" fill="#f2f5f7"/>')
        o.append(_t(64, y, b.tag, 10.0, anchor="start", fill=INK, weight="bold"))
        o.append(_t(92, y, b.name, 10.2, anchor="start", weight="bold"))
        o.append(_t(330, y, f"x{b.qty}", 10.0, anchor="end"))
        o.append(_t(350, y, b.spec[:96], 8.8, anchor="start", fill=MUTED))
        o.append(_t(1180, y, b.source, 9.0, anchor="start", fill=MUTED))
        o.append(_t(1300, y, b.part_no or "—", 9.0, anchor="start", fill=MUTED))
        if b.total is None:
            o.append(_t(1440, y, "NOT PRICED", 8.8, anchor="end", fill=BAD, weight="bold"))
        else:
            o.append(_t(1440, y, f"${b.total:.2f}", 9.8, anchor="end", weight="bold"))
    y += 52

    o.extend(_panel(40, y, 1420, 150, "WHAT IS AND IS NOT KNOWN", BAD))
    o.extend(_para(56, y + 48,
                   f"Struts are priced: ${s['priced_total']:.2f} for {a.n_struts} x 4 ft plus "
                   f"{a.n_struts} x 1 ft, off McMaster's own table. Everything else on the "
                   f"bought list is {s['unpriced']} lines of ordinary hardware that has not been "
                   f"quoted, and the cut parts have not been through SendCutSend's instant quote "
                   f"at these shapes.", 178, size=10.2))
    o.extend(_para(56, y + 92,
                   f"The cut parts total {s['area_cm2']:.0f} cm2 over {s['fab_parts']} pieces "
                   f"with {s['cut_mm']:.0f} mm of cut and {s['bends']} bends. At this thickness "
                   f"the price study found cost is driven by CUT TIME AND HANDLING rather than "
                   f"material, so the part COUNT matters more than the area.", 178, size=10.2))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — %d cut lines, %d bought lines, $%.2f priced, %d not",
             path, len(fab), len(hw), s['priced_total'], s['unpriced'])



# --------------------------------------------------------------------------------------------
def sheet_elevations(path: Path, a: Assembly, strips: bool = True) -> None:
    """Both elevations, true scale, with the whole fridge behind them."""
    FRIDGE_W, DOORS, HINGE_PROUD = 911.2, 117.5, 36.5
    W, H = 1620, 1120
    sc = 0.45
    o = _frame(W, H, "BOTH ELEVATIONS, WITH THE FRIDGE",
               "True scale, nothing broken or exaggerated. The whole appliance is drawn so the "
               "mount can be judged against it rather than on its own.",
               "GENERAL ARRANGEMENT — the mount in place")

    def view(px, py, pw, ph, title, wide, draw):
        o.extend(_panel(px, py, pw, ph, title))
        ox = px + (pw - wide * sc) / 2.0
        oy = py + ph - 70.0
        o.append(f'<line x1="{px + 16:.1f}" y1="{oy:.1f}" x2="{px + pw - 16:.1f}" '
                 f'y2="{oy:.1f}" stroke="{INK}" stroke-width="2"/>')
        o.append(f'<rect x="{px + 16:.1f}" y="{oy:.1f}" width="{pw - 32:.1f}" height="54" '
                 f'fill="#b9a184" opacity="0.30"/>')
        draw(ox, oy)
        return ox, oy

    def X1(ox, mm):
        return ox + mm * sc

    def Y1(oy, mm):
        return oy - mm * sc

    # ---------- looking AT the side panel ----------
    def draw_at(ox, oy):
        o.append(f'<rect x="{X1(ox, 0):.1f}" y="{Y1(oy, a.fridge_h):.1f}" '
                 f'width="{a.fridge_d * sc:.1f}" height="{(oy - Y1(oy, a.fridge_h)):.1f}" '
                 f'fill="{FRIDGE_SIDE}"/>')
        o.append(f'<rect x="{X1(ox, a.fridge_d):.1f}" '
                 f'y="{Y1(oy, a.fridge_h + HINGE_PROUD):.1f}" width="{DOORS * sc:.1f}" '
                 f'height="{(oy - Y1(oy, a.fridge_h + HINGE_PROUD)):.1f}" fill="#8e949a"/>')
        o.append(f'<rect x="{X1(ox, a.clear_window):.1f}" '
                 f'y="{Y1(oy, a.fridge_h + HINGE_PROUD):.1f}" '
                 f'width="{a.hinge_cover * sc:.1f}" height="{HINGE_PROUD * sc:.1f}" '
                 f'fill="#4c4842"/>')
        c, hw = a.strut_centre, a.strut_width / 2
        for s_ in (c - a.strut_spacing / 2, c + a.strut_spacing / 2):
            o.append(f'<rect x="{X1(ox, s_ - hw) - 1:.1f}" y="{oy - 6:.1f}" '
                     f'width="{a.strut_width * sc + 2:.1f}" height="6" fill="{C_STEEL}"/>')
            for lo, hi in ((0.0, a.lower_strut_len), (a.upper_strut_lo, a.strut_top)):
                o.append(f'<rect x="{X1(ox, s_ - hw):.1f}" y="{Y1(oy, hi):.1f}" '
                         f'width="{a.strut_width * sc:.1f}" '
                         f'height="{(Y1(oy, lo) - Y1(oy, hi)):.1f}" fill="{C_STRUT}" '
                         f'stroke="{INK}" stroke-width="0.8"/>')
        for hgt in (a.fridge_h, a.base_gap):
            o.append(f'<rect x="{X1(ox, c - a.clamp_outer_half):.1f}" y="{Y1(oy, hgt) - 4:.1f}" '
                     f'width="{a.clamp_width * sc:.1f}" height="8" rx="1.5" fill="{C_STEEL}"/>')
        o.append(f'<rect x="{X1(ox, c - a.display_w / 2):.1f}" '
                 f'y="{Y1(oy, a.screen_centre + a.display_h / 2):.1f}" '
                 f'width="{a.display_w * sc:.1f}" height="{a.display_h * sc:.1f}" rx="4" '
                 f'fill="#0d0f12"/>')
        b = 13.6 * sc
        o.append(f'<rect x="{X1(ox, c - a.display_w / 2) + b:.1f}" '
                 f'y="{Y1(oy, a.screen_centre + a.display_h / 2) + b:.1f}" '
                 f'width="{a.display_w * sc - 2 * b:.1f}" '
                 f'height="{a.display_h * sc - 2 * b:.1f}" fill="#16212c"/>')
        for tag, mm, lab in (("", a.fridge_h, f"case {a.fridge_h:.0f}"),
                             ("", a.screen_centre, f"screen centre {a.screen_centre:.0f}")):
            o.append(f'<line x1="{X1(ox, -30):.1f}" y1="{Y1(oy, mm):.1f}" '
                     f'x2="{X1(ox, a.fridge_d + DOORS + 16):.1f}" y2="{Y1(oy, mm):.1f}" '
                     f'stroke="{MUTED}" stroke-width="0.7" stroke-dasharray="5 4"/>')
            o.append(_t(X1(ox, a.fridge_d + DOORS + 20), Y1(oy, mm) + 3, lab, 8.4,
                        anchor="start", fill=MUTED))

    # ---------- looking ALONG the panel, at the whole appliance ----------
    def draw_along(ox, oy):
        o.append(f'<rect x="{X1(ox, 0):.1f}" y="{Y1(oy, a.fridge_h):.1f}" '
                 f'width="{FRIDGE_W * sc:.1f}" height="{(oy - Y1(oy, a.fridge_h)):.1f}" '
                 f'fill="#8e949a"/>')
        o.append(f'<line x1="{X1(ox, FRIDGE_W / 2):.1f}" y1="{Y1(oy, a.fridge_h):.1f}" '
                 f'x2="{X1(ox, FRIDGE_W / 2):.1f}" y2="{oy:.1f}" stroke="#6d7378" '
                 f'stroke-width="1.4"/>')
        for hx in (FRIDGE_W / 2 - 40, FRIDGE_W / 2 + 40):
            o.append(f'<rect x="{X1(ox, hx):.1f}" y="{Y1(oy, 1500):.1f}" width="7" '
                     f'height="{700 * sc:.1f}" rx="3" fill="#cdd3d8"/>')
        # the mount, edge-on, on the near side panel
        o.append(f'<rect x="{X1(ox, -a.display_face):.1f}" '
                 f'y="{Y1(oy, a.screen_centre + a.display_h / 2):.1f}" '
                 f'width="{a.panel_d * sc:.1f}" height="{a.display_h * sc:.1f}" fill="#0d0f12"/>')
        o.append(f'<rect x="{X1(ox, -a.gap - a.rear_box):.1f}" '
                 f'y="{Y1(oy, a.box_hi):.1f}" width="{a.rear_box * sc:.1f}" '
                 f'height="{(Y1(oy, a.box_lo) - Y1(oy, a.box_hi)):.1f}" fill="#5b6b7d"/>')
        for lo, hi in ((0.0, a.lower_strut_len), (a.upper_strut_lo, a.strut_top)):
            o.append(f'<rect x="{X1(ox, -a.gap):.1f}" y="{Y1(oy, hi):.1f}" '
                     f'width="{a.strut_depth * sc:.1f}" '
                     f'height="{(Y1(oy, lo) - Y1(oy, hi)):.1f}" fill="{C_STRUT}" '
                     f'stroke="{INK}" stroke-width="0.8"/>')
        for hgt in (a.fridge_h, a.base_gap):
            o.append(f'<rect x="{X1(ox, -a.gap - 2):.1f}" y="{Y1(oy, hgt) - 3:.1f}" '
                     f'width="{(a.gap + a.strut_depth + 4) * sc + 30:.1f}" height="6" '
                     f'fill="{C_STEEL}"/>')
        o.append(f'<rect x="{X1(ox, -a.gap - a.strut_depth):.1f}" y="{oy - 6:.1f}" '
                 f'width="{a.foot_leg * sc:.1f}" height="6" fill="{C_STEEL}"/>')
        o.append(f'<line x1="{X1(ox, -a.display_face):.1f}" y1="{oy + 22:.1f}" '
                 f'x2="{X1(ox, 0):.1f}" y2="{oy + 22:.1f}" stroke="{OK}" stroke-width="1.4"/>')
        o.append(_t(X1(ox, -a.display_face / 2), oy + 17, f"{a.display_face:.1f}", 9.0, fill=OK,
                    weight="bold"))
        o.append(_t(X1(ox, FRIDGE_W / 2), Y1(oy, 900), f"fridge {FRIDGE_W:.1f} wide", 9.5,
                    fill="#4d5459", weight="bold"))

    view(40, 100, 560, 940, "LOOKING AT THE SIDE PANEL — the face the display hangs on",
         a.fridge_d + DOORS, draw_at)
    view(620, 100, 620, 940, "LOOKING ALONG IT — the whole appliance, mount edge-on",
         FRIDGE_W, draw_along)

    o.extend(_panel(1260, 100, 320, 940, "READ TOGETHER", OK))
    yy = 148
    for head, body in (
            ("The mount is narrow",
             f"it occupies {a.clamp_width:.0f} of the {a.clear_window:.1f} mm window on the top, "
             f"and {a.display_face:.1f} mm of depth off the panel."),
            ("It stands on the floor",
             "the left view shows the load path; the right shows how little of the appliance it "
             "touches."),
            ("Nothing reaches the doors",
             f"the doors project {DOORS:.1f} forward of the case and the mount stays behind the "
             f"hinge cover."),
            ("The strut gap is deliberate",
             "the break in the two struts is where the display's ports and buttons stay "
             "reachable."),
            ("Both views are TRUE SCALE",
             "no break, no exaggerated depth. Everything measurable off the drawing.")):
        o.append(_t(1276, yy, head, 11.0, anchor="start", weight="bold", fill=OK))
        o.extend(_para(1276, yy + 17, body, 36, size=9.8, lead=12.0))
        yy += 96
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — both elevations at %.2f scale", path, sc)



# --------------------------------------------------------------------------------------------
def sheet_allparts(path: Path, a: Assembly, strips: bool = True) -> None:
    """Every cut part, flat, all at ONE scale so they can be compared."""
    fab = B.fabricated(a, strips)
    bd = B.bend_deduction(a)
    W, H = 1560, 980
    o = _frame(W, H, "EVERY CUT PART, FLAT",
               f"{sum(f.qty for f in fab)} pieces in {len(fab)} shapes, all at one scale. "
               f"Formed dimensions in; flat length is the legs MINUS the {bd:.2f} mm deduction.",
               "FLAT PATTERNS — the whole cut list")
    SC = min(560.0 / max(f.flat_w for f in fab), 300.0 / max(f.flat_h for f in fab))
    cols = 2
    for i, f in enumerate(fab):
        px = 40 + (i % cols) * 760
        py = 100 + (i // cols) * 420
        o.extend(_panel(px, py, 730, 400, f"{f.tag}   {f.name}   x{f.qty}", OK))
        bx = px + 40
        by = py + 90 + (300 - f.flat_h * SC) / 2
        o.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{f.flat_w * SC:.1f}" '
                 f'height="{f.flat_h * SC:.1f}" fill="{C_PLATE}" stroke="{INK}" '
                 f'stroke-width="1.5"/>')
        if f.bends:
            leg = a.clamp_leg if f.tag == "A" else a.foot_leg
            blx = bx + (leg - bd / 2.0) * SC
            o.append(f'<line x1="{blx:.1f}" y1="{by - 12:.1f}" x2="{blx:.1f}" '
                     f'y2="{by + f.flat_h * SC + 12:.1f}" stroke="{BAD}" stroke-width="1.5" '
                     f'stroke-dasharray="8 5"/>')
            o.append(_t(blx, by - 18, "BEND 90", 8.6, fill=BAD, weight="bold"))
        cy = by + f.flat_h * SC / 2
        if f.tag == "A":
            for sgn in (-1, 1):
                o.append(f'<rect x="{bx + a.clamp_leg * 0.55 * SC - 4:.1f}" '
                         f'y="{cy + sgn * a.strut_spacing / 2 * SC - 4:.1f}" width="8" '
                         f'height="8" fill="{PAPER}" stroke="{INK}" stroke-width="1.1"/>')
        elif f.tag == "B":
            o.append(f'<rect x="{bx + a.foot_leg * 0.55 * SC - a.slot_len / 2 * SC:.1f}" '
                     f'y="{cy - 4:.1f}" width="{a.slot_len * SC:.1f}" height="8" rx="4" '
                     f'fill="{PAPER}" stroke="{INK}" stroke-width="1.1"/>')
        elif f.tag == "C":
            for sx_ in (-1, 1):
                for sy_ in (-1, 1):
                    o.append(f'<circle cx="{bx + f.flat_w * SC / 2 + sx_ * a.vesa / 2 * SC:.1f}" '
                             f'cy="{cy + sy_ * a.vesa / 2 * SC:.1f}" r="2.2" fill="{PAPER}" '
                             f'stroke="{OK}" stroke-width="1.1"/>')
                    o.append(f'<circle cx="{bx + f.flat_w * SC / 2 + sx_ * a.plate_bolt_dx / 2 * SC:.1f}" '
                             f'cy="{cy + sy_ * a.plate_bolt_dy / 2 * SC:.1f}" r="3.0" '
                             f'fill="{PAPER}" stroke="{BAD}" stroke-width="1.2"/>')
            for sgn in (1, -1):
                o.append(f'<rect x="{bx + f.flat_w * SC / 2 - a.vent_wid / 2 * SC:.1f}" '
                         f'y="{cy + sgn * a.vent_r * SC - a.vent_len / 2 * SC:.1f}" '
                         f'width="{a.vent_wid * SC:.1f}" height="{a.vent_len * SC:.1f}" '
                         f'rx="{a.vent_wid / 2 * SC:.1f}" fill="{PAPER}" stroke="{INK}" '
                         f'stroke-width="1.1"/>')
        elif f.tag == "D":
            for sy_ in (-1, 1):
                o.append(f'<circle cx="{bx + f.flat_w * SC / 2:.1f}" '
                         f'cy="{cy + sy_ * a.plate_bolt_dy / 2 * SC:.1f}" r="3.0" '
                         f'fill="{PAPER}" stroke="{BAD}" stroke-width="1.2"/>')
        dy = by + f.flat_h * SC + 30
        o.append(f'<line x1="{bx:.1f}" y1="{dy:.1f}" x2="{bx + f.flat_w * SC:.1f}" '
                 f'y2="{dy:.1f}" stroke="{INK}" stroke-width="1.1"/>')
        for xx in (bx, bx + f.flat_w * SC):
            o.append(f'<line x1="{xx:.1f}" y1="{dy - 5:.1f}" x2="{xx:.1f}" y2="{dy + 5:.1f}" '
                     f'stroke="{INK}" stroke-width="1.1"/>')
        o.append(_t(bx + f.flat_w * SC / 2, dy - 6, f"{f.flat_w:.2f}", 9.4, weight="bold"))
        o.append(f'<line x1="{bx - 18:.1f}" y1="{by:.1f}" x2="{bx - 18:.1f}" '
                 f'y2="{by + f.flat_h * SC:.1f}" stroke="{INK}" stroke-width="1.1"/>')
        o.append(_t(bx - 22, by + f.flat_h * SC / 2, f"{f.flat_h:.2f}", 9.4, anchor="end",
                    weight="bold"))
        o.extend(_para(px + 16, py + 54, f.note, 78, size=10.0))
        o.extend(_para(px + 16, py + 356, f.features, 82, size=9.4))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — %d shapes at 1:%.1f", path, len(fab), 1 / SC)


SHEETS = {"clamp_joints": sheet_joints, "clamp_bom": sheet_bom,
          "clamp_elevations": sheet_elevations, "clamp_allparts": sheet_allparts}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=sorted(SHEETS))
    ap.add_argument("--outdir", type=Path, default=Path("."))
    ap.add_argument("--no-strips", action="store_true")
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args(argv)
    logging.basicConfig(level=args.log_level,
                        format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    a = Assembly()
    for nm, fn in sorted(SHEETS.items()):
        if args.only and nm != args.only:
            continue
        fn(args.outdir / f"{nm}.svg", a, not args.no_strips)
    return 0


if __name__ == "__main__":
    sys.exit(main())
