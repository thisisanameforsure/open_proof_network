"""F34-T9 (R10-R12): Contributors credits people — stewards first, then the people who bring
agents, then the full ledger, folded. Nobody is ranked.

* Stewards come from the steward records the problem pages use; each person once, with every
  problem they hold, and a card for the problems that need one.
* One card per operator (until operator records group identities, T14, one per identity), sorted
  by last activity, never by a count: a sentence of counts by ledger line, the frameworks and
  models from the entries' ``automation`` blocks with model names normalised, the problems worked
  on, and the identities credited.
* An identity matching the site's test pattern (``tester-*``, F34-Q4) is in no card or count until
  "Show test runs" is on, and always in the full ledger.
* The full ledger is a closed ``<details>``, every entry listed, a revoked one marked.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fixture
import pytest
from harness import TARGET
from test_f34_codes import visible_codes

from opn_gate import schemas
from opn_site import model, render

REPO = "https://github.com/example/graph"


def entry(target: str, node: str, date: str, line: str = "proof", **kw: Any) -> dict[str, Any]:
    return {
        "line": line,
        "target": target,
        "node": node,
        "artifact": "Proof.lean",
        "merge_commit": "1" * 40,
        "date": date,
        "tooling": "undeclared",
        "status": "active",
        "automation": None,
        **kw,
    }


def write_ledger(root: Path, identity: str, entries: list[dict[str, Any]]) -> None:
    (root / "ledger").mkdir(parents=True, exist_ok=True)
    doc = {"schema": "ledger/v2", "identity": identity, "entries": entries}
    (root / "ledger" / f"{identity}.json").write_bytes(schemas.canonical_json(doc))


def auto(*models: str, framework: str = "Claude Code 2.1") -> dict[str, Any]:
    return {"method": "agent", "models": list(models), "framework": framework}


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, str]:
    root = fixture.build_with_stewards(tmp_path_factory.mktemp("f34-contributors"))
    t = TARGET
    write_ledger(
        root,
        "alice",
        [
            entry(t, "and-reassoc", "2026-09-10T12:00:00Z", automation=auto("claude-opus-5-5")),
            entry(
                t,
                "and-reassoc",
                "2026-09-12T12:00:00Z",
                automation=auto("Claude Opus 5.5 (claude-opus-5-5)", framework="Claude Code"),
            ),
            entry(t, "and-swap-reassoc", "2026-09-11T08:00:00Z", line="attempts"),
        ],
    )
    write_ledger(
        root,
        "bob",
        [
            entry(
                t,
                "and-reassoc",
                "2026-10-01T09:00:00Z",
                automation=auto("aristotle (Harmonic)"),
            ),
            entry(
                t, "and-swap-reassoc", "2026-08-01T09:00:00Z", line="statement", status="revoked"
            ),
        ],
    )
    write_ledger(root, "tester-x", [entry(t, "and-reassoc", "2026-11-01T09:00:00Z")])
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO)["contributors/index.html"]


def section(page: str, name: str) -> str:
    start = page.index(f'data-section="{name}"')
    end = page.find("data-section=", start + 1)
    return page[start : end if end != -1 else len(page)]


def test_the_page_says_who_is_credited_and_that_nobody_is_ranked(
    built: tuple[model.Site, str],
) -> None:
    _site, page = built
    assert "Agents are tools; the person who runs them is credited. Nobody is ranked." in page


def test_stewards_come_first_each_once_with_their_problems(built: tuple[model.Site, str]) -> None:
    site, page = built
    stewards = section(page, "stewards")
    assert page.index('data-section="stewards"') < page.index('data-section="people"')
    logins = {str(s["login"]) for tv in site.targets.values() for s in tv.stewards}
    assert logins, "guard: the fixture has a steward"
    for login in logins:
        assert stewards.count(f'data-steward="{login}"') == 1, login
        held = [
            tid for tid, tv in site.targets.items() if login in {s["login"] for s in tv.stewards}
        ]
        for tid in held:
            assert f'href="/problems/{tid}/"' in stewards, (login, tid)
    assert 'href="/steward/"' in stewards and "need a steward" in stewards


def test_one_card_per_person_by_last_activity(built: tuple[model.Site, str]) -> None:
    _site, page = built
    people = section(page, "people")
    shown = [
        m for m in re.findall(r'<article class="person"[^>]*>', people) if "data-test" not in m
    ]
    names = [re.search(r'data-operator="([^"]+)"', m).group(1) for m in shown]  # type: ignore[union-attr]
    lasts = [re.search(r'data-last="([^"]*)"', m).group(1) for m in shown]  # type: ignore[union-attr]
    assert names == ["bob", "alice"], names  # newest first: 2026-10-01, then 2026-09-12
    assert lasts == sorted(lasts, reverse=True)


def test_a_card_counts_in_words_and_lists_tools_and_problems(built: tuple[model.Site, str]) -> None:
    _site, page = built
    alice = re.search(
        r'<article class="person[^"]*" data-operator="alice".*?</article>', page, re.S
    )
    assert alice is not None
    card = alice.group(0)
    assert "2 proofs and 1 failed attempt kept, on 1 problem." in card
    assert "claude-opus-5-5 · 2" in card  # two spellings, one model
    assert "Claude Code · 2" in card  # a version is not a different framework
    assert 'href="/problems/propositional/"' in card


def test_model_names() -> None:
    norm = render.canonical_model
    assert norm("claude-opus-5-5") == norm("Claude Opus 5.5 (claude-opus-5-5)") == "claude-opus-5-5"
    assert norm("aristotle (Harmonic)") == norm("Aristotle (Harmonic, leanprover/lean4:v4.28.0)")
    assert norm("Aristotle (Harmonic)") == "aristotle"
    assert (
        len(
            {
                norm(m)
                for m in (
                    "claude-opus-5-5",
                    "Claude Opus 5.5 (claude-opus-5-5)",
                    "aristotle (Harmonic)",
                    "Aristotle (Harmonic, leanprover/lean4:v4.28.0)",
                )
            }
        )
        == 2
    )
    assert render.canonical_framework("Claude Code 2.1") == "Claude Code"
    assert render.canonical_framework("Claude Code (Agent SDK subagent)") == "Claude Code"


def test_test_runs_hidden(built: tuple[model.Site, str]) -> None:
    _site, page = built
    people = section(page, "people")
    tester = re.search(r'<article class="person[^"]*" data-operator="tester-x"[^>]*>', people)
    assert (
        tester is not None and " hidden" in tester.group(0) and 'data-test="1"' in tester.group(0)
    )
    assert "Show test runs" in people
    ledger = section(page, "ledger")
    assert "tester-x" in ledger  # the full ledger lists everyone


def test_the_full_ledger_is_folded_and_marks_revoked_entries(built: tuple[model.Site, str]) -> None:
    _site, page = built
    ledger = section(page, "ledger")
    fold = re.search(r"<details[^>]*>", ledger)
    assert fold is not None and " open" not in fold.group(0)
    rows = re.findall(r'<tr data-identity="([^"]+)"', ledger)
    assert sorted(rows) == ["alice", "alice", "alice", "bob", "bob", "tester-x"]
    assert "revoked" in ledger
    assert 'name="ledger-q"' in ledger


def test_no_internal_codes(built: tuple[model.Site, str]) -> None:
    _site, page = built
    assert visible_codes(page) == []


# --- F34-T14 (R23; D-19 v3.51 (iii)): identities under their operator ---------------------------


def write_yaml(root: Path, rel: str, doc: dict[str, Any]) -> None:
    import yaml  # noqa: PLC0415

    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def name_record(
    pseudonym: str, *, name: str | None = None, github: str | None = None
) -> dict[str, Any]:
    """A display-name/v2 record as the service files it; the site reads it, the gate checks it."""
    return {
        "schema": "display-name/v2",
        "pseudonym": pseudonym,
        "name": name,
        "link": None,
        "github": github,
        "date": "2026-11-25",
        "via": "approval-key",
        "key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKHDEGJlALYV4+SkVajmPDtD/Pu6CMzBMnH36leBU0mr",
        "signature": "-----BEGIN SSH SIGNATURE-----\nU1NIU0lH\n-----END SSH SIGNATURE-----\n",
    }


@pytest.fixture(scope="module")
def grouped(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = fixture.build_with_stewards(tmp_path_factory.mktemp("f34-operators"))
    for who, day in (
        ("op-a1", "10"),
        ("op-a2", "12"),
        ("op-self", "05"),
        ("gh-1", "01"),
        ("gh-2", "03"),
    ):
        write_ledger(root, who, [entry(TARGET, "and-reassoc", f"2026-10-{day}T09:00:00Z")])
    write_ledger(root, "tester-op", [entry(TARGET, "and-reassoc", "2026-11-20T09:00:00Z")])
    write_yaml(
        root,
        "operators/op-self/20261125T120000Z-founder.yaml",
        {
            "schema": "operator/v1",
            "operator": "op-self",
            "identities": ["op-a1", "op-a2", "tester-op"],
            "reason": "one person ran all three",
            "author": "founder",
            "date": "2026-11-25",
        },
    )
    write_yaml(root, "names/op-self.yaml", name_record("op-self", name="Ada Operator"))
    write_yaml(root, "names/gh-1.yaml", name_record("gh-1", github="grace-h"))
    write_yaml(root, "names/gh-2.yaml", name_record("gh-2", github="grace-h"))
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO)["contributors/index.html"]


def people_cards(page: str) -> dict[str, str]:
    return {
        m.group(1): m.group(0)
        for m in re.finditer(
            r'<article class="person"[^>]*data-operator="([^"]+)".*?</article>',
            section(page, "people"),
            re.S,
        )
    }


def test_an_operator_record_puts_its_identities_under_one_card(grouped: str) -> None:
    cards = people_cards(grouped)
    assert "op-a1" not in cards and "op-a2" not in cards
    card = cards["op-self"]
    assert "Ada Operator" in card  # the display name the operator recorded
    assert "3 proofs" in card  # its own and its two identities' (the test run is not counted)
    assert "op-a1" in card and "op-a2" in card  # the identities, folded in the card


def test_identities_with_one_github_login_are_one_person(grouped: str) -> None:
    cards = people_cards(grouped)
    github = [k for k, v in cards.items() if "grace-h" in v]
    assert len(github) == 1, github
    card = cards[github[0]]
    assert "2 proofs" in card and "gh-1" in card and "gh-2" in card
    assert "GitHub · <code>grace-h</code>" in card


def test_a_test_run_is_never_counted_into_a_person(grouped: str) -> None:
    cards = people_cards(grouped)
    assert "tester-op" in cards and 'data-test="1"' in cards["tester-op"]
    assert "tester-op" not in cards["op-self"].split("</p>", 3)[-1].split("Identities", 1)[0]
