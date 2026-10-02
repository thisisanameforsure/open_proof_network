#!/bin/sh
# usage: chk.sh file.lean [mode] [node_id]
T=/tmp/claude-0/-home-claude/31c3e667-c418-5784-a734-bd7529a6bb30/scratchpad/tokens/402-b.token
python3 - "$1" "${2:-check}" "$3" <<'PY' > /tmp/claude-0/-home-claude/31c3e667-c418-5784-a734-bd7529a6bb30/scratchpad/b2/req.json
import json,sys,pathlib
d={"target_id":"erdos-402","mode":sys.argv[2],"content":pathlib.Path(sys.argv[1]).read_text()}
if sys.argv[3]: d["node_id"]=sys.argv[3]
print(json.dumps(d))
PY
curl -sS -m 170 -X POST https://api.openproofnetwork.org/check -H "Authorization: Bearer $(cat $T)" -H 'Content-Type: application/json' --data @/tmp/claude-0/-home-claude/31c3e667-c418-5784-a734-bd7529a6bb30/scratchpad/b2/req.json | python3 -c '
import json,sys
a=json.load(sys.stdin)
print("okay:",a.get("okay"),"env:",a.get("environment"),"exact:",a.get("exact"),"lint:",[w["code"] for w in a.get("lint",[])], a.get("error"),a.get("message"))
r=a.get("result") or {}
for k in ("lean_messages",):
    m=r.get(k) or {}
    for e in (m.get("errors") or [])[:8]: print("ERR",e[:700])
    for e in (m.get("warnings") or [])[:5]: print("WARN",e[:200])
if not r.get("lean_messages"): print(list(r.keys()))
'
