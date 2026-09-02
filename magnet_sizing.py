#!/usr/bin/env python3
"""Right-sizing the magnets: what each one actually has to do, and what that buys.

The hook designs fit McMaster 3506K67 — O48 x 11.51 mm, 175 lb rated, $23.92 — because the
brief's derate chain (35 % on painted appliance sheet, then mu = 0.2 for shear) made a big magnet
look necessary. The load path was then settled as a HOOK, so the magnets carry NO weight and NO
shear: they hold the plate flat. This sheet puts the real duties beside a ladder of smaller
male-stud magnets and reports the safety factor of each against each, with the two things a
smaller magnet changes — the standoff (which is the pad thickness) and the stud (which is the
hole size) — stated rather than hidden.

Duties, from generate_bracket's engineering report (portrait, 5 lb press, 4 body magnets):
    touch torsion   tension on the far-side pair while a finger presses the outer screen edge
    peel            the display's CG hangs 45.7 mm off the panel; the bottom pair holds it in
    grab-and-pull   someone pulls the bottom edge outward — an abuse case, not a use case.
                    What the page calls "lets go at 146 lb" is this, for the O48 set.
    creep / walk    NOT a magnet duty in a hook: the arm bears the weight; the magnets see shear
                    only if the arm walks on its foam, which is a jostle question, not a load.

Derate: 35 % of rated pull on 0.6–0.9 mm painted sheet with a paint gap (CLAUDE.md 1.1). That is
the same factor for every candidate, so the ladder compares like with like; a vendor's rated pull
is on thick bare steel at zero gap and nothing here is.
"""
from __future__ import annotations

import argparse
import html
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging

LOG = logging.getLogger("magsize")

DERATE = 0.35
LBF_PER_KG = 2.2046226218


@dataclass(frozen=True)
class Candidate:
    part: str
    vendor: str
    dia_mm: float
    height_mm: float          # magnet body = the standoff the pad must match
    stud: str
    rated_lbf: float
    usd: float
    date: str
    note: str = ""

    @property
    def derated_lbf(self) -> float:
        return self.rated_lbf * DERATE


# Sourced 2026-09-02 (single observations; see prices.py for the O48). Male stud only — the
# whole fastener stack is built on a stud through the plate with a nut behind.
CANDIDATES = [
    Candidate("MM-C-20", "K&J", 20.0, 7.0, "M4", 28.7, 0.0, "2026-09-02", "price not fetched"),
    Candidate("MM-C-25", "K&J", 25.0, 8.0, "M5", 48.5, 5.04, "2026-09-02", ""),
    Candidate("MM-C-32", "K&J", 32.0, 8.0, "M6", 75.0, 7.64, "2026-09-02", ""),
    Candidate("MM-C-36", "K&J", 36.0, 8.0, "M6", 90.4, 9.72, "2026-09-02",
              "fits a 2 in (50.8) flat bar with 7.4 mm each side — design 4's bar magnet"),
    Candidate("3506K67", "McMaster", 48.02, 11.51, "5/16-18", 175.0, 23.92, "2026-08-27",
              "AS FITTED in designs 1 and 3; AMF's equivalent is $25.68"),
]


@dataclass(frozen=True)
class Duty:
    name: str
    per_magnet_lbf: float
    basis: str


def duties(report: dict, grab_lbf: float = 20.0) -> list[Duty]:
    """Per-magnet demands from the hook generator's own report; grab is an assumed abuse load."""
    torsion = report["torsion_force_per_magnet_lbf"]
    peel_pair = report["peel_lbf"] / 2.0           # the bottom pair shares it
    grab_pair = grab_lbf / 2.0                      # pulling the bottom edge loads the bottom pair
    return [
        Duty("touch torsion, 5 lb at the screen edge", torsion,
             f"{report['torsion_moment_in_lbf']:.1f} in-lb over {report['magnet_spacing_mm']:.0f} mm, "
             f"shared by a pair"),
        Duty("peel from the display's CG offset", peel_pair,
             f"{report['peel_lbf']:.2f} lb total on the bottom pair"),
        Duty(f"grab the bottom edge and pull, {grab_lbf:.0f} lb", grab_pair,
             "ASSUMED abuse case, not a use case; the bottom pair takes it"),
    ]


def render(path: Path, cands: list[Candidate], duties_: list[Duty], report: dict, n_fitted: int) -> None:
    PAPER, INK, MUTED, RULE = "#f7f8fa", "#111", "#5b6166", "#d0d4d8"
    OK, WARN, BAD = "#0b7a4b", "#c8791a", "#b00020"
    W, H = 1720, 980

    def t(x, y, s, size=10.5, anchor="start", fill=INK, weight="normal"):
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica, Arial, sans-serif" '
                f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">'
                f'{html.escape(s)}</text>')

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<rect width="{W}" height="26" fill="#8a1c1c"/>',
         t(W / 2, 18, "REFERENCE ONLY — a sizing study. Rated pulls are vendor figures on thick bare steel; "
                      "every candidate is derated the same 35 %.", 11.5, "middle", "#fff", "bold"),
         t(40, 62, "RIGHT-SIZING THE MAGNETS — what they actually do, against what they could be", 21,
           weight="bold"),
         t(40, 84, "In a hook the magnets carry no weight and no shear. They hold the plate flat: a "
                   "touch press, the CG's peel, and whatever someone does to the bottom edge.", 11.5,
           fill=MUTED)]

    # ---- duties panel
    o.append(f'<rect x="40" y="104" width="620" height="230" rx="7" fill="#fff" stroke="{RULE}"/>')
    o.append(t(56, 128, "WHAT ONE MAGNET HAS TO HOLD", 12.5, weight="bold"))
    o.append(t(56, 146, f"{n_fitted} body magnets fitted; each duty lands on a PAIR", 9.6, fill=MUTED))
    y = 172
    for d in duties_:
        o.append(t(56, y, d.name, 10.8, weight="bold"))
        o.append(t(640, y, f"{d.per_magnet_lbf:.2f} lb / magnet", 11, "end", weight="bold"))
        o.append(t(56, y + 14, d.basis, 9.2, fill=MUTED))
        y += 40
    o.append(t(56, y + 4, "Derate chain: rated x 0.35 (painted 0.6-0.9 mm sheet, paint gap). Shear is not "
                          "a duty here — the arm carries the weight.", 9.2, fill=MUTED))

    # ---- ladder table
    o.append(f'<rect x="690" y="104" width="990" height="230" rx="7" fill="#fff" stroke="{RULE}"/>')
    o.append(t(706, 128, "THE LADDER — male-stud pot magnets, derated the same way", 12.5, weight="bold"))
    cols = [("part", 706), ("O x h mm", 830), ("stud", 920), ("rated", 985), ("derated", 1060),
            ("$ each", 1140), (f"x{n_fitted}", 1205)]
    for d in duties_:
        pass
    heads = cols + [(f"SF {i + 1}", 1290 + i * 90) for i in range(len(duties_))] + [("pad = h", 1560)]
    for name, x in heads:
        o.append(t(x, 152, name, 8.8, fill=MUTED, weight="bold"))
    o.append(t(706, 164, "SF 1 touch · SF 2 peel · SF 3 grab — derated pull / per-magnet duty", 8.4, fill=MUTED))
    y = 186
    for c in cands:
        fitted = c.part == "3506K67"
        o.append(t(706, y, c.part + (" (fitted)" if fitted else ""), 10, weight="bold" if fitted else "normal"))
        o.append(t(830, y, f"{c.dia_mm:.0f} x {c.height_mm:.1f}", 10))
        o.append(t(920, y, c.stud, 10))
        o.append(t(985, y, f"{c.rated_lbf:.0f} lb", 10))
        o.append(t(1060, y, f"{c.derated_lbf:.1f} lb", 10, weight="bold"))
        o.append(t(1140, y, f"${c.usd:.2f}" if c.usd else "n/a", 10))
        o.append(t(1205, y, f"${c.usd * n_fitted:.2f}" if c.usd else "n/a", 10))
        for i, d in enumerate(duties_):
            sf = c.derated_lbf / d.per_magnet_lbf
            col = OK if sf >= 4 else (WARN if sf >= 2 else BAD)
            o.append(t(1290 + i * 90, y, f"{sf:.1f}x", 10, fill=col, weight="bold"))
        o.append(t(1560, y, f"{c.height_mm:.2f} mm", 10))
        y += 24
    o.append(t(706, y + 6, "green >= 4x · amber 2-4x · red < 2x, on the DERATED figure", 8.6, fill=MUTED))

    # ---- what a smaller magnet changes
    o.append(f'<rect x="40" y="354" width="1640" height="300" rx="7" fill="#fff" stroke="{RULE}"/>')
    o.append(t(56, 378, "WHAT CHANGES IF THE MAGNET SHRINKS — the three things nobody prices", 12.5, weight="bold"))
    paras = [
        ("1. The standoff is the pad.", "The magnet body height is the plate-to-panel gap, and the "
         "pad must match it within -0.60/+0.30 mm (CLAUDE.md 1.5). The O48 is 11.51 mm, which 7/16 in "
         "foam (11.11) meets. Every K&J candidate is 8 mm: that is 5/16 in foam (7.94, -0.06 — in band) "
         "— stocked at McMaster, not yet sourced cheaper. So a smaller magnet is not a swap, it is a "
         "pad change too."),
        ("2. The stud is the hole.", "The plate is cut with O8.5 holes for a 5/16-18 stud. An M6 stud "
         "wants O6.5 (O8.5 would let it wander 1.25 mm each way before the washer stops it). That is a "
         "one-parameter change in the generator, but it must be made BEFORE the plate is cut, and it "
         "throws away the fastener matrix's 39 permutations — redo it for M6 nyloc + fender washer."),
        ("3. Margin is where the money went.", f"The O48 gives {cands[-1].derated_lbf / duties_[0].per_magnet_lbf:.0f}x "
         f"on the touch case. MM-C-36 gives {cands[3].derated_lbf / duties_[0].per_magnet_lbf:.0f}x and "
         f"MM-C-32 {cands[2].derated_lbf / duties_[0].per_magnet_lbf:.0f}x — still comfortable — and "
         f"on the 20 lb grab they read {cands[3].derated_lbf / duties_[2].per_magnet_lbf:.1f}x and "
         f"{cands[2].derated_lbf / duties_[2].per_magnet_lbf:.1f}x, which is where a real choice lives: "
         "does the bottom edge have to survive a deliberate pull, or just a press? Four MM-C-36 cost "
         f"${cands[3].usd * 4:.2f} against ${cands[-1].usd * 4:.2f}."),
    ]
    y = 404
    for head, body in paras:
        o.append(t(56, y, head, 11, weight="bold"))
        words, line, lines = body.split(), "", []
        for w_ in words:
            if len(line) + len(w_) + 1 > 150:
                lines.append(line)
                line = w_
            else:
                line = (line + " " + w_).strip()
        lines.append(line)
        for i, ln in enumerate(lines):
            o.append(t(56, y + 16 + i * 14, ln, 10.2, fill="#333"))
        y += 20 + 14 * len(lines) + 12

    # ---- recommendation
    o.append(f'<rect x="40" y="674" width="1640" height="230" rx="7" fill="#fff" stroke="{RULE}"/>')
    o.append(t(56, 698, "WHERE THIS LEAVES THE DECISION", 12.5, weight="bold"))
    rec = [
        "For designs 1 and 3 the O48 stays: the plate is cut for its stud, the 7/16 in pad matches its height, and "
        "the fastener stack is proven. The saving from four MM-C-36 is about $57 and costs a plate parameter, a new "
        "pad thickness and a redone fastener study — worth it only if the plate has not been cut yet AND the grab "
        "case is accepted at ~2x rather than ~7x.",
        "For design 4 (aluminium angle + flat bars) the magnets sit on 2 in bars, where an O48 does not fit and an "
        "MM-C-36 does. That design starts from the small magnet and its 8 mm pad, so nothing is thrown away.",
        "What would change this study: a measured grab load (what does a child actually pull with?), a measured "
        "pull-off on the real panel with one magnet (the 35 % derate is a rule of thumb from the brief, not a "
        "measurement), and a decision on whether pull-off is a safety case or a nuisance case.",
    ]
    y = 722
    for para in rec:
        words, line, lines = para.split(), "", []
        for w_ in words:
            if len(line) + len(w_) + 1 > 165:
                lines.append(line)
                line = w_
            else:
                line = (line + " " + w_).strip()
        lines.append(line)
        for i, ln in enumerate(lines):
            o.append(t(56, y + i * 14, ln, 10.2, fill="#333"))
        y += 14 * len(lines) + 12
    o.append(t(40, H - 30, "Sources: K&J product pages 2026-09-02 (MM-C-25 $5.04, MM-C-32 $7.64, MM-C-36 $9.72); McMaster "
                          "3506K67 $23.92 2026-08-27; duties from bracket_params.json.", 9.4, fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--params", type=Path, default=Path("bracket_params.json"))
    ap.add_argument("--grab", type=float, default=20.0, help="assumed bottom-edge pull, lb")
    ap.add_argument("--out", type=Path, default=Path("magnet_sizing.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)
    p = json.loads(args.params.read_text(encoding="utf-8"))
    rep = p["engineering"]
    n_fitted = sum(1 for h in p["holes"] if h["tag"] == "magnet")
    ds = duties(rep, args.grab)
    for d in ds:
        LOG.info("%-45s %.2f lb per magnet  (%s)", d.name, d.per_magnet_lbf, d.basis)
    for c in CANDIDATES:
        LOG.info("%-9s O%.0f x %.1f %s  rated %.0f -> derated %.1f lb  $%.2f  SF %s", c.part, c.dia_mm,
                 c.height_mm, c.stud, c.rated_lbf, c.derated_lbf, c.usd,
                 " / ".join(f"{c.derated_lbf / d.per_magnet_lbf:.1f}x" for d in ds))
    render(args.out, CANDIDATES, ds, rep, n_fitted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
