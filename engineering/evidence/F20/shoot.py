"""F20-T8 screenshots and measurements (R13, R14): glosses beside the Lean, explainer versions.

Builds the site tests' F20 fixture (``site/tests/gloss_fixture.py``: a drafted, revised and signed
gloss with a second chain on the tutorial's statement, a gloss of a since-filled witness, a
relation's draft, a definition module's gloss, a curated root with a steward's gloss, and an
explainer chain — draft, signed revision, withdrawn third version — anchored to the tutorial's
outline), renders it, serves it, and captures each page at desktop and phone width; the node pages
once as they load and once with every ``<details>`` opened. Measures what the eye misses
(engineering/CLAUDE.md, 2026-09-18 and 2026-09-19): the page's scrollWidth against the viewport,
every label, version line, step list and row gloss against its own box and the viewport, where an
anchored section's steps sit against its words (beside on a desktop, above on a phone), and the
``<math>`` KaTeX wrote. Prints one JSON document and writes it beside the shots; exit 1 when a
measurement fails.

    UV_PROJECT_ENVIRONMENT=<repo>/.venv uv run --frozen --with playwright \
        python engineering/evidence/F20/shoot.py --out engineering/evidence/F20 --prefix task-8
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

import gloss_fixture  # noqa: E402 — site/tests, on the path just above
from playwright.sync_api import Page, sync_playwright  # noqa: E402

from opn_site import model, render  # noqa: E402

WIDTHS = {"desktop": 1440, "phone": 390}
LABELS = (
    ".block-label, summary, .version-facts, .ex-steps li, .ex-prose h3, .gloss-line, "
    ".gloss-foot, .explainer-of, .deps li, .gloss-slot > .cue"
)
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
  out.slots = document.querySelectorAll('.gloss-slot').length;
  out.glosses = document.querySelectorAll('.gloss').length;
  out.cues = [...document.querySelectorAll('.gloss-slot > .cue')].length;
  out.row_glosses = document.querySelectorAll('.stmt .gloss-line').length;
  out.math_spans = document.querySelectorAll('.math').length;
  out.mathml = document.querySelectorAll('.math math').length;
  // An anchored section: where its step list sits against its words.
  out.sections = [...document.querySelectorAll('.ex-section')]
    .filter(s => s.querySelector('.ex-steps'))
    .map(s => {
      const a = s.querySelector('.ex-steps').getBoundingClientRect();
      const b = s.querySelector('.ex-prose').getBoundingClientRect();
      return {steps: s.dataset.steps, beside: a.right <= b.left + 1 && a.top < b.bottom,
              above: a.bottom <= b.top + 1};
    });
  out.blocks = [...document.querySelectorAll('[data-block]')].map(b => {
    const p = b.querySelector('.block-label');
    return {block: b.dataset.block, label: p ? p.querySelector('strong').textContent : null};
  });
  out.inputs = document.querySelectorAll(
    'main form, main input, main textarea, main select').length;
  return out;
}"""


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def build(work: Path) -> tuple[Path, list[str]]:
    """The rendered fixture site and the paths to shoot."""
    root = gloss_fixture.glossed_tree(work / "graph-src")
    site = model.load_site(root, gloss_fixture.COMMIT)
    out = work / "site"
    render.write(render.render_site(site, repo_url="https://github.com/example/graph"), out)
    return out, gloss_fixture.shoot_paths(root)


def shoot(page: Page, url: str, shot: Path, *, expand: bool) -> dict[str, Any]:
    page.goto(url, wait_until="networkidle")
    if expand:
        page.evaluate("() => document.querySelectorAll('details').forEach(d => d.open = true)")
    m: dict[str, Any] = page.evaluate(MEASURE, LABELS)
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
                    for expand in (False, True) if path.startswith("/nodes/") else (False,):
                        shot = (
                            args.out / f"{args.prefix}-{slug}-{name}{'-open' if expand else ''}.png"
                        )
                        m = shoot(page, origin + path, shot, expand=expand)
                        ok = m["scrollWidth"] <= width and not m["overflowing"]
                        if m["math_spans"]:
                            ok = ok and m["mathml"] > 0
                        unlabelled = [b["block"] for b in m["blocks"] if not b["label"]]
                        ok = ok and not unlabelled
                        # D-36: the pages that show glosses and explainers take no input. (The
                        # Problems page's hidden search box is F04's, and accepts nothing.)
                        if "/nodes/" in path or "/proofs/" in path:
                            ok = ok and m["inputs"] == 0
                        placed = "beside" if name == "desktop" else "above"
                        ok = ok and all(s[placed] for s in m["sections"])
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
