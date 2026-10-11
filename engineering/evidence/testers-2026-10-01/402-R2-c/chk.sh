#!/bin/sh
S=/tmp/claude-0/-home-claude/31c3e667-c418-5784-a734-bd7529a6bb30/scratchpad
T=$S/tokens/402-c.token
python3 -c '
import json,sys,pathlib
print(json.dumps({"target_id":"erdos-402","mode":"check","content":pathlib.Path(sys.argv[1]).read_text()}))' "$1" > $S/c/req.json
if [ -f $T ]; then A="Authorization: Bearer $(cat $T)"; else A="X-None: 1"; fi
curl -sS -m 60 -X POST https://api.openproofnetwork.org/check -H "$A" -H 'Content-Type: application/json' --data @$S/c/req.json | python3 -c '
import json,sys
a=json.load(sys.stdin)
print("okay:",a.get("okay"),"env:",a.get("environment"),"exact:",a.get("exact"),"lint:",[w["code"] for w in a.get("lint",[])], a.get("error"),a.get("message"))
r=a.get("result") or {}
m=r.get("lean_messages") or {}
for e in (m.get("errors") or [])[:8]: print("ERR",e[:900])
for e in (m.get("warnings") or [])[:5]: print("WARN",e[:200])
for e in (m.get("infos") or [])[:5]: print("INFO",e[:300])
'
