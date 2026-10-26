#!/bin/sh
cd /Users/mikehiggins/Desktop/repos/opn-testers-1026/engineering/evidence/testers-2026-10-26-e257/A
for i in $(seq 1 80); do
  curl -sS https://api.openproofnetwork.org/precheck/01M5X152QG50Y009T2JXNZZSS2 -o precheck-h4-result.json
  st=$(python3 -c "import json; print(json.load(open('precheck-h4-result.json'))['state'])" 2>/dev/null)
  echo "$(date -u +%H:%M:%SZ) $st" >> watch-h4.log
  case "$st" in done|error) break;; esac
  sleep 15
done
