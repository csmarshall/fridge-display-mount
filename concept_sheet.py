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
    # ELEVATOR bolt, 5/16-18. Head 1 3/16 in dia x 7/64 in high, FLAT; square neck 0.33 x 0.19 in.
    # Chosen over a carriage bolt because the head faces the FRIDGE: 2.78 mm hides inside 3 mm of
    # foam where a carriage bolt's 5.08 mm dome stands proud and presses a hard point on the panel.
    bolt_head_d: float = (1 + 3 / 16) * IN
    bolt_head_h: float = (7 / 64) * IN
    bolt_neck_w: float = 0.33 * IN
    bolt_neck_l: float = 0.19 * IN
    bolt_dia: float = 0.3125 * IN
    screen_centre: float = 1331.0
    display_h: float = 555.23             # portrait: long side vertical
    rear_box: float = 25.0
    panel_d: float = 18.0
    clear_window: float = 406.0           # measured, rear edge to hinge cover
    # The side panel's underside sits this far off the floor. MEASURED as 10-20 mm;
    # 15 is the middle. Everything the lower clamp does has to happen inside it.
    base_gap: float = 15.0
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
             f'height="{(a.fridge_h - a.base_gap) * sc:.1f}" fill="{FRIDGE_SIDE}" '
             f'stroke="{FRIDGE_SIDE_EDGE}" stroke-width="1.2"/>')
    o.append(f'<line x1="{X(-40):.1f}" y1="{Y(a.base_gap):.1f}" x2="{X(fd + 30):.1f}" '
             f'y2="{Y(a.base_gap):.1f}" stroke="{BAD}" stroke-width="0.9" '
             f'stroke-dasharray="4 3"/>')
    o.append(_t(X(-44), Y(a.base_gap) + 3, f"underside {a.base_gap:.0f}", 8.0, anchor="end",
                fill=BAD, weight="bold"))
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
    # Corner AT the underside, so the long leg tucks beneath the cabinet and the
    # short leg rises outside it. It was at 120 mm, which drove it through the
    # fridge's base rather than under it.
    o += clamp(a.base_gap, flip=True)

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
    o.append(_t(X(-116), Y(a.fridge_h) - 8, f"thin layers {EX:.0f}x",
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


def _joint_detail(ox, oy, a: Assembly) -> list[str]:
    """The base joint at 4.5x. The elevation cannot resolve this, and it is where the design is.

    CORRECTED: the slots are in the strut's BACK WEB, so the nut goes INSIDE the channel and bears
    on that web. An earlier version ran the bolt clean through the channel and nutted it outside
    the open face — which is both a longer bolt than needed and exactly where the PLATE's channel
    nuts have to live.
    """
    o: list[str] = []
    K, h = 4.5, 148.0
    def W(mm): return mm * K
    o.append(_t(ox, oy - 42, "THE BASE JOINT — 4.5x", 11.5, anchor="start", weight="bold"))
    o.append(_t(ox, oy - 27, "section through one stud, looking along the fridge face", 9,
                anchor="start", fill=MUTED))

    x, xs = ox, {}
    for name, t, fill in (("fridge", 7.0, FRIDGE_SIDE), ("foam", a.foam, "#f8e2a4"),
                          ("clamp", a.bracket_t, C_STEEL), ("foot", a.bracket_t, C_STEEL),
                          ("web", 1.78, C_STRUT)):
        xs[name] = x
        o.append(f'<rect x="{x:.1f}" y="{oy:.1f}" width="{W(t):.1f}" height="{h:.1f}" '
                 f'fill="{fill}" stroke="{INK}" stroke-width="1"/>')
        x += W(t)
    web_end = x
    inner = W(a.strut_depth - 2 * 1.78)
    o.append(f'<rect x="{x:.1f}" y="{oy:.1f}" width="{inner:.1f}" height="{h:.1f}" fill="#fff" '
             f'stroke="{INK}" stroke-width="0.8" stroke-dasharray="3 3"/>')
    x += inner
    # the return lips: the OPEN face, left clear for the plate's channel nuts
    lip = W(1.78)
    for ly in (oy, oy + h - W(9.0)):
        o.append(f'<rect x="{x:.1f}" y="{ly:.1f}" width="{lip:.1f}" height="{W(9.0):.1f}" '
                 f'fill="{C_STRUT}" stroke="{INK}" stroke-width="1"/>')
    # clear of the nut, in the empty part of the void, and short enough to stay inside it
    o.append(_t(x - 15, oy + h / 2 + 26, "OPEN face — plate bolts here", 8.0, fill=MUTED,
                rot=-90))

    cy = oy + h / 2
    hx = xs["foam"] + W(a.foam) - W(a.bolt_head_h)
    o.append(f'<rect x="{hx:.1f}" y="{cy - W(a.bolt_head_d) / 2:.1f}" '
             f'width="{W(a.bolt_head_h):.1f}" height="{W(a.bolt_head_d):.1f}" fill="#8a6a10" '
             f'stroke="#6d5300" stroke-width="1.2"/>')
    o.append(f'<rect x="{xs["clamp"]:.1f}" y="{cy - W(a.bolt_neck_w) / 2:.1f}" '
             f'width="{W(a.bolt_neck_l):.1f}" height="{W(a.bolt_neck_w):.1f}" fill="#a37f14" '
             f'stroke="#6d5300" stroke-width="1.2"/>')
    # shank stops just past the nut, INSIDE the channel
    nut_x = web_end + 4
    nut_w = W((17 / 64) * 25.4)
    o.append(f'<rect x="{xs["clamp"] + W(a.bolt_neck_l):.1f}" y="{cy - W(a.bolt_dia) / 2:.1f}" '
             f'width="{nut_x + nut_w + 10 - xs["clamp"] - W(a.bolt_neck_l):.1f}" '
             f'height="{W(a.bolt_dia):.1f}" fill="#8a6a10" fill-opacity="0.9" '
             f'stroke="#6d5300" stroke-width="1"/>')
    o.append(f'<rect x="{nut_x:.1f}" y="{cy - W(12.7) / 2:.1f}" width="{nut_w:.1f}" '
             f'height="{W(12.7):.1f}" fill="{C_STEEL}" stroke="{INK}" stroke-width="1.2"/>')

    below = [(xs["fridge"] + W(3.5), "fridge", MUTED, 0),
             (xs["foam"] + W(a.foam / 2), f"foam {a.foam:.0f}", PAD_EDGE, 1),
             (xs["clamp"] + W(a.bracket_t / 2), f"clamp {a.bracket_t:.2f}", INK, 2),
             (xs["foot"] + W(a.bracket_t / 2), f"foot {a.bracket_t:.2f}", INK, 3),
             (xs["web"] + W(0.9), f"strut WEB {1.78:.2f}", INK, 4),
             (nut_x + nut_w / 2, "nut INSIDE the channel", OK, 5)]
    for lx, _t_, _c, row in below:
        o.append(f'<line x1="{lx:.1f}" y1="{oy + h + 2:.1f}" x2="{lx:.1f}" '
                 f'y2="{oy + h + 12 + row * 14:.1f}" stroke="{MUTED}" stroke-width="0.7"/>')
    for lx, txt, col, row in below:
        o.append(_t(lx, oy + h + 22 + row * 14, txt, 8.6, fill=col, weight="bold"))

    nx = ox + W(46)
    o.append(_t(nx, oy + 16, "ELEVATOR bolt, 5/16-18 x 1 in", 10, anchor="start", weight="bold",
                fill=WARN))
    grip = 2 * a.bracket_t + 1.78
    for i, ln in enumerate([
            f"head {a.bolt_head_d:.1f} dia x {a.bolt_head_h:.2f} thick, FLAT — it hides inside",
            f"the {a.foam:.0f} mm foam and never touches the panel. A carriage",
            "bolt's dome would stand 2.08 mm proud of the same foam.",
            "",
            f"The slots are in the strut's BACK WEB, so the bolt only has",
            f"to reach {grip:.2f} mm of material plus a nut — 3/4 in would do,",
            f"1 in is comfortable. The nut sits INSIDE the channel.",
            "",
            f"square neck {a.bolt_neck_w:.2f} across x {a.bolt_neck_l:.2f} long locks in the",
            f"CLAMP's square hole and passes {a.bolt_neck_l - a.bracket_t:.2f} mm beyond, so the",
            f"FOOT slot must clear {a.bolt_neck_w:.2f} mm, not just the shank."]):
        col = BAD if i >= 8 else MUTED
        o.append(_t(nx, oy + 36 + i * 13, ln, 9, anchor="start", fill=col))
    return o


def _base_detail(ox, oy, a: Assembly) -> list[str]:
    """The base at 3.1x, in elevation. The side view puts this whole arrangement inside 3 px."""
    o: list[str] = []
    K, rise, IN_L, OUT_L = 3.1, 40.0, 60.0, 66.0
    t, foam, bg = a.bracket_t, a.foam, a.base_gap
    def X(mm): return ox + (mm + IN_L) * K
    def Y(mm): return oy - mm * K

    o.append(_t(ox, oy - (bg + rise + 20) * K - 26, "THE BASE — 3.1x, in elevation", 11.5,
                anchor="start", weight="bold"))
    o.append(_t(ox, oy - (bg + rise + 20) * K - 12,
                "at side-elevation scale this whole arrangement is 3 px", 9, anchor="start",
                fill=MUTED))
    o.append(f'<line x1="{X(-IN_L):.1f}" y1="{Y(0):.1f}" x2="{X(OUT_L):.1f}" y2="{Y(0):.1f}" '
             f'stroke="{INK}" stroke-width="2"/>')
    o.append(_t(X(-IN_L) + 2, Y(0) + 13, "floor", 8.5, anchor="start", fill=MUTED))

    o.append(f'<rect x="{X(-IN_L):.1f}" y="{Y(bg + rise + 20):.1f}" '
             f'width="{IN_L * K:.1f}" height="{(rise + 20) * K:.1f}" fill="{FRIDGE_SIDE}" '
             f'stroke="{FRIDGE_SIDE_EDGE}" stroke-width="1.2"/>')
    o.append(_t(X(-IN_L / 2), Y(bg + 26), "fridge", 9, fill=ON_FRIDGE_MUTED))
    o.append(f'<line x1="{X(-IN_L):.1f}" y1="{Y(bg):.1f}" x2="{X(OUT_L):.1f}" y2="{Y(bg):.1f}" '
             f'stroke="{BAD}" stroke-width="1" stroke-dasharray="4 3"/>')

    # lower clamp: long leg UNDER the cabinet, short leg rising outside it
    top_leg = bg - foam
    o.append(f'<path d="M{X(foam + t):.1f} {Y(bg + rise):.1f} '
             f'L{X(foam + t):.1f} {Y(top_leg - t):.1f} L{X(-IN_L + 6):.1f} {Y(top_leg - t):.1f} '
             f'L{X(-IN_L + 6):.1f} {Y(top_leg):.1f} L{X(foam):.1f} {Y(top_leg):.1f} '
             f'L{X(foam):.1f} {Y(bg + rise):.1f} Z" fill="{C_STEEL}" stroke="{INK}" '
             f'stroke-width="1.2"/>')
    o.append(f'<rect x="{X(-IN_L + 6):.1f}" y="{Y(bg):.1f}" '
             f'width="{(IN_L - 6 + foam + t) * K:.1f}" height="{foam * K:.1f}" fill="#f8e2a4" '
             f'stroke="{PAD_EDGE}" stroke-width="0.9"/>')
    o.append(f'<rect x="{X(0):.1f}" y="{Y(bg + rise):.1f}" width="{foam * K:.1f}" '
             f'height="{rise * K:.1f}" fill="#f8e2a4" stroke="{PAD_EDGE}" stroke-width="0.9"/>')

    # foot: vertical leg in the stack, horizontal leg outboard on the floor
    o.append(f'<path d="M{X(foam + t):.1f} {Y(bg + rise - 12):.1f} '
             f'L{X(foam + t):.1f} {Y(t):.1f} L{X(OUT_L - 6):.1f} {Y(t):.1f} '
             f'L{X(OUT_L - 6):.1f} {Y(0):.1f} L{X(foam + t):.1f} {Y(0):.1f} '
             f'L{X(foam + 2 * t):.1f} {Y(0):.1f} '
             f'L{X(foam + 2 * t):.1f} {Y(bg + rise - 12):.1f} Z" '
             f'fill="{C_STEEL}" stroke="{INK}" stroke-width="1.2"/>')
    o.append(f'<rect x="{X(foam + 2 * t):.1f}" y="{Y(bg + rise + 20):.1f}" '
             f'width="{a.strut_depth * K:.1f}" height="{(bg + rise + 20 - t) * K:.1f}" '
             f'fill="{C_STRUT}" stroke="{INK}" stroke-width="1.1"/>')

    o.append(_t(X(OUT_L) + 6, Y(bg) + 3, f"underside {bg:.0f}", 8.5, anchor="start", fill=BAD,
                weight="bold"))
    o.append(_t(X(OUT_L) + 6, Y(bg) + 14, "MEASURED 10-20", 7.8, anchor="start", fill=BAD))
    # Below the clamp leg, in the clear run between it and the floor — it was on the dark fridge.
    o.append(_t(X(-IN_L + 6), Y(4.0), "clamp long leg — UNDER the cabinet", 8.4,
                anchor="start", fill=OK, weight="bold"))
    o.append(_t(X(OUT_L) + 6, Y(bg + rise - 20), "clamp short leg", 8.4, anchor="start", fill=INK,
                weight="bold"))
    o.append(_t(X(OUT_L) + 6, Y(bg + rise - 20) + 11, "rises OUTSIDE", 8.4, anchor="start",
                fill=INK))
    o.append(_t(X(OUT_L - 6) + 6, Y(t) - 4, "foot on the floor", 8.4, anchor="start", fill=OK,
                weight="bold"))
    return o


def render(path: Path, a: Assembly) -> None:
    W, H = 1300.0, 1478.0
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

    o += _card(40, 100, 700, 500, "SIDE ELEVATION")
    o += _elevation(112, 566, 0.235, a)

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

    o += _card(760, 450, 500, 300, "THE TWO PARTS")
    o += _card(760, 766, 500, 300, "")
    o += _base_detail(792, 1032, a)
    parts = [
        ("A — studded clamp  x2", INK,
         "L bracket. Long leg on the fridge top, or under its base. Short leg down the side. An "
         "ELEVATOR BOLT through a square laser-cut hole is the stud: a flat 2.78 mm head that "
         "hides inside the foam, and a square shoulder that stops it spinning. No welding, no "
         "second operation. The lower one is the same part, flipped."),
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

    o += _card(40, 616, 700, 320, "")
    o += _joint_detail(76, 688, a)
    o += _card(40, 1086, 1220, 200, "")
    o += _stack_detail(72, 1122, 700, a)
    o.append(_t(800, 1148, "Assembly", 11.5, anchor="start", weight="bold"))
    for i, step in enumerate([
            "1. Stand the struts on the feet; stud through foot slot and strut slot, nut loose.",
            "2. Hook the top clamps over the fridge top; washers behind the strut; nut loose.",
            "3. Slide the lower clamps UP their slots until they engage under the appliance.",
            "4. Lock everything. The struts go into tension and the fridge is gripped."]):
        o.append(_t(812, 1166 + i * 14, step, 9.5, anchor="start", fill=MUTED))

    o += _card(40, 1302, 1220, 152, "STILL OPEN — both need a torch under the fridge", BAD)
    for i, q in enumerate([
            "Does a 150-250 mm clamp reach foul anything under there? Compressor, tubing, "
            "insulation, cross-members. It sets how far the lower clamp can go in, and nothing "
            "else can answer it.",
            "Is there a downward-facing rib or lip within reach? If so, HOOKING it beats bearing "
            "on it — a hook has no compliance at all, where foam has a little.",
            f"The gap under the side measured 10-20 mm and the underside is NOT flat, so the "
            f"lower clamp's short leg plus its foam has to live inside that, at its tightest."]):
        for j, ln in enumerate(_wrap(q, 128)):
            o.append(_t(64, 1342 + i * 34 + j * 13, ("- " if j == 0 else "  ") + ln, 10,
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
