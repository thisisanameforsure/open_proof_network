"""The ledger (F07-R12; D-19, D-13, D-27, D-31).

D-19's ledger is an inclusive record of *artifacts*, not a score: six lines, no weights, and
relative significance assigned retrospectively at write-up (D-32). F07 writes two of those lines,
and the whole of the logic is which merges earn one:

- ``proof`` — every merged proof, counterexample, vacuity certificate and partial assembly. All
  four are kernel-checked artifacts of D-12, and D-12 says a root-level counterexample is a
  research result, not a failure; paying only for proofs would price the record dishonestly.
- ``attempts`` — a merged postmortem, but only the *first* for its ``route_class`` on that node
  (D-13). That single rule is the whole anti-farming defence for the attempts line: the second
  identical route class tells nobody anything the first did not.

Three things earn nothing here, each for its own reason. An annex earns nothing ever (D-31): it
is input, not output. An approach record earns nothing on submission by design (D-14) — it is
paid retroactively on demonstrated reuse, which is not a thing this module can see. And the
tutorial node is off-ledger entirely (D-27): it is the proof-of-work that mints an identity, and
paying for it would make identity creation itself a credit farm.

The ledger is derived from merges that already happened, so it is rebuildable from the graph and
is never a second source of truth (D-35). Every function here is pure: the post-merge job hands
in what merged, and gets back the entry to append.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from opn_gate import schemas

SCHEMA = "ledger/v1"
LEDGER_DIR = "ledger"
UNDECLARED = "undeclared"  # R13: what a hand-opened pull request's tooling is recorded as
Line = Literal["statement", "proof", "review", "attempts", "upstreaming", "write-up"]

#: The artifacts that earn the proof line (D-12, D-19). A reduction is a partial (F07-Q1).
PROOF_ARTIFACTS: tuple[str, ...] = ("proof", "counterexample", "vacuity", "partial", "reduction")


@dataclass(frozen=True)
class Entry:
    """One thing an identity contributed, in the shape ``ledger/v1`` publishes."""

    line: Line
    target: str
    node: str
    artifact: str
    merge_commit: str
    date: str
    tooling: str = UNDECLARED
    route_class: str | None = None
    status: str = "active"

    def as_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "line": self.line,
            "target": self.target,
            "node": self.node,
            "artifact": self.artifact,
            "merge_commit": self.merge_commit,
            "date": self.date,
            "tooling": self.tooling or UNDECLARED,
            "status": self.status,
        }
        if self.route_class is not None:
            doc["route_class"] = self.route_class
        return doc


def ledger_path(graph_root: Path, identity: str) -> Path:
    return graph_root / LEDGER_DIR / f"{identity}.json"


def load(graph_root: Path, identity: str) -> dict[str, Any]:
    """The identity's ledger, or an empty one. A malformed ledger is a graph defect, not a
    reason to start over — losing entries silently is the one thing credit must never do."""
    path = ledger_path(graph_root, identity)
    if not path.is_file():
        return {"schema": SCHEMA, "identity": identity, "entries": []}
    return schemas.load_json(path, SCHEMA)


def entries_of(doc: dict[str, Any]) -> list[dict[str, Any]]:
    raw = doc.get("entries")
    return [e for e in raw if isinstance(e, dict)] if isinstance(raw, list) else []


def earns_attempts(doc: dict[str, Any], node: str, route_class: str) -> bool:
    """D-13: an attempts entry only for the first postmortem of that route class on that node.

    Asked of the ledger itself rather than of the node's ``attempts/`` directory, because the
    question is what this identity was already paid for — two contributors may each bank the
    first postmortem of a class they were first to, and both are first.
    """
    return not any(
        e.get("line") == "attempts"
        and e.get("node") == node
        and e.get("route_class") == route_class
        for e in entries_of(doc)
    )


def append(doc: dict[str, Any], entry: Entry) -> dict[str, Any]:
    """The ledger with ``entry`` appended. Append-only: nothing existing is touched."""
    out = dict(doc)
    out["entries"] = [*entries_of(doc), entry.as_dict()]
    return schemas.validate(out, SCHEMA)


def write(graph_root: Path, doc: dict[str, Any]) -> Path:
    path = ledger_path(graph_root, str(doc["identity"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(schemas.canonical_json(schemas.validate(doc, SCHEMA)))
    return path


# --- what a merge earns ---------------------------------------------------------------------


def proof_entry(  # noqa: PLR0913 — one argument per fact the entry records
    *,
    identity: str,
    target: str,
    node: str,
    artifact_type: str,
    artifact: str,
    merge_commit: str,
    date: str,
    tooling: str = UNDECLARED,
    tutorial: bool = False,
) -> Entry | None:
    """R12: the proof line for a merged D-12 artifact, or ``None`` when it earns nothing.

    ``tutorial`` is the one exclusion that is not about the artifact: D-27's node is how an
    identity is minted, so paying for it would make minting an identity a way to be paid.
    """
    if tutorial or artifact_type not in PROOF_ARTIFACTS:
        return None
    return Entry(
        line="proof",
        target=target,
        node=node,
        artifact=artifact,
        merge_commit=merge_commit,
        date=date,
        tooling=tooling,
    )


def postmortem_entry(  # noqa: PLR0913 — the ledger, plus one argument per fact
    doc: dict[str, Any],
    *,
    identity: str,
    target: str,
    node: str,
    route_class: str,
    artifact: str,
    merge_commit: str,
    date: str,
    tooling: str = UNDECLARED,
    tutorial: bool = False,
) -> Entry | None:
    """R12, D-13: the attempts line, first per route class on that node, never for the tutorial."""
    if tutorial or not earns_attempts(doc, node, route_class):
        return None
    return Entry(
        line="attempts",
        target=target,
        node=node,
        artifact=artifact,
        merge_commit=merge_commit,
        date=date,
        tooling=tooling,
        route_class=route_class,
    )


def record(graph_root: Path, identity: str, entry: Entry | None) -> Path | None:
    """Append ``entry`` to the identity's ledger and write it; ``None`` earns nothing and
    writes nothing, so a merge that pays for nothing leaves no file behind."""
    if entry is None:
        return None
    return write(graph_root, append(load(graph_root, identity), entry))


def contributions(graph_root: Path) -> dict[str, list[dict[str, Any]]]:
    """Every identity's entries, for the site's contributors page (D-36, F04).

    Revoked entries are included, because D-18 revokes credit by marking it, not by deleting it —
    a ledger that quietly dropped them would be a worse record than one that shows the
    revocation. The page labels them; this does not filter them.

    Read from the committed ledger files alone: the site is a view of the graph and derives no
    credit of its own.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    directory = graph_root / LEDGER_DIR
    if not directory.is_dir():
        return out
    for path in sorted(p for p in directory.iterdir() if p.suffix == ".json"):
        doc = schemas.load_json(path, SCHEMA)
        entries = entries_of(doc)
        if entries:
            out[str(doc["identity"])] = entries
    return out
