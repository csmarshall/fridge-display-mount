#!/usr/bin/env python3
"""How hard you have to hit it, by direction and by magnet count.

Every figure is a RESISTANCE-TO-ACCIDENT number, not a removal force. They assume a rigid plate
with every magnet releasing together. Real peeling beats them one magnet at a time — lifting a
corner breaks a single magnet at its own derated pull, which is far less than any total here.

The magnets carry NO vertical load: the hook does. What these numbers describe is what it takes
to shift or unseat the plate, which is a different question from whether it holds the screen up.

Positions are the real ones, not a fudge factor on a count:
  PLATE   4 corners, then the 4 mid-sides            (4 -> 8)
  REACH   2 outer rows, then the middle row, then the centroid   (2 -> 7)
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from bracket_common import LOG_LEVELS, configure_logging
import generate_bracket as G
from generate_bracket import BracketParams

LOG = logging.getLogger("force")

N_PER_LBF = 4.4482216
INK, MUTED, RULE = "#14181c", "#6b757e", "#c9d1d8"
OK, WARN = "#0a8f6f", "#b8860b"


def plate_positions(n: int, p: BracketParams) -> list[tuple[float, float]]:
    """Plate magnets, in the order a builder would actually add them, about the plate centre."""
    i = p.magnet_inset
    hw, hh = p.body_w / 2.0 - i, p.body_h / 2.0 - i
    corners = [(-hw, -hh), (hw, -hh), (-hw, hh), (hw, hh)]
    mids = [(-hw, 0.0), (hw, 0.0), (0.0, -hh), (0.0, hh)]
    return (corners + mids)[:n]


def arm_count_rows(n: int) -> int:
    """Arm magnets resist arm lift in tension; only the count matters, not the position."""
    return n


def forces(n_plate: int, n_arm: int, p: BracketParams, rep: dict) -> dict[str, float]:
    pull = rep["magnet_derated_pull_lbf"]
    weight = rep["total_hanging_lbf"]
    mu = p.mu_magnet_face
    fh = p.fridge_height
    body_bottom = fh - p.neck_len - p.body_h          # plate bottom above the floor
    pos = plate_positions(n_plate, p)

    # --- peel: rotation about the fridge's TOP EDGE, plate magnets in tension ----------------
    # Each plate magnet resists with its own lever below the top edge.
    resist_moment = sum(pull * (fh - (body_bottom + p.body_h / 2.0 + dy)) for _, dy in pos)

    def pull_at(z: float) -> float:
        return resist_moment / max(fh - z, 1.0)

    top = p.screen_centre_height + G.DISPLAY.width / 2.0
    mid = p.screen_centre_height
    bot = p.screen_centre_height - G.DISPLAY.width / 2.0

    # --- twist about the vertical spine: only the horizontal offset does work ----------------
    # Half the magnets are in tension for any given sense of rotation.
    twist_moment = sum(pull * abs(dx) for dx, _ in pos) / 2.0
    twist_force = twist_moment / p.torsion_arm

    return {
        "grab the BOTTOM edge and pull": pull_at(bot),
        "grab the MIDDLE and pull": pull_at(mid),
        "grab the TOP edge and pull": pull_at(top),
        "lift the whole thing straight UP": weight + n_plate * pull * mu + n_arm * pull,
        "slide it front-to-back": (n_plate + n_arm) * pull * mu,
        "press the screen edge to twist it off": twist_force,
    }


LADDER = [(4, 2), (4, 4), (5, 4), (6, 4), (6, 6), (7, 6), (8, 6), (8, 7)]


def render(path: Path, p: BracketParams) -> None:
    flat = G.derive_flat(p)
    geom = G.build_geometry(p, flat)
    rep = G.engineering_report(p, geom)
    dirs = list(forces(4, 4, p, rep).keys())

    fitted_plate = len([h for h in geom.holes if h.tag == "magnet"])
    fitted_arm = len([h for h in geom.holes if h.tag == "arm_magnet"])

    colw, rowh = 116.0, 30.0
    x0, y0 = 330.0, 210.0
    W = x0 + colw * len(LADDER) + 60.0
    H = y0 + rowh * (len(dirs) + 1) + 190.0

    BANNER_H = 34.0
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfcfd"/>',
         f'<rect width="{W:.0f}" height="26" fill="#b00020"/>',
         f'<text x="{W/2:.0f}" y="18" font-family="Helvetica,Arial,sans-serif" font-size="12.5" font-weight="bold" text-anchor="middle" fill="#fff">REFERENCE ONLY — resistance-to-accident figures, not a fabrication drawing</text>',
         f'<text x="40" y="52" font-family="Helvetica,Arial,sans-serif" font-size="20" '
         f'font-weight="bold" fill="{INK}">HOW HARD YOU HAVE TO HIT IT</text>',
         f'<text x="40" y="78" font-family="Helvetica,Arial,sans-serif" font-size="12.5" '
         f'fill="{MUTED}">Force to shift or unseat the mount, by direction and magnet count. '
         f'Each cell is lb on top, newtons below.</text>',
         f'<text x="40" y="98" font-family="Helvetica,Arial,sans-serif" font-size="12.5" '
         f'fill="{MUTED}">Every magnet is a {p.magnet_disc_dia:.0f} mm pot magnet derated to '
         f'{rep["magnet_derated_pull_lbf"]:.1f} lb on painted appliance sheet '
         f'({p.magnet_rated_pull_lbf:.0f} lb rated).</text>',
         f'<text x="40" y="122" font-family="Helvetica,Arial,sans-serif" font-size="12.5" '
         f'fill="#b00020" font-weight="bold">These are resistance-to-ACCIDENT numbers, not '
         f'removal forces — peeling one corner beats them all at '
         f'{rep["magnet_derated_pull_lbf"]:.0f} lb.</text>',
         f'<text x="40" y="142" font-family="Helvetica,Arial,sans-serif" font-size="12.5" '
         f'fill="{MUTED}">The magnets carry NO vertical load. The hook does. This table is about '
         f'shifting the plate, not holding the screen up.</text>']

    # header
    for i, (np_, na) in enumerate(LADDER):
        cx = x0 + colw * i + colw / 2.0
        built = (np_ == fitted_plate and na == fitted_arm)
        if built:
            o.append(f'<rect x="{x0 + colw*i:.1f}" y="{y0 - 56:.1f}" width="{colw:.1f}" '
                     # len(dirs)+1 counted a row that is not drawn, so the highlight ran ~90 px
                     # past the last row as an empty green block.
                     f'height="{rowh*len(dirs) + 37:.1f}" fill="#e8f4ee"/>')
        o.append(f'<text x="{cx:.1f}" y="{y0-38:.1f}" font-family="Helvetica,Arial,sans-serif" '
                 f'font-size="15" font-weight="bold" text-anchor="middle" '
                 f'fill="{INK}">{np_ + na}</text>')
        o.append(f'<text x="{cx:.1f}" y="{y0-24:.1f}" font-family="Helvetica,Arial,sans-serif" '
                 f'font-size="10.5" text-anchor="middle" fill="{MUTED}">'
                 f'{np_} plate · {na} reach</text>')
        if built:
            # Emitted LAST, not here. The first row's zebra band is drawn after the header loop
            # and covers y0-9, so this tag was painted over and never appeared in the render.
            as_built_x = cx
    o.append(f'<text x="40" y="{y0-38:.1f}" font-family="Helvetica,Arial,sans-serif" '
             f'font-size="12" font-weight="bold" fill="{INK}">MAGNETS →</text>')

    tables = [forces(np_, na, p, rep) for np_, na in LADDER]
    # y0-9 sat inside row 1 and overprinted its "146 lb" cell. The header band above is full
    # (count, then the plate/reach breakdown), so the only clear space in this column is under
    # the last rule — which still reads as belonging to the column it sits beneath.
    _as_built_tag = (f'<text x="{as_built_x:.1f}" y="{y0 + rowh*len(dirs) + 12:.1f}" '
                     f'font-family="Helvetica,Arial,sans-serif" font-size="9.5" '
                     f'text-anchor="middle" font-weight="bold" fill="{OK}">AS BUILT</text>')
    for r, name in enumerate(dirs):
        ry = y0 + rowh * r
        if r % 2 == 0:
            o.append(f'<rect x="36" y="{ry-19:.1f}" width="{W-76:.1f}" height="{rowh:.1f}" '
                     f'fill="#f2f5f7"/>')
        o.append(f'<text x="44" y="{ry:.1f}" font-family="Helvetica,Arial,sans-serif" '
                 f'font-size="12" fill="{INK}">{name}</text>')
        vals = [t[name] for t in tables]
        for i, v in enumerate(vals):
            cx = x0 + colw * i + colw / 2.0
            grew = "" if i == 0 else f'{(v/vals[0] - 1)*100:+.0f}%'
            o.append(f'<text x="{cx:.1f}" y="{ry-3:.1f}" font-family="Helvetica,Arial,sans-serif" '
                     f'font-size="12.5" text-anchor="middle" font-weight="bold" '
                     f'fill="{INK}">{v:.0f} lb</text>')
            o.append(f'<text x="{cx:.1f}" y="{ry+10:.1f}" '
                     f'font-family="Helvetica,Arial,sans-serif" font-size="10.5" '
                     f'text-anchor="middle" fill="{MUTED}">{v*N_PER_LBF:.0f} N</text>')
        o.append(f'<line x1="36" y1="{ry+11:.1f}" x2="{W-40:.1f}" y2="{ry+11:.1f}" '
                 f'stroke="{RULE}" stroke-width="0.8"/>')

    o.append(_as_built_tag)          # after the zebra bands, so it is actually visible

    fy = y0 + rowh * len(dirs) + 34
    notes = [
        ("Weakest direction is always SLIDING", "it MOVES the mount rather than detaching it — "
         f"the hook does not resist that axis, and mu is only {p.mu_magnet_face:.1f} on bare "
         f"nickel."),
        ("Doubling the magnets does NOT double the resistance",
         "peel and twist depend on WHERE a magnet sits, not just how many there are. The four "
         "corners are already the best positions on the plate; mid-sides sit on a centreline and "
         "contribute nothing to rotation about it."),
        ("A firm touch press is about "
         f"{p.press_force_lbf:.0f} lb ({p.press_force_lbf*N_PER_LBF:.0f} N)",
         "compare that against the twist row — that is the governing everyday load."),
    ]
    for i, (head, body) in enumerate(notes):
        o.append(f'<text x="40" y="{fy + i*36:.1f}" font-family="Helvetica,Arial,sans-serif" '
                 f'font-size="12" font-weight="bold" fill="{INK}">{head}</text>')
        o.append(f'<text x="40" y="{fy + i*36 + 15:.1f}" '
                 f'font-family="Helvetica,Arial,sans-serif" font-size="11" fill="{MUTED}">'
                 f'{body}</text>')
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — %d directions x %d magnet configurations", path, len(dirs), len(LADDER))
    for (np_, na), t in zip(LADDER, tables):
        LOG.debug("%d plate + %d reach: slide %.0f lb, twist %.0f lb",
                  np_, na, t["slide it front-to-back"],
                  t["press the screen edge to twist it off"])


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("force_table.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
