#!/usr/bin/env python3
"""THIRD DESIGN: the hook plate, with feet under it.

The hook already carried its load through the ARM bearing on the fridge top; its magnets only
ever held it flat. This adds struts and feet so the load can go to the FLOOR instead — and the
point is that either path works on its own:

    arm only      the hook as archived, magnets optional
    feet only     the fridge top carries nothing
    both          what it will actually be built as

So the magnets stop being a decision that has to be right, which was the objection that started
the whole clamped-strut detour. Nothing here reuses the clamp's Assembly: this is the hook's
geometry, and the strut length that fits it is a coincidence worth writing down.
"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import bom as B
from concept_sheet import IN, Assembly

LOG = logging.getLogger("hybrid")


@dataclass(frozen=True)
class Hybrid:
    # --- from the archived hook design, unchanged ---
    fridge_h: float = 1743.07
    arm_reach: float = 180.0
    neck: float = 257.0
    body: float = 310.0
    body_w: float = 310.0
    arm_w: float = 190.0
    screen_centre: float = 1331.0
    plate_t: float = 0.119 * IN        # was .187 HRPO; the feet take load off the plate
    bend_radius: float = 3.02
    k_factor: float = 0.42

    # --- what this design adds ---
    strut_ft: float = 4.0              # THE length that fits. See strut_overlap.
    strut_w: float = 1.625 * IN
    strut_d: float = 0.8125 * IN
    slot_pitch: float = 2.0 * IN
    slot_len: float = 28.6
    # NOT the hook's 246 magnet spacing, which is where this started. At 246 the strut bolts sit
    # directly UNDER the lower magnet discs — 14.27 mm between centres against a 24.01 mm disc
    # radius — so the plate could carry magnets or struts but never both, which is the one thing
    # this design needs it to do. Derived from the clamped-strut design instead: it is the first
    # spacing that clears (32.65 mm centre-to-centre against 30.26 needed) AND it makes the foot
    # and lower clamp the SAME PARTS as that design, so the fallback kit needs no new tooling.
    strut_spacing: float = Assembly().strut_spacing
    magnets: bool = False              # OPTIONAL now, which is the whole point
    part_width: float = 55.0           # same edge-margin rule as the clamp design
    magnet_inset: float = 32.0         # hook design, unchanged
    magnet_disc: float = 48.02         # O48 pot magnet

    @property
    def body_bottom(self) -> float:
        """Where the hook's plate stops. Everything about the feet follows from this."""
        return self.fridge_h - self.neck - self.body

    @property
    def strut_len(self) -> float:
        return self.strut_ft * 12.0 * IN

    @property
    def strut_overlap(self) -> float:
        """How far the strut reaches past the plate's bottom edge.

        This is LUCK, not design. Nothing made the hook's plate stop 43 mm below a stock strut
        length. If the screen height ever moves, the neck moves, the plate bottom moves, and this
        has to be rechecked — 3 ft falls 262 short and 5 ft overshoots by 348.
        """
        return self.strut_len - self.body_bottom

    @property
    def bolt_row(self) -> float:
        """The one strut slot that lands inside the overlap. There is only one."""
        n, best = 0, None
        while True:
            z = 25.4 + n * self.slot_pitch
            if z > self.strut_len - 11.11:
                return best
            if z > self.body_bottom:
                best = z if best is None else best
            n += 1

    @property
    def bolt_edge_margin(self) -> float:
        return self.bolt_row - self.body_bottom

    @property
    def couple_arm(self) -> float:
        """Arm at the top, bolts at the bottom. That separation is what stops it tipping."""
        return self.fridge_h - self.bolt_row

    @property
    def magnet_to_bolt(self) -> float:
        """Clearance from a lower magnet centre to the nearest strut bolt centre.

        The check that forced strut_spacing off 246. Must stay above magnet radius + bolt head.
        """
        import math
        bd = self.bend_deduction
        body_ctr = self.arm_reach + self.neck - bd + self.body / 2.0
        mag_hi = body_ctr + (self.body / 2.0 - self.magnet_inset)
        lat = abs(246.0 / 2.0 - self.strut_spacing / 2.0)
        return math.hypot(lat, abs(self.flat_len - self.bolt_edge_margin - mag_hi))

    @property
    def magnet_to_bolt_needed(self) -> float:
        return self.magnet_disc / 2.0 + 8.5 / 2.0 + 2.0

    @property
    def bend_deduction(self) -> float:
        import math
        r, t, k = self.bend_radius, self.plate_t, self.k_factor
        return 2 * (r + t) * math.tan(math.radians(45)) - (math.pi / 2) * (r + k * t)

    @property
    def flat_len(self) -> float:
        return self.arm_reach + self.neck + self.body - self.bend_deduction


def fabricated(h: Hybrid) -> list[B.Fab]:
    a = Assembly()
    return [
        B.Fab("H", "HOOK PLATE", 1, h.flat_len, h.body_w, 1,
              f"2 x O{a.plate_bolt_dia:.1f} to the struts at {h.strut_spacing:.0f} centres "
              f"(ONE row — only one slot lands in the overlap), "
              f"VESA 100, vents",
              "the archived hook, plus strut holes near its bottom edge"),
        B.Fab("B", "FOOT", a.n_feet, a.foot_leg + a.foot_rise - B.bend_deduction(a),
              a.foot_width, 1, f"1 slot {a.slot_len:.1f} long",
              "one per strut, per BRIEF.md Part B. UNCHANGED from the clamped-strut design"),
        B.Fab("A", "LOWER CLAMP", 1, a.clamp_leg + a.clamp_short - B.bend_deduction(a),
              a.clamp_width, 1, f"2 square holes 8.38 at {a.strut_spacing:.2f} centres",
              "ONE, not two — the hook does the top. Shares its bolts with the feet"),
    ]


def costed(h: Hybrid) -> list[tuple[str, str, float | None, str]]:
    """Live prices where we have them, and NOTHING invented where we do not."""
    return [
        ("HOOK PLATE x1", "SendCutSend, quoted 2026-09-01", 177.77,
         "0.119 CRS, 1 bend, matte black. NOT the archived $197.07 figure, which was "
         "0.187 HRPO with no strut holes. Cut alone $95.39, +bend $107.16, +coat $177.77. "
         "At qty 2 it drops to $123.52 ea, which is the number to quote if a spare is wanted"),
        ("FOOT x2", "SendCutSend, quoted 2026-08-31", 2 * 29.69,
         "one per strut, unchanged part, matte black"),
        ("LOWER CLAMP x1", "SendCutSend, quoted 2026-08-31", 77.95,
         "clamp design's part at QTY 1 ($77.95, not the $59.74 qty-2 rate)"),
        ("STRUT 4 ft x2", "McMaster 3310T791", 2 * 25.48, "already black powder-coated"),
        ("Elevator bolts, pack of 25", "McMaster 92670A781", 9.63,
         "square neck, includes nuts; one pack covers everything"),
        ("MAGNETS x8", "OPTIONAL", None, "$191 if fitted. The design does not need them."),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-level", default="INFO")
    ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    h = Hybrid()
    print(f"\nHOOK + FEET — the third design\n")
    print(f"  plate bottom edge        {h.body_bottom:8.2f} mm above the floor")
    print(f"  strut {h.strut_ft:.0f} ft                {h.strut_len:8.2f}")
    print(f"  overlap                  {h.strut_overlap:+8.2f}  <- luck, not design")
    print(f"  the one slot in it       {h.bolt_row:8.2f}, {h.bolt_edge_margin:.2f} above the edge")
    print(f"  arm-to-bolt couple       {h.couple_arm:8.2f} mm\n")
    print(f"  flat plate               {h.flat_len:.2f} x {h.body_w:.0f}, 1 bend, "
          f"deduction {h.bend_deduction:.2f}\n")
    tot = 0.0
    print(f"  {'item':32} {'cost':>10}   source")
    for nm, src, cost, note in costed(h):
        if cost:
            tot += cost
        print(f"  {nm:32} {('$'+format(cost,'.2f')) if cost else 'NOT PRICED':>10}   {src}")
    print(f"\n  known so far ${tot:.2f}, plus optional magnets ($191 if fitted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
