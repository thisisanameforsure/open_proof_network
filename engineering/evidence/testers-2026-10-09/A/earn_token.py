import json, sys, os; sys.path.insert(0, '.')
import mcp
S = sys.argv[1]
pc = json.load(open(S + "/tutorial_precheck.json"))["body"]
c, d, dt = mcp.call("get_dco", {})
r = d["result"]; dco = r.get("structuredContent") or json.loads(r["content"][0]["text"])
c, d, dt = mcp.call("get_token", {"proof": {"kind": "tutorial", "job_id": pc["id"], "nonce": pc["nonce"]},
                                  "pseudonym": "t1009-a", "dco": {"version": dco["version"], "accepted": True}})
r = d["result"]; p = r.get("structuredContent") or json.loads(r["content"][0]["text"])
body = p.get("body", p)
if "token" in body:
    fd = os.open(S + "/token", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600); os.write(fd, body["token"].encode()); os.close(fd)
    body["token"] = "<redacted>"
print(f"{dt:.1f}s", json.dumps(p if "body" not in p else {**p, "body": body})[:800])
