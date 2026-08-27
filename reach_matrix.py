#!/usr/bin/env python3
"""Reach x thickness matrix: how much arm reach can be bought, at what price, while keeping the
screen at a comfortable height.

Reach and neck are INDEPENDENT levers that both add to the flat length:

    flat_length = body + (neck - BD/2) + (reach - BD/2)

Neck sets how high the screen hangs. Reach sets how much foot the bracket has on the fridge top.
So for any chosen screen height, extra reach costs sheet at a roughly linear rate. This tabulates
that, with the two ceilings that actually stop you: the sponge pad's budget, and the comfort band.

Prices are SendCutSend quotes where measured (marked) and linear interpolation elsewhere.
Reference-only.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
from generate_bracket import (
    MATERIAL,
    MM_PER_INCH,
    BracketParams,
    bend_deduction_mm,
    crown_rise_at,
    flat_gap,
)
from thickness_study import evaluate

LOG = logging.getLogger("matrix")

# Measured SendCutSend quotes, qty 1, cutting only: (thickness_in, flat_length_mm) -> USD.
MEASURED = {
    (0.125, 730.9): 61.54,
    (0.187, 730.9): 131.49,
    (0.187, 780.9): 136.50,
    (0.250, 730.9): 127.79,
    (0.250, 780.9): 133.23,
}
# Rate of change of price with flat length, per thickness, from the measured pairs.
SLOPE_PER_MM = {0.187: (136.50 - 131.49) / 50.0, 0.250: (133.23 - 127.79) / 50.0}
SLOPE_DEFAULT = 0.10  # .125 has only one measured point; assume the same order of magnitude

# The band of heights comfortable for both 5'1" and 6'4" (taller elbow to shorter eye).
COMFORT_LOW, COMFORT_HIGH = 1216.0, 1450.0


@dataclass(frozen=True)
class Cell:
    thickness_in: float
    reach: float
    neck: float
    flat_len: float
    price: float
    measured: bool
    pad_margin: float
    screen_centre: float
    mass_kg: float
    screen_move_mm: float

    @property
    def pad_ok(self) -> bool:
        return self.pad_margin >= 1.2

    @property
    def height_ok(self) -> bool:
        return COMFORT_LOW <= self.screen_centre <= COMFORT_HIGH


def price_for(thickness_in: float, flat_len: float) -> tuple[float, bool]:
    key = (thickness_in, round(flat_len, 1))
    if key in MEASURED:
        return MEASURED[key], True
    anchors = [(l, p) for (t, l), p in MEASURED.items() if t == thickness_in]
    if not anchors:
        return float("nan"), False
    base_len, base_price = min(anchors)
    slope = SLOPE_PER_MM.get(thickness_in, SLOPE_DEFAULT)
    return base_price + (flat_len - base_len) * slope, False


def build(params: BracketParams, thicknesses: Sequence[float], reaches: Sequence[float],
          neck: float) -> list[Cell]:
    cells = []
    for t_in in thicknesses:
        t = t_in * MM_PER_INCH
        # Bend deduction scales with thickness, so the flat length is not simply body+neck+reach.
        bd = bend_deduction_mm(MATERIAL.bend_radius, t, MATERIAL.k_factor, 90.0)
        for reach in reaches:
            flat_len = params.body_h + (neck - bd / 2.0) + (reach - bd / 2.0)
            price, measured = price_for(t_in, flat_len)
            crown = crown_rise_at(reach, params.fridge_top_width, params.crown_rise)
            budget = flat_gap(params.fridge_corner_radius_max, MATERIAL.bend_radius) + crown
            res = evaluate(t_in, params)
            # Mass must track the actual reach: a longer arm is more metal. evaluate() only knows
            # the default geometry, so recompute the area here rather than reuse its figure.
            area = (params.body_w * params.body_h
                    + params.neck_w * (neck + reach)
                    - math.pi * (params.center_open_dia / 2.0) ** 2
                    - 4.0 * params.window_long * params.window_short)
            mass = area * t * MATERIAL.density_g_cc / 1e6
            cells.append(Cell(t_in, reach, neck, flat_len, price, measured,
                              params.arm_pad / budget,
                              params.fridge_height - neck - params.body_h / 2.0,
                              mass, res.screen_edge_movement_mm))
    return cells


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Reach x thickness matrix at a fixed screen height.")
    p.add_argument("--thicknesses", type=float, nargs="+", default=[0.125, 0.187, 0.250])
    p.add_argument("--reaches", type=float, nargs="+", default=[130, 180, 230, 280, 326])
    p.add_argument("--neck", type=float, default=310.0)
    p.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = p.parse_args(argv)
    configure_logging(args.log_level)
    logging.getLogger("generate").setLevel(logging.WARNING)

    params = BracketParams()
    cells = build(params, args.thicknesses, args.reaches, args.neck)
    centre = params.fridge_height - args.neck - params.body_h / 2.0

    print()
    print(f"Neck fixed at {args.neck:.0f} mm  ->  screen centre {centre:.0f} mm above the floor"
          f"  ({'INSIDE' if COMFORT_LOW <= centre <= COMFORT_HIGH else 'OUTSIDE'} the "
          f"{COMFORT_LOW:.0f}-{COMFORT_HIGH:.0f} mm comfort band)")
    print(f"Sponge pad {params.arm_pad:.2f} mm; a reach is viable while pad margin >= 1.20x")
    print()
    hdr = (f"{'thick':>7}{'reach':>7}{'flat mm':>10}{'price':>11}{'pad':>7}{'mass':>7}"
           f"{'screen move':>13}   verdict")
    print(hdr); print("-" * (len(hdr) + 12))
    for c in cells:
        star = "*" if c.measured else " "
        verdict = "ok" if c.pad_ok else "PAD TOO THIN"
        if c.pad_ok and c.screen_move_mm > 0.2:
            verdict = "ok, but flexy"
        print(f"{c.thickness_in:>7.3f}{c.reach:>7.0f}{c.flat_len:>10.1f}"
              f"{('$' + format(c.price, '.2f') + star):>11}{c.pad_margin:>6.2f}x"
              f"{c.mass_kg:>7.2f}{c.screen_move_mm:>11.2f} mm   {verdict}")
    print()
    print("*  = actual SendCutSend quote. Unmarked prices are linear interpolation from the")
    print("   measured pairs and get less trustworthy the further they extrapolate.")
    print()
    best = [c for c in cells if c.pad_ok and c.screen_move_mm <= 0.2]
    if best:
        top = max(best, key=lambda c: c.reach)
        print(f"Most reach that still feels rigid and has pad margin: {top.reach:.0f} mm at "
              f"{top.thickness_in:.3f}\" — flat {top.flat_len:.1f} mm, about ${top.price:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
