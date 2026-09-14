"""Statement evidence (F14-R3, R4; D-4 step 9, D-9, D-10).

What the network knows, from outside itself, about whether a target's root statement says what the
conjecture says: the seed catalog's row for it (``docs/lean_conjecture_catalog.json``, built by
``docs/seed_conjecture_sources_build.py``), with the registry history, misformalization issues,
ported definitions and hazards behind the row's score. One record per write, under
``targets/<id>/evidence/root-<n>.yaml``, append-only and pinned to the root's statement hash, so a
D-8 revision leaves the record on disk and counting for nothing.

The record is evidence, not a signature: it raises no D-9 grade. What it decides is D-4 step 9 — a
proof under a root whose current record scores at least the configured minimum merges without a
non-author's review (F14-R5, ``modes``). The graph holds the record because the gate can read
only the graph at the pinned commit; the catalog stays research data in the network repository.

The external attempts the row names are written to the F12-R10 ledger through
``qa.record_attempt`` (one home per value, F11-Q10) and the record keeps only how many it wrote.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from opn_gate import fidelity, qa, schemas

log = logging.getLogger(__name__)

SCHEMA = "statement-evidence/v1"
EVIDENCE_DIR = "evidence"
CATALOG_FILE = "docs/lean_conjecture_catalog.json"
CATALOG_SCHEMA = "lean-conjecture-catalog/v1"
SUFFIXES: tuple[str, ...] = (".yaml", ".yml")
#: F14-R4: where AlphaProof Nexus lists the statements it attempted, cited per attempt.
NEXUS_ATTEMPTED_URL = (
    "https://github.com/google-deepmind/alphaproof-nexus-results/blob/main/"
    "erdos_problems_attempted.txt"
)
NEXUS_VENUE = "google-deepmind/alphaproof-nexus-results"
NEXUS_SYSTEM = "AlphaProof Nexus"


class EvidenceError(ValueError):
    """The record cannot be written or read as evidence. Nothing is written."""


@dataclass(frozen=True)
class Record:
    """One evidence record on disk."""

    path: Path
    doc: dict[str, Any]

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def statement_hash(self) -> str:
        return str(self.doc["statement_hash"])

    @property
    def score(self) -> int:
        return int(self.doc["catalog"]["score"])

    @property
    def letter(self) -> str:
        return str(self.doc["catalog"]["letter"])

    @property
    def key(self) -> str:
        return str(self.doc["catalog"]["key"])

    def reference(self) -> str:
        """What an attestation cites when this record stood in for step 9 (F14-R6)."""
        return f"evidence:{EVIDENCE_DIR}/{self.name}@{self.statement_hash}:{self.score}"


def evidence_dir(target_dir: Path) -> Path:
    return target_dir / EVIDENCE_DIR


def _number(path: Path) -> int:
    stem = path.stem
    prefix = f"{fidelity.ROOT_SUBJECT}-"
    if not stem.startswith(prefix) or not stem[len(prefix) :].isdigit():
        msg = f"{path.name}: an evidence record is named {prefix}<n>.yaml (F14-R3)"
        raise EvidenceError(msg)
    return int(stem[len(prefix) :])


def load(target_dir: Path) -> list[Record]:
    """Every record, oldest first by number. A record that does not validate raises, because the
    record decides whether a person reviews a proof (C7: a broken record is not silently none)."""
    directory = evidence_dir(target_dir)
    if not directory.is_dir():
        return []
    paths = [p for p in directory.iterdir() if p.is_file() and p.suffix in SUFFIXES]
    out = [Record(path, schemas.load_yaml(path, SCHEMA)) for path in paths]
    return sorted(out, key=lambda r: _number(r.path))


def newest(target_dir: Path) -> Record | None:
    records = load(target_dir)
    return records[-1] if records else None


def current(target_dir: Path, statement_hash: str | None = None) -> Record | None:
    """The newest record pinned to the root's statement as it stands, or ``None``."""
    root_hash = statement_hash or qa.subject_hash(target_dir, fidelity.ROOT_SUBJECT)
    pinned = [r for r in load(target_dir) if r.statement_hash == root_hash]
    return pinned[-1] if pinned else None


def summary(target_dir: Path, statement_hash: str) -> dict[str, Any] | None:
    """F14-R9: the index's ``statement_evidence`` — the newest record, whether it is current, and
    how many of its misformalization issues are open — or ``None`` with no record at all."""
    record = newest(target_dir)
    if record is None:
        return None
    return {
        "file": f"{EVIDENCE_DIR}/{record.name}",
        "key": record.key,
        "score": record.score,
        "letter": record.letter,
        "catalog_commit": str(record.doc["catalog"]["network_commit"]),
        "statement_hash": record.statement_hash,
        "current": record.statement_hash == statement_hash,
        "misformalization_open": sum(
            1 for i in record.doc["misformalization"] if i["state"] == "open"
        ),
    }


# --- the catalog ---------------------------------------------------------------------------------


def load_catalog(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = f"cannot read the catalog {path}: {exc}"
        raise EvidenceError(msg) from exc
    if not isinstance(doc, dict) or doc.get("schema") != CATALOG_SCHEMA:
        msg = f"{path} is not a {CATALOG_SCHEMA} catalog"
        raise EvidenceError(msg)
    return doc


def catalog_row(catalog: dict[str, Any], key: str) -> dict[str, Any]:
    """The row for ``key``, refusing a key the catalog does not hold or a row it did not score."""
    for row in catalog["rows"]:
        if row["key"] == key:
            if row["score"] is None:
                msg = f"{key} is not scored in the catalog ({'; '.join(row['reasons'])})"
                raise EvidenceError(msg)
            return dict(row)
    msg = f"the catalog holds no row {key!r} (F14-R4)"
    raise EvidenceError(msg)


def doc_from_row(  # noqa: PLR0913 — one argument per fact the record pins
    catalog: dict[str, Any],
    row: dict[str, Any],
    *,
    statement_hash: str,
    network_commit: str,
    recorded_by: str,
    date: str,
    attempts_recorded: int,
    ported: dict[str, str] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """R3: the record for one catalog row, validated. ``ported`` maps an upstream local definition
    to the ``defs/<Name>.lean`` it was ported to."""
    ported = ported or {}
    history = row.get("history")
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "subject": fidelity.ROOT_SUBJECT,
        "statement_hash": statement_hash,
        "catalog": {
            "file": CATALOG_FILE,
            "network_commit": network_commit,
            "key": row["key"],
            "fc_commit": catalog["fc_commit"],
            "score": row["score"],
            "letter": row["letter"],
            "reasons": list(row["reasons"]),
        },
        "registry_history": (
            {"first": history["first"], "last": history["last"], "commits": history["n"]}
            if isinstance(history, dict) and history.get("first")
            else None
        ),
        "misformalization": [
            {k: issue[k] for k in ("number", "state", "url", "created", "closed", "pr")}
            for issue in row.get("issues") or []
        ],
        "local_definitions": [
            {"upstream_name": name, "ported_to": ported.get(name)}
            for name in row.get("local_defs") or []
        ],
        "registry_helpers": [],
        "external_attempts_recorded": attempts_recorded,
        "hazards": list(row.get("hazards") or []),
        "site_status": row.get("site_status"),
        "mathlib_definition": row.get("mathlib_definition"),
        "recorded_by": recorded_by,
        "date": date[:10],
    }
    if note is not None:
        doc["note"] = note
    return schemas.validate(doc, SCHEMA)


def write(target_dir: Path, doc: dict[str, Any]) -> Path:
    """Append one validated record as the next ``root-<n>.yaml``."""
    schemas.validate(doc, SCHEMA)
    directory = evidence_dir(target_dir)
    directory.mkdir(parents=True, exist_ok=True)
    taken = {_number(r.path) for r in load(target_dir)}
    n = max(taken, default=0) + 1
    path = directory / f"{fidelity.ROOT_SUBJECT}-{n}.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    log.info(
        "evidence: %s scored %s (%s) as %s",
        target_dir.name,
        doc["catalog"]["score"],
        doc["catalog"]["letter"],
        path.name,
    )
    return path


def record_attempts(
    target_dir: Path, catalog: dict[str, Any], row: dict[str, Any], *, statement_hash: str
) -> list[Path]:
    """R4: each statement AlphaProof Nexus lists as attempted, one ledger entry each, dated by the
    list's publication and pinned to the root's hash. An entry already on the ledger is skipped,
    so a second ``evidence add`` after a revision writes only what is new."""
    names = list(row.get("nexus_attempted") or [])
    published = catalog.get("nexus_published")
    if not names:
        return []
    if not published:
        msg = f"{row['key']} names Nexus attempts, but the catalog records no publication date"
        raise EvidenceError(msg)
    existing = {(e.url, e.statement_hash) for e in qa.load_attempts(target_dir)}
    written: list[Path] = []
    for name in names:
        url = f"{NEXUS_ATTEMPTED_URL}#{name}"
        if (url, statement_hash) in existing:
            continue
        written.append(
            qa.record_attempt(
                target_dir,
                venue=NEXUS_VENUE,
                system=NEXUS_SYSTEM,
                date=str(published),
                url=url,
                statement_hash=statement_hash,
                note=(
                    f"`{name}` is listed as attempted and not solved; dated by the list's "
                    "publication"
                ),
            )
        )
    return written


def add(  # noqa: PLR0913 — one argument per fact the act records
    target_dir: Path,
    catalog: dict[str, Any],
    key: str,
    *,
    network_commit: str,
    recorded_by: str,
    date: str,
    upstream_path: str | None = None,
    ported: dict[str, str] | None = None,
    note: str | None = None,
) -> tuple[Path, ...]:
    """R4: write the evidence record for ``key`` and the attempts it names, refusing before
    anything is written when the key is unknown or unscored, or when the row is for another file
    than the one the target was imported from."""
    row = catalog_row(catalog, key)
    if upstream_path is not None and row["file"] != upstream_path:
        msg = (
            f"{key} is the catalog row for {row['file']}, and {target_dir.name} was imported from "
            f"{upstream_path} (F14-R4)"
        )
        raise EvidenceError(msg)
    statement_hash = qa.subject_hash(target_dir, fidelity.ROOT_SUBJECT)
    # Validate the record before the ledger is touched, so a refusal writes nothing (C7). Every
    # attempt the row names is on the ledger once this returns, whether written now or before.
    doc = doc_from_row(
        catalog,
        row,
        statement_hash=statement_hash,
        network_commit=network_commit,
        recorded_by=recorded_by,
        date=date,
        attempts_recorded=len(row.get("nexus_attempted") or []),
        ported=ported,
        note=note,
    )
    attempts = record_attempts(target_dir, catalog, row, statement_hash=statement_hash)
    path = write(target_dir, doc)
    ledger = (qa.attempts_path(target_dir),) if attempts else ()
    return (*ledger, path)
