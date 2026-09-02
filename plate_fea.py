#!/usr/bin/env python3
"""Plate finite-element check of the BODY plate, with its real holes, under a touch press.

The generators size the plate with a strip-beam model: a magnet-disc-wide strip cantilevered
from the VESA screw, which is easy, conservative and cannot see the holes. This replaces it
with a Kirchhoff plate solved by finite elements (Morley element, scikit-fem) on a gmsh mesh
of the plate exactly as cut: outline fillets, centre vent, four windows, every hole.

Load case — the governing one from CLAUDE.md 1.2: a 5 lb press at the outer screen edge is a
torsion M = F x torsion_arm about the plate normal through the VESA centre. The display box
delivers it to the plate as a COUPLE at the four VESA screws: +F/2 on the two screws of one
column, -F/2 on the other, F = M / vesa. Everything that holds the plate to the panel is
modelled as PINNED over its footprint:

    magnets   the four fitted magnet discs (phase 1 of the third design; the archived hook)
    struts    the elevator-bolt head footprint at each strut bolt (phase 2)

Reported: plate deflection at each VESA screw, the rotation of the VESA pattern, and the
screen-edge movement that rotation implies (rotation x torsion_arm) — the number the strip
model calls "screen edge", so the two can be compared directly.

What this is NOT: a stress check (the strip SF numbers stand, and are large), a model of the
neck or arm (the body is cut free at the neck junction, which is conservative), or a contact
model of the magnets (pinned, not bonded — no uplift allowed, which is the optimistic side).
Treat the results as "the plate answer", not "the truth".

Reads a params JSON written by generate_bracket.py, so the plate here IS the plate cut.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from bracket_common import LOG_LEVELS, configure_logging

LOG = logging.getLogger("fea")

E_STEEL_MPA = 200_000.0
NU_STEEL = 0.29
N_PER_LBF = 4.4482216
ELEVATOR_HEAD_DIA = (1 + 3 / 16) * 25.4     # McMaster 92670A781 head, the strut-side footprint


@dataclass(frozen=True)
class Case:
    support: str           # "magnets" | "struts"
    thickness_mm: float
    w_screws: tuple[float, ...]   # deflection at the 4 VESA screws, mm (+ toward the panel)
    w_max: float
    rotation_rad: float
    screen_edge_mm: float
    n_elements: int
    support_desc: str


def _mesh_plate(p: dict, msh: Path, size: float) -> None:
    """gmsh: the body plate as cut, with the four VESA screw points embedded as mesh nodes."""
    import gmsh
    prm = p["params"]
    bw, bh = prm["body_w"], prm["body_h"]
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("plate")
    occ = gmsh.model.occ
    plate = occ.addRectangle(0, 0, 0, bw, bh, roundedRadius=prm["outer_fillet"])
    cutters = []
    for w in p["windows"]:
        if w["cy"] > bh:            # strap slots live on the neck and arm, not the body
            continue
        cutters.append(occ.addRectangle(w["cx"] - w["w"] / 2, w["cy"] - w["h"] / 2, 0,
                                        w["w"], w["h"], roundedRadius=w["r"]))
    co = p["center_opening"]
    cutters.append(occ.addDisk(co["x"], co["y"], 0, co["dia"] / 2, co["dia"] / 2))
    for h in p["holes"]:
        if h["y"] > bh:
            continue
        cutters.append(occ.addDisk(h["x"], h["y"], 0, h["dia"] / 2, h["dia"] / 2))
    out, _ = occ.cut([(2, plate)], [(2, c) for c in cutters])
    surf = [tag for dim, tag in out if dim == 2]
    # VESA screws as embedded points, so the load lands on a node that is exactly there.
    pts = [occ.addPoint(x, y, 0, size / 2) for x, y in _vesa_points(p)]
    occ.synchronize()
    gmsh.model.mesh.embed(0, pts, 2, surf[0])
    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", size)
    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", size / 3)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.model.mesh.generate(2)
    gmsh.write(str(msh))
    gmsh.finalize()


def _vesa_points(p: dict) -> list[tuple[float, float]]:
    prm = p["params"]
    cx, cy, hv = prm["body_w"] / 2, prm["body_h"] / 2, prm["vesa"] / 2
    return [(cx + sx * hv, cy + sy * hv) for sx in (-1, 1) for sy in (-1, 1)]


def _supports(p: dict, support: str) -> tuple[list[tuple[float, float, float]], str]:
    """Footprints pinned to the panel: (x, y, radius)."""
    if support == "magnets":
        discs = [(d["x"], d["y"], d["dia"] / 2) for d in p["magnet_discs"] if d["tag"] == "magnet_disc"]
        return discs, f"{len(discs)} fitted magnet discs O{discs[0][2] * 2:.0f}"
    if support == "struts":
        bolts = [(h["x"], h["y"], ELEVATOR_HEAD_DIA / 2) for h in p["holes"] if h["tag"] == "strut_bolt"]
        if not bolts:
            raise SystemExit("this plate has no strut bolts — generate it with --strut-bolts first")
        return bolts, f"{len(bolts)} elevator-bolt heads O{ELEVATOR_HEAD_DIA:.1f}"
    raise ValueError(support)


def solve_case(p: dict, support: str, thickness_mm: float, msh: Path) -> tuple[Case, object, np.ndarray]:
    from skfem import Basis, BilinearForm, ElementTriMorley, MeshTri, asm, condense, solve
    from skfem.helpers import dd, ddot, eye, trace

    m = MeshTri.load(msh)
    # gmsh writes the embedded screw points and the geometry's construction points as vertices;
    # any vertex no triangle uses is a zero row in K and the solve returns NaN. Drop them.
    used = np.unique(m.t)
    remap = -np.ones(m.p.shape[1], dtype=int)
    remap[used] = np.arange(used.size)
    m = MeshTri(m.p[:, used], remap[m.t])
    basis = Basis(m, ElementTriMorley())
    t = thickness_mm

    @BilinearForm
    def stiffness(u, v, w):
        def C(T):
            return E_STEEL_MPA / (1 + NU_STEEL) * (T + NU_STEEL / (1 - NU_STEEL) * eye(trace(T), 2))
        return t ** 3 / 12.0 * ddot(C(dd(u)), dd(v))

    K = asm(stiffness, basis)

    # The torsion couple at the VESA screws. Sign by column: +x column pushed into the panel,
    # -x column pulled away — which column is which does not change any magnitude reported.
    prm = p["params"]
    moment_nmm = prm["press_force_lbf"] * N_PER_LBF * p["engineering"]["torsion_arm_mm"]
    per_screw = moment_nmm / prm["vesa"] / 2.0
    f = np.zeros(basis.N)
    screws = _vesa_points(p)
    screw_nodes = []
    for x, y in screws:
        node = int(np.argmin(np.hypot(m.p[0] - x, m.p[1] - y)))
        screw_nodes.append(node)
        sign = 1.0 if x > prm["body_w"] / 2 else -1.0
        f[basis.nodal_dofs[0, node]] += sign * per_screw

    # Pinned footprints: every vertex inside a support disc has w = 0.
    footprints, desc = _supports(p, support)
    fixed_nodes = np.zeros(m.p.shape[1], dtype=bool)
    for x, y, r in footprints:
        fixed_nodes |= np.hypot(m.p[0] - x, m.p[1] - y) <= r
    D = basis.nodal_dofs[0, fixed_nodes]
    if D.size == 0:
        raise SystemExit(f"no mesh vertices inside the {support} footprints — refine the mesh")

    w = solve(*condense(K, f, D=D))
    w_nodes = w[basis.nodal_dofs[0]]
    w_screws = tuple(float(w_nodes[n]) for n in screw_nodes)
    left = np.mean([ws for ws, (x, _) in zip(w_screws, screws) if x < prm["body_w"] / 2])
    right = np.mean([ws for ws, (x, _) in zip(w_screws, screws) if x > prm["body_w"] / 2])
    rotation = (right - left) / prm["vesa"]
    edge = abs(rotation) * p["engineering"]["torsion_arm_mm"]
    case = Case(support, t, w_screws, float(np.max(np.abs(w_nodes))), float(rotation), float(edge),
                m.t.shape[1], desc)
    return case, m, w_nodes


# --------------------------------------------------------------------------------- drawing
def _colour(v: float) -> str:
    """-1..+1 -> blue..white..red."""
    v = max(-1.0, min(1.0, v))
    if v >= 0:
        r, g, b = 255, int(255 * (1 - v)), int(255 * (1 - v))
    else:
        r, g, b = int(255 * (1 + v)), int(255 * (1 + v)), 255
    return f"rgb({r},{g},{b})"


def render(path: Path, p: dict, panels: list[tuple[Case, object, np.ndarray]], strip: dict) -> None:
    """One panel per case: the deflection field, and the numbers beside it."""
    PAPER = "#f7f8fa"
    prm = p["params"]
    bw, bh = prm["body_w"], prm["body_h"]
    sc = 1.15
    PW, PH = 560, 520
    cols = 2
    rows = math.ceil(len(panels) / cols)
    W, H = 60 + cols * PW, 150 + rows * PH + 120
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<rect width="{W}" height="26" fill="#8a1c1c"/>',
         _t(W / 2, 18, "REFERENCE ONLY — a plate-bending model, not a measurement. Pinned supports, "
                       "no contact, body plate only.", 11.5, fill="#fff", weight="bold"),
         _t(40, 62, "BODY PLATE UNDER A TOUCH PRESS — finite-element plate bending vs the strip model",
            20, anchor="start", weight="bold"),
         _t(40, 86, f"{prm['press_force_lbf']:.0f} lb at the screen edge, {p['engineering']['torsion_arm_mm']:.0f} mm "
                    f"from centre, delivered to the plate as a couple at the four VESA screws. Colour is "
                    f"deflection normal to the panel; red toward it, blue away. Same scale in every panel.",
            11.5, anchor="start", fill="#555")]
    wmax = max(c.w_max for c, _, _ in panels) or 1.0
    for k, (case, m, w) in enumerate(panels):
        px, py = 40 + (k % cols) * PW, 110 + (k // cols) * PH
        o.append(f'<rect x="{px}" y="{py}" width="{PW - 20}" height="{PH - 20}" rx="7" fill="#fff" '
                 f'stroke="#d0d4d8"/>')
        o.append(_t(px + 16, py + 24, f"{case.support.upper()} — {case.thickness_mm / 25.4:.3f} in "
                                        f"({case.thickness_mm:.2f} mm)", 12.5, anchor="start", weight="bold"))
        ox, oy = px + 30, py + 40
        # triangles, coloured by mean vertex deflection
        tri = m.t
        wm = w[tri].mean(axis=0) / wmax
        for i in range(tri.shape[1]):
            pts = " ".join(f"{ox + m.p[0, n] * sc:.1f},{oy + (bh - m.p[1, n]) * sc:.1f}" for n in tri[:, i])
            o.append(f'<polygon points="{pts}" fill="{_colour(float(wm[i]))}" stroke="{_colour(float(wm[i]))}" '
                     f'stroke-width="0.4"/>')
        # supports and screws
        for x, y, r in _supports(p, case.support)[0]:
            o.append(f'<circle cx="{ox + x * sc:.1f}" cy="{oy + (bh - y) * sc:.1f}" r="{r * sc:.1f}" '
                     f'fill="none" stroke="#222" stroke-width="1.2" stroke-dasharray="4 3"/>')
        for (x, y), ws in zip(_vesa_points(p), case.w_screws):
            o.append(f'<circle cx="{ox + x * sc:.1f}" cy="{oy + (bh - y) * sc:.1f}" r="4" fill="#111"/>')
            o.append(_t(ox + x * sc + (12 if x > bw / 2 else -12), oy + (bh - y) * sc + 4,
                        f"{ws:+.3f}", 9, anchor="start" if x > bw / 2 else "end", weight="bold"))
        ty = oy + bh * sc + 24
        s = strip.get(case.support, {}).get(round(case.thickness_mm, 2))
        lines = [f"plate max |w| {case.w_max:.3f} mm · VESA rotation {abs(case.rotation_rad) * 1e3:.2f} mrad",
                 f"screen edge moves {case.screen_edge_mm:.3f} mm"
                 + (f"   (strip model: {s:.3f} mm)" if s is not None else ""),
                 f"pinned on {case.support_desc} · {case.n_elements} elements"]
        for i, ln in enumerate(lines):
            o.append(_t(px + 16, ty + i * 15, ln, 10.2, anchor="start",
                        weight="bold" if i == 1 else "normal", fill="#222" if i < 2 else "#666"))
    for i, ln in enumerate((
            "How to read it: the strip model is a magnet-wide cantilever and cannot see the holes; the "
            "plate model can, and is the more trustworthy of the two.",
            "Both are elastic, small-deflection, no contact. A pinned magnet cannot lift off, so the "
            "pull-away column is optimistic there.",
            "Below 0.2 mm at the screen edge reads as rigid to a finger (thickness_study.py).")):
        o.append(_t(40, H - 84 + i * 16, ln, 10.5, anchor="start", fill="#555"))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s (%d panels)", path, len(panels))


def _t(x, y, s, size, anchor="middle", fill="#111", weight="normal"):
    import html
    svg_escape = html.escape
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">'
            f'{svg_escape(s)}</text>')


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--params", type=Path, default=Path("bracket_params.json"),
                    help="params JSON from generate_bracket.py (the plate as cut)")
    ap.add_argument("--thickness", type=float, nargs="+", default=[0.119, 0.187], metavar="IN")
    ap.add_argument("--support", nargs="+", default=["magnets"], choices=["magnets", "struts"])
    ap.add_argument("--mesh-size", type=float, default=5.0, help="mm; the VESA points are finer")
    ap.add_argument("--out", type=Path, default=Path("plate_fea.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)

    p = json.loads(args.params.read_text(encoding="utf-8"))
    msh = args.out.with_suffix(".msh")
    _mesh_plate(p, msh, args.mesh_size)
    LOG.info("meshed %s at %.1f mm", args.params, args.mesh_size)

    # The strip model's answer for the same case, for the comparison line. Same formula as
    # generate_bracket / thickness_study / hybrid.structural, cantilever from the VESA screw.
    prm, eng = p["params"], p["engineering"]
    strip: dict[str, dict[float, float]] = {"magnets": {}}
    for th in args.thickness:
        t = th * 25.4
        spacing = eng["magnet_spacing_mm"]
        force = eng["torsion_force_per_magnet_lbf"] * N_PER_LBF
        lever = spacing / 2 - prm["vesa"] / 2
        I = prm["magnet_disc_dia"] * t ** 3 / 12
        flex = force * lever ** 3 / (3 * E_STEEL_MPA * I)
        strip["magnets"][round(t, 2)] = flex * eng["torsion_arm_mm"] / (spacing / 2)

    panels = []
    for support in args.support:
        for th in args.thickness:
            case, m, w = solve_case(p, support, th * 25.4, msh)
            panels.append((case, m, w))
            LOG.info("%-8s %.3f in: screws %s mm, max %.3f, rotation %.2f mrad -> screen edge %.3f mm "
                     "(strip %s)", support, th, [f"{x:+.3f}" for x in case.w_screws], case.w_max,
                     abs(case.rotation_rad) * 1e3, case.screen_edge_mm,
                     f"{strip[support][round(th * 25.4, 2)]:.3f}" if support in strip else "n/a")
    render(args.out, p, panels, strip)
    msh.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
