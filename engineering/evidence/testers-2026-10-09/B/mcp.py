#!/usr/bin/env python3
"""Tiny MCP client: mcp.py <tool> '<json args>' [--raw]. Token read from B/.token (never printed)."""
import json, sys, time, urllib.request, pathlib, os

URL = "https://api.openproofnetwork.org/mcp"
HERE = pathlib.Path(__file__).parent
SESS = HERE / ".session"
TOK = pathlib.Path('/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/991fcb17-31b7-4871-8364-eb8359f87464/scratchpad/bsecret/token')


def post(payload, sid=None):
    import subprocess, tempfile
    cmd = ["curl", "-sS", "-X", "POST", URL, "-H", "Content-Type: application/json",
           "-H", "Accept: application/json, text/event-stream", "--max-time", "150",
           "-D", "-", "-w", "\n@@TIMING connect=%{time_connect} start=%{time_starttransfer} total=%{time_total}\n",
           "--data-binary", "@-"]
    if sid:
        cmd += ["-H", "Mcp-Session-Id: " + sid]
    if TOK.exists() and os.environ.get("NOAUTH") != "1":
        cmd += ["-H", "Authorization: Bearer " + TOK.read_text().strip()]
    r = subprocess.run(cmd, input=json.dumps(payload).encode(), capture_output=True)
    out = r.stdout.decode()
    body, _, timing = out.rpartition("@@TIMING ")
    sys.stderr.write("  curl " + timing.strip() + "\n")
    head, _, body = body.partition("\r\n\r\n")
    while head.startswith("HTTP/") and " 100 " in head.split("\r\n")[0]:
        head, _, body = body.partition("\r\n\r\n")
    lines = head.split("\r\n")
    try:
        st = int(lines[0].split()[1])
    except Exception:
        st = 0
    h = {}
    for l in lines[1:]:
        if ":" in l:
            k, v = l.split(":", 1); h[k.strip().lower()] = v.strip()
    return st, h, body


def parse(body):
    body = body.strip()
    if body.startswith("{"):
        return json.loads(body)
    out = None
    for line in body.splitlines():
        if line.startswith("data:"):
            out = json.loads(line[5:])
    return out


def session():
    if SESS.exists():
        return SESS.read_text().strip()
    st, h, b = post({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t1009-b", "version": "1"}}})
    sid = h.get("mcp-session-id")
    if sid:
        SESS.write_text(sid)
        post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    return sid


def call(method, params):
    t = time.time()
    sid = session()
    st, h, b = post({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, sid)
    dt = time.time() - t
    if st in (400, 404) and "session" in b.lower():
        SESS.unlink(missing_ok=True)
        sid = session()
        st, h, b = post({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, sid)
    return st, dt, parse(b) if b.strip() else None, b


if __name__ == "__main__":
    tool = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else {}
    if tool == "tools/list":
        st, dt, d, raw = call("tools/list", {})
    else:
        st, dt, d, raw = call("tools/call", {"name": tool, "arguments": args})
    sys.stderr.write(f"[{time.strftime('%H:%M:%SZ', time.gmtime())}] {tool} http={st} {dt:.1f}s\n")
    if d is None:
        print(raw)
        sys.exit(1)
    if "--raw" in sys.argv:
        print(json.dumps(d, indent=1))
        sys.exit(0)
    res = d.get("result", d)
    if isinstance(res, dict) and "structuredContent" in res:
        print(json.dumps(res["structuredContent"], indent=1, ensure_ascii=False))
    elif isinstance(res, dict) and "content" in res:
        for c in res["content"]:
            print(c.get("text", c))
    else:
        print(json.dumps(res, indent=1, ensure_ascii=False))
