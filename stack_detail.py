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

from bracket_common import LOG_LEVELS, configure_logging
import generate_bracket as G
from generate_bracket import FINISH, MATERIAL, BracketParams, part_no

LOG = logging.getLogger("stack")

IN = G.MM_PER_INCH
INK, MUTED, RULE = "#14181c", "#6b757e", "#c9d1d8"
OK, BAD, MARG = "#0a8f6f", "#b00020", "#b8860b"
C_FRIDGE, C_MAGNET, C_PLATE = "#dfe3e6", "#e7b6dd", "#b9c2c9"
C_WASHER, C_NUT, C_STUD = "#cdd5db", "#9aa6ae", "#c9a227"
C_BEAR = "#f0a202"

SCALE = 4.6          # px per mm, used for BOTH axes -- this is a true section, not a schematic
RAD_MAX = 28.0       # mm of plate shown either side of the axis before the break lines


def _t(x, y, s, size=10.0, anchor="middle", fill=INK, weight="normal", rot=0.0):
    tr = f' transform="rotate({rot:.1f} {x:.2f} {y:.2f})"' if rot else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}"{tr}>{s}</text>')


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


def _section(x0, y0, cw, name, wsh, nut_h, nut_kind, nut_key, lock, p, rep):
    """Draw one fastener combination. Returns (svg, does_the_stud_engage)."""
    t = MATERIAL.thickness
    stud = p.magnet_stud_len
    need = t + wsh + nut_h
    slack = stud - need
    # Three states, not two. "washer + full hex nut" misses by 0.08 mm, which is smaller than the
    # tolerance stack on a stud length, a plate thickness and a nut height added together. Calling
    # that a clean FAIL is as dishonest as calling it a pass.
    state = "ok" if slack >= 0.5 else ("marginal" if slack >= -0.5 else "bad")
    good = state == "ok"
    col = {"ok": OK, "marginal": MARG, "bad": BAD}[state]
    tint = {"ok": "#eef7f2", "marginal": "#fdf6e6", "bad": "#fdf0f1"}[state]

    half = RAD_MAX * SCALE
    axis = y0 + 52 + half
    top, bot = axis - half, axis + half
    o: list[str] = []

    o.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{cw:.1f}" height="30" rx="4" '
             f'fill="{tint}" stroke="{col}" stroke-width="1.3"/>')
    o.append(_t(x0 + 12, y0 + 20, name, 12.5, anchor="start", weight="bold", fill=col))
    if lock:
        o.append(f'<rect x="{x0 + 13 + len(name) * 6.6:.1f}" y="{y0 + 8:.1f}" width="46" '
                 f'height="15" rx="7" fill="{INK}"/>')
        o.append(_t(x0 + 36 + len(name) * 6.6, y0 + 19, "LOCKING", 8.5, fill="#fff",
                    weight="bold"))
    verdict = {"ok": f"{slack:+.2f} mm thread to spare",
               "marginal": f"{slack:+.2f} mm — INSIDE THE TOLERANCE STACK",
               "bad": f"STUD SHORT BY {-slack:.2f} mm"}[state]
    o.append(_t(x0 + cw - 12, y0 + 20, verdict, 11.5, anchor="end", fill=col, weight="bold"))

    # ---- the section -------------------------------------------------------------------------
    x = x0 + 34.0
    bom: list[tuple[str, str, str, str | None]] = []

    fw = 0.9 * SCALE + 3
    o += _band(x, fw, axis, RAD_MAX * 2, 0.0, C_FRIDGE, brk=True)
    x += fw

    mag_x, mag_w = x, p.magnet_standoff * SCALE
    o += _band(mag_x, mag_w, axis, p.magnet_disc_dia, p.magnet_hole_dia, C_MAGNET)
    bom.append((C_MAGNET, "MAGNET pot", f"O{p.magnet_disc_dia:.2f} x {p.magnet_standoff:.2f} mm",
                (part_no("magnet")[0], "n/a")))
    x += mag_w

    plate_x, plate_w = x, t * SCALE
    o += _band(plate_x, plate_w, axis, RAD_MAX * 2, p.magnet_hole_dia, C_PLATE, brk=True)
    bom.append((C_PLATE, "PLATE",
                f"{t:.2f} mm ({MATERIAL.thickness_in:.3f} in)", ("this DXF", "")))
    x += plate_w
    face = x

    if wsh:
        o += _band(x, wsh * SCALE, axis, p.washer_od, p.washer_id, C_WASHER)
        bom.append((C_WASHER, "WASHER flat",
                    f"O{p.washer_od:.2f} / O{p.washer_id:.2f} x {wsh:.2f} mm", part_no("washer")))
        x += wsh * SCALE
    o += _band(x, nut_h * SCALE, axis, p.nut_across_flats, 5 / 16 * IN, C_NUT)
    bom.append((C_NUT, f"NUT {nut_kind}",
                f"{p.nut_across_flats:.2f} mm AF x {nut_h:.2f} mm", part_no(nut_key)))
    x += nut_h * SCALE
    stack_end = x

    # the stud, on the axis, drawn as far as it actually reaches
    stud_x = mag_x + mag_w
    o.append(f'<rect x="{stud_x:.2f}" y="{axis - 5/16*IN*SCALE/2:.2f}" '
             f'width="{stud*SCALE:.2f}" height="{5/16*IN*SCALE:.2f}" fill="{C_STUD}" '
             f'fill-opacity="0.8" stroke="#6d5300" stroke-width="1.0"/>')
    se = stud_x + stud * SCALE
    o.append(f'<line x1="{se:.2f}" y1="{top - 4:.2f}" x2="{se:.2f}" y2="{bot:.2f}" '
             f'stroke="{BAD}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    o.append(_t(se + 4, top - 6, "stud ends here", 9.0, anchor="start", fill=BAD, weight="bold"))
    if state != "ok":
        o.append(f'<rect x="{se:.2f}" y="{axis - nut_h*SCALE:.2f}" '
                 f'width="{max(stack_end - se, 2):.2f}" height="{nut_h*SCALE*2:.2f}" '
                 f'fill="{BAD}" fill-opacity="0.22"/>')
        o.append(_t((se + stack_end) / 2, axis - nut_h * SCALE - 6, "no thread here", 8.5,
                    fill=BAD, weight="bold"))

    # ---- the hole edge, and the band that actually bears on it --------------------------------
    hr = p.magnet_hole_dia * SCALE / 2.0
    for yy in (axis - hr, axis + hr):
        o.append(f'<line x1="{plate_x:.2f}" y1="{yy:.2f}" x2="{plate_x + plate_w:.2f}" '
                 f'y2="{yy:.2f}" stroke="{BAD}" stroke-width="1.2"/>')

    bear_od = p.washer_od if wsh else p.nut_across_flats
    bear_id = p.washer_id if wsh else p.magnet_hole_dia
    for sign in (-1, 1):
        ro, ri = bear_od * SCALE / 2.0, bear_id * SCALE / 2.0
        y = axis + ri if sign > 0 else axis - ro
        o.append(f'<rect x="{face - 2.5:.2f}" y="{y:.2f}" width="5" height="{ro - ri:.2f}" '
                 f'fill="{C_BEAR}"/>')
    # and the magnet's own, on the far face of the plate
    for sign in (-1, 1):
        ro, ri = p.magnet_disc_dia * SCALE / 2.0, hr
        y = axis + ri if sign > 0 else axis - ro
        o.append(f'<rect x="{plate_x - 2.5:.2f}" y="{y:.2f}" width="5" height="{ro - ri:.2f}" '
                 f'fill="{C_BEAR}" fill-opacity="0.45"/>')

    # ---- the parts, keyed by colour ------------------------------------------------------------
    # These used to be -45 deg leaders hanging off each layer. At 4.6 px/mm a 1.75 mm washer is
    # eight pixels wide, so five leaders landed on top of each other every time. A keyed list in
    # the panel's dead space reads better and has room for the part number, which the leaders
    # never did.
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
                # Say WHICH finish. A silver part on a sheet that claims to be all-black is
                # exactly the kind of thing nobody notices until the box arrives.
                label, fill = {
                    "black": ("black oxide", MUTED),
                    "n/a": ("zinc case - never black", MUTED),
                }.get(fin, ("PLAIN - no black stocked", BAD))
                o.append(_t(x0 + cw - 12, ry + 14, label, 8.5, anchor="end", fill=fill))

    # ---- radial dimension ladder ---------------------------------------------------------------
    dx = x0 + 196
    o += _dim_v(dx, axis, p.magnet_hole_dia, f"HOLE O{p.magnet_hole_dia:.1f}", BAD)
    o += _dim_v(dx + 40, axis, bear_od,
                f"{'washer O' if wsh else 'nut AF '}{bear_od:.2f}", "#8a5a00")
    o += _dim_v(dx + 84, axis, p.magnet_disc_dia, f"magnet O{p.magnet_disc_dia:.2f}", MUTED)

    area = rep["washer_bearing_area_mm2"] if wsh else rep["nut_bearing_area_mm2"]
    psi = rep["washer_bearing_psi"] if wsh else rep["nut_bearing_psi"]

    ny = bot + 66
    o.append(f'<rect x="{x0:.1f}" y="{ny - 15:.1f}" width="{cw:.1f}" height="52" rx="3" '
             f'fill="#f4f6f8"/>')
    o.append(f'<rect x="{x0 + 10:.1f}" y="{ny - 7:.1f}" width="10" height="10" fill="{C_BEAR}"/>')
    o.append(_t(x0 + 26, ny + 2, "bears on the plate over", 10.5, anchor="start", fill=MUTED))
    o.append(_t(x0 + 168, ny + 2, f"{area:.0f} mm2 ({area/IN**2:.2f} in2)", 11.5, anchor="start",
                weight="bold"))
    o.append(_t(x0 + cw - 12, ny + 2,
                f"magnet side bears over {rep['magnet_bearing_area_mm2']:.0f} mm2", 9.5,
                anchor="end", fill=MUTED))
    o.append(_t(x0 + 26, ny + 22, "contact pressure at magnet pull", 10.5, anchor="start",
                fill=MUTED))
    o.append(_t(x0 + 210, ny + 22, f"{psi:.0f} psi", 11.5, anchor="start", weight="bold"))
    o.append(_t(x0 + cw - 12, ny + 22,
                f"vs {rep['magnet_bearing_psi']:.0f} psi on the magnet side", 9.5, anchor="end",
                fill=MUTED))
    return o, state


def render(path: Path, p: BracketParams) -> None:
    flat = G.derive_flat(p)
    geom = G.build_geometry(p, flat)
    rep = G.engineering_report(p, geom)
    t = MATERIAL.thickness

    # Ordered worst-fitting first, so the drawing reads as a search that CONVERGES rather than a
    # list of unrelated options. The jam nut is the half-height one; it is on this sheet because
    # it is the only way to keep the washer once the plate went to 0.188 in.
    # FIVE nut constructions x washer/no-washer. The first pass carried only the standard nyloc,
    # found it too tall, and concluded no locking nut fits — which does not follow. Thin-profile
    # nylon-insert and distorted-thread ("all-metal") both fit, and the distorted-thread one is
    # the SAME height as a plain hex nut, so it adds locking for nothing.
    nuts = [
        ("nylon-insert locknut", p.nut_h_nyloc, "nylon-insert", "nut_nyloc", True),
        ("THIN nylon-insert locknut", p.nut_h_nyloc_thin, "nyloc THIN", "nut_nyloc_thin", True),
        ("distorted-thread locknut", p.nut_h_distorted, "distorted-thread", "nut_distorted", True),
        ("standard hex nut", p.nut_h_hex, "hex standard", "nut_hex", False),
        ("JAM nut (half height)", p.nut_h_jam, "hex JAM/thin", "nut_jam", False),
    ]
    options = []
    for label, nh, kind, key, lock in nuts:
        options.append((f"washer + {label}", p.washer_t, nh, kind, key, lock))
        options.append((f"{label}, no washer", 0.0, nh, kind, key, lock))

    cw, ch = 548.0, 436.0
    rows = (len(options) + 1) // 2
    W = 40 + cw * 2 + 24 + 40
    H = 168 + ch * rows + 150

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfcfd"/>',
         _t(40, 46, "THE FASTENER SANDWICH AT ONE MAGNET", 19, anchor="start", weight="bold"),
         _t(40, 70, f"True section through one magnet position, drawn at one scale on both axes "
                    f"- {SCALE:.1f} px/mm across AND through. One drawing per fastener "
                    f"combination.", 12, anchor="start", fill=MUTED),
         _t(40, 90, f"Plate {t:.2f} mm ({MATERIAL.thickness_in:.3f} in), hole "
                    f"O{p.magnet_hole_dia:.1f} mm, stud a fixed {p.magnet_stud_len:.2f} mm "
                    f"({p.magnet_stud_len/IN:.3f} in). Change any of those and every panel here "
                    f"changes with it.", 12, anchor="start", fill=MUTED),
         _t(40, 116, "The orange band is where that part actually touches the plate. Part "
                     "numbers are McMaster-Carr, read off their tables on 2026-08-27.", 12,
            anchor="start", fill="#8a5a00", weight="bold"),
         _t(40, 136, f"Washer thickness is a RANGE ({p.washer_t_min:.2f}-{p.washer_t:.2f} mm), "
                     f"not a nominal - every stack here is checked against the THICKEST one you "
                     f"might be shipped.", 11.5, anchor="start", fill=MUTED)]

    best = None
    states = {}
    fits = []
    for i, (name, wsh, nut_h, nkind, nkey, lock) in enumerate(options):
        cx = 40 + (i % 2) * (cw + 24)
        cy = 168 + (i // 2) * ch
        svg, st = _section(cx, cy, cw, name, wsh, nut_h, nkind, nkey, lock, p, rep)
        o += svg
        states[name] = st
        if st == "ok":
            fits.append((name, bool(wsh), lock, p.magnet_stud_len - (t + wsh + nut_h)))
    # LOCKING beats bearing area. Neither bearing case is within 60x of yielding the plate, so the
    # washer is comfort; a nut backing off under touch-cycling is an actual failure.
    best = max(fits, key=lambda f: (f[2], f[1], f[3])) if fits else None

    fy = 168 + rows * ch + 30
    ok_name = best[0] if best else None
    o.append(f'<rect x="40" y="{fy - 20:.1f}" width="{W - 80:.1f}" height="116" fill="#fff" '
             f'stroke="{OK if best else BAD}" stroke-width="1.6" rx="4"/>')
    o.append(_t(56, fy, f"USE: {ok_name}" if best else
                "NO STANDARD NUT FITS - the stud is too short for this plate", 13.5,
                anchor="start", weight="bold", fill=OK if best else BAD))
    o.append(_t(56, fy + 22,
                f"The washer is worth having: it spreads the clamp over "
                f"{rep['washer_bearing_area_mm2']:.0f} mm2 instead of a bare nut's "
                f"{rep['nut_bearing_area_mm2']:.0f} mm2 - {rep['washer_bearing_gain']:.1f}x the "
                f"area, {rep['nut_bearing_psi'] - rep['washer_bearing_psi']:.0f} psi less on the "
                f"plate. The question was only ever whether it FITS.", 11.5, anchor="start",
                fill=MUTED))
    o.append(_t(56, fy + 42,
                f"You can have LOCKING or the washer, not both: the thin nyloc misses with a "
                f"washer by {abs(p.magnet_stud_len - (t + p.washer_t + p.nut_h_nyloc_thin)):.2f} "
                f"mm. Locking wins - the bare nut's {rep['nut_bearing_psi']:.0f} psi is still "
                f"{MATERIAL.yield_psi / rep['nut_bearing_psi']:.0f}x under yield, so the washer "
                f"is comfort, while a nut backing off under touch-cycling is a real failure.",
                11.5, anchor="start", fill=MUTED))
    o.append(_t(56, fy + 62,
                f"Runner-up: the distorted-thread locknut is the SAME "
                f"{p.nut_h_distorted:.2f} mm height as a plain hex nut - locking for nothing - "
                f"but it is not reusable and is not stocked in black.", 11.0,
                anchor="start", fill=MUTED))
    o.append(_t(56, fy + 80, f"Fasteners are specified in {FINISH.upper()} OXIDE throughout: "
                f"only the ARM nuts are visible, and they face up against a matte-black arm.",
                11.0, anchor="start", fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s - plate %.2f mm, stud %.2f mm, %d of %d combinations fit, chosen: %s",
             path, t, p.magnet_stud_len, len(fits), len(options), ok_name or "NONE")
    LOG.debug("bearing: magnet %.0f mm2 / washer %.0f mm2 / bare nut %.0f mm2 (%.2fx)",
              rep["magnet_bearing_area_mm2"], rep["washer_bearing_area_mm2"],
              rep["nut_bearing_area_mm2"], rep["washer_bearing_gain"])
    for name, wsh, nut_h, _k, key, lock in options:
        pn, fin = part_no(key)
        LOG.debug("%-38s needs %5.2f mm, slack %+.2f mm  %s  %s (%s)", name, t + wsh + nut_h,
                  p.magnet_stud_len - (t + wsh + nut_h), "LOCK" if lock else "    ",
                  pn or "UNSOURCED", fin or "-")


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
