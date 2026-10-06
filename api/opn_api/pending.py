"""Pending submissions (F07-T16; D-28 reads, C7): what the service opened, and how it is doing.

A pull request the service opens is recorded (``record``) with what it was — its kind, node,
target, pseudonym and the precheck it stood on. ``GET /submissions/{id}`` answers by the record's
ULID or by the pull-request number, padded or not, with the pull request's live state read from
the host through the App (read-only), and the attestation its merge wrote once there is one.
``GET /submissions.json`` lists every record no live read has found finished.

The live state is cached in ``Context.pulls`` for ``pull_max_stale_s``. A host failure serves the
last state it read, marked ``stale`` with the ``read_at`` of when it was true, with
``pull_request_error`` set — never a 5xx, never a silent success (C7). A live read that finds the
pull request merged or closed closes the record with that state, so a finished pull request never
costs another host call.

F07-T47: no read here spends the host once the App's budget is at or below the reserve kept for
writes (``host_budget_reserve``), and a refusal for budget names the reset and carries
``Retry-After``. The listing reconciles the whole queue against one open-pull-request listing per
``pull_listing_max_stale_s`` (``GitHost.list_open_pull_requests``) rather than one read per
record, which is what let eighteen pollers spend the hour's budget.

The record is operational, not evidentiary (C9): what merged is what the graph's attestations
say, and a pull request opened by hand is answered from its attestation alone.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import clock as clockmod
from opn_api import frontier, hostbudget
from opn_api.app import ApiError, CachedFile, CachedListing, CachedPull
from opn_api.githost import (
    GATE_WORKFLOW,
    GitHostError,
    HostBudget,
    OpenPullRequest,
    PullRequest,
    PullRequestState,
    RateLimitError,
)
from opn_api.store import Submission
from opn_gate import schemas

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

log = logging.getLogger(__name__)

#: The host's open pull requests by number (F07-T47).
Listing = dict[int, OpenPullRequest]

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
HTTP_OK = 200


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
    fingerprints: tuple[str, ...] | list[str] = (),
    defect_class: str | None = None,
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
        fingerprints=tuple(fingerprints),
        defect_class=defect_class,
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
    doc.pop("fingerprints")  # the service's own index, not part of the answer (F07-T35)
    doc.pop("defect_class")  # likewise (F08-T18): the claim's own file says its class
    # F05-T18: the name every write route uses (``POST /submissions``, ``/precheck``, the
    # receipt). ``kind`` stays, and is the only one that speaks for a record that is not an
    # artifact of ``POST /submissions`` (an annex, a witness, a proposal): there this is null.
    doc["artifact_type"] = submission.kind if submission.kind in ATTESTING_KINDS else None
    return doc


# --- a node that is not in the products yet (F08-T11) --------------------------------------------

#: How long a merged proposal usually waits for the post-merge job's products commit.
#: Measured 2026-09-20: three to six minutes from a merge to the post-merge job's products commit
#: (a Mathlib re-derivation is most of it). 120 s sent agents back three times too early.
PRODUCTS_RETRY_AFTER_S = 240
NOT_RENDERED = (
    "a node merged in the last few minutes appears once the post-merge job has rendered the "
    "products, usually three to six minutes after the merge"
)
WAITING_ON_PRODUCTS = "products"


def unknown_node(ctx: Context, node_id: str, where: str = "") -> ApiError:
    """What to answer for a node the products do not carry. The service recorded every proposal
    it opened (T16), so it can tell three cases apart instead of saying "not a node" to all of
    them: ``409 node-pending`` (its pull request is open: named, with what it waits for),
    ``409 products-pending`` (merged; the products are not rendered yet) and ``404 node-unknown``
    (nobody proposed it, or the proposal was closed unmerged). A host that cannot be read still
    names the pull request (C7)."""
    unknown = ApiError(
        404, "node-unknown", f"{node_id} is not a node of this graph{where}; {NOT_RENDERED}"
    )
    found = ctx.store.get_submission_by_node(node_id)
    if found is None:
        return unknown
    details: dict[str, Any] = {"pr_number": found.pr_number, "pr_url": found.pr_url}
    state = None if found.closed is not None else live_state(ctx, found.pr_number)[0]
    merged = (found.final_state or {}).get("merged") if state is None else state.merged
    if merged:
        return ApiError(
            409,
            "products-pending",
            f"{node_id} merged as pull request #{found.pr_number}; {NOT_RENDERED}. Retry shortly.",
            details=details,
            headers={"Retry-After": str(PRODUCTS_RETRY_AFTER_S)},
        )
    if found.closed is not None or (state is not None and state.finished):
        return unknown  # closed unmerged: the node never entered the graph
    waiting = state.waiting_on if state is not None else None
    what = f", which is waiting on: {waiting}" if waiting else ""
    if waiting in GATE_GREEN:
        # F06-T10: this route still needs the merged node, but a precheck does not
        after = (
            "a proof can be prechecked against the proposal already (POST /precheck runs at its "
            "head commit); submit it, and append anything else, once the proposal has merged"
        )
    else:
        after = (
            "nothing can be appended or submitted against it until that merges, and a proof "
            "can be prechecked against it once the proposal's gate is green"
        )
    return ApiError(
        409,
        "node-pending",
        f"{node_id} is proposed in pull request #{found.pr_number}{what}; {after}",
        details={**details, "waiting_on": waiting},
    )


#: F06-T10: the ``waiting_on`` values that mean the proposal's gate concluded success, so its head
#: is a tree the gate admitted and a proof can be prechecked against it before it merges.
GATE_GREEN: tuple[str, ...] = ("merge", "branch-update")


@dataclass(frozen=True)
class GreenProposal:
    """F06-T10: an open proposal whose gate is green, as a precheck or a check reads it — the
    record, the head commit the gate passed, and the node's files there."""

    submission: Submission
    head_sha: str
    statement: str  # Statement.lean at the head, as committed
    context: str | None  # Context.lean at the head, when it has one
    meta: str | None  # META.yaml at the head, for the deps it declares

    @property
    def statement_hash(self) -> str:
        """The hash the gate and the products take of the tree's ``Statement.lean``
        (``layout.Statement.statement_hash`` over the file as ``read_text`` reads it)."""
        text = self.statement.replace("\r\n", "\n").replace("\r", "\n")
        return schemas.content_hash(text.encode("utf-8"))

    def reference(self) -> dict[str, Any]:
        """What a job records about the proposal it ran against."""
        return {
            "pr_number": self.submission.pr_number,
            "pr_url": self.submission.pr_url,
            "head_sha": self.head_sha,
        }


def green_proposal(ctx: Context, node_id: str) -> GreenProposal | None:
    """The open proposal of ``node_id`` when its gate is green, else ``None`` — and ``None`` too
    whenever the host cannot say for certain (a failed read, a missing statement), so the caller
    answers ``node-pending`` as before rather than run against a tree nobody checked (C7)."""
    found = ctx.store.get_submission_by_node(node_id)
    if found is None or found.closed is not None:
        return None
    state, error = live_state(ctx, found.pr_number)
    if state is None or error is not None or state.waiting_on not in GATE_GREEN:
        return None
    node_dir = f"targets/{found.target_id}/nodes/{node_id}/"
    texts: dict[str, str | None] = {}
    for name in ("Statement.lean", "Context.lean", "META.yaml"):
        try:
            got = ctx.githost.fetch_raw(
                ctx.settings.graph_repo, state.head_sha, node_dir + name, etag=None
            )
        except GitHostError as exc:
            log.warning("pull request #%d: %s not read: %s", found.pr_number, name, exc)
            return None
        body = got.body if got.status == HTTP_OK else None
        texts[name] = body.decode("utf-8", errors="replace") if body is not None else None
    statement = texts["Statement.lean"]
    if statement is None:
        return None
    return GreenProposal(
        found, state.head_sha, statement, texts["Context.lean"], texts["META.yaml"]
    )


# --- the live state (C7) -------------------------------------------------------------------------


def pr_lock(ctx: Context, number: int) -> threading.RLock:
    """F07-T39: the lock for one pull request's reconciliation, made on first use."""
    with ctx.pr_locks_guard:
        return ctx.pr_locks.setdefault(number, threading.RLock())


def live_state(ctx: Context, number: int) -> tuple[PullRequestState | None, str | None]:
    """The pull request's state and, when it is not a fresh answer from the host, why. Under
    the pull request's lock, so two threads asking at once make one lookup (F07-T39)."""
    with pr_lock(ctx, number):
        return _live_state(ctx, number)


def superseded(ctx: Context, cached: CachedPull) -> bool:
    """F05-T18: whether something the service read *after* this state says it no longer holds,
    so that serving it as fresh would be serving what the service already knows to be wrong
    (#332 read ``open, waiting_on gate, stale: false`` for 84 s after its merge). Three facts,
    none of which costs a read here:

    * the open listing, read later, no longer carries the pull request: it has merged or closed;
    * the listing carries it at another head: its branch moved, and the cached checks are a
      commit's that is no longer its head;
    * ``main`` has moved since, and the state said its gate was green: it is the one that merged,
      or it is behind now.

    A state that already says finished is never superseded, and a listing or a head read
    *before* the state says nothing about it: after one re-read on evidence, the same evidence
    does not ask for another."""
    state = cached.state
    if state is None or state.finished:
        return False
    listing = ctx.open_pulls
    if listing is not None and listing.fetched_at > cached.fetched_at:
        entry = listing.by_number.get(cached.number)
        if entry is None or (entry.head_sha and entry.head_sha != state.head_sha):
            return True
    moved = cached.main_head is not None and ctx.head is not None and ctx.head != cached.main_head
    return moved and state.waiting_on in GATE_GREEN


def _live_state(ctx: Context, number: int) -> tuple[PullRequestState | None, str | None]:
    cached = ctx.pulls.get(number)
    now = time.monotonic()
    if (
        cached is not None
        and now - cached.fetched_at < ctx.settings.pull_max_stale_s
        and not superseded(ctx, cached)
    ):
        return cached.state, None if cached.state is not None else _unknown(ctx, number)
    last = cached.state if cached is not None else None
    hold = budget_hold(ctx)
    if hold is not None:
        return last, hold
    try:
        state = ctx.githost.get_pull_request(ctx.settings.graph_repo, number)
    except RateLimitError as exc:
        log.warning("pull request #%d: %s", number, exc)
        return last, budget_message(ctx, exc.budget)
    except GitHostError as exc:
        log.warning("pull request #%d: %s", number, exc)
        return last, f"the pull request's live state could not be read from the host: {exc}"
    # fetched_at is taken after the read, so a listing read before it is not evidence against it
    ctx.pulls[number] = CachedPull(
        number, state, time.monotonic(), clockmod.render(ctx.clock.now()), ctx.head
    )
    return state, None if state is not None else _unknown(ctx, number)


def _unknown(ctx: Context, number: int) -> str:
    return f"the host has no pull request #{number} on {ctx.settings.graph_repo}"


# --- the host budget (F07-T47) --------------------------------------------------------------------


def budget_hold(ctx: Context) -> str | None:
    """Why a read must not spend the host now, or ``None``: the budget the host last reported
    is at or below the reserve kept for writes and has not refilled."""
    budget = ctx.githost.budget()
    if budget is None:
        return None
    now = ctx.clock.now().timestamp()
    if hostbudget.held(budget, now, ctx.settings.host_budget_reserve):
        return budget_message(ctx, budget)
    return None


#: F07-T68: the most entries a per-commit answer table keeps before it starts again; the tables
#: are caches, so forgetting costs one host read, and an unbounded one is a leak a poller grows.
MAX_REMEMBERED = 4096


def forget_old(table: dict[str, float], window_s: int) -> None:
    """Drop the entries of a ``key -> monotonic`` table older than ``window_s`` once it is large,
    so a table of recent host reads cannot grow without bound (F07-T68)."""
    if len(table) < MAX_REMEMBERED:
        return
    cutoff = time.monotonic() - window_s
    for key, at in list(table.items()):
        if at < cutoff:
            del table[key]
    if len(table) >= MAX_REMEMBERED:
        table.clear()


def budget_message(ctx: Context, budget: HostBudget) -> str:
    return hostbudget.read_message(
        budget, ctx.clock.now().timestamp(), ctx.settings.host_budget_reserve
    )


def retry_after(ctx: Context) -> dict[str, str]:
    """``Retry-After`` for a read served stale because of the budget: the seconds to its reset.
    Empty when the budget is not what held the read."""
    budget = ctx.githost.budget()
    now = ctx.clock.now().timestamp()
    if budget is None or not hostbudget.held(budget, now, ctx.settings.host_budget_reserve):
        return {}
    return {"Retry-After": str(hostbudget.retry_after_s(budget, now))}


def pull_block(state: PullRequestState, *, read_at: str | None, stale: bool) -> dict[str, Any]:
    """A pull request's state as a route serves it: the host's words plus when they were read
    and whether they are the last the host would give (F07-T47) — a stale block is never
    mistaken for a live one, and ``waiting_on`` is what was true at ``read_at``."""
    return {**state.as_dict(), "read_at": read_at, "stale": stale}


def cached_block(
    ctx: Context, number: int, state: PullRequestState | None, error: str | None
) -> dict[str, Any] | None:
    """The block for ``state`` as ``live_state`` answered it: ``read_at`` from the cache entry
    it came from, stale when the answer was not fresh from the host."""
    if state is None:
        return None
    cached = ctx.pulls.get(number)
    read_at = cached.read_at if cached is not None and cached.state is state else None
    return pull_block(state, read_at=read_at, stale=error is not None)


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


# --- the merge queue (F05-T18) --------------------------------------------------------------------

#: The branches the service opens pull requests from, which are the ones the merge actor takes
#: (``SERVICE_PREFIXES`` in the graph's ``merge.yml``; held equal by
#: ``gate/tests/test_finding_queue_order_is_the_actors.py``).
SERVICE_PREFIXES: tuple[str, ...] = ("propose/", "append/", "submit/")
QUEUE_BASE = "main"
#: How the position is to be read, said in the answer because the position alone overstates it.
QUEUE_ORDER = (
    "pull-request number, oldest first, over the open pull requests the merge actor takes "
    "(non-draft, on a branch the service opened, against main), counted in the pull request's "
    "own lane: the merge actor runs one lane per target in parallel (F07-T56), so only the "
    "pull requests on the same target, and any whose target the service does not know (the "
    "actor holds every lane for one it cannot place), are ahead of it. Within a lane the actor "
    "merges the first one whose gate is green and passes over a red, conflicting or "
    "behind-and-still-running one, so a position is an upper bound on the merges ahead, not a "
    "count of them; consecutive green appends may merge as one batch"
)
QUEUE_NOTE = (
    "each entry's queue.waiting_on is what the service last read for that pull request, with "
    "when; null means not read (GET /submissions/<id> reads it), never that it waits on nothing. "
    "queue.order is the actor's order across every lane; each entry's position counts its own "
    "lane: its target's (the record's target_id), or every lane for one the service cannot place"
)
#: The lane of a pull request the service cannot place in one target: every lane, as the merge
#: actor's ``EVERY_LANE`` (the graph's ``merge.yml``, F07-T56).
EVERY_LANE = "*"
#: The most pull requests an answer names as ahead; ``position`` says how many there are.
MAX_AHEAD = 50
#: F07-T70: the most finished submissions ``GET /submissions/mine`` names, newest first.
MAX_RECENT_MINE = 20


def queue_order(listed: Listing) -> list[int]:
    """The merge actor's queue over the host's open listing: its own ``candidates``, in its
    order. Nothing here asks the host anything; whether a pull request is green is the actor's
    to read, one pull request at a time, and is not known here for the queue as a whole."""
    return sorted(
        entry.number
        for entry in listed.values()
        if not entry.draft
        and entry.same_repo
        and entry.base_ref == QUEUE_BASE
        and entry.head_ref.startswith(SERVICE_PREFIXES)
    )


def last_read(ctx: Context, number: int) -> tuple[str | None, str | None]:
    """``waiting_on`` for a pull request as the service last read it, and when: from the cache
    of per-id reads, whatever its age, and never a read of its own. ``(None, None)`` when
    nobody has asked about it since the process started."""
    cached = ctx.pulls.get(number)
    if cached is None or cached.state is None:
        return None, None
    return cached.state.waiting_on, cached.read_at


def lane_queue(order: list[int], lanes: dict[int, str], number: int) -> list[int]:
    """F07-T69: the part of the actor's ``order`` that shares ``number``'s lane —
    the pull requests on its target and every one the service cannot place, which the actor
    lets hold every lane. A pull request that cannot itself be placed waits for the whole
    queue, as the actor's does (``merge.yml``: "waits until it is first")."""
    lane = lanes.get(number, EVERY_LANE)
    if lane == EVERY_LANE:
        return list(order)
    return [n for n in order if lanes.get(n, EVERY_LANE) in (lane, EVERY_LANE)]


def entry_queue(
    ctx: Context, number: int, order: list[int] | None, lanes: dict[int, str]
) -> dict[str, Any]:
    """One open submission's place: ``position`` from 1 in its own lane, ``of`` how many share
    that lane (F07-T69), and what it was last read to be waiting on.
    ``position`` is null for a pull request the actor does not take, and both are null when the
    host has never been listed."""
    waiting, read_at = last_read(ctx, number)
    queued = lane_queue(order or [], lanes, number)
    position = queued.index(number) + 1 if order is not None and number in queued else None
    return {
        "position": position,
        "of": len(queued) if order is not None else None,
        "waiting_on": waiting,
        "waiting_on_read_at": read_at,
    }


def queue_block(
    ctx: Context, found: Submission, pull: dict[str, Any] | None
) -> dict[str, Any] | None:
    """``GET /submissions/<id>``'s ``queue``: where an open pull request stands and what is
    ahead of it, from the open listing the service reads once per window for every caller
    (``open_listing``), so it costs this answer no host call of its own. ``None`` once the pull
    request has merged or closed. With no listing at all the position is null and ``stale`` is
    true (C7): a host that cannot be listed is said, never guessed around."""
    if found.closed is not None or (pull is not None and pull.get("state") != "open"):
        return None
    listed, error, read_at = open_listing(ctx)
    if listed is None:
        return {
            "position": None,
            "of": None,
            "ahead": [],
            "order": QUEUE_ORDER,
            "read_at": None,
            "stale": True,
        }
    records = {s.pr_number: s for s in ctx.store.list_open_submissions()}
    lanes = {n: s.target_id for n, s in records.items()}
    number = found.pr_number
    lanes[number] = found.target_id  # its own record, whatever the open index says
    order = lane_queue(queue_order(listed), lanes, number)
    position = order.index(number) + 1 if number in order else None
    before = order[: position - 1] if position is not None else []
    ahead = []
    for other in before[:MAX_AHEAD]:
        record = records.get(other)
        waiting, waiting_read_at = last_read(ctx, other)
        ahead.append(
            {
                "pr_number": other,
                # the service's record of it, when it opened it and the record is still open
                "id": record.id if record is not None else None,
                "kind": record.kind if record is not None else None,
                "node_id": record.node_id if record is not None else None,
                "target_id": record.target_id if record is not None else None,
                "waiting_on": waiting,
                "waiting_on_read_at": waiting_read_at,
            }
        )
    return {
        "position": position,
        "of": len(order),
        "ahead": ahead,
        "order": QUEUE_ORDER,
        "read_at": read_at,
        "stale": error is not None,
    }


def top_state(found: Submission | None, pull: dict[str, Any] | None) -> str | None:
    """One word at the top of the answer (testers 2026-10-01, A12: "there is no plain merged
    state at the top"): ``open``, ``merged`` or ``closed``; null when the host could not say."""
    if pull is None:
        return None
    if pull.get("merged"):
        return "merged"
    return "open" if pull.get("state") == "open" else "closed"


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


def final_state(found: Submission) -> dict[str, Any] | None:
    """The state that closed a record, in today's shape. A record closed before F07-T42 kept runs
    without ``jobs`` (the host added the key only where it read the jobs), so a merged submission
    read back in a different shape from an open one; every run carries the key now, ``[]`` where
    nothing was read, old records included."""
    state = found.final_state
    runs = (state or {}).get("runs")
    if state is None or not isinstance(runs, list):
        return state
    return {
        **state,
        "runs": [
            {**run, "jobs": list(run.get("jobs") or [])} if isinstance(run, dict) else run
            for run in runs
        ],
        # F07-T47: a record closed before the block carried them was read when it was closed
        "read_at": state.get("read_at", found.closed),
        "stale": bool(state.get("stale", False)),
    }


def reconcile(
    ctx: Context,
    found: Submission,
    first: tuple[PullRequestState | None, str | None] | None = None,
) -> tuple[Submission, dict[str, Any] | None, str | None]:
    """The record with the host's last word on it, closing it when the pull request has finished.

    Shared by ``GET /submissions/{id}`` and ``GET /submissions.json`` since 2026-09-16. It used
    to live inside ``answer`` alone, so only the submission somebody named was ever reconciled
    and the list kept merged pull requests for ever (#66-#69 sat open for two days). A record
    the host cannot describe is left open with the reason, never silently dropped (C7).

    F07-T39: ``first`` is a live read the caller already made (the snapshot's concurrent
    lookups), and the whole reconciliation holds the pull request's lock, so a losing racer is
    converted once however many readers arrive together.
    """
    with pr_lock(ctx, found.pr_number):
        return _reconcile(ctx, found, first)


def _reconcile(
    ctx: Context,
    found: Submission,
    first: tuple[PullRequestState | None, str | None] | None,
) -> tuple[Submission, dict[str, Any] | None, str | None]:
    if found.closed is not None:
        return found, final_state(found), None
    state, error = first if first is not None else live_state(ctx, found.pr_number)
    from opn_api import racers  # noqa: PLC0415 — racers reads the duplicate rule, which reads this

    if state is not None and error is None and racers.convert(ctx, found, state):
        # F07-T36: a losing racer was moved to its alternate path; read the new state
        state, error = live_state(ctx, found.pr_number)
    block = cached_block(ctx, found.pr_number, state, error)
    if state is not None and error is None and state.finished and block is not None:
        closed = ctx.store.close_submission(
            found.id, closed=closed_time(ctx, state), final_state=block
        )
        found = closed or found
    return found, block, error


def closed_time(ctx: Context, state: PullRequestState) -> str:
    """F05-T18: when the host says the pull request merged or closed, in the record's own
    timestamp shape; the time of this read only when the host gave none, or one that is not that
    shape. ``closed`` had been the moment somebody first asked (#360 merged at 18:19:10Z and read
    ``closed: 19:50:21Z``), and every merge time an agent took from this route was late. The
    block's ``read_at`` still says when it was read."""
    for stamp in (state.merged_at, state.closed_at):
        if stamp:
            try:
                return clockmod.render(clockmod.parse(stamp))
            except ValueError:
                log.warning("pull request #%d: unreadable close time %r", state.number, stamp)
    return clockmod.render(ctx.clock.now())


# --- why the gate said no (F07-T26) --------------------------------------------------------------

GATE_ARTIFACT_PREFIX = "gate-"  # the graph's gate.yml: gate-<pr>-<attempt>
RUN_ID_RE = re.compile(r"/actions/runs/(\d+)")
MAX_VERDICT_BYTES = 256 * 1024


def _verdict_document(zipped: bytes) -> dict[str, Any] | None:
    """The one JSON document in the artifact that carries a verdict: ``admission.json`` for a
    proposal, the verdict for a proof. Anything unreadable is no verdict, never an error (C7)."""
    import io  # noqa: PLC0415
    import zipfile  # noqa: PLC0415

    try:
        with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
            for name in sorted(archive.namelist()):
                info = archive.getinfo(name)
                if not name.endswith(".json") or info.file_size > MAX_VERDICT_BYTES:
                    continue
                doc = json.loads(archive.read(name))
                if isinstance(doc, dict) and "verdict" in doc and "diagnostic" in doc:
                    return doc
    except (zipfile.BadZipFile, ValueError, KeyError) as exc:
        log.warning("gate artifact unreadable: %s", exc)
    return None


def gate_verdict(ctx: Context, number: int, pull: dict[str, Any] | None) -> dict[str, Any] | None:
    """Why the gate refused an open pull request, in the gate's own words, or ``None``. The
    service said ``waiting_on: gate-failed`` and nothing else, and the reason sat in a run log an
    HTTP or MCP contributor cannot read. The gate run keeps its verdict as an artifact; it is read
    once per head commit. The diagnostic is the gate's, quoted as data: it can carry a fragment of
    the contributor's own Lean (a hazard's location), and nothing here interprets it (D-28)."""
    if pull is None or pull.get("waiting_on") != "gate-failed":
        return None
    sha = str(pull.get("head_sha") or "")
    if sha in ctx.verdicts:
        return ctx.verdicts[sha]
    out: dict[str, Any] | None = None
    gate = next((r for r in pull.get("runs") or [] if r.get("name") == GATE_WORKFLOW), None)
    found = RUN_ID_RE.search(str((gate or {}).get("url") or ""))
    if found is not None:
        # F07-T68: an anonymous read, so held at the reserve like the live state beside it, and
        # a failed read is not repeated for ``verdict_retry_s``: every poll of a refused pull
        # request asked again, each ask one or two API calls.
        failed_at = ctx.verdict_failures.get(sha)
        if failed_at is not None and time.monotonic() - failed_at < ctx.settings.verdict_retry_s:
            return None
        if budget_hold(ctx) is not None:
            return None  # not cached: the budget refills
        try:
            zipped = ctx.githost.latest_artifact(
                ctx.settings.graph_repo, int(found.group(1)), f"{GATE_ARTIFACT_PREFIX}{number}-"
            )
        except GitHostError as exc:
            log.warning("pull request #%d: the gate's artifact could not be read: %s", number, exc)
            if sha:
                forget_old(ctx.verdict_failures, ctx.settings.verdict_retry_s)
                ctx.verdict_failures[sha] = time.monotonic()
            return None  # cached as a failure only: a read after the window may reach the host
        ctx.verdict_failures.pop(sha, None)
        doc = _verdict_document(zipped) if zipped is not None else None
        if doc is not None:
            out = {
                "verdict": doc.get("verdict"),
                "first_failing": doc.get("first_failing_step") or doc.get("first_failing_check"),
                "diagnostic": doc.get("diagnostic"),
            }
    if sha:
        ctx.verdicts[sha] = out
    return out


def waiting_on_products(
    ctx: Context, found: Submission, pull: dict[str, Any] | None
) -> dict[str, Any] | None:
    """F05-T13: a merged proposal whose node the products do not carry yet is waiting on the
    post-merge job, and says so, instead of reading as finished while every call on the node
    answers ``products-pending``. F05-T15: so is a merged annex the products' commit lacks, and a
    merged witness whose node still reads ``witness-missing``, the two other things precheck
    answers ``products-pending`` for. A merged postmortem or approach record waits on nothing.
    A graph that cannot be read changes nothing (C7)."""
    from opn_api.store import proposes  # noqa: PLC0415

    if pull is None or not pull.get("merged"):
        return pull
    if proposes(found):
        waits = _node_unrendered
    elif found.kind == "annex" and found.node_id is not None:
        waits = _annex_unrendered
    elif found.kind == "witness" and found.node_id is not None:
        waits = _witness_unrendered
    else:
        return pull
    try:
        waiting = waits(ctx, found, pull)
    except (ApiError, GitHostError, ValueError, KeyError) as exc:
        log.warning("pull request #%d: products not compared: %s", found.pr_number, exc)
        return pull
    return {**pull, "waiting_on": WAITING_ON_PRODUCTS} if waiting else pull


def _node_unrendered(ctx: Context, found: Submission, pull: dict[str, Any]) -> bool:
    from opn_api import precheck  # noqa: PLC0415 — precheck imports this module

    return not any(
        node.get("node_id") == found.node_id
        for nodes in precheck.graph_doc(ctx).values()
        for node in nodes
    )


def _annex_unrendered(ctx: Context, found: Submission, pull: dict[str, Any]) -> bool:
    """The merge commit carries an annex on the node that the commit the target's products were
    rendered from does not: the commit ``precheck.check_cited_annex`` pins a skeleton to. The
    record does not keep the annex's hash, so the node's two ``annex/`` listings are compared;
    both are at immutable commits."""
    from opn_api import precheck  # noqa: PLC0415 — precheck imports this module

    merge = pull.get("merge_commit_sha")
    if not merge:
        return False
    rendered = precheck.rendered_from(ctx, found.target_id)
    directory = f"targets/{found.target_id}/nodes/{found.node_id}/annex"
    # F07-T68: both listings are at immutable commits, so the answer is kept for that pair; and
    # an anonymous read, so held at the reserve (the caller then changes nothing, C7).
    key = (str(merge), rendered, directory)
    known = ctx.annex_unrendered.get(key)
    if known is not None:
        return known
    hold = budget_hold(ctx)
    if hold is not None:
        raise GitHostError(hold)
    repo = ctx.settings.graph_repo
    merged = ctx.githost.list_dir(repo, str(merge), directory) or []
    shown = ctx.githost.list_dir(repo, rendered, directory) or []
    answer = bool(set(merged) - set(shown))
    if len(ctx.annex_unrendered) >= MAX_REMEMBERED:
        ctx.annex_unrendered.clear()
    ctx.annex_unrendered[key] = answer
    return answer


def _witness_unrendered(ctx: Context, found: Submission, pull: dict[str, Any]) -> bool:
    """The node still reads ``witness-missing`` and ``main`` has the filled slot, the test
    precheck refuses on (``precheck.witness_awaits_render``)."""
    from opn_api import precheck  # noqa: PLC0415 — precheck imports this module

    for node in precheck.graph_doc(ctx).get(found.target_id, []):
        if node.get("node_id") == found.node_id:
            facts = precheck.facts_of(found.target_id, node)
            return precheck.witness_awaits_render(ctx, str(found.node_id), facts)
    return False


def answer(ctx: Context, raw: str) -> dict[str, Any]:
    submission_id, number = parse_id(raw)
    found = (
        ctx.store.get_submission(submission_id)
        if submission_id is not None
        else ctx.store.get_submission_by_pr(number or 0)
    )
    if found is None:
        return hand_opened(ctx, raw, number)

    # F05-T18: the two facts a cached state is held against, each read at most once per window
    # for every caller: where main is, and which pull requests the host still lists as open.
    if found.closed is None:
        frontier.pin_head(ctx)
        open_listing(ctx)
    found, pull, error = reconcile(ctx, found)
    pull = waiting_on_products(ctx, found, pull)

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
            if pull is not None and pull.get("merged"):
                # F05-T18: merged and not yet attested is the post-merge job still to commit,
                # which the guide calls ``products``; it read null (A12)
                pull = {**pull, "waiting_on": WAITING_ON_PRODUCTS}
    out = {
        "submission": document(found),
        "state": top_state(found, pull),
        "queue": queue_block(ctx, found, pull),
        "pull_request": pull,
        "pull_request_error": error,
        "gate_verdict": gate_verdict(ctx, found.pr_number, pull),
        "attestation_path": path,
        "attestation": attestation,
        "attestation_note": note,
    }
    from opn_api.store import proposes  # noqa: PLC0415

    if proposes(found):
        out["proposed_statement"], out["proposed_statement_error"] = proposed_statement(
            ctx, found, pull
        )
    return out


#: F07-T41: how much of a proposed ``Statement.lean`` an answer carries. A statement is a few
#: hundred bytes; the cap only keeps a pathological branch from swelling every read of it.
PROPOSED_STATEMENT_MAX_BYTES = 16 * 1024


def proposed_statement(
    ctx: Context, found: Submission, pull: dict[str, Any] | None
) -> tuple[dict[str, Any] | None, str | None]:
    """F07-T41: the statement a proposal proposes, read from its branch at the pull request's head
    commit (the record keeps what the pull request was, not what it says), so a contributor can
    see whether another open proposal is the same statement without leaving the network. It
    rides beside the ``submission`` document, never in it: ``GET /submissions.json`` lists those
    documents and must equal them. ``None`` with the reason when the host cannot say (C7)."""
    head = str((pull or {}).get("head_sha") or "")
    if not head:
        return None, "the pull request's head commit is not known, so its branch was not read"
    path = f"targets/{found.target_id}/nodes/{found.node_id}/Statement.lean"
    try:
        got = ctx.githost.fetch_raw(ctx.settings.graph_repo, head, path, etag=None)
    except GitHostError as exc:
        log.warning("pull request #%d: statement not read: %s", found.pr_number, exc)
        return None, f"the proposed statement could not be read from the host: {exc}"
    if got.status != 200 or got.body is None:
        return None, f"{path} at {head[:12]} answered {got.status}"
    raw = got.body
    return {
        "path": path,
        "head_sha": head,
        # a cut through a multi-byte character drops it rather than inventing a replacement
        "text": raw[:PROPOSED_STATEMENT_MAX_BYTES].decode("utf-8", errors="ignore"),
        "truncated": len(raw) > PROPOSED_STATEMENT_MAX_BYTES,
    }, None


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
    block = cached_block(ctx, number, state, error)
    return {
        "submission": None,
        "state": top_state(None, block),
        "queue": None,  # not a pull request the service opened: the actor does not take it
        "pull_request": block,
        "pull_request_error": error,
        "attestation_path": path,
        "attestation": attestation_doc(raw_doc, path),
        "attestation_note": None,
    }


async def get_submission(ctx: Context, request: Request) -> Response:
    doc = answer(ctx, str(request.path_params["submission_id"]))
    return JSONResponse(doc, headers=retry_after(ctx))


# --- GET /submissions.json ------------------------------------------------------------------------


def open_listing(ctx: Context) -> tuple[Listing | None, str | None, str | None]:
    """The host's open pull requests by number, why that is not fresh (``None`` when it is), and
    when it was read (F07-T47). One listing call per ``pull_listing_max_stale_s``, refreshed by
    one thread at a time; a host that cannot be read, or a budget that must not be spent, leaves
    the last listing standing with the reason (C7)."""
    with ctx.listing_lock:
        return _open_listing(ctx)


def _open_listing(ctx: Context) -> tuple[Listing | None, str | None, str | None]:
    cached = ctx.open_pulls
    now = time.monotonic()
    if cached is not None and now - cached.fetched_at < ctx.settings.pull_listing_max_stale_s:
        return cached.by_number, None, cached.read_at
    last = cached.by_number if cached is not None else None
    last_read = cached.read_at if cached is not None else None
    hold = budget_hold(ctx)
    if hold is not None:
        return last, hold, last_read
    try:
        listed = ctx.githost.list_open_pull_requests(ctx.settings.graph_repo)
    except RateLimitError as exc:
        log.warning("the open pull requests were not listed: %s", exc)
        return last, budget_message(ctx, exc.budget), last_read
    except GitHostError as exc:
        log.warning("the open pull requests were not listed: %s", exc)
        return last, f"the open pull requests could not be listed from the host: {exc}", last_read
    read_at = clockmod.render(ctx.clock.now())
    ctx.open_pulls = CachedListing({p.number: p for p in listed}, now, read_at)
    return ctx.open_pulls.by_number, None, read_at


def listed_state(entry: OpenPullRequest) -> PullRequestState:
    """What the listing says of an open pull request, as a state ``reconcile`` can read: open,
    not merged, its head. Never cached in ``Context.pulls`` and never served — the by-id route
    reads the full state (runs, reviews, mergeability) itself."""
    return PullRequestState(
        number=entry.number,
        url=entry.url,
        state="open",
        merged=False,
        mergeable_state="unknown",
        head_sha=entry.head_sha,
        merge_commit_sha=None,
    )


def snapshot(ctx: Context) -> dict[str, Any]:
    """The open records, each the ``submission`` document its own route carries, and ``host``:
    when the queue was last reconciled against the host and whether that is stale.

    Each is reconciled against the host first, so "open" means the host still calls it open and
    not merely that nobody has asked; a record the host cannot describe stays listed (C7).

    F07-T47: the host's open pull requests are read as one listing per window (F07-T39 had put
    one three-call read per record on a pool; eighteen pollers of this route then spent the
    App's hourly budget). A record the listing carries is open and costs nothing; one it lacks
    has finished, or is unknown, and is read once in full — on the pool, since those reads are
    what remain — and closed with the state that read found. With no listing at all, every
    record stays listed as it is, with the reason in ``host.error``.
    """
    records = ctx.store.list_open_submissions()
    listed, error, read_at = open_listing(ctx)
    still_open: list[Submission] = []
    firsts: dict[int, tuple[PullRequestState | None, str | None]] = {}
    if listed is not None:
        unlisted = [s for s in records if s.pr_number not in listed]
        width = min(ctx.settings.reconcile_concurrency, len(unlisted))
        if width > 1:
            with ThreadPoolExecutor(width, thread_name_prefix="reconcile") as pool:
                reads = list(pool.map(lambda s: live_state(ctx, s.pr_number), unlisted))
        else:
            reads = [live_state(ctx, s.pr_number) for s in unlisted]
        firsts = dict(zip((s.pr_number for s in unlisted), reads, strict=True))
    for submission in records:
        record = submission
        if listed is not None:
            entry = listed.get(submission.pr_number)
            first = firsts[submission.pr_number] if entry is None else (listed_state(entry), None)
            record, _, _ = reconcile(ctx, submission, first)
        if record.closed is None:
            still_open.append(record)
    # F05-T18: each entry's place in the merge actor's order, from the same listing; the list
    # itself is in that order, the pull requests the actor does not take after the ones it does
    order = queue_order(listed) if listed is not None else None
    rank = {number: index for index, number in enumerate(order or [])}
    still_open.sort(key=lambda s: (rank.get(s.pr_number, len(rank)), s.pr_number))
    lanes = {s.pr_number: s.target_id for s in still_open}
    open_now = [
        {**document(s), "queue": entry_queue(ctx, s.pr_number, order, lanes)} for s in still_open
    ]
    return {
        "snapshot_at": clockmod.render(ctx.clock.now()),
        "queue": {"order": order, "description": QUEUE_ORDER, "note": QUEUE_NOTE},
        "open": open_now,
        "host": {"read_at": read_at, "stale": error is not None, "error": error},
    }


#: F22-T8: the filters ``GET /submissions.json`` takes, equality only; ``kind=words`` is a gloss
#: or an explainer, the words of a subject (F21-R5).
SUBMISSION_FILTERS: tuple[str, ...] = ("target", "node", "kind")
WORDS_FILTER = "words"
_FILTER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_FILTER_KIND_RE = re.compile(r"^[a-z][a-z-]*$")


def submission_filters(request: Request) -> dict[str, str]:
    """F22-T8: the request's filters, each checked; a filter the route does not take, or a
    value that cannot name anything, is refused by the catalogued code that names it."""
    query = request.query_params
    unknown_filters = sorted(k for k in query if k not in SUBMISSION_FILTERS)
    if unknown_filters:
        raise ApiError(
            400,
            "filter-unknown",
            f"no such filter: {', '.join(unknown_filters)}; GET /submissions.json takes "
            + ", ".join(SUBMISSION_FILTERS),
            details={"unknown": unknown_filters, "accepted": list(SUBMISSION_FILTERS)},
        )
    out = {k: query[k] for k in SUBMISSION_FILTERS if k in query}
    if "target" in out and not _FILTER_ID_RE.match(out["target"]):
        raise ApiError(400, "target-id-invalid", "target must match ^[a-z0-9][a-z0-9-]*$")
    if "node" in out and not _FILTER_ID_RE.match(out["node"]):
        raise ApiError(400, "node-id-invalid", "node must match ^[a-z0-9][a-z0-9-]*$")
    if "kind" in out and not _FILTER_KIND_RE.match(out["kind"]):
        raise ApiError(
            400,
            "filter-unknown",
            f"kind is {WORDS_FILTER} (a gloss or an explainer) or one submission kind, "
            "as GET /submissions.json spells it",
        )
    return out


def matches(entry: dict[str, Any], filters: dict[str, str]) -> bool:
    kind = filters.get("kind")
    kinds = {"gloss", "explainer"} if kind == WORDS_FILTER else {kind}
    return (
        ("target" not in filters or entry.get("target_id") == filters["target"])
        and ("node" not in filters or entry.get("node_id") == filters["node"])
        and (kind is None or entry.get("kind") in kinds)
    )


def site_headers(ctx: Context) -> dict[str, str]:
    """F22-T8: the site's origin may read this listing from a page (a node's words in review);
    one configured origin, on this route only (``OPN_API_SITE_ORIGIN``)."""
    origin = ctx.settings.site_origin
    return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"} if origin else {}


async def get_submissions(ctx: Context, request: Request) -> Response:
    filters = submission_filters(request)
    doc = snapshot(ctx)
    if filters:
        doc["open"] = [e for e in doc["open"] if matches(e, filters)]
    return JSONResponse(doc, headers=retry_after(ctx) | site_headers(ctx))


# --- GET /submissions/mine (F07-T70) --------------------------------------------------------------


def mine(ctx: Context, pseudonym: str) -> dict[str, Any]:
    """The caller's own submissions: ``open``, each the listing's own entry (the record and its
    place in its lane of the queue, reconciled against the same host listing as
    ``GET /submissions.json``), and ``recent``, the ``MAX_RECENT_MINE`` most recently finished,
    newest first, each with how it ended (``state``: merged or closed). What ``GET /claims/mine``
    is for claims (F05-T14): a lost receipt never loses a pull request. A record finished before
    the per-pseudonym index existed is not in ``recent`` until it is next written."""
    wanted = pseudonym.lower()
    listed = snapshot(ctx)
    open_now = [e for e in listed["open"] if str(e["pseudonym"]).lower() == wanted]
    finished = [s for s in ctx.store.list_submissions_by(pseudonym) if s.closed is not None]
    # newest first: by when it finished, then by number (ULIDs made in one millisecond do not
    # sort by time; the host numbers pull requests in the order they were opened)
    finished.sort(key=lambda s: (str(s.closed), s.pr_number), reverse=True)
    recent = [
        {**document(s), "state": top_state(s, final_state(s))} for s in finished[:MAX_RECENT_MINE]
    ]
    return {
        "pseudonym": pseudonym,
        "snapshot_at": listed["snapshot_at"],
        "open": open_now,
        "recent": recent,
        "host": listed["host"],
    }


async def get_my_submissions(ctx: Context, request: Request) -> Response:
    identity: Identity = request.state.identity
    return JSONResponse(mine(ctx, identity.pseudonym), headers=retry_after(ctx))
