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

F21 adds a third line, ``write-up``: a gloss or explainer version earns it for its author when a
steward or curator's signature on it merges (D-19 v3.31) — once per version, never for the signer,
never for a draft or a signature on one's own version. The version itself earns nothing (R4).

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
#: F07-R12, T15: the one line each classified mode's merge can earn, ``None`` for nothing at
#: merge. ``append`` earns only for a postmortem (D-13; an annex earns nothing, D-31), and an
#: alternate proof is credited at write-up, not when it merges (D-25 v3.13). ``explainer`` earns
#: only on a *signature* (F21-R3, D-19 v3.31): the version's author, never the signer, once per
#: version; the gloss or explainer itself, a draft and a signature on one's own version earn
#: nothing (R4).
MERGE_LINES: dict[str, Line | None] = {
    "proof": "proof",
    "partial": "proof",
    "alternate": None,
    "append": "attempts",
    "explainer": "write-up",
    "proposal": "statement",
    "curator": None,
    "intake": None,
    "fidelity": None,
    "steward": None,  # F15-R8's sibling rule: a commitment is a stake, not an artifact (D-32)
    "proposed-for": None,  # F18-R8: a pointer, not an artifact (D-14 v3.26)
}
#: D-21, F11 §7: the curator of a target earns no proof credit on it. They chose the statement,
#: its decomposition and its difficulty, so a proof of one of its nodes is not a result they
#: competed for. It bars the *proof* line only: their postmortems, statements and write-ups are
#: contributions like anyone else's, and D-13's attempts line is explicitly inclusive.
CURATOR_BARRED_LINES: tuple[Line, ...] = ("proof",)


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
    """Validate, then write: a refused ledger leaves no ``ledger/`` directory behind (C7)."""
    payload = schemas.canonical_json(schemas.validate(doc, SCHEMA))
    path = ledger_path(graph_root, str(doc["identity"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


# --- what a merge earns ---------------------------------------------------------------------


def curator_bar(*, identity: str, curator: str | None, line: Line, target: str) -> str | None:
    """D-21: why ``identity`` may not earn ``line`` on ``target``, or ``None``.

    Returned as a reason rather than swallowed, because a contributor who is also the curator
    should be told *why* a merge of theirs paid nothing — a silent zero looks like a bug in the
    ledger, which is the one thing a credit record must never look like (C7).
    """
    if curator is None or identity != curator or line not in CURATOR_BARRED_LINES:
        return None
    return (
        f"{identity} curated {target}, so the {line} line is barred there (D-21); their attempts, "
        "statements and write-ups on it are unaffected"
    )


def holds_proof_line(graph_root: Path, identity: str, target: str) -> bool:
    """Whether ``identity`` holds an active proof-line entry on ``target``. Read from the
    committed ledger, so a malformed one raises rather than answering no (C7). F15-R5 read this
    to bar a prover from signing; that bar was withdrawn (F15-Q14) and nothing bars on it now."""
    return any(
        e.get("line") == "proof" and e.get("target") == target and e.get("status") == "active"
        for e in entries_of(load(graph_root, identity))
    )


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
    curator: str | None = None,
) -> Entry | None:
    """R12: the proof line for a merged D-12 artifact, or ``None`` when it earns nothing.

    ``tutorial`` is the one exclusion that is not about the artifact: D-27's node is how an
    identity is minted, so paying for it would make minting an identity a way to be paid.
    ``curator`` is the second (D-21, F11-AC16): the target's curator earns nothing on the proof
    line of their own target, whoever else may. A fidelity signer is barred from nothing (D-9
    v3.17 as revised, F15-Q14).
    """
    if tutorial or artifact_type not in PROOF_ARTIFACTS:
        return None
    if curator_bar(identity=identity, curator=curator, line="proof", target=target) is not None:
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


#: F08-R13, D-19: the origins whose proposer authored a statement — a crux (D-14) or a variant
#: (D-30). A hole's statement was written by the elaborator or copied from a skeleton (D-31), so
#: neither earns the line; D-25's `skeleton-hole` origin exists to make that distinction.
STATEMENT_ORIGINS: tuple[str, ...] = ("authored", "variant")


def statement_entry(  # noqa: PLR0913 — one argument per fact the entry records
    *,
    identity: str,
    target: str,
    node: str,
    origin: str,
    merge_commit: str,
    date: str,
    tooling: str = UNDECLARED,
    tutorial: bool = False,
    supersedes: str | None = None,
) -> Entry | None:
    """F08-R13: the statement line for a merged proposal, or ``None`` when it earns nothing —
    a hole (never, D-31), the tutorial node (D-27), or a revision (D-19: a revision never
    re-mints paid credit)."""
    if tutorial or supersedes or origin not in STATEMENT_ORIGINS:
        return None
    return Entry(
        line="statement",
        target=target,
        node=node,
        artifact="Statement.lean",
        merge_commit=merge_commit,
        date=date,
        tooling=tooling,
    )


def writeup_holder(graph_root: Path, *, target: str, node: str, artifact: str) -> str | None:
    """F21-R3, Q3: the identity holding an active write-up entry for ``artifact``, or ``None``.

    Asked of every ledger, not only the author's: a credit correction (F07-T66) may have moved
    the line to someone else, and the version is still credited once. A revoked entry does not
    count (D-18 keeps it, and the line is no longer held)."""
    for identity, entries in contributions(graph_root).items():
        for e in entries:
            if (
                e.get("line") == "write-up"
                and e.get("target") == target
                and e.get("node") == node
                and e.get("artifact") == artifact
                and e.get("status") == "active"
            ):
                return identity
    return None


def writeup_entry(  # noqa: PLR0913 — one argument per fact the entry records
    *,
    author: str | None,
    signer_names: frozenset[str],
    target: str,
    node: str,
    artifact: str,
    merge_commit: str,
    date: str,
    tooling: str = UNDECLARED,
    held_by: str | None = None,
) -> tuple[Entry | None, str]:
    """F21-R3 (D-19 v3.31): the write-up line a signature on a gloss or explainer version earns
    its author, with the reason; ``(None, why)`` when it earns nothing.

    Nothing for a draft (no author), for a signature on one's own version (``signer_names`` is the
    signer's login with any pseudonym ``curators.json`` pairs it with), or when the version is
    already credited (``held_by``, from ``writeup_holder``): credit is per version, once (Q3). The
    signer is never the one credited: D-19 credits work, not review."""
    if author is None:
        return None, f"{artifact} is a draft with no author, so its signature credits nobody (R3)"
    if author in signer_names:
        return None, (
            f"{artifact} is {author}'s own version, and a signature on one's own version earns "
            "nothing (R3, D-19 v3.31)"
        )
    if held_by is not None:
        return None, f"{artifact} is already credited to {held_by}: once per version (Q3)"
    entry = Entry(
        line="write-up",
        target=target,
        node=node,
        artifact=artifact,
        merge_commit=merge_commit,
        date=date,
        tooling=tooling,
    )
    return entry, f"{author} wrote {artifact}, and a signature approved it (R3, D-19 v3.31)"


def statement_tooling(meta: dict[str, Any]) -> str:
    """The tooling a merged proposal's statement line records (D-23, R13; F07-T49): the model
    its proposer declared, which the scaffold wrote into ``META.yaml`` as ``provenance.model``.
    A proposal has no attestation, so ``merge_tooling`` cannot read it; the record is the META.
    ``undeclared`` when the proposer declared nothing."""
    provenance = meta.get("provenance") or {}
    model = provenance.get("model") if isinstance(provenance, dict) else None
    return str(model) if isinstance(model, str) and model.strip() else UNDECLARED


def merge_tooling(graph_root: Path, merge_commit: str) -> str:
    """The ``model_and_tooling`` the post-merge job attested for ``merge_commit`` (R13, T14), or
    ``undeclared``. Read from the committed attestations rather than passed as a flag, because the
    ledger is derived from the graph (D-35) and a pinned gate cannot learn a new flag (T15, Q22).
    A record that does not parse is skipped: it cannot be this merge's."""
    directory = graph_root / "attestations"
    if not directory.is_dir():
        return UNDECLARED
    for path in sorted(directory.glob("*.json")):
        try:
            doc = schemas.load_json(path)
        except schemas.SchemaError:
            continue
        if isinstance(doc, dict) and doc.get("merge_commit") == merge_commit:
            declared = doc.get("model_and_tooling")
            return str(declared) if isinstance(declared, str) and declared else UNDECLARED
    return UNDECLARED


def record(graph_root: Path, identity: str, entry: Entry | None) -> Path | None:
    """Append ``entry`` to the identity's ledger and write it; ``None`` earns nothing and
    writes nothing, so a merge that pays for nothing leaves no file behind."""
    if entry is None:
        return None
    return write(graph_root, append(load(graph_root, identity), entry))


CORRECTION_SCHEMA = "credit-correction/v1"
#: The fields of a ledger/v1 entry that identify its line (F07-T66); ``route_class`` too, where the
#: entry has one, since two attempts lines on one node and merge differ only in it (D-13).
LINE_KEY: tuple[str, ...] = ("line", "node", "artifact", "merge_commit")


def names_entry(correction: dict[str, Any], entry: dict[str, Any], *, target: str) -> bool:
    """Whether ``entry`` is the ledger line ``correction`` names on ``target``."""
    return (
        entry.get("target") == target
        and all(entry.get(k) == correction.get(k) for k in LINE_KEY)
        and entry.get("route_class") == correction.get("route_class")
    )


def corrected_entry(graph_root: Path, correction: dict[str, Any], *, target: str) -> bool:
    """Whether ``correction``'s ``from`` holds the line it names, active (what a curator's pull
    request is checked for before it merges, F07-T66)."""
    return any(
        names_entry(correction, e, target=target) and e.get("status") == "active"
        for e in entries_of(load(graph_root, str(correction["from"])))
    )


def apply_correction(graph_root: Path, correction: dict[str, Any], *, target: str) -> list[Path]:
    """F07-T66 (D-18, D-19 v3.27): apply a merged credit correction; the ledgers written.

    The line ``correction`` names is marked ``revoked`` in ``from``'s ledger, and an ``active``
    copy of it — the original merge, date and tooling, so the record still says when and how the
    work merged — is appended to ``to``'s (none when ``to`` is null). An entry is never deleted.
    Idempotent: a line already revoked is left as it is, and ``to`` gains the line only if it
    does not already hold it active, so a replay of the post-merge job (F07-T33) writes nothing.
    A correction naming no line ``from`` holds writes nothing: the gate refused it before the
    merge (``credit-correction-unknown-entry``), and the ledger is no place to guess."""
    schemas.validate(correction, CORRECTION_SCHEMA)
    giver = load(graph_root, str(correction["from"]))
    found = [e for e in entries_of(giver) if names_entry(correction, e, target=target)]
    if not found:
        return []
    written: list[Path] = []
    if any(e.get("status") == "active" for e in found):
        out = dict(giver)
        out["entries"] = [
            {**e, "status": "revoked"} if names_entry(correction, e, target=target) else e
            for e in entries_of(giver)
        ]
        written.append(write(graph_root, out))
    receiver = correction.get("to")
    if isinstance(receiver, str):
        taker = load(graph_root, receiver)
        held = any(
            names_entry(correction, e, target=target) and e.get("status") == "active"
            for e in entries_of(taker)
        )
        if not held:
            out = dict(taker)
            out["entries"] = [*entries_of(taker), {**found[0], "status": "active"}]
            written.append(write(graph_root, out))
    return written


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
