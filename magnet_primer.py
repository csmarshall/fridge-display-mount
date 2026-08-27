#!/usr/bin/env python3
"""Why the answer to "just use strong magnets" is a hook, drawn for a non-engineer.

The single most common objection to this design, verbatim from a real reader:

    "Amazon has magnets that can handle that weight fine, and are cheap,
     why can't we just use those?"

It is a reasonable objection, and nothing else in the drawing set answers it. This sheet does,
without hand-waving: it shows the arithmetic by which an advertised magnet rating collapses to a
small fraction of itself on a real refrigerator, why peel means you never even get to fight the
total, and how the hook removes the failure mode instead of trying to overpower it.

Every load figure is read out of BracketParams / engineering_report(), so the sheet can never
disagree with the generator. The only numbers with no home in the params are the totalElement
vendor citation (33.5 lb pull vs 7 lb horizontal for their 43 mm rubber pot magnet — a
published vendor datum, not a derivable quantity); the as-built magnet is bare nickel, so its
mu = 0.2 is the only friction figure this sheet quotes.
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import (LOG_LEVELS, N_PER_LBF, configure_logging, kg_lb, lbf_n,
                            FRIDGE_SIDE, FRIDGE_SIDE_EDGE, MAGNET_EDGE, MAGNET_FILL,
                            PAD_EDGE, PAD_FILL)
import generate_bracket as G
from generate_bracket import BracketParams

LOG = logging.getLogger("primer")

INK, MUTED, RULE = "#14181c", "#6b757e", "#c9d1d8"
OK, BAD, MARG = "#0a8f6f", "#b00020", "#b8860b"
PAPER, CARD, TINT = "#fbfcfd", "#ffffff", "#f2f5f7"
C_FOAM = PAD_FILL
C_FRIDGE, C_MAGNET, C_PLATE = FRIDGE_SIDE, MAGNET_FILL, "#b9c2c9"

# Published by totalElement for their 43 mm rubber-coated pot magnet. A citation, not a derived
# value: the vendor's own catalogue is the source, recorded in CLAUDE.md section 1.1.
TOTALELEMENT_PULL_LBF = 33.5
TOTALELEMENT_HORIZONTAL_LBF = 7.0
FONT = "Helvetica,Arial,sans-serif"


def _esc(s) -> str:
    """SVG is XML: a bare < or & in a label silently breaks the whole document."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _wrap(s: str, width: int) -> list[str]:
    """Greedy word wrap so prose never runs off a card. Width is in characters, calibrated per
    call site against the actual pixel budget — Helvetica averages ~0.5 px per pt per char."""
    out, line = [], ""
    for word in s.split():
        cand = f"{line} {word}".strip()
        if len(cand) > width and line:
            out.append(line)
            line = word
        else:
            line = cand
    if line:
        out.append(line)
    return out


def _t(x: float, y: float, s, size: float = 11.0, anchor: str = "start", fill: str = INK,
       weight: str = "normal", style: str = "") -> str:
    st = f' font-style="{style}"' if style else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"{st}>{_esc(s)}</text>')


def _card(x: float, y: float, w: float, h: float, title: str, colour: str = INK) -> list[str]:
    return [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" '
            f'fill="{CARD}" stroke="{RULE}" stroke-width="1.2"/>',
            _t(x + 16, y + 26, title, 13.5, weight="bold", fill=colour)]


def _arrow(x1: float, y1: float, x2: float, y2: float, colour: str, width: float = 2.6) -> str:
    """A straight force arrow with a self-contained head — no <defs>, so no marker id clashes."""
    ang = math.atan2(y2 - y1, x2 - x1)
    L, spread = 11.0, 0.46
    hx1, hy1 = x2 - L * math.cos(ang - spread), y2 - L * math.sin(ang - spread)
    hx2, hy2 = x2 - L * math.cos(ang + spread), y2 - L * math.sin(ang + spread)
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{colour}" stroke-width="{width}"/>'
            f'<path d="M{x2:.1f} {y2:.1f} L{hx1:.1f} {hy1:.1f} L{hx2:.1f} {hy2:.1f} Z" '
            f'fill="{colour}"/>')


def _mini_panel(x: float, y: float, h: float) -> list[str]:
    """A slice of fridge side panel, seen edge-on: thin painted sheet, drawn as a vertical bar."""
    return [f'<rect x="{x:.1f}" y="{y:.1f}" width="10" height="{h:.1f}" fill="{C_FRIDGE}" '
            f'stroke="{INK}" stroke-width="1.0"/>']


def _mini_magnet(x: float, y: float) -> list[str]:
    """A pot magnet stuck to the panel at x (panel face), centred on y. 34 px long, 26 px tall."""
    return [f'<rect x="{x:.1f}" y="{y - 13:.1f}" width="34" height="26" fill="{C_MAGNET}" '
            f'stroke="{INK}" stroke-width="1.0"/>']


def render(path: Path, p: BracketParams) -> None:
    geom = G.build_geometry(p, G.derive_flat(p))
    rep = G.engineering_report(p, geom)

    rated = p.magnet_rated_pull_lbf
    derated = rep["magnet_derated_pull_lbf"]
    shear = rep["magnet_shear_lbf"]
    shear_pct = shear / rated * 100.0
    weight = rep["display_weight_lbf"]
    hanging = rep["total_hanging_lbf"]
    mult = 1.0 / (p.magnet_derate * p.mu_magnet_face)          # rated lb needed per lb held
    # Against the MAGNET-ONLY load, not the hook design's — see the panel below.
    rated_needed = rep["magnet_only_hanging_lbf"] * mult
    vendor_pct = TOTALELEMENT_HORIZONTAL_LBF / TOTALELEMENT_PULL_LBF * 100.0

    W = 1180.0
    o: list[str] = []

    # ---------------------------------------------------------------- header
    y = 48.0
    o.append(_t(40, y, "WHY NOT JUST MAGNETS?", 21, weight="bold"))
    y += 27
    o.append(_t(40, y, '"Amazon has magnets that can handle that weight fine, and are cheap — '
                       'why can\'t we just use those?"', 13.5, fill=MUTED, style="italic"))
    y += 21
    o.append(_t(40, y, "A fair question, and the answer is arithmetic, not opinion. It takes "
                       "three steps: what a rating measures, what the fridge actually does to "
                       "it, and what a lever does to whatever is left.", 12, fill=MUTED))

    # ---------------------------------------------------- section 1: three load directions
    y1 = y + 26
    ch1 = 240.0
    cw = (W - 80 - 2 * 20) / 3.0
    cases = [
        ("PULL — what the box quotes", OK,
         "Straight away from the surface. Ratings are measured THIS way, on thick ground "
         "steel at zero gap. Strongest direction by far."),
        ("SHEAR — what gravity applies", MARG,
         "Sliding DOWN the panel. The magnet only resists through friction: grip = pull x mu, "
         "and mu is tiny on smooth paint. Weakest direction."),
        ("PEEL — what a bump applies", BAD,
         "Levering one edge away. The prying force is multiplied by the lever, and it lands "
         "on ONE magnet at a time — never on the total."),
    ]
    for i, (title, col, prose) in enumerate(cases):
        cx = 40 + i * (cw + 20)
        o += _card(cx, y1, cw, ch1, title, col)
        dx, dy = cx + 44, y1 + 100        # panel bar position within the card
        o += _mini_panel(dx, y1 + 48, 108)
        o += _mini_magnet(dx + 10, dy)
        if i == 0:      # pull: arrow straight out of the panel
            o.append(_arrow(dx + 52, dy, dx + 126, dy, col))
            o.append(_t(dx + 60, dy - 12, "tension", 10, fill=col, weight="bold"))
        elif i == 1:    # shear: arrow sliding down the panel face
            o.append(_arrow(dx + 27, dy + 20, dx + 27, dy + 62, col))
            o.append(_t(dx + 40, dy + 46, "gravity", 10, fill=col, weight="bold"))
        else:           # peel: magnet rotating off about its bottom edge, pry arrow at the top
            o.append(f'<rect x="{dx + 10:.1f}" y="{dy - 13:.1f}" width="34" height="26" '
                     f'fill="{C_MAGNET}" fill-opacity="0.45" stroke="{MUTED}" '
                     f'stroke-width="1.0" stroke-dasharray="3 3" '
                     f'transform="rotate(-16 {dx + 10:.1f} {dy + 13:.1f})"/>')
            o.append(_arrow(dx + 46, dy - 22, dx + 96, dy - 52, col))
            o.append(_t(dx + 62, dy - 52, "pry", 10, fill=col, weight="bold"))
        for j, ln in enumerate(_wrap(prose, 56)):
            o.append(_t(cx + 16, y1 + 176 + j * 15, ln, 10.5, fill=MUTED))

    # ------------------------------------------------- section 2: the derate chain
    y2 = y1 + ch1 + 24
    ch2 = 396.0
    o += _card(40, y2, W - 80, ch2, "WATCH THE NUMBER ON THE BOX COLLAPSE", INK)
    o.append(_t(56, y2 + 46, f"The as-built magnet is a {p.magnet_disc_dia:.0f} mm "
                f"({p.magnet_disc_dia / G.MM_PER_INCH:.2f} in) pot magnet, and its catalogue "
                f"rating is honest — for the test it describes. The fridge is not that test.",
                11.5, fill=MUTED))
    bar_x, bar_h, bar_max = 76.0, 34.0, 620.0
    steps = [
        (rated,   INK,  f"RATED   {lbf_n(rated, 0)}",
         "measured on THICK ground steel, ZERO gap, pulling STRAIGHT OFF"),
        (derated, MARG, f"x {p.magnet_derate:.2f} on the fridge  =  {lbf_n(derated, 1)}  PULL",
         "0.6-0.9 mm painted sheet: thin steel saturates, paint holds the magnet off the metal"),
        (shear,   BAD,  f"x mu {p.mu_magnet_face:.1f} friction  =  {lbf_n(shear, 1)}  SHEAR",
         "the load is SLIDING, not pulling — bare nickel on smooth paint barely grips"),
    ]
    for i, (val, col, label, why) in enumerate(steps):
        by = y2 + 66 + i * 74
        bw = max(val / rated * bar_max, 8.0)
        o.append(f'<rect x="{bar_x:.1f}" y="{by:.1f}" width="{bar_max:.1f}" height="{bar_h:.1f}" '
                 f'fill="{TINT}"/>')
        o.append(f'<rect x="{bar_x:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bar_h:.1f}" '
                 f'fill="{col}" fill-opacity="0.82"/>')
        o.append(_t(bar_x + bar_max + 16, by + 15, label, 13, weight="bold", fill=col))
        o.append(_t(bar_x + bar_max + 16, by + 31, why, 9.5, fill=MUTED))
        if i:
            o.append(_arrow(bar_x + 26, by - 26, bar_x + 26, by - 4, MUTED, 1.8))
    fy = y2 + 66 + 2 * 74 + bar_h + 34   # below the last bar
    o.append(_t(bar_x, fy, f"{lbf_n(shear, 1)} is {shear_pct:.0f}% of the number on the box — "
                f"in the direction the fridge actually loads it.", 14.5, weight="bold",
                fill=BAD))
    # vendor confirmation, a full-width strip so it reads as a citation, not a caveat
    vy = fy + 20
    o.append(f'<rect x="{bar_x:.1f}" y="{vy:.1f}" width="{W - 80 - 72:.1f}" height="62" rx="5" '
             f'fill="{TINT}" stroke="{RULE}" stroke-width="1.0"/>')
    o.append(_t(bar_x + 16, vy + 24, "Not our theory — the vendors publish the drop themselves.",
                11, weight="bold"))
    o.append(_t(bar_x + 16, vy + 44, f"totalElement rate their 43 mm rubber pot magnet at "
                f"{lbf_n(TOTALELEMENT_PULL_LBF, 1)} vertical pull but only "
                f"{lbf_n(TOTALELEMENT_HORIZONTAL_LBF, 1)} horizontal — "
                f"{vendor_pct:.0f}% of the headline, from their own catalogue.", 10.5,
                fill=MUTED))

    # ------------------------------------------------- section 3: peel / unzip
    y3 = y2 + ch2 + 24
    ch3 = 262.0
    half = (W - 80 - 20) / 2.0
    o += _card(40, y3, half, ch3, "PEEL: YOU NEVER FIGHT THE TOTAL", BAD)
    peel_prose = (
        f"Four magnets at {derated:.0f} lb ({derated * N_PER_LBF:.0f} N) each sounds like "
        f"{4 * derated:.0f} lb ({4 * derated * N_PER_LBF:.0f} N) of holding. It is not. Bump "
        f"the screen's top edge and the plate rotates about its bottom — the prying force is "
        f"multiplied by the lever ratio, and the whole moment lands on the TOP magnet alone, "
        f"at its own {derated:.0f} lb. The instant it lets go, its share dumps onto the next "
        f"one down. Magnet mounts do not fail by being overpowered; they fail by unzipping, "
        f"one magnet at a time.")
    for j, ln in enumerate(_wrap(peel_prose, 60)):
        o.append(_t(40 + 16, y3 + 56 + j * 15.5, ln, 10.5, fill=MUTED))
    # diagram, right side of the card: panel, two magnets, plate, pry at the top
    dx, ptop = 40 + 392, y3 + 74
    o += _mini_panel(dx, ptop, 150)
    for my in (ptop + 30, ptop + 120):
        o += _mini_magnet(dx + 10, my)
    o.append(f'<rect x="{dx + 44:.1f}" y="{ptop + 6:.1f}" width="9" height="138" '
             f'fill="{C_PLATE}" stroke="{INK}" stroke-width="1.0"/>')
    o.append(_arrow(dx + 58, ptop + 8, dx + 118, ptop - 18, BAD))
    o.append(_t(dx + 34, ptop - 30, "small pry,", 10, fill=BAD, weight="bold"))
    o.append(_t(dx + 34, ptop - 18, "long lever", 10, fill=BAD, weight="bold"))
    o.append(f'<circle cx="{dx + 48:.1f}" cy="{ptop + 144:.1f}" r="5" fill="none" '
             f'stroke="{MUTED}" stroke-width="1.6"/>')
    o.append(_t(dx + 62, ptop + 148, "pivot", 9.5, fill=MUTED))
    o.append(_t(dx + 62, ptop + 42, "fails first", 9.5, fill=BAD))

    # ------------------------------------------------- section 4: the magnet-only bill
    x4 = 40 + half + 20
    o += _card(x4, y3, half, ch3, "WHAT MAGNET-ONLY WOULD ACTUALLY NEED", INK)
    rows = [
        (f"Hanging load: display {lbf_n(weight, 1)} + bracket "
         f"{lbf_n(rep['bracket_weight_lbf'], 1)}", f"= {lbf_n(hanging, 1)}", INK),
        (f"Rated pull needed per pound held, in shear: 1 / ({p.magnet_derate:.2f} x "
         f"{p.mu_magnet_face:.1f})", f"= {mult:.0f} lb rated per lb held", MARG),
        (f"So holding {lbf_n(hanging, 1)} in shear needs",
         f"~{rated_needed:.0f} lb ({rated_needed * N_PER_LBF / 1000:.1f} kN) RATED — "
         f"{mult:.0f}x whatever it holds, before any safety factor", BAD),
    ]
    ry = y3 + 54
    for left, right, col in rows:
        o.append(_t(x4 + 16, ry, left, 10.5, fill=MUTED))
        ry += 15
        for ln in _wrap(right, 62):
            o.append(_t(x4 + 16, ry, ln, 11.5, weight="bold", fill=col))
            ry += 16
        ry += 8
    o.append(f'<line x1="{x4 + 16:.1f}" y1="{ry - 4:.1f}" x2="{x4 + half - 16:.1f}" '
             f'y2="{ry - 4:.1f}" stroke="{RULE}" stroke-width="0.8"/>')
    o.append(_t(x4 + 16, ry + 16, "And if the panel is 304 stainless (many are), every magnet "
                "contributes", 10.5, fill=MUTED))
    o.append(_t(x4 + 16, ry + 32, "exactly ZERO. This one measured magnetic — the design still "
                "must not care.", 10.5, weight="bold", fill=BAD))

    # ------------------------------------------------- section 5: the hook
    y5 = y3 + ch3 + 24
    ch5 = 280.0
    o += _card(40, y5, W - 80, ch5, "THE ANSWER: DON'T FIGHT THE PHYSICS — HOOK OVER THE TOP",
               OK)
    # diagram: fridge top corner, L-bracket over it, weight into bearing
    gx, gy = 168.0, y5 + 78          # fridge corner (top-left of the fridge box)
    o.append(f'<rect x="{gx:.1f}" y="{gy:.1f}" width="200" height="132" fill="{C_FRIDGE}" '
             f'stroke="{INK}" stroke-width="1.0"/>')
    o.append(_t(gx + 106, gy + 74, "fridge", 11, anchor="middle", fill=MUTED))
    # bracket: arm across the top, spine down the side face, drawn 8 px thick
    # The spine must stand off the fridge face by the MAGNET, because that is what holds it off:
    # fridge | magnet | plate. An earlier version drew the spine 12 px off the face and put the
    # magnets on the far side of it — i.e. on the display side — which inverts the whole stack.
    mag_gap = 34.0                       # _mini_magnet is 34 px long; the gap IS the magnet
    spine_in = gx - mag_gap              # inner face of the spine, against the magnets
    spine_out = spine_in - 8.0           # 8 px of drawn plate thickness
    # The arm does NOT rest on bare steel. A sponge pad and the arm magnets sit in the gap, both
    # ~11.5 mm tall, so the arm floats that far above the top. Drawing it touching hid the pad
    # entirely and made the pad budget in pad_explainer look like it was about nothing.
    lift = 14.0                          # drawn arm standoff = pad/magnet height
    arm_bot = gy - lift
    arm_top = arm_bot - 8.0
    o.append(f'<path d="M{spine_out:.1f} {gy + 124:.1f} L{spine_out:.1f} {arm_top:.1f} '
             f'L{gx + 96:.1f} {arm_top:.1f} L{gx + 96:.1f} {arm_bot:.1f} '
             f'L{spine_in:.1f} {arm_bot:.1f} L{spine_in:.1f} {gy + 124:.1f} Z" '
             f'fill="{C_PLATE}" stroke="{INK}" stroke-width="1.1"/>')
    # what fills that gap: sponge pad either side, arm magnet between
    o.append(f'<rect x="{spine_in + 2:.1f}" y="{arm_bot:.1f}" width="26" height="{lift:.1f}" '
             f'fill="{C_FOAM}" stroke="#a8830f" stroke-width="0.9"/>')
    o.append(f'<rect x="{spine_in + 34:.1f}" y="{arm_bot:.1f}" width="30" height="{lift:.1f}" '
             f'fill="{C_MAGNET}" stroke="{INK}" stroke-width="0.9"/>')
    o.append(f'<rect x="{spine_in + 70:.1f}" y="{arm_bot:.1f}" width="24" height="{lift:.1f}" '
             f'fill="{C_FOAM}" stroke="#a8830f" stroke-width="0.9"/>')
    # Ran right, straight into the facts column of the same card. Two short lines, left of the
    # fridge box, where the panel is empty.
    o.append(_t(spine_out - 6, arm_bot - 6, "sponge pad + arm magnet:", 9.0, anchor="end",
                fill=MUTED))
    o.append(_t(spine_out - 6, arm_bot + 5, "the arm never touches bare steel", 9.0, anchor="end",
                fill=MUTED))
    o.append(_arrow(spine_out + 4, gy + 130, spine_out + 4, gy + 172, INK))
    o.append(_t(spine_out + 16, gy + 162, f"all {lbf_n(hanging, 1)} of it", 10.5, weight="bold"))
    o.append(_arrow(gx + 40, gy - 40, gx + 40, gy - 16, OK))
    o.append(_t(gx + 52, gy - 32, "bearing: the fridge TOP carries the weight", 10.5, fill=OK,
                weight="bold"))
    for my in (gy + 30, gy + 96):
        o += _mini_magnet(spine_in, my)   # BETWEEN the spine and the fridge face, as built
    o.append(_t(spine_out - 6, gy + 66, "magnets", 9.5, anchor="end", fill=MUTED))
    tx5, ty5 = 470.0, y5 + 56
    facts = [
        ("The arm rests ON the fridge top. The vertical load goes into bearing at the corner — "
         "compression on painted steel over a sponge pad.", INK, "normal"),
        ("The magnets carry ZERO vertical load. They only stop swing and rattle, and that duty "
         "is TENSION — their strong direction.", OK, "bold"),
        (f"Demand on a magnet: {lbf_n(rep['torsion_force_per_magnet_lbf'], 1)} from a firm "
         f"{lbf_n(p.press_force_lbf, 0)} touch press, {lbf_n(rep['peel_lbf'], 1)} of total peel "
         f"— against {lbf_n(derated, 0)} of derated capacity each: "
         f"{rep['magnet_tension_sf']:.0f}x in hand.", MUTED, "normal"),
        ("A non-magnetic panel no longer matters: the hook still carries everything, and the "
         "arm's width still resists the twist.", MUTED, "normal"),
        (f"The stakes: {kg_lb(rep['display_mass_kg'])} of optically bonded glass over a kitchen "
         f"floor. \"Probably strong enough\" is not a spec — a hook is.", BAD, "bold"),
    ]
    fy5 = ty5
    for line, col, wt in facts:
        for ln in _wrap(line, 108):
            o.append(_t(tx5, fy5, ln, 11, fill=col, weight=wt))
            fy5 += 15
        fy5 += 10
    # ---- 6. the honest answer to "so how strong WOULD they have to be?" ----------------------
    # This panel concedes the strongest form of the objection. Pure shear is NOT the reason the
    # hook exists — 8 of the specified magnets clear it comfortably. Saying otherwise would be
    # overstating the case, and the real reasons are better ones.
    y6 = y5 + ch5 + 24
    ch6 = 286.0
    o += _card(40, y6, W - 80, ch6,
               "SO HOW STRONG WOULD THEY HAVE TO BE? — the fair answer", INK)
    f_shear = p.magnet_derate * p.mu_magnet_face
    rated = p.magnet_rated_pull_lbf
    ry = y6 + 52
    # Size against the MAGNET-ONLY mass, not the hook design's. Comparing to 24.9 lb would be
    # circular: most of that steel is the neck and arm, and there is no arm without a hook.
    mo = rep["magnet_only_hanging_lbf"]
    o.append(_t(66, ry, f"A magnet-only mount needs no arm, so it is lighter: screen "
                        f"{rep['display_mass_kg']:.2f} kg + body plate "
                        f"{rep['magnet_only_body_plate_kg']:.2f} kg + "
                        f"{rep['magnet_only_magnets']} magnets = {lbf_n(mo, 1)}, not "
                        f"{lbf_n(hanging, 1)}.", 11, fill=MUTED))
    ry += 18
    o.append(_t(66, ry, f"To hold THAT by friction alone, TOTAL rated pull across all magnets "
                        f"(divide by {f_shear:.3f}):", 11.5, fill=MUTED))
    ry += 24
    for sf, lab in ((1.0, "on the edge of sliding"), (2.5, "project standard"),
                    (4.0, "overhead glass")):
        tot = mo * sf / f_shear
        o.append(_t(90, ry, f"SF {sf:.1f}", 11.5, weight="bold",
                    fill=BAD if sf >= 4 else INK))
        o.append(_t(150, ry, lab, 10.5, fill=MUTED))
        o.append(_t(400, ry, lbf_n(tot, 0), 11.5, weight="bold", anchor="end"))
        o.append(_t(418, ry, f"= {tot/8:.0f} lb x 8 magnets", 10.5, fill=MUTED))
        ry += 21
    ry += 12
    got = 8 * rated * f_shear
    o.append(_t(66, ry, f"The magnets already specified are {rated:.0f} lb each. Eight of them "
                        f"give {lbf_n(got, 1)} of shear — SF {got/mo:.1f} on that load.", 11.5,
               weight="bold", fill=OK))
    ry += 20
    o.append(_t(66, ry, "So shear is NOT the reason for the hook. Magnets can carry this weight. "
                        "The hook is there for what shear numbers do not cover:", 11.5, fill=INK))
    ry += 20
    for line in ("PEEL — a lever at one corner beats a single magnet, not the total, and the rest "
                 "unzip after it.",
                 "A NON-MAGNETIC panel makes every one of those numbers zero. This one measured "
                 "magnetic; the design still must not depend on it.",
                 "CREEP — the paint is a polymer and it flows under sustained shear, while the "
                 "compressor vibrates the panel around the clock. Every cycle lets the magnet "
                 "micro-slip, always downhill. An SF that holds today need not hold in a year.",
                 "The failure mode is bonded glass onto a kitchen floor, with no warning."):
        for ln in _wrap(line, 116):
            o.append(_t(84, ry, ln, 10.5, fill=MUTED))
            ry += 14
    o.append("</svg>")

    H = y6 + ch6 + 36
    header = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
              f'viewBox="0 0 {W:.0f} {H:.0f}">'
              f'<rect width="{W:.0f}" height="{H:.0f}" fill="{PAPER}"/>')
    path.write_text(header + "".join(o), encoding="utf-8")
    LOG.info("Wrote %s — derate chain %.0f -> %.1f -> %.1f lb (%.0f%% of rated); "
             "magnet-only would need ~%.0f lb rated for its own %.1f lb load",
             path, rated, derated, shear, shear_pct, rated_needed,
             rep["magnet_only_hanging_lbf"])
    LOG.debug("Vendor citation: totalElement %.1f lb pull vs %.1f lb horizontal (%.0f%%)",
              TOTALELEMENT_PULL_LBF, TOTALELEMENT_HORIZONTAL_LBF, vendor_pct)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("magnet_primer.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
