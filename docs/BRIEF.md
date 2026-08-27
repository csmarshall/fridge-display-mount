> **SUPERSEDED — historical record, do not build from this.**
> This is the ORIGINAL brief, kept verbatim so the provenance of each decision stays auditable.
> It describes a **different refrigerator**. The build target is a **Samsung RS23A500ASR**
> counter-depth side-by-side: 1743.1 mm to top of case, 609.6 mm deep, top and sides both
> magnetic, top measured FLAT. Every fridge-specific number below has been retracted — see
> `CLAUDE.md` §2 for what carried over and what did not. Material also changed from 5052
> aluminium to 0.188 in mild steel (`docs/PRICE-STUDY.md`).

I'm building a magnetic mount that hangs a 23.8" touchscreen on the side panel of a refrigerator. I want you to build the parametric CAD-generation toolchain and the fabrication package for it.

Work in this repo. Create a CLAUDE.md capturing the design invariants below before you write any code, so they survive compaction.
Hardware
Display: Waveshare 23.8" FHD Monitor (SKU 34025)

555.23 (H) × 324.65 (V) × 18.00 (D) mm
3.94 kg
VESA 100 × 100
12 V input, ≥3 A required to boot, 36 W typical
Aluminium enclosure, optically-bonded toughened glass, 10-point capacitive touch
Raspberry Pi 5 mounts internally; enclosure has reserved airflow vents
Bundled PSU is 12 V 5 A (60 W)
Spec source: https://docs.waveshare.com/23.8inch_FHD_Monitor

Mounting surface: LG side-by-side refrigerator (US model), painted steel side panel, approximately 0.6–0.9 mm sheet over foam insulation. LG side-by-sides use a single formed steel wrapper for both sides and the top, so the top edge is a real sheet-metal bend rather than an assembled joint — expect a corner radius in the 6–15 mm range. Side panels are almost always painted steel even on PrintProof stainless models, so magnetic is the likely outcome — but the build still has to survive a non-magnetic panel (see load path below).

Watch for three LG-specific features when validating fit:

A shallow crown on the top panel (wrappers are often domed for rigidity). A rigid 130 mm arm can rock fore-aft on a crowned surface.
Hinge cover caps at the top front corners.
Cable and waterline routing with a step-down at the rear.

The arm must sit mid-depth, clear of all three.
Design that has already been settled — do not re-litigate these
1. The load path is a hook, not friction. A one-piece bent bracket reaches over the top edge of the fridge. The horizontal ARM rests on the fridge top; the entire vertical load transfers into bearing at the top corner. The VERTICAL SPINE drops down the side panel. Magnets carry zero vertical load.

This matters because magnets are rated for pull on thick steel at zero gap, and neither condition applies. Derate to ~35% of rated on fridge sheet, then multiply by μ (≈0.7 rubber-faced, ≈0.2 bare nickel) to get shear capacity. Vendor data confirms the penalty: totalElement rates a 43 mm rubber pot magnet at 33.5 lb vertical pull but only 7 lb horizontal. Magnet-only mounting would need roughly 15× the display weight in rated pull force. The hook eliminates that entire failure mode and makes the design work even if the panel turns out to be non-magnetic 304 stainless.

2. Touch input is the governing magnet load. Pressing near the outer edge of the screen applies torsion about the vertical spine axis:

M_torsion   = F_press × (screen_width / 2)

F_per_side  = M_torsion / magnet_spacing

A 5 lb press 278 mm from centre = ~55 in·lb. Over a 240 mm magnet spacing that's ~6.1 lbf per side. Over a 60 mm spine it's 23 lbf. The plate must be wide. Treat magnet spacing as a load-bearing dimension and warn loudly if any parameter change shrinks it.

3. Peel is negligible here, but compute it anyway.

T_peel = W × d / H

where d = CG offset from the fridge face and H = magnet-to-bottom-pad distance. The display's 18 mm depth keeps d ≈ 26 mm, so T ≈ 0.84 lbf. Report it; don't design around it.

4. The corner radius mismatch is a solved problem — size the pad, don't chase the radius. Nobody publishes sheet-metal bend radii for appliance cabinets, and you don't need one. Let R_f be the fridge's top corner radius and R_b the bracket's inside bend radius (6.35 mm for 3/16" 5052).

R_f < R_b: bracket flats seat cleanly on the fridge flats, air void at the corner. Ideal — the arm bears across its full width. Sponge fills the void.
R_f > R_b: the bracket rides up on the corner and its flats lift off by

flat_gap = (R_f − R_b) × (1 − 1/√2) ≈ 0.293 × (R_f − R_b)

At R_f = 12 mm that's 1.65 mm; even at an implausible R_f = 20 mm it's 4.0 mm. A 10 mm closed-cell sponge pad absorbs the entire plausible range. Implement flat_gap as a function in the generator, report it across R_f = 3–20 mm, and assert the specified pad thickness covers the worst case with compression to spare. Do not add a second bend or a joggle to chase the radius.

5. Other invariants.

Bottom pad thickness must exactly equal the magnet standoff, or the plate sits skewed.
The arm pad must be closed-cell sponge, thick enough to conform to the fridge's top corner radius. A rigid bracket landing on that folded sheet-metal edge will line-load and crease it.
Do not blank off the display's rear vents with solid plate. A Pi 5 behind an unvented slab will throttle.
A flat plate against a wall is loaded in its weak bending axis. Check it; add ribs or thickness rather than assuming.
Manufacturing target: SendCutSend
Verify all of these against their current published specs before you rely on them — fetch the pages, don't trust my numbers. They change.

Material: 5052-H32, 3/16". Not 6061-T6 — it cracks along tight bends. 5052 is among the most formable aluminums and working stress here is ~500 psi against ~28 ksi yield, so the softer alloy is free.
Effective bend radius after bend for 3/16" 5052: 0.250"
Minimum flat flange length: ~1.150" worst case, required on both sides of the bend line for material ≥0.187"
Dies span 0.472"–1.575"; keep cut features at least half the die width from the bend line
2D uploads: all objects on one layer, no open contours, floating interiors bridged
Bend lines are placed interactively in their browser tool — do not put a bend line in the DXF, it will be rejected
Bend deduction comes from their bending calculator, not from a formula you invented
Deliverables
generate_bracket.py — parametric flat-pattern generator using ezdxf.

Formed (post-bend) dimensions are the inputs; derive the flat by subtracting bend deduction.
Expose neck length, bend deduction, body width/height as CLI args.
Emit rounded corners via LWPOLYLINE bulge values, computed from the turn angle at each vertex — handle convex and reflex corners with the same code path. Sign the bulge from the 2D cross product.
Validate before writing. Check flange lengths both sides, feature clearance from the bend line, hole-to-window edge distance (≥1× thickness), magnet disc overhang past the plate edge. Refuse to write files if a check fails; exit non-zero.

bracket_flat.dxf — the upload file. mm units ($INSUNITS = 4), layer 0 only, every contour closed.

bracket_preview.svg — annotated visual check showing the bend line position, magnet disc footprints, and key dimensions. Clearly marked as reference-only, not for upload.

SENDCUTSEND-ORDER.md — order configuration table, bend setup parameters, hole schedule, constraint-compliance table, a full BOM (bracket, magnets, fasteners, soft goods, electrical), an assembly sequence, and a pre-order measurement checklist for the fridge.

audit_dxf.py — reads the generated DXF back and asserts: single layer, zero open contours, correct units, expected extents, expected hole diameters. This is the acceptance test; run it after every generation.
Suggested starting geometry
Landscape orientation. Body 300 × 300 mm (hides behind the 555 × 325 display), neck 130 mm wide, arm 130 mm from the bend apex. VESA 100 × 100 centred on the body. Four Ø4.5 mm magnet holes inset 30 mm from each body corner. Lightening and ventilation: a Ø90 mm centre opening plus four 100 × 40 mm edge windows.

Derive everything else. If your validation finds a better arrangement, take it — but keep magnet spacing ≥ 240 mm and tell me what changed and why.
Hardware BOM constraints
Magnets: Ø43 × 6 mm rubber-coated neodymium pot magnets with M4 female thread. Not male-stud — a stud needs a nut on the display-facing side, which breaks the flat mounting plane.
Use M4 spacers between plate and display: they clear the magnet-screw heads and open an air channel.
Power: budget 36 W (display) + up to 27 W (Pi 5) = 63 W against the bundled 60 W brick. Flag the upgrade.
Code style
Timestamped logging on every operation. INFO for major steps, DEBUG for per-feature detail (per-corner fillet math, hole positions, validation results). Configurable level via CLI. Consistent format across all modules. Include relevant variable state in DEBUG lines.
Self-documenting names, inline comments only where the logic is non-obvious (the bulge math needs one, the bend deduction derivation needs one).
No dead code, no unused variables, no placeholder stubs — implement everything.
unset TMOUT near the top of any shell script.
Type hints and dataclasses where they earn their keep.
Parameters I still need to measure
Leave these as clearly-marked CLI defaults with a warning in the docs:

Neck length — (fridge top → desired display top edge) − 12 mm. Default 100 mm.
Bend deduction — from SendCutSend's calculator. Estimate from BD = 2 × (R+T)tan(45°) − (π/2)(R + K·T) and state your K assumption.
Orientation — build landscape first, but make portrait reachable by parameter. Portrait is mechanically better (torsion arm drops from 278 mm to 162 mm), so note that in the docs.
Fridge top corner radius — default to a 12 mm assumption. It only affects pad sizing (see invariant 4), never the cut geometry. Document the tangent-point measurement in the order doc: hold a straightedge flat against the side and another flat on the top; they intersect at the theoretical sharp corner; measure from that intersection along the top surface to where the flat stops and the curve begins — for a 90° corner that distance is the radius. Cross-check down the side face. Quick screen: a US quarter is Ø24.26 mm (R = 12.13 mm), so if it rocks and won't seat in the corner, R_f is under 12 mm.

Start by writing CLAUDE.md, then the generator, then the audit script. Show me the rendered preview before you write the order document.

