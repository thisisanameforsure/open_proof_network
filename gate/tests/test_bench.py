"""F14-T13: the bench seeds, serves and replays on a fixture graph (fast tier, no toolchain).

The bench is how a fresh agent is tested before a live run: the real service over the fake host,
the site beside it, and a replay that grades the agent's writes. These tests drive all three on
the propositional fixture: both URLs answer, a recorded explainer is merged and changes a page, and
``--assert`` fails on a push ``classify`` refuses.
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Push
from harness import TARGET, TUTORIAL, copy_graph

from opn_gate import products

TOOL = Path(__file__).resolve().parents[1] / "tools" / "bench.py"
EXPLAINER = (
    "---\nauthor: bench-agent\nmodel: claude-fable-5-1\ndate: 2026-09-14\n---\n"
    "Swap the two halves of the conjunction, then swap them back.\n"
)
GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin"}  # fmt: skip


def load_tool() -> Any:
    spec = importlib.util.spec_from_file_location("bench", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # the dataclass resolves its module's namespace
    spec.loader.exec_module(module)
    return module


def graph_repo(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path / "src", publish=True)
    # A live graph carries its products committed; the bench renders the site from them.
    products.generate(root, rendered_from="0" * 40, commit_time="2026-09-14T00:00:00Z").write(root)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "base"]):
        subprocess.run(["git", "-C", str(root), *args], check=True, env=GIT, capture_output=True)
    return root


def get(url: str) -> tuple[int, str]:
    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 — loopback only
        return response.status, response.read().decode("utf-8")


def record(served: Any, **files: str) -> None:
    served.host.pushes.append(
        Push("owner/graph", f"bench/{len(served.host.pushes)}", dict(files), "0" * 40, "a write")
    )
    served.dump()


@pytest.fixture
def bench(tmp_path: Path) -> tuple[Any, Path]:
    tool = load_tool()
    directory = tmp_path / "bench"
    doc = tool.seed(graph_repo(tmp_path), directory)
    assert doc["pages"] > 0 and (directory / "site-base" / "index.html").is_file()
    return tool, directory


def test_serve_answers_on_both_urls(bench: tuple[Any, Path]) -> None:
    tool, directory = bench
    served = tool.start(directory)
    try:
        status, body = get(f"{served.api_url}/frontier.json")
        assert status == 200 and json.loads(body)["entries"], body[:200]
        status, page = get(served.site_url)
        assert status == 200 and "<html" in page.lower()
        urls = json.loads((directory / "urls.json").read_text())
        assert urls == {
            "api": served.api_url,
            "mcp": f"{served.api_url}/mcp",
            "site": served.site_url,
        }
        assert json.loads((directory / "records" / "pushes.json").read_text()) == []
    finally:
        served.stop()


def test_replay_merges_an_explainer_and_the_page_changes(bench: tuple[Any, Path]) -> None:
    tool, directory = bench
    served = tool.start(directory)
    try:
        name = hashlib.sha256(
            EXPLAINER.encode("utf-8")
        ).hexdigest()  # an explainer is named for its hash
        record(served, **{f"targets/{TARGET}/nodes/{TUTORIAL}/explainer/{name}.md": EXPLAINER})
    finally:
        served.stop()
    report = tool.replay(directory)
    assert report["applied"] == [1] and report["refused"] == [], report["pushes"]
    assert report["products"] == {"ok": True} and report["site"]["ok"], report
    assert tool.failures(report) == []
    changed = [page for page in report["site_changes"] if TUTORIAL in page]
    assert changed, report["site_changes"]
    assert (directory / "check" / "report.json").is_file()


def test_assert_fails_on_a_refused_push(
    bench: tuple[Any, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    tool, directory = bench
    served = tool.start(directory)
    try:
        record(served, **{"README.md": "a write outside any target\n"})
    finally:
        served.stop()
    assert tool.main(["replay", "--bench", str(directory)]) == 0  # without --assert it reports
    assert tool.main(["replay", "--bench", str(directory), "--assert"]) == 1
    assert "FAIL push 1 refused" in capsys.readouterr().err


def test_a_push_in_a_mode_with_problems_is_refused_not_skipped(bench: tuple[Any, Path]) -> None:
    """An explainer not named for its hash classifies as ``explainer`` with a problem; the replay
    must count it as refused, so ``--assert`` sees it (found by the first run of this test)."""
    tool, directory = bench
    served = tool.start(directory)
    try:
        record(served, **{f"targets/{TARGET}/nodes/{TUTORIAL}/explainer/bench.md": EXPLAINER})
    finally:
        served.stop()
    report = tool.replay(directory)
    assert report["skipped"] == [] and report["applied"] == [], report
    [refused] = report["refused"]
    assert refused["mode"] == "explainer" and refused["problems"] == ["content-hash-name"], refused
    assert tool.failures(report) == ["push 1 refused: ['content-hash-name']"]


def test_push_records_keep_the_fake_hosts_shape() -> None:
    """The replay reads what ``Served.dump`` writes; the fields it reads must exist on ``Push``."""
    names = {f.name for f in dataclasses.fields(Push)}
    assert {"branch", "files", "message", "author"} <= names
