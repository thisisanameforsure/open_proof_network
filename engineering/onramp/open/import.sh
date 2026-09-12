#!/usr/bin/env bash
# The five Stage 0 open targets, imported from google-deepmind/formal-conjectures at the pinned
# commit (F11-T5, R9; D-10) onto a branch of the graph checkout. The curator's act: run it,
# push the branch, open the pull request (mode intake, one target per commit); Mike's approval
# of the five is the merge (F11-Q3).
#
#   engineering/onramp/open/import.sh [../open_proof_network_graph] [--sandbox]
#
# Without --sandbox admission is skipped here (--no-toolchain: the laptop holds no Mathlib
# image) and the pull request's gate admits each root in the sandbox instead.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
GRAPH="${1:-$ROOT/../open_proof_network_graph}"
MODE="${2:---no-toolchain}"
PIN=c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae
AUTHOR=thisisanameforsure
export PYTHONPATH="$ROOT/gate${PYTHONPATH:+:$PYTHONPATH}"
for n in 68 376 406 172 52; do
  id="erdos-$n"
  uv run --frozen --project "$ROOT" python -m opn_gate.cli intake import-fc "$HERE/upstream/$n.lean" \
    --at "$PIN" --graph "$GRAPH" --target "$id" --from "$HERE/$id/record.yaml" \
    --witness "$HERE/$id/Witness.lean" --statement "$HERE/$id/Statement.lean" \
    --path "FormalConjectures/ErdosProblems/$n.lean" --repo google-deepmind/formal-conjectures \
    --url "https://github.com/google-deepmind/formal-conjectures/blob/$PIN/FormalConjectures/ErdosProblems/$n.lean" \
    --licence Apache-2.0 --attribution "The Formal Conjectures Authors (google-deepmind/formal-conjectures), Apache-2.0" \
    --upstream-author "The Formal Conjectures Authors" --author "$AUTHOR" --date 2026-09-12T12:30:00Z \
    $( [ "$MODE" = "--sandbox" ] && echo --sandbox || echo --no-toolchain ) | tail -3
  echo "imported $id"
done
