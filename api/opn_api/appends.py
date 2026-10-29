"""The append routes (F07-R9, R11, R14; D-13, D-14, D-31, D-34).

``POST /postmortems``, ``POST /annexes`` and ``POST /approach-records`` put a record into the
graph through a pull request the gate merges on schema and path checks alone, because none of
them claims anything a kernel could check (F07-Q4). One rule holds all three: the caller supplies
the content, the service supplies the identity, and the file lands at the path its decision
fixes — ``attempts/`` for a postmortem (D-13), ``annex/<hash>.md`` for an annex (D-31),
``targets/<id>/approaches/`` for an approach record (D-14).

Free text is capped and stored verbatim (R14): the caps come from the schema itself, so there is
one number per field and it is the one the gate enforces. Nothing here interpolates contributor
text into a command, a template or a query — it is written to a file and served, later, as
demarcated untrusted data (D-28, C9).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import clock as clockmod
from opn_api import duplicates, frontier, pending, precheck, submissions
from opn_api import identity as identitymod
from opn_api import uses as usesmod
from opn_api.app import ApiError
from opn_gate import annex as annexmod
from opn_gate import labels, records, schemas

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity, Submission

log = logging.getLogger(__name__)

#: postmortem/v2 (D-23): the record states the model and tooling that drafted it, as an approach
#: record does; written for a target whose pinned gate reads it (``postmortem_schema``).
POSTMORTEM_SCHEMA = records.POSTMORTEM_SCHEMA
POSTMORTEM_V1 = "postmortem/v1"
ANNEX_SCHEMA = "annex/v1"
APPROACH_SCHEMA = "approach-record/v1"
ANNEX_MAX_BYTES = 64 * 1024  # F07 §6
#: F29-Q4: the gate's list is the one home (``opn_gate.labels.LICENCES``); the service reads it.
LICENCES: tuple[str, ...] = labels.LICENCES
FILE_TIMESTAMP = "%Y%m%dT%H%M%SZ"  # sorts lexically, and is a legal file name everywhere


def stamp(ctx: Context) -> str:
    return ctx.clock.now().strftime(FILE_TIMESTAMP)


def record_name(ctx: Context, identity: Identity) -> str:
    """D-13's ``<timestamp>-<contributor>``. Two records in one second by one identity would share
    it, and the gate's append-only rule would then refuse whichever merged second as a
    modification; ``holding_name`` refuses the second before it opens (F13-T23)."""
    return f"{stamp(ctx)}-{identity.pseudonym}"


#: F13-T23: the refusal of a record at a path another request is opening, or an open pull
#: request already adds.
NAME_ERROR = "record-name-taken"
#: The window of the in-flight hold (``name_key``). The hold is dropped once the submission is
#: recorded, after which the open record holds the path itself (``path_holder``); the window is
#: only how long a hold left by a process that died mid-opening lasts (one to two windows).
NAME_HOLD_S = 60
#: The fingerprint an append records for the file it adds (``path_print``), so an open pull
#: request can be found by its path; a record made before 2026-10-29 carries none.
PATH_PRINT = "path:"
#: D-13's ``<timestamp>-<pseudonym>`` file name, which names its second.
TIMESTAMP_NAME_RE = re.compile(r"^\d{8}T\d{6}Z-")


def path_print(path: str) -> str:
    return PATH_PRINT + path


def timestamp_named(path: str) -> bool:
    """Whether the file is named for its second (D-13), so a second later the name is free."""
    return TIMESTAMP_NAME_RE.match(path.rsplit("/", 1)[-1]) is not None


def name_key(ctx: Context, path: str, *, back: int = 0) -> str:
    """The in-flight hold's counter: the path and a window, as ``duplicates.counter_key`` is, so
    a hold nobody dropped lapses with its window in either store (the memory store never
    expires a counter, and DynamoDB counts an expired one until its TTL sweep). ``back`` names
    an earlier window."""
    window = int(ctx.clock.now().timestamp()) // NAME_HOLD_S - back
    return f"name#{path}#{window}"


def path_holder(ctx: Context, path: str) -> Submission | None:
    """The open submission, still able to merge, that adds ``path`` (``duplicates.blocks``: one
    merged, closed, withdrawn, gate-failed or conflicting holds nothing)."""
    wanted = path_print(path)
    for found in ctx.store.list_open_submissions():
        if wanted in found.fingerprints and duplicates.blocks(ctx, found):
            return found
    return None


def name_refusal(path: str, found: Submission | None) -> tuple[str, dict[str, Any]]:
    """The refusal's message and details: who holds the path, and whether waiting frees it."""
    details: dict[str, Any] = {"path": path}
    if found is None:
        if timestamp_named(path):
            return (
                f"a record of yours is being filed at {path} this second: a record's file name "
                "is <timestamp>-<pseudonym> to the second (D-13), so a second one now would "
                "share it and could never merge. Send it again after Retry-After",
                details,
            )
        return (
            f"another request is opening a pull request that adds {path} at this moment; two "
            "pull requests adding one file could never both merge. Send it again after "
            "Retry-After: if that one opened, the answer names it",
            details,
        )
    details |= {"pr_number": found.pr_number, "pr_url": found.pr_url, "submission_id": found.id}
    if timestamp_named(path):
        return (
            f"a record of yours filed this second is open at {path} as pull request "
            f"#{found.pr_number}: a record's file name is <timestamp>-<pseudonym> to the second "
            "(D-13), so a second one now would share it and could never merge. Send it again "
            "after Retry-After",
            details,
        )
    return (
        f"pull request #{found.pr_number} is open and already adds {path}; two pull requests "
        "adding one file could never both merge. This file is named by its content or "
        "numbered after the last merged record, not by the second, so waiting does not free "
        f"it: it is free once #{found.pr_number} merges (a numbered record then takes the next "
        "number) or is withdrawn, and a different text has a different content-named path",
        details,
    )


@dataclass
class NameHold:
    """What ``holding_name`` holds: the counter it took, and whether the pull request opened
    (``append_pr`` says so), since a hold whose pull request opened is kept on a failure."""

    key: str | None
    opened: bool = False


@contextmanager
def holding_name(ctx: Context, path: str) -> Iterator[NameHold]:
    """F13-T23, testers 2026-10-27 F-D9: one pull request per file. Two pull requests adding one
    path could never both merge (the gate's append-only rule refuses the second as a
    modification), so a request for a path is refused ``409 record-name-taken``, and nothing
    opens, in two cases.

    Standing: an open submission still able to merge already adds the path (``path_holder``),
    named in the refusal. It holds the path until it merges or is withdrawn, however long that
    is; a ``<timestamp>-<pseudonym>`` file (D-13) frees itself a second later, so only that
    refusal carries ``Retry-After``.

    In flight: another request is opening a pull request at the path, which the store cannot
    show yet. The path is taken with an atomic counter keyed by the path and a window
    (``name_key``); the current window and the one before are both read, so two requests either
    side of a boundary are still one. Refused ``Retry-After: 1``. Once the pull request has
    opened (``NameHold.opened``), ``append_pr`` drops the counter as soon as the submission is
    recorded (``release_name``), so it never outlasts the opening; if the pull request does not
    open it is dropped as the block ends, so the same request can be sent again at once (C7);
    if it opened and recording failed, it is kept and lapses with its window."""
    found = path_holder(ctx, path)
    if found is not None:
        message, details = name_refusal(path, found)
        retry = {"Retry-After": "1"} if timestamp_named(path) else None
        raise ApiError(409, NAME_ERROR, message, details=details, headers=retry)
    expires = ctx.clock.now() + timedelta(seconds=2 * NAME_HOLD_S)
    key = name_key(ctx, path)
    earlier = ctx.store.bump_counter(name_key(ctx, path, back=1), expires, by=0)
    if ctx.store.bump_counter(key, expires) > 1 or earlier > 0:
        ctx.store.bump_counter(key, expires, by=-1)  # give back the count this request took
        message, details = name_refusal(path, None)
        raise ApiError(409, NAME_ERROR, message, details=details, headers={"Retry-After": "1"})
    hold = NameHold(key)
    try:
        yield hold
    finally:
        if not hold.opened:  # opened: the caller releases it once the submission is recorded
            release_name(ctx, hold)


def release_name(ctx: Context, hold: NameHold) -> None:
    """Drop the in-flight counter; a store that fails leaves it to lapse with its window."""
    if hold.key is None:
        return
    try:
        ctx.store.drop_counter(hold.key)
    except Exception as exc:  # any store failure: the hold lapses with its window
        log.warning("name %s not released: %s", hold.key, type(exc).__name__)
    hold.key = None


def string_cap(spec: Any) -> int | None:
    """A property's string cap, stated on the property or on a ``oneOf``/``anyOf`` branch (a
    nullable string, as ``approach-record/v1`` states ``model_and_tooling``; testers 2026-10-08)."""
    if not isinstance(spec, dict):
        return None
    cap = spec.get("maxLength")
    if isinstance(cap, int):
        return cap
    branches = [*spec.get("oneOf", []), *spec.get("anyOf", [])]
    caps = [c for c in (string_cap(b) for b in branches) if c is not None]
    return min(caps) if caps else None


def check_caps(doc: dict[str, Any], schema_id: str) -> None:
    """R14, AC19: every capped string field, against the cap its own schema publishes.

    The cap is checked here rather than left to validation so the refusal can name the field and
    the number without echoing the text back — a 5,000-character detail must not travel twice.
    """
    properties = schemas.load_schema(schema_id).get("properties", {})
    for field, spec in properties.items():
        cap = string_cap(spec)
        value = doc.get(field)
        if isinstance(cap, int) and isinstance(value, str) and len(value) > cap:
            raise ApiError(
                400,
                "field-too-long",
                f"{field} is {len(value)} characters; the cap is {cap}",
            )


def validated(doc: dict[str, Any], schema_id: str) -> dict[str, Any]:
    """The record, or a 400 naming the first field that does not satisfy its schema."""
    check_caps(doc, schema_id)
    problems = schemas.violations(doc, schema_id)
    if problems:
        first = problems[0]
        raise ApiError(400, "record-invalid", f"{first.path}: {first.message}")
    return doc


def as_mapping(raw: Any, field: str) -> dict[str, Any]:
    """The record the caller sent, as an object — JSON already, or a YAML document."""
    if isinstance(raw, str):
        try:
            raw = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise ApiError(400, f"{field}-invalid", f"{field} is not parseable YAML") from exc
    if not isinstance(raw, dict):
        raise ApiError(400, f"{field}-invalid", f"{field} must be an object or a YAML document")
    return dict(raw)


def node_target(ctx: Context, fields: dict[str, Any]) -> tuple[str, str]:
    node_id = fields.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        raise ApiError(400, "node-id-missing", "node_id is required")
    facts = precheck.node_facts(ctx, node_id)
    return node_id, str(facts["target_id"])


def written_record(doc: dict[str, Any]) -> str:
    """What the contributor wrote, for the duplicate rule (F07-T35): the record before the service
    names its contributor and dates it, so two authors' identical records compare equal."""
    kept = {k: v for k, v in doc.items() if k not in ("schema", "contributor", "date", "node")}
    return str(yaml.safe_dump(kept, sort_keys=True, allow_unicode=True))


def node_dir(target_id: str, node_id: str) -> str:
    return f"targets/{target_id}/nodes/{node_id}/"


#: F22-T3 (testers 2026-10-06, P3-16): what the gate checks for each kind of append, as the
#: pull-request body says it. A kind not listed gets its path and its schema (F07-R9).
APPEND_CHECKS: dict[str, str] = {
    "gloss": (
        "its path, its schema, the Lean file it describes (at that file's hash), that it "
        "supersedes its chain's head, and that a model's draft changes no section a person "
        "wrote (F20-R1 to R7, F21-R12)"
    ),
    "explainer": (
        "its path, its schema, the merged proof it describes, its sections' steps against that "
        "proof's outline, that it supersedes its chain's head, and that a model's draft changes "
        "no section a person wrote (F20-R1 to R7, F21-R12)"
    ),
    "withdrawal": "its path, its schema, and that its author may withdraw that version (F20-R7)",
    "defect claim": (
        "its path, its schema, D-16's pre-triage, and its exhibit, elaborated in the sandbox"
    ),
    "revision request": "its path, its schema, and any exhibit, elaborated in the sandbox",
    "steward record": (
        "its path, its schema, its signature under the graph's approval key, and that its "
        "admission agrees with policy.json (F23-R9)"
    ),
    "approval": (
        "its path, its schema, its signature under the graph's approval key, and that the version "
        "and sections it approves exist (F23-R10, R11)"
    ),
    # D-25 v3.35 (F05-T29, F23-T12): a proposal is unsigned; a confirmation is signed.
    "literature record": (
        "its path and its schema (F07-R9); an unsigned literature record is a proposal and "
        "counts for nothing until a steward of the target or a curator confirms it (D-25 v3.35)"
    ),
    "literature confirmation": (
        "its path, its schema, its signature under the graph's approval key, and that its signer "
        "is an active steward of the target or a listed curator (D-25, D-32 v3.35)"
    ),
    # F23-T13 (D-25 v3.45): the same signed record, naming the proposal it rejects.
    "literature dispute": (
        "its path, its schema, its signature under the graph's approval key, that its signer "
        "is an active steward of the target or a listed curator, and that the record it "
        "disputes is an unsigned proposal on the node (D-25, D-32 v3.45)"
    ),
    # F31-R1 (D-14, D-32 v3.47): a steward's or curator's judgment, signed; never a status.
    "shelving": (
        "its path, its schema, its signature under the graph's approval key, that its signer is "
        "an active steward of the target or a listed curator, that the node is not the root and "
        "is used by no merged proof, and that a named route is one of the node's merged "
        "decompositions (D-14 v3.47)"
    ),
    # F25-R5, R6 (D-3, D-10 v3.37): the two records outside the node.
    "registration record": (
        "its path, its schema, that its submitter is a listed curator or an active steward of the "
        "target and is who the pull request acts for, that its proof names a node of the target "
        "and that node's passing attestation, and that its graph commit is in the graph's "
        "history (F25-R5)"
    ),
    "display name": (
        "its path, its schema, its signature under the graph's approval key, and that it is for "
        "the pseudonym the pull request acts for and no other (F25-R6, D-3 v3.37)"
    ),
}
DEFAULT_CHECKS = "its path and its schema (F07-R9)"


def article(word: str) -> str:
    """``a`` or ``an`` for ``word``, by its first letter: every kind named here is spelt so that
    its vowel letter is its sound (an annex, an explainer, an approach record)."""
    return "an" if word[:1].lower() in "aeiou" else "a"


def pr_body(what: str, pseudonym: str, path: str) -> str:
    """An append's pull-request body: the kind with its article, who filed it, and what the gate
    checks for that kind; it claims nothing a kernel checks."""
    checks = APPEND_CHECKS.get(what, DEFAULT_CHECKS)
    return (
        f"{article(what).capitalize()} {what} appended through the Open Proof Network service by "
        f"`{pseudonym}`. It claims nothing a kernel checks: the gate checks {checks}.\n\n"
        f"`{path}`\n"
    )


def append_pr(  # noqa: PLR0913 — one pull request, described
    ctx: Context,
    identity: Identity,
    *,
    path: str,
    content: str,
    subject: str,
    what: str,
    kind: str,
    target_id: str,
    node_id: str | None,
    written: str | None = None,
    defect_class: str | None = None,
    subject_prints: tuple[str, ...] = (),
    subject_slots: tuple[str, ...] = (),
    extra_body: str = "",
    branch_prefix: str = submissions.APPEND_BRANCH_PREFIX,
    hold_name: bool = True,
) -> dict[str, Any]:
    """One appended file, one branch, one pull request (R11, R2), recorded as ``kind`` so its
    state can be watched through ``GET /submissions/{id}`` (F07-T16). F07-T35: an append
    identical to one open for the same node (or target) is refused before anything is pushed.
    F21-Q5: ``subject_prints`` are recorded beside the content fingerprints (a gloss's or
    explainer's subject key), and ``subject_slots`` are held with them, so two requests for one
    slot arriving together cannot both open (F21-R5). ``extra_body`` follows the body's own lines
    (F22-T4: the gate's warnings to a gloss or explainer). ``branch_prefix`` is ``append/``, which
    the merge actor takes, except for a steward record under reviewed admission (F23-R8:
    ``curate/``, left to a curator). ``hold_name`` is the one-pull-request-per-file rule
    (``holding_name``); a route whose file has one fixed path and its own one-writer rule
    (``names/<pseudonym>.yaml``, F25-R6) turns it off. Testers 2026-10-27 F-D9: the submission
    records the file it adds (``path_print``), which is what holds the path while it is open,
    and the in-flight name hold is given back once it is recorded, so a withdrawn submission
    lets its path go at once."""
    owner = node_id or target_id
    prints = duplicates.check_append(ctx, kind, owner, written or content)
    append_id = identitymod.new_ulid(ctx.clock.now())
    slots = [duplicates.slot(kind, owner, fp) for fp in prints] + list(subject_slots)
    name_hold = holding_name(ctx, path) if hold_name else unheld()
    with duplicates.holding(ctx, slots, kind), name_hold as held_name:
        pr = submissions.open_pr(
            ctx,
            identity,
            branch=branch_prefix + append_id,
            files={path: content},
            subject=subject,
            title=subject,
            body=pr_body(what, identity.pseudonym, path) + extra_body,
        )
        held_name.opened = True  # kept until the record below stands in its place
    log.info("%s %s opened %s for %s", what, append_id, pr.url, identity.id)
    pending.record(
        ctx,
        identity,
        submission_id=append_id,
        kind=kind,
        target_id=target_id,
        node_id=node_id,
        pr=pr,
        fingerprints=[*prints, *subject_prints, path_print(path)],
        defect_class=defect_class,
    )
    release_name(ctx, held_name)  # the open record holds the path now (``path_holder``)
    return {"id": append_id, "path": path, "pr_url": pr.url, "pr_number": pr.number}


@contextmanager
def unheld() -> Iterator[NameHold]:
    """``holding_name``'s stand-in for a route that opts out: holds nothing."""
    yield NameHold(None)


# --- POST /postmortems (D-13) ---------------------------------------------------------------------


#: F05-T8: the fields ``POST /postmortems`` reads; any other top-level key is refused.
POSTMORTEM_FIELDS: tuple[str, ...] = ("node_id", "yaml")


def postmortem_schema(ctx: Context, target_id: str) -> str:
    """The postmortem version written for ``target_id``: v2 when its pinned gate carries the
    v2 schema, else v1 as before. An older gate refuses a v2 file at classify, so a pull request
    opened there could never merge; the answer comes from the pin, as ``annex/v2``'s does."""
    if usesmod.pinned_has(ctx, target_id, f"gate/schemas/{POSTMORTEM_SCHEMA}.json"):
        return POSTMORTEM_SCHEMA
    return POSTMORTEM_V1


def postmortem_tooling(doc: dict[str, Any], schema: str, target_id: str) -> None:
    """The record's own ``model_and_tooling`` (D-23), as declared and never verified: an absent
    one is ``null`` in v2, which requires the field. v1 has no such field, so on an older pin a
    null is dropped and a declared model is refused before anything opens, naming why."""
    if schema != POSTMORTEM_V1:
        doc.setdefault("model_and_tooling", None)
        return
    if doc.get("model_and_tooling") is not None:
        raise ApiError(
            400,
            "record-invalid",
            f"model_and_tooling: the gate {target_id} pins reads postmortem/v1, which has no "
            f"model_and_tooling; {POSTMORTEM_SCHEMA} carries it and reaches a target at its "
            "re-pin. Send the record without it meanwhile",
        )
    doc.pop("model_and_tooling", None)


async def post_postmortems(ctx: Context, request: Request) -> Response:
    """R11: a typed failed attempt, contributed under the caller's identity (AC15)."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, POSTMORTEM_FIELDS)
    node_id, target_id = node_target(ctx, fields)
    doc = as_mapping(fields.get("yaml"), "yaml")
    written = written_record(doc)
    schema = postmortem_schema(ctx, target_id)
    postmortem_tooling(doc, schema, target_id)
    doc["schema"] = schema
    doc["node"] = node_id
    doc["contributor"] = identity.pseudonym  # AC15: the caller, whatever the record said
    validated(doc, schema)
    path = node_dir(target_id, node_id) + f"attempts/{record_name(ctx, identity)}.yaml"
    content = yaml.safe_dump(doc, sort_keys=True, allow_unicode=True)
    return JSONResponse(
        append_pr(
            ctx,
            identity,
            path=path,
            content=content,
            subject=f"postmortem: {node_id}",
            what="postmortem",
            kind="postmortem",
            target_id=target_id,
            node_id=node_id,
            written=written,
        ),
        status_code=201,
    )


# --- POST /annexes (D-31) -------------------------------------------------------------------------


def check_licence(raw: Any, *, licensed: str = "the annex is licensed") -> str:
    """D-23's amendment: annex prose is licensed by its author at submission, or not accepted.
    F05-T17: an absent licence is refused, not defaulted — until 2026-10-01 it was silently
    recorded as ``CC-BY-4.0``, a choice the record then attributed to an author who never made
    it. ``licensed`` names what is being licensed, since ``POST /glosses`` shares the check."""
    if raw is None:
        raise ApiError(
            400,
            "licence-required",
            f"licence is required: {licensed} by its author at submission (D-23); "
            f"one of {', '.join(LICENCES)}",
            details={"accepted": list(LICENCES)},
        )
    if raw not in LICENCES:
        raise ApiError(400, "licence-invalid", f"licence must be one of {', '.join(LICENCES)}")
    return str(raw)


def annex_file(doc: dict[str, Any], text: str) -> str:
    """The file as it lands: YAML front matter, then the prose exactly as it was sent (R14)."""
    head = yaml.safe_dump(doc, sort_keys=True, allow_unicode=True)
    body = text if text.endswith("\n") else text + "\n"
    return f"---\n{head}---\n{body}"


#: F05-T8: the fields ``POST /annexes`` reads; any other top-level key is refused.
ANNEX_FIELDS: tuple[str, ...] = ("node_id", "text", "licence", "model_and_tooling", "steps")
#: F18-R6 (D-31 v3.26): an annex that names its steps is written as this version.
STEPPED_ANNEX_SCHEMA = annexmod.STEPPED_SCHEMA


def check_steps(ctx: Context, target_id: str, front: dict[str, Any], raw: Any) -> None:
    """F18-R6: ``steps`` held to ``annex/v2`` and to unique ids (``record-invalid``), and taken
    only for a target whose pinned gate reads ``annex/v2`` (``annex-steps-unsupported``): an
    older gate refuses such an append, so the pull request would open and go red. The summaries
    are the author's text, written as sent and acted on by nothing (C9)."""
    front["schema"] = STEPPED_ANNEX_SCHEMA
    front["steps"] = raw
    validated(front, STEPPED_ANNEX_SCHEMA)
    repeated = annexmod.duplicate_step_ids(front)
    if repeated:
        raise ApiError(
            400,
            "record-invalid",
            "steps: the step id " + ", ".join(repeated) + " is named more than once; a stepped "
            "annex's ids are unique, since a skeleton's hole is matched to a step by its name",
            details={"duplicates": repeated},
        )
    if not usesmod.pinned_from(
        ctx, target_id, ctx.settings.annex_steps_from, what="stepped annexes"
    ):
        raise ApiError(
            400,
            "annex-steps-unsupported",
            f"the gate {target_id} pins does not read a stepped annex (annex/v2, D-31 v3.26) "
            "yet; it reaches a target at its re-pin. Submit the annex without steps",
        )


async def post_annexes(ctx: Context, request: Request) -> Response:
    """R11, AC14: the hash a skeleton must cite is the file's, and it is the file's name too."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, ANNEX_FIELDS)
    node_id, target_id = node_target(ctx, fields)
    text = fields.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ApiError(400, "text-missing", "text is required")
    if len(text.encode()) > ANNEX_MAX_BYTES:
        raise ApiError(
            400,
            "field-too-long",
            f"the annex is {len(text.encode())} bytes; the cap is {ANNEX_MAX_BYTES}",
        )
    front = {
        "schema": ANNEX_SCHEMA,
        "node": node_id,
        "contributor": identity.pseudonym,
        "licence": check_licence(fields.get("licence")),
        "date": clockmod.render(ctx.clock.now()),
        "model_and_tooling": declared(fields.get("model_and_tooling")),
    }
    written = text
    if "steps" in fields:
        check_steps(ctx, target_id, front, fields["steps"])
        written = text + "\n" + yaml.safe_dump(front["steps"], sort_keys=True, allow_unicode=True)
    else:
        validated(front, ANNEX_SCHEMA)
    content = annex_file(front, text)
    digest = schemas.content_hash(content.encode())
    path = node_dir(target_id, node_id) + f"annex/{digest}.md"
    body = append_pr(
        ctx,
        identity,
        path=path,
        content=content,
        subject=f"annex: {node_id}",
        what="annex",
        kind="annex",
        written=written,
        target_id=target_id,
        node_id=node_id,
    )
    body["hash"] = digest  # what a skeleton cites (D-31)
    return JSONResponse(body, status_code=201)


def declared(raw: Any, field: str = "model_and_tooling", *, cap: int | None = None) -> str | None:
    """A declared model and tooling (D-23): ``None`` for null or empty, else the string; one that
    is not a string, or is longer than ``cap`` characters, is ``tooling-invalid`` naming
    ``field``. An annex's cap is its schema's, checked with every capped field (``check_caps``);
    a gloss's ``drafted_with`` sits under a ``oneOf`` that check cannot read, so it passes its cap
    here (F21-R6)."""
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise ApiError(400, "tooling-invalid", f"{field} must be a string")
    if cap is not None and len(raw) > cap:
        raise ApiError(
            400,
            "tooling-invalid",
            f"{field} is {len(raw)} characters; the cap is {cap}",
            details={"field": field, "length": len(raw), "cap": cap},
        )
    return raw


# --- POST /approach-records (D-14) ----------------------------------------------------------------


def known_target(ctx: Context, target_id: Any) -> str:
    if not isinstance(target_id, str) or not target_id:
        raise ApiError(400, "target-id-missing", "target_id is required")
    index = json.loads(frontier.committed(ctx, "targets/index.json"))
    if not any(t.get("target_id") == target_id for t in index.get("targets", [])):
        raise ApiError(404, "target-unknown", f"{target_id} is not a target of this graph")
    return target_id


#: F05-T8: the fields ``POST /approach-records`` reads; any other top-level key is refused.
APPROACH_FIELDS: tuple[str, ...] = ("target_id", "record")


async def post_approach_records(ctx: Context, request: Request) -> Response:
    """R11: a strategy-level verdict for a route that never reached a statement (D-14)."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, APPROACH_FIELDS)
    target_id = known_target(ctx, fields.get("target_id"))
    doc = as_mapping(fields.get("record"), "record")
    written = written_record(doc)
    doc["schema"] = APPROACH_SCHEMA
    doc["target"] = target_id
    doc["contributor"] = identity.pseudonym
    doc.setdefault("date", clockmod.render(ctx.clock.now()))
    doc.setdefault("pinned_mathlib_sha", None)
    doc.setdefault("model_and_tooling", None)
    validated(doc, APPROACH_SCHEMA)
    path = f"targets/{target_id}/approaches/{record_name(ctx, identity)}.yaml"
    return JSONResponse(
        append_pr(
            ctx,
            identity,
            path=path,
            content=yaml.safe_dump(doc, sort_keys=True, allow_unicode=True),
            subject=f"approach record: {target_id}",
            what="approach record",
            kind="approach-record",
            target_id=target_id,
            node_id=None,
            written=written,
        ),
        status_code=201,
    )
