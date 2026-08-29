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


STRUT_EXAG = 3.0        # the strut is 20.6 mm deep — 4 px here. Drawn thicker to read.


def _elevation(ox, oy, sc, p, mode: str) -> list[str]:
    """Side elevation of one concept, floor at oy. Callouts go RIGHT of the display, where the
    card is empty — over the fridge they were unreadable and over the card title they collided.

    The strut's real depth is 20.6 mm, which is four pixels at this scale. It is drawn at
    STRUT_EXAG so the reader can see what it is; the label says so.
    """
    o: list[str] = []
    fh, fd = p.fridge_height, 300.0
    def X(mm): return ox + mm * sc
    def Y(mm): return oy - mm * sc

    o.append(f'<line x1="{X(-40):.1f}" y1="{Y(0):.1f}" x2="{X(fd + 300):.1f}" '
             f'y2="{Y(0):.1f}" stroke="{INK}" stroke-width="2"/>')
    o.append(_t(X(-36), Y(0) + 15, "floor", 8.5, anchor="start", fill=MUTED))
    o.append(f'<rect x="{X(0):.1f}" y="{Y(fh):.1f}" width="{fd * sc:.1f}" '
             f'height="{fh * sc:.1f}" fill="{FRIDGE_SIDE}" stroke="{FRIDGE_SIDE_EDGE}" '
             f'stroke-width="1.2"/>')
    o.append(_t(X(fd / 2), Y(fh * 0.30), "fridge", 9, fill=ON_FRIDGE_MUTED, rot=-90))

    zc, dv = p.screen_centre_height, G.DISPLAY.width
    # The display hangs OUTBOARD of whatever carries it. In the strut case that is the drawn
    # (exaggerated) strut depth, not the real one, or the panel overlaps the column.
    disp_x = fd + 30 if mode == "hook" else fd + 8 + STRUT.depth * STRUT_EXAG + 8
    lab_x = X(disp_x + 60)
    notes: list[tuple[float, str, str]] = []

    if mode == "hook":
        o.append(f'<path d="M{X(fd + 16):.1f} {Y(zc - 170):.1f} L{X(fd + 16):.1f} {Y(fh):.1f} '
                 f'L{X(fd - p.arm_len):.1f} {Y(fh):.1f} L{X(fd - p.arm_len):.1f} '
                 f'{Y(fh + 12):.1f} L{X(fd + 26):.1f} {Y(fh + 12):.1f} L{X(fd + 26):.1f} '
                 f'{Y(zc - 170):.1f} Z" fill="{C_CHANNEL}" stroke="{INK}" stroke-width="1"/>')
        o.append(f'<path d="M{X(fd - p.arm_len / 2):.1f} {Y(fh + 90):.1f} '
                 f'L{X(fd - p.arm_len / 2):.1f} {Y(fh + 20):.1f}" stroke="{OK}" '
                 f'stroke-width="2.2" marker-end="url(#ar)"/>')
        notes.append((Y(fh + 96), "the whole load bears on the TOP CORNER", OK))
        notes.append((Y(zc), "magnets carry NOTHING", MAGNET_EDGE))
    else:
        sw = STRUT.depth * STRUT_EXAG
        o.append(f'<rect x="{X(fd + 8):.1f}" y="{Y(1524):.1f}" width="{sw * sc:.1f}" '
                 f'height="{1524 * sc:.1f}" fill="#8f9aa4" stroke="{INK}" stroke-width="1"/>')
        for i in range(12):
            o.append(f'<rect x="{X(fd + 8 + sw * 0.3):.1f}" y="{Y(110 + i * 128):.1f}" '
                     f'width="{sw * 0.4 * sc:.1f}" height="5" fill="{INK}" fill-opacity="0.5"/>')
        o.append(f'<rect x="{X(fd - 100):.1f}" y="{Y(16):.1f}" width="{114 * sc:.1f}" '
                 f'height="{16 * sc:.1f}" fill="#8f9aa4" stroke="{INK}" stroke-width="1"/>')
        o.append(f'<path d="M{X(fd - 60):.1f} {Y(190):.1f} L{X(fd - 60):.1f} {Y(40):.1f}" '
                 f'stroke="{OK}" stroke-width="2.2" marker-end="url(#ar)"/>')
        for mz in (zc - 130, zc + 130):
            o.append(f'<rect x="{X(fd - 12):.1f}" y="{Y(mz + 18):.1f}" width="{20 * sc:.1f}" '
                     f'height="{36 * sc:.1f}" fill="{MAGNET_FILL}" stroke="{MAGNET_EDGE}" '
                     f'stroke-width="1"/>')
        notes.append((Y(zc + 150), "magnets PROP it — in PULL", MAGNET_EDGE))
        notes.append((Y(zc - 40), f"strut drawn {STRUT_EXAG:.0f}x deep to be visible", MUTED))
        notes.append((Y(200), "229 lb of fridge anchors the foot", OK))
        notes.append((Y(40), "weight goes into the FLOOR", OK))

    o.append(f'<rect x="{X(disp_x):.1f}" y="{Y(zc + dv / 2):.1f}" width="{20 * sc:.1f}" '
             f'height="{dv * sc:.1f}" fill="#101820" stroke="{INK}" stroke-width="1"/>')
    o.append(_t(X(disp_x) + 5, Y(zc - dv / 2) - 8, "display", 8.5, anchor="start", fill=MUTED))
    # leaders first, then the text, so nothing is drawn across a label
    for ly, _txt, _col in notes:
        o.append(f'<line x1="{X(disp_x) + 22:.1f}" y1="{ly - 4:.1f}" x2="{lab_x - 4:.1f}" '
                 f'y2="{ly - 4:.1f}" stroke="{RULE}" stroke-width="0.8"/>')
    for ly, txt, col in notes:
        o.append(_t(lab_x, ly, txt, 9.0, anchor="start", fill=col, weight="bold"))
    return o


def render(path: Path, p: BracketParams) -> None:
    a = analysis(p, STRUT)
    W, H = 1240.0, 1206.0
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="{PAPER}"/>',
         '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" '
         f'markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{OK}"/>'
         '</marker></defs>',
         f'<rect width="{W:.0f}" height="26" fill="{WARN}"/>',
         _t(W / 2, 18, "ALTERNATE CONCEPT — not the design of record", 12.5, fill="#fff",
            weight="bold"),
         _t(40, 58, "STAND IT ON THE FLOOR INSTEAD", 19, anchor="start", weight="bold"),
         _t(40, 80, "A slotted strut channel from the floor up the side panel, with the display "
                    "on channel nuts. Completely different load path from the hook.", 12,
            anchor="start", fill=MUTED)]

    # ---- the two elevations ------------------------------------------------------------------
    o += _card(40, 100, 560, 470, "THE HOOK — design of record", MUTED)
    o += _elevation(96, 552, 0.205, p, "hook")
    o += _card(620, 100, 580, 470, "THE STRUT — this concept", INK)
    o += _elevation(676, 552, 0.205, p, "channel")

    # ---- the numbers -------------------------------------------------------------------------
    y = 596
    o += _card(40, y, 560, 300, "DOES IT STAND UP?")
    rows = [
        ("Strength at the base", f"{a['moment_nm']:.1f} N·m from a "
         f"{p.press_force_lbf:.0f} lb press", f"SF {a['strength_sf']:.1f}", OK),
        ("Sway, UNPROPPED", f"{a['sway_unpropped_mm']:.1f} mm at the screen",
         "the hook flexes 0.016", BAD),
        ("Free-standing, 400 mm base", f"SF {a['freestanding'][400]:.2f}", "IT FALLS OVER", BAD),
        ("Foot 100 mm under the fridge", f"SF {a['foot_sf'][100]:.1f}", "anchored", OK),
        ("Pull on the props, propped", f"{a['prop_pull_lbf']:.1f} lb shared",
         "vs 61.2 lb each", OK),
    ]
    for i, (k, v, note, col) in enumerate(rows):
        ry = y + 56 + i * 44
        o.append(_t(62, ry, k, 11.5, anchor="start", weight="bold"))
        o.append(_t(62, ry + 15, v, 10.5, anchor="start", fill=MUTED))
        o.append(_t(578, ry, note, 11, anchor="end", fill=col, weight="bold"))

    o += _card(620, y, 580, 300, "WHAT IT COSTS AND BUYS")
    facts = [
        f"Channel {STRUT.part}, {STRUT.finish}, 5 ft: ${STRUT.price_5ft:.2f} and "
        f"{a['mass_kg']:.2f} kg — against $197.07 for the bracket.",
        "The finish is BLACK, which is what the side panel is.",
        "Screen height becomes ADJUSTABLE after the fact — slide it in the slot. The hook's "
        "neck length is fixed at manufacture, and the height is currently a judgement call.",
        "Nothing touches the fridge top: no hinge cover, no corner radius, no arm, no pad budget. "
        "Four of the open pre-order measurements stop mattering.",
        "But the column is visible floor to screen, it stands in the room beside the fridge, and "
        "its foot goes under an appliance that has to come out to be cleaned.",
    ]
    fy = y + 54
    for i, f in enumerate(facts):
        col = BAD if i == len(facts) - 1 else INK
        for ln in _wrap(f, 68):
            o.append(_t(642, fy, ln, 10.8, anchor="start", fill=col))
            fy += 14
        fy += 8

    # ---- the honest verdict ------------------------------------------------------------------
    vy = 928
    o.append(f'<rect x="40" y="{vy:.1f}" width="{W - 80:.1f}" height="238" rx="6" fill="#fff" '
             f'stroke="{WARN}" stroke-width="1.6"/>')
    o.append(_t(62, vy + 28, "THE TRADE", 13.5, anchor="start", weight="bold", fill=WARN))
    verdict = [
        ("The strut is not stiff enough on its own. ", INK, "bold"),
        (f"Unpropped it sways {a['sway_unpropped_mm']:.1f} mm when you touch the screen — "
         f"{a['sway_unpropped_mm'] / 0.016:.0f}x the hook design. Low-profile channel is shallow "
         "and McMaster say outright it is not as strong as standard. Magnets at screen height fix "
         "it, and they take the press in PULL, their strong direction.", MUTED, "normal"),
        ("Free-standing is not an option. ", INK, "bold"),
        ("A 4 kg screen at 1.3 m tips the column under a touch press at every base depth a "
         "kitchen would tolerate — a 400 mm base still only reaches SF 0.33. Something has to "
         "hold it.", MUTED, "normal"),
        ("Putting the foot under the fridge is what rescues it. ", INK, "bold"),
        ("100 mm of foot under 229 lb of appliance gives SF 3.4, and the magnets go back to "
         "carrying nothing structural — the same invariant the hook is built on, reached from the "
         "other end.", MUTED, "normal"),
        ("What it really buys is ADJUSTABILITY, and what it really costs is presence. ", INK,
         "bold"),
        ("Screen height stops being a guess frozen at manufacture. In exchange there is a "
         "1.5 m column standing in the kitchen where there is currently nothing visible at all.",
         MUTED, "normal"),
    ]
    ly = vy + 54
    for text, col, wt in verdict:
        for ln in _wrap(text, 132):
            o.append(_t(62, ly, ln, 11.2, anchor="start", fill=col, weight=wt))
            ly += 15
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — strut %s, I %.0f mm4, sway %.1f mm unpropped, foot SF %.1f at 100 mm",
             path, STRUT.part, STRUT.inertia, a["sway_unpropped_mm"], a["foot_sf"][100])


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
