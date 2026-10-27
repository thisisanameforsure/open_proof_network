"""A contributor's settlement of an open pair direction, submitted directly (F26-T19, R8; D-9, D-28,
D-35 v3.39).

``POST /submissions`` with ``artifact_type: pair-proof`` (and so the MCP ``submit_proof``) takes a
``pair`` — ``target``, ``a``, ``b``, ``direction``, ``kind`` and, for a refutation, ``n`` — the
filled ``lean`` and the route's own disclosure, ``automation`` (D-23 v3.37; the record keeps its
``models``). A pair proof is not a node artifact: no ``node_id``, no ``bundle``, no ``tooling``
and no precheck, each refused by field if sent. Before anything opens, in this order, each refusal
by name (F13-T21's rule):

1. the arguments, then the target, then the review (``review-unknown``);
2. both candidates on the record at main's sha (``candidate-unknown``) and surviving as the gate
   derives it (``pair-candidate-not-surviving``);
3. the pair record in force for the two (``pair-unknown``; ``reviews.in_force``, a later record
   superseding), the direction open on it, and no merged pair-proof record for it the job has not
   yet answered (``pair-direction-settled``); no pull request of the service's for the same
   direction that may still merge (``pair-proof-pending``);
4. the gate's template for the direction, rebuilt from the two candidates as the job prepares them
   (``pair-proof-no-template`` for a kind the direction cannot take), then
   ``pair_proofs.split`` and ``pair_proofs.problems`` (their own codes);
5. the rate limit (``PER_DAY`` per pseudonym and target);
6. the hosted pre-flight (``preflight``): the file elaborates (``pair-proof-fails``), depends on
   nothing but the standard three axioms (``pair-proof-sorry``, ``pair-proof-axiom``), and for a
   proof the guarded copy does *not* elaborate (``pair-proof-degenerate``). A checker that cannot
   answer is an advisory word and the record still opens: the gate's sandbox is the authority
   (``checks.preflight_exhibit``'s precedent, C9, D-4 v3.14).

Then one ``pair-proof/v1`` record — author from the token, never the request; ``date`` now, to
the second; ``statement_hashes`` from the candidate records — at ``review/pair-proofs/`` under
the gate's own record name, in one pull request on an ``append/`` branch.

The checker's check mode answers no axiom list (measured on the live service, 2026-10-27), so the
text it is sent carries a short program after the proof that prints the theorem's axioms on one
info line tagged with a fresh nonce, the way witness mode reads a witness's (F13-T23). Only the
line with this call's nonce is read: a contributor's own ``logInfo`` of the tag cannot vouch.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from starlette.responses import JSONResponse, Response

from opn_api import appends, checks, duplicates, ratelimit, reviews, stewards, submissions
from opn_api.app import ApiError
from opn_api.axle import AxleError
from opn_gate import layout, pair_proofs, review_lean
from opn_gate import paths as gatepaths
from opn_gate import review as reviewmod
from opn_gate.diagnostic import Diagnostic

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

KIND = "pair-proof"
SCHEMA = "pair-proof/v1"
#: The fields a pair object carries; ``n`` only for a refutation.
PAIR_FIELDS: tuple[str, ...] = ("target", "a", "b", "direction", "kind", "n")
#: What a node artifact takes and a pair proof does not.
NODE_FIELDS: tuple[str, ...] = ("node_id", "bundle", "precheck_job_id", "tooling")
#: Settlements per pseudonym per target per day. Higher than a candidate's three (F26 §6): a
#: candidate is a new reading every later pair must compare, a settlement closes work; but every
#: one costs up to two hosted checks, and iterating belongs on POST /check, not here.
PER_DAY = 10
#: The axioms a settlement may rest on (the brief; ``palomar.permitted_axioms``' set).
STANDARD_AXIOMS: frozenset[str] = frozenset({"propext", "Classical.choice", "Quot.sound"})
TAG = "OPN-PAIR-PROOF"
#: The pre-flight's words: both checks answered as the gate would want; a check answered without a
#: verdict, or without the axiom line; the checker could not be asked; the file imports a module
#: only the gate's staging supplies.
PREFLIGHT_PASSED = "passed"
PREFLIGHT_INCONCLUSIVE = checks.PREFLIGHT_INCONCLUSIVE
PREFLIGHT_UNAVAILABLE = checks.PREFLIGHT_UNAVAILABLE
PREFLIGHT_SKIPPED = checks.PREFLIGHT_SKIPPED
DECLARATION = {"proof": "opnDirection", "refutation": "opnInstance"}


def bad(message: str, field: str) -> ApiError:
    return ApiError(400, "arguments-invalid", message, details={"field": field})


@dataclass(frozen=True)
class Pair:
    target: str
    a: str
    b: str
    direction: pair_proofs.Direction
    kind: pair_proofs.Kind
    n: int | None


def checked_pair(raw: Any) -> Pair:
    if not isinstance(raw, dict):
        raise bad("pair is an object of target, a, b, direction, kind and (a refutation) n", "pair")
    extra = sorted(set(raw) - set(PAIR_FIELDS))
    if extra:
        raise bad(f"pair takes {', '.join(PAIR_FIELDS)}; not {', '.join(extra)}", "pair")
    target = raw.get("target")
    if not isinstance(target, str) or not target:
        raise bad("pair.target is the target's id", "pair.target")
    a = reviews.checked_id(raw.get("a"), "pair.a")
    b = reviews.checked_id(raw.get("b"), "pair.b")
    if not a < b:
        raise bad(
            "pair.a is the pair's lexically smaller candidate id, as pair/v1 names it", "pair.a"
        )
    direction = raw.get("direction")
    if direction not in pair_proofs.DIRECTIONS:
        raise bad(
            "pair.direction is forward (a implies b) or backward (b implies a)", "pair.direction"
        )
    kind = raw.get("kind")
    if kind not in pair_proofs.KINDS:
        raise bad("pair.kind is proof or refutation", "pair.kind")
    n = raw.get("n")
    if kind == "proof" and n is not None:
        raise bad("a proof takes no n; n is a refutation's instance", "pair.n")
    if kind == "refutation" and (isinstance(n, bool) or not isinstance(n, int) or n < 0):
        raise bad("a refutation names its instance n, a natural number", "pair.n")
    return Pair(target, a, b, direction, kind, n)


# --- the record at main --------------------------------------------------------------------------


@dataclass(frozen=True)
class Reading:
    """What the record at main says of the pair: each candidate's record and Lean, and the
    review's concepts."""

    records: dict[str, dict[str, Any]]
    sources: dict[str, str]
    concepts: list[str]


def read_pair(ctx: Context, req: Pair, head: dict[str, Any]) -> Reading:
    """Steps 2 and 3, over the review directory as the gate's own derivation reads it."""
    with tempfile.TemporaryDirectory(prefix="opn-pair-proof-") as tmp:
        target_dir = reviews.materialise(ctx, Path(tmp), req.target)
        base = target_dir / gatepaths.REVIEW_DIR
        status = {
            str(c["id"]): str(c["status"]) for c in reviewmod.derive(target_dir)["candidates"]
        }
        records = {str(c.get("id")): c for c in reviews._docs(base / "candidates")}
        for c in (req.a, req.b):
            if c not in records:
                raise ApiError(
                    404,
                    "candidate-unknown",
                    f"{req.target}'s review has no candidate {c}",
                    details={"target_id": req.target, "candidate": c},
                )
            if status.get(c) != reviewmod.SURVIVING:
                raise ApiError(
                    409,
                    "pair-candidate-not-surviving",
                    f"candidate {c} is {status.get(c)}, not surviving: only a direction between "
                    "two surviving candidates is work (F26-R8)",
                    details={"target_id": req.target, "candidate": c, "status": status.get(c)},
                )
        held = next(
            (
                p
                for p in reviews.in_force(reviews._docs(base / "pairs"))
                if (str(p.get("a")), str(p.get("b"))) == (req.a, req.b)
            ),
            None,
        )
        if held is None:
            raise ApiError(
                404,
                "pair-unknown",
                f"the review job has not compared {req.a} and {req.b}: no pair record names them",
                details={"target_id": req.target, "a": req.a, "b": req.b},
            )
        state = (held.get(req.direction) or {}).get("state")
        if state != "open":
            raise settled(req, f"is {state} on the pair record in force", {"state": state})
        for name, doc in merged_settlements(base, req):
            if str(doc.get("date", ""))[:10] >= str(held.get("date", "")):
                raise settled(
                    req,
                    f"is settled by the merged record {name}, which the review job has not yet "
                    "answered",
                    {"record": f"{reviews.review_dir(req.target)}/{pair_proofs.DIR}/{name}"},
                )
        sources: dict[str, str] = {}
        for c in (req.a, req.b):
            lean = base / "candidates" / str(records[c].get("lean_file", ""))
            sources[c] = lean.read_text(encoding="utf-8") if lean.is_file() else ""
    concepts = [str(x) for x in head.get("concepts") or []]
    return Reading(records, sources, concepts)


def merged_settlements(base: Path, req: Pair) -> list[tuple[str, dict[str, Any]]]:
    folder = base / pair_proofs.DIR
    out: list[tuple[str, dict[str, Any]]] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.iterdir()):
        if path.suffix not in reviews.RECORD_SUFFIXES:
            continue
        doc = reviews._yaml(path.read_bytes())
        if doc is not None and (doc.get("a"), doc.get("b"), doc.get("direction")) == (
            req.a,
            req.b,
            req.direction,
        ):
            out.append((path.name, doc))
    return out


def settled(req: Pair, why: str, extra: dict[str, Any]) -> ApiError:
    return ApiError(
        409,
        "pair-direction-settled",
        f"the {req.direction} direction of {req.a} and {req.b} {why}; only an open direction "
        "takes a settlement (F26-R8)",
        details={"target_id": req.target, "a": req.a, "b": req.b, "direction": req.direction}
        | extra,
    )


def written(req: Pair) -> str:
    return f"pair-proof {req.target} {req.a} {req.b} {req.direction}"


def check_not_pending(ctx: Context, req: Pair) -> None:
    fp = duplicates.fingerprint(written(req))
    for found in ctx.store.list_open_submissions():
        if found.kind != KIND or found.target_id != req.target or fp not in found.fingerprints:
            continue
        if duplicates.blocks(ctx, found):
            raise ApiError(
                409,
                "pair-proof-pending",
                f"pull request #{found.pr_number} already settles the {req.direction} direction "
                f"of {req.a} and {req.b} and may still merge",
                details={
                    "target_id": req.target,
                    "pr_number": found.pr_number,
                    "pr_url": found.pr_url,
                    "submission_id": found.id,
                },
            )


# --- the template --------------------------------------------------------------------------------


def candidates_of(reading: Reading, req: Pair) -> tuple[review_lean.Cand, review_lean.Cand]:
    out: list[review_lean.Cand] = []
    for c in (req.a, req.b):
        got = review_lean.prepare(c, reading.sources[c], reading.concepts)
        if isinstance(got, str):
            raise no_template(req, f"candidate {c}: {got}")
        out.append(got)
    return out[0], out[1]


def no_template(req: Pair, why: str) -> ApiError:
    return ApiError(
        422,
        "pair-proof-no-template",
        f"the {req.direction} direction of {req.a} and {req.b} has no {req.kind} template: {why}",
        details={"target_id": req.target, "direction": req.direction, "kind": req.kind},
    )


def template_of(a: review_lean.Cand, b: review_lean.Cand, req: Pair) -> str:
    try:
        return pair_proofs.template(a, b, req.direction, req.kind, req.n)
    except ValueError as exc:
        raise no_template(req, str(exc)) from exc


def diagnostic_error(d: Diagnostic, **extra: Any) -> ApiError:
    return ApiError(422, d.code, d.message, details=dict(d.details) | extra)


def check_text(lean: str, tmpl: str) -> pair_proofs.Filled:
    filled = pair_proofs.split(lean, tmpl)
    if isinstance(filled, Diagnostic):
        raise diagnostic_error(filled)
    found = pair_proofs.problems(filled)
    if found:
        raise diagnostic_error(
            found[0], problems=[{"message": d.message, **d.details} for d in found]
        )
    return filled


# --- the hosted pre-flight -----------------------------------------------------------------------


def tag(nonce: str) -> str:
    return f"{TAG}-{nonce}"


def axiom_text(lean: str, declaration: str, nonce: str) -> str:
    """The filled file as the checker is sent it: ``import Lean`` after the header line when the
    file has no such import, the file, then the program printing ``declaration``'s axioms on one
    line tagged with this call's nonce."""
    head, _, rest = lean.partition("\n")
    needs = "Lean" not in layout.imports_of(lean)
    body = head + "\n" + ("import Lean\n" if needs else "") + rest
    if not body.endswith("\n"):
        body += "\n"
    return (
        body
        + "\n-- the network's axiom probe (F26-T19): not part of the record\n"
        + "open Lean in\n"
        + "run_meta do\n"
        + f"  let ax ← collectAxioms `{declaration}\n"
        + f'  logInfo m!"{tag(nonce)} {{Json.compress (toJson (ax.map toString))}}"\n'
    )


def axioms_read(body: dict[str, Any], nonce: str) -> list[str] | None:
    """The axiom list on the line carrying this call's nonce, or ``None`` when there is none."""
    messages = body.get("lean_messages")
    infos = messages.get("infos") if isinstance(messages, dict) else None
    for info in infos if isinstance(infos, list) else ():
        _, found, rest = str(info).partition(tag(nonce) + " ")
        if not found:
            continue
        try:
            doc = json.loads(rest.strip())
        except ValueError:
            continue
        return checks.axiom_names(doc)
    return None


async def ask(  # noqa: PLR0913 — the call, and what the log names
    ctx: Context,
    *,
    identity_id: str,
    target_id: str,
    text: str,
    environment: str,
    reservation: ratelimit.Reservation,
) -> tuple[dict[str, Any], str | None] | None:
    """One check, charged and logged; ``None`` when the checker could not answer."""
    reservation.take()
    req = checks.CheckRequest(target_id, None, text, "check")
    caller = checks.Caller("identity", identity_id)
    started = time.monotonic()
    try:
        budget = min(checks.PREFLIGHT_TIMEOUT_S, ctx.settings.check_timeout_s)
        answer = await asyncio.to_thread(
            checks.call_checker, ctx, req, text, environment, None, timeout_s=budget
        )
        if answer.body.get("error_type") == checks.LEAN_TIMEOUT:
            raise checks.timed_out(ctx, answer.request_id)
    except (ApiError, AxleError) as exc:
        code = exc.code if isinstance(exc, ApiError) else "upstream-unavailable"
        status = exc.status if isinstance(exc, AxleError) else None
        checks.write_log(
            ctx,
            req,
            caller,
            outcome=code,
            started=started,
            environment=environment,
            upstream_status=status,
        )
        return None
    log_id = checks.write_log(
        ctx,
        req,
        caller,
        outcome=checks.ANSWERED,
        started=started,
        environment=environment,
        answer=answer,
    )
    return answer.body, log_id


def hosted(environment: str) -> str:
    return (
        f"Checked on the hosted fast checker ({environment}); not authoritative, but the gate "
        "elaborates the same text in its sandbox"
    )


def judge_file(body: dict[str, Any], nonce: str, environment: str, log_id: str | None) -> str:
    """The first check's word, or its refusal: errors, ``sorryAx``, an axiom beyond the three."""
    okay = checks.verdict(body)
    if okay is False:
        errors = checks.lean_errors(body)
        if not errors:
            return PREFLIGHT_INCONCLUSIVE
        raise ApiError(
            422,
            "pair-proof-fails",
            "the pair proof does not elaborate: the checker reported Lean errors in it, so "
            f"nothing was opened. {hosted(environment)}",
            details={"errors": errors, "log_id": log_id},
        )
    if okay is None:
        return PREFLIGHT_INCONCLUSIVE
    axioms = axioms_read(body, nonce)
    if axioms is None:
        if checks.sorry_reported(body) is not None:
            axioms = [checks.SORRY_AXIOM]
        else:
            return PREFLIGHT_INCONCLUSIVE
    if checks.SORRY_AXIOM in axioms:
        raise ApiError(
            422,
            "pair-proof-sorry",
            "the pair proof depends on sorryAx, so the gate would refuse it and nothing was "
            f"opened. {hosted(environment)}",
            details={"axioms": axioms, "log_id": log_id},
        )
    outside = [a for a in axioms if a not in STANDARD_AXIOMS]
    if outside:
        raise ApiError(
            422,
            "pair-proof-axiom",
            f"the pair proof depends on axioms beyond propext, Classical.choice and Quot.sound: "
            f"{', '.join(outside)}, so the gate would refuse it and nothing was opened. "
            f"{hosted(environment)}",
            details={"axioms": outside, "allowed": sorted(STANDARD_AXIOMS), "log_id": log_id},
        )
    return PREFLIGHT_PASSED


async def preflight(  # noqa: PLR0911 — one return per outcome word
    ctx: Context,
    identity_id: str,
    req: Pair,
    lean: str,
    first: review_lean.Cand,
) -> str:
    """Step 6. Two checks for a proof (the file with the axiom probe, then the guarded copy),
    one for a refutation, reserved together from the identity's check budget (F13-T28)."""
    if any(layout.module_origin(m)[0] != "library" for m in layout.imports_of(lean)):
        return PREFLIGHT_SKIPPED
    try:
        _, entry = checks.hosted_for(ctx, req.target)
    except ApiError:
        return PREFLIGHT_UNAVAILABLE
    if entry is None or entry.environment is None:
        return PREFLIGHT_UNAVAILABLE
    environment = entry.environment
    nonce = secrets.token_hex(16)
    reservation = ratelimit.reserve_checks(ctx, identity_id, 2 if req.kind == "proof" else 1)
    try:
        got = await ask(
            ctx,
            identity_id=identity_id,
            target_id=req.target,
            text=axiom_text(lean, DECLARATION[req.kind], nonce),
            environment=environment,
            reservation=reservation,
        )
        if got is None:
            return PREFLIGHT_UNAVAILABLE
        word = judge_file(got[0], nonce, environment, got[1])
        if req.kind != "proof":
            return word
        guard = await ask(
            ctx,
            identity_id=identity_id,
            target_id=req.target,
            text=pair_proofs.guarded(lean, first),
            environment=environment,
            reservation=reservation,
        )
        if guard is None:
            return PREFLIGHT_UNAVAILABLE
        okay = checks.verdict(guard[0])
        if okay is True:
            raise ApiError(
                422,
                "pair-proof-degenerate",
                "the proof still elaborates with its hypothesis cleared right after the "
                "template's intro (the degenerate guard), so it never used the hypothesis and is "
                f"not a proof of the direction; nothing was opened. {hosted(environment)}",
                details={"log_id": guard[1]},
            )
        return PREFLIGHT_INCONCLUSIVE if okay is None else word
    finally:
        reservation.release()


# --- the route -----------------------------------------------------------------------------------


def stamp(date: str) -> str:
    return date.replace("-", "").replace(":", "")


async def submit(ctx: Context, identity: Identity, fields: dict[str, Any]) -> Response:
    """``POST /submissions`` for ``artifact_type: pair-proof`` (the module's steps, in order)."""
    for name in NODE_FIELDS:
        if name in fields:
            raise bad(
                f"a pair proof takes no {name}: it is not a node artifact and has no precheck; "
                "send pair, lean and automation",
                name,
            )
    automation = submissions.check_automation(fields.get("automation"))
    req = checked_pair(fields.get("pair"))
    lean = reviews.checked_lean(fields.get("lean"))
    appends.known_target(ctx, req.target)
    head = reviews.required_opening(ctx, req.target)
    reading = read_pair(ctx, req, head)
    check_not_pending(ctx, req)
    a, b = candidates_of(reading, req)
    tmpl = template_of(a, b, req)
    check_text(lean, tmpl)
    ratelimit.enforce(
        ctx,
        KIND,
        f"{identity.pseudonym.casefold()}#{req.target}",
        limit=PER_DAY,
        seconds=ratelimit.DAY_S,
    )
    first, _ = pair_proofs.ordered(a, b, req.direction)
    word = await preflight(ctx, identity.id, req, lean, first)
    date = ctx.clock.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    case = None if req.n is None else review_lean.Case("holds", req.n).key()
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "target": req.target,
        "a": req.a,
        "b": req.b,
        "direction": req.direction,
        "kind": req.kind,
        "case": case,
        "statement_hashes": {
            "a": str(reading.records[req.a].get("statement_hash")),
            "b": str(reading.records[req.b].get("statement_hash")),
        },
        "lean": lean,
        "author": identity.pseudonym,
        "models": list(automation["models"]) if automation else [],
        "date": date,
    }
    appends.validated(doc, SCHEMA)
    name = pair_proofs.record_name(req.a, req.b, req.direction, stamp(date), identity.pseudonym)
    path = f"{reviews.review_dir(req.target)}/{pair_proofs.DIR}/{name}"
    subject = f"pair-proof: {req.target} {req.a}--{req.b} {req.direction} by {identity.pseudonym}"
    body = reviews.open_record_pr(
        ctx,
        identity,
        files={path: reviews.render(doc)},
        subject=subject,
        kind=KIND,
        target_id=req.target,
        written=written(req),
        branch_prefix=submissions.APPEND_BRANCH_PREFIX,
        body=reviews.pr_body(
            f"pair {req.kind}",
            identity.pseudonym,
            path,
            "its path, its schema, that its Lean is the direction's template with only the two "
            "regions filled, that it elaborates with no sorry and only the standard axioms, and "
            "for a proof that the degenerate guard fails; the review job re-checks it and writes "
            "the pair record (F26-R8)",
        ),
        automation=automation,
    )
    digest = hashlib.sha256(lean.encode("utf-8")).hexdigest()
    return JSONResponse(
        {
            **stewards.receipt(body, submissions.APPEND_BRANCH_PREFIX),
            "submission_id": body["id"],
            "artifact_type": KIND,
            "target_id": req.target,
            "pair": {"a": req.a, "b": req.b, "direction": req.direction, "kind": req.kind},
            "lean_sha256": digest,
            "pair_proof_preflight": word,
        },
        status_code=201,
    )
