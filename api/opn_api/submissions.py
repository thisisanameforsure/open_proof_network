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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import bundles, precheck
from opn_api import clock as clockmod
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_api.githost import Author, GitHostError, PullRequest
from opn_gate import bounce, submission
from opn_gate.paths import Claim

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


async def post_submissions(ctx: Context, request: Request) -> Response:
    """R1, R2: bind to a passing precheck, then open the pull request on the graph."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request)
    artifact_type = check_artifact_type(fields.get("artifact_type"))
    tooling = check_tooling(fields.get("tooling"))

    node_id = fields.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        raise ApiError(400, "node-id-missing", "node_id is required")
    facts = precheck.node_facts(ctx, node_id)
    claim = Claim(facts["target_id"], node_id)
    bundle, rejection = bundles.validate(
        fields.get("bundle"),
        claim,
        existing=precheck.existing_paths(ctx, node_id, claim.target_id),
    )
    if rejection is not None or bundle is None:
        assert rejection is not None
        raise ApiError(400, rejection.code, rejection.message)

    # A job for another node cannot reach here: the bundle was just path-checked against this
    # node, and a job's digest is over its bundle's paths, so a foreign job's bundle fails
    # `path-forbidden` above before its digest could match (F05-Q7).
    job = bound_job(ctx, identity, fields, bundle.digest)

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
    return JSONResponse(
        {
            "submission_id": submission_id,
            "pr_url": pr.url,
            "pr_number": pr.number,
            "node_id": node_id,
            "target_id": claim.target_id,
            "artifact_type": artifact_type,
        },
        status_code=201,
    )


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
