"""The formalization review's routes (F26-R14; D-9, D-28, D-35 v3.39).

Every review act is a record on the graph first (F26-Q3): the service opens pull requests and
reads the record at ``main``'s sha, and derives nothing the gate does not derive the same way
(``opn_gate.review`` over a copy of the review directory, so the state the service answers is
the state the products publish).

Writes, each refused by name before any pull request opens (F13-T21's rule):

* ``POST /reviews`` opens a review on a target — a web session or a bearer whose identity is a
  GitHub login. The role is derived, never trusted from the body: ``curator`` for a listed
  login, ``steward`` for an active steward of the target, ``proposer`` only when the body says
  ``role: proposer`` and the target has no review yet (the gate's check of F26-T3 is the arbiter
  of who proposed). ``policy.json``'s ``review_openers`` decides whether that role may open one
  (``review-opener-not-allowed``); one review per target (``review-exists``). The record goes
  on a ``review/`` branch, which the merge actor leaves to a curator.
* ``POST /reviews/<t>/candidates`` appends one ``candidate/v1`` record with its Lean for the
  bearer's identity, in one pull request on an ``append/`` branch. The blind rule's write half:
  the caller must declare ``read_others`` true or false (``candidate-not-blind``); the service
  shows nothing here. ``method`` is the identity's last automation declaration (D-23 v3.37), or
  ``manual`` for a candidate naming no model and ``other`` for one that does.
* ``POST /reviews/<t>/answers`` appends a ``review-answer/v1`` record for the intent signer
  alone — the proposer the opening names, or an active steward of the target for a review the
  network opened — signed by the approval key naming the login, as a v3.33 approval is.
* ``POST /reviews/<t>/signatures`` appends a ``review-signature/v1`` record: ``intent`` by the
  intent signer, ``independent`` by a login that is not the intent signer and authored no
  candidate on the record, by pseudonym or by login (F26-R9).

Reads, open: ``GET /reviews/<t>`` is the review as the records hold it, under the blind rule
(F26-R3, AC12): until the caller's own candidate is on the record — an anonymous caller, or a
bearer whose pseudonym authored none — every candidate's ``lean`` is ``null`` with
``lean_withheld: "blind"``; once it is, every Lean is shown. ``GET /reviews/<t>/questions`` is
the questions waiting, and carries no Lean at all.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, auth, duplicates, pending, ratelimit, session, stewards, submissions
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_gate import pair_proofs, review_lean
from opn_gate import paths as gatepaths
from opn_gate import policy as policymod
from opn_gate import review as reviewmod

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

SCHEMA_REVIEW = "review/v1"
SCHEMA_CANDIDATE = "candidate/v1"
SCHEMA_ANSWER = "review-answer/v1"
SCHEMA_SIGNATURE = "review-signature/v1"
KIND_REVIEW = "review"
KIND_CANDIDATE = "candidate"
KIND_ANSWER = "review-answer"
KIND_SIGNATURE = "review-signature"
#: The opening is a curator-class record: its branch is left to a curator to merge.
REVIEW_BRANCH_PREFIX = "review/"
#: F26 §6: candidates per review per identity per day.
CANDIDATES_PER_DAY = 3
LEAN_MAX_BYTES = 64 * 1024
WORDS_MAX = 20000  # review/v1's cap
ANSWER_MAX = 4000  # review-answer/v1's cap
CITES_MAX = 1000
CASE_KINDS: tuple[str, ...] = ("special-case", "small-value", "consequence", "non-example", "note")
SOURCE_KINDS: tuple[str, ...] = ("proposal", "registry", "existing")
OPENER_ROLES: tuple[str, ...] = ("proposer", "steward", "curator")
METHODS: tuple[str, ...] = ("manual", "copilot", "agent", "autonomous", "other")
SIGNER_ROLES: tuple[str, ...] = ("intent", "independent")
DECISIONS: tuple[str, ...] = ("accept", "split", "send-back")
BLIND = "blind"
#: F05-T8: what each route reads; any other top-level key is refused.
OPEN_FIELDS: tuple[str, ...] = ("target_id", "words", "cases", "concepts", "source", "role")
CANDIDATE_FIELDS: tuple[str, ...] = ("lean", "models", "read_others")
ANSWER_FIELDS: tuple[str, ...] = ("question", "answer", "cites")
SIGNATURE_FIELDS: tuple[str, ...] = ("role", "decision", "cluster", "question")
RECORD_SUFFIXES: tuple[str, ...] = (".yaml", ".yml")
ANSWER_RE = re.compile(r"^a-(?P<n>[1-9][0-9]*)\.ya?ml$")
SIGNATURE_RE = re.compile(
    r"^(?P<role>intent|independent)-(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})-(?P<n>[1-9][0-9]*)\.ya?ml$"
)
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


def bad(message: str, field: str) -> ApiError:
    return ApiError(400, "arguments-invalid", message, details={"field": field})


# --- the record at main ---------------------------------------------------------------------------


def review_dir(target_id: str) -> str:
    return f"targets/{target_id}/{gatepaths.REVIEW_DIR}"


def _yaml(raw: bytes | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    return doc if isinstance(doc, dict) else None


def opening(ctx: Context, target_id: str) -> dict[str, Any] | None:
    """``review.yaml`` at ``main``, or ``None`` for a target with no review."""
    return _yaml(pending.optional_committed(ctx, f"{review_dir(target_id)}/review.yaml"))


def required_opening(ctx: Context, target_id: str) -> dict[str, Any]:
    head = opening(ctx, target_id)
    if head is None:
        raise ApiError(
            404,
            "review-unknown",
            f"{target_id} has no review on the graph; one opens with POST /reviews",
            details={"target_id": target_id},
        )
    return head


def records(ctx: Context, target_id: str, sub: str) -> list[tuple[str, dict[str, Any]]]:
    """``(name, document)`` of every readable record under ``review/<sub>/`` at ``main``, in
    name order; a file that is not a record is skipped, as the gate's reader skips it."""
    directory = f"{review_dir(target_id)}/{sub}"
    out: list[tuple[str, dict[str, Any]]] = []
    for name in sorted(session.listing(ctx, directory)):
        if not name.endswith(RECORD_SUFFIXES):
            continue
        doc = _yaml(pending.optional_committed(ctx, f"{directory}/{name}"))
        if doc is not None:
            out.append((name, doc))
    return out


def candidates(ctx: Context, target_id: str) -> list[dict[str, Any]]:
    return [doc for _, doc in records(ctx, target_id, "candidates")]


def questions(ctx: Context, target_id: str) -> dict[str, dict[str, Any]]:
    return {str(doc.get("id")): doc for _, doc in records(ctx, target_id, "questions")}


def answered_questions(ctx: Context, target_id: str) -> set[str]:
    return {str(doc.get("question")) for _, doc in records(ctx, target_id, "answers")}


def materialise(ctx: Context, root: Path, target_id: str) -> Path:
    """The review directory copied under ``root`` as the graph holds it at ``main`` — every
    record and every Lean beside one — and the target directory answered, so the gate's own
    derivation (``opn_gate.review``) runs over exactly what the products are rendered from."""
    base = review_dir(target_id)
    head = pending.optional_committed(ctx, f"{base}/review.yaml")
    target_dir = root / "targets" / target_id
    if head is not None:
        dest = target_dir / gatepaths.REVIEW_DIR / "review.yaml"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(head)
    for sub in gatepaths.REVIEW_ROLES_BY_DIR:
        directory = f"{base}/{sub}"
        for name in session.listing(ctx, directory):
            if not name.endswith((*RECORD_SUFFIXES, ".json", ".lean")):
                continue
            body = pending.optional_committed(ctx, f"{directory}/{name}")
            if body is None:
                continue
            dest = target_dir / gatepaths.REVIEW_DIR / sub / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
    return target_dir


# --- roles ----------------------------------------------------------------------------------------


def policy_of(ctx: Context) -> policymod.Policy:
    """The graph's ``policy.json`` as the gate reads it, or the defaults with no file; a file
    the gate would refuse is an outage, never a default (C7)."""
    body = pending.optional_committed(ctx, policymod.FILE)
    try:
        return policymod.parse(body)
    except Exception as exc:  # SchemaError, or a malformed file
        raise ApiError(503, "graph-unreadable", f"{policymod.FILE}: {exc}") from exc


def opener_role(ctx: Context, target_id: str, login: str, claimed: Any) -> str:
    """The role the login opens in (D-9 v3.39): a claimed role is honoured only when the login
    holds it; otherwise the highest one held. ``proposer`` is a claim the login makes about a
    target that has no review (the gate's check is the arbiter), never derived."""
    if claimed is not None and claimed not in OPENER_ROLES:
        raise bad(f"role is one of {', '.join(OPENER_ROLES)}", "role")
    held: list[str] = []
    if session.is_curator(ctx, login):
        held.append("curator")
    if session.is_steward(ctx, target_id, login):
        held.append("steward")
    if claimed == "proposer":
        held.append("proposer")
    if claimed is not None and claimed not in held:
        raise ApiError(
            403,
            "review-opener-not-allowed",
            f"{login} is not a {claimed} of {target_id}",
            details={"target_id": target_id, "role": claimed, "held": held},
        )
    if not held:
        raise ApiError(
            403,
            "review-opener-not-allowed",
            f"{login} is neither a listed curator nor an active steward of {target_id}, and "
            "did not propose the problem (role: proposer); only they may open a review (D-9 v3.39)",
            details={"target_id": target_id, "role": None, "held": []},
        )
    return claimed if claimed is not None else held[0]


def check_openers(ctx: Context, target_id: str, role: str) -> None:
    allowed = list(policy_of(ctx).review_openers)
    if role not in allowed:
        raise ApiError(
            403,
            "review-opener-not-allowed",
            f"policy.json allows {', '.join(allowed)} to open a review, not a {role}",
            details={"target_id": target_id, "role": role, "allowed": allowed},
        )


def check_no_review(ctx: Context, target_id: str) -> None:
    """One review per target: merged (``review.yaml`` at main), or proposed in a pull request
    of the service's that may still merge."""
    if opening(ctx, target_id) is not None:
        raise ApiError(
            409,
            "review-exists",
            f"{target_id} has a review already; a revision of the root opens a new one (D-8)",
            details={"target_id": target_id},
        )
    for found in ctx.store.list_open_submissions():
        if found.kind != KIND_REVIEW or found.target_id != target_id:
            continue
        if duplicates.blocks(ctx, found):
            raise ApiError(
                409,
                "review-exists",
                f"pull request #{found.pr_number} already opens a review on {target_id} and may "
                "still merge",
                details={
                    "target_id": target_id,
                    "pr_number": found.pr_number,
                    "pr_url": found.pr_url,
                    "submission_id": found.id,
                },
            )


def intent_signer_holds(ctx: Context, target_id: str, head: dict[str, Any], login: str) -> bool:
    """R9: the proposer the opening names, or, for any other opener (the network's background
    review, a steward's or a curator's), an active steward of the target."""
    opened_by = head.get("opened_by") or {}
    if opened_by.get("role") == "proposer":
        return str(opened_by.get("identity", "")).casefold() == login.casefold()
    return session.is_steward(ctx, target_id, login)


def require_intent_signer(ctx: Context, target_id: str, head: dict[str, Any], login: str) -> None:
    if intent_signer_holds(ctx, target_id, head, login):
        return
    opened_by = head.get("opened_by") or {}
    if opened_by.get("role") == "proposer":
        who = f"the proposer, {opened_by.get('identity')}"
    elif session.active_stewards(session.steward_records(ctx, target_id)):
        who = f"an active steward of {target_id}"
    else:
        who = (
            f"an active steward of {target_id}, and it has none: the review needs a steward (D-32)"
        )
    raise ApiError(
        403,
        "review-not-intent-signer",
        f"{login} is not the intent signer of {target_id}'s review; that is {who}",
        details={"target_id": target_id, "login": login},
    )


# --- the opening ----------------------------------------------------------------------------------


def checked_words(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip() or len(raw) > WORDS_MAX:
        raise bad(f"words is the conjecture in words, 1 to {WORDS_MAX} characters", "words")
    return raw


def checked_cases(raw: Any) -> list[dict[str, str]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise bad("cases is a list of {kind, text}", "cases")
    out: list[dict[str, str]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) != {"kind", "text"}:
            raise bad(f"cases[{i}] is an object of kind and text", "cases")
        out.append({"kind": str(item["kind"]), "text": str(item["text"])})
    return out


def checked_concepts(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(c, str) for c in raw):
        raise bad("concepts is a list of names", "concepts")
    return list(raw)


def checked_source(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {"kind": "proposal", "ref": None}
    if not isinstance(raw, dict) or set(raw) != {"kind", "ref"}:
        raise bad("source is an object of kind and ref", "source")
    if raw["ref"] is not None and not isinstance(raw["ref"], str):
        raise bad("source.ref is a string or null", "source.ref")
    return {"kind": raw["kind"], "ref": raw["ref"]}


def render(doc: dict[str, Any]) -> str:
    """The file as it lands: the schema's field order."""
    return str(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))


def open_record_pr(  # noqa: PLR0913 — one pull request, described
    ctx: Context,
    identity: Identity,
    *,
    files: dict[str, str],
    subject: str,
    kind: str,
    target_id: str,
    written: str,
    branch_prefix: str,
    body: str,
    automation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One record (and the Lean beside it, for a candidate), one branch, one pull request,
    recorded as ``kind`` so it can be watched through ``GET /submissions/{id}``; a request
    identical to one open for the target is refused before anything is pushed (F07-T35)."""
    prints = duplicates.check_append(ctx, kind, target_id, written)
    record_id = identitymod.new_ulid(ctx.clock.now())
    slots = [duplicates.slot(kind, target_id, fp) for fp in prints]
    with duplicates.holding(ctx, slots, kind):
        pr = submissions.open_pr(
            ctx,
            identity,
            branch=branch_prefix + record_id,
            files=files,
            subject=subject,
            title=subject,
            body=body,
        )
    pending.record(
        ctx,
        identity,
        submission_id=record_id,
        kind=kind,
        target_id=target_id,
        node_id=None,
        pr=pr,
        fingerprints=prints,
        automation=automation,
    )
    path = next(iter(files))
    return {"id": record_id, "path": path, "pr_url": pr.url, "pr_number": pr.number}


def pr_body(what: str, pseudonym: str, path: str, checks: str) -> str:
    return (
        f"A {what} appended through the Open Proof Network service by `{pseudonym}`. It claims "
        f"nothing a kernel checks: the gate checks {checks}.\n\n`{path}`\n"
    )


async def post_reviews(ctx: Context, request: Request) -> Response:
    """R14: open a review, as the sign-in, in its own pull request on a ``review/`` branch."""
    held: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, OPEN_FIELDS)
    login = stewards.github_login(held)
    target_id = appends.known_target(ctx, fields.get("target_id"))
    words = checked_words(fields.get("words"))
    cases = checked_cases(fields.get("cases"))
    concepts = checked_concepts(fields.get("concepts"))
    source = checked_source(fields.get("source"))
    role = opener_role(ctx, target_id, login, fields.get("role"))
    ratelimit.enforce(
        ctx,
        KIND_REVIEW,
        login.casefold(),
        limit=ctx.settings.stewards_per_day,
        seconds=ratelimit.DAY_S,
    )
    check_openers(ctx, target_id, role)
    check_no_review(ctx, target_id)
    doc: dict[str, Any] = {
        "schema": SCHEMA_REVIEW,
        "target": target_id,
        "opened_by": {"identity": login, "role": role},
        "date": ctx.clock.now().strftime("%Y-%m-%d"),
        "words": words,
        "cases": cases,
        "concepts": concepts,
        "source": source,
        "tracking": None,
        "supersedes": None,
    }
    appends.validated(doc, SCHEMA_REVIEW)
    path = f"{review_dir(target_id)}/review.yaml"
    body = open_record_pr(
        ctx,
        held,
        files={path: render(doc)},
        subject=f"review: open {target_id} by {login}",
        kind=KIND_REVIEW,
        target_id=target_id,
        written=f"review {target_id}",
        branch_prefix=REVIEW_BRANCH_PREFIX,
        body=pr_body(
            "review opening",
            held.pseudonym,
            path,
            "its path, its schema, and that the opener's role is one policy.json's "
            "review_openers allows (F26-R2; D-9 v3.39)",
        ),
    )
    return JSONResponse(stewards.receipt(body, REVIEW_BRANCH_PREFIX), status_code=201)


# --- candidates -----------------------------------------------------------------------------------


def checked_lean(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise bad("lean is required: the candidate's Lean text", "lean")
    if len(raw.encode("utf-8")) > LEAN_MAX_BYTES:
        raise ApiError(
            400,
            "field-too-long",
            f"lean is longer than {LEAN_MAX_BYTES} bytes",
            details={"field": "lean", "max_bytes": LEAN_MAX_BYTES},
        )
    return raw


def checked_models(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(m, str) and m.strip() for m in raw):
        raise bad("models is a list of model names, each a non-empty string", "models")
    return list(raw)


def checked_read_others(fields: dict[str, Any]) -> bool:
    """The blind rule's declaration (F26-R3): true or false, never omitted."""
    value = fields.get("read_others")
    if not isinstance(value, bool):
        raise ApiError(
            400,
            "candidate-not-blind",
            "read_others must be declared true or false: whether you read another candidate's "
            "Lean before writing this one (the blind rule, D-9 v3.39); it is recorded as your "
            "claim",
            details={"field": "read_others"},
        )
    return value


def last_method(ctx: Context, pseudonym: str, models: list[str]) -> str:
    """D-23 v3.37: the method the identity last declared on a submission; with none declared,
    ``manual`` for a candidate naming no model and ``other`` for one that does."""
    latest: tuple[str, str] | None = None
    for found in ctx.store.list_submissions_by(pseudonym):
        method = (found.automation or {}).get("method")
        if method in METHODS and (latest is None or found.created > latest[0]):
            latest = (found.created, str(method))
    if latest is not None:
        return latest[1]
    return "manual" if not models else "other"


def candidate_id(lean: str) -> tuple[str, str]:
    """``(id, statement_hash)``: ``c-<8 hex>`` of the Lean's sha256, and the whole digest."""
    digest = hashlib.sha256(lean.encode("utf-8")).hexdigest()
    return f"c-{digest[:8]}", digest


async def post_candidates(ctx: Context, request: Request) -> Response:
    """R14: one candidate with its Lean, for the bearer's identity, in one pull request."""
    held: Identity = request.state.identity
    target_id = appends.known_target(ctx, request.path_params.get("target_id"))
    fields, _ = await identitymod.body_fields(request, CANDIDATE_FIELDS)
    lean = checked_lean(fields.get("lean"))
    models = checked_models(fields.get("models"))
    read_others = checked_read_others(fields)
    required_opening(ctx, target_id)
    ratelimit.enforce(
        ctx,
        KIND_CANDIDATE,
        f"{held.pseudonym.casefold()}#{target_id}",
        limit=CANDIDATES_PER_DAY,
        seconds=ratelimit.DAY_S,
    )
    cid, digest = candidate_id(lean)
    if any(c.get("id") == cid for c in candidates(ctx, target_id)):
        raise ApiError(
            409,
            "candidate-exists",
            f"{target_id}'s review already holds candidate {cid} (the same Lean, byte for byte)",
            details={"target_id": target_id, "candidate": cid},
        )
    doc: dict[str, Any] = {
        "schema": SCHEMA_CANDIDATE,
        "target": target_id,
        "id": cid,
        "author": held.pseudonym,
        "method": last_method(ctx, held.pseudonym, models),
        "models": models,
        "read_others": read_others,
        "origin": "submitted",
        "source": None,
        "lean_file": f"{cid}.lean",
        "statement_hash": digest,
        "date": ctx.clock.now().strftime("%Y-%m-%d"),
    }
    appends.validated(doc, SCHEMA_CANDIDATE)
    base = f"{review_dir(target_id)}/candidates"
    path = f"{base}/{cid}.yaml"
    body = open_record_pr(
        ctx,
        held,
        files={path: render(doc), f"{base}/{cid}.lean": lean},
        subject=f"candidate: {target_id} {cid} by {held.pseudonym}",
        kind=KIND_CANDIDATE,
        target_id=target_id,
        written=f"candidate {target_id} {digest}",
        branch_prefix=submissions.APPEND_BRANCH_PREFIX,
        body=pr_body(
            "candidate formalization",
            held.pseudonym,
            path,
            "its path, its schema, and that its Lean sits beside it; the review job compiles, "
            "screens and tests it in the sandbox (F26-R4). Submitted blind: the author declared "
            f"read_others: {str(read_others).lower()}, a claim the record shows (F26-R3)",
        ),
    )
    return JSONResponse(stewards.receipt(body, submissions.APPEND_BRANCH_PREFIX), status_code=201)


# --- answers --------------------------------------------------------------------------------------


def checked_id(raw: Any, field: str) -> str:
    if not isinstance(raw, str) or not ID_RE.match(raw):
        raise bad(f"{field} is a record id (lowercase letters, digits and hyphens)", field)
    return raw


def checked_text(raw: Any, field: str, cap: int) -> str:
    if not isinstance(raw, str) or not raw.strip() or len(raw) > cap:
        raise bad(f"{field} is a string of 1 to {cap} characters", field)
    return raw


def known_question(ctx: Context, target_id: str, question: str) -> None:
    if question not in questions(ctx, target_id):
        raise ApiError(
            404,
            "review-question-unknown",
            f"{target_id}'s review has no question {question}",
            details={"target_id": target_id, "question": question},
        )


def answer_fingerprint(target_id: str, question: str) -> str:
    return f"answer {target_id} {question}"


def check_unanswered(ctx: Context, target_id: str, question: str) -> None:
    """One answer per question: a merged answer names it, or a pull request of the service's
    that may still merge carries one (its fingerprint is the question's)."""
    if question in answered_questions(ctx, target_id):
        raise ApiError(
            409,
            "review-question-answered",
            f"question {question} of {target_id}'s review is answered on the record",
            details={"target_id": target_id, "question": question},
        )
    fp = duplicates.fingerprint(answer_fingerprint(target_id, question))
    for found in ctx.store.list_open_submissions():
        if found.kind != KIND_ANSWER or found.target_id != target_id:
            continue
        if fp in found.fingerprints and duplicates.blocks(ctx, found):
            raise ApiError(
                409,
                "review-question-answered",
                f"pull request #{found.pr_number} already answers question {question} and may "
                "still merge",
                details={
                    "target_id": target_id,
                    "question": question,
                    "pr_number": found.pr_number,
                    "pr_url": found.pr_url,
                    "submission_id": found.id,
                },
            )


def open_of_kind(ctx: Context, kind: str, target_id: str, day: str | None = None) -> int:
    return sum(
        1
        for found in ctx.store.list_open_submissions()
        if found.kind == kind
        and found.target_id == target_id
        and (day is None or found.created[:10] == day)
    )


def next_answer_name(ctx: Context, target_id: str) -> str:
    """``a-<n>.yaml`` after every answer merged and every one still open for the target."""
    taken = [
        int(m.group("n"))
        for name, _ in records(ctx, target_id, "answers")
        if (m := ANSWER_RE.match(name)) is not None
    ]
    return f"a-{max(taken, default=0) + open_of_kind(ctx, KIND_ANSWER, target_id) + 1}.yaml"


async def post_answers(ctx: Context, request: Request) -> Response:
    """R14: the intent signer's answer to one question, signed with the approval key."""
    held: Identity = request.state.identity
    target_id = appends.known_target(ctx, request.path_params.get("target_id"))
    fields, _ = await identitymod.body_fields(request, ANSWER_FIELDS)
    login = stewards.github_login(held)
    question = checked_id(fields.get("question"), "question")
    answer = checked_text(fields.get("answer"), "answer", ANSWER_MAX)
    cites = fields.get("cites")
    if cites is not None:
        cites = checked_text(cites, "cites", CITES_MAX)
    private, public = stewards.approval_key(ctx)
    head = required_opening(ctx, target_id)
    ratelimit.enforce(
        ctx,
        KIND_ANSWER,
        login.casefold(),
        limit=ctx.settings.approvals_per_hour,
        seconds=ratelimit.HOUR_S,
    )
    require_intent_signer(ctx, target_id, head, login)
    known_question(ctx, target_id, question)
    check_unanswered(ctx, target_id, question)
    name = next_answer_name(ctx, target_id)
    doc = stewards.sign_record(
        {
            "schema": SCHEMA_ANSWER,
            "target": target_id,
            "id": name.rsplit(".", 1)[0],
            "question": question,
            "answer": answer,
            "cites": cites,
            "date": ctx.clock.now().strftime("%Y-%m-%d"),
            "login": login,
            "via": stewards.VIA,
        },
        private,
        public,
    )
    appends.validated(doc, SCHEMA_ANSWER)
    path = f"{review_dir(target_id)}/answers/{name}"
    body = open_record_pr(
        ctx,
        held,
        files={path: render(doc)},
        subject=f"answer: {target_id} {question} by {login}",
        kind=KIND_ANSWER,
        target_id=target_id,
        written=answer_fingerprint(target_id, question),
        branch_prefix=submissions.APPEND_BRANCH_PREFIX,
        body=pr_body(
            "review answer",
            held.pseudonym,
            path,
            "its path, its schema, its signature under the graph's approval key, that its login "
            "is the review's intent signer and that the question is open (F26-R7, R9)",
        ),
    )
    return JSONResponse(stewards.receipt(body, submissions.APPEND_BRANCH_PREFIX), status_code=201)


# --- signatures -----------------------------------------------------------------------------------


def authored_by(cands: list[dict[str, Any]], held: Identity, login: str) -> list[str]:
    """The candidates on the record whose author is the signer, by pseudonym or by login."""
    mine = {held.pseudonym.casefold(), login.casefold()}
    return [str(c.get("id")) for c in cands if str(c.get("author", "")).casefold() in mine]


def require_signer(  # noqa: PLR0913 — one role, every condition
    ctx: Context,
    target_id: str,
    head: dict[str, Any],
    *,
    held: Identity,
    login: str,
    role: str,
) -> None:
    """R9: ``intent`` is the intent signer; ``independent`` is anyone else who authored no
    candidate on the record."""
    is_intent = intent_signer_holds(ctx, target_id, head, login)
    if role == "intent":
        if not is_intent:
            raise ApiError(
                403,
                "review-not-signer",
                f"{login} is not the intent signer of {target_id}'s review and cannot sign as one",
                details={"target_id": target_id, "login": login, "role": role},
            )
        return
    if is_intent:
        raise ApiError(
            403,
            "review-not-signer",
            f"{login} is the intent signer of {target_id}'s review; the independent signer is "
            "someone else (F26-R9)",
            details={"target_id": target_id, "login": login, "role": role},
        )
    wrote = authored_by(candidates(ctx, target_id), held, login)
    if wrote:
        raise ApiError(
            403,
            "review-signer-wrote-candidate",
            f"{login} authored {', '.join(wrote)} on {target_id}'s review; the independent signer "
            "wrote no candidate (F26-R9)",
            details={"target_id": target_id, "login": login, "candidates": wrote},
        )


def next_signature_name(ctx: Context, target_id: str, role: str, day: str) -> str:
    """``<role>-<day>-<n>.yaml`` after every signature of that role merged that day and every
    signature pull request of the service's still open for the target that day, whatever its
    role: a gap costs nothing, since the number only tells records apart (F25's rule)."""
    taken = [
        int(m.group("n"))
        for name, _ in records(ctx, target_id, "signatures")
        if (m := SIGNATURE_RE.match(name)) is not None
        and m.group("role") == role
        and m.group("date") == day
    ]
    open_today = open_of_kind(ctx, KIND_SIGNATURE, target_id, day)
    return f"{role}-{day}-{max(taken, default=0) + open_today + 1}.yaml"


async def post_signatures(ctx: Context, request: Request) -> Response:
    """R14: one signer's decision, by role, signed with the approval key."""
    held: Identity = request.state.identity
    target_id = appends.known_target(ctx, request.path_params.get("target_id"))
    fields, _ = await identitymod.body_fields(request, SIGNATURE_FIELDS)
    login = stewards.github_login(held)
    role = fields.get("role")
    if role not in SIGNER_ROLES:
        raise bad(f"role is one of {', '.join(SIGNER_ROLES)}", "role")
    decision = fields.get("decision")
    if decision not in DECISIONS:
        raise bad(f"decision is one of {', '.join(DECISIONS)}", "decision")
    cluster = fields.get("cluster")
    question = fields.get("question")
    if decision == "send-back":
        if cluster is not None:
            raise bad("a send-back names no cluster", "cluster")
    elif cluster is None:
        raise bad(f"{decision} names the candidate representing the cluster", "cluster")
    if cluster is not None:
        cluster = checked_id(cluster, "cluster")
    if question is not None:
        question = checked_id(question, "question")
    private, public = stewards.approval_key(ctx)
    head = required_opening(ctx, target_id)
    ratelimit.enforce(
        ctx,
        KIND_SIGNATURE,
        login.casefold(),
        limit=ctx.settings.approvals_per_hour,
        seconds=ratelimit.HOUR_S,
    )
    require_signer(ctx, target_id, head, held=held, login=login, role=str(role))
    if cluster is not None and not any(c.get("id") == cluster for c in candidates(ctx, target_id)):
        raise ApiError(
            404,
            "candidate-unknown",
            f"{target_id}'s review has no candidate {cluster}",
            details={"target_id": target_id, "candidate": cluster},
        )
    if question is not None:
        known_question(ctx, target_id, question)
    day = ctx.clock.now().strftime("%Y-%m-%d")
    name = next_signature_name(ctx, target_id, str(role), day)
    doc = stewards.sign_record(
        {
            "schema": SCHEMA_SIGNATURE,
            "target": target_id,
            "role": role,
            "decision": decision,
            "cluster": cluster,
            "question": question,
            "date": day,
            "login": login,
            "via": stewards.VIA,
        },
        private,
        public,
    )
    appends.validated(doc, SCHEMA_SIGNATURE)
    path = f"{review_dir(target_id)}/signatures/{name}"
    body = open_signature_pr(ctx, held, path=path, doc=doc, login=login, role=str(role))
    return JSONResponse(stewards.receipt(body, submissions.APPEND_BRANCH_PREFIX), status_code=201)


def open_signature_pr(  # noqa: PLR0913 — one pull request, described
    ctx: Context, held: Identity, *, path: str, doc: dict[str, Any], login: str, role: str
) -> dict[str, Any]:
    target_id = str(doc["target"])
    written = (
        f"signature {target_id} {role} {login} {doc['decision']} {doc['cluster']} {doc['question']}"
    )
    prints = duplicates.check_append(ctx, KIND_SIGNATURE, target_id, written)
    record_id = identitymod.new_ulid(ctx.clock.now())
    slots = [duplicates.slot(KIND_SIGNATURE, target_id, fp) for fp in prints]
    subject = f"signature: {target_id} {role} {doc['decision']} by {login}"
    with duplicates.holding(ctx, slots, KIND_SIGNATURE):
        pr = submissions.open_pr(
            ctx,
            held,
            branch=submissions.APPEND_BRANCH_PREFIX + record_id,
            files={path: render(doc)},
            subject=subject,
            title=subject,
            body=pr_body(
                "review signature",
                held.pseudonym,
                path,
                "its path, its schema, its signature under the graph's approval key, and that "
                "its login holds the role it signs in (F26-R9)",
            ),
        )
    pending.record(
        ctx,
        held,
        submission_id=record_id,
        kind=KIND_SIGNATURE,
        target_id=target_id,
        node_id=None,
        pr=pr,
        fingerprints=prints,
    )
    return {"id": record_id, "path": path, "pr_url": pr.url, "pr_number": pr.number}


# --- the reads ------------------------------------------------------------------------------------


def caller_of(ctx: Context, request: Request) -> Identity | None:
    """The bearer's identity when one is presented (a bad one is refused, never read as
    anonymous), else ``None``."""
    if auth.bearer(request) is None:
        return None
    return auth.authenticate(ctx, request)


def read_at(ctx: Context) -> str:
    return str(ctx.head or ctx.settings.graph_branch)


def review_document(
    ctx: Context, target_id: str, caller: Identity | None, n: int | None = None
) -> dict[str, Any]:
    """The review as the records hold it, the state derived by the gate's own module, and every
    candidate's Lean under the blind rule."""
    with tempfile.TemporaryDirectory(prefix="opn-review-") as tmp:
        target_dir = materialise(ctx, Path(tmp), target_id)
        head = reviewmod.opening(target_dir)
        if head is None:
            raise ApiError(
                404,
                "review-unknown",
                f"{target_id} has no review on the graph; one opens with POST /reviews",
                details={"target_id": target_id},
            )
        base = target_dir / gatepaths.REVIEW_DIR
        state = reviewmod.state_of(target_dir)
        open_pairs = reviewmod.open_pairs(target_dir)
        waiting = {str(q.get("id")) for q in reviewmod.questions_waiting(target_dir)}
        cands = _docs(base / "candidates")
        mine = caller is not None and any(
            str(c.get("author", "")).casefold() == caller.pseudonym.casefold() for c in cands
        )
        concepts = [str(x) for x in head.get("concepts") or []]
        sources: dict[str, str | None] = {}
        shown: list[dict[str, Any]] = []
        for c in cands:
            lean_path = base / "candidates" / str(c.get("lean_file", ""))
            lean = lean_path.read_text(encoding="utf-8") if lean_path.is_file() else None
            sources[str(c.get("id"))] = lean
            shown.append(
                {
                    **c,
                    "lean": lean if mine else None,
                    "lean_withheld": None if mine else BLIND,
                }
            )
        return {
            "target_id": target_id,
            "read_at": read_at(ctx),
            "caller": None if caller is None else caller.pseudonym,
            "blind": not mine,
            "review": head,
            "state": state,
            "candidates": shown,
            "tests": _docs(base / "tests"),
            "questions": [
                {**q, "waiting": str(q.get("id")) in waiting} for q in _docs(base / "questions")
            ],
            "answers": _docs(base / "answers"),
            "pairs": in_force(_named(base / "pairs")),
            "open_pairs": [
                {
                    **row,
                    **direction_templates(
                        prepared(sources.get(row["a"]), row["a"], concepts),
                        prepared(sources.get(row["b"]), row["b"], concepts),
                        row["direction"],
                        shown=mine,
                        n=n,
                    ),
                }
                for row in open_pairs
            ],
            "exhibits": _json_docs(base / "exhibits"),
            "signatures": _docs(base / "signatures"),
        }


def _docs(folder: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.iterdir()):
        if path.suffix in RECORD_SUFFIXES:
            doc = _yaml(path.read_bytes())
            if doc is not None:
                out.append(doc)
    return out


def _json_docs(folder: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.iterdir()):
        if path.suffix != ".json":
            continue
        try:
            doc = json.loads(path.read_bytes())
        except ValueError:
            continue
        if isinstance(doc, dict):
            out.append(doc)
    return out


def waiting_questions(ctx: Context, target_id: str) -> list[dict[str, Any]]:
    """The questions no answer names, each with its target, in the records' order; a target
    with no review has none."""
    if opening(ctx, target_id) is None:
        return []
    answered = answered_questions(ctx, target_id)
    return [
        {"target_id": target_id, **doc}
        for _, doc in records(ctx, target_id, "questions")
        if str(doc.get("id")) not in answered
    ]


def in_force(named: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    """F26-T19: the pair records in force, one per pair, from ``(file name, record)``: the gate's
    own rule (``opn_gate.review.latest_of``, T18), so a later record written the same day as
    ``<a>--<b>--<date>-<k>.yaml`` supersedes ``<a>--<b>.yaml`` here exactly as it does in the
    gate's derivation. Every listing and the submission route read pairs through here."""
    return reviewmod.latest_of(named)


def _named(folder: Path) -> list[tuple[str, dict[str, Any]]]:
    """``(file name, document)`` of every readable record in ``folder``, in name order."""
    out: list[tuple[str, dict[str, Any]]] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.iterdir()):
        if path.suffix in RECORD_SUFFIXES:
            doc = _yaml(path.read_bytes())
            if doc is not None:
                out.append((path.name, doc))
    return out


#: What a caller is told of the refutation template, which takes an instance.
REFUTATION_NOTE = (
    "A refutation is an instance: a natural number `n` at which the direction's first claim holds "
    "and its second fails. Ask for its template with `n` (list_open_pairs with n, or GET "
    "/reviews/<id>?n=<n>), fill it, and submit it with pair.kind refutation and pair.n."
)


def prepared(source: str | None, cid: str, concepts: list[str]) -> review_lean.Cand | str:
    if source is None:
        return f"candidate {cid}'s Lean is not on the record"
    return review_lean.prepare(cid, source, concepts)


def direction_templates(
    a: review_lean.Cand | str,
    b: review_lean.Cand | str,
    direction: str,
    *,
    shown: bool,
    n: int | None,
) -> dict[str, Any]:
    """F26-T19: the fields an open direction gains — its proof template, ready to fill, and how
    to get the refutation template — under the blind rule (F26-R3): a template is both
    candidates' Lean, so a caller with no candidate on the record is shown none of it."""
    if isinstance(a, str) or isinstance(b, str):
        why = a if isinstance(a, str) else str(b)
        return {
            "template": None,
            "template_withheld": None,
            "template_note": why,
            "refutation": {"available": False, "note": why, "template": None},
        }
    first, second = pair_proofs.ordered(a, b, direction)  # type: ignore[arg-type]
    why_not = pair_proofs.provable(first, second)
    no_refute = pair_proofs.refutable(first, second)
    refute_at = None
    if shown and no_refute is None and n is not None:
        refute_at = pair_proofs.template(a, b, direction, "refutation", n)  # type: ignore[arg-type]
    return {
        "template": (
            pair_proofs.template(a, b, direction) if shown and why_not is None else None  # type: ignore[arg-type]
        ),
        "template_withheld": None if shown else BLIND,
        "template_note": why_not,
        "refutation": {
            "available": no_refute is None,
            "note": REFUTATION_NOTE if no_refute is None else no_refute,
            "template": refute_at,
        },
    }


def checked_n(raw: Any) -> int | None:
    """The refutation instance a read asks templates for: a natural number, or absent."""
    if raw is None:
        return None
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise bad("n is a natural number: the instance a refutation template is asked at", "n")
    return raw


def open_directions(
    ctx: Context, target_id: str, caller: str | None = None, n: int | None = None
) -> list[dict[str, Any]]:
    """Each open pair direction of the pair records in force, with its last attempt (F26-R8),
    in the records' order; F26-T19: and its templates, shown to ``caller`` (a pseudonym) only
    when it authored a candidate on the record (the blind rule)."""
    head = opening(ctx, target_id)
    if head is None:
        return []
    concepts = [str(x) for x in head.get("concepts") or []]
    cands = {str(c.get("id")): c for c in candidates(ctx, target_id)}
    shown = caller is not None and any(
        str(c.get("author", "")).casefold() == caller.casefold() for c in cands.values()
    )
    cache: dict[str, review_lean.Cand | str] = {}

    def cand(cid: str) -> review_lean.Cand | str:
        if cid not in cache:
            doc = cands.get(cid)
            source = None
            if doc is not None:
                path = f"{review_dir(target_id)}/candidates/{doc.get('lean_file')}"
                raw = pending.optional_committed(ctx, path)
                source = None if raw is None else raw.decode("utf-8")
            cache[cid] = prepared(source, cid, concepts)
        return cache[cid]

    out: list[dict[str, Any]] = []
    for p in in_force(records(ctx, target_id, "pairs")):
        for direction in ("forward", "backward"):
            d = p.get(direction)
            if isinstance(d, dict) and d.get("state") == "open":
                a, b = str(p.get("a")), str(p.get("b"))
                out.append(
                    {
                        "target_id": target_id,
                        "a": a,
                        "b": b,
                        "direction": direction,
                        "attempt": d.get("attempt"),
                        "submit_as": "pair-proof",
                        **direction_templates(cand(a), cand(b), direction, shown=shown, n=n),
                    }
                )
    return out


async def get_review(ctx: Context, request: Request) -> Response:
    target_id = appends.known_target(ctx, request.path_params.get("target_id"))
    caller = caller_of(ctx, request)
    n = checked_n(request.query_params.get("n"))
    return JSONResponse(review_document(ctx, target_id, caller, n))


async def get_questions(ctx: Context, request: Request) -> Response:
    target_id = appends.known_target(ctx, request.path_params.get("target_id"))
    found = waiting_questions(ctx, target_id)
    return JSONResponse(
        {
            "target_id": target_id,
            "read_at": read_at(ctx),
            "count": len(found),
            "questions": found,
        }
    )
