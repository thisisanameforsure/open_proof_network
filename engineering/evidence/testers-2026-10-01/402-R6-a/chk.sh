#!/bin/sh
# usage: chk.sh file.lean [mode] [node]  (fast check, no token)
D=$(dirname "$0")
python3 - "$1" "${2:-check}" "$3" <<'PY' > $D/.req.json
import json,sys,pathlib
d={"target_id":"erdos-402","mode":sys.argv[2],"content":pathlib.Path(sys.argv[1]).read_text()}
if sys.argv[3]: d["node_id"]=sys.argv[3]
print(json.dumps(d))
PY
curl -sS -m 280 -X POST https://api.openproofnetwork.org/check -H 'Content-Type: application/json' --data @$D/.req.json > $D/.resp.json
python3 - $D/.resp.json <<'PY'
import json,sys
a=json.load(open(sys.argv[1]))
print({k:(v if len(json.dumps(v))<600 else '...') for k,v in a.items() if k!='result'})
m=(a.get("result") or {}).get("lean_messages") or {}
for e in (m.get("errors") or [])[:8]: print("ERR",e[:1500])
for e in (m.get("warnings") or [])[:5]: print("WARN",e[:300])
for e in (m.get("infos") or [])[:8]: print("INFO",e[:900])
PY
