#!/bin/sh
cd "/Users/mikehiggins/Desktop/repos/opn-testers-1026/engineering/evidence/testers-2026-10-26-e257/A"
for i in $(seq 1 200); do
  /private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/07b6ec86-8072-41ac-ab7e-7dba7f2b22c6/scratchpad/t1026-a/api.sh GET /submissions/987 > pr987-state.txt 2>/dev/null
  st=$(python3 -c "
import json; t=open('pr987-state.txt').read().split('\nHTTP')[0]
try:
    d=json.loads(t); pr=d['pull_request']; print(d['state'], pr.get('waiting_on'), pr.get('mergeable_state'), (d.get('queue') or {}).get('position'))
except Exception as e: print('err', e)")
  echo "$(date -u +%H:%M:%SZ) $st" >> watch-pr.log
  case "$st" in merged*|closed*) break;; esac
  sleep 45
done
