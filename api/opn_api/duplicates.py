"""F07-T35: a copy is refused before a pull request opens (D-25 v3.21; testers 2026-09-23).

Every write route used to open a pull request without looking at what was already open for the
node, so #150 (a witness identical, comments aside, to #146) and #168/#171 (one statement twice)
each cost a gate round and a slot in a strictly sequential queue, and the loser sat open for a
person to close. D-25 lets a node keep every *different* proof; what it never keeps is a copy.

What counts as the same, per kind:

* a proof, partial or alternate: the same text once Lean comments and whitespace are set aside,
  against the node's merged proof and attempts and against every submission open for it;
* a witness: any witness, while one is open for the hole — a hole has one slot;
* a proposal: the same node id, which the scaffold derives from the statement;
* an annex, postmortem or approach record: the same text for the same node.

An open pull request blocks only while it can still merge: one whose gate failed, that conflicts
with ``main`` or that has closed is set aside, so a corrected resubmission goes through (#171).
The check reads the open records, which are written after the pull request opens, so two identical
requests in the same seconds would both pass it; each also takes an atomic counter on its slot for
a short window, and the second is refused.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from opn_api import pending, precheck
from opn_api.app import ApiError

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Submission

log = logging.getLogger(__name__)

ERROR = "duplicate-submission"
#: How long a request holds its slot against an identical one arriving at the same moment. A
#: legitimate resubmission follows a gate round (minutes), so it lands in a later window.
SLOT_WINDOW_S = 120
#: Waiting states in which an open pull request can no longer merge as it stands.
NOT_BLOCKING = frozenset({"gate-failed", "conflict"})
_WHITESPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """The text with Lean comments removed — ``--`` to the end of the line, and ``/- … -/``,
    which nest — and every run of whitespace made one space."""
    out: list[str] = []
    depth, i, n = 0, 0, len(text)
    while i < n:
        pair = text[i : i + 2]
        if pair == "/-":
            depth, i = depth + 1, i + 2
        elif pair == "-/" and depth:
            depth, i = depth - 1, i + 2
        elif depth:
            i += 1
        elif pair == "--":
            end = text.find("\n", i)
            i = n if end < 0 else end
        else:
            out.append(text[i])
            i += 1
    return _WHITESPACE.sub(" ", "".join(out)).strip()


def fingerprint(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def slot(kind: str, node_id: str, content: str = "") -> str:
    """The thing two requests must not both take: a kind of artifact on a node, and for a proof
    or an append the content it carries."""
    return f"{kind}#{node_id}#{content}"


def counter_key(ctx: Context, key: str) -> str:
    return f"dup#{key}#{int(ctx.clock.now().timestamp()) // SLOT_WINDOW_S}"


def claim_slot(ctx: Context, key: str) -> int:
    """Take the slot for this window; the count says how many requests have taken it."""
    expires = ctx.clock.now() + timedelta(seconds=2 * SLOT_WINDOW_S)
    return ctx.store.bump_counter(counter_key(ctx, key), expires)


def blocks(ctx: Context, found: Submission) -> bool:
    """Whether an open record still stands in the way: its pull request is open and can merge.
    A record the host cannot describe is taken as blocking (C7: say no rather than open a copy)."""
    record, _live, _error = pending.reconcile(ctx, found)
    if record.closed is not None:
        return False
    state, _why = pending.live_state(ctx, found.pr_number)
    if state is None:
        return True
    if state.finished:
        return False
    return state.waiting_on not in NOT_BLOCKING


def open_rivals(ctx: Context, node_id: str, kinds: frozenset[str]) -> list[Submission]:
    return [
        found
        for found in ctx.store.list_open_submissions()
        if found.node_id == node_id and found.kind in kinds and blocks(ctx, found)
    ]


def refused(message: str, found: Submission | None = None, **extra: Any) -> ApiError:
    details: dict[str, Any] = dict(extra)
    if found is not None:
        details |= {"pr_number": found.pr_number, "pr_url": found.pr_url, "submission_id": found.id}
    return ApiError(409, ERROR, message, details=details)


@contextmanager
def holding(ctx: Context, keys: list[str], what: str) -> Iterator[None]:
    """Around the opening of a pull request, after every other check: refuse the second of two
    identical requests arriving together, and give the slots back if the pull request did not
    open (a push the host refused), so the same request can be sent again at once (C7)."""
    held = [counter_key(ctx, key) for key in keys]
    take(ctx, keys, what)  # refused here, it holds nothing: the slot is the other request's
    try:
        yield
    except BaseException:
        for key in held:
            try:
                ctx.store.drop_counter(key)
            except Exception as exc:  # any store failure: the window expires the slot anyway
                log.warning("slot %s not released: %s", key, type(exc).__name__)
        raise


def take(ctx: Context, keys: list[str], what: str) -> None:
    """Refuse the second of two identical requests arriving together."""
    for key in keys:
        if claim_slot(ctx, key) > 1:
            wait = SLOT_WINDOW_S - int(ctx.clock.now().timestamp()) % SLOT_WINDOW_S
            raise ApiError(
                409,
                ERROR,
                f"an identical {what} for this node was submitted in the last "
                f"{SLOT_WINDOW_S // 60} minutes; read GET /submissions.json, and if it is not "
                "there (its pull request failed to open), submit again after Retry-After",
                headers={"Retry-After": str(wait)},
            )


# --- per kind -------------------------------------------------------------------------------------


def check_witness(ctx: Context, node_id: str) -> None:
    """One witness slot per hole: any open witness that can still merge refuses another."""
    for found in open_rivals(ctx, node_id, frozenset({"witness"})):
        raise refused(
            f"{node_id} already has a witness open as pull request #{found.pr_number}; a hole has "
            "one witness slot, so a second could never merge. Wait for it: if its gate fails or "
            "it is closed, a witness may be proposed again",
            found,
        )


def check_proposal(ctx: Context, node_id: str) -> None:
    """One open proposal per statement: the node id is derived from the statement."""
    for found in open_rivals(ctx, node_id, frozenset({"speculative", "variant"})):
        raise refused(
            f"this statement is already proposed as {node_id} in pull request "
            f"#{found.pr_number}; a statement is proposed once. If that proposal's gate fails, "
            "propose it again with the correction",
            found,
        )


def merged_texts(ctx: Context, target_id: str, node_id: str) -> dict[str, str]:
    """The node's merged proof and attempts, by path; a host that cannot answer refuses nothing
    here (C7), and the gate's byte-identical alternate check still stands behind it."""
    prefix = f"targets/{target_id}/nodes/{node_id}/"
    proved = any(
        node.get("node_id") == node_id and node.get("proof_commit")
        for node in precheck.graph_doc(ctx).get(target_id, [])
    )
    # the node's Proof.lean counts only once the graph says it merged, as for existing_paths
    paths = [prefix + "Proof.lean"] if proved else []
    try:
        names = ctx.githost.list_dir(
            ctx.settings.graph_repo, ctx.settings.graph_branch, prefix + "attempts"
        )
    except Exception as exc:  # any host failure: the check is advisory
        log.warning("%s: attempts not listed: %s", node_id, type(exc).__name__)
        names = None
    paths += [f"{prefix}attempts/{name}" for name in names or () if name.endswith(".lean")]
    out: dict[str, str] = {}
    for path in paths:
        try:
            body = pending.optional_committed(ctx, path)
        except ApiError:
            body = None
        if body is not None:
            out[path] = body.decode("utf-8", errors="replace")
    return out


PROOF_KINDS = frozenset({"proof", "partial", "counterexample", "vacuity", "reduction"})


def check_proof(
    ctx: Context, target_id: str, node_id: str, files: dict[str, str], *, tutorial: bool = False
) -> list[str]:
    """Refuse a proof whose Lean text is already merged on the node or open for it; answer the
    fingerprints to record with the submission, so the next request can be compared with it.
    The tutorial node is exempt: resubmitting its proof is the rehearsal D-27 keeps it open for."""
    prints = sorted({fingerprint(text) for path, text in files.items() if path.endswith(".lean")})
    if tutorial:
        return []
    for path, text in merged_texts(ctx, target_id, node_id).items():
        if fingerprint(text) in prints:
            raise refused(
                f"this is, comments and whitespace aside, the text already merged at {path}; "
                "a node keeps every different proof but never a copy (D-25)",
                path=path,
            )
    for found in open_rivals(ctx, node_id, PROOF_KINDS):
        if set(found.fingerprints) & set(prints):
            raise refused(
                f"this is, comments and whitespace aside, the proof already open for {node_id} as "
                f"pull request #{found.pr_number}; a different proof may race it, a copy may not "
                "(D-25)",
                found,
            )
    return prints


APPEND_KINDS = frozenset({"annex", "postmortem", "approach-record"})


def check_append(ctx: Context, kind: str, node_id: str, text: str) -> list[str]:
    """Refuse an append identical to one open for the same node (or target, for an approach
    record, whose ``node_id`` here is the target's). ``text`` is what the contributor wrote, not
    the file the service renders, which carries the contributor's name and the date."""
    fp = fingerprint(text)
    for found in open_rivals(ctx, node_id, frozenset({kind})):
        if fp in found.fingerprints:
            raise refused(
                f"an identical {kind} for {node_id} is already open as pull request "
                f"#{found.pr_number}",
                found,
            )
    return [fp]
