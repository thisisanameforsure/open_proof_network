"""The post-merge job's pure parts (F00-R14, Q4, Q8; C8 item 1).

After a pull request merges to ``main``, a separate job re-runs the gate on the merge commit,
fills ``merge_commit`` and the step-9 ``review`` block (D-4 v3.11: the tutorial exemption, a
non-author PR approval, or the statement's certificate/provenance), signs the record with the
gate key, and commits it to
``attestations/<id>.json``. Everything here is testable without GitHub: the workflow only feeds
it the merge commit, the pull-request number, the reviews list and the key path.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from opn_gate import attestation, schemas
from opn_gate import graph as graphmod
from opn_gate.diagnostic import Diagnostic
from opn_gate.signer import Signer

log = logging.getLogger(__name__)

ID_WIDTH = 6
_MERGE_RE = re.compile(r"^Merge pull request #(?P<n>\d+)\b")
_SQUASH_RE = re.compile(r"\(#(?P<n>\d+)\)\s*$", re.M)
WAIVER_LINE = "waiver: native_decide"  # F02-R9: what the approving review must say
_WAIVER_LINE_RE = re.compile(r"^\s*" + re.escape(WAIVER_LINE) + r"\s*$", re.M)


def approval_names_waiver(body: str) -> bool:
    """True when a review body contains the line ``waiver: native_decide`` (F02-R9)."""
    return bool(_WAIVER_LINE_RE.search(body or ""))


def check_waiver(doc: dict[str, Any], approval_bodies: Sequence[str]) -> Diagnostic | None:
    """F02-R9: a waived proof (``trust_base: compiler``) merges only if the approving review
    names the waiver; otherwise the post-merge job refuses with this diagnostic."""
    if doc.get("trust_base") != attestation.TRUST_COMPILER:
        return None
    if any(approval_names_waiver(b) for b in approval_bodies):
        return None
    return Diagnostic(
        "waiver-unapproved",
        "the proof used native_decide under a waiver, but no approving review names it; the "
        f"reviewer must include the line `{WAIVER_LINE}` in the approval",
        {"required_line": WAIVER_LINE, "approvals_seen": len(approval_bodies)},
    )


#: F15-R12: the bot commit may carry ``· cc @login …`` after the verdict — one mention per active
#: steward of the target, each a login the grammar admits, and nothing else from the records.
MENTION_SEPARATOR = " · cc "
_BOT_MESSAGE_RE = re.compile(
    r"^gate: #(?P<n>\d+) (?P<verdict>pass|fail)"
    r"(?: · cc (?P<cc>@[A-Za-z0-9-]+(?: @[A-Za-z0-9-]+)*))?$"
)
PRODUCT_FILES: tuple[str, ...] = ("frontier.json", "info.json", "targets/index.json")
CLAIMS_FILE = "claims.json"
CLAIMS_TIMEOUT_S = 10


def fetch_claims_snapshot(url: str, *, opener: Callable[[str, int], bytes] | None = None) -> bytes:
    """F05-R10: ``GET /claims.json`` from the service, as raw bytes.

    Raises ``OSError`` or ``ValueError`` on any failure; the caller falls back (C7).
    """
    if not url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        msg = f"the claims endpoint must be https (or a local runner): {url}"
        raise ValueError(msg)
    if opener is not None:
        return opener(url, CLAIMS_TIMEOUT_S)
    request = urllib.request.Request(url, headers={"User-Agent": "opn-gate"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=CLAIMS_TIMEOUT_S) as resp:  # noqa: S310
        body: bytes = resp.read()
    return body


def refresh_claims(
    graph_root: Path, url: str | None, *, opener: Callable[[str, int], bytes] | None = None
) -> str | None:
    """Write ``claims.json`` from the service, keeping the committed one on any failure.

    Returns ``None`` when the snapshot was refreshed, else the reason the previous file stands
    (F05-R10, AC16: the service is never allowed to block a merge).
    """
    if not url:
        return "no claims endpoint configured"
    try:
        body = fetch_claims_snapshot(url, opener=opener)
        doc = schemas.validate(json.loads(body), "claims/v1")
    except (OSError, ValueError, schemas.SchemaError) as exc:
        reason = f"{type(exc).__name__}: {exc}"
        log.warning(
            "claims snapshot unavailable (%s); keeping the committed %s", reason, CLAIMS_FILE
        )
        return reason
    (graph_root / CLAIMS_FILE).write_bytes(schemas.canonical_json(doc))
    return None


def mention_line(stewards: Sequence[str]) -> str:
    """F15-R12: the suffix that mentions each active steward, or ``""`` when there is none. A
    login outside GitHub's grammar is refused (``ValueError``): the gate refused its record
    upstream, so one reaching here is a defect, not a mention."""
    from opn_gate import steward  # noqa: PLC0415 — the grammar has one home

    logins: list[str] = []
    for login in stewards:
        if not steward.LOGIN_RE.match(login):
            msg = f"{login!r} is not a GitHub login; a steward record with it was refused (F15-R1)"
            raise ValueError(msg)
        if login not in logins:
            logins.append(login)
    return MENTION_SEPARATOR + " ".join(f"@{login}" for login in logins) if logins else ""


def bot_commit_message(pr_number: int, verdict: str, stewards: Sequence[str] = ()) -> str:
    """F03-R12: the one bot commit carrying the attestation and every product; F15-R12: with
    each active steward of the target mentioned after the verdict."""
    if verdict not in ("pass", "fail"):
        msg = f"a bot commit records pass or fail, not {verdict!r}"
        raise ValueError(msg)
    return f"gate: #{attestation_id(pr_number).lstrip('0') or '0'} {verdict}" + mention_line(
        stewards
    )


def parse_bot_commit_message(message: str) -> tuple[int, str] | None:
    """The (pr, verdict) a bot commit's first line names, or ``None`` for any other commit."""
    first = message.splitlines()[0] if message else ""
    m = _BOT_MESSAGE_RE.match(first)
    return (int(m.group("n")), m.group("verdict")) if m else None


def mentioned_in(message: str) -> tuple[str, ...]:
    """The logins a bot commit's first line mentions, in order; ``()`` for none."""
    first = message.splitlines()[0] if message else ""
    m = _BOT_MESSAGE_RE.match(first)
    if m is None or not m.group("cc"):
        return ()
    return tuple(part[1:] for part in m.group("cc").split())


def attestation_id(pr_number: int) -> str:
    """Q8: the merged PR number, zero-padded, unique per graph repo and human-readable."""
    if pr_number <= 0:
        msg = f"pull request number must be positive, got {pr_number}"
        raise ValueError(msg)
    return f"{pr_number:0{ID_WIDTH}d}"


def attestation_path(graph_root: Path, pr_number: int) -> Path:
    return graph_root / "attestations" / f"{attestation_id(pr_number)}.json"


def pr_number_from_message(message: str) -> int | None:
    """The PR number a merge commit's message names (merge commits and squash merges)."""
    first = message.splitlines()[0] if message else ""
    m = _MERGE_RE.match(first)
    if m:
        return int(m.group("n"))
    m = _SQUASH_RE.search(first)
    return int(m.group("n")) if m else None


def approving_reviewer(reviews: list[dict[str, Any]], author: str) -> str | None:
    """D-4 step 9: the latest APPROVED review by an identity other than the author."""
    approved = [
        r
        for r in reviews
        if r.get("state") == "APPROVED" and (r.get("user") or {}).get("login") not in (None, author)
    ]
    if not approved:
        return None
    approved.sort(key=lambda r: str(r.get("submitted_at", "")))
    login = approved[-1]["user"]["login"]
    return str(login)


ReviewKind = Literal[
    "tutorial", "pr-approval", "certificate", "provenance", "intermediate", "calibration"
]


def review_block(
    kind: ReviewKind, *, reviewer: str | None = None, reference: str | None = None
) -> dict[str, Any]:
    """The step-9 record (D-4 v3.11): what stood behind the merge."""
    if kind == "pr-approval" and not reviewer:
        msg = "a pr-approval review needs the approving reviewer's identity"
        raise ValueError(msg)
    if kind in ("certificate", "provenance") and not reference:
        msg = f"a {kind} review needs a reference"
        raise ValueError(msg)
    if kind in ("intermediate", "calibration") and (reviewer or reference):
        # D-4 v3.20: nobody was asked, so nobody is named — the record must not read otherwise.
        msg = f"a step 9 that was not asked ({kind}) names no reviewer and no reference"
        raise ValueError(msg)
    return {"kind": kind, "reviewer": reviewer, "reference": reference}


def record_step9(
    doc: dict[str, Any], *, merge_commit: str, review: dict[str, Any]
) -> dict[str, Any]:
    """Fill the post-merge fields; the record stays unsigned until ``sign_gate``."""
    out = dict(doc)
    out["runner"] = "hosted"
    out["merge_commit"] = merge_commit
    out["review"] = review
    return schemas.validate(out, attestation.SCHEMA)


def sign_gate(doc: dict[str, Any], *, key_path: Path, signer: Signer) -> dict[str, Any]:
    """Sign with the gate key (signature kind ``gate``); the seal time is kept."""
    out = dict(doc)
    sig = signer.sign(attestation.signed_bytes(out), key_path, "gate")
    out["signature"] = {
        "kind": "gate",
        "key_id": sig.key_id,
        "value": sig.value,
        "timestamp": doc["signature"]["timestamp"],
    }
    return schemas.validate(out, str(doc["schema"]))


def finalize(
    doc: dict[str, Any],
    *,
    merge_commit: str,
    review: dict[str, Any],
    key_path: Path,
    signer: Signer,
) -> dict[str, Any]:
    """Fill the post-merge fields and sign with the gate key."""
    return sign_gate(
        record_step9(doc, merge_commit=merge_commit, review=review),
        key_path=key_path,
        signer=signer,
    )


def verify(doc: dict[str, Any], public_key: str, signer: Signer) -> bool:
    """Check a committed attestation's signature against the committed gate public key."""
    sig = doc.get("signature") or {}
    if sig.get("kind") not in ("gate", "service", "contributor") or not sig.get("value"):
        return False
    if sig.get("key_id") != signer.fingerprint(public_key):
        return False
    return signer.verify(attestation.signed_bytes(doc), str(sig["value"]), public_key)


# --- what a merged partial leaves behind (F07-R6, R7; D-12, D-29, D-31) --------------------------
#
# A partial proof is the one artifact that merges without resolving anything: the assembly is
# kernel-checked, the holes are not, and D-29's rule is that those holes become nodes with no
# human deciding they should. So this is where a submission turns into structure — the only
# place in the gate that writes node directories that nobody proposed.
#
# Everything here is a pure function of the merged tree plus the hole report, so the workflow
# feeds it what the gate already computed and the tests need neither GitHub nor Lean.

ANNEX_DIR = "annex"
ATTEMPTS_DIR = "attempts"
CHILD_SEPARATOR = graphmod.HOLE_SEPARATOR
PARTIAL_SUFFIX = "-partial.lean"
ALTERNATE_SUFFIX = "-alternate.lean"
#: D-31 v3.12: the skeleton names its annex in the file, as a comment, so the gate re-derives the
#: citation from evidence instead of trusting a declaration.
#: The line is recognised by its shape and the value checked afterwards, so a citation that is
#: not a hash is refused by name rather than read as no citation at all (F08-Q18).
_ANNEX_LINE_RE = re.compile(r"^\s*--\s*annex:\s*(?P<value>\S+)\s*$", re.M)
_ANNEX_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
DAY_CHARS = 8  # YYYYMMDD, the prefix of a compact timestamp
ORIGIN_COMPILER = "compiler-derived"
ORIGIN_SKELETON = "skeleton-hole"
#: R6: the child is created with a witness slot. Until someone fills it the node is blocked, and
#: F03 derives that from this file rather than from a record (graph.witness_is_stub).
WITNESS_SLOT = (
    "/-! The witness slot for a hole (D-29, F07-R6). Replace `sorry` with an instance\n"
    "satisfying this statement's hypotheses; until then the node is blocked. -/\n\n"
    "theorem witness : {expected} := by\n  sorry\n"
)
#: F07-T20 (R21): the slot when the extractor reported no expected type. It used to say ``True``
#: for every hole, which for any hole with a hypothesis is the wrong obligation, stated in the
#: one place a contributor looks. A declaration must still be there, so the comment says what
#: the line is.
WITNESS_SLOT_UNKNOWN = (
    "/-! The witness slot for a hole (D-29, F07-R6). The `True` below is a placeholder, not the\n"
    "obligation. A witness is one declaration named `witness` whose type is: exists, over this\n"
    "statement's variables, of the conjunction of its hypotheses (`True` only if it has none).\n"
    "The gate computes that type at step 7, and a mismatch names it. Replace the placeholder\n"
    "type and `sorry` with that type and its proof; until a witness merges the node is\n"
    "blocked. -/\n\n"
    "theorem witness : True := by\n  sorry\n"
)


def witness_slot(expected: str | None) -> str:
    """The ``Witness.lean`` a hole is born with: the obligation step 7 will hold a witness to,
    when the extractor reported it, and otherwise a slot that claims nothing."""
    return WITNESS_SLOT.format(expected=expected) if expected else WITNESS_SLOT_UNKNOWN


class MalformedCitationError(ValueError):
    """An ``-- annex:`` line whose value is not a content hash; the message names the line."""

    def __init__(self, message: str, *, line: int) -> None:
        super().__init__(message)
        self.line = line


def annex_citation(partial_text: str) -> str | None:
    """The annex hash a skeleton cites, or ``None`` when the file cites none (D-31 v3.12).

    A line of the citation's shape whose value is not a 64-character lowercase hex hash is a
    ``MalformedCitationError``: a truncated or upper-cased hash is a citation the author got wrong,
    and reading it as no citation would silently make the children ``compiler-derived``.
    """
    m = _ANNEX_LINE_RE.search(partial_text)
    if m is None:
        return None
    value = m.group("value")
    if _ANNEX_HASH_RE.match(value) is None:
        line = partial_text.count("\n", 0, m.start()) + 1
        msg = (
            f"line {line}: `{m.group(0).strip()}` is not an annex citation; the value is the "
            "SHA-256 of the annex, 64 lowercase hex characters (D-31)"
        )
        raise MalformedCitationError(msg, line=line)
    return value


def annex_present(node_dir: Path, digest: str) -> bool:
    return (node_dir / ANNEX_DIR / f"{digest}.md").is_file()


def check_annex_citation(node_dir: Path, partial_text: str) -> Diagnostic | None:
    """R6: a cited annex that is not on the node is a rejection, not a missing footnote.

    The citation is what makes D-31's reuse mechanical — it is how prose that helped becomes
    traceable from the node it helped — so a citation pointing at nothing is worse than none,
    and one that is not a hash is refused by name.
    """
    try:
        digest = annex_citation(partial_text)
    except MalformedCitationError as exc:
        return Diagnostic("annex-malformed", str(exc), {"line": exc.line})
    if digest is None or annex_present(node_dir, digest):
        return None
    return Diagnostic(
        "annex-uncited",
        f"the skeleton cites annex {digest[:12]}…, which is not on this node; submit the annex "
        "first and cite the hash it returns (D-31)",
        {"annex": digest},
    )


def child_origin(partial_text: str) -> str:
    """R6, D-3 v3.12: a hole from a cited skeleton is its own origin, not compiler-derived.

    The elaborator did not choose these statements — a person did, by writing the decomposition —
    and D-25 has always published ``skeleton-hole`` as a filterable frontier value.
    """
    return ORIGIN_SKELETON if annex_citation(partial_text) is not None else ORIGIN_COMPILER


def child_id(parent: str, index: int) -> str:
    """R6: ``<parent>--h<n>``, one-based, stable in the order the holes were extracted."""
    return f"{parent}{CHILD_SEPARATOR}{index}"


_CHILD_INDEX_RE = re.compile(r"^(?P<n>[1-9][0-9]*)(?:-v[0-9]+)?$")


def next_child_index(nodes_dir: Path, parent: str) -> int:
    """R22 (D-12 v3.19): where a further decomposition's holes are numbered from — one past
    the highest ``<parent>--h<n>`` on disk, a revision (``-v<k>``) counting as its number. The
    first decomposition starts at 1; a later one never reuses an earlier one's ids, so two
    routes to one node coexist as two sets of children."""
    prefix = parent + CHILD_SEPARATOR
    highest = 0
    if nodes_dir.is_dir():
        for path in nodes_dir.iterdir():
            if path.is_dir() and path.name.startswith(prefix):
                m = _CHILD_INDEX_RE.match(path.name[len(prefix) :])
                if m:
                    highest = max(highest, int(m.group("n")))
    return highest + 1


def child_statement(
    child: str, hole: Any, *, imports: Sequence[str] = (), opens: Sequence[str] = ()
) -> str:
    """The child's ``Statement.lean``: the hole's obligation, closed over the binders it sat under,
    under the imports and the ``open`` lines its parent's statement carries.

    The closed form is what makes it a node at all — a hole typed ``q`` inside ``∀ p q, …`` is not
    a proposition anyone can state on its own (F07-T4, from the extractor's ``closed_type``). The
    imports are what make it elaborate: a hole over the on-ramp's ``Opn.IsPrime`` names a
    definition only ``Defs.IsPrime`` provides, and the tactics a prover may use on the child are
    the ones the parent's statement imported (F11-Q16). Library and ``Defs.*`` imports only —
    the parent's own Context is not the child's (F01-Q2), and the child imports its own (F07-T23).
    The ``open`` lines come along for the
    same reason: a hole's closed type is printed in the parent's namespace, so ``sigma 1`` under
    ``open ArithmeticFunction.sigma`` names nothing without that line (found live on erdos-412's
    first hole, 2026-09-17, when the first products scan of it said the file does not elaborate).
    """
    decl = child.replace("-", "_")
    # F07-T23: the child's *own* Context, as an intake root imports its own. A hole is a node
    # like any other and may be decomposed in turn; its holes then arrive in its Context.lean,
    # a proof may not add an import (F00-R19), and so a statement born without this line can
    # never be closed through them (found live on variant-2a7919a9, graph PR #123).
    from opn_gate import layout  # noqa: PLC0415 — as below: layout imports schemas

    own = layout.node_module(child, "Context")
    header = "".join(f"import {m}\n" for m in [*imports, own])
    opened = "".join(f"{line}\n" for line in opens)
    return (
        header
        + ("\n" if header else "")
        + opened
        + ("\n" if opened else "")
        + f"/-! Hole `{hole.name}` of a merged partial proof, as a node (D-12 #5, D-29).\n"
        "Statement generated by the gate from the assembly; immutable (D-3). -/\n\n"
        f"theorem {decl} : {hole.closed_type} := by\n  sorry\n"
    )


def parent_imports(statement_text: str) -> list[str]:
    """The imports a child inherits from its parent's statement: library and ``Defs.*``."""
    from opn_gate import scaffold  # noqa: PLC0415 — scaffold imports layout, which imports schemas

    return scaffold.imports_of([statement_text])


_OPEN_LINE_RE = re.compile(r"^open\b[^\n]*$", re.M)


def parent_opens(statement_text: str) -> list[str]:
    """The ``open`` lines a child inherits from its parent's statement, in order, before its
    theorem: the names the closed type is printed under."""
    head = statement_text.split("theorem", 1)[0]
    return [m.group(0).rstrip() for m in _OPEN_LINE_RE.finditer(head)]


@dataclass(frozen=True)
class PartialMerge:
    """What a merged partial produced: the children, and where the assembly was filed."""

    children: tuple[str, ...]
    attempt_path: str
    origin: str
    annex: str | None
    #: F07-T7: per hole, in extraction order, ``{name, child, reused_node}`` — exactly one of the
    #: last two is set: the node created for it, or the existing node it restates.
    holes: tuple[dict[str, str | None], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "children": list(self.children),
            "attempt": self.attempt_path,
            "origin": self.origin,
            "annex": self.annex,
            "holes": [dict(h) for h in self.holes],
        }


def attempt_name(stamp: str, pseudonym: str, suffix: str) -> str:
    """``<ts>-<pseudonym>-partial.lean`` / ``-alternate.lean`` (R6, R7; D-13's shape)."""
    return f"{stamp}-{pseudonym}{suffix}"


def check_attempt_free(node_dir: Path, name: str) -> None:
    """Refuse an attempt name already filed: ``attempts/`` is append-only (D-3). Asked before
    anything else is written, so the refusal leaves nothing behind (C7; F08-Q18)."""
    if (node_dir / ATTEMPTS_DIR / name).exists():
        msg = f"{name} already exists; attempts/ is append-only (D-3)"
        raise GraphWriteError(msg)


def record_attempt(node_dir: Path, name: str, text: str) -> str:
    """File a submission under ``attempts/`` — append-only, so an existing name is a refusal."""
    check_attempt_free(node_dir, name)
    attempts = node_dir / ATTEMPTS_DIR
    attempts.mkdir(parents=True, exist_ok=True)
    (attempts / name).write_text(text, encoding="utf-8")
    return f"{ATTEMPTS_DIR}/{name}"


class GraphWriteError(RuntimeError):
    """The post-merge job cannot write what it was asked to; nothing is left half-written."""


def apply_partial(  # noqa: PLR0913 — the merge's facts, each named
    node_dir: Path,
    holes: Sequence[Any],
    *,
    partial_text: str,
    pseudonym: str,
    stamp: str,
    author: str | None = None,
    assembly_path: str | None = None,
    model: str | None = None,
) -> PartialMerge:
    """R6: turn a merged partial into child nodes, with the assembly on record under ``attempts/``.

    Order matters and is chosen so a failure leaves nothing behind: the citation is checked, the
    attempt's name reserved and every reused node confirmed, then the children are written, then
    the parent's ``deps`` and ``Context.lean`` are regenerated to match, then the assembly is
    filed. The parent's statement is never touched — only the two bot-owned files change, which
    is what keeps D-3's immutability intact (F07-Q2).

    A hole the extractor found to be an existing node's statement (``defeq_sibling``, F07-T7) is
    that node: no ``--h<n>`` directory is written for it and the other holes keep the index of
    their position; it is an edge only when it is one of the parent's own holes (R22, D-12
    v3.19), since the parent must not come to wait on a sibling because of a route. ``model``
    is the submission block's declared model, recorded in each child's provenance as the D-23
    disclosure it came from (R13).

    ``assembly_path`` is the merged assembly's own path under the node when the submission was
    the ``attempts/*.lean`` file partial mode takes (F11-T4): that file *is* the attempt record,
    so nothing is filed again — the first live merge filed the same text twice (F11-Q28). A
    caller without it (the pre-F11 shape, a partial carried elsewhere) still gets the copy.
    """
    from opn_gate import scaffold  # noqa: PLC0415 — scaffold imports layout, which imports schemas

    problem = check_annex_citation(node_dir, partial_text)
    if problem is not None:
        raise GraphWriteError(problem.message)
    if not holes:
        msg = "a partial with no holes creates no children (D-12 #5)"
        raise GraphWriteError(msg)
    on_record = assembly_path is not None and assembly_path.startswith(ATTEMPTS_DIR + "/")
    attempt_file = attempt_name(stamp, pseudonym, PARTIAL_SUFFIX)
    if not on_record:
        check_attempt_free(node_dir, attempt_file)

    # F07-R19: the extractor says whether each hole's printed type elaborates back to the
    # obligation it came from. Where it does not, the child's Statement.lean would be a different
    # proposition: erdos-69's two holes were published over the naturals while the assembly had
    # discharged them over the reals, so a proof of the real obligation could not be admitted and
    # the node published was not the hole (2026-09-17). A node the gate itself writes must be one
    # the gate would admit. Step 4 refuses such a partial before it merges (F07-T19,
    # `hole-not-roundtrip`); this loop is the backstop for a partial merged under a pin that
    # predates that check. Checked over every hole before anything is written, so that a refusal
    # leaves nothing behind (C7).
    for hole in holes:
        if not getattr(hole, "closed_roundtrip", True):
            msg = (
                f"hole {getattr(hole, 'name', '?')!r}: its type does not survive being printed "
                "and read back, so a child node would state a different proposition (F07-R19)"
            )
            raise GraphWriteError(msg)

    origin = child_origin(partial_text)
    annex = annex_citation(partial_text)
    nodes_dir = node_dir.parent
    parent = node_dir.name
    reused = [
        reused_node(nodes_dir, parent, hole) or existing_hole_for(nodes_dir, parent, hole)
        for hole in holes
    ]
    parent_statement = node_dir / "Statement.lean"
    parent_text = parent_statement.read_text(encoding="utf-8") if parent_statement.is_file() else ""
    imports = parent_imports(parent_text)
    opens = parent_opens(parent_text)
    created: list[str] = []
    edges: list[str] = []
    placed: list[dict[str, str | None]] = []
    # R22 (D-12 v3.19): a later decomposition numbers its holes after the earlier ones'.
    first = next_child_index(nodes_dir, parent)
    for index, (hole, existing) in enumerate(zip(holes, reused, strict=True), start=first):
        if existing is not None:
            # R22: a hole that restates one of the node's own holes is that hole again, and the
            # edge is already on the record. One that restates any other sibling adds no edge:
            # an edge the node would wait on is exactly what a decomposition must not add, so
            # the restatement is recorded in the verdict's placement and nowhere else.
            if graphmod.is_hole_child(nodes_dir, parent, existing):
                edges.append(existing)
            placed.append({"name": hole.name, "child": None, "reused_node": existing})
            continue
        child = child_id(parent, index)
        statement = child_statement(child, hole, imports=imports, opens=opens)
        proposal = scaffold.Proposal(
            node_id=child,
            target_id=nodes_dir.parent.name,
            statement=statement,
            witness=witness_slot(getattr(hole, "expected_witness", None)),
            author=author or pseudonym,
            origin=origin,  # type: ignore[arg-type]
            date=stamp_to_date(stamp),
            model=model,
        )
        scaffold.write(nodes_dir, proposal)
        created.append(child)
        edges.append(child)
        placed.append({"name": hole.name, "child": child, "reused_node": None})

    add_deps(node_dir, edges)
    regenerate_context(node_dir, nodes_dir)
    attempt = (
        str(assembly_path) if on_record else record_attempt(node_dir, attempt_file, partial_text)
    )
    return PartialMerge(tuple(created), attempt, origin, annex, tuple(placed))


_HOLE_TYPE_RE = re.compile(r"^theorem\s+\S+\s*:\s*(?P<type>.*?)\s*:=\s*by\s*$", re.M | re.S)
_WS_RE = re.compile(r"\s+")


def existing_hole_for(nodes_dir: Path, parent: str, hole: Any) -> str | None:
    """R22: the parent's own hole child that already states this hole, by text — the child's
    ``Statement.lean`` declares the closed type ``child_statement`` wrote, so a re-run of the
    job, or a later route with the same lemma, finds it here without the sandbox and writes no
    second node. The extractor's ``defeq_sibling`` answers the same question up to definitional
    equality; this is the exact-text floor beneath it."""
    closed = getattr(hole, "closed_type", None)
    if not closed or not nodes_dir.is_dir():
        return None
    wanted = _WS_RE.sub(" ", str(closed)).strip()
    prefix = parent + CHILD_SEPARATOR
    for path in sorted(p for p in nodes_dir.iterdir() if p.name.startswith(prefix)):
        statement = path / "Statement.lean"
        if not statement.is_file():
            continue
        m = _HOLE_TYPE_RE.search(statement.read_text(encoding="utf-8"))
        if m and _WS_RE.sub(" ", m.group("type")).strip() == wanted:
            return path.name
    return None


def reused_node(nodes_dir: Path, parent: str, hole: Any) -> str | None:
    """F07-T7, D-29: the existing node a hole restates, or ``None`` when it needs a node of its own.

    The extractor names the sibling (``defeq_sibling``) after checking definitional equality in
    the sandbox; this only confirms the name is another node of the target, asked before anything
    is written. A name that is not would be an edge to nothing, so it is refused (C7).
    """
    sibling = getattr(hole, "defeq_sibling", None)
    if not sibling:
        return None
    sibling = str(sibling)
    if sibling == parent or not (nodes_dir / sibling / "Statement.lean").is_file():
        msg = (
            f"hole {hole.name} is reported to restate {sibling!r}, which is not another node of "
            "this target; no child or edge was written"
        )
        raise GraphWriteError(msg)
    return sibling


def stamp_to_date(stamp: str) -> str:
    """``20260910T121314Z`` -> ``2026-09-10``, the day META records."""
    return f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}" if len(stamp) >= DAY_CHARS else stamp


def add_deps(node_dir: Path, children: Sequence[str]) -> list[str]:
    """R6, Q2: append the new node ids to the parent's ``deps``. Bot-owned, and additive — the
    statement hash is untouched, so the node's immutability is not what changes here."""
    import yaml  # noqa: PLC0415 — only the writing path needs it

    meta_path = node_dir / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    deps = [str(d) for d in (meta.get("deps") or [])]
    for child in children:
        if child not in deps:
            deps.append(child)
    meta["deps"] = deps
    dumped = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    meta_path.write_text(dumped, encoding="utf-8")
    return deps


def regenerate_context(node_dir: Path, nodes_dir: Path) -> str:
    """R6, Q2: rewrite the parent's ``Context.lean`` from its declared deps.

    Generated rather than edited, for the reason the scaffold generates it: F01-R6 compares each
    signature here with the dep's own ``Statement.lean``, byte for byte.
    """
    import yaml  # noqa: PLC0415

    from opn_gate import scaffold  # noqa: PLC0415

    meta = yaml.safe_load((node_dir / "META.yaml").read_text(encoding="utf-8"))
    deps = graphmod.effective_deps(nodes_dir, meta.get("deps"))  # F08-T10: through any revision
    text = scaffold.context_for(nodes_dir, deps)
    (node_dir / "Context.lean").write_text(text, encoding="utf-8")
    return text


def refresh_contexts(nodes_dir: Path) -> list[Path]:
    """F08-T10 (D-8 v3.18): regenerate every ``Context.lean`` that no longer carries its deps'
    signatures, and return the files rewritten.

    ``Context.lean`` is generated, never authored (D-3: it is not a submission path), and step 8
    holds it to each dep's ``Statement.lean`` byte for byte. A D-8 revision changes what a dep
    *is* without touching the dependent's record, so the dependent's context goes out of date
    and nothing a contributor may submit can mend it. This pass does, for every node whose
    context fails the gate's own check against its effective deps, and leaves a context that
    passes alone. It is a pure function of the tree in both directions: run after a reverted
    revision it writes the old context back, which is what makes the revert complete."""
    from opn_gate import layout  # noqa: PLC0415
    from opn_gate.steps import deps as depstep  # noqa: PLC0415

    rewritten: list[Path] = []
    for node_dir in sorted(p for p in nodes_dir.iterdir() if p.is_dir()):
        node = layout.load_node(node_dir, nodes_dir.parent.name)
        if not isinstance(node, layout.Node):
            continue  # a node the layout refuses is not this pass's to judge
        declared = list(graphmod.effective_deps(nodes_dir, node.meta.get("deps")))
        if not declared or depstep.check_context(node, declared) is None:
            continue
        try:
            regenerate_context(node_dir, nodes_dir)
        except ValueError as exc:  # scaffold.ScaffoldError: a dep with no statement
            log.warning("%s: Context.lean not regenerated: %s", node_dir.name, exc)
            continue
        rewritten.append(node_dir / "Context.lean")
    return rewritten


def record_alternate(node_dir: Path, proof_text: str, *, pseudonym: str, stamp: str) -> str:
    """R7, D-25: a second proof of an already-proved node is recorded, not merged over the first.

    Racing is permitted and on hard nodes desirable, so the loser's work is kept — but
    ``Proof.lean`` is the first one that landed and this never touches it.
    """
    return record_attempt(node_dir, attempt_name(stamp, pseudonym, ALTERNATE_SUFFIX), proof_text)
