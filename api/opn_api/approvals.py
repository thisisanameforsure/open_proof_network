"""``POST /approvals``: a steward or curator approves words from the site (F23-R10; D-3 v3.33,
D-32 v3.33, D-35 v3.33).

A signed-in login that is an active steward of the target or a listed curator approves sections
of one gloss or explainer version. The service writes ``gloss-signature/v3`` or
``explainer-signature/v3`` — the fixed affirmation, the signer the session's login, ``via:
approval-key`` — signs it with the network's approval key over the canonical body the gate
verifies, and opens it on an ``append/`` branch at the ``signed/`` path the gate's own writers use
(``<hash>-<n>.yaml``). It means what an SSH signature means (D-3 v3.33); any other login is 403.

The version and its sections are checked against the graph at the current commit, read into a
scratch tree by the gloss routes' own reader (``glosses.materialise``), so a version that is not
there, or a section it does not have, is refused before anything opens. Whether the signature
counts — the key against ``keys/approval.pub``, the signer's role — is the gate's at the merge.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, ratelimit, session, stewards, submissions
from opn_api import glosses as glossroutes
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_gate import explainers, glosses
from opn_gate import sections as sectionsmod

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

GLOSS = "gloss"
EXPLAINER = "explainer"
SCHEMAS: dict[str, str] = {GLOSS: "gloss-signature/v3", EXPLAINER: "explainer-signature/v3"}
FIELDS: tuple[str, ...] = ("target", "node", "kind", "version", "sections")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def checked(fields: dict[str, Any]) -> tuple[str, str | None, str, str, list[str] | None]:
    """(target, node, kind, version, sections), or ``400 arguments-invalid`` naming the field."""
    bad = stewards.bad
    target = fields.get("target")
    if not isinstance(target, str) or not IDENTIFIER_RE.match(target):
        raise bad("target is required: a target id", field="target")
    node = fields.get("node")
    if node is not None and (not isinstance(node, str) or not IDENTIFIER_RE.match(node)):
        raise bad("node is a node id, or null for a definition module's gloss", field="node")
    kind = fields.get("kind")
    if kind not in SCHEMAS:
        raise bad(f"kind is {GLOSS!r} or {EXPLAINER!r}", field="kind")
    if kind == EXPLAINER and node is None:
        raise bad("an explainer is of a node's proof: node is required", field="node")
    version = fields.get("version")
    if not isinstance(version, str) or not HASH_RE.match(version):
        raise bad("version is the version's SHA-256, its file name", field="version")
    raw = fields.get("sections")
    if raw is None:
        return target, node, str(kind), version, None
    if (
        not isinstance(raw, list)
        or not raw
        or not all(isinstance(s, str) for s in raw)
        or len(set(raw)) != len(raw)
    ):
        raise bad("sections is null (all) or a non-empty list of distinct keys", field="sections")
    if kind == GLOSS and raw != [sectionsmod.WHOLE]:
        raise bad(f"a gloss is one section, {sectionsmod.WHOLE!r}", field="sections")
    return target, node, str(kind), version, list(raw)


def may_approve(ctx: Context, target_id: str, login: str) -> None:
    """R10: an active steward of the target or a listed curator; anyone else is 403."""
    if session.is_curator(ctx, login) or session.is_steward(ctx, target_id, login):
        return
    raise ApiError(
        403,
        "not-steward-or-curator",
        f"{login} is neither an active steward of {target_id} nor a listed curator; only they "
        "may approve words (D-3 v3.33)",
    )


def signature_path(  # noqa: PLR0913 — one version, named
    ctx: Context,
    target_id: str,
    node_id: str | None,
    *,
    kind: str,
    version: str,
    sections: list[str] | None,
) -> str:
    """The graph path the gate's own writer would choose (``glosses.next_signature_path``,
    ``explainers.next_path``) over the graph as it stands, after checking the version is there
    (404 ``version-unknown``) and has the sections named (400)."""
    with tempfile.TemporaryDirectory(prefix="opn-approval-") as tmp:
        root = Path(tmp)
        target_dir = glossroutes.materialise(ctx, root, target_id, node_id, roles=False)
        parent = target_dir if node_id is None else target_dir / "nodes" / node_id
        if kind == GLOSS:
            if version not in glosses.gloss_hashes(parent):
                raise unknown(kind, version)
            path = glosses.next_signature_path(parent, version)
        else:
            if version not in explainers.explainer_hashes(parent):
                raise unknown(kind, version)
            known = explainers.section_keys(parent / explainers.EXPLAINER_DIR / f"{version}.md")
            missing = [s for s in sections or () if s not in known]
            if missing:
                raise stewards.bad(
                    f"explainer {version[:12]}… has no section {', '.join(missing)}; its sections "
                    f"are {', '.join(known) or 'none'}",
                    field="sections",
                    known=known,
                )
            path = explainers.next_path(parent, version)
        return path.relative_to(root).as_posix()


def unknown(kind: str, version: str) -> ApiError:
    return ApiError(
        404, "version-unknown", f"no {kind} {version[:12]}… is merged where the request names"
    )


async def post_approvals(ctx: Context, request: Request) -> Response:
    """R10: one approval, signed with the approval key, in its own pull request."""
    held: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, FIELDS)
    login = stewards.github_login(held)
    target_id, node_id, kind, version, sections = checked(fields)
    private, public = stewards.approval_key(ctx)
    appends.known_target(ctx, target_id)
    ratelimit.enforce(
        ctx,
        "approval",
        login.casefold(),
        limit=ctx.settings.approvals_per_hour,
        seconds=ratelimit.HOUR_S,
    )
    may_approve(ctx, target_id, login)
    if node_id is not None:
        _, found = appends.node_target(ctx, {"node_id": node_id})
        if found != target_id:
            raise stewards.bad(f"{node_id} is a node of {found}, not {target_id}", field="node")
    path = signature_path(ctx, target_id, node_id, kind=kind, version=version, sections=sections)
    doc: dict[str, Any] = {
        "schema": SCHEMAS[kind],
        "target": target_id,
        "node": node_id,
        kind: version,
        "affirmation": glosses.AFFIRMATION if kind == GLOSS else explainers.AFFIRMATION,
        "signer": login,
        "date": ctx.clock.now().strftime("%Y-%m-%d"),
        "via": stewards.VIA,
    }
    if sections is not None:
        doc["sections"] = sections
    doc = stewards.sign_record(doc, private, public)
    appends.validated(doc, SCHEMAS[kind])
    body = appends.append_pr(
        ctx,
        held,
        path=path,
        content=yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        subject=f"approval: {kind} {version[:12]} by {login}",
        what="approval",
        kind="approval",
        target_id=target_id,
        node_id=node_id,
        written=f"{kind} {version} {login} {sections}",
    )
    prefix = submissions.APPEND_BRANCH_PREFIX
    return JSONResponse(stewards.receipt(body, prefix), status_code=201)
