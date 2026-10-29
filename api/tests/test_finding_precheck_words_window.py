"""F06-T18's window, narrowed: a words-only merge held every hole-making precheck on its target.

Measured by tester D on erdos-849, 2026-10-27 (F-D6, ``engineering/evidence/testers-2026-10-27-
e849/``): a statement gloss merged on one node, and for 7 min 23 s every skeleton precheck on
*any* node of the target answered ``409 products-pending``, until the next render landed. The
rule of Q23 asks whether the newest commit touching ``targets/<t>/nodes`` precedes the commit that
wrote the products; a gloss lives at ``nodes/<id>/gloss/<hash>.md`` and an explainer at
``nodes/<id>/explainer/<hash>.md``, so a merge of words looked like a merge that changed nodes.

A hole plan reads the target's statements, ``META.yaml``, which node directories exist, annexes
(a skeleton's citation) and the records that derive statuses; it never reads a gloss or an
explainer, or their signatures. Asserted here: when every path the commits after the products
touched under the target's nodes is one of those words files, the job runs at the products
commit as if nothing had moved; any other path, a list the host says may be truncated, a host
that cannot say, or a budget held at the reserve keeps the refusal (C7: say no rather than
guess). The answer for a pair of commits is kept, since commits never change.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from api_fakes import Harness
from test_finding_precheck_hole_commit import BOT, bot_commit_writes_hole
from test_finding_precheck_products_commit import LATER, history, precheck, skeleton
from test_githost_seam import (  # the seam's fixtures, reused as they stand
    BASE_SHA,
    COMMIT_SHA,
    REPO,
    Script,
    clock,
    host,
    install_app,
    pem,
    rsa_key,
    script,
)
from test_precheck import NODE, TARGET

from opn_api.githost import GitHostError, HostBudget, HttpxGitHost

__all__ = ["clock", "host", "pem", "rsa_key", "script"]  # pytest fixtures

#: Another node of the target, where the words merged.
OTHER = "other-node"
NODES = f"targets/{TARGET}/nodes"
GLOSS = f"{NODES}/{OTHER}/gloss/{'1' * 64}.md"
GLOSS_SIGNED = f"{NODES}/{OTHER}/gloss/signed/{'1' * 64}-1.yaml"
EXPLAINER = f"{NODES}/{OTHER}/explainer/{'2' * 64}.md"
EXPLAINER_SIGNED = f"{NODES}/{OTHER}/explainer/signed/{'2' * 64}-1.yaml"


def window(h: Harness, paths: list[str] | None) -> None:
    """``main`` at ``LATER``, whose newest change to the target's nodes came after ``BOT``, the
    commit that wrote the products; the diff between them touched ``paths``."""
    bot_commit_writes_hole(h, head=LATER)
    history(h, head=LATER, products=BOT, nodes=LATER)
    h.githost.ancestry[(LATER, BOT)] = False
    h.githost.diffs[(BOT, LATER)] = paths


def refused(r: httpx.Response) -> None:
    doc: dict[str, Any] = r.json()
    assert (r.status_code, doc.get("error")) == (409, "products-pending"), r.text


def test_a_gloss_only_merge_does_not_hold_a_skeleton(harness: Harness) -> None:
    """The finding: a gloss on another node merged after the products; the skeleton's plan reads
    nothing it changed, so it runs at the products commit."""
    token = harness.token_for("code_alice", "alice-p")
    window(harness, [GLOSS, f"targets/{TARGET}/graph.json"])
    r = precheck(harness, token, skeleton())
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == BOT


def test_explainers_and_signatures_are_words_too(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    window(harness, [GLOSS_SIGNED, EXPLAINER, EXPLAINER_SIGNED, "targets/other-target/x.lean"])
    r = precheck(harness, token, skeleton())
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == BOT


@pytest.mark.parametrize(
    "path",
    [
        f"{NODES}/new-node/Statement.lean",  # a node appeared: a hole may restate it
        f"{NODES}/{OTHER}/META.yaml",  # superseded, lemmas, proved binders
        f"{NODES}/{OTHER}/Proof.lean",
        f"{NODES}/{OTHER}/attempts/20261027T101500Z-bob-partial.lean",  # holes are coming
        f"{NODES}/{NODE}/annex/{'3' * 64}.md",  # a skeleton's citation reads annexes
        f"{NODES}/{OTHER}/status/20261027T101500Z-carol.yaml",
        f"{NODES}/{OTHER}/shelving/20261027T101500Z-carol.yaml",
        f"{NODES}/{OTHER}/literature/20261027T101500Z-carol.yaml",
        f"{NODES}/{OTHER}/withdrawals/20261027T101500Z-carol.yaml",
        f"{NODES}/{OTHER}/defects/20261027T101500Z-carol.yaml",
        f"{NODES}/{OTHER}/gloss",  # a file named like the directory is not in it
        f"{NODES}/{OTHER}/Statement.gloss/x.md",
    ],
)
def test_anything_a_plan_may_read_still_holds_it(harness: Harness, path: str) -> None:
    """A change beside the words, however small, keeps Q23's refusal."""
    token = harness.token_for("code_alice", "alice-p")
    window(harness, [GLOSS, path])
    refused(precheck(harness, token, skeleton()))
    assert harness.githost.dispatches == []


def test_a_list_that_may_be_truncated_holds_it(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    window(harness, None)
    refused(precheck(harness, token, skeleton()))


def test_a_host_that_cannot_compare_holds_it(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    window(harness, [GLOSS])
    del harness.githost.diffs[(BOT, LATER)]  # the fake's host failure
    refused(precheck(harness, token, skeleton()))


def test_a_budget_at_the_reserve_holds_it_without_asking(harness: Harness) -> None:
    """The compare is one more read on the App's budget; at the reserve it is not spent, and the
    answer is the conservative one."""
    token = harness.token_for("code_alice", "alice-p")
    window(harness, [GLOSS])
    now = harness.clock.now().timestamp()
    harness.githost.budget_seen = HostBudget(
        remaining=0, limit=5000, reset_at=now + 1200, read_at=now
    )
    refused(precheck(harness, token, skeleton()))
    assert harness.githost.diff_calls == []


def test_the_answer_for_a_pair_is_kept(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    window(harness, [GLOSS])
    for _ in range(2):
        r = precheck(harness, token, skeleton())
        assert r.status_code == 202, r.text
    assert harness.githost.diff_calls == [(BOT, LATER)]


# --- the seam: the compare API's file list ------------------------------------------------------

COMPARE = f"/repos/{REPO}/compare/{BASE_SHA}...{COMMIT_SHA}"


def test_the_host_lists_every_name_a_diff_touched(script: Script, host: HttpxGitHost) -> None:
    """Both names of a rename, since a node moved away is a node that changed."""
    files = [
        {"filename": "a/gloss/x.md", "status": "added"},
        {"filename": "b/Statement.lean", "previous_filename": "c/Statement.lean"},
    ]
    install_app(script).on("GET", COMPARE, json={"status": "ahead", "files": files})
    assert host.changed_paths(REPO, BASE_SHA, COMMIT_SHA) == [
        "a/gloss/x.md",
        "b/Statement.lean",
        "c/Statement.lean",
    ]


@pytest.mark.parametrize("body", [{"status": "ahead"}, {"files": [{}] * 300}])
def test_a_list_that_may_be_short_is_none(script: Script, host: HttpxGitHost, body: Any) -> None:
    """GitHub shows at most 300 files for a whole comparison: at the limit, or with no list at
    all, the host cannot say what changed."""
    install_app(script).on("GET", COMPARE, json=body)
    assert host.changed_paths(REPO, BASE_SHA, COMMIT_SHA) is None


@pytest.mark.parametrize("files", [[{"status": "added"}], ["a.md"], [{"filename": ""}]])
def test_a_malformed_file_is_a_host_error(script: Script, host: HttpxGitHost, files: Any) -> None:
    install_app(script).on("GET", COMPARE, json={"files": files})
    with pytest.raises(GitHostError):
        host.changed_paths(REPO, BASE_SHA, COMMIT_SHA)
