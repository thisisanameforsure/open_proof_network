#!/bin/sh
# retry the N=100 precheck until the products render, then poll the job to done
cd "/Users/mikehiggins/Desktop/repos/opn-testers-1026/engineering/evidence/testers-2026-10-26-e257/A"
for i in $(seq 1 30); do
  /private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/07b6ec86-8072-41ac-ab7e-7dba7f2b22c6/scratchpad/t1026-a/api.sh POST /precheck precheck-100.json > precheck-100-resp.txt
  code=$(grep -o 'HTTP [0-9]*' precheck-100-resp.txt | awk '{print $2}')
  echo "$(date -u +%H:%M:%SZ) attempt $i HTTP $code" >> retry-precheck.log
  if [ "$code" = "202" ]; then break; fi
  sleep 30
done
JOB=$(python3 -c "import json; t=open('precheck-100-resp.txt').read().split('\nHTTP')[0]; print(json.loads(t).get('id',''))")
echo "job $JOB" >> retry-precheck.log
[ -z "$JOB" ] && exit 1
for i in $(seq 1 120); do
  curl -sS https://api.openproofnetwork.org/precheck/$JOB -o precheck-100-result.json
  st=$(python3 -c "import json; print(json.load(open('precheck-100-result.json'))['state'])")
  echo "$(date -u +%H:%M:%SZ) $st" >> retry-precheck.log
  if [ "$st" = done ] || [ "$st" = error ]; then break; fi
  sleep 15
done
