#!/bin/zsh
# poll.sh JOB OUT
for i in $(seq 1 40); do
  timeout 140 python3 mcp.py get_precheck "{\"job_id\":\"$1\"}" $2 2>/dev/null
  s=$(python3 -c "import json;d=json.load(open('$2'));b=d.get('body',d);print(b.get('state'))" 2>/dev/null)
  echo "$(date -u +%T) $s"
  [[ $s == done || $s == error ]] && break
  sleep 10
done
