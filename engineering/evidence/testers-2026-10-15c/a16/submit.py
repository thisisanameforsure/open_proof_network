import json
from net import req
H={"Content-Type":"application/json","Authorization":"Bearer "+open("token").read().strip()}
b=json.load(open("precheck-req.json")); j=json.load(open("precheck-job.json"))
s={"node_id":b["node_id"],"artifact_type":"partial","bundle":b["bundle"],"precheck_job_id":j["id"],
 "tooling":{"model":"Claude Opus 5.5 (claude-opus-5-5)","version":None,"harness":"AGENTS.md walkthrough"},
 "automation":{"method":"agent","models":["Claude Opus 5.5 (claude-opus-5-5)"],"framework":"AGENTS.md walkthrough"}}
d=req("https://api.openproofnetwork.org/submissions",json.dumps(s).encode(),H,tries=1)
json.dump(d,open("submitted.json","w"),indent=1); print(json.dumps(d)[:800])
