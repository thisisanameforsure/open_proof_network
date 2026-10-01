#!/bin/sh
# usage: st.sh <submission id>  -> one line of state
curl -sS -m 60 https://api.openproofnetwork.org/submissions/$1 -H "Authorization: Bearer $(cat /tmp/claude-0/-home-claude/31c3e667-c418-5784-a734-bd7529a6bb30/scratchpad/tokens/402-a.token)" | python3 -c "
import json,sys,time
d=json.load(sys.stdin);p=d.get('pull_request',{})
print(time.strftime('%H:%M:%SZ',time.gmtime()),p.get('number'),p.get('state'),'merged',p.get('merged'),'waiting_on',p.get('waiting_on'),p.get('mergeable_state'),'gate',p.get('gate') or p.get('checks') or p.get('gate_verdict'))"
