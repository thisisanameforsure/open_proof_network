"""The Palomar feed watcher and the registration drift check (F25-R14; D-10 v3.37, D-25 v3.35).

Palomar publishes every registered formalization in ``recent.json`` (CC0). Two questions the
network asks of it, once a week, through the one seam ``palomar_host.PalomarHost``:

- **Has somebody registered a proof of a problem the network lists?** Each entry is matched to
  the network's targets by the problem's *number as a token* in the entry's title, abstract,
  theorem names, repository or project path (``Erdős 257``, ``erdos-257``, ``erdos_257``,
  ``Erdos257``, ``E257``, ``#257``, ``/257.lean``) — never as a bare substring, so ``1257`` and
  ``2570`` say nothing of 257. A match is a *candidate* with the evidence that produced it and a
  confidence: ``number`` when the entry names the problem in words (``Erdős 257``, an
  erdosproblems.com url), ``inferred`` when only an identifier carries the number (a namespace,
  a file name, a repository). A candidate is information; with ``--propose`` the tool writes an
  **unsigned** ``literature/v1`` proposal (status ``known``) into an output directory, never into
  the graph, and it never confirms (Q11): confirmation is a steward's or curator's act.
- **Does the registry still say what the network's registration records say?** For the latest
  registration record per registry id (``registrations.latest``), the entry at that id and
  version is fetched and its ``challenge_sha256``, ``solution_sha256`` and status compared with
  the record's. A difference is reported, never written: the record is a curator's and the
  registry's review is the registry's.

An unreachable feed is a warning and exit 1 with nothing written (C7: silence is never an
all-clear). Everything read from the feed is untrusted text: capped where it enters a record,
escaped wherever shown, never interpolated into a command.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml

from opn_gate import intake, literature, palomar, palomar_host, records, registrations, schemas

log = logging.getLogger(__name__)

Confidence = Literal["number", "inferred"]
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
FILE_TIMESTAMP = "%Y%m%dT%H%M%SZ"  # the appends' file-name stamp (api/opn_api/appends.py)
#: What a feed entry is read for; untrusted text, capped before it reaches a record.
TITLE_CAP = 300  # literature/v1 reference title
SUMMARY_CAP = 2000  # literature/v1 summary
EVIDENCE_CAP = 200
_NUM = r"(?<![0-9]){n}(?![0-9])"
_ERDOS_URL_RE = re.compile(r"https?://(?:www\.)?erdosproblems\.com/(?P<n>[0-9]+)(?![0-9])")
_FC_REF_RE = re.compile(r"FormalConjectures/ErdosProblems/(?P<n>[0-9]+)\.lean$")
#: Every token shape the matcher recognises, with the group that carries the number.
_TOKEN_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"[Ee]rd[őoö]s(?:'s)?(?:\s+[Pp]roblem)?\s*#?\s*(?P<n>[0-9]+)(?![0-9])"),
    _ERDOS_URL_RE,
    re.compile(r"(?<![A-Za-z0-9])[Ee]rd[őoö]s[-_]?(?P<n>[0-9]+)(?![0-9])"),
    re.compile(r"(?<![A-Za-z0-9])E(?P<n>[0-9]+)(?![0-9])"),
    re.compile(r"#\s*(?P<n>[0-9]+)(?![0-9])"),
    re.compile(r"/(?P<n>[0-9]+)\.lean(?![A-Za-z0-9])"),
)


class FeedError(Exception):
    """The feed could not be used as asked; nothing was written."""


@dataclass(frozen=True)
class TargetKey:
    """One target as the matcher sees it: its id, its Erdős number if it has one, its title."""

    target_id: str
    number: int | None
    title: str


@dataclass(frozen=True)
class Candidate:
    """A feed entry that may formalise a target's problem; information, never a verdict."""

    target_id: str
    registry_id: str
    version: int
    title: str
    evidence: str
    confidence: Confidence

    @property
    def url(self) -> str:
        return palomar_host.entry_url(self.registry_id, self.version)

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target_id,
            "registry_id": self.registry_id,
            "version": self.version,
            "url": self.url,
            "title": self.title,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


# --- the targets ------------------------------------------------------------------------------


def number_of(doc: dict[str, Any]) -> int | None:
    """The Erdős number a target record names: an erdosproblems.com url in ``source.url``,
    ``prior_art.forum_url`` or ``sources[].url``, or a ``FormalConjectures/ErdosProblems/<n>.lean``
    registry path in ``source.ref``; ``None`` for a target that names none."""
    source: dict[str, Any] = doc["source"] if isinstance(doc.get("source"), dict) else {}
    prior: dict[str, Any] = doc["prior_art"] if isinstance(doc.get("prior_art"), dict) else {}
    urls = [source.get("url"), prior.get("forum_url")]
    for extra in doc.get("sources") or []:
        if isinstance(extra, dict):
            urls.append(extra.get("url"))
    for url in urls:
        if isinstance(url, str):
            m = _ERDOS_URL_RE.search(url)
            if m:
                return int(m.group("n"))
    ref = source.get("ref")
    if isinstance(ref, str):
        m = _FC_REF_RE.search(ref)
        if m:
            return int(m.group("n"))
    return None


def targets_index(graph_root: Path) -> dict[str, TargetKey]:
    """Every target with a record under ``targets/``, keyed by id. A target with no
    ``target.yaml`` (the tutorial) is not indexed: with no record there is nothing to match on."""
    out: dict[str, TargetKey] = {}
    targets = graph_root / "targets"
    if not targets.is_dir():
        return out
    for target_dir in sorted(p for p in targets.iterdir() if p.is_dir()):
        try:
            doc = intake.load_doc(target_dir)
        except schemas.SchemaError as exc:
            log.warning(
                "%s: a target record that does not read is not indexed: %s", target_dir, exc
            )
            continue
        if doc is None:
            continue
        target_id = str(doc.get("id") or target_dir.name)
        out[target_id] = TargetKey(target_id, number_of(doc), str(doc.get("title") or ""))
    return out


# --- the matcher ------------------------------------------------------------------------------

#: The fields read, in the order their evidence is preferred.
_WORD_FIELDS = ("title", "abstract")
_IDENTIFIER_FIELDS = ("theorem_names", "repository", "project_path")


def _texts(entry: dict[str, Any]) -> list[tuple[str, str]]:
    """``(field, text)`` for every field the matcher reads, in preference order."""
    out: list[tuple[str, str]] = []
    for field in _WORD_FIELDS:
        value = entry.get(field)
        if isinstance(value, str):
            out.append((field, value))
    formalization = entry.get("formalization")
    if isinstance(formalization, dict):
        names = formalization.get("theorem_names")
        if isinstance(names, list):
            out.append(("theorem_names", " ".join(str(n) for n in names)))
    source = entry.get("source")
    if isinstance(source, dict):
        for field in ("repository", "project_path"):
            value = source.get(field)
            if isinstance(value, str):
                out.append((field, value))
    return out


def _hits(text: str) -> list[tuple[int, re.Match[str]]]:
    """Every token in ``text`` that carries a problem number, with the pattern's rank."""
    found: list[tuple[int, re.Match[str]]] = []
    for rank, pattern in enumerate(_TOKEN_RES):
        found.extend((rank, m) for m in pattern.finditer(text))
    return found


def _confidence(field: str, rank: int) -> Confidence:
    """Words name a problem (``Erdős 257``, an erdosproblems url, in the title or abstract);
    everything else — a namespace, a file name, a repository, ``E257``, a bare ``#257`` — is an
    inference about what the number means."""
    return "number" if field in _WORD_FIELDS and rank <= 1 else "inferred"


def numbers_named(entry: dict[str, Any]) -> set[int]:
    """Every problem number an entry carries as a token, whatever its confidence (for guards)."""
    return {int(m.group("n")) for _, text in _texts(entry) for _, m in _hits(text)}


def _snippet(text: str, m: re.Match[str]) -> str:
    lo, hi = max(0, m.start() - 30), min(len(text), m.end() + 30)
    piece = text[lo:hi].replace("\n", " ")
    return ("…" if lo else "") + piece + ("…" if hi < len(text) else "")


def match(entries: list[dict[str, Any]], keys: dict[str, TargetKey]) -> list[Candidate]:
    """Every (target, entry) pair whose problem number is a token of the entry, one candidate
    per pair at the best confidence its evidence allows; targets with no number never match."""
    by_number: dict[int, list[TargetKey]] = {}
    for key in keys.values():
        if key.number is not None:
            by_number.setdefault(key.number, []).append(key)
    out: list[Candidate] = []
    for entry in entries:
        registry_id = str(entry.get("id") or "")
        if not palomar_host.ID_RE.match(registry_id):
            log.warning("a feed entry with no Palomar id is passed over: %r", registry_id)
            continue
        best: dict[str, tuple[int, str]] = {}  # target -> (score, evidence); lower is better
        for field, text in _texts(entry):
            for rank, m in _hits(text):
                for key in by_number.get(int(m.group("n")), ()):
                    conf = _confidence(field, rank)
                    score = (0 if conf == "number" else 1) * 100 + rank
                    if key.target_id not in best or score < best[key.target_id][0]:
                        evidence = f"{field}: {_snippet(text, m)}"[:EVIDENCE_CAP]
                        best[key.target_id] = (score, evidence)
        for target_id, (score, evidence) in best.items():
            out.append(
                Candidate(
                    target_id=target_id,
                    registry_id=registry_id,
                    version=int(entry.get("version") or 1),
                    title=str(entry.get("title") or "")[:TITLE_CAP],
                    evidence=evidence,
                    confidence="number" if score < 100 else "inferred",
                )
            )
    out.sort(key=lambda c: (c.target_id, c.registry_id, c.version))
    return out


def report(  # noqa: PLR0913 — one keyword per field of the report
    candidates: list[Candidate],
    *,
    entries: int,
    targets: int,
    drift_found: list[dict[str, Any]] | None = None,
    proposals: list[str] | None = None,
    source: str = "palomar",
) -> str:
    """The run's report as JSON, one document on one line."""
    doc: dict[str, Any] = {
        "ok": True,
        "source": source,
        "entries": entries,
        "targets": targets,
        "candidates": [c.as_dict() for c in candidates],
        "proposals": list(proposals or []),
        "drift": drift_found if drift_found is not None else None,
    }
    return json.dumps(doc, ensure_ascii=False) + "\n"


# --- proposals --------------------------------------------------------------------------------


def _root_of(graph_root: Path, target_id: str) -> str:
    target_dir = graph_root / "targets" / target_id
    declared = records.declared_root(target_dir)
    if declared:
        return declared
    nodes_dir = target_dir / "nodes"
    nodes = sorted(p.name for p in nodes_dir.iterdir() if p.is_dir()) if nodes_dir.is_dir() else []
    if len(nodes) == 1:
        return nodes[0]
    msg = (
        f"{target_id}: no status record declares a root and the target has {len(nodes)} nodes; "
        "a proposal is filed under the root, so declare one first (F11-R14)"
    )
    raise FeedError(msg)


def propose(
    graph_root: Path,
    candidate: Candidate,
    *,
    contributor: str,
    out: Path,
    date: str | None = None,
) -> Path:
    """Write an unsigned ``literature/v1`` proposal for ``candidate`` under
    ``out/targets/<target>/nodes/<root>/literature/``, the path it would take on the graph; the
    graph itself is never written, and nothing is confirmed (Q11). The record validates before it
    is written."""
    node = _root_of(graph_root, candidate.target_id)
    when = date or datetime.now(tz=UTC).strftime(DATE_FORMAT)
    stamp = datetime.strptime(when, DATE_FORMAT).replace(tzinfo=UTC).strftime(FILE_TIMESTAMP)
    summary = (
        f"Palomar entry {candidate.registry_id} (version {candidate.version}) registers a "
        f"Lean formalization whose record names this problem; the match is {candidate.confidence} "
        f"from {candidate.evidence}. A proposal from the feed watcher: whether the entry proves "
        f"this statement is for a steward or curator to read and confirm."
    )
    doc: dict[str, Any] = {
        "schema": literature.SCHEMA,
        "node": node,
        "contributor": contributor,
        "date": when,
        "status": "known",
        "references": [
            {
                "title": f"{candidate.registry_id}: {candidate.title}"[:TITLE_CAP],
                "url": candidate.url,
                "note": "a registered, machine-verified formalization in the Palomar registry",
            }
        ],
        "summary": summary[:SUMMARY_CAP],
        "model_and_tooling": "opn-gate palomar-feed (F25-R14)",
        "confirms": None,
        "via": None,
        "key": None,
        "signature": None,
    }
    validated = schemas.validate(doc, literature.SCHEMA)
    path = (
        out
        / "targets"
        / candidate.target_id
        / "nodes"
        / node
        / literature.DIR
        / f"{stamp}-{contributor}.yaml"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(validated, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return path


# --- drift ------------------------------------------------------------------------------------

_COMPARED: tuple[str, ...] = ("challenge_sha256", "solution_sha256")


def _registry_status(entry: dict[str, Any]) -> str:
    """Palomar's status in the record's vocabulary where the two agree (``registered``,
    ``withdrawn``); anything else is compared as the registry spells it."""
    return str(entry.get("status") or "")


def drift(graph_root: Path, host: palomar_host.PalomarHost) -> list[dict[str, Any]]:
    """For the latest registration record per registry id (withdrawn and not-yet-registered ones
    set aside), fetch the registry's entry at that id and version and report every difference
    in ``challenge_sha256``, ``solution_sha256`` and status; an id the registry no longer serves
    is reported as ``missing``. Nothing is written. A host error propagates: the run is then not
    an all-clear."""
    out: list[dict[str, Any]] = []
    targets = graph_root / "targets"
    if not targets.is_dir():
        return out
    for target_dir in sorted(p for p in targets.iterdir() if p.is_dir()):
        for rec in registrations.latest(registrations.load(target_dir)).values():
            rid, version = rec.doc.get("registry_id"), rec.doc.get("version")
            if not isinstance(rid, str) or not isinstance(version, int):
                continue  # submitted, no id yet: nothing to compare
            if rec.doc.get("status") == registrations.WITHDRAWN:
                continue
            row: dict[str, Any] = {
                "target": target_dir.name,
                "registry_id": rid,
                "version": version,
                "record": rec.path.name,
            }
            entry = host.entry(rid, version)
            if entry is None:
                out.append({**row, "kind": "missing", "differences": []})
                continue
            try:
                entry = palomar.read_entry(entry)
            except palomar.PalomarDocumentError as exc:
                out.append({**row, "kind": "unreadable", "differences": [], "problem": str(exc)})
                continue
            verification = entry.get("verification") or {}
            differences = [
                {"field": f, "record": rec.doc.get(f), "registry": verification.get(f)}
                for f in _COMPARED
                if rec.doc.get(f) != verification.get(f)
            ]
            if rec.doc.get("status") != _registry_status(entry):
                differences.append(
                    {
                        "field": "status",
                        "record": rec.doc.get("status"),
                        "registry": _registry_status(entry),
                    }
                )
            if differences:
                out.append({**row, "kind": "changed", "differences": differences})
    return out


# --- the run ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class RunResult:
    report: dict[str, Any]
    exit_code: int

    def render(self) -> str:
        return json.dumps(self.report, ensure_ascii=False) + "\n"


def load_snapshot(path: Path) -> list[dict[str, Any]]:
    """A saved ``recent.json`` (``{"entries": [...]}``, or a bare list) as the feed."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = f"cannot read the snapshot {path}: {exc}"
        raise FeedError(msg) from exc
    entries = doc.get("entries") if isinstance(doc, dict) else doc
    if not isinstance(entries, list):
        msg = f"the snapshot {path} is not a feed: no entries list"
        raise FeedError(msg)
    return [e for e in entries if isinstance(e, dict)]


def default_host() -> palomar_host.PalomarHost:
    """The real registry; a seam the tests replace."""
    return palomar_host.HttpPalomarHost()


_propose, _drift = propose, drift  # the functions, under the names the flags take below


def run(  # noqa: PLR0913 — one keyword per flag
    graph_root: Path,
    host: palomar_host.PalomarHost | None,
    *,
    snapshot: Path | None = None,
    propose: bool = False,
    contributor: str | None = None,
    out: Path | None = None,
    drift: bool = False,
    date: str | None = None,
) -> RunResult:
    """One run: read the feed (from ``snapshot`` when given, else from ``host``), match, report;
    with ``propose`` write a proposal per candidate under ``out``; with ``drift`` compare every
    registration record with the registry. An unreachable or refusing host is a warning, exit 1
    and nothing written."""
    if propose and (not contributor or out is None):
        msg = "--propose needs --contributor and --out"
        raise FeedError(msg)
    keys = targets_index(graph_root)
    source = str(snapshot) if snapshot is not None else "palomar"
    try:
        if snapshot is not None:
            entries = load_snapshot(snapshot)
        else:
            if host is None:
                host = default_host()
            feed = host.recent()
            entries = [e for e in feed.get("entries", []) if isinstance(e, dict)]
        candidates = match(entries, keys)
        drift_found: list[dict[str, Any]] | None = None
        if drift:
            if host is None:
                host = default_host()
            drift_found = _drift(graph_root, host)
    except palomar_host.PalomarError as exc:
        log.warning("the registry could not be read; nothing written: %s", exc)
        return RunResult(
            {
                "ok": False,
                "source": source,
                "warning": f"the registry is unreachable or refused: {exc}",
                "entries": 0,
                "targets": len(keys),
                "candidates": [],
                "proposals": [],
                "drift": None,
            },
            1,
        )
    written: list[str] = []
    if propose:
        assert contributor is not None and out is not None
        for cand in candidates:
            written.append(
                str(_propose(graph_root, cand, contributor=contributor, out=out, date=date))
            )
    text = report(
        candidates,
        entries=len(entries),
        targets=len(keys),
        drift_found=drift_found,
        proposals=written,
        source=source,
    )
    return RunResult(json.loads(text), 0)
