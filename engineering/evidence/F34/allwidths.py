import functools, http.server, socketserver, sys, threading, json, os
from playwright.sync_api import sync_playwright

root = sys.argv[1]
paths = ["/", "/problems/", "/contributors/", "/docs/", "/about/", "/rules/", "/steward/", "/me/"]
paths += [
    f"/problems/{d}/"
    for d in sorted(os.listdir(f"{root}/problems"))
    if os.path.isfile(f"{root}/problems/{d}/index.html")
]
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
h.log_message = lambda *a: None
wide = {}
with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 900})
        for path in paths:
            pg.goto(
                f"http://127.0.0.1:{srv.server_address[1]}{path}", wait_until="load", timeout=180000
            )
            pg.wait_for_timeout(250)
            w = pg.evaluate("document.documentElement.scrollWidth")
            if w > 390:
                wide[path] = w
        b.close()
print(json.dumps({"pages": len(paths), "wider_than_390": wide}, indent=1))
