"""F12-T5: the watchers (R11, R12; AC8, AC9, AC20; Q1, Q16).

Every consequence of a drift signal is a flag and a freeze, never a downgrade: the tests hold
that line on both sides — the freeze reaches the products, the grade does not move, the status
is untouched — and that a host that cannot be read is a warning that writes nothing, because a
silent all-clear is the one answer a watcher must never give.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import fidelity, modes, products, qa, schemas, watch
from opn_gate.paths import Change
from opn_gate.watch import UpstreamError

REPO = "google-deepmind/formal-conjectures"
PATH = "FormalConjectures/ErdosProblems/68.lean"
PINNED = "c" * 40
HEAD = "d" * 40
SOURCE_URL = f"https://github.com/{REPO}/blob/{PINNED}/{PATH}"
ERDOS_URL = "https://www.erdosproblems.com/68"
WHEN = "2026-09-12T04:17:00Z"
UPSTREAM_TEXT = b"theorem erdos_68 : Irrational (\\sum n, 1 / (n ! - 1)) := by\n  sorry\n"
EDITED_TEXT = (
    b"theorem erdos_68 : Irrational (\\sum n in Set.Ici 2, 1 / (n ! - 1)) := by\n  sorry\n"
)
INJECTION = "<script>alert('drift')</script>"


def erdos_page(status: str, line: str = "Erdős [Er68b]") -> str:
    return (
        "<html><body><h1>#68</h1>"
        f'<span class="tooltip">{status}<span class="tooltiptext">{line}</span></span>'
        '<div id="content">Is the sum irrational?</div></body></html>'
    )


@dataclass
class FakeUpstream:
    """The seam, scripted: heads per repository, files per (repo, ref, path), pages per url.
    ``fail`` makes every call raise (an outage or a 401); ``calls`` is what was asked."""

    heads: dict[str, str] = field(default_factory=lambda: {REPO: HEAD})
    files: dict[tuple[str, str, str], bytes] = field(
        default_factory=lambda: {
            (REPO, PINNED, PATH): UPSTREAM_TEXT,
            (REPO, HEAD, PATH): EDITED_TEXT,
        }
    )
    pages: dict[str, str] = field(default_factory=lambda: {ERDOS_URL: erdos_page("OPEN")})
    fail: str | None = None
    calls: list[str] = field(default_factory=list)

    def head(self, repo: str) -> str:
        self.calls.append(f"head:{repo}")
        if self.fail:
            raise UpstreamError(self.fail)
        return self.heads[repo]

    def fetch(self, repo: str, ref: str, path: str) -> bytes | None:
        self.calls.append(f"fetch:{repo}:{ref[:4]}:{path}")
        if self.fail:
            raise UpstreamError(self.fail)
        return self.files.get((repo, ref, path))

    def page(self, url: str) -> str:
        self.calls.append(f"page:{url}")
        if self.fail:
            raise UpstreamError(self.fail)
        return self.pages[url]


def imported_target(tmp_path: Path, target_id: str = "erdos-68", **overrides: Any) -> Path:
    """A curated target imported from Formal Conjectures at ``PINNED``, as import-fc leaves it."""
    root = copy_graph(tmp_path) if not (tmp_path / "graph").exists() else tmp_path / "graph"
    take_in(
        root,
        target_id=target_id,
        track="open",
        source={"kind": "formal-conjectures", "ref": PATH, "url": SOURCE_URL},
        provenance={
            "statement_source": "formal-conjectures",
            "author": "The Formal Conjectures Authors",
            "adversarially_reviewed": False,
            "upstream_commit": PINNED,
            "upstream_path": PATH,
        },
        sources=[
            {
                "kind": "formal-conjectures",
                "url": SOURCE_URL,
                "accessed": "2026-09-12",
                "licence": "Apache-2.0",
                "attribution": "The Formal Conjectures Authors",
                "quote_policy": "cite",
            }
        ],
        prior_art={"arxiv_query": None, "forum_url": ERDOS_URL, "summary": "Open since 1968."},
        **overrides,
    )
    return root


def index_row(root: Path, target_id: str) -> dict[str, Any]:
    prod = products.generate(root, rendered_from="5" * 40, commit_time=WHEN)
    doc = json.loads(prod.files[Path("targets/index.json")])
    return next(r for r in doc["targets"] if r["target_id"] == target_id)


# --- AC8: an upstream edit is flagged, requested, and frozen — never downgraded -------------------


def test_upstream_drift(tmp_path: Path) -> None:
    """AC8, R11: the path changed upstream — a revision request carrying the diff is opened,
    the drift flag is set, claimable becomes false with the reason named, and the fidelity
    grade is unchanged."""
    root = imported_target(tmp_path)
    target = root / "targets" / "erdos-68"
    grade_before = fidelity.target_grade(target)
    host = FakeUpstream()

    report = watch.watch(root, host, date=WHEN)
    assert report.exit_code == 0
    item = next(t for t in report.targets if t.target_id == "erdos-68")
    assert item.drift == "drifted" and item.head_commit == HEAD
    drift_rel, request_rel = item.written
    assert drift_rel == "targets/erdos-68/drift/20260912T041700Z-opn-watcher-upstream-edit.yaml"
    record = schemas.load_yaml(root / drift_rel, watch.DRIFT_SCHEMA)
    assert record["kind"] == "upstream-edit" and record["state"] == "flagged"
    assert record["upstream"] == {
        "repo": REPO,
        "path": PATH,
        "pinned_commit": PINNED,
        "head_commit": HEAD,
    }
    assert "-theorem erdos_68 : Irrational" in record["diff"]
    assert "+theorem erdos_68 : Irrational (\\sum n in Set.Ici 2" in record["diff"]
    assert record["statement_hash"] == qa.subject_hash(target, "root")

    request = schemas.load_yaml(root / request_rel, "revision-request/v2")
    assert request["defect_class"] == "upstream-drift" and request["node"] == "and-reassoc"
    assert request["contributor"] == watch.WATCHER
    assert "pinned " + PINNED[:12] in request["evidence"]["text"]
    assert "+theorem erdos_68" in request["evidence"]["text"]

    state = watch.drift_state(target, qa.subject_hash(target, "root"))
    assert state.frozen and state.edit is not None and state.resolved is None
    row = index_row(root, "erdos-68")
    assert row["claimable"] is False and "upstream-drift" in row["not_claimable"]
    assert fidelity.target_grade(target) == grade_before == "mechanical-only"
    assert row["fidelity"] == "mechanical-only"

    # The gate accepts the pair as a curator's pull request (R11; the watcher is listed).
    listed = modes.Curators((("watcher", "opn-watcher-bot"),))
    changes = [Change("A", drift_rel), Change("A", request_rel)]
    curated = modes.classify(changes, author="opn-watcher-bot", curators=listed)
    assert curated.mode == "curator", curated.problems
    assert modes.check(root, curated) == []
    # A person's own request does not ride along (F12-Q12's shape).
    personal = dict(request)
    personal["defect_class"] = "junk-value"
    other = "targets/erdos-68/nodes/and-reassoc/revisions/20260912T050000Z-alice.yaml"
    (root / other).write_text(yaml.safe_dump(personal), encoding="utf-8")
    mixed = modes.classify(
        [Change("A", drift_rel), Change("A", other)], author="opn-watcher-bot", curators=listed
    )
    assert [d.code for d in modes.check(root, mixed)] == ["defect-class"]


def test_a_second_run_does_not_flag_the_same_head_twice(tmp_path: Path) -> None:
    root = imported_target(tmp_path)
    host = FakeUpstream()
    first = watch.watch(root, host, date=WHEN)
    second = watch.watch(root, host, date="2026-09-13T04:17:00Z")
    assert len(first.targets[0].written) == 2 and second.targets[0].written == []
    assert any("already flagged" in n for n in second.targets[0].notes)
    # A further upstream move is a new flag.
    host.heads[REPO] = "e" * 40
    host.files[(REPO, "e" * 40, PATH)] = b"theorem erdos_68 : True := by\n  sorry\n"
    third = watch.watch(root, host, date="2026-09-14T04:17:00Z")
    assert len(third.targets[0].written) == 2


def test_an_unchanged_path_and_an_unpinned_target_write_nothing(tmp_path: Path) -> None:
    """R11: no difference, no record; a target the network authored is not watched."""
    root = imported_target(tmp_path)
    take_in(root, target_id="euclid-primes")  # no upstream pin
    host = FakeUpstream(
        files={(REPO, PINNED, PATH): UPSTREAM_TEXT, (REPO, HEAD, PATH): UPSTREAM_TEXT}
    )
    report = watch.watch(root, host, date=WHEN)
    by_id = {t.target_id: t for t in report.targets}
    assert by_id["erdos-68"].drift == "unchanged" and by_id["erdos-68"].written == []
    assert by_id["euclid-primes"].drift == "not watched"
    assert by_id["propositional"].drift == "not watched"  # pre-F11: no record at all
    assert not (root / "targets/erdos-68/drift").exists()
    assert index_row(root, "erdos-68")["not_claimable"] == [
        "status-listed",
        "grade-below-screened-and-signed",
        "no-posting",
    ]


def test_one_head_fetch_per_repository(tmp_path: Path) -> None:
    """§6: one upstream fetch of the head per distinct source repository, never per target."""
    root = imported_target(tmp_path)
    imported_target(tmp_path, "erdos-69")
    host = FakeUpstream()
    watch.watch(root, host, date=WHEN)
    assert host.calls.count(f"head:{REPO}") == 1


def test_a_revision_lifts_the_flag_and_a_curator_can_clear_it(tmp_path: Path) -> None:
    """Q16: the flag is scoped to the root's hash — a D-8 revision changes it and the freeze
    lifts; a curator who judges the edit irrelevant appends a cleared record."""
    root = imported_target(tmp_path)
    target = root / "targets" / "erdos-68"
    watch.watch(root, FakeUpstream(), date=WHEN)
    current = qa.subject_hash(target, "root")
    assert watch.drift_state(target, current).frozen
    assert not watch.drift_state(target, "f" * 64).frozen, "a revised root is not flagged"

    flag = watch.drift_state(target, current).edit
    assert flag is not None
    with pytest.raises(ValueError, match="not a flagged drift record"):
        watch.clear_drift(target, "ghost.yaml", author="mike", date=WHEN, note="n")
    watch.clear_drift(
        target,
        flag.name,
        author="mike",
        date="2026-09-13T00:00:00Z",
        note="the upstream edit is a docstring change",
    )
    assert not watch.drift_state(target, current).frozen
    assert index_row(root, "erdos-68")["not_claimable"] == [
        "status-listed",
        "grade-below-screened-and-signed",
        "no-posting",
    ]


# --- AC9: resolved elsewhere is a flag for dormancy, and the status is untouched ------------------


def test_resolved_elsewhere(tmp_path: Path) -> None:
    """AC9, R12: the source flips the problem to solved — the target is flagged for D-33
    dormancy with the citation attached; its status stays what the curator declared."""
    root = imported_target(tmp_path)
    target = root / "targets" / "erdos-68"
    host = FakeUpstream(
        files={(REPO, PINNED, PATH): UPSTREAM_TEXT, (REPO, HEAD, PATH): UPSTREAM_TEXT},
        pages={ERDOS_URL: erdos_page("SOLVED", f"Proved by X {INJECTION}")},
    )
    report = watch.watch(root, host, date=WHEN)
    item = report.targets[0]
    assert item.statuses == [(ERDOS_URL, "SOLVED")] and len(item.written) == 1
    record = schemas.load_yaml(root / item.written[0], watch.DRIFT_SCHEMA)
    assert record["kind"] == "resolved-elsewhere" and record["upstream"] is None
    assert record["citation"]["url"] == ERDOS_URL and record["citation"]["status"] == "SOLVED"
    # The badge line is kept as data with its markup stripped; the site escapes it (R14).
    assert "alert('drift')" in record["citation"]["text"]
    assert "<script>" not in record["citation"]["text"]
    state = watch.drift_state(target, qa.subject_hash(target, "root"))
    assert state.resolved is not None and not state.frozen, "a notice freezes nothing (R12)"
    row = index_row(root, "erdos-68")
    assert row["status"] == "listed", "the status is never changed by the watcher (R12)"
    assert "upstream-drift" not in row["not_claimable"]
    # The same status on the next run is not a second flag.
    again = watch.watch(root, host, date="2026-09-13T04:17:00Z")
    assert again.targets[0].written == []


def test_parse_status_reads_the_badge_or_nothing() -> None:
    assert watch.parse_status(erdos_page("OPEN", "Erdős asked")) == ("OPEN", "Erdős asked")
    assert watch.parse_status(erdos_page("DISPROVED (LEAN)")) == (
        "DISPROVED (LEAN)",
        "Erdős [Er68b]",
    )
    assert watch.parse_status("<html>no badge</html>") is None


# --- AC20: unreachable is a warning and a non-zero exit, never a false all-clear -----------------


def test_upstream_unreachable_is_a_warning_not_all_clear(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """AC20: the host raises, or answers 401 — the run exits non-zero with a logged warning,
    writes no drift flag and opens no revision request."""
    root = imported_target(tmp_path)
    for failure in ("git ls-remote failed: could not resolve host", "fetching answered 401"):
        with caplog.at_level("WARNING", logger="opn_gate.watch"):
            report = watch.watch(root, FakeUpstream(fail=failure), date=WHEN)
        assert report.exit_code == 1
        assert report.targets[0].drift == "unreachable" and report.targets[0].written == []
        assert failure in report.render() and "not an all-clear" in report.render()
        assert any(failure in r.getMessage() for r in caplog.records)
    assert not (root / "targets/erdos-68/drift").exists()
    assert not (root / "targets/erdos-68/nodes/and-reassoc/revisions").exists()
    # A path missing at the *pinned* commit is a defect of the pin, reported and left alone.
    gone = FakeUpstream(files={(REPO, HEAD, PATH): EDITED_TEXT})
    report = watch.watch(root, gone, date=WHEN)
    assert report.exit_code == 1 and "pinned commit" in report.targets[0].problems[0]


def test_dry_run_reports_and_writes_nothing(tmp_path: Path) -> None:
    """AC13's shape: the dry run says what it would do, writes nothing, exits 0."""
    root = imported_target(tmp_path)
    host = FakeUpstream(pages={ERDOS_URL: erdos_page("SOLVED")})
    report = watch.watch(root, host, date=WHEN, dry_run=True)
    assert report.exit_code == 0
    notes = report.targets[0].notes
    assert any("would flag upstream-edit" in n for n in notes)
    assert any("would flag resolved-elsewhere" in n for n in notes)
    assert report.targets[0].written == []
    assert not (root / "targets/erdos-68/drift").exists()
    text = report.render()
    assert "dry run" in text and "drifted" in text and "SOLVED" in text


def test_the_tool_runs_a_dry_run_and_commits_on_a_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The command line: a dry run exits 0 and writes the report; ``--branch`` commits what a
    live run wrote; a missing graph is a usage error."""
    import importlib.util  # noqa: PLC0415

    # gate/tools is a directory of scripts, not a package: load the tool by its file.
    tool = Path(__file__).resolve().parents[1] / "tools" / "watch_upstream.py"
    spec = importlib.util.spec_from_file_location("watch_upstream", tool)
    assert spec is not None and spec.loader is not None
    watch_upstream: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(watch_upstream)

    root = imported_target(tmp_path)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "seed"], check=True)
    monkeypatch.setattr(watch, "GitUpstreamHost", FakeUpstream)

    out = tmp_path / "report.txt"
    assert (
        watch_upstream.main(["--graph", str(root), "--dry-run", "--out", str(out), "--date", WHEN])
        == 0
    )
    assert "would flag upstream-edit" in out.read_text()
    assert (
        watch_upstream.main(["--graph", str(root), "--date", WHEN, "--branch", "watcher/test"]) == 0
    )
    log = subprocess.run(
        ["git", "-C", str(root), "log", "--oneline", "-1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "watcher: " in log and "2 record(s)" in log
    branch = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert branch == "watcher/test"
    assert watch_upstream.main(["--graph", str(tmp_path / "nowhere")]) == 2
    assert watch_upstream.main(["--graph", str(root), "--date", "yesterday"]) == 2
