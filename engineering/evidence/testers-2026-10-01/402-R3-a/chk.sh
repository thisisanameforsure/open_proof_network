#!/bin/sh
# usage: chk.sh file.lean [mode] [node_id]
S=/tmp/claude-0/-home-claude/31c3e667-c418-5784-a734-bd7529a6bb30/scratchpad
python3 - "$1" "${2:-check}" "$3" <<'PY' > $S/a2/req.json
import json,sys,pathlib
d={"target_id":"erdos-402","mode":sys.argv[2],"content":pathlib.Path(sys.argv[1]).read_text()}
if sys.argv[3]: d["node_id"]=sys.argv[3]
print(json.dumps(d))
PY
curl -sS -m 60 -X POST https://api.openproofnetwork.org/check -H "Authorization: Bearer $(cat $S/tokens/402-a.token)" -H 'Content-Type: application/json' --data @$S/a2/req.json > $S/a2/resp.json
python3 - $S/a2/resp.json <<'PY'
import json,sys
a=json.load(open(sys.argv[1]))
print("okay:",a.get("okay"),"env:",a.get("environment"),"exact:",a.get("exact"),"lint:",[w["code"] for w in a.get("lint",[])], a.get("error"),a.get("message"), "witness:", a.get("witness") and {k:(v if k=="matches" else str(v)[:60]) for k,v in a["witness"].items()})
m=(a.get("result") or {}).get("lean_messages") or {}
for e in (m.get("errors") or [])[:8]: print("ERR",e[:900])
for e in (m.get("warnings") or [])[:5]: print("WARN",e[:200])
for e in (m.get("infos") or [])[:5]: print("INFO",e[:200])
PY
