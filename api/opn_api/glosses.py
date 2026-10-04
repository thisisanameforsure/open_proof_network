"""The gloss routes (F20-R10, R11; D-3 v3.30, D-28, D-35): ``POST /glosses`` and
``POST /glosses/withdrawals``.

A gloss is prose saying what one Lean file says; an explainer is prose about one merged proof
artifact; a withdrawal takes one version of either out of its chain. All three are appends that
claim nothing a kernel checks, so the service opens them as ``append/`` pull requests the merge
actor merges, as it does an annex. Two rules hold every one:

* **The caller supplies the words, the service supplies the identity** (F07-R11; F18-Q7(a)). The
  record's ``author`` is the token's pseudonym and nothing the body says; its ``date`` is today;
  a gloss or explainer is named by the hash of the file as it lands (D-3), and placed where its
  subject puts it — ``nodes/<id>/gloss/``, ``targets/<id>/gloss/`` for a definition module,
  ``nodes/<id>/explainer/`` for a proof. Every such pull request is authored by the service's
  App, so the gate judges who is acting from that ``author`` (``modes.acting_names``, F20-T6).
* **Refused before anything opens** (the owner's ruling of 2026-09-24, F13-T21): the gate's own
  classifier and checks (R1 to R7) run over a scratch tree holding exactly the files they read —
  the subject, the node's versions, signatures and withdrawals, the outlines, the stewards and
  the curators, fetched from the graph at ``main`` — with the new file added, and the first
  problem is the refusal, by the gate's code, with no branch pushed and no pull request opened.
  The gate checks it again at the merge.

The service has no OpenSSH (F06-Q6), so the signed records the checks read (steward commitments,
signatures) are verified by ``HostVerifier``, the service's own SSHSIG reader. A pseudonym spelled
like another person's real-identity login is refused here (``author-names-another``): the gate
reads the ``author`` of a service pull request as that person's name, so the service must never
write one for anybody else.

``node_glosses`` is the toolchain-free twin of the committed ``glosses.json`` for one node
(F10-Q7): the same gate function over the same files, read from the host into a scratch tree.
"""

from __future__ import annotations

import logging
import re
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, pending, sshsig
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_api.githost import GitHostError
from opn_gate import config as gate_config
from opn_gate import explainers, glosses, modes, products, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change
from opn_gate.signer import NAMESPACE, Signature, SignatureKind, SignerError

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

log = logging.getLogger(__name__)

#: F05-T8: the fields each route reads; any other top-level key is refused.
GLOSS_FIELDS: tuple[str, ...] = ("subject", "text", "supersedes", "licence")
WITHDRAWAL_FIELDS: tuple[str, ...] = ("record", "reason")
#: What ``subject`` may hold. ``kind`` is a gloss's (statement, witness, relation, definition)
#: or ``proof`` for an explainer; ``node_id`` names the node, ``target_id`` and ``module`` a
#: definition module; ``proof`` the merged artifact an explainer describes; ``lean_hash`` the
#: text a gloss describes, the file as it stands when omitted.
SUBJECT_KEYS: tuple[str, ...] = ("kind", "node_id", "target_id", "module", "proof", "lean_hash")
PROOF_KIND = "proof"
GLOSS_KINDS: tuple[str, ...] = (*glosses.KIND_FILES, glosses.DEFINITION)
TEXT_MAX_BYTES = appends.ANNEX_MAX_BYTES  # the cap an annex's prose has (F07 §6)
WITHDRAWAL_SCHEMA = "withdrawal/v2"
#: The login the scratch classification is opened as, and the login the gate treats as the
#: service's: the same value, so the pre-flight judges the record as the merge will (F20-T6).
OPENER = gate_config.DEFAULT_SERVICE_LOGIN
#: The status a gate refusal answers with; any other code is the request's fault, 400.
STATUS: dict[str, int] = {
    "record-not-head": 409,  # a race the second loses, naming the head (F20-Q3)
    "signed-supersede": 403,
    "withdrawal-unauthorized": 403,
}
#: A version a withdrawal names, by its graph path.
RECORD_RE = re.compile(
    r"^targets/(?P<target>[a-z0-9][a-z0-9-]*)/(?:nodes/(?P<node>[a-z0-9][a-z0-9-]*)/)?"
    r"(?P<dir>gloss|explainer)/(?P<hash>[0-9a-f]{64})\.md$"
)
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
#: A definition module's path under ``defs/``: gloss/v1's characters, relative, no empty segment.
MODULE_RE = re.compile(r"^[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*\.lean$")
YAML_SUFFIXES = (".yaml", ".yml")


class HostVerifier:
    """``opn_gate.signer.Signer`` for the service: verifies SSHSIG in Python (``sshsig``), since
    the function has no ``ssh-keygen`` (F06-Q6). It never signs: every signature the network
    counts is made with its signer's own key, never by the service (F20-R10)."""

    def sign(self, payload: bytes, key_path: Path, kind: SignatureKind) -> Signature:
        msg = "the service signs no record: a signature is its signer's own (F20-R10)"
        raise SignerError(msg)

    def verify(self, payload: bytes, signature: str, public_key: str) -> bool:
        try:
            return sshsig.verify(payload, signature, public_key, namespace=NAMESPACE)
        except sshsig.SshsigError:
            return False  # a malformed record counts for nothing (C7)

    def fingerprint(self, public_key: str) -> str:
        try:
            return sshsig.fingerprint(public_key)
        except sshsig.SshsigError as exc:
            raise SignerError(str(exc)) from exc


# --- the scratch tree ----------------------------------------------------------------------------


class _Host:
    """Copies files of the graph at ``main`` into ``root`` under their graph paths. ``lister``
    replaces the uncached listing, for a read tool that lists through its own per-head cache."""

    def __init__(
        self, ctx: Context, root: Path, lister: Callable[[str], list[str]] | None = None
    ) -> None:
        self.ctx = ctx
        self.root = root
        self.lister = lister

    def copy(self, path: str) -> bool:
        body = pending.optional_committed(self.ctx, path)
        if body is None:
            return False
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        return True

    def names(self, directory: str) -> list[str]:
        if self.lister is not None:
            return self.lister(directory)
        settings = self.ctx.settings
        try:
            listed = self.ctx.githost.list_dir(
                settings.graph_repo, settings.graph_branch, directory
            )
        except GitHostError as exc:
            raise ApiError(
                503, "graph-unreachable", f"cannot list {directory} in the graph: {exc}"
            ) from exc
        return list(listed or [])

    def copy_dir(self, directory: str, suffixes: tuple[str, ...]) -> None:
        for name in self.names(directory):
            if name.endswith(suffixes):
                self.copy(f"{directory}/{name}")


def materialise(  # noqa: PLR0913 — the node, and how the host is read for it
    ctx: Context,
    root: Path,
    target_id: str,
    node_id: str | None,
    *,
    lister: Callable[[str], list[str]] | None = None,
    roles: bool = True,
) -> Path:
    """Fill ``root`` with what the gate's gloss, explainer and withdrawal checks read for one
    node (or, ``node_id`` None, the target's definition modules), and answer the target's
    directory. Nothing else of the graph is fetched; without ``roles`` not the stewards and the
    curators either, which only the checks' who-may rules read."""
    host = _Host(ctx, root, lister)
    target = f"targets/{target_id}"
    if roles:
        host.copy(modes.CURATORS_FILE)
        host.copy_dir(f"{target}/stewards", YAML_SUFFIXES)
    if node_id is None:
        host.copy_dir(f"{target}/{glosses.DEFS_DIR}", (".lean",))
        parent = target
    else:
        parent = f"{target}/nodes/{node_id}"
        for name in (*glosses.KIND_FILES.values(), "Proof.lean"):
            host.copy(f"{parent}/{name}")
        host.copy_dir(f"{parent}/attempts", (".lean",))
        host.copy_dir(f"{parent}/{explainers.EXPLAINER_DIR}", (".md",))
        host.copy_dir(f"{parent}/{explainers.EXPLAINER_DIR}/{explainers.SIGNED_DIR}", YAML_SUFFIXES)
    host.copy_dir(f"{parent}/{glosses.GLOSS_DIR}", (".md",))
    host.copy_dir(f"{parent}/{glosses.GLOSS_DIR}/{glosses.SIGNED_DIR}", YAML_SUFFIXES)
    host.copy_dir(f"{parent}/withdrawals", YAML_SUFFIXES)
    target_dir = root / target
    target_dir.mkdir(parents=True, exist_ok=True)
    if node_id is not None:
        for digest in explainers.merged_artifacts(target_dir / "nodes" / node_id):
            host.copy(f"{target}/{explainers.OUTLINES_DIR}/{digest}.json")
    return target_dir


# --- the pre-flight ------------------------------------------------------------------------------


def refuse(problems: list[Diagnostic]) -> NoReturn:
    """The gate's first problem as the refusal, every problem in ``details``."""
    first = problems[0]
    raise ApiError(
        STATUS.get(first.code, 400),
        first.code,
        first.message,
        details={**first.details, "problems": [d.as_dict() for d in problems]},
    )


def preflight(root: Path, path: str, content: bytes, verifier: HostVerifier) -> None:
    """R1 to R7 over the scratch tree with ``path`` added, as the merge would run them on a pull
    request the service opened: refused by the gate's code, or nothing."""
    dest = root / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    try:
        curators = modes.load_curators(root)
    except modes.CuratorsError:
        curators = modes.Curators()
    classification = modes.classify(
        [Change("A", path)],
        author=OPENER,
        curators=curators,
        graph_root=root,
        service_login=OPENER,
    )
    problems = list(classification.problems)
    if classification.ok:
        problems.extend(modes.check(root, classification, signer=verifier))
    if problems:
        refuse(problems)


def check_own_name(identity: Identity, root: Path, target_id: str, verifier: HostVerifier) -> None:
    """F20-T6: the gate reads a service pull request's ``author`` as the person acting, and
    compares it with the target's stewards and the listed curators by login. A pseudonym spelled
    like one of those logins (GitHub logins ignore case) is that person's name, so the service
    writes it only for the identity that proved that very login."""
    real = modes.real_identities(root, target_id, signer=verifier)
    name = identity.pseudonym.casefold()
    if not any(login.casefold() == name for login in real):
        return
    proved = (
        identity.proof_reference.casefold()
        if identity.proof_kind == identitymod.PROOF_GITHUB
        else None
    )
    if proved != name:
        raise ApiError(
            403,
            "author-names-another",
            f"your pseudonym {identity.pseudonym!r} is spelled like the login of an active "
            f"steward of {target_id} or a listed curator, and your identity did not prove that "
            "login; a gloss, explainer or withdrawal you file would read as theirs (F20-T6). "
            "File it under an identity whose pseudonym names nobody else",
            details={"pseudonym": identity.pseudonym, "target_id": target_id},
        )


# --- POST /glosses -------------------------------------------------------------------------------


def subject_of(raw: Any) -> dict[str, Any]:
    """The ``subject`` object, its keys within ``SUBJECT_KEYS`` and its kind one of the five."""
    if not isinstance(raw, dict):
        raise ApiError(
            400,
            "subject-invalid",
            "subject is an object: {kind, node_id} for a statement, witness or relation; "
            "{kind: definition, target_id, module} for a definition module; {kind: proof, "
            "node_id, proof} for an explainer of a merged proof artifact",
        )
    unknown = sorted(k for k in raw if k not in SUBJECT_KEYS)
    if unknown:
        raise ApiError(
            400,
            "subject-invalid",
            f"subject holds {', '.join(unknown)}; it holds only {', '.join(SUBJECT_KEYS)} — "
            "the author of a version is the token's identity, never the request's",
            details={"unknown": unknown, "accepted": list(SUBJECT_KEYS)},
        )
    kind = raw.get("kind")
    if kind not in (*GLOSS_KINDS, PROOF_KIND):
        raise ApiError(
            400,
            "subject-invalid",
            f"subject.kind is one of {', '.join((*GLOSS_KINDS, PROOF_KIND))}",
            details={"kind": kind},
        )
    for key in ("node_id", "target_id", "module", "proof", "lean_hash"):
        value = raw.get(key)
        if value is not None and not isinstance(value, str):
            raise ApiError(400, "subject-invalid", f"subject.{key} is a string")
    if kind == PROOF_KIND and not HASH_RE.match(str(raw.get("proof") or "")):
        raise ApiError(
            400,
            "subject-invalid",
            "an explainer's subject names the merged artifact it describes: subject.proof is "
            "its SHA-256 (64 lowercase hex characters), as get_node's outlines list them",
        )
    return dict(raw)


def where(ctx: Context, subject: dict[str, Any]) -> tuple[str, str | None]:
    """``(target, node)`` of the subject: a node's (404 ``node-unknown`` when the products do
    not list it), or for a definition module its target's (404 ``target-unknown``)."""
    if subject["kind"] == glosses.DEFINITION:
        target_id = appends.known_target(ctx, subject.get("target_id"))
        if not MODULE_RE.match(str(subject.get("module") or "")):
            # Checked before the module is read, so a path cannot leave the target's defs/.
            raise ApiError(
                400,
                "subject-invalid",
                "a definition's subject names its module by its path under defs/ (letters, "
                "digits and _, segments joined by /, ending .lean)",
            )
        return target_id, None
    node_id, target_id = appends.node_target(ctx, {"node_id": subject.get("node_id")})
    named = subject.get("target_id")
    if named is not None and named != target_id:
        raise ApiError(
            400,
            "subject-invalid",
            f"{node_id} is a node of {target_id}, not of {named}",
            details={"node_id": node_id, "target_id": target_id},
        )
    return target_id, node_id


def text_of(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ApiError(400, "text-missing", "text is required: the prose, as Markdown")
    if len(raw.encode()) > TEXT_MAX_BYTES:
        raise ApiError(
            400,
            "field-too-long",
            f"the text is {len(raw.encode())} bytes; the cap is {TEXT_MAX_BYTES}",
        )
    return raw


def front_matter(  # noqa: PLR0913 — one argument per fact the record carries
    target_dir: Path,
    subject: dict[str, Any],
    *,
    target_id: str,
    node_id: str | None,
    supersedes: Any,
    author: str,
    date: str,
    licence: str,
) -> tuple[dict[str, Any], str]:
    """``(front matter, schema)`` of the record: ``gloss/v1`` or ``explainer/v1``."""
    common = {"supersedes": supersedes, "author": author, "drafter": None}
    if subject["kind"] == PROOF_KIND:
        doc = {
            "schema": explainers.RECORD_SCHEMA,
            "target": target_id,
            "node": node_id,
            "proof": subject["proof"],
            **common,
            "date": date,
            "licence": licence,
        }
        return doc, explainers.RECORD_SCHEMA
    module = subject.get("module") if node_id is None else None
    file = glosses.subject_file(
        target_dir, {"kind": subject["kind"], "node": node_id, "module": module}
    )
    lean_hash = subject.get("lean_hash")
    if lean_hash is None:
        # The file as it stands. One that is not there is named by the gate (the empty text's
        # hash stands in, and gloss-subject-unknown is checked before the hash is).
        found = file.read_bytes() if file is not None and file.is_file() else b""
        lean_hash = schemas.content_hash(found)
    doc = {
        "schema": glosses.SCHEMA,
        "target": target_id,
        "subject": {
            "kind": subject["kind"],
            "node": node_id,
            "module": module,
            "lean_hash": lean_hash,
        },
        **common,
        "date": date,
        "licence": licence,
    }
    return doc, glosses.SCHEMA


def record_file(front: dict[str, Any], text: str) -> str:
    """The file as it lands: the front matter, then the prose exactly as sent (R14)."""
    head = yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
    body = text if text.endswith("\n") else text + "\n"
    return f"---\n{head}---\n{body}"


async def post_glosses(ctx: Context, request: Request) -> Response:
    """R10: a gloss of a statement, witness, relation or definition module, or an explainer of a
    merged proof artifact; new, or superseding the head of its chain."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, GLOSS_FIELDS)
    subject = subject_of(fields.get("subject"))
    target_id, node_id = where(ctx, subject)
    text = text_of(fields.get("text"))
    licence = appends.check_licence(fields.get("licence"))
    supersedes = fields.get("supersedes")
    record = "explainer" if subject["kind"] == PROOF_KIND else "gloss"
    with tempfile.TemporaryDirectory(prefix="opn-gloss-") as tmp:
        root = Path(tmp)
        target_dir = materialise(ctx, root, target_id, node_id)
        verifier = HostVerifier()
        check_own_name(identity, root, target_id, verifier)
        front, schema = front_matter(
            target_dir,
            subject,
            target_id=target_id,
            node_id=node_id,
            supersedes=supersedes,
            author=identity.pseudonym,
            date=ctx.clock.now().strftime("%Y-%m-%d"),
            licence=licence,
        )
        appends.validated(front, schema)
        content = record_file(front, text)
        digest = schemas.content_hash(content.encode())
        parent = f"targets/{target_id}/" + (f"nodes/{node_id}/" if node_id else "")
        directory = explainers.EXPLAINER_DIR if record == "explainer" else glosses.GLOSS_DIR
        path = f"{parent}{directory}/{digest}.md"
        preflight(root, path, content.encode(), verifier)
    owner = node_id or subject.get("module") or target_id
    written = yaml.safe_dump(
        {"subject": front.get("subject") or front.get("proof"), "supersedes": supersedes},
        sort_keys=True,
    )
    body = appends.append_pr(
        ctx,
        identity,
        path=path,
        content=content,
        subject=f"{record}: {owner} {subject['kind']}",
        what=record,
        kind=record,
        target_id=target_id,
        node_id=node_id,
        written=written + text,
    )
    body |= {"hash": digest, "record": record}
    if record == "gloss":
        body["lean_hash"] = front["subject"]["lean_hash"]
    return JSONResponse(body, status_code=201)


# --- POST /glosses/withdrawals -------------------------------------------------------------------


async def post_withdrawals(ctx: Context, request: Request) -> Response:
    """R7, R10: a ``withdrawal/v2`` record taking one gloss or explainer version out of its chain;
    the file stays in the tree and every reader reads it as absent."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, WITHDRAWAL_FIELDS)
    raw = fields.get("record")
    m = RECORD_RE.match(raw) if isinstance(raw, str) else None
    if m is None or (m.group("dir") == explainers.EXPLAINER_DIR and m.group("node") is None):
        raise ApiError(
            400,
            "record-invalid",
            "record is the graph path of one version: targets/<id>/nodes/<node>/gloss/<hash>.md, "
            "targets/<id>/nodes/<node>/explainer/<hash>.md, or targets/<id>/gloss/<hash>.md for "
            "a definition module's gloss",
            details={"record": raw},
        )
    target_id, node_id = m.group("target"), m.group("node")
    if node_id is not None:
        _, found = appends.node_target(ctx, {"node_id": node_id})
        if found != target_id:
            raise ApiError(
                400,
                "record-invalid",
                f"{node_id} is a node of {found}, not of {target_id}",
                details={"record": raw},
            )
    else:
        appends.known_target(ctx, target_id)
    doc = {
        "schema": WITHDRAWAL_SCHEMA,
        "withdraws": f"{m.group('dir')}/{m.group('hash')}.md",
        "reason": fields.get("reason"),
        "author": identity.pseudonym,
        "date": ctx.clock.now().strftime("%Y-%m-%d"),
    }
    appends.validated(doc, WITHDRAWAL_SCHEMA)
    parent = f"targets/{target_id}/" + (f"nodes/{node_id}/" if node_id else "")
    path = f"{parent}withdrawals/{appends.record_name(ctx, identity)}.yaml"
    content = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    with tempfile.TemporaryDirectory(prefix="opn-gloss-") as tmp:
        root = Path(tmp)
        materialise(ctx, root, target_id, node_id)
        verifier = HostVerifier()
        check_own_name(identity, root, target_id, verifier)
        preflight(root, path, content.encode(), verifier)
    body = appends.append_pr(
        ctx,
        identity,
        path=path,
        content=content,
        subject=f"withdrawal: {raw}",
        what="withdrawal",
        kind="gloss-withdrawal",
        target_id=target_id,
        node_id=node_id,
        written=str(raw),
    )
    return JSONResponse(body | {"withdraws": raw}, status_code=201)


# --- get_node's chains, when the graph has no glosses.json yet (F10-Q7) --------------------------


def node_glosses(
    ctx: Context, target_id: str, node_id: str, lister: Callable[[str], list[str]]
) -> list[dict[str, Any]]:
    """The ``glosses/v1`` subjects of one node, derived from its files at ``main`` by the gate's
    own function (``products.glosses_doc``), as the committed product would carry them. The
    read tool lists through its own cache (``lister``), so a read costs the App's budget once
    per head (F07-T68)."""
    with tempfile.TemporaryDirectory(prefix="opn-gloss-") as tmp:
        root = Path(tmp)
        target_dir = materialise(ctx, root, target_id, node_id, lister=lister, roles=False)
        scope = products.GlossScope(
            target_id, target_dir, {node_id: target_dir / "nodes" / node_id}
        )
        doc = products.glosses_doc(scope, None, signer=HostVerifier())
    return [s for s in doc["subjects"] if s["node"] == node_id]
