# Low-Profile Strut Channel — McMaster-Carr

Captured from the McMaster listing 2026-08-29. Their product page is a JavaScript app that
renders nothing to a bot, so a PDF of it is a blank shell — this transcription is the reference.

## The chosen part

**3310T791 — Black Powder-Coated Steel, slotted hole**

Black matters twice over: it matches the fridge's own side panel, and it matches the textured
black powder coat chosen for the steel parts.

| | |
|---|---|
| Height (depth off the panel) | **13/16 in = 20.64 mm** |
| Width (the slotted face) | **1 5/8 in = 41.28 mm** |
| Inside channel width | 7/8 in = 22.23 mm |
| Wall thickness | **0.07 in = 1.78 mm** |
| Slot | 1 1/8 in long × 9/16 in wide |

McMaster's own caveat, worth keeping in front of you: *"Low-profile is channel not as strong as
standard, but it's the same width, so it fits most of the accessories we offer."*

### Prices by length

| 1 ft | 1.5 ft | 2 ft | 3 ft | 4 ft | 5 ft | 6 ft | 80 in | 8 ft | 10 ft |
|---|---|---|---|---|---|---|---|---|---|
| $6.37 | $9.55 | $12.74 | $19.11 | $25.48 | $30.26 | **$34.40** | $38.86 | $45.86 | $54.15 |

Two 6 ft lengths = **$68.80**.

## The rest of the range, same dimensions

| Material | Wall | Part | 6 ft |
|---|---|---|---|
| Zinc-Plated Steel | 0.08" | 3310T513 | $43.79 |
| **Black Powder-Coated Steel** | **0.07"** | **3310T791** | **$34.40** |
| Green Powder-Coated Steel | 0.07" | 3310T515 | $34.40 |
| White Powder-Coated Steel | 0.07" | 3310T488 | $39.26 |
| Yellow Powder-Coated Steel | 0.07" | 3310T777 | $92.16 |
| Galvanized Steel | 0.08" | 3310T517 | $33.75 |
| 304 Stainless Steel | 0.08" | 33085T93 | $84.73 |
| 316 Stainless Steel | 0.08" | 33085T94 | $116.91 |
| Aluminum | 0.06" | 3230T36 | $30.73 |
| Primed Steel | 0.08" | 3310T514 | $79.59 |

Note the powder-coated and aluminium options are **thinner** than the plated/stainless ones
(0.07 and 0.06 vs 0.08 in). If the section properties ever get re-derived, the finish changes them.

## Section properties — DERIVED, not published

McMaster do not publish I or Z for this profile. These were computed from the dimensions above
with an **estimated 6 mm return lip**, so they carry that estimate's error. Recompute if the lip
is ever measured on the real part.

Bending about the axis that resists a push away from the panel (the weak direction, because the
flat back must face the fridge for the magnets to bear on it):

| | |
|---|---|
| Area | 162 mm² |
| I | **9,334 mm⁴** |
| Z | **719 mm³** |
| Mass | 1.27 kg/m → 2.32 kg per 6 ft length |

## Why the orientation is forced

The flat back must face the fridge: it is the only surface that can bear a Ø48 magnet, and the
magnet's 5/16"-18 stud passes through the 1.78 mm web into a channel nut inside. Turn the channel
90° and only an edge touches the appliance.

That forces the **weak** bending axis into the pull direction. It does not matter, because the
magnets carry that load rather than the strut — but it is why the sway numbers look poor if you
ever analyse the strut as an unpropped cantilever.
