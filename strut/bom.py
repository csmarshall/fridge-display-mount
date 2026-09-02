#!/usr/bin/env python3
"""Every part and every fastener, derived from the same Assembly the drawings use.

Nothing here is typed twice. Quantities come from the geometry (how many struts, how many
clamped surfaces), sizes come from the derived properties, and prices are the ones actually
recorded against a source. Anything without a source says so.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from concept_sheet import IN, Assembly   # puts the repo root on sys.path

WEB = 0.07 * IN                 # strut wall
NUT_H = 6.7                     # 5/16 standard hex nut
WASHER_T = 1.52                 # 5/16 flat washer
ELEV_HEAD = 2.78                # elevator bolt head, flat
M4_HEAD = 2.2                   # M4 button head


# LIVE SendCutSend quotes, 2026-08-31, 0.119 in A36/1008 CRS + MATTE BLACK POWDER COAT.
# Matte black "includes free deburring", which is why it was specified.
# Prices are PER PIECE at the quantity we actually need.
# Cut-part quotes live in ONE place, ../prices.py (dated SendCutSend observations). The
# cut/bend/coated ladder that used to sit here is in that file's notes.
from prices import P as _PRICES  # noqa: E402
QUOTED = {
    "A": dict(qty=2, each=_PRICES["clamp_bar"].unit),
    "B": dict(qty=2, each=_PRICES["foot"].unit),
    "C": dict(qty=1, each=_PRICES["plate_c"].unit),
    "D": dict(qty=2, each=_PRICES["strip"].unit),   # quoted, but powder coating is DISABLED at this width
}


@dataclass(frozen=True)
class Fab:
    """A part we have cut. Everything is 0.119 in mild steel unless it says otherwise."""
    tag: str
    name: str
    qty: int
    flat_w: float
    flat_h: float
    bends: int
    features: str
    note: str = ""

    @property
    def area_cm2(self) -> float:
        return self.flat_w * self.flat_h / 100.0

    @property
    def perim_mm(self) -> float:
        return 2.0 * (self.flat_w + self.flat_h)

    @property
    def each(self) -> float | None:
        return QUOTED.get(self.tag, {}).get("each")

    @property
    def line_total(self) -> float | None:
        return None if self.each is None else self.each * self.qty


@dataclass(frozen=True)
class Buy:
    tag: str
    name: str
    qty: int
    spec: str
    source: str
    part_no: str = ""
    unit: float | None = None      # None = not priced yet, and the BOM says so

    @property
    def total(self) -> float | None:
        return None if self.unit is None else self.unit * self.qty


def bend_deduction(a: Assembly) -> float:
    """SendCutSend's PUBLISHED deduction for this gauge. One home: Assembly.bend_deduction."""
    return a.bend_deduction


def fabricated(a: Assembly, with_strips: bool = True) -> list[Fab]:
    bd = bend_deduction(a)
    out = [
        Fab("A", "CLAMP BAR", a.n_clamps, a.clamp_leg + a.clamp_short - bd, a.clamp_width, 1,
            f"2 square holes 8.38 at {a.strut_spacing:.2f} centres",
            "spans both struts; the lower one is the same part flipped"),
        Fab("B", "FOOT", a.n_feet, a.foot_leg + a.foot_rise - bd, a.foot_width, 1,
            f"1 slot {a.slot_len:.1f} long", "strut stands on it; slot is the height adjustment"),
        Fab("C", "PLATE", a.n_plates, a.plate_w, a.plate_h, 0,
            f"4 x M4 VESA at 100, 4 x O{a.plate_bolt_dia:.1f} at "
            f"{a.plate_bolt_dx:.0f} x {a.plate_bolt_dy:.2f}, 2 vents {a.vent_len:.0f}x{a.vent_wid:.0f}",
            "flat; splices the two strut pieces"),
    ]
    if with_strips:
        out.append(Fab("D", "BACKING STRIP", 2, 20.0, a.plate_bolt_dy + 2 * a.plate_edge, 0,
                       f"4 x O{a.plate_bolt_dia:.1f} matching the plate",
                       "inside the channel; makes each plate bolt a sandwich"))
    return out


def hardware(a: Assembly, with_strips: bool = True) -> list[Buy]:
    # Each bar picks up both struts. The base bolts also carry the feet -- same bolts,
    # not extra ones, so the feet add NO fasteners of their own.
    n_clamp_bolts = a.n_clamps * a.n_struts
    n_foot_bolts = 0                                 # the feet ride the lower clamp bolts
    n_plate_bolts = 4
    # Clamp leg AND foot leg share one bolt at the base; at the top two washers replace
    # the foot leg so the strut sits parallel. Both work out the same, which is the point.
    grip_clamp = 2.0 * a.bracket_t + WEB
    grip_plate = a.plate_t + WEB + (a.bracket_t if with_strips else 0.0)
    def bolt_len(grip):
        need = grip + NUT_H + 3.0
        for L in (12.7, 15.88, 19.05, 22.23, 25.4):
            if L >= need:
                return L
        return 25.4
    return [
        Buy("S1", "Strut channel, 4 ft", a.n_struts, "low-profile 13/16 x 1 5/8, slotted",
            "McMaster", "3310T791", 25.48),
        Buy("S2", "Strut channel, 1 ft", a.n_struts, "same section", "McMaster", "3310T791",
            6.37),
        # PRICED LIVE 2026-08-31. McMaster's shortest 5/16-18 elevator bolt is 3/4 in, so the
        # 5/8 my grip calc allowed does not exist — ONE length covers every joint, which is
        # simpler than the two the drawings assumed.
        # NOTE the unit is a PACK, not a piece. Multiplying a pack price by the piece count is
        # how a $9.63 line became $96.30 the first time this was totalled.
        Buy("F1", "Elevator bolt 5/16-18 x 3/4, SQUARE neck", 1,
            f"PACK OF 25, zinc plated, flat {ELEV_HEAD} head, INCLUDES NUT — "
            f"{n_clamp_bolts + n_foot_bolts + n_plate_bolts} needed, so one pack",
            "McMaster", "92670A781", 9.63),
        Buy("F1b", "ALTERNATIVE: black oxide, RIBBED neck", 0,
            "90432A170 1-1/2 in $7.11/10. BLACK, but ribbed necks are meant to bite soft metal "
            "and plastic — no square neck exists in black oxide at this size",
            "McMaster", "90432A150", None),
        Buy("F5", "Flat washer 5/16", 2 * a.n_struts + n_plate_bolts,
            f"{WASHER_T} thick. TWO per TOP clamp bolt only, standing in for the "
            f"foot leg that is not there — the base bolts do not get them",
            "McMaster", "", None),
        Buy("F6", "M4 screw", 4, "button head, into the VESA inserts", "McMaster", "", None),
        Buy("P1", "Closed-cell foam, 3 mm", 1,
            f"clamp faces, {a.clamp_leg:.0f} x {a.clamp_width:.0f} x {a.n_clamps}",
            "sheet", "", None),
        Buy("P2", "Non-marking floor pad", a.n_feet,
            f"under the feet, {a.floor_pad:.0f} thick — EPDM, not rubber "
            f"(rubber can stain polyurethane)", "sheet", "", None),
        Buy("P3", "Pad, plate to fridge", a.n_pads,
            f"O{a.pad_dia:.0f} x {a.pad_t:.2f}, at the plate corners", "sheet", "", None),
    ]


def summary(a: Assembly, with_strips: bool = True) -> dict:
    fab = fabricated(a, with_strips)
    hw = hardware(a, with_strips)
    priced = [b for b in hw if b.total is not None]
    return dict(
        fab_parts=sum(f.qty for f in fab),
        fab_kinds=len(fab),
        area_cm2=sum(f.area_cm2 * f.qty for f in fab),
        cut_mm=sum(f.perim_mm * f.qty for f in fab),
        bends=sum(f.bends * f.qty for f in fab),
        hw_lines=len(hw),
        hw_pieces=sum(b.qty for b in hw),
        priced_total=sum(b.total for b in priced),
        unpriced=len([b for b in hw if b.total is None]),
    )


def main(argv: Sequence[str] | None = None) -> int:
    a = Assembly()
    for strips in (False, True):
        s = summary(a, strips)
        tag = "WITH strips" if strips else "without strips"
        print(f"\n=== {tag} ===")
        for f in fabricated(a, strips):
            print(f"  {f.tag} {f.name:15s} x{f.qty}  {f.flat_w:7.2f} x {f.flat_h:7.2f}  "
                  f"{f.bends} bend  {f.area_cm2:6.0f} cm2")
        print(f"  -> {s['fab_parts']} parts, {s['area_cm2']:.0f} cm2, {s['cut_mm']:.0f} mm cut, "
              f"{s['bends']} bends")
        print(f"  -> hardware {s['hw_pieces']} pieces on {s['hw_lines']} lines, "
              f"${s['priced_total']:.2f} priced, {s['unpriced']} lines not yet priced")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
