# usage: wchk.py witness.lean (--node ID | --statement file)
import json,sys,pathlib,subprocess
d={"target_id":"erdos-402","mode":"witness","content":pathlib.Path(sys.argv[1]).read_text()}
if sys.argv[2]=="--node": d["node_id"]=sys.argv[3]
else: d["statement"]=pathlib.Path(sys.argv[3]).read_text()
pathlib.Path('.wreq.json').write_text(json.dumps(d))
out=subprocess.run(["curl","-sS","-m","280","-X","POST","https://api.openproofnetwork.org/check","-H","Content-Type: application/json","--data","@.wreq.json"],capture_output=True,text=True).stdout
a=json.loads(out); pathlib.Path('.wresp.json').write_text(out)
print("okay",a.get("okay"),"env",a.get("environment"),a.get("exact"),"lint",[l["code"] for l in a.get("lint",[])],a.get("user_error"),a.get("error"),a.get("message"))
w=a.get("witness") or {}; print("matches",w.get("matches")); print("expected:",str(w.get("expected"))[:1500]); 
if not w.get("matches"): print("given:",str(w.get("given"))[:1500])
m=(a.get("result") or {}).get("lean_messages") or {}
for e in (m.get("errors") or [])[:6]: print("ERR",e[:1200])
