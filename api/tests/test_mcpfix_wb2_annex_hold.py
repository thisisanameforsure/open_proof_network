"""mcpfix WB2 item 3 (testers 2026-11-25, t883 item 6; the owner's ruling of 2026-11-25: "an annex
is just text"; hold only when unavoidable, and then say why and for how long).

After a gloss and an annex merged on erdos-883, every skeleton precheck on the node answered
``409 products-pending`` for minutes, ``retry_after_s: 300`` flat, naming two commits and no pull
request. F06-T18 counted ``annex/`` as a change to a node because a skeleton may cite an annex
(``check_cited_annex``). Now an annex is words to a hole plan, and the one hold left is a bundle
that *cites* an annex the products commit does not carry; that refusal names the merge it waits
on (pull request and ``merged_at`` when the service saw it merge) and its ``retry_after_s`` is
what is left of the median from that merge, not the flat 300.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from api_fakes import Harness
from test_finding_precheck_hole_commit import BOT
from test_finding_precheck_products_commit import LATER, PARTIAL, PARTIAL_PATH, precheck, skeleton
from test_finding_precheck_words_window import GLOSS, NODES, window
from test_precheck import NODE, TARGET

from opn_api import clock as clockmod
from opn_api import pending
from opn_api.store import Submission

DIGEST = "3" * 64
ANNEX = f"{NODES}/{NODE}/annex/{DIGEST}.md"
OTHER_ANNEX = f"{NODES}/{NODE}/annex/{'4' * 64}.md"


def citing(digest: str = DIGEST) -> dict[str, str]:
    return {PARTIAL_PATH: f"-- annex: {digest}\n" + PARTIAL}


def annex_on_main(h: Harness, path: str = ANNEX) -> None:
    """The annex is on ``main`` and not in ``BOT``, the commit that wrote the products."""
    h.githost.files[path] = b"---\nschema: annex/v1\n---\nAn argument.\n"
    h.githost.absent_at.setdefault(BOT, set()).add(path)
    h.context.files.clear()


def merged_annex(h: Harness, number: int, minutes_ago: int) -> str:
    """The service's record of the annex's pull request, seen merged ``minutes_ago``."""
    merged_at = clockmod.render(h.clock.now() - timedelta(minutes=minutes_ago))
    h.store.put_submission(
        Submission(
            id=f"01M{number:023d}",
            kind="annex",
            node_id=NODE,
            target_id=TARGET,
            pr_number=number,
            pr_url=f"https://github.com/pr/{number}",
            pseudonym="bob",
            precheck_job_id=None,
            created=merged_at,
            closed=merged_at,
            final_state={"merged": True, "merged_at": merged_at, "merge_commit_sha": LATER},
        )
    )
    h.store.note_merged(number, h.clock.now() + timedelta(hours=1))
    return merged_at


def test_a_gloss_merged_after_the_products_holds_nothing(harness: Harness) -> None:
    """(a) the guard: already true before this change."""
    token = harness.token_for("code_alice", "alice-p")
    window(harness, [GLOSS])
    r = precheck(harness, token, skeleton())
    assert r.status_code == 202, r.text


def test_an_annex_merged_after_the_products_holds_no_bundle_that_does_not_cite_it(
    harness: Harness,
) -> None:
    """(b) the finding: an annex is text to a plan that does not cite it."""
    token = harness.token_for("code_alice", "alice-p")
    window(harness, [GLOSS, ANNEX])
    annex_on_main(harness)
    r = precheck(harness, token, skeleton())
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == BOT


def test_a_bundle_citing_an_annex_from_another_merge_is_held_by_nothing(harness: Harness) -> None:
    """A bundle that cites an annex the products already carry is not held by a newer one."""
    token = harness.token_for("code_alice", "alice-p")
    window(harness, [ANNEX])
    annex_on_main(harness)
    harness.githost.files[OTHER_ANNEX] = b"---\nschema: annex/v1\n---\nOlder.\n"
    r = precheck(harness, token, citing("4" * 64))
    assert r.status_code == 202, r.text


def test_a_bundle_citing_the_new_annex_is_held_naming_the_merge(harness: Harness) -> None:
    """(c) the one hold left: it names the pull request and when it merged, and the wait is
    what is left of the median from that merge."""
    token = harness.token_for("code_alice", "alice-p")
    window(harness, [ANNEX])
    annex_on_main(harness)
    merged_at = merged_annex(harness, 41, minutes_ago=10)
    r = precheck(harness, token, citing())
    assert r.status_code == 409, r.text
    doc: dict[str, Any] = r.json()
    assert doc["error"] == "products-pending"
    assert "#41" in doc["message"] and merged_at in doc["message"], doc["message"]
    details = doc["details"]
    assert details["pr_number"] == 41 and details["merged_at"] == merged_at
    assert details["retry_after_s"] == pending.products_retry_after_s(harness.context, merged_at)
    assert details["retry_after_s"] < pending.PRODUCTS_RETRY_FLAT_S
    assert harness.githost.dispatches == []
