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
``partial``      a ``.lean`` assembly under ``attempts/``, plus appends (D-12 #4, #5)
``append``       only new postmortems, precheck records, annexes, approach records, revision
                 requests or defect claims (the last two may carry a Lean exhibit, which is
                 elaborated in the sandbox — ``opn_gate.exhibits``)
``explainer``    only new files under ``explainer/`` (D-3), on a node that already has a proof
``proposal``     exactly one new node directory and nothing else — or only ``Witness.lean``
                 on a hole whose slot is unfilled (F08-R2, R5); admission decides, nobody
                 reviews (D-29)
``curator``      status records, or a versioned node ``<id>-v<n>``, by a login listed in the
                 graph's ``curators.json`` (F08-R8); reviewed by a second listed identity when
                 there is one (D-21, D-22)
``intake``       a whole new target — ``target.yaml``, ``gate-spec.json``, ``defs/``, the
                 fidelity certificates, a status record and exactly one node, the root — by a
                 listed curator (F11-R2, D-6); the root is admitted, which builds the
                 definitions first, and a second listed identity reviews when there is one
===============  ==========================================================================

A diff that fits none of them is rejected at step 2, naming the paths — never guessed at.

Modes are decided from the diff alone, plus one fact the host reports: who opened the pull
request, which only the curator rule consults. Whether the *submitter* called it a counterexample
or a reduction is in the ``opn-submission`` block (``submission-meta/v1``, F07-R2), and the
artifact checks that consume it are F07-T2's; classification never reads it, because the block is
not evidentiary and the paths are.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from opn_gate import graph as graphmod
from opn_gate import layout, paths, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change, Located, Role

Mode = Literal["proof", "partial", "append", "explainer", "proposal", "curator", "intake"]

#: The modes that run the Lean pipeline; the others never build a proof (R9, R10; F08-R2).
BUILDING_MODES: tuple[Mode, ...] = ("proof", "partial")
#: F08-R8: the graph's role file — the founder's, and the only one at Stage 0 (F08 §7).
CURATORS_FILE = "curators.json"
#: F08-R8, D-22: why step 9 is not asked of a curator PR while the founder is the only curator.
WAIVER_SINGLE_CURATOR = "single-curator"
#: F08-Q2: the one status a proposer may give their own new node.
PROPOSAL_STATUS = "speculative"

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
        return self.mode in BUILDING_MODES

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
            "problems": [d.as_dict() for d in self.problems],
        }


def classify(  # noqa: PLR0911 — one return per rejection
    changes: Iterable[Change],
    *,
    author: str | None = None,
    curators: Curators | None = None,
) -> Classification:
    """R3, F08-R2, R8: the diff's one mode, or the reasons it is not a submission at all.

    ``author`` is the login that opened the pull request, as the host reports it; ``curators`` is
    the graph's role file. Both are consulted only when the diff is curator-shaped.
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
    curator_records = [
        loc for loc in located if loc.role in paths.CURATOR_ROLES and loc.node_id not in new_dirs
    ]
    if any(loc.role in paths.INTAKE_ROLES for loc in located):
        return _classify_intake(
            located, changes, target_id, new_dirs, author=author, curators=curators or Curators()
        )
    if curator_records or any(paths.is_versioned(n) for n in new_dirs):
        return _classify_curator(
            located, changes, target_id, new_dirs, author=author, curators=curators or Curators()
        )

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
    admit = node_id if mode == "proposal" else None
    return Classification(mode, target_id, node_id, tuple(located), admit=admit)


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
    allowed = set(paths.NODE_ROLES) | set(paths.CURATOR_ROLES)
    if "qa-record" in roles:
        # F12-R4: the screen's own claim rides with the QA record that produced it; the claim is
        # then held to being a screen-finding (``check_defect_claim``), not a contributor's.
        allowed.add("defect-claim")
    if not roles <= allowed:
        return Classification(None, target_id, None, tuple(located), (_mixed(roles),))
    node_roles = set(paths.NODE_ROLES)
    touched = sorted(
        {loc.path for loc in located if loc.role in node_roles and loc.node_id not in new_dirs}
        | {c.path for c in changes if c.status != "A"}
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
    allowed = set(paths.INTAKE_ROLES) | set(paths.NODE_ROLES) | {"target-status"}
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


def _mode_for(roles: set[Role]) -> Mode | None:  # noqa: PLR0911 — one return per mode
    appendish = set(paths.APPEND_ROLES)
    if "node" in roles:  # F08-R2: a whole new directory, and nothing outside it
        return "proposal" if roles <= (set(paths.NODE_ROLES) | {"node-status"}) else None
    if roles == {"witness"}:  # F08-R5: filling a hole's slot
        return "proposal"
    if roles & (set(paths.NODE_ROLES) | {"node-status"}):
        return None  # a node file or a status record outside a new directory, with other things
    if "proof" in roles or "waiver" in roles:
        return "proof" if roles <= ({"proof", "waiver"} | appendish) else None
    if "partial" in roles:
        return "partial" if roles <= ({"partial"} | appendish) else None
    if "explainer" in roles:
        return "explainer" if roles == {"explainer"} else None
    return "append"


def _rejected(problems: list[Diagnostic]) -> Classification:
    return Classification(None, None, None, (), tuple(problems))


def _verb(status: str) -> str:
    return {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}[status]


# --- the checks the non-building modes run instead of a build ----------------------------------


def check(
    graph_root: Path, classification: Classification, *, base: BaseReader | None = None
) -> list[Diagnostic]:
    """R9, R10, F08-R2, R5, R8: everything a pull request is checked for before any sandbox.

    Content rules that belong to a file rather than to a mode — an annex is named for its own
    content, a postmortem validates against its schema — are applied to those files wherever they
    appear, so a proof that carries an append is held to the same rules. A proposal's shape and a
    witness completion's precondition are mode rules, checked here so a malformed proposal never
    costs a sandbox.
    """
    problems: list[Diagnostic] = []
    for located in classification.located:
        if located.role in paths.APPEND_ROLES:
            problems.extend(check_append_file(graph_root, located, mode=classification.mode))
        elif located.role == "explainer":
            problems.extend(check_explainer_file(graph_root, located, classification))
        elif located.role in paths.CURATOR_ROLES:
            problems.extend(check_status_record(graph_root, located, classification))
    if classification.mode == "proposal":
        problems.extend(check_proposal(graph_root, classification, base))
    return problems


def check_status_record(
    graph_root: Path, located: Located, classification: Classification
) -> list[Diagnostic]:
    """A status record validates against its schema; inside a proposer's new node it may only
    say ``speculative`` (F08-Q2) — every other status is a curator's judgment (D-8, D-14, D-18)."""
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    problems = _check_schema(located, data, code="record-invalid")
    if problems or classification.mode != "proposal":
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
    return problems


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
    return []


SCREEN_FINDING = "screen-finding"


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
    annex (D-3), and it is named for its content like one, because a correction is a new entry."""
    if located.node_id is not None and not _has_proof(graph_root, located):
        return [
            Diagnostic(
                "explainer-unproved",
                f"{located.node_id} has no merged proof, so this text is an annex misfiled as an "
                "explainer: submit it under annex/ (D-3, D-31)",
                {"path": located.path, "node": located.node_id},
            )
        ]
    data = _read(graph_root, located)
    if isinstance(data, Diagnostic):
        return [data]
    naming = paths.check_content_hash_name(located, data)
    return [naming] if naming is not None else []


def _has_proof(graph_root: Path, located: Located) -> bool:
    """A node has a merged proof exactly when ``Proof.lean`` is in the tree: it is the one file a
    submission may create and it only ever arrives by a merge (D-3)."""
    assert located.node_id is not None
    proof = graph_root / "targets" / located.target_id / "nodes" / located.node_id / "Proof.lean"
    return proof.is_file()


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
