"""The proposal routes (F08-R3, R4, R5; D-14, D-29, D-30, D-35).

``POST /proposals/speculative`` and ``POST /proposals/variant`` are D-28's
``propose_speculative_node`` and ``propose_variant``: they put a whole new node directory into
the graph through a pull request that admission decides (D-29) and nobody reviews. ``POST
/proposals/witness`` fills the witness slot of a compiler-derived hole (F07-Q3, F08-R5) — the one
addition to an existing directory the ``proposal`` mode permits.

The service scaffolds the directory with the gate's own builder (``opn_gate.scaffold``), so the
bytes it pushes are exactly the bytes ``opn-gate admit`` will judge; it decides nothing about
whether the statement is worth having, and it never elaborates anything (C9). The identity is
the caller's, the date is the service clock's, and ``Context.lean`` is generated from the deps'
committed statements rather than accepted, because F01-R6 needs it byte-equal to them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, frontier, precheck, ratelimit, submissions
from opn_api import clock as clockmod
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_gate import graph as graphmod
from opn_gate import scaffold

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

log = logging.getLogger(__name__)

PROPOSE_BRANCH_PREFIX = "propose/"
SPECULATIVE_PREFIX = "spec"  # F08-R3: <target>/spec-<hash8>
VARIANT_PREFIX = "variant"
MAX_LEAN_BYTES = 64 * 1024  # a statement, a witness or a relation proof; F07 §6's annex cap
MAX_DEPS = 20  # F07 §6's holes-per-partial cap, reused: a proposal is not a decomposition dump


def lean_text(fields: dict[str, Any], name: str, *, required: bool = True) -> str | None:
    """A Lean file the caller sent: a string, non-empty when required, under the size cap.
    Stored verbatim (F07-R14); its meaning is admission's business."""
    raw = fields.get(name)
    if raw is None or raw == "":
        if required:
            raise ApiError(400, f"{name}-missing", f"{name} is required")
        return None
    if not isinstance(raw, str):
        raise ApiError(400, f"{name}-invalid", f"{name} must be the text of a Lean file")
    if len(raw.encode()) > MAX_LEAN_BYTES:
        raise ApiError(
            400,
            "field-too-long",
            f"{name} is {len(raw.encode())} bytes; the cap is {MAX_LEAN_BYTES}",
        )
    return raw


def dep_statements(
    ctx: Context, target_id: str, raw: Any
) -> tuple[tuple[str, ...], dict[str, str]]:
    """R3: the declared deps, each a node of the target, with its committed ``Statement.lean``."""
    if raw is None:
        return (), {}
    if not isinstance(raw, list) or not all(isinstance(d, str) and d for d in raw):
        raise ApiError(400, "deps-invalid", "deps must be a list of node ids")
    if len(raw) > MAX_DEPS:
        raise ApiError(400, "deps-invalid", f"a proposal declares at most {MAX_DEPS} deps")
    known = {n["node_id"] for n in precheck.graph_doc(ctx).get(target_id, [])}
    deps = tuple(dict.fromkeys(raw))  # order kept, duplicates dropped
    statements: dict[str, str] = {}
    for dep in deps:
        if dep not in known:
            raise ApiError(404, "dep-unknown", f"{dep} is not a node of target {target_id}")
        path = f"targets/{target_id}/nodes/{dep}/Statement.lean"
        statements[dep] = frontier.committed(ctx, path).decode("utf-8")
    return deps, statements


def model_of(fields: dict[str, Any]) -> str | None:
    """D-23: the model declared as the statement's author's tool, capped, never trusted."""
    raw = fields.get("model")
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str) or len(raw) > submissions.MAX_TOOLING_CHARS:
        raise ApiError(
            400,
            "tooling-invalid",
            f"model must be a string of at most {submissions.MAX_TOOLING_CHARS} characters",
        )
    return raw


def scaffolded(proposal: scaffold.Proposal, statements: dict[str, str]) -> dict[str, str]:
    """The directory's files under their graph paths, or the 400 the gate's own builder would
    have refused with. The builder's paths are relative to the node directory; the branch's are
    relative to the graph root, and that prefix is what puts the node where D-3 says it lives."""
    prefix = f"targets/{proposal.target_id}/nodes/{proposal.node_id}/"
    try:
        files = scaffold.files(None, proposal, dep_statements=statements)
    except scaffold.ScaffoldError as exc:
        raise ApiError(400, "proposal-invalid", str(exc)) from exc
    return {prefix + rel: content for rel, content in files.items()}


def open_proposal(  # noqa: PLR0913 — one pull request, described
    ctx: Context,
    identity: Identity,
    *,
    target_id: str,
    node_id: str,
    files: dict[str, str],
    what: str,
) -> dict[str, Any]:
    """R3, R5 -> F07-R2: one branch, one authored commit, one pull request the gate admits."""
    ratelimit.check_proposal(ctx, identity.id)
    proposal_id = identitymod.new_ulid(ctx.clock.now())
    subject = f"proposal: {node_id}"
    pr = submissions.open_pr(
        ctx,
        identity,
        branch=PROPOSE_BRANCH_PREFIX + proposal_id,
        files=files,
        subject=subject,
        title=subject,
        body=(
            f"A {what} proposed through the Open Proof Network service by "
            f"`{identity.pseudonym}`. Admission is mechanical (D-29): the gate checks the "
            "layout, the statement, the witness, the hazards, the context, the graph and any "
            "relation proof (F08-R1), and no one approves structure.\n\n"
            f"`targets/{target_id}/nodes/{node_id}/`\n"
        ),
    )
    log.info("%s %s opened %s for %s", what, proposal_id, pr.url, identity.id)
    return {
        "proposal_id": proposal_id,
        "node_id": node_id,
        "target_id": target_id,
        "pr_url": pr.url,
        "pr_number": pr.number,
    }


def node_files(
    ctx: Context, identity: Identity, fields: dict[str, Any], **kwargs: Any
) -> tuple[str, dict[str, str], str]:
    """The target, the files and the node id of a speculative or variant proposal."""
    target_id = appends.known_target(ctx, fields.get("target_id"))
    statement = lean_text(fields, "statement")
    witness = lean_text(fields, "witness")
    assert statement is not None and witness is not None
    deps, statements = dep_statements(ctx, target_id, fields.get("deps"))
    node_id = scaffold.speculative_id(statement, kwargs.pop("prefix"))
    proposal = scaffold.Proposal(
        node_id=node_id,
        target_id=target_id,
        statement=statement,
        witness=witness,
        author=identity.pseudonym,
        deps=deps,
        date=clockmod.render(ctx.clock.now()),
        model=model_of(fields),
        **kwargs,
    )
    return target_id, scaffolded(proposal, statements), node_id


# --- POST /proposals/speculative (D-14 mechanism 2) -----------------------------------------------


async def post_speculative(ctx: Context, request: Request) -> Response:
    """R3: a crux statement as a typechecked, refutable object — origin authored, marked
    speculative by a status record inside the new directory (F08-Q2)."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request)
    target_id, files, node_id = node_files(
        ctx, identity, fields, prefix=SPECULATIVE_PREFIX, origin="authored", speculative=True
    )
    return JSONResponse(
        open_proposal(
            ctx,
            identity,
            target_id=target_id,
            node_id=node_id,
            files=files,
            what="speculative node",
        ),
        status_code=201,
    )


# --- POST /proposals/variant (D-30) ---------------------------------------------------------------


async def post_variant(ctx: Context, request: Request) -> Response:
    """R4: a labeled variant of the root; a label above ``related`` needs its implication proof,
    and the label lives in that proof's file (F08-Q6), so the two cannot be separated."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request)
    relation = fields.get("relation") or "related"
    if relation not in scaffold.RELATION_LABELS:
        raise ApiError(
            400,
            "relation-invalid",
            f"relation must be one of {', '.join(scaffold.RELATION_LABELS)} (D-30)",
        )
    proof = lean_text(fields, "relation_proof", required=False)
    if relation in scaffold.LABELS_NEEDING_PROOF and proof is None:
        raise ApiError(
            400,
            "relation-proof-required",
            f"a variant labeled {relation!r} claims an implication, so it needs a relation_proof "
            "— a Lean proof of "
            + ("variant → root" if relation == "resolves" else "root → variant")
            + " (D-30)",
        )
    target_id, files, node_id = node_files(
        ctx,
        identity,
        fields,
        prefix=VARIANT_PREFIX,
        origin="variant",
        relation=str(relation),
        relation_proof=proof,
    )
    return JSONResponse(
        open_proposal(
            ctx, identity, target_id=target_id, node_id=node_id, files=files, what="variant"
        ),
        status_code=201,
    )


# --- POST /proposals/witness (F07-Q3, F08-R5) -----------------------------------------------------


def hole_awaiting_witness(ctx: Context, node_id: Any) -> str:
    """R5: the node exists, is a hole, and is blocked for want of a witness — as the products
    say, because the products are what the gate derived from the tree (F03)."""
    if not isinstance(node_id, str) or not node_id:
        raise ApiError(400, "node-id-missing", "node_id is required")
    for target_id, nodes in precheck.graph_doc(ctx).items():
        for node in nodes:
            if node.get("node_id") != node_id:
                continue
            if node.get("cause") != graphmod.CAUSE_WITNESS_MISSING:
                raise ApiError(
                    400,
                    "witness-not-missing",
                    f"{node_id} is {node.get('status')} and its witness slot is not open; only "
                    f"a hole blocked with cause {graphmod.CAUSE_WITNESS_MISSING!r} takes one "
                    "(F08-R5)",
                )
            return str(target_id)
    raise ApiError(404, "node-unknown", f"{node_id} is not a node of this graph")


async def post_witness(ctx: Context, request: Request) -> Response:
    """R5: fill a hole's witness slot — a pull request adding only ``Witness.lean``."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request)
    node_id = fields.get("node_id")
    target_id = hole_awaiting_witness(ctx, node_id)
    assert isinstance(node_id, str)
    witness = lean_text(fields, "witness")
    assert witness is not None
    if "sorry" in witness:
        raise ApiError(400, "witness-invalid", "a witness with a sorry leaves the slot empty")
    path = f"targets/{target_id}/nodes/{node_id}/Witness.lean"
    return JSONResponse(
        open_proposal(
            ctx,
            identity,
            target_id=target_id,
            node_id=node_id,
            files={path: witness},
            what="witness for a hole",
        ),
        status_code=201,
    )
