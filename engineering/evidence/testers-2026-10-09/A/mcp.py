#!/usr/bin/env python3
"""Minimal MCP (streamable HTTP) client. Usage: mcp.py TOOL 'JSON-ARGS' [--auth] [--out FILE]
Token is read from $SECRET (outside the evidence dir); it is never printed."""
import json, sys, time, urllib.request, os
URL = "https://api.openproofnetwork.org/mcp"
SECRET = "/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/991fcb17-31b7-4871-8364-eb8359f87464/scratchpad/a/token"

def post(body, sid=None, auth=False):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
         "MCP-Protocol-Version": "2025-06-18"}
    if sid: h["Mcp-Session-Id"] = sid
    if auth: h["Authorization"] = "Bearer " + open(SECRET).read().strip()
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=h, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=300)
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode()
    return r.status, r.headers, r.read().decode()

def parse(text):
    text = text.strip()
    if text.startswith("{"): return json.loads(text)
    msgs = [json.loads(l[5:]) for l in text.splitlines() if l.startswith("data:")]
    return msgs[-1] if msgs else {"raw": text}

def call(tool, args, auth=False):
    t0 = time.time()
    st, hd, tx = post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t1009-a", "version": "1"}}}, auth=auth)
    sid = hd.get("Mcp-Session-Id")
    if sid: post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid, auth)
    if tool == "tools/list":
        st, hd, tx = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, sid, auth)
    else:
        st, hd, tx = post({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": args}}, sid, auth)
    dt = time.time() - t0
    return st, parse(tx), dt

if __name__ == "__main__":
    tool = sys.argv[1]; args = json.loads(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2][:1] in "-@" else {}
    if len(sys.argv) > 2 and sys.argv[2].startswith("@"): pass
    for a in sys.argv[2:]:
        if a.startswith("@"): args = json.load(open(a[1:]))
    auth = "--auth" in sys.argv
    st, doc, dt = call(tool, args, auth)
    out = None
    if "--out" in sys.argv: out = sys.argv[sys.argv.index("--out") + 1]
    res = doc.get("result", doc)
    # unwrap tool content
    payload = res
    if isinstance(res, dict) and "structuredContent" in res: payload = res["structuredContent"]
    elif isinstance(res, dict) and "content" in res:
        try: payload = json.loads(res["content"][0]["text"])
        except Exception: payload = res
    s = json.dumps(payload, indent=1, ensure_ascii=False)
    if out: open(out, "w").write(s)
    sys.stderr.write(f"[{tool}] http={st} {dt:.1f}s isError={res.get('isError') if isinstance(res, dict) else None}\n")
    print(s if not out else s[:3000])
