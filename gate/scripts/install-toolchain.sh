#!/usr/bin/env bash
# Install elan (if absent) and the pinned Lean toolchain (F00-T2).
#
#   gate/scripts/install-toolchain.sh              # installs the pin in ./lean-toolchain
#   gate/scripts/install-toolchain.sh <toolchain>  # installs a graph's pin, e.g. from gate-spec.json
#
# Never edits shell configuration; elan lives under $ELAN_HOME (default ~/.elan) and the gate finds
# it there (opn_gate.config OPN_ELAN_HOME) or on PATH. lean4checker is not installed separately:
# it ships inside every toolchain from v4.28.0 as `leanchecker` (F00-Q10).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLCHAIN="${1:-$(tr -d '[:space:]' < "$HERE/../../lean-toolchain")}"
ELAN_HOME="${ELAN_HOME:-$HOME/.elan}"
export ELAN_HOME
ELAN="$ELAN_HOME/bin/elan"

if [ ! -x "$ELAN" ]; then
  echo "install-toolchain: installing elan into $ELAN_HOME"
  curl -sSf https://elan.lean-lang.org/elan-init.sh \
    | sh -s -- -y --no-modify-path --default-toolchain none
fi

echo "install-toolchain: elan $("$ELAN" --version)"
"$ELAN" toolchain install "$TOOLCHAIN"
echo "install-toolchain: $("$ELAN" run "$TOOLCHAIN" lean --version)"
"$ELAN" run "$TOOLCHAIN" leanchecker --help >/dev/null 2>&1 || true
echo "install-toolchain: done — add $ELAN_HOME/bin to PATH or leave it to opn_gate (OPN_ELAN_HOME)"
