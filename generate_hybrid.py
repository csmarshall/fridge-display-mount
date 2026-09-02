#!/usr/bin/env python3
"""The third design's cut part: the hook plate with strut holes, made BY THE HOOK GENERATOR.

This repo does not draw the plate. It runs the hook repo's generate_bracket.py twice at this
design's gauge: once plain, to learn where every hole, window and magnet disc is; then with
`--strut-bolts` carrying the rows hybrid.pick_bolt_rows chose from that answer. The generator
validates the rows against its own features and refuses to write if any fouls; then the hook
repo's audit_dxf.py accepts the DXF against the JSON it was written with. Nothing here is a
second home for the hook's geometry.

Outputs, all in dxf/: H_hook_plate.dxf (upload this), H_hook_plate.json (what the audit and the
sheets read), H_hook_plate_preview.svg (reference only, never upload).
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from hybrid import (HOOK_REPO_DEFAULT, PHASES, PLATE_JSON, Hybrid, hook_generator_args,
                    pick_bolt_rows, structural, validate)

LOG = logging.getLogger("hyb")
OUT = Path("dxf")
STEM = "H_hook_plate"


def run_hook_generator(hook_repo: Path, extra: Sequence[str], out_dir: Path, name: str) -> dict:
    """One run of the hook generator into out_dir; returns its params JSON. Raises on refusal."""
    gen = hook_repo / "generate_bracket.py"
    if not gen.exists():
        raise SystemExit(f"hook generator not found at {gen} — pass --hook-repo")
    cmd = [sys.executable, str(gen), *extra, "--out-dir", str(out_dir.resolve()), "--name", name]
    LOG.debug("running: %s", " ".join(cmd))
    res = subprocess.run(cmd, cwd=hook_repo, capture_output=True, text=True)
    for line in res.stdout.splitlines() + res.stderr.splitlines():
        if " ERROR " in line or " WARNING " in line:
            LOG.log(logging.ERROR if " ERROR " in line else logging.WARNING,
                    "hook generator: %s", line.split("] ", 1)[-1])
    if res.returncode != 0:
        raise SystemExit(f"hook generator refused ({res.returncode}) — see above")
    return json.loads((out_dir / f"bracket_params_{name}.json").read_text(encoding="utf-8"))


def run_audit(hook_repo: Path, dxf: Path, expect: Path) -> None:
    cmd = [sys.executable, str(hook_repo / "audit_dxf.py"), "--dxf", str(dxf.resolve()),
           "--expect", str(expect.resolve())]
    res = subprocess.run(cmd, cwd=hook_repo, capture_output=True, text=True)
    tail = (res.stdout + res.stderr).strip().splitlines()[-1] if (res.stdout + res.stderr) else ""
    if res.returncode != 0:
        raise SystemExit(f"audit FAILED: {tail}")
    LOG.info("audit: %s", tail.split("] ", 1)[-1])


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hook-repo", type=Path, default=HOOK_REPO_DEFAULT,
                    help=f"checkout of csmarshall/fridge-display-mount (default {HOOK_REPO_DEFAULT})")
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(message)s")

    h = Hybrid()
    OUT.mkdir(exist_ok=True)
    scratch = OUT / "_hook_ref"
    scratch.mkdir(exist_ok=True)

    # Pass 1: the plain hook at this gauge, for its feature map. Written to a scratch dir that
    # is gitignored; nothing in it is a deliverable.
    ref = run_hook_generator(args.hook_repo, hook_generator_args(h), scratch, "ref")
    rows = pick_bolt_rows(h, ref)
    LOG.info("slot rows inside the plate: %s", [round(r, 1) for r in h.candidate_rows])
    LOG.info("rows chosen (lowest and highest CLEAR, bracketing the VESA): %s",
             [round(r, 2) for r in rows])
    h = Hybrid(bolt_rows=rows)

    # This repo's own checks, BEFORE the second run: bracketing, gauge agreement, both phases.
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
    plate = run_hook_generator(args.hook_repo, hook_generator_args(h) + strut, scratch, "plate")
    for src, dst in (("bracket_flat_plate.dxf", f"{STEM}.dxf"),
                     ("bracket_params_plate.json", f"{STEM}.json"),
                     ("bracket_preview_plate.svg", f"{STEM}_preview.svg")):
        shutil.copyfile(scratch / src, OUT / dst)
    run_audit(args.hook_repo, OUT / f"{STEM}.dxf", OUT / f"{STEM}.json")

    n_strut = sum(1 for x in plate["holes"] if x["tag"] == "strut_bolt")
    LOG.info("dxf/%s.dxf  %.2f x %.0f, 1 bend, %d holes (%d strut) + %d windows",
             STEM, plate["flat"]["height_mm"], plate["flat"]["width_mm"], len(plate["holes"]),
             n_strut, len(plate["windows"]))
    LOG.info("  foot + lower clamp are the clamp design's parts, NOT new — see generate_parts.py")
    assert PLATE_JSON == OUT / f"{STEM}.json"
    return 0


if __name__ == "__main__":
    sys.exit(main())
