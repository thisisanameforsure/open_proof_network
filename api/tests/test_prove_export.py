"""F17-T3 / AC1, AC2: ``opn-prove export`` writes, byte for byte, what the network's fast check
forwards for the same statement, and the client imports only the standard library.

Two builders of one document drift unless a test holds them together (the F10-Q7 precedent). The
reference is the service's own ``checks.inline_defs`` and ``checks.forwarded_text`` over the same
fixture graph served by the fake host; every node of every fixture graph is compared, which covers
a node with ``Defs`` (onramp), with its own Context imported (all three graphs) and with neither. A
mutant client that inlines the definitions in another order is caught.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness, make_harness

from opn_api import checks
from opn_gate import layout

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "gate" / "clients" / "prove" / "opn_prove.py"
GRAPHS = ROOT / "gate" / "tests" / "fixtures" / "graphs"


def load_client() -> Any:
    spec = importlib.util.spec_from_file_location("opn_prove", CLIENT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


prove = load_client()


def nodes() -> list[tuple[str, str, str]]:
    out = []
    for graph in sorted(p for p in GRAPHS.iterdir() if p.is_dir()):
        for statement in sorted(graph.glob("targets/*/nodes/*/Statement.lean")):
            out.append((graph.name, statement.parts[-4], statement.parts[-2]))
    return out


def served(graph: str) -> Harness:
    root = GRAPHS / graph
    harness = make_harness()
    harness.githost.files.update(
        {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    )
    harness.context.files.clear()
    return harness


def reference(harness: Harness, target: str, node: str, text: str) -> str:
    """What ``POST /check`` forwards for ``text`` checked against the node (F13-R5, T11, T12)."""
    statement = layout.parse_statement(text)
    assert isinstance(statement, layout.Statement)
    defs = checks.inline_defs(harness.context, target, statement, text, node)
    return checks.forwarded_text(text, defs)


@pytest.mark.parametrize(("graph", "target", "node"), nodes())
def test_parity(graph: str, target: str, node: str) -> None:
    text = (GRAPHS / graph / "targets" / target / "nodes" / node / "Statement.lean").read_text(
        encoding="utf-8"
    )
    ours = prove.export(prove.find_node(GRAPHS / graph, node, target))
    assert ours == reference(served(graph), target, node, text), f"{graph}/{node}"


def test_parity_covers_the_cases() -> None:
    """The comparison is worth something only if the fixtures have what it compares."""
    texts = [
        (GRAPHS / g / "targets" / t / "nodes" / n / "Statement.lean").read_text(encoding="utf-8")
        for g, t, n in nodes()
    ]
    assert any(prove.defs_modules(t) for t in texts), "no node imports Defs"
    assert any("import Nodes." in t for t in texts), "no node imports its own Context"
    assert any(not prove.defs_modules(t) and "import Nodes." not in t for t in texts)


def test_mutant_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """A client that inlines the definitions in reverse order no longer matches the service."""
    graph, target, node = next(
        (g, t, n)
        for g, t, n in nodes()
        if len(
            prove.inlined_modules(
                prove.find_node(GRAPHS / g, n, t),
                prove.parse_statement(
                    (GRAPHS / g / "targets" / t / "nodes" / n / "Statement.lean").read_text()
                ),
            )
        )
        > 1
    )
    real = prove.inlined_modules
    monkeypatch.setattr(prove, "inlined_modules", lambda *a: list(reversed(real(*a))))
    text = (GRAPHS / graph / "targets" / target / "nodes" / node / "Statement.lean").read_text()
    ours = prove.export(prove.find_node(GRAPHS / graph, node, target))
    assert ours != reference(served(graph), target, node, text)


def test_stdlib_only() -> None:
    """AC1 / R1: every module the client imports is in the standard library."""
    tree = ast.parse(CLIENT.read_text(encoding="utf-8"))
    modules = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            modules |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            modules.add(n.module.split(".")[0])
    assert modules - {"__future__"} <= set(sys.stdlib_module_names), modules


def test_no_syntax_newer_than_3_10() -> None:
    """R1, F17-Q3: the client parses as Python 3.10 (a contributor's prover environment rarely
    runs the network's 3.13)."""
    ast.parse(CLIENT.read_text(encoding="utf-8"), feature_version=(3, 10))


def test_project_pins_the_graph(tmp_path: Path) -> None:
    """R2: ``--project`` writes a Lake project on the graph's toolchain and Mathlib commit."""
    graph, target, node = next(n for n in nodes() if n[0] == "onramp")
    found = prove.find_node(GRAPHS / graph, node, target)
    spec = found.gate_spec()
    problem = prove.write_project(found, tmp_path / "project")
    assert problem.read_text().endswith(prove.export(found))
    lakefile = (tmp_path / "project" / "lakefile.toml").read_text()
    assert spec["mathlib_sha"] in lakefile
    toolchain = (tmp_path / "project" / "lean-toolchain").read_text().strip()
    assert toolchain == spec["lean_toolchain"]
