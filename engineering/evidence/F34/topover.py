import functools, http.server, socketserver, sys, threading, json
from playwright.sync_api import sync_playwright

root, path = sys.argv[1], sys.argv[2]
JS = """() => { const vw = document.documentElement.clientWidth; const out = []; const seen = new Set();
  for (const el of document.querySelectorAll('main *')) { const r = el.getBoundingClientRect();
    const p = el.parentElement.getBoundingClientRect();
    if (r.right > vw + 1 && p.right <= vw + 1) { const path = []; for (let e = el; e && e.tagName !== 'MAIN'; e = e.parentElement) path.unshift(e.tagName.toLowerCase() + (typeof e.className === 'string' && e.className ? '.' + e.className.split(' ').join('.') : ''));
      const k = path.slice(-4).join(' > '); if (!seen.has(k)) { seen.add(k); out.push({path: path.slice(-5).join(' > '), right: Math.round(r.right), pos: getComputedStyle(el).position, disp: getComputedStyle(el).display}); } } }
  return out.slice(0, 12); }"""
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
h.log_message = lambda *a: None
with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 900})
        pg.goto(
            f"http://127.0.0.1:{srv.server_address[1]}{path}", wait_until="load", timeout=180000
        )
        pg.wait_for_timeout(1500)
        print(pg.evaluate("document.documentElement.scrollWidth"))
        print(json.dumps(pg.evaluate(JS), ensure_ascii=False, indent=1))
        b.close()
