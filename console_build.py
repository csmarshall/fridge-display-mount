#!/usr/bin/env python3
"""Build index.html — the single working surface for this project.

Diagrams, decisions, numbers, checklists and prices on one page. Every FIGURE is derived from the
generator at build time, so the page cannot drift from the cut file; only prose and measured
prices are authored here. Notes typed on the page persist locally and can be copied out in one go.
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from bracket_common import (LOG_LEVELS, area_cm2_in2, configure_logging, in_mm,
                            kg_lb, lbf_n, mm_in)
import detach_study
import generate_bracket as G
from generate_bracket import BracketParams, MATERIAL, build_geometry, derive_flat

LOG = logging.getLogger("console")

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SIZE_RE = re.compile(r'<svg[^>]*?\bwidth="([\d.]+)"[^>]*?\bheight="([\d.]+)"', re.S)

# Measured at app.sendcutsend.com on this date. Prices are observations, not derived values, so
# they live here with their date attached rather than pretending to be computed.
#
# RE-QUOTED 2026-08-27 for the .188 in build. The old table below was the .119 in quote and sat on
# a page that declared .188 settled — every downstream card that reasons from a price (vents,
# lightening, reach ladder) was arguing from a part that is no longer being made.
PRICE_DATE = "2026-08-27"

# McMaster 3506K67 unit price, qty 1. An observation with a date, not a derived value.
MAGNET_UNIT_USD = 23.92
PRICES = [
    ("reach180 (AS BUILT, .188 in)", "310 x 738.8", "$112.50", "$126.71", "$197.07"),
]
# Only the as-built variant was re-quoted at .188 in. The .119 in ladder below is kept because the
# reach-cost and vent-cost cards are derived from it, and those RATIOS still hold even though the
# absolute figures do not. It must never be presented as a current price.
PRICES_SUPERSEDED_119 = [
    ("reach130 (short)", "310 x 687", "$96.70", "$108.47", "$174.30"),
    ("reach180 (long)", "310 x 737", "$101.04", "$112.81", "$182.54"),
]

DIAGRAM_INFO = {
    # The CURRENT design. It lives in csmarshall/fridge-strut-mount; the sheet is copied here so
    # one page can carry both designs. Regenerate it there, then re-copy.
    "strut_concept.svg": ("Concept sheet — the whole assembly",
                         "Side elevation, the base joint at 4.5x, and the panel-to-screen "
                         "stack. The sheet the design was decided from.", "current"),
    "clamp_frame.svg": ("The frame, from the front",
                       "Two struts tied top and bottom by IDENTICAL bars. The only view that "
                       "shows it as one frame — and a true-scale strip answering whether the "
                       "strut stands proud of the fridge.", "current"),
    "clamp_dims.svg": ("The mount, dimensioned",
                      "Front and side elevation with 32 TAGGED lengths, the plate's hole pattern, "
                      "and all four display options dashed over the mount at one scale.",
                      "current"),
    "clamp_orientation.svg": ("Why portrait fits and landscape does not",
                             "Every dimension that decides it on one depth axis — case, doors, "
                             "hinge cover, window, bar, struts, box, and both orientations.",
                             "current"),
    "clamp_stack.svg": ("The stack, panel to screen",
                       "Section at 7x, cut twice — through a strut and through the box, because "
                       "the stack is not the same in both places. 52.05 mm total.", "current"),
    "clamp_depth.svg": ("Why the struts sit BESIDE the box",
                       "Plan view, the two arrangements compared. Nesting took 23.7 mm — 31% — "
                       "off how far the screen stands out. ADOPTED.", "current"),
    "clamp_plate.svg": ("What holds the monitor — the plate",
                       "Part C. The display bolts to it, it bolts to the struts, the struts "
                       "stand on the floor. Carries the vent windows the Pi needs.", "current"),
    "clamp_approval.svg": ("Approval sheet — clamped strut",
                          "Partner-facing. What it is, what it sticks out into the room, what is "
                          "not settled.", "current"),
    "clamp_loadpath.svg": ("Where the weight goes",
                          "Down the strut, into the foot, into the floor. The clamps carry "
                          "nothing.", "current"),
    "clamp_parts.svg": ("Flat patterns — the two parts",
                       "Two bent parts, two of each, both drawn at the same scale. Bend "
                       "deduction is still an estimate.", "current"),
    "clamp_assembly.svg": ("Assembly order",
                          "Four steps. Everything stays loose until the last one.", "current"),
    "clamp_clearance.svg": ("Top clamp vs the hinge cover",
                           "Plan view. Centring the struts on the case depth drives the front "
                           "clamp 51 mm INTO the cover; the window is the datum.", "current"),
    "clamp_height_check.svg": ("Does a slot land where the clamps need one?",
                              "A fixed 50.8 mm slot pitch against whatever height the fridge "
                              "is. Both clamps land inside a half-slot.", "current"),
    "approval_sheet.svg": ("Approval sheet", "For significant-other review. Three views plus plain-language facts.", "prev"),
    "bracket_preview.svg": ("Technical flat pattern", "The cut file, annotated. Reference only.", "prev"),
    "magnet_pattern_study.svg": ("Magnet layout study", "Does staggering help? Closed-form comparison.", "prev"),
    "spacing_explainer.svg": ("Magnet spacing floor", "Why a bigger disc runs out of plate.", "prev"),
    "assembly_drawing.svg": ("Assembly, 23.8in", "Display and rear box as transparent overlays.", "prev"),
    "assembly_drawing_27in.svg": ("Assembly, 27in", "Same bracket, larger panel.", "prev"),
    "ergonomics_sweep.svg": ("Ergonomics sweep",
                            "Mounting height vs neck length, on the Samsung 1743 mm case height. "
                            "Note the built neck (257 mm) is not one of the four panels — they "
                            "bracket it.", "shared"),
    "arm_width_sweep.svg": ("Arm width sweep",
                           "Arm width vs hold-down on the Samsung 610 mm counter-depth top, "
                           "against the MEASURED 406 mm clear window.", "prev"),
    "thickness_study.svg": ("Thickness study — SUPERSEDED",
                           "ALUMINIUM-era: highlights 0.187 in 5052 at 5.89 kg. The build is "
                           "A36 steel 0.187 in at 5.81 kg. See docs/PRICE-STUDY.md instead.",
                           "prev"),
    "variant_compare.svg": ("Variant comparison", "The reach variants side by side.", "prev"),
    "pad_explainer.svg": ("Pad budget", "Why the pad thickness is locked to the magnet height, and what the corner radius costs.", "prev"),
    "orientation_compare.svg": ("Orientation", "Portrait vs landscape, counter-depth.", "shared"),
    "display_compare.svg": ("23.8 vs 27 inch", "Both panels, same bracket.", "shared"),
    # Was falling through to a snake_case filename title with no caption, sitting uncaptioned
    # among real deliverables. It is a TEST harness — a tool for judging a validator refusal —
    # not a cable harness, and not a fabrication drawing.
    "stack_detail.svg": ("Fastener sandwich at one magnet",
                        "Every stack shape that fits, in true section — magnet | plate | washer | "
                        "nut, and whether the fixed 1/2 in stud still reaches.", "prev"),
    "magnet_primer.svg": ("Why not just magnets?",
                         "Pull vs shear vs peel, and why a 175 lb magnet delivers 12 lb where "
                         "it counts. Start here if the hook looks like overkill.", "shared"),
    "fastener_matrix.svg": ("Every fastener permutation",
                           "All 39 nut x washer x threadlocker combinations with the arithmetic "
                           "shown: plate + washer + nut vs stud.", "prev"),
    "force_table.svg": ("Force by direction and magnet count",
                       "What it takes to shift or unseat it, 6 to 15 magnets, in lb and newtons.",
                       "prev"),
    "mount_views.svg": ("Both faces of the mount",
                       "Front and back side by side — magnets and foam on the fridge face, "
                       "VESA and spacers on the display face.", "prev"),
    "hinge_clearance.svg": ("Hinge cover clearance",
                            "Plan view: where the arm and the hinge cover meet, or miss. The one "
                            "view that dimensions it.", "prev"),
    "harness_view.svg": ("Magnet placement validator — deliberate FAIL",
                        "Shows a configuration the validator REFUSES, on purpose, so a refusal "
                        "can be judged rather than obeyed. NOT the built part.", "prev"),
}
GROUP_ORDER_ALL = [("current", "CURRENT DESIGN — clamped strut"),
               ("shared", "APPLIES TO BOTH DESIGNS"),
               ("prev", "PREVIOUS DESIGN — magnet hook, superseded")]


@dataclass
class Item:
    """One thing on the page that Charles can comment on."""
    id: str
    title: str
    body: str = ""
    meta: str = ""
    state: str = ""          # settled | open | blocked | ""
    note: bool = True

    def __post_init__(self) -> None:
        # A mis-folded positional argument used to land a whole sentence here and render as a
        # giant status pill that overflowed across neighbouring cards. Fail the build instead.
        if self.state not in ("settled", "open", "blocked", ""):
            raise ValueError(f"Item {self.id!r}: state must be settled/open/blocked, "
                             f"got {self.state[:60]!r}")


@dataclass
class Section:
    id: str
    title: str
    blurb: str
    kind: str                # cards | decisions | checklist | table | diagrams
    items: list = field(default_factory=list)
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def svg_size(path: Path, default=(1600, 1000)) -> tuple[int, int]:
    m = SIZE_RE.search(path.read_text(encoding="utf-8")[:4000])
    if not m:
        LOG.warning("%s has no explicit width/height — defaulting to %s", path.name, default)
        return default
    return (int(float(m.group(1))), int(float(m.group(2))))


def export_pngs(root: Path, out_dir: Path, scale: int = 2) -> list[Path]:
    """macOS Preview has NO SVG support, so anything meant for Preview or for sending must raster."""
    if not Path(CHROME).exists():
        LOG.error("Chrome not found at %s — cannot rasterise", CHROME)
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    written, skipped = [], 0
    for svg in sorted(root.glob("*.svg")):
        w, h = svg_size(svg)
        png = out_dir / (svg.stem + ".png")
        # Incremental: rasterising all 29 costs ~20 s, which is enough friction that the PNGs
        # would quietly go stale. Only redo the ones whose SVG actually moved.
        if png.exists() and png.stat().st_mtime >= svg.stat().st_mtime:
            skipped += 1
            written.append(png)
            continue
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        f"--force-device-scale-factor={scale}", "--virtual-time-budget=3000",
                        f"--screenshot={png}", f"--window-size={w},{h}", svg.resolve().as_uri()],
                       capture_output=True, text=True)
        if png.exists():
            written.append(png)
            LOG.info("  %-28s -> %s (%dx%d @%dx)", svg.name, png.name, w, h, scale)
        else:
            LOG.error("  %-28s FAILED to rasterise", svg.name)
    if skipped:
        LOG.info("  %d already current", skipped)
    return written


# ---- content ----------------------------------------------------------------------------------
def build_sections(root: Path) -> tuple[list[Section], dict]:
    p = BracketParams()
    flat = derive_flat(p)
    geom = build_geometry(p, flat)
    rep = G.engineering_report(p, geom)
    # FITTED only. Giving the optional positions discs made these count holes as magnets, which
    # is how the page came to claim 293 lb of pull-off from a 4+4 build. Third instance of this
    # exact bug today (approval_sheet, assembly_drawing, here) — same cause each time.
    n_body = len([h for h in geom.magnet_discs
                  if h.region == "body" and not h.tag.startswith("spare")])
    n_arm = len([h for h in geom.magnet_discs
                 if h.region == "arm" and not h.tag.startswith("spare")])
    n_body_opt = len([h for h in geom.magnet_discs
                      if h.region == "body" and h.tag.startswith("spare")])
    n_arm_opt = len([h for h in geom.magnet_discs
                     if h.region == "arm" and h.tag.startswith("spare")])

    import approval_sheet as A
    world = A.World(p, G.DISPLAY, "left")
    rows = A.magnet_rows(geom)
    arm_offs = A.arm_magnet_offsets(p)
    # ONE model for "how hard to pull off" — SETTLED 2026-08-27. approval_sheet.let_go_lbf said
    # 178 lb while force_table said 146 for the SAME grab, and the page showed both on different
    # cards. force_table is canonical: it is what the approval sheet and "The numbers" row already
    # quote, and it is the more conservative of the two. let_go_lbf is no longer called from here.
    import force_table as _ft
    _ft_forces = _ft.forces(n_body, n_arm, p, rep)
    weakest = _ft_forces["grab the BOTTOM edge and pull"]
    let_go = weakest
    # Force-by-direction, computed rather than transcribed: these figures moved by more than 2x
    # when the magnet SKU changed, and the page carried the old ones for a while without noticing.
    # Was detach_study.modes(p), which is a THIRD model and disagreed with both of the others
    # (299 vs 245/306 for the middle grab). Derived from force_table so one function answers
    # "how hard to pull it off" everywhere on this page.
    # Why each direction differs, so the card explains itself rather than listing bare numbers.
    _WHY = {
        "grab the BOTTOM edge and pull": "the easiest place to grab, so the honest figure",
        "grab the MIDDLE and pull": "shorter lever than the bottom edge",
        "grab the TOP edge and pull": "pulling almost straight into the magnets",
    }
    detach_modes = [(k, None, v, _WHY.get(k, "")) for k, v in _ft_forces.items()
                    if k in _WHY]
    _detach_meta = None

    S: list[Section] = []

    S.append(Section("status", "Two designs", "This project changed load path once. Both are here, "
                     "and the difference is not a detail.", "decisions", items=[
        Item("st-current",
             "CURRENT — a clamped strut standing on the floor",
             "Two 6 ft low-profile slotted struts up the side panel, clamped top and bottom by a "
             "pair of identical L brackets, standing on the floor through an outboard foot. The "
             "clamps hold it in; the floor carries the weight. The display height becomes "
             "adjustable after the fact, nothing depends on the fridge top's geometry, and there "
             "are NO MAGNETS — which removes the derate chain, the fastener stack, the peel "
             "failure mode and the dependency on the panel being magnetic at all.",
             "Work continues in csmarshall/fridge-strut-mount. Two questions remain and both need "
             "a torch under the appliance: whether the lower clamp's reach fouls anything, and "
             "whether there is a rib worth hooking rather than bearing on. See the clamped-strut "
             "sheet under Diagrams.",
             "open"),
        Item("st-previous",
             "[MAGNET HOOK] PREVIOUS — a hook over the top, held flat by magnets",
             "One bent plate: an arm reaching over the fridge top carrying the entire load into "
             "bearing at the corner, a neck down the side, and 8 magnets holding the plate flat. "
             "It is FINISHED — validated, audited 15/15, and quoted at $197.07. It is superseded "
             "for adjustability and floor loading, NOT for being wrong.",
             "Everything below this section documents that design. Tagged hook-final in this "
             "repo if it is ever needed. Its magnet primer is worth reading whichever design "
             "wins — the physics of why magnet ratings mislead does not change.",
             "settled"),
    ]))

    S.append(Section("decisions", "Open decisions", "Tagged by which design they belong to. [MAGNET HOOK] items are kept for the record and are NOT live — the clamped strut does not have magnets, an arm, or a plate thickness to choose.",
                     "decisions", items=[
        Item("d-magnets",
             "[MAGNET HOOK] Magnet layout and count — the four corners are provably optimal",
             "Exhaustive search, 1.25M layouts, under your margins (7.99 mm of plate beyond every "
             "disc = 12.7x the 0.63 mm tolerance stack; 6 mm between adjacent discs). Result: the "
             "FOUR CORNERS at inset 32 are the single best positions on the plate — 43.4 units of "
             "any-angle attachment per magnet, more than any other arrangement. Going 4 -> 8 body "
             "buys +97% attachment for +100% magnets: essentially linear, 1.7% LESS efficient per "
             "magnet. There is no knee. Symmetric counts are 4/8/12 only — the centre vent and the "
             "four vent windows occupy both centrelines, so no symmetric 6 exists on the body.",
             f"SETTLED: {len(rows)*2} body + {len(arm_offs)*2} arm, McMaster 3506K67 "
             f"(O{p.magnet_disc_dia:.0f} x {p.magnet_standoff:.1f} mm, {p.magnet_rated_pull_lbf:.0f} lb rated, "
             f"{rep['magnet_derated_pull_lbf']:.1f} lb derated on painted sheet). That reads "
             f"{rep['magnet_tension_sf']:.0f}x on the governing touch-torsion case and lets go at "
             f"{let_go:.0f} lb — about {let_go / rep['display_weight_lbf']:.0f}x the display's own "
             f"{rep['display_weight_lbf']:.1f} lb. Magnet spend "
             f"${(len(rows)*2 + len(arm_offs)*2) * MAGNET_UNIT_USD:.2f} at "
             f"${MAGNET_UNIT_USD:.2f} each, qty 1, {PRICE_DATE}. Count was always an insurance "
             f"decision rather than an optimisation — the magnets carry NONE of the weight; the "
             f"hook does. Spare holes are cut at the four mid-sides and on the arm, so going up "
             f"in count later needs no recut.",
             "settled"),
        Item("d-detach",
             "[MAGNET HOOK] What it takes to pull it off — by direction",
             " ".join(f"{name}: {force:.0f} lb ({why})."
                      for name, _, force, why in detach_modes if force != float("inf")),
             f"Caveat: these assume a rigid plate with every magnet releasing at once. Peeling "
             f"beats them one at a time — lifting one corner of the arm breaks a single magnet at "
             f"~{rep['magnet_derated_pull_lbf']:.0f} lb using the arm as the lever. So these are "
             f"resistance-to-accident numbers, NOT removal forces. Weakest direction is sliding it "
             f"along the panel, which MOVES it rather than detaching it — the hook does not resist "
             f"that axis.", "settled"),
        Item("d-vents",
             "[MAGNET HOOK] Vent windows: keep them",
             "Quoted live. Removing all four makes the part $0.68 DEARER ($97.38 vs $96.70) on an "
             "identical blank. 23% less cutting does not pay for the 148 cm² of steel you then keep "
             "— their material component tracks part area and cut time is cheap at this size.",
             "No decision needed unless you want them gone for looks. They also save 116 g.", "settled"),
        Item("d-lighten",
             "[MAGNET HOOK] Lightening the plate to save material — not worth it",
             "Three live price points solve for the pricing model: about $4.00 per 100 cm2 of "
             "steel, $0.136 per inch of cut, and $16.22 fixed. So the $96.70 part is roughly $58 "
             "steel + $23 cutting + $16 setup. The consequence is a hard break-even: a cutout only "
             "pays for itself above Ø53 mm. Anything smaller costs more in cut time than the steel "
             "it saves — so a field of small lightening holes actively LOSES money. Removing a "
             "realistic 25% of the plate as Ø100 mm cutouts saves about $6.74, 7% of the part.",
             "Recommend: no. ~$7 for real topology work and fresh recut risk, and it fights your "
             "own preference for the bracket being heavier rather than lighter. Caveat: the model "
             "is an exact fit on three points, so treat it as indicative — I can quote a "
             "deliberately lightened variant to validate it if you want the number nailed down.",
             "settled"),
        Item("d-reach",
             "[MAGNET HOOK] How far the arm reaches onto the fridge top — SETTLED at 180 mm",
             "Reach costs sheet one-for-one, and the cost is linear: about $16.50 per 100 mm "
             "powder-coated — $8.68 laser and material, $7.80 coating, with bending a flat $11.77 "
             "that does not scale. Coated: 130 mm $174.30 / 230 mm $190.78 / 330 mm $207.26 / "
             "430 mm $223.74 / 530 mm $240.22. Slopes are fitted from the two LIVE quotes at 130 "
             "and 180 mm, so the far end is projected rather than verified.",
             "Neither the pad budget nor the 1118 mm sheet limit binds before 530 mm — with the "
             "top measured flat, reach costs sheet but no pad. What binds is FIT: hinge covers "
             "stand 36.5 mm proud, and the cabinet is only 609.6 mm deep, so 330 mm is already "
             "more than halfway across the top. Decide on the measured clear window, not price.",
             "settled"),
        Item("d-height",
             f"[BOTH] Screen centre at {rep['screen_centre_height_mm']:.0f} mm — APPROVED 2026-08-27",
             f"A 5 ft 1 in viewer's eye line ({1549*0.935:.0f} mm) lands on the screen. A 6 ft 4 in "
             f"viewer's ({1930*0.935:.0f} mm) sits {1930*0.935 - rep['screen_top_portrait_mm']:.0f} mm "
             "ABOVE the top edge, so they look down at it. Normal for a fridge-side display, but it "
             "is a choice.",
             "Charles confirmed the viewing height looks right on the actual fridge. "
             "Adjustable with --screen-centre-height if that ever changes.", "settled"),
        Item("d-thickness",
             "[MAGNET HOOK] Plate thickness — SETTLED at 0.187 in / 4.75 mm HRPO (SendCutSend list it as .188)",
             f"Chosen for heft and margin, NOT for stiffness you can feel: plate flex under a "
             f"touch is 0.016 mm here against 0.064 mm at 0.119 in, and neither is perceptible. "
             f"What it buys is {rep['bracket_mass_kg']:.2f} kg instead of 3.71 kg, plus the best "
             f"$/kg and stiffness-per-dollar in the material sweep. Hot-rolled is cheaper stock "
             f"than cold-rolled, which is why .188 HRPO undercuts .135 CRS despite being thicker.",
             "+$11.21 over the 0.119 build. Commercial TV mounts run 1.8-2.7 mm; this is 4.75 mm.",
             "settled"),
        Item("d-orient", "[BOTH] Portrait — on practical grounds, CORRECTED from \"impossible\"",
             "At the old 246 mm strut spacing landscape overhung the cabinet's REAR edge and was "
             "geometrically impossible. Narrowing the struts to 160 moved them forward, and "
             "landscape now technically fits — by 1.5 mm at the rear against 52.9 at the front.",
             "That is flush with the back of the cabinet and wildly off centre, so portrait "
             "remains the choice. But the honest reason is now practical, not geometric, and the "
             "earlier claim on this page overstated it.",
             "settled"),
        Item("d-datum", "[BOTH] Struts as far FORWARD as the hinge cover allows — SETTLED",
             "Centring on the CASE drives the clamp bar into the cover. Centring on the WINDOW is "
             "safe but pushes the screen 101.5 mm behind the case centre, away from where anyone "
             "stands. Hard forward centres best but leaves zero tolerance against a cover "
             "position read off a photograph.",
             "Chosen: forward, holding cover_margin (20 mm) back. With the struts narrowed to "
             "160 the bar is shorter and can sit further forward still, so the screen is now "
             "25.7 mm rearward — down from 68.7 at the old spacing, and 101.5 window-centred.",
             "settled"),
        Item("d-spacing", "[BOTH] Strut spacing 160, re-derived — was an inherited 246",
             "246 was the MAGNET-HOLE spacing from the hook design, carried over verbatim when "
             "the load path changed and never re-derived. What actually bounds it: the plate "
             "bolts should clear the 134 mm rear box without leaning on spacer height (floor "
             "~155), and touch-press wobble at the screen edge grows as 1/spacing squared.",
             "160 keeps wobble at 0.72 mm under a firm 5 lbf press — under a millimetre, and the "
             "model overstates it by putting the load at mid-span. It makes the plate 29% "
             "narrower (297 to 211), the clamp bar 215 instead of 301, and cuts the screen's "
             "rearward bias from 68.7 to 25.7 mm. Bolts still clear the box by 13 mm each side.",
             "settled"),
        Item("d-coat",
             "[BOTH] Powder coat at SendCutSend, or spray it yourself",
             "Matte black powder adds $66–70 and pushes delivery Aug 31 → Sep 3. Bare CRS will "
             "surface-rust in a kitchen, so it needs something.",
             "Recommend: let them do it. A hand-sprayed edge on bare steel is where rust starts.", "open"),
    ]))

    S.append(Section("checklist", "Before ordering", "Measurements that gate an order. [MAGNET HOOK] ones no longer gate anything: the clamp design does not care whether the panel is magnetic or what the top corner radius is. That is the point of it.",
                     "checklist", items=[
        Item("m-window", "[BOTH] Clear window on the fridge top, front to back — MEASURED 2026-08-27",
             f"{p.top_clear_window:.0f} mm clear from the rear edge to the hinge cover, against a "
             f"{p.neck_w:.0f} mm arm width — fits with {p.top_clear_window - p.neck_w:.0f} mm to "
             f"spare ({p.top_clear_window / p.neck_w:.2f}x). The hinge cover occupies the front "
             f"{609.6 - p.top_clear_window:.0f} mm and is removable/adjustable, so even a clash "
             f"would be recoverable. This was the likeliest recut risk; it is now closed.",
             "", "settled"),
        Item("m-height", "[BOTH] Height to the TOP OF THE CASE, not the hinges",
             f"Design assumes Samsung's published {p.fridge_height:.0f} mm. Sets the neck length and "
             "therefore the screen height.", "", "blocked"),
        Item("m-magnetic", "[MAGNET HOOK] Is the side panel actually magnetic? — YES, measured 2026-08-26",
             "Checked on the actual unit: the TOP and the SIDES are both magnetic. That confirms "
             "the arm retention magnets will do their job, so all eight are fitted in the first "
             "order. It also demotes the non-magnetic-panel fallback behind the 190 mm arm width "
             "from a design driver to free insurance.",
             "The hook carries all the weight either way — this was never load-bearing.", "settled"),
        Item("m-radius", "[MAGNET HOOK] Top corner radius",
             f"The {p.arm_pad:.1f} mm pad covers up to R{rep['max_fridge_corner_radius_covered_mm']:.0f} mm, "
             "so this is a confirmation rather than an input.", "", "blocked"),
        Item("m-fan", "[BOTH] Photograph the display's rear box",
             f"The Pi fan opening is at R{G.DISPLAY.rear_face_feature_radius:.1f} mm from the VESA "
             "centre, scaled off a raster drawing to ±5 mm. The vent windows sit on that radius.",
             "NOW GATES THE PLATE SIZE. The plate is 152 mm tall specifically to stop "
             "short of this opening so no vent windows have to be cut at all. Two edge "
             "notches insure against the radius being wrong, but the opening's own size "
             "is not published anywhere and has to be measured.", "open"),
        Item("m-thread", "[BOTH] VESA insert thread depth",
             "Sets the M4 screw length. Any standard head clears the fridge inside the "
             f"{p.magnet_standoff:.0f} mm standoff.", "", "open"),
    ]))

    # The clamp design has SEVEN sheets against the magnet design's eighteen, and that gap invites
    # the wrong conclusion. Most of it is not missing work: roughly half the magnet sheets exist
    # only BECAUSE there are magnets, and the clamp deletes their subject matter. Saying so
    # explicitly turns an apparent hole into the argument for the change.
    S.append(Section("parity", "Sheet for sheet",
                     "Why the current design has fewer drawings, and which of them are gaps "
                     "rather than deletions.", "table",
                     columns=["magnet-hook sheet", "clamped-strut counterpart", "status"],
                     rows=[
        ("Approval sheet", "Approval sheet — clamped strut", "drawn"),
        ("Assembly, 23.8in / 27in", "Assembly order", "drawn"),
        ("Technical flat pattern", "Flat patterns — the two parts", "drawn"),
        ("Hinge cover clearance", "Top clamp vs the hinge cover", "drawn — and it FOUND a "
         "collision"),
        ("Force by direction and magnet count", "Where the weight goes", "drawn"),
        ("(nothing equivalent)", "Does a slot land where the clamps need one?", "new — the strut "
         "has a fixed pitch the hook never had"),
        ("Magnet layout study", "—", "N/A — no magnets"),
        ("Magnet spacing floor", "—", "N/A — no magnets"),
        ("Magnet placement validator", "—", "N/A — no magnets"),
        ("Every fastener permutation", "—", "N/A — no studs to permute"),
        ("Fastener sandwich at one magnet", "—", "N/A — no magnet stack"),
        ("Why not just magnets?", "kept, under APPLIES TO BOTH", "still the best explanation of "
         "why this design exists"),
        ("Pad budget / corner radius", "—", "N/A — nothing bends over the corner"),
        ("Arm width sweep, variant comparison", "—", "N/A — no arm"),
        ("Both faces of the mount", "—", "gap — worth drawing"),
        ("Ergonomics sweep", "kept, under APPLIES TO BOTH", "more relevant now, not less — the "
         "clamp design is adjustable"),
    ]))

    S.append(Section("numbers", "The numbers", "Derived from the generator at build time — these cannot drift.",
                     "table",
                     columns=["", "value", "note"],
                     rows=[
        ("Material", f"{MATERIAL.name} {in_mm(MATERIAL.thickness_in)}", "textured black"),
        ("Flat pattern", f"{mm_in(flat.width)} × {mm_in(flat.height, 1)}",
         f"bend deduction {mm_in(flat.bend_deduction, 2)}"),
        # Split out, because "bracket mass" alone got quoted as if it were the whole thing, and
        # "total hanging" got read as the screen being that heavy. Most of this is STEEL.
        ("Screen alone", kg_lb(rep['display_mass_kg']), "the Waveshare panel, nothing else"),
        ("Bracket, magnets, pads, fasteners", kg_lb(rep['bracket_mass_kg']),
         f"steel plate {rep['plate_mass_kg']:.2f} + magnets {rep['magnet_mass_kg']:.2f} + foam "
         f"{rep['foam_mass_kg']:.2f} + nuts/washers {rep['fastener_mass_kg']:.2f} kg. The screen "
         f"figure is Waveshare's published spec; the steel is derived from the cut geometry; the "
         f"magnets, foam and fasteners are ESTIMATES (no vendor mass is published for the "
         f"magnet)"),
        ("WHOLE MOUNTED SYSTEM", kg_lb(rep['total_hanging_lbf'] * 0.45359237),
         "all of it borne by the fridge top, which is structural — the case alone weighs 229 lb"),
        ("Magnets", f"{n_body} body + {n_arm} arm FITTED "
                    f"(+{n_body_opt + n_arm_opt} optional positions cut)",
         f"Ø{mm_in(p.magnet_disc_dia)} × {mm_in(p.magnet_standoff, 2)} bare nickel"),
        ("Magnet spacing", mm_in(rep['magnet_spacing_mm']),
         f"load-bearing floor {mm_in(p.min_magnet_spacing)}"),
        ("Torsion margin", f"{rep['magnet_tension_sf']:.1f}×",
         f"{lbf_n(rep['torsion_force_per_magnet_lbf'], 2)} per magnet"),
        ("Pull-off force", lbf_n(weakest, 0),
         "grabbing the screen's BOTTOM edge — the easiest place, so the honest figure"),
        ("Screen centre", mm_in(rep['screen_centre_height_mm']),
         f"top {mm_in(rep['screen_top_portrait_mm'])} / bottom {mm_in(rep['screen_bottom_portrait_mm'])}"),
        ("Stands off", mm_in(world.standoff),
         f"arm reaches {mm_in(p.arm_len)} onto the top"),
        ("Neck bending", f"{rep['neck_stress_psi']:.0f} psi ({rep['neck_stress_psi']*0.00689476:.2f} MPa)",
         f"SF {rep['neck_sf']:.0f}× on {MATERIAL.yield_psi:.0f} psi "
         f"({MATERIAL.yield_psi*0.00689476:.0f} MPa) yield"),
        ("Strap slots", f"{mm_in(p.strap_slot_thickness)} × {mm_in(p.strap_slot_length)}",
         "1/2 in (12.7 mm) ONE-WRAP, also passes 5/8 in (15.9 mm)"),
        ("Cut length", f"{rep['cut_length_mm']/25.4:.1f} in ({rep['cut_length_mm']:.0f} mm)",
         area_cm2_in2(rep['plate_area_mm2']/100) + " of plate"),
    ]))

    S.append(Section("prices", "Live prices",
                     f"Quoted at SendCutSend {PRICE_DATE}, qty 1. Deburring included. Nothing in a cart.",
                     "table",
                     columns=["variant", "blank (mm)", "cut only", "+ bend", "+ textured black"],
                     rows=PRICES))

    found = sorted(root.glob("*.svg"))
    S.append(Section("diagrams", "Diagrams",
                     "DIAGRAM_COUNT drawings, all generated from the same parameters as the cut file.",
                     "diagrams", items=[Item(f.name, *DIAGRAM_INFO.get(f.name, (f.stem, "", "prev"))[:2],
                                             meta=DIAGRAM_INFO.get(f.name, ("", "", "prev"))[2])
                                        for f in found]))
    ctx = {"files": {f.name: f.stat().st_mtime for f in found}, "params": p, "report": rep}
    return S, ctx


CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{--bg:#f4f6f8;--panel:#fff;--ink:#14181c;--muted:#6b757e;--rule:#d7dee4;--accent:#c0169a;
 --ok:#0a8f6f;--warn:#b8860b;--stop:#b00020;--shadow:0 1px 2px rgba(20,24,28,.06),0 8px 22px rgba(20,24,28,.05)}
:root[data-theme="dark"]{--bg:#14181c;--panel:#1c2126;--ink:#e8eef3;--muted:#8b97a2;--rule:#2c343b;
 --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 22px rgba(0,0,0,.3)}
html,body{margin:0}
body{background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
header{position:sticky;top:0;z-index:30;background:var(--panel);border-bottom:1px solid var(--rule);box-shadow:var(--shadow)}
.bar{display:flex;gap:14px;align-items:center;padding:9px 18px;flex-wrap:wrap}
.bar h1{font-size:14px;margin:0;letter-spacing:.4px;white-space:nowrap}
.bar .sub{color:var(--muted);font-size:11.5px}
.spacer{flex:1}
nav a{color:var(--muted);text-decoration:none;font-size:12.5px;padding:4px 9px;border-radius:6px;white-space:nowrap}
nav a:hover{background:var(--bg);color:var(--ink)}
button.b{border:1px solid var(--rule);background:var(--panel);color:var(--ink);border-radius:7px;
 padding:5px 11px;font:inherit;font-size:12.5px;cursor:pointer}
button.b:hover{border-color:var(--accent)}
button.b.pri{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:600}
.seg{display:inline-flex;border:1px solid var(--rule);border-radius:7px;overflow:hidden}
.seg button{border:0;border-right:1px solid var(--rule);background:transparent;color:var(--muted);
 padding:5px 10px;font:inherit;font-size:12.5px;cursor:pointer}
.seg button:last-child{border-right:0}
.seg button[aria-pressed="true"]{background:var(--accent);color:#fff;font-weight:600}
main{max-width:1780px;margin:0 auto;padding:18px}
section{margin:0 0 26px}
section>h2{font-size:15px;margin:0 0 3px;letter-spacing:.3px}
section>.blurb{color:var(--muted);font-size:12.5px;margin:0 0 12px}
.cards{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(340px,1fr))}
.card{background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:13px 15px;box-shadow:var(--shadow)}
.card h3{margin:0 0 5px;font-size:13.5px;display:flex;gap:8px;align-items:baseline}
.card p{margin:0 0 6px;font-size:12.5px;color:var(--ink)}
.card .meta{color:var(--muted);font-size:11.5px;font-style:italic}
.pill{font-size:10px;text-transform:uppercase;letter-spacing:.8px;padding:2px 7px;border-radius:20px;
 border:1px solid currentColor;white-space:nowrap;font-weight:700}
.pill.open{color:var(--warn)} .pill.blocked{color:var(--stop)} .pill.settled{color:var(--ok)}
.collapsed-line{display:none;font-size:12.5px;color:var(--muted);gap:8px;align-items:baseline}
.collapsed-line .pill{flex:none}
body.hide-done .card.done>*:not(.collapsed-line){display:none}
body.hide-done .card.done{padding:9px 15px;background:transparent;box-shadow:none;
  border-style:dashed;align-self:start}
body.hide-done .card.done .collapsed-line{display:flex}
.chk{display:flex;gap:10px;align-items:flex-start}
.chk input{margin-top:3px;width:16px;height:16px;accent-color:var(--ok);flex:0 0 auto}
.chk.done h3,.chk.done p{opacity:.45;text-decoration:line-through}
table{border-collapse:collapse;width:100%;background:var(--panel);border:1px solid var(--rule);
 border-radius:10px;overflow:hidden;box-shadow:var(--shadow);font-size:12.5px}
th,td{text-align:left;padding:8px 13px;border-bottom:1px solid var(--rule)}
th{background:var(--bg);color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.7px}
tr:last-child td{border-bottom:0}
td:first-child{font-weight:600}
.note{margin-top:8px}
.note textarea{width:100%;min-height:52px;border:1px solid var(--rule);border-radius:7px;padding:7px 9px;
 font:inherit;font-size:12.5px;background:var(--bg);color:var(--ink);resize:vertical}
.note textarea:focus{outline:2px solid var(--accent);outline-offset:-1px}
.note .t{background:none;border:0;color:var(--muted);font:inherit;font-size:11.5px;cursor:pointer;padding:2px 0}
.note .t:hover{color:var(--accent)}
.note[data-has="1"] .t{color:var(--accent);font-weight:600}
.picker{display:flex;flex-wrap:wrap;gap:6px 10px;margin-bottom:12px}
.grp{display:flex;flex-wrap:wrap;gap:6px;align-items:center;border:1px solid var(--rule);border-radius:8px;padding:5px 9px}
.grp>span{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.7px}
.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--rule);border-radius:20px;
 padding:3px 11px;cursor:pointer;font-size:12.5px;background:var(--bg);white-space:nowrap}
.chip input{margin:0;accent-color:var(--accent)}
.chip[data-on="1"]{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 12%,transparent);font-weight:600}
#grid{display:grid;gap:14px;align-items:start}
figure{margin:0;background:var(--panel);border:1px solid var(--rule);border-radius:10px;overflow:hidden;box-shadow:var(--shadow)}
figcaption{padding:8px 12px;border-bottom:1px solid var(--rule);display:flex;gap:9px;align-items:baseline}
figcaption b{font-size:13px} figcaption .n{color:var(--muted);font-size:11.5px;flex:1}
figcaption a{color:var(--ok);font-size:11.5px;text-decoration:none;white-space:nowrap}
.frame{overflow:auto;background:#fff;padding:7px}
:root[data-theme="dark"] .frame{background:#eef1f3}
.frame img{display:block;height:auto;max-width:none}
#grid.fit .frame img{width:100%}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--ink);color:var(--bg);
 padding:9px 17px;border-radius:8px;font-size:13px;opacity:0;transition:opacity .18s;pointer-events:none;z-index:60}
.toast.on{opacity:1}
kbd{border:1px solid var(--rule);border-bottom-width:2px;border-radius:4px;padding:1px 5px;font-size:11px;color:var(--muted)}
"""

JS = """
const KEY='chore-console-v1';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const st=Object.assign({notes:{},done:{},off:{},cols:2,zoom:'fit',theme:'light',
                        hideDone:true},load());
function load(){try{return JSON.parse(localStorage.getItem(KEY))||{}}catch(e){return{}}}
function save(){try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}}
function toast(m){const t=$('#toast');t.textContent=m;t.classList.add('on');
  clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove('on'),1600)}

function apply(){
  document.documentElement.dataset.theme=st.theme;
  // Collapse anything settled or ticked down to a one-line summary. It stays on the page —
  // hiding a decision outright would lose the record of why it was made.
  document.body.classList.toggle('hide-done', st.hideDone!==false);
  const hb=$('[data-act="hidedone"]');
  if(hb){hb.setAttribute('aria-pressed', st.hideDone!==false?'true':'false');
         hb.textContent = st.hideDone!==false ? 'Show settled' : 'Hide settled';}
  const g=$('#grid');
  if(g){g.style.gridTemplateColumns=`repeat(${st.cols},minmax(0,1fr))`;g.classList.toggle('fit',st.zoom==='fit');
    $$('#grid .frame img').forEach(i=>i.style.width=st.zoom==='fit'?'100%':st.zoom+'%');}
  $$('figure').forEach(f=>{const on=st.off[f.dataset.file]!==true;f.hidden=!on;
    const c=$(`.chip[data-file="${CSS.escape(f.dataset.file)}"]`);
    if(c){c.dataset.on=on?'1':'0';c.querySelector('input').checked=on}});
  $$('.chk').forEach(c=>{const d=!!st.done[c.dataset.id]||c.dataset.state==='settled';c.classList.toggle('done',d);
    c.querySelector('input').checked=d});
  $$('.note').forEach(n=>{const v=st.notes[n.dataset.id]||'';const ta=n.querySelector('textarea');
    if(ta.value!==v)ta.value=v;n.dataset.has=v.trim()?'1':'0';
    n.querySelector('.t').textContent=v.trim()?'note ✓':'+ note';
    ta.hidden=!(v.trim()||n.dataset.openq==='1')});
  $$('.seg[data-key] button').forEach(b=>b.setAttribute('aria-pressed',
    String(st[b.parentElement.dataset.key]==b.dataset.val)));
  const n=Object.values(st.notes).filter(v=>v&&v.trim()).length;
  $('#ncount').textContent=n?`${n} note${n>1?'s':''}`:'no notes yet';
  save();
}
document.addEventListener('input',e=>{
  const n=e.target.closest('.note'); if(n){st.notes[n.dataset.id]=e.target.value;
    n.dataset.has=e.target.value.trim()?'1':'0';
    const c=Object.values(st.notes).filter(v=>v&&v.trim()).length;
    $('#ncount').textContent=c?`${c} note${c>1?'s':''}`:'no notes yet';save()}
});
document.addEventListener('change',e=>{
  const c=e.target.closest('.chip'); if(c){st.off[c.dataset.file]=!e.target.checked;apply();return}
  const k=e.target.closest('.chk'); if(k){st.done[k.dataset.id]=e.target.checked;apply()}
});
document.addEventListener('click',e=>{
  const t=e.target.closest('.note .t');
  if(t){const n=t.closest('.note');const ta=n.querySelector('textarea');
    ta.hidden=!ta.hidden;n.dataset.openq=ta.hidden?'0':'1';if(!ta.hidden)ta.focus();return}
  const b=e.target.closest('.seg[data-key] button');
  if(b){st[b.parentElement.dataset.key]=b.dataset.val;apply();return}
  const a=e.target.closest('[data-act]'); if(!a)return;
  const act=a.dataset.act;
  if(act==='hidedone'){st.hideDone=!st.hideDone;apply();return}
  if(act==='all'||act==='none'){$$('figure').forEach(f=>st.off[f.dataset.file]=(act==='none'));apply()}
  if(act==='only'){const g=a.dataset.grp.split('|');
    $$('figure').forEach(f=>st.off[f.dataset.file]=!g.includes(f.dataset.file));apply()}
  if(act==='copy'){
    const out=[];
    $$('.note').forEach(n=>{const v=(st.notes[n.dataset.id]||'').trim();
      if(v)out.push(`### ${n.dataset.title}\\n${v}`)});
    $$('.chk').forEach(c=>{if(st.done[c.dataset.id])out.push(`- [x] DONE: ${c.dataset.title}`)});
    if(!out.length){toast('No notes to copy yet');return}
    const txt='Commentary from the console page:\\n\\n'+out.join('\\n\\n');
    navigator.clipboard.writeText(txt).then(()=>toast('Copied — paste it to Claude'),
      ()=>{const t=document.createElement('textarea');t.value=txt;document.body.appendChild(t);
           t.select();document.execCommand('copy');t.remove();toast('Copied')});
  }
  if(act==='clear'){if(confirm('Clear all notes and ticks on this page?')){
    st.notes={};st.done={};apply();toast('Cleared')}}
});
document.addEventListener('keydown',e=>{
  if(e.target.matches('input,textarea'))return;
  if(e.key>='1'&&e.key<='4'){st.cols=+e.key;apply()}
  if(e.key==='f'){st.zoom=st.zoom==='fit'?'100':'fit';apply()}
  if(e.key==='t'){st.theme=st.theme==='dark'?'light':'dark';apply()}
});
apply();
"""


def note_box(item_id: str, title: str) -> str:
    return (f'<div class="note" data-id="{esc(item_id)}" data-title="{esc(title)}" data-has="0">'
            f'<button class="t">+ note</button>'
            f'<textarea placeholder="Your commentary — this stays on your machine until you copy it" '
            f'hidden></textarea></div>')


def render_cards(sec: Section, checklist: bool = False) -> str:
    out = ['<div class="cards">']
    for it in sec.items:
        pill = f'<span class="pill {it.state}">{esc(it.state)}</span>' if it.state else ""
        inner = (f'<h3>{esc(it.title)}{pill}</h3>'
                 + (f'<p>{esc(it.body)}</p>' if it.body else "")
                 + (f'<div class="meta">{esc(it.meta)}</div>' if it.meta else "")
                 + (note_box(it.id, it.title) if it.note else ""))
        done = it.state == "settled"
        cls = "card done" if done else "card"
        summary = (f'<div class="collapsed-line"><span class="pill {it.state}">'
                   f'{esc(it.state)}</span> {esc(it.title)}</div>') if done else ""
        if checklist:
            out.append(f'<div class="{cls} chk" data-id="{esc(it.id)}" '
                       f'data-state="{esc(it.state)}" data-title="{esc(it.title)}">{summary}'
                       f'<input type="checkbox"{" checked" if done else ""}>'
                       f'<div>{inner}</div></div>')
        else:
            out.append(f'<div class="{cls}">{summary}{inner}</div>')
    out.append("</div>")
    return "".join(out)


def render_table(sec: Section) -> str:
    head = "".join(f"<th>{esc(c)}</th>" for c in sec.columns)
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in sec.rows)
    return (f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
            + f'<div class="cards" style="margin-top:12px">'
              f'<div class="card">{note_box("n-" + sec.id, sec.title)}</div></div>')


GROUP_ORDER = GROUP_ORDER_ALL
OTHER_LABEL = {"clamp": "Archived magnet-hook design",
               "hook": "Back to the current design"}
TITLES = {"clamp": "FRIDGE-SIDE CHORE DISPLAY",
          "hook": "ARCHIVE — MAGNET HOOK DESIGN"}
SUBS = {"clamp": "clamped strut, standing on the floor",
        "hook": "SUPERSEDED by the clamped strut — kept for the record"}
PAGE_TITLES = {"clamp": "Fridge display mount — clamped strut",
               "hook": "Archive — magnet hook design"}


# Which groups and which items belong on each page. The hook design is ARCHIVED, not deleted:
# it is finished, quoted and audited, and its reasoning still explains why the strut design won.
VARIANTS = {
    "clamp": {"groups": [("current", "The clamped strut"),
                         ("shared", "Background — applies to any mount")],
              "drop_sections": {"parity", "numbers", "prices"},
              "keep": lambda t: not t.startswith("[MAGNET HOOK]")},
    "hook":  {"groups": [("prev", "Magnet hook — the archived design"),
                         ("shared", "Background — applies to any mount")],
              "drop_sections": set(),
              "keep": lambda t: t.startswith("[MAGNET HOOK]") or t.startswith("[BOTH]")},
}


def filter_sections(sections: list[Section], variant: str) -> list[Section]:
    """Split the one model into the two pages without duplicating any content."""
    from dataclasses import replace
    cfg = VARIANTS[variant]
    want = {k for k, _ in cfg["groups"]}
    RETITLE = {
        "clamp": {"status": ("What is being built",
                             "One design. The magnet hook that came before it is archived on its "
                             "own page — see the link in the header."),
                  "decisions": ("Open decisions",
                                "Things waiting on you for the clamped strut."),
                  "checklist": ("Before ordering",
                                "Measurements that gate an order for this design.")},
        "hook": {"status": ("Why this was superseded",
                            "Finished, audited and quoted. Replaced for adjustability and floor "
                            "loading, NOT for being wrong."),
                 "decisions": ("Decisions, as they stood",
                               "Frozen. These belonged to the hook and are kept for the record."),
                 "checklist": ("Measurements it needed",
                               "Two of these stopped mattering the moment the design stopped "
                               "depending on magnets and on the fridge top's geometry.")},
    }[variant]
    out: list[Section] = []
    for sec in sections:
        if sec.id in cfg["drop_sections"]:
            continue
        if sec.kind == "diagrams":
            items = [i for i in sec.items if (i.meta or "study") in want]
        elif sec.kind == "table":
            out.append(sec)
            continue
        else:
            # The tags did their job while both designs shared a page. Now that each page IS one
            # design, they are noise — strip them rather than leave a label nothing contrasts with.
            items = [replace(i, title=i.title.replace("[MAGNET HOOK] ", "")
                                             .replace("[BOTH] ", ""))
                     for i in sec.items if cfg["keep"](i.title)]
        if items:
            sec = replace(sec, items=items)
            if sec.kind == "diagrams":
                sec = replace(sec, blurb=sec.blurb.replace("DIAGRAM_COUNT", str(len(items))))
            if sec.id in RETITLE:
                t, b = RETITLE[sec.id]
                sec = replace(sec, title=t, blurb=b)
            out.append(sec)
    return out


def render_diagrams(sec: Section, ctx: dict) -> str:
    groups: dict[str, list[Item]] = {}
    for it in sec.items:
        groups.setdefault(it.meta or "study", []).append(it)
    chips, figs = [], []
    for key, label in GROUP_ORDER:
        got = groups.get(key, [])
        if not got:
            continue
        row = [f'<div class="grp"><span>{esc(label)}</span>',
               f'<button class="chip" data-act="only" data-grp="{esc("|".join(i.id for i in got))}">only</button>']
        for it in got:
            row.append(f'<label class="chip" data-file="{esc(it.id)}" data-on="1">'
                       f'<input type="checkbox" checked>{esc(it.title)}</label>')
            mt = ctx["files"][it.id]
            figs.append(
                f'<figure data-file="{esc(it.id)}"><figcaption><b>{esc(it.title)}</b>'
                f'<span class="n">{esc(it.body)}</span>'
                f'<a href="{esc(it.id)}" target="_blank" rel="noopener">'
                f'{time.strftime("%H:%M", time.localtime(mt))} ↗</a></figcaption>'
                f'<div class="frame"><img src="{esc(it.id)}?v={int(mt)}" loading="lazy" '
                f'alt="{esc(it.title)}"></div>'
                f'<div style="padding:6px 12px 10px">{note_box("fig-" + it.id, it.title)}</div>'
                f'</figure>')
        row.append("</div>")
        chips.append("".join(row))
    controls = ('<span class="seg" data-key="cols">'
                + "".join(f'<button data-val="{i}">{i}</button>' for i in (1, 2, 3, 4)) + "</span>"
                '<span class="seg" data-key="zoom">'
                '<button data-val="fit">Fit</button><button data-val="100">100%</button>'
                '<button data-val="150">150%</button><button data-val="250">250%</button></span>'
                '<span class="seg"><button data-act="all">All</button>'
                '<button data-act="none">None</button></span>')
    return (f'<div class="picker">{"".join(chips)}</div>'
            f'<div class="picker" style="gap:10px">{controls}</div>'
            f'<div id="grid">{"".join(figs)}</div>')


ARCHIVE_BANNER = ('<div style="background:#b00020;color:#fff;padding:9px 16px;font:600 13px/1.4 '
                  'system-ui,sans-serif">ARCHIVED DESIGN &mdash; this is the magnet hook, which '
                  'is finished and quoted but NOT what is being built. It is kept because its '
                  'reasoning is what led to the clamped strut.</div>')


def build(root: Path, out: Path, variant: str = "clamp", other: str = "") -> int:
    global GROUP_ORDER
    sections, ctx = build_sections(root)
    sections = filter_sections(sections, variant)
    GROUP_ORDER = VARIANTS[variant]["groups"]
    nav = " ".join(f'<a href="#{s.id}">{esc(s.title)}</a>' for s in sections)
    if other:
        nav += f' <a href="{esc(other)}" class="xpage">{esc(OTHER_LABEL[variant])} \u2192</a>'

    body = []
    for s in sections:
        if s.kind == "decisions":
            inner = render_cards(s)
        elif s.kind == "checklist":
            inner = render_cards(s, checklist=True)
        elif s.kind == "table":
            inner = render_table(s)
        else:
            inner = render_diagrams(s, ctx)
        body.append(f'<section id="{s.id}"><h2>{esc(s.title)}</h2>'
                    f'<p class="blurb">{esc(s.blurb)}</p>{inner}</section>')

    doc = f"""<!doctype html>
<html lang="en" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{PAGE_TITLES[variant]}</title><style>{CSS}</style></head><body>
{ARCHIVE_BANNER if variant == 'hook' else ''}<header><div class="bar">
  <h1>{TITLES[variant]}</h1>
  <span class="sub">{SUBS[variant]} &middot; built {time.strftime('%d %b %H:%M')}</span>
  <nav>{nav}</nav>
  <span class="spacer"></span>
  <span class="sub" id="ncount">no notes yet</span>
  <button class="b pri" data-act="hidedone" aria-pressed="true">Hide settled</button>
  <button class="b pri" data-act="copy">Copy notes for Claude</button>
  <button class="b" data-act="clear">Clear</button>
  <span class="seg" data-key="theme"><button data-val="light">Light</button><button data-val="dark">Dark</button></span>
  <span class="sub"><kbd>1</kbd>-<kbd>4</kbd> cols · <kbd>f</kbd> fit · <kbd>t</kbd> theme</span>
</div></header>
<main>{''.join(body)}</main>
<div class="toast" id="toast"></div>
<script>{JS}</script></body></html>
"""
    out.write_text(doc, encoding="utf-8")
    LOG.info("Wrote %s — %d sections, %d diagrams", out, len(sections), len(ctx["files"]))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the project console page.")
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, default=Path("index.html"))
    ap.add_argument("--no-png", action="store_true",
                    help="skip the png/ export. Preview cannot open SVG, so the PNGs "
                         "are the viewable copy — only skip when iterating fast.")
    ap.add_argument("--png-dir", type=Path, default=Path("png"))
    ap.add_argument("--png-scale", type=int, default=2)
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    # Two pages from one model: the live design, and the archive it replaced.
    rc = build(a.root, a.out, variant="clamp", other="archive.html")
    rc |= build(a.root, a.out.parent / "archive.html", variant="hook",
                other=a.out.name)
    if not a.no_png:
        LOG.info("Rasterising for Preview (%dx) — Preview has no SVG support:", a.png_scale)
        LOG.info("Wrote %d PNGs", len(export_pngs(a.root, a.png_dir, a.png_scale)))
    if a.open:
        subprocess.run(["open", str(a.out)])
    return rc


if __name__ == "__main__":
    sys.exit(main())
