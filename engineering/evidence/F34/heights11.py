import functools, http.server, socketserver, sys, threading, json
from playwright.sync_api import sync_playwright

PAGES = ["abc", "erdos-257", "erdos-1094", "singmaster", "goldbach"]
out = {}
for label, d in (("before", sys.argv[1]), ("after", sys.argv[2])):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=d)
    h.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with sync_playwright() as p:
            b = p.chromium.launch()
            for w in (1440, 390):
                pg = b.new_page(viewport={"width": w, "height": 900})
                for t in PAGES:
                    r = pg.goto(
                        f"http://127.0.0.1:{srv.server_address[1]}/problems/{t}/",
                        wait_until="load",
                        timeout=180000,
                    )
                    if r is None or r.status != 200:
                        continue
                    pg.wait_for_timeout(500)
                    v = pg.evaluate(
                        "({h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth})"
                    )
                    out.setdefault(t, {}).setdefault(str(w), {})[label] = v
            b.close()
for t, ws in out.items():
    for w, v in ws.items():
        print(
            json.dumps({"page": t, "width": int(w), **{k: v.get(k) for k in ("before", "after")}})
        )
