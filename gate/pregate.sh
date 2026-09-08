#!/usr/bin/env bash
# pregate.sh — run the gate locally on one node (D-4, D-27; F00-R11).
#
#   gate/pregate.sh --graph <graph-checkout> --node <node-id> [--sign ~/.ssh/id_ed25519]
#                   [--model <name>] [--harness <name>] [--out <dir>] [--base <git-ref>]
#
# Runs steps 1, 2, 4 and 5 with the pinned toolchain in an ordinary local build (step 3's isolation
# is the authoritative run's), prints a JSON verdict, and writes verdict.json + attestation.json
# (runner: local; unsigned unless --sign). Exit 0 pass · 1 fail · 3 bounced · 2 error.
# Needs elan (gate/scripts/install-toolchain.sh) and either uv or a python3 with jsonschema+pyyaml.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/gate${PYTHONPATH:+:$PYTHONPATH}"

if command -v uv >/dev/null 2>&1; then
  exec uv run --frozen --project "$ROOT" python -m opn_gate.cli pregate "$@"
fi
exec python3 -m opn_gate.cli pregate "$@"
