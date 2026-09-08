#!/usr/bin/env python3
"""Gauge x magnet matrix: every bendable material and thickness against every magnet type and count.

The two earlier studies never met. thickness_study.py swept gauge at one (absent) magnet set;
magnet_economics.py swept magnets at one gauge. This sheet crosses them on the SAME models:
generate_bracket.engineering_report() for each gauge (plate mass, hanging load, neck and body
SF), thickness_study's cantilever for the screen-edge flex with the material's own modulus, and
force_table/magnet_economics' hold model for each magnet set. Prices come from prices.py only.

What the cross shows, and why it is worth a sheet: the grab-the-bottom-edge hold does NOT depend
on the plate at all — it is magnets against a hand — so the cheapest set to 6x is the same on every
row. What the gauge changes is the hanging weight (peel), the flex a finger feels, and the plate
price. Those are the cells; the magnet answer is a column.
"""
from __future__ import annotations

import argparse
import html
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import generate_bracket as G
import magnet_economics as ME
import prices as PR
from bracket_common import LOG_LEVELS, configure_logging
from generate_bracket import BracketParams, MM_PER_INCH

LOG = logging.getLogger("matrix")
N_PER_LBF = 4.4482216
# Young's modulus by family. A material property, not derivable — thickness_study.py carries only
# the aluminium figure because it predates steel.
E_MPA = {"5052": 70_300.0, "mild-steel": 200_000.0}
GAUGES = [("mild-steel", t) for t in (0.104, 0.119, 0.135, 0.187)] + [("5052", t) for t in (0.100, 0.125, 0.187, 0.250)]
AS_BUILT = ("mild-steel", G.Material().thickness_in)
COUNTS = (4, 6, 8, 12)
CUT_MAX = 8            # positions the plate actually has; 12 needs four more holes
TARGET_SF = 6.0


@dataclass(frozen=True)
class Row:
    family: str
    thickness_in: float
    plate_kg: float
    hanging_lbf: float
    neck_sf: float
    body_sf: float
    screen_edge_mm: float
    peel_lbf: float
    peel_lever_mm: float
    price: PR.PlatePrice | None
    rep: dict
    p: BracketParams

    @property
    def label(self) -> str:
        return f"{G.MATERIALS[self.family][3].split()[0]} .{int(round(self.thickness_in * 1000)):03d} in"


@dataclass(frozen=True)
class Cell:
    magnet: ME.Magnet
    n: int
    grab_sf: float
    peel_sf: float
    magnets_usd: float


def evaluate_gauge(family: str, t_in: float) -> Row:
    G.set_material(family, t_in)
    p = BracketParams()
    flat = G.derive_flat(p)
    geom = G.build_geometry(p, flat)
    rep = G.engineering_report(p, geom)
    t = t_in * MM_PER_INCH
    # thickness_study's cantilever, VESA screw out to the magnet, with THIS material's modulus
    force_n = rep["torsion_force_per_magnet_lbf"] * N_PER_LBF
    lever = p.magnet_spacing_x / 2.0 - p.vesa / 2.0
    second_moment = p.magnet_disc_dia * t ** 3 / 12.0
    defl = force_n * lever ** 3 / (3.0 * E_MPA[family] * second_moment)
    screen_edge = defl * (p.torsion_arm / (p.magnet_spacing_x / 2.0))
    key = (family, t_in)
    return Row(family, t_in, rep["plate_mass_kg"], rep["total_hanging_lbf"], rep["neck_sf"],
               rep["body_weak_axis_sf"], screen_edge, rep["peel_lbf"], rep["peel_lever_mm"],
               PR.PLATE_SWEEP.get(key), rep, p)


def peel_sf(row: Row, m: ME.Magnet, n: int) -> float:
    """Overturning about the plate's BOTTOM edge from the hung weight, resisted by every magnet on
    its own lever above that edge. Demand is the generator's own peel figure (W x d at the as-built
    lever), restated as a moment so it is independent of which magnet the generator fitted."""
    demand_in_lbf = row.peel_lbf * row.peel_lever_mm / MM_PER_INCH
    capacity = sum(m.derated * ((dy + row.p.body_h / 2.0) / MM_PER_INCH) for _, dy in ME.positions(n, row.p))
    return capacity / demand_in_lbf


def cells(row: Row) -> dict[tuple[str, int], Cell]:
    out = {}
    for m in ME.MAGNETS:
        for n in COUNTS:
            f = ME.hold(n, m, row.p, row.rep)
            out[(m.part, n)] = Cell(m, n, f["grab the BOTTOM edge and pull"] / ME.GRAB_LBF, peel_sf(row, m, n), n * m.usd)
    return out


def cheapest_to(cs: dict[tuple[str, int], Cell], sf: float) -> Cell | None:
    ok = [c for c in cs.values() if c.grab_sf >= sf and c.peel_sf >= sf and c.n <= CUT_MAX]
    return min(ok, key=lambda c: c.magnets_usd) if ok else None


# ------------------------------------------------------------------------------ sheet
def render(path: Path, rows: list[Row]) -> None:
    PAPER, INK, MUTED, RULE, HI = "#f7f8fa", "#111", "#5b6166", "#d0d4d8", "#0b7a4b"
    W = 1500
    mags = ME.MAGNETS
    x0, lw = 40, 250                          # row label block
    cw = (W - 80 - lw) / len(mags)            # one column per magnet type
    top_h = 40 + len(rows) * 21               # facts table
    rh = 58
    H = 150 + top_h + 62 + len(rows) * rh + 110

    def t(x, y, s, size=10.0, anchor="start", fill=INK, weight="normal"):
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="{size}" '
                f'text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">{html.escape(s)}</text>')

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         t(40, 44, "GAUGE x MAGNET MATRIX — every bendable material and thickness against every magnet type", 20, weight="bold"),
         t(40, 66, "Same models as the cut file: engineering_report() per gauge, force_table's hold per magnet set, prices.py for money.", 10.5, fill=MUTED),
         t(40, 82, f"Cells give the fewest magnets of that type reaching {TARGET_SF:.0f}x on BOTH a {ME.GRAB_LBF:.0f} lb grab of the bottom "
                   f"edge and peel from the hung weight, using only the {CUT_MAX} positions the plate has cut, with the cost of those magnets. Green = as built.", 10.5, fill=MUTED)]
    # ---- panel 1: what the gauge changes
    y = 112
    o.append(t(40, y, "WHAT THE GAUGE CHANGES (magnet-independent)", 11, fill=MUTED, weight="bold"))
    cols = [40, 250, 350, 460, 560, 660, 780, 930, 1150]
    hdr = ["material / gauge", "plate", "hangs", "neck SF", "body SF", "screen-edge flex", "peel demand",
           "cut only (live, real file)", "bent + coated (live, real file)"]
    y += 22
    for x, h in zip(cols, hdr):
        o.append(t(x, y, h, 9, fill=MUTED, weight="bold"))
    o.append(f'<line x1="40" y1="{y + 6}" x2="{W - 40}" y2="{y + 6}" stroke="{RULE}"/>')
    for r in rows:
        y += 21
        built = (r.family, r.thickness_in) == AS_BUILT
        if built:
            o.append(f'<rect x="34" y="{y - 14}" width="{W - 68}" height="20" rx="4" fill="{HI}" fill-opacity="0.1"/>')
        o.append(t(cols[0], y, r.label + (" — AS BUILT" if built else ""), 10.5, weight="bold" if built else "normal"))
        o.append(t(cols[1], y, f"{r.plate_kg:.2f} kg", 10))
        o.append(t(cols[2], y, f"{r.hanging_lbf:.1f} lb", 10))
        o.append(t(cols[3], y, f"{r.neck_sf:.0f}x", 10))
        o.append(t(cols[4], y, f"{r.body_sf:.0f}x", 10))
        o.append(t(cols[5], y, f"{r.screen_edge_mm:.3f} mm", 10))
        o.append(t(cols[6], y, f"{r.peel_lbf:.2f} lb", 10))
        pr = r.price
        o.append(t(cols[7], y, f"${pr.cut:.2f}" if pr else "not quoted", 10, fill=INK if pr else MUTED))
        o.append(t(cols[8], y, f"${pr.complete:.2f}  {pr.date}  {pr.note}"[:60] if pr and pr.complete else "not quoted", 10,
                   fill=INK if pr else MUTED, weight="bold" if pr else "normal"))
    # ---- panel 2: the matrix
    y = 150 + top_h
    o.append(t(40, y, "FEWEST MAGNETS OF EACH TYPE TO 6x, AND WHAT THEY COST — by gauge", 11, fill=MUTED, weight="bold"))
    y += 14
    for j, m in enumerate(mags):
        x = x0 + lw + j * cw
        o.append(f'<rect x="{x + 3}" y="{y}" width="{cw - 6}" height="40" rx="5" fill="#fff" stroke="{RULE}"/>')
        o.append(t(x + cw / 2, y + 16, m.part, 11, "middle", weight="bold"))
        o.append(t(x + cw / 2, y + 31, f"O{m.dia_mm:g} x {m.h_mm:g} mm, {m.rated_lbf:g} lb rated, ${m.usd:.2f}, {m.derated:.1f} lb derated",
                   8.4, "middle", MUTED))
    y += 48
    best_any = None
    for r in rows:
        built = (r.family, r.thickness_in) == AS_BUILT
        cs = cells(r)
        if built:
            o.append(f'<rect x="34" y="{y}" width="{W - 68}" height="{rh}" rx="5" fill="{HI}" fill-opacity="0.1"/>')
        o.append(t(x0, y + 24, r.label, 11.5, weight="bold"))
        o.append(t(x0, y + 40, f"{r.plate_kg:.2f} kg plate, hangs {r.hanging_lbf:.1f} lb, flex {r.screen_edge_mm:.3f} mm", 8.6, fill=MUTED))
        for j, m in enumerate(mags):
            x = x0 + lw + j * cw
            best = min((c for c in cs.values() if c.magnet is m and c.grab_sf >= TARGET_SF and c.peel_sf >= TARGET_SF
                        and c.n <= CUT_MAX), key=lambda c: c.magnets_usd, default=None)
            if best is None:
                twelve = cs[(m.part, 12)]
                o.append(t(x + cw / 2, y + 22, f"none in the {CUT_MAX} cut holes", 9.5, "middle", MUTED))
                o.append(t(x + cw / 2, y + 38, f"12 x (4 more holes) = {twelve.grab_sf:.1f}x, ${twelve.magnets_usd:.2f}", 8.6, "middle", MUTED))
                continue
            is_built = built and m.part == r.rep["part_nos"]["magnet"] and best.n == r.rep["magnet_count_fitted"]
            if is_built:
                o.append(f'<rect x="{x + 3}" y="{y + 4}" width="{cw - 6}" height="{rh - 8}" rx="5" fill="none" stroke="{HI}" stroke-width="2"/>')
            plate_usd = r.price.complete if r.price else None
            total = f"  plate+magnets ${plate_usd + best.magnets_usd:.2f}" if plate_usd is not None else ""
            o.append(t(x + cw / 2, y + 22, f"{best.n} x  ${best.magnets_usd:.2f}", 12, "middle", weight="bold"))
            o.append(t(x + cw / 2, y + 38, f"grab {best.grab_sf:.1f}x  peel {best.peel_sf:.0f}x{total}", 8.6, "middle", MUTED))
            if plate_usd is not None and (best_any is None or plate_usd + best.magnets_usd < best_any[0]):
                best_any = (plate_usd + best.magnets_usd, r, best)
        y += rh
    # ---- reading
    y += 20
    o.append(f'<line x1="40" y1="{y - 10}" x2="{W - 40}" y2="{y - 10}" stroke="{RULE}"/>')
    lines = [
        "The magnet answer is a COLUMN, not a cell: the grab hold is magnets against a hand and never sees the plate, so the fewest-to-6x count "
        "is the same on every row. Peel is where the plate weighs in, and even the heaviest gauge leaves it far above 6x.",
        "What the gauge actually buys is stiffness (a finger feels flex, not stress — neck and body SF are never near 1) at the cost of "
        "hanging weight and, on the same file, price. Aluminium halves the plate mass but its flex is 3x steel's at the same gauge.",
        "Plate prices are LIVE SendCutSend quotes on the real file (2026-09-08): cut only, and bent + coated. Hot-rolled .187 steel is cheaper "
        "than cold-rolled .135; aluminium at .100 and .125 is the cheapest plate but 3x the flex of steel at the same gauge.",
    ]
    if best_any:
        tot, r, c = best_any
        lines.append(f"Cheapest complete plate-and-magnet set on LIVE numbers: {r.label} with {c.n} x {c.magnet.part} = ${tot:.2f} "
                     f"(grab {c.grab_sf:.1f}x, peel {c.peel_sf:.0f}x, flex {r.screen_edge_mm:.3f} mm).")
    for i, s in enumerate(lines):
        o.append(t(40, y + 16 * i, s, 9.8, fill=INK if i == len(lines) - 1 else MUTED, weight="bold" if i == len(lines) - 1 else "normal"))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("gauge_magnet_matrix.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)
    rows = [evaluate_gauge(f, t) for f, t in GAUGES]
    G.set_material(*AS_BUILT)   # leave the module as the generator expects it
    for r in rows:
        cs = cells(r)
        best = cheapest_to(cs, TARGET_SF)
        LOG.info("%-22s plate %.2f kg hangs %5.1f lb  neck %3.0fx body %3.0fx  flex %.3f mm  peel %.2f lb  cheapest 6x: %s",
                 r.label, r.plate_kg, r.hanging_lbf, r.neck_sf, r.body_sf, r.screen_edge_mm, r.peel_lbf,
                 f"{best.n} x {best.magnet.part} ${best.magnets_usd:.2f}" if best else "none")
    render(args.out, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
