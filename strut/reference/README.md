# reference/

Everything here is EVIDENCE, not opinion. If a number in the design contradicts something in this
directory, the file wins until someone re-verifies it.

## The appliance

(The Samsung spec sheet and both Waveshare dimension drawings now live once, in
`../../docs/reference/`; the copies that used to be here were byte-identical and were removed on
the 2026-09-02 merge.)

- **`samsung-RS23A500ASR-specsheet.pdf`** — the fridge. Case 35 7/8 × 68 5/8 × 24 in
  (911.2 × **1743.1** × **609.6 mm**), 229 lb, counter-depth. The height that matters is the CASE
  height, not the height over the hinge covers.

## The display

- **`waveshare-23.8-dimension-drawing.jpg`** — the one being mounted. 555.23 × 324.65 × 18 mm
  panel, plus a **25 mm raised rear box** (260 × 134, centred) carrying the VESA 100 pattern, so
  overall depth is 43 mm. 3.94 kg. The Pi 5 fan/GPIO opening is in the rear box FACE at a
  **~82 mm radius** (fan, ~30 dia) and **~107 mm** (GPIO slot), both SCALED off the drawing;
  the hook's windows sit at 87.5, an average — do not blank either off.
- **`waveshare-27-dimension-drawing.jpg`** — the 27 in shares the same rear box, VESA and depth
  profile. Only the panel size and mass differ (629.62 × 367.40, 4.92 kg).

## The strut

- **`strut-channel-3310T791.md`** — the chosen channel, transcribed from McMaster because their
  page renders nothing to a bot. Dimensions, the whole price ladder, and **derived** section
  properties with the assumption that produced them stated.

## The fabricator

- **`sendcutsend-mild-steel.pdf`** — material and thickness range.
- **`sendcutsend-bending-guidelines.pdf`** — bend radius, minimum flange, die width, feature
  keep-out from the bend line. The bent foot lives or dies by this document.
- **`sendcutsend-powder-coating.pdf`** — the 15 colours and the part-size limits. **Textured
  Black** was chosen for the previous design because the fridge's side panel is dark and matte.

## Inherited from the hook design — the reasoning, not the geometry

These four carry work that stays true regardless of load path.

- **`inherited-magnet_primer.pdf`** — why a 175 lb magnet delivers 12 lb where it counts. Pull vs
  shear vs peel, the derate chain, and the arithmetic for what magnet-only would actually need.
  **Read this before resizing the magnets.**
- **`inherited-fastener_matrix.pdf`** — all 39 nut × washer × threadlocker permutations against a
  fixed 1/2 in stud, with part numbers. If the magnet changes, the stud may change and this whole
  sheet has to be recomputed — but the METHOD transfers directly.
- **`inherited-bracket_preview.pdf`** — the plate as built: 310 × 310, VESA 100 plus MIS-E/MIS-F
  spare patterns, vent windows on an 87.5 mm radius, cable slots, magnet holes at 246 mm.
- **`inherited-channel_concept.pdf`** — the concept sheet that led to this project, including the
  wedge arithmetic and the numbers the strut design starts from.
- **`inherited-price-study.md`** — the material/thickness price ladder, and why 0.187 in mild
  steel beat aluminium and stainless.
- **`inherited-hook-BOM.md`** — the previous BOM, with sourced part numbers for magnets, nuts,
  washers, threadlocker and foam. Several lines transfer unchanged; the magnet line is the one
  deliberately being revisited.
