"""The watchers (F12-R11, R12; D-10 v3.12): an inherited statement is watched at its pin.

The registries the network inherits from correct roughly one statement in ten, most found by
provers after merge, so a pinned copy goes stale in silence — and a problem can be resolved
somewhere else while the frontier works on it. Two checks, each with one consequence and
neither with authority over a grade:

- **Upstream edit.** For each target whose provenance names an upstream path and commit, the
  path at the pinned commit is compared with the path at upstream head. A difference opens a
  D-8 revision request carrying the diff, writes a ``drift/v1`` record that flags the target,
  and freezes proving compute: the products derive ``claimable: false`` while the flag stands
  (``drift_state``). The fidelity grade does not move — D-9 downgrades on a *confirmed* defect,
  and an upstream edit is a signal.
- **Resolved elsewhere.** For each source that publishes the problem's status, a flip away
  from open writes a ``resolved-elsewhere`` record with the citation attached. It never changes
  the target's status: dormancy is a curator's declaration (D-33), and this is the notice.

The flag is scoped to the root's statement hash at the time: a D-8 revision changes the hash
and lifts it, and a curator who judges the edit irrelevant appends a ``cleared`` record
(F12-Q16). Everything fetched is untrusted text — capped here, escaped at render, never
interpolated into a command (F12 §7).

Upstream is reached through one seam, ``UpstreamHost``, so the fast tier fakes it. A host that
cannot be reached is a warning and a non-zero exit, and writes nothing: silence must never read
as an all-clear (AC20, C7). The real host reads public repositories unauthenticated — the head
commit through ``git ls-remote`` and the file through the raw content host — and a source's page
through the standard library (F12 §7, C5).
"""

from __future__ import annotations

import difflib
import html
import logging
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml

from opn_gate import config, intake, layout, qa, schemas

log = logging.getLogger(__name__)

DRIFT_SCHEMA = "drift/v1"
DRIFT_DIR = "drift"
REVISION_SCHEMA = "revision-request/v2"
UPSTREAM_DRIFT = "upstream-drift"
WATCHER = "opn-watcher"
KIND_EDIT = "upstream-edit"
KIND_RESOLVED = "resolved-elsewhere"
FLAGGED = "flagged"
CLEARED = "cleared"
DIFF_CAP = 16384  # drift/v1's cap on the diff
EVIDENCE_CAP = 2000  # revision-request's cap on the evidence text
OPEN_STATUS = "open"
SUFFIXES: tuple[str, ...] = (".yaml", ".yml")
RAW_URL = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
FETCH_TIMEOUT_S = 30
_GITHUB_REPO_RE = re.compile(r"^https?://github\.com/(?P<repo>[^/]+/[^/#?]+)")
_ERDOS_URL_RE = re.compile(r"^https?://(?:www\.)?erdosproblems\.com/")
#: The status badge on an erdosproblems.com page, as the seed pass read it
#: (docs/seed_conjecture_sources_build.py); the site publishes no API.
_ERDOS_STATUS_RE = re.compile(
    r'<span class="tooltip">\s*(.*?)\s*<span class="tooltiptext">\s*(.*?)\s*</span>', re.S
)
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class UpstreamError(RuntimeError):
    """Upstream could not be read; the message carries no credential."""


class UpstreamHost(Protocol):
    """Everything the watcher asks of the outside world."""

    def head(self, repo: str) -> str:
        """The commit at the repository's default branch."""

    def fetch(self, repo: str, ref: str, path: str) -> bytes | None:
        """The file at ``ref``, or ``None`` when it does not exist there."""

    def page(self, url: str) -> str:
        """A source's page, as text."""


class GitUpstreamHost:
    """The real seam: ``git ls-remote`` for the head, the raw content host for files, and the
    standard library for pages. Unauthenticated, read-only, one fetch per call."""

    def __init__(self, *, git: str = "git", timeout_s: int = FETCH_TIMEOUT_S) -> None:
        self.git = git
        self.timeout_s = timeout_s

    def head(self, repo: str) -> str:
        proc = subprocess.run(
            [self.git, "ls-remote", f"https://github.com/{repo}", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=self.timeout_s,
            env=config.child_environment(drop=config.GIT_REPO_VARIABLES),
        )
        if proc.returncode != 0:
            msg = f"git ls-remote {repo} failed: {proc.stderr.strip()[:200]}"
            raise UpstreamError(msg)
        sha = proc.stdout.split()[0] if proc.stdout.split() else ""
        if not _SHA_RE.match(sha):
            msg = f"git ls-remote {repo} answered no commit"
            raise UpstreamError(msg)
        return sha

    def fetch(self, repo: str, ref: str, path: str) -> bytes | None:
        url = RAW_URL.format(repo=repo, ref=ref, path=path)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "opn-watcher"})  # noqa: S310
            with urllib.request.urlopen(request, timeout=self.timeout_s) as resp:  # noqa: S310
                body: bytes = resp.read()
                return body
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            msg = f"fetching {url} answered {exc.code}"
            raise UpstreamError(msg) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            msg = f"fetching {url} failed: {exc.__class__.__name__}"
            raise UpstreamError(msg) from exc

    def page(self, url: str) -> str:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "opn-watcher"})  # noqa: S310
            with urllib.request.urlopen(request, timeout=self.timeout_s) as resp:  # noqa: S310
                return str(resp.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            msg = f"fetching {url} failed: {exc.__class__.__name__}"
            raise UpstreamError(msg) from exc


# --- the drift record --------------------------------------------------------------------------


@dataclass(frozen=True)
class DriftRecord:
    kind: str
    state: str
    statement_hash: str
    date: str
    author: str
    upstream: dict[str, str] | None = None
    citation: dict[str, str] | None = None
    diff: str | None = None
    clears: str | None = None
    note: str | None = None
    path: Path | None = None

    @property
    def name(self) -> str:
        return self.path.name if self.path is not None else "<unwritten>"

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema": DRIFT_SCHEMA,
            "kind": self.kind,
            "state": self.state,
            "statement_hash": self.statement_hash,
            "date": self.date,
            "author": self.author,
            "upstream": self.upstream,
            "citation": self.citation,
            "diff": self.diff,
        }
        if self.clears is not None:
            out["clears"] = self.clears
        if self.note is not None:
            out["note"] = self.note
        return out


@dataclass(frozen=True)
class DriftState:
    """What stands on a target for the root's current statement (R11, R14)."""

    statement_hash: str
    edit: DriftRecord | None  # a flagged, uncleared upstream edit
    resolved: DriftRecord | None  # a flagged, uncleared resolved-elsewhere notice

    @property
    def frozen(self) -> bool:
        """R11: compute is frozen while an upstream edit stands."""
        return self.edit is not None

    def as_dict(self) -> dict[str, Any] | None:
        current = self.edit or self.resolved
        if current is None:
            return None
        return {
            "kind": current.kind,
            "date": current.date,
            "record": current.name,
            "upstream": current.upstream,
            "citation": current.citation,
            "frozen": self.frozen,
        }


def drift_dir(target_dir: Path) -> Path:
    return target_dir / DRIFT_DIR


def load_drift(target_dir: Path) -> list[DriftRecord]:
    """Every drift record, oldest first by name; one that does not validate raises, because a
    flag derives claimability (C7: a broken flag is not silently no flag)."""
    directory = drift_dir(target_dir)
    if not directory.is_dir():
        return []
    out: list[DriftRecord] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file() and p.suffix in SUFFIXES):
        doc = schemas.load_yaml(path, DRIFT_SCHEMA)
        out.append(
            DriftRecord(
                kind=str(doc["kind"]),
                state=str(doc["state"]),
                statement_hash=str(doc["statement_hash"]),
                date=str(doc["date"]),
                author=str(doc["author"]),
                upstream=doc.get("upstream"),
                citation=doc.get("citation"),
                diff=doc.get("diff"),
                clears=doc.get("clears"),
                note=doc.get("note"),
                path=path,
            )
        )
    return out


def drift_state(target_dir: Path, statement_hash: str) -> DriftState:
    """The latest flagged record of each kind for this hash that no later record clears."""
    records = load_drift(target_dir)
    cleared = {r.clears for r in records if r.state == CLEARED and r.clears}
    latest: dict[str, DriftRecord] = {}
    for record in records:
        if record.state != FLAGGED or record.statement_hash != statement_hash:
            continue
        if record.name in cleared:
            continue
        latest[record.kind] = record
    return DriftState(statement_hash, latest.get(KIND_EDIT), latest.get(KIND_RESOLVED))


def write_drift(target_dir: Path, record: DriftRecord) -> Path:
    doc = schemas.validate(record.as_dict(), DRIFT_SCHEMA)
    stamp = record.date.replace("-", "").replace(":", "")
    path = drift_dir(target_dir) / f"{stamp}-{record.author}-{record.kind}.yaml"
    if path.exists():
        msg = f"{path} already exists; drift records are append-only"
        raise ValueError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def clear_drift(target_dir: Path, name: str, *, author: str, date: str, note: str) -> Path:
    """A curator's clearing of a flag they judged irrelevant (F12-Q16)."""
    flagged = {r.name: r for r in load_drift(target_dir) if r.state == FLAGGED}
    if name not in flagged:
        msg = f"{name} is not a flagged drift record of {target_dir.name}"
        raise ValueError(msg)
    record = DriftRecord(
        kind=flagged[name].kind,
        state=CLEARED,
        statement_hash=flagged[name].statement_hash,
        date=date,
        author=author,
        clears=name,
        note=note,
    )
    return write_drift(target_dir, record)


# --- reading a target's provenance --------------------------------------------------------------


@dataclass(frozen=True)
class Pin:
    repo: str
    path: str
    commit: str


def repo_of(url: str | None) -> str | None:
    """``owner/name`` from a GitHub url, or ``None``."""
    if not url:
        return None
    m = _GITHUB_REPO_RE.match(url)
    return m.group("repo") if m else None


def pin_of(doc: dict[str, Any]) -> Pin | None:
    """R11: the upstream path and commit a target's provenance names, with the repository from
    its source url; ``None`` for a target the network authored."""
    provenance = doc.get("provenance") or {}
    path, commit = provenance.get("upstream_path"), provenance.get("upstream_commit")
    if not (isinstance(path, str) and isinstance(commit, str) and _SHA_RE.match(commit)):
        return None
    candidates = [
        doc.get("source", {}).get("url"),
        *(s.get("url") for s in doc.get("sources") or []),
    ]
    for url in candidates:
        repo = repo_of(url if isinstance(url, str) else None)
        if repo is not None:
            return Pin(repo, path, commit)
    return None


def status_pages(doc: dict[str, Any]) -> list[str]:
    """R12: the source pages that publish a status — erdosproblems.com, by url."""
    urls: list[str] = []
    for source in doc.get("sources") or []:
        url = source.get("url")
        if source.get("kind") == "erdos" and isinstance(url, str):
            urls.append(url)
    forum = (doc.get("prior_art") or {}).get("forum_url")
    if isinstance(forum, str) and _ERDOS_URL_RE.match(forum) and forum not in urls:
        urls.append(forum)
    return urls


def parse_status(page: str) -> tuple[str, str] | None:
    """The status badge and its line, as the seed pass read them; ``None`` when absent."""
    m = _ERDOS_STATUS_RE.search(page)
    if not m:
        return None
    status = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
    line = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
    return status, line[:EVIDENCE_CAP]


def unified_diff(pinned: bytes | None, head: bytes | None, path: str) -> str:
    before = (pinned or b"").decode("utf-8", errors="replace").splitlines(keepends=True)
    after = (head or b"").decode("utf-8", errors="replace").splitlines(keepends=True)
    text = "".join(difflib.unified_diff(before, after, f"pinned/{path}", f"head/{path}"))
    if len(text) > DIFF_CAP:
        text = text[: DIFF_CAP - 40] + "\n[diff truncated at 16 KiB]\n"
    return text


# --- the run --------------------------------------------------------------------------------------


@dataclass
class TargetReport:
    target_id: str
    pin: Pin | None = None
    head_commit: str | None = None
    changed: bool | None = None  # None: not compared
    statuses: list[tuple[str, str]] = field(default_factory=list)  # (url, status)
    written: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def drift(self) -> str:
        """The upstream comparison's result, or why there is none. A status page that could
        not be read is a warning beside it, not a verdict on the pin."""
        if self.pin is None:
            return "not watched"
        if self.changed is None:
            return "unreachable"
        return "drifted" if self.changed else "unchanged"


@dataclass
class Report:
    date: str
    dry_run: bool
    targets: list[TargetReport] = field(default_factory=list)

    @property
    def problems(self) -> list[str]:
        return [f"{t.target_id}: {p}" for t in self.targets for p in t.problems]

    @property
    def exit_code(self) -> int:
        return 1 if self.problems else 0

    def render(self) -> str:
        lines = [f"opn watcher {self.date} ({'dry run' if self.dry_run else 'live'})"]
        for t in self.targets:
            where = (
                f"{t.pin.repo}:{t.pin.path} @ {t.pin.commit[:12]}" if t.pin else "no upstream pin"
            )
            head = f" -> {t.head_commit[:12]}" if t.head_commit else ""
            lines.append(f"  {t.target_id:<24} {t.drift:<12} {where}{head}")
            lines.extend(f"      status {status!r} at {url}" for url, status in t.statuses)
            lines.extend(f"      wrote {w}" for w in t.written)
            lines.extend(f"      note: {n}" for n in t.notes)
            lines.extend(f"      WARNING: {p}" for p in t.problems)
        if self.problems:
            lines.append(
                "WARNING: upstream could not be read for some targets; nothing was "
                "written for them and this is not an all-clear (F12-AC20)"
            )
        return "\n".join(lines) + "\n"


def watch(  # noqa: PLR0915 — one statement per fact the report records
    graph_root: Path,
    host: UpstreamHost,
    *,
    date: str,
    dry_run: bool = False,
    targets: list[str] | None = None,
) -> Report:
    """R11, R12 over every curated target (or the ones named). One head fetch per repository
    (§6). A target whose upstream cannot be read is reported and left untouched (AC20)."""
    report = Report(date=date, dry_run=dry_run)
    heads: dict[str, str] = {}
    directory = graph_root / "targets"
    ids = targets or (
        sorted(p.name for p in directory.iterdir() if p.is_dir()) if directory.is_dir() else []
    )
    for target_id in ids:
        target_dir = directory / target_id
        item = TargetReport(target_id)
        report.targets.append(item)
        doc = intake.load_doc(target_dir)
        if doc is None:
            item.notes.append("no target record (pre-F11); not watched")
            continue
        pin = pin_of(doc)
        item.pin = pin
        try:
            root_hash = qa.subject_hash(target_dir, "root")
        except Exception as exc:  # a defective graph: named, and nothing written (C7)
            item.problems.append(f"the root cannot be read: {exc}")
            continue
        state = drift_state(target_dir, root_hash)
        if pin is not None:
            try:
                if pin.repo not in heads:
                    heads[pin.repo] = host.head(pin.repo)
                head = heads[pin.repo]
                item.head_commit = head
                pinned = host.fetch(pin.repo, pin.commit, pin.path)
                current = pinned if head == pin.commit else host.fetch(pin.repo, head, pin.path)
            except UpstreamError as exc:
                log.warning("watcher: %s: upstream unreachable: %s", target_id, exc)
                item.problems.append(str(exc))
                continue
            if pinned is None:
                item.problems.append(
                    f"{pin.path} does not exist at the pinned commit {pin.commit[:12]}"
                )
                continue
            item.changed = pinned != current
            if item.changed:
                _flag_edit(
                    target_dir,
                    item,
                    pin=pin,
                    head=head,
                    pinned=pinned,
                    current=current,
                    root_hash=root_hash,
                    state=state,
                    date=date,
                    dry_run=dry_run,
                )
        for url in status_pages(doc):
            try:
                page = host.page(url)
            except UpstreamError as exc:
                log.warning("watcher: %s: %s unreachable: %s", target_id, url, exc)
                item.problems.append(str(exc))
                continue
            parsed = parse_status(page)
            if parsed is None:
                item.notes.append(f"{url}: no status badge found")
                continue
            status, line = parsed
            item.statuses.append((url, status))
            if status.casefold() != OPEN_STATUS:
                _flag_resolved(
                    target_dir,
                    item,
                    url=url,
                    status=status,
                    line=line,
                    root_hash=root_hash,
                    state=state,
                    date=date,
                    dry_run=dry_run,
                )
    return report


def _flag_edit(  # noqa: PLR0913 — the facts of one flag
    target_dir: Path,
    item: TargetReport,
    *,
    pin: Pin,
    head: str,
    pinned: bytes,
    current: bytes | None,
    root_hash: str,
    state: DriftState,
    date: str,
    dry_run: bool,
) -> None:
    if state.edit is not None and (state.edit.upstream or {}).get("head_commit") == head:
        item.notes.append(f"already flagged by {state.edit.name}")
        return
    diff = unified_diff(pinned, current, pin.path)
    removed = current is None
    if dry_run:
        item.notes.append(
            f"would flag upstream-edit ({'path removed upstream' if removed else 'path changed'}, "
            f"{len(diff)} bytes of diff) and open a revision request"
        )
        return
    record = DriftRecord(
        kind=KIND_EDIT,
        state=FLAGGED,
        statement_hash=root_hash,
        date=date,
        author=WATCHER,
        upstream={
            "repo": pin.repo,
            "path": pin.path,
            "pinned_commit": pin.commit,
            "head_commit": head,
        },
        diff=diff,
        note="the path removed upstream" if removed else None,
    )
    graph_root = target_dir.parents[1]
    written = write_drift(target_dir, record)
    item.written.append(written.relative_to(graph_root).as_posix())
    item.written.append(_revision_request(target_dir, pin, head, diff, date=date))


def _revision_request(target_dir: Path, pin: Pin, head: str, diff: str, *, date: str) -> str:
    """R11: the D-8 request the flag opens, carrying the diff (capped; the record has it whole).
    A curator acts on it by versioning the root (F08-R9) or clears the flag (Q16)."""
    graph_root = target_dir.parents[1]
    root = qa.root_node(target_dir)
    head_line = (
        f"upstream {pin.repo} changed {pin.path} between the pinned {pin.commit[:12]} and head "
        f"{head[:12]} (D-10 v3.12). The full diff is in the target's drift record. "
    )
    text = (head_line + diff)[:EVIDENCE_CAP]
    doc = {
        "schema": REVISION_SCHEMA,
        "node": root,
        "contributor": WATCHER,
        "defect_class": UPSTREAM_DRIFT,
        "evidence": {"text": text},
        "date": date[:10],
    }
    schemas.validate(doc, REVISION_SCHEMA)
    stamp = date.replace("-", "").replace(":", "")
    path = (
        layout.graph_nodes_dir(graph_root, target_dir.name)
        / root
        / "revisions"
        / f"{stamp}-{WATCHER}.yaml"
    )
    if path.exists():
        msg = f"{path} already exists; revision requests are append-only"
        raise ValueError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path.relative_to(graph_root).as_posix()


def _flag_resolved(  # noqa: PLR0913 — the facts of one flag
    target_dir: Path,
    item: TargetReport,
    *,
    url: str,
    status: str,
    line: str,
    root_hash: str,
    state: DriftState,
    date: str,
    dry_run: bool,
) -> None:
    if state.resolved is not None and (state.resolved.citation or {}).get("status") == status:
        item.notes.append(f"already flagged by {state.resolved.name}")
        return
    if dry_run:
        item.notes.append(f"would flag resolved-elsewhere ({status!r} at {url}) for D-33 dormancy")
        return
    record = DriftRecord(
        kind=KIND_RESOLVED,
        state=FLAGGED,
        statement_hash=root_hash,
        date=date,
        author=WATCHER,
        citation={"url": url, "status": status[:100], "text": line},
        note="flagged for D-33 dormancy: the curator decides; the status is untouched (R12)",
    )
    written = write_drift(target_dir, record)
    item.written.append(written.relative_to(target_dir.parents[1]).as_posix())
    log.warning("watcher: %s is %s at %s — flagged for D-33 dormancy", target_dir.name, status, url)
