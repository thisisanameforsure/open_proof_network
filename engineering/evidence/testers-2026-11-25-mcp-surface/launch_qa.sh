#!/bin/zsh
# usage: launch_qa.sh <dir> <pseudonym> <mcpconfig> <extra allowed tool patterns...>
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
dir=$1; pseudo=$2; cfg=$3; shift 3
cd "$dir"
export OPN_TOKEN="$(cat .token)"
prompt="$(sed "s/PSEUDONYM/${pseudo}/" ../endpoints-common.md)

$(cat brief.md)

Started at $(date -u +%H:%MZ); stop and write REPORT.md by $(date -u -v+60M +%H:%MZ)."
claude -p "$prompt" --model opus --mcp-config "$cfg" --strict-mcp-config \
  --allowedTools "mcp__open-proof-network__search" "mcp__open-proof-network__read" \
    "mcp__open-proof-network__write" "Read" "Write" "Edit" "Bash(date:*)" "Bash(curl:*)" \
    "Bash(python3:*)" "$@" \
  --output-format stream-json --verbose > transcript.jsonl 2> stderr.log
echo "exit $?" >> stderr.log
