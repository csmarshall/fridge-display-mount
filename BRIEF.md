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

It is a modest fraction, and further inboard is cheaper.

**DECIDED 2026-08-29: do not chase that load transfer.** The wedge is driven SNUG only — enough to
close the gap, no more. Nothing is taken off the fridge's levelling legs and nothing presses hard
on a base pan that was not designed for a point load.

**This changes what the foot is for, and it is a better answer.** A snug wedge does not anchor by
weight; it removes the slack so the tail is CAPTURED. If the frame tries to tip, the tail can only
rise by the wedge clearance before it bears on the underside of the appliance — tipping is arrested
**geometrically**, by a positive stop, not by friction or by transferred weight. That is a
mechanism you can design and inspect, where "how hard someone drove a wedge" is not.

The magnets still carry the working case on their own, in pull, at roughly 49×. The captured tail
is what stops a lurch becoming a topple.

---

## 3. Open — must be resolved on the actual appliance

**Measured 2026-08-29, roughly:** the gap under the side is **10–20 mm**, and **the underside is
NOT flat**. Both change the design — see §3b.

**Still open — need the appliance:**

1. **Whether a 150–250 mm tail fouls anything.** The irregular underside that gives the pad
   something to bear on also gives the tail something to hit: compressor, tubing, insulation,
   cross-members. This sets the tail depth and nothing else can.
2. **Whether there is a downward-facing rib or lip within reach.** If there is, HOOKING it beats
   bearing on it, because a hook has no compliance at all.

**Answered 2026-08-29:**

3. **Wedge pressure — SNUG ONLY.** See above. The foot captures the tail; it does not transfer
   load. Nothing comes off the levelling legs.
4. **Floor — wood, flat enough.** **No levelling adjustment** — the foot stays a simple bent part.
   But it gets a **pad underneath**, and the reason is not the pressure: at under 3 psi nothing is
   being crushed. It is that the foot's **laser-cut edges line-load a floor that is not perfectly
   flat**, that any grit trapped beneath turns the foot into an abrasive, and that this assembly
   sits unmoved for years rather than being shuffled about.

   **The pad has to GRIP as well as protect**, which rules out the obvious choice. Felt is the
   standard furniture answer and it is wrong here — it would let the assembly slide, which is the
   one thing it must not do. Wants a non-marking rubber or EPDM. **Flag:** rubber left in contact
   with a polyurethane wood finish for years can discolour it through plasticizer migration, so
   the compound matters. Not yet sourced.
5. **Pull-out — rare, treat it as a teardown.** Moving the fridge means unwedging and re-seating.
   That permits a deeper tail and a properly fitted wedge rather than something designed to slide
   in and out, and it means the wedge can be shaped for the gap rather than generic.

---

## 3a. CLAMP the struts to the fridge — decided 2026-08-29

Two adjustable L brackets, one near the top of the struts and one near the bottom, each reaching
from the strut onto the fridge with **foam on the face that touches the appliance**. Slide them
along the strut slots until both are engaged, then lock. The struts are then positively clamped
against the side panel.

**This is the strongest version of the design so far, and it is mostly free.**

### What the top bracket actually has to do

It is a RETENTION bracket, not a hook. The foot already carries the weight.

| clamp height | force to hold the top in |
|---|---|
| at the fridge top (1743 mm) | **3.8 lb** |
| lower, at 1500 mm | 4.4 lb |
| lower still, 1200 mm | 5.5 lb |

Compare the hook design's arm, which carried the **entire 24.9 lb** hanging weight, bore on a
sponge pad, and needed a **180 mm reach** purely to land magnets on metal. This bracket carries
nothing. Its reach only has to be enough not to slip off — tens of millimetres.

### What that buys

- **Anti-tip becomes positive and mechanical.** No longer a magnetic duty. The "what if a magnet
  peels" failure mode goes away.
- **The magnets drop to anti-rattle, or go entirely.** They were carrying 5 lb of pull; the clamp
  now does that. At $23.92 each that is **up to $191 off the BOM** — the largest line in it.
- **The hinge cover stops mattering.** A tens-of-mm reach at the rear of a 406 mm clear window is
  not a clearance problem the way a 180 mm arm was.
- **The slots ARE the adjustment.** A 6 ft strut is 1829 mm against a 1743 mm fridge, so it
  already stands 86 mm proud — the top bracket has somewhere to live without extending anything,
  and the clamp is made by sliding the lower bracket up until snug and locking it.

### What it costs

It reintroduces a fridge-top interface, which §1 had listed as something this design escaped.
That is a real give-back — but a light retention bracket with a short reach is a much smaller
commitment than an arm carrying the whole load, and the clear-window measurement that made the
hook work is already in hand.

### The two clamp brackets are ONE part, made twice

Top and bottom are the same L, the lower one flipped. Foam goes on the same face of the part in
both cases — facing down onto the fridge top, facing up against its underside. One DXF, one part
number, quantity two.

Size the part for the BOTTOM's constraint, which is the strict one: it has to enter a 10–20 mm
irregular gap. The top merely rests on a surface and has a 406 mm clear window to live in, so it
is never the binding case.

### The foot and the lower clamp must be SEPARATE parts

They point opposite ways off the same strut — foot outward onto the floor, clamp inward under the
appliance — so they do not conflict. But they cannot be one part, and the reason is mechanical
rather than aesthetic:

**The lower clamp has to slide UP the slot to generate clamp force. The foot has to stay on the
floor.** Combine them and tightening the clamp lifts the foot off the ground, which destroys the
load path you built the foot for.

### Sizing the foot, now that the clamp exists

If the foot had to resist tipping alone, by reaching out into the room:

| outward reach | SF |
|---|---|
| 200 mm | 1.04 |
| 250 mm | 1.30 |
| 300 mm | **1.56** |

About 300 mm gets there unaided — and that is a lot of steel on a kitchen floor, right where
someone walks.

**The clamp removes that requirement.** With anti-tip handled at the top for 3.8 lb, the foot only
has to carry 154 N downward and not rock. Size it for bearing and for not wobbling underfoot, not
for tipping — which means it can be modest, and stay out of the way.

### Open on this

- **How the brackets generate clamp force.** Sliding the lower one up the slot until snug needs no
  extra parts, but it wants drawing before it is believed — this is exactly the kind of thing that
  reads fine in prose and turns out to need a jacking feature once it is drawn.
- **What the bottom bracket engages.** Same 10–20 mm irregular gap as the foot, so probably the
  same conforming-pad answer in a second place.
- **Whether the identical-part idea survives contact with both reaches.** If the bottom is limited
  by fouling and the top by nothing, one length may be wrong for one of them.

---

## 3c. THE ASSEMBLY — decided 2026-08-31

**Two parts, two of each.**

**Part A — the studded clamp (×2, the lower one flipped).** An L: the long leg lies on the fridge
top, or reaches under its base. The short leg runs down (or up) the side. An **ELEVATOR bolt**
through a square hole in the short leg gives the stud — its square shoulder locks in the laser-cut
hole so it cannot spin, which means the bracket stays a pure laser-plus-one-bend part with no
welding and no secondary operation.

**Elevator, not carriage, because the head faces the FRIDGE.** 5/16"-18 elevator: head 30.16 mm
diameter x **2.78 mm** thick and FLAT, against a carriage bolt's 19.81 mm x 5.08 mm dome. At 2.78
the head **hides inside the 3 mm foam and never touches the panel**; a carriage dome stands
**2.08 mm proud** of the same foam and presses a hard point on appliance sheet. It also spreads
over 715 mm2 instead of 308 — 2.3x the bearing.

The square neck is 8.38 mm across x 4.83 mm long, so it passes **1.80 mm beyond** a 3.02 mm clamp
leg: **the foot's slot has to clear 8.38 mm, not just the 7.94 mm shank.**

**The nut goes INSIDE the channel, bearing on the strut's back web.** The slots are in that web,
so the bolt passes clamp 3.02 + foot 3.02 + web 1.78 = **7.83 mm of material**, plus the nut. A
3/4 in bolt would do; 1 in is comfortable.

Running the bolt clean through the channel and nutting it outside the open face would be a much
longer bolt for no reason, and it would put the nut exactly where the **plate's channel nuts have
to live**. The open face stays clear. Foam lines the inside of the L; no steel touches the appliance
anywhere.

**Part B — the slotted foot (×2, one per strut).** Vertical leg carrying an elongated slot for the
stud; horizontal leg bending **outward, into the room**, tucking under the strut so the strut
stands on it. It therefore never touches the floor and needs no separate floor pad.

**REVISED 2026-08-31: one foot per strut, not two back to back.** The inboard foot was removed
because it was doing nothing the rest of the assembly was not already doing:

| what it might have done | what actually does it |
|---|---|
| resist tipping outward | the outboard foot |
| resist tipping inward | **the fridge** — it is right there |
| anti-lift under the appliance | the lower CLAMP, which was always its job |

Removing it takes one layer out of the stud stack: the gap drops 12.07 → **9.05 mm**, the display
face comes in to **75.7 mm**, and the top washers halve from 6.05 to **3.02 mm**.

### The stack through the stud, and the washers that make it work

At the base the stud passes clamp leg + foot leg = **6.05 mm** before it reaches the strut. Left
alone that would stand the strut off at the bottom and hard against the panel at the top, so it
would lean.

**Fix: 3.02 mm of washers behind the strut at the top**, replacing the foot leg that is not there.
The strut then sits **~9 mm off the panel, parallel, top and bottom** — and nothing but foam ever
touches the appliance.

### How far the display ends up sticking out

66.7 mm of it is fixed no matter what — strut 20.64 + plate + 25 mm rear box + 18 mm panel. Only
the gap is a variable:

| | gap | display face off the panel |
|---|---|---|
| two feet back to back | 12.07 mm | 78.7 mm |
| **one foot, as built** | **9.05 mm** | **75.7 mm** |
| feet outboard of the strut entirely | 6.02 mm | 72.7 mm |

Standard-height channel instead of low-profile would add **20.6 mm** on top of any of these, which
is why low-profile is a requirement and not a preference. Everything here is well inside the
117 mm the doors project.

### Assembly sequence

1. Bolt the two feet back to back, slots aligned, and stand the struts on the outboard legs.
2. Hook the top clamps over the fridge top; stud through washers and the strut slot; nut loose.
3. Slide the lower clamps **up** their slots until they engage under the appliance; lock.
4. Tighten the top nuts. The struts go into tension between the clamps and the fridge is gripped.

### Sliding along the panel — SOLVED by geometry, not friction

Friction alone gives roughly **15–30 lb** of resistance (foot plus preloaded clamps). Enough for
ordinary use, but not positive location.

**Use the clear window instead.** The hinge cover occupies the front 203 mm of the fridge top and
the measured clear window behind it is **406 mm**. Size the top clamp's long leg to very nearly
fill that window and it is captured front-to-back between the hinge cover and the rear edge — a
geometric stop, using a measurement already in hand, needing no extra feature and no second bend.

---

## 3b. The foot, after the gap was measured

**10–20 mm, and not flat.** Two consequences.

### The wedge is the wrong device — use a conforming pad

A wedge bears on unknown high points of an irregular surface, and at the tight end of the range a
0.187 in foot leaves only 5.25 mm for it, which is a fragile shim needing per-location fitting.

**Use a foam pad on top of the tail instead.** It conforms to whatever is up there, which is
precisely the problem, and it needs no fitting. The obvious objection — that foam is a spring and
therefore not a stop — does not survive the arithmetic. The force is small and the area is large:

| pad | thickness | squash under a tip load | screen movement |
|---|---|---|---|
| 60 × 200 mm | 10 mm | 0.37 mm | **2.5 mm** |
| 80 × 250 mm | 10 mm | 0.22 mm | 1.5 mm |

At design loads it barely moves. It behaves as a stop.

### The one real trap is PRELOAD, and it is a big one

Area multiplies pressure. On a 60 × 200 mm pad of the project's 12-psi-at-25 % neoprene:

| compressed | force pushing UP on the fridge |
|---|---|
| 2 % | 18 lb |
| 10 % | 89 lb |
| 25 % | **223 lb — half the appliance** |
| 50 % | 446 lb — you are lifting it |

**Size the pad to JUST TOUCH.** Do not squeeze it in. Fit it by building up layers until contact,
which is acceptable because moving the fridge is a teardown anyway. Half a percent of strain is
0.3 mm of screen movement — the job needs nothing more than contact.

### Foot thickness: go thinner than the hook's

The foot only sees the full moment as a BACKSTOP, so it does not need SF 10.

| | | |
|---|---|---|
| 0.187 in | SF 9.8 | only 5.25 mm of pad room in a 10 mm gap |
| **0.119 in** | **SF 4.0** | **6.98 mm of pad room** |
| 0.075 in | SF 1.6 | too thin |

**0.119 in** is the balance. Threaded jacking screws were considered and rejected: precise and
adjustable, but they bear on a point of an irregular surface, and conformity is worth more here
than adjustability. Keep them in mind only if a genuinely rigid stop is ever wanted.

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
