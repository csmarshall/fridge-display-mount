# CLAUDE.md — Fridge-Side Display Mount, STRUT REVISION

A floor-standing frame that carries a Waveshare 23.8 in FHD touch monitor on the **left side
panel** of a Samsung RS23A500ASR counter-depth side-by-side. Two slotted struts on a bent foot,
magnets for stiffness, the floor for load.

Original brief: `BRIEF.md`. Evidence: `reference/`. Live state: `session-state.md`.

**This supersedes a completed hook design** (repo `csmarshall/fridge-magnet-mount`, tag
`hook-final`). That design is not wrong — it is superseded. Anything in this file that contradicts
it is a deliberate change, not an oversight.

---

## 1. Design invariants — SETTLED, do not re-litigate

### 1.-1 NOTHING IS FIXED TO THE BUILDING. EVER.
**Stated by Charles 2026-09-01, in these words:** *"WE ARE NOT BOLTING INTO THE FLOOR EVER!!!
This mount is designed to be removable and cause no damage to the things it's leaning against
and clamping onto."*

No floor anchors, no wall anchors, no adhesive to the appliance, no fastener into anything that
is not a part of this mount. Every load goes to the **floor by bearing** and to the **fridge by
clamping**, and the whole thing lifts away leaving no mark. This governs the appliance too: foam
lines the inside of every clamp, no steel touches the panel, and the pads are EPDM rather than
rubber because rubber stains polyurethane floors.

Why this is written at the very top rather than buried: it is not a preference, it is the reason
the design has the shape it has. The clamp reaches under the fridge INSTEAD of an anchor; the
foot turns outboard onto the floor INSTEAD of being screwed to it. Anyone "simplifying" either
of those into a fixing has thrown away the point of the project.

**It has already been violated once — in a DRAWING, not in the design.** `hybrid_sketch.py` drew
the lower clamp's short leg running DOWN through the floor line (it runs UP the side; the lower
clamp is the top clamp FLIPPED), which made the elevator bolts read as anchoring into the floor.
Fixed 2026-09-01. **When drawing the base, check that nothing crosses the floor line.**


### 1.0 Anti-tip is a CLAMP, not the magnets
Two adjustable L brackets, top and bottom of the struts, foam-faced where they touch the
appliance, slid along the strut slots until engaged and locked. That clamps the struts to the side
panel positively.

The top bracket carries NO weight — the foot does — so it holds about **3.8 lb**, and its reach
only has to be enough not to slip. It is not a hook; do not size it like one.

**The two clamp brackets are ONE part made twice**, the lower flipped, sized for the bottom's
10–20 mm gap because the top is never the binding case.

**The foot and the lower clamp must NOT be combined into one part.** The clamp slides UP the slot
to generate its force; the foot must stay on the floor. One part doing both means tightening the
clamp lifts the foot off the ground.

**Consequence: the magnets are no longer structural.** They drop to anti-rattle, or go entirely.
If a future revision removes the clamp, the magnets have to come back to structural duty and every
number in §1.1 changes with them.

### 1.0b Two parts, two of each — and the stud is an ELEVATOR BOLT
Part A is the studded clamp, Part B the slotted foot. The stud is an **ELEVATOR bolt** through a
square laser-cut hole: the square shoulder stops it spinning, so the bracket needs no welding and
stays a laser-plus-one-bend part. **Do not specify a welded stud** — SendCutSend cannot weld and it
would make the bracket a two-operation part.

**Elevator, not carriage, because the head faces the FRIDGE.** At 2.78 mm thick and flat it hides
inside the 3 mm foam; a carriage bolt's 5.08 mm dome stands proud of the same foam and presses a
hard point onto appliance sheet. It also bears over 715 mm² instead of 308.

**The nut goes INSIDE the channel**, bearing on the strut's back web — the slots are in that web.
The bolt only spans 7.83 mm of material, so 3/4-1 in is plenty. Do NOT run it through the channel
and nut it outside: that is where the PLATE's channel nuts have to go, and the open face must
stay clear.

**The foot slot must clear the 8.38 mm square NECK, not the 7.94 mm shank.** The neck is 4.83 mm
long against a 3.02 mm clamp leg, so it passes 1.80 mm through into the foot. Easy to get wrong by
sizing off the thread.

**ONE foot per strut, outboard, tucked under the strut.** The strut stands on its horizontal leg
and never touches the floor. The inboard foot was removed 2026-08-31 as redundant: tipping outward
is the outboard foot's job, tipping inward is stopped by the fridge itself, and anti-lift under the
appliance was always the lower clamp's.

Because the base stack puts 6.05 mm between panel and strut, the top needs **3.02 mm of washers**
to keep the strut parallel. Without them it leans.

**LOW-PROFILE CHANNEL IS A REQUIREMENT, not a preference.** Standard height would add 20.6 mm to
the display's projection. Minimising that projection is an explicit goal — the display face sits
75.7 mm off the panel as designed, of which 66.7 mm is unavoidable.

**Sliding is stopped by the 406 mm clear window**, not by friction: size the top clamp's long leg
to fill it and the hinge cover and rear edge capture the assembly front-to-back.

### 1.1 The load path is the FLOOR, and the magnets are for STIFFNESS
Vertical load goes display → plate → struts → bent foot → floor. Compression into a floor is
unarguable and needs no justification.

The magnets do NOT carry weight. They resist a touch press pulling the screen away from the panel,
which is a **PULL** on them — their strong direction, unlike the hook design where the equivalent
duty was shear and torsion. Demand is ~1.25 lb each against ~61 lb derated. Any magnet resize must
preserve a large margin here, but the margin available is enormous.

**The foot gives stability, the magnets give stiffness, and they do not substitute for each
other.** Tying the strut bases does nothing for sway, because the pull load is out of the frame's
plane. Unpropped sway is 4.7 mm; that is what the magnets remove.

### 1.2 Strut orientation is forced
Flat back on the panel, slots facing the room. It is the only orientation where a magnet can bear
on the channel, and it gives a wide flat bearing that will not dent appliance sheet. The
consequence is that the channel's WEAK bending axis faces the pull direction. Accept it — the
magnets carry that load, not the strut.

### 1.3 The pad CAPTURES the tail; it does not transfer load
The foot slides under the fridge and a **conforming foam pad** on the tail takes out the slack —
never enough to lift weight off the appliance's levelling legs or press on its base pan.

The gap is **10–20 mm and the underside is NOT flat** (2026-08-29), which is why it is a pad and
not a wedge or a jacking screw: conformity is worth more than adjustability against a surface
whose shape is unknown.

**PRELOAD IS THE TRAP.** Area multiplies pressure — a 60 × 200 mm pad compressed 25 % pushes
223 lb upward, half the appliance. Size it to JUST TOUCH and fit it by building up layers.
Half a percent of strain is 0.3 mm of screen movement, and contact is all the job needs.

The anti-tip mechanism is therefore **geometric, not frictional**: with the slack gone, the tail
can only rise by the wedge clearance before it bears on the underside of the cabinet. Tipping is
stopped by a positive stop you can design and inspect.

Do NOT reintroduce a design that depends on how hard someone drove a wedge. Size everything so the
magnets carry the working case on their own; the captured tail is what stops a lurch becoming a
topple.

**Corollary — state the failure mode honestly.** If every magnet released, the hook design's screen
would sag but stay hung. This one would rotate on the captured tail. That is a real difference and
the package must say so rather than bury it.

### 1.4 Do not blank off the display's rear vents
The rear box carries the Pi 5's fan and GPIO in its FACE, at an **87.5 mm radius** from the VESA
centre. Vent windows are placed on that radius, not as a margin from a plate edge, so one covers
the opening in every 90° rotation. Spacers between plate and display are load-bearing on this
invariant: without them the plate bolts flat onto the Pi's cooling.

### 1.5 Provenance is part of the number
Every figure is MEASURED, DERIVED, or ESTIMATED, and says which. The strut's section properties
are derived with an estimated return lip. The magnet mass is an estimate because no vendor
publishes one. A guess and a vendor figure must never wear the same font.

---

## 2. Hardware

Everything dimensional lives in `reference/`. Do not restate figures here that the evidence
already carries — point at it.

- **Display** — Waveshare 23.8 in FHD (SKU 34025). 555.23 × 324.65 × 18 mm panel + 25 mm rear box
  = 43 mm overall, 3.94 kg, VESA 100 on the rear box face.
- **Floor** — wood, flat enough to need no levelling adjustment. The foot stays a simple bent
  part but gets a **pad underneath**: not for pressure (under 3 psi) but because laser-cut edges
  line-load an imperfect floor and this sits unmoved for years. The pad must **grip as well as
  protect** — felt is the standard answer and is wrong here, because sliding is the one failure
  this design has no other defence against. Non-marking rubber or EPDM; the compound matters,
  since rubber against a polyurethane finish can discolour it over years.
- **Servicing** — the fridge is pulled out rarely; moving it is treated as a teardown. The wedge
  may therefore be fitted to the gap rather than designed to slide in and out.
- **Fridge** — Samsung RS23A500ASR. Case **1743.1 mm** tall, **609.6 mm** deep, 229 lb.
  **Top and sides both measured MAGNETIC** (2026-08-26). The top is measured FLAT — but this
  design does not touch it, so that no longer matters.
- **Strut** — McMaster 3310T791, black powder-coated, 20.64 × 41.28 mm, 1.78 mm wall.
  See `reference/strut-channel-3310T791.md`.
- **Magnets** — DELIBERATELY REOPENED. See BRIEF.md §4.

## 3. Manufacturing — SendCutSend

Same fabricator, same process as the hook design: laser cut plus ONE 90° bend on the foot.
Constraints in `reference/sendcutsend-*.pdf`. Re-verify before ordering; they change.

The DXF carries **one dashed LINE** at the bend centre — a geometry-only upload greys out bending
and the app reports "No bend lines detected". A SOLID line would be read as a cut and would slice
the part in half.

## 4. Code style
- Timestamped logging, level configurable. Type hints and dataclasses where they earn it.
- **No drifting constants.** Derive anything derivable. If a constant genuinely cannot be derived,
  say so and explain why.
- **Never hand-maintain what the generator can emit** — order tables, hole schedules, BOM
  quantities. The previous project's order document drifted a full revision this way.
- A CLI flag may only turn something OFF. Argparse defaults silently overrode dataclass values
  five separate times in the previous project.
- Full implementations, no stubs. Remove dead code.

## 5. Drawing rules — learned the hard way
- SVG is XML: escape `&`, `<`, `>` in every text emitter.
- Emit leaders, rules and dimensions BEFORE any text that must survive them.
- Derive label positions; never fix two things that have to stay clear of each other.
- Colour follows the BACKGROUND. The fridge renders near-black; text on it needs the light
  palette, text on paper does not.
- **Render it and look at it.** Layout cannot be reasoned about. Three consecutive fix passes in
  the previous project each repaired defects and introduced new ones.

## 6. Environment
`python3 -m venv .venv && .venv/bin/pip install ezdxf`. Run everything with `.venv/bin/python`.
