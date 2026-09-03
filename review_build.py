#!/usr/bin/env python3
"""review.html — the page for an outside engineer to review the four designs.

Not the working console (index/hook/clamp.html, which carry every sheet and every decision). This
is a guided read: the problem, the four designs in increasing order of maturity and stiffness,
about sixteen curated sheets with captions, the revision history, the money, and the questions we
would like answered — each with a link that opens a GitHub issue on this repo.

Everything numeric is read from the generators' outputs (bracket_params.json, the hybrid plate's
JSON, prices.py, angle/dxf/D4_params.json) so the page cannot drift from the drawings. The revision
timeline is a curated list of commit hashes whose date and subject come from git at build time.
"""
from __future__ import annotations

import argparse
import html
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence
from urllib.parse import quote

from bracket_common import LOG_LEVELS, configure_logging

LOG = logging.getLogger("review")
REPO = "csmarshall/fridge-display-mount"
SITE = "https://csmarshall.github.io/fridge-display-mount/"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def issue_link(title: str, body: str) -> str:
    return (f"https://github.com/{REPO}/issues/new?title={quote(title)}&body={quote(body)}"
            f"&labels={quote('review')}")


# Milestones, by hash. Date and subject are read from git so the list cannot go stale in wording.
MILESTONES = [
    ("51bb87e", "Design 1 starts: parametric hook generator, validate-then-write"),
    ("d73bb32", "Design 1 settles on 0.187 in steel; first live SendCutSend quote"),
    ("9267a4a", "Fastener study: all 39 nut / washer / locker permutations"),
    ("801f77f", "Design 2 starts: floor-standing slotted strut"),
    ("774dd09", "Design 2: clamps top and bottom; magnets stop being structural"),
    ("067507b", "Design 2: nested struts, screen 52 mm off the fridge"),
    ("e63c0e4", "Design 2 quoted: $346 in parts against the hook's $197"),
    ("67228cf", "Design 3 starts: the hook plate prepared to take struts"),
    ("6b52a8b", "Design 3: the plate is the hook generator's output, two bolt rows, 5 ft struts"),
    ("b04ec07", "Plate finite-element check agrees with the strip model to ~15%"),
    ("232131d", "One repo: the strut work merged in with history"),
    ("55a71f7", "One price table builds every quote"),
    ("6b4a56a", "Magnet right-sizing study; a stock-aluminium design 4, later rejected"),
]


def git_line(h: str) -> tuple[str, str, str]:
    out = subprocess.run(["git", "log", "-1", "--format=%ad%x09%h%x09%s", "--date=short", h],
                         capture_output=True, text=True).stdout.strip()
    d, hh, s = out.split("\t", 2)
    return d, hh, s


def load_numbers(root: Path) -> dict:
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "strut"))
    sys.path.insert(0, str(root / "angle"))
    import prices as PR
    import hybrid as HY
    from angle import Angle
    from concept_sheet import Assembly
    hook = json.loads((root / "bracket_params.json").read_text(encoding="utf-8"))
    plate3 = json.loads((root / "strut" / "dxf" / "H_hook_plate.json").read_text(encoding="utf-8"))
    h3 = HY.Hybrid(**dict(HY.Hybrid.fields_from_hook(plate3), bolt_rows=tuple(plate3["params"]["strut_bolt_rows"])))
    s3 = {ph: HY.structural(h3, ph, plate3["engineering"]["plate_mass_kg"]) for ph in HY.PHASES}
    quotes = {q.design: q for q in PR.all_quotes()}
    return dict(PR=PR, hook=hook, plate3=plate3, h3=h3, s3=s3, quotes=quotes, a4=Angle(),
                a2=Assembly())


CSS = """
:root{--ink:#111;--muted:#5b6166;--rule:#d0d4d8;--paper:#f7f8fa;--card:#fff;
 --d1:#1b6ea8;--d2:#c8791a;--d3:#0b7a4b;--d4:#6b3fa0}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);
 font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
header{background:#fff;border-bottom:1px solid var(--rule);padding:18px 28px}
header h1{margin:0;font-size:22px}header .sub{color:var(--muted);font-size:13px}
nav a{margin-right:14px;font-size:13px;color:var(--d1);text-decoration:none}
main{max-width:1180px;margin:0 auto;padding:24px 28px 80px}
section{margin:36px 0}h2{font-size:20px;margin:0 0 4px}h3{font-size:16px;margin:22px 0 6px}
p.blurb{color:var(--muted);margin:0 0 14px}
.design{border:1px solid var(--rule);border-radius:10px;background:var(--card);padding:18px 22px;margin:18px 0}
.design h2{display:flex;align-items:center;gap:10px}
.tag{font-size:11px;font-weight:700;letter-spacing:.04em;padding:3px 8px;border-radius:999px;color:#fff}
.t1{background:var(--d1)}.t2{background:var(--d2)}.t3{background:var(--d3)}.t4{background:var(--d4)}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0 14px}
td,th{padding:6px 8px;border-bottom:1px solid var(--rule);text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
td.v{font-weight:700}td:first-child{width:20%;color:var(--muted)}td.v{width:38%}
figure{margin:16px 0;border:1px solid var(--rule);border-radius:8px;background:#fff;overflow:hidden}
figcaption{padding:10px 14px;font-size:13.5px;border-bottom:1px solid var(--rule)}
figcaption b{display:block;font-size:14px}figcaption span{color:var(--muted)}
figure img{display:block;width:100%;height:auto}
.ask{background:#fff8e6;border:1px solid #f0d58a;border-radius:8px;padding:12px 16px;margin:14px 0}
.ask ul{margin:6px 0 0 18px}.ask a{color:var(--d1)}
.btn{display:inline-block;padding:7px 12px;border-radius:6px;background:var(--d1);color:#fff;
 text-decoration:none;font-weight:600;font-size:13px}
.tl{list-style:none;padding:0;margin:0}.tl li{padding:6px 0;border-bottom:1px dashed var(--rule);font-size:14px}
.tl code{color:var(--muted);font-size:12px;margin-right:8px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.foot{color:var(--muted);font-size:12.5px;margin-top:40px}
"""


def fig(root: Path, rel: str, title: str, caption: str) -> str:
    p = root / rel
    mt = int(p.stat().st_mtime) if p.exists() else 0
    return (f'<figure><figcaption><b>{esc(title)}</b><span>{esc(caption)}</span> '
            f'<a href="{esc(rel)}" target="_blank" rel="noopener">open ↗</a></figcaption>'
            f'<a href="{esc(rel)}" target="_blank" rel="noopener"><img src="{esc(rel)}?v={mt}" loading="lazy" alt="{esc(title)}"></a></figure>')


def table(rows: list[tuple[str, str, str]]) -> str:
    body = "".join(f"<tr><td>{esc(k)}</td><td class='v'>{esc(v)}</td><td>{esc(n)}</td></tr>" for k, v, n in rows)
    return f"<table><thead><tr><th></th><th>value</th><th>note</th></tr></thead><tbody>{body}</tbody></table>"


def ask(design: int, questions: list[str]) -> str:
    items = "".join(f"<li>{esc(q)}</li>" for q in questions)
    link = issue_link(f"Review, design {design}: ", f"Design {design} — see {SITE}review.html\n\n")
    return (f'<div class="ask"><b>What we would like your view on</b><ul>{items}</ul>'
            f'<p style="margin:10px 0 0"><a class="btn" href="{esc(link)}" target="_blank" rel="noopener">'
            f'Comment on design {design} (opens a GitHub issue)</a></p></div>')


def build(root: Path, out: Path) -> int:
    N = load_numbers(root)
    PR, hook, plate3, h3, s3, Q, a4, a2 = (N[k] for k in ("PR", "hook", "plate3", "h3", "s3", "quotes", "a4", "a2"))
    rep = hook["engineering"]
    q = Q

    body = []
    # ---------------------------------------------------------------- the problem
    body.append(f"""<section id="problem"><h2>The problem</h2>
<p class="blurb">A 23.8 in touch monitor on the side of a counter-depth fridge, at standing height, for a
household chore board. Nothing may be fixed to the building or the appliance; it has to come off
leaving no mark.</p>
{table([
    ("Display", "Waveshare 23.8 in FHD touch, 555 x 325 x 18 mm panel + 25 mm rear box, 3.94 kg", "VESA 100 on the rear box; Pi 5 fan in the box face"),
    ("Fridge", "Samsung RS23A500ASR, case 1743 mm tall, 610 mm deep (counter-depth)", "top and sides measured MAGNETIC; hinge covers stand 36.5 mm proud of the top"),
    ("Orientation", "portrait", "a 555 mm landscape display nearly fills a 610 mm panel"),
    ("Screen centre", f"{rep['screen_centre_height_mm']:.0f} mm above the floor", "chosen for a 5 ft 1 in to 6 ft 4 in household"),
    ("Governing everyday load", "a 5 lb press at the outer screen edge", f"a torsion of {rep['torsion_moment_in_lbf']:.0f} in-lb about the mount"),
    ("Rules that bind every design", "nothing fixed to the building; magnets carry no weight; foam between any steel and the panel; pad thickness matches the magnet standoff", "CLAUDE.md sections 1 and 9"),
])}
<p>Three designs are up for review, in <b>increasing order of maturity and stiffness</b>: design 1 is finished but
has no fallback, design 2 stands alone on the floor, and design 3 is design 1 with a fallback built in and is what we
intend to order. A fourth, the hook rebuilt from stock aluminium and hand-drilled, was worked up and rejected by the
owner; its magnet study survives below.</p>
{fig(root, "magnet_primer.svg", "Why not just magnets?", "The derate chain: a magnet's rated pull delivers a small fraction as shear on painted appliance sheet. This is why every design carries the weight some other way.")}
</section>""")

    # ---------------------------------------------------------------- design 1
    body.append(f"""<section id="d1" class="design"><h2><span class="tag t1">DESIGN 1</span> The hook — one bent plate, held flat by magnets</h2>
<p class="blurb">An arm reaches 180 mm over the fridge top and bears there, carrying the entire weight into the
top corner. A neck drops down the side to a 310 x 310 mm body carrying the VESA and eight O32 K&J pot
magnets that hold the plate flat. 0.187 in A36 steel, laser cut and bent, powder coated. Finished, audited
and quoted; no fallback if it proves too lively.</p>
{table([
    ("Hanging on the hook", f"{rep['total_hanging_lbf']:.1f} lb", "display + steel + magnets + foam"),
    ("Neck bending", f"{rep['neck_stress_psi']:.0f} psi, SF {rep['neck_sf']:.0f}x", "on 36,000 psi yield"),
    ("Touch torsion per magnet", f"{rep['torsion_force_per_magnet_lbf']:.2f} lb", f"MM-C-32 derated {rep['magnet_derated_pull_lbf']:.1f} lb: SF {rep['magnet_tension_sf']:.0f}x"),
    ("Peel", f"{rep['peel_lbf']:.2f} lb", f"CG {rep['cg_offset_mm']:.1f} mm off the panel over {rep['peel_lever_mm']:.0f} mm"),
    ("Flat pattern", f"{hook['flat']['width_mm']:.0f} x {hook['flat']['height_mm']:.1f} mm, 1 bend", "the bend deduction is SendCutSend's published figure"),
    ("Parts", f"${q[1].priced:.2f} priced, {q[1].unpriced} not", f"budget-sourced ${PR.budget(q[1]).priced:.2f}"),
])}
{fig(root, "approval_sheet.svg", "Approval sheet — the hook in place", "Front elevation, side elevation and a shaded projection. The projection is a painter's-algorithm render, not a photograph.")}
{fig(root, "mount_views.svg", "Both faces of the mount", "Magnets and foam on the fridge face; VESA and spacers on the display face.")}
{fig(root, "hinge_clearance.svg", "Hinge cover clearance", "Where the arm lands on the fridge top relative to the hinge cover. Two readings of the cover exist and the second puts the arm touching it — an open measurement.")}
{fig(root, "bracket_preview.svg", "The flat pattern", "The cut file annotated: every hole, window, slot and the single bend line.")}
{fig(root, "magnet_economics.svg", "Magnet economics — hold against cost", "Every type at every count the plate takes, on one hold model; the dashed lines are 2x, 4x and 6x on a 20 lb grab of the bottom edge.")}
{fig(root, "magnet_sizing.svg", "Right-sizing the magnets", "What one magnet actually holds against a ladder of smaller male-stud magnets, and what a smaller one changes: pad, stud, holes. The O48 stays; this is why.")}
{ask(1, [
    "The arm bears the whole load on an 11.5 mm closed-cell foam pad over a corner of unknown radius. Would you want a stiffer bearing, or is the foam the right thing between steel and painted sheet?",
    "Eight O32 magnets read 16x on the touch case and 6.3x on a 20 lb pull of the bottom edge, chosen from the economics chart. Right margin for a household display, or would you spend the $35 for the O36s?",
    "Anything you would change in the plate before it is cut: the vent windows, the 0.187 in gauge, the powder coat?",
])}
</section>""")

    # ---------------------------------------------------------------- design 2
    body.append(f"""<section id="d2" class="design"><h2><span class="tag t2">DESIGN 2</span> The clamped strut — floor-standing</h2>
<p class="blurb">Two low-profile slotted struts stand on the floor through an outboard foot and run up the side
panel; identical L brackets clamp them to the fridge's top and to its underside; a small plate across the
struts carries the display. The floor takes the weight, the clamps hold it in, no magnets. Height-adjustable
after the fact; nothing depends on the fridge top's geometry. Fully drawn, quoted; its foot and lower clamp
are also design 3's fallback kit.</p>
{table([
    ("Load path", "display → plate → struts → foot → floor", "compression into the floor"),
    ("Strut spacing", f"{a2.strut_spacing:.2f} mm", "the display box nests BETWEEN the struts"),
    ("Display face off the panel", f"{a2.display_face:.1f} mm", "nested: the strut is beside the box, not behind it"),
    ("Anti-tip", "a clamp, not the magnets", "the lower clamp captures the tail under the fridge; snug, never preloaded"),
    ("Parts", f"${q[2].priced:.2f} priced, {q[2].unpriced} not", f"budget-sourced ${PR.budget(q[2]).priced:.2f}"),
])}
{fig(root, "strut/clamp_real.svg", "What it will look like", "Realistic elevation, true scale, with people at 5 ft 1 and 6 ft 5 and their eye lines.")}
{fig(root, "strut/clamp_dims.svg", "The mount, dimensioned", "Front and side elevations with tagged lengths, the plate's hole pattern, and all four display options.")}
{fig(root, "strut/clamp_loadpath.svg", "Where the weight goes", "Down the strut, into the foot, into the floor. The clamps carry nothing.")}
{fig(root, "strut/clamp_stack.svg", "The stack, panel to screen", "Section through a strut and through the box; the two are not the same.")}
{ask(2, [
    "The lower clamp reaches under a fridge with a 10 to 20 mm, non-flat underside and captures the tail with a foam pad that must not be preloaded. Does that read as a positive stop to you, or as something that will get wedged tight the first time it rattles?",
    "The plate is bolted to the struts through their slots with elevator bolts, nuts inside the channel. Anything you would change in that joint?",
    "Two 5 ft struts standing on a kitchen floor next to a fridge: is this a thing you would want in your own kitchen?",
])}
</section>""")

    # ---------------------------------------------------------------- design 3
    rows3 = sorted(h3.bolt_rows)
    body.append(f"""<section id="d3" class="design"><h2><span class="tag t3">DESIGN 3</span> The hook, with the plate prepared for struts — being ordered</h2>
<p class="blurb">Design 1's plate, cut at 0.119 in instead of 0.187, with four extra holes in two rows near the
bottom edge. Phase 1 is the hook with four body magnets. If that proves too lively in use, phase 2 bolts two
5 ft struts through those holes onto design 2's feet and lower clamp, and the magnets come off. The plate is
cut once for both. Generated by the same generator as design 1, audited, and checked by a plate
finite-element model.</p>
{table([
    ("Plate", f"{plate3['flat']['width_mm']:.0f} x {plate3['flat']['height_mm']:.2f} mm, 0.119 in, {len(plate3['holes'])} holes", "design 1's hole set plus four strut bolts"),
    ("Strut bolt rows", f"{rows3[0]:.1f} and {rows3[-1]:.1f} mm above the bottom edge", "picked to bracket the VESA and clear every magnet face and window"),
    ("Phase 1, on magnets", f"neck SF {s3['magnets'].neck_sf:.0f}x, body SF {s3['magnets'].body_sf:.0f}x, screen edge {s3['magnets'].screen_edge_mm:.3f} mm", "FEA: 0.065 mm under a 5 lb press"),
    ("Phase 2, on struts", f"neck SF {s3['struts'].neck_sf:.0f}x, body SF {s3['struts'].body_sf:.0f}x, screen edge {s3['struts'].screen_edge_mm:.3f} mm", "FEA: 0.036 mm; the plate is a beam between the bolt rows"),
    ("Standoff", f"magnets {h3.magnet_standoff:.2f} mm, struts {h3.strut_standoff:.2f} mm", "the magnets come OFF when the struts go on"),
    ("Parts", f"phase 1 ${PR.phase(q[3], 1):.2f}, kit ${PR.phase(q[3], 2):.2f}", f"budget-sourced ${PR.phase(PR.budget(q[3]), 1):.2f} + ${PR.phase(PR.budget(q[3]), 2):.2f}; the plate quote needs re-taking"),
])}
{fig(root, "strut/hybrid_overview.svg", "The whole design, by purchase phase", "Blue is bought now; amber only if the arm is too lively. The two red lines are the bolt rows.")}
{fig(root, "strut/hybrid_sketch.svg", "If the hook needs help — the bottom end", "The feet and lower clamp under the plate. A sketch, not a fabrication drawing.")}
{fig(root, "strut/dxf/H_hook_plate_preview.svg", "The plate as cut", "The generator's own preview of the upload file.")}
{fig(root, "plate_fea.svg", "Plate bending under a touch — finite elements vs the strip model", "Kirchhoff plate on the real cut geometry, both gauges, pinned on magnets and on strut bolts.")}
{ask(3, [
    "Thinning the plate from 0.187 to 0.119 in: the strip model and the FEA both say it is fine (0.065 mm at the screen edge). Do you agree, and would you want the thicker gauge anyway?",
    "Phase 2 hangs the plate on two bolt rows 203 mm apart with the arm still over the top and the magnets removed. Is there a failure mode in that hybrid state we have not modelled?",
    "The four arm magnets are cut for but not bought. Is anti-walk on a foam pad under compressor vibration a real risk over years, or not?",
])}
</section>""")

    # ---------------------------------------------------------------- money + revisions
    body.append(f"""<section id="money"><h2>What each costs</h2>
<p class="blurb">Dated vendor observations from one price table, never derived. Display and PSU excluded; they are
the same purchase whichever design wins.</p>
{fig(root, "quotes.svg", "Three quotes from one price table", "As listed, and budget-sourced with the substitutions shown and their caveats.")}
{fig(root, "vendors.svg", "Comparison shop", "The same plate file quoted at SendCutSend, OSH Cut and Fabworks on the same day. Only the first two can bend from a DXF.")}
</section>
<section id="revisions"><h2>Revisions</h2>
<p class="blurb">Milestones, from the repository history. {len(MILESTONES)} of {subprocess.run(['git', 'rev-list', '--count', 'HEAD'], capture_output=True, text=True).stdout.strip()} commits.</p>
<ul class="tl">{"".join(f"<li><code>{esc(d)} {esc(hh)}</code>{esc(label)} <span style='color:var(--muted)'>— {esc(s)}</span></li>" for (h, label) in MILESTONES for (d, hh, s) in [git_line(h)])}</ul>
</section>
<section id="how"><h2>How to comment</h2>
<p>Each design has a button that opens a GitHub issue with the design in the title. Anything else:
<a class="btn" href="{esc(issue_link('Review: ', f'See {SITE}review.html' + chr(10) + chr(10)))}" target="_blank" rel="noopener">open a general issue</a>.
The full working pages, with every sheet and every decision, are <a href="index.html">design 3</a>,
<a href="hook.html">design 1</a> and <a href="clamp.html">design 2</a>. The generators, cut files and this page's
source are in <a href="https://github.com/{REPO}">the repository</a>.</p>
<p class="foot">Human-crafted and AI-assisted, human-directed: every dimension, constraint and trade-off was reviewed and decided by a person; the code was written with AI as a power tool. Built {time.strftime('%d %b %Y %H:%M')}.</p>
</section>""")

    nav = " ".join(f'<a href="#{i}">{esc(l)}</a>' for i, l in (
        ("problem", "The problem"), ("d1", "Design 1"), ("d2", "Design 2"),
        ("d3", "Design 3 (proposed)"), ("money", "Costs"), ("revisions", "Revisions"), ("how", "How to comment")))
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fridge display mount — engineering review</title><style>{CSS}</style></head><body>
<header><h1>Fridge-side display mount — for review</h1>
<div class="sub">Three ways to hang a 24 in touch screen on the side of a fridge, none of them fixed to anything. Read top to bottom; the last design is the one we intend to build.</div>
<nav style="margin-top:8px">{nav}</nav></header>
<main>{"".join(body)}</main></body></html>
"""
    out.write_text(doc, encoding="utf-8")
    LOG.info("Wrote %s", out)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, default=Path("review.html"))
    ap.add_argument("--log-level", choices=LOG_LEVELS, default="INFO")
    a = ap.parse_args(argv)
    configure_logging(a.log_level)
    return build(a.root, a.out)


if __name__ == "__main__":
    sys.exit(main())
