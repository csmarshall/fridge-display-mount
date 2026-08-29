# Fridge-Side Display Mount — STRUT REVISION

Mount a Waveshare 23.8 in FHD touch monitor on the **left side panel** (facing the fridge) of a
Samsung RS23A500ASR counter-depth side-by-side, at a comfortable standing touch height, to run a
household chore board.

**This supersedes a completed hook design.** That design is finished, validated and quoted — it is
not abandoned for being wrong. It is superseded because this one is height-adjustable after the
fact, does not depend on the fridge top at all, and puts the load into the floor. The hook repo is
tagged and kept; see "What came before".

---

## 1. The design, as decided

A **frame**, not a bracket:

```
        display  -> plate -> two struts -> bent foot -> FLOOR
                       |          |
                    (VESA)    magnets to the side panel, in PULL
```

- **Two 6 ft slotted struts**, McMaster **3310T791**, black powder-coated low-profile channel,
  running vertically up the side panel at **246 mm centres**.
- **A bent foot** — one manufactured part — that ties both strut bases together, slides under the
  fridge, and is **wedged** so the appliance's own weight bears on it.
- **A plate** across the struts carrying the display on VESA 100.
- **Magnets** through the strut webs onto the side panel.

### The strut orientation is forced, and it is the good one

Flat back against the panel, slots facing the room. It is the only orientation where a magnet can
bear on the channel, and it gives a wide flat bearing. The cost is that the channel's WEAK bending
axis ends up in the pull direction — which does not matter, because the magnets carry that load.

### The plate should bolt on unmodified if it can

The hook design's plate is 310 × 310 with four Ø8.5 magnet holes at **246 mm centres**, which is
exactly the strut spacing, and Ø8.5 clears a 5/16 channel bolt. Reusing it unchanged is the
cheapest good outcome. **Verify this rather than assuming it** — the previous plate's holes were
sized for a magnet stud, not a channel bolt, and the loads are different now.

---

## 2. What is settled, and the numbers behind it

All computed against a 5 lb press at the screen centre (1331 mm), which is the governing everyday
load — not the display's weight.

| | |
|---|---|
| Overturning at the base | 29.6 N·m |
| Foot strength, 310 mm wide, 0.187 in | 25 MPa vs 248 yield — **SF 10** |
| Strut strength, pull direction | 41 MPa — **SF 6.1** |
| Torsion, edge press, over 246 mm spacing | **3.3 lb per strut** |
| Magnets propping at screen height | **5 lb of PULL shared over 4** — 1.25 lb each |
| Sway if the magnets were absent | **4.7 mm** at the screen |

**The magnets provide STIFFNESS, the foot provides STABILITY, and they are not interchangeable.**
Tying the strut bases does nothing for sway, because the pull load is out of the frame's plane.

### The wedge

The foot slides under the fridge and is wedged (wood shims or similar) so appliance weight lands
on it. What that has to achieve:

| wedge inboard | weight needed on the foot | as a share of the fridge |
|---|---|---|
| 100 mm | 66.6 lb | 29 % |
| 150 mm | 44.4 lb | 19 % |
| **200 mm** | **33.3 lb** | **15 %** |
| 250 mm | 26.6 lb | 12 % |

It is a modest fraction, and further inboard is cheaper. But **how hard someone drove a wedge is
not a designable quantity**, so treat the wedge as BACKUP. The magnets carry the case on their
own at roughly 49×, in pull.

---

## 3. Open — must be resolved on the actual appliance

1. **How high the cabinet base sits off the floor.** This is the entire budget for foot thickness
   plus wedge. If it is less than about 10 mm the foot has to get thinner or the design changes.
2. **What the underside is like 100–250 mm in** — flat pan, ribs, a rail, or a void. It sets the
   wedge position and whether anything can be positively hooked instead of merely wedged.
3. **Whether wedging ~15 % of the appliance onto the foot rocks it or dents the base pan.** A
   fridge sits on levelling legs; taking load off them is not automatically harmless.
4. **Floor flatness and finish** where the foot lands. It is a wood floor.
5. **Whether the fridge gets pulled out to clean**, and how the foot behaves when it does.

---

## 4. The magnet decision — deliberately reopened

The hook design used McMaster **3506K67**: Ø48.02 × 11.51 mm, 175 lb rated, **$23.92 each**, eight
of them — **$191, the largest line in the BOM**.

In this design the demand is **1.25 lb per magnet against 61.2 lb of derated capacity — 49×**.
That is heavily over-specified. **Resize it.** Constraints to respect:

- Derate to **~35 %** of rated pull on 0.6–0.9 mm painted appliance sheet. Vendor ratings assume
  thick steel at zero gap and neither holds here.
- The magnet body height IS the standoff, and it must clear the strut wall (1.78 mm) with enough
  stud left for a nut inside the channel.
- Keeping a **5/16"-18 male stud** would let the whole fastener analysis carry over unchanged
  (`reference/inherited-fastener_matrix.pdf`). A different thread means redoing it.
- Read `reference/inherited-magnet_primer.pdf` first. The physics of why ratings mislead is
  already worked out and it does not need redoing.

---

## 5. Deliverables

Match the previous project's shape — it worked:

| | |
|---|---|
| `generate_foot.py` | parametric generator for the bent foot. Formed dimensions in, flat pattern derived by subtracting the bend deduction. **Validates, then writes; exits non-zero and writes NOTHING on failure.** |
| `foot_flat.dxf` | the upload file. mm, layer 0, closed contours, one dashed bend line |
| `foot_params.json` | machine-readable expected geometry |
| `audit_dxf.py` | acceptance test, run after every generation (copied in, needs re-pointing) |
| `assembly_*.svg` | how it goes together |
| `SENDCUTSEND-ORDER.md` | order config, hole schedule GENERATED from the params, compliance table |
| `BOM.md` | sourced, with part numbers and dates |
| `index.html` | the console page, via `console_build.py` |

---

## 6. Hard-won lessons from the previous project

These cost real time. Do not rediscover them.

- **Never hand-maintain a table that the generator could emit.** The previous order document's
  hole schedule drifted a whole revision and described screws into a thread that did not exist.
- **A flag may only turn something OFF.** Argparse defaults silently overrode dataclass values
  five separate times, once putting duplicate holes 0.02 mm apart into a cut file.
- **Filter `spare` when counting magnets.** Counting holes as fitted magnets produced wrong force
  figures on four different sheets.
- **SVG is XML.** Text emitters must escape `&`, `<`, `>` — one bare `<=` silently destroyed a
  whole document.
- **Emit every leader, rule and dimension BEFORE any text that has to survive them.** The same
  z-order bug appeared in four different sheets; a halo behind text is useless if geometry is
  painted over it afterwards.
- **Derive positions, never fix two things that must stay clear of each other.** Fixing one and
  moving the other into it happened repeatedly.
- **Colour follows the BACKGROUND, not the subject.** The fridge is near-black; anything drawn on
  it needs the light palette, and anything drawn on paper does not.
- **Render and look. Do not reason about layout.** Three consecutive fix passes each repaired
  defects and introduced new ones; only rendering caught it.
- **State provenance.** Mark every number as measured, derived, or estimated. A vendor figure and
  a guess must not wear the same font.
