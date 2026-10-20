#!/usr/bin/env python3
"""Tiny MCP JSON-RPC client. Usage: mcp.py <tool> '<json args>' [outfile]. Token from $SCR/token (never printed)."""
import json, sys, os, urllib.request, time
URL = "https://api.openproofnetwork.org/mcp"
SCR = "/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/85614363-b225-4c5e-8f33-6eebe144b2d6/scratchpad/a14"
def call(method, params, sid=None):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    tp = os.path.join(SCR, "token")
    if os.path.exists(tp):
        h["Authorization"] = "Bearer " + open(tp).read().strip()
    if sid: h["Mcp-Session-Id"] = sid
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(URL, data=body, headers=h)
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = r.read().decode(); s = r.headers.get("Mcp-Session-Id")
    if raw.lstrip().startswith("event") or raw.lstrip().startswith("data"):
        raw = "\n".join(l[5:] for l in raw.splitlines() if l.startswith("data:"))
    return json.loads(raw) if raw.strip() else {}, s
tool = sys.argv[1]; args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
t0 = time.time()
init, sid = call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t1015b-t", "version": "1"}})
if tool == "__list":
    res, _ = call("tools/list", {}, sid)
else:
    res, _ = call("tools/call", {"name": tool, "arguments": args}, sid)
out = res
r = res.get("result", {})
if "structuredContent" in r: out = r["structuredContent"]
elif "content" in r and r["content"] and r["content"][0].get("type") == "text":
    try: out = json.loads(r["content"][0]["text"])
    except Exception: out = r["content"][0]["text"]
txt = json.dumps(out, indent=1, ensure_ascii=False)
for k in ("token", "nonce"):
    pass
if len(sys.argv) > 3:
    open(sys.argv[3], "w").write(txt)
    print(f"[{time.time()-t0:.1f}s] wrote {sys.argv[3]} ({len(txt)} bytes)", file=sys.stderr)
else:
    print(txt); print(f"[{time.time()-t0:.1f}s]", file=sys.stderr)
