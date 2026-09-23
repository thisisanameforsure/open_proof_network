"""F07-T36: a losing racer's proof becomes an alternate, as D-25 says (testers 2026-09-23).

D-25 (v3.13) lets racers race — "first merged fills ``Proof.lean``; a losing racer's complete
proof is recorded in ``attempts/`` as an alternate proof" — and nothing did the recording. Every
proof pull request writes the node's ``Proof.lean``, so once one merges the others conflict with
``main`` and would sit open for ever. The service opened those branches, so it moves each loser's
proof, byte for byte, to the path an alternate takes (F07-T12) on a fresh commit from ``main``,
and the gate checks it there as the alternate it now is.

It happens on a live read of an open proof whose node's proof has merged and whose branch still
carries ``Proof.lean`` (such a pull request can never merge, whatever the host says of it),
once per submission (a store counter marks it), and never for a copy of the winner, which the
gate refuses as ``alternate-duplicate`` and the duplicate rule refuses before that (F07-T35).
A host or store failure leaves the pull request as it was (C7).
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from opn_api import clock as clockmod
from opn_api import duplicates, precheck, submissions
from opn_api.githost import Author, GitHostError, PullRequestState
from opn_gate.paths import ALTERNATE_SUFFIX

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Submission

log = logging.getLogger(__name__)

#: How long the "converted" mark lasts; a pull request converted and still conflicting after a
#: day is a person's to look at, not something to rebuild again and again.
MARK_S = 24 * 3600
FILE_TIMESTAMP = "%Y%m%dT%H%M%SZ"


def is_losing_racer(ctx: Context, found: Submission, state: PullRequestState) -> bool:
    # Not ``mergeable_state == "dirty"``: the host answered ``unknown`` for #172 for minutes while
    # main kept moving. A proof pull request on a node whose proof has merged cannot merge; that
    # it still carries ``Proof.lean`` is checked where the file is read.
    if found.kind != "proof" or found.node_id is None or state.finished:
        return False
    for node in precheck.graph_doc(ctx).get(found.target_id, []):
        if node.get("node_id") == found.node_id:
            return bool(node.get("proof_commit"))
    return False


def alternate_path(found: Submission) -> str:
    stamp = clockmod.parse(found.created).strftime(FILE_TIMESTAMP)
    return (
        f"targets/{found.target_id}/nodes/{found.node_id}/attempts/"
        f"{stamp}-{found.pseudonym}{ALTERNATE_SUFFIX}"
    )


def convert(ctx: Context, found: Submission, state: PullRequestState) -> bool:  # noqa: PLR0911 — one return per reason not to
    """Move a losing racer's proof to its alternate path; answer whether it was moved."""
    if not is_losing_racer(ctx, found, state):
        return False
    node_dir = f"targets/{found.target_id}/nodes/{found.node_id}/"
    repo = ctx.settings.graph_repo
    try:
        fetched = ctx.githost.fetch_raw(repo, state.head_sha, node_dir + "Proof.lean", etag=None)
        winner = ctx.githost.fetch_raw(
            repo, ctx.settings.graph_branch, node_dir + "Proof.lean", etag=None
        )
    except GitHostError as exc:
        log.warning("racer #%d: proof not read: %s", found.pr_number, exc)
        return False
    if fetched.status != 200 or fetched.body is None:
        return False  # not a Proof.lean submission (an alternate already, or a partial)
    text = fetched.body.decode("utf-8")
    if winner.body is not None and duplicates.fingerprint(text) == duplicates.fingerprint(
        winner.body.decode("utf-8", errors="replace")
    ):
        return False  # a copy of the winner: nothing to keep
    mark = f"racer#{found.id}"
    if ctx.store.bump_counter(mark, ctx.clock.now() + timedelta(seconds=MARK_S)) > 1:
        return False
    now = clockmod.render(ctx.clock.now())
    author = Author(found.pseudonym, f"{found.pseudonym}@{submissions.AUTHOR_DOMAIN}", now)
    message = (
        f"alternate: {found.node_id}\n\n"
        "The node's proof merged first; this proof is kept as an alternate (D-25), unchanged.\n\n"
        f"Signed-off-by: {found.pseudonym} <{found.pseudonym}@{submissions.AUTHOR_DOMAIN}>\n"
    )
    try:
        ctx.githost.push_branch(
            repo,
            submissions.SUBMIT_BRANCH_PREFIX + found.id,
            {alternate_path(found): text},
            base=ctx.settings.graph_branch,
            message=message,
            author=author,
            committer=submissions.committer_for(ctx, now),
            replace=True,
        )
    except GitHostError as exc:
        log.warning("racer #%d: not moved to an alternate: %s", found.pr_number, exc)
        ctx.store.drop_counter(mark)
        return False
    ctx.pulls.pop(found.pr_number, None)  # its state is about to change: read it afresh next time
    log.info("racer #%d moved to %s", found.pr_number, alternate_path(found))
    return True
