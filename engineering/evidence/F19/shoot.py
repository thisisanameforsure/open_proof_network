"""F19 screenshots and measurements (AC11): the node page with an outline, and the reading view.

Builds the site tests' fixture graph with the F19 fixtures (an outlined tutorial proof, an
explainer and an annex carrying TeX, and for the reading view a three-node proof chain), renders
it, serves it, and captures each page at desktop and phone width — once as it loads and once with
every ``<details>`` opened. Measures what the eye misses (engineering/CLAUDE.md, 2026-09-18 and
2026-09-19): the page's scrollWidth against the viewport, every outline label and provenance label
against its own box and the viewport, the docstring card on keyboard focus, and the ``<math>``
elements KaTeX wrote (R13's MathML). Prints one JSON document and writes it beside the shots;
exit 1 when a measurement fails.

    UV_PROJECT_ENVIRONMENT=<repo>/.venv uv run --frozen --with playwright \
        python engineering/evidence/F19/shoot.py --out engineering/evidence/F19 --prefix ac11
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
for rel in ("gate", "gate/tests", "site", "site/tests"):
    sys.path.insert(0, str(REPO_ROOT / rel))

import reading_fixture  # noqa: E402 — site/tests, on the path just above
from playwright.sync_api import Page, sync_playwright  # noqa: E402

from opn_site import model, render  # noqa: E402

WIDTHS = {"desktop": 1440, "phone": 390}
LABELS = ".po-routine, .po-note, .po-tag, .block-label, .po-id, .po-kind, summary"
MEASURE = """(labels) => {
  const vw = document.documentElement.clientWidth;
  const out = {viewport: vw, scrollWidth: document.documentElement.scrollWidth, overflowing: []};
  for (const el of document.querySelectorAll(labels)) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;  // inside a closed <details>
    const inline = getComputedStyle(el).display === 'inline';
    const clipped = !inline && el.scrollWidth > el.clientWidth + 1;
    if (r.right > vw + 0.5 || r.left < -0.5 || clipped) {
      out.overflowing.push({label: el.className || el.tagName, text: el.textContent.slice(0, 60),
                            left: Math.round(r.left), right: Math.round(r.right)});
    }
  }
  out.steps = document.querySelectorAll('.po-step').length;
  out.open_steps = document.querySelectorAll('.po-step > details[open]').length;
  out.math_spans = document.querySelectorAll('.math').length;
  out.mathml = document.querySelectorAll('.math math').length;
  out.blocks = [...document.querySelectorAll('[data-block]')].map(b => {
    const p = b.querySelector('.block-label');
    return {block: b.dataset.block, label: p ? p.querySelector('strong').textContent : null};
  });
  return out;
}"""
TOOLTIP = """() => {
  const el = document.querySelector('.term.const');
  if (!el) return null;
  for (let d = el.closest('details'); d; d = d.parentElement.closest('details')) d.open = true;
  el.focus();
  const card = el.querySelector('.term-card');
  const r = card.getBoundingClientRect();
  return {visible: getComputedStyle(card).display !== 'none', left: Math.round(r.left),
          right: Math.round(r.right), viewport: document.documentElement.clientWidth,
          text: card.textContent};
}"""


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def build(work: Path) -> tuple[Path, list[str]]:
    """The rendered fixture site and the paths to shoot."""
    root, pages = reading_fixture.shoot_tree(work / "graph-src")
    site = model.load_site(root, reading_fixture.COMMIT)
    out = work / "site"
    render.write(render.render_site(site, repo_url=reading_fixture.REPO), out)
    return out, pages


def shoot(page: Page, url: str, shot: Path, *, expand: bool) -> dict[str, Any]:
    page.goto(url, wait_until="networkidle")
    if expand:
        page.evaluate("() => document.querySelectorAll('details').forEach(d => d.open = true)")
    m: dict[str, Any] = page.evaluate(MEASURE, LABELS)
    m["tooltip"] = page.evaluate(TOOLTIP) if not expand else None
    page.screenshot(path=str(shot), full_page=True)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--prefix", required=True)
    args = ap.parse_args()
    report: dict[str, Any] = {"shots": [], "ok": True}
    with tempfile.TemporaryDirectory() as tmp:
        site_dir, paths = build(Path(tmp))
        server, port = serve(site_dir)
        origin = f"http://127.0.0.1:{port}"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name, width in WIDTHS.items():
                page = browser.new_page(viewport={"width": width, "height": 900})
                for path in paths:
                    slug = path.strip("/").replace("/", "-")
                    for expand in (False, True):
                        shot = (
                            args.out / f"{args.prefix}-{slug}-{name}{'-open' if expand else ''}.png"
                        )
                        m = shoot(page, origin + path, shot, expand=expand)
                        tip = m.get("tooltip")
                        ok = m["scrollWidth"] <= width and not m["overflowing"]
                        if tip is not None:
                            ok = ok and tip["visible"] and tip["right"] <= tip["viewport"]
                        if m["math_spans"]:
                            ok = ok and m["mathml"] > 0
                        unlabelled = [b["block"] for b in m["blocks"] if not b["label"]]
                        ok = ok and not unlabelled
                        report["ok"] = report["ok"] and ok
                        report["shots"].append(
                            {
                                "path": path,
                                "width": width,
                                "expanded": expand,
                                "file": shot.name,
                                "ok": ok,
                                "unlabelled": unlabelled,
                                **m,
                            }
                        )
                page.close()
            browser.close()
        server.shutdown()
    text = json.dumps(report, indent=1, ensure_ascii=False) + "\n"
    (args.out / f"{args.prefix}-measurements.json").write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
