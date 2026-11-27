import functools, http.server, json, socketserver, subprocess, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from opn_site import config, model, render
graph = Path(sys.argv[1])
commit = subprocess.run(["git","-C",str(graph),"rev-parse","HEAD"],capture_output=True,text=True,check=True).stdout.strip()
files = render.render_site(model.load_site(graph, commit), repo_url="https://github.com/example/graph", featured_target=config.DEFAULT_FEATURED_TARGET)
PROBE = """() => {
  const sel = 'main button, main [role=button], main [role=tab], main summary, main ol.route-outline > li > a, main .btn, main a.act, main select, main input';
  const out = {};
  for (const el of document.querySelectorAll(sel)) {
    if (el.closest('[hidden]') || getComputedStyle(el).display === 'none') continue;
    const r = el.getBoundingClientRect(); if (!r.width) continue;
    if (Math.min(r.height, 1e9) < 44 ) {
      const k = (el.tagName.toLowerCase() + '.' + (el.getAttribute('class')||'').split(' ')[0] + (el.closest('svg') ? ' (svg:' + el.closest('svg').getAttribute('class') + ')' : ''));
      out[k] = out[k] || {n:0, h: Math.round(r.height), w: Math.round(r.width)}; out[k].n++;
    }
  }
  return out;
}"""
with tempfile.TemporaryDirectory() as tmp:
    render.write(files, Path(tmp))
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp); h.log_message = lambda *a: None
    with socketserver.TCPServer(("127.0.0.1", 0), h) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": 390, "height": 900})
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/problems/erdos-257/"); pg.wait_for_timeout(800)
            print(json.dumps(pg.evaluate(PROBE), indent=1)); b.close()
