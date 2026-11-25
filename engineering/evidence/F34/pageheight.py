import functools, http.server, socketserver, sys, threading, json
from playwright.sync_api import sync_playwright

h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=sys.argv[1])
h.log_message = lambda *a: None
with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        out = {}
        for w in (1440, 390):
            pg = b.new_page(viewport={"width": w, "height": 900})
            pg.goto(
                f"http://127.0.0.1:{srv.server_address[1]}/problems/",
                wait_until="load",
                timeout=180000,
            )
            pg.wait_for_timeout(800)
            out[w] = pg.evaluate(
                "({h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth, worked: document.querySelectorAll('[data-section=worked] [data-id]:not([hidden])').length, waiting: document.querySelectorAll('[data-section=waiting] [data-id]:not([hidden])').length, bytes: document.documentElement.outerHTML.length})"
            )
        print(json.dumps(out))
        b.close()
