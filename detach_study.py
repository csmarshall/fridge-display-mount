#!/usr/bin/env python3
"""What force, in what direction, actually gets this off the fridge?

Each mode is worked from the same derated magnet pull the rest of the design uses (35% of rated,
for thin painted appliance sheet at a small gap). Where a mode is resisted by friction rather than
tension it uses mu, which is an estimate, not a measurement — those rows are the soft ones.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
import generate_bracket as G
import approval_sheet as A
from generate_bracket import BracketParams, build_geometry, derive_flat

LOG = logging.getLogger("detach")


def modes(params: BracketParams) -> list[tuple[str, str, float, str]]:
    flat = derive_flat(params)
    geom = build_geometry(params, flat)
    rep = G.engineering_report(params, geom)
    W = A.World(params, G.DISPLAY, "left")
    rows = A.magnet_rows(geom)
    offs = A.arm_magnet_offsets(params)
    pull = rep["magnet_derated_pull_lbf"]
    n_body, n_arm = len(rows) * 2, len(offs) * 2
    weight = rep["total_hanging_lbf"]
    mu = params.mu_magnet_face

    # Peel about the fridge's top edge. Resisting moment is fixed; the force needed depends
    # entirely on where you grab.
    resist_moment = A.let_go_lbf(params, W, rows, offs, pull) * (
        W.FH - (params.screen_centre_height - W.disp_h / 2.0))
    def pull_at(z: float) -> float:
        return resist_moment / max(W.FH - z, 1.0)

    top = params.screen_centre_height + W.disp_h / 2.0
    mid = params.screen_centre_height
    bot = params.screen_centre_height - W.disp_h / 2.0

    out = [
        ("Pull straight out, gripping the BOTTOM edge", "peel about the fridge's top edge",
         pull_at(bot), "the worst place to grab — longest lever"),
        ("Pull straight out, gripping the MIDDLE", "same, shorter lever",
         pull_at(mid), "where a hand naturally lands"),
        ("Pull straight out, gripping the TOP edge", "same, very short lever",
         pull_at(top), "the display would fail first"),
        ("Lift the whole thing straight UP", "body magnets in shear + lip magnets in TENSION",
         weight + n_body * pull * mu + n_arm * pull,
         "this is how you would try to remove it — see note"),
        ("Slide it along the panel, front to back", "every magnet in shear",
         (n_body + n_arm) * pull * mu,
         "MOVES it rather than detaching it — the hook does not resist this direction"),
        ("Press the screen edge until it twists off", "torsion about the vertical spine",
         params.press_force_lbf * (pull / (rep["torsion_force_per_side_lbf"] / len(rows))),
         "a firm touch press is about 5 lbf"),
        ("Hang off it downwards", "arm bears on the fridge top",
         float("inf"), "nothing to detach — it is already resting on the fridge"),
    ]
    return out, dict(n_body=n_body, n_arm=n_arm, pull=pull, weight=weight, mu=mu,
                     bot=bot, mid=mid, top=top)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Detachment force by direction.")
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)

    for label, br, ao in (("MINIMUM  4 body + 2 lip", (), ()),
                          ("AS BUILT  8 body + 4 lip", (75.0, 225.0), (40.0,))):
        p = BracketParams(extra_magnet_rows=br, extra_arm_magnet_offsets=ao)
        ms, info = modes(p)
        print(f"\n{'='*96}\n{label}  —  {info['n_body']} on the side, {info['n_arm']} on the top lip, "
              f"{info['pull']:.1f} lbf derated pull each\n{'='*96}")
        print(f"{'direction':<46}{'force':>12}   how it resists")
        for name, how, f, note in ms:
            val = "cannot" if f == float("inf") else f"{f:,.0f} lbf"
            print(f"{name:<46}{val:>12}   {how}")
            print(f"{'':<46}{'':>12}   {note}")
    print("\nCAVEAT — these assume the plate is rigid and every magnet lets go at once.")
    print("Peeling defeats them one at a time and takes far less: lifting one corner of the arm")
    print("breaks a single magnet at ~25 lbf with the arm itself as the lever. That is how you")
    print("would actually take it off, and it is why the numbers below are NOT removal forces.")
    print(f"\nFor scale: the display weighs {G.DISPLAY.weight_lbf:.1f} lbf and the whole assembly "
          f"{G.engineering_report(BracketParams(), build_geometry(BracketParams(), derive_flat(BracketParams())))['total_hanging_lbf']:.1f} lbf.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
