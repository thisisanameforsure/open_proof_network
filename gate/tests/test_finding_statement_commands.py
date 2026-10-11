# ruff: noqa: RUF001 — the cases are Lean source, with its double-struck letters
"""F08-T37 (D-3 v3.28): a proposed statement holds its imports, ``open``, ``namespace`` and
``end`` lines, doc comments and its declarations, and nothing else.

The judges import a node's ``Statement`` and ``Context`` as modules of record (D-4 v3.27,
F02-T10 to T14), so a command there that runs code when the module is loaded (``initialize``),
or that changes what later text means (``instance``, ``macro_rules``, ``notation``,
``attribute``, ``set_option``), would act inside the checks that judge the node. Each case below
was admitted by step 2 before this rule; each is now refused at step 2 as
``statement-command-forbidden``, naming the file, the line and the command.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from fakes import FakeToolchain, witness_result
from harness import TARGET, copy_graph, make_context, node_dir
from test_admit import context_for, failure
from test_wave import wave  # noqa: F401 — the wave driver's fixture, reused

from opn_gate import admit, curator, layout, postmerge, scaffold, schemas
from opn_gate.steps.paths_step import PathsStep

CODE = "statement-command-forbidden"
THEOREM = "theorem OpnProp.and_weaken"

#: (case, file, the text spliced in before the theorem (or at the end of a Context), the line
#: the refusal must name, the command it must name).
CASES: list[tuple[str, str, str, str]] = [
    ("initialize", "Statement.lean", 'initialize IO.println "loaded"\n\n', "initialize"),
    ("instance", "Statement.lean", "instance : Inhabited Prop := ⟨True⟩\n\n", "instance"),
    (
        "macro_rules",
        "Statement.lean",
        "macro_rules | `(True) => `(False)\n\n",
        "macro_rules",
    ),
    ("set_option", "Statement.lean", "set_option autoImplicit true\n\n", "set_option"),
    ("eval-in-context", "Context.lean", '\n#eval IO.println "loaded"\n', "#eval"),
]


def splice(ctx_root: Path, case_dir: Path, name: str, text: str) -> int:
    """Put ``text`` into the proposal's file and keep META's hash honest; the 1-based line the
    first non-blank line of ``text`` lands on."""
    path = case_dir / name
    before = path.read_text(encoding="utf-8")
    if name == "Statement.lean":
        at = before.index(THEOREM)
        after = before[:at] + text + before[at:]
        line = before[:at].count("\n") + 1
    else:
        after = before + text
        line = before.count("\n") + 1 + (len(text) - len(text.lstrip("\n")))
    path.write_text(after, encoding="utf-8")
    meta_path = case_dir / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["statement-hash"] = schemas.content_hash(
        (case_dir / "Statement.lean").read_text(encoding="utf-8").encode("utf-8")
    )
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    return line


@pytest.mark.parametrize(("case", "name", "text", "command"), CASES, ids=[c[0] for c in CASES])
def test_admission_refuses_a_command_beyond_d3s_list(
    tmp_path: Path, case: str, name: str, text: str, command: str
) -> None:
    """Each command was admitted at step 2 before v3.28; now the layout check refuses it, names
    it and its line, and nothing after it runs (the statement is never elaborated)."""
    good = witness_result(expected="∃ p q, p ∧ q", witness="∃ p q, p ∧ q")
    toolchain = FakeToolchain(witness=good)
    ctx = context_for(tmp_path, "good", toolchain=toolchain)
    case_dir = ctx.graph_root / "targets" / ctx.claim.target_id / "nodes" / "good"
    line = splice(ctx.graph_root, case_dir, name, text)
    result = admit.run(ctx)
    assert failure(result) == ("layout", CODE), result.as_dict()
    assert result.diagnostic is not None
    assert result.diagnostic.details["file"] == name
    assert result.diagnostic.details["line"] == line
    assert result.diagnostic.details["command"] == command
    after = [c for c in result.checks if c.name not in ("toolchain", "layout")]
    assert {c.result for c in after} == {"skipped"}


def test_step_two_refuses_a_node_whose_context_carries_a_command(tmp_path: Path) -> None:
    """The submission pipeline's step 2 holds the node it loads to the same rule: a Context on
    the tree with an ``#eval`` is refused before any build imports it."""
    ctx = make_context(tmp_path)
    nd = node_dir(ctx)
    shutil.copy(nd / "Statement.lean", nd / "Proof.lean")
    proof = (nd / "Proof.lean").read_text(encoding="utf-8")
    (nd / "Proof.lean").write_text(
        proof.replace("  sorry", "  intro p q h\n  exact ⟨h.2, h.1⟩"), encoding="utf-8"
    )
    context = nd / "Context.lean"
    context.write_text(
        context.read_text(encoding="utf-8") + '\n#eval IO.println "loaded"\n', encoding="utf-8"
    )
    result = PathsStep().run(ctx)
    assert not result.ok
    assert result.diagnostic is not None
    assert result.diagnostic.code == CODE
    assert result.diagnostic.details["file"] == "Context.lean"
    assert result.diagnostic.details["command"] == "#eval"


# --- the reading: what counts as a command, and what does not ------------------------------------


def commands(text: str) -> list[tuple[int, str]]:
    return [(o.line, o.command) for o in layout.forbidden_commands(text)]


ALLOWED: dict[str, str] = {
    "comments, nested and doc": (
        "/- a /- nested -/ block with #eval inside -/\n"
        "-- a line comment: instance : Foo := ⟨⟩\n"
        "/-! module doc: set_option x true -/\n"
        "import Mathlib\n\n"
        "open Nat Finset\nopen scoped BigOperators\nopen Real in\n"
        "namespace Opn\n\n"
        "/-- the doc comment of the theorem: initialize -/\n"
        "theorem t (n : ℕ)\n    (h : 0 < n) :\n    ∑ i ∈ range n, i ≤ n * n := by\n  sorry\n\n"
        "end Opn\n"
    ),
    "a let binding, a structure instance, a default argument and the card notation": (
        "theorem t : ∀ s : Finset ℕ, let m := #s; (x : ℕ := 3) → m ≤ m + x ∧ "
        "({ fst := 1, snd := 2 } : ℕ × ℕ).1 = 1 :=\n  sorry\n"
    ),
    "a Context of two signatures under one header": (
        "import Mathlib\n\n/-! Declared dependencies (D-4 step 8): `a`, `b`. -/\n\n"
        "open Nat\n\ntheorem Opn.a : True := by\n  sorry\n\ntheorem Opn.b : 1 = 1 := by\n  sorry\n"
    ),
    "a quoted name, a string and a character inside the type": (
        "theorem «odd -- name» : \"a -- b\".length = 6 ∧ '\"' = '\"' := sorry\n"
    ),
    "an end with no name, and lemma": "lemma t : True := sorry\nend\n",
}


@pytest.mark.parametrize("text", ALLOWED.values(), ids=list(ALLOWED))
def test_what_a_statement_may_hold_passes(text: str) -> None:
    assert commands(text) == []


REFUSED: dict[str, tuple[str, list[tuple[int, str]]]] = {
    "an attribute on the theorem": ("@[simp] theorem t : True := sorry\n", [(1, "@[simp]")]),
    "a modifier on the theorem": ("protected theorem t : True := sorry\n", [(1, "protected")]),
    "a section": ("section\ntheorem t : True := sorry\nend\n", [(1, "section")]),
    "a command after the sorry on the same line": (
        "theorem t : True := by sorry #eval 1\n",
        [(1, "#eval")],
    ),
    "a command hidden behind a quote Lean reads as a character": (
        "theorem a : '\"' = 'x' := sorry\n#eval 1 --\"\n",
        [(2, "#eval")],
    ),
    "a command after an open line's names": ("open Nat #eval 1\n", [(1, "#eval")]),
    "a command word in an open line": ("open Nat instance\n", [(1, "instance")]),
    "a second command on an import line": ("import Mathlib open Nat\n", [(1, "open")]),
    "a Context signature proved rather than sorry": (
        "theorem a : True := by trivial\ntheorem b : True := sorry\n",
        [(1, "theorem")],
    ),
    "a declaration that never reaches its body": ("theorem a : True\n", [(1, "theorem")]),
    "an attribute inside the type": ("theorem a : @[simp] True := sorry\n", [(1, "@[")]),
    "a term-level set_option": (
        "theorem a : set_option pp.all true in True := sorry\n",
        [(1, "set_option")],
    ),
    "every forbidden command, each named": (
        'import Mathlib\nnotation "ℵ" => 0\nattribute [simp] Nat.add_comm\n'
        "theorem t : True := sorry\nuniverse u\nvariable (n : ℕ)\n",
        [(2, "notation"), (3, "attribute"), (5, "universe"), (6, "variable")],
    ),
}


@pytest.mark.parametrize(("text", "expected"), REFUSED.values(), ids=list(REFUSED))
def test_anything_else_is_refused_and_named(text: str, expected: list[tuple[int, str]]) -> None:
    assert commands(text) == expected


def test_the_mask_keeps_every_offset() -> None:
    text = (
        ALLOWED["comments, nested and doc"]
        + ALLOWED["a quoted name, a string and a character inside the type"]
    )
    masked = layout.code_mask(text)
    assert len(masked) == len(text)
    assert [i for i, c in enumerate(masked) if c == "\n"] == [
        i for i, c in enumerate(text) if c == "\n"
    ]


# --- the gate's own writers never write a refused file -------------------------------------------


def test_the_hole_writer_and_the_context_writer_pass() -> None:
    """Postmerge's child statement (imports and ``open`` lines inherited from the parent) and the
    Context the scaffold and postmerge generate from those children's statements."""
    holes = [
        SimpleNamespace(name="h1", closed_type="∀ (n : ℕ), (2 : ℕ) ≤ n → ∃ p, Nat.Prime p ∧ p ∣ n"),
        SimpleNamespace(name="h2", closed_type="∀ (a : ℕ → ℤ), let b := a 0; b = b"),
    ]
    children = {
        f"t--h{i}": postmerge.child_statement(
            f"t--h{i}",
            hole,
            imports=["Mathlib", "Defs.IsPrime"],
            opens=["open Nat", "open scoped BigOperators", "open Real in"][: i + 1],
        )
        for i, hole in enumerate(holes, start=1)
    }
    for text in children.values():
        assert commands(text) == []
    context = scaffold.context_from(tuple(children), children)
    assert commands(context) == []
    assert commands(scaffold.context_from((), {})) == []
    assert commands(layout.with_own_context(children["t--h1"], "t--h1")) == []


def test_a_scaffolded_proposal_and_a_revision_pass(tmp_path: Path) -> None:
    """``scaffold.files`` (the service's and the curator's builder) and ``opn-gate revise``."""
    from test_finding_b_revise_v2 import (  # noqa: PLC0415 — the revision fixture's own inputs
        AUTHOR,
        DATE,
        INTERIOR,
        NEW_STATEMENT,
        v2_request_doc,
        write_doc,
    )

    root = copy_graph(tmp_path, publish=True)
    request = write_doc(root, INTERIOR, v2_request_doc(INTERIOR))
    revision = curator.revise(
        root, TARGET, INTERIOR, NEW_STATEMENT, request, author=AUTHOR, date=DATE
    )
    new_dir = layout.graph_nodes_dir(root, TARGET) / revision.new_id
    assert layout.check_commands(new_dir) is None
    for node in layout.graph_nodes_dir(root, TARGET).iterdir():
        assert layout.check_commands(node) is None, node.name


def test_the_wave_drafts_pass(
    wave: tuple[Path, dict[str, Any], dict[str, Any]],  # noqa: F811 — the imported fixture
) -> None:
    """F14-T11's driver: the registry's ``@[category ...]`` attribute, ``namespace`` and its
    copyright header are not carried into the draft, so every drafted statement passes."""
    out, _result, _doc = wave
    drafted = sorted(out.glob("*/Statement.lean"))
    assert drafted, "the fixture drafts some rows"
    for path in drafted:
        assert layout.command_problem("Statement.lean", path.read_text(encoding="utf-8")) is None
