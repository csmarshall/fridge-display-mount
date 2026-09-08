#!/usr/bin/env python3
"""Removability band: how hard the mount is to move, by magnet count, against what a human does.

Charles, 2026-09-08: "reliably means it takes effort to move it but it's not impossible" — a bump
must not shift it, a person applying real effort must be able to. That is a BAND, not a floor, so
the magnet answer is the count whose forces sit inside it, not the most hold for the money.

Forces are force_table.forces() with magnet_economics' per-type derated pull: the same model as
every other sheet. The human reference forces are ESTIMATES with no vendor behind them — a
casual hip or elbow bump, a deliberate one-hand pull, a determined two-hand pull. Change them
at the top; the band moves with them.

Which direction matters for each act:
  bump          -> slide front-to-back (magnet shear at mu 0.2 PLUS the hanging weight on the arm's EPDM skin at mu_arm_pad)
                   and twist about the spine (an edge knock)
  reposition    -> slide front-to-back (the intended way to shift it along the panel)
  take it off   -> lift straight up (weight + magnet shear), or peel the bottom edge out first
The hook carries the weight in every case: nothing here can drop the screen. What a bump can do is
shift it a few millimetres; what a person can do is slide it or lift it off.
"""
from __future__ import annotations

import argparse
import html
import logging
import sys
from pathlib import Path
from typing import Sequence

import generate_bracket as G
import magnet_economics as ME
from bracket_common import LOG_LEVELS, configure_logging
from generate_bracket import BracketParams

LOG = logging.getLogger("remov")
# Human reference forces, lbf. ESTIMATES — ergonomics rules of thumb, not measurements.
BUMP_LBF = 20.0            # a casual hip / elbow / shoulder bump, sustained for the moment it lasts
BUMP_MARGIN = 1.5          # slide resistance must exceed the bump by this much to count as 'will not shift'
ONE_HAND_LBF = 45.0        # a deliberate one-hand pull or push
TWO_HAND_LBF = 100.0       # a determined two-hand pull at waist to chest height
COUNTS = (4, 6, 8)
TYPES = ("MM-C-25", "MM-C-32", "MM-C-36")
ACTS = [("slide front-to-back", "slide it front-to-back", "bump / reposition"),
        ("press the screen edge to twist it off", "press the screen edge to twist it off", "edge knock"),
        ("lift straight up (weight + shear)", "lift the whole thing straight UP", "take it off"),
        ("peel the bottom edge out", "grab the BOTTOM edge and pull", "take it off, bottom first")]


def table(p: BracketParams, rep: dict) -> dict[tuple[str, int], dict[str, float]]:
    out = {}
    by_part = {m.part: m for m in ME.MAGNETS}
    for part in TYPES:
        for n in COUNTS:
            out[(part, n)] = ME.hold(n, by_part[part], p, rep)
    return out


def verdict(f: dict[str, float]) -> tuple[str, str]:
    slide = f["slide it front-to-back"]
    lift = f["lift the whole thing straight UP"]
    if slide < BUMP_LBF:
        return "bump can shift it", "#b02a2a"
    if slide < BUMP_LBF * BUMP_MARGIN:
        return f"under {BUMP_MARGIN:g}x bump margin", "#b8860b"
    if lift <= TWO_HAND_LBF:
        return "in the band", "#0b7a4b"
    return "needs two people or a pry", "#b8860b"


def render(path: Path, p: BracketParams, rep: dict, tb: dict) -> None:
    PAPER, INK, MUTED, RULE = "#f7f8fa", "#111", "#5b6166", "#d0d4d8"
    W, H = 1240, 700
    VW = 190                                  # verdict column
    x0, lw, cw = 40, 240, (W - 80 - 240 - VW) / len(ACTS)
    fitted = rep["part_nos"]["magnet"]["plain"], rep["magnet_only_magnets"]

    def t(x, y, s, size=10.0, anchor="start", fill=INK, weight="normal"):
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica, Arial, sans-serif" font-size="{size}" '
                f'text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">{html.escape(s)}</text>')

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         t(40, 44, "REMOVABILITY BAND — a bump must not shift it, a person must be able to", 20, weight="bold"),
         t(40, 66, f"Force to move the mount each way, by magnet set, against three human references (ESTIMATES): bump {BUMP_LBF:.0f} lb, "
                   f"one hand {ONE_HAND_LBF:.0f} lb, two hands {TWO_HAND_LBF:.0f} lb. Green = in the band: slide resistance at least {BUMP_MARGIN:g}x "
                   "the bump, and two hands can lift it off.", 10.5, fill=MUTED),
         t(40, 82, f"Hangs {rep['total_hanging_lbf']:.1f} lb on the hook whichever set is fitted; the magnets only keep it flat. Slide "
                   f"credits magnet shear at mu {p.mu_magnet_face:g} plus the weight on the arm's EPDM skin at mu {p.mu_arm_pad:g} (ESTIMATE, decided 2026-09-08).",
           10.5, fill=MUTED)]
    y = 118
    for j, (label, _, act) in enumerate(ACTS):
        x = x0 + lw + j * cw
        o.append(t(x + cw / 2, y, label, 10.5, "middle", weight="bold"))
        o.append(t(x + cw / 2, y + 14, act, 8.8, "middle", MUTED))
    o.append(f'<line x1="40" y1="{y + 22}" x2="{W - 40}" y2="{y + 22}" stroke="{RULE}"/>')
    y += 44
    by_part = {m.part: m for m in ME.MAGNETS}
    for part in TYPES:
        m = by_part[part]
        o.append(t(x0, y, f"{part}  O{m.dia_mm:g} x {m.h_mm:g} mm, {m.derated:.1f} lb derated, ${m.usd:.2f} ea", 10, fill=MUTED, weight="bold"))
        y += 8
        for n in COUNTS:
            f = tb[(part, n)]
            y += 30
            vtxt, vcol = verdict(f)
            is_fit = (part, n) == fitted
            o.append(f'<rect x="34" y="{y - 20}" width="{W - 68}" height="30" rx="5" fill="{vcol}" fill-opacity="{0.16 if is_fit else 0.07}"'
                     + (f' stroke="{vcol}" stroke-width="1.5"' if is_fit else "") + "/>")
            o.append(t(x0 + 8, y, f"{n} x  ${n * m.usd:.2f}" + ("   AS BUILT" if is_fit else ""), 11.5, weight="bold"))
            for j, (_, key, _) in enumerate(ACTS):
                x = x0 + lw + j * cw
                v = f[key]
                ref = ("< bump" if v < BUMP_LBF else "one hand" if v <= ONE_HAND_LBF else "two hands" if v <= TWO_HAND_LBF else "> two hands")
                o.append(t(x + cw / 2 - 30, y, f"{v:.0f} lb", 12, "end", weight="bold"))
                o.append(t(x + cw / 2 - 22, y, ref, 9.2, "start", MUTED))
            o.append(t(W - 48, y, vtxt, 10, "end", vcol, "bold"))
        y += 22
    y += 8
    o.append(f'<line x1="40" y1="{y}" x2="{W - 40}" y2="{y}" stroke="{RULE}"/>')
    notes = [
        "Read across a row: the smallest number is what a bump has to beat (slide). The lift figure is what it takes to get it off the fridge "
        "the intended way; peel is the hard way and is high on every set because eight levers fight it.",
        "Nothing on this sheet drops the screen: the hook carries the weight. A set above the band is not unsafe, it is inconvenient — "
        "repositioning becomes a two-person job. A set below it walks when the fridge door slams.",
        "The 35 % derate flatters thin magnets on painted sheet; a measured pull on the actual panel would move every number here by the "
        "same factor. The human references are round numbers; move them at the top of removability.py and the verdicts follow.",
    ]
    for i, s in enumerate(notes):
        o.append(t(40, y + 20 + 16 * i, s, 9.8, fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("removability.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)
    G.set_material("mild-steel", 0.187)     # design 3's plate — the one on order (decided 2026-09-08)
    p = BracketParams()
    rep = G.engineering_report(p, G.build_geometry(p, G.derive_flat(p)))
    tb = table(p, rep)
    for (part, n), f in tb.items():
        LOG.info("%-8s x%d  slide %5.1f  twist %5.1f  lift %5.1f  peel %6.1f  -> %s", part, n, f["slide it front-to-back"],
                 f["press the screen edge to twist it off"], f["lift the whole thing straight UP"], f["grab the BOTTOM edge and pull"],
                 verdict(f)[0])
    render(args.out, p, rep, tb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
