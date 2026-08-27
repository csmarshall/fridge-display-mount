# fridge-magnet-mount

Parametric flat-pattern generator and fabrication package for a **magnetic-assisted hook bracket**
that hangs a Waveshare 23.8 in FHD touch monitor on the side panel of a Samsung RS23A500ASR
counter-depth side-by-side refrigerator. The screen runs a household chore list.

Human-crafted and AI-assisted, human-directed: every dimension, constraint and trade-off here was
reviewed and decided by a human; the code was written with AI as a power tool.

## The load path, in one line

The arm reaches over the fridge top and **bears** there — the hook carries all vertical load.
**The magnets carry none.** They resist touch torsion and stop the plate walking. Get that
backwards and none of the rest of this makes sense.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install ezdxf
.venv/bin/python generate_bracket.py      # writes bracket_flat.dxf + preview + params
.venv/bin/python audit_dxf.py             # acceptance test — run after EVERY generation
.venv/bin/python console_build.py         # builds index.html, the working surface
open index.html
```

`generate_bracket.py` **validates before it writes** and exits non-zero having written nothing if
any check fails. That is deliberate: a silently-wrong cut file costs real money.

## What is here

| file | purpose |
|---|---|
| `generate_bracket.py` | the generator. Formed dimensions in, flat pattern out |
| `audit_dxf.py` | independent acceptance test against the written DXF |
| `bracket_flat.dxf` | **the upload file** — mm, layer 0, closed contours, one dashed bend line |
| `bracket_preview.svg` | annotated reference drawing. **Never upload this one** |
| `bracket_params.json` | every derived number, machine-readable |
| `approval_sheet.py` | partner-facing sheet: 3D view, two elevations, plain-language facts |
| `console_build.py` | builds `index.html` — decisions, checklist, numbers, prices, diagrams |
| `render3d.py` | painter's-algorithm projector. NOT a photograph; do not caption it as one |
| `docs/` | brief, price study, vendor reference drawings |
| `CLAUDE.md` | design invariants. Read this before changing anything |

Study scripts (`*_sweep.py`, `*_compare.py`, `*_explainer.py`, `*_study.py`) each answer one
question and write one SVG.

## House rules that bit us

- **No drifting constants.** If a value is derivable, derive it. Hardcoded numbers here have gone
  stale three times — a magnet total, a detach table, a pad rule — each time silently.
- **One home per fact.** The magnet height once appeared as 11.5, 12 and 13 mm on three drawings.
- **CLI flags may only turn things off.** `x = not args.no_x` silently overrode dataclass defaults
  and shipped duplicate holes into a cut file. Three separate bugs of this shape so far.

## Status

Not yet ordered. Four measurements gate it — see the "Before ordering" section of `index.html`.
Prices are dated observations, not derived values; re-verify before ordering.
