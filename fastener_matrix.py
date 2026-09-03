#!/usr/bin/env python3
"""Every fastener permutation behind the plate, with the arithmetic shown.

`stack_detail.svg` draws the stacks. This sheet is the WORKING: every nut construction McMaster
stocks in 5/16"-18, crossed with every washer option and with/without threadlocker, each with the
sum spelled out so nothing has to be taken on trust.

The governing sum never changes:

    plate + washer + nut  <=  stud

Everything else on this sheet is a consequence of it. Washer thicknesses are the MAX of the range
McMaster sells them to, because a stack that has to fit must survive the thickest one shipped.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
import generate_bracket as G
from generate_bracket import (FINISH, MATERIAL, SPECIFIED_LOCKER, SPECIFIED_NUT, SPECIFIED_WASHER, BracketParams,
                              stack_permutations)

LOG = logging.getLogger("matrix")

IN = G.MM_PER_INCH
INK, MUTED, RULE = "#14181c", "#6b757e", "#c9d1d8"
OK, BAD, MARG = "#0a8f6f", "#b00020", "#b8860b"

COLS = [
    ("#",            34,  "end"),
    ("nut",         274,  "start"),
    ("nut ht",       58,  "end"),
    ("washer",      168,  "start"),
    ("wshr t",       54,  "end"),
    ("plate + washer + nut", 176, "end"),
    ("= needs",      64,  "end"),
    ("vs stud",      62,  "end"),
    ("slack",        62,  "end"),
    ("locking",     134,  "start"),
    ("bearing",      70,  "end"),
    ("psi",          52,  "end"),
    ("nut part",     84,  "end"),
    ("washer part",  84,  "end"),
]


def _esc(s) -> str:
    """SVG is XML: a bare < or & in a label silently breaks the whole document."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _t(x, y, s, size=10.0, anchor="middle", fill=INK, weight="normal"):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}">{_esc(s)}</text>')


def render(path: Path, p: BracketParams) -> None:
    geom = G.build_geometry(p, G.derive_flat(p))
    rep = G.engineering_report(p, geom)
    clamp = rep["magnet_derated_pull_lbf"]
    rows = stack_permutations(p)

    groups = [("FITS", "ok", OK, "at least 0.50 mm of thread to spare"),
              ("INSIDE THE TOLERANCE STACK", "marginal", MARG,
               "within +/-0.50 mm — three stacked tolerances can swallow this; do not build on it"),
            ("DOES NOT FIT", "bad", BAD, "the stud ends before the nut does")]

    rowh, x0, y0 = 21.0, 40.0, 236.0
    W = x0 + sum(c[1] for c in COLS) + 40
    H = y0 + (len(rows) + len(groups) * 2) * rowh + 200

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfcfd"/>',
         _t(40, 48, "EVERY FASTENER PERMUTATION BEHIND THE PLATE", 20, anchor="start",
            weight="bold"),
         _t(40, 74, f"{len(rows)} combinations: {len(G.NUTS)} nut constructions x "
                    f"{len(G.WASHERS)} washer options, and with/without threadlocker for the nuts "
                    f"that do not lock on their own.", 12.5, anchor="start", fill=MUTED),
         _t(40, 96, "The governing sum, every row:", 12.5, anchor="start", fill=MUTED),
         _t(232, 96, "plate + washer + nut  <=  stud", 13.5, anchor="start", weight="bold"),
         _t(40, 118, f"plate {MATERIAL.thickness:.2f} mm ({MATERIAL.thickness_in:.3f} in) - "
                     f"stud {p.magnet_stud_len:.2f} mm ({p.magnet_stud_len/IN:.3f} in), fixed by "
                     f"the magnet - plate hole O{p.magnet_hole_dia:.1f} mm.", 12,
            anchor="start", fill=MUTED),
         _t(40, 140, "Washer thickness is the MAX of the range McMaster sells it to, never the "
                     "nominal: a stack that must fit has to survive the thickest one shipped.",
            12, anchor="start", fill=MUTED),
         _t(40, 162, "\"bearing\" is the annulus the OUTERMOST part presses on the plate with — "
                     f"the washer if there is one, else the nut's own face. Pressure is at the "
                     f"magnet's {clamp:.1f} lb.", 12, anchor="start", fill=MUTED),
         _t(40, 184, f"Nut and washer part numbers are the {FINISH.upper()}-OXIDE ones where "
                     f"stocked; a number in grey means only plain 18-8 exists.", 12,
            anchor="start", fill=MUTED)]

    # header
    x = x0
    for name, w, anchor in COLS:
        ax = x + (w - 6 if anchor == "end" else 6)
        o.append(_t(ax, y0 - 8, name, 9.5, anchor=anchor, fill=MUTED, weight="bold"))
        x += w
    o.append(f'<line x1="{x0:.1f}" y1="{y0 - 3:.1f}" x2="{W - 40:.1f}" y2="{y0 - 3:.1f}" '
             f'stroke="{INK}" stroke-width="1.2"/>')

    y = y0
    n = 0
    for title, state, colour, blurb in groups:
        members = [r for r in rows if r.state == state]
        if not members:
            continue
        y += 6
        o.append(f'<rect x="{x0:.1f}" y="{y - 1:.1f}" width="{W - 40 - x0:.1f}" '
                 f'height="{rowh - 2:.1f}" fill="{colour}" fill-opacity="0.10"/>')
        # Measure the string that is ACTUALLY DRAWN, count suffix included. An earlier fix used
        # len(title) alone and still collided, because the "— 11" is appended at draw time.
        head = f"{title} — {len(members)}"
        o.append(_t(x0 + 8, y + 13, head, 11.5, anchor="start", weight="bold", fill=colour))
        o.append(_t(x0 + 24 + len(head) * 6.9, y + 13, blurb, 10, anchor="start", fill=MUTED))
        y += rowh + 2

        for r in members:
            n += 1
            spec = (r.nut.key == SPECIFIED_NUT and r.washer.key == SPECIFIED_WASHER
                    and r.locker == SPECIFIED_LOCKER)
            if spec:
                o.append(f'<rect x="{x0:.1f}" y="{y - 1:.1f}" width="{W - 40 - x0:.1f}" '
                         f'height="{rowh - 2:.1f}" fill="{OK}" fill-opacity="0.16"/>')
            elif n % 2 == 0:
                o.append(f'<rect x="{x0:.1f}" y="{y - 1:.1f}" width="{W - 40 - x0:.1f}" '
                         f'height="{rowh - 2:.1f}" fill="#eef1f4"/>')
            bw = "bold" if spec else "normal"
            wsh = r.washer.key != "none"
            lockcol = {"NONE": BAD}.get(r.locking, INK)
            pn_nut, fin_nut = G.part_no(f"nut_{r.nut.key}")
            pn_w, fin_w = G.part_no(f"washer_{r.washer.key}") if wsh else (None, "")

            cells = [
                (str(n), MUTED, "normal"),
                (r.nut.name + ("  <<< SPECIFIED" if spec else ""), INK, bw),
                (f"{r.nut.height:.2f}", INK, "normal"),
                (r.washer.name if wsh else "—", INK if wsh else MUTED, "normal"),
                (f"{r.washer.t:.2f}" if wsh else "0.00", INK if wsh else MUTED, "normal"),
                (f"{r.plate:.2f} + {r.washer.t:.2f} + {r.nut.height:.2f}", MUTED, "normal"),
                (f"{r.needed:.2f}", INK, "normal"),
                (f"{r.stud:.2f}", MUTED, "normal"),
                (f"{r.slack:+.2f}", colour, "bold"),
                (r.locking + (" (threadlocker)" if r.locker == "threadlocker" else ""),
                 lockcol, "bold" if r.locking != "NONE" else "normal"),
                (f"{r.bearing_area:.0f}", INK, "normal"),
                (f"{r.bearing_psi(clamp):.0f}", INK, "normal"),
                (pn_nut or "—", INK if fin_nut == "black" else MUTED, "normal"),
                (pn_w or "—", INK if fin_w == "black" else MUTED, "normal"),
            ]
            x = x0
            for (name, w, anchor), (txt, fill, weight) in zip(COLS, cells):
                ax = x + (w - 6 if anchor == "end" else 6)
                o.append(_t(ax, y + 14, txt, 9.5, anchor=anchor, fill=fill, weight=weight))
                x += w
            y += rowh

    # ---- what the table is telling you ---------------------------------------------------------
    fy = y + 40
    fits = [r for r in rows if r.state == "ok"]
    mech = [r for r in fits if r.nut.locking == "mechanical"]
    best_area = max(fits, key=lambda r: r.bearing_area)
    o.append(f'<rect x="40" y="{fy - 22:.1f}" width="{W - 80:.1f}" height="132" fill="#fff" '
             f'stroke="{OK}" stroke-width="1.6" rx="4"/>')
    spec = next(r for r in rows if r.nut.key == SPECIFIED_NUT
                and r.washer.key == SPECIFIED_WASHER and r.locker == SPECIFIED_LOCKER)
    o.append(_t(56, fy, f"SPECIFIED: {spec.label}", 14, anchor="start", weight="bold", fill=OK))
    runner = next((r for r in sorted(fits, key=lambda r: -r.slack)
                   if r.nut.locking == "mechanical" and r is not spec), None)
    o.append(_t(56, fy + 24,
                f"Of {len(rows)} permutations, {len(fits)} fit and {len(mech)} of those lock "
                f"MECHANICALLY. The specified stack: {spec.slack:+.2f} mm of thread to spare, "
                f"{spec.bearing_area:.0f} mm2 of bearing, locking {spec.nut.locking if spec.locker == 'dry' else spec.locker}.",
                11.5, anchor="start", fill=MUTED))
    o.append(_t(56, fy + 44,
                f"THICKNESS is what runs out in this stack, not diameter: the stud is "
                f"{rows[0].stud:.1f} mm (an ESTIMATE for the MM-C-32 until K&J's drawing is read) "
                f"against a {rows[0].plate:.2f} mm plate, so a 1.6 mm washer is the difference "
                f"between fitting and the tolerance band.", 11.5, anchor="start", fill=MUTED))
    o.append(_t(56, fy + 68,
                (f"Runner-up with a mechanical lock: {runner.label}, {runner.slack:+.2f} mm, "
                 f"{runner.bearing_area:.0f} mm2." if runner else "No other mechanical-locking stack fits.")
                + " M6 part numbers are NOT VERIFIED: this catalogue is DIN nominal heights, not "
                "McMaster's tables yet.", 11.5, anchor="start", fill=MUTED))
    o.append(_t(56, fy + 92,
                f"None of this is close to a bearing problem: even the smallest annulus here is "
                f"~{MATERIAL.yield_psi / rows[0].bearing_psi(clamp):.0f}x under {MATERIAL.name}'s "
                f"{MATERIAL.yield_psi:.0f} psi yield. The stack is decided by THREAD LENGTH and "
                f"by locking, not by bearing.", 11.5, anchor="start", fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — %d permutations: %d fit, %d marginal, %d fail", path, len(rows),
             len(fits), sum(1 for r in rows if r.state == "marginal"),
             sum(1 for r in rows if r.state == "bad"))
    for r in rows:
        LOG.debug("%-64s %5.2f vs %5.2f  %+6.2f  %-22s %5.0f mm2", r.label, r.needed, r.stud,
                  r.slack, r.locking, r.bearing_area)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("fastener_matrix.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
