"""F22 screenshots and measurements (T15-T19), rendered from the live graph's products.

Renders the site from a detached worktree of the graph at ``--commit`` (the caller makes and
removes it; this script never touches a graph checkout), serves it, and captures at 1440 and 390:
erdos-1050's problem page, the h3 and h1-v2 node pages, the proof's reading view and a spec node.
For each it measures what the eye misses (engineering/CLAUDE.md, 2026-09-18 and 2026-09-19):
``scrollWidth`` against the viewport, KaTeX's ``<math>`` output and ``.katex-error`` count, the
lists the words now render, literal Markdown left on the page outside Lean, code and diffs, the
withdrawn-chain line (T16), the sections' words-before-steps order on a phone (T18 R), the graph's
drawn label size on a phone, and inputs inside ``<main>`` (D-36).

T19 (words in review) is driven with the service's address set, and the fetch the page makes is
answered by Playwright with a listing in the service's shape: on 2026-10-06 the live queue was
empty and the deployed service had neither the filters nor CORS yet (both are the SVC agent's
half, not yet deployed), so no live pull request could be shown. The answer is recorded beside
the shots.

    uv run --frozen --with playwright python engineering/evidence/F22/shoot.py \
        --graph <worktree> --commit <sha> --out engineering/evidence/F22 --prefix shots
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
for rel in ("gate", "site"):
    sys.path.insert(0, str(REPO_ROOT / rel))

from playwright.sync_api import Page, Route, sync_playwright  # noqa: E402

from opn_site import model, render  # noqa: E402

WIDTHS = {"desktop": 1440, "phone": 390}
TARGET = "erdos-1050"
API = "https://api.example.invalid"
REPO = "https://github.com/thisisanameforsure/open_proof_network_graph"
#: The listing the T19 fetch is answered with: the service's ``submissions.json`` shape, filtered.
LISTING = {
    "open": [
        {
            "kind": "gloss",
            "target_id": TARGET,
            "node_id": "erdos-1050--h1-v2--h3",
            "pr_number": 999,
            "pr_url": f"{REPO}/pull/999",
            "pseudonym": "f22-shoot",
        },
        {
            "kind": "explainer",
            "target_id": TARGET,
            "node_id": "erdos-1050--h1-v2--h3",
            "pr_number": 1000,
            "pr_url": f"{REPO}/pull/1000",
            "pseudonym": "f22-shoot",
        },
    ]
}
MEASURE = """() => {
  const vw = document.documentElement.clientWidth;
  const main = document.querySelector('main');
  const strip = (root) => {
    const c = root.cloneNode(true);
    c.querySelectorAll('pre, code, .diff, details.diff, .katex, script').forEach(e => e.remove());
    return c.textContent;
  };
  const words = [...document.querySelectorAll('.prose, .ex-prose, .gloss-prose')];
  const text = words.map(strip).join('\\n');
  const out = {
    viewport: vw, scrollWidth: document.documentElement.scrollWidth,
    math_spans: document.querySelectorAll('.math').length,
    mathml: document.querySelectorAll('.math math').length,
    katex_errors: document.querySelectorAll('.katex-error').length,
    lists_in_words: words.reduce((n, w) => n + w.querySelectorAll('ul, ol').length, 0),
    literal_bold: (text.match(/\\*\\*/g) || []).length,
    literal_dash_paragraphs: words.reduce((n, w) =>
      n + [...w.querySelectorAll('p')].filter(p => /^- /.test(p.textContent)).length, 0),
    bare_withdrawn: document.body.textContent.includes('Every version of this explainer is withdrawn'),
    withdrawn_lines: document.querySelectorAll('.withdrawn-chain').length,
    sorry_notes: document.querySelectorAll('.sorry-note').length,
    inputs: main ? main.querySelectorAll('form, input, textarea, select, button').length : 0,
    in_review: [...document.querySelectorAll('.in-review')].filter(e => !e.hidden)
      .map(e => e.textContent),
  };
  out.sections_words_first = [...document.querySelectorAll('.ex-section')]
    .filter(s => s.querySelector('.ex-steps') && s.offsetParent)
    .map(s => {
      const a = s.querySelector('.ex-steps').getBoundingClientRect();
      const b = s.querySelector('.ex-prose').getBoundingClientRect();
      return {beside: a.right <= b.left + 1 && a.top < b.bottom, words_first: b.bottom <= a.top + 1};
    });
  const label = document.querySelector('svg.dag text');
  if (label) {
    const svg = document.querySelector('svg.dag');
    const scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
    out.dag_label_px = Math.round(13 * scale * 10) / 10;
  }
  return out;
}"""


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def paths(site: model.Site) -> dict[str, str]:
    tv = site.targets[TARGET]
    proofs = list(tv.graph.get("target_proofs") or [])
    reading = f"/problems/{TARGET}/proofs/{str(proofs[0]['artifact_hash'])[:12]}/"
    return {
        "problem": f"/problems/{TARGET}/",
        "h3": f"/nodes/{TARGET}/erdos-1050--h1-v2--h3/",
        "h1v2": f"/nodes/{TARGET}/erdos-1050--h1-v2/",
        "reading": reading,
        "spec": f"/nodes/{TARGET}/spec-440db0f9/",
    }


def answer(route: Route) -> None:
    route.fulfill(
        status=200,
        content_type="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
        body=json.dumps(LISTING),
    )


#: Where each page's change is, so a second capture shows it rather than the page's top.
FOCUS = {
    "problem": ".proved-in-words",
    "h3": ".withdrawn-chain",
    "h1v2": ".deps",
    "reading": ".rv-toc",
    "spec": ".ex-section",
}
#: A third capture for the pages whose words carry lists and math.
WORDS = {
    "problem": ".dag-wrap",
    "h3": ".in-review:not([hidden])",
    "h1v2": ".gloss-prose ul",
    "reading": ".rv-order",
    "spec": ".gloss-prose",
}


def shoot(page: Page, url: str, shot: Path, slug: str) -> dict[str, Any]:
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(300)
    m: dict[str, Any] = page.evaluate(MEASURE)
    page.screenshot(path=str(shot), full_page=False)
    for suffix, selector in (("focus", FOCUS.get(slug)), ("words", WORDS.get(slug))):
        if selector is None or page.locator(selector).count() == 0:
            continue
        page.locator(selector).first.scroll_into_view_if_needed()
        page.evaluate("() => window.scrollBy(0, -80)")
        page.screenshot(path=str(shot.with_name(shot.stem + f"-{suffix}.png")), full_page=False)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", required=True, type=Path)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--prefix", required=True)
    args = ap.parse_args()
    site = model.load_site(args.graph, args.commit)
    report: dict[str, Any] = {"commit": args.commit, "listing": LISTING, "shots": [], "ok": True}
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        out = Path(tmp) / "site"
        render.write(render.render_site(site, repo_url=REPO, api_url=API), out)
        server, port = serve(out)
        origin = f"http://127.0.0.1:{port}"
        browser = p.chromium.launch()
        for name, width in WIDTHS.items():
            phone = name == "phone"
            context = browser.new_context(
                viewport={"width": width, "height": 1000}, has_touch=phone, is_mobile=phone
            )
            context.route(f"{API}/submissions.json**", answer)
            page = context.new_page()
            for slug, path in paths(site).items():
                shot = args.out / f"{args.prefix}-{slug}-{name}.png"
                m = shoot(page, origin + path, shot, slug)
                # D-36's no-input rule is the record pages' (node, reading view); the problem
                # page's proof picker and graph toggle are buttons by design (F18, F04-T33).
                inputs_ok = slug == "problem" or m["inputs"] == 0
                ok = m["scrollWidth"] <= width and m["katex_errors"] == 0 and inputs_ok
                ok = ok and (m["mathml"] > 0 or m["math_spans"] == 0)
                ok = ok and not m["bare_withdrawn"] and m["literal_dash_paragraphs"] == 0
                if phone:
                    ok = ok and all(s["words_first"] for s in m["sections_words_first"])
                if slug == "h3":
                    ok = ok and len(m["in_review"]) == 2
                report["ok"] = report["ok"] and ok
                report["shots"].append(
                    {"page": slug, "width": width, "file": shot.name, "ok": ok, **m}
                )
            context.close()
        browser.close()
        server.shutdown()
    text = json.dumps(report, indent=1, ensure_ascii=False) + "\n"
    (args.out / f"{args.prefix}-measurements.json").write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
