"""Pending submissions (F07-T16; D-28 reads, C7): what the service opened, and how it is doing.

A pull request the service opens is recorded (``record``) with what it was — its kind, node,
target, pseudonym and the precheck it stood on. ``GET /submissions/{id}`` answers by the record's
ULID or by the pull-request number, padded or not, with the pull request's live state read from
the host through the App (read-only), and the attestation its merge wrote once there is one.
``GET /submissions.json`` lists every record no live read has found finished.

The live state is cached in ``Context.pulls`` for ``frontier_max_stale_s``, the committed files'
window. A host failure serves the last state it read with ``pull_request_error`` set — never a
5xx, never a silent success (C7). A live read that finds the pull request merged or closed closes
the record with that state, so a finished pull request never costs another host call.

The record is operational, not evidentiary (C9): what merged is what the graph's attestations
say, and a pull request opened by hand is answered from its attestation alone.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import clock as clockmod
from opn_api import frontier
from opn_api.app import ApiError, CachedFile, CachedPull
from opn_api.githost import GitHostError, PullRequest, PullRequestState
from opn_api.store import Submission

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

log = logging.getLogger(__name__)

#: The kinds whose merge writes ``attestations/<n>.json``: ``POST /submissions``' artifact types
#: (``submissions.ARTIFACT_TYPES``, asserted equal in the tests — not imported, because
#: ``submissions`` will call ``record``). Every other kind merges on path and schema checks alone.
ATTESTING_KINDS: tuple[str, ...] = ("proof", "counterexample", "vacuity", "reduction", "partial")
#: The gate's attestation file name: the merged pull request's number, zero-padded to six
#: (``opn_gate.postmerge.attestation_id``, F07-Q8).
ATTESTATION_WIDTH = 6
ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
NUMBER_RE = re.compile(r"^[0-9]+$")
MAX_NUMBER_DIGITS = 12  # after the leading zeros: no pull request on any graph is near this

NOTE_NO_ATTESTATION = "no-attestation-for-mode"  # the kind merges without a build
NOTE_NOT_MERGED = "not-merged"  # the host says the pull request has not merged
NOTE_PENDING = "attestation-pending"  # merged; the post-merge job has not committed it yet
NOTE_UNKNOWN = "pull-request-unavailable"  # the host could not say, and main has no attestation


# --- the record ----------------------------------------------------------------------------------


def record(  # noqa: PLR0913 — one opened pull request, described
    ctx: Context,
    identity: Identity,
    *,
    submission_id: str,
    kind: str,
    target_id: str,
    node_id: str | None,
    pr: PullRequest,
    precheck_job_id: str | None = None,
) -> Submission | None:
    """Remember a pull request the service just opened. The pull request exists whatever happens
    here, so a store failure is logged and the caller still answers 201 with its number: the
    record is advisory and the pull request is the truth (C7, C9)."""
    submission = Submission(
        id=submission_id,
        kind=kind,
        node_id=node_id,
        target_id=target_id,
        pr_number=pr.number,
        pr_url=pr.url,
        pseudonym=identity.pseudonym,
        precheck_job_id=precheck_job_id,
        created=clockmod.render(ctx.clock.now()),
    )
    try:
        ctx.store.put_submission(submission)
    except Exception as exc:  # any store failure: the pull request is open regardless
        log.error(
            "submission %s (pull request #%d) was opened but not recorded: %s",
            submission_id,
            pr.number,
            type(exc).__name__,
        )
        return None
    return submission


def document(submission: Submission) -> dict[str, Any]:
    """A record as the routes serve it: every field but the state that closed it, which the
    answer carries as ``pull_request`` instead."""
    doc = asdict(submission)
    doc.pop("final_state")
    return doc


# --- the live state (C7) -------------------------------------------------------------------------


def live_state(ctx: Context, number: int) -> tuple[PullRequestState | None, str | None]:
    """The pull request's state and, when it is not a fresh answer from the host, why."""
    cached = ctx.pulls.get(number)
    now = time.monotonic()
    if cached is not None and now - cached.fetched_at < ctx.settings.frontier_max_stale_s:
        return cached.state, None if cached.state is not None else _unknown(ctx, number)
    try:
        state = ctx.githost.get_pull_request(ctx.settings.graph_repo, number)
    except GitHostError as exc:
        log.warning("pull request #%d: %s", number, exc)
        last = cached.state if cached is not None else None
        return last, f"the pull request's live state could not be read from the host: {exc}"
    ctx.pulls[number] = CachedPull(number, state, now)
    return state, None if state is not None else _unknown(ctx, number)


def _unknown(ctx: Context, number: int) -> str:
    return f"the host has no pull request #{number} on {ctx.settings.graph_repo}"


# --- the attestation ------------------------------------------------------------------------------


def attestation_path(number: int) -> str:
    return f"attestations/{number:0{ATTESTATION_WIDTH}d}.json"


def optional_committed(ctx: Context, path: str) -> bytes | None:
    """``frontier.committed`` for a file that may not exist yet: ``None`` on the host's 404
    instead of a 503, because an attestation that has not been written is an answer, not an
    outage. Same cache, same window, same freshness generation (F05-T10)."""
    frontier.generation(ctx)
    cached = ctx.files.setdefault(path, CachedFile(path))
    now = time.monotonic()
    if cached.body is not None and now - cached.fetched_at < ctx.settings.frontier_max_stale_s:
        return cached.body
    try:
        got = ctx.githost.fetch_raw(
            ctx.settings.graph_repo, ctx.settings.graph_branch, path, etag=cached.etag
        )
    except GitHostError as exc:
        log.warning("%s: %s", path, exc)
        got = None
    if got is not None and got.status == 200 and got.body is not None:
        cached.body, cached.etag, cached.fetched_at = got.body, got.etag, now
        return got.body
    if got is not None and got.status == 304 and cached.body is not None:
        cached.fetched_at = now
        return cached.body
    if got is not None and got.status == 404:
        ctx.files.pop(path, None)
        return None
    if cached.body is not None:
        return cached.body  # the last good copy (C7)
    ctx.files.pop(path, None)
    raise ApiError(503, "graph-unreachable", f"cannot read {path} from the graph")


def attestation_doc(raw: bytes, path: str) -> dict[str, Any]:
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise ApiError(502, "attestation-unparseable", f"{path} is not JSON") from exc
    if not isinstance(doc, dict):
        raise ApiError(502, "attestation-unparseable", f"{path} is not one object")
    return doc


# --- GET /submissions/{id} ------------------------------------------------------------------------


def parse_id(raw: str) -> tuple[str | None, int | None]:
    """A ULID, or a pull-request number with any number of leading zeros."""
    if NUMBER_RE.match(raw):
        digits = raw.lstrip("0")
        if len(digits) > MAX_NUMBER_DIGITS:
            raise unknown(raw)
        return None, int(digits or "0")
    if ULID_RE.match(raw.upper()):
        return raw.upper(), None
    raise ApiError(
        400,
        "submission-id-invalid",
        "a submission id is the ULID POST /submissions answered or the pull-request number",
    )


def unknown(raw: str) -> ApiError:
    return ApiError(
        404,
        "submission-unknown",
        f"{raw} is neither a pull request the service opened nor one the graph has attested",
    )


def reconcile(
    ctx: Context, found: Submission
) -> tuple[Submission, dict[str, Any] | None, str | None]:
    """The record with the host's last word on it, closing it when the pull request has finished.

    Shared by ``GET /submissions/{id}`` and ``GET /submissions.json`` since 2026-09-16. It used
    to live inside ``answer`` alone, so only the submission somebody named was ever reconciled
    and the list kept merged pull requests for ever (#66-#69 sat open for two days). A record
    the host cannot describe is left open with the reason, never silently dropped (C7).
    """
    if found.closed is not None:
        return found, found.final_state, None
    state, error = live_state(ctx, found.pr_number)
    if state is not None and error is None and state.finished:
        closed = ctx.store.close_submission(
            found.id,
            closed=clockmod.render(ctx.clock.now()),
            final_state=state.as_dict(),
        )
        found = closed or found
    return found, state.as_dict() if state is not None else None, error


def answer(ctx: Context, raw: str) -> dict[str, Any]:
    submission_id, number = parse_id(raw)
    found = (
        ctx.store.get_submission(submission_id)
        if submission_id is not None
        else ctx.store.get_submission_by_pr(number or 0)
    )
    if found is None:
        return hand_opened(ctx, raw, number)

    found, pull, error = reconcile(ctx, found)

    path: str | None = None
    attestation: dict[str, Any] | None = None
    if found.kind not in ATTESTING_KINDS:
        note: str | None = NOTE_NO_ATTESTATION
    elif pull is not None and not pull["merged"]:
        note = NOTE_NOT_MERGED
    else:
        candidate = attestation_path(found.pr_number)
        raw_doc = optional_committed(ctx, candidate)
        if raw_doc is not None:
            path, attestation, note = candidate, attestation_doc(raw_doc, candidate), None
        else:
            note = NOTE_PENDING if pull is not None else NOTE_UNKNOWN
    return {
        "submission": document(found),
        "pull_request": pull,
        "pull_request_error": error,
        "attestation_path": path,
        "attestation": attestation,
        "attestation_note": note,
    }


def hand_opened(ctx: Context, raw: str, number: int | None) -> dict[str, Any]:
    """No record: a pull request opened by hand is answered once the graph has attested it.
    Without an attestation the id is unknown — the service does not look up pull requests it
    never opened and nothing merged, which would let anyone spend the App's rate budget."""
    if number is None or number <= 0:
        raise unknown(raw)
    path = attestation_path(number)
    raw_doc = optional_committed(ctx, path)
    if raw_doc is None:
        raise unknown(raw)
    state, error = live_state(ctx, number)
    return {
        "submission": None,
        "pull_request": state.as_dict() if state is not None else None,
        "pull_request_error": error,
        "attestation_path": path,
        "attestation": attestation_doc(raw_doc, path),
        "attestation_note": None,
    }


async def get_submission(ctx: Context, request: Request) -> Response:
    return JSONResponse(answer(ctx, str(request.path_params["submission_id"])))


# --- GET /submissions.json ------------------------------------------------------------------------


def snapshot(ctx: Context) -> dict[str, Any]:
    """The open records, each the ``submission`` document its own route carries.

    Each is reconciled against the host first, so "open" means the host still calls it open and
    not merely that nobody has asked. One lookup per open record per freshness window, on the
    same cache ``answer`` uses; a record the host cannot describe stays listed (C7).
    """
    open_now: list[dict[str, Any]] = []
    for submission in ctx.store.list_open_submissions():
        record, _, _ = reconcile(ctx, submission)
        if record.closed is None:
            open_now.append(document(record))
    return {"snapshot_at": clockmod.render(ctx.clock.now()), "open": open_now}


async def get_submissions(ctx: Context, request: Request) -> Response:
    return JSONResponse(snapshot(ctx))
