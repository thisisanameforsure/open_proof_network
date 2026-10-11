"""F22-T19 (feature request E; Mike chose live fetch): words in review, on the node page.

Writers and the reader asked to see on a node page that words for it were already in flight
(W1, R1): twenty-five open pull requests on erdos-1050 and nothing on any page said so. The page
stays static (D-36): a small same-origin script fetches the service's open listing for the node,
``<api>/submissions.json?node=<id>&kind=words``, and writes "In review: #N by X" under the
statement's words and under the explainer. The service's address comes from the site's config and
never from a template; with no address there is no script, and without the script, or when the
fetch fails, the page is exactly as rendered. The page's Content-Security-Policy gains one
``connect-src`` for the service's origin, a template parameter rather than a hostname.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import fixture
import pytest
import reading_fixture as rf
from harness import TARGET
from test_finding_csp_fonts import TEMPLATE, check_deploy, directives, served_policy

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.org/prod"
SCRIPT = render.STATIC / "in-review.js"


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return rf.chain_tree(tmp_path_factory.mktemp("in-review"))


def node_page(root: Path, api_url: str | None) -> str:
    pages = render.render_site(
        model.load_site(root, fixture.COMMIT), repo_url=REPO, api_url=api_url
    )
    return pages[f"nodes/{TARGET}/{rf.ROOT}/index.html"]


# --- the markup -----------------------------------------------------------------------------------


def test_a_node_page_carries_the_script_and_its_two_slots(root: Path) -> None:
    page = node_page(root, API)
    tag = re.search(r'<script src="/in-review.js"([^>]*)></script>', page)
    assert tag is not None
    attrs = dict(re.findall(r'data-([a-z]+)="([^"]*)"', tag.group(1)))
    assert attrs == {"api": API, "target": TARGET, "node": rf.ROOT, "repo": REPO}
    slots = re.findall(r'<div class="in-review" data-in-review="([a-z]+)" hidden></div>', page)
    assert slots == ["gloss", "explainer"]
    assert "/in-review.js" in render.SCRIPTS


def test_without_a_service_address_the_page_has_no_script_and_no_slot(root: Path) -> None:
    page = node_page(root, None)
    assert "in-review" not in page


def test_the_address_comes_from_config_never_a_template() -> None:
    for path in render.TEMPLATES.glob("*.html"):
        assert "submissions.json" not in path.read_text(encoding="utf-8"), path.name
    assert "https://" not in SCRIPT.read_text(encoding="utf-8")


# --- the script -----------------------------------------------------------------------------------


def test_the_script_builds_the_endpoint_from_its_data() -> None:
    js = SCRIPT.read_text(encoding="utf-8")
    assert '"/submissions.json?node=" + encodeURIComponent(node) + "&kind=words"' in js
    assert "textContent" in js and "innerHTML" not in js  # contributor names are text, never markup


NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_the_script_renders_in_review_lines_and_leaves_the_page_on_failure(tmp_path: Path) -> None:
    """Drive the script under a minimal DOM: one gloss and one explainer pull request for this
    node and one for another target; then a failed fetch, which must leave the slots hidden."""
    harness = tmp_path / "run.js"
    harness.write_text(
        HARNESS.replace("__SCRIPT__", SCRIPT.as_posix()).replace("__REPO__", REPO),
        encoding="utf-8",
    )
    assert NODE is not None
    out = subprocess.run([NODE, str(harness)], capture_output=True, text=True, check=True).stdout
    lines = out.strip().splitlines()
    assert lines[0] == f"GET {API}/submissions.json?node={rf.ROOT}&kind=words"
    assert lines[1] == f"gloss: visible: In review: #41 → {REPO}/pull/41 by alice <b>"
    assert lines[2] == "explainer: visible: In review: #42 by bob"
    assert lines[3] == "failed: gloss hidden, explainer hidden"


# --- the policy -----------------------------------------------------------------------------------


def test_the_policy_allows_the_service_origin_and_nothing_else() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "ServiceOrigin:" in text  # a parameter, not a hostname
    with_service = directives(served_policy("https://api.example.org"))
    assert with_service["connect-src"] == ["https://api.example.org"]
    without = directives(served_policy(""))
    assert without["connect-src"] == ["'none'"]


def test_the_deploy_check_expects_the_policy_with_the_service_origin() -> None:
    cd = check_deploy()
    assert cd.csp("https://api.example.org/prod") == served_policy("https://api.example.org")
    assert cd.csp(None) == served_policy("")


HARNESS = r"""
const fs = require("fs");
function el(tag, attrs) {
  return {tagName: tag, attrs: attrs || {}, children: [], hidden: false, textContent: "",
          dataset: {}, setAttribute(k, v) { this.attrs[k] = v; },
          appendChild(c) { this.children.push(c); return c; }};
}
function text(n) { return n.textContent + n.children.map(text).join("") +
  (n.attrs.href ? " → " + n.attrs.href : ""); }
function run(fetchImpl, done) {
  const slots = {gloss: el("div"), explainer: el("div")};
  slots.gloss.hidden = true; slots.explainer.hidden = true;
  slots.gloss.dataset.inReview = "gloss"; slots.explainer.dataset.inReview = "explainer";
  global.document = {
    currentScript: {dataset: {api: "https://api.example.org/prod", target: "propositional",
                              node: "and-swap-reassoc", repo: "__REPO__"}},
    querySelectorAll: () => [slots.gloss, slots.explainer],
    createElement: (t) => el(t),
    createTextNode: (s) => ({textContent: s, children: [], attrs: {}}),
  };
  global.fetch = fetchImpl;
  eval(fs.readFileSync("__SCRIPT__", "utf8"));
  setTimeout(() => done(slots), 20);
}
const listing = {open: [
  {kind: "gloss", target_id: "propositional", node_id: "and-swap-reassoc", pr_number: 41,
   pr_url: "__REPO__/pull/41", pseudonym: "alice <b>"},
  {kind: "explainer", target_id: "propositional", node_id: "and-swap-reassoc", pr_number: 42,
   pr_url: "https://elsewhere.example/pull/42", pseudonym: "bob"},
  {kind: "gloss", target_id: "other-target", node_id: "and-swap-reassoc", pr_number: 43,
   pr_url: "__REPO__/pull/43", pseudonym: "carol"},
]};
run((url) => { console.log("GET " + url);
  return Promise.resolve({ok: true, json: () => Promise.resolve(listing)}); }, (s) => {
  for (const k of ["gloss", "explainer"]) {
    console.log(k + ": " + (s[k].hidden ? "hidden" : "visible") + ": " +
                s[k].children.map(text).join(" | "));
  }
  run(() => Promise.reject(new Error("offline")), (f) => {
    console.log("failed: gloss " + (f.gloss.hidden ? "hidden" : "visible") + ", explainer " +
                (f.explainer.hidden ? "hidden" : "visible"));
  });
});
"""
