"""POST /check on the live network (the F13 fast check: AXLE, Lean 4.33.1, the target's Mathlib)."""
import json, time, urllib.request, urllib.error
API = "https://api.openproofnetwork.org/check"
CALLS = []

def check(target: str, content: str, timeout: int = 60) -> dict:
    body = json.dumps({"target_id": target, "content": content}).encode()
    req = urllib.request.Request(API, data=body, headers={"content-type": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        out = {"http_error": e.code, "body": e.read().decode()[:2000]}
    CALLS.append({"target": target, "bytes": len(content), "s": round(time.time() - t, 1),
                  "okay": out.get("okay"), "err": out.get("http_error")})
    return out

def messages(out: dict) -> dict:
    lm = (out.get("result") or {}).get("lean_messages") or {}
    return {"errors": lm.get("errors", []), "infos": lm.get("infos", []),
            "failed": (out.get("result") or {}).get("failed_declarations", [])}
