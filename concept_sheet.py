#!/usr/bin/env python3
"""The assembly as decided: two struts, two clamps, two feet, no magnets.

Everything here is derived from ASSEMBLY, which is the single home for the dimensions. If a number
on this sheet disagrees with the brief, this file is the one that was run and the brief is prose.

The point of the sheet is the STACK. Every millimetre between the panel and the display is either
unavoidable (the strut, the plate, the display's own 43 mm) or a design choice (the 9 mm gap), and
the sheet exists so that distinction is visible rather than argued about.

Self-contained: no ezdxf, no generator. It is a drawing, not a deliverable.
"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from bracket_common import (LOG_LEVELS, configure_logging, FRIDGE_SIDE, FRIDGE_SIDE_EDGE,
                            ON_FRIDGE_MUTED, ON_FRIDGE_OK, PAD_EDGE, PAD_FILL)

LOG = logging.getLogger("concept")
IN = 25.4

INK, MUTED, RULE, PAPER = "#14181c", "#6b757e", "#c9d1d8", "#fbfcfd"
OK, BAD, WARN = "#0a8f6f", "#b00020", "#b8860b"
C_STEEL, C_STRUT, C_PLATE = "#4a545e", "#8f9aa4", "#b9c2c9"


@dataclass(frozen=True)
class Assembly:
    """One home for the assembly's dimensions. Change here, the sheet follows."""
    fridge_h: float = 68.625 * IN         # 1743.1 — case, not hinge covers
    fridge_d: float = 24.0 * IN           # 609.6 counter-depth
    strut_len: float = 6 * 12 * IN        # 1828.8
    strut_depth: float = (13 / 16) * IN   # 20.64 low-profile
    strut_width: float = (1 + 5 / 8) * IN
    slot_pitch: float = 2.0 * IN          # 50.8, CONFIRMED off McMaster's table
    strut_spacing: float = 246.0          # = the plate's magnet-hole spacing
    bracket_t: float = 0.119 * IN         # 3.02 clamp and foot
    foam: float = 3.0
    plate_t: float = 0.119 * IN
    plate_h: float = 310.0
    screen_centre: float = 1331.0
    display_h: float = 555.23             # portrait: long side vertical
    rear_box: float = 25.0
    panel_d: float = 18.0
    clear_window: float = 406.0           # measured, rear edge to hinge cover
    hinge_cover: float = 203.0

    @property
    def gap(self) -> float:
        """Panel face to strut back: foam + clamp leg + one foot leg."""
        return self.foam + 2 * self.bracket_t

    @property
    def top_washers(self) -> float:
        """What the top clamp needs behind the strut to stay parallel — the absent foot leg."""
        return self.bracket_t

    @property
    def display_face(self) -> float:
        return self.gap + self.strut_depth + self.plate_t + self.rear_box + self.panel_d

    @property
    def fixed_part(self) -> float:
        """The bit no design decision can change."""
        return self.strut_depth + self.plate_t + self.rear_box + self.panel_d

    @property
    def proud(self) -> float:
        return self.strut_len - self.fridge_h


A = Assembly()


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _t(x, y, s, size=10.0, anchor="middle", fill=INK, weight="normal", rot=0.0):
    tr = f' transform="rotate({rot:.1f} {x:.2f} {y:.2f})"' if rot else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}"{tr}>{_esc(s)}</text>')


def _wrap(text: str, limit: int) -> list[str]:
    out, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if len(t) <= limit:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def _card(x, y, w, h, title, colour=INK) -> list[str]:
    return [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" '
            f'fill="#fff" stroke="{RULE}" stroke-width="1.1"/>',
            _t(x + 20, y + 25, title, 12.5, anchor="start", weight="bold", fill=colour)]


def _elevation(ox, oy, sc, a: Assembly) -> list[str]:
    """Side elevation: fridge left, assembly hanging off its right-hand face."""
    o: list[str] = []
    def X(mm): return ox + mm * sc
    def Y(mm): return oy - mm * sc
    fd = 260.0                                   # only part of the depth is drawn

    o.append(f'<line x1="{X(-120):.1f}" y1="{Y(0):.1f}" x2="{X(fd + 340):.1f}" '
             f'y2="{Y(0):.1f}" stroke="{INK}" stroke-width="2"/>')
    o.append(f'<rect x="{X(0):.1f}" y="{Y(a.fridge_h):.1f}" width="{fd * sc:.1f}" '
             f'height="{(a.fridge_h - 70) * sc:.1f}" fill="{FRIDGE_SIDE}" '
             f'stroke="{FRIDGE_SIDE_EDGE}" stroke-width="1.2"/>')
    o.append(_t(X(fd / 2), Y(a.fridge_h * 0.35), "fridge", 9, fill=ON_FRIDGE_MUTED, rot=-90))

    # exaggerate the thin layers so the stack is legible; the sheet says so
    EX = 4.0
    gap_px = a.gap * sc * EX
    strut_x = X(fd) + gap_px
    strut_w = a.strut_depth * sc * EX

    # the strut, with its slots
    o.append(f'<rect x="{strut_x:.1f}" y="{Y(a.strut_len + 6):.1f}" width="{strut_w:.1f}" '
             f'height="{a.strut_len * sc:.1f}" fill="{C_STRUT}" stroke="{INK}" '
             f'stroke-width="1"/>')
    n = int(a.strut_len / a.slot_pitch)
    for i in range(n):
        sy = 25.4 + i * a.slot_pitch
        o.append(f'<rect x="{strut_x + strut_w * 0.3:.1f}" y="{Y(sy + 14):.1f}" '
                 f'width="{strut_w * 0.4:.1f}" height="{28.6 * sc:.1f}" fill="{INK}" '
                 f'fill-opacity="0.45"/>')

    # foot: vertical leg in the stack, horizontal leg OUTBOARD, strut stands on it
    foot_t = a.bracket_t * sc * EX
    o.append(f'<path d="M{strut_x - foot_t:.1f} {Y(300):.1f} '
             f'L{strut_x - foot_t:.1f} {Y(a.bracket_t):.1f} '
             f'L{strut_x + strut_w + 150 * sc:.1f} {Y(a.bracket_t):.1f} '
             f'L{strut_x + strut_w + 150 * sc:.1f} {Y(0):.1f} '
             f'L{strut_x - foot_t:.1f} {Y(0):.1f} Z" fill="{C_STEEL}" stroke="{INK}" '
             f'stroke-width="1.1"/>')

    # the two clamps: long leg onto the fridge, short leg down/up the side, stud outward
    def clamp(y_corner, flip):
        s = -1 if flip else 1
        leg = 150.0
        short = 44.0
        c = []
        c.append(f'<path d="M{X(fd):.1f} {Y(y_corner):.1f} '
                 f'L{X(fd - leg):.1f} {Y(y_corner):.1f} '
                 f'L{X(fd - leg):.1f} {Y(y_corner + s * a.bracket_t):.1f} '
                 f'L{strut_x - foot_t:.1f} {Y(y_corner + s * a.bracket_t):.1f} '
                 f'L{strut_x - foot_t:.1f} {Y(y_corner - s * short):.1f} '
                 f'L{X(fd):.1f} {Y(y_corner - s * short):.1f} Z" '
                 f'fill="{C_STEEL}" stroke="{INK}" stroke-width="1.1"/>')
        # foam inside the L
        c.append(f'<rect x="{X(fd - leg):.1f}" '
                 f'y="{Y(y_corner + (a.foam if not flip else 0)):.1f}" '
                 f'width="{leg * sc:.1f}" height="{a.foam * sc * EX:.1f}" fill="{PAD_FILL}" '
                 f'stroke="{PAD_EDGE}" stroke-width="0.7"/>')
        # the carriage-bolt stud, horizontal, through the stack
        sy = y_corner - s * short * 0.55
        c.append(f'<rect x="{strut_x - foot_t - 3:.1f}" y="{Y(sy + 5):.1f}" '
                 f'width="{strut_w + foot_t + 14:.1f}" height="{10 * sc:.1f}" '
                 f'fill="{WARN}" stroke="#6d5300" stroke-width="0.9"/>')
        return c

    o += clamp(a.fridge_h, flip=False)
    o += clamp(120.0, flip=True)

    # plate and display, outboard of the strut
    px = strut_x + strut_w
    o.append(f'<rect x="{px:.1f}" y="{Y(a.screen_centre + a.plate_h / 2):.1f}" '
             f'width="{a.plate_t * sc * EX:.1f}" height="{a.plate_h * sc:.1f}" '
             f'fill="{C_PLATE}" stroke="{INK}" stroke-width="1"/>')
    dx = px + a.plate_t * sc * EX
    o.append(f'<rect x="{dx:.1f}" y="{Y(a.screen_centre + a.display_h / 2):.1f}" '
             f'width="{(a.rear_box + a.panel_d) * sc:.1f}" '
             f'height="{a.display_h * sc:.1f}" fill="#101820" stroke="{INK}" stroke-width="1"/>')

    labs = [(Y(a.fridge_h) - 10, "TOP CLAMP — hooks the top, holds 3.8 lb", OK),
            (Y(a.screen_centre + a.display_h / 2) - 6, "display", MUTED),
            (Y(a.screen_centre), "plate — the SAME part, 246 mm centres", INK),
            (Y(760), "2 x 6 ft low-profile strut", INK),
            (Y(160), "LOWER CLAMP — slides up to grip", OK),
            (Y(30), "FOOT — outboard, strut stands on it", OK)]
    lx = dx + (a.rear_box + a.panel_d) * sc + 26
    for ly, _x, _c in labs:
        o.append(f'<line x1="{dx + (a.rear_box + a.panel_d) * sc + 4:.1f}" y1="{ly - 4:.1f}" '
                 f'x2="{lx - 4:.1f}" y2="{ly - 4:.1f}" stroke="{RULE}" stroke-width="0.8"/>')
    for ly, txt, col in labs:
        o.append(_t(lx, ly, txt, 9.0, anchor="start", fill=col, weight="bold"))
    o.append(_t(X(-116), Y(a.fridge_h) - 8, f"thin layers drawn {EX:.0f}x to be visible",
                8.5, anchor="start", fill=MUTED))
    return o


def _stack_detail(ox, oy, w, a: Assembly) -> list[str]:
    """The stud stack in section, at a big scale. This is the sheet's real subject."""
    o: list[str] = []
    layers = [
        ("fridge panel", 8.0, FRIDGE_SIDE, "the appliance"),
        ("foam", a.foam, PAD_FILL, "nothing steel ever touches the fridge"),
        ("clamp leg", a.bracket_t, C_STEEL, "0.119 in"),
        ("foot leg", a.bracket_t, C_STEEL, "0.119 in — at the TOP this is washers instead"),
        ("STRUT", a.strut_depth, C_STRUT, "low-profile: 20.64, not 41.28"),
        ("plate", a.plate_t, C_PLATE, "the same part as the hook design"),
        ("rear box", a.rear_box, "#2b3138", "the display's own"),
        ("panel", a.panel_d, "#101820", "the display's own"),
    ]
    total = sum(t for _, t, _, _ in layers) - 8.0
    sc = (w - 300) / total
    x = ox
    o.append(_t(ox, oy - 26, "THE STACK, PANEL TO SCREEN — true scale", 11.5, anchor="start",
                weight="bold"))
    for i, (name, t, fill, note) in enumerate(layers):
        bw = max(t * sc, 2.0)
        o.append(f'<rect x="{x:.1f}" y="{oy:.1f}" width="{bw:.1f}" height="76" fill="{fill}" '
                 f'stroke="{INK}" stroke-width="0.9"/>')
        ly = oy + 92 + (i % 4) * 15
        o.append(f'<line x1="{x + bw / 2:.1f}" y1="{oy + 78:.1f}" x2="{x + bw / 2:.1f}" '
                 f'y2="{ly - 9:.1f}" stroke="{MUTED}" stroke-width="0.7"/>')
        o.append(_t(x + bw / 2, ly, f"{name} {t:.2f}" if name != "fridge panel" else name,
                    8.5, fill=INK, weight="bold"))
        x += bw
    o.append(f'<line x1="{ox + 8.0 * sc:.1f}" y1="{oy - 12:.1f}" x2="{x:.1f}" '
             f'y2="{oy - 12:.1f}" stroke="{INK}" stroke-width="1.1"/>')
    o.append(_t((ox + 8.0 * sc + x) / 2, oy - 16,
                f"{a.display_face:.1f} mm — and {a.fixed_part:.1f} of it cannot be designed away",
                9.5, weight="bold"))
    return o


def render(path: Path, a: Assembly) -> None:
    W, H = 1300.0, 1212.0
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="{PAPER}"/>',
         f'<rect width="{W:.0f}" height="26" fill="{WARN}"/>',
         _t(W / 2, 18, "CONCEPT — the assembly as decided, nothing built yet", 12.5,
            fill="#fff", weight="bold"),
         _t(40, 58, "TWO STRUTS, TWO CLAMPS, TWO FEET, NO MAGNETS", 19, anchor="start",
            weight="bold"),
         _t(40, 80, "Clamped to the side panel top and bottom, standing on the floor. The clamps "
                    "grip; the floor carries; nothing magnetic is involved.", 12, anchor="start",
            fill=MUTED)]

    o += _card(40, 100, 700, 700, "SIDE ELEVATION")
    o += _elevation(112, 760, 0.335, a)

    o += _card(760, 100, 500, 330, "WHAT HOLDS IT")
    rows = [("Weight", "into the FLOOR through the foot", "154 N", OK),
            ("Tipping", "the two clamps, gripping vertically", "3.8 lb at the top", OK),
            ("Sway", "clamped top and bottom, so it is a BEAM", "0.34 mm", OK),
            ("Sliding", f"captured in the {a.clear_window:.0f} mm clear window", "geometric", OK),
            ("Magnets", "none — the clamp does what they did", "-$191", OK)]
    for i, (k, v, n, c) in enumerate(rows):
        ry = 146 + i * 54
        o.append(_t(784, ry, k, 11.5, anchor="start", weight="bold"))
        o.append(_t(784, ry + 15, v, 10, anchor="start", fill=MUTED))
        o.append(_t(1238, ry, n, 11, anchor="end", fill=c, weight="bold"))

    o += _card(760, 450, 500, 350, "THE TWO PARTS")
    parts = [
        ("A — studded clamp  x2", INK,
         "L bracket. Long leg on the fridge top, or under its base. Short leg down the side. A "
         "CARRIAGE BOLT through a square laser-cut hole is the stud: the square shoulder stops it "
         "spinning, so no welding and no second operation. Foam inside the L. The lower one is "
         "the same part, flipped."),
        ("B — slotted foot  x2", INK,
         "L bracket. Vertical leg carries the elongated slot the stud passes through; horizontal "
         "leg turns OUTBOARD and the strut stands on it, so the strut never touches the floor. "
         "The inboard foot was deleted as redundant."),
    ]
    py = 496
    for head, col, body in parts:
        o.append(_t(784, py, head, 11.5, anchor="start", weight="bold", fill=col))
        py += 17
        for ln in _wrap(body, 62):
            o.append(_t(796, py, ln, 9.8, anchor="start", fill=MUTED))
            py += 13
        py += 12

    o += _card(40, 820, 1220, 200, "")
    o += _stack_detail(72, 856, 700, a)
    o.append(_t(800, 882, "Assembly", 11.5, anchor="start", weight="bold"))
    for i, step in enumerate([
            "1. Stand the struts on the feet; stud through foot slot and strut slot, nut loose.",
            "2. Hook the top clamps over the fridge top; washers behind the strut; nut loose.",
            "3. Slide the lower clamps UP their slots until they engage under the appliance.",
            "4. Lock everything. The struts go into tension and the fridge is gripped."]):
        o.append(_t(812, 900 + i * 14, step, 9.5, anchor="start", fill=MUTED))

    o += _card(40, 1036, 1220, 152, "STILL OPEN — both need a torch under the fridge", BAD)
    for i, q in enumerate([
            "Does a 150-250 mm clamp reach foul anything under there? Compressor, tubing, "
            "insulation, cross-members. It sets how far the lower clamp can go in, and nothing "
            "else can answer it.",
            "Is there a downward-facing rib or lip within reach? If so, HOOKING it beats bearing "
            "on it — a hook has no compliance at all, where foam has a little.",
            f"The gap under the side measured 10-20 mm and the underside is NOT flat, so the "
            f"lower clamp's short leg plus its foam has to live inside that, at its tightest."]):
        for j, ln in enumerate(_wrap(q, 128)):
            o.append(_t(64, 1076 + i * 34 + j * 13, ("- " if j == 0 else "  ") + ln, 10,
                        anchor="start", fill=MUTED))
    o.append("</svg>")
    path.write_text("".join(o), encoding="utf-8")
    LOG.info("Wrote %s — gap %.2f mm, display face %.1f mm (%.1f unavoidable), strut stands "
             "%.0f mm proud of the fridge", path, a.gap, a.display_face, a.fixed_part, a.proud)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("concept_sheet.svg"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    args = ap.parse_args(argv)
    configure_logging(args.log_level)
    render(args.out, A)
    return 0


if __name__ == "__main__":
    sys.exit(main())
