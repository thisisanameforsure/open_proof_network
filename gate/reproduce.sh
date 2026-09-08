#!/usr/bin/env bash
# reproduce.sh — replay the gate on a merged commit inside the step-3 image (D-5; F00-R15).
#
#   gate/reproduce.sh --graph <graph-checkout> --commit <sha> --node <node-id>
#                     [--compare attestations/<id>.json] [--out <dir>] [--no-build]
#
# Exports the tree at <sha>, diffs it against its first parent, runs steps 1, 2, 4 and 5 in the
# sandbox image built from gate/Dockerfile for the graph's pinned toolchain, and writes
# attestation.json. With --compare it masks runner, merge_commit and signature and reports whether
# the reproduction is identical to the committed attestation (exit 0) or not (exit 1).
# Needs docker and either uv or a python3 with jsonschema+pyyaml.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/gate${PYTHONPATH:+:$PYTHONPATH}"

if command -v uv >/dev/null 2>&1; then
  exec uv run --frozen --project "$ROOT" python -m opn_gate.cli reproduce "$@"
fi
exec python3 -m opn_gate.cli reproduce "$@"
