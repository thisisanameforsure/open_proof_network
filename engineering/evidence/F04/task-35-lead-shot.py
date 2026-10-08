import sys, threading, http.server, functools, socketserver
from playwright.sync_api import sync_playwright
site, out = sys.argv[1], sys.argv[2]
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=site)
H.log_message = lambda *a: None
srv = socketserver.TCPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 900})
    for name, path in [("root", "nodes/erdos-1094/erdos-1094/"), ("h3", "nodes/erdos-1094/erdos-1094--h3/"), ("h1", "nodes/erdos-1094/erdos-1094--h1/")]:
        pg.goto(f"http://127.0.0.1:{port}/{path}", wait_until="networkidle")
        h = pg.locator("h2", has_text="Attestation").first
        h.scroll_into_view_if_needed()
        box = h.bounding_box(); y = box["y"] + pg.evaluate("window.scrollY")
        pg.screenshot(path=f"{out}/{name}-attestation.png", full_page=True, clip={"x": 0, "y": y - 10, "width": 1440, "height": 260})
        print(name, pg.locator("h2:has-text('Attestation') + *").first.inner_text()[:300].replace("\n", " | "))
    b.close()
srv.shutdown()
