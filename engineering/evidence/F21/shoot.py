"""F21-T12 screenshots and measurements (R7, R14): words by section, and edits awaiting review.

Builds ``site/tests/gloss_fixture.sectioned_tree`` twice — before review (the tutorial's explainer
shows one section drafted with a model, one written by a person, one verified by a curator, and a
person's edit of the verified one awaiting review; its statement's gloss shows verified words with
an edit awaiting review) and after a curator signs the edit — renders each, serves it, and
captures the tutorial's node page and its proof's reading view at desktop and phone width, the
node page also with every ``<details>`` opened. Measures what the eye misses (engineering/CLAUDE.md,
2026-09-18 and 2026-09-19): scrollWidth against the viewport, every state label, pending edit,
diff and step list against its own box and the viewport, where an anchored section's steps sit
against its words (beside on a desktop, above on a phone), that each pending edit sits below the
section it changes, and that nothing on the page takes input (D-36). Prints one JSON document and
writes it beside the shots; exit 1 when a measurement fails.

    UV_PROJECT_ENVIRONMENT=<repo>/.venv uv run --frozen --with playwright \
        python engineering/evidence/F21/shoot.py --out engineering/evidence/F21 --prefix task-12
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
import reading_fixture  # noqa: E402
from harness import TARGET  # noqa: E402
from playwright.sync_api import Page, sync_playwright  # noqa: E402

from opn_gate import schemas  # noqa: E402
from opn_site import model, render  # noqa: E402

WIDTHS = {"desktop": 1440, "phone": 390}
LABELS = (
    ".block-label, .label, .words-state, .pending-head, pre.diff, .ex-steps li, .ex-prose h3, "
    ".version-facts, summary, .vouched, .gloss-foot"
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
  out.states = [...document.querySelectorAll('.words-state')].map(
    s => ({state: s.dataset.state, text: s.textContent}));
  out.pending = [...document.querySelectorAll('.pending-edit')].map(p => {
    const key = p.dataset.pending;
    const sec = [...document.querySelectorAll('.ex-section')].find(s => s.dataset.key === key);
    const r = p.getBoundingClientRect();
    return {key, text: p.querySelector('.pending-head').textContent.slice(0, 80),
            below_its_section: sec ? sec.getBoundingClientRect().bottom <= r.top + 1 : null};
  });
  out.sections = [...document.querySelectorAll('.ex-section')]
    .filter(s => s.querySelector('.ex-steps'))
    .map(s => {
      const a = s.querySelector('.ex-steps').getBoundingClientRect();
      const b = s.querySelector('.ex-prose').getBoundingClientRect();
      return {key: s.dataset.key, beside: a.right <= b.left + 1 && a.top < b.bottom,
              above: a.bottom <= b.top + 1};
    });
  out.math_spans = document.querySelectorAll('.math').length;
  out.mathml = document.querySelectorAll('.math math').length;
  out.inputs = document.querySelectorAll(
    'main form, main input, main textarea, main select, main button').length;
  return out;
}"""


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def build(work: Path, *, approve_edit: bool) -> tuple[Path, list[str]]:
    """One rendered fixture site and the paths to shoot."""
    root, _ = gloss_fixture.sectioned_tree(work / "graph-src", approve_edit=approve_edit)
    site = model.load_site(root, gloss_fixture.COMMIT)
    out = work / "site"
    render.write(render.render_site(site, repo_url="https://github.com/example/graph"), out)
    proof = gloss_fixture.node_dir(root, gloss_fixture.ROOT) / "Proof.lean"
    reading = reading_fixture.reading_path(TARGET, schemas.content_hash(proof.read_bytes()))
    return out, [
        f"/nodes/{TARGET}/{gloss_fixture.TUTORIAL}/",
        "/" + reading.removesuffix("index.html"),
    ]


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
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for phase, approve in (("before", False), ("after", True)):
            with tempfile.TemporaryDirectory() as tmp:
                site_dir, paths = build(Path(tmp), approve_edit=approve)
                server, port = serve(site_dir)
                origin = f"http://127.0.0.1:{port}"
                for name, width in WIDTHS.items():
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    for path in paths:
                        slug = "node" if path.startswith("/nodes/") else "reading"
                        for expand in (False, True) if slug == "node" else (False,):
                            suffix = "-open" if expand else ""
                            shot = args.out / f"{args.prefix}-{phase}-{slug}-{name}{suffix}.png"
                            m = shoot(page, origin + path, shot, expand=expand)
                            ok = m["scrollWidth"] <= width and not m["overflowing"]
                            ok = ok and m["inputs"] == 0
                            if m["math_spans"]:
                                ok = ok and m["mathml"] > 0
                            placed = "beside" if name == "desktop" else "above"
                            ok = ok and all(s[placed] for s in m["sections"])
                            ok = ok and all(
                                e["below_its_section"] is not False for e in m["pending"]
                            )
                            # Before review there is an edit awaiting review; after, none.
                            ok = ok and (bool(m["pending"]) != approve)
                            report["ok"] = report["ok"] and ok
                            report["shots"].append(
                                {
                                    "phase": phase,
                                    "path": path,
                                    "width": width,
                                    "expanded": expand,
                                    "file": shot.name,
                                    "ok": ok,
                                    **m,
                                }
                            )
                    page.close()
                server.shutdown()
        browser.close()
    text = json.dumps(report, indent=1, ensure_ascii=False) + "\n"
    (args.out / f"{args.prefix}-measurements.json").write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
