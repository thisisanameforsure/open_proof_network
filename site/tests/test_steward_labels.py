"""F23-T8 / AC12: every steward the site shows says how they were admitted (R14; D-32 v3.33).

``steward/v2`` carries ``admitted_by``: ``self`` under open admission, or the login of the curator
who merged it under reviewed. A ``steward/v1`` record was merged by a curator before the switch
existed, so it reads "admitted by curator" without a name. The site reads the label from the
record of the commit the steward is active under; the index decides who is active (the gate's
rule), the record only says how they came in.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from fixture import (
    COMMIT,
    STEWARD_LOGIN,
    STEWARDED_TARGET,
    STEWARDLESS_TARGET,
    build_with_stewards,
)

from opn_gate import steward
from opn_site import model, render

REPO = "https://github.com/example/graph"
SELF_LOGIN = "self-steward"
REVIEWED_LOGIN = "reviewed-steward"
CURATOR = "curator-one"


def v2_record(login: str, admitted_by: str, *, action: str = "commit") -> dict[str, object]:
    return {
        "schema": "steward/v2",
        "target": STEWARDLESS_TARGET,
        "action": action,
        "login": login,
        "name": login.replace("-", " ").title(),
        "link": None,
        "commitment": steward.COMMITMENT,
        "date": "2026-10-07",
        "via": "approval-key",
        "admitted_by": admitted_by,
        "key": "ssh-ed25519 AAAA approval",
        "signature": "-----BEGIN SSH SIGNATURE-----\nx\n-----END SSH SIGNATURE-----\n",
    }


def add_v2_stewards(root: Path) -> None:
    """Two v2 commits on the stewardless target — one self-admitted, one admitted by a curator
    (an earlier self commit by the same login stepped down first) — and the index rows the
    products would publish for them."""
    directory = root / "targets" / STEWARDLESS_TARGET / "stewards"
    directory.mkdir(exist_ok=True)
    docs = [
        v2_record(REVIEWED_LOGIN, "self"),
        v2_record(REVIEWED_LOGIN, "self", action="step-down"),
        v2_record(SELF_LOGIN, "self"),
        v2_record(REVIEWED_LOGIN, CURATOR),
    ]
    for n, doc in enumerate(docs, start=1):
        (directory / f"{n}.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    index_path = root / "targets" / "index.json"
    index = json.loads(index_path.read_text())
    for row in index["targets"]:
        if row["target_id"] == STEWARDLESS_TARGET:
            row["stewards"] = [
                {
                    "login": SELF_LOGIN,
                    "name": "Self Steward",
                    "link": "https://orcid.org/0000-0001-0000-0001",
                    "since": "2026-10-07",
                },
                {
                    "login": REVIEWED_LOGIN,
                    "name": "Reviewed Steward",
                    "link": "https://orcid.org/0000-0001-0000-0002",
                    "since": "2026-10-07",
                },
            ]
    index_path.write_text(json.dumps(index))


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = build_with_stewards(tmp_path_factory.mktemp("steward-labels"))
    add_v2_stewards(root)
    return render.render_site(model.load_site(root, COMMIT), repo_url=REPO)


def label_after(text: str, name: str) -> str:
    m = re.search(re.escape(name) + r'</a> <span class="admitted"[^>]*>([^<]+)</span>', text)
    assert m is not None, (name, text[:600])
    return m.group(1)


def test_v2_labels_on_the_problem_page(pages: dict[str, str]) -> None:
    page = pages[f"problems/{STEWARDLESS_TARGET}/index.html"]
    card = page[page.index('<aside class="card steward-card">') :]
    card = card[: card.index("</aside>")]
    section = page[page.index("<h2>Steward</h2>") :]
    for where in (card, section):
        assert label_after(where, "Self Steward") == "self-admitted"
        assert label_after(where, "Reviewed Steward") == f"admitted by {CURATOR}"


def test_v1_reads_admitted_by_curator(pages: dict[str, str]) -> None:
    page = pages[f"problems/{STEWARDED_TARGET}/index.html"]
    assert 'class="admitted" data-admitted="curator">admitted by curator</span>' in page
    assert STEWARD_LOGIN in page


def test_the_problem_cards_carry_the_labels(pages: dict[str, str]) -> None:
    listing = pages["problems/index.html"]
    start = listing.index(f'id="p-{STEWARDLESS_TARGET}"')
    card = listing[start : listing.index("</article>", start)]
    assert label_after(card, "Self Steward") == "self-admitted"
    assert label_after(card, "Reviewed Steward") == f"admitted by {CURATOR}"


def test_every_shown_steward_is_labelled(pages: dict[str, str]) -> None:
    """R14: no steward name is shown on a problem page without its label beside it."""
    for rel, text in pages.items():
        if not rel.startswith("problems/") or not rel.endswith("index.html"):
            continue
        for name in ("Self Steward", "Reviewed Steward"):
            for m in re.finditer(re.escape(name) + "</a>", text):
                after = text[m.end() : m.end() + 40]
                assert after.startswith(' <span class="admitted"'), (rel, after)
