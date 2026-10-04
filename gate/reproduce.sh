#!/usr/bin/env bash
# reproduce.sh — replay the gate on a merged commit inside the step-3 image (D-5; F00-R15).
#
#   gate/reproduce.sh --graph <graph-checkout> --commit <sha> --node <node-id>
#                     [--compare attestations/<id>.json] [--out <dir>] [--no-build]
#                     [--allow-network-mismatch]
#
# Exports the tree at <sha>, diffs it against its first parent, runs steps 1, 2 and 4 to 8 (F01,
# F02) in the sandbox image built from gate/Dockerfile for the graph's pinned toolchain — the
# image also carries the built Lean metaprograms steps 6-8 call (F01-R10, F02-R1) — and writes
# attestation.json. With --compare it masks runner, merge_commit and signature and reports whether
# the reproduction is identical to the committed attestation (exit 0) or not (exit 1).
#
# Run it from a checkout of this repository at the graph's pinned network_commit, with gate/
# unedited: a record speaks for the pinned gate only (D-5), so any other checkout is refused with
# `network-mismatch` before anything is exported or built (exit 2; F07-T65). To replay with
# another gate anyway, pass --allow-network-mismatch: the mismatch is reported and a --compare
# result is never identical.
# Needs docker and either uv or a python3 with jsonschema+pyyaml.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/gate${PYTHONPATH:+:$PYTHONPATH}"

if command -v uv >/dev/null 2>&1; then
  exec uv run --frozen --project "$ROOT" python -m opn_gate.cli reproduce "$@"
fi
exec python3 -m opn_gate.cli reproduce "$@"
