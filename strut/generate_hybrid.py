#!/usr/bin/env python3
"""The third design's cut part: the hook plate with strut holes, made BY THE HOOK GENERATOR.

This directory does not draw the plate. It calls the project's generate_bracket.py twice at this
design's gauge: once plain, to learn where every hole, window and magnet disc is; then with
`--strut-bolts` carrying the rows hybrid.pick_bolt_rows chose from that answer. The generator
validates the rows against its own features and refuses to write if any fouls; then audit_dxf.py
accepts the DXF against the JSON it was written with. Nothing here is a second home for the
hook's geometry.

Run from strut/. Outputs, all in dxf/: H_hook_plate.dxf (upload this), H_hook_plate.json (what
the audit and the sheets read), H_hook_plate_preview.svg (reference only, never upload).
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audit_dxf                      # noqa: E402  (shared, one level up)
import generate_bracket               # noqa: E402
from hybrid import (PHASES, PLATE_JSON, Hybrid, hook_generator_args,   # noqa: E402
                    pick_bolt_rows, structural, validate)

LOG = logging.getLogger("hyb")
OUT = Path("dxf")
STEM = "H_hook_plate"


def run_hook_generator(extra: Sequence[str], out_dir: Path, name: str) -> dict:
    """One in-process run of the hook generator into out_dir; returns its params JSON."""
    argv = [*extra, "--out-dir", str(out_dir.resolve()), "--name", name]
    LOG.debug("generate_bracket %s", " ".join(argv))
    if generate_bracket.main(argv) != 0:
        raise SystemExit("hook generator refused — see its errors above")
    return json.loads((out_dir / f"bracket_params_{name}.json").read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(message)s")

    h = Hybrid()
    OUT.mkdir(exist_ok=True)
    # pass 1 below also tells us which magnet the hook carries; h is rebuilt from it before validating
    scratch = OUT / "_hook_ref"
    scratch.mkdir(exist_ok=True)

    # Pass 1: the plain hook at this gauge, for its feature map. Scratch dir, gitignored.
    ref = run_hook_generator(hook_generator_args(h), scratch, "ref")
    h = Hybrid(**Hybrid.fields_from_hook(ref))
    rows = pick_bolt_rows(h, ref)
    LOG.info("slot rows inside the plate: %s", [round(r, 1) for r in h.candidate_rows])
    LOG.info("rows chosen (lowest and highest CLEAR, bracketing the VESA): %s",
             [round(r, 2) for r in rows])
    h = Hybrid(**dict(Hybrid.fields_from_hook(ref), bolt_rows=rows))

    # This design's own checks, BEFORE the second run: bracketing, gauge agreement, both phases.
    issues = validate(h, ref)
    for sev, tag, msg in issues:
        LOG.log(logging.ERROR if sev == "ERROR" else logging.WARNING, "%s %s: %s", sev, tag, msg)
    if any(sev == "ERROR" for sev, _, _ in issues):
        LOG.error("%d error(s) — nothing written", sum(sev == "ERROR" for sev, _, _ in issues))
        return 1
    for phase in PHASES:
        s = structural(h, phase, ref["engineering"]["plate_mass_kg"])
        LOG.info("  %-8s standoff %.2f, hangs %.1f lb, neck SF %.1fx, body SF %.1fx, "
                 "screen edge %.3f mm (%s)", phase, s.standoff, s.hanging_lbf, s.neck_sf,
                 s.body_sf, s.screen_edge_mm, s.model)

    # Pass 2: the plate with the strut rows. The generator re-validates every row against its
    # features and exits non-zero having written nothing if one fouls.
    strut = ["--strut-bolts", f"{h.strut_spacing:.4f}", *(f"{r:.4f}" for r in rows)]
    plate = run_hook_generator(hook_generator_args(h) + strut, scratch, "plate")
    for src, dst in (("bracket_flat_plate.dxf", f"{STEM}.dxf"),
                     ("bracket_params_plate.json", f"{STEM}.json"),
                     ("bracket_preview_plate.svg", f"{STEM}_preview.svg")):
        shutil.copyfile(scratch / src, OUT / dst)
    if audit_dxf.main(["--dxf", str(OUT / f"{STEM}.dxf"), "--expect", str(OUT / f"{STEM}.json")]) != 0:
        raise SystemExit("audit FAILED — see above")

    n_strut = sum(1 for x in plate["holes"] if x["tag"] == "strut_bolt")
    LOG.info("dxf/%s.dxf  %.2f x %.0f, 1 bend, %d holes (%d strut) + %d windows — audited",
             STEM, plate["flat"]["height_mm"], plate["flat"]["width_mm"], len(plate["holes"]),
             n_strut, len(plate["windows"]))
    LOG.info("  foot + lower clamp are the clamp design's parts, NOT new — see generate_parts.py")
    assert PLATE_JSON == OUT / f"{STEM}.json"
    return 0


if __name__ == "__main__":
    sys.exit(main())
