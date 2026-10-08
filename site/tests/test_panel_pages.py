"""F24-T6 / AC10: the panel, its motions, the write-up ladder and the rules page, from a v9 index.

The index is ``panel_fixture``'s, written by hand and validated against the published schema
here, so the site is checked against the contract rather than against what one gate commit
happens to write. The controls (vote, invite, accept, the write-up acts) are drawn by
``panel.js`` only once the service answers (F23-R15), so the static page carries none of them:
the browser half is in ``test_web_flows.py``.
"""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

import panel_fixture as pf
import pytest
from fixture import COMMIT, STEWARD_LOGIN, STEWARDED_TARGET, STEWARDLESS_TARGET

from opn_gate import schemas
from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.org"
POLICY_SCHEMA = Path(schemas.__file__).parent.parent / "schemas" / "policy" / "v3.json"
LADDER = (
    "drafted",
    "written",
    "steward-signed",
    "panel-verified",
    "released",
    "on-arxiv",
    "submitted",
    "accepted",
)


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return pf.build(tmp_path_factory.mktemp("panel"))


@pytest.fixture(scope="module")
def pages(root: Path) -> dict[str, str]:
    return render.render_site(model.load_site(root, COMMIT), repo_url=REPO, api_url=API)


def section(page: str, sid: str) -> str:
    start = page.index(f'<h2 id="{sid}">')
    end = page.find("<h2", start + 1)
    return page[start : end if end >= 0 else len(page)]


@pytest.fixture(scope="module")
def panel(pages: dict[str, str]) -> str:
    return section(pages[f"problems/{STEWARDED_TARGET}/index.html"], "panel")


@pytest.fixture(scope="module")
def writeup(pages: dict[str, str]) -> str:
    return section(pages[f"problems/{STEWARDED_TARGET}/index.html"], "writeup")


def test_the_hand_built_index_is_a_valid_v9(root: Path) -> None:
    doc = json.loads((root / "targets" / "index.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "targets-index/v9"
    schemas.validate(doc, "targets-index/v9")  # raises on any departure from the contract


# --- the panel -----------------------------------------------------------------------------


def test_members_are_listed_and_the_lapsed_steward_apart(panel: str) -> None:
    members = panel[panel.index('<ul class="panel-members">') :]
    members = members[: members.index("</ul>")]
    assert (
        f"<code>{STEWARD_LOGIN}</code>" in members and f"<code>{pf.SECOND_MEMBER}</code>" in members
    )
    assert pf.LAPSED_LOGIN not in members
    lapsed = panel[panel.index('class="panel-lapsed"') :]
    assert f"<code>{pf.LAPSED_LOGIN}</code>" in lapsed
    assert "lapsed" in lapsed.lower() and "last act 2026-01-03" in lapsed


def test_the_open_motion_in_plain_words_with_its_tally(panel: str) -> None:
    opened = panel[panel.index('<ul class="motions open">') :]
    opened = opened[: opened.index("</ul>")]
    assert f"Invite <code>{pf.INVITEE}</code> — {escape(pf.NOTE)}" in opened
    assert "closes 2026-10-19" in opened and "1 yes · 0 no so far" in opened
    assert "<script>" not in panel


def test_decided_motions_show_their_outcome_and_the_uncounted_voter(panel: str) -> None:
    decided = panel[panel.index('<ul class="motions decided">') :]
    decided = decided[: decided.index("</ul>")]
    assert f"Verify the write-up \u2018{escape(pf.TITLE)}\u2019" in decided
    assert "Set the authorship threshold to 0.1" in decided
    assert '<span class="outcome passed">passed</span>, 2 yes · 0 no' in decided
    assert '<span class="outcome failed">failed</span>, 1 yes · 1 no' in decided
    assert f"voted, not counted (helped prove it): <code>{pf.PROVER}</code>" in decided


def test_the_panel_links_the_rules(panel: str) -> None:
    assert 'href="/rules/"' in panel


def test_the_controls_are_not_in_the_static_page(pages: dict[str, str], panel: str) -> None:
    """R9 via F23-R15: an empty slot carrying data; panel.js draws every control."""
    for markup in ("<button", "<input", "<form", "<textarea", "<select"):
        assert markup not in panel
    page = pages[f"problems/{STEWARDED_TARGET}/index.html"]
    slot = re.search(r'<div class="panel-ctl"[^>]*>', page)
    assert slot is not None and f'data-target="{STEWARDED_TARGET}"' in slot.group(0)
    assert '<script src="/panel.js"' in page


def test_with_no_service_there_is_no_panel_script(root: Path) -> None:
    page = render.render_site(model.load_site(root, COMMIT), repo_url=REPO)[
        f"problems/{STEWARDED_TARGET}/index.html"
    ]
    assert "/panel.js" not in page


# --- the write-up --------------------------------------------------------------------------


def test_the_official_writeup_is_linked_and_escaped(writeup: str) -> None:
    assert f'<a href="https://example.org/writeups/1.pdf">{escape(pf.TITLE)}</a>' in writeup
    assert "<b>the lemma</b>" not in writeup
    assert escape(pf.JOURNAL) in writeup and "<i>Mathematics</i>" not in writeup
    assert f'href="https://arxiv.org/abs/{pf.ARXIV}"' in writeup
    assert f'href="https://doi.org/{pf.DOI}"' in writeup


def test_the_official_writeup_sits_on_the_whole_ladder(writeup: str) -> None:
    ladder = writeup[writeup.index('<ol class="ladder"') :]
    ladder = ladder[: ladder.index("</ol>")]
    rungs = re.findall(r'<li class="rung ([a-z ]+)"[^>]*>([a-z-]+)', ladder)
    assert [r[1] for r in rungs] == list(LADDER)
    assert [r[0] for r in rungs].count("reached") == 1
    assert dict((w, c) for c, w in rungs)["accepted"] == "reached"


def test_authors_signers_and_coauthors(writeup: str) -> None:
    official = writeup[: writeup.index('class="writeups-other"')]
    assert (
        f"Authors: <code>{STEWARD_LOGIN}</code> (signed), <code>{pf.SECOND_MEMBER}</code> (signed)"
        in official
    )
    assert f"Coauthors: <code>{STEWARD_LOGIN}</code>, <code>{pf.SECOND_MEMBER}</code>" in official


def test_the_other_writeups_with_their_stages(writeup: str) -> None:
    others = writeup[writeup.index('class="writeups-other"') :]
    assert "Write-up 2" in others and "drafted" in others and "claude-fable-5-1" in others
    assert "Write-up 3" in others and "withdrawn" in others
    assert (
        f"<code>{pf.SECOND_MEMBER}</code> (signed), <code>{STEWARD_LOGIN}</code> (not yet signed)"
        in others
    )


def test_no_writeup_says_so(pages: dict[str, str]) -> None:
    w = section(pages[f"problems/{STEWARDLESS_TARGET}/index.html"], "writeup")
    assert "No write-up has been recorded for this problem yet." in w
    p = section(pages[f"problems/{STEWARDLESS_TARGET}/index.html"], "panel")
    assert "No panel yet" in p


# --- the rules page ------------------------------------------------------------------------


def test_every_setting_in_the_schema_is_on_the_rules_page(pages: dict[str, str]) -> None:
    page = pages["rules/index.html"]
    settings = json.loads(POLICY_SCHEMA.read_text(encoding="utf-8"))["properties"]["panel"][
        "properties"
    ]
    assert settings
    for key, spec in settings.items():
        row = page[page.index(f'data-setting="{key}"') :]
        row = row[: row.index("</tr>")]
        assert escape(spec["description"]) in row, key


def test_rules_values_since_and_reason(pages: dict[str, str]) -> None:
    page = pages["rules/index.html"]
    row = page[page.index('data-setting="vote_threshold"') :]
    row = row[: row.index("</tr>")]
    assert "2/3" in row and "2026-10-08" in row and "significant share" in row
    row = page[page.index('data-setting="steward_lapse_days"') :]
    row = row[: row.index("</tr>")]
    assert "180 days" in row and "the default" in row
    assert 'data-setting="steward_admission"' in page


def test_the_footer_links_the_rules(pages: dict[str, str]) -> None:
    for path in ("index.html", "docs/index.html", f"problems/{STEWARDED_TARGET}/index.html"):
        assert 'href="/rules/"' in pages[path].split("<footer", 1)[1], path


# --- /me/ and the Docs -----------------------------------------------------------------------


def test_me_script_lists_votes_and_invitations() -> None:
    js = (Path(render.__file__).parent / "static" / "me.js").read_text(encoding="utf-8")
    assert "Waiting for your vote" in js and "Invitations to accept" in js
    assert "awaiting" in js


def test_docs_stewards_text_names_the_panel(pages: dict[str, str]) -> None:
    docs = pages["docs/index.html"]
    start = docs.index('<h2 id="stewards">')
    s = docs[start : docs.index("<h2", start + 1)]
    assert 'href="/rules/"' in s and "panel" in s and "lapse" in s


def test_a_lapsed_steward_is_not_named_as_a_steward_outside_the_panel(
    pages: dict[str, str], panel: str
) -> None:
    """F24-R4: a lapsed steward is not on the panel and is not a steward for claimability, so
    the page's steward line and the home page's count leave them out; only the panel section
    names them, as lapsed (T6's "not done", fixed at merge)."""
    page = pages[f"problems/{STEWARDED_TARGET}/index.html"]
    outside = page.replace(panel, "")
    assert "Old Hand" not in outside
    assert pf.LAPSED_LOGIN in panel
