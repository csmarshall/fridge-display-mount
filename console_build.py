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
    "approval_sheet.svg": ("Approval sheet", "For significant-other review. Three views plus plain-language facts.", "key"),
    "bracket_preview.svg": ("Technical flat pattern", "The cut file, annotated. Reference only.", "key"),
    "magnet_pattern_study.svg": ("Magnet layout study", "Does staggering help? Closed-form comparison.", "key"),
    "spacing_explainer.svg": ("Magnet spacing floor", "Why a bigger disc runs out of plate.", "key"),
    "assembly_drawing.svg": ("Assembly, 23.8in", "Display and rear box as transparent overlays.", "detail"),
    "assembly_drawing_27in.svg": ("Assembly, 27in", "Same bracket, larger panel.", "detail"),
    "ergonomics_sweep.svg": ("Ergonomics sweep",
                            "Mounting height vs neck length, on the Samsung 1743 mm case height. "
                            "Note the built neck (257 mm) is not one of the four panels — they "
                            "bracket it.", "study"),
    "arm_width_sweep.svg": ("Arm width sweep",
                           "Arm width vs hold-down on the Samsung 610 mm counter-depth top, "
                           "against the MEASURED 406 mm clear window.", "study"),
    "thickness_study.svg": ("Thickness study — SUPERSEDED",
                           "ALUMINIUM-era: highlights 0.187 in 5052 at 5.89 kg. The build is "
                           "A36 steel 0.187 in at 5.81 kg. See docs/PRICE-STUDY.md instead.",
                           "study"),
    "variant_compare.svg": ("Variant comparison", "The reach variants side by side.", "study"),
    "pad_explainer.svg": ("Pad budget", "Why the pad thickness is locked to the magnet height, and what the corner radius costs.", "study"),
    "orientation_compare.svg": ("Orientation", "Portrait vs landscape, counter-depth.", "study"),
    "display_compare.svg": ("23.8 vs 27 inch", "Both panels, same bracket.", "study"),
    # Was falling through to a snake_case filename title with no caption, sitting uncaptioned
    # among real deliverables. It is a TEST harness — a tool for judging a validator refusal —
    # not a cable harness, and not a fabrication drawing.
    "stack_detail.svg": ("Fastener sandwich at one magnet",
                        "Every stack shape that fits, in true section — magnet | plate | washer | "
                        "nut, and whether the fixed 1/2 in stud still reaches.", "key"),
    "magnet_primer.svg": ("Why not just magnets?",
                         "Pull vs shear vs peel, and why a 175 lb magnet delivers 12 lb where "
                         "it counts. Start here if the hook looks like overkill.", "key"),
    "fastener_matrix.svg": ("Every fastener permutation",
                           "All 39 nut x washer x threadlocker combinations with the arithmetic "
                           "shown: plate + washer + nut vs stud.", "key"),
    "force_table.svg": ("Force by direction and magnet count",
                       "What it takes to shift or unseat it, 6 to 15 magnets, in lb and newtons.",
                       "key"),
    "mount_views.svg": ("Both faces of the mount",
                       "Front and back side by side — magnets and foam on the fridge face, "
                       "VESA and spacers on the display face.", "key"),
    "hinge_clearance.svg": ("Hinge cover clearance",
                            "Plan view: where the arm and the hinge cover meet, or miss. The one "
                            "view that dimensions it.", "key"),
    "harness_view.svg": ("Magnet placement validator — deliberate FAIL",
                        "Shows a configuration the validator REFUSES, on purpose, so a refusal "
                        "can be judged rather than obeyed. NOT the built part.", "study"),
}
GROUP_ORDER = [("key", "Key drawings"), ("detail", "Assembly detail"), ("study", "Background studies")]


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
    written = []
    for svg in sorted(root.glob("*.svg")):
        w, h = svg_size(svg)
        png = out_dir / (svg.stem + ".png")
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        f"--force-device-scale-factor={scale}", "--virtual-time-budget=3000",
                        f"--screenshot={png}", f"--window-size={w},{h}", svg.resolve().as_uri()],
                       capture_output=True, text=True)
        if png.exists():
            written.append(png)
            LOG.info("  %-28s -> %s (%dx%d @%dx)", svg.name, png.name, w, h, scale)
        else:
            LOG.error("  %-28s FAILED to rasterise", svg.name)
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

    S.append(Section("decisions", "Open decisions", "Things waiting on you. Everything else is settled.",
                     "decisions", items=[
        Item("d-magnets",
             "Magnet layout and count — the four corners are provably optimal",
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
             "What it takes to pull it off — by direction",
             " ".join(f"{name}: {force:.0f} lb ({why})."
                      for name, _, force, why in detach_modes if force != float("inf")),
             f"Caveat: these assume a rigid plate with every magnet releasing at once. Peeling "
             f"beats them one at a time — lifting one corner of the arm breaks a single magnet at "
             f"~{rep['magnet_derated_pull_lbf']:.0f} lb using the arm as the lever. So these are "
             f"resistance-to-accident numbers, NOT removal forces. Weakest direction is sliding it "
             f"along the panel, which MOVES it rather than detaching it — the hook does not resist "
             f"that axis.", "settled"),
        Item("d-vents",
             "Vent windows: keep them",
             "Quoted live. Removing all four makes the part $0.68 DEARER ($97.38 vs $96.70) on an "
             "identical blank. 23% less cutting does not pay for the 148 cm² of steel you then keep "
             "— their material component tracks part area and cut time is cheap at this size.",
             "No decision needed unless you want them gone for looks. They also save 116 g.", "settled"),
        Item("d-lighten",
             "Lightening the plate to save material — not worth it",
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
             "How far the arm reaches onto the fridge top — SETTLED at 180 mm",
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
             f"Screen centre at {rep['screen_centre_height_mm']:.0f} mm — APPROVED 2026-08-27",
             f"A 5 ft 1 in viewer's eye line ({1549*0.935:.0f} mm) lands on the screen. A 6 ft 4 in "
             f"viewer's ({1930*0.935:.0f} mm) sits {1930*0.935 - rep['screen_top_portrait_mm']:.0f} mm "
             "ABOVE the top edge, so they look down at it. Normal for a fridge-side display, but it "
             "is a choice.",
             "Charles confirmed the viewing height looks right on the actual fridge. "
             "Adjustable with --screen-centre-height if that ever changes.", "settled"),
        Item("d-thickness",
             "Plate thickness — SETTLED at 0.187 in / 4.75 mm HRPO (SendCutSend list it as .188)",
             f"Chosen for heft and margin, NOT for stiffness you can feel: plate flex under a "
             f"touch is 0.016 mm here against 0.064 mm at 0.119 in, and neither is perceptible. "
             f"What it buys is {rep['bracket_mass_kg']:.2f} kg instead of 3.71 kg, plus the best "
             f"$/kg and stiffness-per-dollar in the material sweep. Hot-rolled is cheaper stock "
             f"than cold-rolled, which is why .188 HRPO undercuts .135 CRS despite being thicker.",
             "+$11.21 over the 0.119 build. Commercial TV mounts run 1.8-2.7 mm; this is 4.75 mm.",
             "settled"),
        Item("d-coat",
             "Powder coat at SendCutSend, or spray it yourself",
             "Matte black powder adds $66–70 and pushes delivery Aug 31 → Sep 3. Bare CRS will "
             "surface-rust in a kitchen, so it needs something.",
             "Recommend: let them do it. A hand-sprayed edge on bare steel is where rust starts.", "open"),
    ]))

    S.append(Section("checklist", "Before ordering", "Four measurements gate the order. Nothing else does.",
                     "checklist", items=[
        Item("m-window", "Clear window on the fridge top, front to back — MEASURED 2026-08-27",
             f"{p.top_clear_window:.0f} mm clear from the rear edge to the hinge cover, against a "
             f"{p.neck_w:.0f} mm arm width — fits with {p.top_clear_window - p.neck_w:.0f} mm to "
             f"spare ({p.top_clear_window / p.neck_w:.2f}x). The hinge cover occupies the front "
             f"{609.6 - p.top_clear_window:.0f} mm and is removable/adjustable, so even a clash "
             f"would be recoverable. This was the likeliest recut risk; it is now closed.",
             "", "settled"),
        Item("m-height", "Height to the TOP OF THE CASE, not the hinges",
             f"Design assumes Samsung's published {p.fridge_height:.0f} mm. Sets the neck length and "
             "therefore the screen height.", "", "blocked"),
        Item("m-magnetic", "Is the side panel actually magnetic? — YES, measured 2026-08-26",
             "Checked on the actual unit: the TOP and the SIDES are both magnetic. That confirms "
             "the arm retention magnets will do their job, so all eight are fitted in the first "
             "order. It also demotes the non-magnetic-panel fallback behind the 190 mm arm width "
             "from a design driver to free insurance.",
             "The hook carries all the weight either way — this was never load-bearing.", "settled"),
        Item("m-radius", "Top corner radius",
             f"The {p.arm_pad:.1f} mm pad covers up to R{rep['max_fridge_corner_radius_covered_mm']:.0f} mm, "
             "so this is a confirmation rather than an input.", "", "blocked"),
        Item("m-fan", "Photograph the display's rear box",
             f"The Pi fan opening is at R{G.DISPLAY.rear_face_feature_radius:.1f} mm from the VESA "
             "centre, scaled off a raster drawing to ±5 mm. The vent windows sit on that radius.",
             "Only matters once the panel is in hand.", "open"),
        Item("m-thread", "VESA insert thread depth",
             "Sets the M4 screw length. Any standard head clears the fridge inside the "
             f"{p.magnet_standoff:.0f} mm standoff.", "", "open"),
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
                     f"{len(found)} drawings, all generated from the same parameters as the cut file.",
                     "diagrams", items=[Item(f.name, *DIAGRAM_INFO.get(f.name, (f.stem, "", "study"))[:2],
                                             meta=DIAGRAM_INFO.get(f.name, ("", "", "study"))[2])
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


def build(root: Path, out: Path) -> int:
    sections, ctx = build_sections(root)
    nav = " ".join(f'<a href="#{s.id}">{esc(s.title)}</a>' for s in sections)
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
<title>Fridge mount — project console</title><style>{CSS}</style></head><body>
<header><div class="bar">
  <h1>FRIDGE-SIDE CHORE DISPLAY</h1>
  <span class="sub">built {time.strftime('%d %b %H:%M')}</span>
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
    ap.add_argument("--png", action="store_true", help="also rasterise every SVG into png/")
    ap.add_argument("--png-dir", type=Path, default=Path("png"))
    ap.add_argument("--png-scale", type=int, default=2)
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    rc = build(a.root, a.out)
    if a.png:
        LOG.info("Rasterising for Preview / sending (%dx):", a.png_scale)
        LOG.info("Wrote %d PNGs", len(export_pngs(a.root, a.png_dir, a.png_scale)))
    if a.open:
        subprocess.run(["open", str(a.out)])
    return rc


if __name__ == "__main__":
    sys.exit(main())
