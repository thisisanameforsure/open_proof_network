"""The write tools (F09-R2, R7, R8; D-19, D-28, D-35).

Each forwards one call to its endpoint with the caller's bearer and passes the endpoint's status
and body through in an envelope ``{status, body}`` (``retry_after`` beside them when the
identity layer sent one), adding nothing: a 201 is the receipt, a 400 is the endpoint's named
refusal, a 429 is the identity layer's limit (R8) — all of them the same answer curl would get.
A refusal is an error result carrying that envelope. Without a verified bearer, a write tool
declared ``bearer`` is refused by the server at 401 with ``auth.UNAUTHORIZED`` — the route's
own shape — and never reaches its endpoint (R2). Two writes are anonymous by declaration
(F09-T6): ``precheck_submission`` forwards whatever bearer there is and lets ``POST /precheck``
decide, which opens the tutorial node (F06-R2); ``get_token`` is ``POST /tokens``, the call that
mints an identity, so it never carries one.

Parameter names follow D-28's rows. Where the endpoint's body spells a field differently
(``ttl`` is ``ttl_hours``, ``stmt`` is ``statement``, ``attestation`` binds through the job id
it carries) the mapping is ``RENAMES`` and nowhere else — every handler builds its body through
``present``, which applies it (F09-T7); ``submit_proof`` also takes that id directly as
``precheck_job_id``, exactly one of the two; the optional fields the endpoints accept
beyond D-28's lists (``tooling``, ``licence``, ``model_and_tooling``, ``deps``, ``model``,
``defect_class``) are offered so the tool is not weaker than its plain path (Q7).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from opn_api import submissions
from opn_api.mcp import auth
from opn_api.mcp.calls import ID_PARAM, Answer, Call, Tool, ToolError, error, params

LEAN = {"type": "string", "description": "the text of a Lean file"}
BUNDLE = {
    "type": "object",
    "description": "graph-relative path -> file content, the node's files being submitted",
    "additionalProperties": {"type": "string"},
}
POLL = "poll get_precheck with job_id until state is done or error; a precheck takes minutes"


def unauthorized() -> ToolError:
    return ToolError(Answer(auth.UNAUTHORIZED_STATUS, dict(auth.UNAUTHORIZED)).envelope())


async def forward(
    call: Call, method: str, path: str, body: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """One endpoint call with the caller's bearer, if the server gave the call one; the envelope,
    as a failure when the endpoint refused. Whether a bearer is required is the tool's
    declaration, enforced by the server before the handler runs (``Tool.access``)."""
    answer = await call.endpoint(method, path, json=body)
    if answer.refused:
        raise ToolError(answer.envelope())
    return answer.envelope()


#: The adapter's one machine-readable rename map (F09-T7): per tool, the D-28 argument and the
#: endpoint body field it is sent as, wherever the two are spelled differently. A tool or an
#: argument not named here is sent under its own name. The guide's MCP appendix is checked
#: against this table (F10-T7).
RENAMES: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "claim_node": MappingProxyType({"ttl": "ttl_hours"}),
        "propose_speculative_node": MappingProxyType({"stmt": "statement"}),
        "propose_variant": MappingProxyType({"stmt": "statement"}),
        "submit_proof": MappingProxyType({"attestation": "precheck_job_id"}),
    }
)


def present(tool: str, args: Mapping[str, Any], *names: str) -> dict[str, Any]:
    """The named parameters that were supplied, each under the body field ``RENAMES`` gives it
    for ``tool``, so an omitted optional stays omitted rather than becoming ``null``."""
    renames = RENAMES.get(tool, {})
    return {renames.get(n, n): args[n] for n in names if n in args}


async def claim_node(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present("claim_node", args, "node_id", "target_id", "ttl")
    return await forward(call, "POST", "/claims", body)


async def release_claim(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    return await forward(call, "DELETE", f"/claims/{args['claim_id']}")


async def precheck_submission(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present("precheck_submission", args, "node_id", "bundle", "artifact_type")
    out = await forward(call, "POST", "/precheck", body)
    body = out["body"] if isinstance(out["body"], dict) else {}
    return {**out, "job_id": body.get("id"), "poll": POLL}


async def check_lean(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    """F13-R12: ``POST /check``, with whatever bearer there is; the endpoint charges an identity
    or an address and answers in the same response, so there is nothing to poll."""
    body = present("check_lean", args, "target_id", "node_id", "content", "mode")
    return await forward(call, "POST", "/check", body)


#: The two ways to name the passing precheck a submission binds to; exactly one is given.
PRECHECK_REFS = ("attestation", "precheck_job_id")


async def submit_proof(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    given = [n for n in PRECHECK_REFS if n in args]
    if len(given) != 1:
        raise error(
            "arguments-invalid",
            "submit_proof takes exactly one of `attestation` (the get_precheck result) and "
            f"`precheck_job_id` (its id); {'both were' if given else 'neither was'} given",
            "adapter",
        )
    fields = dict(args)
    attestation = fields.get("attestation")
    if isinstance(attestation, dict):
        fields["attestation"] = attestation.get("id")  # the id is what binds (F09-Q2)
    body = present(
        "submit_proof", fields, "node_id", "artifact_type", "bundle", "tooling", *PRECHECK_REFS
    )
    return await forward(call, "POST", "/submissions", body)


async def submit_postmortem(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present("submit_postmortem", args, "node_id", "yaml")
    return await forward(call, "POST", "/postmortems", body)


async def submit_informal_annex(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present("submit_informal_annex", args, "node_id", "text", "licence", "model_and_tooling")
    return await forward(call, "POST", "/annexes", body)


async def submit_approach_record(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present("submit_approach_record", args, "target_id", "record")
    return await forward(call, "POST", "/approach-records", body)


async def file_defect_claim(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present("file_defect_claim", args, "stmt_ref", "class", "line", "exhibit")
    return await forward(call, "POST", "/defect-claims", body)


async def file_revision_request(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present("file_revision_request", args, "node_id", "defect_class", "evidence")
    return await forward(call, "POST", "/revision-requests", body)


async def propose_speculative_node(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present(
        "propose_speculative_node",
        args,
        "target_id",
        "stmt",
        "witness",
        "deps",
        "model",
        "acknowledged_hazards",
    )
    return await forward(call, "POST", "/proposals/speculative", body)


async def propose_variant(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present(
        "propose_variant",
        args,
        "target_id",
        "stmt",
        "witness",
        "relation",
        "relation_proof",
        "deps",
        "model",
        "acknowledged_hazards",
    )
    return await forward(call, "POST", "/proposals/variant", body)


async def get_token(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present("get_token", args, "proof", "pseudonym", "dco")
    return await forward(call, "POST", "/tokens", body)


async def propose_witness(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present("propose_witness", args, "node_id", "witness")
    return await forward(call, "POST", "/proposals/witness", body)


#: One declared tooling string as ``submissions.check_tooling`` reads it: a string of at most
#: ``MAX_TOOLING_CHARS``, or ``null`` for undeclared (F09-T10: the guide's own example says
#: ``"version": None``, and the adapter refused what the endpoint takes).
DECLARED = {"type": ["string", "null"], "maxLength": submissions.MAX_TOOLING_CHARS}
TOOLING = {
    "type": "object",
    "description": "the D-23 declaration: model, version, harness (each a string or null)",
    "properties": {
        "model": DECLARED,
        "version": DECLARED,
        "harness": DECLARED,
    },
}
DEPS = {"type": "array", "items": ID_PARAM, "description": "node ids the statement depends on"}
MODEL = {"type": "string", "description": "the model or tooling that produced the statement"}
#: F08-T14: META.yaml's own shape (F02-R4), so a statement that carries an intended step-6 finding
#: can be proposed at all.
HAZARDS = {
    "type": "array",
    "description": "step-6 hazard findings you intend, each as the gate's hazard-unacknowledged "
    "diagnostic prints it: checker, location, and your justification",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["checker", "location", "justification"],
        "properties": {
            "checker": {"type": "string"},
            "location": {"type": "string"},
            "justification": {"type": "string", "maxLength": 500},
        },
    },
}

TOOLS: tuple[Tool, ...] = (
    Tool(
        "claim_node",
        "Register an advisory, non-exclusive claim on a frontier node; returns the receipt. "
        "`ttl` is in hours, within the published flat caps; undeclared means the minimum.",
        params(
            {"node_id": ID_PARAM, "ttl": {"type": "integer", "minimum": 1}, "target_id": ID_PARAM},
            ("node_id",),
        ),
        claim_node,
        write=True,
    ),
    Tool(
        "release_claim",
        "Release a claim early; only its holder may.",
        params({"claim_id": {"type": "string", "pattern": "^[0-9A-Z]{26}$"}}, ("claim_id",)),
        release_claim,
        write=True,
    ),
    Tool(
        "precheck_submission",
        "Run the gate's steps 1-2 and 4-8 on a bundle server-side, structurally identical to "
        "pregate.sh, and get back a job id to poll; a passing precheck yields the signed "
        "attestation submit_proof needs. On the tutorial node no token is needed: the job is "
        "answered with a single-use nonce, and its passing {id, nonce} is the proof get_token "
        "takes. Every other node needs a token.",
        params(
            {
                "node_id": ID_PARAM,
                "bundle": BUNDLE,
                "artifact_type": {
                    "enum": ["proof", "counterexample", "vacuity", "reduction", "partial"],
                    "description": "optional: the type this bundle will be submitted as; a "
                    "bundle at the wrong path for it is refused before any job starts",
                },
            },
            ("node_id", "bundle"),
        ),
        precheck_submission,
        write=True,
        access="endpoint",
    ),
    Tool(
        "check_lean",
        "Check Lean text within 20 s on the hosted checker matched to the target's pinned "
        "Mathlib (AXLE, a third party) and get its errors, goal states and, with mode verify and "
        "a node_id, its comparison against the node's statement, plus warnings wherever the gate "
        "would refuse what the checker accepted. The body's `okay` is true, false, or null when "
        "the checker gave no verdict (then `user_error` says why, e.g. the node's statement did "
        "not compile); `result` is the checker's body verbatim. The target's Defs modules and, "
        "with a node_id, the node's own Context (its dependencies' and holes' theorems) are "
        "inlined for you (`inlined_defs`); without a node_id you can check a statement that is "
        "not a node yet. A proof that uses a dependency is checked with mode check, not verify. "
        "Never authoritative: a precheck is the verdict. "
        "No token needed; a token raises the limit. Every call is logged without its text; "
        "GET /hosted-checkers.json says which targets have a checker.",
        params(
            {
                "target_id": ID_PARAM,
                "node_id": ID_PARAM,
                "content": LEAN,
                "mode": {"enum": ["check", "verify"], "description": "verify needs node_id"},
            },
            ("target_id", "content"),
        ),
        check_lean,
        write=True,
        access="endpoint",
    ),
    Tool(
        "get_token",
        "Mint a write token (D-19); no token needed, since this is how an identity starts. "
        "`proof` is {kind: tutorial, job_id, nonce} from a passing precheck_submission of the "
        "tutorial node made without a token (or a GitHub proof); `pseudonym` is the name your "
        "contributions carry; `dco` is {version, accepted: true} with the version GET /dco.json "
        "publishes. The token is shown once: send it as `Authorization: Bearer <token>`.",
        params(
            {
                "proof": {"type": "object", "description": "{kind: tutorial, job_id, nonce}"},
                "pseudonym": {"type": "string"},
                "dco": {"type": "object", "description": "{version, accepted: true}"},
            },
            ("proof", "pseudonym", "dco"),
        ),
        get_token,
        write=True,
        access="anyone",
    ),
    Tool(
        "submit_proof",
        "Open the submission pull request on the graph: the ledger identity as author and "
        "sign-off, the service as committer. Name the passing precheck of this bundle with "
        "exactly one of `attestation` (the get_precheck result) or `precheck_job_id` (its id). "
        "On a node whose Proof.lean has already merged, a later proof is an alternate: put it "
        "at attempts/<timestamp>-<pseudonym>-alternate.lean with artifact_type proof (D-25).",
        params(
            {
                "node_id": ID_PARAM,
                "artifact_type": {
                    "enum": ["proof", "counterexample", "vacuity", "reduction", "partial"]
                },
                "bundle": BUNDLE,
                "attestation": {
                    "type": "object",
                    "description": "the get_precheck result; its `id` binds the submission. "
                    "Give this or precheck_job_id, not both",
                },
                "precheck_job_id": {
                    "type": "string",
                    "description": "the id of a passing precheck of this bundle. Give this or "
                    "attestation, not both",
                },
                "tooling": TOOLING,
            },
            ("node_id", "artifact_type", "bundle"),
        ),
        submit_proof,
        write=True,
    ),
    Tool(
        "submit_postmortem",
        "Append a schema-checked postmortem (D-13) under the node; `yaml` is the record as an "
        "object, validated against postmortem/v1.",
        params({"node_id": ID_PARAM, "yaml": {"type": "object"}}, ("node_id", "yaml")),
        submit_postmortem,
        write=True,
    ),
    Tool(
        "submit_informal_annex",
        "Attach a content-hashed informal argument to a node (D-31); untrusted data that earns "
        "nothing. Returns the hash a skeleton must cite.",
        params(
            {
                "node_id": ID_PARAM,
                "text": {"type": "string"},
                "licence": {"enum": ["CC-BY-4.0", "CDLA-Permissive-2.0", "Apache-2.0"]},
                "model_and_tooling": {"type": "string"},
            },
            ("node_id", "text"),
        ),
        submit_informal_annex,
        write=True,
    ),
    Tool(
        "submit_approach_record",
        "Record a target-scoped strategy verdict (D-14); `record` validates against "
        "approach-record/v1.",
        params({"target_id": ID_PARAM, "record": {"type": "object"}}, ("target_id", "record")),
        submit_approach_record,
        write=True,
    ),
    Tool(
        "file_defect_claim",
        "File a statement-defect claim (D-16): a class from the taxonomy, a line of the "
        "referenced file, and a Lean exhibit; malformed claims bounce here with the rule named.",
        params(
            {
                "stmt_ref": {"type": "string"},
                "class": {"type": "string"},
                "line": {"type": "integer", "minimum": 1},
                "exhibit": LEAN,
            },
            ("stmt_ref", "class", "line", "exhibit"),
        ),
        file_defect_claim,
        write=True,
    ),
    Tool(
        "file_revision_request",
        "File a D-8 revision request against a node: a defect class and evidence "
        "(`{text, exhibit?}`) for a curator to act on.",
        params(
            {
                "node_id": ID_PARAM,
                "defect_class": {"type": "string"},
                "evidence": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}, "exhibit": LEAN},
                    "required": ["text"],
                },
            },
            ("node_id", "defect_class", "evidence"),
        ),
        file_revision_request,
        write=True,
    ),
    Tool(
        "propose_speculative_node",
        "Enter a crux statement as a speculative node (D-14): `stmt` and `witness` are Lean "
        "files; admission is mechanical (D-29).",
        params(
            {
                "target_id": ID_PARAM,
                "stmt": LEAN,
                "witness": LEAN,
                "deps": DEPS,
                "model": MODEL,
                "acknowledged_hazards": HAZARDS,
            },
            ("target_id", "stmt", "witness"),
        ),
        propose_speculative_node,
        write=True,
    ),
    Tool(
        "propose_variant",
        "Enter a labeled variant of the root (D-30): relation is resolves, partial or related "
        "(default); a label above related needs `relation_proof`, gate-checked.",
        params(
            {
                "target_id": ID_PARAM,
                "stmt": LEAN,
                "witness": LEAN,
                "relation": {"enum": ["resolves", "partial", "related"]},
                "relation_proof": LEAN,
                "deps": DEPS,
                "model": MODEL,
                "acknowledged_hazards": HAZARDS,
            },
            ("target_id", "stmt", "witness"),
        ),
        propose_variant,
        write=True,
    ),
    Tool(
        "propose_witness",
        "Fill the witness slot of a hole blocked `witness-missing` (a node a merged partial "
        "created, F08-R5): opens the pull request adding only its Witness.lean. `witness` is "
        "the Lean file.",
        params({"node_id": ID_PARAM, "witness": LEAN}, ("node_id", "witness")),
        propose_witness,
        write=True,
    ),
)
