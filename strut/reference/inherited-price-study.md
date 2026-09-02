# Price Study — SendCutSend, pulled live 2026-08-25

Same part throughout: `bracket_flat_reach130.dxf`, 310 × 730.909 mm, qty 1, cut only unless noted.
Prices are what their instant quote returned, not estimates.

## Thickness / material sweep, sheet cutting only

| Material | Thickness | Price (qty 1) | qty 2 /ea | qty 10 /ea |
|---|---|---|---|---|
| 5052-H32 aluminium | .100" (2.5 mm) | **$59.38** | $47.50 | $30.42 |
| 5052-H32 aluminium | .125" (3.2 mm) | **$61.54** | $45.00 | $34.81 |
| 5052-H32 aluminium | **.187" (4.7 mm)** — as designed | **$131.49** | $86.11 | $61.06 |
| 5052-H32 aluminium | .250" (6.3 mm) | **$127.79** | $91.72 | $76.56 |
| A36/1008 mild steel | .119" (3.0 mm) CRS | **$87.39** | $57.01 | $41.66 |
| A36/1008 mild steel | .135" (3.4 mm) CRS | **$131.68** | $87.27 | $62.99 |

### What the numbers say

**The cliff is between .125" and .187" aluminium — it more than doubles, $61.54 → $131.49.**
Below .125" almost nothing is saved ($59.38 at .100"), so price down there is dominated by cut time
and handling, not material. Above it, .250" is actually *cheaper* than .187" ($127.79), which is
counterintuitive but is what their quote returns — likely stock and nesting, not a typo, since it
reproduced.

**Steel is not the saving.** At equal bending stiffness (E·t³) the match for .187" aluminium is
~3.35 mm of steel, i.e. .135", and that costs $131.68 — dead level with the aluminium it replaces,
while roughly doubling the plate mass. Thinner .119" steel at $87.39 is the only steel worth a
second look, and it gives up stiffness.

## Powder coating

| Option | Price | Delta |
|---|---|---|
| No coating | $151.26 | — |
| **Gloss Black powder coat** | **$220.52** | **+$69.26** |

Includes free deburring. Lead time moves out ~2 days (Sep 1 → Sep 3).

15 colours offered: Gloss / Matte / Wrinkle / Textured Black, Bronze, Textured Gray, Metallic Grey,
Safety Orange, Gloss Red / White / Blue / Green / Grey / Yellow, Matte White.

**Powder coat costs more than the bend and all four countersinks combined.** It is also the single
finishing choice with a mechanical consequence — see the warning below.

## Full ladder, as designed (5052 .187", variant A, qty 1)

| Configuration | Price |
|---|---|
| Sheet cutting | $131.49 |
| + 1 bend @ 90° | $145.70 |
| + 1 countersink | $151.26 |
| + 4 countersinks (projected) | ~$167.94 |
| + Gloss Black powder coat | **~$237.20** |

## Coating and the magnets — CORRECTED 2026-08-25

An earlier version of this document claimed powder coat lands "under the magnets" and costs holding
force, and recommended masking. **That was wrong.** The stack is:

```
fridge steel | magnet rubber face | magnet body 6 mm | screwed to -> plate
```

The magnet's WORKING FACE touches the fridge. The plate sits BEHIND the magnet. Coating the plate
puts material between the plate and the magnet's back, never between the magnet and the steel it
grips. Pull is governed by the face-to-fridge gap, which coating does not change.

**So coat the whole part freely. No masking, no sanding, no penalty.**

What genuinely does open a magnet-to-fridge gap, and is already accounted for:
- the magnet's own rubber coating (it is in the vendor's rated pull, and in our 35% derate)
- paint on the FRIDGE panel (same derate)
- the fridge panel's flatness — a side panel bowed outward means the corner magnets sit off it

One small second-order point in steel's favour: coating between the magnet's steel cup and a
FERROUS plate slightly reduces flux shunting into the plate, if anything a marginal gain.

The only residual concern is coplanarity — four rigid magnets on a plate whose coating varies in
thickness sit at slightly different depths. Powder is uniform to well under 0.05 mm, which is small
against the fridge panel's own flatness. Not worth acting on.

## If cost is the driver

Dropping to **.125" 5052 saves ~$70** and would still be structurally fine on paper — the plate is
hugely overbuilt (neck bending SF 66×, weak axis SF 34× at .187"; roughly 2.25× the stress at .125",
so SF ~29× and ~15×). **But it is not a free swap:**

- Bend radius, minimum flange and **bend deduction all change with thickness**, so the flat pattern
  must be regenerated — `--bend-deduction` from their calculator for .125", and the generator's
  `Material` constants updated.
- Thinner plate is floppier in handling and around the Ø90 vent and windows, which is a feel issue
  rather than a strength one.
- **Countersinks still fit at .125", but only just, and only because our holes are oversized.**
  Their M4 90° countersink has an 8.001 mm major. Depth is `(major − hole)/2`:

  | hole | depth needed | .125" limit (60% × 3.175) | verdict |
  |---|---|---|---|
  | our Ø4.5 | **1.750 mm** | 1.905 mm | **fits**, 0.155 mm to spare |
  | their nominal Ø4.166 | 1.918 mm | 1.905 mm | **exceeds** by 0.013 mm |

  So the very thing that looked sloppy — drawing Ø4.5 instead of their 4.166 minor — is what keeps
  countersinking legal at .125". At .187" both fit comfortably (2.850 mm allowed). Worth confirming
  with them rather than trusting my arithmetic on a 0.155 mm margin.


---

# Thickness Study — strength vs stiffness vs bulk

Generated by `thickness_study.py`; chart in `thickness_study.svg`.

| thickness | mass | screen-edge movement | neck SF | weak-axis SF | M4 c'sink | cut price |
|---|---|---|---|---|---|---|
| .080" (2.03 mm) | 0.83 kg | 1.82 mm | 13x | 6x | **too deep** | — |
| .100" (2.54 mm) | 1.03 kg | 0.93 mm | 20x | 10x | **too deep** | $59.38 |
| .125" (3.17 mm) | 1.29 kg | 0.48 mm | 31x | 15x | fits | $61.54 |
| **.187" (4.75 mm)** | 1.93 kg | **0.14 mm** | 66x | 34x | fits | $131.49 |
| .250" (6.35 mm) | 2.58 kg | 0.06 mm | 110x | 60x | fits | $127.79 |

**Strength is never the limit.** Even at .080" the neck carries 13x and the weak axis 6x. Nothing in
this range comes close to yielding. What changes by a factor of 30 across the range is **stiffness**,
and stiffness is what a hand feels.

"Screen-edge movement" is how far the corner of the display moves under the design load — 5 lbf
pressed at the outer edge, 278 mm off centre. Modelled as a cantilever from the VESA screw out to
the magnet, then amplified geometrically to where the finger actually is. Conservative: the real
plate is supported at four magnets and loaded at four VESA points, so it is stiffer than this
predicts. Treat the numbers as an upper bound and the *ratios* as reliable.

Below .125" the M4 90 deg countersink exceeds the 60%-of-thickness depth limit, so **.100" and
thinner cannot have countersunk VESA holes at all** — screw heads would then stand proud on the
fridge-facing side.

## "Strong but not bulky" — the bulk is not in the plate

| thickness | stack off the fridge | plate's share |
|---|---|---|
| .125" | 62.17 mm | 5.1% |
| .187" | 63.75 mm | 7.5% |
| .250" | 65.35 mm | 9.7% |

Magnet 6.0 + plate + spacer 10.0 + display 43.0. **The display's own 43 mm is two thirds of the
standoff.** Going from .187" to .125" buys back 1.6 mm of a 64 mm stack — invisible — while
tripling the flex. Bulk is not the reason to go thinner; only cost is.

**Recommendation: stay at .187".** It is the thinnest plate that lands inside "feels rigid"
(0.14 mm), it keeps countersinks legal with margin, and the 0.64 kg it adds over .125" is carried by
the hook, not the magnets.

## Powder coat masking — not offered, and not needed

> *"SendCutSend is unable to provide masking or finish specific areas or portions of parts."*

Coating adds **.002"–.005" per side (0.05–0.13 mm)** over the whole part. Per the correction above,
that is harmless here: it never lands between a magnet face and the fridge. Coat the lot.

Also worth knowing: tabs/micro-joints are not removed before coating and stay visible through it,
and tapped holes are not plugged. Neither applies to this part.

---

# Reach x Thickness Matrix

Reach and neck are **independent levers that both add to the same flat length**:

```
flat_length = body(300) + (neck - BD/2) + (reach - BD/2)
```

Neck sets how high the screen hangs. Reach sets how much foot the bracket has on the fridge top.
Neither one trades against the other — they just both cost sheet, at roughly **$0.10 per mm**.

```
Neck fixed at 310 mm  ->  screen centre 1331 mm above the floor  (INSIDE the 1216-1450 mm comfort band)
Sponge pad 6.35 mm; a reach is viable while pad margin >= 1.20x

  thick  reach   flat mm      price    pad   mass  screen move   verdict
------------------------------------------------------------------------------------
  0.125    130     733.0    $61.75   1.59x   1.29       0.48 mm   ok, but flexy
  0.125    180     783.0    $66.75   1.43x   1.37       0.48 mm   ok, but flexy
  0.125    230     833.0    $71.75   1.32x   1.45       0.48 mm   ok, but flexy
  0.125    280     883.0    $76.75   1.25x   1.53       0.48 mm   ok, but flexy
  0.125    326     929.0    $81.35   1.20x   1.61       0.48 mm   ok, but flexy
  0.187    130     730.9   $131.49*  1.59x   1.93       0.14 mm   ok
  0.187    180     780.9   $136.50*  1.43x   2.05       0.14 mm   ok
  0.187    230     830.9   $141.51   1.32x   2.17       0.14 mm   ok
  0.187    280     880.9   $146.52   1.25x   2.30       0.14 mm   ok
  0.187    326     926.9   $151.13   1.20x   2.41       0.14 mm   ok
  0.250    130     728.8   $127.56   1.59x   2.58       0.06 mm   ok
  0.250    180     778.8   $133.00   1.43x   2.75       0.06 mm   ok
  0.250    230     828.8   $138.44   1.32x   2.91       0.06 mm   ok
  0.250    280     878.8   $143.88   1.25x   3.07       0.06 mm   ok
  0.250    326     924.8   $148.88   1.20x   3.22       0.06 mm   ok

*  = actual SendCutSend quote. Unmarked prices are linear interpolation from the
   measured pairs and get less trustworthy the further they extrapolate.

Most reach that still feels rigid and has pad margin: 326 mm at 0.187" — flat 926.9 mm, about $151.13
```

## What this says

**Reach is cheap.** At .187", going from the minimum 130 mm to the pad's limit of 326 mm — an extra
196 mm of foot on the fridge top — costs about **$20**. That is the best value on the whole part.

**The pad, not the price, is the ceiling.** The 1/4" sponge runs out of squash at **326 mm** of
reach, because a longer arm rides further up the crowned top and that stacks with the corner-radius
gap. Step to a **3/8" pad and reach could go past 450 mm** — but then the pad no longer matches the
6 mm magnet height, so the arm magnets would need to be 3/8" tall too, and nobody stocks those.
**Treat 326 mm as the practical maximum.**

**Screen height is not the constraint you might think.** Any neck from **200 to 400 mm** puts the
screen centre inside the 1216-1450 mm band comfortable for 5'1"-6'4":

| neck | screen centre | |
|---|---|---|
| 200 mm | 1441 mm | top of band |
| 260 mm | 1381 mm | variant C |
| 310 mm | 1331 mm | variants A/B, band centre |
| 400 mm | 1241 mm | bottom of band |

So you can pick reach and height almost independently. Only the sum costs money.

## Diminishing returns

Reach resists fore-and-aft rocking by lengthening the lever the arm bears over. Going 130 -> 230 mm
is a large proportional gain. Going 230 -> 326 mm adds much less, while the arm becomes a 326 mm
tongue lying across a 910 mm fridge top — a third of the way over, collecting dust and competing
with whatever you store up there. **230-280 mm is the sweet spot**: most of the structural benefit,
about $10-15 over the minimum, and still an unobtrusive shelf.

## On .250" being cheaper than .187"

Real and reproducible — .250" quotes lower at **qty 1** on both flat lengths tested. But it reverses
at quantity:

| | qty 1 | qty 2 /ea |
|---|---|---|
| .187" variant A | $131.49 | **$86.11** |
| .250" variant A | **$127.79** | $91.72 |
| .187" variant B | $136.50 | **$89.17** |
| .250" variant B | **$133.23** | $95.44 |

A genuinely cheaper material would be cheaper at every quantity. This looks like a setup or nesting
artifact at qty 1. What .250" actually costs you: **+0.65 kg (+35%)** of plate, and 1.6 mm more
exposed edge. What it buys: screen-edge movement drops 0.14 -> 0.06 mm, which is stiffness you
already have at .187".

**Recommendation: stay at .187".** The $3.70 is noise, it evaporates the moment you order two, and
you would be paying for it in weight.


---

# Vent windows, and aluminium vs powder-coated steel

All quoted live 2026-08-25 on the SAME part (310 x 682.958 mm, portrait geometry, neck 262).

## Do the vent windows cost anything?

| | cut length | price, 5052 .187" |
|---|---|---|
| with the four windows | 3565 mm | **$129.46** |
| without them | 2591 mm | **$126.86** |

**$2.60.** Cut length drops 27% and the price barely moves, because the bounding box is unchanged
and material dominates. **Keep the windows** — they are effectively free, and they are the only
direct escape path over the display's rear-box opening.

Note on the internal-CPU-fan point: the openings in the display's rear box are fixed hardware. They
exist whichever fan is fitted, and an internally-cooled Pi still has to push its heat out through
them. The plate does not seal anything — it stands 10 mm off on spacers and is open on all four
edges — but a window directly over the opening is strictly better than solid plate, for $2.60.

## Aluminium vs mild steel

| option | mass | stiffness | screen move | neck SF | non-mag margin | bare | + powder |
|---|---|---|---|---|---|---|---|
| 5052 alu .187" | 1.86 kg | 100% | 0.14 mm | 66x | 2.58x | **$129.46** | $198.72 |
| mild steel .119" | 3.47 kg | 73% | 0.19 mm | 34x | 2.99x | **$86.75** | **$156.01** |
| mild steel .135" | 3.94 kg | 107% | 0.13 mm | 42x | 3.12x | $130.49 | $199.75 |

Stiffness is `E x t^3` relative to the aluminium baseline; screen move is scaled from the measured
0.14 mm. "Non-mag margin" is the arm hold-down over lift demand in the fallback case where the side
panel turns out not to be magnetic — the one place extra mass genuinely helps.

### Heavier IS better here

Confirmed rather than assumed. The hook carries all vertical load, so mass costs nothing
structurally, and it *buys* margin in the non-magnetic fallback: 2.58x -> 3.12x purely from weight.
The only real costs of mass are a two-person install (already true) and a trivial increase in
bearing load at the fridge's top corner.

### But steel changes the finish decision

Bare CRS will surface-rust in a kitchen. Steel effectively **requires** the powder coat, so the
honest comparison is steel+powder against aluminium's chosen finish:

- **Powder coating anyway?** Steel wins. `.119" steel + powder = $156` beats `alu + powder = $199`
  by $43. Or `.135" steel + powder = $200`, same price as aluminium but stiffer and heavier.
- **Happy with bare metal?** Aluminium wins. `$129` bare, and it will not corrode.

### One unverified caveat with steel

The pot magnets would be screwed to a **ferrous** backing plate. Pot magnets carry their own steel
cup which closes the magnetic circuit behind the magnet, so a steel plate behind them should make
little difference — but this is reasoning, not measurement. If going steel, test one magnet against
a steel offcut before committing.


---

# Live re-quote, 2026-08-25 — CURRENT geometry, both reach variants

Everything above this line was quoted against the **old** geometry: before the strap slots, before
the extra magnet rows, and at the old 310 mm neck. Those numbers are superseded. Re-quoted live at
app.sendcutsend.com against `variants/bracket_flat_reach130.dxf` and `..._reach180.dxf` as they
stand today (8 body magnets + 4 top-lip, 10 strap slots, 4 vent windows, 4 VESA patterns).

**A36/1008 mild steel, .119" (3.0 mm) CRS, qty 1, no finishing:**

| variant | blank | cut only | + one 90 deg bend | bend costs |
|---|---|---|---|---|
| reach130 (short) | 310 x 687.0 | **$96.70** | **$108.47** | $11.77 |
| reach180 (long) | 310 x 737.0 | **$101.04** | **$112.81** | $11.77 |
| difference | +50 mm | +$4.34 | **+$4.34** | — |

Quantity breaks on the short reach (cut only): 2 = $64.48 ea, 10 = $48.60 ea, 50 = $34.10 ea.
Both variants quoted "Arrives as soon as Aug 31".

**The long reach costs $4.34.** That is the entire price argument, and it is small enough that reach
should be chosen on fit — how far the arm can sit inboard past the hinge covers on the measured
fridge — rather than on cost.

The bend is a flat **$11.77** on either, and the app read the dashed bend line correctly both times,
reporting "1 Bend" with no intervention. That confirms the DXF bend-line decision end to end on the
current files.

**Cost of the changes since the last quote:** the short reach went $86.75 -> $96.70, i.e. **+$9.95**
for the 10 strap slots and the extra magnet holes. Worth knowing, not worth undoing.

## Finishing, same session

Matte black powder coating is offered on this material and includes deburring free:

| variant | cut only | + 90 deg bend | + matte black powder | coating adds |
|---|---|---|---|---|
| reach130 (short) | $96.70 | $108.47 | **$174.30** | $65.83 |
| reach180 (long) | $101.04 | $112.81 | **$182.54** | $69.73 |
| difference | +$4.34 | +$4.34 | **+$8.24** | |

Coated quantity breaks, short reach: 2 = $123.26 ea, 10 = $92.55 ea, 50 = $71.37 ea.
Lead time slips from **Aug 31 bare to Sep 3 coated**.

**Deburring is already included in every price above** — it is selected by default under Surface
Options, and powder coating includes it free regardless.

## Countersinking is not available on this material

Verified in their app: the Countersinking panel is greyed out on both variants and its tooltip
reads *"This operation is unavailable in this material."* That is a MATERIAL restriction on
A36/1008 mild steel, not the 60%-of-thickness depth cap this document previously blamed. The
depth math was real (1.80 mm needed against an 1.81 mm limit) but it was never the binding
constraint. The decision — ISO 7380 button heads — is unchanged.


## Removing the vent windows COSTS money — verified 2026-08-25

Quoted live, A36/1008 .119", qty 1, cut only, identical blank:

| | cut length | plate area | cut only |
|---|---|---|---|
| with 4 vent windows | 165.5 in | 1447 cm² | **$96.70** |
| no vent windows | 127.2 in (−23%) | 1595 cm² | **$97.38** |

**Removing them makes the part $0.68 dearer.** 23% less cutting does not pay for the 148 cm² of
steel you now keep — SendCutSend's material component tracks the part's own area, and their cut-time
component is small at this size. The windows are better than free: they are a $0.68 discount plus
116 g less mass.

That settles the question the CLAUDE.md vent invariant (§1.5) raised from the other direction: there
is no cost argument for blanking off the display's rear vents, so the invariant costs nothing to
honour. Keep them.


## What the price is actually made of, and why lightening does not pay

Three live points with known geometry (reach130, reach180, no-windows) solve
`price = a·part_area + b·cut_length + c` exactly:

- **$4.005 per 100 cm² of steel**
- **$0.136 per inch of cut**
- **$16.22 fixed** — setup, handling, minimum

So the $96.70 reach130 is roughly **$58 steel + $23 cutting + $16 fixed**.

That gives a hard break-even for any lightening cutout. A circle of radius R saves `a·πR²` of steel
and adds `b·2πR/2.54` of cutting, so it only pays above:

    R = 2b / (2.54·a) = 26.7 mm   ->   diameter 53 mm

| cutout | steel saved | cut added | net |
|---|---|---|---|
| Ø20 mm | $0.13 | $0.34 | **−$0.21** |
| Ø53 mm | $0.88 | $0.89 | $0.00 |
| Ø100 mm | $3.15 | $1.68 | **+$1.46** |
| Ø150 mm | $7.08 | $2.52 | **+$4.55** |

**A field of small lightening holes loses money.** Only a few large openings pay. Removing a
realistic 25% of the plate as Ø100 mm cutouts saves about **$6.74 — 7%** of the part price, for real
topology work, fresh edge-rule validation and recut risk. And it works against the preference for
this bracket to be heavier rather than lighter.

Caveat: three points, three unknowns, so the fit is exact and unvalidated. It predicts nothing yet.
A fourth quote on a deliberately lightened part would test it.

---

## Thickness ladder — live quotes 2026-08-26, on the AS-BUILT `bracket_flat.dxf`

All A36/1008 mild steel, 310 x 692 mm blank, qty 1. "full" = cut + 1 bend at 90 deg + matte black
powder coat. Quoted directly in app.sendcutsend.com against the real upload, not modelled.

| thickness | | bendable | cut only | full | mass | flex under 5 lbf | $/kg |
|---|---|---|---|---|---|---|---|
| .119" | 3.02 mm | yes | $96.07 | **$177.00** | 3.49 kg | 1.44 mm | $50.78 |
| .187" | 4.75 mm | yes | $107.28 | **$188.21** | 5.48 kg | 0.37 mm | $34.36 |
| .250" | 6.35 mm | yes | $137.55 | **$218.48** | 7.32 kg | 0.16 mm | $29.84 |
| .313" | 7.95 mm | **NO** | $186.43 | — | 9.17 kg | 0.08 mm | — |
| .375" | 9.52 mm | **NO** | $248.52 | — | 10.98 kg | 0.05 mm | — |
| .500" | 12.70 mm | **NO** | $297.58 | — | 14.65 kg | 0.02 mm | — |

### The hard ceiling is BENDING, not price
SendCutSend's app, quoted verbatim today: *"Bending isn't available on your selected material or
thickness. On compatible materials, our thickness range is .030" - .250" (varies per material)."*
At .313" and above the Bending panel greys out and the 3D preview stays flat. **.250" is therefore
the thickest this one-piece hook design can ever be.** Anything thicker would need a different
architecture — two pieces bolted or welded — which reopens the whole load path.

### The price curve is NOT monotonic
.187" HRPO ($107.28) is **cheaper than .135" CRS ($141.53)** despite being 39% thicker, because
hot-rolled is cheaper stock than cold-rolled. Do not assume thicker costs more inside this range.

### Thicker material forces a design change
At .187" and .250" the generator REFUSES to write: the centre arm spare hole sits 3.46 mm / 2.45 mm
from the arm strap slots against a 1x-thickness rule that has grown to 4.75 / 6.35 mm. SendCutSend
independently raised a **Deformation Warning** at .250" ("your bend line die area crosses geometry,
1 bend affected") because the die widens from 0.630" to 1.575". Both pass cleanly with
`--no-spare-holes`. So going thick costs the spare-magnet provision unless the strap slots move.

### Denser materials were NOT quoted
Mild steel is the cheapest metal SendCutSend offers, and the density gain from switching is small
(7.85 -> ~8.0 stainless, 8.5 brass, 8.96 copper) against a large price increase. For "heaviest per
dollar" steel wins on reasoning, but this is REASONED, not quoted — if it matters, quote stainless.

---

## Cross-material sweep — live quotes 2026-08-27, on the CURRENT 310 x 742 file

The part changed (reach 130 -> 180, blank 692 -> 742), so every earlier price in this document is
for a SMALLER part and is not comparable. These are quoted against `bracket_flat.dxf` as built.

| material | thickness | cut only | full (bend + matte black) | mass | plate flex |
|---|---|---|---|---|---|
| A36/1008 mild steel CRS | .119" | $103.16 | **$185.54** | 3.71 kg | 0.064 mm |
| A36/1008 mild steel HRPO | .188" | $112.43 | **$197.25** | 5.84 kg | 0.016 mm |
| A36/1008 mild steel HRPO | .250" | $144.33 | ~$229 (projected) | 7.74 kg | 0.007 mm |
| 5052-H32 aluminium | .187" | $144.87 | not quoted | 1.98 kg | 0.047 mm |
| 5052-H32 aluminium | .250" | $145.60 | not quoted | 2.65 kg | 0.020 mm |
| 304 stainless | .187" | $214.60 | not quoted | 5.92 kg | 0.017 mm |

**Mild steel wins on every axis that matters here.** At equal thickness aluminium costs 29 % more
for a third of the stiffness; stainless costs 91 % more for the same stiffness. Steel is
simultaneously the cheapest and the densest practical option, so price and heft do not trade off.

### The "cheap 1/4 inch" — RETIRED
An earlier version of this study recorded 5052 aluminium **.250" ($127.79) cheaper than .187"
($131.49)** and called it counterintuitive but reproducible. **It does not reproduce at the current
geometry**: .187" is $144.87 and .250" is $145.60 — 73 cents apart, i.e. flat, not inverted. Two
things follow: the anomaly was ALUMINIUM, never steel; and it was geometry-specific, so it should
never have been generalised. Steel .250" is $144.33, comfortably dearer than .188" at $112.43.

**The one non-monotonicity that DOES still hold is steel .188" HRPO ($112.43) undercutting .135"
CRS**, because hot-rolled is cheaper stock than cold-rolled. That is a stock-form effect, not a
thickness effect.
