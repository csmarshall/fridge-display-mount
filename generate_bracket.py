#!/usr/bin/env python3
"""Parametric flat-pattern generator for the fridge-side display mount bracket.

Formed (post-bend) dimensions are the inputs. The flat pattern is derived by subtracting
the bend deduction, half from each leg. Validation runs before anything is written; if a
check fails, no files are produced and the process exits non-zero.

See CLAUDE.md for the design invariants this implements.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import ezdxf
from ezdxf.math import bulge_to_arc

from bracket_common import (
    INSUNITS_MILLIMETERS,
    LOG_LEVELS,
    REQUIRED_LAYER,
    configure_logging,
)

LOG = logging.getLogger("generate")

MM_PER_INCH = 25.4
LBF_PER_KG = 2.2046226218  # weight in lbf of one kg under standard gravity
GRAVITY_SF = 1.0

# ---------------------------------------------------------------------------
# Material / vendor constants (verified against sendcutsend.com — see CLAUDE.md §3)
# ---------------------------------------------------------------------------


# SendCutSend's published bending table for 5052-H32, read from their bending-calculator page
# on 2026-08-25. Columns: K factor, bend deduction @90 deg, effective bend radius @90 deg, die
# width, minimum FORMED flange length @90 deg — all inches. These are vendor figures, not
# estimates, and they supersede the K-factor formula that used to derive the bend deduction here.
# Note .187" and .250" share the same 0.250" effective bend radius: going thicker buys no
# corner-radius tolerance.
BEND_SPECS = {}
BEND_SPECS_5052 = {
    0.040: (0.45, 0.062, 0.024, 0.472, 0.286),
    0.063: (0.42, 0.096, 0.035, 0.472, 0.303),
    0.080: (0.48, 0.116, 0.038, 0.472, 0.313),
    0.090: (0.37, 0.142, 0.032, 0.472, 0.326),
    0.100: (0.40, 0.191, 0.125, 0.630, 0.463),
    0.125: (0.44, 0.216, 0.125, 0.630, 0.476),
    0.187: (0.43, 0.356, 0.250, 0.984, 0.798),
    0.250: (0.42, 0.442, 0.250, 1.575, 1.371),
}

# A36/1008 mild steel, same table, same source. Note how much TIGHTER the effective bend radius is
# than aluminium at comparable thickness (.063" vs .250"), which makes the corner-radius mismatch
# WORSE, not better: flat_gap grows as (R_f - R_b).
BEND_SPECS_MILD_STEEL = {
    0.030: (0.38, 0.0610, 0.045, 0.472, 0.286),
    0.048: (0.38, 0.0860, 0.045, 0.472, 0.298),
    0.059: (0.40, 0.1080, 0.063, 0.472, 0.309),
    0.074: (0.40, 0.1290, 0.063, 0.472, 0.320),
    0.104: (0.34, 0.1815, 0.063, 0.630, 0.459),
    0.119: (0.38, 0.1955, 0.063, 0.630, 0.466),
    0.135: (0.32, 0.2440, 0.100, 0.984, 0.742),
    0.187: (0.36, 0.3225, 0.125, 0.984, 0.781),
    0.250: (0.36, 0.4215, 0.150, 1.575, 1.361),
}

# name -> (spec table, yield psi, density g/cc, human label)
MATERIALS = {
    "5052": (BEND_SPECS_5052, 28_000.0, 2.68, "5052-H32 aluminium"),
    "mild-steel": (BEND_SPECS_MILD_STEEL, 36_000.0, 7.85, "A36/1008 mild steel"),
}


@dataclass(frozen=True)
class Material:
    """5052-H32 as SendCutSend publishes it. All lengths mm unless named otherwise."""

    family: str = "mild-steel"
    thickness_in: float = 0.119

    @property
    def name(self) -> str:
        return MATERIALS[self.family][3]

    @property
    def yield_psi(self) -> float:
        return MATERIALS[self.family][1]

    @property
    def density_g_cc(self) -> float:
        return MATERIALS[self.family][2]

    @property
    def _spec(self) -> tuple[float, float, float, float, float]:
        return MATERIALS[self.family][0][self.thickness_in]

    @property
    def k_factor(self) -> float:
        return self._spec[0]

    @property
    def published_bend_deduction_in(self) -> float:
        return self._spec[1]

    @property
    def published_bend_deduction(self) -> float:
        return self._spec[1] * MM_PER_INCH

    @property
    def bend_radius_in(self) -> float:
        return self._spec[2]

    @property
    def die_width_in(self) -> float:
        return self._spec[3]

    @property
    def min_flange_in(self) -> float:
        return self._spec[4]

    die_min_in: float = 0.472
    sheet_max_in: tuple[float, float] = (30.0, 44.0)

    @property
    def thickness(self) -> float:
        return self.thickness_in * MM_PER_INCH

    @property
    def bend_radius(self) -> float:
        return self.bend_radius_in * MM_PER_INCH

    @property
    def min_flange(self) -> float:
        return self.min_flange_in * MM_PER_INCH

    @property
    def die_width(self) -> float:
        return self.die_width_in * MM_PER_INCH

    @property
    def bend_clearance(self) -> float:
        """Cut features must clear the bend centerline by half the die used for THIS thickness.

        Previously this assumed the widest die they own (1.575"), which was needlessly
        conservative: their published table gives the actual die per thickness.
        """
        return self.die_width / 2.0

    @property
    def min_hole_dia(self) -> float:
        """Laser pierce floor: roughly 50% of material thickness."""
        return 0.5 * self.thickness

    @property
    def min_edge_distance(self) -> float:
        """Hole/feature to edge. SendCutSend publishes 2x thickness; the brief's floor is 1x."""
        return 2.0 * self.thickness

    @property
    def sheet_max(self) -> tuple[float, float]:
        return (self.sheet_max_in[0] * MM_PER_INCH, self.sheet_max_in[1] * MM_PER_INCH)


@dataclass(frozen=True)
class Display:
    """Waveshare 23.8in FHD Monitor, SKU 34025.

    NOT a uniform slab. Read off Waveshare's dimension drawing
    (waveshare.com/img/devkit/LCD/27inch-FHD-Monitor/23.8inch-FHD-Monitor-details-size.jpg):
    a flat 18 mm panel with a 25 mm raised rear box, 43 mm overall. The VESA 100 pattern is on
    that raised box, so the bracket lands on the box face and stands 25 mm clear of the panel.
    """

    width: float = 555.23
    height: float = 324.65
    panel_depth: float = 18.00  # flat panel section
    rear_box_depth: float = 25.00  # how far the raised rear housing stands proud of the panel back
    rear_box_w: float = 260.00
    rear_box_h: float = 134.00
    active_w: float = 528.04
    active_h: float = 297.46
    bezel: float = 13.60
    corner_radius: float = 10.00
    mass_kg: float = 3.94
    vesa: float = 100.0  # CONFIRMED on the dimension drawing, on the rear box face
    watts: float = 36.0
    # Pi 5 fan / GPIO opening in the REAR BOX FACE, measured off the drawing at roughly 82 mm from
    # the VESA centre along one axis. Scaled from a raster drawing, so call it +/- 5 mm and confirm
    # against the physical unit. This is the thing the plate must not blank off.
    # Measured against the dimensioned 260 mm box width on each drawing: 99 px / 1.131 px-per-mm
    # on the 23.8in and 100.5 px / 1.150 on the 27in, i.e. 87.5 and 87.4 mm. The two agree because
    # both sizes use the same Pi bay assembly in the same 260 x 134 box. Still a raster read, so
    # +/- 5 mm.
    rear_face_feature_radius: float = 87.5
    rear_face_feature_dia: float = 30.0

    @property
    def depth(self) -> float:
        """Overall depth, panel plus raised rear box."""
        return self.panel_depth + self.rear_box_depth

    @property
    def weight_lbf(self) -> float:
        return self.mass_kg * LBF_PER_KG

    def centroid_from_box_face(self) -> float:
        """Depth of the display's centre of mass, measured out from the rear box face.

        Volume-weighted across the two sections rather than assumed at mid-depth: the panel is the
        bulk of the volume but sits furthest out, and getting this wrong understates the
        overturning moment. Volume is a proxy for mass here — the panel is glass, backlight and
        aluminium while the box holds a PCB and a fan, so this is an estimate, not a measurement.
        """
        box_volume = self.rear_box_w * self.rear_box_h * self.rear_box_depth
        panel_volume = self.width * self.height * self.panel_depth
        box_centroid = self.rear_box_depth / 2.0
        panel_centroid = self.rear_box_depth + self.panel_depth / 2.0
        return (box_volume * box_centroid + panel_volume * panel_centroid) / (box_volume + panel_volume)


# Both Waveshare panels share the rear box, the VESA pattern, the depth profile and the Pi bay, so
# one bracket serves either. Only mass and the torsion arm change.
DISPLAYS: dict[str, Display] = {
    "23.8": Display(),
    "27": Display(
        width=629.62,
        height=367.40,
        active_w=598.68,
        active_h=336.46,
        bezel=15.47,
        corner_radius=6.00,
        mass_kg=4.92,
    ),
}

MATERIAL = Material()


def set_material(family: str, thickness_in: float) -> None:
    """Select material and thickness. Rebinds the module-level MATERIAL."""
    global MATERIAL
    if thickness_in not in MATERIALS[family][0]:
        raise SystemExit(f"{family} is not bendable at {thickness_in}\" — SendCutSend publishes "
                         f"bend specs only for {sorted(MATERIALS[family][0])}")
    MATERIAL = Material(family=family, thickness_in=thickness_in)
    LOG.info("Material: %s at %.3f in (%.3f mm) — K %.2f, bend deduction %.4f in, "
             "effective bend radius %.3f in (%.2f mm), die %.3f in, min formed flange %.3f in",
             MATERIAL.name, MATERIAL.thickness_in, MATERIAL.thickness, MATERIAL.k_factor,
             MATERIAL.published_bend_deduction_in, MATERIAL.bend_radius_in, MATERIAL.bend_radius,
             MATERIAL.die_width_in, MATERIAL.min_flange_in)
DISPLAY = DISPLAYS["23.8"]


def set_display(name: str) -> None:
    """Select the panel the bracket is being generated for. Rebinds the module-level DISPLAY."""
    global DISPLAY
    DISPLAY = DISPLAYS[name]
    LOG.info(
        "Display: Waveshare %sin — %.2f x %.2f mm, %.2f kg, rear box %.0f x %.0f x %.0f, VESA %.0f",
        name, DISPLAY.width, DISPLAY.height, DISPLAY.mass_kg, DISPLAY.rear_box_w,
        DISPLAY.rear_box_h, DISPLAY.rear_box_depth, DISPLAY.vesa,
    )


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------


@dataclass
class BracketParams:
    """Formed (post-bend) geometry plus load-case inputs. Every length in mm."""

    # PORTRAIT is now the default, decided 2026-08-25. Two independent reasons:
    #  1. Dimensional — the fridge is counter-depth, so the side panel is only 610 mm front to
    #     back and the door sweeps the front ~64 mm of it. A 555 mm landscape display does not
    #     fit the 546 mm usable window; a 325 mm portrait one fits with 221 mm to spare.
    #  2. Mechanical — the brief already noted it: the touch-torsion arm drops from 278 mm to
    #     162 mm, roughly halving the load the magnets have to hold.
    orientation: str = "portrait"
    # 310 wide (not the brief's 300) buys 250 mm of horizontal magnet spacing against the
    # 240 mm floor. Torsion is about the VERTICAL axis, so only the horizontal span carries it.
    # The ceiling is portrait: the display is only 324.65 mm wide that way, so a body wider than
    # about 310 mm stops hiding behind it.
    body_w: float = 310.0
    # 310, matching the width. The width was grown 300 -> 310 to clear the 240 mm torsion
    # floor; the height was left at the brief's 300 and never revisited, which made Y spacing
    # permanently 10 mm tighter than X and is what blocked every larger magnet. Square fixes it.
    # The display is 324.65 mm wide in portrait, so a 310 mm plate is still fully hidden.
    body_h: float = 310.0
    # 190 mm (not the brief's 130) roughly halves the couple force at the bend under a touch
    # press, which is what holds the arm down if the side panel turns out to be non-magnetic.
    # Width runs front-to-back, where the fridge top is straight, so it costs no sheet: the
    # bounding box is already set by the body.
    neck_w: float = 190.0
    # bend apex -> body top edge. Puts the screen centre at 1331 mm on a 1791 mm fridge, the
    # middle of the band comfortable for 5'1"-6'4". MEASURE the fridge and re-derive.
    neck_len: float = 257.0  # puts the screen centre at 1331 mm on the 1743 mm Samsung case
    # ---- Samsung RS23A500ASR, 23 cu ft COUNTER-DEPTH side-by-side --------------------
    # From Samsung's published spec sheet (us-specsheet-rs23a500asr-aa-551113934.pdf):
    #   with hinges, handles and doors : 35 7/8" x 70 1/16" x 28 5/8"
    #   WITHOUT hinges and door        : 35 7/8" x 68 5/8"  x 24"
    # The arm rests on the CASE, so 68 5/8" (1743.1 mm) is the height that matters, not the
    # 70 1/16" hinge figure. MEASURE yours — installed height varies with the levelling feet.
    fridge_height: float = 68.625 * MM_PER_INCH  # 1743.1 mm, top of case
    # Hinge covers stand this far above the case top (70 1/16" - 68 5/8"). The arm lands behind them.
    hinge_cover_proud: float = (70.0625 - 68.625) * MM_PER_INCH  # 36.5 mm

    # Hinge cover footprint, MEASURED from the 2026-08-27 photo — which is a view of the LEFT
    # SIDE PANEL, the face the display hangs on. The ruler therefore runs FRONT-TO-BACK along the
    # top of that panel, not across the width. Datum is the REAR edge of the top.
    #
    # Sanity check that settles the reading: the photo shows the fridge edge at ruler ~27.5 in.
    # Case depth 24 in + doors projecting 4.6 in = 28.6 in. A FRONT view would have had to read
    # 35.9 in. The side reading needs no fudge; the front reading did.
    #
    # CONSEQUENCE: the cover constrains ARM WIDTH (which runs front-to-back), not arm reach.
    # This is the "clear window on the fridge top, front to back" that the pre-order checklist
    # calls the likeliest recut risk. It is now measured, and it passes.
    hinge_cover_from_rear: float = 16.0 * MM_PER_INCH    # 406 mm — cover's rear-most edge
    # Charles reports the cover LIFTS slightly, so thin material can be slipped under it. Not
    # relied on: the arm clears it by 216 mm, so this is a fallback, not part of the design.
    hinge_cover_lifts: bool = True

    @property
    def top_clear_window(self) -> float:
        """Usable front-to-back top depth: rear edge to the hinge cover."""
        return self.hinge_cover_from_rear
    fridge_top_width: float = 35.875 * MM_PER_INCH  # 911.2 mm, side to side across the top
    # COUNTER-DEPTH: the cabinet is only 24" deep. This is the front-to-back size of the top
    # surface the arm lands on, and of the side panel the body hangs against — 240 mm shallower
    # than a standard-depth box. It is what the 190 mm arm width has to fit inside.
    fridge_depth: float = 24.0 * MM_PER_INCH  # 609.6 mm, cabinet only
    fridge_depth_with_doors: float = 28.625 * MM_PER_INCH  # 727.1 mm
    # 0.0 — Charles reports the top is flat in use (things sit on it without rocking), which is
    # better evidence than any spec sheet. The original 3.0 mm was my own unsourced placeholder,
    # carried over from the brief's LG wrapper-doming rationale. With crown = 0 the arm pad only
    # has to absorb the corner-radius mismatch, so reach stops costing pad margin.
    crown_rise: float = 0.0
    # 180, not 130: the arm carries THREE magnet rows at +36 / +90 / +144, and the 54 mm row
    # pitch is a hard floor (O48 disc + 6 mm). The binding constraint is landing the outermost
    # full disc on metal, which needs 168 mm; 180 gives 12 mm beyond it. Costs $8.85 coated.
    arm_len: float = 180.0  # bend apex -> arm tip
    bend_angle_deg: float = 90.0
    bend_deduction: float = 0.0  # 0 => derive from material + K
    vesa: float = 100.0
    # Extra FDMI patterns cut now so a larger display can be fitted later without a new bracket.
    # (width, height, hole diameter). MIS-D/E use M4, MIS-F uses M6, hence the two diameters.
    # 75x75 is deliberately absent: its holes fall only 5.8 mm from the O90 centre vent, inside
    # the 2x-thickness edge rule — and it is a SMALL-display pattern, the wrong direction anyway.
    # 300x300 and larger do not fit a 310 x 300 body at all.
    # BOTH MIS-E orientations. A future display's VESA pattern is fixed relative to ITS body, so a
    # 200x100 panel hung in portrait presents 100x200 to the plate. Cutting both costs four holes.
    extra_vesa: tuple[tuple[float, float, float], ...] = (
        (200.0, 100.0, 4.4),   # MIS-E landscape, M4
        (100.0, 200.0, 4.4),   # MIS-E portrait, M4
        (200.0, 200.0, 6.5),   # MIS-F, M6
    )
    # 4.4, deliberately NOT the same as the magnet holes. SendCutSend's quote app groups
    # countersink options BY DIAMETER, so identical diameters put all ten holes in one anonymous
    # list of ten dropdowns and you have to know the file's entity order to pick the right four.
    # A distinct diameter gives the VESA holes their own 4-hole group in the UI, which is
    # self-documenting and impossible to misassign. Still ample M4 clearance (4.4 vs 4.0).
    vesa_hole_dia: float = 4.4
    # FALSE on the steel build. A 90 deg M4 countersink needs 1.80 mm of depth, and SendCutSend
    # caps it at 60% of thickness = 1.81 mm on a 3.02 mm plate — 0.01 mm of slack, and it would
    # remove 60% of the plate at four points. Low-head screws give the same result: a 2.2 mm
    # button head still clears the fridge by 3.8 mm inside the 6 mm magnet standoff.
    # Set True (and open the holes to ~5.0 mm) if flush heads are wanted instead.
    countersink_vesa: bool = False
    countersink_major: float = 0.315 * MM_PER_INCH  # SendCutSend's M4 90 deg profile, 8.001 mm
    # 7.0, not 6.5. The magnet is McMaster 5679K57, whose tapped hole is 1/4"-20 (6.35 mm
    # major). A 6.5 mm hole leaves 0.15 mm of clearance, which is not assemblable. 7.0 gives
    # 0.65 mm — between a close and a free fit — and still leaves 26.5 mm to the plate edge.
    # 8.5 clears the 3506K66's male 5/16"-18 stud (7.94 mm major) by 0.56 mm. The stud passes
    # THROUGH the plate and takes a washer and nut in the 25 mm of air behind.
    magnet_hole_dia: float = 8.5
    # 29.06 = disc radius 21.06 + an 8 mm edge margin. 8 mm is 12.7x the 0.63 mm worst-case
    # radial tolerance stack (magnet diameter + laser position + screw play), and it is what the
    # O42.11 disc needs to keep BOTH magnet spacings above the 240 mm floor.
    # A ROUND 32 mm. The magnet is an imperial part (1 57/64 in = 48.02 mm) and that cannot be
    # helped, but the position we CHOOSE should be a whole number: inset 32 puts the spacing at
    # exactly 246 mm on a 310 mm plate. The edge margin is then a DERIVED 7.99 mm rather than a
    # nominal 8.00 — same thing, but the drawing reads in whole millimetres.
    magnet_inset: float = 32.0
    # Extra magnet ROWS, as body-y positions, beyond the two corner rows at magnet_inset and
    # body_h - magnet_inset. Each entry adds a PAIR (left and right at the same inset). Resistance
    # to someone pulling the screen bottom outward is the sum of pull x distance below the fridge's
    # top edge, so every added pair helps — but placement is constrained by the vent windows.
    # 75 and 225: the two widest clear O36 bands left on the plate once the vent windows, the
    # centre vent and every VESA pattern are placed. Eight body magnets take the pull-off force
    # from 60 to 120 lbf on their own. Set () to go back to the four corner magnets.
    # EMPTY: four corner magnets only. The corners are provably the best four positions on the
    # plate, and at 150 lbf rated each there is no case for a second row.
    extra_magnet_rows: tuple[float, ...] = ()
    # Provision, not fitment: four spare magnet holes at the midpoint of each plate side, on the
    # SAME inset line as the corner magnets. Nothing goes in them at build time. If the mount ever
    # turns out not to hold, four more magnets drop straight in — and for straight PULL-OFF, which
    # is that failure mode, capacity is purely count x pull, so position does not matter.
    # A O48 disc here clips ~5% of the display's fan opening; a O25 would clear it entirely.
    spare_mid_holes: bool = True
    # Same idea on the ARM: one spare row INBOARD of the fitted one, toward the bend. Outboard
    # does not fit — it would land at bend +144 on a 130 mm arm. The strap slots do NOT clash:
    # they run up the centreline at x 145-165 while arm magnets sit at x 95 and 215, 52 mm apart
    # across the arm, so nothing has to move to make room.
    # FALSE now that all three arm rows are fitted magnet positions: the old "spare" row sat one
    # pitch BEHIND the fitted row, which with a back row at +36 would land at -18, behind the bend.
    spare_arm_holes: bool = False
    # McMaster 3506K66: 1 21/32 in OD. A male-STUD part, which is the only construction that
    # works on a 3 mm plate — the threaded-HOLE version of the same magnet (5679K58) carries an
    # 11.28 mm boss that would stand the magnet off the plate by that much.
    # McMaster 3506K67, 1 57/64 in. Male-stud construction, as with the K66 it supersedes.
    magnet_disc_dia: float = (1 + 57 / 64) * MM_PER_INCH
    # 5/16 in = 7.9375. The magnet body height IS the standoff, so this sets how far the
    # display sits off the fridge and it feeds the CG offset and the bottom pad thickness.
    magnet_standoff: float = (29.0 / 64.0) * MM_PER_INCH   # 11.51 mm, the 3506K67 disc height
    center_open_dia: float = 90.0
    # 80, not 100. The MIS-E 200x100 holes land exactly on the ends of the left/right windows at
    # 100 mm long. The windows cannot move — they sit on the 87.5 mm radius so one covers the Pi's
    # fan in every rotation — so they get shorter instead. Costs 1.3 points of open area; the fan
    # coverage margin is in the RADIAL direction (window 46 wide) and is unaffected.
    window_long: float = 80.0
    # 46 mm across the radial direction, not 40: the windows must cover the rear box's fan opening
    # with margin for the +/- 5 mm uncertainty in reading its position off a raster drawing.
    window_short: float = 46.0
    # Vent windows sit on a RADIUS from the VESA centre rather than a margin from the plate edge,
    # so that all four line up with the rear box's fan/GPIO opening whichever way the display is
    # rotated: that opening is a fixed distance from the VESA centre on one axis, so a cardinal
    # window at the same radius always lands over it.
    window_radius: float = 87.5
    # Set False to omit the four vent windows entirely — a cost/appearance experiment. The plate
    # does not seal the display: it stands 10 mm off the rear box on spacers and is open on all
    # four edges, so removing the windows narrows the escape path rather than closing it.
    vent_windows: bool = True
    outer_fillet: float = 8.0
    reflex_fillet: float = 6.0
    window_fillet: float = 5.0
    # 1/4 in = 6.35 mm. Closed-cell sponge is sold in imperial thicknesses, so the pad is picked
    # from stock and the magnets are picked to match it, not the other way round.
    # 0.0 => DERIVE from the magnet. The pad is a purchased consumable sized TO the magnet,
    # never a constraint the magnet must obey: if a taller magnet needs a thicker pad, you buy
    # the next sponge stock size up. Treating 3/8 in as fixed made it look like a hard ceiling
    # on magnet thickness, which it never was.
    arm_pad_override: float = 0.0
    # SendCutSend's quote app reports "No bend lines detected" for a geometry-only 2D file and
    # greys out Bending entirely. Their own guidance table says .dxf wants a DASHED line (not
    # hidden) at the bend centre, so the line is required, not optional.
    bend_line: bool = True
    # Cable tie-down points: pairs of holes on the centreline that a zip tie or P-clip threads
    # through, so the display's power lead is captured up the neck, over the bend and onto the
    # fridge top, where it is out of sight. Positions are OFFSETS FROM THE BEND LINE (negative =
    # neck side, positive = arm side) so they track any change to neck length or arm reach.
    cable_ties: bool = True
    # COUNTS, not positions. The old fixed offsets (-220, -130, -40, +45, +115) claimed in their
    # own comment to "track any change to neck length or arm reach" and did nothing of the kind:
    # shortening the neck to 212 mm pushed the -220 pair 1.48 mm from the body edge, inside the
    # 2x-thickness rule. Positions are now spread across whatever neck and arm actually exist,
    # between the bend keep-out and the region edges, so a parameter change cannot strand one.
    cable_tie_neck_pairs: int = 3
    cable_tie_arm_pairs: int = 2
    # Centre-to-centre of the two slots in a pair, across the plate. The strap drops through one,
    # passes behind the bridge between them and comes back up the other, so this minus the slot
    # thickness IS the bridge width: 16.0 - 4.0 = 12 mm of material for the strap to loop under.
    cable_tie_pair_gap: float = 16.0
    # VELCRO Brand ONE-WRAP, 8 in x 1/2 in (the strap Charles has: amazon B09X64G72B). Nominal
    # width 12.7 mm.
    strap_width: float = 0.5 * MM_PER_INCH
    # Per side. 2.65 mm takes the slot to 18.0 mm, which swallows a nominal 1/2 in strap with room
    # to spare AND still passes a 5/8 in (15.9 mm) one, so a different strap in the drawer does not
    # mean a different bracket. It costs nothing: the slots sit in the middle of a 190 mm neck.
    strap_clearance: float = 2.65
    # Across the strap's thickness. ONE-WRAP is about 1.9 mm of hook-and-loop laminate; 4.0 mm
    # leaves enough that the strap threads with a fingertip rather than a tool.
    strap_slot_thickness: float = 4.0
    arm_magnets: bool = True
    arm_magnet_disc_dia: float = (1 + 57 / 64) * MM_PER_INCH  # same SKU: 3506K67
    arm_magnet_standoff: float = (29.0 / 64.0) * MM_PER_INCH
    arm_magnet_offset: float = 90.0  # formed distance from the bend apex, along the arm
    # Extra rows of arm ("top lip") magnets, as further formed offsets from the bend apex. Each
    # entry adds a PAIR at arm_magnet_spacing. These still carry ZERO vertical load — the hook does
    # that — but they are NOT decorative: they sit on the far side of the pivot from the display,
    # so when someone pulls the screen bottom outward they resist with a lever equal to their
    # offset. Short lever, so each one is worth much less than a body magnet, but not nothing.
    # One extra top-lip row at 40 mm from the bend apex. Its disc spans 22-58 mm along the arm,
    # so it clears both the bend keep-out and the 90 mm row without crowding either.
    # EMPTY: one arm row = 2 magnets, retention only. A second row would not clear the first
    # at this disc size anyway (needs 48.1 mm, the rows are 50 mm apart).
    # THREE evenly spaced arm rows at +36 / +90 / +144, all of them fitted magnet positions —
    # back, middle and front across the reach at the 54 mm minimum pitch (O48 disc + 6 mm).
    # Anti-jostle only, like the others — ZERO credit in the vertical load path.
    extra_arm_magnet_offsets: tuple[float, ...] = (36.0, 144.0)
    arm_magnet_spacing: float = 120.0  # centre-to-centre across the arm width
    fridge_corner_radius: float = 12.0  # MEASURE. Affects pad sizing only, never cut geometry.
    # Design envelope for the pad, not a guess at the actual radius. LG uses a single formed steel
    # wrapper for both sides and the top, so the top edge is a real sheet-metal bend and lands in
    # the 6-15 mm range. The pad is sized against the top of that band; coverage beyond it is
    # REPORTED as sensitivity rather than designed to, because 3/8 in sponge would then force a
    # magnet height that nobody stocks.
    fridge_corner_radius_max: float = 15.0
    # 0 — spacers deleted 2026-08-25. Both original justifications expired:
    #  * "clear the magnet screw heads" — the display's 25 mm raised rear box already does this;
    #    all four magnet holes sit outside the box footprint and have 25 mm of air regardless.
    #  * "keep the plate off the Pi's fan opening" — the vent windows sit on an 87.5 mm radius
    #    precisely so one lands over that opening in every rotation.
    # Deleting them lowers the CG offset 48.5 -> 38.5 mm, cuts neck bending 21%, removes 10 mm of
    # protrusion and takes a compliant column out of the load path. Set non-zero to restore.
    spacer_len: float = 0.0
    screw_head_height: float = 4.0  # M4 socket head cap screw
    press_force_lbf: float = 5.0
    # McMaster 5679K57: encased neodymium N42 in a zinc-plated STEEL case, threaded hole,
    # rated 100 lbf. Rating basis is their stated "direct contact with rust-free, unpainted iron",
    # the same basis K&J use, so the 35% derate for thin painted appliance sheet still applies.
    # Supersedes an unverified 71.7 lbf figure for a K&J part I could not confirm exists.
    # McMaster 3506K66, N42 in a zinc-plated STEEL case, male 5/16"-18 x 1/2" stud.
    # Their rating basis is "direct contact with rust-free, unpainted iron", the same as K&J's,
    # so the 35% derate for thin PAINTED appliance sheet still applies on top.
    magnet_rated_pull_lbf: float = 175.0
    magnet_derate: float = 0.35
    mu_rubber: float = 0.2   # BARE nickel now, not rubber. Irrelevant: the hook carries
                             # all vertical load and the magnets work in tension, not shear.
    mu_bare_nickel: float = 0.2
    min_magnet_spacing: float = 240.0  # LOAD-BEARING FLOOR — see CLAUDE.md §1.2

    @property
    def strap_slot_length(self) -> float:
        """Slot dimension along the neck — the direction the strap's width sits in."""
        return self.strap_width + 2.0 * self.strap_clearance

    @property
    def magnet_spacing_x(self) -> float:
        return self.body_w - 2.0 * self.magnet_inset

    @property
    def magnet_spacing_y(self) -> float:
        return self.body_h - 2.0 * self.magnet_inset

    bottom_pad_thickness_override: float = 0.0  # 0 => stock 1/4 in

    @property
    def arm_pad(self) -> float:
        """Arm sponge pad — derived from the arm magnet the same way, unless overridden."""
        return self.arm_pad_override or sponge_stock_for(self.arm_magnet_standoff)

    @property
    def bottom_pad_thickness(self) -> float:
        """Invariant 1.5 says the pad equals the magnet standoff, or the plate sits skewed.

        The functional requirement is that the pad must not be THINNER than the magnet, or the
        rigid magnet holds the plate off and the pad does nothing. Being slightly proud is
        harmless because the pad is compressible sponge and simply squashes to the magnet plane.
        That matters because sponge comes in imperial thicknesses and there is no 6.00 mm stock:
        1/4 in is 6.35 mm, 0.35 mm over the magnet, well inside the sponge's compression.
        """
        return self.bottom_pad_thickness_override or sponge_stock_for(self.magnet_standoff)

    @property
    def screen_centre_height(self) -> float:
        """Height above the floor of the VESA centre, which is the screen centre in either
        orientation. The brief's '- 12 mm' is this same relationship seen from the display's top
        edge: the display overhangs the body by (display - body)/2, which is 12.3 mm tall in
        landscape and 127.6 mm in portrait. Derived, never hardcoded."""
        return self.fridge_height - self.neck_len - self.body_h / 2.0

    @property
    def display_overhang(self) -> float:
        """How far the display extends past the body top and bottom edges, this orientation."""
        span = DISPLAY.height if self.orientation == "landscape" else DISPLAY.width
        return (span - self.body_h) / 2.0

    @property
    def torsion_arm(self) -> float:
        """Half the screen dimension the press moment acts across, for this orientation."""
        return (DISPLAY.width if self.orientation == "landscape" else DISPLAY.height) / 2.0

    @property
    def cg_offset(self) -> float:
        """CG offset from the fridge face, derived from the mounting stack (no magic 26 mm).

        The stack lands on the display's RAISED REAR BOX, not on the panel, so the display's own
        centre of mass sits a long way further out than half its overall depth.
        """
        return (
            self.magnet_standoff
            + MATERIAL.thickness
            + self.spacer_len
            + DISPLAY.centroid_from_box_face()
        )

    @property
    def peel_lever(self) -> float:
        """Top magnet row down to the bottom bearing pad at the body's lower edge."""
        return (self.body_h / 2.0 - self.magnet_inset) + self.body_h / 2.0


@dataclass
class FlatPattern:
    """Flat-pattern envelope derived from the formed dimensions."""

    arm_flat: float
    neck_flat: float
    body_h: float
    width: float
    height: float
    bend_line_y: float
    bend_deduction: float


# Closed-cell sponge is sold in imperial thicknesses. There is no continuous range, so the
# pad is whichever stock size first clears the magnet.
# Imperial AND metric stock. Metric matters: 11.5 mm sits 0.01 mm from the 11.51 mm magnet,
# which no imperial size gets near.
PAD_STOCK_MM = tuple(sorted(
    [f * MM_PER_INCH for f in (1/8, 3/16, 1/4, 5/16, 3/8, 7/16, 1/2, 5/8, 3/4, 1.0)]
    + [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 11.0, 11.5, 12.0, 15.0, 20.0]))

# How far BELOW the magnet the pad may sit. Being a little under is CORRECT: the rigid magnets
# then bear on the panel and the joint is stiff, with the pad protecting paint across a hair of
# gap that the paint and tolerance stack closes. Being OVER is what must not happen — the plate
# lands on the pad, the magnets never reach steel, and the mount feels spongy AND grips less.
PAD_UNDERSIZE_ALLOWANCE_MM = 0.60


def sponge_stock_for(magnet_height: float) -> float:
    """Stock thickness closest to the magnet height, biased UNDER rather than over.

    Previously this took the thinnest stock NOT THINNER than the magnet, which for an 11.51 mm
    magnet returned 1/2 in (12.70) — 1.19 mm PROUD. That is the wrong side: it holds the plate
    off the magnets. Being slightly under is the side that makes the joint feel solid.
    """
    usable = [t for t in PAD_STOCK_MM if t >= magnet_height - PAD_UNDERSIZE_ALLOWANCE_MM]
    if not usable:
        raise ValueError(f"no pad stock suits a {magnet_height:.2f} mm magnet")
    return min(usable, key=lambda t: (abs(t - magnet_height), t > magnet_height))


def bend_deduction_mm(radius: float, thickness: float, k_factor: float, angle_deg: float) -> float:
    """BD = 2*(R+T)*tan(a/2) - (pi*a/180)*(R + K*T).

    The first term is the outside setback (twice, one per leg); the second is the length of
    the neutral axis through the bend. Their difference is what the flat loses. K places the
    neutral axis inside the material; 0.42 is a common aluminium value and is an ASSUMPTION
    here — replace it with SendCutSend's bending-calculator figure before ordering.
    """
    angle = math.radians(angle_deg)
    setback = 2.0 * (radius + thickness) * math.tan(angle / 2.0)
    neutral_arc = angle * (radius + k_factor * thickness)
    deduction = setback - neutral_arc
    LOG.debug(
        "bend_deduction: R=%.4f T=%.4f K=%.3f angle=%.1f setback=%.4f neutral_arc=%.4f BD=%.4f",
        radius, thickness, k_factor, angle_deg, setback, neutral_arc, deduction,
    )
    return deduction


def flat_gap(fridge_radius: float, bracket_radius: float) -> float:
    """Lift-off of the bracket flats when the fridge corner is sharper-radiused than the bend.

    If R_f <= R_b the bracket flats seat on the fridge flats and the gap is zero (the void is
    at the corner, which the sponge fills). If R_f > R_b the bracket rides up on the corner
    and each flat lifts by (R_f - R_b)*(1 - 1/sqrt(2)).
    """
    if fridge_radius <= bracket_radius:
        return 0.0
    return (fridge_radius - bracket_radius) * (1.0 - 1.0 / math.sqrt(2.0))


def crown_rise_at(reach: float, top_width: float, crown: float) -> float:
    """How far the crowned fridge top rises under the arm, `reach` mm inboard from the side edge.

    Wrappers are domed across their width for rigidity. Model the dome as a parabola: zero at both
    side edges, `crown` at the centre. This is what limits arm REACH — the arm runs across the dome
    — while arm WIDTH runs front-to-back, where the top is straight. The two dimensions are bounded
    by different things, which is why they are not proportional.
    """
    half = top_width / 2.0
    if reach >= half:
        return crown
    return crown * (1.0 - ((half - reach) / half) ** 2)


def derive_flat(params: BracketParams) -> FlatPattern:
    """Subtract the bend deduction, half from each leg, and stack the flat envelope."""
    deduction = params.bend_deduction
    if deduction <= 0.0:
        # Their PUBLISHED figure, not a derivation. The formula below is kept for reference and
        # for thicknesses they do not publish, but a vendor number always wins over our estimate.
        deduction = MATERIAL.published_bend_deduction
        estimate = bend_deduction_mm(
            MATERIAL.bend_radius, MATERIAL.thickness, MATERIAL.k_factor, params.bend_angle_deg
        )
        LOG.info("Bend deduction: %.4f mm — SendCutSend published %.3f in for %s at %.3f in "
                 "(our K=%.2f formula would have given %.4f mm, off by %.4f)",
                 deduction, MATERIAL.published_bend_deduction_in, MATERIAL.name,
                 MATERIAL.thickness_in, MATERIAL.k_factor, estimate, abs(estimate - deduction))
    else:
        LOG.info("Bend deduction supplied on the command line: %.3f mm", deduction)

    arm_flat = params.arm_len - deduction / 2.0
    neck_flat = params.neck_len - deduction / 2.0
    height = params.body_h + neck_flat + arm_flat
    flat = FlatPattern(
        arm_flat=arm_flat,
        neck_flat=neck_flat,
        body_h=params.body_h,
        width=params.body_w,
        height=height,
        bend_line_y=params.body_h + neck_flat,
        bend_deduction=deduction,
    )
    LOG.debug(
        "flat: arm_flat=%.3f neck_flat=%.3f body_h=%.3f width=%.3f height=%.3f bend_line_y=%.3f",
        arm_flat, neck_flat, params.body_h, flat.width, flat.height, flat.bend_line_y,
    )
    return flat


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hole:
    x: float
    y: float
    dia: float
    tag: str
    region: str = "body"  # which rectangle the edge-distance checks measure against

    @property
    def radius(self) -> float:
        return self.dia / 2.0


@dataclass(frozen=True)
class WindowRect:
    cx: float
    cy: float
    w: float
    h: float
    r: float
    tag: str
    region: str = "body"  # which rectangle the edge-distance check measures against

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return (self.cx - self.w / 2, self.cy - self.h / 2, self.cx + self.w / 2, self.cy + self.h / 2)

    def distance_to_point(self, px: float, py: float) -> float:
        """Signed distance from a point to the rounded rectangle boundary.

        Positive outside, negative inside, and exact in BOTH directions — the naive
        `hypot(max(overshoot, 0)) - r` form saturates at -r everywhere inside the shape, which
        silently understates interior clearance. The interior term is the `min(max(qx, qy), 0)`
        below.
        """
        qx = abs(px - self.cx) - (self.w / 2.0 - self.r)
        qy = abs(py - self.cy) - (self.h / 2.0 - self.r)
        outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
        inside = min(max(qx, qy), 0.0)
        return outside + inside - self.r


@dataclass
class Geometry:
    outline: list[tuple[float, float]]
    holes: list[Hole]
    windows: list[WindowRect]
    center_opening: Hole
    magnet_discs: list[Hole]
    flat: FlatPattern
    regions: dict[str, tuple[float, float, float, float]]


def _spread(lo: float, hi: float, n: int, inset: float = 0.10) -> list[float]:
    """n positions evenly spread across [lo, hi], held off both ends by `inset` of the span."""
    if n <= 0 or hi <= lo:
        return []
    a, b = lo + (hi - lo) * inset, hi - (hi - lo) * inset
    if n == 1:
        return [(a + b) / 2.0]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def derive_cable_tie_positions(params: BracketParams, flat: FlatPattern) -> list[tuple[float, str]]:
    """Flat-pattern y positions for the strap slots, as (y, region).

    Bounded by three real constraints rather than chosen by hand: the slot's own half-length, the
    2x-thickness edge rule against the region it sits in, and the bend keep-out (half the die
    width) on whichever side of the bend line it approaches.
    """
    half = params.strap_slot_length / 2.0
    edge = MATERIAL.min_edge_distance + half
    clear = MATERIAL.bend_clearance + half
    neck = _spread(params.body_h + edge, flat.bend_line_y - clear, params.cable_tie_neck_pairs)
    arm = _spread(flat.bend_line_y + clear, flat.height - edge, params.cable_tie_arm_pairs)
    return [(y, "neck") for y in neck] + [(y, "arm") for y in arm]


def rear_box_footprint(orientation: str) -> tuple[float, float]:
    """The raised rear box as seen looking at the plate: (across plate x, along plate y).

    The box is fixed to the DISPLAY — 260 mm along the display's long axis, 134 mm across it — so
    rotating the display to portrait rotates the box with it. Stating this in one place because it
    was previously asserted twice and the two copies disagreed.
    """
    if orientation == "portrait":
        return (DISPLAY.rear_box_h, DISPLAY.rear_box_w)
    return (DISPLAY.rear_box_w, DISPLAY.rear_box_h)


def build_geometry(params: BracketParams, flat: FlatPattern) -> Geometry:
    """Flat-pattern outline (CCW) and interior features, origin at the body's lower-left corner."""
    bw, bh, nw = params.body_w, params.body_h, params.neck_w
    neck_x0 = (bw - nw) / 2.0
    neck_x1 = neck_x0 + nw
    top = flat.height

    outline = [
        (0.0, 0.0),
        (bw, 0.0),
        (bw, bh),
        (neck_x1, bh),
        (neck_x1, top),
        (neck_x0, top),
        (neck_x0, bh),
        (0.0, bh),
    ]
    LOG.debug("outline vertices (CCW): %s", ["(%.2f, %.2f)" % p for p in outline])

    cx, cy = bw / 2.0, bh / 2.0
    half_vesa = params.vesa / 2.0

    holes: list[Hole] = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            holes.append(Hole(cx + sx * half_vesa, cy + sy * half_vesa, params.vesa_hole_dia, "vesa"))
    for pat_w, pat_h, pat_dia in params.extra_vesa:
        tag = f"vesa{pat_w:.0f}x{pat_h:.0f}"
        for sx in (-1, 1):
            for sy in (-1, 1):
                holes.append(Hole(cx + sx * pat_w / 2.0, cy + sy * pat_h / 2.0, pat_dia, tag))

    arm_x0 = neck_x0
    arm_x1 = neck_x1
    # Three distinct rectangles, because a hole's edge distance must be measured against the
    # region it actually sits in: the neck and arm are narrower than the body.
    regions = {
        "body": (0.0, 0.0, bw, bh),
        "neck": (arm_x0, bh, arm_x1, flat.bend_line_y),
        "arm": (arm_x0, flat.bend_line_y, arm_x1, top),
    }

    magnet_x = bw / 2.0 - params.magnet_inset
    magnet_y = bh / 2.0 - params.magnet_inset
    magnet_discs: list[Hole] = []
    rows = [cy - magnet_y, cy + magnet_y] + list(params.extra_magnet_rows)
    for sx in (-1, 1):
        for hy in rows:
            hx = cx + sx * magnet_x
            holes.append(Hole(hx, hy, params.magnet_hole_dia, "magnet"))
            magnet_discs.append(Hole(hx, hy, params.magnet_disc_dia, "magnet_disc"))

    # Retention magnets on the arm. They stop the arm walking fore-aft on the crowned fridge top
    # and resist a jostle lifting the hook; they are given ZERO credit in the load path. Placed
    # by formed distance from the bend apex, so the flat position moves with the bend deduction.
    if params.arm_magnets:
        for off in (params.arm_magnet_offset,) + tuple(params.extra_arm_magnet_offsets):
            arm_hole_y = flat.bend_line_y + off - flat.bend_deduction / 2.0
            for sx in (-1, 1):
                hx = cx + sx * params.arm_magnet_spacing / 2.0
                holes.append(Hole(hx, arm_hole_y, params.magnet_hole_dia, "arm_magnet", "arm"))
                magnet_discs.append(Hole(hx, arm_hole_y, params.arm_magnet_disc_dia,
                                         "arm_magnet_disc", "arm"))
            LOG.debug("arm magnets at y=%.2f (formed %.1f mm from the bend apex, less BD/2=%.3f)",
                      arm_hole_y, off, flat.bend_deduction / 2.0)


    for hole in holes:
        LOG.debug("hole %-11s region=%-4s at (%.2f, %.2f) dia %.2f",
                  hole.tag, hole.region, hole.x, hole.y, hole.dia)

    if params.spare_arm_holes and params.arm_magnets:
        sep = params.arm_magnet_disc_dia + 6.0
        spare_off = params.arm_magnet_offset - sep
        spare_y = flat.bend_line_y + spare_off - flat.bend_deduction / 2.0
        for sx in (-1, 1):
            holes.append(Hole(cx + sx * params.arm_magnet_spacing / 2.0, spare_y,
                              params.magnet_hole_dia, "spare_arm_magnet", "arm"))
        # Plus one on the arm CENTRELINE, level with the fitted row. The hole clears the strap
        # slots by 5.1 mm; a fitted O48 disc would NOT — it would sit over them. So this is a
        # choose-one position: a third arm magnet, or that strap tie-down, not both.
        holes.append(Hole(cx, flat.bend_line_y + params.arm_magnet_offset - flat.bend_deduction / 2.0,
                          params.magnet_hole_dia, "spare_arm_magnet", "arm"))
        LOG.debug("spare arm holes at bend +%.1f (fitted row is at +%.1f)",
                  spare_off, params.arm_magnet_offset)

    if params.spare_mid_holes:
        i = params.magnet_inset
        for sx, sy, tag in ((cx, i, "spare_bottom"), (cx, bh - i, "spare_top"),
                            (i, bh / 2.0, "spare_left"), (bw - i, bh / 2.0, "spare_right")):
            holes.append(Hole(sx, sy, params.magnet_hole_dia, "spare_magnet", "body"))
        LOG.debug("spare mid-side magnet holes at inset %.1f, O%.1f", i, params.magnet_hole_dia)

    center_opening = Hole(cx, cy, params.center_open_dia, "center_vent")

    # Edge windows: long axis parallel to the edge they sit on, outer edge inset by
    # window_edge_margin so the rim stays continuous and stiff.
    offset_x = offset_y = params.window_radius
    windows = [] if not params.vent_windows else [
        WindowRect(cx, cy + offset_y, params.window_long, params.window_short, params.window_fillet, "vent_top"),
        WindowRect(cx, cy - offset_y, params.window_long, params.window_short, params.window_fillet, "vent_bottom"),
        WindowRect(cx - offset_x, cy, params.window_short, params.window_long, params.window_fillet, "vent_left"),
        WindowRect(cx + offset_x, cy, params.window_short, params.window_long, params.window_fillet, "vent_right"),
    ]
    # Strap tie-downs: pairs of SLOTS, not round holes. A hook-and-loop strap is a flat band, so
    # it needs a slot at least its width; a 5 mm hole only ever took a zip tie. Long axis runs
    # ALONG the neck because that is how the strap's width lies when it encircles a cable that
    # runs up the neck.
    if params.cable_ties:
        slot_l = params.strap_slot_length
        slot_t = params.strap_slot_thickness
        # Corner radius is a fraction of the slot thickness rather than a full half-round end: a
        # true obround has zero straight edge on the short side, which the fillet builder cannot
        # construct (its tangent length would exceed half the adjacent edge).
        slot_r = slot_t * 0.35
        for ty, region in derive_cable_tie_positions(params, flat):
            off = ty - flat.bend_line_y
            for sx, side in ((-1, "l"), (1, "r")):
                windows.append(WindowRect(cx + sx * params.cable_tie_pair_gap / 2.0, ty,
                                          slot_t, slot_l, slot_r,
                                          f"strap_{off:+.0f}{side}", region))
        LOG.debug("strap slots %.1f x %.1f mm (fits a %.1f mm strap, +%.2f/side) at bend %s",
                  slot_t, slot_l, params.strap_width, params.strap_clearance,
                  ", ".join(f"{y - flat.bend_line_y:+.0f}"
                            for y, _ in derive_cable_tie_positions(params, flat)))

    for win in windows:
        LOG.debug("window %-12s centre (%.2f, %.2f) %.1f x %.1f r%.1f", win.tag, win.cx, win.cy, win.w, win.h, win.r)

    return Geometry(outline, holes, windows, center_opening, magnet_discs, flat, regions)


# ---------------------------------------------------------------------------
# Rounded-corner polyline (bulge) construction
# ---------------------------------------------------------------------------


def fillet_polygon(
    points: Sequence[tuple[float, float]],
    convex_radius: float,
    reflex_radius: float,
    label: str,
) -> list[tuple[float, float, float]]:
    """Round every corner of a closed CCW polygon, returning LWPOLYLINE (x, y, bulge) tuples.

    One code path handles convex and reflex corners: the signed turn angle comes from
    atan2(cross, dot) of the incoming and outgoing edge directions, so a left turn (convex on
    a CCW polygon) is positive and a right turn (reflex) is negative. The arc that rounds a
    corner subtends exactly that turn angle, and the DXF bulge of an arc is tan(theta/4) —
    signed the same way, positive for counter-clockwise. So the sign falls straight out of the
    2D cross product with no special-casing.
    """
    count = len(points)
    result: list[tuple[float, float, float]] = []
    for i, (px, py) in enumerate(points):
        prev_x, prev_y = points[(i - 1) % count]
        next_x, next_y = points[(i + 1) % count]

        in_x, in_y = px - prev_x, py - prev_y
        out_x, out_y = next_x - px, next_y - py
        in_len, out_len = math.hypot(in_x, in_y), math.hypot(out_x, out_y)
        if in_len == 0.0 or out_len == 0.0:
            raise ValueError(f"{label}: zero-length edge at vertex {i}")
        in_x, in_y = in_x / in_len, in_y / in_len
        out_x, out_y = out_x / out_len, out_y / out_len

        cross = in_x * out_y - in_y * out_x
        dot = in_x * out_x + in_y * out_y
        turn = math.atan2(cross, dot)

        if abs(turn) < 1e-9:
            result.append((px, py, 0.0))
            LOG.debug("%s vertex %d (%.2f, %.2f): collinear, no fillet", label, i, px, py)
            continue

        radius = convex_radius if turn > 0 else reflex_radius
        tangent = radius * math.tan(abs(turn) / 2.0)
        if tangent > in_len / 2.0 + 1e-9 or tangent > out_len / 2.0 + 1e-9:
            raise ValueError(
                f"{label}: fillet r={radius:.3f} at vertex {i} needs tangent {tangent:.3f} mm "
                f"but adjacent edges are {in_len:.3f} and {out_len:.3f} mm"
            )

        start = (px - in_x * tangent, py - in_y * tangent)
        end = (px + out_x * tangent, py + out_y * tangent)
        bulge = math.tan(turn / 4.0)
        result.append((start[0], start[1], bulge))
        result.append((end[0], end[1], 0.0))
        LOG.debug(
            "%s vertex %d (%.2f, %.2f): turn=%+.2f deg (%s) r=%.2f tangent=%.3f bulge=%+.5f",
            label, i, px, py, math.degrees(turn), "convex" if turn > 0 else "reflex",
            radius, tangent, bulge,
        )
    return result


def rounded_rect_points(win: WindowRect) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = win.bounds
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def flatten_bulged(points: Sequence[tuple[float, float, float]], segments_per_arc: int = 24) -> list[tuple[float, float]]:
    """Sample a closed bulged polyline into straight segments, for the SVG preview only."""
    out: list[tuple[float, float]] = []
    count = len(points)
    for i in range(count):
        x, y, bulge = points[i]
        nx, ny, _ = points[(i + 1) % count]
        out.append((x, y))
        if abs(bulge) < 1e-12:
            continue
        center, _sa, _ea, radius = bulge_to_arc((x, y), (nx, ny), bulge)
        # Derive the sweep from the bulge itself rather than from the returned angles.
        # ezdxf normalises a NEGATIVE bulge by swapping the endpoints, so start_angle then
        # belongs to the far end and end_angle-start_angle traces the 270 deg complement of a
        # 90 deg corner. That drew a loop at every reflex corner and over-counted cut length.
        # By definition bulge = tan(included_angle / 4), signed, so:
        start_angle = math.atan2(y - center.y, x - center.x)
        sweep = 4.0 * math.atan(bulge)
        for step in range(1, segments_per_arc):
            angle = start_angle + sweep * step / segments_per_arc
            out.append((center.x + radius * math.cos(angle), center.y + radius * math.sin(angle)))
    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass
class Issue:
    severity: str  # "ERROR" or "WARNING"
    code: str
    message: str


def _check(issues: list[Issue], ok: bool, severity: str, code: str, message: str) -> None:
    if ok:
        LOG.debug("check PASS  %-24s %s", code, message)
    else:
        issues.append(Issue(severity, code, message))
        LOG.log(logging.ERROR if severity == "ERROR" else logging.WARNING, "check %s %-22s %s", severity, code, message)


def validate(params: BracketParams, geom: Geometry) -> list[Issue]:
    """Every constraint that could put a part in the bin. ERROR blocks file output."""
    issues: list[Issue] = []
    flat = geom.flat
    t = MATERIAL.thickness

    LOG.info("Validating flat pattern against SendCutSend and design constraints")

    # --- magnet spacing: the load-bearing dimension (CLAUDE.md 1.2) -------------------
    for axis, spacing in (("X", params.magnet_spacing_x), ("Y", params.magnet_spacing_y)):
        _check(
            issues, spacing >= params.min_magnet_spacing - 1e-9, "ERROR", f"magnet_spacing_{axis}",
            f"magnet spacing {axis} = {spacing:.1f} mm vs floor {params.min_magnet_spacing:.1f} mm. "
            f"THIS IS A LOAD-BEARING DIMENSION: torsion force per side scales as 1/spacing.",
        )

    # --- bend forming ----------------------------------------------------------------
    for name, length in (("arm", flat.arm_flat), ("neck", flat.neck_flat)):
        _check(
            issues, length >= MATERIAL.min_flange, "ERROR", f"flange_{name}",
            f"{name} flat flange {length:.2f} mm < minimum {MATERIAL.min_flange:.2f} mm "
            f"(their published minimum FORMED flange for this thickness)",
        )

    clearance = MATERIAL.bend_clearance
    # Features live on both sides of the bend now (arm magnets above it, everything else below),
    # so measure the unsigned distance from the bend centerline.
    candidates: list[tuple[float, str]] = [(flat.neck_flat, "neck_shoulder"), (flat.arm_flat, "arm_tip")]
    for hole in list(geom.holes) + [geom.center_opening]:
        candidates.append((abs(hole.y - flat.bend_line_y) - hole.radius,
                           f"{hole.tag}@({hole.x:.0f},{hole.y:.0f})"))
    for win in geom.windows:
        x0, y0, x1, y1 = win.bounds
        candidates.append((min(abs(y0 - flat.bend_line_y), abs(y1 - flat.bend_line_y)), win.tag))
    nearest, nearest_tag = min(candidates, key=lambda c: c[0])
    _check(
        issues, nearest >= clearance, "ERROR", "bend_clearance",
        f"nearest cut feature ({nearest_tag}) is {nearest:.2f} mm from the bend centerline; "
        f"need >= {clearance:.2f} mm (half the {MATERIAL.die_width_in:.3f}\" die they use at this "
        f"thickness)",
    )

    # --- hole geometry ---------------------------------------------------------------
    for hole in geom.holes:
        _check(
            issues, hole.dia >= MATERIAL.min_hole_dia, "ERROR", f"hole_dia_{hole.tag}",
            f"{hole.tag} hole dia {hole.dia:.2f} mm < laser minimum {MATERIAL.min_hole_dia:.2f} mm",
        )
        rx0, ry0, rx1, ry1 = geom.regions[hole.region]
        edge_gap = min(hole.x - rx0, hole.y - ry0, rx1 - hole.x, ry1 - hole.y) - hole.radius
        _check(
            issues, edge_gap >= MATERIAL.min_edge_distance, "ERROR", f"hole_edge_{hole.tag}",
            f"{hole.tag} hole at ({hole.x:.1f}, {hole.y:.1f}) is {edge_gap:.2f} mm from the "
            f"{hole.region} edge; "
            f"need >= {MATERIAL.min_edge_distance:.2f} mm (2x thickness)",
        )
        # Hole-to-hole. There was NO such check, and a CLI default silently re-enabled a spare
        # row on top of a fitted one — shipping two pairs of holes 0.02 mm apart into the cut
        # file, which validation and the audit both passed. Web-to-web must be at least 1x
        # thickness, and anything closer than that (including near-coincident duplicates from two
        # code paths computing the same row) is now an error.
        for other in geom.holes:
            if other is hole:
                continue
            web = math.hypot(hole.x - other.x, hole.y - other.y) - hole.radius - other.radius
            _check(
                issues, web >= t, "ERROR", f"hole_hole_{hole.tag}",
                f"{hole.tag} hole at ({hole.x:.2f}, {hole.y:.2f}) leaves only {web:.2f} mm of web "
                f"to {other.tag} at ({other.x:.2f}, {other.y:.2f}); need >= {t:.2f} mm "
                f"(1x thickness). A near-zero value means two code paths emitted the same hole.",
            )
        for win in geom.windows:
            gap = win.distance_to_point(hole.x, hole.y) - hole.radius
            _check(
                issues, gap >= t, "ERROR", f"hole_window_{hole.tag}",
                f"{hole.tag} hole at ({hole.x:.1f}, {hole.y:.1f}) is {gap:.2f} mm from window "
                f"{win.tag}; need >= {t:.2f} mm (1x thickness)",
            )
        center_clear = math.hypot(hole.x - geom.center_opening.x, hole.y - geom.center_opening.y) \
            - geom.center_opening.radius - hole.radius
        _check(
            issues, center_clear >= MATERIAL.min_edge_distance, "ERROR", f"hole_center_{hole.tag}",
            f"{hole.tag} hole is {center_clear:.2f} mm from the centre vent; need >= "
            f"{MATERIAL.min_edge_distance:.2f} mm",
        )

    # --- windows ---------------------------------------------------------------------
    for win in geom.windows:
        x0, y0, x1, y1 = win.bounds
        rx0, ry0, rx1, ry1 = geom.regions[win.region]
        edge_gap = min(x0 - rx0, y0 - ry0, rx1 - x1, ry1 - y1)
        _check(
            issues, edge_gap >= MATERIAL.min_edge_distance, "ERROR", f"window_edge_{win.tag}",
            f"window {win.tag} is {edge_gap:.2f} mm from the {win.region} edge; need >= "
            f"{MATERIAL.min_edge_distance:.2f} mm",
        )
        center_gap = win.distance_to_point(geom.center_opening.x, geom.center_opening.y) \
            - geom.center_opening.radius
        _check(
            issues, center_gap >= MATERIAL.min_edge_distance, "ERROR", f"window_center_{win.tag}",
            f"window {win.tag} is {center_gap:.2f} mm from the centre vent; need >= "
            f"{MATERIAL.min_edge_distance:.2f} mm",
        )

    # --- magnet discs (physical hardware, not cut geometry) --------------------------
    # Distance from each disc centre to the REAL filleted outline, not the region rectangle. A
    # rectangle check passes a disc that pokes past a corner fillet — the corner is exactly where
    # a magnet pushed toward the edge runs out of plate first.
    outline_pts = flatten_bulged(
        fillet_polygon(geom.outline, params.outer_fillet, params.reflex_fillet, "overhang-check"),
        segments_per_arc=48)

    def distance_to_outline(px: float, py: float) -> float:
        best = float("inf")
        n = len(outline_pts)
        for i in range(n):
            ax, ay = outline_pts[i]
            bx, by = outline_pts[(i + 1) % n]
            dx, dy = bx - ax, by - ay
            seg = dx * dx + dy * dy
            t = 0.0 if seg == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg))
            best = min(best, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
        return best

    for disc in geom.magnet_discs:
        rx0, ry0, rx1, ry1 = geom.regions[disc.region]
        overhang = max(rx0 + disc.radius - disc.x, ry0 + disc.radius - disc.y,
                       disc.x + disc.radius - rx1, disc.y + disc.radius - ry1,
                       disc.radius - distance_to_outline(disc.x, disc.y))
        _check(
            issues, overhang <= 0.0, "ERROR", "magnet_overhang",
            f"O{disc.dia:.0f} magnet at ({disc.x:.1f}, {disc.y:.1f}) overhangs the {disc.region} "
            f"edge by {overhang:.2f} mm; increase the inset or the plate size",
        )
        for win in geom.windows:
            gap = win.distance_to_point(disc.x, disc.y) - disc.radius
            _check(
                issues, gap >= 0.0, "WARNING", "magnet_window_overlap",
                f"magnet disc at ({disc.x:.1f}, {disc.y:.1f}) overlaps window {win.tag} by "
                f"{-gap:.2f} mm — the magnet face would sit over a hole",
            )

    # --- sheet size ------------------------------------------------------------------
    short, long = sorted((flat.width, flat.height))
    max_short, max_long = MATERIAL.sheet_max
    _check(
        issues, short <= max_short and long <= max_long, "ERROR", "sheet_size",
        f"flat pattern {flat.width:.1f} x {flat.height:.1f} mm exceeds the "
        f"{max_short:.0f} x {max_long:.0f} mm instant-pricing sheet",
    )

    # --- soft goods ------------------------------------------------------------------
    # The arm pad has two things to absorb at once and they STACK: lift-off from the corner-radius
    # mismatch, and the rise of the crowned top under the arm's reach.
    envelope_gap = flat_gap(params.fridge_corner_radius_max, MATERIAL.bend_radius)
    crown = crown_rise_at(params.arm_len, params.fridge_top_width, params.crown_rise)
    pad_budget = envelope_gap + crown
    _check(
        issues, params.arm_pad >= pad_budget * 1.2, "ERROR", "arm_pad",
        f"arm sponge pad {params.arm_pad:.2f} mm must cover the flat gap "
        f"{envelope_gap:.2f} mm at the design envelope R_f = {params.fridge_corner_radius_max:.0f} mm "
        f"PLUS {crown:.2f} mm of crown rise over a {params.arm_len:.0f} mm reach = "
        f"{pad_budget:.2f} mm, with compression to spare (>= 1.2x)",
    )
    if params.arm_magnets:
        arm_excess = params.arm_pad - params.arm_magnet_standoff
        _check(
            issues, -PAD_UNDERSIZE_ALLOWANCE_MM <= arm_excess <= 0.30, "ERROR", "arm_pad_standoff",
            f"arm pad {params.arm_pad:.2f} mm vs arm magnet height "
            f"{params.arm_magnet_standoff:.2f} mm: excess {arm_excess:+.2f} mm must be "
            f"{-PAD_UNDERSIZE_ALLOWANCE_MM:+.2f} to +0.30 mm (same invariant as the bottom pad)",
        )
        arm_disc_gap = params.arm_magnet_spacing - params.arm_magnet_disc_dia
        _check(
            issues, arm_disc_gap >= MATERIAL.thickness, "ERROR", "arm_magnet_gap",
            f"arm magnet discs are {arm_disc_gap:.2f} mm apart; need >= {MATERIAL.thickness:.2f} mm "
            f"so they seat independently on a crowned top",
        )
    # BOUNDS INVERTED 2026-08-27. The old rule allowed the pad to sit up to 2.5 mm PROUD of the
    # magnet and rejected anything under. That is backwards for a joint that has to feel rigid:
    # proud means the plate lands on the pad, the magnets never reach the panel, and the mount is
    # both spongier and weaker. A little UNDER is correct — the rigid magnets bear and the pad
    # protects paint across a hair of gap the paint stack closes.
    # Arm WIDTH runs front-to-back, and the hinge cover eats the front of the top. This is the
    # constraint the checklist called the likeliest recut risk.
    window_gap = params.top_clear_window - params.neck_w
    _check(
        issues, window_gap >= 0.0, "ERROR", "arm_width_vs_hinge_cover",
        f"arm is {params.neck_w:.0f} mm wide front-to-back but the clear window from the rear "
        f"edge to the hinge cover is only {params.top_clear_window:.0f} mm: short by "
        f"{-window_gap:.0f} mm. The cover lifts slightly, so this is recoverable, but it is not "
        f"designed for.",
    )

    bottom_excess = params.bottom_pad_thickness - params.magnet_standoff
    _check(
        issues, -PAD_UNDERSIZE_ALLOWANCE_MM <= bottom_excess <= 0.30, "ERROR", "bottom_pad",
        f"bottom pad {params.bottom_pad_thickness:.2f} mm vs magnet standoff "
        f"{params.magnet_standoff:.2f} mm: excess {bottom_excess:+.2f} mm must be "
        f"{-PAD_UNDERSIZE_ALLOWANCE_MM:+.2f} to +0.30 mm. Proud of the magnet holds the plate off "
        f"the panel; a little under lets the magnets bear, which is what makes it feel solid.",
    )

    # --- assembly stack --------------------------------------------------------------
    # Magnet screw heads face the display. What clears them is the spacer PLUS, for any head that
    # sits outside the raised rear box's footprint, the 25 mm the box holds the panel away. Check
    # each head against the box rather than assuming the spacer is the only gap.
    box_w, box_h = rear_box_footprint(params.orientation)
    bx0, bx1 = params.body_w / 2 - box_w / 2, params.body_w / 2 + box_w / 2
    by0, by1 = params.body_h / 2 - box_h / 2, params.body_h / 2 + box_h / 2
    for hole in (h for h in geom.holes if h.tag == "magnet"):
        under_box = bx0 <= hole.x <= bx1 and by0 <= hole.y <= by1
        clearance = params.spacer_len + (0.0 if under_box else DISPLAY.rear_box_depth)
        _check(
            issues, clearance > params.screw_head_height, "ERROR", "screw_head_clearance",
            f"magnet screw head at ({hole.x:.0f}, {hole.y:.0f}) has {clearance:.1f} mm to the "
            f"display ({'under the rear box' if under_box else 'clear of the box'}) but the head is "
            f"{params.screw_head_height:.1f} mm tall",
        )

    # --- countersink feasibility -------------------------------------------------------
    # SendCutSend cap countersink depth at 60% of material thickness. For a 90 deg profile the
    # depth is simply (major - hole)/2, so a THIN plate with a SMALL hole is the tight case —
    # which is exactly where a thin steel plate lands.
    if params.countersink_vesa:
        csk_depth = (params.countersink_major - params.vesa_hole_dia) / 2.0
        csk_limit = 0.6 * MATERIAL.thickness
        _check(
            issues, csk_depth <= csk_limit, "ERROR", "countersink_depth",
            f"M4 90 deg countersink needs {csk_depth:.2f} mm of depth into a "
            f"{MATERIAL.thickness:.2f} mm plate, but SendCutSend caps it at 60% = "
            f"{csk_limit:.2f} mm. Either open the VESA holes up (a bigger hole means a shallower "
            f"cone), use a thicker plate, or drop the countersinks and use low-head screws",
        )
        _check(
            issues, csk_depth <= csk_limit * 0.9, "WARNING", "countersink_margin",
            f"countersink depth {csk_depth:.2f} mm is within 10% of the {csk_limit:.2f} mm limit — "
            f"only {csk_limit - csk_depth:.2f} mm of slack. Confirm with SendCutSend before ordering",
        )
        _check(
            issues, MATERIAL.thickness - csk_depth >= 1.5, "WARNING", "countersink_remaining",
            f"only {MATERIAL.thickness - csk_depth:.2f} mm of plate left under the countersink cone",
        )

    # --- rear-face opening coverage (vent invariant, the specific case) ----------------
    # The rear box face carries the Pi's fan and GPIO at a fixed radius from the VESA centre. The
    # display can be hung in any 90 deg rotation, so check all four cardinal positions: a window
    # must cover the opening in each, or the plate blanks the Pi's cooling in that orientation.
    cx_v, cy_v = params.body_w / 2.0, params.body_h / 2.0
    feature_r = DISPLAY.rear_face_feature_dia / 2.0
    vents = [w for w in geom.windows if w.tag.startswith("vent")]
    for label, (fx_off, fy_off) in (
        ("+X", (DISPLAY.rear_face_feature_radius, 0.0)),
        ("-X", (-DISPLAY.rear_face_feature_radius, 0.0)),
        ("+Y", (0.0, DISPLAY.rear_face_feature_radius)),
        ("-Y", (0.0, -DISPLAY.rear_face_feature_radius)),
    ):
        if not vents:
            _check(issues, False, "WARNING", f"rear_vent_{label}",
                   "no vent windows: the display's rear-box opening is covered by solid plate. "
                   "Air can still escape radially through the 10 mm spacer plenum, which is open "
                   "on all four plate edges, but there is no direct path over the opening")
            continue
        fx, fy = cx_v + fx_off, cy_v + fy_off
        best = min(win.distance_to_point(fx, fy) for win in vents)
        margin = -best - feature_r  # distance_to_point is negative inside the window
        _check(
            issues, margin >= 0.0, "ERROR", f"rear_vent_{label}",
            f"rotation {label}: the rear box opening at plate ({fx:.0f}, {fy:.0f}) is not covered by "
            f"any vent window (short by {-margin:.2f} mm). The plate would blank the Pi's fan in "
            f"this orientation",
        )
        _check(
            issues, margin >= 5.0, "WARNING", f"rear_vent_margin_{label}",
            f"rotation {label}: only {margin:.2f} mm of window margin around the rear box opening; "
            f"its radius was scaled off a raster drawing to +/- 5 mm",
        )

    # --- fillet feasibility ----------------------------------------------------------
    # Building the rounded contours is itself a constraint check: a fillet whose tangent length
    # exceeds half an adjacent edge cannot be drawn. Do it here so --dry-run catches it rather
    # than the DXF writer crashing later.
    try:
        fillet_polygon(geom.outline, params.outer_fillet, params.reflex_fillet, "outline")
        for win in geom.windows:
            fillet_polygon(rounded_rect_points(win), win.r, win.r, f"window:{win.tag}")
        _check(issues, True, "ERROR", "fillet_feasible", "all corner fillets fit their edges")
    except ValueError as exc:
        _check(issues, False, "ERROR", "fillet_feasible", str(exc))

    # --- open area (vent invariant) --------------------------------------------------
    open_area = math.pi * geom.center_opening.radius ** 2 + sum(w.w * w.h for w in vents)
    open_fraction = open_area / (params.body_w * params.body_h)
    _check(
        issues, open_fraction >= 0.15, "WARNING", "vent_open_area",
        f"body is only {open_fraction * 100:.1f}% open; a Pi 5 behind a mostly-solid slab will throttle",
    )

    LOG.info(
        "Validation complete: %d error(s), %d warning(s)",
        sum(1 for i in issues if i.severity == "ERROR"),
        sum(1 for i in issues if i.severity == "WARNING"),
    )
    return issues


# ---------------------------------------------------------------------------
# Engineering report
# ---------------------------------------------------------------------------


def engineering_report(params: BracketParams, geom: Geometry) -> dict:
    """Load-path numbers. Everything derived from the parameters — no measured constants."""
    flat = geom.flat
    weight_lbf = DISPLAY.weight_lbf

    plate_area_mm2 = (
        params.body_w * params.body_h
        + params.neck_w * (flat.neck_flat + flat.arm_flat)
        - math.pi * geom.center_opening.radius ** 2
        - sum(w.w * w.h for w in geom.windows)
    )
    bracket_mass_kg = plate_area_mm2 * MATERIAL.thickness * MATERIAL.density_g_cc / 1e6
    bracket_lbf = bracket_mass_kg * LBF_PER_KG
    total_lbf = weight_lbf + bracket_lbf

    # Overturning moment about the fridge face: each mass acts at its own CG offset, so the
    # display (out past the spacers) and the plate itself (essentially on the face) are summed
    # separately rather than lumping the whole weight at the display's offset.
    bracket_cg_offset = params.magnet_standoff + MATERIAL.thickness / 2.0
    overturning_in_lbf = (weight_lbf * params.cg_offset + bracket_lbf * bracket_cg_offset) / MM_PER_INCH

    # 1.2 Touch torsion about the vertical spine axis.
    arm_in = params.torsion_arm / MM_PER_INCH
    moment_in_lbf = params.press_force_lbf * arm_in
    spacing_in = params.magnet_spacing_x / MM_PER_INCH
    force_per_side = moment_in_lbf / spacing_in
    force_per_magnet = force_per_side / 2.0

    # 1.3 Peel.
    peel_lbf = overturning_in_lbf / (params.peel_lever / MM_PER_INCH)

    # Magnet capacity: rated pull derated for thin sheet and standoff, then mu for shear.
    derated_pull = params.magnet_rated_pull_lbf * params.magnet_derate
    shear_rubber = derated_pull * params.mu_rubber
    shear_bare = derated_pull * params.mu_bare_nickel

    # Neck bending at the bend root: the hung weight acts at the CG offset from the plate face.
    neck_z_in3 = (params.neck_w / MM_PER_INCH) * (MATERIAL.thickness / MM_PER_INCH) ** 2 / 6.0
    neck_moment = overturning_in_lbf
    neck_stress_psi = neck_moment / neck_z_in3

    # Weak-axis check on the body plate: the torsion force travels out-of-plane from the VESA
    # screw to the magnet. Effective strip width is taken as the magnet disc diameter, which is
    # conservative — real load spreads wider than the disc.
    body_lever_in = (params.magnet_spacing_x / 2.0 - params.vesa / 2.0) / MM_PER_INCH
    body_z_in3 = (params.magnet_disc_dia / MM_PER_INCH) * (MATERIAL.thickness / MM_PER_INCH) ** 2 / 6.0
    body_moment = force_per_magnet * body_lever_in
    body_stress_psi = body_moment / body_z_in3

    # Cut length and area drive the SendCutSend quote, so report both: laser time scales with
    # cut length, material with the bounding rectangle.
    def contour_length(points: Sequence[tuple[float, float]]) -> float:
        return sum(math.dist(points[i], points[(i + 1) % len(points)]) for i in range(len(points)))

    cut_length = contour_length(
        flatten_bulged(fillet_polygon(geom.outline, params.outer_fillet, params.reflex_fillet, "quote-outline"),
                       segments_per_arc=64)
    )
    for win in geom.windows:
        cut_length += contour_length(
            flatten_bulged(fillet_polygon(rounded_rect_points(win), win.r, win.r, f"quote-{win.tag}"),
                           segments_per_arc=64)
        )
    cut_length += math.pi * geom.center_opening.dia
    cut_length += sum(math.pi * h.dia for h in geom.holes)

    gaps = {r: flat_gap(float(r), MATERIAL.bend_radius) for r in range(3, 21)}

    # Longest arm reach the specified pad can still absorb, given the corner gap already eats into
    # the budget. Scanned rather than solved: the parabola inverts messily and 1 mm is fine here.
    worst_gap_report = flat_gap(params.fridge_corner_radius_max, MATERIAL.bend_radius)
    crown_here = crown_rise_at(params.arm_len, params.fridge_top_width, params.crown_rise)
    max_covered_radius = 0.0
    for candidate in range(3, 61):
        if params.arm_pad >= (flat_gap(float(candidate), MATERIAL.bend_radius) + crown_here) * 1.2:
            max_covered_radius = float(candidate)
        else:
            break
    max_reach = 0.0
    for candidate in range(10, int(params.fridge_top_width / 2)):
        budget = worst_gap_report + crown_rise_at(float(candidate), params.fridge_top_width, params.crown_rise)
        if params.arm_pad >= budget * 1.2:
            max_reach = float(candidate)
        else:
            break

    report = {
        "display_weight_lbf": weight_lbf,
        "bracket_mass_kg": bracket_mass_kg,
        "bracket_weight_lbf": bracket_lbf,
        "total_hanging_lbf": total_lbf,
        "overturning_moment_in_lbf": overturning_in_lbf,
        "torsion_arm_mm": params.torsion_arm,
        "torsion_moment_in_lbf": moment_in_lbf,
        "magnet_spacing_mm": params.magnet_spacing_x,
        "torsion_force_per_side_lbf": force_per_side,
        "torsion_force_per_magnet_lbf": force_per_magnet,
        "cg_offset_mm": params.cg_offset,
        "peel_lever_mm": params.peel_lever,
        "peel_lbf": peel_lbf,
        "magnet_derated_pull_lbf": derated_pull,
        "magnet_shear_rubber_lbf": shear_rubber,
        "magnet_shear_bare_nickel_lbf": shear_bare,
        "magnet_tension_sf": derated_pull / force_per_magnet,
        "neck_stress_psi": neck_stress_psi,
        "neck_sf": MATERIAL.yield_psi / neck_stress_psi,
        "body_weak_axis_stress_psi": body_stress_psi,
        "body_weak_axis_sf": MATERIAL.yield_psi / body_stress_psi,
        "flat_gap_by_fridge_radius_mm": gaps,
        "worst_flat_gap_mm": max(gaps.values()),
        "arm_pad_thickness_mm": params.arm_pad,
        "crown_rise_under_arm_mm": crown_rise_at(params.arm_len, params.fridge_top_width, params.crown_rise),
        "arm_pad_budget_mm": flat_gap(params.fridge_corner_radius_max, MATERIAL.bend_radius)
            + crown_rise_at(params.arm_len, params.fridge_top_width, params.crown_rise),
        "fridge_corner_radius_envelope_mm": params.fridge_corner_radius_max,
        "max_arm_reach_mm": max_reach,
        "max_fridge_corner_radius_covered_mm": max_covered_radius,
        "bottom_pad_thickness_mm": params.bottom_pad_thickness,
        "power_budget_w": DISPLAY.watts + 27.0,
        "fridge_height_mm": params.fridge_height,
        "screen_centre_height_mm": params.screen_centre_height,
        "display_overhang_mm": params.display_overhang,
        "screen_top_landscape_mm": params.screen_centre_height + DISPLAY.height / 2.0,
        "screen_bottom_landscape_mm": params.screen_centre_height - DISPLAY.height / 2.0,
        "screen_top_portrait_mm": params.screen_centre_height + DISPLAY.width / 2.0,
        "screen_bottom_portrait_mm": params.screen_centre_height - DISPLAY.width / 2.0,
        "arm_magnets": params.arm_magnets,
        "material": MATERIAL.name,
        "thickness_in": MATERIAL.thickness_in,
        "countersink_depth_mm": (params.countersink_major - params.vesa_hole_dia) / 2.0,
        "countersink_limit_mm": 0.6 * MATERIAL.thickness,
        "display_mass_kg": DISPLAY.mass_kg,
        "display_wh_mm": [DISPLAY.width, DISPLAY.height],
        "display_overall_depth_mm": DISPLAY.depth,
        "display_centroid_from_box_face_mm": DISPLAY.centroid_from_box_face(),
        "rear_box_mm": [DISPLAY.rear_box_w, DISPLAY.rear_box_h, DISPLAY.rear_box_depth],
        "rear_face_feature_radius_mm": DISPLAY.rear_face_feature_radius,
        "cut_length_mm": cut_length,
        "plate_area_mm2": plate_area_mm2,
        "bounding_area_mm2": flat.width * flat.height,
    }

    LOG.info("Load path: hook bearing carries %.2f lbf; magnets carry zero vertical load", total_lbf)
    LOG.info(
        "Touch torsion: %.1f lbf at %.1f mm = %.1f in-lbf over %.0f mm spacing -> %.2f lbf/side (%.2f lbf/magnet)",
        params.press_force_lbf, params.torsion_arm, moment_in_lbf, params.magnet_spacing_x,
        force_per_side, force_per_magnet,
    )
    LOG.info("Peel: display %.2f lbf at d=%.1f mm + bracket %.2f lbf at d=%.1f mm (derived stack) "
             "= %.2f in-lbf over H=%.1f mm -> T=%.2f lbf",
             weight_lbf, params.cg_offset, bracket_lbf, bracket_cg_offset,
             overturning_in_lbf, params.peel_lever, peel_lbf)
    LOG.info("Magnet: %.1f lbf rated -> %.2f lbf derated pull; SF vs %.2f lbf tension = %.1fx",
             params.magnet_rated_pull_lbf, derated_pull, force_per_magnet, report["magnet_tension_sf"])
    LOG.info("Neck bending %.0f psi (SF %.0fx); body weak axis %.0f psi (SF %.0fx) vs %.0f psi yield",
             neck_stress_psi, report["neck_sf"], body_stress_psi, report["body_weak_axis_sf"], MATERIAL.yield_psi)
    LOG.info(
        "Height: fridge %.0f mm -> screen centre %.0f mm; landscape %.0f-%.0f, portrait %.0f-%.0f mm "
        "above the floor (display overhangs the body by %.1f mm this orientation)",
        params.fridge_height, params.screen_centre_height,
        report["screen_bottom_landscape_mm"], report["screen_top_landscape_mm"],
        report["screen_bottom_portrait_mm"], report["screen_top_portrait_mm"],
        params.display_overhang,
    )
    if params.arm_magnets:
        LOG.info("Fridge: Samsung RS23A500ASR counter-depth — case %.0f mm tall, %.0f mm wide, "
             "%.0f mm deep; hinge covers stand %.0f mm proud of the case top",
             params.fridge_height, params.fridge_top_width, params.fridge_depth,
             params.hinge_cover_proud)
    side_margin = (params.fridge_depth - DISPLAY.width) / 2.0
    LOG.info("Side panel is only %.0f mm deep (counter-depth). A %.0f mm landscape display leaves "
             "%.0f mm front and back if centred; the doors project a further %.0f mm forward",
             params.fridge_depth, DISPLAY.width, side_margin,
             params.fridge_depth_with_doors - params.fridge_depth)
    if params.arm_magnets:
        arm_offs = sorted({params.arm_magnet_offset, *params.extra_arm_magnet_offsets})
        LOG.info("Top-lip magnets: %d x O%.0f x %.0f mm at %s mm from the bend apex — no credit "
                 "in the VERTICAL load path, but they do resist peel (short lever)",
                 len(arm_offs) * 2, params.arm_magnet_disc_dia, params.arm_magnet_standoff,
                 "/".join(f"{o:.0f}" for o in arm_offs))
    LOG.info(
        "Arm pad budget: %.2f mm corner gap at the R_f=%.0f mm envelope + %.2f mm crown rise over a "
        "%.0f mm reach = %.2f mm; pad %.2f mm gives %.2fx. Longest reach this pad supports: %.0f mm",
        worst_gap_report, params.fridge_corner_radius_max, report["crown_rise_under_arm_mm"],
        params.arm_len, report["arm_pad_budget_mm"], params.arm_pad,
        params.arm_pad / report["arm_pad_budget_mm"], max_reach,
    )
    LOG.info("Arm pad %.2f mm covers a measured fridge corner radius up to R_f = %.0f mm at this reach",
             params.arm_pad, max_covered_radius)
    LOG.info(
        "Display profile: %.0f mm panel + %.0f mm raised rear box (%.0f x %.0f) = %.0f mm overall; "
        "CG sits %.1f mm out from the box face, so d = %.1f mm from the fridge",
        DISPLAY.panel_depth, DISPLAY.rear_box_depth, DISPLAY.rear_box_w, DISPLAY.rear_box_h,
        DISPLAY.depth, DISPLAY.centroid_from_box_face(), params.cg_offset,
    )
    LOG.info("Quote drivers: bounding %.1f x %.1f mm = %.0f cm2, cut area %.0f cm2, "
             "cut length %.0f mm (%.1f in)",
             flat.width, flat.height, flat.width * flat.height / 100.0, plate_area_mm2 / 100.0,
             cut_length, cut_length / MM_PER_INCH)
    LOG.debug("flat_gap sweep R_f=3..20 mm: %s", {k: round(v, 3) for k, v in gaps.items()})
    return report


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def write_dxf(path: Path, params: BracketParams, geom: Geometry) -> None:
    """Layer 0 only, millimetres, every contour closed, no bend line (placed in the web tool)."""
    doc = ezdxf.new("R2010", setup=True)  # setup=True registers the standard DASHED linetype
    doc.header["$INSUNITS"] = INSUNITS_MILLIMETERS
    doc.header["$MEASUREMENT"] = 1
    msp = doc.modelspace()
    attribs = {"layer": REQUIRED_LAYER}

    outline = fillet_polygon(geom.outline, params.outer_fillet, params.reflex_fillet, "outline")
    msp.add_lwpolyline(outline, format="xyb", close=True, dxfattribs=attribs)
    LOG.info("DXF: outline written as closed LWPOLYLINE with %d vertices", len(outline))

    for win in geom.windows:
        pts = fillet_polygon(rounded_rect_points(win), win.r, win.r, f"window:{win.tag}")
        msp.add_lwpolyline(pts, format="xyb", close=True, dxfattribs=attribs)
    n_vent = sum(1 for w in geom.windows if w.tag.startswith("vent"))
    LOG.info("DXF: %d vent windows and %d strap slots written",
             n_vent, len(geom.windows) - n_vent)

    msp.add_circle((geom.center_opening.x, geom.center_opening.y), geom.center_opening.radius, dxfattribs=attribs)
    for hole in geom.holes:
        msp.add_circle((hole.x, hole.y), hole.radius, dxfattribs=attribs)
    LOG.info("DXF: %d circles written (1 centre vent + %d holes)", len(geom.holes) + 1, len(geom.holes))

    if params.bend_line:
        # A dashed LINE at the bend centre, spanning exactly the bend length (the neck width).
        # This is the one entity in the file that is NOT a cut: SendCutSend reads it as the bend
        # location and it is consumed by their bending tool.
        x0 = (params.body_w - params.neck_w) / 2.0
        x1 = x0 + params.neck_w
        y = geom.flat.bend_line_y
        msp.add_line((x0, y), (x1, y),
                     dxfattribs={"layer": REQUIRED_LAYER, "linetype": "DASHED"})
        LOG.info("DXF: bend line written as a DASHED LINE at y=%.3f, x %.1f -> %.1f (%.0f mm long)",
                 y, x0, x1, x1 - x0)
    else:
        LOG.warning("DXF: NO bend line written — SendCutSend's app will grey out Bending")

    doc.saveas(path)
    LOG.info("Wrote %s", path)


def _svg_polyline(points: Sequence[tuple[float, float]], **attrs: str) -> str:
    body = " ".join(f"{x:.3f},{y:.3f}" for x, y in points)
    extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<polygon points="{body}" {extra}/>'


def _svg_text(x: float, y: float, text: str, size: float = 9.0, anchor: str = "middle",
              fill: str = "#111", weight: str = "normal", rotate: float = 0.0) -> str:
    transform = f' transform="rotate({rotate:.1f} {x:.2f} {y:.2f})"' if rotate else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"'
            f'{transform}>{text}</text>')


def _svg_text_masked(x: float, y: float, text: str, size: float = 9.0, anchor: str = "middle",
                     fill: str = "#111", bg: str = "#efefe9") -> str:
    """Label with an opaque pad behind it, for text that must overlie geometry.

    The region labels sit in the middle of the neck and arm, which is exactly where the strap
    slots and the bend centreline are, so they came out struck through.
    """
    wpx = _text_width(text, size)
    x0 = {"middle": x - wpx / 2.0, "end": x - wpx, "start": x}[anchor] - 4.0
    return (f'<rect x="{x0:.2f}" y="{y - size * 0.86:.2f}" width="{wpx + 8:.2f}" '
            f'height="{size * 1.22:.2f}" fill="{bg}" fill-opacity="0.92" rx="2"/>'
            + _svg_text(x, y, text, size=size, anchor=anchor, fill=fill))


def _dim_horizontal(y: float, x0: float, x1: float, label: str, flip_h: float, colour: str = "#0a7") -> str:
    """Dimension line in flat-pattern space; caller supplies the SVG y already flipped."""
    parts = [f'<line x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}" stroke="{colour}" stroke-width="0.6"/>']
    for x in (x0, x1):
        parts.append(f'<line x1="{x:.2f}" y1="{y - 3:.2f}" x2="{x:.2f}" y2="{y + 3:.2f}" stroke="{colour}" stroke-width="0.6"/>')
    parts.append(_svg_text((x0 + x1) / 2, y - 3, label, size=8.5, fill=colour))
    return "".join(parts)


def _dim_vertical(x: float, y0: float, y1: float, label: str, colour: str = "#0a7") -> str:
    parts = [f'<line x1="{x:.2f}" y1="{y0:.2f}" x2="{x:.2f}" y2="{y1:.2f}" stroke="{colour}" stroke-width="0.6"/>']
    for y in (y0, y1):
        parts.append(f'<line x1="{x - 3:.2f}" y1="{y:.2f}" x2="{x + 3:.2f}" y2="{y:.2f}" stroke="{colour}" stroke-width="0.6"/>')
    parts.append(_svg_text(x - 4, (y0 + y1) / 2, label, size=8.5, anchor="middle", fill=colour, rotate=-90))
    return "".join(parts)


# Mean advance width of Helvetica/Arial as a fraction of the em, for mixed-case text. Used only
# to reserve layout space, never to position glyphs, so an approximation is honest here — it is
# rounded UP so the reservation errs toward too much room rather than a truncated legend.
_HELVETICA_MEAN_ADVANCE = 0.55


def _text_width(text: str, size: float) -> float:
    """Approximate rendered width of `text` at `size` px, for reserving layout space."""
    return len(text) * size * _HELVETICA_MEAN_ADVANCE


def _preview_legend_entries(params: BracketParams, geom: Geometry) -> list[tuple]:
    """Legend rows for the reference preview: (swatch kind, colour, radius, text lines).

    Split out so the drawing can measure the legend BEFORE it decides where the side elevation
    goes. Everything here is hardware rather than cut geometry, which is why it is explained in a
    legend rather than labelled in place — an in-place label can collide with a vent window.
    """
    box_w, box_h = rear_box_footprint(params.orientation)
    return [
        ("circle", "#c0169a", 6.0, [
            f"O{params.magnet_disc_dia:.0f} x {params.magnet_standoff:.0f} body / "
            f"O{params.arm_magnet_disc_dia:.0f} x {params.arm_magnet_standoff:.0f} arm",
            "pot-magnet footprints (hardware, not cut)"]),
        ("circle", "#1a5fb4", 2.25, [
            f"O{params.vesa_hole_dia:.1f} VESA {params.vesa:.0f} x {params.vesa:.0f} + "
            + " + ".join(f"{int(w)}x{int(h)}" for w, h, _ in params.extra_vesa),
            ("countersunk 90 deg on the fridge face" if params.countersink_vesa
             else "NOT countersunk — use low-head screws")]),
        ("circle", "#1a5fb4", 2.5, [
            f"{params.strap_slot_thickness:.0f} x {params.strap_slot_length:.0f} strap slots, "
            f"{params.cable_tie_neck_pairs + params.cable_tie_arm_pairs} pairs up the",
            "neck and arm — captures the power lead"]),
        ("circle", "#c0169a", 2.25, [
            f"O{params.magnet_hole_dia:.1f} magnet hole (M6 clearance),",
            "never countersunk"]),
        ("circle", "#a8630f", 6.0, [
            "Pi fan / GPIO opening in the display's rear box,",
            f"R{DISPLAY.rear_face_feature_radius:.0f} from the VESA centre — drawn in all four",
            "rotations. A vent window covers it in each."]),
        ("rect", "#8a9199", 0.0, [
            f"Display rear box {box_w:.0f} x {box_h:.0f} mm as mounted ({params.orientation}),",
            f"standing {DISPLAY.rear_box_depth:.0f} mm proud of the panel.",
            "The plate lands on this."]),
    ]


def write_svg(path: Path, params: BracketParams, geom: Geometry, report: dict, dxf_name: str) -> None:
    """Annotated reference drawing: flat pattern on the left, hook side elevation on the right.

    Explicitly NOT an upload file — the banner says so and the bend line is drawn, which the
    DXF deliberately omits.
    """
    flat = geom.flat
    scale = 0.55
    fridge_w = 260.0
    # Drawn fridge height follows the bracket so a long neck cannot run off the schematic.
    fridge_h = params.neck_len + params.body_h + 150.0

    margin_l, margin_t = 96.0, 112.0

    # The legend sits in the gutter between the flat pattern and the side elevation. Its width is
    # set by its longest line, so DERIVE the gutter from that instead of hardcoding one: a
    # hardcoded 250 pt gutter silently ran the longest entries underneath the fridge drawing and
    # truncated them, which loses information rather than merely looking untidy.
    LEGEND_INDENT = 20.0          # swatch column, before the text starts
    LEGEND_OFFSET = 32.0          # from the flat pattern's right edge to the swatch
    LEGEND_SIZE = 8.5             # text size used for every legend line
    legend_entries = _preview_legend_entries(params, geom)
    legend_text_w = max(_text_width(line, LEGEND_SIZE)
                        for _, _, _, lines in legend_entries for line in lines)
    bend_gutter = max(250.0, LEGEND_OFFSET + LEGEND_INDENT + legend_text_w + 28.0)
    elev_x = margin_l + flat.width + bend_gutter + fridge_w * scale
    width = elev_x + 380.0
    notes_top = margin_t + flat.height + 88.0
    height = notes_top + 78.0

    def fx(x: float) -> float:
        return margin_l + x

    def fy(y: float) -> float:
        """Flat-pattern y (up-positive) -> SVG y (down-positive)."""
        return margin_t + flat.height - y

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}">',
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="#fbfbf9"/>',
        f'<rect x="0" y="0" width="{width:.0f}" height="32" fill="#b00020"/>',
        _svg_text(width / 2, 22, f"REFERENCE ONLY — DO NOT UPLOAD THIS FILE. Upload {dxf_name}.",
                  size=15, fill="#fff", weight="bold"),
        _svg_text(margin_l, 56,
                  f"Fridge-side display mount — flat pattern, {MATERIAL.name} "
                  f"{MATERIAL.thickness_in:.3f}\" ({MATERIAL.thickness:.2f} mm)",
                  size=14, anchor="start", weight="bold"),
        _svg_text(margin_l, 72,
                  f"{params.orientation} · formed arm {params.arm_len:.0f} + neck {params.neck_len:.0f} + body "
                  f"{params.body_h:.0f} mm · arm width {params.neck_w:.0f} mm · bend deduction "
                  f"{flat.bend_deduction:.2f} mm · flat {flat.width:.1f} x {flat.height:.1f} mm",
                  size=10.5, anchor="start", fill="#555"),
    ]

    # --- flat pattern ---------------------------------------------------------------
    outline_pts = flatten_bulged(fillet_polygon(geom.outline, params.outer_fillet, params.reflex_fillet, "svg-outline"))
    out.append(_svg_polyline([(fx(x), fy(y)) for x, y in outline_pts],
                             fill="#e9e9e3", stroke="#222", stroke_width="1.2"))
    for win in geom.windows:
        pts = flatten_bulged(fillet_polygon(rounded_rect_points(win), win.r, win.r, f"svg-{win.tag}"))
        out.append(_svg_polyline([(fx(x), fy(y)) for x, y in pts], fill="#fbfbf9", stroke="#222", stroke_width="1.0"))
    co = geom.center_opening
    out.append(f'<circle cx="{fx(co.x):.2f}" cy="{fy(co.y):.2f}" r="{co.radius:.2f}" fill="#fbfbf9" '
               f'stroke="#222" stroke-width="1.0"/>')
    for disc in geom.magnet_discs:
        out.append(f'<circle cx="{fx(disc.x):.2f}" cy="{fy(disc.y):.2f}" r="{disc.radius:.2f}" fill="#c0169a" '
                   f'fill-opacity="0.10" stroke="#c0169a" stroke-width="0.9" stroke-dasharray="4 3"/>')
    for hole in geom.holes:
        colour = "#c0169a" if "magnet" in hole.tag else "#1a5fb4"
        out.append(f'<circle cx="{fx(hole.x):.2f}" cy="{fy(hole.y):.2f}" r="{hole.radius:.2f}" fill="#fff" '
                   f'stroke="{colour}" stroke-width="1.0"/>')

    # --- bend line ------------------------------------------------------------------
    by = fy(flat.bend_line_y)
    out.append(f'<line x1="{fx(-32):.2f}" y1="{by:.2f}" x2="{fx(flat.width + 26):.2f}" y2="{by:.2f}" '
               f'stroke="#b00020" stroke-width="1.4" stroke-dasharray="9 5"/>')
    out.append(_svg_text(fx(flat.width + 32), by - 4, "BEND CENTERLINE", size=10, anchor="start",
                         fill="#b00020", weight="bold"))
    out.append(_svg_text(fx(flat.width + 32), by + 9,
                         f"{flat.arm_flat:.2f} mm from the arm tip", size=8.5, anchor="start", fill="#b00020"))
    out.append(_svg_text(fx(flat.width + 32), by + 21,
                         f"90 deg, inside R {MATERIAL.bend_radius:.2f} mm", size=8.5, anchor="start", fill="#b00020"))
    out.append(_svg_text(fx(flat.width + 32), by + 33,
                         ("dashed LINE in the DXF — the app reads" if params.bend_line
                          else "NOT in the DXF — set it in their web tool"),
                         size=8.5, anchor="start", fill="#b00020"))
    out.append(_svg_text(fx(flat.width + 32), by + 45,
                         ("it and reports \"1 Bend\"" if params.bend_line
                          else "SendCutSend web bending tool"),
                         size=8.5, anchor="start", fill="#b00020"))

    # --- region labels --------------------------------------------------------------
    out.append(_svg_text_masked(fx(flat.width / 2), fy(flat.bend_line_y + 22.0),
                                "ARM — rests on the fridge top", size=9.5, fill="#666"))
    out.append(_svg_text_masked(fx(flat.width / 2), fy(params.body_h + flat.neck_flat / 2),
                                "NECK", size=9.5, fill="#666"))
    out.append(_svg_text_masked(fx(flat.width / 2), fy(params.body_h - 8.0),
                                "BODY — vertical spine", size=9, fill="#666"))
    # Rear box footprint and the Pi fan / GPIO opening it carries, in all four rotations — this is
    # what the vent windows are positioned against, so show it rather than assert it.
    svg_box_w, svg_box_h = rear_box_footprint(params.orientation)
    box_x0 = fx(params.body_w / 2 - svg_box_w / 2)
    box_y1 = fy(params.body_h / 2 + svg_box_h / 2)
    out.append(f'<rect x="{box_x0:.2f}" y="{box_y1:.2f}" width="{svg_box_w:.2f}" '
               f'height="{svg_box_h:.2f}" fill="none" stroke="#8a9199" stroke-width="0.9" '
               f'stroke-dasharray="7 4"/>')
    for dx_off, dy_off in ((DISPLAY.rear_face_feature_radius, 0.0), (-DISPLAY.rear_face_feature_radius, 0.0),
                           (0.0, DISPLAY.rear_face_feature_radius), (0.0, -DISPLAY.rear_face_feature_radius)):
        out.append(f'<circle cx="{fx(params.body_w / 2 + dx_off):.2f}" '
                   f'cy="{fy(params.body_h / 2 + dy_off):.2f}" '
                   f'r="{DISPLAY.rear_face_feature_dia / 2:.2f}" fill="#e8a33d" fill-opacity="0.35" '
                   f'stroke="#a8630f" stroke-width="1.0" stroke-dasharray="3 2"/>')

    out.append(_svg_text(fx(params.body_w / 2), fy(params.body_h / 2) + 3,
                         f"O{params.center_open_dia:.0f} vent", size=8.5, fill="#444"))

    # --- dimensions -----------------------------------------------------------------
    out.append(_dim_horizontal(fy(flat.height) - 26, fx((flat.width - params.neck_w) / 2),
                               fx((flat.width + params.neck_w) / 2), f"neck / arm width {params.neck_w:.0f}", 0))
    out.append(_dim_horizontal(fy(0) + 26, fx(params.magnet_inset), fx(flat.width - params.magnet_inset),
                               f"magnet spacing {params.magnet_spacing_x:.0f} "
                               f"(load-bearing, floor {params.min_magnet_spacing:.0f})", 0))
    out.append(_dim_horizontal(fy(0) + 48, fx(0), fx(flat.width), f"body width {flat.width:.1f}", 0))
    out.append(_dim_vertical(fx(-26), fy(0), fy(flat.height), f"flat {flat.height:.1f}"))
    out.append(_dim_vertical(fx(-56), fy(flat.height - flat.arm_flat), fy(flat.height), f"arm flat {flat.arm_flat:.2f}"))
    out.append(_dim_vertical(fx(-56), fy(params.body_h), fy(flat.height - flat.arm_flat), f"neck flat {flat.neck_flat:.2f}"))
    out.append(_dim_vertical(fx(-56), fy(0), fy(params.body_h), f"body {params.body_h:.0f}"))
    out.append(_dim_vertical(fx(flat.width + 16), fy(params.magnet_inset), fy(params.body_h - params.magnet_inset),
                             f"magnet spacing {params.magnet_spacing_y:.0f}"))

    # --- legend ---------------------------------------------------------------------
    # Everything that is hardware rather than cut geometry gets explained here rather than
    # labelled in place, so adding an entry can never collide with a vent window.
    legend_x, legend_y = fx(flat.width + LEGEND_OFFSET), by + 94
    out.append(_svg_text(legend_x, legend_y - 16, "LEGEND", size=9, anchor="start",
                         weight="bold", fill="#444"))
    row_y = legend_y
    for kind, colour, radius, lines in legend_entries:
        if kind == "circle":
            out.append(f'<circle cx="{legend_x + 7:.2f}" cy="{row_y - 3:.2f}" r="{radius:.2f}" '
                       f'fill="{colour}" fill-opacity="0.2" stroke="{colour}" stroke-width="1" '
                       f'stroke-dasharray="{"3 2" if radius > 4 else "none"}"/>')
        else:
            out.append(f'<rect x="{legend_x + 1:.2f}" y="{row_y - 9:.2f}" width="12" height="10" '
                       f'fill="none" stroke="{colour}" stroke-width="1" stroke-dasharray="4 2"/>')
        for i, line in enumerate(lines):
            out.append(_svg_text(legend_x + LEGEND_INDENT, row_y + i * 11, line,
                                 size=LEGEND_SIZE, anchor="start", fill=colour))
        row_y += len(lines) * 11 + 8

    # --- side elevation -------------------------------------------------------------
    elev_y = margin_t + 70.0
    rf = params.fridge_corner_radius
    pad, standoff = params.arm_pad, params.magnet_standoff

    def sx(v: float) -> float:
        return elev_x + v * scale

    def sy(v: float) -> float:
        return elev_y + v * scale

    out.append(_svg_text(elev_x - fridge_w * scale, elev_y - 58,
                         "SIDE ELEVATION — hook load path", size=13, anchor="start", weight="bold"))
    out.append(_svg_text(elev_x - fridge_w * scale, elev_y - 43,
                         f"schematic, {scale:.2f}x. Vertical load bears at the top corner; magnets carry none.",
                         size=9, anchor="start", fill="#555"))

    out.append(
        f'<path d="M {sx(-fridge_w):.2f} {sy(0):.2f} H {sx(-rf):.2f} '
        f'A {rf * scale:.2f} {rf * scale:.2f} 0 0 1 {sx(0):.2f} {sy(rf):.2f} '
        f'V {sy(fridge_h):.2f} H {sx(-fridge_w):.2f} Z" fill="#dfe3e6" stroke="#8a9199" stroke-width="1"/>'
    )
    out.append(_svg_text(sx(-fridge_w / 2), sy(fridge_h * 0.78), "REFRIGERATOR", size=10, fill="#6a737b"))
    out.append(_svg_text(sx(-fridge_w / 2), sy(fridge_h * 0.78) + 14,
                         f"top corner R_f = {rf:.0f} mm", size=8.5, fill="#6a737b"))
    out.append(_svg_text(sx(-fridge_w / 2), sy(fridge_h * 0.78) + 26,
                         "MEASURE THIS", size=8.5, fill="#b00020", weight="bold"))

    # Bracket section: arm along the fridge top, then down the side face.
    arm_x0 = -params.arm_len
    body_bottom = params.neck_len + params.body_h
    out.append(
        f'<path d="M {sx(arm_x0):.2f} {sy(-pad):.2f} H {sx(standoff):.2f} '
        f'V {sy(body_bottom):.2f} H {sx(standoff + MATERIAL.thickness):.2f} '
        f'V {sy(-pad - MATERIAL.thickness):.2f} H {sx(arm_x0):.2f} Z" '
        f'fill="#9a5b00" stroke="#5d3600" stroke-width="0.8"/>'
    )
    out.append(f'<rect x="{sx(arm_x0):.2f}" y="{sy(-pad):.2f}" width="{(standoff - arm_x0) * scale:.2f}" '
               f'height="{pad * scale:.2f}" fill="#f2c14e" fill-opacity="0.8" stroke="#a8830f" stroke-width="0.7"/>')
    out.append(_dim_horizontal(sy(-pad) - 14, sx(arm_x0), sx(0),
                               f"arm {params.arm_len:.0f} mm — set MID-DEPTH", 0, colour="#5d3600"))

    if params.arm_magnets:
        out.append(f'<rect x="{sx(-params.arm_magnet_offset - params.arm_magnet_disc_dia / 2):.2f}" '
                   f'y="{sy(-pad):.2f}" width="{params.arm_magnet_disc_dia * scale:.2f}" '
                   f'height="{params.arm_magnet_standoff * scale:.2f}" fill="#c0169a" fill-opacity="0.30" '
                   f'stroke="#c0169a" stroke-width="0.8"/>')

    magnet_rows = [params.neck_len + params.magnet_inset, params.neck_len + params.body_h - params.magnet_inset]
    for my in magnet_rows:
        out.append(f'<rect x="{sx(0):.2f}" y="{sy(my - params.magnet_disc_dia / 2):.2f}" '
                   f'width="{standoff * scale:.2f}" height="{params.magnet_disc_dia * scale:.2f}" '
                   f'fill="#c0169a" fill-opacity="0.30" stroke="#c0169a" stroke-width="0.8"/>')
    out.append(f'<rect x="{sx(0):.2f}" y="{sy(body_bottom - 40.0):.2f}" width="{standoff * scale:.2f}" '
               f'height="{40.0 * scale:.2f}" fill="#f2c14e" fill-opacity="0.9" stroke="#a8830f" stroke-width="0.7"/>')

    # The display is not a slab: the bracket lands on a raised rear box and the panel stands
    # rear_box_depth further out again.
    display_x = standoff + MATERIAL.thickness + params.spacer_len
    display_top = params.neck_len - params.display_overhang
    display_span = DISPLAY.height if params.orientation == "landscape" else DISPLAY.width
    box_top = params.neck_len + params.body_h / 2.0 - DISPLAY.rear_box_h / 2.0
    out.append(f'<rect x="{sx(display_x):.2f}" y="{sy(box_top):.2f}" '
               f'width="{DISPLAY.rear_box_depth * scale:.2f}" '
               f'height="{DISPLAY.rear_box_h * scale:.2f}" fill="#3c3c3c" stroke="#000" stroke-width="0.8"/>')
    panel_x = display_x + DISPLAY.rear_box_depth
    out.append(f'<rect x="{sx(panel_x):.2f}" y="{sy(display_top):.2f}" '
               f'width="{DISPLAY.panel_depth * scale:.2f}" '
               f'height="{display_span * scale:.2f}" fill="#2b2b2b" stroke="#000" stroke-width="0.8"/>')
    for tick in range(10):  # the rear box's side-wall vent grille
        ty = box_top + 18.0 + tick * (DISPLAY.rear_box_h - 36.0) / 9.0
        out.append(f'<line x1="{sx(display_x + 5):.2f}" y1="{sy(ty):.2f}" '
                   f'x2="{sx(display_x + DISPLAY.rear_box_depth - 4):.2f}" y2="{sy(ty):.2f}" '
                   f'stroke="#8a9199" stroke-width="0.7"/>')
    out.append(_svg_text(sx(panel_x + DISPLAY.panel_depth + 6), sy(box_top) - 4,
                         f"rear box {DISPLAY.rear_box_w:.0f} x {DISPLAY.rear_box_h:.0f} x "
                         f"{DISPLAY.rear_box_depth:.0f} mm — VESA lands here", size=8, anchor="start",
                         fill="#555"))
    for vesa_y in (params.neck_len + params.body_h / 2 - params.vesa / 2,
                   params.neck_len + params.body_h / 2 + params.vesa / 2):
        out.append(f'<line x1="{sx(standoff + MATERIAL.thickness):.2f}" y1="{sy(vesa_y):.2f}" '
                   f'x2="{sx(display_x):.2f}" y2="{sy(vesa_y):.2f}" stroke="#1a5fb4" stroke-width="2.4"/>')
    cg_x = standoff + MATERIAL.thickness + params.spacer_len + DISPLAY.centroid_from_box_face()
    cg_y = params.neck_len + params.body_h / 2.0
    out.append(f'<line x1="{sx(0):.2f}" y1="{sy(cg_y):.2f}" x2="{sx(cg_x):.2f}" y2="{sy(cg_y):.2f}" '
               f'stroke="#b00020" stroke-width="0.8" stroke-dasharray="3 3"/>')
    out.append(f'<circle cx="{sx(cg_x):.2f}" cy="{sy(cg_y):.2f}" r="4.5" fill="#fbfbf9" stroke="#b00020" '
               f'stroke-width="1.5"/>')
    out.append(_svg_text(sx(cg_x + 9) + 22, sy(cg_y) + 13, f"display CG — d = {params.cg_offset:.1f} mm",
                         size=8, anchor="start", fill="#b00020"))

    # Elevation callouts, stacked in one column so nothing overlaps the drawing.
    callouts = [
        ("#8a6a10", f"closed-cell sponge arm pad {pad:.2f} mm (1/4 in) — conforms to the top corner radius"),
        ("#c0169a", f"{len(sorted({params.arm_magnet_offset, *params.extra_arm_magnet_offsets})) * 2} x "
                    f"O{params.arm_magnet_disc_dia:.0f} x {params.arm_magnet_standoff:.0f} mm top-lip "
                    f"magnets, same SKU as the body — zero VERTICAL load, but they do resist peel"),
        ("#c0169a", f"{len([h for h in geom.magnet_discs if h.region == 'body'])} x "
                    f"O{params.magnet_disc_dia:.0f} x {params.magnet_standoff:.0f} mm BARE nickel pot "
                    f"magnets, M6 female thread — tape the fridge, not the magnet"),
        ("#8a6a10", f"bottom bearing pad {params.bottom_pad_thickness:.2f} mm, "
                    f"{params.bottom_pad_thickness - params.magnet_standoff:+.2f} mm proud of the magnets "
                    f"— sponge squashes flush"),
        ("#111", f"display {DISPLAY.depth:.0f} mm overall = {DISPLAY.panel_depth:.0f} mm panel + "
                 f"{DISPLAY.rear_box_depth:.0f} mm rear box, {DISPLAY.mass_kg:.2f} kg; CG offset "
                 f"d = {params.cg_offset:.1f} mm, volume-weighted across both sections"),
        ("#5d3600", f"{MATERIAL.name} plate {MATERIAL.thickness:.2f} mm, inside bend "
                    f"R {MATERIAL.bend_radius:.2f} mm"),
    ]
    callout_y = max(sy(fridge_h), sy(body_bottom), sy(display_top + DISPLAY.height)) + 26
    for i, (colour, text) in enumerate(callouts):
        y = callout_y + i * 14
        out.append(f'<rect x="{elev_x - fridge_w * scale:.2f}" y="{y - 7:.2f}" width="9" height="9" fill="{colour}"/>')
        out.append(_svg_text(elev_x - fridge_w * scale + 15, y, text, size=8.5, anchor="start", fill="#333"))

    # --- engineering notes ----------------------------------------------------------
    notes = [
        f"Vertical load {report['total_hanging_lbf']:.2f} lbf (display {report['display_weight_lbf']:.2f} + bracket "
        f"{report['bracket_weight_lbf']:.2f}) bears at the top corner. Magnets carry ZERO vertical load.",
        f"Touch torsion: {params.press_force_lbf:.0f} lbf at {params.torsion_arm:.0f} mm = "
        f"{report['torsion_moment_in_lbf']:.1f} in-lbf over {report['magnet_spacing_mm']:.0f} mm spacing -> "
        f"{report['torsion_force_per_side_lbf']:.2f} lbf/side, {report['torsion_force_per_magnet_lbf']:.2f} lbf/magnet "
        f"(SF {report['magnet_tension_sf']:.1f}x on {report['magnet_derated_pull_lbf']:.2f} lbf derated pull).",
        f"Peel {report['peel_lbf']:.2f} lbf over H = {report['peel_lever_mm']:.0f} mm — negligible, as expected. "
        f"Arm pad budget {report['arm_pad_budget_mm']:.2f} mm = corner gap at the "
        f"R_f = {params.fridge_corner_radius_max:.0f} mm envelope plus crown rise; the "
        f"{params.arm_pad:.2f} mm (1/4 in) pad gives "
        f"{params.arm_pad / report['arm_pad_budget_mm']:.2f}x and covers a measured R_f up to "
        f"{report['max_fridge_corner_radius_covered_mm']:.0f} mm.",
        f"Display is not a slab: {DISPLAY.panel_depth:.0f} mm panel + {DISPLAY.rear_box_depth:.0f} mm raised "
        f"rear box = {DISPLAY.depth:.0f} mm overall, VESA on the box. Vent windows sit at R"
        f"{params.window_radius:.0f} so one lands over the Pi fan opening in every 90 deg rotation.",
        f"Neck bending {report['neck_stress_psi']:.0f} psi (SF {report['neck_sf']:.0f}x); body weak axis "
        f"{report['body_weak_axis_stress_psi']:.0f} psi (SF {report['body_weak_axis_sf']:.0f}x) vs "
        f"{MATERIAL.yield_psi:.0f} psi yield. No ribs required.",
    ]
    out.append(f'<line x1="{margin_l:.0f}" y1="{notes_top - 14:.0f}" x2="{width - 40:.0f}" y2="{notes_top - 14:.0f}" '
               f'stroke="#ccc" stroke-width="1"/>')
    for i, note in enumerate(notes):
        out.append(_svg_text(margin_l, notes_top + i * 13, note, size=9, anchor="start", fill="#333"))

    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")
    LOG.info("Wrote %s (%d elements)", path, len(out))


def write_params_json(path: Path, params: BracketParams, geom: Geometry, report: dict) -> None:
    """Machine-readable expectations, consumed by audit_dxf.py as the acceptance baseline."""
    flat = geom.flat
    payload = {
        "material": {
            "name": MATERIAL.name,
            "thickness_mm": MATERIAL.thickness,
            "bend_radius_mm": MATERIAL.bend_radius,
            "k_factor": MATERIAL.k_factor,
        },
        "params": {k: getattr(params, k) for k in params.__dataclass_fields__},
        "flat": {
            "width_mm": flat.width,
            "height_mm": flat.height,
            "arm_flat_mm": flat.arm_flat,
            "neck_flat_mm": flat.neck_flat,
            "bend_line_y_mm": flat.bend_line_y,
            "bend_deduction_mm": flat.bend_deduction,
        },
        "expected_dxf": {
            "insunits": INSUNITS_MILLIMETERS,
            "layers": [REQUIRED_LAYER],
            "extents_mm": [0.0, 0.0, flat.width, flat.height],
            "bend_line_count": 1 if params.bend_line else 0,
            "bend_line_y_mm": geom.flat.bend_line_y,
            "bend_line_x_range_mm": [(params.body_w - params.neck_w) / 2.0,
                                      (params.body_w + params.neck_w) / 2.0],
            "lwpolyline_count": 1 + len(geom.windows),
            "circle_count": 1 + len(geom.holes),
            "hole_diameters_mm": sorted({round(h.dia, 4) for h in geom.holes}
                                        | {round(geom.center_opening.dia, 4)}),
        },
        "holes": [{"tag": h.tag, "x": h.x, "y": h.y, "dia": h.dia} for h in geom.holes],
        "windows": [{"tag": w.tag, "cx": w.cx, "cy": w.cy, "w": w.w, "h": w.h, "r": w.r} for w in geom.windows],
        "engineering": report,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
    LOG.info("Wrote %s", path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    defaults = BracketParams()
    p = argparse.ArgumentParser(
        description="Generate the flat-pattern DXF, preview SVG and parameter JSON for the fridge display mount.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--material", choices=tuple(MATERIALS), default="mild-steel",
                   help="plate material; changes bend radius, deduction and flange minimums")
    p.add_argument("--thickness", type=float, default=0.119,
                   help="plate thickness in inches, must be one SendCutSend publishes bend specs for")
    p.add_argument("--display", choices=tuple(DISPLAYS), default="23.8",
                   help="which Waveshare panel to generate for; both share the bracket geometry")
    p.add_argument("--orientation", choices=("landscape", "portrait"), default=defaults.orientation,
                   help="portrait is mechanically better: torsion arm drops from 278 to 162 mm")
    p.add_argument("--body-width", type=float, default=defaults.body_w)
    p.add_argument("--body-height", type=float, default=defaults.body_h)
    p.add_argument("--neck-width", type=float, default=defaults.neck_w)
    p.add_argument("--neck-length", type=float, default=defaults.neck_len,
                   help="MEASURE: (fridge top -> desired display top edge) - 12 mm")
    p.add_argument("--arm-length", type=float, default=defaults.arm_len)
    p.add_argument("--bend-deduction", type=float, default=0.0,
                   help="mm, from SendCutSend's bending calculator; 0 derives an estimate from K")
    p.add_argument("--magnet-inset", type=float, default=defaults.magnet_inset)
    p.add_argument("--fridge-corner-radius", type=float, default=defaults.fridge_corner_radius,
                   help="MEASURE: affects pad sizing only, never cut geometry")
    p.add_argument("--fridge-corner-radius-max", type=float, default=defaults.fridge_corner_radius_max,
                   help="design envelope the arm pad must cover, mm")
    p.add_argument("--arm-pad-thickness", type=float, default=0.0,
                   help="must equal the arm magnet height when arm magnets are fitted")
    p.add_argument("--fridge-height", type=float, default=defaults.fridge_height,
                   help="height to TOP OF CASE, not top of hinge. LG publishes 1750 mm (68 29/32 in) "
                        "for the 2706 side-by-sides; their 70 15/32 in figure is to the hinge top")
    p.add_argument("--screen-centre-height", type=float, default=None,
                   help="target height of the screen centre above the floor, mm. Given this, the "
                        "neck length is DERIVED and --neck-length is ignored")
    p.add_argument("--vesa-hole-dia", type=float, default=defaults.vesa_hole_dia,
                   help="VESA clearance hole diameter; a bigger hole gives a shallower countersink")
    p.add_argument("--countersink", action="store_true",
                   help="add VESA countersinks; on thin steel also pass --vesa-hole-dia 5.0")
    p.add_argument("--extra-magnet-rows", type=float, nargs="*", default=None,
                   help="extra magnet rows as body-y positions; each adds a left+right pair")
    p.add_argument("--no-cable-ties", action="store_true",
                   help="omit the cable tie-down holes")
    p.add_argument("--strap-width", type=float, default=None,
                   help="hook-and-loop strap width in mm (default %.2f = 1/2 in); the slot is this "
                        "plus 2x the clearance" % (0.5 * MM_PER_INCH))
    p.add_argument("--no-spare-holes", action="store_true",
                   help="omit the spare magnet holes (four mid-side, two on the arm)")
    p.add_argument("--no-windows", action="store_true",
                   help="omit the four vent windows (cost/appearance experiment)")
    p.add_argument("--no-bend-line", action="store_true",
                   help="omit the dashed bend line; SendCutSend's app will then refuse to offer bending")
    p.add_argument("--extra-arm-magnet-offsets", type=float, nargs="*", default=None,
                   help="extra rows of top-lip magnet PAIRS, as formed offsets from the bend apex")
    p.add_argument("--no-arm-magnets", action="store_true",
                   help="omit the two arm retention magnet holes")
    p.add_argument("--press-force", type=float, default=defaults.press_force_lbf,
                   help="assumed touch press at the outer screen edge, lbf")
    p.add_argument("--spacer-length", type=float, default=defaults.spacer_len)
    p.add_argument("--out-dir", type=Path, default=Path("."))
    p.add_argument("--name", default="",
                   help="variant suffix for the output filenames, e.g. --name reach180 writes "
                        "bracket_flat_reach180.dxf. Empty writes the unsuffixed default set")
    p.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    p.add_argument("--dry-run", action="store_true", help="validate and report, write nothing")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)
    LOG.info("Bracket generator starting (orientation=%s, log level=%s)", args.orientation, args.log_level)
    set_material(args.material, args.thickness)
    set_display(args.display)

    neck_len = args.neck_length
    if args.screen_centre_height is not None:
        neck_len = args.fridge_height - args.screen_centre_height - args.body_height / 2.0
        LOG.info(
            "Neck derived from height target: %.1f (fridge) - %.1f (screen centre) - %.1f (half body) "
            "= %.2f mm, overriding --neck-length %.1f",
            args.fridge_height, args.screen_centre_height, args.body_height / 2.0, neck_len, args.neck_length,
        )

    params = BracketParams(
        orientation=args.orientation,
        body_w=args.body_width,
        body_h=args.body_height,
        neck_w=args.neck_width,
        neck_len=neck_len,
        fridge_height=args.fridge_height,
        arm_magnets=not args.no_arm_magnets,
        bend_line=not args.no_bend_line,
        vent_windows=not args.no_windows,
        # A store_true flag is False when absent, so `not args.no_spare_holes` silently forced
        # these back to True and OVERRODE the dataclass defaults. That is the third time this
        # project has been bitten by a CLI default quietly replacing a real default. The flag may
        # only ever turn these OFF; when it is absent the dataclass governs.
        **({"spare_mid_holes": False, "spare_arm_holes": False} if args.no_spare_holes else {}),
        **({"strap_width": args.strap_width} if args.strap_width else {}),
        cable_ties=not args.no_cable_ties,
        **({"extra_magnet_rows": tuple(args.extra_magnet_rows)}
           if args.extra_magnet_rows is not None else {}),
        **({"extra_arm_magnet_offsets": tuple(args.extra_arm_magnet_offsets)}
           if args.extra_arm_magnet_offsets is not None else {}),
        vesa_hole_dia=args.vesa_hole_dia,
        countersink_vesa=args.countersink,
        arm_len=args.arm_length,
        bend_deduction=args.bend_deduction,
        magnet_inset=args.magnet_inset,
        fridge_corner_radius=args.fridge_corner_radius,
        fridge_corner_radius_max=args.fridge_corner_radius_max,
        arm_pad_override=args.arm_pad_thickness,
        press_force_lbf=args.press_force,
        spacer_len=args.spacer_length,
    )
    LOG.debug("params: %s", {k: getattr(params, k) for k in params.__dataclass_fields__})

    flat = derive_flat(params)
    geom = build_geometry(params, flat)

    # Validate BEFORE the engineering report: the report builds the filleted contours to measure
    # cut length, and an infeasible fillet must surface as a validation error, not a traceback.
    issues = validate(params, geom)
    errors = [i for i in issues if i.severity == "ERROR"]
    if errors:
        LOG.error("REFUSING TO WRITE: %d validation error(s)", len(errors))
        for issue in errors:
            LOG.error("  [%s] %s", issue.code, issue.message)
        return 1

    report = engineering_report(params, geom)

    if args.dry_run:
        LOG.info("--dry-run: validation passed, no files written")
        return 0

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.name}" if args.name else ""
    dxf_path = out_dir / f"bracket_flat{suffix}.dxf"
    json_path = out_dir / f"bracket_params{suffix}.json"
    write_dxf(dxf_path, params, geom)
    write_svg(out_dir / f"bracket_preview{suffix}.svg", params, geom, report, dxf_path.name)
    write_params_json(json_path, params, geom, report)
    LOG.info("Done. Verify with: audit_dxf.py --dxf %s --expect %s", dxf_path, json_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
