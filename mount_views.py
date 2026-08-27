#!/usr/bin/env python3
"""Front and back of the mount, side by side — what goes on which face.

Neither face is obvious from the flat pattern, because the flat pattern shows CUT geometry and
almost everything that matters here is HARDWARE stuck to one side or the other:

  BACK  (faces the fridge)   magnets, foam strips, bottom pad — everything that touches paint
  FRONT (faces the display)  VESA screws and the magnets' own screw heads

The two are mirror images, so the drawing mirrors the back view. Get that wrong and someone
drills or sticks something onto the wrong face.
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

LOG = logging.getLogger("views")

INK, MUTED, RULE = "#14181c", "#6b757e", "#c9d1d8"
PLATE, FOAM = "#e7ebee", "#c9962a"
MAG, VESA, STRAP = "#c0169a", "#1a5fb4", "#2b3036"


def _t(x, y, s, size=10.0, anchor="middle", fill=INK, weight="normal", rot=0.0):
    tr = f' transform="rotate({rot:.1f} {x:.2f} {y:.2f})"' if rot else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}"{tr}>{s}</text>')


def render(path: Path, p: BracketParams) -> None:
    flat = G.derive_flat(p)
    geom = G.build_geometry(p, flat)
    s = 0.66
    pw, ph = flat.width * s, flat.height * s
    gap = 150.0
    ox, oy = 80.0, 150.0
    W = ox * 2 + pw * 2 + gap + 120.0
    H = oy + ph + 210.0

    def panel(x0: float, mirrored: bool) -> list[str]:
        """One face. `mirrored` flips x so the BACK reads as you'd see it from the fridge."""
        def X(mm):
            return x0 + ((flat.width - mm) if mirrored else mm) * s

        def Y(mm):
            return oy + (flat.height - mm) * s

        out = [f'<path d="M{X(0):.1f},{Y(0):.1f} L{X(flat.width):.1f},{Y(0):.1f} '
               f'L{X(flat.width):.1f},{Y(p.body_h):.1f} '
               f'L{X((p.body_w + p.neck_w)/2):.1f},{Y(p.body_h):.1f} '
               f'L{X((p.body_w + p.neck_w)/2):.1f},{Y(flat.height):.1f} '
               f'L{X((p.body_w - p.neck_w)/2):.1f},{Y(flat.height):.1f} '
               f'L{X((p.body_w - p.neck_w)/2):.1f},{Y(p.body_h):.1f} '
               f'L{X(0):.1f},{Y(p.body_h):.1f} Z" fill="{PLATE}" stroke="{INK}" '
               f'stroke-width="1.5"/>']
        # bend line, so the arm is identifiable on both faces
        out.append(f'<line x1="{X((p.body_w-p.neck_w)/2):.1f}" y1="{Y(flat.bend_line_y):.1f}" '
                   f'x2="{X((p.body_w+p.neck_w)/2):.1f}" y2="{Y(flat.bend_line_y):.1f}" '
                   f'stroke="#b00020" stroke-width="1.3" stroke-dasharray="8 5"/>')
        out.append(_t(X(p.body_w/2), Y(flat.bend_line_y) - 6, "bend", 7.4, fill="#b00020"))

        # Everything CUT appears on both faces — it goes through the plate.
        for w in geom.windows:
            out.append(f'<rect x="{min(X(w.cx-w.w/2), X(w.cx+w.w/2)):.1f}" '
                       f'y="{Y(w.cy + w.h/2):.1f}" width="{w.w*s:.1f}" height="{w.h*s:.1f}" '
                       f'fill="#fff" stroke="{STRAP}" stroke-width="1"/>')
        out.append(f'<circle cx="{X(geom.center_opening.x):.1f}" '
                   f'cy="{Y(geom.center_opening.y):.1f}" '
                   f'r="{geom.center_opening.radius*s:.1f}" fill="#fff" stroke="{INK}" '
                   f'stroke-width="1.2"/>')
        for h in geom.holes:
            if h.tag.startswith("vesa"):
                out.append(f'<circle cx="{X(h.x):.1f}" cy="{Y(h.y):.1f}" '
                           f'r="{max(h.dia/2*s, 2.0):.1f}" fill="#fff" stroke="{VESA}" '
                           f'stroke-width="1.4"/>')
        return out, X, Y

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
           f'viewBox="0 0 {W:.0f} {H:.0f}">',
           f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fbfcfd"/>',
           '<pattern id="fm" width="7" height="7" patternUnits="userSpaceOnUse" '
           'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" '
           f'stroke="{FOAM}" stroke-width="2.4"/></pattern>',
           '<pattern id="om" width="6" height="6" patternUnits="userSpaceOnUse" '
           'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" '
           f'stroke="{MAG}" stroke-width="1.6"/></pattern>',
           '<pattern id="om" width="6" height="6" patternUnits="userSpaceOnUse" '
           'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" '
           f'stroke="{MAG}" stroke-width="1.6"/></pattern>',
           _t(ox, 44, "THE MOUNT, BOTH FACES — what sticks to which side", 17,
              anchor="start", weight="bold"),
           _t(ox, 68, "Shown flat. The two faces are mirror images, so the fridge-side view is "
                      "mirrored — everything that touches paint is on that face.",
              11, anchor="start", fill=MUTED)]

    # FRONT left, BACK right — the order you meet them: you look at the display face first.
    fx0 = ox
    bx = ox + pw + gap

    # ---------------- BACK: faces the fridge -------------------------------------------------
    body, X, Y = panel(bx, mirrored=True)
    out += body
    out.append(_t(bx + pw/2, oy - 34, "BACK — faces the fridge", 13, weight="bold"))
    out.append(_t(bx + pw/2, oy - 18, "magnets · foam · pad", 9.5, fill=MUTED))

    if p.foam_strips:
        chan, strip = p.foam_channel_w, p.foam_strip_w
        cxm = p.body_w / 2.0
        for sx in (cxm - chan/2 - strip, cxm + chan/2):
            out.append(f'<rect x="{min(X(sx), X(sx+strip)):.1f}" '
                       f'y="{Y(flat.bend_line_y):.1f}" width="{strip*s:.1f}" '
                       f'height="{(flat.bend_line_y - p.body_h)*s:.1f}" '
                       f'fill="url(#fm)" stroke="{FOAM}" stroke-width="1" '
                       f'stroke-dasharray="5 3"/>')
        my = (p.body_h + flat.height) / 2
        out.append(_t(X(cxm - chan/2 - strip/2), Y(my), f"PAD", 9, fill="#8a6a10", weight="bold"))
        out.append(_t(X(cxm - chan/2 - strip/2), Y(my) + 12, f"{strip:.0f} mm", 8, fill="#8a6a10"))
        out.append(_t(X(cxm + chan/2 + strip/2), Y(my), f"PAD", 9, fill="#8a6a10", weight="bold"))
        out.append(_t(X(cxm + chan/2 + strip/2), Y(my) + 12, f"{strip:.0f} mm", 8, fill="#8a6a10"))
        # Vertical, but placed in the largest CLEAR RUN between strap-slot pairs rather than
        # straight down the middle — the slots live on this centreline, so a full-length label
        # lies on top of the very features it is describing.
        neck_rows = sorted({round(w.cy, 1) for w in geom.windows if w.region == "neck"})
        sh = next((w.h for w in geom.windows if w.region == "neck"), 0.0)
        edges = ([p.body_h] + [v for y in neck_rows for v in (y - sh/2, y + sh/2)]
                 + [flat.bend_line_y])
        runs = [(edges[i+1] - edges[i], (edges[i] + edges[i+1]) / 2.0)
                for i in range(0, len(edges) - 1, 2)]
        run_len, run_mid = max(runs)
        # Size to fit BOTH the channel width and the run it sits in.
        label = f"{chan:.0f} mm CLEAR"
        fs = min(9.0, chan * s * 0.46, run_len * s / (len(label) * 0.52))
        # Rotation swaps the axes: a SECOND line has to step in X, not Y, or it lands on top of
        # the first. Keep both inside the channel, so step by less than half its width.
        step = min(fs + 1.5, chan * s * 0.34)
        out.append(_t(X(cxm) - step / 2.0, Y(run_mid), label, fs,
                      fill="#4a5560", weight="bold", rot=-90))
        out.append(_t(X(cxm) + step / 2.0, Y(run_mid), "straps feed here", fs * 0.84,
                      fill="#6b757e", rot=-90))

    n_fit = n_spare = 0
    for h in geom.holes:
        if "magnet" not in h.tag:
            continue
        dia = p.arm_magnet_disc_dia if h.region == "arm" else p.magnet_disc_dia
        spare = h.tag.startswith("spare")
        n_spare, n_fit = (n_spare + 1, n_fit) if spare else (n_spare, n_fit + 1)
        fill_a = ('fill="url(#om)" fill-opacity="0.45"' if spare
                  else f'fill="{MAG}" fill-opacity="0.22"')
        dash_a = ' stroke-dasharray="5 4" opacity="0.55"' if spare else ''
        out.append(f'<circle cx="{X(h.x):.1f}" cy="{Y(h.y):.1f}" r="{dia/2*s:.1f}" '
                   f'{fill_a} stroke="{MAG}" stroke-width="1.2"{dash_a}/>')
        # The O8.5 mounting hole underneath — a real cut feature, hidden by the magnet on this
        # face. Dashed so it reads as "there, but behind".
        out.append(f'<circle cx="{X(h.x):.1f}" cy="{Y(h.y):.1f}" r="{h.dia/2*s:.1f}" '
                   f'fill="none" stroke="{INK}" stroke-width="1.1" stroke-dasharray="3 2.5" '
                   f'opacity="0.85"/>')
    out.append(_t(bx + pw/2, oy + ph + 34,
                  f"{n_fit} FITTED (solid) stand {p.magnet_standoff:.1f} mm proud — they set "
                  f"the gap the foam fills", 9.0, fill=MUTED))
    out.append(_t(bx + pw/2, oy + ph + 50,
                  f"{n_spare} HASHED = ADDITIONAL IF NEEDED — holes cut, magnets not bought",
                  9.0, fill="#8c1070", weight="bold"))
    out.append(_t(bx + pw/2, oy + ph + 98,
                  "arm fit order if fitting fewer: FRONT row first (4x the back row against a "
                  "tip lift), then BACK, then MIDDLE", 8.4, fill=MUTED))
    out.append(_t(bx + pw/2, oy + ph + 82,
                  "each mid-side addition covers ~11.5 mm of a vent window — accepted",
                  8.4, fill=MUTED))
    out.append(_t(bx + pw/2, oy + ph + 66,
                  f"ONE pad stock {p.bottom_pad_thickness:.1f} mm ({p.bottom_pad_thickness/25.4:.3f} in) "
                  f"— arm, neck and bottom alike, matched to the magnet",
                  9.0, fill=MUTED))

    # ---------------- FRONT: faces the display -----------------------------------------------
    body, X, Y = panel(fx0, mirrored=False)
    out += body
    out.append(_t(fx0 + pw/2, oy - 34, "FRONT — faces the display", 13, weight="bold"))
    out.append(_t(fx0 + pw/2, oy - 18,
                  "VESA screws · magnet screw heads · magnets ghosted behind", 9.5, fill=MUTED))

    # Every magnet position, dashed, as a GHOST — the point being that from this side you see
    # a screw head and nothing else. The disc lives entirely behind the plate.
    for d in geom.magnet_discs:
        opt = d.tag.startswith("spare")
        gfill = 'fill="url(#om)" fill-opacity="0.30"' if opt else 'fill="none"'
        out.append(f'<circle cx="{X(d.x):.1f}" cy="{Y(d.y):.1f}" r="{d.radius*s:.1f}" '
                   f'{gfill} stroke="{MAG}" stroke-width="1.1" stroke-dasharray="5 4" '
                   f'opacity="{0.45 if opt else 0.6}"/>')
    for h in geom.holes:
        if "magnet" in h.tag:
            # Real cut hole on this face too — nothing covers it from the display side.
            out.append(f'<circle cx="{X(h.x):.1f}" cy="{Y(h.y):.1f}" r="{h.dia/2*s:.1f}" '
                       f'fill="#fff" stroke="{MAG}" stroke-width="1.3"/>')
    spacer_txt = (f"M4 spacers hold the display {p.spacer_len:.0f} mm off the plate"
                  if p.spacer_len else
                  "NO spacers — the display bolts straight to the plate")
    out.append(_t(fx0 + pw/2, oy + ph + 34, spacer_txt, 9.0, fill=MUTED))
    out.append(_t(fx0 + pw/2, oy + ph + 50,
                  "vent windows and the centre opening stay clear on BOTH faces", 9.0, fill=MUTED))
    out.append(_t(fx0 + pw/2, oy + ph + 66,
                  "magnet screw heads land on this face — nothing may sit flat over them",
                  9.0, fill=MUTED))
    out.append(_t(fx0 + pw/2, oy + ph + 82,
                  "dashed = magnet discs BEHIND the plate. None of them shows from this side.",
                  8.6, fill="#8c1070"))

    out.append("</svg>")
    path.write_text("".join(out), encoding="utf-8")
    LOG.info("Wrote %s — foam %.0f mm strips either side of a %.0f mm channel",
             path, p.foam_strip_w, p.foam_channel_w)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("mount_views.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    render(a.out, BracketParams())
    return 0


if __name__ == "__main__":
    sys.exit(main())
