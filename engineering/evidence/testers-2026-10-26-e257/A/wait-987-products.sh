#!/bin/sh
S=/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/07b6ec86-8072-41ac-ab7e-7dba7f2b22c6/scratchpad/t1026-a
cd /Users/mikehiggins/Desktop/repos/opn-testers-1026/engineering/evidence/testers-2026-10-26-e257/A
for i in $(seq 1 60); do
  $S/api.sh GET /submissions/987 > pr987-final.txt 2>/dev/null
  r=$(python3 -c "
import json; t=open('pr987-final.txt').read().split('\nHTTP')[0]
try:
    d=json.loads(t); a=d.get('attestation') or {}; print(d.get('attestation_path'), a.get('artifact_hash'), [h.get('became') for h in d.get('holes') or []])
except Exception as e: print('err')")
  echo "$(date -u +%H:%M:%SZ) $r"
  case "$r" in None*|err*) sleep 30;; *) break;; esac
done
