"""F23-T9 (R12, R13, R15): what the static node pages and /me/ carry for the words controls.

The controls themselves are drawn by ``words.js`` and ``me.js`` once the service answers (driven
in a browser by test_web_flows.py, AC11). Here, the static half: every shown gloss and explainer
carries an empty, hidden slot with what Edit and Withdraw need, every section that is not final
an empty slot for Approve, and each state reads Draft, Pending or Final; a build with no service
carries no slot at all; /me/ is a shell holding each problem's waiting sections, hidden.
"""

from __future__ import annotations

import json
import re
from html import unescape

import gloss_fixture as gf
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.invalid"
NODE_PAGE = f"nodes/{TARGET}/{gf.TUTORIAL}/index.html"
CTL = re.compile(r'<div class="words-ctl" ([^>]*) hidden></div>')
APPROVE = re.compile(r'<div class="words-approve" ([^>]*) hidden></div>')
ATTR = re.compile(r'([a-z-]+)="([^"]*)"')


def attrs(raw: str) -> dict[str, str]:
    return {k: unescape(v) for k, v in ATTR.findall(raw)}


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root, _ = gf.sectioned_tree(tmp_path_factory.mktemp("words-controls"))
    return render.render_site(model.load_site(root, gf.COMMIT), repo_url=REPO, api_url=API)


def test_every_shown_version_has_an_edit_slot(pages: dict[str, str]) -> None:
    """R12: the statement's gloss and the explainer each carry one slot with the subject, the
    head a new version supersedes, the path a withdrawal names and the words to start from."""
    page = pages[NODE_PAGE]
    slots = [attrs(m) for m in CTL.findall(page)]
    kinds = sorted(s["data-kind"] for s in slots)
    assert kinds == ["explainer", "gloss"], kinds
    for s in slots:
        assert s["data-target"] == TARGET and s["data-node"] == gf.TUTORIAL
        assert re.fullmatch(r"[0-9a-f]{64}", s["data-head"])
        assert s["data-path"].startswith(f"targets/{TARGET}/nodes/{gf.TUTORIAL}/")
        assert s["data-text"].strip()
    gloss = next(s for s in slots if s["data-kind"] == "gloss")
    assert json.loads(gloss["data-subject"]) == {"kind": "statement", "node_id": gf.TUTORIAL}
    assert gloss["data-text"].strip() == gf.GLOSS_VERIFIED
    explainer = next(s for s in slots if s["data-kind"] == "explainer")
    subject = json.loads(explainer["data-subject"])
    assert subject["kind"] == "proof" and re.fullmatch(r"[0-9a-f]{64}", subject["proof"])
    assert page.count('<script src="/words.js"') == 1


def test_each_section_that_is_not_final_has_an_approve_slot(pages: dict[str, str]) -> None:
    """R12: one Approve slot per shown section and per edit awaiting review, each naming its
    section and version; a final section's slot says so, and the script draws nothing there."""
    page = pages[NODE_PAGE]
    slots = [attrs(m) for m in APPROVE.findall(page)]
    explainer = {
        (s["data-section"], s["data-state"]) for s in slots if s["data-kind"] == "explainer"
    }
    assert explainer == {
        (gf.KEY_OVERVIEW, "drafted"),
        (gf.KEY_Q, "written"),
        (gf.KEY_P, "verified"),
        (gf.KEY_P, "pending"),
    }
    gloss = {(s["data-section"], s["data-state"]) for s in slots if s["data-kind"] == "gloss"}
    assert gloss == {("whole", "verified"), ("whole", "pending")}
    for s in slots:
        assert re.fullmatch(r"[0-9a-f]{64}", s["data-version"])


def test_the_states_read_draft_pending_final(pages: dict[str, str]) -> None:
    page = pages[NODE_PAGE]
    assert '<span class="words-word">Draft</span> · written by alice' in page
    assert '<span class="words-word">Draft</span> · drafted, by the model named above' in page
    assert re.search(
        rf'<span class="words-word">Final</span> · read against the Lean by {gf.CURATOR} '
        r"\(\d{4}-\d{2}-\d{2}\)",
        page,
    )
    assert '<span class="words-word">Pending</span> · <strong>Awaiting review</strong>' in page


def test_no_service_no_slot(tmp_path_factory: pytest.TempPathFactory) -> None:
    """C7: without a service address the page is the read-only page, with no slot and no
    script."""
    root, _ = gf.sectioned_tree(tmp_path_factory.mktemp("words-controls-off"))
    files = render.render_site(model.load_site(root, gf.COMMIT), repo_url=REPO)
    page = files[NODE_PAGE]
    assert "words-ctl" not in page and "words-approve" not in page and "/words.js" not in page
    assert "/me.js" not in files["me/index.html"]


def test_the_me_page_is_a_shell_with_the_waiting_sections(pages: dict[str, str]) -> None:
    """R13: /me/ holds, hidden, each problem's sections waiting for approval, linked to their
    page; its script draws the rest once the service answers."""
    page = pages["me/index.html"]
    assert f'<div class="me" data-me data-repo="{REPO}">' in page
    assert '<script src="/me.js"></script>' in page
    waiting = re.search(rf'<ul class="waiting" data-target="{TARGET}" hidden>(.*?)</ul>', page)
    assert waiting is not None
    rows = re.findall(r"<li>(.*?)</li>", waiting.group(1))
    node = f'href="/nodes/{TARGET}/{gf.TUTORIAL}/"'
    keys = [re.search(r"<code>([^<]+)</code>", r) for r in rows if node in r]
    found = sorted(k.group(1) for k in keys if k)
    # The drafted and written sections and the two edits awaiting review; never the final one.
    assert found == sorted([gf.KEY_OVERVIEW, gf.KEY_Q, gf.KEY_P, "whole"]), found
    main = page.split("<main>", 1)[1]
    assert not re.search(r"<(form|input|textarea|select|button)\b", main)
