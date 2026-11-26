"""At 390px, list elements whose right edge passes the viewport and are not inside a box that scrolls."""

import functools, http.server, socketserver, sys, threading, json
from playwright.sync_api import sync_playwright

root, paths = sys.argv[1], sys.argv[2].split(",")
JS = """() => {
  const vw = document.documentElement.clientWidth, out = [];
  const scrolls = el => { for (let p = el.parentElement; p; p = p.parentElement) {
      const s = getComputedStyle(p); if (/(auto|scroll|hidden)/.test(s.overflowX) && p !== document.body && p !== document.documentElement) return true; } return false; };
  for (const el of document.querySelectorAll('main *, header *, footer *')) {
    const r = el.getBoundingClientRect();
    if (r.width && r.right > vw + 1 && !scrolls(el)) {
      const parentOver = el.parentElement && el.parentElement.getBoundingClientRect().right > vw + 1 && !scrolls(el.parentElement);
      if (!parentOver) out.push({tag: el.tagName.toLowerCase(), cls: el.className && el.className.baseVal === undefined ? el.className : '', right: Math.round(r.right), text: (el.textContent||'').trim().slice(0,60)});
    }
  }
  return {scrollWidth: document.documentElement.scrollWidth, culprits: out.slice(0, 12)};
}"""
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
h.log_message = lambda *a: None
with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        for path in paths:
            pg = b.new_page(viewport={"width": 390, "height": 900})
            pg.goto(
                f"http://127.0.0.1:{srv.server_address[1]}{path}", wait_until="load", timeout=180000
            )
            print(path, json.dumps(pg.evaluate(JS), ensure_ascii=False, indent=1))
        b.close()
