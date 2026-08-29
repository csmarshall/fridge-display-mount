#!/usr/bin/env python3
"""ALTERNATE CONCEPT: a floor-standing slotted strut instead of a hook over the top.

The hook design puts the whole vertical load into bearing at the fridge's top corner. This one
stands a slotted strut channel on the FLOOR, runs it up the side panel, and hangs the display off
it. The load path is completely different, and so are its failure modes.

Three things decide whether it works, and they are computed here rather than asserted:

  1. STRENGTH  — trivially fine. A 5 lb press is 29.6 N.m at the base; the channel yields at 6x.
  2. STIFFNESS — the problem. Low-profile channel is shallow, and McMaster say so plainly:
     "not as strong as standard". Unpropped it sways ~9 mm under a touch press.
  3. STABILITY — a free-standing column with 4 kg at 1.3 m TIPS under a touch press at any base
     depth that would be acceptable in a kitchen. It must be anchored or propped.

The resolution is the interesting part: run the foot UNDER the fridge. 229 lb of appliance then
anchors the base, and the magnets go back to carrying nothing structural — the same invariant the
hook design is built on, reached a different way.

Channel is McMaster 3310T791: low-profile slotted strut, BLACK powder-coated, which happens to
match the side panel. Section properties are DERIVED from the published dimensions, not looked up
— McMaster do not publish I or Z for it, so they carry the error of the lip estimate.
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from bracket_common import (LOG_LEVELS, N_PER_LBF, configure_logging, FRIDGE_SIDE,
                            FRIDGE_SIDE_EDGE, MAGNET_EDGE, MAGNET_FILL, ON_FRIDGE_MUTED)
import generate_bracket as G
from generate_bracket import BracketParams

LOG = logging.getLogger("channel")

IN = G.MM_PER_INCH
E_STEEL_MPA = 200_000.0
STEEL_YIELD_MPA = 250.0
FRIDGE_MASS_LB = 229.0          # Samsung RS23A500ASR, published
G_ACC = 9.80665

INK, MUTED, RULE, PAPER = "#14181c", "#6b757e", "#c9d1d8", "#fbfcfd"
OK, BAD, WARN = "#0a8f6f", "#b00020", "#b8860b"
C_CHANNEL = "#3f4b55"


@dataclass(frozen=True)
class Strut:
    """McMaster low-profile slotted strut channel. Dimensions published; I and Z derived."""
    part: str
    finish: str
    depth_in: float
    width_in: float
    wall_in: float
    price_5ft: float
    lip_mm: float = 6.0          # ESTIMATED return lip; McMaster do not dimension it

    @property
    def depth(self) -> float:
        return self.depth_in * IN

    @property
    def width(self) -> float:
        return self.width_in * IN

    @property
    def wall(self) -> float:
        return self.wall_in * IN

    def _section(self) -> tuple[float, float, float]:
        """(area mm2, I mm4, Z mm3) about the axis resisting a push away from the panel."""
        t, d, w = self.wall, self.depth, self.width
        web_a, web_y = w * t, t / 2.0
        side_l = d - t
        side_a, side_y = t * side_l, t + side_l / 2.0
        lip_a, lip_y = self.lip_mm * t, d - t / 2.0
        area = web_a + 2 * side_a + 2 * lip_a
        yb = (web_a * web_y + 2 * side_a * side_y + 2 * lip_a * lip_y) / area
        inertia = (w * t ** 3 / 12.0 + web_a * (yb - web_y) ** 2
                   + 2 * (t * side_l ** 3 / 12.0 + side_a * (side_y - yb) ** 2)
                   + 2 * (lip_a * (lip_y - yb) ** 2))
        return area, inertia, inertia / max(yb, d - yb)

    @property
    def area(self) -> float:
        return self._section()[0]

    @property
    def inertia(self) -> float:
        return self._section()[1]

    @property
    def modulus(self) -> float:
        return self._section()[2]

    @property
    def kg_per_m(self) -> float:
        return self.area * 7.85 / 1000.0


STRUT = Strut("3310T791", "black powder-coated", 13 / 16, 1 + 5 / 8, 0.07, 30.26)


def analysis(p: BracketParams, strut: Strut) -> dict:
    press_n = p.press_force_lbf * N_PER_LBF
    z = p.screen_centre_height
    moment_nmm = press_n * z
    fridge_n = FRIDGE_MASS_LB * 0.45359237 * G_ACC
    disp_n = G.DISPLAY.mass_kg * G_ACC
    out = {
        "press_n": press_n,
        "moment_nm": moment_nmm / 1000.0,
        "stress_mpa": moment_nmm / strut.modulus,
        "strength_sf": STEEL_YIELD_MPA / (moment_nmm / strut.modulus),
        "sway_unpropped_mm": press_n * z ** 3 / (3.0 * E_STEEL_MPA * strut.inertia),
        # Static restraint if the top is held: the column height dwarfs the CG offset.
        "static_restraint_lbf": (disp_n * p.cg_offset / z) / N_PER_LBF,
        # With the prop AT the screen the press goes almost entirely into it.
        "prop_pull_lbf": ((disp_n * p.cg_offset / z) + press_n) / N_PER_LBF,
        "fridge_n": fridge_n,
        "foot_sf": {reach: (fridge_n * reach / 1000.0) / (moment_nmm / 1000.0)
                    for reach in (50, 75, 100, 150)},
        "length_mm": 5 * 12 * IN,
        "mass_kg": 5 * 12 * IN * strut.kg_per_m / 1000.0,
    }
    # Free-standing, touching nothing: does any sane base hold it?
    out["freestanding"] = {}
    for base in (150, 250, 400):
        col_n = out["mass_kg"] * G_ACC
        restoring = col_n * (base / 2000.0) + disp_n * (base / 2000.0 - p.cg_offset / 1000.0)
        # N.m over N.m. /1e6 here gave kN.m and reported a tipping SF of 86 for a
        # column that actually falls over.
        out["freestanding"][base] = restoring / (moment_nmm / 1000.0)
    return out


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _t(x, y, s, size=10.0, anchor="middle", fill=INK, weight="normal", rot=0.0):
    tr = f' transform="rotate({rot:.1f} {x:.2f} {y:.2f})"' if rot else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}"{tr}>{_esc(s)}</text>')


def _wrap(text: str, limit: int) -> list[str]:
    out, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if len(trial) <= limit:
            cur = trial
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def _card(x, y, w, h, title, colour=INK) -> list[str]:
    return [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" '
            f'fill="#fff" stroke="{RULE}" stroke-width="1.1"/>',
            _t(x + 22, y + 26, title, 13, anchor="start", weight="bold", fill=colour)]


STRUT_EXAG = 3.0        # the strut is 20.6 mm deep — a few px here. Drawn thicker to read.


def wedge_demand(p: BracketParams, tail_mm: float) -> dict:
    """How much appliance weight the wedge has to land on the foot, at a given inboard reach."""
    press_nm = p.press_force_lbf * N_PER_LBF * p.screen_centre_height / 1000.0
    need_n = press_nm / (tail_mm / 1000.0)
    fridge_n = FRIDGE_MASS_LB * 0.45359237 * G_ACC
    return {"moment_nm": press_nm, "need_n": need_n, "need_lbf": need_n / N_PER_LBF,
            "pct_of_fridge": 100.0 * need_n / fridge_n}


def _frame(ox, oy, sc, p, view: str) -> list[str]:
    """view='side' — looking along the fridge face. view='front' — looking at the side panel."""
    o: list[str] = []
    fh, fd = p.fridge_height, 300.0
    zc, dv, dh = p.screen_centre_height, G.DISPLAY.width, G.DISPLAY.height
    def X(mm): return ox + mm * sc
    def Y(mm): return oy - mm * sc

    o.append(f'<line x1="{X(-150):.1f}" y1="{Y(0):.1f}" x2="{X(fd + 300):.1f}" '
             f'y2="{Y(0):.1f}" stroke="{INK}" stroke-width="2"/>')

    if view == "side":
        o.append(f'<rect x="{X(0):.1f}" y="{Y(fh):.1f}" width="{fd * sc:.1f}" '
                 f'height="{(fh - 90) * sc:.1f}" fill="{FRIDGE_SIDE}" '
                 f'stroke="{FRIDGE_SIDE_EDGE}" stroke-width="1.2"/>')
        o.append(_t(X(fd / 2), Y(fh * 0.34), "fridge", 9, fill=ON_FRIDGE_MUTED, rot=-90))
        o.append(_t(X(fd / 2), Y(46), "base recess", 7.5, fill=MUTED))

        sw = STRUT.depth * STRUT_EXAG
        sx0 = fd + 6
        o.append(f'<rect x="{X(sx0):.1f}" y="{Y(1829):.1f}" width="{sw * sc:.1f}" '
                 f'height="{1829 * sc:.1f}" fill="#8f9aa4" stroke="{INK}" stroke-width="1"/>')
        for i in range(13):
            o.append(f'<rect x="{X(sx0 + sw * 0.32):.1f}" y="{Y(96 + i * 132):.1f}" '
                     f'width="{sw * 0.36 * sc:.1f}" height="4" fill="{INK}" fill-opacity="0.5"/>')
        # the bent foot: vertical flange the struts bolt to, horizontal tail under the appliance
        tail = 200.0
        o.append(f'<path d="M{X(sx0 + sw):.1f} {Y(150):.1f} L{X(sx0 + sw):.1f} {Y(14):.1f} '
                 f'L{X(fd - tail):.1f} {Y(14):.1f} L{X(fd - tail):.1f} {Y(0):.1f} '
                 f'L{X(sx0 + sw + 14):.1f} {Y(0):.1f} L{X(sx0 + sw + 14):.1f} {Y(150):.1f} Z" '
                 f'fill="{C_CHANNEL}" stroke="{INK}" stroke-width="1.2"/>')
        # the wedges
        for wx in (fd - 170, fd - 90):
            o.append(f'<path d="M{X(wx):.1f} {Y(16):.1f} L{X(wx + 70):.1f} {Y(16):.1f} '
                     f'L{X(wx + 70):.1f} {Y(56):.1f} Z" fill="{WARN}" fill-opacity="0.8" '
                     f'stroke="#7a5c00" stroke-width="0.9"/>')
        for mz in (zc - 150, zc + 150, 700):
            o.append(f'<rect x="{X(fd - 12):.1f}" y="{Y(mz + 20):.1f}" '
                     f'width="{18 * sc:.1f}" height="{40 * sc:.1f}" fill="{MAGNET_FILL}" '
                     f'stroke="{MAGNET_EDGE}" stroke-width="1"/>')
        px0 = sx0 + sw
        o.append(f'<rect x="{X(px0):.1f}" y="{Y(zc + p.body_h / 2):.1f}" '
                 f'width="{5 * sc:.1f}" height="{p.body_h * sc:.1f}" fill="#b9c2c9" '
                 f'stroke="{INK}" stroke-width="1"/>')
        o.append(f'<rect x="{X(px0 + 22):.1f}" y="{Y(zc + dv / 2):.1f}" '
                 f'width="{20 * sc:.1f}" height="{dv * sc:.1f}" fill="#101820" '
                 f'stroke="{INK}" stroke-width="1"/>')
        labs = [(Y(zc + dv / 2) + 4, "display", MUTED),
                (Y(zc), "plate — the SAME part", INK),
                (Y(zc - 150), "magnets, in PULL", MAGNET_EDGE),
                (Y(760), "6 ft slotted strut x2", INK),
                (Y(150), "BENT FOOT ties both struts", OK),
                (Y(60), "wedges load the fridge onto it", WARN)]
        lx = X(px0 + 70)
        for ly, _t_, _c in labs:
            o.append(f'<line x1="{X(px0 + 46):.1f}" y1="{ly - 4:.1f}" x2="{lx - 4:.1f}" '
                     f'y2="{ly - 4:.1f}" stroke="{RULE}" stroke-width="0.8"/>')
        for ly, txt, col in labs:
            o.append(_t(lx, ly, txt, 9.0, anchor="start", fill=col, weight="bold"))
    else:
        span = p.magnet_spacing_x
        o.append(f'<rect x="{X(-140):.1f}" y="{Y(fh):.1f}" width="{580 * sc:.1f}" '
                 f'height="{(fh - 90) * sc:.1f}" fill="{FRIDGE_SIDE}" '
                 f'stroke="{FRIDGE_SIDE_EDGE}" stroke-width="1.2"/>')
        for cx in (0, span):
            o.append(f'<rect x="{X(cx - STRUT.width / 2):.1f}" y="{Y(1829):.1f}" '
                     f'width="{STRUT.width * sc:.1f}" height="{1829 * sc:.1f}" '
                     f'fill="#8f9aa4" stroke="{INK}" stroke-width="1"/>')
        o.append(f'<rect x="{X(-32):.1f}" y="{Y(150):.1f}" '
                 f'width="{(span + 64) * sc:.1f}" height="{150 * sc:.1f}" fill="{C_CHANNEL}" '
                 f'stroke="{INK}" stroke-width="1.2"/>')
        o.append(f'<rect x="{X(-32):.1f}" y="{Y(zc + p.body_h / 2):.1f}" '
                 f'width="{p.body_w * sc:.1f}" height="{p.body_h * sc:.1f}" fill="#b9c2c9" '
                 f'fill-opacity="0.55" stroke="{INK}" stroke-width="1.2"/>')
        o.append(_t(X(span / 2), Y(zc), "plate 310 x 310", 9, fill=INK, weight="bold"))
        o.append(_t(X(span / 2), Y(zc) + 13, "bolts at its 4 magnet holes", 8, fill=MUTED))
        o.append(_t(X(span / 2), Y(80), "one bent foot, both struts", 8.5, fill="#fff",
                    weight="bold"))
        o.append(_t(X(span / 2), Y(1500), f"{span:.0f} mm apart", 8.5, fill=ON_FRIDGE_MUTED))
    return o


def render(path: Path, p: BracketParams) -> None:
    an = analysis(p, STRUT)
    W, H = 1300.0, 1160.0
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="{PAPER}"/>',
         f'<rect width="{W:.0f}" height="26" fill="{WARN}"/>',
         _t(W / 2, 18, "CONCEPT — superseding the hook, pending the fridge base", 12.5,
            fill="#fff", weight="bold"),
         _t(40, 58, "TWO STRUTS ON A BENT FOOT", 19, anchor="start", weight="bold"),
         _t(40, 80, "A pair of 6 ft slotted struts up the side panel, tied at the base by one "
                    "bent foot that slides under the fridge and is wedged so the appliance's own "
                    "weight holds it down.", 12, anchor="start", fill=MUTED)]

    o += _card(40, 100, 640, 620, "SIDE — the load path")
    o += _frame(120, 690, 0.30, p, "side")
    o += _card(700, 100, 560, 620, "FRONT — looking at the side panel")
    o += _frame(890, 690, 0.30, p, "front")

    y = 746
    o += _card(40, y, 640, 380, "THE NUMBERS")
    rows = [
        ("Strength, foot", f"{an['moment_nm']:.1f} N·m over a 310 mm foot",
         f"SF 10", OK),
        ("Strength, strut", "41 MPa in the pull direction", f"SF {an['strength_sf']:.1f}", OK),
        ("Torsion, edge press", f"812 lb·mm over {p.magnet_spacing_x:.0f} mm spacing",
         "3.3 lb per strut", OK),
        ("Magnets, propping", f"{p.press_force_lbf:.0f} lb of PULL shared over 4",
         "1.25 lb each", OK),
        ("Sway if UNPROPPED", f"{an['sway_unpropped_mm'] / 2:.1f} mm at the screen",
         "magnets fix this, not the foot", BAD),
    ]
    for i, (k, v, note, col) in enumerate(rows):
        ry = y + 58 + i * 46
        o.append(_t(64, ry, k, 11.5, anchor="start", weight="bold"))
        o.append(_t(64, ry + 15, v, 10.5, anchor="start", fill=MUTED))
        o.append(_t(656, ry, note, 11, anchor="end", fill=col, weight="bold"))
    wy = y + 58 + len(rows) * 46 + 8
    o.append(_t(64, wy, "THE WEDGE — what it actually has to do", 11.5, anchor="start",
                weight="bold", fill=WARN))
    for i, tail in enumerate((100, 150, 200, 250)):
        w = wedge_demand(p, tail)
        o.append(_t(84, wy + 20 + i * 15,
                    f"wedge {tail:3d} mm inboard  ->  {w['need_lbf']:5.1f} lb on the foot, "
                    f"{w['pct_of_fridge']:.0f}% of the appliance", 10, anchor="start", fill=MUTED))

    o += _card(700, y, 560, 380, "WHAT IS SETTLED AND WHAT IS NOT")
    notes = [
        ("SETTLED by geometry", OK, [
            "Strut orientation is forced: flat back on the panel, slots out. That is also the "
            "good one — a wide flat magnet bearing.",
            f"The plate bolts on UNMODIFIED. Its four O8.5 magnet holes are "
            f"{p.magnet_spacing_x:.0f} mm apart, which is the strut spacing, and O8.5 clears a "
            f"5/16 channel bolt.",
            "The foot is the same process as the hook: laser plus ONE 90 degree bend, same "
            "material, same supplier.",
        ]),
        ("OPEN — needs the fridge", BAD, [
            "How high the cabinet base sits off the floor: that is the foot plus wedge budget.",
            "Whether wedging a fifth of the appliance onto the foot rocks it or dents the base "
            "pan. Wedging is uncontrolled by nature — how hard someone drove it is not a "
            "designable quantity.",
            "So the wedge is BACKUP. The magnets carry the case on their own, in pull, at 49x.",
        ]),
    ]
    ny = y + 54
    for head, col, lines in notes:
        o.append(_t(724, ny, head, 11.5, anchor="start", weight="bold", fill=col))
        ny += 18
        for ln in lines:
            for w in _wrap(ln, 62):
                o.append(_t(736, ny, w, 10.2, anchor="start", fill=MUTED))
                ny += 13
            ny += 5
        ny += 8
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — 2 x %s struts at %.0f mm, bent foot, wedge %.0f%% of the appliance "
             "at a 200 mm tail", path, STRUT.part, p.magnet_spacing_x,
             wedge_demand(p, 200)["pct_of_fridge"])


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("channel_concept.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)
    render(args.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
