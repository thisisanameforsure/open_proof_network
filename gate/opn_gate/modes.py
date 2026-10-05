"""What kind of pull request this is, and what that kind may touch (F07-R3, R9, R10; F08-R2, R5,
R8).

Until F07 every pull request the gate saw was a proof of one node. D-12's other artifacts, D-13's
postmortems, D-31's annexes, D-14's approach records and D-3's explainers all reach the graph the
same way — a pull request — and they need different checks: a proof runs the Lean pipeline, an
append asserts nothing a kernel could check and merges on its schema, an explainer is prose about
an object that already merged. F08 adds the two kinds that change the graph's *structure*: a
proposal, which anyone may make and admission decides (D-29), and a curator record, which only a
listed identity may file (D-8, D-33).

So the diff is classified into exactly one mode before anything else runs:

===============  ==========================================================================
``proof``        the node's ``Proof.lean``, plus appends — the D-4 pipeline (D-12 #1, #2, #3)
``partial``      a ``.lean`` assembly under ``attempts/``, plus appends (D-12 #4, #5) and the
                 witnesses it carries for its holes, ``attempts/<assembly>.<n>.witness``
                 (F07-R23, D-29 v3.24)
``append``       only new postmortems, precheck records, annexes, approach records, revision
                 requests or defect claims (the last two may carry a Lean exhibit, which is
                 elaborated in the sandbox — ``opn_gate.exhibits``)
``explainer``    only new files under ``explainer/`` (D-3), on a node that already has a proof —
                 and, since F15-R8, signature files under ``explainer/signed/``, alone or with
                 new explainers: a real-identity contributor's comprehension claim on one
                 explainer, refused by name when the explainer is absent, the sentence
                 differs, the signature fails or the signer is neither an active steward of
                 the target nor a listed curator (F15-Q4). Since F20-R1, also glosses under
                 ``gloss/`` of a node of any status or of a target's definition modules
                 (D-3 v3.30), checked by ``opn_gate.glosses`` and never built
``proposal``     exactly one new node directory and nothing else — or only ``Witness.lean``
                 on a hole whose slot is unfilled (F08-R2, R5); admission decides, nobody
                 reviews (D-29)
``curator``      status records, or a versioned node ``<id>-v<n>``, by a login listed in the
                 graph's ``curators.json`` (F08-R8); reviewed by a second listed identity when
                 there is one (D-21, D-22). Also a curated target's D-10 posting: its
                 ``target.yaml`` modified alone, ``posting`` null to a posting (F11-R5)
``intake``       a whole new target — ``target.yaml``, ``gate-spec.json``, ``defs/``, the
                 fidelity certificates, a status record and exactly one node, the root — by a
                 listed curator (F11-R2, D-6); the root is admitted, which builds the
                 definitions first, and a second listed identity reviews when there is one
``fidelity``     only new certificates for one subject of an existing curated target, opened by
                 their attestor (F11-R3, D-9): the signature is the review, so nobody else
                 approves it, and it builds nothing
``curator``      … and the graph's ``policy.json``, the steward rule's switch (F15-R3, Q2),
                 flipped either way by a listed curator and nothing else in the same pull
                 request
``steward``      only new steward records — a signed commitment or step-down (F15-R1, R2;
                 D-32 v3.17) — each checked by name and nothing built; the signature binds
                 the record, not the pull request's author (F15-Q8), and the merge is the
                 curator's check of the identity link (F15-Q7). Inside an intake or a
                 curator pull request the records are checked the same way
``proposed-for`` exactly one new ``proposed-for/`` record on one node and nothing else (F18-R8,
                 D-14 v3.26): which node of its target the statement was proposed for, by the
                 node's proposer or a listed curator (``check_proposed_for``). Nothing is built
                 and nothing is derived from it. A proposal may carry its node's first record
===============  ==========================================================================

A diff that fits none of them is rejected at step 2, naming the paths — never guessed at.

Modes are decided from the diff alone, plus one fact the host reports: who opened the pull
request, which the curator rule consults and the certificate rule compares with the attestor
(``check_certificate``). Whether the *submitter* called it a counterexample
or a reduction is in the ``opn-submission`` block (``submission-meta/v1``, F07-R2), and the
artifact checks that consume it are F07-T2's; classification never reads it, because the block is
not evidentiary and the paths are.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, Literal

import yaml

from opn_gate import annex as annexmod
from opn_gate import (
    config,
    defs,
    evidence,
    fidelity,
    glosses,
    intake,
    layout,
    ledger,
    paths,
    qa,
    records,
    schemas,
    sections,
    signed,
    steward,
)
from opn_gate import graph as graphmod
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change, Located, Role
from opn_gate.signer import Signer

Mode = Literal[
    "proof",
    "partial",
    "alternate",
    "append",
    "explainer",
    "proposal",
    "curator",
    "intake",
    "fidelity",
    "steward",
    "proposed-for",
]

#: The modes that run the Lean pipeline; the others never build a proof (R9, R10; F08-R2).
BUILDING_MODES: tuple[Mode, ...] = ("proof", "partial", "alternate")
#: F08-R8: the graph's role file — the founder's, and the only one at Stage 0 (F08 §7).
CURATORS_FILE = "curators.json"
#: F08-R8, D-22: why step 9 is not asked of a curator PR while the founder is the only curator.
WAIVER_SINGLE_CURATOR = "single-curator"
#: F08-Q2: the one status a proposer may give their own new node.
PROPOSAL_STATUS = "speculative"
#: D-4 v3.11: step 9 is a property of the statement. For these modes — every kernel-checked
#: artifact of D-12 alike — the root's certificate or registry provenance stands in for a
#: person; an alternate asks no step 9 at all (v3.13), and curator records keep F08-R8's rule.
STATEMENT_REVIEW_MODES: tuple[Mode, ...] = ("proof", "partial")
#: D-4 v3.11: the rung the root's certificate must reach ("at least screened-and-signed").
STEP9_GRADE = fidelity.SIGNED_FROM
#: F14-R5 (Mike, 2026-09-14): registry provenance alone no longer satisfies step 9; a root's
#: recorded catalog evidence at the configured minimum does (``step9_evidence``).
#: What stood in for the review; ``pr-approval`` is the person D-4 asks for otherwise.
#: D-4 v3.20: ``intermediate`` and ``calibration`` are not things that stood in for a person —
#: they are why no person was asked: the artifact settles no root, or the target claims nothing
#: new. Recorded all the same, so an attestation never reads as if a review had happened.
StatementBasis = Literal["certificate", "provenance", "intermediate", "calibration"]
ReviewKind = Literal["certificate", "provenance", "intermediate", "calibration", "pr-approval"]
NOT_ASKED_INTERMEDIATE: StatementBasis = "intermediate"
NOT_ASKED_CALIBRATION: StatementBasis = "calibration"

log = logging.getLogger(__name__)

#: What a file looked like at the pull request's base commit: its bytes, or ``None`` when it did
#: not exist. Only the witness-completion rule needs the base (F08-R5): whether a hole's slot was
#: still unfilled is a fact about the tree *before* the change, and the head no longer has it.
BaseReader = Callable[[str], bytes | None]

_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<yaml>.*?)\r?\n---[ \t]*\r?\n", re.S)


@dataclass(frozen=True)
class Curators:
    """``curators.json`` (F08-R8): ``{identities: [{pseudonym, github_login}]}``."""

    identities: tuple[tuple[str, str], ...] = ()  # (pseudonym, github_login)

    @property
    def logins(self) -> frozenset[str]:
        return frozenset(login for _, login in self.identities)

    def pseudonym_of(self, login: str) -> str | None:
        for pseudonym, listed in self.identities:
            if listed == login:
                return pseudonym
        return None


class CuratorsError(ValueError):
    """``curators.json`` is present but is not the role file R8 describes."""


def load_curators(graph_root: Path) -> Curators:
    """The graph's curator list, or an empty one when the graph has no ``curators.json``.

    Checked at the boundary (conventions §4) but not by a published schema: the file is a role
    list the founder owns (F08 §7), not a record of the mathematics, so D-34's versioning does not
    reach it — and adding a schema would put it in ``info.json``'s index for no consumer.
    """
    path = graph_root / CURATORS_FILE
    if not path.is_file():
        return Curators()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        msg = f"{CURATORS_FILE} is not readable JSON: {exc}"
        raise CuratorsError(msg) from exc
    identities = doc.get("identities") if isinstance(doc, dict) else None
    if not isinstance(identities, list):
        msg = f"{CURATORS_FILE} must be an object with an `identities` list (F08-R8)"
        raise CuratorsError(msg)
    out: list[tuple[str, str]] = []
    for entry in identities:
        if not (
            isinstance(entry, dict)
            and isinstance(entry.get("pseudonym"), str)
            and isinstance(entry.get("github_login"), str)
            and entry["pseudonym"]
            and entry["github_login"]
        ):
            msg = f"{CURATORS_FILE}: each identity is {{pseudonym, github_login}}, got {entry!r}"
            raise CuratorsError(msg)
        out.append((entry["pseudonym"], entry["github_login"]))
    return Curators(tuple(out))


@dataclass(frozen=True)
class Classification:
    """What the diff is. ``mode`` is ``None`` exactly when ``problems`` says why it is nothing."""

    mode: Mode | None
    target_id: str | None
    node_id: str | None
    located: tuple[Located, ...] = ()
    problems: tuple[Diagnostic, ...] = ()
    #: The node directory admission runs on (F08-R1): a proposal's, or a curator's versioned node.
    admit: str | None = None
    #: Who may give step 9's approval. ``None`` means any non-author (D-4); a curator PR names the
    #: other listed identities (F08-R8), and an empty tuple is the founding-team waiver (D-22).
    reviewers: tuple[str, ...] | None = None
    #: The login that opened the pull request, as the host reported it. Only the certificate
    #: rule reads it after classification (a certificate is its attestor's own act, F11-R3);
    #: it is the host's fact, not a finding, so ``as_dict`` does not publish it.
    author: str | None = None
    #: Each existing ``Proof.lean`` the diff modifies. Whether that is allowed depends on the
    #: node's tutorial flag, which only ``check`` can read (D-3 v3.13, D-27); not published.
    replaced: tuple[str, ...] = ()
    #: D-4 v3.11: what satisfies step 9 in place of a person for a proof or a partial — the
    #: root's certificate or its registry provenance — and the reference the attestation records.
    #: Read from the graph (``with_statement_review``), since the diff alone cannot say.
    review_basis: StatementBasis | None = None
    review_reference: str | None = None
    #: F20-T6: whether the pull request was opened by the network's service (its App's login,
    #: ``config.service_login``), which acts for the identity it wrote into the record's own
    #: ``author``. The host's fact, like ``author``; not published.
    by_service: bool = False

    @property
    def ok(self) -> bool:
        return self.mode is not None

    @property
    def needs_gate(self) -> bool:
        """Whether the D-4 proof pipeline runs. Appends and explainers assert nothing (R9, R10);
        a proposal is admitted, not proved (F08-R2)."""
        return self.mode in BUILDING_MODES

    @property
    def needs_admission(self) -> bool:
        """Whether admission runs in the sandbox on a new node directory (F08-R2, R8)."""
        return self.admit is not None

    @property
    def needs_review(self) -> bool:
        """Step 9 is a review of a *statement's* claim; an append makes none (F07-Q4), a
        proposal is admitted mechanically (D-29), and a curator record needs a second curator
        only when there is one (F08-R8)."""
        if self.mode in ("curator", "intake"):
            return bool(self.reviewers)
        if self.mode == "alternate":
            # D-4 v3.13: the statement met step 9 when the first proof merged, and a later proof
            # changes no verdict, status, dependency or credit (D-25, F07-Q20).
            return False
        if self.mode in STATEMENT_REVIEW_MODES and self.review_basis is not None:
            return False  # D-4 v3.11: the statement's certificate or provenance is the review
        return self.mode in BUILDING_MODES

    @property
    def review_kind(self) -> ReviewKind | None:
        """What satisfies step 9: a person's approval when one is asked, the root's certificate
        or provenance when it stands in (D-4 v3.11), and ``None`` where step 9 is not asked."""
        if self.needs_review:
            return "pr-approval"
        if self.mode in STATEMENT_REVIEW_MODES or self.mode == "alternate":
            # F07-T38: an alternate is not asked (v3.13) and says why, as v3.20's words do
            return self.review_basis
        return None

    @property
    def review_waived(self) -> str | None:
        """Why step 9 is not asked when the mode would otherwise ask it — for the record."""
        if self.mode in ("curator", "intake") and not self.reviewers:
            return WAIVER_SINGLE_CURATOR
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "target": self.target_id,
            "node": self.node_id,
            "needs_gate": self.needs_gate,
            "needs_admission": self.needs_admission,
            "admit": self.admit,
            "needs_review": self.needs_review,
            "reviewers": None if self.reviewers is None else list(self.reviewers),
            "review_waived": self.review_waived,
            "review_kind": self.review_kind,
            "review_reference": (
                self.review_reference if self.review_kind in ("certificate", "provenance") else None
            ),
            "problems": [d.as_dict() for d in self.problems],
        }


def with_statement_review(
    graph_root: Path,
    classification: Classification,
    *,
    minimum: int = config.DEFAULT_STEP9_MIN_SCORE,
) -> Classification:
    """D-4 step 9 (F14-R5): for a proof or a partial it is satisfied by the root's certificate,
    else by the root's recorded catalog evidence scoring ``minimum`` or more, else by a
    non-author's approval — decided from the checkout. Where a statement came from is not evidence
    that it says what the conjecture says, so registry provenance alone no longer stands in
    (F07-T17 narrowed; Mike, 2026-09-14).

    The checkout is the pull request's merge commit, and a building mode's diff cannot add a
    certificate or an evidence record or modify ``target.yaml`` (each makes it ``mode-mixed``), so
    what is read here is what stood on the base: nobody vouches for the statement in the pull
    request that proves it.
    """
    if classification.mode == "alternate" and classification.target_id is not None:
        # F07-T38: an alternate settles nothing (its node is proved), so the post-merge record says
        # which of v3.20's reasons applies; without one the job's --review-kind had nothing to take.
        return replace(classification, review_basis=alternate_basis(graph_root, classification))
    if classification.mode not in STATEMENT_REVIEW_MODES or classification.target_id is None:
        return classification
    target_dir = graph_root / "targets" / classification.target_id
    not_asked = step9_not_asked(graph_root, classification)
    if not_asked is not None:
        return replace(classification, review_basis=not_asked, review_reference=None)
    certificate = root_certificate(target_dir)
    if certificate is not None:
        return replace(classification, review_basis="certificate", review_reference=certificate)
    recorded = step9_evidence(target_dir, minimum)
    if recorded is not None:
        # F14-R6: recorded as provenance, so the attestation schema and an older pin still read it.
        return replace(classification, review_basis="provenance", review_reference=recorded)
    return classification


def alternate_basis(graph_root: Path, classification: Classification) -> StatementBasis:
    """Why an alternate asks no review: ``calibration`` on a calibration target, else
    ``intermediate`` (it settles nothing: the node it proves is already proved)."""
    from opn_gate import intake  # noqa: PLC0415

    assert classification.target_id is not None
    target_dir = graph_root / "targets" / classification.target_id
    try:
        if intake.is_calibration(intake.load_doc(target_dir)):
            return NOT_ASKED_CALIBRATION
    except (ValueError, OSError) as exc:
        log.warning(
            "step 9: %s does not load; the alternate is intermediate: %s", target_dir.name, exc
        )
    return NOT_ASKED_INTERMEDIATE


def step9_not_asked(graph_root: Path, classification: Classification) -> StatementBasis | None:
    """D-4 v3.20 (F07-T24): why step 9 is not asked of this proof or partial at all, or ``None``
    when it is. The review is a mathematician confirming that the Lean statement says what the
    conjecture says, at the moment the conjecture would be called settled, so it is asked only of
    an artifact that settles the target: a proof on the root, or on a ``resolves`` variant (D-30:
    it implies the root) while the root is still open. A skeleton settles nothing (D-12 v3.19),
    and neither does a hole, a crux, or a variant beneath a closed root. A calibration target
    (``target.yaml``, curator-only and unmodifiable by a proof's diff) is a result already in the
    literature and asks nothing, as the tutorial node does not (D-27).

    Read from the checkout, like the certificate. A graph that does not load answers ``None``:
    the review stays asked, because nothing stands in for a person on a guess (C7)."""
    from opn_gate import graph as graphmod  # noqa: PLC0415 — graph imports records
    from opn_gate import intake  # noqa: PLC0415

    assert classification.target_id is not None
    target_dir = graph_root / "targets" / classification.target_id
    try:
        if intake.is_calibration(intake.load_doc(target_dir)):
            return NOT_ASKED_CALIBRATION
        if classification.mode == "partial":
            return NOT_ASKED_INTERMEDIATE
        tg = graphmod.load_target(graph_root, classification.target_id)
    except (ValueError, OSError) as exc:  # SchemaError, GraphError, IntakeError: a graph defect
        log.warning("step 9: %s does not load, so a review is asked: %s", target_dir.name, exc)
        return None
    node = tg.nodes.get(classification.node_id or "")
    root_open = tg.statuses.get(tg.root) not in graphmod.RESOLVED_STATUSES
    settles = node is None or node.node_id == tg.root or (node.relation == "resolves" and root_open)
    # ``resolves`` while the root is open is a proof of the root by another road; a node the
    # graph does not carry is treated as if it settled, so the review stays asked (C7).
    return None if settles else NOT_ASKED_INTERMEDIATE


def root_certificate(target_dir: Path) -> str | None:
    """The newest counting signature on the root, as ``fidelity/<file>``, when the root's grade is
    at least ``screened-and-signed`` — counting as F11-R3 counts: ``fidelity/v2`` pinned to the
    root as it stands (F11-T9), the latest one's grade. ``None`` otherwise, and when the
    certificates or the root cannot be read (C7: nothing stands in for a person on a guess)."""
    try:
        certs = fidelity.load(target_dir).get(fidelity.ROOT_SUBJECT, [])
        if not certs:
            return None
        counted = fidelity.counting(certs, fidelity.current_hash(target_dir, fidelity.ROOT_SUBJECT))
    except (ValueError, OSError) as exc:  # SchemaError, QaError, GraphError: a graph defect
        log.warning("step 9: the root certificates of %s do not read: %s", target_dir.name, exc)
        return None
    if not fidelity.meets(fidelity.grade_of(counted), STEP9_GRADE):
        return None
    newest = [cert for cert in counted if cert.signs][-1]
    return f"{fidelity.FIDELITY_DIR}/{newest.path.name}"


def step9_evidence(target_dir: Path, minimum: int = config.DEFAULT_STEP9_MIN_SCORE) -> str | None:
    """F14-R3, R5, R6: the newest evidence record pinned to the root as it stands, as the reference
    an attestation cites, when it scores ``minimum`` or more; ``None`` otherwise, and when the
    records or the root cannot be read (C7: nothing stands in for a person on a guess)."""
    try:
        record = evidence.current(target_dir)
    except (ValueError, OSError) as exc:  # SchemaError, EvidenceError, QaError: a graph defect
        log.warning("step 9: the evidence records of %s do not read: %s", target_dir.name, exc)
        return None
    if record is None or record.score < minimum:
        return None
    return record.reference()


def classify(  # noqa: PLR0911, PLR0912 — one return and one branch per rejection
    changes: Iterable[Change],
    *,
    author: str | None = None,
    curators: Curators | None = None,
    graph_root: Path | None = None,
    service_login: str | None = config.DEFAULT_SERVICE_LOGIN,
) -> Classification:
    """R3, F08-R2, R8: the diff's one mode, or the reasons it is not a submission at all.

    ``author`` is the login that opened the pull request, as the host reports it; ``curators`` is
    the graph's role file. Both are consulted only when the diff is curator-shaped.

    ``graph_root``, the checkout, is read for one fact the path cannot give: what a withdrawal
    withdraws. A withdrawal of a gloss or explainer version (F20-R7) is its author's, a steward's
    or a curator's and rides the explainer mode; every other withdrawal stays a curator record
    (F08-T31). Without a checkout every withdrawal is read as a curator's, the stricter reading.

    ``service_login`` is the login the network's service opens pull requests as (F20-T6): such a
    pull request acts for the identity the service wrote into the record's ``author``, which is
    how the explainer mode's role rules then read it (``acting_names``).
    """
    changes = list(changes)
    if not changes:
        return _rejected([Diagnostic("mode-empty", "the pull request changes no file")])

    located: list[Located] = []
    problems: list[Diagnostic] = []
    for change in changes:
        problems.extend(_locate_change(change, located))
    if problems:
        return _rejected(problems)

    targets = sorted({loc.target_id for loc in located})
    if len(targets) > 1:
        return _rejected(
            [
                Diagnostic(
                    "mode-multi-target",
                    f"a submission touches one target; this one touches {', '.join(targets)}",
                    {"targets": targets},
                )
            ]
        )
    target_id = targets[0]

    # A new node directory is one whose definition files are added; a status record outside
    # every new directory, or a versioned directory, is a curator's act (F08-R8).
    new_dirs = sorted({loc.node_id for loc in located if loc.role == "node" and loc.node_id})
    versions_withdrawn = {
        loc.path
        for loc in located
        if loc.role == "withdrawal"
        and graph_root is not None
        and withdraws_version(graph_root, loc.path)
    }
    curator_records = [
        loc
        for loc in located
        if loc.role in paths.CURATOR_ROLES
        and loc.node_id not in new_dirs
        and loc.path not in versions_withdrawn
    ]
    if any(loc.role in paths.INTAKE_ROLES for loc in located):
        # A target's own files arrive whole in its intake (F11-R2); after it, exactly two of them
        # change again, each in a pull request of its own (F11-R5): the record takes its posting,
        # and a signer adds certificates (F11-R3). Anything else is an intake, or a mixture.
        roles = {loc.role for loc in located}
        added = {c.path for c in changes if c.status == "A"}
        adds_record = any(loc.role == "target-record" and loc.path in added for loc in located)
        if roles == {"definition"}:
            # F11-R15: definitions alone are a curator's addition to a target that exists.
            return _classify_definitions(
                located, target_id, author=author, curators=curators or Curators()
            )
        if adds_record or roles & {"gate-spec", "definition"}:
            return _classify_intake(
                located,
                changes,
                target_id,
                new_dirs,
                author=author,
                curators=curators or Curators(),
            )
        if roles == {"target-record"}:
            return _classify_posting(
                located, target_id, author=author, curators=curators or Curators()
            )
        if roles == {"fidelity"}:
            return _classify_certificate(located, target_id, author=author)
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "mode-mixed",
                    "a target's posting (target.yaml) and a signer's fidelity certificates are "
                    "each a pull request of their own, carrying nothing else (F11-R3, R5); this "
                    "one mixes: " + ", ".join(sorted(roles)),
                    {"roles": sorted(roles)},
                ),
            ),
        )
    if curator_records or any(paths.is_versioned(n) for n in new_dirs):
        return _classify_curator(
            located, changes, target_id, new_dirs, author=author, curators=curators or Curators()
        )
    # F15-R2, R6: steward records and write-up records alone are the steward mode — both are a
    # steward's signed acts — whoever opened the pull request (Q8); brought by anything else
    # that is not an intake or a curator record, they are a mixture.
    if all(loc.role in ("steward", "writeup") for loc in located):
        return Classification("steward", target_id, None, tuple(located), author=author)

    nodes = sorted({loc.node_id for loc in located if loc.node_id is not None})
    if len(nodes) > 1:
        return _rejected(
            [
                Diagnostic(
                    "mode-multi-node",
                    "a submission touches one node (D-2, D-3); this one touches "
                    + ", ".join(nodes),
                    {"nodes": nodes},
                )
            ]
        )
    node_id = nodes[0] if nodes else None

    roles = {loc.role for loc in located}
    mode = _mode_for(roles)
    if mode is None:
        return Classification(None, target_id, node_id, tuple(located), (_mixed(roles),))
    pointers = [loc.path for loc in located if loc.role == "proposed-for"]
    if len(pointers) > 1:
        multiple = Diagnostic(
            "proposed-for-multiple",
            f"a pull request adds one proposed-for record (F18-R8; the latest is the one shown); "
            f"this one adds {len(pointers)}: " + ", ".join(pointers),
            {"paths": pointers},
        )
        return Classification(None, target_id, node_id, tuple(located), (multiple,))
    alternates = [loc.path for loc in located if loc.role == "alternate"]
    if len(alternates) > 1:
        multiple = Diagnostic(
            "alternate-multiple",
            f"a pull request adds one alternate proof (D-25); this one adds {len(alternates)}: "
            + ", ".join(alternates),
            {"paths": alternates},
        )
        return Classification(None, target_id, node_id, tuple(located), (multiple,))
    admit = node_id if mode == "proposal" else None
    modified = {c.path for c in changes if c.status == "M"}
    replaced = tuple(loc.path for loc in located if loc.role == "proof" and loc.path in modified)
    # F18-R8: who may write a proposed-for record is ``check_proposed_for``'s question, and the
    # curator half of it is the host's fact, so it rides on the classification. F20-R6, R7: so
    # is the steward-or-curator half of superseding a signed version and of a withdrawal.
    who = author if pointers or mode == "explainer" else None
    return Classification(
        mode,
        target_id,
        node_id,
        tuple(located),
        admit=admit,
        replaced=replaced,
        author=who,
        by_service=mode == "explainer" and author is not None and author == service_login,
    )


def _classify_curator(  # noqa: PLR0913 — the diff, its located paths and the host's one fact
    located: list[Located],
    changes: list[Change],
    target_id: str,
    new_dirs: list[str],
    *,
    author: str | None,
    curators: Curators,
) -> Classification:
    """F08-R8: status records and versioned nodes, by a listed login, reviewed by another one.

    A curator PR may touch several nodes — D-8's revision marks the old node superseded and each
    dependent stale in the same change — so the one-node scope rule does not apply; the one-target
    rule still does. What it may do to those nodes is *add records*: a node's own files are
    immutable once merged (D-3), so any node file outside the one new versioned directory — a
    modified witness, a deleted relation, a witness added to an existing hole, which is a
    proposal (F08-R5) — is refused before the author is asked (F08-Q18).
    """
    roles = {loc.role for loc in located}
    # F15-R2, R6: a curator may carry a steward's signed record or a write-up record (Q8);
    # each is checked like any other.
    allowed = set(paths.NODE_ROLES) | set(paths.CURATOR_ROLES) | {"steward", "writeup"}
    if "qa-record" in roles:
        # F12-R4: the screen's own claim rides with the QA record that produced it; the claim is
        # then held to being a screen-finding (``check_defect_claim``), not a contributor's.
        allowed.add("defect-claim")
    if "drift-record" in roles:
        # F12-R11: the watcher's revision request rides with the drift record that opened it,
        # held to the upstream-drift class (``check_revision_request``).
        allowed.add("revision-request")
    if not roles <= allowed:
        return Classification(None, target_id, None, tuple(located), (_mixed(roles),))
    node_roles = set(paths.NODE_ROLES)
    # F12-R10: the attempts ledger is the one curator file that grows in place.
    growing = {loc.path for loc in located if loc.role in paths.MODIFIABLE_ROLES}
    touched = sorted(
        {loc.path for loc in located if loc.role in node_roles and loc.node_id not in new_dirs}
        | {c.path for c in changes if c.status != "A" and c.path not in growing}
    )
    if touched:
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "mode-mixed",
                    f"{', '.join(touched)}: a curator pull request adds status records and at "
                    "most one versioned node directory (F08-R8); an existing node's files are "
                    "immutable (D-3), and a witness for a hole is a proposal (F08-R5)",
                    {"paths": touched},
                ),
            ),
        )
    unversioned = [n for n in new_dirs if not paths.is_versioned(n)]
    if unversioned:
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "mode-mixed",
                    f"{', '.join(unversioned)}: a new node is a proposal like anyone else's "
                    "(D-29, F08-Q3) and belongs in its own pull request; a curator pull request "
                    "adds status records and versioned nodes only (F08-R8)",
                    {"nodes": unversioned},
                ),
            ),
        )
    if len(new_dirs) > 1:
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "mode-multi-node",
                    "a revision adds one versioned node (D-8); this one adds "
                    + ", ".join(new_dirs),
                    {"nodes": new_dirs},
                ),
            ),
        )
    if author is None or author not in curators.logins:
        who = "unknown" if author is None else repr(author)
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "curator-unlisted",
                    f"status records and versioned nodes are a curator's act (D-8, D-29, D-33) and "
                    f"the pull request's author ({who}) is not listed in {CURATORS_FILE}",
                    {"author": author, "listed": sorted(curators.logins)},
                ),
            ),
        )
    admit = new_dirs[0] if new_dirs else None
    nodes = sorted({loc.node_id for loc in located if loc.node_id is not None})
    node_id = admit or (nodes[0] if len(nodes) == 1 else None)
    reviewers = tuple(sorted(curators.logins - {author}))
    return Classification(
        "curator", target_id, node_id, tuple(located), admit=admit, reviewers=reviewers
    )


def _classify_intake(  # noqa: PLR0913 — one return per refusal; the diff and the host's fact
    located: list[Located],
    changes: list[Change],
    target_id: str,
    new_dirs: list[str],
    *,
    author: str | None,
    curators: Curators,
) -> Classification:
    """F11-R2 (D-6): a curated target enters whole, by a listed curator, and its root is admitted.

    The pull request adds the target's record, its gate-spec, its definitions, the certificates
    intake wrote and its status record, plus exactly one node directory — the root — and
    nothing else: no proof, no append, no second node. Everything is an addition, since the
    target did not exist. The root is admitted in the sandbox like a proposal's node, and
    admission builds ``defs/`` before the root's Context, so the definitions are checked by the
    same act (F11-Q13). D-6's artifact rules on the record itself are ``intake new``'s and run
    where the curator ran it; the gate's step here is the shape and the author.
    """
    roles = {loc.role for loc in located}
    # F14-R4: an import may carry the root's catalog evidence and the attempts its row names.
    # F15-R13, Q8: a proposal's intake carries the proposer's steward record, signed offline.
    allowed = (
        set(paths.INTAKE_ROLES)
        | set(paths.NODE_ROLES)
        | {
            "target-status",
            "statement-evidence",
            "attempts-ledger",
            "steward",
        }
    )
    if not roles <= allowed:
        return Classification(None, target_id, None, tuple(located), (_mixed(roles),))
    modified = sorted(c.path for c in changes if c.status != "A")
    if modified:
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "mode-mixed",
                    f"{', '.join(modified)}: an intake adds a target that did not exist; nothing "
                    "in it is a modification (F11-R2, D-3)",
                    {"paths": modified},
                ),
            ),
        )
    for role, name in (("target-record", "target.yaml"), ("gate-spec", "gate-spec.json")):
        if role not in roles:
            return Classification(
                None,
                target_id,
                None,
                tuple(located),
                (
                    Diagnostic(
                        "intake-incomplete",
                        f"an intake adds targets/{target_id}/{name}; this one does not (F11-R2)",
                        {"missing": name},
                    ),
                ),
            )
    if len(new_dirs) != 1:
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "intake-root",
                    "an intake adds exactly one node, the root (F11-R2, D-6); this one adds "
                    + (", ".join(new_dirs) if new_dirs else "none"),
                    {"nodes": new_dirs},
                ),
            ),
        )
    if author is None or author not in curators.logins:
        who = "unknown" if author is None else repr(author)
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "curator-unlisted",
                    f"a target is taken in by a curator (D-6, F11-R2) and the pull request's "
                    f"author ({who}) is not listed in {CURATORS_FILE}",
                    {"author": author, "listed": sorted(curators.logins)},
                ),
            ),
        )
    root = new_dirs[0]
    reviewers = tuple(sorted(curators.logins - {author}))
    return Classification(
        "intake", target_id, root, tuple(located), admit=root, reviewers=reviewers
    )


def definitions_added(changes: Iterable[Change]) -> list[Located] | None:
    """The diff's files when it is new ``defs/`` files of one target and nothing else (F11-R15),
    else ``None``. The shape alone, without the author: the sandbox step that elaborates them is
    told no author, and who may open such a pull request is ``classify``'s question."""
    located: list[Located] = []
    for change in changes:
        if _locate_change(change, located):
            return None
    if not located or {loc.role for loc in located} != {"definition"}:
        return None
    return located if len({loc.target_id for loc in located}) == 1 else None


def _classify_definitions(
    located: list[Located], target_id: str, *, author: str | None, curators: Curators
) -> Classification:
    """F11-R15 (D-3; Q35): new ``defs/`` files alone are a listed curator's pull request.

    Every change is an addition: a definition is immutable, so ``_locate_change`` has already
    refused a rewrite or a deletion by path, and nothing else may ride along (the caller routes
    here only when definitions are the whole diff). That the target exists, that each name can
    be a module and that none collides with one already there are ``check_definitions``'s, which
    reads the tree; that they elaborate is the sandbox's (``cli.run_exhibits``).
    """
    if author is None or author not in curators.logins:
        who = "unknown" if author is None else repr(author)
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "curator-unlisted",
                    f"a shared definition is added by a curator, never by a prover (D-3, "
                    f"F11-R15), and the pull request's author ({who}) is not listed in "
                    f"{CURATORS_FILE}",
                    {"author": author, "listed": sorted(curators.logins)},
                ),
            ),
        )
    reviewers = tuple(sorted(curators.logins - {author}))
    return Classification(
        "curator", target_id, None, tuple(located), reviewers=reviewers, author=author
    )


def _classify_posting(
    located: list[Located], target_id: str, *, author: str | None, curators: Curators
) -> Classification:
    """F11-R5 (D-10): ``targets/<id>/target.yaml`` modified alone is ``intake post``'s curator PR.

    The shape is all the diff can say; that the modification is the posting and nothing else is
    ``check_posting``'s, which needs the base. The record is the only path in the pull request —
    the caller routes here only when it is — so the one-node rule has nothing to count.
    """
    if author is None or author not in curators.logins:
        who = "unknown" if author is None else repr(author)
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "curator-unlisted",
                    f"recording a target's D-10 posting is a curator's act (F11-R5) and the pull "
                    f"request's author ({who}) is not listed in {CURATORS_FILE}",
                    {"author": author, "listed": sorted(curators.logins)},
                ),
            ),
        )
    reviewers = tuple(sorted(curators.logins - {author}))
    return Classification(
        "curator", target_id, None, tuple(located), reviewers=reviewers, author=author
    )


_CERTIFICATE_NAME_RE = re.compile(r"^(?P<subject>.+)-[1-9][0-9]*\.ya?ml$")


def certificate_subject(path: str) -> str:
    """The subject a certificate's file name gives (``fidelity/<subject>-<n>.yaml``, F11-R3), or
    the bare file name when it follows no such pattern (then ``check_certificate`` refuses it)."""
    name = PurePosixPath(path).name
    m = _CERTIFICATE_NAME_RE.match(name)
    return m.group("subject") if m else name


def _classify_certificate(
    located: list[Located], target_id: str, *, author: str | None
) -> Classification:
    """F11-R3, D-9: new certificates for one subject, and nothing else, are the signer's own PR.

    Every change is an addition — a certificate is not modifiable, so ``_locate_change`` has
    already refused a rewrite or a deletion by path. Who may open it is not a curator question:
    the pull request's author must be the certificate's attestor, which is in the file, so it is
    ``check_certificate``'s, with the other content rules. No reviewer is named: D-9's non-author
    signature *is* the review of the statement, and asking another person to approve it would
    make the signer's act someone else's.
    """
    subjects = sorted({certificate_subject(loc.path) for loc in located})
    if len(subjects) != 1:
        return Classification(
            None,
            target_id,
            None,
            tuple(located),
            (
                Diagnostic(
                    "certificate-subjects",
                    "a certificate pull request signs one subject (F11-R3, D-9); this one adds "
                    "certificates for " + ", ".join(subjects),
                    {"subjects": subjects},
                ),
            ),
        )
    return Classification("fidelity", target_id, None, tuple(located), author=author)


def _mixed(roles: set[Role]) -> Diagnostic:
    return Diagnostic(
        "mode-mixed",
        "this pull request mixes kinds of change that belong in separate ones: "
        + ", ".join(sorted(roles)),
        {"roles": sorted(roles)},
    )


def _locate_change(change: Change, located: list[Located]) -> list[Diagnostic]:
    """Place one change, or say why it is outside every mode. Appends to ``located`` on success."""
    if change.old_path is not None:
        return [
            Diagnostic(
                "path-forbidden",
                f"{change.old_path} -> {change.path}: nothing in the graph is renamed",
                {"path": change.old_path, "status": change.status},
            )
        ]
    where = paths.locate(change.path)
    if where is None:
        return [
            Diagnostic(
                "path-forbidden",
                f"{change.path} is not a path any submission may touch",
                {"path": change.path, "status": change.status},
            )
        ]
    allowed: tuple[str, ...] = ("A", "M") if where.role in paths.MODIFIABLE_ROLES else ("A",)
    if change.status not in allowed:
        return [
            Diagnostic(
                "path-forbidden",
                f"{change.path}: a {where.role} may not be {_verb(change.status)}",
                {"path": change.path, "status": change.status, "role": where.role},
            )
        ]
    located.append(where)
    return []


#: The roles the explainer mode carries: prose about Lean that asserts nothing a kernel checks,
#: and the signatures on it (F15-R8; F20-R1).
#: A withdrawal reaches this table only when it withdraws a gloss or explainer version (F20-R7):
#: ``classify`` sends every other withdrawal to the curator mode first.
EXPLAINER_FAMILY: frozenset[Role] = frozenset(
    {"explainer", "explainer-signature", "gloss", "gloss-signature", "withdrawal"}
)


def withdraws_version(graph_root: Path, path: str) -> bool:
    """Whether the withdrawal at ``path`` names a gloss or explainer version (F20-R7). One that
    cannot be read names nothing, so it stays a curator record and is refused there (C7)."""
    try:
        doc = yaml.safe_load((graph_root / path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return False
    named = doc.get("withdraws") if isinstance(doc, dict) else None
    return isinstance(named, str) and named.startswith(VERSION_DIRS)


#: The directories whose files are versions of a chain (D-3 v3.30), as a withdrawal names them.
VERSION_DIRS: tuple[str, ...] = ("gloss/", "explainer/")


def _mode_for(roles: set[Role]) -> Mode | None:  # noqa: PLR0911 — one return per mode
    appendish = set(paths.APPEND_ROLES)
    if "node" in roles:  # F08-R2: a whole new directory, and nothing outside it
        # F18-R8: a proposal may carry its node's first proposed-for record.
        allowed = set(paths.NODE_ROLES) | {"node-status", "proposed-for"}
        return "proposal" if roles <= allowed else None
    if roles == {"witness"}:  # F08-R5: filling a hole's slot
        return "proposal"
    if roles & (set(paths.NODE_ROLES) | {"node-status"}):
        return None  # a node file or a status record outside a new directory, with other things
    if "proposed-for" in roles:  # F18-R8: a pointer is a pull request of its own
        return "proposed-for" if roles == {"proposed-for"} else None
    if "proof" in roles or "waiver" in roles:
        return "proof" if roles <= ({"proof", "waiver"} | appendish) else None
    if "alternate" in roles:  # D-25 v3.13: a later proof of a proved node, plus appends
        return "alternate" if roles <= ({"alternate"} | appendish) else None
    if "partial" in roles:
        # F07-R23: the assembly, the witnesses it carries for its holes, and appends. A carried
        # witness with no assembly beside it falls through to the end and fits no mode.
        return "partial" if roles <= ({"partial", "hole-witness"} | appendish) else None
    if roles & EXPLAINER_FAMILY:
        # F15-R8: signature files alone, or with new explainers, are the explainer mode; F20-R1
        # (D-3 v3.30): so are glosses, prose about a Lean file that asserts as little.
        return "explainer" if roles <= EXPLAINER_FAMILY else None
    # F15: a steward record, a write-up or a policy file is nobody's append; only D-13's,
    # D-31's and D-14's records reach the append mode.
    return "append" if roles <= appendish else None


def _rejected(problems: list[Diagnostic]) -> Classification:
    return Classification(None, None, None, (), tuple(problems))


def _verb(status: str) -> str:
    return {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}[status]


# --- the checks the non-building modes run instead of a build ----------------------------------


def check_as_service(
    root: Path,
    path: str,
    content: bytes,
    *,
    service_login: str = config.DEFAULT_SERVICE_LOGIN,
    signer: Signer | None = None,
) -> list[Diagnostic]:
    """The gate's classifier and checks over ``root`` with one new file at ``path``, as the merge
    would run them on a pull request the service opened adding it: every problem, or none. The
    file is written into ``root`` and left there; ``root`` is the caller's scratch tree.

    One function for both callers that must judge a gloss, explainer or withdrawal before any
    pull request exists (F20-T6, T10): the service's pre-flight, over the files it fetched from
    the host, and the drafter's own check of each draft (R16), over a copy of its checkout — so
    neither restates a rule."""
    dest = root / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    try:
        curators = load_curators(root)
    except CuratorsError:
        curators = Curators()
    classification = classify(
        [Change("A", path)],
        author=service_login,
        curators=curators,
        graph_root=root,
        service_login=service_login,
    )
    problems = list(classification.problems)
    if classification.ok:
        problems.extend(check(root, classification, signer=signer))
    return problems


def check(  # noqa: PLR0912 — one branch per role with a check of its own
    graph_root: Path,
    classification: Classification,
    *,
    base: BaseReader | None = None,
    signer: Signer | None = None,
) -> list[Diagnostic]:
    """R9, R10, F08-R2, R5, R8: everything a pull request is checked for before any sandbox.

    Content rules that belong to a file rather than to a mode — an annex is named for its own
    content, a postmortem validates against its schema — are applied to those files wherever they
    appear, so a proof that carries an append is held to the same rules. A proposal's shape and a
    witness completion's precondition are mode rules, checked here so a malformed proposal never
    costs a sandbox.

    ``signer`` verifies the signed records the explainer mode reads (stewards, signatures); by
    default the platform's ssh-keygen. The service passes its own verifier, since its runtime
    has no OpenSSH (F06-Q6, F20-T6).
    """
    problems: list[Diagnostic] = []
    for located in classification.located:
        if located.role in paths.APPEND_ROLES:
            problems.extend(check_append_file(graph_root, located, mode=classification.mode))
        elif located.role == "explainer":
            found = check_explainer_file(graph_root, located, classification)
            problems.extend(
                found
                or check_draft_provenance(graph_root, located, classification)
                or check_version_head(graph_root, located)
                or check_model_lock(graph_root, located, signer=signer)
                or check_own_edit_opener(graph_root, located, classification, signer=signer)
            )
        elif located.role == "explainer-signature":
            problems.extend(
                check_explainer_signature(graph_root, located, classification, signer=signer)
            )
        elif located.role == "gloss":
            found = glosses.check_gloss(graph_root, located)
            problems.extend(
                found
                or check_draft_provenance(graph_root, located, classification)
                or check_version_head(graph_root, located)
                or check_model_lock(graph_root, located, signer=signer)
                or check_own_edit_opener(graph_root, located, classification, signer=signer)
            )
        elif located.role == "gloss-signature":
            problems.extend(
                check_gloss_signature(graph_root, located, classification, signer=signer)
            )
        elif located.role == "statement-evidence":
            problems.extend(check_evidence(graph_root, located))
        elif located.role in ("formalization", "formalization-statement"):
            problems.extend(check_formalization(graph_root, located))
        elif located.role == "steward":
            problems.extend(check_steward_record(graph_root, located, classification))
        elif located.role == "writeup":
            problems.extend(check_writeup_record(graph_root, located, classification))
        elif located.role == "proposed-for":
            problems.extend(check_proposed_for(graph_root, located, classification))
        elif located.role == "policy":
            # F15-R3: the switch validates; who may flip it is the curator mode's author rule.
            data = _read(graph_root, located)
            problems.extend(
                [data] if isinstance(data, Diagnostic) else _check_schema(located, data)
            )
        elif located.role == "withdrawal":
            problems.extend(check_withdrawal(graph_root, located, classification, signer=signer))
        elif located.role == "credit-correction":
            problems.extend(check_credit_correction(graph_root, located))
        elif located.role in paths.CURATOR_ROLES:
            problems.extend(check_status_record(graph_root, located, classification))
        elif located.role == "target-record" and classification.mode == "curator":
            problems.extend(check_posting(graph_root, located, base))
    if classification.mode == "curator":
        problems.extend(check_definitions(graph_root, classification))
    if classification.mode == "proposal":
        problems.extend(check_proposal(graph_root, classification, base))
    if classification.mode == "fidelity":
        problems.extend(check_certificate(graph_root, classification))
    if classification.mode == "alternate":
        problems.extend(check_alternate(graph_root, classification))
    problems.extend(check_replaced_proof(graph_root, classification))
    return problems


def warnings(graph_root: Path, classification: Classification) -> list[Diagnostic]:
    """What the gate tells a pull request without refusing it (F20-R5). Never a problem: the
    classification's ``ok`` does not read these. Today: ``explainer-name-unanchored`` on each
    explainer record whose anchored sections cite a name their steps do not use."""
    from opn_gate import explainers  # noqa: PLC0415 — explainers reads glosses, as this does

    found: list[Diagnostic] = []
    for located in classification.located:
        if located.role == "explainer" and located.node_id is not None:
            found.extend(explainers.name_warnings(graph_root, located))
    return found


def check_definitions(graph_root: Path, classification: Classification) -> list[Diagnostic]:
    """F11-R15: what a definition added after intake is held to before any sandbox.

    The target must be on the record: the diff adds no gate-spec (it would be an intake), so one
    in the tree was there on the base, and without one this is an intake that forgot everything
    but its definitions (R2). Then the merged ``defs/`` must still be buildable as modules — each
    name a Lean identifier, each import a library module or another definition, no cycle — which
    is ``defs.order``'s answer with its own diagnostics; and no new name may differ from another
    only in case, since those are one file on a case-folding checkout and two modules in the
    sandbox. The same path cannot be added twice: git calls that a modification, refused by path.
    """
    added = [loc for loc in classification.located if loc.role == "definition"]
    if not added or classification.target_id is None:
        return []
    target_id = classification.target_id
    spec = layout.gate_spec_path(graph_root, target_id)
    if not spec.is_file():
        return [
            Diagnostic(
                "intake-incomplete",
                f"targets/{target_id} is not a target on this graph: a definition is added to "
                "a target that exists (F11-R15), and a new target arrives whole, in an intake "
                f"that adds targets/{target_id}/gate-spec.json (F11-R2)",
                {"missing": "gate-spec.json"},
            )
        ]
    target_dir = spec.parent
    ordered = defs.order(target_dir)
    if isinstance(ordered, Diagnostic):
        return [ordered]
    problems: list[Diagnostic] = []
    present = sorted(p.name for p in defs.target_defs_dir(target_dir).glob("*.lean"))
    for loc in added:
        name = PurePosixPath(loc.path).name
        twins = [other for other in present if other != name and other.lower() == name.lower()]
        if twins:
            problems.append(
                Diagnostic(
                    "defs-clash",
                    f"defs/{name} differs from defs/{twins[0]} only in case: one file on a "
                    "case-folding checkout and two modules in the sandbox; choose another name",
                    {"file": name, "existing": twins[0]},
                )
            )
    return problems


def check_status_record(  # noqa: PLR0911 — one return per rule
    graph_root: Path, located: Located, classification: Classification
) -> list[Diagnostic]:
    """A status record validates against its schema; inside a proposer's new node it may only
    say ``speculative`` (F08-Q2) — every other status is a curator's judgment (D-8, D-14, D-18).
    A target declared ``active`` is held to activation's rule (``check_activation``)."""
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems = _check_schema(located, data, code="record-invalid")
    if problems:
        return problems
    if located.role == "target-status":
        return check_activation(graph_root, located, data, classification)
    if classification.mode != "proposal":
        if located.role == "node-status":
            return check_dispute_reference(graph_root, located, data)
        return problems
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]  # defence in depth: _check_schema just parsed this same document
    if doc.get("status") != PROPOSAL_STATUS:
        return [
            Diagnostic(
                "proposal-status",
                f"{located.path}: a proposal may mark its node {PROPOSAL_STATUS!r} and nothing "
                f"else (D-14, F08-Q2); {doc.get('status')!r} is a curator's record (F08-R8)",
                {"path": located.path, "status": doc.get("status")},
            )
        ]
    return []


def check_dispute_reference(graph_root: Path, located: Located, data: bytes) -> list[Diagnostic]:
    """F08-T38 (D-18 v3.28): a ``disputed`` record names the defect claim it accepts — a valid,
    standing claim on its own node — by the curator command's own rule (``curator.accepted_claim``,
    F08-T35), so a hand-written record is held to what the command writes. Without a claim it
    could never lift when one is withdrawn (``graph.disputed_is_void``, F08-T32). Every other
    status (``abandoned``, D-14) takes no claim and is not asked."""
    from opn_gate import curator  # noqa: PLC0415 — curator pulls in the toolchain steps

    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]  # defence in depth: _check_schema just parsed this same document
    if doc.get("status") != curator.DISPUTED or located.node_id is None:
        return []
    reference = doc.get("reference")
    node_dir = PurePosixPath(located.path).parent.parent
    try:
        curator.accepted_claim(
            graph_root / node_dir,
            located.target_id,
            located.node_id,
            None if reference is None else str(reference),
        )
    except curator.CuratorError as exc:
        return [
            Diagnostic(
                "dispute-claim-unnamed",
                f"{located.path}: a disputed record names the defect claim on this node it "
                f"accepts for adjudication (D-18 v3.28); {exc}",
                {"path": located.path, "reference": reference},
            )
        ]
    return []


def check_steward_record(  # noqa: PLR0911 — one return per rule
    graph_root: Path,
    located: Located,
    classification: Classification,
    *,
    signer: Signer | None = None,
) -> list[Diagnostic]:
    """F15-R1, R2: a steward record validates, names the target it sits under, is numbered as
    R1 lays them out, and *counts* — its signature verifies under its own key, its sentence is
    the fixed one, and a step-down is signed with the key its login committed with. A record
    that would merge and count for nothing is refused here by name instead.

    The verdict is sequential: the target's records are checked in order with the pull
    request's own among them, so a step-down is judged against the commit it undoes, and only
    the pull request's files are reported.
    """
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems = _check_schema(located, data, code="record-invalid")
    if problems:
        return problems
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    if doc.get("target") != located.target_id:
        return [
            Diagnostic(
                "steward-target",
                f"{located.path} is a record for target {doc.get('target')!r}, and it sits under "
                f"targets/{located.target_id}/ (F15-R1)",
                {"path": located.path, "target": doc.get("target")},
            )
        ]
    name = PurePosixPath(located.path).name
    if not re.match(r"^[1-9][0-9]*\.ya?ml$", name):
        return [
            Diagnostic(
                "steward-name",
                f"{located.path}: a steward record is stewards/<n>.yaml, numbered (F15-R1)",
                {"path": located.path},
            )
        ]
    target_dir = graph_root / "targets" / located.target_id
    if not intake.record_path(target_dir).is_file() and not any(
        loc.role == "target-record" for loc in classification.located
    ):
        return [
            Diagnostic(
                "steward-uncurated",
                f"{located.target_id} has no {intake.TARGET_FILE}: a steward commits to a "
                "curated target (F15-R1, D-6 v3.17)",
                {"target": located.target_id},
            )
        ]
    try:
        checked = steward.check(steward.load(target_dir), signer or signed.default_signer())
    except schemas.SchemaError as exc:  # an earlier record no longer reads: a graph defect
        return [Diagnostic("record-invalid", str(exc), {"path": located.path})]
    verdict = next((c for c in checked if c.record.path.name == name), None)
    if verdict is None:  # defence in depth: the file was read above
        return [
            Diagnostic(
                "steward-name",
                f"{located.path} is not among the target's numbered records",
                {"path": located.path},
            )
        ]
    return [
        Diagnostic(
            problem.split(":", 1)[0],
            f"{located.path}: {problem}",
            {"path": located.path, "login": verdict.record.login},
        )
        for problem in verdict.problems
    ]


def check_writeup_record(
    graph_root: Path,
    located: Located,
    classification: Classification,
    *,
    signer: Signer | None = None,
) -> list[Diagnostic]:
    """F15-R6: a write-up record validates, names the target it sits under, is numbered, its
    signature verifies under its own key, and its signer is an active steward of the target or
    a listed curator (``real_identities``) — the stewards read with the pull request's own
    records in the tree, so a steward may commit and record in one pull request."""
    from opn_gate import writeup  # noqa: PLC0415 — only this check reads write-ups

    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems = _check_schema(located, data, code="record-invalid")
    if problems:
        return problems
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    if doc.get("target") != located.target_id:
        return [
            Diagnostic(
                "writeup-target",
                f"{located.path} is a record for target {doc.get('target')!r}, and it sits under "
                f"targets/{located.target_id}/ (F15-R6)",
                {"path": located.path, "target": doc.get("target")},
            )
        ]
    if not re.match(r"^[1-9][0-9]*\.ya?ml$", PurePosixPath(located.path).name):
        return [
            Diagnostic(
                "writeup-name",
                f"{located.path}: a write-up record is writeup/<n>.yaml, numbered (F15-R6)",
                {"path": located.path},
            )
        ]
    verifier = signer or signed.default_signer()
    found: list[Diagnostic] = []
    if not signed.verifies(doc, verifier):
        found.append(
            Diagnostic(
                "writeup-signature",
                f"{located.path}: the signature does not verify under the record's key",
                {"path": located.path},
            )
        )
    who = str(doc.get("signer"))
    if who not in real_identities(graph_root, located.target_id, signer=verifier):
        found.append(
            Diagnostic(
                "writeup-signer",
                f"{located.path}: {who!r} is neither an active steward of {located.target_id} "
                "nor a listed curator; a write-up record is theirs to sign (F15-R6, Q4)",
                {"path": located.path, "signer": who},
            )
        )
    del writeup  # the record's shape is the schema's; nothing else is read here
    return found


def check_formalization(graph_root: Path, located: Located) -> list[Diagnostic]:
    """F14-R7: a formalization arrives as its record and its statement, and the pair is sound —
    one sorry-bodied theorem, declared and hashed as the record says, never a node's name, library
    and ``Defs.*`` imports only (``formalizations.problems``). The record's path carries the
    check; its statement is checked through it, so a pair is reported once, and a statement with no
    record beside it is ``formalization-incomplete``. That it is added, not modified, is the curator
    mode's rule (a formalization is not a modifiable role)."""
    from opn_gate import formalizations  # noqa: PLC0415 — only these paths need it

    parts = PurePosixPath(located.path).parts
    name = parts[3] if len(parts) > 3 else ""
    target_dir = graph_root / "targets" / located.target_id
    record = formalizations.formalizations_dir(target_dir) / name / formalizations.RECORD_FILE
    if located.role == "formalization-statement" and record.is_file():
        return []
    return formalizations.problems(target_dir, name)


def check_evidence(graph_root: Path, located: Located) -> list[Diagnostic]:
    """F14-R3: an evidence record validates, and it speaks for the root as it stands at head.

    A record pinned to another statement would count for nothing at step 9, so adding one is a
    mistake the curator hears about now (``evidence-stale``) rather than a record that silently
    does nothing. Whether the score is the catalog's is the curator's act, like the record
    itself; the attestation cites the file, so the claim is public (F14-R6)."""
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems = _check_schema(located, data, code="record-invalid")
    if problems:
        return problems
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    target_dir = graph_root / "targets" / located.target_id
    try:
        current = qa.subject_hash(target_dir, fidelity.ROOT_SUBJECT)
    except ValueError as exc:  # QaError, GraphError, SchemaError: the root does not read
        return [
            Diagnostic(
                "evidence-unreadable",
                f"{located.path}: the root's statement does not read: {exc}",
                {"path": located.path},
            )
        ]
    if doc.get("statement_hash") != current:
        return [
            Diagnostic(
                "evidence-stale",
                f"{located.path}: pinned to {doc.get('statement_hash')}, and the root's statement "
                f"as it stands is {current} (F14-R3)",
                {"path": located.path, "recorded": doc.get("statement_hash"), "current": current},
            )
        ]
    return []


_ABSENT = object()


def check_posting(  # noqa: PLR0911 — one return per rule
    graph_root: Path, located: Located, base: BaseReader | None
) -> list[Diagnostic]:
    """F11-R5, D-10: a modified target record records its posting and nothing else.

    Two facts, one from each side of the diff: at the base ``posting`` was null (``intake post``
    records a posting once, so a rewrite or a removal is refused), and at the head it is a
    posting the record's schema accepts — with every other field exactly as it was, because the
    record's other fields are D-6's artifacts and are not re-opened by posting (F11-Q10).
    """
    if base is None:
        return [
            Diagnostic(
                "posting-unverified",
                f"{located.path}: whether the target had no posting before is a fact about the "
                "base commit, which this check was not given (F11-R5)",
                {"path": located.path},
            )
        ]
    before_bytes = base(located.path)
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    after = _document(located, data)
    if isinstance(after, Diagnostic):
        return [after]
    before = _document(located, before_bytes) if before_bytes is not None else None
    if not isinstance(before, dict):
        return [
            Diagnostic(
                "posting-unverified",
                f"{located.path}: the base commit holds no readable target record to compare the "
                "posting against (F11-R5)",
                {"path": located.path},
            )
        ]
    declared = intake.record_schema(after)  # D-34: validated at the version it declares
    violations = schemas.violations(after, declared)
    if violations:
        return [
            Diagnostic(
                "record-invalid",
                f"{located.path} does not satisfy {declared}: {v.path}: {v.message}",
                {"path": located.path, "schema": declared, "field": v.path},
            )
            for v in violations[:5]
        ]
    changed = sorted(
        key
        for key in set(before) | set(after)
        if key != "posting" and before.get(key, _ABSENT) != after.get(key, _ABSENT)
    )
    if changed:
        return [
            Diagnostic(
                "posting-fields",
                f"{located.path}: a curator modifies a target record only to record its D-10 "
                f"posting (F11-R5); this change also edits {', '.join(changed)}",
                {"path": located.path, "fields": changed},
            )
        ]
    if before.get("posting") is not None:
        return [
            Diagnostic(
                "posting-recorded",
                f"{located.path}: the target is already posted at {before['posting'].get('url')}; "
                "a posting is recorded once and never rewritten or removed (F11-R5, D-10)",
                {"path": located.path, "posting": before["posting"]},
            )
        ]
    if after.get("posting") is None:
        return [
            Diagnostic(
                "posting-absent",
                f"{located.path}: the change records no posting; a curator modifies a target "
                "record only to record its D-10 posting (F11-R5)",
                {"path": located.path},
            )
        ]
    return []


def check_certificate(  # noqa: PLR0911, PLR0912, PLR0915 — one return per rule that stops the rest
    graph_root: Path, classification: Classification
) -> list[Diagnostic]:
    """F11-R3, D-9, F12-R9: a certificate pull request is its signer's, on a screened statement.

    In order: the target is curated (its ``target.yaml`` is in the tree — and since this pull
    request adds certificates only, the head's record is the base's); every added file is a
    certificate valid at the version it declares, named for the one subject it grades, which is
    the root or one of the target's definitions. Then, per certificate: it is ``fidelity/v2`` and
    pinned to the subject's hash at head (F11-T9: anything else merges and counts for nothing,
    ``certificate-unpinned`` / ``certificate-stale``); the pull request's author is its attestor;
    it agrees with the subject's author on record (the earliest certificate already in the tree);
    and from ``screened-and-signed`` up the attestor is not that author. Last, for a signature,
    the subject's QA pass is complete for the statement as it stands, read from the files alone
    (``qa.require_complete``) — the exhibit replay F12-R9 adds belongs to the command, which runs
    where a toolchain is; this mode starts no sandbox.
    """
    target_id = classification.target_id
    assert target_id is not None
    target_dir = graph_root / "targets" / target_id
    if not intake.record_path(target_dir).is_file():
        return [
            Diagnostic(
                "certificate-uncurated",
                f"{target_id} has no {intake.TARGET_FILE}: certificates stand beside a curated "
                "target (F11-R3), and a new target's certificates ride in its intake (F11-R2)",
                {"target": target_id},
            )
        ]
    docs: list[tuple[Located, dict[str, Any]]] = []
    problems: list[Diagnostic] = []
    for located in classification.located:
        data = _read(graph_root, located)
        doc = data if isinstance(data, Diagnostic) else _document(located, data)
        if isinstance(doc, Diagnostic):
            problems.append(doc)
            continue
        # Validated against the version the file declares, from the set the reader accepts
        # (D-34); whether that version may still be *added* is the unpinned rule below.
        declared = str(doc.get("schema"))
        if declared not in fidelity.READABLE_SCHEMAS:
            problems.append(
                Diagnostic(
                    "certificate-invalid",
                    f"{located.path} declares {declared!r}; a fidelity certificate is one of "
                    f"{', '.join(fidelity.READABLE_SCHEMAS)}",
                    {"path": located.path, "schema": declared},
                )
            )
            continue
        violations = schemas.violations(doc, declared)
        problems.extend(
            Diagnostic(
                "certificate-invalid",
                f"{located.path} does not satisfy {declared}: {v.path}: {v.message}",
                {"path": located.path, "schema": declared, "field": v.path},
            )
            for v in violations[:5]
        )
        if not violations:
            docs.append((located, doc))
    if problems:
        return problems
    for located, doc in docs:
        if certificate_subject(located.path) != doc["subject"]:
            problems.append(
                Diagnostic(
                    "certificate-name",
                    f"{located.path} grades {doc['subject']!r}; a certificate is named "
                    f"fidelity/<subject>-<n>.yaml for the subject it grades (F11-R3)",
                    {"path": located.path, "subject": doc["subject"]},
                )
            )
    if problems:
        return problems
    subject = str(docs[0][1]["subject"])
    known = fidelity.subjects_of(target_dir)
    if subject not in known:
        return [
            Diagnostic(
                "certificate-subject",
                f"{subject!r} is not a fidelity subject of {target_id}; D-9's subjects are the "
                f"root and each definition: {', '.join(known)}",
                {"subject": subject, "subjects": list(known)},
            )
        ]
    added = {PurePosixPath(loc.path).name for loc, _ in docs}
    try:
        on_disk = fidelity.load(target_dir).get(subject, [])
    except ValueError as exc:  # SchemaError: an earlier certificate no longer reads
        return [Diagnostic("certificate-invalid", str(exc), {"subject": subject})]
    on_record = fidelity.author_of([c for c in on_disk if c.path.name not in added])
    try:
        current = fidelity.current_hash(target_dir, subject)
    except ValueError as exc:  # QaError: the root does not load, so no statement to pin
        current = None
        unhashable: str | None = str(exc)
    else:
        unhashable = None
    author = classification.author
    for located, doc in docs:
        attestor, grade = str(doc["attestor"]), str(doc["grade"])
        subject_author = str(doc["subject_author"])
        if doc["schema"] != fidelity.SCHEMA:
            problems.append(
                Diagnostic(
                    "certificate-unpinned",
                    f"{located.path} is {doc['schema']}, which pins no statement and counts for "
                    f"nothing; a new certificate is {fidelity.SCHEMA}, pinned to the statement it "
                    "signs (D-9, F12-R9)",
                    {"path": located.path, "schema": doc["schema"]},
                )
            )
        elif doc["statement_hash"] != current:
            pinned = doc["statement_hash"]
            problems.append(
                Diagnostic(
                    "certificate-stale",
                    f"{located.path} is pinned to {pinned}, and {subject!r} as it stands is "
                    + (current if current is not None else f"unreadable ({unhashable})")
                    + ": a certificate counts only for the statement it was signed against "
                    "(D-9, F12-R9)",
                    {"path": located.path, "statement_hash": pinned, "current": current},
                )
            )
        if author is None or attestor != author:
            who = "unknown" if author is None else repr(author)
            problems.append(
                Diagnostic(
                    "certificate-attestor",
                    f"{located.path} is attested by {attestor!r} and the pull request was opened "
                    f"by {who}: a certificate is its signer's own pull request (F11-R3, D-9)",
                    {"path": located.path, "attestor": attestor, "author": author},
                )
            )
        if on_record is not None and subject_author != on_record:
            problems.append(
                Diagnostic(
                    "certificate-author",
                    f"{located.path} names {subject_author!r} as the author of {subject!r}, which "
                    f"is on record as authored by {on_record!r}; a subject has one author (D-9)",
                    {
                        "path": located.path,
                        "subject_author": subject_author,
                        "on_record": on_record,
                    },
                )
            )
        if fidelity.is_signature(grade) and attestor == subject_author:
            problems.append(
                Diagnostic(
                    "certificate-self-signed",
                    f"{located.path}: {attestor!r} authored {subject!r}, so they cannot attest it "
                    f"at {grade!r}; every rung from {fidelity.SIGNED_FROM} up is a non-author's "
                    "signature (D-9, F11-R3)",
                    {"path": located.path, "attestor": attestor, "grade": grade},
                )
            )
    if problems:
        return problems
    if any(fidelity.is_signature(str(doc["grade"])) for _, doc in docs):
        try:
            qa.require_complete(target_dir, subject, routed=qa.routed_by_claims(target_dir))
        except ValueError as exc:  # QaError, or a record or root that does not load
            return [
                Diagnostic(
                    "certificate-qa-incomplete",
                    f"{exc} — a signature from {fidelity.SIGNED_FROM} up rests on a complete QA "
                    "pass for the statement as it stands (F12-R9, D-9)",
                    {"subject": subject, "qa_code": getattr(exc, "code", None)},
                )
            ]
    return []


def check_activation(
    graph_root: Path, located: Located, data: bytes, classification: Classification
) -> list[Diagnostic]:
    """F14-R2 (was F11-R4, R5; D-33): a curated target is declared ``active`` only as activation
    allows.

    The rule is ``intake.activation_refusal`` — the one both ``intake activate`` and ``opn-gate
    status <target> active`` apply (F11-T10): from ``listed`` or ``dormant`` only, and not while an
    upstream edit freezes the root (the grade and the posting left the rule with F14-R1).
    A record written any other way reaches the graph through this check instead. The gate sees
    the tree *after* the pull request, whose latest status record is this one, so the status it
    flips from is read with the pull request's own status records left out — the base's, since
    status records are append-only. A target with no ``target.yaml`` keeps F08-R11, since
    claimability is not derived for it (F11-Q4, Q5).
    """
    doc = _document(located, data)
    if isinstance(doc, Diagnostic) or doc.get("status") != intake.ACTIVE:
        return [doc] if isinstance(doc, Diagnostic) else []
    target_dir = graph_root / "targets" / located.target_id
    added = frozenset(
        PurePosixPath(loc.path).name
        for loc in classification.located
        if loc.role == "target-status" and loc.target_id == located.target_id
    )
    try:
        record = intake.load_doc(target_dir)
        if record is None:
            return []
        prior = records.load_target_status(target_dir, exclude=added)
        refusal = intake.activation_refusal_from(
            target_dir, record, prior.status if prior is not None else None
        )
    except ValueError as exc:  # SchemaError, FidelityError, QaError: the inputs do not read
        refusal = f"claimability cannot be derived: {exc}"
    if refusal is None:
        return []
    return [
        Diagnostic(
            "activation-refused",
            f"{located.path}: {located.target_id} cannot be declared active (F11-R4, R5; D-6, "
            f"D-33): {refusal}",
            {"path": located.path, "refusal": refusal},
        )
    ]


def check_proposed_for(  # noqa: PLR0911 — one return per rule
    graph_root: Path, located: Located, classification: Classification
) -> list[Diagnostic]:
    """F18-R8 (D-14 v3.26): a proposed-for record validates, is written by the node's proposer —
    the record's ``author`` is its ``META.yaml`` ``provenance.author`` — or arrives in a pull
    request a listed curator opened, and names one other node of the same target that has not
    been superseded (D-8). Each failure is refused by its own code; a superseded node is refused
    naming its successor, which is the node the record should name.

    The record is a hint: it claims nothing about the mathematics, and nothing derives a status,
    a frontier entry or a dependency from it, so nothing else is asked of it."""
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    found = _check_schema(located, data, code="proposed-for-malformed")
    if found:
        return [
            Diagnostic("proposed-for-malformed", d.message, {**d.details, "path": located.path})
            for d in found
        ][:1]
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):  # defence in depth: _check_schema just parsed it
        return [Diagnostic("proposed-for-malformed", doc.message, {"path": located.path})]
    node_id = str(located.node_id)
    named = str(doc["for"])
    nodes_dir = graph_root / "targets" / located.target_id / "nodes"
    details: dict[str, Any] = {"path": located.path, "node": node_id, "for": named}
    author = str(doc["author"])
    proposer = _proposer_of(nodes_dir / node_id)
    if author != proposer and not _is_curator(graph_root, classification.author):
        return [
            Diagnostic(
                "proposed-for-author",
                f"{located.path}: a proposed-for record is written by the node's proposer "
                f"({proposer!r}) or a listed curator (F18-R8, D-14 v3.26); this one is "
                f"{author!r}, in a pull request opened by "
                f"{classification.author or 'an unknown login'}",
                {**details, "author": author, "proposer": proposer},
            )
        ]
    if named == node_id:
        return [
            Diagnostic(
                "proposed-for-self",
                f"{located.path}: a statement is proposed for another node of its target, never "
                "for itself (F18-R8)",
                details,
            )
        ]
    if not (nodes_dir / named).is_dir():
        return [
            Diagnostic(
                "proposed-for-unknown-node",
                f"{located.path}: {named} is not a node of {located.target_id} (F18-R8)",
                details,
            )
        ]
    successor = _successor_of(nodes_dir, named)
    if successor is not None:
        instead = f" by {successor}: name that node instead" if successor != named else ""
        return [
            Diagnostic(
                "proposed-for-superseded",
                f"{located.path}: {named} has been superseded{instead} (D-8); a statement is "
                "proposed for a live node (F18-R8)",
                {**details, "successor": successor if successor != named else None},
            )
        ]
    return []


def _proposer_of(node_dir: Path) -> str | None:
    """The node's ``provenance.author`` at head, or ``None`` when its META does not read."""
    try:
        meta = schemas.load_yaml(node_dir / "META.yaml")
    except (OSError, schemas.SchemaError):
        return None
    provenance = meta.get("provenance")
    author = provenance.get("author") if isinstance(provenance, dict) else None
    return str(author) if author else None


def _is_curator(graph_root: Path, login: str | None) -> bool:
    """Whether the login that opened the pull request is listed in ``curators.json``."""
    if not login:
        return False
    try:
        return login in load_curators(graph_root).logins
    except CuratorsError:
        return False


def _successor_of(nodes_dir: Path, node_id: str) -> str | None:
    """The end of ``node_id``'s revision chain when a status record says it is superseded (the
    node itself when the record names no sound successor), else ``None`` — ``uses``'s reading."""
    try:
        record = records.load_node_status(nodes_dir / node_id)
    except (OSError, schemas.SchemaError):
        return None
    if record is None or record.status != "superseded":
        return None
    return graphmod.current_id(nodes_dir, node_id)


def check_proposal(
    graph_root: Path, classification: Classification, base: BaseReader | None
) -> list[Diagnostic]:
    """F08-R2, R5: a proposal is a whole node directory, or a witness for a hole's empty slot."""
    node_id = classification.admit
    assert node_id is not None
    roles = {loc.role for loc in classification.located}
    prefix = f"targets/{classification.target_id}/nodes/{node_id}/"
    added = {loc.path[len(prefix) :] for loc in classification.located}
    if roles == {"witness"}:
        return check_witness_completion(graph_root, classification, base)
    required = (*paths.NODE_DEFINITION_FILES, paths.WITNESS_FILE)
    missing = [name for name in required if name not in added]
    if missing:
        return [
            Diagnostic(
                "proposal-incomplete",
                f"a proposal adds a whole node directory (D-3); {node_id} is missing "
                + ", ".join(missing),
                {"node": node_id, "missing": missing},
            )
        ]
    return []


def check_witness_completion(
    graph_root: Path, classification: Classification, base: BaseReader | None
) -> list[Diagnostic]:
    """F08-R5, F07-Q3: ``Witness.lean`` alone may change on a hole whose slot is unfilled.

    Three facts, each from the tree: the node exists (its ``META.yaml`` is at the head, untouched
    by this diff), its origin is a hole's (the post-merge job is the only thing that creates a
    node with a slot), and its witness at the *base* was the slot — so a witness that was already
    real is never replaced, because a witness is as immutable as the statement it serves (D-3).
    """
    located = classification.located[0]
    node_id = located.node_id
    assert node_id is not None
    node_dir = graph_root / "targets" / located.target_id / "nodes" / node_id
    if not (node_dir / "META.yaml").is_file():
        return [
            Diagnostic(
                "proposal-incomplete",
                f"a proposal adds a whole node directory (D-3); {node_id} has no META.yaml, so "
                "this Witness.lean belongs to nothing",
                {"node": node_id, "missing": list(paths.NODE_DEFINITION_FILES)},
            )
        ]
    try:
        meta = schemas.load_yaml(node_dir / "META.yaml")
    except schemas.SchemaError as exc:
        return [Diagnostic("meta-invalid", str(exc), {"node": node_id})]
    origin = str(meta.get("origin"))
    if origin not in graphmod.HOLE_ORIGINS:
        return [
            Diagnostic(
                "witness-not-a-hole",
                f"{node_id} has origin {origin!r}; only a hole's witness slot is filled in after "
                "the node exists (D-29, F07-Q3), and any other witness is immutable (D-3)",
                {"node": node_id, "origin": origin},
            )
        ]
    if base is None:
        return [
            Diagnostic(
                "witness-completion-unverified",
                f"{located.path}: whether the witness slot was still unfilled is a fact about the "
                "base commit, which this check was not given",
                {"path": located.path},
            )
        ]
    before = base(located.path)
    # The slot is unfilled while `sorry` is a token of its code; the slot's own header comment
    # names the word, so a witness filled under that header is real (F08-Q18).
    if before is not None and not layout.mentions_sorry(before.decode("utf-8", errors="replace")):
        return [
            Diagnostic(
                "witness-filled",
                f"{node_id} already has a witness; a witness is immutable once it is real (D-3), "
                "and a different one is a different node",
                {"node": node_id, "path": located.path},
            )
        ]
    return []


def check_append_file(
    graph_root: Path, located: Located, *, mode: Mode | None = None
) -> list[Diagnostic]:
    """One appended record: name, size and schema — plus D-16's pre-triage for a defect claim.
    An append claims nothing a kernel could check, so this is all the gate asks before the
    sandbox; an exhibit's elaboration is the sandbox's (``opn_gate.exhibits``)."""
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems: list[Diagnostic] = []
    if located.role == "defect-claim":
        problems.extend(check_defect_claim(graph_root, located, data, mode=mode))
        if problems:
            return problems
    if located.role == "revision-request" and mode == "curator":
        problems.extend(check_watcher_request(located, data))
        if problems:
            return problems
    if located.role in paths.CONTENT_HASHED_ROLES:
        naming = paths.check_content_hash_name(located, data)
        if naming is not None:
            problems.append(naming)
    if located.role == "annex" and len(data) > paths.ANNEX_MAX_BYTES:
        problems.append(
            Diagnostic(
                "annex-too-large",
                f"{located.path}: {len(data)} bytes; an annex is capped at "
                f"{paths.ANNEX_MAX_BYTES} bytes",
                {"path": located.path, "bytes": len(data), "cap": paths.ANNEX_MAX_BYTES},
            )
        )
    problems.extend(_check_schema(located, data))
    if located.role == "annex" and not problems:
        problems.extend(_check_step_ids(located, data))
    return problems


def _check_step_ids(located: Located, data: bytes) -> list[Diagnostic]:
    """F18-R6: a stepped annex names each step once, since a hole is matched to a step by its
    name; JSON Schema cannot say that of a list of objects, so it is asked here."""
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    repeated = annexmod.duplicate_step_ids(doc)
    if not repeated:
        return []
    return [
        Diagnostic(
            "append-invalid",
            f"{located.path} names the step "
            + ", ".join(repeated)
            + " more than once; a stepped annex's step ids are unique (D-31 v3.26)",
            {"path": located.path, "schema": doc.get("schema"), "duplicates": repeated},
        )
    ]


def referenced_file(located: Located, stmt_ref: str) -> str | None:
    """F08-R7: the file a defect claim points at, from where the record sits — a node's own
    ``Statement.lean`` under ``nodes/<id>/defects/``, a ``defs/`` file under ``defs/defects/``.
    ``None`` when the reference and the location disagree."""
    if located.node_id is not None:
        if stmt_ref != located.node_id:
            return None
        return f"targets/{located.target_id}/nodes/{located.node_id}/Statement.lean"
    if not stmt_ref.startswith("defs/"):
        return None
    return f"targets/{located.target_id}/{stmt_ref}"


def check_defect_claim(  # noqa: PLR0911 — one return per rule
    graph_root: Path, located: Located, data: bytes, *, mode: Mode | None = None
) -> list[Diagnostic]:
    """D-16's pre-triage, repeated in CI as D-35 requires: the class is from the taxonomy and the
    exhibit is present (both the schema's), and the line is an existing line of the referenced
    file (this check's). A claim that fails any of them bounces; nothing is adjudicated here.

    F12-R4, Q7: a ``defect-claim/v2`` claim of class ``screen-finding`` is the screen's, so it
    names the exhibit file the QA record cites, and one that ``routes`` names a screen-finding
    claim in its own directory. In a curator pull request (the QA run's), a claim is the
    screen's or nothing: a curator files their own claims as anyone does, in an append.
    """
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    schema_problems = _check_schema(located, data, code="record-invalid")
    if schema_problems:
        return schema_problems
    finding_problems = check_screen_finding(graph_root, located, doc, mode=mode)
    if finding_problems:
        return finding_problems
    stmt_ref = str(doc.get("stmt_ref"))
    path = referenced_file(located, stmt_ref)
    if path is None:
        return [
            Diagnostic(
                "defect-ref",
                f"{located.path}: stmt_ref {stmt_ref!r} is not the statement this record sits "
                "under (a node's defects/ names that node; defs/defects/ names a defs/ file)",
                {"path": located.path, "stmt_ref": stmt_ref},
            )
        ]
    target = graph_root / path
    if not target.is_file():
        return [
            Diagnostic(
                "defect-ref",
                f"{located.path}: stmt_ref {stmt_ref!r} names no file ({path})",
                {"path": located.path, "stmt_ref": stmt_ref, "file": path},
            )
        ]
    lines = target.read_text(encoding="utf-8").splitlines()
    line = int(doc["line"])
    if line > len(lines):
        return [
            Diagnostic(
                "defect-line",
                f"{located.path}: line {line} is beyond {path}, which has {len(lines)} lines "
                "(D-16: a claim points at a specific line or bounces)",
                {"path": located.path, "line": line, "lines": len(lines), "file": path},
            )
        ]
    return check_circular_claim(graph_root, located, doc)


def check_circular_claim(
    graph_root: Path, located: Located, doc: dict[str, Any]
) -> list[Diagnostic]:
    """F08-T17 (D-16): a ``circular-decomposition`` claim names an ancestor, and the ancestor is a
    node that depends on this claim's node transitively, read through revisions — the one fact the
    implication the sandbox checks is about (``exhibits.check_circular``). An ``ancestor`` on any
    other class claims something nobody checks, so it is refused rather than carried."""
    ancestor = doc.get("ancestor")
    if doc.get("class") != records.CIRCULAR_CLASS:
        if ancestor is None:
            return []
        return [
            Diagnostic(
                "circular-ancestor",
                f"{located.path}: `ancestor` belongs to a {records.CIRCULAR_CLASS} claim; a "
                f"{doc.get('class')!r} claim names none (F08-T17)",
                {"path": located.path, "class": doc.get("class"), "ancestor": ancestor},
            )
        ]
    if located.node_id is None or not isinstance(ancestor, str):
        lacks = "a node's defects/" if located.node_id is None else "an ancestor"
        return [
            Diagnostic(
                "circular-ancestor",
                f"{located.path}: a {records.CIRCULAR_CLASS} claim sits under a node and names "
                f"a node above it; this one lacks {lacks} (F08-T17)",
                {"path": located.path, "ancestor": ancestor},
            )
        ]
    nodes_dir = layout.graph_nodes_dir(graph_root, located.target_id)
    above = graphmod.ancestors(nodes_dir, located.node_id)
    if ancestor not in above:
        return [
            Diagnostic(
                "circular-ancestor",
                f"{located.path}: {ancestor!r} does not depend on {located.node_id}, even through "
                "revisions, so the claim relates the node to nothing it was meant to reduce; name "
                f"one of: {', '.join(sorted(above)) or 'none (nothing depends on this node)'}",
                {"path": located.path, "ancestor": ancestor, "ancestors": sorted(above)},
            )
        ]
    return []


SCREEN_FINDING = "screen-finding"
UPSTREAM_DRIFT = "upstream-drift"


def check_watcher_request(located: Located, data: bytes) -> list[Diagnostic]:
    """F12-R11: in a curator pull request a revision request is the watcher's — class
    ``upstream-drift`` — or nothing; a person's request is an append like anyone's."""
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    if doc.get("defect_class") == UPSTREAM_DRIFT:
        return []
    return [
        Diagnostic(
            "defect-class",
            f"{located.path}: a curator pull request carries the watcher's request "
            f"({UPSTREAM_DRIFT}) beside its drift record and no other; file a "
            f"{doc.get('defect_class')!r} request as an append like anyone else (F12-R11, D-8)",
            {"path": located.path, "class": doc.get("defect_class")},
        )
    ]


def check_screen_finding(
    graph_root: Path, located: Located, doc: dict[str, Any], *, mode: Mode | None
) -> list[Diagnostic]:
    """F12-R4's two v2 rules, and the curator-mode restriction (F12-Q7)."""
    claim_class = str(doc.get("class"))
    if mode == "curator" and claim_class != SCREEN_FINDING:
        return [
            Diagnostic(
                "defect-class",
                f"{located.path}: a curator pull request carries the screen's own claim "
                f"({SCREEN_FINDING}) beside its QA record and no other; file a {claim_class} "
                "claim as an append like anyone else (F12-R4, D-16)",
                {"path": located.path, "class": claim_class},
            )
        ]
    if claim_class == SCREEN_FINDING:
        exhibit = doc.get("qa_exhibit")
        if not isinstance(exhibit, str) or not (graph_root / exhibit).is_file():
            return [
                Diagnostic(
                    "defect-ref",
                    f"{located.path}: a {SCREEN_FINDING} claim names the exhibit file the QA "
                    f"record cites under targets/<id>/qa/exhibits/ (F12-R4, R15); "
                    f"qa_exhibit is {exhibit!r}",
                    {"path": located.path, "qa_exhibit": exhibit},
                )
            ]
    routes = doc.get("routes")
    if isinstance(routes, dict):
        name = str(routes.get("claim"))
        sibling = (graph_root / located.path).parent / name
        routed_doc = _document(located, sibling.read_bytes()) if sibling.is_file() else None
        if not isinstance(routed_doc, dict) or routed_doc.get("class") != SCREEN_FINDING:
            return [
                Diagnostic(
                    "defect-route",
                    f"{located.path}: routes {name!r}, which is not a {SCREEN_FINDING} claim in "
                    "the same directory (F12-R4)",
                    {"path": located.path, "claim": name},
                )
            ]
    return []


def exhibit_of(role: Role, doc: dict[str, Any]) -> str | None:
    """The Lean exhibit a record carries, or ``None`` (F08-R6, R7)."""
    if role == "defect-claim":
        value = doc.get("exhibit")
    elif role == "revision-request":
        evidence = doc.get("evidence")
        value = evidence.get("exhibit") if isinstance(evidence, dict) else None
    else:
        value = None
    return value if isinstance(value, str) and value.strip() else None


def exhibits(graph_root: Path, classification: Classification) -> list[Located]:
    """The appended records whose exhibit the sandbox has to elaborate (F08-R6, R7)."""
    out: list[Located] = []
    for located in classification.located:
        if located.role not in paths.EXHIBIT_ROLES:
            continue
        data = _read(graph_root, located)
        if isinstance(data, Diagnostic):
            continue  # already a problem in `check`; nothing to elaborate
        doc = _document(located, data)
        if not isinstance(doc, Diagnostic) and exhibit_of(located.role, doc) is not None:
            out.append(located)
    return out


def check_explainer_file(
    graph_root: Path, located: Located, classification: Classification
) -> list[Diagnostic]:
    """R10: an explainer is prose about a merged proof; on an unproved node it is a misfiled
    annex (D-3), and it is named for its content like one, because a correction is a new entry.

    F20-R2, R4: an explainer whose front matter declares ``explainer/v1`` names the merged
    artifact it describes — which may be a partial assembly on a node with no ``Proof.lean`` —
    and the outline steps its sections describe; ``explainers.check_record`` holds it to both.
    One filed before F20 keeps the rule above."""
    from opn_gate import explainers  # noqa: PLC0415 — explainers reads glosses, as this does

    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    if located.node_id is not None and explainers.is_record(data):
        naming = paths.check_content_hash_name(located, data)
        if naming is not None:
            return [naming]
        return explainers.check_record(graph_root, located, data) or []
    if located.node_id is not None and not _has_proof(graph_root, located):
        return [
            Diagnostic(
                "explainer-unproved",
                f"{located.node_id} has no merged proof, so this text is an annex misfiled as an "
                "explainer: submit it under annex/ (D-3, D-31)",
                {"path": located.path, "node": located.node_id},
            )
        ]
    naming = paths.check_content_hash_name(located, data)
    return [naming] if naming is not None else []


def real_identities(graph_root: Path, target_id: str, *, signer: Signer) -> frozenset[str]:
    """F15-Q4: who is real-identity at Stage 0 — the target's active stewards and the graph's
    listed curators, both curator-checked. Widening the set is one function when a registry
    exists (D-22)."""
    try:
        listed = load_curators(graph_root).logins
    except CuratorsError:
        listed = frozenset()
    target_dir = graph_root / "targets" / target_id
    return frozenset(steward.active_logins(target_dir, signer)) | listed


def acting_names(
    graph_root: Path, classification: Classification | None, record_author: str | None
) -> frozenset[str]:
    """F20-T6: the names of whoever a gloss, explainer or withdrawal pull request acts for.

    A pull request the service opened (``Classification.by_service``) acts for the identity the
    service authenticated, which it writes into the record's own ``author`` and nowhere else; any
    other pull request acts for the login that opened it, whatever its record says. A listed
    curator is known by both halves of their ``curators.json`` pair, each read in the direction
    its namespace allows: the service's pseudonym to the login it is paired with (a pseudonym is
    the service's to issue, once), and a host login to its pseudonym (a login is the host's) —
    never a host login to a login, since anyone may register a login spelled like a pseudonym.
    The service refuses to write a pseudonym spelled like another person's real-identity login
    (``api/opn_api/glosses.py``), which is what makes the first direction safe for stewards too.
    Empty when nobody is known."""
    if classification is None:
        return frozenset()
    who = record_author if classification.by_service else classification.author
    if not who:
        return frozenset()
    try:
        curators = load_curators(graph_root)
    except CuratorsError:
        return frozenset({who})
    if classification.by_service:
        paired = {login for pseudonym, login in curators.identities if pseudonym == who}
    else:
        paired = {pseudonym for pseudonym, login in curators.identities if login == who}
    return frozenset({who, *paired})


def check_explainer_signature(
    graph_root: Path,
    located: Located,
    classification: Classification,
    *,
    signer: Signer | None = None,
) -> list[Diagnostic]:
    """F15-R8: a signature validates, sits under the node and target it names, is named for
    the explainer it signs, and is valid — the explainer is on the node (at head, so one
    arriving in the same pull request counts), the affirmation is the fixed sentence, the
    signature verifies under its own key — and its signer is a real-identity contributor
    (``real_identities``). Each failure is refused by name; a signature claims nothing about
    the mathematics and changes no verdict, so nothing else is asked of it."""
    from opn_gate import explainers  # noqa: PLC0415 — only this check reads signatures

    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems = _check_schema(located, data, code="record-invalid")
    if problems:
        return problems
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    if doc.get("target") != located.target_id or doc.get("node") != located.node_id:
        return [
            Diagnostic(
                "signature-node",
                f"{located.path} signs an explainer on {doc.get('target')}/{doc.get('node')}, "
                f"and it sits under {located.target_id}/{located.node_id} (F15-R8)",
                {"path": located.path, "target": doc.get("target"), "node": doc.get("node")},
            )
        ]
    node_dir = graph_root / "targets" / located.target_id / "nodes" / str(located.node_id)
    verifier = signer or signed.default_signer()
    sig = explainers.signature_of(doc, graph_root / located.path)
    found = [
        Diagnostic(
            problem.split(":", 1)[0],
            f"{located.path}: {problem}",
            {"path": located.path, "signer": sig.signer},
        )
        for problem in explainers.problems_of(sig, node_dir, verifier)
    ]
    if sig.signer not in real_identities(graph_root, located.target_id, signer=verifier):
        found.append(
            Diagnostic(
                "signer-unlisted",
                f"{located.path}: {sig.signer!r} is neither an active steward of "
                f"{located.target_id} nor a listed curator; at Stage 0 a signature is a "
                "real-identity contributor's (F15-R8, Q4; D-22)",
                {"path": located.path, "signer": sig.signer},
            )
        )
    return found


def _record_parent(graph_root: Path, located: Located) -> Path:
    """The directory holding a record's ``gloss/``, ``explainer/`` or ``withdrawals/``: its node,
    or its target for a definition module's gloss."""
    rel = PurePosixPath(located.path)
    depth = 3 if rel.parent.name == glosses.SIGNED_DIR else 2
    return graph_root / rel.parents[depth - 1]


def _versions_of(parent: Path, role: str) -> list[glosses.Version]:
    from opn_gate import explainers  # noqa: PLC0415 — explainers reads glosses, as this does

    return glosses.load_versions(parent) if role == "gloss" else explainers.versions(parent)


def check_draft_provenance(
    graph_root: Path, located: Located, classification: Classification
) -> list[Diagnostic]:
    """F21-R2 (Q2; D-3 v3.31): no new drafts. The network drafts nothing (F21-R1), so an added
    gloss or explainer version carrying a ``drafter`` block is refused ``draft-not-accepted``
    whoever opened the pull request — the service, a curator or anyone else. The block stays in
    the schemas only for the versions already merged, which still validate, render and can be
    superseded by a person; refusing it here keeps anyone from filing words as "machine-drafted
    by" a model. ``classification`` names the opener in the refusal and decides nothing.
    (F20-T10's ``drafter-not-service`` let the service's own pull request through.)"""
    parent = _record_parent(graph_root, located)
    stem = PurePosixPath(located.path).stem
    version = next((v for v in _versions_of(parent, located.role) if v.hash == stem), None)
    if version is None or version.drafter is None:
        return []
    return [
        Diagnostic(
            "draft-not-accepted",
            f"{located.path} carries a drafter block: the network accepts no new drafts "
            "(F21-R2, D-3 v3.31). Words are a contributor's work; file the version with yourself "
            "as its author (drafter: null) and name any model that helped in drafted_with",
            {"path": located.path, "author": classification.author},
        )
    ]


def check_version_head(graph_root: Path, located: Located) -> list[Diagnostic]:
    """F20-R6: a gloss or explainer that supersedes names the current head of a chain of its own
    subject. Who may supersede a signed version is no longer asked: anyone may, and a person's
    change to verified words is pending until a steward or curator signs it (F21-R13, withdrawing
    F20-R6's ``signed-supersede``; ``opn_gate.sections``)."""
    parent = _record_parent(graph_root, located)
    siblings = _versions_of(parent, located.role)
    stem = PurePosixPath(located.path).stem
    version = next((v for v in siblings if v.hash == stem), None)
    if version is None or version.supersedes is None:
        return []  # nothing superseded; a file that did not load was refused by its own check
    directory = glosses.GLOSS_DIR if located.role == "gloss" else "explainer"
    return glosses.head_problems(
        located.path, version, siblings, glosses.withdrawn_versions(parent, directory)
    )


def _chain_before(
    graph_root: Path, located: Located, *, signer: Signer | None, models_only: bool
) -> tuple[glosses.Version, sections.Derived, str] | None:
    """The version ``located`` adds, what its chain shows over the versions ahead of it (with the
    valid signatures on them), and the version's text; ``None`` when there is nothing to judge (no
    such version, no version ahead, an unreadable file, or, with ``models_only``, a person's
    version)."""
    from opn_gate import explainers  # noqa: PLC0415 — explainers reads glosses, as this does

    parent = _record_parent(graph_root, located)
    siblings = _versions_of(parent, located.role)
    stem = PurePosixPath(located.path).stem
    version = next((v for v in siblings if v.hash == stem), None)
    if version is None or (models_only and not version.by_model):
        return None
    gloss = located.role == "gloss"
    directory = glosses.GLOSS_DIR if gloss else explainers.EXPLAINER_DIR
    withdrawn = glosses.withdrawn_versions(parent, directory)
    same = [v for v in siblings if v.subject == version.subject]
    chain = glosses.chain_of(glosses.chains(same, withdrawn), version.hash)
    if chain is None:
        return None  # defence in depth: every version is in some chain
    ahead = chain.versions[: [v.hash for v in chain.versions].index(version.hash)]
    if not ahead:
        return None
    verifier = signer or signed.default_signer()
    if gloss:
        approvals: dict[str, list[frozenset[str] | None]] = {
            h: [None if s.sections is None else frozenset(s.sections) for s in found]
            for h, found in glosses.valid_signatures(parent, verifier).items()
        }
    else:
        approvals = explainers.approvals_of(explainers.valid(parent, verifier))
    before = sections.of_chain(glosses.Chain(ahead, withdrawn), approvals, withdrawn)
    try:
        text = (graph_root / located.path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None  # the file's own check names what is wrong with it
    return version, before, text


def check_own_edit_opener(
    graph_root: Path,
    located: Located,
    classification: Classification | None,
    *,
    signer: Signer | None = None,
) -> list[Diagnostic]:
    """F21-Q14: an author's edit of their own written words shows at once (the owner's ruling,
    Q10), so a version that uses that privilege must be filed by its author. On a pull request the
    service did not open, a version naming an ``author`` that changes a section the chain shows
    as written by that same author is refused ``author-not-opener`` unless the author is among the
    opener's names (``acting_names``). The service writes the author from the token, so its pull
    requests are not in question; a version that merely proposes a change to another's words is
    pending and gains nothing from its name, so it is not checked; with no opener known (a local
    classify without ``--author``) nothing is judged."""
    if classification is None or classification.by_service or not classification.author:
        return []
    found = _chain_before(graph_root, located, signer=signer, models_only=False)
    if found is None:
        return []
    version, before, text = found
    if version.by_model or version.author is None:
        return []
    gloss = located.role == "gloss"
    edits = sections.own_edits(before, sections.parts_of_text(text, gloss=gloss), version.author)
    if not edits or version.author in acting_names(graph_root, classification, version.author):
        return []
    keys = ", ".join(p.key for p in edits)
    return [
        Diagnostic(
            "author-not-opener",
            f"{located.path} names author {version.author} and changes words that author wrote "
            f"({keys}), which would show at once as their own edit (F21-Q10); but the pull "
            f"request was opened by {classification.author}. File it through the service, which "
            "writes the author from the token, or open it as the author; a change to another "
            "person's words is filed under your own name and waits for a steward or curator",
            {
                "path": located.path,
                "author": version.author,
                "opened_by": classification.author,
                "sections": [p.key for p in edits],
            },
        )
    ]


def check_model_lock(
    graph_root: Path, located: Located, *, signer: Signer | None = None
) -> list[Diagnostic]:
    """F21-R12 (D-3 v3.31, Q7): a version a model drafted (one naming ``drafted_with``) may not
    change or omit a section its chain shows as written or verified: ``locked-by-a-person``, one
    per such section, naming its key and the Lean it describes — for an explainer's ``steps:``
    section the lines its steps span in the proof's outline (the least start to the greatest
    end), for its overview or a gloss the whole file. What the chain shows is derived over the
    versions ahead of this one, with the valid signatures on them (``opn_gate.sections``). A
    person's version is never refused here: their change to locked words is pending until a
    steward or curator signs it. (A legacy ``drafter`` block is refused before this, R2.)"""
    found = _chain_before(graph_root, located, signer=signer, models_only=True)
    if found is None:
        return []
    version, before, text = found
    gloss = located.role == "gloss"
    target_dir = graph_root / "targets" / located.target_id
    out: list[Diagnostic] = []
    for placed in sections.breaches(before, sections.parts_of_text(text, gloss=gloss)):
        file, lines = _locked_lean(target_dir, version, placed.key)
        where = (
            f"Lean lines {lines[0]}-{lines[1]} of {file}" if lines is not None else f"all of {file}"
        )
        out.append(
            Diagnostic(
                "locked-by-a-person",
                f"{located.path} names drafted_with and changes or omits section {placed.key} "
                f"({where}), which its chain shows as {placed.state} (version "
                f"{placed.version[:12]}…): a person's words are locked against models (F21-R12, "
                "D-3 v3.31). Keep that section exactly as the chain shows it, or file the version "
                "as your own words (drafted_with: null); a person's change to it is pending until "
                "a steward or curator signs it",
                {
                    "path": located.path,
                    "section": placed.key,
                    "state": placed.state,
                    "version": placed.version,
                    "file": file,
                    "lines": list(lines) if lines is not None else None,
                },
            )
        )
    return out


def _locked_lean(
    target_dir: Path, version: glosses.Version, key: str
) -> tuple[str, tuple[int, int] | None]:
    """The Lean a locked section describes, as ``(file relative to the target, lines)``: an
    explainer's ``steps:`` section spans its steps' lines in the artifact's outline (``None`` when
    the outline or a step is missing); its overview, and a gloss, are the whole file."""
    from opn_gate import explainers  # noqa: PLC0415 — explainers reads glosses, as this does

    kind, node, third = version.subject
    if kind != "proof":
        lean = glosses.subject_file(target_dir, {"kind": kind, "node": node, "module": third})
        return (lean.relative_to(target_dir).as_posix() if lean is not None else str(kind)), None
    node_dir = target_dir / "nodes" / str(node)
    proof = str(third)
    artifact = explainers.merged_artifacts(node_dir).get(proof, proof)
    file = f"nodes/{node}/{artifact}"
    if not key.startswith(sections.STEPS):
        return file, None
    outline = explainers.outline_of(target_dir, proof)
    steps = explainers.outline_steps(outline) if outline is not None else {}
    named_steps = [steps.get(s) for s in key[len(sections.STEPS) :].split(",")]
    spans = [s["span"] for s in named_steps if s is not None]
    if not spans or len(spans) != len(named_steps):
        return file, None
    return file, (min(s["start_line"] for s in spans), max(s["end_line"] for s in spans))


def check_gloss_signature(
    graph_root: Path,
    located: Located,
    classification: Classification,
    *,
    signer: Signer | None = None,
) -> list[Diagnostic]:
    """F20-R8: a gloss signature validates, sits beside the gloss it signs under the node (or
    target) it names, is valid (``glosses.signature_problems``) and is a real-identity
    contributor's: an active steward of the target or a listed curator. It changes no status,
    grade or digestion state (F20-Q12), so nothing else is asked of it."""
    del classification
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems = _check_schema(located, data, code="record-invalid")
    if problems:
        return problems
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    if doc.get("target") != located.target_id or doc.get("node") != located.node_id:
        return [
            Diagnostic(
                "signature-node",
                f"{located.path} signs a gloss on {doc.get('target')}/{doc.get('node')}, and it "
                f"sits under {located.target_id}/{located.node_id} (F20-R8)",
                {"path": located.path, "target": doc.get("target"), "node": doc.get("node")},
            )
        ]
    verifier = signer or signed.default_signer()
    found = glosses.signature_problems(
        located.path, doc, _record_parent(graph_root, located), verifier
    )
    who = str(doc["signer"])
    if who not in real_identities(graph_root, located.target_id, signer=verifier):
        found.append(
            Diagnostic(
                "signer-unlisted",
                f"{located.path}: {who!r} is neither an active steward of {located.target_id} nor "
                "a listed curator; a gloss is signed by one of them (F20-R8; D-22)",
                {"path": located.path, "signer": who},
            )
        )
    return found


def _has_proof(graph_root: Path, located: Located) -> bool:
    """A node has a merged proof exactly when ``Proof.lean`` is in the tree: it is the one file a
    submission may create and it only ever arrives by a merge (D-3)."""
    assert located.node_id is not None
    proof = graph_root / "targets" / located.target_id / "nodes" / located.node_id / "Proof.lean"
    return proof.is_file()


def check_replaced_proof(graph_root: Path, classification: Classification) -> list[Diagnostic]:
    """D-3 v3.13: a merged ``Proof.lean`` is never modified; a later proof of the node is an
    alternate (D-25). The tutorial node is the exception D-27 makes it: permanently open, every
    operator proves it again, and it earns nothing, so its proof file is a rehearsal slot rather
    than a record. A META that cannot be read is not taken as a tutorial (C7: refuse)."""
    problems: list[Diagnostic] = []
    for path in classification.replaced:
        node = path.rsplit("/", 1)[0]
        try:
            meta = yaml.safe_load((graph_root / node / "META.yaml").read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            meta = None
        if isinstance(meta, dict) and meta.get("tutorial") is True:
            continue
        problems.append(
            Diagnostic(
                "proof-replaces-merged",
                f"{path}: a merged Proof.lean is never modified (D-3 v3.13); a later proof of "
                f"this node is submitted as {node}/attempts/<ts>-<pseudonym>"
                f"{paths.ALTERNATE_SUFFIX} (D-25)",
                {"path": path},
            )
        )
    return problems


def check_alternate(graph_root: Path, classification: Classification) -> list[Diagnostic]:
    """R7, D-25 v3.13: an alternate is a later proof of a proved node. The one duplicate the gate
    refuses is an exact copy of the node's proof or of an alternate already recorded; no
    similarity between proofs is ever judged (F07-Q20)."""
    problems: list[Diagnostic] = []
    for located in (loc for loc in classification.located if loc.role == "alternate"):
        assert located.node_id is not None
        if not _has_proof(graph_root, located):
            problems.append(
                Diagnostic(
                    "alternate-unproved",
                    f"{located.node_id} has no merged Proof.lean, so there is nothing for this to "
                    "be an alternate to: submit it as the node's Proof.lean (D-25)",
                    {"path": located.path, "node": located.node_id},
                )
            )
            continue
        data = _read(graph_root, located)
        if isinstance(data, Diagnostic):
            problems.append(data)
            continue
        node_dir = graph_root / "targets" / located.target_id / "nodes" / located.node_id
        itself = graph_root / located.path
        recorded = sorted(
            p
            for p in (node_dir / "attempts").glob(f"*{paths.ALTERNATE_SUFFIX}")
            if p.is_file() and p != itself
        )
        for other in (node_dir / "Proof.lean", *recorded):
            if other.read_bytes() == data:
                same = other.relative_to(graph_root).as_posix()
                problems.append(
                    Diagnostic(
                        "alternate-duplicate",
                        f"{located.path} is byte-identical to {same}; an alternate must differ "
                        "from every proof already recorded (D-25)",
                        {"path": located.path, "same_as": same},
                    )
                )
                break
    return problems


def check_withdrawal(
    graph_root: Path,
    located: Located,
    classification: Classification | None = None,
    *,
    signer: Signer | None = None,
) -> list[Diagnostic]:
    """F08-T31 (D-14, D-18 v3.27): a withdrawal validates, and names a record that is on the
    record — a valid status record or defect claim in this node's own ``status/`` or
    ``defects/``. Who may file one is the curator mode's rule (F08-R8): a listed login, reviewed
    by another one. The schema's pattern keeps the name inside the node, so a record of another
    node or another target cannot be named at all; one that is not there is refused by name.

    F20-R7 (D-3 v3.30): or a gloss or explainer version beside it — under a node, or under the
    target for a definition module's gloss — withdrawn by that version's author (the record's
    ``author`` is the version's), or in a pull request an active steward of the target or a
    listed curator opened; a curator's pull request is the curator mode, already asked."""
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems = _check_schema(located, data, code="record-invalid")
    if problems:
        return problems
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]  # defence in depth: _check_schema just parsed this same document
    named = str(doc["withdraws"])
    node_dir = PurePosixPath(located.path).parent.parent
    if named.startswith(VERSION_DIRS):
        return _check_version_withdrawal(graph_root, located, doc, classification, signer)
    if _is_record_on_file(graph_root, f"{node_dir}/{named}"):
        return []
    return [
        Diagnostic(
            "withdrawal-unknown-record",
            f"{located.path} withdraws {named}, which is not a status record or a defect claim "
            f"of this node on the record ({node_dir}/{named}); a withdrawal names one of its own "
            "node's records (F08-T31, D-18 v3.27)",
            {"path": located.path, "withdraws": named},
        )
    ]


def _check_version_withdrawal(
    graph_root: Path,
    located: Located,
    doc: dict[str, Any],
    classification: Classification | None,
    signer: Signer | None,
) -> list[Diagnostic]:
    """F20-R7: the version is on the record beside the withdrawal, and the withdrawal is its
    author's, or a steward's or curator's pull request."""
    named = str(doc["withdraws"])
    directory, _, name = named.partition("/")
    parent = _record_parent(graph_root, located)
    role = "gloss" if directory == glosses.GLOSS_DIR else "explainer"
    stem = PurePosixPath(name).stem
    version = next((v for v in _versions_of(parent, role) if v.hash == stem), None)
    if version is None or (role == "explainer" and located.node_id is None):
        return [
            Diagnostic(
                "withdrawal-unknown-record",
                f"{located.path} withdraws {named}, which is not a {role} version on the record "
                f"beside it ({parent.relative_to(graph_root).as_posix()}/{named}); a withdrawal "
                "names a version under its own node, or a definition gloss under its target "
                "(F20-R7)",
                {"path": located.path, "withdraws": named},
            )
        ]
    if classification is None or classification.mode == "curator":
        return []  # the curator mode asked who opened it (F08-R8)
    # F20-T6: who acts is the opener, or for a pull request the service opened the record's own
    # ``author``, which the service fills from the identity it authenticated (``acting_names``).
    names = acting_names(graph_root, classification, str(doc["author"]))
    if version.author is not None and version.author in names:
        return []
    verifier = signer or signed.default_signer()
    if names & real_identities(graph_root, located.target_id, signer=verifier):
        return []
    opened = classification.author
    return [
        Diagnostic(
            "withdrawal-unauthorized",
            f"{located.path} withdraws {named}, by {doc['author']!r} in a pull request opened by "
            f"{opened or 'an unknown login'}; a version is withdrawn by its author "
            f"({version.author or 'a draft has none'}), an active steward of {located.target_id} "
            "or a listed curator, and a pull request acts for whoever opened it, or for the "
            "record's author when the network's service opened it (F20-R7, D-3 v3.30)",
            {
                "path": located.path,
                "withdraws": named,
                "author": doc["author"],
                "opened_by": opened,
            },
        )
    ]


def check_credit_correction(graph_root: Path, located: Located) -> list[Diagnostic]:
    """F07-T66 (D-18, D-19 v3.27): a credit correction validates, names a line its ``from``
    holds active on this target's ledger as it stands, and moves it to someone else. Who may file
    one is the curator mode's rule (F08-R8). The post-merge ledger step applies it
    (``ledger.apply_correction``)."""
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems = _check_schema(located, data, code="record-invalid")
    if problems:
        return problems
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]  # defence in depth: _check_schema just parsed this same document
    if doc.get("to") == doc["from"]:
        return [
            Diagnostic(
                "credit-correction-same-identity",
                f"{located.path} moves a line from {doc['from']!r} to {doc['from']!r}; a "
                "correction names the identity that should hold it, or null for none (F07-T66)",
                {"path": located.path, "identity": doc["from"]},
            )
        ]
    try:
        held = ledger.corrected_entry(graph_root, doc, target=located.target_id)
    except schemas.SchemaError:
        held = False  # a ledger that does not read holds nothing a correction can name
    if held:
        return []
    return [
        Diagnostic(
            "credit-correction-unknown-entry",
            f"{located.path} names a {doc['line']} line on {doc['node']} ({doc['artifact']}, "
            f"merge {doc['merge_commit'][:12]}) that ledger/{doc['from']}.json does not hold "
            f"active on {located.target_id} (F07-T66, D-19 v3.27)",
            {
                "path": located.path,
                "from": doc["from"],
                "line": doc["line"],
                "node": doc["node"],
                "merge_commit": doc["merge_commit"],
            },
        )
    ]


def _is_record_on_file(graph_root: Path, rel: str) -> bool:
    """Whether ``rel`` is a node's status record or defect claim, present and valid against a
    version its role accepts (F08-T31: what a withdrawal may name)."""
    role = paths.locate(rel)
    path = graph_root / rel
    if role is None or role.role not in ("node-status", "defect-claim") or not path.is_file():
        return False
    try:
        record = schemas.load_yaml(path)
    except schemas.SchemaError:
        return False
    schema_id = str(record.get("schema"))
    accepted = paths.SCHEMAS_FOR_ROLE[role.role]
    return schema_id in accepted and not schemas.violations(record, schema_id)


def _read(graph_root: Path, located: Located) -> bytes | Diagnostic:
    path = graph_root / located.path
    try:
        return path.read_bytes()
    except OSError as exc:
        return Diagnostic(
            "append-unreadable",
            f"{located.path} cannot be read from the checkout: {exc.strerror}",
            {"path": located.path},
        )


def _check_schema(
    located: Located, data: bytes, *, code: str = "append-invalid"
) -> list[Diagnostic]:
    accepted = paths.SCHEMAS_FOR_ROLE.get(located.role)
    if accepted is None:
        return []
    doc = _document(located, data)
    if isinstance(doc, Diagnostic):
        return [doc]
    # The record names its own version and several may be live (D-34), so the accepted set is
    # what is pinned; anything outside it is refused naming the set rather than one version.
    schema_id = str(doc.get("schema"))
    if schema_id not in accepted:
        return [
            Diagnostic(
                code,
                f"{located.path} declares {schema_id!r}; a {located.role} record is one of "
                f"{', '.join(accepted)}",
                {"path": located.path, "schema": schema_id},
            )
        ]
    violations = schemas.violations(doc, schema_id)
    return [
        Diagnostic(
            code,
            f"{located.path} does not satisfy {schema_id}: {v.path}: {v.message}",
            {"path": located.path, "schema": schema_id, "field": v.path},
        )
        for v in violations[:5]
    ]


def _document(located: Located, data: bytes) -> dict[str, Any] | Diagnostic:
    """The record inside an appended file: the file itself for YAML and JSON records, the YAML
    front matter for an annex, whose body is prose the gate never reads (D-31)."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return Diagnostic(
            "append-invalid",
            f"{located.path} is not valid UTF-8",
            {"path": located.path},
        )
    if located.role == "annex":
        m = _FRONT_MATTER_RE.match(text)
        if m is None:
            return Diagnostic(
                "append-invalid",
                f"{located.path} has no YAML front matter; an annex declares its node, its "
                "contributor and the licence its author releases the prose under (D-23, D-31)",
                {"path": located.path},
            )
        text = m.group("yaml")
    try:
        doc = yaml.safe_load(text)  # a superset of JSON, so it reads both records
    except yaml.YAMLError as exc:
        return Diagnostic(
            "append-invalid",
            f"{located.path} is not parseable: {exc.__class__.__name__}",
            {"path": located.path},
        )
    if not isinstance(doc, dict):
        return Diagnostic(
            "append-invalid",
            f"{located.path} must hold one record object",
            {"path": located.path},
        )
    return doc
