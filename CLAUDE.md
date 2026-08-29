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

### 1.3 The wedge is BACKUP, never the primary load path
The foot slides under the fridge and is wedged so appliance weight bears on it. That is a real and
useful anchor, but **how hard someone drove a wedge is not a designable quantity**. Size everything
so the magnets alone carry the case; treat the wedge as redundancy. Report what the wedge
contributes; never depend on it.

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
