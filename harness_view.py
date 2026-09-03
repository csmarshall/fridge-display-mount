#!/usr/bin/env python3
"""Draw the WHOLE flat pattern for an arbitrary magnet, bypassing the validator.

The point is to see a candidate that the validator refuses, so a human can judge whether the
refusal is meaningful or merely literal. Nothing here writes a cut file.
"""
from __future__ import annotations
import argparse, logging, math, sys
from pathlib import Path
from typing import Sequence
from bracket_common import LOG_LEVELS, configure_logging
import generate_bracket as G
from generate_bracket import BracketParams, MATERIAL, build_geometry, derive_flat

LOG = logging.getLogger("harness")
INK, MUTED, RULE, OK, BAD = "#14181c", "#6b757e", "#c9d1d8", "#0a8f6f", "#b00020"


def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def T(x, y, s, size=10, anchor="middle", fill=INK, weight="normal", rot=0.0):
    tr = f' transform="rotate({rot:.1f} {x:.1f} {y:.1f})"' if rot else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"'
            f'{tr}>{esc(s)}</text>')


def draw(path: Path, p: BracketParams) -> dict:
    flat = derive_flat(p)
    geom = build_geometry(p, flat)
    issues = G.validate(p, geom)
    # Dedupe by code. The validator can raise the same failure once per offending feature, and
    # the panel printed each of them as an identical line ("FAIL hole_window_... short by -2.98")
    # with no way to tell them apart, which read as a rendering bug rather than as two features.
    errs, _seen = [], set()
    for i in issues:
        if i.severity == "ERROR" and i.code not in _seen:
            _seen.add(i.code)
            errs.append(i)
    s = 1.05
    L, Rm, Tp, B = 150.0, 330.0, 120.0, 150.0
    W = flat.width * s + L + Rm
    H = flat.height * s + Tp + B
    def X(v): return L + v * s
    def Y(v): return Tp + (flat.height - v) * s
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}"><rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/>',
         f'<rect x="24" y="20" width="{W-48:.0f}" height="46" fill="{INK}" rx="3"/>',
         T(46, 50, f"FULL FLAT PATTERN — O{p.magnet_disc_dia:.2f} magnets at a "
                   f"{p.magnet_inset-p.magnet_disc_dia/2:.2f} mm edge margin", 16,
           anchor="start", fill="#fff", weight="bold")]
    # outline
    pts = " ".join(f"{X(x):.2f},{Y(y):.2f}" for x, y in geom.outline)
    o.append(f'<polygon points="{pts}" fill="#f4f6f8" stroke="{INK}" stroke-width="1.8"/>')
    o.append(f'<line x1="{X(0):.1f}" y1="{Y(flat.bend_line_y):.1f}" x2="{X(p.body_w):.1f}" '
             f'y2="{Y(flat.bend_line_y):.1f}" stroke="#b00020" stroke-width="1.4" '
             f'stroke-dasharray="10 6"/>')
    o.append(T(X(p.body_w)+8, Y(flat.bend_line_y)+4, "bend", 9.5, anchor="start", fill="#b00020"))
    _region_labels: list[str] = []
    # These sit on the plate's centreline, which is exactly where the strap slots and the centre
    # vent are, so the geometry drew straight through the letters. A panel behind each label makes
    # them legible wherever they land, rather than hunting for a clear spot per region.
    for lbl, yy in (("ARM", (flat.bend_line_y+flat.height)/2), ("NECK", (p.body_h+flat.bend_line_y)/2),
                    ("BODY (the plate)", p.body_h/2)):
        lx, ly = X(p.body_w/2), Y(yy)
        _region_labels.append(f'<rect x="{lx - len(lbl)*3.4 - 6:.1f}" y="{ly - 11:.1f}" '
                 f'width="{len(lbl)*6.8 + 12:.1f}" height="16" rx="3" fill="#fbfcfd" '
                 f'fill-opacity="0.88"/>')
        _region_labels.append(T(lx, ly, lbl, 11, fill=MUTED))
    # features
    co = geom.center_opening
    o.append(f'<circle cx="{X(co.x):.1f}" cy="{Y(co.y):.1f}" r="{co.radius*s:.1f}" fill="#fff" '
             f'stroke="{RULE}" stroke-width="1.2"/>')
    for w in geom.windows:
        x0, y0, x1, y1 = w.bounds
        o.append(f'<rect x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{(x1-x0)*s:.1f}" '
                 f'height="{(y1-y0)*s:.1f}" rx="{w.r*s:.1f}" fill="#fff" stroke="{RULE}" '
                 f'stroke-width="1.1"/>')
    for h in geom.holes:
        if h.tag.endswith("magnet"): continue
        o.append(f'<circle cx="{X(h.x):.1f}" cy="{Y(h.y):.1f}" r="{max(h.radius*s,1.4):.1f}" '
                 f'fill="none" stroke="{RULE}" stroke-width="1"/>')
    for d in geom.magnet_discs:
        o.append(f'<circle cx="{X(d.x):.1f}" cy="{Y(d.y):.1f}" r="{d.radius*s:.1f}" '
                 f'fill="#7d868d" fill-opacity="0.32" stroke="#5b646b" stroke-width="1.5"/>')
        o.append(f'<circle cx="{X(d.x):.1f}" cy="{Y(d.y):.1f}" r="2" fill="{INK}"/>')
    # spacings
    i = p.magnet_inset
    spx, spy = p.body_w-2*i, p.body_h-2*i
    fl = p.min_magnet_spacing
    def dim(x0,x1,y,val,vert=False):
        c = OK if val >= fl else BAD
        if vert:
            o.append(f'<line x1="{y:.1f}" y1="{x0:.1f}" x2="{y:.1f}" y2="{x1:.1f}" stroke="{c}" stroke-width="2"/>')
            for q in (x0,x1): o.append(f'<line x1="{y-6:.1f}" y1="{q:.1f}" x2="{y+6:.1f}" y2="{q:.1f}" stroke="{c}" stroke-width="2"/>')
        else:
            o.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="{c}" stroke-width="2"/>')
            for q in (x0,x1): o.append(f'<line x1="{q:.1f}" y1="{y-6:.1f}" x2="{q:.1f}" y2="{y+6:.1f}" stroke="{c}" stroke-width="2"/>')
    ybar = Y(0)+40
    dim(X(i), X(p.body_w-i), ybar, spx)
    o.append(T((X(i)+X(p.body_w-i))/2, ybar-9, f"X spacing {spx:.2f}  (floor {fl:.0f})", 12,
               fill=OK if spx>=fl else BAD, weight="bold"))
    xbar = X(0)-52
    dim(Y(p.body_h-i), Y(i), xbar, spy, vert=True)
    o.append(T(xbar-10, (Y(i)+Y(p.body_h-i))/2, f"Y spacing {spy:.2f}  (floor {fl:.0f})", 12,
               fill=OK if spy>=fl else BAD, weight="bold", rot=-90))
    # edge margin close-up callout
    mg = i - p.magnet_disc_dia/2
    o.append(f'<line x1="{X(0):.1f}" y1="{Y(i)+0:.1f}" x2="{X(i-p.magnet_disc_dia/2):.1f}" '
             f'y2="{Y(i):.1f}" stroke="{BAD if mg<8 else OK}" stroke-width="2.5"/>')
    # Was at X(0)+14, which is inside the O48 corner disc. Pushed outboard of the plate edge so
    # the callout reads against paper instead of against the magnet it is describing.
    o.append(T(X(0)-14, Y(i)-10, f"{mg:.2f} mm of plate", 10.5, anchor="end",
               fill=BAD if mg<8 else OK, weight="bold"))
    o.append(T(X(0)-14, Y(i)+14, "outside the disc", 9.5, anchor="end", fill=MUTED))
    # Region labels LAST. Drawn inline they were painted over by the features that
    # come after them — the strap slots ran through NECK, and the O90 vent hid BODY
    # completely. A halo cannot help when the geometry is drawn on top of it.
    o.extend(_region_labels)

    # verdict block
    vx = X(flat.width)+40
    o.append(T(vx, Tp+20, "VALIDATOR", 12, anchor="start", weight="bold"))
    # Say it on the SHEET, not just in the page caption. A reviewer had to ask whether the FAIL
    # was the point or a stale parameter set; a drawing that raises that question should answer it.
    o.append(T(vx, Tp+34, "This sheet is SUPPOSED to fail.", 9.5, anchor="start", fill=BAD,
               weight="bold"))
    o.append(T(vx, Tp+46, "It renders a rejected layout so the", 8.5, anchor="start", fill=MUTED))
    o.append(T(vx, Tp+56, "refusal can be judged by eye.", 8.5, anchor="start", fill=MUTED))
    yy = Tp+76
    if errs:
        for e in errs[:4]:
            o.append(T(vx, yy, "FAIL  "+e.code, 11, anchor="start", fill=BAD, weight="bold"))
            short = fl-min(spx,spy)
            o.append(T(vx, yy+14, f"short by {short:.2f} mm — that is {short/fl*100:.2f}% of the floor",
                       9.5, anchor="start", fill=MUTED))
            yy += 36
    else:
        o.append(T(vx, yy, "PASSES", 11, anchor="start", fill=OK, weight="bold"))
    o.append(T(vx, yy+14, f"blank {flat.width:.0f} x {flat.height:.1f} mm", 10, anchor="start", fill=MUTED))
    o.append(T(vx, yy+30, f"magnets {len(geom.magnet_discs)} off O{p.magnet_disc_dia:.2f}", 10,
               anchor="start", fill=MUTED))
    o.append(T(vx, yy+46, f"edge margin {mg:.2f} mm (min allowed {MATERIAL.min_edge_distance:.2f})",
               10, anchor="start", fill=MUTED))
    o.append("</svg>")
    path.write_text("\n".join(o), encoding="utf-8")
    return dict(errs=[e.code for e in errs], spx=spx, spy=spy, margin=mg, blank=(flat.width, flat.height))


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Draw the whole flat pattern for a candidate magnet.")
    ap.add_argument("--od", type=float, default=(1+57/64)*25.4)
    ap.add_argument("--thk", type=float, default=(29/64)*25.4)
    ap.add_argument("--margin", type=float, default=MATERIAL.min_edge_distance)
    ap.add_argument("--pull", type=float, default=175.0, help="rated pull of the DEMO magnet (the O48, so the refusal is the real one)")
    ap.add_argument("--out", type=Path, default=Path("harness_view.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    p = BracketParams(magnet_disc_dia=a.od, magnet_standoff=a.thk, magnet_rated_pull_lbf=a.pull,
                      magnet_hole_dia=8.5, magnet_inset=a.od/2+a.margin,
                      arm_magnet_disc_dia=a.od, arm_magnet_standoff=a.thk,
                      extra_magnet_rows=(), extra_arm_magnet_offsets=())
    d = draw(a.out, p)
    LOG.info("O%.2f at %.2f mm margin: X %.2f, Y %.2f, errors %s",
             a.od, a.margin, d["spx"], d["spy"], d["errs"] or "none")
    LOG.info("Wrote %s", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
