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
    # DESIGN 3 — the hook plate prepared for struts. Generated in strut/ by generate_hybrid.py
    # and hybrid_sketch.py; the FEA sheet by plate_fea.py at the root.
    "strut/hybrid_overview.svg": ("The third design — one plate, two ways to hold it up",
                                  "Whole-design elevation split by WHEN each part is bought, "
                                  "and the cost table for both phases.", "hybrid"),
    "strut/hybrid_sketch.svg": ("If the hook needs help — the bottom end",
                                "Contingency sketch of the feet and lower clamp under the plate. "
                                "Not a fabrication drawing.", "hybrid"),
    "strut/dxf/H_hook_plate_preview.svg": ("The plate as cut — 0.119 in, with strut holes",
                                          "The hook generator's own preview of THE file to "
                                          "upload: every hook hole plus four strut bolts in two "
                                          "rows. Reference only.", "hybrid"),
    "angle/angle_concept.svg": ("Design 4 - the hook in stock aluminium",
                                "Clip, two bars, a 5 in plate, four O36 magnets. Same load path, no custom "
                                "plate, no coat, hand-drilled. Validated by angle/angle.py.", "angle"),
    "angle/angle_drill.svg": ("Design 4 drill drawing - 1:1 templates",
                              "The three parts with every hole dimensioned from a datum corner; the SVG's "
                              "unit is 1 mm, print at 100 %.", "angle"),
    "magnet_sizing.svg": ("Right-sizing the magnets",
                          "What one magnet actually holds (touch, peel, a grab) against a ladder of "
                          "smaller male-stud magnets, and what a smaller one changes: pad, stud, holes.",
                          "shared"),
    "quotes.svg": ("What each design costs — three quotes from one price table",
                   "Dated vendor observations. Design 3's phase 1 is design 1 at 0.119 in with "
                   "4 magnets; its kit is design 2's feet and lower clamp. Display excluded.",
                   "shared"),
    "plate_fea.svg": ("Plate bending under a touch — finite elements vs the strip model",
                      "Kirchhoff plate on the real cut geometry, both gauges, pinned on magnets "
                      "and on strut bolts. Screen-edge movement for each.", "hybrid"),
    # DESIGN 2 — the clamped strut. Generated in strut/ (merged from its own repo 2026-09-02).
    "strut/concept_sheet.svg": ("Concept sheet — the whole assembly",
                         "Side elevation, the base joint at 4.5x, and the panel-to-screen "
                         "stack. The sheet the design was decided from.", "clamp"),
    "strut/clamp_frame.svg": ("The frame, from the front",
                       "Two struts tied top and bottom by IDENTICAL bars. The only view that "
                       "shows it as one frame — and a true-scale strip answering whether the "
                       "strut stands proud of the fridge.", "clamp"),
    "strut/clamp_elevations.svg": ("Both elevations, with the fridge",
                            "True scale, nothing broken. Looking AT the side panel, and ALONG "
                            "it at the whole appliance with the mount edge-on.", "clamp"),
    "strut/clamp_allparts.svg": ("Every cut part, flat",
                          "The whole cut list at one scale — clamp bar, foot, plate, backing "
                          "strip — with hole patterns and bend lines.", "clamp"),
    "strut/clamp_joints.svg": ("Every joint, as a stack",
                        "All four bolted joints layer by layer at 15x, each with its grip and "
                        "the bolt length that follows from it.", "clamp"),
    "strut/clamp_bom.svg": ("Bill of materials",
                     "7 cut parts, 45 bought pieces. Says plainly which lines are priced and "
                     "which are not.", "clamp"),
    "strut/clamp_real.svg": ("What it will look like",
                      "Realistic elevation, true scale and unbroken, with people at 5ft1 and "
                      "6ft5 for reference and their eye lines to the screen.", "clamp"),
    "strut/clamp_dims.svg": ("The mount, dimensioned",
                      "Front and side elevation with 32 TAGGED lengths, the plate's hole pattern, "
                      "and all four display options dashed over the mount at one scale.",
                      "clamp"),
    "strut/clamp_orientation.svg": ("Why portrait fits and landscape does not",
                             "Every dimension that decides it on one depth axis — case, doors, "
                             "hinge cover, window, bar, struts, box, and both orientations.",
                             "clamp"),
    "strut/clamp_stack.svg": ("The stack, panel to screen",
                       "Section at 7x, cut twice — through a strut and through the box, because "
                       "the stack is not the same in both places. 52.05 mm total.", "clamp"),
    "strut/clamp_depth.svg": ("Why the struts sit BESIDE the box",
                       "Plan view, the two arrangements compared. Nesting took 23.7 mm — 31% — "
                       "off how far the screen stands out. ADOPTED.", "clamp"),
    "strut/clamp_plate.svg": ("What holds the monitor — the plate",
                       "Part C. The display bolts to it, it bolts to the struts, the struts "
                       "stand on the floor. Carries the vent windows the Pi needs.", "clamp"),
    "strut/clamp_approval.svg": ("Approval sheet — clamped strut",
                          "Partner-facing. What it is, what it sticks out into the room, what is "
                          "not settled.", "clamp"),
    "strut/clamp_loadpath.svg": ("Where the weight goes",
                          "Down the strut, into the foot, into the floor. The clamps carry "
                          "nothing.", "clamp"),
    "strut/clamp_parts.svg": ("Flat patterns — the two parts",
                       "Two bent parts, two of each, both drawn at the same scale. Bend "
                       "deduction is still an estimate.", "clamp"),
    "strut/clamp_assembly.svg": ("Assembly order",
                          "Four steps. Everything stays loose until the last one.", "clamp"),
    "strut/clamp_clearance.svg": ("Top clamp vs the hinge cover",
                           "Plan view. Centring the struts on the case depth drives the front "
                           "clamp 51 mm INTO the cover; the window is the datum.", "clamp"),
    "strut/clamp_height_check.svg": ("Does a slot land where the clamps need one?",
                              "A fixed 50.8 mm slot pitch against whatever height the fridge "
                              "is. Both clamps land inside a half-slot.", "clamp"),
    "approval_sheet.svg": ("Approval sheet", "For significant-other review. Three views plus plain-language facts.", "hook"),
    "bracket_preview.svg": ("Technical flat pattern", "The cut file, annotated. Reference only.", "hook"),
    "magnet_pattern_study.svg": ("Magnet layout study", "Does staggering help? Closed-form comparison.", "hook"),
    "spacing_explainer.svg": ("Magnet spacing floor", "Why a bigger disc runs out of plate.", "hook"),
    "assembly_drawing.svg": ("Assembly, 23.8in", "Display and rear box as transparent overlays.", "hook"),
    "assembly_drawing_27in.svg": ("Assembly, 27in", "Same bracket, larger panel.", "hook"),
    "ergonomics_sweep.svg": ("Ergonomics sweep",
                            "Mounting height vs neck length, on the Samsung 1743 mm case height. "
                            "Note the built neck (257 mm) is not one of the four panels — they "
                            "bracket it.", "shared"),
    "arm_width_sweep.svg": ("Arm width sweep",
                           "Arm width vs hold-down on the Samsung 610 mm counter-depth top, "
                           "against the MEASURED 406 mm clear window.", "hook"),
    "thickness_study.svg": ("Thickness study — aluminium-era chart",
                           "Drawn for 5052 before the switch to steel; the shape of the curve "
                           "still holds, the figures do not. The steel decision and its live "
                           "quotes are in docs/PRICE-STUDY.md.", "hook"),
    "variant_compare.svg": ("Variant comparison", "The reach variants side by side.", "hook"),
    "pad_explainer.svg": ("Pad budget", "Why the pad thickness is locked to the magnet height, and what the corner radius costs.", "hook"),
    "orientation_compare.svg": ("Orientation", "Portrait vs landscape, counter-depth.", "shared"),
    "display_compare.svg": ("23.8 vs 27 inch", "Both panels, same bracket.", "shared"),
    # Was falling through to a snake_case filename title with no caption, sitting uncaptioned
    # among real deliverables. It is a TEST harness — a tool for judging a validator refusal —
    # not a cable harness, and not a fabrication drawing.
    "stack_detail.svg": ("Fastener sandwich at one magnet",
                        "Every stack shape that fits, in true section — magnet | plate | washer | "
                        "nut, and whether the fixed 1/2 in stud still reaches.", "hook"),
    "magnet_primer.svg": ("Why not just magnets?",
                         "Pull vs shear vs peel, and why a 175 lb magnet delivers 12 lb where "
                         "it counts. Start here if the hook looks like overkill.", "shared"),
    "fastener_matrix.svg": ("Every fastener permutation",
                           "All 39 nut x washer x threadlocker combinations with the arithmetic "
                           "shown: plate + washer + nut vs stud.", "hook"),
    "force_table.svg": ("Force by direction and magnet count",
                       "What it takes to shift or unseat it, 6 to 15 magnets, in lb and newtons.",
                       "hook"),
    "mount_views.svg": ("Both faces of the mount",
                       "Front and back side by side — magnets and foam on the fridge face, "
                       "VESA and spacers on the display face.", "hook"),
    "hinge_clearance.svg": ("Hinge cover clearance",
                            "Plan view: where the arm and the hinge cover meet, or miss. The one "
                            "view that dimensions it.", "hook"),
    "harness_view.svg": ("Magnet placement validator — deliberate FAIL",
                        "Shows a configuration the validator REFUSES, on purpose, so a refusal "
                        "can be judged rather than obeyed. NOT the built part.", "hook"),
}
GROUP_ORDER_ALL = [("hybrid", "DESIGN 3 — hook with optional strut"),
                   ("hook", "DESIGN 1 — the hook alone"),
                   ("clamp", "DESIGN 2 — clamped strut"),
                   ("angle", "DESIGN 4 — stock aluminium (REJECTED)"),
                   ("shared", "APPLIES TO EVERY DESIGN")]


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
    strut = root / "strut"
    for svg in (sorted(root.glob("*.svg")) + sorted(strut.glob("*.svg"))
                + sorted((strut / "dxf").glob("*_preview.svg")) + sorted((root / "angle").glob("*.svg"))):
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

    # ---- the third design, read from what strut/generate_hybrid.py actually produced
    sys.path.insert(0, str((root / "strut").resolve()))
    import hybrid as HY
    plate_json = root / "strut" / "dxf" / "H_hook_plate.json"
    hook3 = json.loads(plate_json.read_text(encoding="utf-8"))
    h3 = HY.Hybrid(bolt_rows=tuple(hook3["params"]["strut_bolt_rows"]))
    s3 = {ph: HY.structural(h3, ph, hook3["engineering"]["plate_mass_kg"]) for ph in HY.PHASES}
    cost3 = HY.costed(h3)
    import prices as PR
    _q3 = PR.quote_hybrid(n_magnets=h3.n_magnets_fitted, strut_ft=int(h3.strut_ft))
    now3, later3 = PR.phase(_q3, 1), PR.phase(_q3, 2)
    rows3 = sorted(h3.bolt_rows)
    sys.path.insert(0, str((root / "angle").resolve()))
    import angle as AN
    a4 = AN.Angle()
    d4 = json.loads((root / "angle" / "dxf" / "D4_params.json").read_text(encoding="utf-8"))
    q4 = PR.quote_angle()

    S.append(Section("status", "Three designs, one plate", "One display, one fridge, three ways to "
                     "hold the plate up. Design 3 is what is being ordered; the other two are its "
                     "parents and each has its own page.", "decisions", items=[
        Item("st-hybrid",
             "[HYBRID] DESIGN 3 — BEING ORDERED: the hook, with the plate prepared for struts",
             f"Design 1's plate, cut at {h3.plate_t / 25.4:.3f} in with four extra O8.5 holes in two "
             f"rows ({rows3[0]:.1f} and {rows3[-1]:.1f} mm above the bottom edge) at "
             f"{h3.strut_spacing:.2f} centres. Phase 1 is the hook: arm over the top, "
             f"{h3.n_magnets_fitted} body magnets holding the plate flat. If that proves too lively, "
             f"phase 2 bolts two {h3.strut_ft:.0f} ft struts through those holes onto design 2's feet "
             f"and lower clamp, and the magnets come off. Nothing about the plate changes between "
             f"the phases.",
             f"First order ${now3:.2f}; the support kit ${later3:.2f} only if needed. Touch flex at "
             f"the screen edge: {s3['magnets'].screen_edge_mm:.3f} mm on magnets, "
             f"{s3['struts'].screen_edge_mm:.3f} mm on struts (strip model; the FEA sheet says "
             f"0.065 / 0.036). Generated by the hook generator, audited, in strut/dxf/.",
             "open"),
        Item("st-hook",
             "[HOOK] DESIGN 1 — the hook alone, held flat by magnets",
             "One bent plate: an arm reaching over the fridge top carrying the entire load into "
             "bearing at the corner, a neck down the side, and magnets holding the plate flat. "
             "FINISHED — validated, audited 15/15, and quoted at $197.07 in 0.187 in HRPO. "
             "Design 3 IS this plate, thinner and with four more holes; every sheet on the hook "
             "page still describes it.",
             "Tagged hook-final in this repo. Its magnet primer is worth reading whichever design "
             "wins — the physics of why magnet ratings mislead does not change.",
             "settled"),
        Item("st-angle",
             "[ANGLE] DESIGN 4 — REJECTED 2026-09-02: the hook in stock aluminium, hand-drilled",
             f"A 2 x 2 x 3/16 in angle clipped over the fridge top corner, two 2 x 1/4 in flat bars "
             f"down the side {a4.bar_spacing:.0f} mm apart carrying four O36 K&J magnets, and a 5 x 3/16 in "
             f"bar across them for the VESA. Same load path as the hook, no custom plate, no coat, "
             f"bare 6061. ${q4.priced:.2f} in parts, {q4.unpriced} lines unpriced, some estimated. "
             f"Validated by its own generator; three drill templates audited.",
             f"Hangs {a4.hanging_lbf:.1f} lb at {a4.bearing_psi:.2f} psi on the top; magnet SF {a4.magnet_sf_touch:.0f}x "
             f"touch / {a4.magnet_sf_grab:.1f}x on a 20 lb grab; screen edge {a4.bar_touch_flex_mm:.3f} mm. The clip "
             f"must live inside the hinge-cover window, which puts the screen {a4.display_bias_rearward:.0f} mm "
             f"rearward of the case centre unless the cover is lifted. No strut option. "
             f"REJECTED by Charles: he will not hand-drill it. Kept for its magnet study and the "
             f"plate-vs-fan finding; not offered for review.",
             "settled"),
        Item("st-clamp",
             "[CLAMP] DESIGN 2 — a clamped strut standing on the floor",
             "Two low-profile slotted struts up the side panel, clamped top and bottom by a pair "
             "of identical L brackets, standing on the floor through an outboard foot. The clamps "
             "hold it in; the floor carries the weight. Height-adjustable after the fact, nothing "
             "depends on the fridge top, NO magnets. Its foot and lower clamp are design 3's "
             "support kit, unchanged.",
             "Standalone fallback. Two questions remain and both need a torch under the appliance: "
             "whether the lower clamp's reach fouls anything, and whether there is a rib worth "
             "hooking rather than bearing on.",
             "settled"),
    ]))

    S.append(Section("decisions", "Open decisions", "Tagged by which design they belong to. [HOOK] items are kept for the record and are NOT live — the clamped strut does not have magnets, an arm, or a plate thickness to choose.",
                     "decisions", items=[
        Item("d-magnets",
             "[HOOK] Magnet layout and count — the four corners are provably optimal",
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
             "[HOOK] What it takes to pull it off — by direction",
             " ".join(f"{name}: {force:.0f} lb ({why})."
                      for name, _, force, why in detach_modes if force != float("inf")),
             f"Caveat: these assume a rigid plate with every magnet releasing at once. Peeling "
             f"beats them one at a time — lifting one corner of the arm breaks a single magnet at "
             f"~{rep['magnet_derated_pull_lbf']:.0f} lb using the arm as the lever. So these are "
             f"resistance-to-accident numbers, NOT removal forces. Weakest direction is sliding it "
             f"along the panel, which MOVES it rather than detaching it — the hook does not resist "
             f"that axis.", "settled"),
        Item("d-vents",
             "[HOOK] Vent windows: keep them",
             "Quoted live. Removing all four makes the part $0.68 DEARER ($97.38 vs $96.70) on an "
             "identical blank. 23% less cutting does not pay for the 148 cm² of steel you then keep "
             "— their material component tracks part area and cut time is cheap at this size.",
             "No decision needed unless you want them gone for looks. They also save 116 g.", "settled"),
        Item("d-lighten",
             "[HOOK] Lightening the plate to save material — not worth it",
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
             "[HOOK] How far the arm reaches onto the fridge top — SETTLED at 180 mm",
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
             f"[ALL] Screen centre at {rep['screen_centre_height_mm']:.0f} mm — APPROVED 2026-08-27",
             f"A 5 ft 1 in viewer's eye line ({1549*0.935:.0f} mm) lands on the screen. A 6 ft 4 in "
             f"viewer's ({1930*0.935:.0f} mm) sits {1930*0.935 - rep['screen_top_portrait_mm']:.0f} mm "
             "ABOVE the top edge, so they look down at it. Normal for a fridge-side display, but it "
             "is a choice.",
             "Charles confirmed the viewing height looks right on the actual fridge. "
             "Adjustable with --screen-centre-height if that ever changes.", "settled"),
        Item("d-thickness",
             "[HOOK] Plate thickness — SETTLED at 0.187 in / 4.75 mm HRPO (SendCutSend list it as .188)",
             f"Chosen for heft and margin, NOT for stiffness you can feel: plate flex under a "
             f"touch is 0.016 mm here against 0.064 mm at 0.119 in, and neither is perceptible. "
             f"What it buys is {rep['bracket_mass_kg']:.2f} kg instead of 3.71 kg, plus the best "
             f"$/kg and stiffness-per-dollar in the material sweep. Hot-rolled is cheaper stock "
             f"than cold-rolled, which is why .188 HRPO undercuts .135 CRS despite being thicker.",
             "+$11.21 over the 0.119 build. Commercial TV mounts run 1.8-2.7 mm; this is 4.75 mm.",
             "settled"),
        Item("d-orient", "[ALL] Portrait — on practical grounds, CORRECTED from \"impossible\"",
             "At the old 246 mm strut spacing landscape overhung the cabinet's REAR edge and was "
             "geometrically impossible. Narrowing the struts to 160 moved them forward, and "
             "landscape now technically fits — by 1.5 mm at the rear against 52.9 at the front.",
             "That is flush with the back of the cabinet and wildly off centre, so portrait "
             "remains the choice. But the honest reason is now practical, not geometric, and the "
             "earlier claim on this page overstated it.",
             "settled"),
        Item("d-datum", "[CLAMP] Struts as far FORWARD as the hinge cover allows — SETTLED",
             "Centring on the CASE drives the clamp bar into the cover. Centring on the WINDOW is "
             "safe but pushes the screen 101.5 mm behind the case centre, away from where anyone "
             "stands. Hard forward centres best but leaves zero tolerance against a cover "
             "position read off a photograph.",
             "Chosen: forward, holding cover_margin (20 mm) back. With the struts narrowed to "
             "160 the bar is shorter and can sit further forward still, so the screen is now "
             "25.7 mm rearward — down from 68.7 at the old spacing, and 101.5 window-centred.",
             "settled"),
        Item("d-spacing", "[CLAMP] Strut spacing 160, re-derived — was an inherited 246",
             "246 was the MAGNET-HOLE spacing from the hook design, carried over verbatim when "
             "the load path changed and never re-derived. What actually bounds it: the plate "
             "bolts should clear the 134 mm rear box without leaning on spacer height (floor "
             "~155), and touch-press wobble at the screen edge grows as 1/spacing squared.",
             "160 keeps wobble at 0.72 mm under a firm 5 lbf press — under a millimetre, and the "
             "model overstates it by putting the load at mid-span. It makes the plate 29% "
             "narrower (297 to 211), the clamp bar 215 instead of 301, and cuts the screen's "
             "rearward bias from 68.7 to 25.7 mm. Bolts still clear the box by 13 mm each side.",
             "settled"),
        Item("d-h-rows",
             f"[HYBRID] {h3.strut_ft:.0f} ft struts and two bolt rows — SETTLED 2026-09-01",
             f"A 4 ft strut put ONE slot row {17.73:.1f} mm above the plate edge and the plate "
             f"cantilevered 144 mm to the VESA: 0.876 mm of screen-edge movement under a 5 lb "
             f"press, four times the feel-rigid band and WORSE than the magnets. {h3.strut_ft:.0f} ft "
             f"puts {len(h3.candidate_rows)} slot rows inside the plate; the lowest and highest that "
             f"clear every magnet face, window and hole are {rows3[0]:.2f} and {rows3[-1]:.2f}, "
             f"bracketing the VESA, and the plate becomes a beam between them: "
             f"{s3['struts'].screen_edge_mm:.3f} mm by the strip model, 0.036 by FEA.",
             f"The rows are PICKED from the hook generator's own feature map and the generator "
             f"re-validates them; if the mounting height moves they are re-picked and the build "
             f"refuses if they no longer bracket. The strut stands {h3.strut_above_plate:.0f} mm "
             f"above the plate top, behind the display.", "settled"),
        Item("d-h-magnets",
             f"[HYBRID] {h3.n_magnets_fitted} body magnets in phase 1, arm magnets not bought — SETTLED 2026-09-01",
             "The magnets are NOT optional in phase 1: nothing else holds the bottom of the plate to "
             "the panel. An earlier costing called them optional and was wrong. The four ARM "
             "magnets are anti-walk insurance with zero load credit; their holes are cut, they are "
             "bought only if the arm is seen to creep on the foam.",
             f"${h3.n_magnets_fitted * HY.MAGNET_EACH_USD:.2f} at ${HY.MAGNET_EACH_USD:.2f} each. "
             f"They come OFF when the struts go on: the plate then sits {h3.strut_standoff:.2f} mm "
             f"off the panel against the magnets' {h3.magnet_standoff:.2f}.", "settled"),
        Item("d-h-thickness",
             f"[HYBRID] Plate thickness {h3.plate_t / 25.4:.3f} in for design 3 — SETTLED, checked both ways",
             "Design 1 chose 0.187 in for heft, not stiffness — its own record says flex is "
             "imperceptible at either gauge. 0.119 in makes the whole kit one gauge (plate, clamp, "
             f"feet share a bend spec) and hangs 2.1 kg less on the fridge top. Checked: neck SF "
             f"{s3['magnets'].neck_sf:.0f}x / body SF {s3['magnets'].body_sf:.0f}x on magnets, "
             f"{s3['struts'].neck_sf:.0f}x / {s3['struts'].body_sf:.0f}x on struts; the FEA plate "
             "model agrees with the strip model to ~15%.",
             "Bend deduction is SendCutSend's published 4.97 mm for this gauge, one home for all "
             "three designs.", "settled"),
        Item("d-a-magnet",
             "[ANGLE] O36 K&J MM-C-36 on the bars, 5/16 in pad — SETTLED 2026-09-02",
             f"The largest male-stud pot magnet that fits a 2 in bar with an edge margin ({a4.bar_edge_margin:.1f} mm "
             f"each side). Derated {a4.magnet_derated_lbf:.1f} lb against {a4.torsion_per_magnet_lbf:.2f} lb of touch "
             f"torsion: SF {a4.magnet_sf_touch:.0f}x; {a4.magnet_sf_grab:.1f}x on an assumed 20 lb grab of the bottom "
             f"edge. Its 8 mm body is the standoff, so the pad is 5/16 in foam ({a4.pad:.2f} mm, "
             f"{a4.pad - a4.standoff:+.2f} in the -0.60/+0.30 band).",
             "See magnet_sizing.svg for the ladder. The O48 would not fit the bar.", "settled"),
        Item("d-a-plate",
             "[ANGLE] Plate is a 5 x 3/16 in bar, not an 8 x 8 plate — SETTLED 2026-09-02",
             f"The display's rear box carries the Pi fan at ~R{a4.fan_r:.0f} on its vertical axis; an 8 in plate "
             f"would blank it. 5 in stops {a4.plate_fan_clearance:.1f} mm short of the opening. 3/16 in, because "
             f"the VESA holes sit 13.5 mm from the bar's edge and the 2T rule needs that to be >= 2 x thickness.",
             "The fan position is SCALED off a raster drawing to ±5 mm — measure it before cutting the plate.", "settled"),
        Item("d-a-clip",
             "[ANGLE] Clip inside the hinge-cover window; bars butt the clip's top leg — SETTLED 2026-09-02",
             f"Centred on the case the 12 in clip would run into the hinge cover. It sits {a4.clip_from_rear:.0f}-"
             f"{a4.clip_from_rear + a4.clip_len:.0f} mm from the rear edge with {a4.hinge_margin:.0f} mm to the cover, "
             f"putting the screen {a4.display_bias_rearward:.0f} mm rearward of the case centre. The bars run the full "
             f"2 in leg so the two 1/4-20 bolts per bar sit 17 and 37 mm from the top, 2T inside both parts.",
             "The cover lifts off (Charles): recover the bias by removing it, or accept it.", "settled"),
        Item("d-coat",
             "[ALL] Powder coat at SendCutSend, or spray it yourself",
             "Matte black powder adds $66–70 and pushes delivery Aug 31 → Sep 3. Bare CRS will "
             "surface-rust in a kitchen, so it needs something.",
             "Recommend: let them do it. A hand-sprayed edge on bare steel is where rust starts.", "open"),
    ]))

    S.append(Section("checklist", "Before ordering", "Measurements that gate an order. [HOOK] ones no longer gate anything: the clamp design does not care whether the panel is magnetic or what the top corner radius is. That is the point of it.",
                     "checklist", items=[
        Item("m-window", "[ALL] Clear window on the fridge top, front to back — MEASURED, TWICE",
             f"Two readings of the same cover: 2026-08-27 gave {p.top_clear_window:.1f} mm clear "
             f"from the rear edge (cover {609.6 - p.top_clear_window:.0f} deep); 2026-08-31 gave "
             f"400.05 (cover 209.55). Charles's word for the second was 'roughly'. The hook designs "
             f"(1 and 3) centre the plate on the case depth, which puts the {p.neck_w:.0f} mm arm's "
             f"front edge {p.top_clear_window - (609.6 + p.neck_w) / 2:.1f} mm from the cover on "
             f"the first reading and TOUCHING it on the second. The clamp design's top bar reaches "
             f"only tens of mm and is not affected.",
             "The hook generator still carries the first reading. Resolve with one measurement; "
             "if 400 stands, move the hook plate ~10 mm rearward (plate_from_rear_override) or "
             "lift the cover, which Charles says is removable.", "open"),
        Item("m-height", "[ALL] Height to the TOP OF THE CASE, not the hinges",
             f"Design assumes Samsung's published {p.fridge_height:.0f} mm. Sets the neck length and "
             "therefore the screen height.", "", "blocked"),
        Item("m-magnetic", "[HOOK] Is the side panel actually magnetic? — YES, measured 2026-08-26",
             "Checked on the actual unit: the TOP and the SIDES are both magnetic. That confirms "
             "the arm retention magnets will do their job, so all eight are fitted in the first "
             "order. It also demotes the non-magnetic-panel fallback behind the 190 mm arm width "
             "from a design driver to free insurance.",
             "The hook carries all the weight either way — this was never load-bearing.", "settled"),
        Item("m-radius", "[HOOK] Top corner radius",
             f"The {p.arm_pad:.1f} mm pad covers up to R{rep['max_fridge_corner_radius_covered_mm']:.0f} mm, "
             "so this is a confirmation rather than an input.", "", "blocked"),
        Item("m-fan", "[ALL] Photograph the display's rear box",
             "TWO features in the box face, both SCALED off Waveshare's raster drawing to ±5 mm: "
             "the Pi fan at ~R82 (~30 dia) and the GPIO slot at ~R107. The hook plate's four vent "
             f"windows sit at R{G.DISPLAY.rear_face_feature_radius:.1f}, an average of the two, so "
             "one covers the fan in every rotation; the clamp design's plate stops short of both.",
             "Neither feature is dimensioned anywhere. One photo with a rule across the box "
             "settles the windows for designs 1 and 3 and the plate height for design 2.", "open"),
        Item("m-h-requote", "[HYBRID] Re-quote the plate at SendCutSend",
             "The $177.77 quote (2026-09-01, 0.119 CRS, 1 bend, matte black) was taken on a "
             "six-hole redrawing that could not take magnets. The real plate has the hook's full "
             "hole set plus four strut holes: same bounding box to the millimetre, more cut length. "
             "Upload strut/dxf/H_hook_plate.dxf and re-quote; expect a small increase.",
             "Nothing is in a cart. The four clamp-design DXFs also moved 0.38 mm when the bend "
             "deduction went to the published value — re-upload those too before any order.",
             "open"),
        Item("m-a-stock", "[ANGLE] Price the aluminium for real",
             "The angle is priced from Speedy Metals; the two bars and the 5 in bar are ESTIMATES from a "
             "metals4u price range. Three items, one order from one supplier.", "", "open"),
        Item("m-a-foam", "[ANGLE] Source 5/16 in neoprene foam strips",
             "The 8 mm magnet standoff wants 7.94 mm foam. McMaster stocks it; not yet priced.", "", "open"),
        Item("m-thread", "[ALL] VESA insert thread depth",
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

    S.append(Section("hnumbers", "Design 3 — the numbers",
                     "Read from strut/dxf/H_hook_plate.json, which the hook generator wrote and the "
                     "audit accepted — these cannot drift from the cut file.", "table",
                     columns=["", "value", "note"],
                     rows=[
        ("Material", f"A36/1008 mild steel {h3.plate_t / 25.4:.3f} in ({h3.plate_t:.2f} mm) CRS", "matte black"),
        ("Flat pattern", f"{hook3['flat']['width_mm']:.0f} × {hook3['flat']['height_mm']:.2f} mm",
         f"1 bend, deduction {h3.bend_deduction:.2f} mm (SendCutSend published)"),
        ("Holes / windows", f"{len(hook3['holes'])} / {len(hook3['windows'])}",
         f"the hook's set plus {sum(1 for x in hook3['holes'] if x['tag'] == 'strut_bolt')} strut bolts"),
        ("Strut bolt rows", f"{rows3[0]:.2f} and {rows3[-1]:.2f} mm above the bottom edge",
         f"{h3.strut_spacing:.2f} centres; picked from {len(h3.candidate_rows)} candidate slots"),
        ("Plate mass", f"{hook3['engineering']['plate_mass_kg']:.2f} kg", "steel only"),
        ("Phase 1 (magnets): neck / body SF", f"{s3['magnets'].neck_sf:.0f}x / {s3['magnets'].body_sf:.0f}x",
         f"hangs {s3['magnets'].hanging_lbf:.1f} lb; screen edge {s3['magnets'].screen_edge_mm:.3f} mm strip, 0.065 FEA"),
        ("Phase 2 (struts): neck / body SF", f"{s3['struts'].neck_sf:.0f}x / {s3['struts'].body_sf:.0f}x",
         f"beam between rows; screen edge {s3['struts'].screen_edge_mm:.3f} mm strip, 0.036 FEA"),
        ("Magnet vs strut standoff", f"{h3.magnet_standoff:.2f} vs {h3.strut_standoff:.2f} mm",
         "the magnets come OFF when the struts go on"),
        ("Strut", f"{h3.strut_ft:.0f} ft McMaster 3310T791 x2",
         f"stands {h3.strut_above_plate:.0f} mm above the plate top, behind the display"),
    ]))
    qrows = []
    for q in PR.all_quotes():
        for g in q.groups:
            for ln in g.lines:
                pr = ln.price
                qrows.append((f"design {q.design}", g.title, f"{ln.qty:g} x {ln.item}",
                              "NOT PRICED" if ln.total is None else f"${ln.total:.2f}",
                              f"{pr.source} {pr.date}".strip(), pr.note))
        if q.design == 3:
            qrows.append((f"design {q.design}", "PHASE 1 — first order", "", f"${PR.phase(q, 1):.2f}", "", ""))
            qrows.append((f"design {q.design}", "PHASE 2 — the kit", "", f"${PR.phase(q, 2):.2f}", "", ""))
        qrows.append((f"design {q.design}", "PRICED TOTAL, as listed", f"{q.unpriced} lines not priced",
                      f"${q.priced:.2f}", "", ""))
        b = PR.budget(q)
        swaps = "; ".join(f"{ln.item.split(' — ')[0]} ${ln.total:.2f}" for g in b.groups for ln in g.lines
                          if ln.key.startswith("b_"))
        qrows.append((f"design {q.design}", "BUDGET-SOURCED", f"{b.unpriced} lines not priced",
                      f"${b.priced:.2f}" + (f" (phase 1 ${PR.phase(b, 1):.2f} + kit ${PR.phase(b, 2):.2f})" if q.design == 3 else ""),
                      "sourced 2026-09-02", swaps))
    S.append(Section("quotes", "What each design costs",
                     "Three quotes from ONE price table (prices.py). Dated vendor observations, never "
                     "derived. Design 3's phase 1 is design 1 rebased to 0.119 in and 4 magnets; its "
                     "kit is design 2's feet and lower clamp. Display and PSU excluded — same purchase "
                     "whichever design wins. Nothing in a cart.", "table",
                     columns=["design", "group", "line", "cost", "source", "note"], rows=qrows))

    e4 = d4["engineering"]
    S.append(Section("anumbers", "Design 4 — the numbers",
                     "From angle/dxf/D4_params.json, which angle/angle.py wrote after validating — these "
                     "cannot drift from the drill templates.", "table",
                     columns=["", "value", "note"],
                     rows=[
        ("Stock", "2 x 2 x 3/16 angle 12 in; 2 x 1/4 bar 24 in x2; 5 x 3/16 bar 12 in", "6061-T6, bare"),
        ("Clip position", f"{e4['clip_from_rear_mm']:.0f} mm from the rear edge", f"{e4['hinge_margin_mm']:.0f} mm to the hinge cover; screen {e4['display_bias_rearward_mm']:.0f} mm rearward"),
        ("Hanging / bearing", f"{e4['hanging_lbf']:.1f} lb / {e4['bearing_psi']:.2f} psi", "2 in x 12 in on 5/16 in foam"),
        ("Magnets", f"4 x MM-C-36 at {a4.bar_spacing:.0f} centres, rows {e4['magnet_rows_mm'][0]:.0f} / {e4['magnet_rows_mm'][1]:.0f}", f"derated {e4['magnet_derated_lbf']:.1f} lb; SF touch {e4['magnet_sf_touch']:.0f}x, peel {e4['magnet_sf_peel']:.0f}x, grab {e4['magnet_sf_grab']:.1f}x"),
        ("Bar bending", f"{e4['bar_overturning_psi']:.0f} psi, SF {e4['bar_overturning_sf']:.0f}x", "35 ksi yield"),
        ("Plate bending", f"{e4['plate_psi']:.0f} psi, SF {e4['plate_sf']:.0f}x", "weak axis, 5 in strip"),
        ("Screen edge under 5 lb", f"{e4['bar_touch_flex_mm']:.3f} mm", "bar as a beam between its magnets"),
        ("Plate vs fan opening", f"{e4['plate_fan_clearance_mm']:.1f} mm", "against a ±5 mm scaled figure — measure"),
        ("Display face", f"{e4['display_face_mm']:.0f} mm off the panel", "8 + 6.35 + 4.76 + 25 + 18"),
        ("Holes to drill", f"{sum(len(p['holes']) * p['qty'] for p in d4['parts'].values())}", "three DXF templates, audited"),
    ]))

    strut = root / "strut"
    found = (sorted(root.glob("*.svg")) + sorted(strut.glob("*.svg"))
             + sorted((strut / "dxf").glob("*_preview.svg")) + sorted((root / "angle").glob("*.svg")))
    rel = lambda f: f.relative_to(root).as_posix()
    S.append(Section("diagrams", "Diagrams",
                     "DIAGRAM_COUNT drawings, all generated from the same parameters as the cut file.",
                     "diagrams", items=[Item(rel(f), *DIAGRAM_INFO.get(rel(f), (f.stem, "", "hook"))[:2],
                                             meta=DIAGRAM_INFO.get(rel(f), ("", "", "hook"))[2])
                                        for f in found]))
    ctx = {"files": {rel(f): f.stat().st_mtime for f in found}, "params": p, "report": rep}
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
PAGES = {"hybrid": "index.html", "hook": "hook.html", "clamp": "clamp.html", "angle": "angle.html"}
NAV_HIDE = {"angle"}      # still built, reachable by URL, but REJECTED — not in the nav
TITLES = {"hybrid": "FRIDGE-SIDE CHORE DISPLAY",
          "hook": "DESIGN 1 — THE HOOK ALONE",
          "clamp": "DESIGN 2 — CLAMPED STRUT",
          "angle": "DESIGN 4 — STOCK ALUMINIUM"}
SUBS = {"hybrid": "design 3: the hook, with the plate prepared for struts — being ordered",
        "hook": "finished and quoted; design 3 is this plate with four more holes",
        "clamp": "floor-standing fallback; its feet and lower clamp are design 3's support kit",
        "angle": "the hook in hardware-store 6061, hand-drilled; the cheapest to try"}
PAGE_TITLES = {"hybrid": "Fridge display mount — design 3, hook with optional strut",
               "hook": "Fridge display mount — design 1, the hook",
               "clamp": "Fridge display mount — design 2, clamped strut",
               "angle": "Fridge display mount — design 4, stock aluminium"}
NAV_LABEL = {"hybrid": "Design 3 — being ordered", "hook": "Design 1 — hook", "clamp": "Design 2 — clamped strut",
             "angle": "Design 4 — stock aluminium"}

# Which groups and which items belong on each page. Items are tagged [HYBRID], [HOOK], [CLAMP]
# or [ALL]; design 3 IS the hook plate, so its page carries the hook's items as well as its own.
VARIANTS = {
    "hybrid": {"groups": [("hybrid", "Design 3 — the plate prepared for struts"),
                          ("hook", "Design 1 — the hook this is built on"),
                          ("shared", "Background — applies to any mount")],
               "drop_sections": {"parity", "numbers", "prices", "hprices", "anumbers"},
               "keep": lambda t: t.startswith(("[HYBRID]", "[HOOK]", "[ALL]"))},
    "hook":   {"groups": [("hook", "Design 1 — the hook"),
                          ("shared", "Background — applies to any mount")],
               "drop_sections": {"parity", "hnumbers", "hprices", "anumbers"},
               "keep": lambda t: t.startswith(("[HOOK]", "[ALL]"))},
    "clamp":  {"groups": [("clamp", "Design 2 — the clamped strut"),
                          ("shared", "Background — applies to any mount")],
               "drop_sections": {"numbers", "prices", "hnumbers", "hprices", "anumbers"},
               "keep": lambda t: t.startswith(("[CLAMP]", "[ALL]"))},
    "angle":  {"groups": [("angle", "Design 4 — stock aluminium"),
                          ("shared", "Background — applies to any mount")],
               "drop_sections": {"parity", "numbers", "prices", "hnumbers", "hprices"},
               "keep": lambda t: t.startswith(("[ANGLE]", "[ALL]"))},
}


def filter_sections(sections: list[Section], variant: str) -> list[Section]:
    """Split the one model into the two pages without duplicating any content."""
    from dataclasses import replace
    cfg = VARIANTS[variant]
    want = {k for k, _ in cfg["groups"]}
    RETITLE = {
        "hybrid": {"decisions": ("Decisions",
                                 "Design 3's own, then the hook decisions it inherits unchanged."),
                   "checklist": ("Before ordering",
                                 "What gates the first order: the plate, the magnets, the bolts.")},
        "hook": {"decisions": ("Decisions, as they stood",
                               "Frozen with design 1. Design 3 inherits every one of them."),
                 "checklist": ("Measurements it needed",
                               "Kept for the record; the live list is on design 3's page.")},
        "clamp": {"decisions": ("Open decisions",
                                "Things waiting on you for the clamped strut."),
                  "checklist": ("Before ordering",
                                "Measurements that gate an order for this design on its own.")},
        "angle": {"decisions": ("Decisions",
                                "Design 4's own; it inherits the hook's load-path reasoning, not its parts."),
                  "checklist": ("Before buying stock",
                                "What gates a trip to the metal supplier.")},
    }[variant]
    out: list[Section] = []
    for sec in sections:
        if sec.id in cfg["drop_sections"]:
            continue
        if sec.id == "status":
            # The overview of all three designs belongs on every page; only the tags come off.
            items = [replace(i, title=re.sub(r"^\[[A-Z]+\] ", "", i.title)) for i in sec.items]
        elif sec.kind == "diagrams":
            items = [i for i in sec.items if (i.meta or "study") in want]
        elif sec.kind == "table":
            out.append(sec)
            continue
        else:
            # The tags did their job while both designs shared a page. Now that each page IS one
            # design, they are noise — strip them rather than leave a label nothing contrasts with.
            items = [replace(i, title=re.sub(r"^\[[A-Z]+\] ", "", i.title))
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


BANNERS = {
    "hybrid": "",
    "angle": ('<div style="background:#b00020;color:#fff;padding:9px 16px;font:600 13px/1.4 '
              'system-ui,sans-serif">DESIGN 4 &mdash; REJECTED 2026-09-02. Stock aluminium, hand-drilled: validated, '
              'cheapest, and not wanted &mdash; the owner will not hand-drill it. Kept for the record. '
              'See the index page for what is being ordered.</div>'),
    "hook": ('<div style="background:#1b6ea8;color:#fff;padding:9px 16px;font:600 13px/1.4 '
             'system-ui,sans-serif">DESIGN 1 &mdash; the hook alone. Finished and quoted, and the '
             'basis of design 3, which is this plate cut thinner with four strut holes. See the '
             'index page for what is being ordered.</div>'),
    "clamp": ('<div style="background:#c8791a;color:#fff;padding:9px 16px;font:600 13px/1.4 '
              'system-ui,sans-serif">DESIGN 2 &mdash; the clamped strut, standing on the floor. A '
              'standalone fallback; its feet and lower clamp are also design 3\'s support kit. See '
              'the index page for what is being ordered.</div>'),
}


def build(root: Path, out: Path, variant: str, model=None) -> int:
    global GROUP_ORDER
    sections, ctx = model if model else build_sections(root)
    sections = filter_sections(sections, variant)
    GROUP_ORDER = VARIANTS[variant]["groups"]
    nav = " ".join(f'<a href="#{s.id}">{esc(s.title)}</a>' for s in sections)
    for v, page in PAGES.items():
        if v != variant and v not in NAV_HIDE:
            nav += f' <a href="{esc(page)}" class="xpage">{esc(NAV_LABEL[v])} \u2192</a>'

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
{BANNERS[variant]}<header><div class="bar">
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
    # Three pages from ONE model: design 3 on the index, its two parents on their own pages.
    model = build_sections(a.root)
    rc = 0
    for variant, page in PAGES.items():
        rc |= build(a.root, a.out.parent / page, variant, model)
    # The hook used to live at archive.html and that URL has been shared; keep it pointing home.
    (a.out.parent / "archive.html").write_text(
        '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=hook.html">'
        '<title>moved</title><a href="hook.html">The hook design moved to hook.html</a>\n',
        encoding="utf-8")
    if not a.no_png:
        LOG.info("Rasterising for Preview (%dx) — Preview has no SVG support:", a.png_scale)
        LOG.info("Wrote %d PNGs", len(export_pngs(a.root, a.png_dir, a.png_scale)))
    if a.open:
        subprocess.run(["open", str(a.out)])
    return rc


if __name__ == "__main__":
    sys.exit(main())
