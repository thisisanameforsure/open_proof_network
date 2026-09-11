"""The write tools (F09-R2, R7, R8; D-19, D-28, D-35).

Each forwards one call to its endpoint with the caller's bearer and passes the endpoint's status
and body through in an envelope ``{status, body}`` (``retry_after`` beside them when the
identity layer sent one), adding nothing: a 201 is the receipt, a 400 is the endpoint's named
refusal, a 429 is the identity layer's limit (R8) — all of them the same answer curl would get.
A refusal is an error result carrying that envelope. Without a verified bearer, a write tool
answers the SDK's unauthorized body at 401 and never reaches its endpoint (R2).

Parameter names follow D-28's rows. Where the endpoint's body spells a field differently
(``ttl`` is ``ttl_hours``, ``stmt`` is ``statement``, ``attestation`` binds through the job id
it carries) the mapping is here and nowhere else; the optional fields the endpoints accept
beyond D-28's lists (``tooling``, ``licence``, ``model_and_tooling``, ``deps``, ``model``,
``defect_class``) are offered so the tool is not weaker than its plain path (Q7).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from opn_api.mcp import auth
from opn_api.mcp.calls import ID_PARAM, Answer, Call, Tool, ToolError, params

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
    """One endpoint call with the bearer; the envelope, as a failure when the endpoint refused."""
    if not call.token:
        raise unauthorized()
    answer = await call.endpoint(method, path, json=body)
    if answer.refused:
        raise ToolError(answer.envelope())
    return answer.envelope()


def present(args: Mapping[str, Any], *names: str, **renamed: str) -> dict[str, Any]:
    """The given parameters that were supplied, renamed where the endpoint spells them
    differently, so an omitted optional stays omitted rather than becoming ``null``."""
    out = {n: args[n] for n in names if n in args}
    out.update({to: args[fr] for fr, to in renamed.items() if fr in args})
    return out


async def claim_node(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    return await forward(
        call, "POST", "/claims", present(args, "node_id", "target_id", ttl="ttl_hours")
    )


async def release_claim(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    return await forward(call, "DELETE", f"/claims/{args['claim_id']}")


async def precheck_submission(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    out = await forward(call, "POST", "/precheck", present(args, "node_id", "bundle"))
    body = out["body"] if isinstance(out["body"], dict) else {}
    return {**out, "job_id": body.get("id"), "poll": POLL}


async def submit_proof(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    attestation = args.get("attestation")
    body = present(args, "node_id", "artifact_type", "bundle", "tooling")
    body["precheck_job_id"] = (
        attestation.get("id") if isinstance(attestation, dict) else attestation
    )
    return await forward(call, "POST", "/submissions", body)


async def submit_postmortem(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    return await forward(call, "POST", "/postmortems", present(args, "node_id", "yaml"))


async def submit_informal_annex(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    return await forward(
        call, "POST", "/annexes", present(args, "node_id", "text", "licence", "model_and_tooling")
    )


async def submit_approach_record(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    return await forward(call, "POST", "/approach-records", present(args, "target_id", "record"))


async def file_defect_claim(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    return await forward(
        call, "POST", "/defect-claims", present(args, "stmt_ref", "class", "line", "exhibit")
    )


async def file_revision_request(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    return await forward(
        call, "POST", "/revision-requests", present(args, "node_id", "defect_class", "evidence")
    )


async def propose_speculative_node(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present(args, "target_id", "witness", "deps", "model", stmt="statement")
    return await forward(call, "POST", "/proposals/speculative", body)


async def propose_variant(call: Call, args: dict[str, Any]) -> dict[str, Any]:
    body = present(
        args,
        "target_id",
        "witness",
        "relation",
        "relation_proof",
        "deps",
        "model",
        stmt="statement",
    )
    return await forward(call, "POST", "/proposals/variant", body)


TOOLING = {
    "type": "object",
    "description": "the D-23 declaration: model, version, harness (each a string)",
    "properties": {
        "model": {"type": "string"},
        "version": {"type": "string"},
        "harness": {"type": "string"},
    },
}
DEPS = {"type": "array", "items": ID_PARAM, "description": "node ids the statement depends on"}
MODEL = {"type": "string", "description": "the model or tooling that produced the statement"}

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
        "attestation submit_proof needs.",
        params({"node_id": ID_PARAM, "bundle": BUNDLE}, ("node_id", "bundle")),
        precheck_submission,
        write=True,
    ),
    Tool(
        "submit_proof",
        "Open the submission pull request on the graph: the ledger identity as author and "
        "sign-off, the service as committer. `attestation` is the get_precheck result of a "
        "passing precheck of this bundle.",
        params(
            {
                "node_id": ID_PARAM,
                "artifact_type": {
                    "enum": ["proof", "counterexample", "vacuity", "reduction", "partial"]
                },
                "bundle": BUNDLE,
                "attestation": {
                    "type": "object",
                    "description": "the get_precheck result; its `id` binds the submission",
                },
                "tooling": TOOLING,
            },
            ("node_id", "artifact_type", "bundle", "attestation"),
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
            {"target_id": ID_PARAM, "stmt": LEAN, "witness": LEAN, "deps": DEPS, "model": MODEL},
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
            },
            ("target_id", "stmt", "witness"),
        ),
        propose_variant,
        write=True,
    ),
)
