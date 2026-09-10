"""F08-T4: the append gate's one build, and every way it fails (R6, R7; Q15; C7, C9).

``test_modes.py`` proves the classifier hands the right records to ``exhibits.run`` and that a
failing exhibit is named (AC11); ``test_exhibits_lean.py`` proves the real toolchain agrees. What
is pinned here is the rest of the runner: a node that cannot be staged, a Context that does not
compile, the wall-clock cap, a missing toolchain, a malformed record — each a named diagnostic,
none a crash and none silent.
"""

from __future__ import annotations

from pathlib import Path

import samples
import yaml
from fakes import FakeToolchain
from harness import TARGET, TUTORIAL, copy_graph
from scripted import ScriptedToolchain

from opn_gate import config, exhibits, layout, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Claim, Located
from opn_gate.steps.base import RunContext

CONTEXT_MODULE = f"Nodes.«{TUTORIAL}».Context"
EXHIBIT0 = f"Nodes.«{TUTORIAL}».Exhibit0"


def context(root: Path, toolchain: FakeToolchain) -> RunContext:
    spec_path = layout.gate_spec_path(root, TARGET)
    return RunContext(
        graph_root=root,
        claim=Claim(TARGET, TUTORIAL),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=root.parent / "work",
        toolchain=toolchain,
        settings=config.load({}),
    )


def revision(root: Path, name: str = "20260910T000000-alice", **overrides: object) -> Located:
    rel = f"targets/{TARGET}/nodes/{TUTORIAL}/revisions/{name}.yaml"
    doc = samples.revision_request(**overrides)
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
    return Located("revision-request", rel, TARGET, TUTORIAL)


def defs_claim(root: Path) -> Located:
    rel = f"targets/{TARGET}/defs/defects/20260910T000000-alice.yaml"
    doc = samples.defect_claim(stmt_ref="defs/Helper.lean", line=1)
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
    return Located("defect-claim", rel, TARGET, None)


def codes(found: list[Diagnostic]) -> list[str]:
    return [d.code for d in found]


def test_no_records_touches_no_toolchain(tmp_path: Path) -> None:
    fake = FakeToolchain()
    assert exhibits.run(context(copy_graph(tmp_path), fake), []) == []
    assert fake.calls == []


def test_a_missing_toolchain_is_the_one_diagnostic(tmp_path: Path) -> None:
    """Step 1's failure stands in for every exhibit: nothing is elaborated without a toolchain."""
    root = copy_graph(tmp_path)
    fake = FakeToolchain(missing=True)
    found = exhibits.run(context(root, fake), [revision(root)])
    assert codes(found) == ["toolchain-missing"]
    assert all(not c.startswith("elaborate:") for c in fake.calls)


def test_a_record_without_an_exhibit_builds_nothing(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    fake = FakeToolchain()
    located = revision(root, evidence={"text": "prose only"})
    assert exhibits.run(context(root, fake), [located]) == []
    assert all(not c.startswith("elaborate:") for c in fake.calls)


def test_a_malformed_record_is_named_not_elaborated(tmp_path: Path) -> None:
    """The record is read at the boundary (conventions §4); YAML that does not parse, or a file
    that is not UTF-8, is the diagnostic, and no Lean of it runs."""
    root = copy_graph(tmp_path)
    located = revision(root)
    (root / located.path).write_text("evidence: [unterminated\n", encoding="utf-8")
    fake = FakeToolchain()
    found = exhibits.run(context(root, fake), [located])
    assert codes(found) == ["append-invalid"]
    assert all(not c.startswith("elaborate:") for c in fake.calls)

    (root / located.path).write_bytes(b"\xff\xfe not utf-8")
    found = exhibits.run(context(root, FakeToolchain()), [located])
    assert codes(found) == ["append-invalid"]
    assert "UTF-8" in found[0].message


def test_an_exhibit_about_a_node_with_no_statement_cannot_be_staged(tmp_path: Path) -> None:
    """The exhibit is elaborated against the node it is about (Q15); a node missing its files is
    refused before the exhibit is written, naming the file."""
    root = copy_graph(tmp_path)
    located = revision(root)
    (layout.graph_nodes_dir(root, TARGET) / TUTORIAL / "Statement.lean").unlink()
    fake = FakeToolchain()
    found = exhibits.run(context(root, fake), [located])
    assert codes(found) == ["exhibit-node"]
    assert found[0].details == {"node": TUTORIAL, "missing": "Statement.lean"}
    assert all(not c.startswith("elaborate:") for c in fake.calls)


def test_a_context_that_does_not_elaborate_fails_the_exhibit_before_it_runs(
    tmp_path: Path,
) -> None:
    root = copy_graph(tmp_path)
    located = revision(root)
    fake = ScriptedToolchain(failing_modules={CONTEXT_MODULE})
    found = exhibits.run(context(root, fake), [located])
    assert codes(found) == ["exhibit-node"]
    assert found[0].details["node"] == TUTORIAL and "messages" in found[0].details
    assert f"elaborate:{EXHIBIT0}" not in fake.calls


def test_the_wall_clock_cap_is_named(tmp_path: Path) -> None:
    """Both the node's Context and the exhibit itself run under the cap (C9: contributor Lean)."""
    root = copy_graph(tmp_path)
    located = revision(root)
    found = exhibits.run(context(root, ScriptedToolchain(timeout_modules={EXHIBIT0})), [located])
    assert codes(found) == ["exhibit-timeout"]
    assert found[0].details == {"path": located.path}

    other = copy_graph(tmp_path / "b")  # a fresh work directory: nothing staged yet
    found = exhibits.run(
        context(other, ScriptedToolchain(timeout_modules={CONTEXT_MODULE})), [revision(other)]
    )
    assert codes(found) == ["exhibit-timeout"]
    assert "Context" in found[0].message


def test_every_failing_exhibit_is_named_not_only_the_first(tmp_path: Path) -> None:
    """C7: two bad exhibits are two diagnostics; the node is staged once for both (Q15)."""
    root = copy_graph(tmp_path)
    first = revision(root, "20260910T000000-alice")
    second = revision(root, "20260910T000001-bob", contributor="bob")
    fake = ScriptedToolchain(failing_modules={EXHIBIT0, f"Nodes.«{TUTORIAL}».Exhibit1"})
    found = exhibits.run(context(root, fake), [first, second])
    assert codes(found) == ["exhibit-elaboration", "exhibit-elaboration"]
    assert [d.details["path"] for d in found] == [first.path, second.path]
    assert fake.calls.count(f"elaborate:{CONTEXT_MODULE}") == 1


def test_a_defs_exhibit_is_a_bare_module_and_its_failure_says_so(tmp_path: Path) -> None:
    """Q15: an exhibit about a defs/ file stages no node and elaborates as ``Exhibit<n>``."""
    root = copy_graph(tmp_path)
    (root / "targets" / TARGET / "defs" / "Helper.lean").write_text("def helper : Nat := 0\n")
    located = defs_claim(root)
    fake = ScriptedToolchain(failing_modules={"Exhibit0"})
    found = exhibits.run(context(root, fake), [located])
    assert codes(found) == ["exhibit-elaboration"]
    assert found[0].details["module"] == "Exhibit0"
    assert fake.calls == ["resolve:leanprover/lean4:v4.33.1:install=False", "elaborate:Exhibit0"]
    assert (root.parent / "work" / "src" / "Exhibit0.lean").read_text() == samples.defect_claim()[
        "exhibit"
    ]
