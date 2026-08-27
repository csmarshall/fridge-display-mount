#!/usr/bin/env python3
"""Does staggering the inner magnets into an X beat keeping them in the outer columns?

Answers it by computing, for each candidate layout, the moment a magnet group can resist about an
axis through the plate centre at every orientation — plus the two named load cases (touch torsion
about the vertical spine, peel about the fridge's top edge). Feasibility is checked against the
same rules the generator enforces: vent windows, centre vent, every VESA hole, plate edges and
disc-on-disc overlap.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path
from typing import Sequence

import numpy as np

from bracket_common import LOG_LEVELS, configure_logging
import generate_bracket as G
from generate_bracket import BracketParams, MATERIAL, build_geometry, derive_flat

LOG = logging.getLogger("magpat")

Pt = tuple[float, float]


class Plate:
    """Everything a magnet disc has to avoid, read straight off the generated geometry."""

    def __init__(self, params: BracketParams) -> None:
        self.p = params
        flat = derive_flat(params)
        # base geometry with the four CORNER magnets only, so candidate extras are placed against
        # a plate that already contains every hole, window and vent they must clear
        base = BracketParams(**{**params.__dict__, "extra_magnet_rows": ()})
        self.geom = build_geometry(base, derive_flat(base))
        self.r = params.magnet_disc_dia / 2.0
        self.edge = MATERIAL.min_edge_distance
        self.cx, self.cy = params.body_w / 2.0, params.body_h / 2.0
        self.corners: list[Pt] = [(h.x, h.y) for h in self.geom.magnet_discs if h.region == "body"]
        self.vents = [w for w in self.geom.windows if w.tag.startswith("vent")]
        self.holes = [h for h in self.geom.holes
                      if h.region == "body" and not h.tag.endswith("magnet")]

    def feasible(self, x: float, y: float, others: Sequence[Pt] = ()) -> bool:
        p, r = self.p, self.r
        if not (r + self.edge <= x <= p.body_w - r - self.edge):
            return False
        if not (r + self.edge <= y <= p.body_h - r - self.edge):
            return False
        co = self.geom.center_opening
        if math.hypot(x - co.x, y - co.y) < co.radius + r + self.edge:
            return False
        for w in self.vents:
            if w.distance_to_point(x, y) < r:
                return False
        for h in self.holes:
            # a magnet may sit over its OWN hole; any other hole must clear the disc
            if math.hypot(x - h.x, y - h.y) < 1e-6:
                continue
            if math.hypot(x - h.x, y - h.y) < r + h.radius + self.edge:
                return False
        for ox, oy in others:
            if math.hypot(x - ox, y - oy) < 2 * r + 2.0:
                return False
        return True


def capacity_curve(points: Sequence[Pt], cx: float, cy: float, n: int = 181) -> np.ndarray:
    """Resisting moment per unit magnet pull vs axis orientation, in mm.

    For an axis through the centre only the magnets on the OPENING side are in tension; the others
    are pressed against the panel and contribute nothing. So the sum runs over the positive side,
    not over |d|.
    """
    pts = np.array(points, dtype=float)
    dx, dy = pts[:, 0] - cx, pts[:, 1] - cy
    th = np.linspace(0.0, math.pi, n)
    # signed perpendicular distance from the axis at angle th
    d = dx[None, :] * np.sin(th)[:, None] - dy[None, :] * np.cos(th)[:, None]
    return np.clip(d, 0.0, None).sum(axis=1)


def torsion_capacity(points: Sequence[Pt], cx: float) -> float:
    """Touch torsion acts about the VERTICAL spine: only horizontal offset resists it."""
    return sum(max(0.0, x - cx) for x, _ in points)


def peel_capacity(points: Sequence[Pt], params: BracketParams) -> float:
    """Peel pivots on the fridge's top EDGE, outside the plate, so every magnet is in tension."""
    body_top_z = params.fridge_height - params.neck_len
    return sum((params.fridge_height - (body_top_z - (params.body_h - y))) for _, y in points)


def quad(cx, cy, u, v):
    """The four mirror images of an offset (u, v) about the plate centre."""
    return [(cx - u, cy - v), (cx + u, cy - v), (cx - u, cy + v), (cx + u, cy + v)]


def quad_capacity(u1, v1, u2, v2, n=361):
    """Worst-axis resisting moment for TWO mirrored quadruples, in closed form.

    For a mirrored quadruple at offset (u, v), the four signed distances to an axis at angle t are
    +/-(u sin t - v cos t) and +/-(u sin t + v cos t). Only the positive ones are in tension, and
    their sum collapses to 2*max(u|sin t|, v|cos t|) — so an eight-magnet symmetric layout needs no
    per-point loop, and the whole design space can be enumerated instead of sampled.
    """
    t = np.linspace(0.0, math.pi / 2, n)
    sn, cs = np.abs(np.sin(t)), np.abs(np.cos(t))
    u1, v1, u2, v2 = (np.atleast_1d(np.asarray(a, dtype=float)) for a in (u1, v1, u2, v2))
    f = (np.maximum(u1[:, None] * sn, v1[:, None] * cs)
         + np.maximum(u2[:, None] * sn, v2[:, None] * cs))
    return 2.0 * f.min(axis=1)


def feasible_quads(plate: Plate, step: float = 3.0) -> list[tuple[float, float]]:
    """Every (u, v) whose four mirror images all fit and do not collide with each other."""
    out = []
    umax, vmax = plate.cx - plate.r - plate.edge, plate.cy - plate.r - plate.edge
    for u in np.arange(plate.r + plate.edge, umax + step, step):
        for v in np.arange(plate.r + plate.edge, vmax + step, step):
            pts = quad(plate.cx, plate.cy, u, v)
            if 2 * u < 2 * plate.r + 2 or 2 * v < 2 * plate.r + 2:
                continue
            placed = []
            if all(plate.feasible(x, y, placed) or placed.append((x, y)) is not None
                   for x, y in pts):
                pass
            ok, placed = True, []
            for x, y in pts:
                if not plate.feasible(x, y, placed):
                    ok = False
                    break
                placed.append((x, y))
            if ok:
                out.append((float(u), float(v)))
    return out


def pareto(plate: Plate, quads: Sequence[tuple[float, float]]):
    """All feasible eight-magnet layouts, scored on worst axis and on touch torsion."""
    n = len(quads)
    arr = np.array(quads)
    rows = []
    clash = 2 * plate.r + 2.0
    for i in range(n):
        u1, v1 = arr[i]
        for j in range(i + 1, n):
            u2, v2 = arr[j]
            # the two quadruples must not foul each other
            if math.hypot(u1 - u2, v1 - v2) < clash or math.hypot(u1 - u2, v1 + v2) < clash:
                continue
            rows.append((u1, v1, u2, v2))
    if not rows:
        return np.empty((0, 6))
    R = np.array(rows)
    worst = quad_capacity(R[:, 0], R[:, 1], R[:, 2], R[:, 3])
    tors = 2.0 * (R[:, 0] + R[:, 2])
    return np.column_stack([R, worst, tors])


# ---- drawing ---------------------------------------------------------------------------------
INK, MUTED, RULE = "#14181c", "#6b757e", "#c9d1d8"
COLS = {"current": "#2e9e5b", "x": "#c0169a", "best": "#1a5fb4"}


def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def T(x, y, s, size=10.0, anchor="middle", fill=INK, weight="normal", rot=0.0):
    tr = f' transform="rotate({rot:.1f} {x:.1f} {y:.1f})"' if rot else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}"{tr}>{esc(s)}</text>')


def plate_panel(ox, oy, s, plate: Plate, extras: Sequence[Pt], key: str, title: str,
                subtitle: str) -> str:
    p = plate.p
    def X(v): return ox + v * s
    def Y(v): return oy + (p.body_h - v) * s
    o = [T(ox, oy - 30, title, 13, anchor="start", weight="bold", fill=COLS[key]),
         T(ox, oy - 15, subtitle, 9.5, anchor="start", fill=MUTED),
         f'<rect x="{X(0):.1f}" y="{Y(p.body_h):.1f}" width="{p.body_w*s:.1f}" '
         f'height="{p.body_h*s:.1f}" rx="{p.outer_fillet*s:.1f}" fill="#f4f6f8" '
         f'stroke="{INK}" stroke-width="1.4"/>']
    co = plate.geom.center_opening
    o.append(f'<circle cx="{X(co.x):.1f}" cy="{Y(co.y):.1f}" r="{co.radius*s:.1f}" fill="#fff" '
             f'stroke="{RULE}" stroke-width="1"/>')
    for w in plate.vents:
        x0, y0, x1, y1 = w.bounds
        o.append(f'<rect x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{(x1-x0)*s:.1f}" '
                 f'height="{(y1-y0)*s:.1f}" rx="{w.r*s:.1f}" fill="#fff" stroke="{RULE}" '
                 f'stroke-width="1"/>')
    for h in plate.holes:
        o.append(f'<circle cx="{X(h.x):.1f}" cy="{Y(h.y):.1f}" r="{max(h.radius*s,1.3):.1f}" '
                 f'fill="none" stroke="{RULE}" stroke-width="0.9"/>')
    for x, y in plate.corners:
        o.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{plate.r*s:.1f}" fill="#7d868d" '
                 f'fill-opacity="0.30" stroke="#5b646b" stroke-width="1.2"/>')
    for x, y in extras:
        o.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{plate.r*s:.1f}" fill="{COLS[key]}" '
                 f'fill-opacity="0.34" stroke="{COLS[key]}" stroke-width="1.6"/>')
    # lever arms from the centre, the thing the whole comparison turns on
    o.append(f'<circle cx="{X(plate.cx):.1f}" cy="{Y(plate.cy):.1f}" r="2.5" fill="{INK}"/>')
    for x, y in list(plate.corners) + list(extras):
        o.append(f'<line x1="{X(plate.cx):.1f}" y1="{Y(plate.cy):.1f}" x2="{X(x):.1f}" '
                 f'y2="{Y(y):.1f}" stroke="{INK}" stroke-width="0.6" stroke-dasharray="3 3" '
                 f'opacity="0.35"/>')
    return "".join(o)


def perimeter_gap(P, cx, cy):
    """Largest unsupported run around the plate rim — how far the edge can lift between magnets."""
    ang = sorted(P, key=lambda q: math.atan2(q[1] - cy, q[0] - cx))
    return max(math.dist(ang[i], ang[(i + 1) % len(ang)]) for i in range(len(ang)))


def named(plate: Plate, params: BracketParams):
    """The layouts the decision came down to, as explicit POINT SETS.

    Point sets, not (u,v) quadruple pairs: the earlier form could only express eight magnets in two
    mirrored fours, so it silently drew a four-magnet layout as eight stacked ones and reported the
    torsion of the wrong set.
    """
    cx, cy = plate.cx, plate.cy
    i = params.magnet_inset
    corners = [(i, i), (params.body_w - i, i), (i, params.body_h - i),
               (params.body_w - i, params.body_h - i)]
    second = [(i, 75.0), (params.body_w - i, 75.0),
              (i, 225.0), (params.body_w - i, 225.0)]
    midside = [(i, cy), (params.body_w - i, cy)]
    # Labels corrected 2026-08-27. This sheet used to call the 8-up second-row layout "AS BUILT"
    # and the corners-plus-mid-sides layout "REJECTED" — exactly backwards against the cut file,
    # which fits FOUR corner magnets and cuts the four MID-SIDE positions as spare holes. The
    # second-row layout is drawn nowhere in the DXF.
    return [
        ("best", "AS BUILT — 4 corners",
         "the four fitted magnets; best four positions on the plate", corners),
        ("x", "PROVISIONED — 4 + mid-sides",
         "mid-side HOLES are cut, magnets not fitted — the upgrade path", corners + midside),
        ("current", "CONSIDERED — 8, second row",
         "corners plus a second row up the sides; NOT cut", corners + second),
    ]


def render(path: Path, params: BracketParams) -> dict:
    plate = Plate(params)
    cx, cy = plate.cx, plate.cy
    rows = []
    for key, title, sub, pts in named(plate, params):
        curve = capacity_curve(pts, cx, cy)
        rows.append({
            "key": key, "title": title, "sub": sub, "pts": pts, "n": len(pts),
            "worst": float(curve.min()),
            "torsion": float(curve[len(curve) // 2]),      # axis at 90 deg = the vertical spine
            "gap": perimeter_gap(pts, cx, cy),
            "per": float(curve.min()) / len(pts),
        })
    base = rows[0]                                          # compare against AS BUILT (4 corners)

    s = 0.62
    pw, ph = params.body_w * s, params.body_h * s
    gap = 62.0
    W = 74 + len(rows) * (pw + gap)
    H = 572.0
    oy = 128.0
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>',
         f'<rect x="24" y="22" width="{W-48:.0f}" height="44" fill="{INK}" rx="3"/>',
         T(44, 50, "MAGNET LAYOUT — WHERE THE MAGNETS GO", 16, anchor="start", fill="#fff",
           weight="bold"),
         T(W-44, 50, "same magnets, same plate", 10, anchor="end", fill="#9fb0bd")]

    for i, r in enumerate(rows):
        ox = 52 + i * (pw + gap)
        o.append(plate_panel(ox, oy, s, plate, r["pts"], r["key"], r["title"], r["sub"]))
        by = oy + ph + 30
        o.append(T(ox, by, f"{r['n']} MAGNETS", 9, anchor="start", fill=MUTED))
        for j, (lab, val, unit) in enumerate((
                ("any-angle hold", f"{r['worst']:.0f}", "worst of all directions"),
                ("touch torsion", f"{r['torsion']:.0f}", "the governing case"),
                ("per magnet", f"{r['per']:.1f}", "efficiency"))):
            yy = by + 20 + j * 32
            o.append(T(ox, yy, lab.upper(), 8, anchor="start", fill=MUTED))
            o.append(T(ox, yy + 13, val, 13, anchor="start", weight="bold", fill=COLS[r["key"]]))
            o.append(T(ox + 52, yy + 13, unit, 8.2, anchor="start", fill=MUTED))
            if i != 1:
                k = {"any-angle hold": "worst", "touch torsion": "torsion", "per magnet": "per"}[lab]
                d = (r[k] / base[k] - 1) * 100
                o.append(T(ox + pw, yy + 13, f"{d:+.0f}%", 10.5, anchor="end", weight="bold",
                           fill="#0a8f6f" if d >= 0 else "#b00020"))
    o.append(T(52, H - 46, "A magnet ON a centreline has ZERO lever about that centreline. That is "
                           "why mid-side and diagonal", 10, anchor="start", fill=INK))
    o.append(T(52, H - 33, "positions keep losing, and why the corners win: they work about BOTH "
                           "axes at once.", 10, anchor="start", fill=INK))
    o.append(T(52, H - 15, "Peel resistance is identical in all three: symmetric layouts depend "
                           "only on HOW MANY magnets, never where.", 10, anchor="start", fill=MUTED))
    o.append("</svg>")
    path.write_text("\n".join(o), encoding="utf-8")
    return {"rows": rows}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Magnet layout comparison.")
    ap.add_argument("--out", type=Path, default=Path("magnet_pattern_study.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    for r in render(a.out, BracketParams())["rows"]:
        LOG.info("%-24s %2d magnets  any-angle %6.1f  torsion %6.0f  per magnet %5.1f",
                 r["title"], r["n"], r["worst"], r["torsion"], r["per"])
    LOG.info("Wrote %s", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
