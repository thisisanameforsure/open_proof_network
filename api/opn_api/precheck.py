"""Precheck jobs (F06-R1, R2, R3, R5, R8, R9, R10; D-19, D-28, D-35).

``POST /precheck`` validates a bundle against the node at the graph's ``main``, records a job,
and hands it to the scratch repo through the ``GitHost`` seam. ``GET /precheck/<id>`` reports
the job, advancing its state by looking at the run when it is not yet terminal (Q3: polling on
read, so the service stays stateless and holds no inbound webhook secret).

The tutorial node is the one route a caller may use without a token, because proving it is the
account-free identity proof of D-19 and requiring a token first would be circular (Q2). Such a
job carries a single-use nonce, which F06-T4 exchanges for a write token.

Job state: ``queued`` -> ``running`` -> ``done`` | ``error``, and ``expired`` once the result is
older than the retention window (R5). Terminal states never change again.
"""

from __future__ import annotations

import io
import json
import logging
import secrets
import zipfile
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import auth, bundles, frontier, ratelimit, sshsig
from opn_api import clock as clockmod
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_api.githost import GitHostError, WorkflowRun
from opn_gate import attestation, schemas, signer
from opn_gate.paths import Claim

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.bundles import Bundle

log = logging.getLogger(__name__)

State = Literal["queued", "running", "done", "error", "expired"]
TERMINAL: frozenset[str] = frozenset({"done", "error", "expired"})
RESULT_RETENTION_DAYS = 30  # R5
NONCE_BYTES = 24
KEY_JOB = "job#"
JOB_FILE = "job.json"
BUNDLE_DIR = "bundle"
RESULT_FILE = "result.json"
MAX_RESULT_BYTES = 1024 * 1024  # §6: a result is capped at 1 MiB
SERVICE_KIND = "service"
EXPECTED_RUNNER = "hosted"  # R6: the job runs on a hosted runner and says so


@dataclass(frozen=True)
class Job:
    """A precheck job record (R3). ``identity_id`` is None exactly for anonymous tutorial jobs."""

    id: str
    node_id: str
    target_id: str
    statement_hash: str
    graph_commit: str
    bundle_digest: str
    created: str
    state: State = "queued"
    identity_id: str | None = None
    nonce: str | None = None
    nonce_consumed: bool = False
    run_id: str | None = None
    run_url: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    @property
    def anonymous(self) -> bool:
        return self.identity_id is None

    @property
    def claim(self) -> Claim:
        return Claim(self.target_id, self.node_id)

    def expired_at(self, now: datetime) -> bool:
        """R5: results are served for the retention window, then the body is dropped."""
        if self.state != "done":
            return False
        return clockmod.parse(self.created) + timedelta(days=RESULT_RETENTION_DAYS) <= now

    def as_dict(self, now: datetime, *, include_nonce: bool = False) -> dict[str, Any]:
        """The response body. The nonce is returned once, at creation, and never again (R2)."""
        state: State = "expired" if self.expired_at(now) else self.state
        out: dict[str, Any] = {
            "id": self.id,
            "node_id": self.node_id,
            "target_id": self.target_id,
            "state": state,
            "created": self.created,
            "graph_commit": self.graph_commit,
            "bundle_digest": self.bundle_digest,
            "authenticated": not self.anonymous,
        }
        if state == "done":
            out["result"] = self.result
        if state == "error":
            out["error"] = self.error
            out["run_url"] = self.run_url
        if state == "expired":
            out["message"] = f"results are served for {RESULT_RETENTION_DAYS} days"
        if include_nonce and self.nonce:
            out["nonce"] = self.nonce
        # The scratch repo is public, so a submitter learns that before they submit again (§7).
        out["public"] = True
        return out


def new_nonce() -> str:
    return secrets.token_urlsafe(NONCE_BYTES)


def store_key(job_id: str) -> str:
    return KEY_JOB + job_id


# --- the node this job is about ------------------------------------------------------------------


def node_facts(ctx: Context, node_id: str) -> dict[str, Any]:
    """The node as the graph's ``main`` has it: its target, statement hash and whether it is the
    tutorial node. Read from the committed frontier and targets index rather than a checkout,
    because the service holds no copy of the graph (D-35)."""
    for entry in frontier.committed_frontier(ctx)["entries"]:
        if entry["node_id"] == node_id:
            return {
                "target_id": str(entry["target_id"]),
                "statement_hash": str(entry["statement_hash"]),
                "tutorial": bool(entry["tutorial"]),
            }
    # A proved node has left the frontier but may still be prechecked — the tutorial node is
    # normally in exactly that state, and it is the one D-19 depends on.
    graph = graph_doc(ctx)
    for target_id, nodes in graph.items():
        for node in nodes:
            if node["node_id"] == node_id:
                return {
                    "target_id": target_id,
                    "statement_hash": str(node["statement_hash"]),
                    "tutorial": bool(node["tutorial"]),
                }
    raise ApiError(404, "node-unknown", f"{node_id} is not a node of this graph")


def graph_doc(ctx: Context) -> dict[str, list[dict[str, Any]]]:
    """Every target's nodes, from the committed ``targets/<id>/graph.json`` files."""
    import json  # noqa: PLC0415 — one caller

    index = json.loads(frontier.committed(ctx, "targets/index.json"))
    out: dict[str, list[dict[str, Any]]] = {}
    for target in index.get("targets", []):
        target_id = str(target["target_id"])
        doc = json.loads(frontier.committed(ctx, f"targets/{target_id}/graph.json"))
        out[target_id] = list(doc.get("nodes", []))
    return out


def rendered_from(ctx: Context) -> str:
    """The graph commit the products were rendered from: what a job is pinned to (R3)."""
    commit = frontier.committed_frontier(ctx).get("rendered_from")
    if not isinstance(commit, str) or not commit:
        raise ApiError(503, "graph-unrendered", "the graph has no rendered_from commit to pin to")
    return commit


def existing_paths(ctx: Context, node_id: str, target_id: str) -> frozenset[str]:
    """Which of the node's files already exist at ``main``, so the bundle's additions and
    modifications are classified as the gate would classify them (R1)."""
    prefix = f"targets/{target_id}/nodes/{node_id}/"
    # Only Proof.lean's existence changes a verdict: everything else the bundle may carry is
    # append-only, where "already there" is a rejection the gate makes on content, not on us.
    graph = graph_doc(ctx)
    for node in graph.get(target_id, []):
        if node["node_id"] == node_id and node.get("proof_commit"):
            return frozenset({prefix + bundles.PROOF_FILE})
    return frozenset()


# --- POST /precheck ------------------------------------------------------------------------------


async def post_precheck(ctx: Context, request: Request) -> Response:
    """R1, R2, R3, R10. Authentication is decided by the node: the tutorial one is open (Q2)."""
    fields, _ = await identitymod.body_fields(request)
    node_id = fields.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        raise ApiError(400, "node-id-missing", "node_id is required")
    facts = node_facts(ctx, node_id)
    claim = Claim(facts["target_id"], node_id)

    identity = None
    nonce = None
    if facts["tutorial"] and auth.bearer(request) is None:
        # R2: anonymous, address-limited, and answered with a single-use nonce.
        ratelimit.check_anonymous_precheck(ctx, ratelimit.client_address(request))
        nonce = new_nonce()
    else:
        identity = auth.authenticate(ctx, request)
        ratelimit.check_precheck(ctx, identity.id)

    bundle, rejection = bundles.validate(
        fields.get("bundle"), claim, existing=existing_paths(ctx, node_id, claim.target_id)
    )
    if rejection is not None or bundle is None:
        assert rejection is not None
        raise ApiError(400, rejection.code, rejection.message, headers={})

    now = ctx.clock.now()
    job = Job(
        id=identitymod.new_ulid(now),
        node_id=node_id,
        target_id=claim.target_id,
        statement_hash=facts["statement_hash"],
        graph_commit=rendered_from(ctx),
        bundle_digest=bundle.digest,
        created=clockmod.render(now),
        identity_id=identity.id if identity else None,
        nonce=nonce,
    )
    save(ctx, job)
    dispatch(ctx, job, bundle)
    return JSONResponse(job.as_dict(now, include_nonce=nonce is not None), status_code=202)


# --- handing the job to the scratch repository (R3, R10) -----------------------------------------


def branch_name(job_id: str) -> str:
    return f"job/{job_id}"


def artifact_name(job_id: str) -> str:
    """What the scratch workflow uploads the result as (``gate/precheck/precheck.yml``)."""
    return f"result-{job_id}"


def branch_files(job: Job, bundle: Bundle) -> dict[str, str]:
    """The branch's contents: the job record at the root and the bundle under ``bundle/``,
    whose paths stay relative to the graph root so ``precheck.job`` can apply them (R3, R4)."""
    record = {
        "id": job.id,
        "node_id": job.node_id,
        "target_id": job.target_id,
        "statement_hash": job.statement_hash,
        "graph_commit": job.graph_commit,
        "bundle_digest": job.bundle_digest,
        "created": job.created,
    }
    files = {JOB_FILE: json.dumps(record, indent=2, sort_keys=True) + "\n"}
    for path, content in bundle.files.items():
        files[f"{BUNDLE_DIR}/{path}"] = content
    return files


def dispatch(ctx: Context, job: Job, bundle: Bundle) -> None:
    """R3: push the branch and dispatch the workflow. R10: a failure is never silent — the job
    is marked ``error`` with the cause and the submitter is told, so no bundle is dropped (C7)."""
    settings = ctx.settings
    branch = branch_name(job.id)
    try:
        ctx.githost.push_branch(
            settings.precheck_repo,
            branch,
            branch_files(job, bundle),
            base=settings.precheck_branch,
            message=f"precheck job {job.id} ({job.node_id})",
        )
        ctx.githost.dispatch_workflow(
            settings.precheck_repo,
            settings.precheck_workflow,
            ref=branch,
            inputs={"job_id": job.id},
        )
    except GitHostError as exc:
        log.warning("precheck %s could not be dispatched: %s", job.id, exc)
        save(ctx, replace(job, state="error", error=f"dispatch failed: {exc}"))
        raise ApiError(
            502, "dispatch-failed", f"the precheck job could not be started: {exc}"
        ) from exc


# --- GET /precheck/<id> --------------------------------------------------------------------------


async def get_precheck(ctx: Context, request: Request) -> Response:
    """R5: report the job, advancing it from the run when it is not yet terminal."""
    job = load(ctx, str(request.path_params["job_id"]))
    if job is None:
        raise ApiError(404, "job-unknown", "no such precheck job")
    job = advance(ctx, job)
    return JSONResponse(job.as_dict(ctx.clock.now()))


def advance(ctx: Context, job: Job) -> Job:
    """R5, Q3: poll on read. Look up the run, and when it has finished, take its artifact,
    verify the signature and store the result. A terminal job never changes again.

    A host failure while polling leaves the job as it is and is logged: a transient GitHub
    outage must not turn a running job into a permanent error (C7).
    """
    if job.state in TERMINAL or job.expired_at(ctx.clock.now()):
        return job
    try:
        run = ctx.githost.find_run(
            ctx.settings.precheck_repo, ctx.settings.precheck_workflow, branch=branch_name(job.id)
        )
    except GitHostError as exc:
        log.warning("precheck %s: cannot read the run: %s", job.id, exc)
        return job
    if run is None:
        return job  # dispatched, but the run is not visible yet
    if not run.completed:
        return _saved(ctx, replace(job, state="running", run_id=str(run.id), run_url=run.url))
    return _collect(ctx, job, run)


def _collect(ctx: Context, job: Job, run: WorkflowRun) -> Job:
    """The run has finished: take the artifact or record why there is no result (R5)."""
    finished = replace(job, run_id=str(run.id), run_url=run.url)
    if not run.succeeded:
        why = f"the precheck run {run.conclusion or 'failed'}"
        return _saved(ctx, replace(finished, state="error", error=why))
    try:
        zipped = ctx.githost.download_artifact(
            ctx.settings.precheck_repo, run.id, artifact_name(job.id)
        )
    except GitHostError as exc:
        log.warning("precheck %s: cannot download the result: %s", job.id, exc)
        return finished if finished == job else _saved(ctx, finished)
    if zipped is None:
        return _saved(
            ctx, replace(finished, state="error", error="the precheck run produced no result")
        )
    try:
        result = read_result(zipped)
        verify_result(ctx, finished, result)
    except ResultError as exc:
        log.warning("precheck %s: %s", job.id, exc)
        return _saved(ctx, replace(finished, state="error", error=str(exc)))
    return _saved(ctx, replace(finished, state="done", result=result))


def _saved(ctx: Context, job: Job) -> Job:
    save(ctx, job)
    return job


# --- the result, and the signature that makes it worth having (R5, R6) ---------------------------


class ResultError(Exception):
    """The artifact is not a result this service will serve. The job becomes ``error``."""


def read_result(zipped: bytes) -> dict[str, Any]:
    """``result.json`` out of the artifact zip, refusing anything oversized or malformed."""
    try:
        with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
            info = next((i for i in archive.infolist() if i.filename == RESULT_FILE), None)
            if info is None:
                msg = f"the artifact carries no {RESULT_FILE}"
                raise ResultError(msg)
            if info.file_size > MAX_RESULT_BYTES:
                msg = f"the result is {info.file_size} bytes; the limit is {MAX_RESULT_BYTES}"
                raise ResultError(msg)
            raw = archive.read(info)
    except (zipfile.BadZipFile, OSError) as exc:
        msg = f"the result artifact is not a readable zip: {type(exc).__name__}"
        raise ResultError(msg) from exc
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        msg = "the result artifact is not valid JSON"
        raise ResultError(msg) from exc
    if not isinstance(doc, dict):
        msg = "the result artifact is not a JSON object"
        raise ResultError(msg)
    return doc


def precheck_public_key(ctx: Context) -> str:
    """The precheck public key as the graph commits it (C8 item 2). Read through the same
    committed-file cache the frontier uses, so a rotation reaches the service by merge."""
    return frontier.committed(ctx, ctx.settings.precheck_key_path).decode("utf-8").strip()


def verify_result(ctx: Context, job: Job, result: dict[str, Any]) -> None:
    """R5, R6: the attestation must validate, be signed by the committed precheck key as kind
    ``service``, and be about this job — the graph commit, the node and the bundle it recorded.

    Verification is the whole point of the artifact: without it the api would be serving
    whatever the scratch repository handed it, and the scratch repository is public (§7).
    """
    doc = result.get("attestation")
    if not isinstance(doc, dict):
        msg = "the result carries no attestation"
        raise ResultError(msg)
    schema = doc.get("schema")
    if schema not in attestation.ACCEPTED_SCHEMAS:
        msg = f"the attestation names an unknown schema {schema!r}"
        raise ResultError(msg)
    try:
        schemas.validate(doc, str(schema))
    except schemas.SchemaError as exc:
        msg = f"the attestation does not validate against {schema}: {exc}"
        raise ResultError(msg) from exc

    signature = doc.get("signature") or {}
    if signature.get("kind") != SERVICE_KIND:
        msg = f"the attestation is signed as {signature.get('kind')!r}, not {SERVICE_KIND}"
        raise ResultError(msg)
    public_key = precheck_public_key(ctx)
    try:
        expected_id = sshsig.fingerprint(public_key)
        ok = sshsig.verify(
            attestation.signed_bytes(doc),
            str(signature.get("value") or ""),
            public_key,
            namespace=signer.NAMESPACE,
        )
    except sshsig.SshsigError as exc:
        msg = f"the attestation's signature is malformed: {exc}"
        raise ResultError(msg) from exc
    if signature.get("key_id") != expected_id:
        msg = "the attestation is signed by a key that is not the committed precheck key"
        raise ResultError(msg)
    if not ok:
        msg = "the attestation's signature does not verify against the committed precheck key"
        raise ResultError(msg)

    for field, expected, found in (
        ("graph commit", job.graph_commit, doc.get("graph_commit")),
        ("node", job.node_id, doc.get("node_id")),
        ("runner", EXPECTED_RUNNER, doc.get("runner")),
        ("bundle digest", job.bundle_digest, result.get("bundle_digest")),
    ):
        if found != expected:
            msg = f"the result's {field} is {found!r}, not this job's {expected!r}"
            raise ResultError(msg)


# --- storage -------------------------------------------------------------------------------------


def save(ctx: Context, job: Job) -> None:
    from dataclasses import asdict  # noqa: PLC0415 — one caller

    expires = clockmod.parse(job.created) + timedelta(days=RESULT_RETENTION_DAYS + 1)
    ctx.store.put_job(job.id, asdict(job), expires)


def load(ctx: Context, job_id: str) -> Job | None:
    record = ctx.store.get_job(job_id)
    if record is None:
        return None
    fields = {f: record.get(f) for f in Job.__dataclass_fields__}
    return Job(**fields)  # type: ignore[arg-type]
