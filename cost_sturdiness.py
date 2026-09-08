#!/usr/bin/env python3
"""Cost against sturdiness: plate gauge (rows) x magnet count (columns), with the cutoffs drawn.

Charles, 2026-09-08: "a table showing material thicknesses vs # of magnets with lines to show the
cutoffs you think for best cost <> sturdiness". Every cell is the LIVE plate price plus the magnets,
with the two sturdiness numbers that matter: the row's screen-edge flex under a 5 lb press (what a
finger feels) and the column's slide resistance (what a bump has to beat). Same models as
gauge_magnet_matrix.py and removability.py; nothing is re-derived here.

The cutoffs, and where they come from:
  FEELS RIGID   rows with flex under 0.2 mm (thickness_study.py's band). Above the line the plate
                reads as flexible under a firm touch, whatever the safety factor says.
  BUMP MARGIN   columns whose slide resistance is at least 1.5x a 20 lb bump (removability.py).
  DOMINATED     a row that costs more than 0.187 in steel AND flexes more is greyed: there is no
                reason to buy it. Thicker-and-dearer rows that flex less are not dominated, but the
                flex they buy is below anything a finger notices — the diminishing-returns line.
"""
from __future__ import annotations

import argparse
import html
import logging
import sys
from pathlib import Path
from typing import Sequence

import gauge_magnet_matrix as GM
import generate_bracket as G
import magnet_economics as ME
import prices as PR
import removability as RM
from bracket_common import LOG_LEVELS, configure_logging

LOG = logging.getLogger("cost")
FEELS_RIGID_MM = 0.2          # thickness_study.py's "feels rigid" band (it is a literal there)
MAGNET = "3506K64"
COUNTS = (4, 6, 8)
CHOSEN = ("mild-steel", 0.187), 8


def render(path: Path, rows: list[GM.Row]) -> None:
    PAPER, INK, MUTED, RULE, HI, CUT = "#f7f8fa", "#111", "#5b6166", "#d0d4d8", "#0b7a4b", "#b02a2a"
    m = {x.part: x for x in ME.MAGNETS}[MAGNET]
    W = 1180
    x0, lw = 40, 330
    cw = (W - 80 - lw) / len(COUNTS)
    rh = 56
    top = 150
    H = top + 60 + len(rows) * rh + 150 + 16 * 9 + 22 * 3 + 20

    def t(x, y, s, size=10.0, anchor="start", fill=INK, weight="normal"):
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="{size}" '
                f'text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">{html.escape(s)}</text>')

    # order rows floppiest first so the rigid cutoff is one horizontal line
    rows = sorted(rows, key=lambda r: -r.screen_edge_mm)
    ref = next(r for r in rows if (r.family, r.thickness_in) == CHOSEN[0])
    dominated = {(r.family, r.thickness_in) for r in rows
                 if r.price and r.price.complete > ref.price.complete and r.screen_edge_mm > ref.screen_edge_mm}
    # magnet columns: slide resistance from the same hold model, plate-independent
    p119 = ref.p
    slide = {n: ME.hold(n, m, p119, ref.rep)["slide it front-to-back"] for n in COUNTS}
    lift = {}
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         t(40, 44, f"COST vs STURDINESS — plate gauge x {MAGNET} count, live prices, cutoffs drawn", 20, weight="bold"),
         t(40, 66, "Each cell: plate (bent, black powder coat, SendCutSend 2026-09-08) + magnets at the 5-9 break. Row = how much the screen edge "
                   "moves under a 5 lb press; column = how hard a bump must push to slide the mount.", 10.5, fill=MUTED),
         t(40, 82, f"Red lines are the cutoffs: feels rigid (< {FEELS_RIGID_MM:g} mm) and bump margin (slide >= {RM.BUMP_LBF * RM.BUMP_MARGIN:.0f} lb). "
                   "Grey rows cost more than 0.187 in steel and flex more — nothing to buy there. Green = chosen.", 10.5, fill=MUTED)]
    # column headers
    y = top - 30
    o.append(t(x0, y, "PLATE", 9.2, fill=MUTED, weight="bold"))
    o.append(t(x0, y + 14, "material / gauge, flex, plate price", 8.6, fill=MUTED))
    for j, n in enumerate(COUNTS):
        x = x0 + lw + j * cw
        ok = slide[n] >= RM.BUMP_LBF * RM.BUMP_MARGIN
        o.append(t(x + cw / 2, y, f"{n} x {MAGNET}   ${n * m.usd:.2f}", 11, "middle", weight="bold"))
        o.append(t(x + cw / 2, y + 14, f"slide {slide[n]:.0f} lb — " + ("bump margin OK" if ok else "under the bump margin"), 8.8, "middle",
                   HI if ok else CUT))
    o.append(f'<line x1="40" y1="{y + 22}" x2="{W - 40}" y2="{y + 22}" stroke="{RULE}"/>')
    # my ranking of the viable cells (Charles, 2026-09-08: "I don't want the plate to be too flimsy"):
    # stiffest plate first, then the most magnets — margin against two stacked estimates — then cost.
    viable = [(r, n) for r in rows for n in COUNTS
              if slide[n] >= RM.BUMP_LBF * RM.BUMP_MARGIN and r.screen_edge_mm < FEELS_RIGID_MM
              and (r.family, r.thickness_in) not in dominated]
    ranked = sorted(viable, key=lambda rn: (rn[0].screen_edge_mm, -rn[1], rn[0].price.complete + rn[1] * m.usd))
    rank = {(r.family, r.thickness_in, n): i + 1 for i, (r, n) in enumerate(ranked)}
    # rows
    y = top
    rigid_drawn = False
    for r in rows:
        key = (r.family, r.thickness_in)
        dom = key in dominated
        if not rigid_drawn and r.screen_edge_mm < FEELS_RIGID_MM:
            o.append(f'<line x1="34" y1="{y - 4}" x2="{W - 34}" y2="{y - 4}" stroke="{CUT}" stroke-width="2" stroke-dasharray="8 4"/>')
            o.append(t(x0 + lw - 12, y - 8, f"FEELS RIGID below this line (< {FEELS_RIGID_MM:g} mm)", 9, "end", CUT, "bold"))
            rigid_drawn = True
        fill = MUTED if dom else INK
        o.append(t(x0, y + 22, r.label + ("   dominated" if dom else ""), 11.5, fill=fill, weight="bold"))
        o.append(t(x0, y + 38, f"flex {r.screen_edge_mm:.3f} mm   plate ${r.price.complete:.2f}   {r.plate_kg:.2f} kg   neck {r.neck_sf:.0f}x",
                   8.8, fill=MUTED))
        for j, n in enumerate(COUNTS):
            x = x0 + lw + j * cw
            total = r.price.complete + n * m.usd
            chosen = key == CHOSEN[0] and n == CHOSEN[1]
            ok = slide[n] >= RM.BUMP_LBF * RM.BUMP_MARGIN and r.screen_edge_mm < FEELS_RIGID_MM and not dom
            if chosen:
                o.append(f'<rect x="{x + 4}" y="{y + 4}" width="{cw - 8}" height="{rh - 8}" rx="6" fill="{HI}" fill-opacity="0.14" stroke="{HI}" stroke-width="2"/>')
            elif ok:
                o.append(f'<rect x="{x + 4}" y="{y + 4}" width="{cw - 8}" height="{rh - 8}" rx="6" fill="{HI}" fill-opacity="0.05"/>')
            o.append(t(x + cw / 2, y + 26, f"${total:.2f}", 14, "middle", MUTED if (dom or not ok) else INK, "bold"))
            if ok:
                rk = rank[(r.family, r.thickness_in, n)]
                o.append(f'<circle cx="{x + 22}" cy="{y + 22}" r="11" fill="{HI if rk <= 3 else MUTED}"/>')
                o.append(t(x + 22, y + 26, str(rk), 11, "middle", "#fff", "bold"))
            o.append(t(x + cw / 2, y + 42, "CHOSEN" if chosen else ("viable" if ok else ("dominated" if dom else
                      ("flexible" if r.screen_edge_mm >= FEELS_RIGID_MM else "bump can shift it"))), 8.8, "middle",
                      HI if chosen or ok else MUTED))
        y += rh
    # vertical bump-margin cutoff between the last failing and first passing column
    for j in range(1, len(COUNTS)):
        a, b = COUNTS[j - 1], COUNTS[j]
        if slide[a] < RM.BUMP_LBF * RM.BUMP_MARGIN <= slide[b]:
            x = x0 + lw + j * cw
            o.append(f'<line x1="{x}" y1="{top - 56}" x2="{x}" y2="{y + 4}" stroke="{CUT}" stroke-width="2" stroke-dasharray="8 4"/>')
            o.append(t(x + 6, top - 44, "BUMP MARGIN right of this line", 9, "start", CUT, "bold"))
    # reading
    y += 24
    o.append(f'<line x1="40" y1="{y - 10}" x2="{W - 40}" y2="{y - 10}" stroke="{RULE}"/>')
    cheapest = min((r for r in rows if r.screen_edge_mm < FEELS_RIGID_MM and (r.family, r.thickness_in) not in dominated),
                   key=lambda r: r.price.complete)
    n_min = next(n for n in COUNTS if slide[n] >= RM.BUMP_LBF * RM.BUMP_MARGIN)
    lines = [
        f"Cheapest viable cell: {cheapest.label} with {n_min} x {MAGNET} = ${cheapest.price.complete + n_min * m.usd:.2f} "
        f"(flex {cheapest.screen_edge_mm:.3f} mm, slide {slide[n_min]:.0f} lb).",
        f"Chosen: {ref.label} with {CHOSEN[1]} x = ${ref.price.complete + CHOSEN[1] * m.usd:.2f}. The extra "
        f"${ref.price.complete + CHOSEN[1] * m.usd - (cheapest.price.complete + n_min * m.usd):.2f} buys "
        f"{cheapest.screen_edge_mm / ref.screen_edge_mm:.0f}x less flex and {slide[CHOSEN[1]] / slide[n_min]:.1f}x the slide resistance — "
        "margin against the 35 % magnet derate, which is the number nobody has measured.",
        "Diminishing returns: every plate dearer than 0.187 in steel either flexes more (grey) or removes flex no finger can feel; every "
        "magnet past 8 needs holes the plate does not have. The chosen cell is the corner of the viable region, not the middle of it.",
    ]
    for i, s in enumerate(lines):
        o.append(t(40, y + 16 * i + 4, s, 9.8, fill=INK if i < 2 else MUTED, weight="bold" if i == 1 else "normal"))
    y += 16 * len(lines) + 22
    o.append(t(40, y, "MY ORDER OF PREFERENCE — stiffest plate first (\"I don't want the plate to be too flimsy\"), then the most "
                      "magnets, then cost. The numbers in the cells are this list.", 10, weight="bold"))
    why = {
        ("mild-steel", 0.187): "the only gauge whose flex is below anything a finger can find; hot-rolled, so it undercuts 0.135",
        ("mild-steel", 0.119): "fine on paper, 4x the flex of 0.187 for $13 less — not a trade worth making",
        ("mild-steel", 0.104): "inside the rigid band by a third; the thinnest steel I would call not flimsy, and only just",
    }
    yy = y
    last_gauge = None
    for i, (r, n) in enumerate(ranked):
        key = (r.family, r.thickness_in)
        if key != last_gauge:
            yy += 22
            o.append(t(52, yy, f"{r.label} — {why[key]}", 9.6, weight="bold", fill=INK if i < 3 else MUTED))
            last_gauge = key
        yy += 16
        total = r.price.complete + n * m.usd
        tag = {8: "full margin against both estimates", 6: "in the band, one estimate less margin",
               4: "passes only because the rubber skin is credited — an estimate on an estimate"}[n]
        o.append(t(70, yy, f"{i + 1}.  {n} x {MAGNET}   ${total:.2f}   flex {r.screen_edge_mm:.3f} mm, slide {slide[n]:.0f} lb   —   {tag}",
                   9.4, fill=INK if i < 3 else MUTED, weight="bold" if i == 0 else "normal"))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("cost_sturdiness.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)
    rows = [GM.evaluate_gauge(f, t) for f, t in GM.GAUGES if (f, t) in PR.PLATE_SWEEP]
    G.set_material(*GM.AS_BUILT)
    render(args.out, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
