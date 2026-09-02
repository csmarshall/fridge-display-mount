#!/usr/bin/env python3
"""ONE home for every price in the project, and the three quotes built from it.

Every figure here is a DATED OBSERVATION — a SendCutSend configurator quote or a vendor listing on
a given day — never a derived value. The three designs are costed from the same table so that a
line shared between them (a magnet, a bolt pack, a foam roll) can only ever have one price.

    design 1  THE HOOK          plate at 0.187 in HRPO + 8 magnets + the hook hardware
    design 2  CLAMPED STRUT     five cut parts + struts + bolts; no magnets
    design 3  HOOK + STRUT KIT  design 1 REBASED to 0.119 in and 4 magnets (phase 1),
                                plus design 2's feet and lower clamp and 5 ft struts (the kit)

Design 3's phase 1 IS design 1 at the other gauge and magnet count, and the sheet says so in one
line. Design 2's plate is a different part (small, no arm), so it shares nothing with 1 or 3
except the strut hardware.

The display and its PSU are the same purchase whichever design wins and are listed once, outside
the three quotes. Unpriced lines are carried as NOT PRICED and counted, never guessed.

Run it for the table; `quotes.svg` is the sheet; console_build.py reads quote() for the page.
"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

LOG = logging.getLogger("prices")


@dataclass(frozen=True)
class Price:
    """One observation. `unit` is per `pack` — a pack price is never multiplied by a piece count."""
    key: str
    item: str
    unit: float | None          # None = not priced; the quote says so and counts it
    pack: str                   # "each", "pack of 25", "10 ft roll", ...
    source: str
    date: str
    note: str = ""


# --------------------------------------------------------------------------------- the table
P: dict[str, Price] = {p.key: p for p in (
    # SendCutSend, A36/1008 mild steel, configurator quotes qty 1 unless the note says otherwise
    Price("plate_187", "Hook plate, 0.187 in HRPO, 1 bend, textured black", 197.07, "each",
          "SendCutSend", "2026-08-27", "bracket_flat.dxf as built; cut $112.50, +bend $126.71"),
    Price("plate_119", "Hook plate, 0.119 in CRS, 1 bend, matte black, WITH strut holes", 177.77, "each",
          "SendCutSend", "2026-09-01",
          "RE-QUOTE: taken on a six-hole redrawing; the real file has the hook's full hole set. "
          "Same bounding box, more cut length. $123.52 ea at qty 2"),
    Price("clamp_bar", "Clamp bar (part A), 0.119 in, 1 bend, matte black", 59.74, "each",
          "SendCutSend", "2026-08-31", "qty-2 rate; $77.95 at qty 1"),
    Price("clamp_bar_q1", "Lower clamp (part A) alone, qty 1", 77.95, "each",
          "SendCutSend", "2026-08-31", "design 3 needs ONE — the hook does the top"),
    Price("foot", "Foot (part B), 0.119 in, 1 bend, matte black", 29.69, "each",
          "SendCutSend", "2026-08-31", "qty-2 rate"),
    Price("plate_c", "Strut plate (part C), 0.119 in, flat, matte black", 94.05, "each",
          "SendCutSend", "2026-08-31", ""),
    Price("strip", "Backing strip (part D), 20 mm wide, BARE CRS", 8.11, "each",
          "SendCutSend", "2026-08-31", "qty-2 rate; too narrow for powder coat — fit-or-not undecided"),
    # McMaster-Carr
    Price("magnet", "Pot magnet 3506K67, O48 x 11.51, 5/16-18 male stud, 175 lb", 23.92, "each",
          "McMaster 3506K67", "2026-08-27", "$20.62 ea at 10+"),
    Price("jam_nut", "Jam nut 5/16-18, black-oxide 18-8, half height", 3.20, "pack of 25",
          "McMaster 98514A035", "2026-08-27", ""),
    Price("washer_os", "Oversized washer O1.250 OD, black-oxide 18-8", 8.37, "pack of 10",
          "McMaster 90377A164", "2026-08-27", "two packs for eight magnets plus spares"),
    Price("threadlocker", "Loctite 243, 0.34 fl oz", 18.42, "bottle",
          "McMaster 91458A115", "2026-08-27", "the jam nut has no locking feature of its own"),
    Price("primer", "Adhesive primer for the threadlocker (black oxide + stainless)", None, "bottle",
          "McMaster", "", "NOT SOURCED"),
    Price("vesa_screws", "M4 x 0.7 low-head socket cap, 18-8", None, "pack of 25",
          "McMaster 91239A180", "", "part number not verified; length after the spacer is chosen"),
    Price("spacers", "M4 unthreaded aluminium spacers, ~10 mm", None, "4",
          "McMaster", "", "length depends on the measured nut-stack height"),
    Price("foam_hook", "Neoprene foam strip 7/16 in x 2 in, adhesive-backed", 141.83, "10 ft roll",
          "McMaster 93375K678", "2026-08-27", "arm pad, neck strips and bottom pad from one roll"),
    Price("velcro", "VELCRO ONE-WRAP 1/2 in, black", 31.25, "25 yd roll",
          "hookandloop.com 189755", "2026-08-27", "for the strap slots"),
    Price("strut_4ft", "Strut channel 3310T791, low-profile slotted, 4 ft", 25.48, "each",
          "McMaster 3310T791", "2026-08-31", "black powder-coated"),
    Price("strut_1ft", "Strut channel 3310T791, 1 ft", 6.37, "each",
          "McMaster 3310T791", "2026-08-31", "design 2's upper piece"),
    Price("strut_5ft", "Strut channel 3310T791, 5 ft", 30.26, "each",
          "McMaster 3310T791", "2026-08-31", "design 3's length: six slot rows inside the plate"),
    Price("elevator", "Elevator bolt 5/16-18 x 3/4, square neck, zinc, WITH nuts", 9.63, "pack of 25",
          "McMaster 92670A781", "2026-08-31", "one pack covers every strut joint"),
    Price("washer_5_16", "Flat washer 5/16", None, "pack",
          "McMaster", "", "two per top clamp bolt (design 2 only)"),
    Price("m4_button", "M4 button head screws", None, "pack", "McMaster", "", "design 2's VESA screws"),
    Price("foam_3mm", "Closed-cell foam sheet, 3 mm", None, "sheet", "", "", "clamp faces"),
    Price("floor_pad", "Non-marking EPDM floor pad, 3 mm", None, "sheet", "", "",
          "under the feet — EPDM, rubber stains polyurethane"),
    Price("plate_pad", "Small pads, plate corners to fridge", None, "4", "", "", ""),
    # BUDGET ALTERNATIVES — sourced 2026-09-02 from search snippets and vendor pages (retail sites
    # block direct fetches, so each is a single observation, not a cross-check). Same job, cheaper
    # source or sensible quantity. Where the cheap part does NOT meet a design rule, the note says so.
    Price("b_nyloc", "Nyloc nut 5/16-18, 18-8 stainless — replaces jam nut + threadlocker + primer",
          12.80, "pack of 50", "BCP Fasteners BCP587", "2026-09-02",
          "one nut per magnet stud; 8.2 mm tall vs the jam nut's 4.76 — CHECK the stud reaches "
          "(fastener_matrix: thin nyloc + washer was marginal). Amazon 10-packs exist, unpriced"),
    Price("b_fender", "Fender washer 5/16 x 1-1/4 OD, stainless", 1.47, "pack of 2",
          "Home Depot Everbilt 825241", "2026-09-02", "same OD as the McMaster oversized washer"),
    Price("b_foam", "Neoprene closed-cell sheet 1/2 in, 80 x 24 in, NO adhesive", 37.99, "half sheet",
          "The Foam Factory", "2026-09-02",
          "12.7 mm = 1.19 mm PROUD of the 11.51 magnets, outside the -0.60/+0.30 pad rule. Use only "
          "if laminated to 7/16 or the rule is consciously waived; needs contact adhesive (~$8)"),
    Price("b_velcro", "VELCRO ONE-WRAP thin ties 8 x 1/2 in", 5.97, "pack of 50",
          "Walmart", "2026-09-02", "$7.29 at Office Depot; pre-cut 8 in ties suit the 4 x 18 slots"),
    Price("b_strut10", "Superstrut ZB14HS10EG half-slot channel 1-5/8 x 13/16, 14 ga, 10 ft", 33.00, "each",
          "Home Depot", "2026-09-02",
          "SAME slot pattern as McMaster 3310T791 (1-1/8 in slots on 2 in centres); cut in half for "
          "two 5 ft; electro-galvanized, not black. Measure the first slot from the cut end"),
    Price("b_epdm", "EPDM sheet 1/8 in x 12 x 24, adhesive-backed, 60A", 11.26, "sheet",
          "Home Depot / Lowe's Rubber-Cal 31-P16-125-012-024", "2026-09-02", "floor pads AND clamp faces"),
    Price("b_magnet36", "OPTION: K&J MM-C-36 pot magnet, O36 x 8 mm, M6 male stud, 90.4 lb", 9.72, "each",
          "K&J Magnetics", "2026-09-02",
          "NOT in the budget column: 8 mm standoff needs an 8 mm pad no imperial foam gives, and the "
          "plate's O8.5 holes want a 6.5 for an M6 stud. SF still ~19x. A design change, not a swap"),
    # DESIGN 4 - stock aluminium (angle_concept.py). ESTIMATE where the vendor page would not
    # give a price for the exact size; sourced where it did.
    Price("al_angle", "6061-T6 angle 2 x 2 x 1/4 in, 12 in", 18.86, "each", "Speedy Metals", "2026-09-02",
          "price shown is their 2 x 2-1/2 x 1/4; 2 x 2 is the same order of cost"),
    Price("al_bar", "6061-T6 flat bar 2 x 1/4 in, 24 in", 12.50, "each", "ESTIMATE", "2026-09-02",
          "metals4u lists $8.33 for 12 in and a $8.33-49.42 range; 24 in taken as ~$12.50"),
    Price("al_plate", "6061 plate 1/4 in, 8 x 8 in", 30.00, "each", "ESTIMATE", "2026-09-02",
          "Online Metals cut-to-size; page blocked the price fetch"),
    Price("mmc36", "K&J MM-C-36 pot magnet, O36 x 8 mm, M6 male stud, 90.4 lb", 9.72, "each",
          "K&J Magnetics", "2026-09-02", ""),
    Price("m6_nyloc", "M6 nyloc nuts + 1/4-20 bolts, washers", 15.00, "lot", "ESTIMATE", "2026-09-02",
          "hardware store; 4 nylocs, 8 bolts, washers"),
    Price("foam_5_16", "Neoprene foam 5/16 in, adhesive strips", None, "roll", "McMaster", "",
          "8 mm standoff wants 7.94 mm foam; stocked, not yet priced"),
    # common to every design
    Price("display", "Waveshare 23.8 in FHD touch monitor, SKU 34025, with 12 V 5 A PSU", 349.99, "each",
          "waveshare.com", "2026-08-27", ""),
    Price("psu", "Mean Well GST90A12-P1M 12 V 80 W brick", 29.50, "each",
          "Digi-Key", "2026-08-27", "bundled brick is 60 W against a 63 W budget"),
    Price("iec_cord", "IEC C13 cord, 6 ft", 7.52, "each", "Digi-Key 212099-01", "2026-08-27", ""),
)}


@dataclass(frozen=True)
class Line:
    key: str
    qty: float
    label: str = ""                 # overrides the table's item text when the quote needs to

    @property
    def price(self) -> Price:
        return P[self.key]

    @property
    def item(self) -> str:
        return self.label or self.price.item

    @property
    def total(self) -> float | None:
        return None if self.price.unit is None else self.price.unit * self.qty


@dataclass
class Group:
    title: str
    lines: list[Line] = field(default_factory=list)

    @property
    def priced(self) -> float:
        return sum(ln.total for ln in self.lines if ln.total is not None)

    @property
    def unpriced(self) -> int:
        return sum(1 for ln in self.lines if ln.total is None)


@dataclass
class Quote:
    design: int
    name: str
    tagline: str
    groups: list[Group]

    @property
    def priced(self) -> float:
        return sum(g.priced for g in self.groups)

    @property
    def unpriced(self) -> int:
        return sum(g.unpriced for g in self.groups)


# The hardware a hook plate needs whichever gauge it is cut at. ONE list, used by 1 and 3.
def hook_hardware(n_magnets: int) -> Group:
    return Group("Hook hardware", [
        Line("jam_nut", 1), Line("washer_os", 2 if n_magnets > 5 else 1),
        Line("threadlocker", 1), Line("primer", 1), Line("vesa_screws", 1), Line("spacers", 1),
        Line("foam_hook", 1), Line("velcro", 1),
    ])


def quote_hook() -> Quote:
    return Quote(1, "THE HOOK", "one bent plate over the fridge top, held flat by magnets", [
        Group("Cut steel", [Line("plate_187", 1)]),
        Group("Magnets", [Line("magnet", 8, "Pot magnet 3506K67 — 4 body + 4 arm, as the BOM fits them")]),
        hook_hardware(8),
    ])


def quote_clamp(with_strips: bool = False) -> Quote:
    cut = [Line("clamp_bar", 2), Line("foot", 2), Line("plate_c", 1)]
    if with_strips:
        cut.append(Line("strip", 2))
    return Quote(2, "CLAMPED STRUT", "two struts to the floor, clamped top and bottom; no magnets", [
        Group("Cut steel", cut),
        Group("Struts and bolts", [Line("strut_4ft", 2), Line("strut_1ft", 2), Line("elevator", 1)]),
        Group("Hardware", [Line("washer_5_16", 1), Line("m4_button", 1), Line("foam_3mm", 1),
                           Line("floor_pad", 1), Line("plate_pad", 1)]),
    ])


def quote_hybrid(n_magnets: int = 4, strut_ft: int = 5) -> Quote:
    strut_key = {4: "strut_4ft", 5: "strut_5ft"}[strut_ft]
    return Quote(3, "HOOK + STRUT KIT", "design 1 rebased to 0.119 in and 4 magnets; the kit only if needed", [
        Group("Phase 1 — cut steel (this is design 1's plate, thinner, four more holes)",
              [Line("plate_119", 1)]),
        Group("Phase 1 — magnets", [Line("magnet", n_magnets,
                                          f"Pot magnet 3506K67 — the {n_magnets} BODY magnets; arm holes cut, not bought")]),
        hook_hardware(n_magnets),
        Group("Phase 2 — the strut kit, ONLY if the arm is too lively", [
            Line("foot", 2), Line("clamp_bar_q1", 1), Line(strut_key, 2), Line("elevator", 1),
            Line("foam_3mm", 1), Line("floor_pad", 1),
        ]),
    ])


# What the budget column swaps. key -> (alt key, qty) or None to drop the line (its job is done
# by another alt — the nyloc covers the threadlocker and its primer). Anything not listed is bought
# exactly as in the main column: the plate keeps its powder coat (Charles, 2026-09-02) and the O48
# magnets have no cheaper source ($25.68 at AMF, $23.92 McMaster).
BUDGET: dict[str, tuple[str, float] | None] = {
    "jam_nut": ("b_nyloc", 1), "threadlocker": None, "primer": None,
    "washer_os": ("b_fender", 2), "foam_hook": ("b_foam", 1), "velcro": ("b_velcro", 1),
    "strut_5ft": ("b_strut10", 1), "strut_4ft": ("b_strut10", 1), "strut_1ft": None,
    "floor_pad": ("b_epdm", 1), "foam_3mm": None, "plate_pad": None,
}


def budget(q: Quote) -> Quote:
    """The same quote with the sourced alternatives swapped in. Nothing unlisted changes."""
    groups = []
    for g in q.groups:
        lines = []
        for ln in g.lines:
            if ln.key not in BUDGET:
                lines.append(ln)
                continue
            alt = BUDGET[ln.key]
            if alt is None:
                continue
            key, qty = alt
            if key == "b_epdm" and any(x.key == "b_epdm" for x in lines):
                continue            # one sheet does both jobs
            lines.append(Line(key, qty))
        groups.append(Group(g.title, lines))
    return Quote(q.design, q.name, q.tagline + " — BUDGET-SOURCED", groups)


def quote_angle() -> Quote:
    return Quote(4, "STOCK ALUMINIUM (CONCEPT)", "the hook in hardware-store 6061, hand-drilled; not validated", [
        Group("Stock aluminium", [Line("al_angle", 1), Line("al_bar", 2), Line("al_plate", 1)]),
        Group("Magnets", [Line("mmc36", 4, "K&J MM-C-36 - sized for the duty, on the bars")]),
        Group("Hardware", [Line("m6_nyloc", 1), Line("foam_5_16", 1), Line("b_velcro", 1),
                           Line("vesa_screws", 1), Line("spacers", 1)]),
    ])


def common() -> Group:
    return Group("Common to every design — the display itself",
                 [Line("display", 1), Line("psu", 1), Line("iec_cord", 1)])


def all_quotes() -> list[Quote]:
    return [quote_hook(), quote_clamp(), quote_hybrid(), quote_angle()]


def phase(q: Quote, which: int) -> float:
    """Design 3 split: phase 1 = everything not in the kit group; phase 2 = the kit."""
    return sum(g.priced for g in q.groups if (g.title.startswith("Phase 2")) == (which == 2))


# --------------------------------------------------------------------------------- the sheet
def render(path: Path, quotes: list[Quote]) -> None:
    import html as _h
    PAPER, INK, MUTED, RULE = "#f7f8fa", "#111", "#5b6166", "#d0d4d8"
    COL = {1: "#1b6ea8", 2: "#c8791a", 3: "#0b7a4b", 4: "#6b3fa0"}
    PW = 440
    W = 40 + len(quotes) * (PW + 24)
    rows_max = max(sum(len(g.lines) + 2 for g in q.groups) for q in quotes)
    H = 250 + rows_max * 22 + 330

    def t(x, y, s, size=10.5, anchor="start", fill=INK, weight="normal"):
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica, Arial, sans-serif" '
                f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">'
                f'{_h.escape(s)}</text>')

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<rect width="{W}" height="26" fill="#8a1c1c"/>',
         t(W / 2, 18, "REFERENCE ONLY — dated vendor observations, not derived values. Nothing is in a "
                      "cart. Display and PSU excluded (same purchase whichever design wins).", 11.5,
           "middle", "#fff", "bold"),
         t(40, 62, "WHAT EACH DESIGN COSTS — three quotes from one price table", 21, weight="bold"),
         t(40, 84, "Design 3's phase 1 is design 1 at 0.119 in with 4 magnets instead of 8; its kit is "
                   "design 2's feet and lower clamp plus 5 ft struts. Design 2's plate is a different "
                   "part and shares nothing but the strut hardware.", 11.5, fill=MUTED)]
    for k, q in enumerate(quotes):
        px, py = 40 + k * (PW + 24), 110
        o.append(f'<rect x="{px}" y="{py}" width="{PW}" height="{H - py - 60}" rx="7" fill="#fff" stroke="{RULE}"/>')
        o.append(f'<rect x="{px}" y="{py}" width="{PW}" height="34" rx="7" fill="{COL[q.design]}"/>')
        o.append(t(px + 14, py + 23, f"DESIGN {q.design} — {q.name}", 13, fill="#fff", weight="bold"))
        o.append(t(px + 14, py + 54, q.tagline, 9.8, fill=MUTED))
        y = py + 80
        for g in q.groups:
            o.append(t(px + 14, y, g.title.upper(), 9.2, fill=COL[q.design], weight="bold"))
            y += 16
            for ln in g.lines:
                p = ln.price
                qty = f"{ln.qty:g} x " if ln.qty != 1 or p.pack != "each" else ""
                o.append(t(px + 22, y, f"{qty}{ln.item}"[:62], 9.0))
                o.append(t(px + PW - 14, y, "NOT PRICED" if ln.total is None else f"${ln.total:.2f}",
                           9.6, "end", MUTED if ln.total is None else INK, "bold"))
                y += 13
                o.append(t(px + 22, y, f"{p.source} {p.date}  {p.note}"[:72], 7.4, fill=MUTED))
                y += 12
            o.append(f'<line x1="{px + 14}" y1="{y - 4}" x2="{px + PW - 14}" y2="{y - 4}" stroke="{RULE}"/>')
            o.append(t(px + PW - 14, y + 9, f"group ${g.priced:.2f}"
                       + (f" + {g.unpriced} not priced" if g.unpriced else ""), 9.2, "end", MUTED))
            y += 26
        # what the budget column changes, then both totals
        b = budget(q)
        swapped = [(ln.item.split(" — ")[0], ln.total) for g in b.groups for ln in g.lines if ln.key.startswith("b_")]
        yb = H - 150 - 30 - 16 * (len(swapped) + 1)
        o.append(t(px + 14, yb, "BUDGET-SOURCED — what changes", 9.2, fill=COL[q.design], weight="bold"))
        for i, (nm, tot) in enumerate(swapped):
            o.append(t(px + 22, yb + 16 * (i + 1), nm[:56], 8.8))
            o.append(t(px + PW - 14, yb + 16 * (i + 1), f"${tot:.2f}", 9.2, "end", weight="bold"))
        yb = H - 150
        o.append(f'<rect x="{px + 10}" y="{yb}" width="{PW - 20}" height="80" rx="5" fill="{COL[q.design]}" fill-opacity="0.08"/>')
        if q.design == 3:
            o.append(t(px + 22, yb + 22, "PHASE 1 — first order", 10.5, weight="bold"))
            o.append(t(px + PW - 22, yb + 22, f"${phase(q, 1):.2f}", 13, "end", weight="bold"))
            o.append(t(px + 22, yb + 44, "PHASE 2 — the kit, only if needed", 10.5, weight="bold"))
            o.append(t(px + PW - 22, yb + 44, f"${phase(q, 2):.2f}", 13, "end", weight="bold"))
            o.append(t(px + 22, yb + 66, f"budget-sourced: phase 1 ${phase(b, 1):.2f}, kit ${phase(b, 2):.2f}", 10,
                       fill=COL[q.design], weight="bold"))
            o.append(t(px + PW - 22, yb + 66, f"${b.priced:.2f}", 11, "end", fill=COL[q.design], weight="bold"))
        else:
            o.append(t(px + 22, yb + 26, "PRICED TOTAL, as listed", 10.5, weight="bold"))
            o.append(t(px + PW - 22, yb + 26, f"${q.priced:.2f}", 15, "end", weight="bold"))
            o.append(t(px + 22, yb + 48, "budget-sourced", 10.5, weight="bold", fill=COL[q.design]))
            o.append(t(px + PW - 22, yb + 48, f"${b.priced:.2f}", 15, "end", weight="bold", fill=COL[q.design]))
            o.append(t(px + 22, yb + 68, f"plus {q.unpriced} / {b.unpriced} lines not priced", 9.5, fill=MUTED))
    c = common()
    o.append(t(40, H - 40, f"Common to every design: {'; '.join(f'{ln.item} ${ln.total:.2f}' for ln in c.lines)} "
                          f"= ${c.priced:.2f}.", 9.8, fill=MUTED))
    o.append(t(40, H - 24, "Design 1 vs design 3 phase 1: the same plate and hardware; the difference is the gauge "
                          "($197.07 vs $177.77) and four fewer magnets ($95.68).", 9.8, fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("quotes.svg"))
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(message)s")
    qs = all_quotes()
    for q in qs:
        print(f"\nDESIGN {q.design} — {q.name}   priced ${q.priced:.2f}, {q.unpriced} not priced")
        for g in q.groups:
            print(f"  {g.title}")
            for ln in g.lines:
                print(f"    {ln.qty:>4g}  {ln.item[:62]:62} "
                      f"{'NOT PRICED' if ln.total is None else '$' + format(ln.total, '.2f'):>11}")
        b = budget(q)
        if q.design == 3:
            print(f"  phase 1 ${phase(q, 1):.2f}   phase 2 ${phase(q, 2):.2f}   "
                  f"budget: phase 1 ${phase(b, 1):.2f}, kit ${phase(b, 2):.2f}")
        print(f"  BUDGET-SOURCED ${b.priced:.2f} ({b.unpriced} not priced): "
              + "; ".join(f"{ln.item.split(' — ')[0][:40]} ${ln.total:.2f}" for g in b.groups for ln in g.lines if ln.key.startswith('b_')))
    print(f"\nCommon to all: ${common().priced:.2f}")
    render(args.out, qs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
