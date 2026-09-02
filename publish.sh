#!/usr/bin/env bash
# publish.sh — rebuild everything, validate it, and push main + the gh-pages branch GitHub Pages
# serves. gh-pages is a flat tree of the three HTML pages and every SVG they reference, nothing
# else; it is rebuilt from scratch on every publish so nothing stale can survive in it.
#
#   ./publish.sh            build + validate + publish
#   ./publish.sh --check    build + validate only, push nothing
#
# Push goes over the HTTPS remote with the osxkeychain credential helper (gh auth). If you would
# rather push over SSH, `source ~/.ssh_agent_socket` first and switch the remote.
unset TMOUT
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="$ROOT/.venv/bin/python"
cd "$ROOT"

log() { printf '%s INFO  [publish] %s\n' "$(date +%Y-%m-%dT%H:%M:%S%z)" "$*"; }
die() { printf '%s ERROR [publish] %s\n' "$(date +%Y-%m-%dT%H:%M:%S%z)" "$*" >&2; exit 1; }

[ -x "$PY" ] || die ".venv missing — python3 -m venv .venv && .venv/bin/pip install ezdxf gmsh scikit-fem numpy scipy meshio"

log "design 1: generate + audit"
"$PY" generate_bracket.py --log-level WARNING
"$PY" audit_dxf.py --log-level WARNING

log "design 2: parts + sheets (strut/)"
( cd strut && "$PY" generate_parts.py >/dev/null && "$PY" clamp_sheets.py >/dev/null && "$PY" package.py >/dev/null && "$PY" concept_sheet.py >/dev/null )

log "design 3: plate via the root generator, audited, then its sheets"
( cd strut && "$PY" generate_hybrid.py --log-level WARNING && "$PY" hybrid_sketch.py >/dev/null )

log "plate FEA on design 3's plate"
"$PY" plate_fea.py --params strut/dxf/H_hook_plate.json --support magnets struts --thickness 0.119 0.187 --log-level WARNING

log "design 1 studies"
for s in approval_sheet arm_width_sweep assembly_drawing display_compare ergonomics_sweep fastener_matrix force_table harness_view hinge_clearance magnet_pattern_study magnet_primer mount_views orientation_compare pad_explainer spacing_explainer stack_detail thickness_study variant_compare; do
  "$PY" "$s.py" >/dev/null 2>&1 || die "$s.py failed"
done

log "pages"
"$PY" console_build.py --log-level WARNING

# Every SVG the pages reference must exist, or a card is a broken image on the live site.
for page in index.html hook.html clamp.html; do
  grep -oE 'src="[^"?]+\.svg' "$page" | sed 's/src="//' | sort -u | while read -r f; do
    [ -f "$f" ] || die "$page references missing $f"
  done
done
log "validated: every referenced sheet exists"

if [ "${1:-}" = "--check" ]; then
  log "--check: nothing pushed"
  exit 0
fi

[ -z "$(git status --porcelain)" ] || die "working tree not clean — commit first, publish exactly what is in git"

log "push main"
git push origin main

log "assemble gh-pages"
WT="$(mktemp -d)"
trap 'rm -rf "$WT"; git worktree prune' EXIT
git fetch -q origin gh-pages || true
if git show-ref -q refs/remotes/origin/gh-pages; then
  git worktree add -q "$WT" origin/gh-pages
  ( cd "$WT" && git checkout -q -B gh-pages && git rm -rq . )
else
  git worktree add -q --detach "$WT"
  ( cd "$WT" && git checkout -q --orphan gh-pages && git rm -rqf . )
fi
cp index.html hook.html clamp.html archive.html "$WT/"
mkdir -p "$WT/strut/dxf"
cp ./*.svg "$WT/"
cp strut/*.svg "$WT/strut/"
cp strut/dxf/*_preview.svg "$WT/strut/dxf/"
printf 'png/\n' > "$WT/.gitignore"
( cd "$WT" && git add -A && git -c user.name="$(git config user.name)" -c user.email="$(git config user.email)" commit -q -m "Publish $(git -C "$ROOT" rev-parse --short main): $(git -C "$ROOT" log -1 --format=%s main)" && git push -q origin gh-pages )
log "published https://csmarshall.github.io/fridge-display-mount/"
