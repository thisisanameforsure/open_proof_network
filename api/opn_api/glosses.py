"""The gloss routes (F20-R10, R11; D-3 v3.30, D-28, D-35): ``POST /glosses`` and
``POST /glosses/withdrawals``.

A gloss is prose saying what one Lean file says; an explainer is prose about one merged proof
artifact; a withdrawal takes one version of either out of its chain. All three are appends that
claim nothing a kernel checks, so the service opens them as ``append/`` pull requests the merge
actor merges, as it does an annex. Two rules hold every one:

* **The caller supplies the words, the service supplies the identity** (F07-R11; F18-Q7(a)). The
  record (``gloss/v2`` or ``explainer/v2`` since F21-R6, with the caller's ``drafted_with`` naming
  any model that drafted the words, null otherwise) has as its ``author`` the token's pseudonym
  and nothing the body says; its ``date`` is today;
  a gloss or explainer is named by the hash of the file as it lands (D-3), and placed where its
  subject puts it — ``nodes/<id>/gloss/``, ``targets/<id>/gloss/`` for a definition module,
  ``nodes/<id>/explainer/`` for a proof. Every such pull request is authored by the service's
  App, so the gate judges who is acting from that ``author`` (``modes.acting_names``, F20-T6).
* **Refused before anything opens** (the owner's ruling of 2026-09-24, F13-T21): the gate's own
  classifier and checks (R1 to R7) run over a scratch tree holding exactly the files they read —
  the subject, the node's versions, signatures and withdrawals, the outlines, the stewards and
  the curators, fetched from the graph at ``main`` — with the new file added, and the first
  problem is the refusal, by the gate's code, with no branch pushed and no pull request opened.
  The gate checks it again at the merge. That includes F21-R12's model lock: a version naming
  ``drafted_with`` that changes a section a person wrote or a steward verified is refused 409
  ``locked-by-a-person`` here, naming the section and its Lean lines (``STATUS``).

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
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, duplicates, frontier, pending, sshsig, submissions
from opn_api import clock as clockmod
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_api.githost import GitHostError
from opn_gate import config as gate_config
from opn_gate import explainers, glosses, modes, products, schemas
from opn_gate import sections as sectionsmod
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change
from opn_gate.signer import NAMESPACE, Signature, SignatureKind, SignerError
from opn_site import prose

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity, Submission

log = logging.getLogger(__name__)

#: F05-T8: the fields each route reads; any other top-level key is refused. ``drafted_with``
#: (F21-R6, D-23) names the model and tooling that drafted the words, in the caller's words.
#: F22-T5: ``dry_run`` runs the whole pre-flight and opens nothing. F22-T6: ``amends`` names an
#: open words submission of the caller's whose version this one replaces, in place.
GLOSS_FIELDS: tuple[str, ...] = (
    "subject",
    "text",
    "supersedes",
    "licence",
    "drafted_with",
    "dry_run",
    "amends",
)
#: F21-R6: the record versions the service writes — v1 plus ``drafted_with`` — always, with the
#: field null when the request names no model. The gate keeps reading v1 (D-34), and its own
#: ``glosses.SCHEMA`` and ``explainers.RECORD_SCHEMA`` stay the v1 strings its readers compare
#: against; these two are what lands.
GLOSS_SCHEMA = "gloss/v2"
EXPLAINER_SCHEMA = "explainer/v2"
#: D-23's cap on a declared model and tooling, as ``gloss/v2`` and ``explainer/v2`` publish it.
DRAFTED_WITH_MAX_CHARS = 200
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
#: F21-R13 withdrew ``signed-supersede`` (anyone may supersede; a change to verified words is
#: pending). ``locked-by-a-person`` (F21-R12) is 409, a conflict with the chain's present state
#: as ``record-not-head`` is: the caller is allowed to file, but these words conflict with what a
#: person wrote, and the same request with that section kept (or as one's own words) succeeds.
#: The section rules are the request's fault, 400, named so the table reads whole.
STATUS: dict[str, int] = {
    "record-not-head": 409,  # a race the second loses, naming the head (F20-Q3)
    "locked-by-a-person": 409,
    "section-duplicate": 400,
    "signature-section-unknown": 400,
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
#: F22-T6: the version a words submission carries, recorded beside its subject keys so an
#: amendment can say which version it replaced.
VERSION_PRINT = "version:"


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


def preflight(root: Path, path: str, content: bytes, verifier: HostVerifier) -> list[Diagnostic]:
    """R1 to R7 over the scratch tree with ``path`` added, as the merge would run them on a pull
    request the service opened: refused by the gate's code, or the gate's warnings (F22-T4).

    The warnings are ``modes.warnings`` over the same tree and the same classification the gate
    makes at the merge (F20-R5: never a refusal), so the writer reads in the answer what only
    the Actions log said before (testers 2026-10-06, request A)."""
    problems = modes.check_as_service(root, path, content, service_login=OPENER, signer=verifier)
    if problems:
        refuse(problems)
    try:
        curators = modes.load_curators(root)
    except modes.CuratorsError:
        curators = modes.Curators()
    # the classification check_as_service made, made again: it does not hand it back
    classification = modes.classify(
        [Change("A", path)],
        author=OPENER,
        curators=curators,
        graph_root=root,
        service_login=OPENER,
    )
    return modes.warnings(root, classification)


def warnings_note(found: list[Diagnostic]) -> str:
    """The pull request's lines for the gate's warnings (F22-T4): none when there are none."""
    if not found:
        return ""
    lines = "".join(f"- `{w.code}`: {w.message}\n" for w in found)
    return f"\nThe gate warns, without refusing (F20-R5):\n\n{lines}"


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
    drafted_with: str | None = None,
) -> tuple[dict[str, Any], str]:
    """``(front matter, schema)`` of the record: ``gloss/v2`` or ``explainer/v2`` (F21-R6). The
    author is always a person, the token's identity; the service files no draft (F21-R1), so
    ``drafter`` is always null, and a model that helped is named in ``drafted_with``."""
    common = {"supersedes": supersedes, "author": author, "drafter": None}
    if subject["kind"] == PROOF_KIND:
        doc = {
            "schema": EXPLAINER_SCHEMA,
            "target": target_id,
            "node": node_id,
            "proof": subject["proof"],
            **common,
            "date": date,
            "licence": licence,
            "drafted_with": drafted_with,
        }
        return doc, EXPLAINER_SCHEMA
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
        "schema": GLOSS_SCHEMA,
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
        "drafted_with": drafted_with,
    }
    return doc, GLOSS_SCHEMA


def record_file(front: dict[str, Any], text: str) -> str:
    """The file as it lands: the front matter, then the prose exactly as sent (R14)."""
    head = yaml.safe_dump(front, sort_keys=False, allow_unicode=True)
    body = text if text.endswith("\n") else text + "\n"
    return f"---\n{head}---\n{body}"


def words_key(target_id: str, node_id: str | None, subject: dict[str, Any]) -> str:
    """F21-Q5: the subject's key, ``words:<target>:<file-or-proof-hash>`` — an explainer's proof
    hash, or a gloss's Lean file relative to its target (``nodes/<id>/Statement.lean``,
    ``defs/<module>``)."""
    if subject["kind"] == PROOF_KIND:
        return duplicates.words_key(target_id, str(subject["proof"]))
    module = subject.get("module") if node_id is None else None
    file = glosses.subject_file(
        Path(), {"kind": subject["kind"], "node": node_id, "module": module}
    )
    return duplicates.words_key(target_id, file.as_posix() if file is not None else "")


def dry_run_of(raw: Any) -> bool:
    """F22-T5: ``dry_run`` is a boolean, absent meaning false. Anything else is the catalogued
    ``arguments-invalid``, naming the field (a code of its own would need a catalog row)."""
    if raw is None:
        return False
    if not isinstance(raw, bool):
        raise ApiError(
            400,
            "arguments-invalid",
            "dry_run is true or false",
            details={"field": "dry_run"},
        )
    return raw


def dry_sections(target_dir: Path, subject: dict[str, Any], text: str) -> list[dict[str, Any]]:
    """F22-T5: each section of the words as the gate keys it (``opn_gate.sections``): a gloss is
    one ``whole``; an explainer's sections are ``overview`` and ``steps:<ids>``, each with the
    steps its heading names and what they resolve to in the proof's outline (``id``, ``kind``,
    ``name`` and the Lean ``lines`` they span). ``resolved`` is null where nothing can resolve: a
    gloss, or a proof with no outline yet. The text has passed the pre-flight, so every named
    step is in the outline when there is one."""
    if subject["kind"] != PROOF_KIND:
        return [{"key": sectionsmod.WHOLE, "steps": [], "resolved": None}]
    outline = explainers.outline_of(target_dir, str(subject["proof"]))
    steps = explainers.outline_steps(outline) if outline is not None else None
    found = explainers.sections(text)
    if not any(s.steps for s in found):
        found = [explainers.Section("", (), text)]  # the gate reads it as one overview
    out: list[dict[str, Any]] = []
    for section in found:
        resolved: list[dict[str, Any]] | None = None
        if steps is not None:
            resolved = []
            for step_id in section.steps:
                step = steps.get(step_id)
                if step is None:
                    continue
                span = step.get("span") or {}
                resolved.append(
                    {
                        "id": step_id,
                        "kind": step.get("kind"),
                        "name": step.get("name"),
                        "lines": [span.get("start_line"), span.get("end_line")],
                    }
                )
        out.append(
            {
                "key": sectionsmod.key_of(section.steps),
                "steps": list(section.steps),
                "resolved": resolved,
            }
        )
    return out


def preview_html(text: str) -> str:
    """F22-T5: the words as the site renders prose, by the site's own renderer (``opn_site.prose``,
    packaged with the function): escaped, math marked for the page's renderer."""
    return prose.render(text, math=True)


def amended_submission(ctx: Context, identity: Identity, raw: Any) -> Submission:
    """F22-T6: the open words submission ``amends`` names, which must be the caller's own. Every
    refusal is a catalogued code: an id that is not one (``submission-id-invalid``), not the
    service's (``submission-unknown``), not a gloss or explainer (``subject-invalid``), another
    identity's (``not-holder``), merged (``submission-merged``) or closed
    (``submission-unknown``). Open-ness is read fresh, as ``GET /submissions/{id}`` reads it."""
    if not isinstance(raw, str | int) or isinstance(raw, bool):
        raise ApiError(
            400,
            "submission-id-invalid",
            "amends is the id POST /glosses answered (a ULID) or the pull-request number",
        )
    submission_id, number = pending.parse_id(str(raw))
    found = (
        ctx.store.get_submission(submission_id)
        if submission_id is not None
        else ctx.store.get_submission_by_pr(number or 0)
    )
    if found is None:
        raise pending.unknown(str(raw))
    if found.kind not in duplicates.WORDS_KINDS:
        raise ApiError(
            400,
            "subject-invalid",
            f"amends names a {found.kind} pull request (#{found.pr_number}); only a gloss's or "
            "an explainer's words are amended",
            details={"amends": found.id, "kind": found.kind},
        )
    if found.pseudonym.casefold() != identity.pseudonym.casefold():
        raise ApiError(
            403,
            "not-holder",
            f"pull request #{found.pr_number} is {found.pseudonym}'s; only its author amends it",
            details={"amends": found.id, "pr_number": found.pr_number},
        )
    frontier.pin_head(ctx)
    pending.open_listing(ctx)
    found, pull, _error = pending.reconcile(ctx, found)
    if found.closed is not None:
        merged = bool((pull or {}).get("merged"))
        raise ApiError(
            409 if merged else 404,
            "submission-merged" if merged else "submission-unknown",
            f"pull request #{found.pr_number} has "
            + (
                "merged: supersede the version it added instead"
                if merged
                else "closed: file the words anew"
            ),
            details={"amends": found.id, "pr_number": found.pr_number},
        )
    return found


def check_amended_subject(found: Submission, words: str) -> None:
    """F22-T6: an amendment writes the same subject as the pull request it amends."""
    if words not in found.fingerprints:
        raise ApiError(
            400,
            "subject-invalid",
            f"pull request #{found.pr_number} writes the words for another subject; an "
            "amendment replaces words for the same file or proof",
            details={"amends": found.id, "pr_number": found.pr_number, "subject": words},
        )


def amend(  # noqa: PLR0913 — one amended pull request, described
    ctx: Context,
    identity: Identity,
    found: Submission,
    *,
    path: str,
    content: str,
    subject_line: str,
    prints: list[str],
) -> dict[str, Any]:
    """F22-T6: move the amended pull request's own branch to one commit from ``main`` adding the
    new version, so the old one is gone from it, and keep the pull request (its number and its
    place in the queue); the gate runs again on the new head. The pull request says first which
    version is replaced by which (trackable; a comment that fails is logged and moves nothing
    less). The record keeps its id and takes the new fingerprints."""
    settings = ctx.settings
    now = clockmod.render(ctx.clock.now())
    old = next(
        (p.removeprefix(VERSION_PRINT) for p in found.fingerprints if p.startswith(VERSION_PRINT)),
        None,
    )
    new = path.rsplit("/", 1)[-1].removesuffix(".md")
    note = (
        f"Amended by its author `{identity.pseudonym}` (F22-T6): this branch now carries "
        f"`{path}` (`{new}`), one commit from `{settings.graph_branch}`"
        + (f", in place of `{old}`." if old else ".")
    )
    try:
        ctx.githost.comment_on_pull_request(settings.graph_repo, found.pr_number, note)
    except GitHostError as exc:
        log.warning("amend #%d: no comment posted: %s", found.pr_number, exc)
    try:
        head = ctx.githost.push_branch(
            settings.graph_repo,
            submissions.APPEND_BRANCH_PREFIX + found.id,
            {path: content},
            base=settings.graph_branch,
            message=f"{subject_line}\n\n{submissions.sign_off(identity)}\n",
            author=submissions.author_for(identity, now),
            committer=submissions.committer_for(ctx, now),
            replace=True,
        )
    except GitHostError as exc:
        log.warning("amend #%d: branch not moved: %s", found.pr_number, exc)
        raise ApiError(
            502,
            "pull-request-failed",
            f"pull request #{found.pr_number} could not be amended; it is as it was: {exc}",
        ) from exc
    ctx.pulls.pop(found.pr_number, None)  # its head moved: read it afresh next time
    try:
        ctx.store.put_submission(replace(found, fingerprints=tuple(prints)))
    except Exception as exc:  # any store failure: the branch moved regardless (C7)
        log.error("amend #%d: record not updated: %s", found.pr_number, type(exc).__name__)
    return {
        "id": found.id,
        "path": path,
        "pr_url": found.pr_url,
        "pr_number": found.pr_number,
        "head_sha": head,
        "amended": True,
    }


def one_writer(
    ctx: Context, words: str, supersedes: Any, *, exclude: int | None
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """F21-R5, F22-T1: the one-writer rule for the request, and ``(slots, prints)``: the keys it
    holds while its pull request opens and records with it. A new chain waits for the writer at
    work on its subject; a superseding version for the writer at work on its head. ``exclude``
    is the pull request being amended (F22-T6)."""
    if supersedes is None:
        duplicates.check_words(ctx, words, exclude=exclude)
        return (words,), (words,)
    head_key = duplicates.supersedes_key(words, str(supersedes))
    duplicates.check_supersession(ctx, head_key, str(supersedes), exclude=exclude)
    return (head_key,), (words, head_key)


def receipt(
    body: dict[str, Any], digest: str, front: dict[str, Any], warned: list[Diagnostic]
) -> dict[str, Any]:
    """The answer to a filed version: the pull request, the file's hash, the record kind, the
    gate's warnings (F22-T4) and, for a gloss, the hash of the Lean text it describes."""
    record = "explainer" if front["schema"] == EXPLAINER_SCHEMA else "gloss"
    body |= {"hash": digest, "record": record, "warnings": [w.as_dict() for w in warned]}
    if record == "gloss":
        body["lean_hash"] = front["subject"]["lean_hash"]
    return body


async def post_glosses(ctx: Context, request: Request) -> Response:
    """R10: a gloss of a statement, witness, relation or definition module, or an explainer of a
    merged proof artifact; new, or superseding the head of its chain."""
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, GLOSS_FIELDS)
    subject = subject_of(fields.get("subject"))
    target_id, node_id = where(ctx, subject)
    text = text_of(fields.get("text"))
    licence = appends.check_licence(
        fields.get("licence"), licensed="a gloss or explainer is licensed"
    )
    supersedes = fields.get("supersedes")
    drafted_with = appends.declared(
        fields.get("drafted_with"), "drafted_with", cap=DRAFTED_WITH_MAX_CHARS
    )
    dry_run = dry_run_of(fields.get("dry_run"))
    amended = (
        amended_submission(ctx, identity, fields["amends"])
        if fields.get("amends") is not None
        else None
    )
    exclude = amended.pr_number if amended is not None else None
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
            drafted_with=drafted_with,
        )
        appends.validated(front, schema)
        content = record_file(front, text)
        digest = schemas.content_hash(content.encode())
        parent = f"targets/{target_id}/" + (f"nodes/{node_id}/" if node_id else "")
        directory = explainers.EXPLAINER_DIR if record == "explainer" else glosses.GLOSS_DIR
        path = f"{parent}{directory}/{digest}.md"
        warned = preflight(root, path, content.encode(), verifier)
        sections = dry_sections(target_dir, subject, text) if dry_run else []
    # F21-R5: after the gate's own refusals, as the copy rule is (appends.append_pr): a new chain
    # waits for the writer already at work on its subject; a superseding version does not.
    words = words_key(target_id, node_id, subject)
    if amended is not None:
        check_amended_subject(amended, words)
    slots, prints = one_writer(ctx, words, supersedes, exclude=exclude)
    owner = node_id or subject.get("module") or target_id
    written = yaml.safe_dump(
        {"subject": front.get("subject") or front.get("proof"), "supersedes": supersedes},
        sort_keys=True,
    )
    if dry_run:
        # F22-T5: every check a real request meets, the copy rule included, and nothing taken:
        # no slot, no branch, no pull request, no record
        duplicates.check_append(ctx, record, owner, written + text)
        return JSONResponse(
            {
                "ok": True,
                "dry_run": True,
                "record": record,
                "path": path,
                "hash": digest,
                "warnings": [w.as_dict() for w in warned],
                "sections": sections,
                "preview_html": preview_html(text),
            }
        )
    if amended is not None:
        fingerprint = duplicates.fingerprint(written + text)
        body = amend(
            ctx,
            identity,
            amended,
            path=path,
            content=content,
            subject_line=f"{record}: {owner} {subject['kind']} (amended)",
            prints=[fingerprint, *prints, VERSION_PRINT + digest],
        )
        return JSONResponse(receipt(body, digest, front, warned))
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
        subject_prints=(*prints, VERSION_PRINT + digest),
        subject_slots=slots,
        extra_body=warnings_note(warned),
    )
    return JSONResponse(receipt(body, digest, front, warned), status_code=201)


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
    """The ``glosses/v2`` subjects of one node, derived from its files at ``main`` by the gate's
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
