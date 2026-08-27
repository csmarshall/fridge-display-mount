#!/usr/bin/env python3
"""Layered assembly drawing: plate, display and the display's raised rear box, in portrait.

The display and its rear bump-out are drawn as transparent overlays on the plate so the alignment
between VESA holes, vent windows, magnets and the box footprint can be read directly. Front
elevation plus a depth section. Reference-only.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging, FRIDGE_SIDE, FRIDGE_SIDE_EDGE, MAGNET_EDGE, MAGNET_FILL, PAD_EDGE, PAD_FILL
import generate_bracket as G
from generate_bracket import (
    DISPLAYS, MATERIAL, BracketParams, build_geometry, derive_flat, set_display,
)

LOG = logging.getLogger("assembly")


def _esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _t(x, y, s, size=10.0, anchor="middle", fill="#111", weight="normal", rotate=0.0, family=None):
    tr = f' transform="rotate({rotate:.1f} {x:.1f} {y:.1f})"' if rotate else ""
    fam = family or "Helvetica,Arial,sans-serif"
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" '
            f'text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"{tr}>{_esc(s)}</text>')


def _dim_h(x0, x1, y, label, colour="#0a7", tick=5):
    o = [f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="{colour}" stroke-width="0.7"/>']
    for x in (x0, x1):
        o.append(f'<line x1="{x:.1f}" y1="{y-tick:.1f}" x2="{x:.1f}" y2="{y+tick:.1f}" '
                 f'stroke="{colour}" stroke-width="0.7"/>')
    o.append(_t((x0+x1)/2, y-4, label, 8.5, fill=colour))
    return "".join(o)


def _dim_v(y0, y1, x, label, colour="#0a7", tick=5):
    o = [f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x:.1f}" y2="{y1:.1f}" stroke="{colour}" stroke-width="0.7"/>']
    for y in (y0, y1):
        o.append(f'<line x1="{x-tick:.1f}" y1="{y:.1f}" x2="{x+tick:.1f}" y2="{y:.1f}" '
                 f'stroke="{colour}" stroke-width="0.7"/>')
    o.append(_t(x-4, (y0+y1)/2, label, 8.5, fill=colour, rotate=-90))
    return "".join(o)


def render(path: Path, params: BracketParams, display_key: str) -> None:
    set_display(display_key)
    d = G.DISPLAY
    flat = derive_flat(params)
    geom = build_geometry(params, flat)

    # portrait: the display and its box present their SHORT dimension across the panel
    dw, dh = d.height, d.width
    bw, bh = d.rear_box_h, d.rear_box_w

    sc = 1.05
    over_v = (dh - params.body_h) / 2.0 * sc
    # oy was a fixed 250, which worked for the 23.8 in and pushed the 27 in display's top
    # dimension up underneath the title bar. Derive it from how far the display actually
    # overhangs, so a taller panel moves the whole elevation down instead of colliding.
    TITLE_BOTTOM, DIM_SPACE = 96.0, 46.0
    ox = 300.0
    oy = TITLE_BOTTOM + over_v + DIM_SPACE
    W = 1560.0
    # Trailing pad was 150 on top of the overhang, leaving a third of the canvas blank.
    H = oy + params.body_h * sc + over_v + 72

    cx, cy = params.body_w / 2, params.body_h / 2

    def X(mm): return ox + mm * sc
    def Y(mm): return oy + (params.body_h - mm) * sc   # body-y up

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
           f'viewBox="0 0 {W:.0f} {H:.0f}">',
           f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>',
           f'<rect x="24" y="24" width="{W-48:.0f}" height="{H-48:.0f}" fill="none" '
           f'stroke="#111" stroke-width="1.6"/>',
           f'<rect x="24" y="24" width="{W-48:.0f}" height="46" fill="#111"/>',
           _t(44, 54, "FRIDGE-SIDE DISPLAY MOUNT — ASSEMBLY, PORTRAIT", 17, anchor="start",
              fill="#fff", weight="bold"),
           _t(W-44, 54, f"{display_key} in  ·  {MATERIAL.name} {MATERIAL.thickness_in:.3f} in  ·  "
                        f"REFERENCE ONLY", 11, anchor="end", fill="#bbb")]

    # ---- transparent display panel -----------------------------------------------
    out.append(f'<rect x="{X(cx-dw/2):.1f}" y="{Y(cy+dh/2):.1f}" width="{dw*sc:.1f}" '
               f'height="{dh*sc:.1f}" rx="{d.corner_radius*sc:.1f}" fill="#1a5fb4" '
               f'fill-opacity="0.10" stroke="#1a5fb4" stroke-width="1.6" stroke-dasharray="9 5"/>')
    # active area
    out.append(f'<rect x="{X(cx-d.active_h/2):.1f}" y="{Y(cy+d.active_w/2):.1f}" '
               f'width="{d.active_h*sc:.1f}" height="{d.active_w*sc:.1f}" fill="none" '
               f'stroke="#1a5fb4" stroke-width="0.7" stroke-dasharray="3 3" stroke-opacity="0.6"/>')

    # ---- transparent rear box (the bump-out) --------------------------------------
    out.append(f'<rect x="{X(cx-bw/2):.1f}" y="{Y(cy+bh/2):.1f}" width="{bw*sc:.1f}" '
               f'height="{bh*sc:.1f}" fill="#c0169a" fill-opacity="0.13" stroke="#c0169a" '
               f'stroke-width="1.4" stroke-dasharray="7 4"/>')
    # ---- the plate ----------------------------------------------------------------
    out.append(f'<rect x="{X(0):.1f}" y="{Y(params.body_h):.1f}" width="{params.body_w*sc:.1f}" '
               f'height="{params.body_h*sc:.1f}" rx="{params.outer_fillet*sc:.1f}" '
               f'fill="#8a9199" fill-opacity="0.22" stroke="#333" stroke-width="2"/>')
    for w in (w for w in geom.windows if w.tag.startswith("vent")):
        x0, y0, x1, y1 = w.bounds
        out.append(f'<rect x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{(x1-x0)*sc:.1f}" '
                   f'height="{(y1-y0)*sc:.1f}" rx="{w.r*sc:.1f}" fill="#fff" stroke="#333" '
                   f'stroke-width="1.2"/>')
    co = geom.center_opening
    out.append(f'<circle cx="{X(co.x):.1f}" cy="{Y(co.y):.1f}" r="{co.radius*sc:.1f}" fill="#fff" '
               f'stroke="#333" stroke-width="1.2"/>')
    n_body_fitted = len([h for h in geom.magnet_discs
                         if h.region == "body" and not h.tag.startswith("spare")])
    n_body_opt = len([h for h in geom.magnet_discs
                      if h.region == "body" and h.tag.startswith("spare")])
    for disc in (h for h in geom.magnet_discs
                 if h.region == "body" and not h.tag.startswith("spare")):
        out.append(f'<circle cx="{X(disc.x):.1f}" cy="{Y(disc.y):.1f}" r="{disc.radius*sc:.1f}" '
                   f'fill="{MAGNET_FILL}" fill-opacity="0.22" stroke="{MAGNET_FILL}" stroke-width="1.2"/>')
    for h in geom.holes:
        if h.region != "body":
            continue
        col = {"magnet": MAGNET_FILL, "vesa": "#1a5fb4", "vesa200x100": "#7aa7d9",
               "vesa200x200": "#7aa7d9", "arm_magnet": MAGNET_FILL}.get(h.tag, "#555")
        out.append(f'<circle cx="{X(h.x):.1f}" cy="{Y(h.y):.1f}" r="{max(h.radius*sc,1.6):.1f}" '
                   f'fill="#fff" stroke="{col}" stroke-width="1.3"/>')

    # rear-face opening drawn LAST so the white vent windows cannot hide it — this overlap is
    # the single most important alignment on the drawing
    for sy in (-1, 1):
        oy_mm = cy + sy * d.rear_face_feature_radius
        out.append(f'<circle cx="{X(cx):.1f}" cy="{Y(oy_mm):.1f}" '
                   f'r="{d.rear_face_feature_dia/2*sc:.1f}" fill="#e8a33d" fill-opacity="0.75" '
                   f'stroke="#a8630f" stroke-width="1.6"/>')
    # +34 put this inside the rear-box outline, so the dashed magenta line ran through it.
    # Anchor outboard of the box instead, with a leader back to the opening.
    _lx = X(cx + bw / 2) + 14
    _ly = Y(cy + d.rear_face_feature_radius)
    out.append(f'<line x1="{X(cx) + d.rear_face_feature_dia/2*sc:.1f}" y1="{_ly:.1f}" '
               f'x2="{_lx - 4:.1f}" y2="{_ly:.1f}" stroke="#a8630f" stroke-width="0.8"/>')
    # neck stub, so the plate does not read as a floating rectangle
    out.append(f'<rect x="{X(cx-params.neck_w/2):.1f}" y="{Y(params.body_h)-52:.1f}" '
               f'width="{params.neck_w*sc:.1f}" height="52" fill="#8a9199" fill-opacity="0.22" '
               f'stroke="#333" stroke-width="2"/>')
    out.append(_t(X(cx), Y(params.body_h) - 34, f"NECK {params.neck_w:.0f} wide", 9, fill="#333"))

    # ---- dimensions ---------------------------------------------------------------
    out.append(_dim_h(X(0), X(params.body_w), Y(params.body_h) - 72, f"PLATE {params.body_w:.0f}"))
    out.append(_dim_h(X(cx-dw/2), X(cx+dw/2), Y(cy+dh/2) - 18,
                      f"DISPLAY {dw:.2f}", colour="#1a5fb4"))
    out.append(_dim_h(X(cx-bw/2), X(cx+bw/2), Y(cy+bh/2) - 14, f"REAR BOX {bw:.0f}", colour="#c0169a"))
    out.append(_dim_v(Y(params.body_h), Y(0), X(0) - 34, f"PLATE {params.body_h:.0f}"))
    out.append(_dim_v(Y(cy+dh/2), Y(cy-dh/2), X(0) - 76, f"DISPLAY {dh:.2f}", colour="#1a5fb4"))

    out.append(_dim_v(Y(cy+bh/2), Y(cy-bh/2), X(cx+bw/2) + 26, f"REAR BOX {bh:.0f}", colour="#c0169a"))
    out.append(_dim_h(X(cx-params.vesa/2), X(cx+params.vesa/2), Y(cy) + 4, f"VESA {params.vesa:.0f}",
                      colour="#1a5fb4"))
    out.append(_dim_h(X(params.magnet_inset), X(params.body_w-params.magnet_inset),
                      Y(0) + 40, f"MAGNET SPACING {params.body_w-2*params.magnet_inset:.0f}",
                      colour=MAGNET_FILL))

    # overhang callouts — how far the display covers the plate edge
    over_x = (dw - params.body_w) / 2
    over_y = (dh - params.body_h) / 2
    out.append(_t(X(0) - 6, Y(0) + 92, f"display overhangs plate {over_x:.1f} mm each side",
                  9, anchor="start", fill="#1a5fb4"))
    out.append(_t(X(0) - 6, Y(0) + 105, f"and {over_y:.1f} mm top and bottom",
                  9, anchor="start", fill="#1a5fb4"))

    # LAST thing drawn on this elevation, deliberately. A panel behind text is worthless if
    # anything is painted over it afterwards, and this label is crossed by the rear-box dimension,
    # the plate edge and the display outline. A previous attempt moved it after SOME of the
    # dimensions; the vertical REAR BOX one still followed and still cut through it.
    out.append(f'<rect x="{_lx - 5:.1f}" y="{_ly - 16:.1f}" width="152" height="26" rx="3" '
               f'fill="#fbfbf9" fill-opacity="0.92"/>')
    out.append(_t(_lx, _ly - 6, "Pi fan / GPIO opening", 9, anchor="start", fill="#a8630f",
                  weight="bold"))
    out.append(_t(_lx, _ly + 6, "sits inside the vent window", 8.5, anchor="start",
                  fill="#a8630f"))


    # ---- depth section ------------------------------------------------------------
    sx0 = X(params.body_w) + 230
    ssc = 2.9
    stack = [("FRIDGE PANEL", 6.0, FRIDGE_SIDE, FRIDGE_SIDE_EDGE),
             ("magnet", params.magnet_standoff, MAGNET_FILL, "#1a7a44"),
             ("plate", MATERIAL.thickness, "#8a9199", "#333"),
             ("rear box", d.rear_box_depth, "#c0169a", "#8c1070"),
             ("panel", d.panel_depth, "#1a5fb4", "#12447f")]
    out.append(_t(sx0, oy - 120, "DEPTH SECTION", 13, anchor="start", weight="bold"))
    out.append(_t(sx0, oy - 104, f"total {params.magnet_standoff + MATERIAL.thickness + d.depth:.1f} mm "
                                 f"off the fridge face  ·  {ssc:.1f}x", 9.5, anchor="start", fill="#666"))
    xx = sx0
    for name, t, fill, stroke in stack:
        wpx = t * ssc * 3.2
        out.append(f'<rect x="{xx:.1f}" y="{oy - 70:.1f}" width="{wpx:.1f}" height="150" '
                   f'fill="{fill}" fill-opacity="0.30" stroke="{stroke}" stroke-width="1.3"/>')
        out.append(_t(xx + wpx/2, oy + 96, f"{t:.2f}", 8.5, fill=stroke, weight="bold"))
        out.append(_t(xx + wpx/2, oy - 78, name, 8.5, fill=stroke, rotate=-40))
        xx += wpx
    out.append(_t(sx0, oy + 124, "No spacers: the rear box holds the panel 25 mm off the plate,",
                  9.5, anchor="start", fill="#333"))
    out.append(_t(sx0, oy + 138, "which is what the spacers were originally specified to do.",
                  9.5, anchor="start", fill="#333"))

    # ---- legend -------------------------------------------------------------------
    ly = oy + 190
    out.append(_t(sx0, ly - 16, "LAYERS", 12, anchor="start", weight="bold"))
    for i, (col, op, label) in enumerate([
            ("#333", 0.22, f"PLATE — {MATERIAL.name} {MATERIAL.thickness:.2f} mm"),
            ("#1a5fb4", 0.10, f"DISPLAY {display_key} in — {dw:.1f} x {dh:.1f} mm, transparent"),
            ("#c0169a", 0.13, f"REAR BOX bump-out — {bw:.0f} x {bh:.0f} x {d.rear_box_depth:.0f} mm"),
            ("#e8a33d", 0.55, f"rear-face opening, R{d.rear_face_feature_radius:.0f} from VESA centre"),
            (MAGNET_FILL, 0.22, f"{n_body_fitted} body magnets "
                              f"O{params.magnet_disc_dia:.2f} mm "
                              f"({params.magnet_disc_dia/25.4:.2f} in) — FITTED"),
            ("#c0169a", 0.10, f"{n_body_opt} more body positions cut but NOT fitted"),
            ("#a8630f", 1.0, f"strap slots {params.strap_slot_thickness:.0f} x "
                              f"{params.strap_slot_length:.0f} mm (on the neck, not shown here)")]):
        yy = ly + i * 20
        out.append(f'<rect x="{sx0:.1f}" y="{yy-9:.1f}" width="15" height="11" fill="{col}" '
                   f'fill-opacity="{op}" stroke="{col}" stroke-width="1.1"/>')
        out.append(_t(sx0 + 23, yy, label, 9.5, anchor="start", fill="#333"))

    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    LOG.info("Wrote %s — display %.1f x %.1f, box %.0f x %.0f, overhang %.1f / %.1f mm",
             path, dw, dh, bw, bh, over_x, over_y)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Layered assembly drawing, portrait.")
    ap.add_argument("--display", choices=tuple(DISPLAYS), default="23.8")
    ap.add_argument("--out", type=Path, default=Path("assembly_drawing.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams(), a.display)
    return 0


if __name__ == "__main__":
    sys.exit(main())
