#!/usr/bin/env bash
# Install one Mathlib checkout with its oleans, at the commit a graph pins (F11-R6; D-7).
#
#   gate/scripts/install-mathlib.sh <mathlib-sha> [<lean-toolchain>]
#
# Puts the checkout at $OPN_MATHLIB_HOME/<sha> (default ~/.opn/mathlib/<sha>), fetches the oleans
# from Mathlib's cache (`lake exe cache get`) rather than building them, checks the checkout's own
# lean-toolchain is the toolchain given (Mathlib oleans are specific to the Lean that built them),
# and leaves a MATHLIB_SHA stamp beside it — which is what the gate reads at step 1
# (opn_gate.toolchain.mathlib_library_path). The same steps build the image
# (gate/Dockerfile, MATHLIB_SHA); a laptop or CI runs this instead. Needs git, curl and elan.
set -euo pipefail

SHA="${1:?usage: install-mathlib.sh <mathlib-sha> [<lean-toolchain>]}"
if [ "${#SHA}" -ne 40 ] || [ -n "$(printf '%s' "$SHA" | tr -d '0-9a-f')" ]; then
  echo "install-mathlib: not a 40-hex commit: $SHA" >&2; exit 2
fi
HOME_DIR="${OPN_MATHLIB_HOME:-$HOME/.opn/mathlib}"
ELAN_HOME="${ELAN_HOME:-${OPN_ELAN_HOME:-$HOME/.elan}}"
export ELAN_HOME
export PATH="$ELAN_HOME/bin:$PATH"
DEST="$HOME_DIR/$SHA"

if [ -f "$DEST/MATHLIB_SHA" ] && [ "$(cat "$DEST/MATHLIB_SHA")" = "$SHA" ] \
   && [ -d "$DEST/.lake/build/lib/lean" ]; then
  echo "install-mathlib: $SHA already installed at $DEST"
else
  mkdir -p "$DEST"
  cd "$DEST"
  if [ ! -d .git ]; then
    echo "install-mathlib: fetching mathlib4 at $SHA (one commit)"
    git init -q
    git remote add origin https://github.com/leanprover-community/mathlib4.git
  fi
  git fetch --depth 1 origin "$SHA"
  git checkout -q --detach FETCH_HEAD
  echo "install-mathlib: lean-toolchain $(tr -d '[:space:]' < lean-toolchain)"
  echo "install-mathlib: lake exe cache get (the oleans, from Mathlib's cache; several GiB)"
  lake exe cache get
  echo "install-mathlib: lake build (a no-op after the cache; proves the tree is complete)"
  lake build
  printf '%s\n' "$SHA" > MATHLIB_SHA
fi

PINNED="$(tr -d '[:space:]' < "$DEST/lean-toolchain")"
if [ -n "${2:-}" ] && [ "$PINNED" != "$2" ]; then
  echo "install-mathlib: Mathlib $SHA pins $PINNED, but $2 was asked for (D-7: a graph pins the Mathlib its toolchain built)" >&2
  exit 1
fi
echo "install-mathlib: done — $DEST ($(du -sh "$DEST/.lake" 2>/dev/null | cut -f1) of oleans), toolchain $PINNED"
