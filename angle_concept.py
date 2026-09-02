#!/usr/bin/env python3
"""DESIGN 4 — CONCEPT: the hook made from stock aluminium, no laser cutting.

The hook's load path is right and its price is wrong: one big custom plate (a third of the money)
and magnets sized for margin rather than duty (another third). This keeps the load path and
throws away the custom plate. Three pieces of hardware-store 6061, drilled by hand:

    CLIP    a 2 x 2 x 1/4 in angle, ~12 in long, laid over the fridge's top corner. One leg
            bears on the top (the hook), the other hangs down the side. It carries ALL the weight,
            exactly as the arm did — the 180 mm reach existed only to land arm magnets on metal,
            and there are none here.
    BARS    two 2 x 1/4 in flat bars, ~24 in, bolted to the clip's hanging leg and running down
            the side panel 250 mm apart. Each carries two O36 male-stud magnets (K&J MM-C-36) on
            its face: the magnets' 250 mm spacing meets the 240 mm torsion floor, and O36 is the
            largest pot magnet that fits a 2 in bar with an edge margin.
    PLATE   an 8 x 8 x 1/4 in plate bolted across the bars at screen height carrying VESA 100.
            It carries no magnets, so its size is set by the VESA pattern and the box, not by a
            magnet spacing.

Standoff is the magnet height, 8 mm, so the pads are 5/16 in foam (7.94 mm, -0.06 — in the pad
band). Bare 6061 does not rust; no coating needed.

What it gives up against design 3: no strut option (the bars are not a strut interface), the
fridge-top bearing is 2 in wide instead of 180 mm (fine on foam at under 1 psi, but the clip must
sit square), and every hole is hand-drilled. What it does not give up: the hook, the torsion
floor, the derate chain, the pad rule. It is CONCEPT ONLY — dimensions are derived, prices are
estimates where marked, and nothing is validated by a generator yet.
"""
from __future__ import annotations

import argparse
import html
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging

LOG = logging.getLogger("angle")
IN = 25.4
LBF_PER_KG = 2.2046226218
AL_DENSITY_G_CC = 2.70


@dataclass(frozen=True)
class Angle:
    fridge_h: float = 1743.07
    fridge_d: float = 609.6
    screen_centre: float = 1331.0
    display_w: float = 324.65        # portrait
    display_h: float = 555.23
    display_kg: float = 3.94
    rear_box: float = 25.0
    box_w: float = 134.0             # portrait: short axis horizontal
    cg_from_box_face: float = 29.4
    clip_leg: float = 2.0 * IN       # 2 x 2 angle
    clip_t: float = 0.25 * IN
    clip_len: float = 12.0 * IN      # stock cut; spans both bars with margin
    bar_w: float = 2.0 * IN
    bar_t: float = 0.25 * IN
    bar_spacing: float = 250.0       # magnet spacing across = torsion floor 240 + margin
    plate_side: float = 8.0 * IN
    plate_t: float = 0.25 * IN
    vesa: float = 100.0
    magnet_dia: float = 36.0         # K&J MM-C-36
    magnet_h: float = 8.0
    magnet_rated_lbf: float = 90.4
    derate: float = 0.35
    pad: float = 5.0 / 16.0 * IN     # 7.94 mm
    press_lbf: float = 5.0
    clip_overlap: float = 40.0       # bar-to-clip bolted overlap on the hanging leg

    @property
    def plate_top(self) -> float:
        return self.screen_centre + self.plate_side / 2.0

    @property
    def plate_bottom(self) -> float:
        return self.screen_centre - self.plate_side / 2.0

    @property
    def magnet_rows(self) -> tuple[float, float]:
        """Two rows per bar: just above the plate and just below it, so the plate sits between."""
        return (self.plate_bottom - self.magnet_dia / 2.0 - 10.0,
                self.plate_top + self.magnet_dia / 2.0 + 10.0)

    @property
    def bar_len(self) -> float:
        """From the clip's hanging leg down past the lower magnet row, rounded to stock."""
        need = self.fridge_h - (self.magnet_rows[0] - self.magnet_dia / 2.0 - 15.0)
        for stock in (18.0, 24.0, 36.0, 48.0):
            if stock * IN >= need:
                return stock * IN
        return math.ceil(need / IN) * IN

    @property
    def bar_bottom(self) -> float:
        return self.fridge_h - self.bar_len

    @property
    def magnet_spacing_v(self) -> float:
        return self.magnet_rows[1] - self.magnet_rows[0]

    @property
    def bar_edge_margin(self) -> float:
        return (self.bar_w - self.magnet_dia) / 2.0

    @property
    def torsion_per_magnet_lbf(self) -> float:
        m_in_lbf = self.press_lbf * (self.display_w / 2.0 / IN)
        return m_in_lbf / (self.bar_spacing / IN) / 2.0

    @property
    def magnet_derated_lbf(self) -> float:
        return self.magnet_rated_lbf * self.derate

    @property
    def magnet_sf(self) -> float:
        return self.magnet_derated_lbf / self.torsion_per_magnet_lbf

    @property
    def hardware_kg(self) -> float:
        clip = (2 * self.clip_leg - self.clip_t) * self.clip_t * self.clip_len
        bars = 2 * self.bar_w * self.bar_t * self.bar_len
        plate = self.plate_side ** 2 * self.plate_t
        return (clip + bars + plate) * AL_DENSITY_G_CC / 1e6

    @property
    def hanging_lbf(self) -> float:
        return (self.display_kg + self.hardware_kg + 4 * 0.05) * LBF_PER_KG

    @property
    def bearing_psi(self) -> float:
        area_in2 = (self.clip_leg / IN) * (self.clip_len / IN)
        return self.hanging_lbf / area_in2

    @property
    def cg_offset(self) -> float:
        """Display CG from the panel: pad/magnet standoff + bar + plate + box face to CG."""
        return self.magnet_h + self.bar_t + self.plate_t + self.cg_from_box_face

    @property
    def peel_lbf(self) -> float:
        """W x d / H on the lower magnet pair, H = clip corner to the lower row."""
        w = self.display_kg * LBF_PER_KG
        h = self.fridge_h - self.magnet_rows[0]
        return w * self.cg_offset / h

    @property
    def clip_flat_gap(self) -> float:
        """Extruded 6061 angle inside radius ~3 mm vs an assumed 12 mm fridge corner."""
        return 0.293 * max(0.0, 12.0 - 3.0)

    @property
    def display_face(self) -> float:
        return self.magnet_h + self.bar_t + self.plate_t + self.rear_box + 18.0


def render(path: Path, a: Angle) -> None:
    PAPER, INK, MUTED, RULE = "#f7f8fa", "#111", "#5b6166", "#d0d4d8"
    FRIDGE, AL, MAG, PAD, OK, WARN, BAD = "#3a3734", "#9aa4ad", "#c0169a", "#f2c14e", "#0b7a4b", "#c8791a", "#b00020"
    W, H = 1720, 1180

    def t(x, y, s, size=10.5, anchor="start", fill=INK, weight="normal"):
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica, Arial, sans-serif" '
                f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">'
                f'{html.escape(s)}</text>')

    def wrap(x, y, text, limit, size=10.2, lead=14.0, fill="#333"):
        words, line, lines = text.split(), "", []
        for w_ in words:
            if len(line) + len(w_) + 1 > limit:
                lines.append(line)
                line = w_
            else:
                line = (line + " " + w_).strip()
        lines.append(line)
        return [t(x, y + i * lead, ln, size, fill=fill) for i, ln in enumerate(lines)], len(lines)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<rect width="{W}" height="26" fill="#6b3fa0"/>',
         t(W / 2, 18, "DESIGN 4 — CONCEPT ONLY. Stock aluminium, hand-drilled. Nothing here is validated by a "
                      "generator; prices marked ESTIMATE are estimates.", 11.5, "middle", "#fff", "bold"),
         t(40, 62, "DESIGN 4 — THE HOOK IN STOCK ALUMINIUM: clip, two bars, a small plate", 21, weight="bold"),
         t(40, 84, "Same load path as the hook (the clip bears on the top; magnets only hold it flat), no custom "
                   "plate, no coating, magnets sized for the duty. Portrait, 23.8 in.", 11.5, fill=MUTED)]

    # ---------------- side elevation (looking along the panel), true scale
    o.append(f'<rect x="40" y="104" width="520" height="760" rx="7" fill="#fff" stroke="{RULE}"/>')
    o.append(t(56, 128, "LOOKING ALONG THE PANEL — side elevation, true scale", 12.5, weight="bold"))
    sc = 0.36
    base = 840.0
    fx0 = 150.0                       # fridge side panel face, svg x
    fw = 240.0                        # how much fridge depth to draw, mm

    def Y(mm):
        return base - mm * sc

    o.append(f'<rect x="{fx0}" y="{Y(a.fridge_h):.1f}" width="{fw * sc:.1f}" height="{(base - Y(a.fridge_h)):.1f}" fill="{FRIDGE}"/>')
    o.append(t(fx0 + fw * sc / 2, base - 40, "FRIDGE", 10, "middle", "#cfd4d8", "bold"))
    o.append(t(fx0 + fw * sc / 2, base - 26, "side panel, continues right", 8.4, "middle", "#9aa1a7"))
    # clip: top leg on the fridge top (over foam), hanging leg down the side (over foam)
    o.append(f'<rect x="{fx0 - a.pad * sc:.1f}" y="{Y(a.fridge_h + a.pad + a.clip_t):.1f}" width="{(a.pad + a.clip_leg) * sc:.1f}" height="{a.clip_t * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8"/>')
    o.append(f'<rect x="{fx0 - (a.pad + a.clip_t) * sc:.1f}" y="{Y(a.fridge_h + a.pad + a.clip_t):.1f}" width="{a.clip_t * sc:.1f}" height="{(a.clip_leg + a.pad) * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8"/>')
    o.append(f'<rect x="{fx0:.1f}" y="{Y(a.fridge_h + a.pad):.1f}" width="{a.clip_leg * sc:.1f}" height="{a.pad * sc:.1f}" fill="{PAD}"/>')
    o.append(f'<rect x="{fx0 - a.pad * sc:.1f}" y="{Y(a.fridge_h):.1f}" width="{a.pad * sc:.1f}" height="{a.clip_leg * sc:.1f}" fill="{PAD}"/>')
    # bar: down the side, outside the clip's hanging leg
    bx = fx0 - (a.pad + a.clip_t + a.bar_t) * sc
    o.append(f'<rect x="{bx:.1f}" y="{Y(a.fridge_h - a.clip_leg + a.clip_overlap):.1f}" width="{a.bar_t * sc:.1f}" height="{(a.bar_len - a.clip_leg + a.clip_overlap) * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8"/>')
    # magnets between bar and panel at the two rows (they replace the pad locally)
    for r in a.magnet_rows:
        o.append(f'<rect x="{fx0 - a.magnet_h * sc:.1f}" y="{Y(r + a.magnet_dia / 2):.1f}" width="{a.magnet_h * sc:.1f}" height="{a.magnet_dia * sc:.1f}" fill="{MAG}"/>')
        o.append(f'<rect x="{fx0 - a.pad * sc:.1f}" y="{Y(r + a.magnet_dia / 2 + 30):.1f}" width="{a.pad * sc:.1f}" height="{30 * sc:.1f}" fill="{PAD}"/>')
    # plate on the bars, display box, panel
    px = bx - a.plate_t * sc
    o.append(f'<rect x="{px:.1f}" y="{Y(a.plate_top):.1f}" width="{a.plate_t * sc:.1f}" height="{a.plate_side * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8"/>')
    boxx = px - a.rear_box * sc
    o.append(f'<rect x="{boxx:.1f}" y="{Y(a.screen_centre + 130):.1f}" width="{a.rear_box * sc:.1f}" height="{260 * sc:.1f}" fill="#4a5f78"/>')
    o.append(f'<rect x="{boxx - 18 * sc:.1f}" y="{Y(a.screen_centre + a.display_h / 2):.1f}" width="{18 * sc:.1f}" height="{a.display_h * sc:.1f}" fill="#1f3550"/>')
    # dims
    for mm, lab in ((a.fridge_h, f"fridge top {a.fridge_h:.0f}"), (a.screen_centre, f"screen centre {a.screen_centre:.0f}"),
                    (a.bar_bottom, f"bar bottom {a.bar_bottom:.0f}"), (a.magnet_rows[1], f"upper magnets {a.magnet_rows[1]:.0f}"),
                    (a.magnet_rows[0], f"lower magnets {a.magnet_rows[0]:.0f}")):
        o.append(f'<line x1="{fx0 + fw * sc:.1f}" y1="{Y(mm):.1f}" x2="{fx0 + fw * sc + 24:.1f}" y2="{Y(mm):.1f}" stroke="{MUTED}" stroke-width="0.8"/>')
        o.append(t(fx0 + fw * sc + 28, Y(mm) + 3, lab, 8.8, fill=INK))
    o.append(t(56, base + 18, f"display face {a.display_face:.0f} mm off the panel (8 magnet + 6.35 bar + 6.35 plate + 25 box + 18)", 9.2, fill=MUTED))

    # ---------------- front view (looking at the panel)
    o.append(f'<rect x="590" y="104" width="520" height="760" rx="7" fill="#fff" stroke="{RULE}"/>')
    o.append(t(606, 128, "LOOKING AT THE PANEL — front, true scale", 12.5, weight="bold"))
    cx = 850.0

    def X(mm):
        return cx + mm * sc

    o.append(f'<rect x="{X(-260):.1f}" y="{Y(a.fridge_h):.1f}" width="{520 * sc:.1f}" height="{(base - Y(a.fridge_h)):.1f}" fill="{FRIDGE}"/>')
    o.append(f'<rect x="{X(-a.clip_len / 2):.1f}" y="{Y(a.fridge_h):.1f}" width="{a.clip_len * sc:.1f}" height="{a.clip_leg * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8"/>')
    o.append(t(X(270), Y(a.fridge_h) + 2, f"CLIP 2 x 2 x 1/4 angle, {a.clip_len / IN:.0f} in", 8.8, "start", INK, "bold"))
    o.append(f'<line x1="{X(a.clip_len / 2):.1f}" y1="{Y(a.fridge_h) - 1:.1f}" x2="{X(266):.1f}" y2="{Y(a.fridge_h) - 1:.1f}" stroke="{MUTED}" stroke-width="0.7"/>')
    for s_ in (-1, 1):
        x0 = X(s_ * a.bar_spacing / 2 - a.bar_w / 2)
        o.append(f'<rect x="{x0:.1f}" y="{Y(a.fridge_h - a.clip_leg + a.clip_overlap):.1f}" width="{a.bar_w * sc:.1f}" height="{(a.bar_len - a.clip_leg + a.clip_overlap) * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8" opacity="0.92"/>')
        for r in a.magnet_rows:
            o.append(f'<circle cx="{X(s_ * a.bar_spacing / 2):.1f}" cy="{Y(r):.1f}" r="{a.magnet_dia / 2 * sc:.1f}" fill="{MAG}" fill-opacity="0.55" stroke="{MAG}" stroke-dasharray="3 2"/>')
        for yy in (a.fridge_h - a.clip_leg + a.clip_overlap - 10, a.fridge_h - a.clip_leg + 10):
            o.append(f'<circle cx="{X(s_ * a.bar_spacing / 2):.1f}" cy="{Y(yy):.1f}" r="2.2" fill="{INK}"/>')
    o.append(f'<rect x="{X(-a.plate_side / 2):.1f}" y="{Y(a.plate_top):.1f}" width="{a.plate_side * sc:.1f}" height="{a.plate_side * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8" opacity="0.85"/>')
    for sx in (-1, 1):
        for sy in (-1, 1):
            o.append(f'<circle cx="{X(sx * a.vesa / 2):.1f}" cy="{Y(a.screen_centre + sy * a.vesa / 2):.1f}" r="2.4" fill="none" stroke="#1a5fb4" stroke-width="1.2"/>')
    o.append(f'<rect x="{X(-a.display_w / 2):.1f}" y="{Y(a.screen_centre + a.display_h / 2):.1f}" width="{a.display_w * sc:.1f}" height="{a.display_h * sc:.1f}" rx="3" fill="none" stroke="{INK}" stroke-width="1.2" stroke-dasharray="7 5"/>')
    o.append(t(X(270), Y(a.screen_centre + a.display_h / 2) + 4, "display, 24 in portrait (dashed)", 8.8, "start", INK))
    o.append(t(X(270), Y(a.screen_centre) + 4, f"PLATE {a.plate_side / IN:.0f} x {a.plate_side / IN:.0f} x 1/4, VESA 100", 8.8, "start", INK, "bold"))
    o.append(t(X(270), Y(a.magnet_rows[1]) + 4, "O36 magnets, 4", 8.8, "start", MAG, "bold"))
    o.append(t(X(270), Y(a.fridge_h - a.clip_leg + a.clip_overlap / 2) + 12, "bar-to-clip bolts", 8.8, "start", INK))
    for mm in (a.screen_centre + a.display_h / 2, a.screen_centre, a.magnet_rows[1], a.fridge_h - a.clip_leg + a.clip_overlap / 2):
        o.append(f'<line x1="{X(a.display_w / 2 + 4):.1f}" y1="{Y(mm):.1f}" x2="{X(266):.1f}" y2="{Y(mm):.1f}" stroke="{MUTED}" stroke-width="0.7" stroke-dasharray="3 3"/>')
    o.append(f'<line x1="{X(-a.bar_spacing / 2):.1f}" y1="{base + 14:.1f}" x2="{X(a.bar_spacing / 2):.1f}" y2="{base + 14:.1f}" stroke="{INK}" stroke-width="1.2"/>')
    o.append(t(cx, base + 30, f"bar / magnet spacing {a.bar_spacing:.0f} (floor 240)", 9.4, "middle", INK, "bold"))

    # ---------------- numbers + parts + trade-offs
    o.append(f'<rect x="1140" y="104" width="540" height="760" rx="7" fill="#fff" stroke="{RULE}"/>')
    o.append(t(1156, 128, "DERIVED NUMBERS", 12.5, weight="bold"))
    rows = [
        ("hanging on the clip", f"{a.hanging_lbf:.1f} lb", f"display + {a.hardware_kg:.2f} kg of aluminium"),
        ("bearing on the fridge top", f"{a.bearing_psi:.2f} psi", f"2 in x {a.clip_len / IN:.0f} in on foam"),
        ("clip corner vs fridge corner", f"{a.clip_flat_gap:.1f} mm lift", "R_f 12 assumed, 5/16 pad absorbs it"),
        ("touch torsion per magnet", f"{a.torsion_per_magnet_lbf:.2f} lb", f"5 lb at {a.display_w / 2:.0f} mm over {a.bar_spacing:.0f}"),
        ("magnet derated pull", f"{a.magnet_derated_lbf:.1f} lb", f"MM-C-36 {a.magnet_rated_lbf:.0f} lb x 0.35"),
        ("magnet SF, touch", f"{a.magnet_sf:.0f}x", "vs 37x for the O48"),
        ("peel on the lower pair", f"{a.peel_lbf:.2f} lb", f"CG {a.cg_offset:.1f} mm out, H {a.fridge_h - a.magnet_rows[0]:.0f}"),
        ("magnet on a 2 in bar", f"{a.bar_edge_margin:.1f} mm each side", "O36 is the largest that fits"),
        ("bar stock", f"{a.bar_len / IN:.0f} in x2", f"bottom at {a.bar_bottom:.0f} mm"),
        ("standoff = pad", f"{a.magnet_h:.0f} mm / 5/16 in", f"{a.pad - a.magnet_h:+.2f} mm — in the -0.60/+0.30 band"),
    ]
    y = 152
    for k, v, n in rows:
        o.append(t(1156, y, k, 9.8))
        o.append(t(1440, y, v, 10, "end", INK, "bold"))
        o.append(t(1452, y, n, 8.4, fill=MUTED))
        y += 20
    o.append(t(1156, y + 12, "PARTS — see prices.py design 4 for the quote", 12.5, weight="bold"))
    parts = [
        ("6061 angle 2 x 2 x 1/4, 12 in", "$18.86 Speedy Metals (2 x 2-1/2 listed; 2 x 2 similar)"),
        ("6061 flat bar 2 x 1/4, 24 in, x2", "ESTIMATE ~$25 (metals4u lists $8.33 for 12 in)"),
        ("6061 plate 8 x 8 x 1/4", "ESTIMATE ~$30"),
        ("K&J MM-C-36 magnets x4", "$38.88 sourced 2026-09-02"),
        ("M6 nyloc nuts, 1/4-20 bolts x8, washers", "ESTIMATE ~$15"),
        ("5/16 in neoprene foam strips", "to source; McMaster stocks it"),
    ]
    y += 36
    for k, v in parts:
        o.append(t(1156, y, k, 9.8, weight="bold"))
        o.append(t(1156, y + 12, v, 8.6, fill=MUTED))
        y += 30
    o.append(t(1156, y + 8, "TRADE-OFFS", 12.5, weight="bold"))
    tos = ("No strut option — the bars are not a strut interface, so the fallback is design 2 whole. The top "
           "bearing is 2 in wide, not 180 mm: fine at under 1 psi on foam, but the clip must sit square or it "
           "rocks. Fourteen holes drilled by hand; the VESA pattern wants a template. Bare aluminium, no coat. "
           "Nothing validated: this needs its own generator before it is more than a sketch.")
    lines, n = wrap(1156, y + 30, tos, 78, 9.6, 13.0)
    o.extend(lines)

    o.append(t(40, H - 260, "WHERE IT SITS AGAINST THE OTHERS", 12.5, weight="bold"))
    cmp_ = [
        "Design 1 / 3: same hook physics, a custom 310 x 742 plate at $178-197 plus $96-191 of O48 magnets. Design 4 "
        "replaces the plate with ~$75 of stock and the magnets with $39 of MM-C-36 — but has to be drilled, aligned "
        "and squared by hand, and has no path to struts.",
        "Design 2: floor-standing, no fridge-top dependency, $327-346. Design 4 depends on the fridge top like 1 and 3.",
        "If design 3's re-quote comes back well over $178, or the plate is never cut, this is the design that costs "
        "least to try. If the plate IS cut, design 4 is moot — the plate is the thing it exists to avoid.",
    ]
    y = H - 236
    for para in cmp_:
        lines, n = wrap(40, y, para, 175, 10.2, 14.0)
        o.extend(lines)
        y += 14 * n + 10
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("angle_concept.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)
    a = Angle()
    LOG.info("clip %.0f in, bars %.0f in x2 at %.0f centres, plate %.0f in; magnets at %.0f / %.0f; hanging %.1f lb; "
             "bearing %.2f psi; torsion %.2f lb/magnet -> SF %.0fx; peel %.2f lb; face %.0f mm off the panel",
             a.clip_len / IN, a.bar_len / IN, a.bar_spacing, a.plate_side / IN, *a.magnet_rows, a.hanging_lbf,
             a.bearing_psi, a.torsion_per_magnet_lbf, a.magnet_sf, a.peel_lbf, a.display_face)
    render(args.out, a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
