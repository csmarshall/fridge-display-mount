#!/usr/bin/env python3
"""The fastener sandwich at one magnet, drawn once per fastener combination.

Two things go wrong behind the plate and neither is visible anywhere else in the drawing set:

  1. THREAD RUN-OUT.  The magnet's stud is a fixed 1/2 in. Everything it must pass through --
     plate, washer, nut -- is not. A thicker plate eats the thread the nut needs.
  2. BEARING AREA.  Three different parts clamp against this plate and they do not share a
     footprint. The magnet face is enormous, a bare nut is tiny, and the washer sits between.
     Same clamp load through a fifth of the area is five times the pressure.

Both are consequences of the SAME hole, so both are drawn on the SAME section. Every dimension
comes from BracketParams / engineering_report -- this module owns no fastener numbers of its own.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging, FRIDGE_SIDE, FRIDGE_SIDE_EDGE, MAGNET_EDGE, MAGNET_FILL, PAD_EDGE, PAD_FILL
import generate_bracket as G
from generate_bracket import (FINISH, MATERIAL, SPECIFIED_LOCKER, SPECIFIED_NUT, SPECIFIED_WASHER,
                              BracketParams, part_no, stack_permutations)

LOG = logging.getLogger("stack")

IN = G.MM_PER_INCH
INK, MUTED, RULE = "#14181c", "#6b757e", "#c9d1d8"
OK, BAD, MARG = "#0a8f6f", "#b00020", "#b8860b"
C_FRIDGE, C_MAGNET, C_PLATE = FRIDGE_SIDE, MAGNET_FILL, "#b9c2c9"
C_WASHER, C_NUT, C_STUD = "#cdd5db", "#9aa6ae", "#c9a227"
C_BEAR = "#f0a202"

SCALE = 4.6          # px per mm, used for BOTH axes -- this is a true section, not a schematic
RAD_MAX = 28.0       # mm of plate shown either side of the axis before the break lines


def _esc(s) -> str:
    """SVG is XML: a bare < or & in a label silently breaks the whole document."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _t(x, y, s, size=10.0, anchor="middle", fill=INK, weight="normal", rot=0.0):
    tr = f' transform="rotate({rot:.1f} {x:.2f} {y:.2f})"' if rot else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}"{tr}>{_esc(s)}</text>')


def _band(x, w, axis_y, outer, inner, fill, stroke=INK, brk=False):
    """One layer of the section: an annular part cut through its axis is two mirrored bars.

    brk=True clips the part at RAD_MAX and adds break ticks -- the plate and the fridge panel
    both run far past this detail and drawing them to their true extent would say otherwise.
    """
    out = []
    ro, ri = min(outer / 2.0, RAD_MAX) * SCALE, inner * SCALE / 2.0
    for sign in (-1, 1):
        y = axis_y + ri if sign > 0 else axis_y - ro
        out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{ro - ri:.2f}" '
                   f'fill="{fill}" stroke="{stroke}" stroke-width="0.9"/>')
        if brk:
            ey = axis_y + sign * ro
            out.append(f'<line x1="{x - 2:.2f}" y1="{ey - sign*4:.2f}" x2="{x + w + 2:.2f}" '
                       f'y2="{ey + sign*2:.2f}" stroke="#fbfcfd" stroke-width="3.2"/>')
            out.append(f'<line x1="{x - 2:.2f}" y1="{ey - sign*5:.2f}" x2="{x + w + 2:.2f}" '
                       f'y2="{ey + sign*1:.2f}" stroke="{MUTED}" stroke-width="0.8"/>')
            out.append(f'<line x1="{x - 2:.2f}" y1="{ey - sign*1:.2f}" x2="{x + w + 2:.2f}" '
                       f'y2="{ey + sign*5:.2f}" stroke="{MUTED}" stroke-width="0.8"/>')
    return out


def _dim_v(x, axis_y, dia, label, colour=INK, size=9.0):
    """A vertical dimension across a part's full diameter -- this is the radial story."""
    r = dia * SCALE / 2.0
    o = [f'<line x1="{x:.2f}" y1="{axis_y - r:.2f}" x2="{x:.2f}" y2="{axis_y + r:.2f}" '
         f'stroke="{colour}" stroke-width="0.9"/>']
    for yy in (axis_y - r, axis_y + r):
        o.append(f'<line x1="{x - 4:.2f}" y1="{yy:.2f}" x2="{x + 4:.2f}" y2="{yy:.2f}" '
                 f'stroke="{colour}" stroke-width="1.1"/>')
    o.append(_t(x - 4, axis_y, label, size, anchor="middle", fill=colour, weight="bold",
                rot=-90))
    return o


def _section(x0, y0, cw, opt, p, rep) -> list[str]:
    """Draw one permutation, straight off its StackOption. No fastener numbers live here."""
    t, stud = opt.plate, opt.stud
    nut_h, wsh = opt.nut.height, opt.washer.t
    spec = (opt.nut.key == SPECIFIED_NUT and opt.washer.key == SPECIFIED_WASHER)
    col = {"ok": OK, "marginal": MARG, "bad": BAD}[opt.state]
    tint = {"ok": "#eef7f2", "marginal": "#fdf6e6", "bad": "#fdf0f1"}[opt.state]

    half = RAD_MAX * SCALE
    axis = y0 + 52 + half
    top, bot = axis - half, axis + half
    o: list[str] = []

    verdict = {"ok": f"{opt.slack:+.2f} mm to spare",
               "marginal": f"{opt.slack:+.2f} mm — TOLERANCE STACK",
               "bad": f"SHORT BY {-opt.slack:.2f} mm"}[opt.state]
    o.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{cw:.1f}" height="30" rx="4" '
             f'fill="{tint}" stroke="{col}" stroke-width="{2.2 if spec else 1.3}"/>')
    name = opt.nut.name + ("" if opt.washer.key == "none" else f" + {opt.washer.name}")
    # The verdict is right-aligned in the same 30 px strip. "distorted-thread locknut
    # (centre-lock) + OVERSIZED washer O1.250" ran straight into it and the two overprinted.
    # Shrink the title until it fits the space the verdict leaves, rather than letting it collide.
    avail = cw - 24 - len(verdict) * 6.2 - 18
    size = 11.5 if len(name) * 6.4 <= avail else max(8.5, avail / max(len(name), 1) * 1.55)
    o.append(_t(x0 + 12, y0 + 20, name, size, anchor="start", weight="bold", fill=col))
    o.append(_t(x0 + cw - 12, y0 + 20, verdict, 11, anchor="end", fill=col, weight="bold"))

    # ---- the section -------------------------------------------------------------------------
    x = x0 + 34.0
    bom: list[tuple[str, str, str, tuple]] = []

    fw = 0.9 * SCALE + 3
    o += _band(x, fw, axis, RAD_MAX * 2, 0.0, C_FRIDGE, brk=True)
    x += fw

    mag_x, mag_w = x, p.magnet_standoff * SCALE
    o += _band(mag_x, mag_w, axis, p.magnet_disc_dia, p.magnet_hole_dia, C_MAGNET)
    bom.append((C_MAGNET, "MAGNET pot", f"O{p.magnet_disc_dia:.2f} x {p.magnet_standoff:.2f} mm",
                (part_no("magnet")[0], "n/a")))
    x += mag_w

    plate_x, plate_w = x, t * SCALE
    o += _band(plate_x, plate_w, axis, RAD_MAX * 2, opt.hole_dia, C_PLATE, brk=True)
    bom.append((C_PLATE, "PLATE", f"{t:.2f} mm ({MATERIAL.thickness_in:.3f} in)",
                ("this DXF", "")))
    x += plate_w
    face = x

    if wsh:
        o += _band(x, wsh * SCALE, axis, opt.washer.od, opt.washer.bore, C_WASHER)
        bom.append((C_WASHER, "WASHER",
                    f"O{opt.washer.od:.2f} / O{opt.washer.bore:.2f} x {wsh:.2f} mm",
                    part_no(f"washer_{opt.washer.key}")))
        x += wsh * SCALE
    af = opt.nut.across_flats_in * IN
    o += _band(x, nut_h * SCALE, axis, af, 5 / 16 * IN, C_NUT)
    # A flange or keps nut carries its own bearing face, wider than the flats. Draw it, or the
    # section would understate what actually touches the plate.
    if opt.nut.bearing_od > af:
        o += _band(x, 0.05 * IN * SCALE, axis, opt.nut.bearing_od, 5 / 16 * IN, C_NUT)
    bom.append((C_NUT, "NUT", f"{af:.2f} mm AF x {nut_h:.2f} mm", part_no(f"nut_{opt.nut.key}")))
    x += nut_h * SCALE
    stack_end = x

    stud_x = mag_x + mag_w
    o.append(f'<rect x="{stud_x:.2f}" y="{axis - 5/16*IN*SCALE/2:.2f}" '
             f'width="{stud*SCALE:.2f}" height="{5/16*IN*SCALE:.2f}" fill="{C_STUD}" '
             f'fill-opacity="0.8" stroke="#6d5300" stroke-width="1.0"/>')
    se = stud_x + stud * SCALE
    o.append(f'<line x1="{se:.2f}" y1="{top - 4:.2f}" x2="{se:.2f}" y2="{bot:.2f}" '
             f'stroke="{BAD}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    o.append(_t(se + 4, top - 6, "stud ends here", 9.0, anchor="start", fill=BAD, weight="bold"))
    if opt.state != "ok":
        o.append(f'<rect x="{se:.2f}" y="{axis - nut_h*SCALE:.2f}" '
                 f'width="{max(stack_end - se, 2):.2f}" height="{nut_h*SCALE*2:.2f}" '
                 f'fill="{col}" fill-opacity="0.22"/>')

    hr = opt.hole_dia * SCALE / 2.0
    for yy in (axis - hr, axis + hr):
        o.append(f'<line x1="{plate_x:.2f}" y1="{yy:.2f}" x2="{plate_x + plate_w:.2f}" '
                 f'y2="{yy:.2f}" stroke="{BAD}" stroke-width="1.2"/>')

    bear_od = opt.washer.od if wsh else opt.nut.bearing_od
    bear_id = opt.washer.bore if wsh else opt.hole_dia
    for sign in (-1, 1):
        ro, ri = min(bear_od / 2.0, RAD_MAX) * SCALE, bear_id * SCALE / 2.0
        yy = axis + ri if sign > 0 else axis - ro
        o.append(f'<rect x="{face - 2.5:.2f}" y="{yy:.2f}" width="5" height="{ro - ri:.2f}" '
                 f'fill="{C_BEAR}"/>')
    for sign in (-1, 1):
        ro, ri = p.magnet_disc_dia * SCALE / 2.0, hr
        yy = axis + ri if sign > 0 else axis - ro
        o.append(f'<rect x="{plate_x - 2.5:.2f}" y="{yy:.2f}" width="5" height="{ro - ri:.2f}" '
                 f'fill="{C_BEAR}" fill-opacity="0.45"/>')

    # ---- parts, keyed by colour ----------------------------------------------------------------
    bx, by = x0 + 306, axis - 62
    o.append(_t(bx, by - 14, "PARTS IN THIS STACK", 9.5, anchor="start", weight="bold",
                fill=MUTED))
    for j, (swatch, pname, detail, (pn, fin)) in enumerate(bom):
        ry = by + j * 34
        o.append(f'<rect x="{bx:.1f}" y="{ry - 8:.1f}" width="11" height="11" fill="{swatch}" '
                 f'stroke="{INK}" stroke-width="0.8"/>')
        o.append(_t(bx + 18, ry + 1, pname, 10.0, anchor="start", weight="bold"))
        o.append(_t(bx + 18, ry + 14, detail, 9.0, anchor="start", fill=MUTED))
        if pn is None:
            o.append(_t(x0 + cw - 12, ry + 1, "NOT SOURCED", 9.5, anchor="end", fill=BAD,
                        weight="bold"))
        else:
            o.append(_t(x0 + cw - 12, ry + 1, pn, 10.0, anchor="end",
                        fill=INK if fin else MUTED, weight="bold" if fin else "normal"))
            if fin:
                label, fill = {"black": ("black oxide", MUTED),
                               "n/a": ("zinc case - never black", MUTED),
                               }.get(fin, ("PLAIN - no black stocked", BAD))
                o.append(_t(x0 + cw - 12, ry + 14, label, 8.5, anchor="end", fill=fill))

    dx = x0 + 196
    o += _dim_v(dx, axis, opt.hole_dia, f"HOLE O{opt.hole_dia:.1f}", BAD)
    o += _dim_v(dx + 40, axis, min(bear_od, RAD_MAX * 2),
                f"{'washer O' if wsh else 'nut '}{bear_od:.2f}", "#8a5a00")
    o += _dim_v(dx + 84, axis, p.magnet_disc_dia, f"magnet O{p.magnet_disc_dia:.2f}", MUTED)

    ny = bot + 66
    o.append(f'<rect x="{x0:.1f}" y="{ny - 15:.1f}" width="{cw:.1f}" height="52" rx="3" '
             f'fill="#f4f6f8"/>')
    o.append(f'<rect x="{x0 + 10:.1f}" y="{ny - 7:.1f}" width="10" height="10" fill="{C_BEAR}"/>')
    o.append(_t(x0 + 26, ny + 2, "bears on the plate over", 10.5, anchor="start", fill=MUTED))
    o.append(_t(x0 + 168, ny + 2, f"{opt.bearing_area:.0f} mm2 "
                f"({opt.bearing_area/IN**2:.2f} in2)", 11.5, anchor="start", weight="bold"))
    o.append(_t(x0 + cw - 12, ny + 2, f"{opt.plate:.2f} + {wsh:.2f} + {nut_h:.2f} = "
                f"{opt.needed:.2f} vs stud {stud:.2f}", 9.5, anchor="end", fill=MUTED))
    o.append(_t(x0 + 26, ny + 22, "contact pressure at magnet pull", 10.5, anchor="start",
                fill=MUTED))
    o.append(_t(x0 + 210, ny + 22,
                f"{opt.bearing_psi(rep['magnet_derated_pull_lbf']):.0f} psi", 11.5,
                anchor="start", weight="bold"))
    o.append(_t(x0 + cw - 12, ny + 22, f"locking: {opt.locking}", 9.5, anchor="end",
                fill=BAD if opt.locking == "NONE" else INK,
                weight="normal" if opt.locking == "NONE" else "bold"))
    return o


def render(path: Path, p: BracketParams) -> None:
    geom = G.build_geometry(p, G.derive_flat(p))
    rep = G.engineering_report(p, geom)
    t = MATERIAL.thickness

    # Threadlocker does not change the GEOMETRY, so drawing a section for it would be a duplicate.
    # This sheet shows every distinct stack shape that is not a hopeless miss; fastener_matrix.svg
    # carries all 39 permutations including the chemical ones.
    allperm = stack_permutations(p)
    seen, options = set(), []
    for r in allperm:
        key = (r.nut.key, r.washer.key)
        if key in seen or r.state == "bad":
            continue
        seen.add(key)
        options.append(r)

    cw, ch = 548.0, 436.0
    rows = (len(options) + 1) // 2
    W = 40 + cw * 2 + 24 + 40
    H = 190 + ch * rows + 150

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfcfd"/>',
         _t(40, 46, "THE FASTENER SANDWICH AT ONE MAGNET", 19, anchor="start", weight="bold"),
         _t(40, 70, f"True section through one magnet position, drawn at one scale on both axes "
                    f"- {SCALE:.1f} px/mm across AND through. One drawing per distinct stack "
                    f"shape.", 12, anchor="start", fill=MUTED),
         _t(40, 90, f"Plate {t:.2f} mm ({MATERIAL.thickness_in:.3f} in), hole "
                    f"O{p.magnet_hole_dia:.1f} mm, stud a fixed {p.magnet_stud_len:.2f} mm "
                    f"({p.magnet_stud_len/IN:.3f} in). Change any of those and every panel here "
                    f"changes with it.", 12, anchor="start", fill=MUTED),
         _t(40, 112, "The orange band is where that part actually touches the plate. Part numbers "
                     "are McMaster-Carr, read off their tables on 2026-08-27.", 12,
            anchor="start", fill="#8a5a00", weight="bold"),
         _t(40, 132, f"Washer thickness is the MAX of the range it is sold to - every stack is "
                     f"checked against the thickest one that might ship.", 11.5, anchor="start",
            fill=MUTED),
         _t(40, 154, f"Showing the {len(options)} stack shapes that fit or are marginal, out of "
                     f"{len(allperm)} permutations. Threadlocker changes locking, not geometry, "
                     f"so it has no separate panel - see fastener_matrix.svg for all of them.",
            11.5, anchor="start", fill=MUTED)]

    for i, opt in enumerate(options):
        cx = 40 + (i % 2) * (cw + 24)
        cy = 190 + (i // 2) * ch
        o += _section(cx, cy, cw, opt, p, rep)

    spec = next(r for r in allperm
                if r.nut.key == SPECIFIED_NUT and r.washer.key == SPECIFIED_WASHER
                and r.locker == SPECIFIED_LOCKER)
    fits = [r for r in allperm if r.state == "ok"]
    best_area = max(fits, key=lambda r: r.bearing_area)
    fy = 190 + rows * ch + 30
    o.append(f'<rect x="40" y="{fy - 20:.1f}" width="{W - 80:.1f}" height="134" fill="#fff" '
             f'stroke="{OK}" stroke-width="1.6" rx="4"/>')
    o.append(_t(56, fy, f"USE: {spec.label}", 13.5, anchor="start", weight="bold", fill=OK))
    o.append(_t(56, fy + 22,
                f"{spec.plate:.2f} + {spec.washer.t:.2f} + {spec.nut.height:.2f} = "
                f"{spec.needed:.2f} mm against a {spec.stud:.2f} mm stud: "
                f"{spec.slack:+.2f} mm to spare, and {spec.bearing_area:.0f} mm2 of bearing - "
                f"the most of any stack that fits, {spec.bearing_area / 69.9:.0f}x a bare nut.",
                11.5, anchor="start", fill=MUTED))
    o.append(_t(56, fy + 42,
                f"The half-height JAM nut is what buys the room: it is "
                f"{G.NUTS_BY_KEY['nyloc_thin'].height - spec.nut.height:.2f} mm shorter than the "
                f"thinnest LOCKNUT, which is exactly what a washer costs. Locking is chemical "
                f"instead - threadlocker adds no height at all.", 11.5, anchor="start",
                fill=MUTED))
    # Was one line and ran past the box and off the canvas. Split at a sentence boundary.
    o.append(_t(56, fy + 62,
                f"Runner-up is the THIN nylon-insert locknut, no washer: "
                f"{G.NUTS_BY_KEY['nyloc_thin'].height + spec.plate:.2f} mm used, +1.60 mm spare, "
                f"and a MECHANICAL lock that needs no chemical.", 11.5, anchor="start", fill=MUTED))
    o.append(_t(56, fy + 80,
                "It survives being taken apart, and bears on only 70 mm2 — which is harmless. So "
                "this is a preference, not a correctness call.", 11.5, anchor="start", fill=MUTED))
    o.append(_t(56, fy + 82, f"Fasteners are {FINISH.upper()} OXIDE where stocked - only the ARM "
                f"nuts are visible, facing up against a textured-black arm.", 11.0, anchor="start",
                fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s - %d distinct stack shapes drawn from %d permutations; specified: %s",
             path, len(options), len(allperm), spec.label)
    for opt in options:
        LOG.debug("%-58s %5.2f vs %5.2f  %+6.2f  %-10s %5.0f mm2", opt.label, opt.needed,
                  opt.stud, opt.slack, opt.state, opt.bearing_area)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("stack_detail.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
