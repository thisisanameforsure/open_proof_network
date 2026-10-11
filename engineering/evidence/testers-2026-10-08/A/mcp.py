#!/usr/bin/env python3
"""Call one MCP tool over JSON-RPC. Usage: mcp.py <tool> <args-json-or-@file> [--auth] [--out FILE]
Token (if --auth) is read from /private/tmp/claude-501/opn-testers-1008/A/token, never printed."""
import json, sys, time, urllib.request, pathlib
tool = sys.argv[1]; a = sys.argv[2]
args = json.loads(pathlib.Path(a[1:]).read_text() if a.startswith("@") else a)
hdr = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
if "--auth" in sys.argv:
    hdr["Authorization"] = "Bearer " + pathlib.Path("/private/tmp/claude-501/opn-testers-1008/A/token").read_text().strip()
method = "tools/list" if tool == "-list" else "tools/call"
params = {} if tool == "-list" else {"name": tool, "arguments": args}
body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
req = urllib.request.Request("https://api.openproofnetwork.org/mcp", data=body, headers=hdr, method="POST")
t = time.time()
try:
    with urllib.request.urlopen(req, timeout=300) as r:
        code = r.status; raw = r.read().decode()
except urllib.error.HTTPError as e:
    code = e.code; raw = e.read().decode()
dt = time.time() - t
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
if out: pathlib.Path(out).write_text(raw)
sys.stderr.write(f"[{time.strftime('%H:%M:%SZ', time.gmtime())}] {tool} http={code} {dt:.1f}s\n")
try:
    d = json.loads(raw)
    res = d.get("result", d)
    if "content" in res:
        for c in res["content"]:
            if c.get("type") == "text":
                print(c["text"][:int(dict(enumerate(sys.argv)).get(sys.argv.index("--max")+1, 6000)) if "--max" in sys.argv else 6000])
        if res.get("isError"): print("isError: true")
    else:
        print(json.dumps(res)[:6000])
except Exception:
    print(raw[:6000])
