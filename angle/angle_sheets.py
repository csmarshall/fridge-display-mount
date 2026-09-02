#!/usr/bin/env python3
"""Design 4's sheets: the elevation sheet and the drill drawing. Both read angle.Angle and the
generator's D4_params.json, so they cannot disagree with the cut files.

    angle_concept.svg   side and front elevations at true scale, derived numbers, parts, trade-offs
    angle_drill.svg     the three parts with every hole dimensioned from a datum corner — print at
                        100 % for a 1:1 template (the SVG's user unit is 1 mm)
"""
from __future__ import annotations

import argparse
import html
import json
import logging
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bracket_common import LOG_LEVELS, configure_logging   # noqa: E402
from angle import IN, Angle, OUT, report                    # noqa: E402

LOG = logging.getLogger("angle-sheets")
HERE = Path(__file__).resolve().parent
PAPER, INK, MUTED, RULE = "#f7f8fa", "#111", "#5b6166", "#d0d4d8"
FRIDGE, AL, MAG, PAD = "#3a3734", "#9aa4ad", "#c0169a", "#f2c14e"
D4 = "#6b3fa0"


def t(x, y, s, size=10.5, anchor="start", fill=INK, weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}">'
            f'{html.escape(s)}</text>')


def wrap(x, y, text, limit, size=10.2, lead=14.0, fill="#333"):
    words, line, lines = text.split(), "", []
    for w_ in words:
        if len(line) + len(w_) + 1 > limit:
            lines.append(line)
            line = w_
        else:
            line = (line + " " + w_).strip()
    lines.append(line)
    return [t(x, y + i * lead, ln, size, fill=fill) for i, ln in enumerate(lines)], len(lines)


def panel(x, y, w, h, title):
    return [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#fff" stroke="{RULE}"/>',
            t(x + 16, y + 24, title, 12.5, weight="bold")]


# ================================================================================ elevation sheet
def render_concept(path: Path, a: Angle, r: dict, prices: dict) -> None:
    W, H = 1720, 1180
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
         f'<rect width="{W}" height="26" fill="{D4}"/>',
         t(W / 2, 18, "DESIGN 4 — stock aluminium, hand-drilled. Validated by angle/angle.py; three DXF drill "
                      "templates audited. Prices marked ESTIMATE are estimates.", 11.5, "middle", "#fff", "bold"),
         t(40, 62, "DESIGN 4 — THE HOOK IN STOCK ALUMINIUM: clip, two bars, a plate", 21, weight="bold"),
         t(40, 84, "Same load path as the hook (the clip bears on the top; magnets only hold it flat), no custom "
                   "plate, no coating, magnets sized for the duty. Portrait, 23.8 in.", 11.5, fill=MUTED)]

    # ---- side elevation
    o.extend(panel(40, 104, 520, 760, "LOOKING ALONG THE PANEL — side elevation, true scale"))
    sc, base, fx0, fw = 0.36, 840.0, 150.0, 240.0

    def Y(mm):
        return base - mm * sc

    o.append(f'<rect x="{fx0}" y="{Y(a.fridge_h):.1f}" width="{fw * sc:.1f}" height="{(base - Y(a.fridge_h)):.1f}" fill="{FRIDGE}"/>')
    o.append(t(fx0 + fw * sc / 2, base - 40, "FRIDGE", 10, "middle", "#cfd4d8", "bold"))
    o.append(t(fx0 + fw * sc / 2, base - 26, "side panel, continues right", 8.4, "middle", "#9aa1a7"))
    o.append(f'<rect x="{fx0 - a.pad * sc:.1f}" y="{Y(a.fridge_h + a.pad + a.clip_t):.1f}" width="{(a.pad + a.clip_leg) * sc:.1f}" height="{a.clip_t * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8"/>')
    o.append(f'<rect x="{fx0 - (a.pad + a.clip_t) * sc:.1f}" y="{Y(a.fridge_h + a.pad + a.clip_t):.1f}" width="{a.clip_t * sc:.1f}" height="{(a.clip_leg + a.pad) * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8"/>')
    o.append(f'<rect x="{fx0:.1f}" y="{Y(a.fridge_h + a.pad):.1f}" width="{a.clip_leg * sc:.1f}" height="{a.pad * sc:.1f}" fill="{PAD}"/>')
    o.append(f'<rect x="{fx0 - a.pad * sc:.1f}" y="{Y(a.fridge_h):.1f}" width="{a.pad * sc:.1f}" height="{a.clip_leg * sc:.1f}" fill="{PAD}"/>')
    bx = fx0 - (a.pad + a.clip_t + a.bar_t) * sc
    o.append(f'<rect x="{bx:.1f}" y="{Y(a.bar_top):.1f}" width="{a.bar_t * sc:.1f}" height="{a.bar_len * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8"/>')
    for row in a.magnet_rows:
        o.append(f'<rect x="{fx0 - a.magnet_h * sc:.1f}" y="{Y(row + a.magnet_dia / 2):.1f}" width="{a.magnet_h * sc:.1f}" height="{a.magnet_dia * sc:.1f}" fill="{MAG}"/>')
    px = bx - a.plate_t * sc
    o.append(f'<rect x="{px:.1f}" y="{Y(a.plate_top):.1f}" width="{a.plate_t * sc:.1f}" height="{a.plate_h * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8"/>')
    boxx = px - a.rear_box * sc
    o.append(f'<rect x="{boxx:.1f}" y="{Y(a.screen_centre + 130):.1f}" width="{a.rear_box * sc:.1f}" height="{260 * sc:.1f}" fill="#4a5f78"/>')
    o.append(f'<rect x="{boxx - 18 * sc:.1f}" y="{Y(a.screen_centre + a.display_h / 2):.1f}" width="{18 * sc:.1f}" height="{a.display_h * sc:.1f}" fill="#1f3550"/>')
    for mm, lab in ((a.fridge_h, f"fridge top {a.fridge_h:.0f}"), (a.magnet_rows[1], f"upper magnets {a.magnet_rows[1]:.0f}"),
                    (a.screen_centre, f"screen centre {a.screen_centre:.0f}"), (a.magnet_rows[0], f"lower magnets {a.magnet_rows[0]:.0f}"),
                    (a.bar_bottom, f"bar bottom {a.bar_bottom:.0f}")):
        o.append(f'<line x1="{fx0 + fw * sc:.1f}" y1="{Y(mm):.1f}" x2="{fx0 + fw * sc + 24:.1f}" y2="{Y(mm):.1f}" stroke="{MUTED}" stroke-width="0.8"/>')
        o.append(t(fx0 + fw * sc + 28, Y(mm) + 3, lab, 8.8))
    o.append(t(56, base + 18, f"display face {a.display_face:.0f} mm off the panel (8 magnet + 6.35 bar + 4.76 plate + 25 box + 18)", 9.2, fill=MUTED))

    # ---- front view
    o.extend(panel(590, 104, 520, 760, "LOOKING AT THE PANEL — front, true scale"))
    cx = 850.0

    def X(mm):
        return cx + mm * sc

    o.append(f'<rect x="{X(-260):.1f}" y="{Y(a.fridge_h):.1f}" width="{520 * sc:.1f}" height="{(base - Y(a.fridge_h)):.1f}" fill="{FRIDGE}"/>')
    o.append(f'<rect x="{X(-a.clip_len / 2):.1f}" y="{Y(a.fridge_h):.1f}" width="{a.clip_len * sc:.1f}" height="{a.clip_leg * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8"/>')
    for s_ in (-1, 1):
        x0 = X(s_ * a.bar_spacing / 2 - a.bar_w / 2)
        o.append(f'<rect x="{x0:.1f}" y="{Y(a.bar_top):.1f}" width="{a.bar_w * sc:.1f}" height="{a.bar_len * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8" opacity="0.92"/>')
        for row in a.magnet_rows:
            o.append(f'<circle cx="{X(s_ * a.bar_spacing / 2):.1f}" cy="{Y(row):.1f}" r="{a.magnet_dia / 2 * sc:.1f}" fill="{MAG}" fill-opacity="0.55" stroke="{MAG}" stroke-dasharray="3 2"/>')
        for h in a.clip_holes():
            if (h["x"] - a.clip_len / 2) * s_ > 0:
                o.append(f'<circle cx="{X(s_ * a.bar_spacing / 2):.1f}" cy="{Y(a.fridge_h - h["y"]):.1f}" r="2.2" fill="{INK}"/>')
    o.append(f'<rect x="{X(-a.plate_w / 2):.1f}" y="{Y(a.plate_top):.1f}" width="{a.plate_w * sc:.1f}" height="{a.plate_h * sc:.1f}" fill="{AL}" stroke="{INK}" stroke-width="0.8" opacity="0.85"/>')
    for sx in (-1, 1):
        for sy in (-1, 1):
            o.append(f'<circle cx="{X(sx * a.vesa / 2):.1f}" cy="{Y(a.screen_centre + sy * a.vesa / 2):.1f}" r="2.4" fill="none" stroke="#1a5fb4" stroke-width="1.2"/>')
    # the fan opening, so the plate's clearance is visible
    for sy in (-1, 1):
        o.append(f'<circle cx="{X(0):.1f}" cy="{Y(a.screen_centre + sy * a.fan_r):.1f}" r="{a.fan_dia / 2 * sc:.1f}" fill="#e8a33d" fill-opacity="0.5" stroke="#a8630f" stroke-dasharray="3 2"/>')
    o.append(f'<rect x="{X(-a.display_w / 2):.1f}" y="{Y(a.screen_centre + a.display_h / 2):.1f}" width="{a.display_w * sc:.1f}" height="{a.display_h * sc:.1f}" rx="3" fill="none" stroke="{INK}" stroke-width="1.2" stroke-dasharray="7 5"/>')
    labels = [(a.fridge_h, f"CLIP 2 x 2 x 3/16 angle, {a.clip_len / IN:.0f} in", "bold"),
              (a.fridge_h - a.clip_leg + a.clip_overlap / 2, "bar-to-clip bolts, 1/4-20", "normal"),
              (a.screen_centre + a.display_h / 2, "display, 24 in portrait (dashed)", "normal"),
              (a.magnet_rows[1], "O36 magnets, 4, K&J MM-C-36", "bold"),
              (a.screen_centre - a.fan_r, f"Pi fan opening (R{a.fan_r:.0f}), {a.plate_fan_clearance:.1f} mm clear of the plate", "normal"),
              (a.screen_centre, f"PLATE 5 x 3/16 flat bar, {a.plate_w / IN:.0f} in, VESA 100", "bold"),
              (a.bar_bottom, f"bar bottom {a.bar_bottom:.0f}", "normal")]
    for mm, lab, wt in labels:
        o.append(f'<line x1="{X(a.display_w / 2 + 4):.1f}" y1="{Y(mm):.1f}" x2="{X(266):.1f}" y2="{Y(mm):.1f}" stroke="{MUTED}" stroke-width="0.7" stroke-dasharray="3 3"/>')
        o.append(t(X(270), Y(mm) + 3, lab, 8.8, "start", MAG if "magnet" in lab else INK, wt))
    o.append(f'<line x1="{X(-a.bar_spacing / 2):.1f}" y1="{base + 14:.1f}" x2="{X(a.bar_spacing / 2):.1f}" y2="{base + 14:.1f}" stroke="{INK}" stroke-width="1.2"/>')
    o.append(t(cx, base + 30, f"bar / magnet spacing {a.bar_spacing:.0f} (floor 240)", 9.4, "middle", INK, "bold"))

    # ---- numbers, parts, trade-offs
    o.extend(panel(1140, 104, 540, 760, "DERIVED NUMBERS — from angle/angle.py, validated"))
    rows = [
        ("hanging on the clip", f"{a.hanging_lbf:.1f} lb", f"display + {a.hardware_kg:.2f} kg aluminium + magnets"),
        ("bearing on the fridge top", f"{a.bearing_psi:.2f} psi", "2 in x 12 in on 5/16 in foam"),
        ("clip position", f"{a.clip_from_rear:.0f}-{a.clip_from_rear + a.clip_len:.0f} from the rear", f"{a.hinge_margin:.0f} mm to the hinge cover"),
        ("screen rearward of case centre", f"{a.display_bias_rearward:.0f} mm", "the cover forces it; the cover lifts off"),
        ("touch torsion per magnet", f"{a.torsion_per_magnet_lbf:.2f} lb", f"MM-C-36 derated {a.magnet_derated_lbf:.1f} lb: SF {a.magnet_sf_touch:.0f}x"),
        ("peel / 20 lb grab", f"{a.peel_lbf:.2f} lb / SF {a.magnet_sf_grab:.1f}x", "grab is an assumed abuse case"),
        ("bar bending, overturning", f"{a.bar_overturning_psi:.0f} psi, SF {a.bar_overturning_sf:.0f}x", "6061-T6, 35 ksi yield"),
        ("plate bending", f"{a.plate_psi:.0f} psi, SF {r['plate_sf']:.0f}x", "5 in strip, weak axis"),
        ("screen edge under 5 lb", f"{a.bar_touch_flex_mm:.3f} mm", "bar as a beam between its magnets"),
        ("plate vs Pi fan opening", f"{a.plate_fan_clearance:.1f} mm clear", "why the plate is 5 in, not 8"),
        ("standoff = pad", f"{a.magnet_h:.0f} mm / 5/16 in", f"{a.pad - a.magnet_h:+.2f} mm — in the -0.60/+0.30 band"),
    ]
    y = 152
    for k, v, n in rows:
        o.append(t(1156, y, k, 9.8))
        o.append(t(1440, y, v, 10, "end", INK, "bold"))
        o.append(t(1452, y, n, 8.2, fill=MUTED))
        y += 20
    o.append(t(1156, y + 12, "PARTS — prices.py design 4", 12.5, weight="bold"))
    y += 36
    for k, v in prices.items():
        o.append(t(1156, y, k, 9.8, weight="bold"))
        o.append(t(1156, y + 12, v, 8.6, fill=MUTED))
        y += 30
    o.append(t(1156, y + 8, "TRADE-OFFS", 12.5, weight="bold"))
    tos = ("No strut option — the bars are not a strut interface, so the fallback is design 2 whole. The clip "
           f"must live inside the hinge-cover window, which puts the screen {a.display_bias_rearward:.0f} mm behind the case "
           "centre unless the cover is lifted. The top bearing is 2 in wide: fine on foam, but the clip must sit "
           f"square. {sum(len(p['holes']) * p['qty'] for p in a.parts().values())} holes drilled by hand from the "
           "templates. Bare aluminium, no coat.")
    lines, n = wrap(1156, y + 30, tos, 78, 9.6, 13.0)
    o.extend(lines)

    o.append(t(40, H - 260, "WHERE IT SITS AGAINST THE OTHERS", 12.5, weight="bold"))
    cmp_ = [
        "Designs 1 and 3: same hook physics, a custom 310 x 742 plate at $178-197 plus $96-191 of O48 magnets. Design 4 "
        "replaces the plate with stock and the magnets with $39 of MM-C-36, and pays for it in hand work and a screen "
        "that sits rearward of centre.",
        "Design 2: floor-standing, no fridge-top dependency. Design 4 depends on the fridge top like 1 and 3.",
        "If design 3's re-quote comes back well over $178, or the plate is never cut, this is the design that costs least "
        "to try. If the plate IS cut, design 4 is moot — the plate is the thing it exists to avoid.",
    ]
    y = H - 236
    for para in cmp_:
        lines, n = wrap(40, y, para, 175, 10.2, 14.0)
        o.extend(lines)
        y += 14 * n + 10
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


# ================================================================================ drill drawing
def render_drill(path: Path, a: Angle) -> None:
    """Every part 1:1 (user unit = mm) with holes dimensioned from the bottom-left datum corner."""
    parts = a.parts()
    margin, gap = 40.0, 60.0
    widest = max(p["w"] for p in parts.values())
    total_h = sum(p["h"] for p in parts.values()) + gap * (len(parts) + 1) + 120
    W = widest + 2 * margin + 420
    H = total_h + margin
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * 2:.0f}" height="{H * 2:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fff"/>',
         t(margin, 24, "DESIGN 4 — DRILL DRAWING. The viewBox unit is 1 mm: print with the page scaled so the 100 mm bar below measures 100 mm.", 9, weight="bold"),
         t(margin, 38, "Every hole from the bottom-left datum corner of its part. Diameters are drill sizes for the "
                       "hardware named. Verify one dimension with a rule before drilling.", 6.5, fill=MUTED)]
    o.append(f'<line x1="{margin}" y1="52" x2="{margin + 100}" y2="52" stroke="{INK}" stroke-width="0.6"/>')
    o.append(t(margin + 104, 54, "100 mm scale bar", 6, fill=MUTED))
    y = 70.0
    for name, p in parts.items():
        w, h = p["w"], p["h"]
        # part outline, y up: SVG y grows down so map part y -> (y + h - py)
        o.append(f'<rect x="{margin}" y="{y}" width="{w}" height="{h}" fill="#f4f5f7" stroke="{INK}" stroke-width="0.4"/>')
        o.append(t(margin + w + 12, y + 10, f"{name}  x{p['qty']}", 8, weight="bold"))
        o.append(t(margin + w + 12, y + 20, p["stock"], 6.2, fill=MUTED))
        o.append(t(margin + w + 12, y + 30, f"{w:.1f} x {h:.1f} x {p['t']:.2f} mm", 6.2, fill=MUTED))
        # datum marker
        o.append(f'<circle cx="{margin}" cy="{y + h}" r="2" fill="none" stroke="#b00020" stroke-width="0.5"/>')
        o.append(t(margin - 3, y + h + 8, "datum (0,0)", 5.5, "end", "#b00020"))
        ty = y + 40
        for hh in p["holes"]:
            hx, hy = margin + hh["x"], y + h - hh["y"]
            o.append(f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="{hh["dia"] / 2:.2f}" fill="none" stroke="{INK}" stroke-width="0.4"/>')
            o.append(f'<line x1="{hx - 6:.1f}" y1="{hy:.1f}" x2="{hx + 6:.1f}" y2="{hy:.1f}" stroke="{INK}" stroke-width="0.25"/>')
            o.append(f'<line x1="{hx:.1f}" y1="{hy - 6:.1f}" x2="{hx:.1f}" y2="{hy + 6:.1f}" stroke="{INK}" stroke-width="0.25"/>')
            o.append(t(margin + w + 12, ty, f"{hh['tag']:<11} O{hh['dia']:.1f}  x {hh['x']:.2f}  y {hh['y']:.2f}", 6.2))
            ty += 8
        y += h + gap
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s", path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)
    a = Angle()
    js = OUT / "D4_params.json"
    if not js.exists():
        raise SystemExit("run angle/angle.py first — the sheets read its D4_params.json")
    r = json.loads(js.read_text(encoding="utf-8"))["engineering"]
    import prices as PR
    q = PR.quote_angle()
    prices = {}
    for g in q.groups:
        for ln in g.lines:
            pr = ln.price
            prices[f"{ln.qty:g} x {ln.item}"[:52]] = (f"${ln.total:.2f} {pr.source} {pr.date}" if ln.total is not None
                                                      else f"NOT PRICED — {pr.note}")[:70]
    render_concept(HERE / "angle_concept.svg", a, r, prices)
    render_drill(HERE / "angle_drill.svg", a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
