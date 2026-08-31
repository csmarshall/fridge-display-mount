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

import math

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
    # SPLIT STRUTS. Two stock McMaster lengths per side with a gap over the display's rear box,
    # so the box's long edges — where the ports and controls most likely are — stay reachable.
    # Both sides split identically, so it does not matter which edge they turn out to be on.
    strut_split: bool = True
    lower_strut_ft: float = 4.0           # stock, $25.48
    upper_strut_ft: float = 1.0           # stock, $6.37
    # DERIVED, not chosen: the upper piece's slots are anchored to ITS OWN lower end, so where
    # that piece sits decides whether a slot lands on the top clamp. 25.4 (one inch) puts a slot
    # EXACTLY on the clamp — at 60 the nearest was 16.2 mm away, outside the half-slot.
    strut_top_proud: float = 25.4
    strut_len: float = 6 * 12 * IN        # 1828.8 — the UNSPLIT length, kept for comparison
    strut_depth: float = (13 / 16) * IN   # 20.64 low-profile
    strut_width: float = (1 + 5 / 8) * IN
    slot_pitch: float = 2.0 * IN          # 50.8, CONFIRMED off McMaster's table
    n_struts: int = 2
    clamped_surfaces: int = 2             # the fridge TOP and the fridge UNDERSIDE. Two planes.
    clamp_spans: bool = True              # ONE clamp reaching across BOTH struts, per surface
    lower_pad_inset: float = 40.0         # bearing pads inboard of each strut on the lower bar
    nested: bool = True                   # box passes BETWEEN the struts instead of behind them
    box_clearance: float = 6.0            # each side, box to strut
    pad_dia: float = 25.0                 # small pads, NOT a full sheet — see pad_t
    n_pads: int = 4
    bracket_t: float = 0.119 * IN         # 3.02 clamp and foot
    foam: float = 3.0
    plate_t: float = 0.119 * IN
    plate_margin: float = 15.0            # beyond the true minimum, all round
    plate_bolt_pitches: int = 2           # strut-bolt rows, in WHOLE slot pitches
    # --- REAR BOX. 260 x 134 is DIMENSIONED on Waveshare's drawing; everything below it is
    # --- SCALED against that 260, because the drawing dimensions none of it.
    box_h_portrait: float = 260.0         # the box's 260 axis runs VERTICAL in portrait
    fan_r: float = 82.0                   # SCALED — fan centre from the VESA/box centre
    fan_dia: float = 30.0                 # SCALED — Pi 5 active cooler is about this
    gpio_r: float = 107.0                 # SCALED — GPIO slot, further out than the fan
    gpio_len: float = 50.0                # SCALED — along the 260 axis
    gpio_wid: float = 44.0                # SCALED — across it; WIDER than the fan
    scale_tol: float = 5.0                # how wrong a raster-scaled figure could be
    notch_w: float = 50.0
    box_w_portrait: float = 134.0         # rear box, SHORT axis — horizontal in portrait
    # ELEVATOR bolt, 5/16-18. Head 1 3/16 in dia x 7/64 in high, FLAT; square neck 0.33 x 0.19 in.
    # Chosen over a carriage bolt because the head faces the FRIDGE: 2.78 mm hides inside 3 mm of
    # foam where a carriage bolt's 5.08 mm dome stands proud and presses a hard point on the panel.
    bolt_head_d: float = (1 + 3 / 16) * IN
    bolt_head_h: float = (7 / 64) * IN
    bolt_neck_w: float = 0.33 * IN
    bolt_neck_l: float = 0.19 * IN
    bolt_dia: float = 0.3125 * IN
    screen_centre: float = 1331.0
    # THE DISPLAY. 23.8 in as specified; the 27 in shares the same rear box, VESA and depth
    # profile, so `--display 27` only changes these two numbers and the mass.
    display_w: float = 324.65             # portrait: SHORT side horizontal (front-to-back)
    display_h: float = 555.23             # portrait: long side vertical
    rear_box: float = 25.0
    panel_d: float = 18.0
    clear_window_measured: float = 406.0  # tape reading 2026-08-27, cross-check only
    # The side panel's underside sits this far off the floor. MEASURED as 10-20 mm;
    # 15 is the middle. Everything the lower clamp does has to happen inside it.
    base_gap: float = 15.0
    # Under the outboard foot. Steel on a wood floor is a bad long-term contact: not because of
    # the pressure, which is under 3 psi, but because laser-cut EDGES line-load an imperfect floor
    # and because this thing sits unmoved for years. Wants GRIP as well as protection — felt would
    # protect but it would also let the assembly slide, which is the one thing it must not do.
    floor_pad: float = 3.0
    cover_margin: float = 20.0            # clamp-to-hinge-cover clearance DELIBERATELY kept back
    hinge_proud: float = 36.5              # covers stand this far above the CASE top (spec sheet)
    hinge_cover: float = 203.0
    # --- the two bent parts. Named here because the elevation, the part drawings and the
    # --- clearance check all need them and must never disagree.
    clamp_leg: float = 150.0              # long leg, lies on the fridge top / under its base
    clamp_short: float = 44.0             # short leg, down the side alongside the strut
    foot_leg: float = 150.0               # horizontal, turns OUTBOARD
    foot_rise: float = 120.0              # vertical leg carrying the elongated slot
    slot_len: float = 28.6                # strut slot, long axis
    n_plates: int = 1
    vesa: float = 100.0                   # VESA 100 on the display's raised rear box
    vesa_hole_dia: float = 4.5            # M4 clearance
    pi_fan_radius: float = 87.5           # Pi 5 fan/GPIO opening, from the dimension drawing
    plate_bolt_dia: float = 8.5           # clearance for the 5/16 strut hardware
    bend_radius: float = 3.02             # ESTIMATE ~1T; replace with SendCutSend's calculator
    k_factor: float = 0.42

    @property
    def n_clamps(self) -> int:
        """How many clamp PARTS. Not the same as how many surfaces are gripped.

        Spanning: one bar per surface, reaching across both struts — 2 parts for 2 surfaces.
        Separate: one clamp per strut per surface — 4 parts for the same 2 surfaces.

        Written down because the parts sheet once said 2 while the design needed 4, conflating
        surfaces gripped with parts that grip them. A wrong quantity on a fabrication drawing is
        the expensive kind of wrong.
        """
        return self.clamped_surfaces if self.clamp_spans else (self.n_struts
                                                               * self.clamped_surfaces)

    @property
    def clamp_outer_half(self) -> float:
        """Half the front-to-back extent of the clamping at one surface. Same either way."""
        return (self.clamp_width / 2.0 if self.clamp_spans
                else self.strut_spacing / 2.0 + self.part_width / 2.0)

    @property
    def n_feet(self) -> int:
        return self.n_struts

    @property
    def plate_edge(self) -> float:
        """Hole centre to plate edge: half the hole plus SendCutSend's 2T rule."""
        return self.plate_bolt_dia / 2.0 + 2.0 * self.bracket_t

    @property
    def plate_w(self) -> float:
        """Across, front-to-back. Set by the STRUT SPACING — never by the display's outline.

        The old 310 square came from the hook design, where the plate had to hide behind the
        display in EITHER orientation. Landscape is impossible on this cabinet, so that reason is
        gone — but the plate barely shrinks, because what actually sets it is where the struts
        are, and they did not move.
        """
        return self.plate_bolt_dx + 2.0 * (self.plate_edge + self.plate_margin)

    @property
    def plate_h(self) -> float:
        """Up-down. Short enough to sit BELOW the Pi opening instead of covering it.

        The tall version existed only to carry vent windows over an opening the plate did not
        need to reach in the first place. Dropping under it removes the windows entirely — the
        cheapest feature is the one not cut.
        """
        h_bolt = self.plate_bolt_dy / 2.0 + self.plate_edge
        h_vesa = self.vesa / 2.0 + self.vesa_hole_dia / 2.0 + 2.0 * self.bracket_t
        return 2.0 * (max(h_bolt, h_vesa) + self.plate_margin)

    @property
    def opening_near_edge(self) -> float:
        """Worst-case nearest approach of the Pi opening to the box centre.

        The FAN is the near feature, not the GPIO slot. Every term here is scaled off a raster,
        so the tolerance is carried explicitly rather than hidden in a rounded number.
        """
        return self.fan_r - self.fan_dia / 2.0 - self.scale_tol

    @property
    def plate_covers_fan_by(self) -> float:
        """How far the plate edge laps over the fan. POSITIVE means the notch is doing real work.

        This was assumed to be negative — the notches were described as idle insurance against a
        radius that might be wrong. Reading the fan position off Waveshare's own drawing says
        otherwise: the plate does overlap it, and the notch is what uncovers it.
        """
        return self.plate_h / 2.0 - (self.fan_r - self.fan_dia / 2.0)

    @property
    def notch_depth(self) -> float:
        """How far the edge notches cut in. Derived from the uncertainty, not chosen.

        If the opening really is where the drawing suggests, the plate edge already clears it and
        these do nothing. If it sits at the near end of its tolerance, they vent it anyway. An
        open notch costs a fraction of the cut length an enclosed window does.
        """
        return max(0.0, self.plate_h / 2.0 - self.opening_near_edge)

    @property
    def n_notches(self) -> int:
        return 2

    @property
    def bolt_clear_of_box(self) -> float:
        """Bolt head to the edge of the display's rear box. Must stay positive.

        The heads sit on the display side of the plate, so anything under the Pi bump-out would
        foul it. They clear because the strut spacing is far wider than the box — not by luck of
        the bolt positions.
        """
        return self.plate_bolt_dx / 2.0 - self.box_w_portrait / 2.0

    @property
    def strut_spacing(self) -> float:
        """Front-to-back centres of the two struts. DERIVED, and by different rules per layout.

        246 used to be hardcoded here, inherited verbatim from the magnet plate's MAGNET-HOLE
        spacing and never re-derived once the magnets went away.

        NESTED: the rear box has to pass BETWEEN the struts, so the box width plus a strut width
        plus clearance IS the spacing. Nothing else is free to choose.

        STACKED: bounded below by the bolts clearing the box (~155) and above by plate width;
        touch-press wobble at the screen edge grows as 1/spacing^2, and 160 keeps it under a
        millimetre.
        """
        if self.nested:
            return self.box_w_portrait + self.strut_width + 2.0 * self.box_clearance
        return 160.0

    @property
    def pad_t(self) -> float:
        """Pad thickness behind the plate. Fills the space that is actually left, no more.

        These are small pads at the plate corners, not a covering sheet: the plate is not pressed
        against the fridge by anything, so there is nothing here to compress. Their only job is to
        stop bare steel meeting paint if the plate ever flexes.
        """
        return self.gap - self.plate_t

    @property
    def lower_strut_len(self) -> float:
        return self.lower_strut_ft * 12.0 * IN

    @property
    def upper_strut_len(self) -> float:
        return self.upper_strut_ft * 12.0 * IN

    @property
    def strut_top(self) -> float:
        return self.fridge_h + self.strut_top_proud

    @property
    def upper_strut_lo(self) -> float:
        return self.strut_top - self.upper_strut_len

    @property
    def box_lo(self) -> float:
        return self.screen_centre - self.box_h_portrait / 2.0

    @property
    def box_hi(self) -> float:
        return self.screen_centre + self.box_h_portrait / 2.0

    @property
    def edge_open(self) -> float:
        """How much of the box's long edge the gap actually exposes."""
        return (min(self.upper_strut_lo, self.box_hi)
                - max(self.lower_strut_len, self.box_lo))

    def _slots_between(self, lo: float, hi: float, origin: float) -> list[float]:
        """Slot centres on a piece whose lower end is at `origin`, within [lo, hi]."""
        out, n = [], 0
        while True:
            z = origin + 25.4 + n * self.slot_pitch
            if z > hi:
                return out
            if z >= lo:
                out.append(z)
            n += 1

    @property
    def plate_bolt_lo(self) -> float:
        """Highest slot on the LOWER piece that is still below the box. A real slot, not a wish."""
        cand = self._slots_between(0.0, self.lower_strut_len - 11.11, 0.0)
        return max(z for z in cand if z < self.box_lo + 30.0)

    @property
    def plate_bolt_hi(self) -> float:
        """Lowest slot on the UPPER piece above the box."""
        cand = self._slots_between(self.upper_strut_lo, self.strut_top - 11.11,
                                   self.upper_strut_lo)
        return min(z for z in cand if z > self.box_hi - 30.0)

    @property
    def plate_centre(self) -> float:
        """The plate is ASYMMETRIC about the VESA: its bolts are set by two different slot grids."""
        return (self.plate_bolt_hi + self.plate_bolt_lo) / 2.0

    @property
    def vesa_offset_in_plate(self) -> float:
        return self.screen_centre - self.plate_centre

    @property
    def fan_near(self) -> float:
        return self.fan_r - self.fan_dia / 2.0 - self.scale_tol

    @property
    def gpio_far(self) -> float:
        return self.gpio_r + 6.0 + self.scale_tol

    @property
    def vent_r(self) -> float:
        """One window per side covering fan AND GPIO, so it is centred between them."""
        return (self.fan_near + self.gpio_far) / 2.0

    @property
    def vent_len(self) -> float:
        return self.gpio_far - self.fan_near

    @property
    def vent_wid(self) -> float:
        """Across the window. The GPIO slot is WIDER than the fan, so the fan does not set this.

        Sizing the window to the fan alone left the GPIO slot poking out either side of it —
        caught by drawing both features rather than trusting the one number.
        """
        return max(self.fan_dia, self.gpio_wid) + 2.0 * self.scale_tol

    @property
    def n_vents(self) -> int:
        return 2

    @property
    def plate_bolt_dy(self) -> float:
        """Vertical spacing of the plate-to-strut bolts. A WHOLE NUMBER OF SLOT PITCHES.

        Three pitches, not a round 150, so both bolt rows sit identically in their slots. Any
        other spacing puts one row near the middle of a slot and the other near its end, and the
        plate then only mounts at certain heights.
        """
        if self.strut_split:
            return self.plate_bolt_hi - self.plate_bolt_lo
        return self.plate_bolt_pitches * self.slot_pitch

    @property
    def plate_bolt_dx(self) -> float:
        return self.strut_spacing

    @property
    def part_width(self) -> float:
        """Across the clamp and the foot, front-to-back. DERIVED, not chosen.

        The floor is set by the horizontal leg, which the strut stands on: it has to be at least
        as wide as the strut plus SendCutSend's hole-to-edge margin of 2T each side. Rounded UP to
        the next 5 mm so the part has a tidy dimension — that rounding is the only judgement in it.

        Width is nearly free here, the same way arm width was on the magnet design: it runs
        front-to-back ALONG the fridge face, so it adds nothing to how far the display stands off
        the panel and nothing to the sheet's bounding box. Only the foot's outboard LEG is in the
        room.
        """
        floor = self.strut_width + 4.0 * self.bracket_t
        return math.ceil(floor / 5.0) * 5.0

    @property
    def clamp_width(self) -> float:
        """Across the clamp. A spanning bar must reach both struts AND carry its own edge margin.

        Tying the two struts into a frame is the only lever that changes rigidity in KIND rather
        than degree: widening the individual parts adds steel that is not tied to anything at its
        far end, and the couple arm stays the strut spacing regardless.
        """
        return self.strut_spacing + self.part_width if self.clamp_spans else self.part_width

    @property
    def foot_width(self) -> float:
        return self.part_width

    @property
    def proud_of_covers(self) -> float:
        """Strut top above the HINGE COVER tops, not just the case. The covers are what you see."""
        return self.strut_len - (self.fridge_h + self.hinge_proud)

    @property
    def clear_window(self) -> float:
        """Rear edge to the hinge cover. DERIVED; the 406 tape reading agrees to 0.6 mm."""
        return self.fridge_d - self.hinge_cover

    @property
    def strut_centre(self) -> float:
        """Front-to-back centre of the strut pair, measured from the REAR edge.

        As far FORWARD as the hinge cover allows while keeping `cover_margin` in hand. Three
        datums were possible and the other two are both wrong:

          case centre (304.8)  drives the front clamp 48.7 mm INTO the cover. Blocked outright.
          window centre (203.3) is safe but leaves the screen 101.5 mm behind the case centre,
                                pushed away from where anyone actually stands.
          hard forward (256.1)  centres best but leaves ZERO tolerance against a cover position
                                that was read off a photograph.

        So: forward, but holding `cover_margin` back from the limit. That margin is the entire
        design decision here — it buys centring with clearance, and it is the number to change if
        the cover is ever measured properly or removed.
        """
        return self.clear_window - self.cover_margin - self.clamp_outer_half

    @property
    def display_bias_rearward(self) -> float:
        """How far behind the case centre the screen ends up as a result. Cosmetic, not structural."""
        return self.fridge_d / 2.0 - self.strut_centre

    @property
    def hinge_margin(self) -> float:
        """Front clamp edge to the hinge cover. Negative means a collision."""
        return self.clear_window - (self.strut_centre + self.clamp_outer_half)

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
        """How far the screen face stands off the fridge panel.

        NESTED: the strut is BESIDE the box, not behind it, so its depth leaves the stack. The
        plate lives inside the clamp gap rather than adding to it — the clamps set the strut's
        back face wherever the plate happens to be.
        """
        if self.nested:
            return self.gap + self.rear_box + self.panel_d
        return self.gap + self.strut_depth + self.plate_t + self.rear_box + self.panel_d

    @property
    def fixed_part(self) -> float:
        """The bit no design decision can change: the display's OWN depth.

        The strut and plate used to be counted here as if they were unavoidable. Once the box
        nests between the struts they are not part of the depth at all, so the only irreducible
        term is the display itself.
        """
        return self.rear_box + self.panel_d

    @property
    def proud(self) -> float:
        return (self.strut_top if self.strut_split else self.strut_len) - self.fridge_h


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


# The elevation is BROKEN between these heights: a 20.64 mm strut against a 1743 mm fridge is
# 1:84, so at true scale the strut can only ever be a line. Removing a dead stretch of the middle
# lets the whole thing be drawn 1.8x bigger in the same space. The break is marked, and the region
# removed carries nothing — no clamp, no plate, no display.
BREAK_LO, BREAK_HI = 250.0, 980.0


def _elevation(ox, oy, sc, a: Assembly) -> list[str]:
    """Side elevation, BROKEN vertically. Horizontal thin layers are separately exaggerated."""
    o: list[str] = []
    cut = BREAK_HI - BREAK_LO

    def Y(mm):
        """Height in mm -> y. Anything above the break is pulled down by the removed stretch."""
        return oy - (mm if mm <= BREAK_LO else mm - cut) * sc

    def X(mm):
        return ox + mm * sc
    fd = 260.0

    o.append(f'<line x1="{X(-120):.1f}" y1="{Y(0):.1f}" x2="{X(fd + 340):.1f}" '
             f'y2="{Y(0):.1f}" stroke="{INK}" stroke-width="2"/>')
    o.append(f'<rect x="{X(0):.1f}" y="{Y(a.fridge_h):.1f}" width="{fd * sc:.1f}" '
             f'height="{(Y(a.base_gap) - Y(a.fridge_h)):.1f}" fill="{FRIDGE_SIDE}" '
             f'stroke="{FRIDGE_SIDE_EDGE}" stroke-width="1.2"/>')
    o.append(_t(X(fd / 2), Y(1500), "fridge", 9, fill=ON_FRIDGE_MUTED, rot=-90))
    o.append(f'<line x1="{X(-40):.1f}" y1="{Y(a.base_gap):.1f}" x2="{X(fd + 30):.1f}" '
             f'y2="{Y(a.base_gap):.1f}" stroke="{BAD}" stroke-width="0.9" '
             f'stroke-dasharray="4 3"/>')
    o.append(_t(X(-44), Y(a.base_gap) + 3, f"underside {a.base_gap:.0f}", 8.0, anchor="end",
                fill=BAD, weight="bold"))

    EX = 4.0
    gap_px = a.gap * sc * EX
    strut_x = X(fd) + gap_px
    strut_w = a.strut_depth * sc * EX

    o.append(f'<rect x="{strut_x:.1f}" y="{Y(a.strut_len + 6):.1f}" width="{strut_w:.1f}" '
             f'height="{(Y(0) - Y(a.strut_len)):.1f}" fill="{C_STRUT}" stroke="{INK}" '
             f'stroke-width="1"/>')
    n = int(a.strut_len / a.slot_pitch)
    for i in range(n):
        sy = 25.4 + i * a.slot_pitch
        if BREAK_LO < sy < BREAK_HI:
            continue
        o.append(f'<rect x="{strut_x + strut_w * 0.3:.1f}" y="{Y(sy + 14):.1f}" '
                 f'width="{strut_w * 0.4:.1f}" height="{28.6 * sc:.1f}" fill="{INK}" '
                 f'fill-opacity="0.45"/>')

    foot_t = a.bracket_t * sc * EX
    o.append(f'<path d="M{strut_x - foot_t:.1f} {Y(300):.1f} '
             f'L{strut_x - foot_t:.1f} {Y(a.bracket_t):.1f} '
             f'L{strut_x + strut_w + 150 * sc:.1f} {Y(a.bracket_t):.1f} '
             f'L{strut_x + strut_w + 150 * sc:.1f} {Y(0):.1f} '
             f'L{strut_x - foot_t:.1f} {Y(0):.1f} Z" fill="{C_STEEL}" stroke="{INK}" '
             f'stroke-width="1.1"/>')

    def clamp(y_corner, flip):
        sgn = -1 if flip else 1
        leg, short = a.clamp_leg, a.clamp_short
        c = [f'<path d="M{X(fd):.1f} {Y(y_corner):.1f} L{X(fd - leg):.1f} {Y(y_corner):.1f} '
             f'L{X(fd - leg):.1f} {Y(y_corner + sgn * a.bracket_t):.1f} '
             f'L{strut_x - foot_t:.1f} {Y(y_corner + sgn * a.bracket_t):.1f} '
             f'L{strut_x - foot_t:.1f} {Y(y_corner - sgn * short):.1f} '
             f'L{X(fd):.1f} {Y(y_corner - sgn * short):.1f} Z" '
             f'fill="{C_STEEL}" stroke="{INK}" stroke-width="1.1"/>']
        fy = y_corner + (a.foam if not flip else 0)
        c.append(f'<rect x="{X(fd - leg):.1f}" y="{Y(fy):.1f}" width="{leg * sc:.1f}" '
                 f'height="{a.foam * sc * EX:.1f}" fill="#f8e2a4" stroke="{PAD_EDGE}" '
                 f'stroke-width="0.7"/>')
        sy = y_corner - sgn * short * 0.55
        c.append(f'<rect x="{strut_x - foot_t - 3:.1f}" y="{Y(sy + 5):.1f}" '
                 f'width="{strut_w + foot_t + 14:.1f}" height="{10 * sc:.1f}" '
                 f'fill="#8a6a10" stroke="#6d5300" stroke-width="0.9"/>')
        return c

    o += clamp(a.fridge_h, flip=False)
    o += clamp(a.base_gap, flip=True)

    px = strut_x + strut_w
    o.append(f'<rect x="{px:.1f}" y="{Y(a.screen_centre + a.plate_h / 2):.1f}" '
             f'width="{a.plate_t * sc * EX:.1f}" height="{a.plate_h * sc:.1f}" '
             f'fill="{C_PLATE}" stroke="{INK}" stroke-width="1"/>')
    dx = px + a.plate_t * sc * EX
    # The DISPLAY, dashed and to true scale — the only object on the sheet whose size the reader
    # already knows, so it is what makes the strut's slenderness legible.
    o.append(f'<rect x="{dx:.1f}" y="{Y(a.screen_centre + a.display_h / 2):.1f}" '
             f'width="{(a.rear_box + a.panel_d) * sc:.1f}" '
             f'height="{a.display_h * sc:.1f}" fill="#101820" fill-opacity="0.12" '
             f'stroke="{INK}" stroke-width="1.4" stroke-dasharray="7 4"/>')
    cap_y = Y(a.screen_centre - a.display_h / 2) + 14
    o.append(_t(dx, cap_y, "23.8 in display — TRUE SCALE", 8.6, anchor="start", weight="bold"))
    o.append(_t(dx, cap_y + 11, f"{a.display_h:.0f} tall x 43 deep. Drawn dashed purely so the",
                8.0, anchor="start", fill=MUTED))
    o.append(_t(dx, cap_y + 21, "strut beside it has something familiar for scale.", 8.0,
                anchor="start", fill=MUTED))

    # the break itself, drawn across everything it crosses
    by = Y(BREAK_LO) - 3
    for x0, x1 in ((X(-20), X(fd + 20)), (strut_x - foot_t - 10, strut_x + strut_w + 12)):
        o.append(f'<path d="M{x0:.1f} {by + 7:.1f} L{(x0 + x1) / 2:.1f} {by - 5:.1f} '
                 f'L{x1:.1f} {by + 7:.1f}" fill="none" stroke="{PAPER}" stroke-width="7"/>')
        o.append(f'<path d="M{x0:.1f} {by + 7:.1f} L{(x0 + x1) / 2:.1f} {by - 5:.1f} '
                 f'L{x1:.1f} {by + 7:.1f}" fill="none" stroke="{BAD}" stroke-width="1.4"/>')
    o.append(_t(strut_x + strut_w + 22, by + 2, f"BREAK — {cut:.0f} mm removed", 8.2,
                anchor="start", fill=BAD, weight="bold"))

    labs = [(Y(a.fridge_h) - 10, "TOP CLAMP — hooks the top, holds 3.8 lb", OK),
            (Y(a.screen_centre + a.display_h / 2) - 14, "plate — the SAME part, 246 mm centres",
             INK),
            (Y(1120), "2 x 6 ft low-profile strut — 20.64 mm deep", INK),
            (Y(a.base_gap + 90), "LOWER CLAMP — slides up to grip", OK),
            (Y(30), "FOOT — outboard, strut stands on it", OK)]
    lx = dx + (a.rear_box + a.panel_d) * sc + 150
    for ly, _x, _c in labs:
        o.append(f'<line x1="{dx + (a.rear_box + a.panel_d) * sc + 4:.1f}" y1="{ly - 4:.1f}" '
                 f'x2="{lx - 4:.1f}" y2="{ly - 4:.1f}" stroke="{RULE}" stroke-width="0.8"/>')
    for ly, txt, col in labs:
        o.append(_t(lx, ly, txt, 9.0, anchor="start", fill=col, weight="bold"))
    o.append(_t(X(-116), Y(a.fridge_h) - 8,
                f"vertical BROKEN; horizontal thin layers {EX:.0f}x", 8.5, anchor="start",
                fill=MUTED))
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
    fp = a.floor_pad
    o.append(f'<path d="M{X(foam + t):.1f} {Y(bg + rise - 12):.1f} '
             f'L{X(foam + t):.1f} {Y(fp + t):.1f} L{X(OUT_L - 6):.1f} {Y(fp + t):.1f} '
             f'L{X(OUT_L - 6):.1f} {Y(fp):.1f} L{X(foam + t):.1f} {Y(fp):.1f} '
             f'L{X(foam + 2 * t):.1f} {Y(fp):.1f} '
             f'L{X(foam + 2 * t):.1f} {Y(bg + rise - 12):.1f} Z" '
             f'fill="{C_STEEL}" stroke="{INK}" stroke-width="1.2"/>')
    # the floor pad, under the whole footprint
    o.append(f'<rect x="{X(foam + t):.1f}" y="{Y(fp):.1f}" '
             f'width="{(OUT_L - 6 - foam - t) * K:.1f}" height="{fp * K:.1f}" fill="#c7b299" '
             f'stroke="#8a7458" stroke-width="0.9"/>')
    o.append(f'<rect x="{X(foam + 2 * t):.1f}" y="{Y(bg + rise + 20):.1f}" '
             f'width="{a.strut_depth * K:.1f}" '
             f'height="{(bg + rise + 20 - t - a.floor_pad) * K:.1f}" '
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
    o.append(_t(X(OUT_L - 6) + 6, Y(fp + t) - 3, "foot", 8.4, anchor="start", fill=OK,
                weight="bold"))
    o.append(_t(X(OUT_L - 6) + 6, Y(fp / 2) + 3, f"floor pad {fp:.0f}", 8.4, anchor="start",
                fill="#8a7458", weight="bold"))
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
    o += _elevation(112, 566, 0.40, a)

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
        (f"A — spanning clamp bar  x{a.n_clamps}", INK,
         f"One bar per surface, reaching across BOTH struts — {a.clamp_width:.0f} mm "
         f"front-to-back. That is what ties the two struts into a frame; widening the individual "
         f"parts would only add steel that is not joined to anything at its far end. Long leg on "
         f"the fridge top, or under its base. ELEVATOR BOLTS through square laser-cut holes are "
         f"the studs: a flat 2.78 mm head that hides inside the foam, and a square shoulder that "
         f"stops it spinning. No welding. The lower one is the same part, flipped, bearing on two "
         f"pads because the underside is not flat."),
        (f"B — slotted foot  x{a.n_feet}", INK,
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
