#!/usr/bin/env bash
# Fetch every input of docs/seed_conjecture_sources_build.py into a work directory (F14-R11, F11-Q23).
#
# The inputs are fetched, never committed: erdosproblems.com states no licence, and the rest are
# public repositories the build reads at a pin. Usage:
#
#   docs/seed_conjecture_sources_fetch.sh <work-dir> [<formal-conjectures commit>]
#   uv run --no-project --with pyyaml python3 docs/seed_conjecture_sources_build.py --work <work-dir>
#
# Needs git, curl, gh (authenticated, for the issue list) and python3.
set -euo pipefail

W=${1:?usage: seed_conjecture_sources_fetch.sh <work-dir> [<fc-commit>]}
PIN=${2:-c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae}
mkdir -p "$W"
cd "$W"

# The registry at the pin, with its whole history (first and last change per file).
[ -d fc ] || git clone -q https://github.com/google-deepmind/formal-conjectures.git fc
git -C fc checkout -q "$PIN"
git -C fc log --format='COMMIT %H %cI' --name-status --diff-filter=AMR -- FormalConjectures > fc_file_history.txt

# Every issue or pull request labelled misformalization, open and closed.
gh api --paginate 'repos/google-deepmind/formal-conjectures/issues?labels=misformalization&state=all&per_page=100' \
  | python3 -c 'import sys, json; json.dump(json.loads(sys.stdin.read().replace("][", ",")), open("fc_misform_issues.json", "w"))'

# The Erdős status database and its AI-contributions wiki.
[ -d ep ] || git clone -q --depth 1 https://github.com/teorth/erdosproblems.git ep
[ -d epwiki ] || git clone -q --depth 1 https://github.com/teorth/erdosproblems.wiki.git epwiki

# AlphaProof Nexus's published attempts and outputs.
[ -d nexus ] || git clone -q --depth 1 https://github.com/google-deepmind/alphaproof-nexus-results.git nexus
# The date the attempt list was published: the attempts ledger's date for each named attempt (F14-R4).
gh api repos/google-deepmind/alphaproof-nexus-results --jq '.created_at' | cut -c1-10 > nexus_published.txt

# Epoch's LeanOpenProblems (FrontierMath Erdős selection); the build reads epoch/apn/data.
[ -d epoch-src ] || git clone -q --depth 1 https://github.com/epoch-research/LeanOpenProblems.git epoch-src
ln -sfn epoch-src epoch

# One erdosproblems.com page per Erdős file in the registry, politely paced.
mkdir -p ep_pages
for f in fc/FormalConjectures/ErdosProblems/*.lean; do
  b=$(basename "$f" .lean)
  case $b in (*[!0-9]*) continue ;; esac
  [ -s "ep_pages/$b.html" ] && continue
  curl -sfL --max-time 30 -A "open-proof-network catalog (research; one fetch per problem)" \
    "https://www.erdosproblems.com/$b" -o "ep_pages/$b.html" || rm -f "ep_pages/$b.html"
  sleep 0.4
done
echo "inputs in $W"
