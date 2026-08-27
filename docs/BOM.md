# Bill of Materials — Fridge-Side Display Mount

> **CORRECTION 2026-08-27.** This BOM was drafted assuming the VESA holes are countersunk 90°. They are NOT — countersinking is disabled in the build because SendCutSend does not offer it on mild steel. Countersinking is NOT needed: the magnets hold the plate 11.5 mm off the panel, so a proud screw head on the fridge-facing side has clearance. Any standard M4 head works — socket cap, pan or low head. Confirmed by the owner. Everything else stands.


**Prices are observations, not derived values.** Every price below was read from the linked
vendor page on **2026-08-27** (SendCutSend: live quote in the owner's own session, same date).
Vendor prices and stock change without notice — **re-check every line before ordering.**
Anything marked NOT VERIFIED could not be confirmed against a live product page and must not
be ordered as written.

Quantities are taken from the generated design (`bracket_params.json` + hole schedule from
`generate_bracket.py`): **8 magnet positions fitted** (4 body `magnet` + 4 arm `arm_magnet`),
**7 spare positions** cut but unfitted (4 `spare_magnet` + 3 `spare_arm_magnet`), 4 VESA 100
holes fitted (200×200 M6 provision cut but unused), pad thickness target 11.5 mm biased under.

## Main BOM

| # | Part number | Description | Qty | Unit price | Ext. price | Source | Status |
|---|---|---|---|---|---|---|---|
| 1 | SendCutSend custom (`bracket_flat.dxf`) | Bracket: A36/1008 mild steel 0.119 in, 310 × 742 mm flat, 1 bend, 4 countersinks (90° M4, concave face), matte black powder coat | 1 | $185.54 | $185.54 | [sendcutsend.com](https://sendcutsend.com) — live quote 2026-08-27 | VERIFIED (live quote, owner's session) |
| 2 | Waveshare 23.8inch FHD Monitor (SKU 34025) | 23.8 in 1920×1080 capacitive touch monitor, optically bonded, VESA 100, incl. 12 V 5 A PSU + screws pack | 1 | $349.99 | $349.99 | [waveshare.com](https://www.waveshare.com/27inch-fhd-monitor.htm) (select "23.8inch") | VERIFIED |
| 3 | [3506K67](https://www.mcmaster.com/3506K67/) | Encased neodymium magnet, N42, zinc-plated steel case, 1 57/64" OD × 29/64" (11.51 mm) thick, **5/16"-18 × 1/2" male stud**, 175 lbf max pull | 8 | $23.92 | $191.36 | McMaster-Carr | VERIFIED ($20.62 ea at 50+; delivers next day) |
| 4 | [90101A122](https://www.mcmaster.com/90101A122/) | **THIN-PROFILE nylon-insert locknut**, black-oxide 18-8 stainless, **5/16"-18 UNC** (imperial — NOT M8). 1/2" across flats × **1/4" (6.35 mm)** high. This is a real locking feature that fits: +1.60 mm of stud to spare | 1 pack of 50 | $18.72 | $18.72 | McMaster-Carr | **VERIFIED 2026-08-27.** Plain 18-8 equivalent is [90101A237](https://www.mcmaster.com/90101A237/), $10.34/50 |
| 5 | ~~[96765A145](https://www.mcmaster.com/96765A145/)~~ | ~~Washer, general-purpose flat, black-oxide 18-8, 5/16", Ø0.750"/Ø0.344", 0.040"–0.060" thick~~ — **DO NOT ORDER for the magnets.** With the thin locknut it leaves only +0.08 mm, inside the tolerance stack | 0 | — | — | McMaster-Carr | **OUT 2026-08-27** — locknut or washer, not both, and the washer is not needed. See below |
| 6 | [91239A180](https://www.mcmaster.com/91239A180/) | VESA screws: M4 × 0.7, **LOW-HEAD** socket cap, 18-8 stainless — pack of 25. NOT flat head: the plate's VESA holes are NOT countersunk (`countersink_vesa = False`; SendCutSend cannot countersink mild steel), so a 90° flat head would sit proud on a plain hole | 1 pack | NOT VERIFIED | — | McMaster-Carr | **NOT VERIFIED — corrected after the BOM was drafted on a wrong countersink premise. Confirm part number and length before ordering.** |
| 7 | [93375K678](https://www.mcmaster.com/93375K678/) | Neoprene foam strip, closed-cell, **7/16" (11.11 mm) thick**, 2" wide × 10 ft, adhesive-backed, 15 lb/ft³, 12 psi to compress 25% (Soft) | 1 | $141.83 | $141.83 | McMaster-Carr | VERIFIED (price from listing table; see foam note) |
| 8 | [189755](https://www.hookandloop.com/brands/velcro/cable-ties/1-2-velcro-brand-one-wrap-black) | VELCRO® Brand ONE-WRAP®, 1/2" wide, black, 25 yd roll ($1.25/yd) — for the 4.0 × 18.0 mm cable slots | 1 | $31.25 | $31.25 | hookandloop.com | VERIFIED |
| 9 | M4 spacers, ~10 mm, aluminum, unthreaded | Stand display VESA face off the plate; clear the magnet nut stack and keep the rear-vent air channel open | 4 | — | — | [McMaster aluminum unthreaded spacers](https://www.mcmaster.com/products/spacers/material~aluminum/) | **NOT VERIFIED — length depends on measured nut-stack height; pick the part after measuring** |
| 10 | [GST90A12-P1M](https://www.digikey.com/en/products/detail/mean-well-usa-inc/GST90A12-P1M/7703717) | PSU upgrade: Mean Well 12 V / 6.67 A / 80 W desktop brick, barrel 5.5 mm OD × 2.5 mm ID, Level VI (bundled brick is 60 W vs 63 W budget) | 1 | $29.50 | $29.50 | Digi-Key (2,610 in stock) | VERIFIED — **confirm display jack size/polarity first** |
| 11 | [212099-01](https://www.digikey.com/en/products/detail/qualtek/212099-01/5639883) | IEC cord for item 10 (sold without one): NEMA 5-15P → C13, 6 ft, black, SVT 18 AWG | 1 | $7.52 | $7.52 | Digi-Key (3,107 in stock) | VERIFIED |
| 12 | 3506K67 (same SKU as item 3) | Optional: populate the 7 spare magnet positions | 7 | $23.92 | $167.44 | McMaster-Carr | VERIFIED (same page as item 3) |


## Stud length — this changed when the plate went to .188 in

The magnet's stud is a fixed **12.70 mm (1/2 in)**. Every millimetre of plate comes straight off
the thread left for the nut. At the settled **4.75 mm** plate:

All ten combinations of {standard nyloc, thin nyloc, distorted-thread, standard hex,
jam nut} × {washer, no washer} are drawn in
section in `stack_detail.svg`. Checked against the **thickest** washer McMaster might ship
(0.069 in), because they sell it to a range, not a nominal:

| stack | locking | needs | vs stud | |
|---|---|---|---|---|
| washer + nylon-insert locknut | yes | 15.23 mm | −2.53 mm | does not fit |
| nylon-insert locknut, no washer | yes | 13.48 mm | −0.78 mm | does not fit |
| washer + distorted-thread locknut | yes | 13.25 mm | −0.55 mm | does not fit |
| washer + standard hex nut | — | 13.25 mm | −0.55 mm | does not fit |
| washer + THIN nylon-insert locknut | yes | 12.62 mm | +0.08 mm | inside the tolerance stack |
| standard hex nut, no washer | — | 11.50 mm | +1.20 mm | fits, but does not lock |
| distorted-thread locknut, no washer | yes | 11.50 mm | +1.20 mm | fits; runner-up |
| **THIN nylon-insert locknut, no washer** | **yes** | **11.10 mm** | **+1.60 mm** | **use this** |
| washer + JAM nut | — | 11.03 mm | +1.66 mm | fits; does not lock |
| JAM nut, no washer | — | 9.51 mm | +3.19 mm | fits; does not lock |

At the earlier .119 in plate the nyloc-without-washer case worked, which is why this BOM was
first drafted with nylocs. It no longer does. `stack_detail.svg` regenerates from the same
parameters and re-checks itself if the thickness changes again.

### Why the washer is worth the 1.75 mm

Three parts clamp against this plate and they do not share a footprint (all derived in
`engineering_report()`, reported as `*_bearing_area_mm2`):

| bears on the plate | area | pressure at the magnet's 61.2 lbf |
|---|---|---|
| magnet face (Ø48.02 against Ø8.5 hole) | 1754 mm² | 23 psi |
| **washer (Ø19.05 / Ø8.74)** | **225 mm²** | **176 psi** |
| bare thin nut (12.70 AF against Ø8.5 hole) | 70 mm² | 565 psi |

None of these threatens 36 000 psi mild steel — this joint is preloaded by the magnet's own pull,
not by torque. The washer is cheap insurance against point-loading a hole edge, not a structural
necessity.

### Locking — RESOLVED 2026-08-27

An earlier revision of this BOM said no locking feature fits. That was wrong: it tested exactly
one locknut (the standard-height nylon-insert, 8.73 mm), found it too tall, and generalised from
a single sample. **Two locking constructions fit comfortably:**

- **Thin-profile nylon-insert locknut, 1/4" (6.35 mm)** — +1.60 mm to spare. Specified.
- **Distorted-thread ("all-metal") locknut, 17/64" (6.75 mm)** — +1.20 mm, and the *same height
  as a plain hex nut*, so it adds locking for nothing. Runner-up only because it is not reusable
  and is not stocked in black oxide.

Threadlocker is no longer needed.

**The washer is the thing that had to go, not the locking** — for two independent reasons:

1. **It does not fit.** With the thin locknut a worst-case washer leaves +0.08 mm, which is
   inside the tolerance stack on a stud length, a plate thickness and a washer thickness added
   together. Note *thickness* is what runs out, not diameter — a larger washer would not help.
2. **It is not needed.** The bare nut bears at 565 psi on the plate, ~64× under mild steel's
   36 000 psi yield. There is no point-loading problem for a washer to solve here. A nut backing
   off under touch-cycling, by contrast, is a real failure mode.

**If you would rather have the washer than the locking nut**, the swap is a JAM nut
([98514A035](https://www.mcmaster.com/98514A035/)) plus an **oversized** washer
([90377A164](https://www.mcmaster.com/90377A164/), black oxide, Ø1.250"): 11.03 mm used, +1.66 mm
to spare, and **732 mm²** of bearing — 10× the bare nut. It costs the locking feature, so it
would want threadlocker. Not the specified build.

### Finish — BLACK OXIDE, specified (2026-08-27)

Only the **arm** fasteners are visible: the plate's nuts hide in the 10 mm spacer gap behind the
display, and every magnet body faces the fridge. On the arm the magnets sit underneath and the
nuts face **up**, where you look straight down at them against a matte-black arm.

| part | plain 18-8 | **black oxide 18-8 (specified)** | delta per piece |
|---|---|---|---|
| **thin nylon-insert locknut** | 90101A237 — $10.34/50 | **90101A122** — $18.72/50 | +$0.17 |
| standard hex nut (not used) | 91841A030 — $8.28/50 | 97149A150 — $6.60/25 | +$0.10 |
| thin/jam hex nut (not used) | 91847A030 — $7.25/100 | 98514A035 — $3.20/25 | +$0.06 |
| washer (not used) | 92141A030 — $7.53/100 | 96765A145 — $15.95/100 | +$0.08 |
| distorted-thread locknut | 90047A115 — $13.45/50 | **not stocked in black** | — |

At 15 magnet positions the black upcharge is **under $3 for the whole build**. Two caveats:
black oxide on stainless is a cosmetic conversion coating with little corrosion resistance (fine
indoors), and it does nothing for the **magnet cases**, which are zinc-plated steel and stay
silver. On the arm they face down and are not visible; on the plate nothing is.

*Black-oxide part numbers were read from the same McMaster tables on 2026-08-27 but at small
screen size — re-check the digits at order time.*

**The thread is 5/16"-18 UNC — imperial.** It is NOT M8. The two are close enough (7.94 vs
8.00 mm) to cross-thread if the wrong box is opened.

## Subtotals

| | |
|---|---|
| **Fitted now** (items 1–8, spacers excluded pending measurement) | **$928.73** |
| **Optional upgrades** (items 10–12: PSU + cord + 7 spare magnets) | **$204.46** |
| Item 9 (spacers) | unpriced until measured — typically < $10 |

At 15 magnets total the order crosses nothing useful; the 50+ price break on 3506K67 is far away.
Nut, washer, and screw packs each cover the full build several times over.

## Measure before ordering

1. **Display VESA insert depth** (item 6 length). M4 × 10 mm leaves only ~5.25 mm of engagement past the
   4.75 mm plate. The display's insert depth is not published; measure the actual monitor before
   committing. Same McMaster family stocks 8/12/16 mm lengths if 10 mm is wrong. The Waveshare
   "screws pack" contents are also unknown until the box is open.
2. **Magnet stud stack-up** (items 3/4/5) — RESOLVED 2026-08-27, see the stud-length section.
   Plate 4.75 + thin nylon-insert locknut 6.35 = 11.10 mm against a 12.70 mm stud, +1.60 mm to
   spare, with a locking feature and no washer. The stale figures that used to sit here were
   computed on the .119 in plate.
3. **Spacer length** (item 9) = whatever the nut stack actually measures proud of the plate
   (~10 mm expected), so the display's rear box lands on spacers, not on nuts.
4. **Display DC jack** (item 10): assumed 5.5/2.5 mm barrel, center-positive — confirm against the
   bundled brick before buying the Mean Well.
5. **Fridge-side unknowns** (affect pads, not cut geometry, but check before final assembly):
   top corner radius `R_f`, crown, whether the Samsung side panel is magnetic at all, hinge-cover
   clearance. See CLAUDE.md §2.
6. **SendCutSend bend deduction**: replace the generator's estimated BD with their bending
   calculator value before the production order.

## Foam note (item 7)

7/16" (11.11 mm) is the thickest adhesive-backed closed-cell neoprene McMaster stocks that stays
**under** the 11.51 mm magnet face height — it exists only as **strips** (max 2" wide, 10 ft);
their sheet line jumps 3/8" → 1/2", and 1/2" (12.7 mm) would stand proud of the magnets. The
design's 72 mm-wide neck pads must therefore be built up from strip runs (one 2" run + one ~21 mm
rip per pad), and the arm/bottom pads pieced the same way. One 2" × 10 ft roll (0.155 m²) covers
the whole pad plan (~0.115 m²) with margin. Cheaper narrower rolls exist on the same listing
(1" × 10 ft = [93375K677](https://www.mcmaster.com/93375K677/), $76.83) if piecing from 1" runs is
acceptable. Note the stocked foam is rated Soft (12 psi to compress 25%), not the 50–60A "firm"
originally intended — see Decisions.

## Substitutions that would work

- **Locknuts**: it must be a **THIN-PROFILE** 5/16"-18 locknut — a standard-height nylon-insert
  nut is 8.73 mm and does not fit, whatever it is made of. The only other construction that fits
  is the distorted-thread type at 17/64" ([90047A115](https://www.mcmaster.com/90047A115/),
  $13.45/50, plain only). Check the **height** column, not the description.
- **Washers**: none. There is no room for one behind the plate (see the stud-length section).
- **VESA screws**: any standard M4 head — socket cap, pan or low head. The holes are NOT countersunk and do not need to be: the 11.5 mm magnet standoff clears the head. Material is
  non-structural here. Black-oxide is specified for consistency with the magnet fasteners.
- **Foam**: blended Buna-N/neoprene/vinyl strips on the same McMaster listing, or EPDM equivalents,
  as long as closed-cell, adhesive-backed, and ≤ 11.51 mm thick.
- **Strap**: 5/8" ONE-WRAP also passes the 18 mm slots; 3/4" (19.05 mm) does **not**.
- **PSU**: any regulated 12 V ≥ 80 W Level VI brick with the correct barrel; GST120A12-R7B
  (102 W, $42.90 at Digi-Key) if headroom is wanted, but it uses a 4-pin DIN plug — wrong
  connector as shipped.
- **Not substitutable**: the magnets' male-stud style is load-bearing for the flat mounting plane
  (female-thread pots would need a screw head on the display side); the 7/16"-under-11.51 mm foam
  bias; the 240 mm magnet-spacing floor (geometry, not a purchasable).

## DECISIONS NEEDED

1. **Washer under the magnet nuts, or not?** The 1/2" stud is ~0.3 mm too short for full nylon
   engagement with a standard washer in the stack. Options: (a) omit the washer — full collar
   engagement, nut bears directly on plate (**recommended**; the joint is torsion-loaded shear,
   not tension, and the plate face is powder-coated steel); (b) keep the washer and accept partial
   collar engagement; (c) source a thinner washer.
2. **Foam width strategy**: one 2" × 10 ft roll pieced into 72 mm pads ($141.83,
   **recommended** — fewest seams), or two 1" × 10 ft rolls ($153.66 total), given no 72 mm-wide
   stock exists at 7/16".
3. **Accept Soft-rated foam?** Stocked 7/16" neoprene is 12 psi-to-compress (Soft), not the 50–60A
   firm sponge in the brief. **Recommended: accept** — the pad's job is conforming to the corner
   radius and crown, and the hook (not the pad) carries the load; a 50–60A solid rubber pad at
   this thickness is not a stocked item anywhere obvious. If Charles disagrees, the search widens
   to Grainger/Rubber-Cal custom-cut.
4. **Buy the PSU upgrade now or try the bundled 60 W brick first?** 63 W budget vs 60 W brick is
   only over budget when the Pi 5 peaks. **Recommended: order items 10–11 with the rest** — $37
   against a bricked boot-loop debugging session, and next-day availability either way.