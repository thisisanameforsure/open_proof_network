#!/usr/bin/env bash
# The devcontainer's post-create command (F10-R6; D-27). Runs once, inside the published gate
# image, after the graph is checked out at $GRAPH (the workspace folder).
#
#   GRAPH=<graph checkout> NETWORK=/opt/opn/network gate/devcontainer/post-create.sh
#
# What it does: prove the toolchain, the metaprograms and the gate's Python environment are all
# present and runnable without a build; then fetch the graph's olean cache when the target's
# gate-spec.json names one (F10-R7; a null olean_cache_url means there is nothing to fetch, and a
# miss is not an error — the first pregate.sh builds instead, C7). It never installs anything:
# the image is the pin (D-4 step 1, F10-Q1).
set -euo pipefail

NETWORK="${NETWORK:-/opt/opn/network}"
GRAPH="${GRAPH:-$PWD}"
export NETWORK GRAPH
export UV_CACHE_DIR="${UV_CACHE_DIR:-${HOME:-/tmp}/.cache/uv}"

echo "post-create: network $NETWORK, graph $GRAPH"
elan_home="${OPN_ELAN_HOME:-/opt/elan}"
"$elan_home/bin/elan" --version
for spec in "$GRAPH"/targets/*/gate-spec.json; do
  [ -f "$spec" ] || { echo "post-create: no targets/*/gate-spec.json under $GRAPH"; exit 1; }
  toolchain="$(uv run --frozen --project "$NETWORK" python -c 'import json,sys; print(json.load(open(sys.argv[1]))["lean_toolchain"])' "$spec")"
  echo "post-create: $(basename "$(dirname "$spec")") pins $toolchain: $("$elan_home/bin/elan" run "$toolchain" lean --version)"
done
# F11-R6: a Mathlib-pinned target's checkout is in the image, at the sha the spec names.
for spec in "$GRAPH"/targets/*/gate-spec.json; do
  sha="$(uv run --frozen --project "$NETWORK" python -c 'import json,sys; print(json.load(open(sys.argv[1]))["mathlib_sha"] or "")' "$spec")"
  [ -n "$sha" ] || continue
  home="${OPN_MATHLIB_HOME:-/opt/opn/mathlib}"
  if [ "$(cat "$home/$sha/MATHLIB_SHA" 2>/dev/null)" = "$sha" ] && [ -d "$home/$sha/.lake/build/lib/lean" ]; then
    echo "post-create: $(basename "$(dirname "$spec")") pins Mathlib $sha: present in the image"
  else
    echo "post-create: $(basename "$(dirname "$spec")") pins Mathlib $sha but the image lacks it; pin an image built for it (gate/tools/pin_image.py --check --verify)"; exit 1
  fi
done
test -x "${OPN_LEAN_PKG_BIN:-/opt/opn/lean/.lake/build/bin}/opn-hazards"
echo "post-create: metaprograms present in ${OPN_LEAN_PKG_BIN:-/opt/opn/lean/.lake/build/bin}"
PYTHONPATH="$NETWORK/gate" uv run --frozen --project "$NETWORK" python -m opn_gate.cli --help >/dev/null
echo "post-create: opn-gate runs ($(uv run --frozen --project "$NETWORK" python --version))"

# F10-R7: the olean cache, when the graph names one. Absent, the first pregate.sh builds.
for spec in "$GRAPH"/targets/*/gate-spec.json; do
  target="$(basename "$(dirname "$spec")")"
  url="$(uv run --frozen --project "$NETWORK" python -c 'import json,sys; print(json.load(open(sys.argv[1]))["olean_cache_url"] or "")' "$spec")"
  if [ -z "$url" ]; then
    echo "post-create: $target names no olean cache (olean_cache_url null); nothing to fetch"
    continue
  fi
  PYTHONPATH="$NETWORK/gate" uv run --frozen --project "$NETWORK" python -m opn_gate.cli cache fetch \
    --graph "$GRAPH" --target "$target" || echo "post-create: cache fetch for $target failed; pregate.sh will build (C7)"
done
echo "post-create: done — try: $NETWORK/gate/pregate.sh --graph \"\$GRAPH\" --node <tutorial node>"
