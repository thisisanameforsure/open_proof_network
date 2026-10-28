"""Loaders for the records the merge products are derived from (F03-T1; D-13, F03-Q3, Q5).

Three kinds of file, all schema-checked at the boundary (conventions §4):

- ``nodes/<id>/attempts/*.yaml`` — D-13 postmortems (``postmortem/v1`` or ``v2``). A file that
  does not validate is never dropped silently: it is counted as ``invalid`` and named (F03-R7).
- ``nodes/<id>/status/*.yaml`` — curator or adjudication overrides (``node-status/v1``).
- ``targets/<id>/status/*.yaml`` — the target's declaration (``target-status/v1`` or ``v2``).

For the status records the latest wins: ordered by ``date``, then file name. F08-T31 (D-18
v3.27): a node's status record or defect claim named by a curator's ``withdrawals/`` record is
read as absent by every loader here; the file stays in the tree.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from opn_gate import paths, schemas

log = logging.getLogger(__name__)

#: What a writer writes (D-13; D-23's disclosure needs ``model_and_tooling``).
POSTMORTEM_SCHEMA = "postmortem/v2"
#: Every version a postmortem may declare: D-34 versions, never edits, so records already on the
#: graph keep validating against the version they name. The set is the append path's own.
POSTMORTEM_SCHEMAS: tuple[str, ...] = paths.SCHEMAS_FOR_ROLE["postmortem"]
NODE_STATUS_SCHEMAS: tuple[str, ...] = ("node-status/v1",)
#: F11-R12: v2 renamed D-9's second rung, and D-34 forbids editing v1 — so both are live,
#: and a record is validated against the version it declares.
TARGET_STATUS_SCHEMAS: tuple[str, ...] = ("target-status/v1", "target-status/v2")
INVALID = "invalid"
ATTEMPT_SUFFIXES: tuple[str, ...] = (".yaml", ".yml")


@dataclass(frozen=True)
class AttemptSummary:
    """What the frontier publishes about a node's attempts (F03-R5, R7; D-25)."""

    count: int = 0
    refuted_route_classes: tuple[str, ...] = ()
    failure_class_histogram: dict[str, int] = field(default_factory=dict)
    invalid_files: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.count,
            "refuted_route_classes": list(self.refuted_route_classes),
            "failure_class_histogram": dict(sorted(self.failure_class_histogram.items())),
        }


def count_attempts(records: int, lean_names: Iterable[str], named: Iterable[str]) -> int:
    """T7: the postmortem files, plus each partial assembly beside them that no valid record
    names in ``artifacts.partial_proof``. An alternate is a proof, not an attempt (D-25 v3.13).
    One rule for the frontier and for ``CONTEXT.json``, which reads through a host (F10-Q7)."""
    partials = {n for n in lean_names if not n.endswith(paths.ALTERNATE_SUFFIX)}
    return records + len(partials - {PurePosixPath(n).name for n in named})


def postmortem_doc(doc: object, where: object = "a postmortem") -> dict[str, Any]:
    """``doc`` validated against the version it declares, which must be one of
    ``POSTMORTEM_SCHEMAS``; anything else raises ``SchemaError`` (a record declaring another
    schema is not a postmortem, however well it validates against that schema)."""
    declared = doc.get("schema") if isinstance(doc, dict) else None
    if declared not in POSTMORTEM_SCHEMAS:
        msg = (
            f"{where} declares {declared!r}; a postmortem is one of {', '.join(POSTMORTEM_SCHEMAS)}"
        )
        raise schemas.SchemaError(msg)
    return schemas.validate(doc, str(declared))


def load_postmortem(path: Path) -> dict[str, Any]:
    """A postmortem file, read and held to :func:`postmortem_doc`."""
    try:
        doc: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        msg = f"cannot read YAML {path}: {exc}"
        raise schemas.SchemaError(msg) from exc
    return postmortem_doc(doc, path)


def load_attempts(node_dir: Path) -> AttemptSummary:
    """Aggregate ``attempts/*.yaml``; invalid files count under ``invalid`` and are named.

    T7: the count also takes the partial assemblies filed beside them (D-3, D-12 #5), each an
    attempt on the node. A partial that a valid record names in ``artifacts.partial_proof`` is
    that record's attempt, counted once; an alternate is a proof, not an attempt (D-25 v3.13).
    """
    attempts_dir = node_dir / "attempts"
    if not attempts_dir.is_dir():
        return AttemptSummary()
    files = sorted(p for p in attempts_dir.iterdir() if p.suffix in ATTEMPT_SUFFIXES)
    lean_names = [p.name for p in attempts_dir.iterdir() if p.is_file() and p.suffix == ".lean"]
    named: set[str] = set()
    refuted: set[str] = set()
    histogram: Counter[str] = Counter()
    invalid: list[str] = []
    for path in files:
        try:
            doc = load_postmortem(path)
        except schemas.SchemaError as exc:
            log.warning("attempt record %s is invalid and counted as such: %s", path, exc)
            invalid.append(path.name)
            histogram[INVALID] += 1
            continue
        if doc["outcome"] == "refuted-route":
            refuted.add(str(doc["route_class"]))
        failure_class = doc.get("failure_class")
        if failure_class is not None:
            histogram[str(failure_class)] += 1
        partial = (doc.get("artifacts") or {}).get("partial_proof")
        if isinstance(partial, str):
            named.add(PurePosixPath(partial).name)
    return AttemptSummary(
        count=count_attempts(len(files), lean_names, named),
        refuted_route_classes=tuple(sorted(refuted)),
        failure_class_histogram=dict(histogram),
        invalid_files=tuple(invalid),
    )


@dataclass(frozen=True)
class StatusRecord:
    """A status override, with where it came from."""

    status: str
    author: str
    date: str
    path: Path
    doc: dict[str, Any]


def _latest_record(
    status_dir: Path, accepted: tuple[str, ...], exclude: frozenset[str] = frozenset()
) -> StatusRecord | None:
    """The latest record in ``status_dir``, each validated against the version it declares.

    A record names its own schema and several versions are live at once (D-34), so pinning one
    here would refuse a record the protocol publishes. What is pinned instead is the *set*: a
    record declaring anything outside it is a graph defect and raises, like a malformed one.
    ``exclude`` names files to leave out — the records a pull request adds, when the gate asks
    what the status was before it (status records are append-only, so that is the base's).
    """
    if not status_dir.is_dir():
        return None
    paths = sorted(
        p for p in status_dir.iterdir() if p.suffix in ATTEMPT_SUFFIXES and p.name not in exclude
    )
    # a bad status record is a graph defect: ``load_yaml`` raises
    return latest_status(((p, schemas.load_yaml(p)) for p in paths), accepted)


def latest_status(
    docs: Iterable[tuple[Path, dict[str, Any]]], accepted: tuple[str, ...]
) -> StatusRecord | None:
    """The latest of the loaded records — by date, then file name — each validated against the
    set of versions it may declare. The rule :func:`_latest_record` applies to a directory, on
    its own so a reader that is not a directory (the bundle's host reader, F08-T22) applies the
    same one; a record declaring a version outside ``accepted`` raises, as a malformed one does."""
    records: list[StatusRecord] = []
    for path, doc in docs:
        if str(doc.get("schema")) not in accepted:
            msg = f"{path} declares {doc.get('schema')!r}; expected one of {', '.join(accepted)}"
            raise schemas.SchemaError(msg)
        records.append(
            StatusRecord(str(doc["status"]), str(doc["author"]), str(doc["date"]), path, doc)
        )
    if not records:
        return None
    records.sort(key=lambda r: (r.date, r.path.name))
    return records[-1]


def load_node_status(node_dir: Path) -> StatusRecord | None:
    """The node's effective override (F03-R1's last five statuses), or ``None``. A withdrawn
    record is absent (F08-T31), so the latest of the others is the override."""
    return _latest_record(
        node_dir / "status", NODE_STATUS_SCHEMAS, withdrawn_names(node_dir, "status")
    )


#: F08-T31 (D-14, D-18 v3.27): a curator's withdrawals of this node's records.
WITHDRAWAL_SCHEMA = "withdrawal/v1"
#: F20-R7: v2 adds gloss and explainer versions; a withdrawal of either version is read alike.
WITHDRAWAL_SCHEMAS: tuple[str, ...] = (WITHDRAWAL_SCHEMA, "withdrawal/v2")
WITHDRAWALS_DIR = "withdrawals"


def withdrawn(node_dir: Path, present: Callable[[Path], bool] | None = None) -> frozenset[str]:
    """The node's records a merged withdrawal names, as ``status/<file>`` or ``defects/<file>``.

    Derive, never rewrite (F08-T10): the withdrawal is the fact, and the record it names stays in
    the tree. No date is compared — a withdrawal applies because it is on the record, never
    because it is newer than what it names. A file that does not validate as ``withdrawal/v1``
    is logged and passed over, so the record it meant to withdraw stands: the gate refused it at
    merge, and one bad file must never decide what the graph says (2026-09-17).

    ``present``, when given, keeps only the withdrawal files it accepts: the gate's head check
    reads the withdrawals that stood on a pull request's base, not those merged after it
    (F22-T11)."""
    directory = node_dir / WITHDRAWALS_DIR
    if not directory.is_dir():
        return frozenset()
    named: set[str] = set()
    for path in sorted(p for p in directory.iterdir() if p.suffix in ATTEMPT_SUFFIXES):
        if present is not None and not present(path):
            continue
        try:
            doc = schemas.load_yaml(path)  # against the version it declares (D-34)
            if doc.get("schema") not in WITHDRAWAL_SCHEMAS:
                msg = f"declares {doc.get('schema')!r}, not one of {', '.join(WITHDRAWAL_SCHEMAS)}"
                raise schemas.SchemaError(msg)
        except schemas.SchemaError as exc:
            log.warning("%s: a withdrawal that does not validate is passed over: %s", path, exc)
            continue
        named.add(str(doc["withdraws"]))
    return frozenset(named)


def withdrawn_names(
    node_dir: Path, directory: str, present: Callable[[Path], bool] | None = None
) -> frozenset[str]:
    """The file names under ``<node>/<directory>/`` a withdrawal names (F08-T31); ``present`` as
    in :func:`withdrawn`."""
    prefix = f"{directory}/"
    return frozenset(w[len(prefix) :] for w in withdrawn(node_dir, present) if w.startswith(prefix))


def load_target_status(
    target_dir: Path, *, exclude: frozenset[str] = frozenset()
) -> StatusRecord | None:
    """The target's latest declaration (D-33; F03-Q5), or ``None`` — leaving out the files named
    in ``exclude`` (the gate's view of the status before a pull request's own records, F11-T8)."""
    return _latest_record(target_dir / "status", TARGET_STATUS_SCHEMAS, exclude)


def declared_root(target_dir: Path) -> str | None:
    """The root the target's latest declaration names, or ``None`` (F11-R14; F03-Q5).

    The products read the root from the latest record alone, so every tool that writes a later
    target record carries this value forward: a record that left it out would undeclare the
    root, and the first variant or crux after it would stop the products (F08-Q19).
    """
    latest = load_target_status(target_dir)
    root = latest.doc.get("root") if latest is not None else None
    return str(root) if root else None


#: F08-T17 (D-16); retired by F08-T42 (D-16 v3.43): the gate refuses a new claim of this class,
#: and a merged one stays in the record as history that no product reads.
CIRCULAR_CLASS = "circular-decomposition"
DEFECTS_DIR = "defects"


@dataclass(frozen=True)
class DefectClaim:
    """F08-T35, F08-T36 (D-16, D-18 v3.28): one defect claim filed against a node, as the
    products show it — its file (``defects/<file>``, relative to the node), its class and
    whether it stands or a curator's withdrawal names it (F08-T31)."""

    file: str
    defect_class: str
    withdrawn: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "class": self.defect_class,
            "state": "withdrawn" if self.withdrawn else "standing",
        }


def defect_claims(node_dir: Path) -> list[DefectClaim]:
    """Every defect claim under the node, oldest first (D-13's stamp sorts), withdrawn ones
    included and marked so (D-16 v3.28: every claim is shown). A file that does not validate
    against the version it declares is logged and passed over: the gate refused it at merge,
    and one bad file must never decide what the products say (2026-09-17)."""
    directory = node_dir / DEFECTS_DIR
    if not directory.is_dir():
        return []
    accepted = paths.SCHEMAS_FOR_ROLE["defect-claim"]
    gone = withdrawn_names(node_dir, DEFECTS_DIR)
    found: list[DefectClaim] = []
    for path in sorted(p for p in directory.iterdir() if p.suffix in ATTEMPT_SUFFIXES):
        try:
            doc = schemas.load_yaml(path)
        except schemas.SchemaError as exc:
            log.warning("%s: a defect claim that does not read is passed over: %s", path, exc)
            continue
        schema_id = str(doc.get("schema"))
        if schema_id not in accepted or schemas.violations(doc, schema_id):
            log.warning("%s: a defect claim that does not validate is passed over", path)
            continue
        found.append(
            DefectClaim(f"{DEFECTS_DIR}/{path.name}", str(doc["class"]), path.name in gone)
        )
    return found
