"""``POST /submissions`` (F07-R1, R2, R14; D-12, D-23, D-25, D-28, D-35).

The plain path to the graph is a pull request, and the service's job is to open one that is
indistinguishable from a hand-opened one: the contributor's ledger identity as author and
sign-off, the GitHub App as committer, the bundle as the diff, and the two blocks in the body
that let the gate bounce a submission before it spends a runner.

Nothing here decides anything mathematical. The precheck attestation the submission is bound to
was signed by the precheck key (F06), the gate re-derives every verdict on the merge commit
(D-4), and this module never merges: the App may open a pull request and may not approve or
merge one (C8).

``open_pr`` is the shared act — branch, authored commit, pull request — that the append routes
(``opn_api.appends``) use too, because D-13, D-14 and D-31 records reach the graph the same way.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import bundles, duplicates, pending, precheck
from opn_api import clock as clockmod
from opn_api import identity as identitymod
from opn_api import uses as usesmod
from opn_api.app import ApiError, host_budget_refusal
from opn_api.githost import Author, GitHostError, PullRequest, RateLimitError
from opn_api.store import KEY_PRECHECK_USED
from opn_gate import annex as annexmod
from opn_gate import bounce, carried, postmerge, submission
from opn_gate import paths as gate_paths
from opn_gate.paths import ALTERNATE_SUFFIX, Claim
from opn_gate.postmerge import PARTIAL_SUFFIX

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

log = logging.getLogger(__name__)

ARTIFACT_TYPES: tuple[str, ...] = ("proof", "counterexample", "vacuity", "reduction", "partial")
#: Q6, R2: a reserved TLD, so no deliverable address is ever fabricated, and the pseudonym is
#: the only name the record carries (D-19).
AUTHOR_DOMAIN = "anon.opn.invalid"
SUBMIT_BRANCH_PREFIX = "submit/"
APPEND_BRANCH_PREFIX = "append/"
TOOLING_FIELDS: tuple[str, ...] = ("model", "version", "harness")
MAX_TOOLING_CHARS = 200  # matches submission-meta/v1


@dataclass(frozen=True)
class Opened:
    """What a caller gets back: the id the service gave this act, and where the PR is."""

    id: str
    branch: str
    pull_request: PullRequest


def author_for(identity: Identity, now: str) -> Author:
    return Author(identity.pseudonym, f"{identity.pseudonym}@{AUTHOR_DOMAIN}", now)


def committer_for(ctx: Context, now: str) -> Author:
    """R2, D-23: the App carried the commit; the identity wrote it. Named rather than omitted,
    because GitHub fills an absent committer with the author (found on the live host, F07-T6)."""
    return Author(ctx.settings.committer_name, ctx.settings.committer_email, now)


def sign_off(identity: Identity) -> str:
    """D-23's Developer Certificate of Origin line, in git's own shape."""
    return f"Signed-off-by: {identity.pseudonym} <{identity.pseudonym}@{AUTHOR_DOMAIN}>"


def open_pr(  # noqa: PLR0913 — every argument is part of the pull request being opened
    ctx: Context,
    identity: Identity,
    *,
    branch: str,
    files: dict[str, str],
    subject: str,
    title: str,
    body: str,
) -> PullRequest:
    """R2: one authored commit on a fresh branch of the graph, then the pull request.

    A host failure is never silent and never half-done from the caller's point of view: the
    branch may survive a failed pull-request call, but the caller is told the submission did not
    open, so nothing is recorded as submitted that is not (C7).
    """
    settings = ctx.settings
    now = clockmod.render(ctx.clock.now())
    message = f"{subject}\n\n{sign_off(identity)}\n"
    try:
        ctx.githost.push_branch(
            settings.graph_repo,
            branch,
            files,
            base=settings.graph_branch,
            message=message,
            author=author_for(identity, now),
            committer=committer_for(ctx, now),
        )
        return ctx.githost.open_pull_request(
            settings.graph_repo,
            head=branch,
            base=settings.graph_branch,
            title=title,
            body=body,
        )
    except GitHostError as exc:
        log.warning("%s could not be opened on %s: %s", branch, settings.graph_repo, exc)
        if isinstance(exc, RateLimitError):  # F07-T47: come back at the reset, not a bare 502
            raise host_budget_refusal(ctx, exc) from exc
        raise ApiError(
            502, "pull-request-failed", f"the pull request could not be opened: {exc}"
        ) from exc


# --- POST /submissions ---------------------------------------------------------------------------


def check_artifact_type(raw: Any) -> str:
    if raw not in ARTIFACT_TYPES:
        raise ApiError(
            400,
            "artifact-type-invalid",
            f"artifact_type must be one of {', '.join(ARTIFACT_TYPES)}",
        )
    return str(raw)


def check_tooling(raw: Any) -> dict[str, str | None]:
    """R14, D-23: three declared strings, capped and stored verbatim. Undeclared is allowed —
    the gate is blind to tooling (D-1) and a lie here costs the network nothing."""
    if raw is None:
        return dict.fromkeys(TOOLING_FIELDS)
    if not isinstance(raw, dict):
        raise ApiError(
            400, "tooling-invalid", "tooling must be an object of model, version, harness"
        )
    out: dict[str, str | None] = {}
    for field in TOOLING_FIELDS:
        value = raw.get(field)
        if value is None or value == "":
            out[field] = None
            continue
        if not isinstance(value, str) or len(value) > MAX_TOOLING_CHARS:
            raise ApiError(
                400,
                "tooling-invalid",
                f"tooling.{field} must be a string of at most {MAX_TOOLING_CHARS} characters",
            )
        out[field] = value
    return out


def bound_job(
    ctx: Context, identity: Identity, fields: dict[str, Any], digest: str
) -> precheck.Job:
    """R1: the precheck this submission stands on — done, passing, this identity's, this bundle.

    Every mismatch is named, because each one is something the submitter can fix, and none of
    them tells an attacker anything they did not already have to know to get here.
    """
    job_id = fields.get("precheck_job_id")
    if not isinstance(job_id, str) or not job_id:
        raise ApiError(
            400, "precheck-required", "precheck_job_id is required (D-4: no attestation, no CI)"
        )
    job = precheck.load(ctx, job_id)
    if job is None:
        raise ApiError(400, "precheck-unknown", f"no precheck job {job_id}")
    job = precheck.advance(ctx, job)
    if job.expired_at(ctx.clock.now()):
        raise ApiError(
            400, "precheck-expired", "that precheck's result is past its retention window"
        )
    if job.state != "done":
        raise ApiError(400, "precheck-not-done", f"precheck {job_id} is {job.state}, not done")
    verdict = (job.result or {}).get("verdict")
    if verdict != "pass":
        raise ApiError(
            400, "precheck-not-passing", f"precheck {job_id} reports verdict {verdict!r}"
        )
    if job.identity_id != identity.id:
        raise ApiError(400, "precheck-not-yours", f"precheck {job_id} was not run by this identity")
    if job.bundle_digest != digest:
        raise ApiError(
            400,
            "precheck-bundle-differs",
            "the bundle differs from the one that was prechecked; precheck this bundle first",
        )
    return job


@contextmanager
def using(ctx: Context, job: precheck.Job) -> Iterator[None]:
    """F06-T11 (audit 2026-10-04): a precheck job opens one pull request. Taken atomically around
    the opening, after every other check, so only an opened pull request spends it: the second
    taker is 409 ``precheck-used``, and a pull request that failed to open gives the job back so
    the same request can be sent again at once (C7). The marker lives as long as the job's
    result, after which ``bound_job`` refuses the job as expired anyway."""
    key = KEY_PRECHECK_USED + job.id
    expires = clockmod.parse(job.created) + timedelta(days=precheck.RESULT_RETENTION_DAYS)
    if ctx.store.bump_counter(key, expires) > 1:
        raise ApiError(
            409,
            "precheck-used",
            f"precheck {job.id} has already opened a pull request; a precheck job is used once. "
            "Read GET /submissions.json for it, or precheck again for a new submission",
            details={"precheck_job_id": job.id},
        )
    try:
        yield
    except BaseException:
        try:
            ctx.store.drop_counter(key)
        except Exception as exc:  # any store failure: the job stays used, which refuses, not opens
            log.warning("precheck %s not released: %s", job.id, type(exc).__name__)
        raise


def check_proposal_statement(job: precheck.Job, facts: dict[str, Any]) -> None:
    """F06-T10: a job run at a proposal's head binds only if the node merged with the statement
    the job checked. The gate's bounce rule compares the attestation's statement hash with the
    merged tree and ignores the commit it ran at, so a proposal branch that moved to another
    statement after the precheck would be refused by the gate; it is refused here first, before
    a pull request is opened. A job for a node on main was pinned to it, and passes."""
    if job.proposal and job.statement_hash != facts.get("statement_hash"):
        raise ApiError(
            400,
            "precheck-statement-differs",
            f"precheck {job.id} ran against pull request #{job.proposal.get('pr_number')} at "
            f"{str(job.proposal.get('head_sha'))[:12]}, and {job.node_id} merged with a "
            "different Statement.lean; precheck the proof again against the merged node",
            details={"prechecked": job.statement_hash, "merged": facts.get("statement_hash")},
        )


#: D-12: where each artifact type lands. A proof, counterexample or vacuity certificate is the
#: node's ``Proof.lean`` (D-3), or for a proof also an alternate of a proved node (D-25 v3.13);
#: a partial, and a reduction (a partial with one hole, the gate's ``Artifact.is_reduction``), is
#: an assembly under ``attempts/`` (F11-Q28) — the gate's path role ``partial``.
PROOF_TYPES: tuple[str, ...] = ("proof", "counterexample", "vacuity")
PARTIAL_TYPES: tuple[str, ...] = ("partial", "reduction")
PARTIAL_PATTERN = "attempts/<ts>-<pseudonym>" + PARTIAL_SUFFIX


def roles_of(files: Mapping[str, str]) -> dict[str, list[str]]:
    """The gate's role of every bundle path (``opn_gate.paths.locate``), paths sorted per role.
    ``bundles.validate`` has already refused a path with no role, so none is dropped here."""
    out: dict[str, list[str]] = {}
    for path in sorted(files):
        where = gate_paths.locate(path)
        if where is not None:
            out.setdefault(where.role, []).append(path)
    return out


def check_artifact_path(claim: Claim, files: Mapping[str, str], artifact_type: str) -> None:
    """F07-T7 (finding 4): the declared type and the path it lands at agree, by the gate's own
    roles. A partial or reduction carries an assembly and no ``Proof.lean`` (the gate's partial
    mode is the assembly plus appends, ``modes._mode_for``); the other three carry no assembly.
    A mismatch is a 400 naming the path the type belongs at."""
    roles = roles_of(files)
    proof = claim.node_prefix + bundles.PROOF_FILE
    partial = claim.node_prefix + PARTIAL_PATTERN
    if artifact_type in PARTIAL_TYPES:
        if "proof" in roles or "partial" not in roles:
            found = ", ".join(roles.get("proof") or sorted(files))
            raise ApiError(
                400,
                "artifact-path-mismatch",
                f"a {artifact_type} is an assembly at {partial} (D-12, F11-Q28), not {found}; "
                f"a proof of the node is {proof} with artifact_type proof",
            )
    elif "partial" in roles:
        raise ApiError(
            400,
            "artifact-path-mismatch",
            f"a {artifact_type} is the node's {proof} (D-3), not {roles['partial'][0]}; an "
            f"assembly under attempts/ is artifact_type partial, named {partial}",
        )


def check_placement(
    claim: Claim,
    files: Mapping[str, str],
    *,
    artifact_type: str,
    proved: bool,
    tutorial: bool,
) -> None:
    """R7, D-25 v3.13: where a proof lands depends on whether the node is proved, and the
    gate refuses the wrong place (``proof-replaces-merged``, ``alternate-unproved``). Refused
    here first, before a precheck is bound or anything pushed. The tutorial node's proof stays
    open to rehearsal (D-27). F07-T7: the type must match its path first."""
    check_artifact_path(claim, files, artifact_type)
    proof = claim.node_prefix + bundles.PROOF_FILE
    if proved and not tutorial and proof in files:
        raise ApiError(
            400,
            "proof-replaces-merged",
            f"{claim.node_id} already has a merged Proof.lean, which is never modified (D-3); "
            f"submit this proof as {claim.node_prefix}attempts/<ts>-<pseudonym>{ALTERNATE_SUFFIX} "
            "with artifact_type proof (D-25)",
        )
    attempts = claim.node_prefix + "attempts/"
    alternates = sorted(p for p in files if p.startswith(attempts) and p.endswith(ALTERNATE_SUFFIX))
    if alternates and not proved:
        raise ApiError(
            400,
            "alternate-unproved",
            f"{claim.node_id} has no merged Proof.lean, so {alternates[0]} has nothing to be an "
            f"alternate to: submit it as {proof} (D-25)",
        )


def check_carried(claim: Claim, files: Mapping[str, str]) -> list[carried.Carried]:
    """F07-R23 (D-29 v3.24): the witnesses a partial's bundle carries for its holes, as the
    gate's own grammar reads them (``opn_gate.carried``, which step 2 applies): refused here
    with the gate's code — a file that names no hole, a hole named twice, a ``sorry``, a name
    not attached to the assembly, a witness with no partial beside it — before a precheck job
    is spent or anything is pushed. A bundle with several assemblies is left to the gate, which
    refuses it by its own name (``partial-multiple``)."""
    roles = roles_of(files)
    found = roles.get("hole-witness") or []
    if not found:
        return []
    assemblies = roles.get("partial") or []
    prefix = claim.node_prefix
    if not assemblies:
        problem = carried.without_partial([p[len(prefix) :] for p in found])
        raise ApiError(400, problem.code, problem.message, details=dict(problem.details))
    if len(assemblies) > 1:
        return []
    witnesses, refusal = carried.read(
        assemblies[0][len(prefix) :], {p[len(prefix) :]: files[p] for p in found}
    )
    if refusal is not None:
        raise ApiError(400, refusal.code, refusal.message, details=dict(refusal.details))
    return witnesses


def check_witnesses_checked(job: precheck.Job, witnesses: list[carried.Carried]) -> None:
    """F07-R23: a bundle that carries witnesses binds only to a precheck that checked them.

    The job ran the gate the target pins. One pinned before R23 ignores a ``.witness`` file at
    step 2, so its precheck passes without looking at it, and its classifier then refuses the
    pull request by path: the submission would open and go red. The result of a gate that does
    check them names each on its hole (``holes[].witness``, path and hash); anything else is
    refused here, by name, with the way that works on every pin."""
    if not witnesses:
        return
    unchecked = precheck.unchecked_witnesses(
        job.result, [{"path": w.path, "sha256": w.sha256} for w in witnesses]
    )
    if unchecked:
        raise ApiError(
            400,
            "hole-witness-unchecked",
            f"precheck {job.id} did not check the carried witness "
            + ", ".join(unchecked)
            + ": the gate this target pins does not read a partial's carried witnesses yet "
            "(F07-R23 reaches a target at its re-pin). Submit the partial without them and "
            "send each hole's witness through POST /proposals/witness once the hole exists",
            details={"unchecked": unchecked},
        )


def check_annex_steps(
    ctx: Context, claim: Claim, files: Mapping[str, str], job: precheck.Job
) -> None:
    """F18-R6 (D-31 v3.26): a partial citing a stepped annex names every hole after a step, by
    the gate's own check (``opn_gate.annex.check_steps``), before anything is pushed. The hole
    names are the extractor's, which only a run knows, so they are read from the precheck's
    result (``holes[].name``, F06-T9) and never guessed from the text: a result that names no
    holes refuses nothing here, and the gate decides. A job run on a gate that checks steps has
    already failed on such a bundle (``precheck-not-passing``); this is for a job run on a gate
    that does not, and gives the refusal its own name. The annex is read from the bundle or from
    ``main`` (its name is its hash, so any commit holding it holds the same text); an unreadable
    host refuses nothing (C7)."""
    holes = (job.result or {}).get("holes")
    if not isinstance(holes, list):
        return
    names = [
        str(h["name"]) for h in holes if isinstance(h, dict) and isinstance(h.get("name"), str)
    ]
    assemblies = roles_of(files).get("partial") or []
    if len(assemblies) != 1:
        return
    try:
        digest = postmerge.annex_citation(files[assemblies[0]])
    except postmerge.MalformedCitationError:
        return
    if digest is None:
        return
    path = f"{claim.node_prefix}{annexmod.ANNEX_DIR}/{digest}.md"
    text = files.get(path)
    if text is None:
        try:
            raw = pending.optional_committed(ctx, path)
        except (GitHostError, ApiError):
            return
        if raw is None:
            return
        text = raw.decode("utf-8", "replace")
    problem = annexmod.check_steps(annexmod.steps_of(text), names, annex=digest)
    if problem is not None:
        raise ApiError(400, problem.code, problem.message, details=dict(problem.details))


#: F05-T8: the fields ``POST /submissions`` reads; any other top-level key is refused.
SUBMISSION_FIELDS: tuple[str, ...] = (
    "node_id",
    "artifact_type",
    "bundle",
    "tooling",
    "precheck_job_id",
)


async def post_submissions(ctx: Context, request: Request) -> Response:
    """R1, R2: bind to a passing precheck, then open the pull request on the graph."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, SUBMISSION_FIELDS)
    artifact_type = check_artifact_type(fields.get("artifact_type"))
    tooling = check_tooling(fields.get("tooling"))

    node_id = fields.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        raise ApiError(400, "node-id-missing", "node_id is required")
    facts = precheck.node_facts(ctx, node_id)
    # F06-T6: a job outlives the state it was minted in, so a node that turned blocked since its
    # precheck passed is refused here too — the shared 409 node-blocked, before the bundle is
    # placed or any job is bound, and nothing pushed or recorded.
    precheck.check_open(ctx, node_id, facts)
    claim = Claim(facts["target_id"], node_id)
    existing = precheck.existing_paths(ctx, node_id, claim.target_id)
    bundle, rejection = bundles.validate(fields.get("bundle"), claim, existing=existing)
    if rejection is not None or bundle is None:
        assert rejection is not None
        raise ApiError(400, rejection.code, rejection.message)
    proved = claim.node_prefix + bundles.PROOF_FILE in existing
    check_placement(
        claim,
        bundle.files,
        artifact_type=artifact_type,
        proved=proved,
        tutorial=bool(facts["tutorial"]),
    )
    witnesses = check_carried(claim, bundle.files)  # F07-R23: step 2's refusals, first
    # F08-R21 (T26): a use line step 2 would refuse, by the gate's code, before anything opens.
    # Asked again here: a job prechecked before the target's re-pin ran no such pre-flight.
    usesmod.check_bundle(ctx, claim, bundle.files)

    # F07-T35 (D-25 v3.21): a copy of a proof merged on the node or open for it is refused
    # before the precheck job is spent on it; a different proof races as before.
    prints = duplicates.check_proof(
        ctx, claim.target_id, node_id, dict(bundle.files), tutorial=bool(facts["tutorial"])
    )

    # A job for another node cannot reach here: the bundle was just path-checked against this
    # node, and a job's digest is over its bundle's paths, so a foreign job's bundle fails
    # `path-forbidden` above before its digest could match (F05-Q7).
    job = bound_job(ctx, identity, fields, bundle.digest)
    check_proposal_statement(job, facts)
    check_witnesses_checked(job, witnesses)  # F07-R23: nothing opens the pinned gate did not check
    check_annex_steps(ctx, claim, bundle.files, job)  # F18-R6: the holes the run named
    neighbours = on_the_node(
        ctx, node_id, artifact_type, proved=proved, tutorial=bool(facts["tutorial"])
    )

    now = ctx.clock.now()
    submission_id = identitymod.new_ulid(now)
    meta = {
        "schema": submission.SCHEMA,
        "submission_id": submission_id,
        "identity": {"pseudonym": identity.pseudonym, "proof_kind": identity.proof_kind},
        "artifact_type": artifact_type,
        "tooling": tooling,
        "precheck_job_id": job.id,
    }
    subject = f"{artifact_type}: {node_id}"
    slots = [duplicates.slot("proof", node_id, fp) for fp in prints]
    with duplicates.holding(ctx, slots, "proof"), using(ctx, job):
        pr = open_pr(
            ctx,
            identity,
            branch=SUBMIT_BRANCH_PREFIX + submission_id,
            files=dict(bundle.files),
            subject=subject,
            title=subject,
            body=submission_body(job, meta),
        )
    log.info("submission %s opened %s for %s", submission_id, pr.url, identity.id)
    # F07-T16: remembered so GET /submissions/{id} can answer its live state; advisory — a store
    # failure is logged inside and the pull request is still answered (C7, C9).
    pending.record(
        ctx,
        identity,
        submission_id=submission_id,
        kind=artifact_type,
        target_id=claim.target_id,
        node_id=node_id,
        pr=pr,
        precheck_job_id=job.id,
        fingerprints=prints,
    )
    return JSONResponse(
        {
            "submission_id": submission_id,
            "pr_url": pr.url,
            "pr_number": pr.number,
            "node_id": node_id,
            "target_id": claim.target_id,
            "artifact_type": artifact_type,
            **neighbours,
        },
        status_code=201,
    )


def on_the_node(
    ctx: Context, node_id: str, artifact_type: str, *, proved: bool, tutorial: bool
) -> dict[str, Any]:
    """F07-T40: what else is on the node, for the receipt; it refuses nothing (D-25 lets proofs
    race). ``rivals`` are the submissions open on the node that can still merge, read before
    this one opens, so it is not among them; on a node whose proof has merged, ``node_proved``,
    and for a proof, which there lands as an alternate (F07-T12), ``becomes``. A key is absent
    when nothing applies. The tutorial node is rehearsed, never raced (D-27): nothing to say."""
    if tutorial:
        return {}
    out: dict[str, Any] = {}
    try:
        rivals = [
            {"pr_number": found.pr_number, "pseudonym": found.pseudonym}
            for found in duplicates.open_rivals(ctx, node_id, duplicates.PROOF_KINDS)
        ]
    except Exception as exc:  # any store or host failure: the receipt is advisory (C7)
        log.warning("%s: rivals not listed: %s", node_id, type(exc).__name__)
        rivals = []
    if rivals:
        out["rivals"] = rivals
    if proved:
        out["node_proved"] = True
        if artifact_type == "proof":
            out["becomes"] = "alternate"
    return out


def submission_body(job: precheck.Job, meta: dict[str, Any]) -> str:
    """The pull-request body: prose for a person, then the two blocks the gate reads (R2)."""
    attestation = (job.result or {}).get("attestation") or {}
    lines = [
        f"Submitted through the Open Proof Network service by "
        f"`{meta['identity']['pseudonym']}` as a {meta['artifact_type']}.",
        "",
        f"Precheck job `{job.id}` passed against graph commit `{job.graph_commit}`.",
        "",
        bounce.render_block(attestation),
        "",
        submission.render_block(meta),
    ]
    return "\n".join(lines)
