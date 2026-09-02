# CLAUDE.md — Fridge-Side Display Mount

ONE project, THREE designs, one plate. A Waveshare 23.8" FHD touch monitor on the side panel of a
**Samsung RS23A500ASR** counter-depth side-by-side refrigerator, running a household chore board.

| # | design | where | status |
|---|---|---|---|
| 1 | **Hook** — magnetic-assisted hook bracket over the fridge top | repo root | finished, quoted, tagged `hook-final` |
| 2 | **Clamped strut** — two slotted struts to the floor, clamped top and bottom | `strut/` | standalone fallback; its feet + lower clamp are design 3's support kit |
| 3 | **Hook with optional strut** — design 1's plate, cut thinner with four strut holes, so design 2's feet can be added later without recutting | `strut/hybrid*.py`, plate via the root generator | **BEING ORDERED** |
| 4 | **Stock aluminium hook** — 2 x 2 angle clip, two 2 x 1/4 bars, a 5 in bar for the VESA, four O36 magnets; hand-drilled | `angle/` | validated, cheapest; the fallback if the plate is never cut |

Sections 1–8 below are design 1's invariants and remain the base of design 3. Section 9 carries
designs 2 and 3; section 10 carries design 4. `strut/` was its own repo (`csmarshall/fridge-strut-mount`) until 2026-09-02;
it was merged here with history because the third design's plate is built by the root generator
and two repos meant two homes for one fact.

Original brief for design 1: `docs/BRIEF.md`. Design 2's brief: `strut/BRIEF.md`.
Live session state: `session-state.md`. Published page: <https://csmarshall.github.io/fridge-display-mount/>.

---

## 1. Design invariants — SETTLED, do not re-litigate

### 1.1 The load path is a hook, not friction
One-piece bent bracket. `ARM` (horizontal) reaches over the fridge top and rests on it;
the entire vertical load transfers into **bearing at the top corner**. `NECK` + `BODY`
(the vertical spine) drop down the side panel. **Magnets carry zero vertical load.**

Rationale: magnets are rated for pull on thick steel at zero gap; neither condition holds
on 0.6–0.9 mm painted appliance sheet. Derate to **~35 % of rated** pull, then multiply by
μ (**0.2** — the specified magnet is BARE nickel; a rubber face would give 0.7 but is not what is fitted) for shear. Vendor confirmation: totalElement
rates a 43 mm rubber pot magnet at 33.5 lb vertical pull but only 7 lb horizontal.
Magnet-only mounting needs ~14x the held weight in RATED pull — **which is not actually out of reach, and this file used to imply it was.** 8 of the specified O48 magnets give 98 lbf of shear against a 21.5 lbf hanging load: SF 4.6. **Shear is therefore NOT the argument for the hook.** The argument is peel (a corner lever beats one magnet, not the total), a possibly non-magnetic panel (every number goes to zero), creep under sustained shear on paint, and the consequence being bonded glass on a floor. Overstating the shear case weakens a design that has better reasons. See `magnet_primer.svg`. The hook removes
that failure mode entirely and survives a **non-magnetic** (304 stainless) panel.

### 1.2 Touch input is the governing magnet load
Pressing near the outer screen edge applies torsion about the vertical spine axis:

```
M_torsion  = F_press x (screen_width / 2)
F_per_side = M_torsion / magnet_spacing
```

**Magnet spacing is a load-bearing dimension.** Hard floor: **240 mm**. The generator must
refuse to write files and warn loudly if any parameter change shrinks it.

### 1.3 Peel is negligible — compute and report it anyway
```
T_peel = W x d / H      d = CG offset from fridge face, H = magnet-to-bottom-pad distance
```
`d` is **derived from the mounting stack** (magnet + plate + spacer + half display depth),
never hardcoded. Report it; do not design around it.

### 1.3b Arm width vs arm reach — bounded by different things
They are **not proportional**. Arm WIDTH runs front-to-back, where the fridge top is straight; it
costs no sheet (the body already sets the bounding box) and its only limit is the clear window
between the hinge caps and the rear step-down. Arm REACH runs across the top, costs sheet length one-for-one, and is bounded by the arm pad budget.

Arm width is the fallback structural dimension: under a touch press the hook sees a couple across
the arm width, `F = M_torsion / arm_width`, which is what holds the arm down if the panel turns out
to be **non-magnetic**. 130 mm gives 1.01x margin there; 190 mm gives 1.52x.

### 1.4 Corner-radius mismatch: size the pad, do not chase the radius
`R_f` = fridge top corner radius (unpublished, unknown). `R_b` = bracket inside bend radius.

- `R_f < R_b` — bracket flats seat on fridge flats, air void at corner. Ideal. Sponge fills it.
- `R_f > R_b` — bracket rides the corner and its flats lift by
  `flat_gap = (R_f - R_b) x (1 - 1/sqrt(2)) ~= 0.293 x (R_f - R_b)`

At `R_f = 12 mm` that is 1.65 mm; at an implausible 20 mm, 4.0 mm. A 10 mm closed-cell
sponge pad absorbs the whole plausible range. `flat_gap()` is implemented in the generator,
reported across `R_f = 3–20 mm`, and asserted against the specified pad thickness.

**The pad budget is the corner-radius lift alone:** `pad >= flat_gap(R_f_envelope) x 1.2`.
~~Plus a crown term~~ — **REMOVED 2026-08-27.** The brief's fridge had a formed steel wrapper that
domes; the Samsung's top was straightedged and photographed FLAT, so the crown term had been zero
throughout and the parameter, its function and its explanatory sheet were drift waiting to happen.
If a future fridge IS crowned, the term to restore is `+ crown_rise_at(reach)`. The envelope is
`R_f = 15 mm`, the top of the range a formed steel wrapper plausibly produces; coverage beyond it is
REPORTED as sensitivity (the 1/4 in pad actually covers a measured R_f up to 19 mm at 130 mm reach)
rather than designed to, because designing to R_f = 20 would force a pad thickness that no stocked
magnet height matches.
**Do not add a second bend or a joggle.**

### 1.5 Other invariants
- Bottom pad thickness **matches the magnet standoff, biased UNDER not over** — REVISED
  2026-08-27. The old rule allowed up to +2.5 mm proud and rejected anything under; that is
  backwards. Proud means the plate lands on the pad, the magnets never reach the panel, and the
  mount is both spongier and weaker — the single soft element in an otherwise rigid stack. A
  little under lets the rigid magnets bear while the pad still protects paint. Stock now includes
  METRIC sizes because **11.5 mm sits 0.01 mm from the 11.51 mm magnet** and no imperial size is
  close. Validator bound is now **-0.60 to +0.30 mm**.
  *Implementation note — CORRECTED 2026-08-27.* An earlier version of this paragraph asserted the
  OPPOSITE rule ("the pad must never be THINNER than the magnet ... accepts 0 to +1.0 mm and
  rejects anything negative") directly below the rule above it. That text was left over from the
  6 mm-magnet era and is deleted. The code has always implemented the rule as stated above:
  `-PAD_UNDERSIZE_ALLOWANCE_MM (0.60) <= excess <= +0.30`, biased UNDER, because a pad proud of
  the magnets means the plate lands on sponge and the magnets never reach steel.
- Arm pad is **closed-cell sponge**, thick enough to conform to the top corner radius. A
  rigid bracket landing on folded appliance sheet will line-load and crease it.
- **Do not blank off the display's rear vents** with solid plate — a Pi 5 behind an
  unvented slab throttles. *Concretely:* the display's raised rear box carries the Pi's fan and GPIO
  in its FACE, ~82 mm from the VESA centre. The vent windows are therefore placed on a **radius of
  87.5 mm** rather than a margin from the plate edge, so one covers the opening in **every 90 deg
  rotation**. The M4 spacers are also load-bearing on this invariant: without them the plate bolts
  flat onto the Pi's cooling.
- A flat plate against a wall is loaded in its **weak bending axis**. Check it; add ribs or
  thickness rather than assuming.

---

## 2. Hardware

**Display — Waveshare 23.8" FHD Monitor (SKU 34025)** — verified against
<https://docs.waveshare.com/23.8inch_FHD_Monitor> and, for anything dimensional, the dimension
drawing at
<https://www.waveshare.com/img/devkit/LCD/27inch-FHD-Monitor/23.8inch-FHD-Monitor-details-size.jpg>
(2026-08-24). **The spec table's "18.00(D)" is the panel section only; overall depth is 43 mm.**

| Property | Value | Verified |
|---|---|---|
| Outer dimensions | 555.23 (H) x 324.65 (V) x 18.00 (D) mm | yes |
| Weight — **SCREEN ALONE** | 3.94 kg (8.69 lb) | yes |
| Weight — **whole mounted system** | **11.31 kg (24.9 lb)** = screen 3.94 + steel plate 5.81 + magnets 1.27 + foam 0.20 + fasteners 0.10. Screen is Waveshare's published figure (they do not say whether it includes the stand — if it does, this is conservative); steel is derived from the cut geometry; magnets/foam/fasteners are ESTIMATES. Excluded, together under 0.1 kg: M4 spacers, VESA screws, cable | part measured, part derived, part estimated |
| Input voltage | 11.5–12.5 V, **>= 3 A to boot** | yes |
| Typical power | 36 W | yes |
| Touch | 10-point capacitive, optically bonded, 6H toughened glass | yes |
| Overall depth | **43.00 mm** = 18.00 panel + **25.00 raised rear box** | dimension drawing |
| Rear box footprint | 260 x 134 mm, centred | dimension drawing |
| VESA | 100 x 100, **on the raised rear box face** | **CONFIRMED** on the dimension drawing |
| Active area / bezel | 528.04 x 297.46 mm / 13.60 mm | dimension drawing |
| Panel corner radius | R10.00 | dimension drawing |
| Pi 5 fan / GPIO opening | in the rear box FACE, on the box's **260 axis**. TWO features, not one: **fan ~R82 (~30 dia)** and **GPIO slot ~R107**. Both **SCALED** against the dimensioned 260 mm box width — Waveshare dimensions NEITHER. The old single "87.5" figure averaged them and hid that the fan is the near one, which is the only one a plate edge can foul | scaled off the dimension drawing 2026-08-31 |
| Enclosure material / Pi 5 bay | not stated | measure |
| Bundled PSU | not stated on the spec page (brief says 12 V 5 A / 60 W) | confirm in box |

Anything marked "measure" is a **pre-order checklist item**, not an assumption to build on.

**The 27in panel shares the bracket.** Waveshare's 27in FHD Monitor (SKU 33975 US) has the SAME
rear box (260 x 134 x 25), the SAME VESA 100 on that box, the SAME 43 mm depth profile and the fan
at the SAME 87.4 mm radius — only the panel size (629.62 x 367.40) and mass (4.92 kg) differ.
`--display 27` restates the load case; the generated DXF is geometrically identical, verified by
hashing the entity geometry. Drawing saved in `docs/reference/`. Upsizing does not mean recutting.

**Mounting surface — Samsung RS23A500ASR**, 23 cu ft **counter-depth** side-by-side.
Published dimensions (`docs/reference/samsung-RS23A500ASR-specsheet.pdf`), verified 2026-08-25:

| | |
|---|---|
| Case, without hinges or doors | 35 7/8" x **68 5/8"** x **24"**  =  911.2 x **1743.1** x **609.6 mm** |
| With hinges, handles and doors | 35 7/8" x 70 1/16" x 28 5/8"  =  911.2 x 1779.6 x 727.1 mm |
| Height that matters (arm rests on the CASE) | **1743.1 mm** |
| Hinge covers stand proud of the case top by | **36.5 mm** — the arm lands behind them |
| Doors project forward of the cabinet by | 117.5 mm |
| Weight | 229 lbs |

**COUNTER-DEPTH is the consequential fact.** The cabinet is only **610 mm** deep, so:
- the top surface the arm lands on is 610 mm front-to-back, not the ~850 mm of a standard-depth box
- the side panel the body hangs on is 610 mm deep, and a **555 mm landscape display leaves only
  27 mm front and back if centred**. Portrait (324.65 mm) is roomy by comparison.

**RETRACTED — these came from the brief's fridge and do not carry over.** The original brief described a different unit:
a single formed steel wrapper for both sides and the top, hence a real sheet-metal bend at the top
edge with R_f in the 6-15 mm range, and a crown from wrapper doming. **None of that is established
for Samsung.** Samsung may use a separate top panel, a different corner radius, or a plastic top
cap. Until measured, treat as UNKNOWN:
- top corner radius `R_f` — the `R_f = 15 mm` design envelope came from that wrapper reasoning
- **Hinge cover and the front-to-back clear window — MEASURED 2026-08-27.** The photo is a view
  of the **LEFT SIDE PANEL**, the face the display hangs on, so the ruler runs **front-to-back**
  along the top of that panel with its zero at the **REAR** edge.
  **How to know that reading is right:** the fridge edge reads ruler ~27.5 in. Case depth 24 in
  plus doors projecting 4.6 in = 28.6 in — it matches. Read as a FRONT view it would have had to
  span 35.9 in. Two earlier readings of this same photo treated it as a frontal view and invented
  a 213 mm ruler offset to reconcile the 8-inch gap. **The gap was the tell.** If a datum needs a
  fudge factor to work, question the framing, not the ruler.
  - hinge cover occupies the **front 203 mm** of the top (ruler 16-24 in)
  - **clear window, rear edge to cover: 406 mm**
  - **SECOND READING 2026-08-31 (design 2 work): 15.75 in -> window 400.05, cover 209.55.**
    Charles's word was "roughly". The root generator still carries 406.4; `strut/` carries
    400.05. **At 400 the hook's centred arm TOUCHES the cover** (6.6 mm clear at 406). Open on the
    page's checklist; resolve with one measurement, then make one home for it
  - arm WIDTH is 190 mm front-to-back -> the 406 mm window is **2.14x** the arm width
  - **BUT that is not the installed margin.** The plate is centred on the case depth, which puts
    the arm's front edge ~6.6 mm from the cover, not 216 mm. The 2.14x figure describes how much
    window exists; `hinge_clearance.svg` dimensions where the arm actually lands. Quote the 6.6 mm
    when asking "does it fit", and the 2.14x only when asking "is there room to move it"

  This closes "clear window on the fridge top, front to back", which the pre-order checklist
  called the likeliest recut risk. Modelled as `hinge_cover_from_rear` with a validator check on
  `neck_w`, so widening the arm cannot silently run into it.
  **The cover is also removable/adjustable** (Charles) — it lifts for installation or comes off
  entirely. Recorded as a fallback; the design does not need it.
- ~~whether the side panel is magnetic~~ — **MEASURED 2026-08-26: the top AND the sides are both
  magnetic.** Charles checked the actual unit with a magnet. This promotes two things that were
  previously hedged: (a) the arm retention magnets will actually work, so they are worth fitting
  in the first order; (b) the non-magnetic-panel fallback in section 1.3b is no longer the
  governing case for arm WIDTH. Keep the 190 mm width and its 1.52x margin anyway — it costs no
  sheet and the fallback margin is now free insurance, not a design driver
- hinge cover footprint and any rear cable/waterline step-down

Samsung's own side elevation draws the top as a flat straight line, and a straightedge laid across
it agrees (photographed 2026-08-27). Crown is no longer modelled anywhere.


---

## 3. Manufacturing target — SendCutSend

Verified 2026-08-24 against sendcutsend.com. Re-verify before ordering; these change.

| Constraint | Value | Source |
|---|---|---|
| Material | **A36/1008 mild steel, 0.187" (4.75 mm) HRPO** — as built. SendCutSend label the gauge ".188"; 0.187 in is the actual thickness and what the generator uses. ~~0.119" (3.023 mm) CRS~~ superseded 2026-08-27 | /materials/mild-steel/ |
| Why steel, not the brief's aluminium | The price study killed 0.187" 5052: it sits past a cost cliff at **$131.49** qty 1, while 0.119" steel is **$87.39** and stiffer per unit price. Steel is also what the magnets want. `--material 5052` still generates a valid part; the bend table differs (steel's effective bend radius is much tighter) so the flat pattern is NOT interchangeable. See `docs/PRICE-STUDY.md` | price study 2026-08-25 |
| Superseded alloy note | The brief specified 5052, **not 6061-T6** (cracks on tight bends). That reasoning still holds *if* aluminium is ever revisited | brief |
| Effective bend radius after bend | **0.250" (6.35 mm)** | material bending specs |
| Bend relief depth (if used) | 0.270" | material bending specs |
| Min flange length | **~1.150" (29.21 mm)**, required **both sides** of the bend line for material >= 0.187" | published for 0.250"; **not directly confirmed for 0.187"** — treated as conservative. Our flanges are 130 mm / 400 mm, so this is not close to binding |
| Die width range | **0.472"–1.575"** | /guidelines/bend-deformation/ |
| Feature clearance from bend centerline | **>= 1/2 die width** -> worst case **0.7875" (20.0 mm)** | /guidelines/bend-deformation/ |
| Min hole diameter | ~50 % of thickness -> 2.38 mm | small-geometry guidance |
| Hole-to-edge spacing | **>= 2 x thickness (9.53 mm)** — stricter than the brief's 1x; enforce 2x | small-geometry guidance |
| Max flat size (instant pricing) | 30" x 44" (762 x 1118 mm) | /materials/5052-aluminum/ |
| Bend deduction | from **their bending calculator**, not an invented formula. Our default is an estimate — see §4 | /faq/what-are-your-material-bending-specifications/ |
| 2D upload | one layer, no open contours, floating interiors bridged | brief |

**Bend lines in the DXF — SETTLED 2026-08-25 by testing against their live app.** The brief said no
bend line in the DXF. That is WRONG for their current flow. A geometry-only upload greys out Bending
and the app reports *"No bend lines detected"*, with a format table specifying **.dxf -> dashed line
(not hidden)**. The DXF therefore carries **one dashed `LINE`** at the bend centre spanning exactly
the bend length. It is a marker, not a cut path: it does not affect extents or price, and with it the
app reports "1 Bend". `audit_dxf.py` verifies its count, position, span and `DASHED` linetype — a
SOLID line would be read as a cut and would slice the part in half.

---

## 4. Parameters still to be measured (clearly-marked CLI defaults)

| Parameter | Default | How to resolve |
|---|---|---|
| Neck length | **310 mm** | Derived, not hardcoded: `neck = fridge_height - screen_centre - body_h/2`. Screen centre 1331 mm is mid-band for 5'1"-6'4". The brief's "- 12 mm" is not magic either: it is `(display_height - body_height)/2`, 12.3 mm landscape and 127.6 mm portrait. Use `--fridge-height` + `--screen-centre-height` |
| Bend deduction | **SendCutSend's PUBLISHED table** (`BEND_SPECS_MILD_STEEL`: 0.3225 in at .187, 0.1955 in at .119), NOT an estimate — an earlier version of this row said "K = 0.42 estimate" long after the generator had switched. `strut/` re-derived it with K = 0.42 until 2026-09-02 and got 5.35 mm where the table says 4.97; now it reads the same table (`strut/concept_sheet.py: SCS_MILD_STEEL_BEND`) | verify against their calculator if a new gauge is ever used |
| Orientation | **portrait — as built** | the generator default is portrait; it is mechanically better (torsion arm 278 -> 162 mm) and the counter-depth cabinet is only 610 mm deep, which a 555 mm landscape display nearly fills |
| Fridge top corner radius `R_f` | **12 mm** | affects **pad sizing only**, never cut geometry. Straightedge on the side, another on the top; they meet at the theoretical sharp corner; measure from that intersection along the top to the tangent point — for a 90 deg corner that distance is the radius. Cross-check down the side face. Quick screen: a US quarter is O 24.26 mm (R = 12.13 mm) — if it rocks and will not seat, `R_f` < 12 mm |

---

## 4b. Settled geometry (as built)
**REFRESHED 2026-08-27 against `bracket_params.json`.** Every figure below was stale — the block
had drifted a whole revision behind the generator, which is exactly the failure mode this file is
supposed to prevent. If you change a parameter, re-read the JSON rather than editing prose here.

Body **310 x 310** (hides behind the display in BOTH orientations; portrait is only 324.65 mm
wide). Magnet inset **32 mm**, giving spacing **246 x 246** against the 240 mm floor, and a
derived **7.99 mm** of plate beyond each disc — 12.7x the 0.63 mm tolerance stack.
Neck/arm width **190 mm**. Neck **257 mm**. Arm reach **180 mm** — the shortest that lands the
outermost full O48 disc on metal. Flat blank **310 x 738.8 mm**, bend line at **562.9**, bend
deduction **8.19 mm**.

**Arm retention magnets:** rows at **+36 and +144 mm** from the bend apex are FITTED; a third row
at **+90** is cut but left empty as an upgrade path. 120 mm apart across the arm. Anti-jostle only
— **zero credit in the load path**. The 54 mm row pitch is a hard floor (O48 disc + 6 mm).

**Cable retention is SLOTS, not round holes** — 5 pairs of 4.0 x 18.0 mm slots (R1.40 ends),
16.0 mm centre-to-centre so the bridge between a pair is 12.0 mm. Sized for a 1/2 in VELCRO
ONE-WRAP (12.7 mm) with 2.65 mm clearance per side, which also passes a 5/8 in strap. A flat
hook-and-loop band cannot thread a 5 mm hole; that hole size only ever suited a zip tie. Slots are
`WindowRect`s, so they are LWPOLYLINEs in the DXF, and the outermost pair sits at bend **+105**
not +115 — an 18 mm slot at +115 lands 3.5 mm from the arm tip, inside the 2x-thickness edge rule.

**Countersinks: NONE.** `countersink_vesa = False`. ~~90 deg M4 on the four VESA holes~~ —
**RETRACTED:** SendCutSend does not offer countersinking on mild steel, and it is not needed
anyway: the display stands off on M4 spacers and the 11.51 mm magnet standoff clears any
proud head against the fridge. Any standard M4 head works.

**Live quote 2026-08-27, as-built .188 in file:** cut **$112.50**, +1 bend **$126.71**,
+textured black **$197.07**. (~~$185.85 / blank 742~~ was the .119 in build.)

## 5. BOM constraints
- Magnets: **McMaster 3506K67, O 48.02 x 11.51 mm bare-nickel/zinc-cased pot, 5/16"-18 MALE
  STUD.** ~~O43 x 6 mm rubber-coated, M4 female thread~~ — **RETRACTED 2026-08-27.**
  The original rule said "not male-stud, because a stud needs a nut on the display-facing side and
  breaks the flat mounting plane." That reasoning was wrong on its own terms: the display does not
  sit on the plate, it stands off on M4 spacers, so there is no flat mounting plane for a nut to
  break — the nut lives in that air gap with ~10 mm of clearance. The female-thread version of
  this magnet (5679K58) carries an **11.28 mm boss** that would stand the magnet off the plate by
  that much, which is a far worse problem than a nut in a gap. The male stud is now load-bearing
  to the design; see `fastener_matrix.svg` for the 39 nut/washer permutations it forces.
- **M4 spacers** between plate and display: clear the magnet screw heads and open an air channel.
- Power: 36 W (display) + up to 27 W (Pi 5) = **63 W against a 60 W bundled brick.** Flag the upgrade.
- **Magnet pull ratings are not trustworthy across vendors.** AMF rates the O43 x 6 rubber pot at
  9 kg (19.8 lbf); totalElement rates a 43 mm rubber pot at 33.5 lbf. Design against the
  conservative figure: SF 2.5x rather than 4.2x. Both pass.

---

## 6. Deliverables
| File | Purpose |
|---|---|
| `generate_bracket.py` | parametric flat-pattern generator (ezdxf). Formed dimensions in, flat derived by subtracting bend deduction. Validates, then writes; **exits non-zero and writes nothing on failure** |
| `bracket_flat.dxf` | the upload file. mm (`$INSUNITS = 4`), layer 0 only, every contour closed |
| `bracket_preview.svg` | annotated visual check — bend line, magnet footprints, key dims. **Reference only, never upload** |
| `bracket_params.json` | machine-readable expected geometry, consumed by the audit |
| `audit_dxf.py` | acceptance test: single layer, zero open contours, correct units, expected extents, expected hole diameters. Run after every generation |
| `SENDCUTSEND-ORDER.md` | order config, bend setup, countersink spec, hole schedule, compliance table, sourced BOM, assembly sequence, fridge measurement checklist |
| `build_variants.sh` | builds and audits both arm-reach variants into `variants/`, with a comparison table |
| `render3d.py` | tiny painter's-algorithm 3D projector — perspective, backface culling, Lambert shading. No renderer is installed on toad; this is NOT a photograph and must not be captioned as one |
| `approval_sheet.py` / `approval_sheet.svg` | partner-facing sheet: front elevation, side elevation, shaded 3D view, plain-language fact band. Reads the same params as the DXF, and refuses to draw a part that does not validate |
| `ergonomics_sweep.py` / `.svg` | mounting-height study: neck length vs the band comfortable for 5'1"-6'4" |
| `arm_width_sweep.py` / `.svg` | arm width study in plan view: lift demand vs hold-down in the non-magnetic fallback |
| `plate_fea.py` / `plate_fea.svg` | Kirchhoff-plate finite elements (gmsh + scikit-fem, in `.venv`) of the body plate as cut, under the touch press, pinned on magnets or strut bolts. Validates the strip model (~15 % agreement) |
| `console_build.py` | builds **three pages** from one model: `index.html` (design 3), `hook.html` (1), `clamp.html` (2); `archive.html` redirects to `hook.html`. Reads `strut/*.svg` and `strut/dxf/*_preview.svg` directly — no copies |
| `publish.sh` | rebuilds, validates, and pushes `main` plus the `gh-pages` branch that GitHub Pages serves |
| `strut/generate_parts.py` -> `strut/dxf/{A_clamp_bar,B_foot,C_plate,D_backing_strip}.dxf` | design 2's cut parts |
| `strut/generate_hybrid.py` -> `strut/dxf/H_hook_plate.{dxf,json}` + `_preview.svg` | design 3's plate: calls the ROOT generator in-process with `--strut-bolts`, rows picked by `strut/hybrid.py` from the generator's own JSON, audited by the root audit |
| `strut/clamp_sheets.py`, `strut/package.py`, `strut/bom.py`, `strut/concept_sheet.py`, `strut/hybrid_sketch.py` | design 2's and 3's sheets. Run from `strut/` with `../.venv/bin/python` |

## 7. Code style
- Timestamped logging on every operation; INFO for major steps, DEBUG for per-feature detail
  (per-corner fillet math, hole positions, validation results). Level configurable via CLI.
  Consistent format across modules. DEBUG lines carry relevant variable state.
- Self-documenting names; inline comments only where the logic is non-obvious (bulge math,
  bend-deduction derivation).
- **No drifting constants** — derive anything derivable. No dead code, no stubs.
- Type hints and dataclasses where they earn their keep. `unset TMOUT` in any shell script.

## 8. Environment
`python3 -m venv .venv && .venv/bin/pip install ezdxf gmsh scikit-fem numpy scipy meshio` — one
venv for everything (`TOOLS-INSTALLED.md`). Run root scripts with `.venv/bin/python`, `strut/`
scripts from inside `strut/` with `../.venv/bin/python`. `strut/` finds the shared modules
(`bracket_common`, `generate_bracket`, `audit_dxf`) one level up via `sys.path` in
`strut/concept_sheet.py` and `strut/generate_hybrid.py`.

---

## 9. Designs 2 and 3 — invariants (merged from the strut repo's CLAUDE.md, 2026-09-02)

### 9.-1 NOTHING IS FIXED TO THE BUILDING. EVER.
**Charles, 2026-09-01, verbatim:** *"WE ARE NOT BOLTING INTO THE FLOOR EVER!!! This mount is
designed to be removable and cause no damage to the things it's leaning against and clamping
onto."* No floor anchors, no wall anchors, no adhesive to the appliance, no fastener into anything
that is not part of this mount. Load goes to the **floor by bearing** and to the **fridge by
clamping**; foam lines every clamp face; no steel touches the panel; floor pads are EPDM (rubber
stains polyurethane). The clamp reaches under the fridge INSTEAD of an anchor; the foot turns
outboard INSTEAD of being screwed down. It was violated once, in a DRAWING (the lower clamp's
short leg drawn through the floor) — `strut/hybrid_sketch.py` now asserts no part rect spans the
floor line. **When drawing the base, check that nothing crosses the floor line.**

### 9.0 Design 2: anti-tip is a CLAMP, not the magnets
Two identical L brackets (one part, made twice, the lower flipped), foam-faced, slid along the
strut slots until engaged and locked. The top one carries NO weight (the foot does) — ~3.8 lb of
retention, reach only enough not to slip; do not size it like a hook. **Foot and lower clamp are
SEPARATE parts** — the clamp slides UP the slot to clamp, the foot must stay on the floor. The
magnets are therefore not structural in design 2 and are not fitted.
- The stud is an **ELEVATOR bolt** (McMaster 92670A781) through a square laser-cut hole — no
  welded stud (SendCutSend cannot weld). Elevator, not carriage: the 2.78 mm flat head faces the
  FRIDGE and hides in the 3 mm foam. **Nut INSIDE the channel** on the back web; bolt spans
  7.83 mm; the foot slot clears the 8.38 mm square NECK, not the 7.94 shank.
- **ONE foot per strut, outboard, tucked under the strut** (inboard foot removed 2026-08-31).
  The strut stands on the foot's horizontal leg and never touches the floor.
- Joint stack: `J1 TOP CLAMP head -> clamp leg -> washer -> washer -> web -> nut` (grip 7.84);
  `J2 LOWER CLAMP + FOOT head -> clamp leg -> foot leg -> web -> nut` (grip 7.82). The two top
  washers stand in for the absent foot leg so the strut stays parallel. ONE 3/4 in bolt does every
  joint; the feet add no fasteners of their own.
- **LOW-PROFILE channel is a requirement** (McMaster 3310T791, 13/16 in deep). Strut orientation
  is forced: flat back on the panel, slots to the room. Nested: the display box passes BETWEEN
  the struts, so strut spacing = box 134 + 2 x 6 clearance + strut 41.27 = **187.28** (Assembly
  derives it).
- **Sliding is stopped by the clear window**, not friction: the top clamp's long leg fills it.

### 9.1 Design 2: the load path is the FLOOR
display -> plate -> struts -> bent foot -> floor. The pad under the tail CAPTURES it (10–20 mm
irregular gap, measured 2026-08-29) — never a wedge or jacking screw, never preloaded: size it to
JUST TOUCH, fit by layers. **PRELOAD IS THE TRAP** (a 60 x 200 pad at 25 % strain pushes 223 lb
upward). Anti-tip is geometric: the tail can only rise by its clearance before it bears on the
cabinet underside. State the failure mode honestly: if every magnet released, design 1's screen
sags but stays hung; design 2 rotates on the captured tail.

### 9.2 Design 3: the hook plate, prepared for struts — SETTLED 2026-09-01
- **The plate is the ROOT generator's output**, not a redrawing: `generate_bracket.py
  --thickness 0.119 --strut-bolts 187.28 <rows>`. An earlier six-hole redrawing could not take
  the magnets phase 1 needs; it is gone. `strut/generate_hybrid.py` runs the generator twice
  (plain, for the feature map; then with rows) and the root audit accepts the result.
- **Two phases, one plate.** Phase 1 = the hook: arm over the top, **4 body magnets REQUIRED**
  (nothing else holds the plate bottom in; the 4 arm magnets are anti-walk only, holes cut, not
  bought). Phase 2 = if too lively: two **5 ft** struts through **two bolt rows bracketing the
  VESA** onto design 2's feet and lower clamp UNCHANGED; the **magnets come OFF** (plate then
  sits 6.02 mm off the panel vs the magnets' 11.51).
- **Why 5 ft, not 4:** 4 ft put ONE row 17.7 mm above the plate edge; the plate cantilevered
  144 mm to the VESA and the model gave 0.876 mm at the screen edge — worse than the magnets.
  Two rows (17.73 and 220.93) make it a beam: 0.118 mm strip / 0.036 mm FEA. Rows are PICKED by
  `strut/hybrid.py` from the generator's JSON (lowest and highest clear of every magnet face,
  window and hole) and the build refuses if they no longer bracket.
- **Strut bolts must clear the magnet faces** (`strut_bolt_disc`, 2 mm): at the hook's 246
  spacing the bolts sat under the lower discs (14.27 mm centre-to-centre vs 30.26 needed); 187.28
  is the first spacing that clears AND is design 2's own.
- **0.119 in, not the hook's 0.187.** Design 1 chose 0.187 for heft (its own record); checked at
  0.119 in both phases (neck SF 32x/41x, body 34x/36x; FEA agrees with the strip model to ~15 %).
  One gauge for the whole kit.
- **Money has ONE home: `prices.py`** (dated vendor observations, never derived), which builds all
  three quotes and `quotes.svg`; `strut/bom.py`, `strut/hybrid.py` and the page read it. Design 3
  phase 1 = design 1 rebased to 0.119 in and 4 magnets: **$476.52** priced (plate $177.77 —
  RE-QUOTE, taken on the six-hole file; 4 magnets $95.68; the hook hardware $203.07) + 3 unpriced
  lines; the kit **$207.48** only if needed. Design 1 $599.87, design 2 $346.24. Display + PSU
  ($387.01) are the same purchase whichever wins and are listed once, outside the quotes.
  **Budget column (sourced 2026-09-02, single observations):** nyloc nuts replace jam nut +
  Loctite + primer; Home Depot fender washers; Foam Factory 1/2 in sheet (FAILS the pad rule by
  +1.19 mm — laminate or waive consciously); Walmart VELCRO 50-pack; a $33 Superstrut 10 ft
  half-slot stick (SAME slot pattern as 3310T791) cut in half; Rubber-Cal EPDM. Design 3 phase 1
  $333.15, kit $191.22. The plate keeps its powder coat (Charles) and the O48 magnet has no
  cheaper source; those two are the floor. A 36 mm K&J male-stud magnet ($9.72) is recorded as a
  DESIGN CHANGE option, not a swap: 8 mm standoff, M6 stud, no imperial foam matches.

### 9.3 Provenance is part of the number
Every figure is MEASURED, DERIVED or ESTIMATED and says which. A guess and a vendor figure must
never wear the same font.

### 9.4 Drawing rules — learned the hard way
SVG is XML: escape `&`, `<`, `>`. Emit leaders and dimensions BEFORE text. Derive label positions.
Colour follows the BACKGROUND (the fridge renders near-black). **Render it and look at it** —
layout cannot be reasoned about; three consecutive fix passes each repaired defects and introduced
new ones. **Every image opened for Charles carries a question or an explicit "no action needed".**

---

## 10. Design 4 — the hook in stock aluminium (2026-09-02)
`angle/angle.py` is the model, validator and generator; `angle/angle_sheets.py` draws the elevation
sheet and the 1:1 drill drawing; `angle/dxf/` holds three audited drill templates and `D4_params.json`.
- **Same load path as design 1.** A 2 x 2 x 3/16 in 6061 angle CLIP bears on the top corner and
  carries all the weight; two 2 x 1/4 in BARS (24 in) hang from it 250 mm apart; four K&J MM-C-36
  magnets (O36 x 8 mm, M6 stud, 90 lb) on the bars hold it flat; a 5 x 3/16 in bar across the bars
  carries VESA 100. Bare 6061, no coat. Everything hand-drilled from the templates.
- **The plate is 5 in tall because of the Pi fan** (~R82 on the box's vertical axis): 8 in would
  blank it. 5 in clears by 3.5 mm against a ±5 mm SCALED figure — measure the box before cutting.
- **3/16 in for the clip and the plate, not 1/4.** The 2T hole-to-edge rule fails at 1/4 in for the
  VESA holes (13.5 mm from the bar edge) and for the clip bolts inside a 2 in leg. The validator
  caught both; the fix was the gauge, not the rule.
- **The bars run the full leg and butt the clip's top leg**, so the two 1/4-20 bolts per bar sit 17
  and 37 mm from the top with 2T of edge in both parts.
- **The clip lives inside the hinge-cover window** (400.05 on the later reading, 20 mm margin), which
  puts the screen ~77 mm rearward of the case centre. The cover lifts off; the model reports the
  bias rather than hiding it.
- **Standoff 8 mm = 5/16 in foam** (7.94, in the pad band). Not the O48's 7/16 in. Not yet sourced.
- Numbers (validated): hangs ~14 lb at ~0.6 psi; magnet SF ~19x touch / ~49x peel / 3.2x on an
  assumed 20 lb grab; bar SF ~57x; screen edge ~0.03 mm. No strut option — the fallback is design 2.
- Money: `prices.py` design 4, ~$130 priced, the bars ESTIMATES, the angle and magnets sourced.
