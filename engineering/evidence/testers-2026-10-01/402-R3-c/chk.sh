#!/bin/sh
# usage: chk.sh file.lean   (anonymous fast check)
python3 - "$1" <<'PY' > /tmp/claude-0/-home-claude/31c3e667-c418-5784-a734-bd7529a6bb30/scratchpad/r3c-req.json
import json,sys,pathlib
print(json.dumps({"target_id":"erdos-402","mode":"check","content":pathlib.Path(sys.argv[1]).read_text()}))
PY
curl -sS -m 170 -X POST https://api.openproofnetwork.org/check -H 'Content-Type: application/json' --data @/tmp/claude-0/-home-claude/31c3e667-c418-5784-a734-bd7529a6bb30/scratchpad/r3c-req.json | python3 -c '
import json,sys
a=json.load(sys.stdin)
print("okay:",a.get("okay"),"env:",a.get("environment"),"exact:",a.get("exact"),"lint:",[w["code"] for w in a.get("lint",[])], a.get("error"),a.get("message"))
r=a.get("result") or {}
m=r.get("lean_messages") or {}
for e in (m.get("errors") or [])[:8]: print("ERR",e[:300],"...",e[-900:])
for e in (m.get("warnings") or [])[:5]: print("WARN",e[:200])
if not r.get("lean_messages"): print(list(r.keys()), str(a)[:500])
'
