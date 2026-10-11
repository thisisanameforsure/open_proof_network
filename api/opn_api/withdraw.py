"""Withdrawing one's own pull request (F07-T43, Q50; ruling D5, 2026-09-24).

``DELETE /submissions/{id}`` — by the record's ULID or the pull-request number, as the read route
takes them — closes a pull request the service opened, unmerged, and deletes the branch it pushed,
through the App. Only the identity that opened it may: the record keeps its pseudonym (F07-T16),
which the identities table keeps unique (F05-R4). A merged pull request is ``409``; one already
closed is answered as withdrawn without another host call, so a repeat is harmless. Whether it has
merged is read from the host at the moment of asking, never from the cache, because withdrawing a
pull request that merged a minute ago must not answer "withdrawn".

The record is closed in the store with the state the host was left in, so ``GET /submissions.json``
drops it at once and the duplicate rule (F07-T35) stops counting it. The graph's merge actor merges
only open pull requests, so a withdrawn one leaves its queue by the host's own state. A host that
fails leaves the record open and says so (``502 withdraw-failed``, C7).

Before the close, the service comments on the pull request who withdrew it and through which
route (F07-T64), so the host's own record says why the App closed it; a comment that fails is
logged and does not stop the withdrawal.
"""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import clock as clockmod
from opn_api import pending, proposals, submissions
from opn_api.app import ApiError, CachedPull, host_budget_refusal
from opn_api.githost import GitHostError, PullRequestState, RateLimitError

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity, Submission

log = logging.getLogger(__name__)

#: The branches the service itself pushes (``submissions.open_pr``'s callers). A branch outside
#: these is never deleted, whatever the pull request says its head is.
SERVICE_BRANCH_PREFIXES: tuple[str, ...] = (
    submissions.SUBMIT_BRANCH_PREFIX,
    submissions.APPEND_BRANCH_PREFIX,
    proposals.PROPOSE_BRANCH_PREFIX,
)


def failed(ctx: Context, number: int, exc: GitHostError) -> ApiError:
    if isinstance(exc, RateLimitError):  # F07-T47: come back at the reset, not a bare 502
        return host_budget_refusal(ctx, exc)
    return ApiError(
        502,
        "withdraw-failed",
        f"pull request #{number} could not be withdrawn; it is still open: {exc}",
    )


def merged(found: Submission) -> ApiError:
    return ApiError(
        409,
        "submission-merged",
        f"pull request #{found.pr_number} has merged; a merged submission is part of the record "
        "and cannot be withdrawn (a D-8 revision request or a defect claim is the route)",
        details={"pr_number": found.pr_number, "pr_url": found.pr_url},
    )


def answer(found: Submission, pull: dict[str, object] | None, deleted: bool) -> Response:
    return JSONResponse(
        {
            "withdrawn": True,
            "submission": pending.document(found),
            "pull_request": pull,
            "branch_deleted": deleted,
        }
    )


def comment(ctx: Context, found: Submission) -> None:
    """F07-T64: say on the host, before the close, who withdrew and how; the App closes the pull
    request, so without it the host shows a close with no reason. A failed comment is logged and
    never blocks the withdrawal (C7)."""
    body = (
        f"Withdrawn by `{found.pseudonym}`, the identity that opened it, through the service "
        f"(`DELETE /submissions/{found.id}`, F07-T43). The service closes this pull request "
        "unmerged and deletes the branch it pushed."
    )
    try:
        ctx.githost.comment_on_pull_request(ctx.settings.graph_repo, found.pr_number, body)
    except GitHostError as exc:
        log.warning("withdrawn #%d: no comment posted: %s", found.pr_number, exc)


def close_record(ctx: Context, found: Submission, state: PullRequestState) -> Submission:
    ctx.pulls[state.number] = CachedPull(state.number, state, time.monotonic())
    closed = ctx.store.close_submission(
        found.id, closed=clockmod.render(ctx.clock.now()), final_state=state.as_dict()
    )
    return closed or found


async def delete_submission(ctx: Context, request: Request) -> Response:
    identity: Identity = request.state.identity
    raw = str(request.path_params["submission_id"])
    submission_id, number = pending.parse_id(raw)
    found = (
        ctx.store.get_submission(submission_id)
        if submission_id is not None
        else ctx.store.get_submission_by_pr(number or 0)
    )
    if found is None:  # a pull request opened by hand has no holder the service can check
        raise pending.unknown(raw)
    if found.pseudonym != identity.pseudonym:
        raise ApiError(
            403, "not-holder", "only the identity that opened a submission may withdraw it"
        )
    if found.closed is not None:
        if (found.final_state or {}).get("merged"):
            raise merged(found)
        return answer(found, found.final_state, deleted=False)  # a repeat: nothing to do

    repo = ctx.settings.graph_repo
    try:
        state = ctx.githost.get_pull_request(repo, found.pr_number)
    except GitHostError as exc:
        raise failed(ctx, found.pr_number, exc) from exc
    if state is None:
        raise pending.unknown(raw)
    if state.merged:
        close_record(ctx, found, state)
        raise merged(found)
    if state.finished:  # closed on the host already, by a person or the racer rule
        return answer(close_record(ctx, found, state), state.as_dict(), deleted=False)

    comment(ctx, found)
    try:
        branch = ctx.githost.close_pull_request(repo, found.pr_number)
    except GitHostError as exc:
        raise failed(ctx, found.pr_number, exc) from exc
    closed_state = replace(state, state="closed")
    found = close_record(ctx, found, closed_state)
    deleted = False
    if branch is not None and branch.startswith(SERVICE_BRANCH_PREFIXES):
        try:
            deleted = ctx.githost.delete_branch(repo, branch)
        except GitHostError as exc:  # the pull request is closed; a stray branch is harmless
            log.warning("withdrawn #%d: branch %s not deleted: %s", found.pr_number, branch, exc)
    log.info("submission %s (#%d) withdrawn by %s", found.id, found.pr_number, identity.id)
    return answer(found, closed_state.as_dict(), deleted)
