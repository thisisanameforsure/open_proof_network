"""F11-T6 / R11, AC14: the invited-run readiness rehearsal drives both paths end to end.

``gate/tools/rehearsal.py`` is run here the way the walkthrough test runs AGENTS.md: a git
checkout of the fixture graph, the api on a real loopback port over the fake host, and precheck
runs that finish by themselves. Every step but the two no fixture can close — the root closing
(nothing merges on green, F07-Q16) and the deployed site — comes back ``ok``, the record is
written with a time per step, and the exit code says *pending* rather than ready, which is what
the live run says until the merges land.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import PrecheckKey, make_harness, make_precheck_key
from harness import TARGET
from test_walkthrough import AutoRunGitHost, build_graph_repo, serve_in_thread, tree_files

ROOT = Path(__file__).resolve().parents[2]
STATEMENT = "theorem OpnProp.and_swap_roundtrip : ∀ p q : Prop, p ∧ q → p ∧ q := by\n  sorry\n"
WITNESS = "theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, trivial, trivial⟩\n"


def _load() -> Any:
    path = ROOT / "gate" / "tools" / "rehearsal.py"
    spec = importlib.util.spec_from_file_location("rehearsal", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rehearsal = _load()


@pytest.fixture
def served(tmp_path: Path) -> Iterator[tuple[str, Path, AutoRunGitHost]]:
    (tmp_path / "key").mkdir()
    key: PrecheckKey = make_precheck_key(tmp_path / "key")
    graph = build_graph_repo(tmp_path, key)
    host = AutoRunGitHost(tree_files(graph), key)
    harness = make_harness(githost=host)
    base, loop = serve_in_thread(harness.app)
    yield base, graph, host
    loop.call_soon_threadsafe(loop.stop)


def test_both_paths_end_to_end_and_the_rest_pending(
    served: tuple[str, Path, AutoRunGitHost], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base, graph, host = served
    node = rehearsal.choose_node(rehearsal.frontier(base), None, None)[1]
    proof = tmp_path / "Proof.lean"
    proof.write_text(
        (graph / "targets" / TARGET / "nodes" / node / "Proof.lean").read_text(encoding="utf-8")
    )
    statement, witness = tmp_path / "S.lean", tmp_path / "W.lean"
    statement.write_text(STATEMENT, encoding="utf-8")
    witness.write_text(WITNESS, encoding="utf-8")
    out = tmp_path / "readiness.txt"
    code = rehearsal.main(
        [
            base, "--proof", str(proof), "--variant-statement", str(statement),
            "--variant-witness", str(witness), "--out", str(out), "--timeout", "30",
        ]
    )  # fmt: skip
    printed = capsys.readouterr().out
    assert code == rehearsal.EXIT_PENDING, printed
    record = out.read_text(encoding="utf-8")
    assert "verdict: PENDING" in record
    lines = {
        line.split()[2]: line.split()[1]
        for line in record.splitlines()
        if line[:8].strip().replace(".", "").isdigit()
    }
    for step in ("claim", "precheck+submit", "postmortem", "variant"):
        for path in ("http", "mcp"):
            assert lines[f"{step}:{path}"] == "ok", (step, path, record)
    assert lines["identity:http"] == lines["identity:mcp"] == "ok"
    assert lines["frontier"] == "ok"
    assert lines["root-closes"] == "pending" and lines["site"] == "skipped"
    # Two identities, two pull requests of each kind: the acts reached the host.
    titles = [p.title for p in host.pulls]
    assert sum(t.startswith("proof: ") for t in titles) == 2
    assert sum(t.startswith("postmortem: ") for t in titles) == 2
    assert sum(t.startswith("proposal: ") for t in titles) == 2


def test_without_inputs_the_optional_steps_are_skipped(
    served: tuple[str, Path, AutoRunGitHost], tmp_path: Path
) -> None:
    base, _graph, _host = served
    out = tmp_path / "readiness.txt"
    code = rehearsal.main([base, "--out", str(out), "--timeout", "30"])
    record = out.read_text(encoding="utf-8")
    assert code == rehearsal.EXIT_PENDING
    assert "skipped  precheck+submit:http  — no --proof given" in record
    assert "skipped  variant:mcp  — no --variant-statement" in record
    assert "ok       claim:http" in record and "ok       postmortem:mcp" in record


def test_a_node_off_the_frontier_fails_the_first_step(
    served: tuple[str, Path, AutoRunGitHost], tmp_path: Path
) -> None:
    base, _graph, _host = served
    out = tmp_path / "readiness.txt"
    code = rehearsal.main([base, "--node", "no-such-node", "--out", str(out)])
    assert code == rehearsal.EXIT_FAIL
    assert "failed   frontier  — no-such-node is not on the frontier" in out.read_text()


def test_only_https_or_the_local_runner(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        rehearsal.main(["http://example.org", "--out", str(tmp_path / "r")])
