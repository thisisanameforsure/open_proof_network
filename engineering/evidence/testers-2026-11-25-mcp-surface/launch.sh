#!/bin/zsh
# usage: launch.sh <dir> <pseudonym>
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
dir=$1; pseudo=$2
cd "$dir"
export OPN_TOKEN="$(cat .token)"
prompt="$(sed "s/PSEUDONYM/${pseudo}/" ../common.md)

$(cat brief.md)

Started at $(date -u +%H:%MZ); stop and write REPORT.md by $(date -u -v+60M +%H:%MZ)."
claude -p "$prompt" --model opus --mcp-config ../mcp.json --strict-mcp-config \
  --allowedTools "mcp__open-proof-network__search" "mcp__open-proof-network__read" \
    "mcp__open-proof-network__write" "Read" "Write" "Edit" "Bash(date:*)" \
  --output-format stream-json --verbose > transcript.jsonl 2> stderr.log
echo "exit $?" >> stderr.log
