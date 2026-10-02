#!/bin/sh
# usage: chk.sh file.lean   (fast check, no token)
S=/tmp/claude-0/-home-claude/31c3e667-c418-5784-a734-bd7529a6bb30/scratchpad/r4c
python3 - "$1" <<'PY' > $S/req.json
import json,sys,pathlib
print(json.dumps({"target_id":"erdos-402","mode":"check","content":pathlib.Path(sys.argv[1]).read_text()}))
PY
curl -sS -m 170 -X POST https://api.openproofnetwork.org/check -H 'Content-Type: application/json' --data @$S/req.json > $S/resp.json
python3 - $S/resp.json <<'PY'
import json,sys
a=json.load(open(sys.argv[1]))
print("okay:",a.get("okay"),"env:",a.get("environment"),"exact:",a.get("exact"),"lint:",[w["code"] for w in a.get("lint",[])], a.get("error"),a.get("message"))
m=(a.get("result") or {}).get("lean_messages") or {}
for e in (m.get("errors") or [])[:8]: print("ERR",e[:1500])
for e in (m.get("warnings") or [])[:5]: print("WARN",e[:300])
for e in (m.get("infos") or [])[:8]: print("INFO",e[:600])
PY
