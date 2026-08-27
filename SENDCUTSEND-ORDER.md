# SendCutSend Order Package — Fridge-Side Display Mount

**A36/1008 mild steel, 0.119" (3.02 mm), portrait, painted matte black.**
Three variants sharing one body, one bend position and one hole pattern. Figures read from
`variants/bracket_params_*.json`; prices are live quotes from 2026-08-25. Regenerate with
`./build_variants.sh` and re-read this document after any change.

Fridge: **Samsung RS23A500ASR**, counter-depth side-by-side. Display: Waveshare 23.8" or 27" FHD
monitor — the bracket is geometrically identical for either.

## 0. Pick one of three

| | **A** `reach130` | **B** `reach180` | **C** `reach180_neck212` |
|---|---|---|---|
| Arm reach across the fridge top | 130 mm | **180 mm** | **180 mm** |
| Neck (drop) | 262 mm | 262 mm | **212 mm** |
| Flat pattern | 310 x **687.0** | 310 x **737.0** | 310 x **687.0** |
| Screen centre above floor | **1331 mm** | **1331 mm** | **1381 mm** |
| Part mass | **3.45 kg** | 3.68 kg | **3.45 kg** |
| Cut price, qty 1 | **~$87** | ~$92 | **~$87** |

Everything else is identical: body 310 x 300, neck/arm width 190, four corner magnets at
250 x 240 spacing, two arm retention magnets, four vent windows on an 87.5 mm radius, O90 centre
vent, VESA 100 plus MIS-E 200x100 and MIS-F 200x200, five pairs of strap slots, and one
90 deg bend 559.5 mm from the body end.

**How to choose.** The reach difference is about $5, so cost is not the deciding factor:

1. **Measure the fridge's top corner radius.** The 1/4 in pad covers a measured **R_f up to 19 mm**
   in steel (the steel bend radius is tighter than aluminium's, which makes the mismatch worse).
   Above that, step the pad up.
2. Otherwise pick on screen height. **A and B put the screen centre at 1331 mm**, mid-band for
   5'1"-6'4". **C puts it at 1381 mm**, 2 in higher. B buys 50 mm more foot on the fridge top.
3. **Unsure? Take A.** Cheapest, lightest, shortest arm.

## 0b. Why steel, and why 0.119"

Decided 2026-08-25 after quoting the alternatives on the identical part:

| | mass | stiffness | screen move | neck SF | non-mag margin | bare | + powder |
|---|---|---|---|---|---|---|---|
| 5052 alu .187" | 1.86 kg | 100% | 0.14 mm | 66x | 2.58x | $129.46 | $198.72 |
| **mild steel .119"** | **3.47 kg** | 73% | 0.19 mm | 34x | **2.99x** | **$86.75** | $156.01 |
| mild steel .135" | 3.94 kg | 107% | 0.13 mm | 42x | 3.12x | $130.49 | $199.75 |

The part is being **coated either way** — SendCutSend powder or matte black rattle can — so bare
corrosion resistance is not a differentiator and steel's price advantage is real: **about $43
cheaper** on either route.

**Mass is a benefit here, not a cost.** The hook carries all vertical load, so weight is
structurally free, and it buys margin in the fallback where the side panel turns out not to be
magnetic: hold-down over lift demand goes 2.58x -> 2.99x purely from the extra weight.

Steel is not a drop-in swap — its published bend radius is **0.063" (1.60 mm)** against aluminium's
0.250", so the bend deduction, the flat length and the corner-radius budget all change. Everything
below is regenerated for steel.

## 1. Order configuration

| Field | Value |
|---|---|
| File to upload | the ONE variant you chose in §0 — `bracket_flat_reach130.dxf`, `..._reach180.dxf` or `..._reach180_neck260.dxf`. **Never** a preview SVG |
| Material | **A36/1008 mild steel** (cold rolled, CRS — smooth and paint-friendly) |
| Thickness | **0.119" (3.02 mm)** |
| Quantity | 1 (a second identical part is $93.47/ea — cheaper than a second variant) |
| Bending | **1 bend**, added in the browser bending tool after upload |
| Countersinking | **None** — see §3. Use low-head screws instead |
| Deburring | Yes — the plate is handled bare-handed during install |
| Finish | Either SendCutSend Gloss Black powder (+$69.26, includes free deburring) or spray it yourself matte black (~$10, saves $59). **Steel must be coated** — bare CRS surface-rusts in a kitchen. No masking needed anywhere |
| Tapping / hardware insertion | None |

Peak working stress in steel is 1200 psi against 36 ksi yield — SF 30x. Both the aluminium and
the steel options are enormously overbuilt; the choice was made on cost, mass and finish, not
on strength.

---

## 2. Bend setup

Place the bend in SendCutSend's browser bending tool after upload. **The DXF deliberately contains
no bend line.**

| Parameter | A — reach130 | B — reach180 |
|---|---|---|
| Number of bends | 1 | 1 |
| Bend angle | 90° | 90° |
| Bend centreline from the arm tip | **127.52 mm (5.021")** | **177.52 mm (6.989")** |
| Bend centreline from the body end | **559.52 mm (22.028")** | 559.52 mm (22.028") |
| Bend direction | Either UP or DOWN — same physical part, mirrored. Confirm in the 3D preview that it forms the hook; the fridge sits in the INSIDE (concave) corner of the L | same |
| Inside bend radius after bend | **1.60 mm (0.063")** — much tighter than aluminium | same |
| Bend length | **190 mm (7.48")** | same |
| Bend deduction used | **4.9657 mm (0.1955")** — SendCutSend's published figure | same |
| Formed legs from the bend apex | arm 130, neck+body 562 mm | arm 180, neck+body 562 mm |

### Bend deduction — RESOLVED, no longer an estimate

SendCutSend publishes a full bending table on their
[bending calculator page](https://sendcutsend.com/bending-calculator/). For A36/1008 mild steel at
0.119":

| K factor | Bend deduction @90° | Effective bend radius @90° | Die width | Min formed flange @90° |
|---|---|---|---|---|
| 0.38 | **0.1955"** | **0.063"** | 0.630" | 0.466" |

Those are vendor figures, not derived, and the generator now uses them directly. The K-factor
formula is retained in the code only for thicknesses they do not publish.

**Note the bend radius.** At 0.063" (1.60 mm) it is a quarter of aluminium's 0.250", which makes the
fridge corner-radius mismatch *worse*: `flat_gap = (R_f − R_b) × 0.293`, so a smaller R_b means a
bigger gap. Pad margin drops from 2.51x (aluminium) to **1.62x**, still covering a measured R_f up
to 19 mm.

### Bend lines in the DXF — RESOLVED by testing against their app, 2026-08-25

The brief said bend lines must not appear in the DXF. **That is wrong for their current flow, and
we confirmed it empirically:** uploading a geometry-only file greys out Bending entirely and their
Design Help panel reports

> **"No bend lines detected."** … *Each bend needs a correctly formatted line marking its center.*

with a format table that says **AutoCAD .dxf → Dashed line (not hidden)**.

**The DXF therefore now carries one dashed `LINE` at the bend centre**, spanning exactly the 190 mm
bend length. With it, Bending becomes selectable and the app reports "1 Bend". The line is a marker,
not a cut path — it does not appear in the extents and does not affect price.

`audit_dxf.py` verifies it specifically: count, y position, x span, and that its linetype is
`DASHED` (a solid line would be read as a cut path and would slice the part in half). Regenerate
with `--no-bend-line` only if their flow changes back.

---

## 3. Screw heads on the fridge-facing face — NOT countersunk

The two screw families point in opposite directions:

- **VESA screws** run fridge-side → plate → spacer → display. Their heads land on the
  **fridge-facing** face, inside the 6 mm the magnets hold the plate off the panel.
- **Magnet screws** (4 body + 2 arm) run display-side → plate → into the magnet's female thread.
  Their heads face the **display**, where the raised rear box holds the panel 25 mm clear. Nothing
  to be flush with — plain socket cap plus a washer, which clamps better than a countersink and
  removes no material.

On the aluminium build the VESA holes were countersunk. **On 0.119" mild steel they cannot be**,
and the reason is simpler and harder than the geometry argument that used to sit here.

**SendCutSend does not offer countersinking on A36/1008 mild steel at all.** Verified in their quote
app 2026-08-25: the Countersinking panel is greyed out on both reach variants, and its tooltip reads
*"This operation is unavailable in this material."* It is a MATERIAL restriction, not a
depth-versus-thickness one — changing the hole diameter or the plate thickness will not unlock it,
and neither will anything we do to the DXF.

This supersedes an earlier note in this document that blamed the 60% depth cap. That analysis was
real but was not the binding constraint:

| | depth needed | 60% limit | slack | plate left under the cone |
|---|---|---|---|---|
| M4 90° into a Ø4.4 hole, 3.02 mm plate | 1.80 mm | 1.81 mm | **0.01 mm** | 1.22 mm |

So the depth cap would have made it marginal anyway — 0.01 mm of slack, removing 60% of an
already-thin plate at four points — but the operation was never on the menu. Either way the answer
is the same, and it was already the decision.

**Use low-head screws instead** — they achieve the same thing, which is keeping metal away from the
fridge paint:

| screw | head height | clearance to the fridge inside the 8 mm standoff |
|---|---|---|
| M4 socket cap, DIN 912 | 4.0 mm | 4.0 mm |
| M4 low head, DIN 7984 | 2.8 mm | 5.2 mm |
| **M4 button head, ISO 7380** | **2.2 mm** | **5.8 mm** — use this |

The generator still validates the depth rule (`countersink_depth` is an ERROR past the 60% limit),
which stays useful if the build ever moves to a material where the operation IS offered — 5052
aluminium, where it was quoted successfully at $5.56 for one countersink.

**Never countersink the FRIDGE-side face of the magnet holes.** The magnet's back must sit flat on
the plate; a cone there would let it rock on its screw.

## 3b. The display is not a slab — and it drives three decisions

Read off Waveshare's dimension drawing
([23.8inch-FHD-Monitor-details-size.jpg](https://www.waveshare.com/img/devkit/LCD/27inch-FHD-Monitor/23.8inch-FHD-Monitor-details-size.jpg)),
not from the spec table:

| Feature | Value |
|---|---|
| Overall depth | **43.00 mm** — not the 18.00 mm the spec page quotes |
| Flat panel section | 18.00 mm |
| Raised rear box | **25.00 mm proud**, footprint **260 × 134 mm**, centred |
| VESA 100 × 100 | **CONFIRMED**, and it is on the raised rear box face |
| Active area / bezel | 528.04 × 297.46 mm / 13.60 mm |
| Panel corner radius | R10.00 |
| Rear box side walls | vented (grille visible in the side view) |
| Rear box **face** | carries the Pi 5's fan and GPIO header, offset **87.5 mm** from the VESA centre on one axis |

**1. The bracket lands on the rear box, not the panel.** The 25 mm box already holds the plate clear
of the panel back. That is a bigger air gap than the spacers were ever going to open.

**2. The spacers stay anyway, and for a better reason than the original one.** The stated rationale
was clearing the magnet screw heads — the box does that on its own. But the box *face* carries the
Pi's fan and GPIO, so a plate bolted flat against it would sit directly on the Pi's cooling. The
10 mm spacers keep a plenum over it. **Do not delete them to save 10 mm of depth.**

**3. The CG is much further out than an 18 mm slab implies**, so the vent windows moved.
Volume-weighting the two sections puts the display's centre of mass **29.45 mm out from the box
face**, giving **d = 50.20 mm** from the fridge — not the 29.75 mm a uniform-slab assumption gives.
Peel rises from 1.09 to **1.75 lbf** and neck bending to 426 psi (SF 66×). Still negligible, but it
was wrong before and it is right now.

The vent windows are now placed on a **radius of 87.5 mm from the VESA centre** rather than a margin
from the plate edge, and widened to 46 mm across. That radius is the fan opening's distance from the
VESA centre, so **one window lands over the Pi's fan in every 90° rotation** — landscape either way
up, portrait either way round. Margin is 8 mm all round.

> ⚠ The 87.5 mm was scaled against the dimensioned 260 mm box width on both drawings (23.8" reads
> 87.5, 27" reads 87.4), so it is better than a guess — but it is still a raster read. Treat it as
> **±5 mm**. The 8 mm of window margin
> covers that, but photograph the rear box face before ordering (checklist §9) and tell me if the
> fan is somewhere else.

## 3c. Upsizing to the 27" — the same bracket fits

Checked against the 27" dimension drawing
([27inch-FHD-Monitor-details-size.jpg](https://www.waveshare.com/img/devkit/LCD/27inch-FHD-Monitor/27inch-FHD-Monitor-details-size.jpg),
saved in `docs/reference/`). The two panels share everything the bracket touches:

| | 23.8" (SKU 34025) | 27" (SKU 33975 US) |
|---|---|---|
| Outer | 555.23 × 324.65 × **43.00** | 629.62 × 367.40 × **43.00** |
| Panel / rear box depth | 18.00 / 25.00 | **identical** |
| **Rear box footprint** | 260 × 134 | **identical** |
| **VESA** | 100 × 100 on the box | **identical** |
| **Fan offset from VESA centre** | 87.5 mm | **87.4 mm** |
| Active area / bezel | 528.04 × 297.46 / 13.60 | 598.68 × 336.46 / 15.47 |
| Panel corner radius | R10.00 | R6.00 |
| Mass | 3.94 kg | **4.92 kg** |
| Power | 36 W typical, ≥ 3 A | same |

The rear box, VESA pattern, depth profile and fan position are the same on both — they use the same
Pi bay assembly in the same housing. **Generating for either produces a geometrically identical
DXF** (verified by hashing the entity geometry: only ezdxf's GUIDs and timestamp differ). So you can
order the bracket now and upsize later without recutting.

`generate_bracket.py --display 27` restates the load case:

| Quantity | 23.8" | 27" |
|---|---|---|
| Total hanging load | 12.90 lbf | **15.06 lbf** |
| Torsion moment (5 lbf at the screen edge) | 54.6 in·lbf | **62.0 in·lbf** |
| Force per magnet | 2.78 lbf | **3.15 lbf** |
| Magnet SF, optimistic / conservative rating | 4.2× / 2.5× | **3.7× / 2.2×** |
| Peel | 1.75 lbf | 2.18 lbf |
| Neck bending | 426 psi, SF 66× | 532 psi, SF 53× |
| Body weak axis | 831 psi, SF 34× | 942 psi, SF 30× |
| Non-magnetic arm-width margin | 1.52× | **1.47×** |
| Screen band, landscape | 1168–1493 mm | 1147–1514 mm |
| Screen band, portrait | 1053–1608 mm | 1016–1646 mm |
| Plate hidden in portrait, per side | 7.3 mm | **28.7 mm** |

Everything still passes, with the two thinnest margins being the conservative magnet rating (2.2×)
and the non-magnetic arm fallback (1.47×). The 27" actually **hides the plate better** — its portrait
width is 367 mm against the 310 mm body, versus 325 mm on the 23.8".

Two things to re-check if you do upsize: the 27" is 1 kg heavier, so re-do the "press hard at the
outer edge" test in step 10 of assembly; and its portrait bottom edge sits at 1016 mm, 37 mm lower
than the 23.8", which is below the taller user's elbow.

## 4. Hole schedule

Origin at the **lower-left corner of the body** (the end furthest from the bend), X right,
Y toward the bend. **No countersinks** — see §3.

| # | Tag | X (mm) | Y (mm) | Ø | Purpose |
|---|---|---|---|---|---|
| 1 | arm_magnet | 95.0 | 647.0 | 4.5 | retention magnet, same SKU |
| 2 | arm_magnet | 215.0 | 647.0 | 4.5 | retention magnet, same SKU |
| 3 | magnet | 30.0 | 30.0 | 4.5 | M4 SHCS + washer into pot-magnet female thread |
| 4 | magnet | 30.0 | 270.0 | 4.5 | M4 SHCS + washer into pot-magnet female thread |
| 5 | magnet | 280.0 | 30.0 | 4.5 | M4 SHCS + washer into pot-magnet female thread |
| 6 | magnet | 280.0 | 270.0 | 4.5 | M4 SHCS + washer into pot-magnet female thread |
| 7 | vesa | 105.0 | 100.0 | 4.4 | M4 button head into the display's VESA 100 pattern, through spacer |
| 8 | vesa | 105.0 | 200.0 | 4.4 | M4 button head into the display's VESA 100 pattern, through spacer |
| 9 | vesa | 205.0 | 100.0 | 4.4 | M4 button head into the display's VESA 100 pattern, through spacer |
| 10 | vesa | 205.0 | 200.0 | 4.4 | M4 button head into the display's VESA 100 pattern, through spacer |
| 11 | vesa200x100 | 55.0 | 100.0 | 4.4 | MIS-E 200x100, M4 — spare pattern for a future larger display |
| 12 | vesa200x100 | 55.0 | 200.0 | 4.4 | MIS-E 200x100, M4 — spare pattern for a future larger display |
| 13 | vesa200x100 | 255.0 | 100.0 | 4.4 | MIS-E 200x100, M4 — spare pattern for a future larger display |
| 14 | vesa200x100 | 255.0 | 200.0 | 4.4 | MIS-E 200x100, M4 — spare pattern for a future larger display |
| 15 | vesa200x200 | 55.0 | 50.0 | 6.5 | MIS-F 200x200, M6 — spare pattern for a future larger display |
| 16 | vesa200x200 | 55.0 | 250.0 | 6.5 | MIS-F 200x200, M6 — spare pattern for a future larger display |
| 17 | vesa200x200 | 255.0 | 50.0 | 6.5 | MIS-F 200x200, M6 — spare pattern for a future larger display |
| 18 | vesa200x200 | 255.0 | 250.0 | 6.5 | MIS-F 200x200, M6 — spare pattern for a future larger display |
| 19 | vent | 155.0 | 150.0 | 90.0 | centre lightening / airflow opening |

Vent windows (rounded rectangles, R5 corners), same origin:

| Tag | Centre X | Centre Y | W × H | Covers the rear-box opening in |
|---|---|---|---|---|
| vent_top | 155.0 | 237.5 | 80 × 46 | portrait, one way round |
| vent_bottom | 155.0 | 62.5 | 80 × 46 | portrait, the other |
| vent_left | 67.5 | 150.0 | 46 × 80 | landscape, one way up |
| vent_right | 242.5 | 150.0 | 46 × 80 | landscape, the other |

**Diameter groups**, which is how SendCutSend's app buckets hole operations:

- **4.400 mm — 8 holes** — VESA 100 + MIS-E 200x100 (M4)
- **4.500 mm — 6 holes** — magnets, 4 body + 2 arm (M4)
- **6.500 mm — 4 holes** — MIS-F 200x200 (M6)
- **90.000 mm — 1 hole** — centre vent

All four windows sit on a radius of 87.5 mm from the VESA centre so one
covers the display's rear-box opening in every 90° rotation. Open area 22.7% of the body.
Outer corners R8; the two reflex corners at the neck/body shoulders R6.

## 4b. Cable routing

Five pairs of **strap slots** run up the centreline, positioned as **offsets from the bend line** so
they track any change to neck length or arm reach:

| offset from bend | y in the flat | region | nearest edge |
|---|---|---|---|
| −220 mm | 339.5 | neck | 30.5 mm |
| −130 mm | 429.5 | neck | 85.0 mm |
| −40 mm | 519.5 | neck | 31.0 mm |
| +45 mm | 604.5 | arm | 36.0 mm |
| +105 mm | 664.5 | arm | 13.5 mm |

Each slot is **4.0 mm x 18.0 mm** with R1.40 ends, and the two slots in a pair are 16.0 mm apart
centre to centre — so the **bridge between them is 12.0 mm**. A hook-and-loop strap drops through
one slot, passes behind the bridge and comes back up the other, then wraps the cable.

**Sized for VELCRO Brand ONE-WRAP, 8 in x 1/2 in** (12.7 mm nominal). The 18.0 mm slot length is
12.7 + 2 x 2.65 mm of clearance, which means it also passes a **5/8 in (15.9 mm)** strap with
2.1 mm to spare — a different strap out of the drawer does not mean a different bracket. The 4.0 mm
slot width takes ONE-WRAP's ~1.9 mm laminate with enough room to thread by fingertip.
`--strap-width` re-derives the slot if you standardise on something else.

Two things moved when the round holes became slots, both caught by the validator rather than by
eye:

- the outermost pair went from **+115 to +105 mm**. An 18 mm slot at +115 finishes 3.5 mm from the
  arm tip, inside the 2x-thickness (6.05 mm) edge rule; +105 restores 13.5 mm.
- slots are `WindowRect`s, not holes, so they are **LWPOLYLINEs in the DXF, not CIRCLEs**. The part
  now carries 4 vent windows + 10 strap slots = 14 closed interior contours. The audit reads the
  expected count from `bracket_params.json`, so this needs no manual bookkeeping.

The run is: out of the display's rear box, up behind the display (hidden), up the exposed neck,
over the bend, and onto the fridge top, where the last two pairs hold it down. From there the lead
crosses the top to the rear edge and drops down the back, out of sight.

Note the geometry: the arm points **inboard across the top**, while the back of the fridge is 90°
from that. So the tie-downs get the cable safely onto the top surface; the last leg across to the
rear edge is loose cable, but it is invisible up there.

The −40 pair's slot ends 31 mm from the bend centreline, comfortably outside the 8.00 mm keep-out (½ the
0.630" die). Omit them all with `--no-cable-ties`.

## 5. Constraint compliance

Verified 2026-08-25 against sendcutsend.com. `generate_bracket.py` refuses to write files
and exits non-zero if any of these fail.

| Constraint | Requirement | Actual | Status |
|---|---|---|---|
| Material offered at thickness | A36/1008 in 0.119" CRS | yes | PASS |
| Flat within instant-pricing sheet | ≤ 762 × 1118 mm | 310 × 687.0 mm | PASS |
| Min formed flange, arm side | ≥ 11.84 mm (0.466") | 127.5 mm | PASS |
| Min formed flange, neck side | ≥ 11.84 mm | 259.5 mm | PASS |
| Feature clearance from bend line | ≥ 8.00 mm (½ of the 0.630" die) | 83.0 mm (arm magnet holes) | PASS |
| Min hole diameter | ≥ 1.51 mm (~50% of thickness) | 4.40 mm smallest | PASS |
| Hole to plate edge | ≥ 6.05 mm (2 × thickness) | 27.8 mm | PASS |
| Countersinking | not offered on A36/1008 mild steel (their app, verified) | n/a — ISO 7380 button heads | PASS |
| Magnet disc within its region | overhang ≤ 0 | 8.50 mm inboard | PASS |
| Magnet spacing (load-bearing) | ≥ 240 mm | 250 mm horizontal, 240 vertical | PASS |
| Arm pad covers corner gap + crown | ≥ 1.2× the budget | 1.62× | PASS |
| Bottom pad vs magnet standoff | 0 to +1.0 mm proud | +0.35 mm | PASS |
| Rear-box opening covered | a window covers it in all 4 rotations | 8.00 mm margin each | PASS |
| Body open area (vents) | ≥ 15% | 22.7% | PASS |
| Corner fillets fit their edges | tangent ≤ ½ each adjacent edge | all fit | PASS |
| DXF: single layer / units / contours | layer 0, $INSUNITS 4, zero open contours | 5 LWPOLYLINE + 19 CIRCLE + 1 dashed bend LINE | PASS |

`audit_dxf.py` runs 15 acceptance checks per variant; all three currently report 0 failures.

### Load-path numbers — steel .119", portrait, 23.8 in display

| Quantity | Value | Note |
|---|---|---|
| Display weight | 8.69 lbf (3.94 kg) | |
| Bracket weight | 7.61 lbf (3.45 kg) | steel, and the mass is a benefit here |
| Total hanging load | **16.29 lbf** | carried entirely by bearing at the fridge top corner |
| Touch press assumed | 5 lbf at 162 mm | portrait halves this arm vs landscape |
| Force per magnet | **1.62 lbf** | over the 250 mm magnet span |
| Magnet safety factor | **7.2×** optimistic, **4.3×** on the conservative 19.8 lbf rating | |
| Peel | 1.77 lbf | d = 48.5 mm, H = 270 mm |
| Neck bending | 1066 psi, **SF 34×** | vs 36 ksi yield |
| Body weak axis | 1200 psi, **SF 30×** | conservative strip width. No ribs required |
| Screen centre | **1331 mm** above the floor | portrait: screen spans 1053–1609 mm |
| Arm pad budget | 3.92 mm | covers a measured R_f up to 19 mm |
| Cut length | 3573 mm | |

## 6. Bill of materials — with sources

Prices not quoted; they move. Links are to specific products that match the spec, not endorsements
— check dimensions on the listing before ordering.

### Bracket
| Item | Spec | Qty | Source |
|---|---|---|---|
| Bracket plate | **A36/1008 mild steel 0.119" CRS**, per DXF, 1 bend, no countersinks | 1 | [SendCutSend](https://sendcutsend.com/materials/mild-steel/) |

### Magnets — **one part number for all six**
| Item | Spec | Qty | Source |
|---|---|---|---|
| **Bare Ni-plated neodymium pot magnet** | **Ø36 × 8 mm, M6 FEMALE thread, N38, 71.7 lbf rated** — K&J MM-H-36 | **6** (4 body + 2 arm) | [K&J MM-H-36](https://www.kjmagnetics.com/mm-h-36-metric-internal-thread-mounting-magnet) | [CMS Magnetics, Ø43 × 6 mm M4 female, Amazon](https://www.amazon.com/CMS-MAGNETICS-Durability-Combustible-Environment/dp/B0DD1W4M86) · [AMF Magnets US](https://amfmagnets.com/products/female-thread-neodymium-pot-diameter-43mm-x-6mm-with-rubber-case) · [totalElement](https://totalelement.com/collections/neodymium-threaded-pot-magnets) |

**BARE, not rubber-coated — decided 2026-08-25.** The moulded rubber jacket is ~0.76 mm thick, and
pot-magnet pull falls off steeply with gap. A bare Ø36 magnet rates **71.7 lbf** against the
rubber-coated Ø43's **19.8 lbf** — 3.6× more holding force from the *smaller* magnet. Scratch
protection comes instead from a strip of **electrical tape or thin PTFE film on the fridge** where
each magnet lands: 0.18 mm against the rubber's 0.76 mm, a quarter of the gap.

Consequence for the yank case (a 20 lbf pull at the screen bottom): margin goes **0.83× → 3.00×**
on four magnets. That was the thinnest margin in the design and is now comfortable.

Bare nickel drops μ from ~0.7 to ~0.2, which does not matter here: the hook carries every bit of
the vertical load and the magnets work in tension, not shear.

> **CORRECTED 2026-08-25 — they are not the same magnet.** I previously wrote that vendors
> "disagree badly" about one part. They do not; these are two different products:
>
> | | grade | thread | rated pull |
> |---|---|---|---|
> | AMF / CMS Ø43 × 6 | **N35** | **M4 female** | 9 kg = **19.8 lbf** |
> | totalElement Ø43 × 6.1 | **N52** | **M6 × 15 male stud** | **33.5 lbf** (7 lbf shear) |
>
> The brief's "33.5 lb vertical, 7 lb horizontal" figure came from the N52 male-stud part. The
> female-thread part this BOM specifies is the N35, and **19.8 lbf is its real rating**. Every
> margin quoted against 33.5 lbf assumed the N52.
>
> Buy 8 of whichever you choose and keep spares; you will drop one.

### Fasteners
| Item | Spec | Qty | Source |
|---|---|---|---|
| Magnet screw | **M4 × 10 mm socket head cap**, A2 stainless — 6.98 mm into the magnet's 9 mm thread | 6 | any A2 M4 SHCS assortment |
| Magnet washer | M4 flat, stainless | 6 | " |
| **VESA screw** | **M4 × 20 mm BUTTON HEAD, ISO 7380**, A2 stainless — 2.2 mm head clears the fridge by 3.8 mm | 4 | any A2 ISO 7380 button-head M4 assortment |
| M4 spacer / standoff | **M4 female-female, 10 mm**, brass or stainless — **required, see §3b** | 4 | [uxcell M4 × 10 brass hex standoff](https://www.amazon.com/Hexagon-Female-Brass-Standoff-Spacer/dp/B00NQ9KJC6) |
| Thread locker | Removable (blue) | 1 | on the magnet screws only; keep the display screws serviceable |

**Magnet screw length = plate thickness + 6 to 7 mm of engagement**, and must not exceed the
magnet's 9 mm thread depth or it bottoms out and jacks the magnet off the plate. In the 3.02 mm
steel plate, M4 × 10 gives 6.98 mm — ten threads. M4 × 14 would bottom out. Verify the thread depth
on the magnets you actually receive before ordering screws.

VESA screw length is **3.02 (plate) + 10 (spacer) + engagement**, plus the 2.2 mm button head
sitting proud on the fridge side. 20 mm assumes ~7 mm of thread into the rear box's inserts. **Measure the display's VESA insert depth first** —
bottoming out in a thin aluminium enclosure strips it. Buy 16, 20 and 25 mm if in doubt.

### Soft goods
| Item | Spec | Qty | Source |
|---|---|---|---|
| Arm pad | **Closed-cell** neoprene sponge, **3/8" (9.53 mm)**, adhesive-backed, ≥ 200 × 190 mm | 1 | [Qiveno closed-cell neoprene w/ adhesive](https://www.amazon.com/Closed-Neoprene-Rubber-Sheet-Adhesive/dp/B0DZ61MVBX) · [Rubber Sheet Warehouse (cut to size)](https://rubbersheetwarehouse.com/products/foam-sponge-rubber-closed-cell-neoprene-epdm-sbr-with-adhesive) |
| Bottom bearing pad | Same material and thickness, ~310 × 25 mm | 1 | same sheet |

Must be **closed-cell**: open-cell soaks up kitchen grease and takes a permanent set. Cut Ø46 mm
clearance holes in the arm pad at the two magnet positions so the magnets reach the steel.

Pads are **3/8" (9.53 mm)** over an **8 mm** magnet — 1.53 mm proud, 16% compression, which
closed-cell sponge absorbs easily. A pad *thinner* than the magnet would hold the plate off, which
is what the "pad = standoff" invariant really protects against; being proud is the safe direction.

| Fridge protection | Electrical tape or thin PTFE/UHMW film, cut into six discs slightly larger than Ø36 | 1 roll | Stuck to the FRIDGE where each magnet lands. This is what replaces the rubber coating |

### Finish

| Item | Spec | Qty | Notes |
|---|---|---|---|
| Matte black paint | Self-etching primer for steel + matte black top coat, rattle can | 1 | **Steel must be coated** — bare CRS surface-rusts in a kitchen. Degrease thoroughly first; CRS arrives lightly oiled. No masking needed: coating never lands between a magnet face and the fridge |

Alternative: SendCutSend Gloss Black powder, +$69.26, includes free deburring. Spraying it yourself
saves about $59 and gives a matte finish; their powder is tougher and more even.

### Electrical
| Item | Spec | Qty | Source |
|---|---|---|---|
| PSU | **12 V, ≥ 8 A (96 W), 5.5 × 2.5 mm barrel, UL listed** | 1 | [LEDwholesalers 12V 8A 96W UL](https://www.amazon.com/LEDwholesalers-Adapter-5-5x2-5mm-UL-Listed-3224-12VR2/dp/B01MZGNJA5) |
| Raspberry Pi 5 | 4 or 8 GB | 1 | mounts in the display's internal bay — **unconfirmed, verify the bay exists** |
| Pi 5 active cooler | Official | 1 | needed precisely because the plate sits behind the display |

**The bundled 60 W brick is a flag, not a failure.** The display is 36 W typical and needs ≥ 3 A just
to boot; a Pi 5 can pull 27 W under load. 63 W against 60 W leaves no headroom, and brownouts on a
Pi 5 present as random reboots. **Confirm the bundled brick's barrel size and polarity before buying
a replacement** — the Waveshare page states neither.

---

## 7. Assembly sequence

1. **Verify the part.** Run the audit on the file you actually uploaded. On arrival, check the bend
   with a square and measure both legs from the bend apex: arm 130 (A) or 180 (B), neck+body 562 mm.
   Deburr anything the service missed.
2. **Dry-fit the bare bracket, no display, no pads.** Look for three things: the arm rocking
   fore-aft on the crowned top; contact with the hinge cover caps at the front corners; and the rear
   cable/waterline step-down. Slide it along the top until the arm sits **mid-depth**, clear of all
   three. Mark the position with tape.
3. **Fit the arm pad.** Clean with IPA, apply the 1/4" closed-cell sponge across the full arm width
   and around the bend so it covers the inside radius. Cut the two Ø46 clearance holes for the arm
   magnets. Re-fit and confirm the rocking is gone.
4. **Fit the bottom bearing pad** along the lower edge of the body.
5. **Fit the magnets** — 4 body corners, 2 on the arm. M4 × 8 + washer, blue threadlocker, snug.
   Do not over-torque into a rubber-coated body. Check all magnet faces in each plane are coplanar;
   one proud magnet skews the whole plate.
6. **Fit the spacers.** M4 × 10 mm standoffs at the four VESA holes, display side.
7. **Mount the display to the bracket on a bench, face down on a towel.** M4 × 20 flat heads from
   the fridge-facing side, through the plate and spacers into the VESA inserts. Confirm the button
   heads stand no more than ~2.2 mm proud on the fridge side. Do not hang first and screw later.
8. **Hang the assembly.** Two people. Lower the arm over the fridge top at the taped position, let
   the hook take the weight, *then* let the body swing in and the magnets land. **Never lead with
   the magnets** — a Ø43 neodymium pot magnet landing on painted steel chips paint and pinches
   fingers.
9. **Route power** down the rear step-down channel. Leave a service loop so the display can be
   lifted off without unplugging.
10. **Verify under load.** Press hard at the outer screen edge — the design case is 5 lbf at 278 mm.
    Nothing should shift or click. Nudge the display sideways and upward to confirm the arm magnets
    are doing their retention job. Then lift it straight up: it must come off the hook cleanly, which
    confirms the magnets never took vertical load in the first place.

---

## 8. Regeneration

```sh
./build_variants.sh                    # both variants, audited, with a comparison table
```

Or one variant with measured inputs:

```sh
.venv/bin/python generate_bracket.py --name reach130 --arm-length 130 --neck-width 190 \
    --out-dir variants \
    --fridge-height <measured> --screen-centre-height 1331 \
    --bend-deduction <from SendCutSend's calculator> \
    --fridge-corner-radius <measured> --crown-rise <measured> \
    --log-level DEBUG
```

Giving `--screen-centre-height` **derives** the neck length from the fridge height and ignores
`--neck-length`. Portrait: add `--orientation portrait`. The cut geometry does not change — the body
is square enough that only the load case moves — and the magnet safety factor rises from 4.2× to
about 7.2× because the torsion arm drops from 278 mm to 162 mm.

---

## 9. Pre-order validation — work top to bottom

### Tier 1 — blocks the order, changes the cut file

- [ ] **Fridge overall height.** Design assumes Samsung's published 68 5/8" (1743 mm) to top of CASE. The neck length is
      derived from it, so this sets where the screen lands. 40 mm of error = 40 mm of screen height.
      Re-run with `--fridge-height <measured> --screen-centre-height 1331`.
- [x] **Bend deduction — RESOLVED.** SendCutSend publishes 0.1955" for A36/1008 at 0.119"/90°,
      and the generator uses it directly. No longer an estimate, no longer blocking.
- [ ] **Arm clear window on the fridge top, front to back.** The arm is **190 mm** wide and must land
      between the hinge cover caps and the rear cable/waterline step-down. Assumed 621 mm clear of an
      851 mm deep top. If it is under 190 mm, the arm width has to change and that is a recut.

### Tier 2 — decides which variant

- [ ] **Top corner radius `R_f`.** Straightedge flat on the side, another flat on the top; they meet
      at the theoretical sharp corner. Measure from that intersection along the top to where the flat
      becomes curve — for a 90° corner that distance *is* the radius. Cross-check down the side.
      *Quick screen:* a US quarter is Ø24.26 mm (R = 12.13). If it rocks and won't seat, R_f < 12.
      **R_f > 17 mm forces variant A.**
- [ ] **Crown across the top.** Straightedge front-to-back and side-to-side at the intended arm
      position; measure the gap at the ends. Assumed 3 mm. **Over ~5 mm prefers variant A.**

### Tier 3 — can still move the vents, but only if badly wrong

- [ ] **Rear box fan/GPIO position.** Photograph the display's raised rear box and measure the fan
      centre from the VESA centre. Design assumes **87.5 mm ± 5** (it reads the same on both the
      23.8" and 27" drawings). The vent windows sit on that radius so one covers the fan in every
      rotation, with 8 mm of margin. If the fan is elsewhere, send me the measurement.
- [ ] **Rear box dimensions.** Confirm 260 × 134 × 25 mm on the physical unit.

### Tier 4 — BOM and assembly, does not block the cut

- [ ] **VESA insert thread depth** — sets the M4 flat-head screw length. 20 mm assumes ~5 mm
      engagement. Bottoming out in a thin enclosure strips it.
- [ ] **Is the side panel magnetic?** A test magnet in several places, especially near the front edge.
      If not (304 stainless), the hook still carries everything — the 190 mm arm width was chosen so
      the non-magnetic fallback holds — but tell me and re-check assembly step 10.
- [ ] **Side panel flatness** over the 300 mm the body covers. A bowed panel means the magnets do not
      all touch.
- [ ] **Bundled PSU label**: volts, amps, barrel diameter, polarity. Budget is 63 W against a 60 W
      brick.
- [ ] **Pi 5 bay** exists and its ports stay reachable with the plate on.
- [ ] **Wall clearance behind the fridge** — the display adds ~64 mm of depth on the side.

### Tier 5 — at the order screen

- [ ] Upload the chosen variant. Confirm it parses at the expected size and that the **cyan dashed
      bend line** appears across the neck.
- [ ] Material **A36/1008 mild steel**, thickness **.119"**, quantity as decided.
- [ ] **Bending:** 1 bend, **90°**. Check the 3D preview forms the hook — do not trust the up/down
      label.
- [ ] **No countersinking.** All holes plain — see §3. Low-head screws do the job instead.
- [ ] Deburring on. Powder coat only if you have read the magnet-pad note.
- [ ] Confirm **max bend length for 0.119" steel** — their FAQ page 404s. Ours is **7.48"**, far
      inside their published 16–44" range, and their app offered Bending on this material without
      complaint.
- [ ] Minimum formed flange for 0.119" steel is their published 0.466" (11.84 mm). Ours are
      127.5/177.5 mm and 259.5 mm — nowhere near binding.
- [ ] `audit_dxf.py` run against the exact file uploaded — 15 checks, 0 failures.
- [ ] Decide finish: SendCutSend powder (+$69.26) or spray it yourself (~$10).


---

## Magnet, settled 2026-08-26 — McMaster 5679K58 (SUPERSEDES 5679K57 below)

| | |
|---|---|
| part | **McMaster-Carr 5679K57** |
| construction | encased neodymium, **zinc-plated STEEL case**, threaded hole |
| size | Ø35.99 mm (1.417") x 7.94 mm (5/16") |
| grade | **N42** |
| rated pull | **100 lbf** — their basis: "direct contact with rust-free, unpainted iron" |
| derated (thin painted sheet, 35%) | **35.0 lbf** |
| thread | 1/4"-20, **9.65 mm deep, BLIND** |
| price | $9.30 each, delivers next day |

**Fastener: 1/4"-20 x 1/2" socket head cap screw + flat washer, medium threadlocker.**
Screw enters from the DISPLAY side, through a **Ø7.0 mm** clearance hole in the plate, into the
magnet. It clamps the plate against the magnet's back face — steel on steel, nothing in the
magnetic circuit.

**Do not fit a longer screw.** The tapped hole is 9.65 mm and blind; plate + washer is 4.62 mm, so
anything over **14.27 mm bottoms out and never clamps**. A 5/8" screw looks right for a 3 mm plate
and is wrong.

Head clearance on the display side is 25 mm (the magnets sit outside the rear box footprint)
against 7.95 mm needed — no countersinking, any head style.

**Why this part:** neodymium is the only material worth considering (ceramic is ~10% of its pull,
SmCo ~55%, and their heat/corrosion advantages are worthless in a kitchen). Case material matters
more than grade — a steel case returns the flux and beats an aluminium one 3.7x at the same size.
Threaded hole rather than stud: McMaster's stud versions have **identical pull** at every size and
cost $0.84-$4.65 more each.


### Final magnet spec — 6 x McMaster 5679K58

| | |
|---|---|
| part | **McMaster-Carr 5679K58**, x6 (4 on the plate, 2 on the arm) |
| construction | encased neodymium, **zinc-plated STEEL case**, threaded hole |
| size | **O42.11 x 9.13 mm** (1 21/32" x 23/64") |
| grade | N42 · rated **150 lbf** · derated 52.5 lbf |
| thread | **5/16"-18, 11.18 mm deep, BLIND** |
| plate hole | **O8.5 mm** |
| fastener | **5/16"-18 x 5/8" SHCS + flat washer + Loctite 243** |
| price | $11.60 ea, **$70 the set** |

**Do not fit a 3/4" screw** — max is 16.20 mm; 3/4" (19.05) bottoms in the blind hole and never
clamps. 5/8" gives 1.37xD of engagement.

Edge margin is **8 mm** (not the 12 mm used elsewhere): that is what the O42.11 disc needs to keep
both spacings over the 240 mm floor. 8 mm is still 12.7x the 0.63 mm worst-case radial tolerance
stack. Magnet 9.13 mm vs 9.52 mm pad — the pad is still the thicker of the two, as required.

**O42.11 is the largest disc this plate can take.** Inset <= (300 - 240)/2 = 30 mm comes off the
SHORT plate dimension and the spacing floor, and applies to four magnets exactly as much as to
eight — empty corners do not buy diameter. 5679K59 (O48.4) would need a negative edge margin and is
also thicker than the pad.


---

## FINAL MAGNET SPEC — 6 x McMaster-Carr 3506K66

| | |
|---|---|
| part | **McMaster-Carr 3506K66** x6 — 4 on the plate corners, 2 on the arm |
| construction | encased neodymium, **zinc-plated STEEL case**, **male threaded stud** |
| size | **O42.07 x 9.13 mm** (1 21/32" x 23/64") |
| grade / pull | N42 · **150 lbf rated** · 52.5 lbf derated |
| stud | **male 5/16"-18 x 1/2"** |
| plate hole | **O8.5 mm** |
| fastener | flat washer + **5/16"-18 nut** + Loctite 243, on the display side |
| price | $16.25 ea · **$97.50 the set** · next-day |

**Why the STUD and not the threaded-hole version.** The threaded-hole twin (5679K58) is the same
magnet at the same price, but it carries an **11.28 mm threaded boss** on its back. On a
3.02 mm plate that boss would stand the magnet off by its full length, pushing the display
from 55 to about 66 mm off the fridge. A male stud passes
straight through the plate and takes a nut in the 25 mm of air behind. Studs are NOT stronger —
McMaster's stud and hole versions have identical pull at every size — but for thin plate the stud
is the only one that physically works.

**Geometry as built**
- inset 29.03 mm = disc radius + an **8 mm edge margin** (12.7x the 0.63 mm tolerance stack)
- spacing X 252 / Y 242 mm, both over the 240 mm floor
- pad 9.52 mm (3/8 in), DERIVED as the first sponge stock size clearing the magnet
- standoff 55.15 mm · torsion margin 33x
- pull-off 139 lbf at the screen bottom

**O42.07 is the largest disc this plate takes.** inset <= (300 - 240)/2 = 30 mm comes off the SHORT
plate dimension and the spacing floor, independent of magnet count.


---

## FINAL — 6 x McMaster 3506K67 on a SQUARE 310 x 310 plate

| | |
|---|---|
| part | **McMaster-Carr 3506K67** x6 — 4 on the plate corners, 2 on the arm |
| size | **O48.02 x 11.51 mm** (1 57/64" x 29/64") |
| grade / pull | N42 · **175 lbf rated** · 61.2 derated |
| stud | male **5/16"-18 x 1/2"** · plate hole **O8.5** |
| fastener | washer + 5/16"-18 nut + Loctite 243, display side |
| price | $23.92 ea · **$143.52 the set** |

**THE PLATE IS NOW SQUARE, 310 x 310.** This is the change that made the bigger magnet possible.
The width had been grown 300 -> 310 to clear the 240 mm torsion floor; the height was left at the
brief's 300 and never revisited, which made Y spacing permanently 10 mm tighter than X. Every
larger magnet had been failing on Y alone — 3506K67 missed by 0.11 mm at the minimum edge margin,
0.05% of the floor. Squaring the plate removes the asymmetry rather than shaving the margin:
spacing is now **246 / 246 mm**, both clear, at a full **8 mm** edge margin.

- blank 310 x 692.0 mm (was 310 x 687.0) — about 0.7% more sheet
- neck shortened 262 -> 257 mm so the screen centre stays at 1331 mm
- pad steps to **1/2 in** (derived — the magnet is 11.51 mm)
- standoff 57.53 mm · torsion **37x** · pull-off **162 lbf**
- display still hides the plate: 7.3 mm each side, 122.6 mm top and bottom
