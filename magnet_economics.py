#!/usr/bin/env python3
"""Magnet economics: hold against cost, for every magnet type and count that fits the plate.

The question is "how many magnets, of which type, is the most hold for the money, and where do
returns diminish". Hold is the ONE model the page already uses everywhere: force_table.forces(),
the pull-off at the bottom edge with the plate pivoting about the fridge's top edge, each magnet
resisting with its own lever. Only the derated pull per magnet changes between types; the plate
positions and the levers are the hook's.

Counts follow the plate's positions in the order a builder would add them: the four corners
(provably the best four, magnet_pattern_study), then the four mid-sides that are already cut as
spare holes, then a second pair of rows at body y 75 and 225 (the two widest clear bands, per
the generator's extra_magnet_rows note) for 12. Types cannot be mixed on one plate: the magnet
height IS the standoff, and the pad matches it.

Two honesty notes drawn on the sheet. The 35 % derate is a rule of thumb; a thin magnet loses
more of its rating to a paint gap than a thick one, so the small end of the ladder is optimistic
until one is measured on the actual panel. And hold is linear in count for a given type — there
is no knee in the physics; the knees are the plate's position budget (8 cut, 12 possible) and the
step from one type to the next.
"""
from __future__ import annotations

import argparse
import html
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import force_table as FT
import generate_bracket as G
from bracket_common import LOG_LEVELS, configure_logging
from generate_bracket import BracketParams

LOG = logging.getLogger("mageco")
DERATE = 0.35
GRAB_LBF = 20.0


@dataclass(frozen=True)
class Magnet:
    part: str
    dia_mm: float
    h_mm: float
    stud: str
    rated_lbf: float
    usd: float
    pad: str

    @property
    def derated(self) -> float:
        return self.rated_lbf * DERATE

    @property
    def lb_per_usd(self) -> float:
        return self.derated / self.usd


# Sourced 2026-09-02 (K&J product pages) and 2026-08-27 (McMaster). Same table as magnet_sizing.py.
MAGNETS = [
    Magnet("MM-C-20", 20, 7.0, "M4", 28.7, 3.77, "9/32 in (7.14, -0.14 — no stock 7 mm foam; 1/4 in is -0.65, out of band)"),
    Magnet("MM-C-25", 25, 8.0, "M5", 48.5, 5.04, "5/16 in"),
    Magnet("MM-C-32", 32, 8.0, "M6", 75.0, 7.64, "5/16 in"),
    Magnet("MM-C-36", 36, 8.0, "M6", 90.4, 9.72, "5/16 in"),
    Magnet("3506K67", 48.02, 11.51, "5/16-18", 175.0, 23.92, "7/16 in"),
]
COUNTS = (4, 6, 8, 12)


_ORIG_POSITIONS = FT.plate_positions      # captured before hold() swaps it in


def positions(n: int, p: BracketParams) -> list[tuple[float, float]]:
    base = _ORIG_POSITIONS(min(n, 8), p)
    if n > 8:
        hw = p.body_w / 2.0 - p.magnet_inset
        cy = p.body_h / 2.0
        extra = [(sx * hw, y - cy) for y in (75.0, 225.0) for sx in (-1, 1)]
        base = base + extra[: n - 8]
    return base


def hold(n: int, m: Magnet, p: BracketParams, rep: dict) -> dict[str, float]:
    """force_table's model with this magnet's derated pull and this many positions."""
    rep2 = dict(rep, magnet_derated_pull_lbf=m.derated)
    FT.plate_positions = positions
    try:
        f = FT.forces(n, 0, p, rep2)
    finally:
        FT.plate_positions = _ORIG_POSITIONS
    return f


@dataclass(frozen=True)
class Point:
    magnet: Magnet
    n: int
    cost: float
    bottom_lbf: float
    twist_lbf: float

    @property
    def grab_sf(self) -> float:
        return self.bottom_lbf / GRAB_LBF


def study(p: BracketParams, rep: dict) -> list[Point]:
    out = []
    for m in MAGNETS:
        for n in COUNTS:
            f = hold(n, m, p, rep)
            out.append(Point(m, n, n * m.usd, f["grab the BOTTOM edge and pull"],
                             f["press the screen edge to twist it off"]))
    return out


def cheapest_reaching(points: list[Point], target_lbf: float) -> Point | None:
    ok = [pt for pt in points if pt.bottom_lbf >= target_lbf]
    return min(ok, key=lambda pt: pt.cost) if ok else None


# ------------------------------------------------------------------------------ sheet
def render(path: Path, points: list[Point], rep: dict) -> None:
    PAPER, INK, MUTED, RULE = "#f7f8fa", "#111", "#5b6166", "#d0d4d8"
    COL = {"MM-C-20": "#8a8f94", "MM-C-25": "#c8791a", "MM-C-32": "#1b6ea8", "MM-C-36": "#0b7a4b", "3506K67": "#c0169a"}
    W, H = 1720, 1060

    def t(x, y, s, size=10.5, anchor="start", fill=INK, weight="normal"):
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica, Arial, sans-serif" '
                f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">'
                f'{html.escape(s)}</text>')

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<rect width="{W}" height="26" fill="#8a1c1c"/>',
         t(W / 2, 18, "REFERENCE ONLY — one hold model (force_table), vendor prices on a date, a 35 % derate that is a "
                      "rule of thumb. Types cannot be mixed: the magnet height is the standoff.", 11.5, "middle", "#fff", "bold"),
         t(40, 62, "MAGNET ECONOMICS — hold against cost, every type, every count the plate takes", 21, weight="bold"),
         t(40, 84, f"Hold = force to pull the BOTTOM edge off, plate pivoting on the fridge's top edge (the page's "
                   f"'lets go at' figure). Grab case {GRAB_LBF:.0f} lb; the dashed lines are 2x, 4x and 6x on it.",
           11.5, fill=MUTED)]

    # ---- chart
    cx0, cy0, cw, ch = 90, 130, 1000, 640
    # The chart stops at $130: the O48 at 8 and 12 sits far off to the right and would squash the
    # region where the decision lives. Those two points are in the table.
    XCAP = 130.0
    shown = [pt for pt in points if pt.cost <= XCAP]
    xmax = XCAP * 1.04
    ymax = max(pt.bottom_lbf for pt in shown) * 1.10

    def X(c):
        return cx0 + c / xmax * cw

    def Y(v):
        return cy0 + ch - v / ymax * ch

    o.append(f'<rect x="{cx0}" y="{cy0}" width="{cw}" height="{ch}" fill="#fff" stroke="{RULE}"/>')
    for k in range(0, int(xmax) + 1, 25):
        o.append(f'<line x1="{X(k):.1f}" y1="{cy0}" x2="{X(k):.1f}" y2="{cy0 + ch}" stroke="#eceff1"/>')
        o.append(t(X(k), cy0 + ch + 16, f"${k}", 9.5, "middle", MUTED))
    for k in range(0, int(ymax) + 1, 50):
        o.append(f'<line x1="{cx0}" y1="{Y(k):.1f}" x2="{cx0 + cw}" y2="{Y(k):.1f}" stroke="#eceff1"/>')
        o.append(t(cx0 - 8, Y(k) + 3, f"{k} lb", 9.5, "end", MUTED))
    o.append(t(cx0 + cw / 2, cy0 + ch + 36, "magnets, total cost (US$, qty-1 prices)", 10.5, "middle", INK, "bold"))
    o.append(f'<text x="{cx0 - 60}" y="{cy0 + ch / 2}" transform="rotate(-90 {cx0 - 60} {cy0 + ch / 2})" '
             f'font-family="Helvetica, Arial, sans-serif" font-size="10.5" font-weight="bold" text-anchor="middle" fill="{INK}">'
             f'pull-off at the bottom edge (lb)</text>')
    for mult, lab in ((2, "2x — nuisance"), (4, "4x"), (6, "6x — safety")):
        v = GRAB_LBF * mult
        if v < ymax:
            o.append(f'<line x1="{cx0}" y1="{Y(v):.1f}" x2="{cx0 + cw}" y2="{Y(v):.1f}" stroke="#b00020" stroke-width="0.9" stroke-dasharray="6 4"/>')
            o.append(t(cx0 + cw - 6, Y(v) - 4, f"{lab}: {v:.0f} lb", 9.2, "end", "#b00020", "bold"))
    for k, m in enumerate(MAGNETS):
        pts = [pt for pt in shown if pt.magnet is m]
        path_d = " ".join(f"{'M' if i == 0 else 'L'}{X(pt.cost):.1f} {Y(pt.bottom_lbf):.1f}" for i, pt in enumerate(pts))
        o.append(f'<path d="{path_d}" fill="none" stroke="{COL[m.part]}" stroke-width="2"/>')
        for pt in pts:
            o.append(f'<circle cx="{X(pt.cost):.1f}" cy="{Y(pt.bottom_lbf):.1f}" r="4.5" fill="{COL[m.part]}" stroke="#fff" stroke-width="1.2"/>')
            o.append(t(X(pt.cost) + 6, Y(pt.bottom_lbf) + 12, f"x{pt.n}", 8.6, "start", COL[m.part], "bold"))
        last = pts[-1]
        # series label to the right of its last point, staggered so near-parallel lines do not collide
        lx, ly = X(last.cost) + 12, Y(last.bottom_lbf) - 4 - (k % 2) * 14
        o.append(t(lx, ly, f"{m.part}  O{m.dia_mm:.0f}  {m.lb_per_usd:.1f} lb/$", 9.6, "start", COL[m.part], "bold"))
    off = [pt for pt in points if pt.cost > XCAP]
    o.append(t(cx0 + cw - 8, cy0 + 16, "off the chart: " + "; ".join(f"{pt.n} x {pt.magnet.part} ${pt.cost:.0f}, {pt.bottom_lbf:.0f} lb" for pt in off),
               9.2, "end", MUTED))

    # ---- table: cheapest way to each target, and lb per dollar
    tx, ty = 1120, 130
    o.append(f'<rect x="{tx}" y="{ty}" width="560" height="640" rx="7" fill="#fff" stroke="{RULE}"/>')
    o.append(t(tx + 16, ty + 24, "THE LADDER, PER MAGNET", 12.5, weight="bold"))
    heads = [("part", 0), ("O x h", 90), ("stud", 160), ("derated", 215), ("$", 285), ("lb / $", 335), ("pad", 395)]
    for name, dx in heads:
        o.append(t(tx + 16 + dx, ty + 48, name, 8.6, fill=MUTED, weight="bold"))
    y = ty + 68
    for m in MAGNETS:
        o.append(t(tx + 16, y, m.part, 9.8, fill=COL[m.part], weight="bold"))
        o.append(t(tx + 106, y, f"{m.dia_mm:.0f} x {m.h_mm:.1f}", 9.4))
        o.append(t(tx + 176, y, m.stud, 9.4))
        o.append(t(tx + 231, y, f"{m.derated:.1f} lb", 9.4))
        o.append(t(tx + 301, y, f"${m.usd:.2f}", 9.4))
        o.append(t(tx + 351, y, f"{m.lb_per_usd:.2f}", 9.8, weight="bold"))
        o.append(t(tx + 411, y, m.pad[:24], 8.4, fill=MUTED))
        y += 20
    y += 14
    o.append(t(tx + 16, y, "CHEAPEST WAY TO EACH TARGET (bottom-edge pull-off)", 12.5, weight="bold"))
    y += 24
    for mult in (2, 3, 4, 6, 8):
        target = GRAB_LBF * mult
        best = cheapest_reaching(points, target)
        if best is None:
            o.append(t(tx + 16, y, f"{mult}x ({target:.0f} lb): nothing on the plate reaches it", 9.8, fill="#b00020"))
        else:
            alts = sorted((pt for pt in points if pt.bottom_lbf >= target and pt is not best), key=lambda pt: pt.cost)[:2]
            o.append(t(tx + 16, y, f"{mult}x ({target:.0f} lb):", 9.8, weight="bold"))
            o.append(t(tx + 96, y, f"{best.n} x {best.magnet.part} = ${best.cost:.2f}, holds {best.bottom_lbf:.0f} lb", 9.8, fill=COL[best.magnet.part], weight="bold"))
            if alts:
                o.append(t(tx + 96, y + 13, "then " + "; ".join(f"{a.n} x {a.magnet.part} ${a.cost:.2f} ({a.bottom_lbf:.0f} lb)" for a in alts), 8.4, fill=MUTED))
        y += 32
    y += 6
    o.append(t(tx + 16, y, "WHAT THE CHART SAYS", 12.5, weight="bold"))
    notes = [
        "Hold is linear in count for one type: no knee inside a line. The knees are the plate's position budget "
        "(4 corners, 4 mid-side spares already cut, 4 more with a second row pair) and the jump between types.",
        "Per dollar the small K&J magnets beat the O48 by 25-35 %, and eight of them fit where four O48 sit.",
        "The 35 % derate is generous to thin magnets: a paint gap costs a 7 mm magnet a larger share of its "
        "rating than an 11.5 mm one. Measure one on the panel before buying twelve.",
        "Every K&J option is an 8 mm standoff and a 5/16 in pad, an M-thread stud and a smaller plate hole. "
        "Pick the TYPE first (it sets the plate), then the COUNT (spares are just holes).",
    ]
    for para in notes:
        words, line, lines = para.split(), "", []
        for w_ in words:
            if len(line) + len(w_) + 1 > 92:
                lines.append(line)
                line = w_
            else:
                line = (line + " " + w_).strip()
        lines.append(line)
        for i, ln in enumerate(lines):
            o.append(t(tx + 16, y + 18 + i * 12.5, ln, 9.0, fill="#333"))
        y += 18 + 12.5 * len(lines) + 2

    o.append(t(40, H - 60, f"Twist (press the screen edge to unseat it) scales the same way and is never the limit: "
                          f"even 4 x MM-C-20 read {min(pt.twist_lbf for pt in points):.0f} lb against a 5 lb press.", 10, fill=MUTED))
    o.append(t(40, H - 42, "Sources: K&J product pages 2026-09-02; McMaster 3506K67 2026-08-27; hold model force_table.forces() "
                          "on the built plate (310 body, inset 32, neck 257).", 9.4, fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("magnet_economics.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)
    p = BracketParams()
    flat = G.derive_flat(p)
    geom = G.build_geometry(p, flat)
    rep = G.engineering_report(p, geom)
    pts = study(p, rep)
    for pt in pts:
        LOG.info("%-8s x%2d  $%6.2f  bottom %6.1f lb (%.1fx grab)  twist %5.1f lb", pt.magnet.part, pt.n, pt.cost,
                 pt.bottom_lbf, pt.grab_sf, pt.twist_lbf)
    for mult in (2, 4, 6):
        b = cheapest_reaching(pts, GRAB_LBF * mult)
        LOG.info("cheapest to %dx: %s", mult, f"{b.n} x {b.magnet.part} ${b.cost:.2f} ({b.bottom_lbf:.0f} lb)" if b else "none")
    render(args.out, pts, rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
