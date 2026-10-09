import json, sys, sys; sys.path.insert(0, '.')
import mcp
G, S = sys.argv[1], sys.argv[2]
st = open(G + "/targets/tutorial/nodes/tutorial-and-swap/Statement.lean").read()
pr = st.replace(":= by\n  sorry", ":= by\n  intro p q hpq\n  exact ⟨hpq.right, hpq.left⟩")
assert pr != st
code, doc, dt = mcp.call("precheck_submission", {"node_id": "tutorial-and-swap", "bundle": {"targets/tutorial/nodes/tutorial-and-swap/Proof.lean": pr}})
res = doc["result"]; p = res.get("structuredContent") or json.loads(res["content"][0]["text"])
json.dump(p, open(S + "/tutorial_precheck.json", "w"))
red = json.loads(json.dumps(p))
def scrub(o):
    if isinstance(o, dict):
        return {k: ("<redacted>" if k == "nonce" else scrub(v)) for k, v in o.items()}
    return o
print(f"{dt:.1f}s", json.dumps(scrub(red))[:1500])
