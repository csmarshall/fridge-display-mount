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


SHEETS = {"clamp_joints": sheet_joints, "clamp_bom": sheet_bom}


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
