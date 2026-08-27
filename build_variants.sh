#!/usr/bin/env bash
# Build, audit and compare the two arm-reach variants of the fridge-side display mount.
# Everything else is identical between them; only the reach across the fridge top differs.
unset TMOUT
set -euo pipefail

PYTHON="${PYTHON:-.venv/bin/python}"
OUT_DIR="${OUT_DIR:-variants}"
ARM_WIDTH=190
MATERIAL="${MATERIAL:-mild-steel}"
THICKNESS="${THICKNESS:-0.119}"

usage() {
    cat <<USAGE
Usage: $0 [-o OUT_DIR] [-h]

  -o OUT_DIR   where to write the variant packages (default: variants)
  -h           this help

Emits, for each variant, a DXF, an annotated preview SVG and a parameter JSON, then runs the
acceptance audit against each. Exits non-zero if any variant fails to generate or audit.
USAGE
}

while getopts ":o:h" opt; do
    case "$opt" in
        o) OUT_DIR="$OPTARG" ;;
        h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

mkdir -p "$OUT_DIR"

# variant name -> "arm reach:neck length" in mm. C trades neck for reach at constant flat length.
VARIANTS="reach130:130:262 reach180:180:262 reach180_neck212:180:212"

for entry in $VARIANTS; do
    name="${entry%%:*}"
    rest="${entry#*:}"
    reach="${rest%%:*}"
    neck="${rest##*:}"
    echo "=== building $name ($MATERIAL ${THICKNESS}in, reach ${reach}, neck ${neck}, arm ${ARM_WIDTH}) ==="
    "$PYTHON" generate_bracket.py \
        --name "$name" \
        --arm-length "$reach" \
        --neck-length "$neck" \
        --neck-width "$ARM_WIDTH" \
        --material "$MATERIAL" --thickness "$THICKNESS" \
        --out-dir "$OUT_DIR"
    "$PYTHON" audit_dxf.py \
        --dxf "$OUT_DIR/bracket_flat_${name}.dxf" \
        --expect "$OUT_DIR/bracket_params_${name}.json"
done

echo
echo "=== comparison ==="
"$PYTHON" - "$OUT_DIR" <<'PY'
import json, sys
from pathlib import Path

out_dir = Path(sys.argv[1])
rows = []
for path in sorted(out_dir.glob("bracket_params_*.json")):
    data = json.loads(path.read_text())
    flat, eng, par = data["flat"], data["engineering"], data["params"]
    rows.append((
        path.stem.replace("bracket_params_", ""),
        par["arm_len"], flat["width_mm"], flat["height_mm"],
        eng["cut_length_mm"], eng["bracket_mass_kg"],
        eng["arm_pad_budget_mm"], par["arm_pad_thickness"] / eng["arm_pad_budget_mm"],
    ))

header = f"{'variant':<10}{'reach':>7}{'flat W':>9}{'flat H':>9}{'cut mm':>9}{'mass kg':>9}{'pad need':>10}{'pad SF':>8}"
print(header)
print("-" * len(header))
for name, reach, w, h, cut, mass, budget, sf in rows:
    print(f"{name:<10}{reach:>7.0f}{w:>9.1f}{h:>9.1f}{cut:>9.0f}{mass:>9.2f}{budget:>10.2f}{sf:>8.2f}")
print()
print("Upload both DXFs to SendCutSend's instant quote. Bounding box differs only in length,")
print("so the price delta is the extra sheet the longer reach consumes.")
PY
