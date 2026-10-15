"""F00-T11 and F02-T15 (the owner, 2026-10-14): a proof may carry helper lemmas, and the gate's
heartbeat cap is 1000000.

The 2026-10-14b testers spent most of an hour fitting a ported development under Lean's default
200000 heartbeats in one theorem: van Doorn-Tang's medium case costs 221k as separate lemmas
and 328k inlined, because every ``at *`` walks every earlier ``have``. The owner's ruling: raise
the cap to 1000k and allow helper lemmas.

The rule (F00-R19 as amended): ``Proof.lean`` is ``Statement.lean`` with the ``sorry`` replaced
and, optionally, a block of **private** declarations (``theorem``, ``lemma``, ``def``,
``abbrev``) placed directly before the statement's declaration (before its doc comment, when it
has one). With the block removed the file is held to the statement exactly as before. The block
may not hold anything that could change the cap, the environment or what the statement says:
no ``set_option``, ``axiom``, ``instance``, notation or macro, attribute, ``open``, ``variable``
or ``#`` command, and no public declaration. ``private`` keeps a helper's name out of every
importer, so two nodes' helpers never clash. What the helpers prove is the kernel's question
(step 4), what they rest on is the axiom probe's (step 5), and that the statement means what it
did is the meaning check's (step 4), as for use lines (F08-R16).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opn_gate import config, layout, paths, toolchain

FIXTURES = Path(__file__).parent / "fixtures"
GRAPH = FIXTURES / "graphs" / "propositional"


def tutorial() -> layout.Node:
    node = layout.load_node(
        layout.graph_nodes_dir(GRAPH, "propositional") / "tutorial-and-swap", "propositional"
    )
    assert isinstance(node, layout.Node)
    return node


#: A statement of the live shape: imports, an ``open``, a doc comment on the declaration.
DOC_STATEMENT = (
    "import Std\n"
    "\n"
    "open Nat\n"
    "\n"
    "/-- One and one. -/\n"
    "theorem Opn.one_one : 1 + 1 = 2 := by\n"
    "  sorry\n"
)


def doc_statement() -> layout.Statement:
    st = layout.parse_statement(DOC_STATEMENT)
    assert isinstance(st, layout.Statement)
    return st


def with_helpers(st: layout.Statement, helpers: str, body: str = " rfl\n") -> str:
    """``st``'s text with ``helpers`` inserted where the rule puts them and the body replaced."""
    marker = "/-- One and one. -/\n" if "/--" in st.prefix else "theorem "
    at = st.prefix.index(marker)
    return st.prefix[:at] + helpers + st.prefix[at:] + body + st.suffix


HELPER = "private theorem two : 1 + 1 = 2 := rfl\n\n"


# --- what the block may hold ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "helpers",
    [
        HELPER,
        "private lemma two : 1 + 1 = 2 := rfl\n",
        "/-- A helper with its own doc comment. -/\nprivate lemma two : 1 + 1 = 2 := by\n  rfl\n\n",
        "-- a line comment\nprivate def k : Nat := 2\n\nprivate abbrev K : Type := Nat\n",
        "noncomputable private def k : Nat := 2\n",
        "private noncomputable def k : Nat := 2\n",
        "/- a block comment\n   over two lines -/\nprivate theorem two : 1 + 1 = 2 := rfl\n",
        "private theorem two : 1 + 1 = 2 := by\n  have h : 1 = 1 := rfl\n  rfl\n\n"
        "private theorem three : 1 + 2 = 3 := rfl\n",
    ],
)
def test_private_helpers_before_the_declaration_pass_step_2(helpers: str) -> None:
    st = doc_statement()
    assert paths.check_proof_is_statement(st, with_helpers(st, helpers, " two\n")) is None


def test_helpers_before_a_statement_with_no_doc_comment() -> None:
    node = tutorial()
    good = node.proof_path.read_text(encoding="utf-8")
    helped = good.replace(
        "theorem OpnProp.and_swap",
        "private theorem swap {p q : Prop} (h : p ∧ q) : q ∧ p := ⟨h.2, h.1⟩\n\n"
        "theorem OpnProp.and_swap",
    )
    assert helped != good
    assert paths.check_proof_is_statement(node.statement, helped) is None


def test_no_helpers_is_the_old_rule() -> None:
    st = doc_statement()
    assert paths.check_proof_is_statement(st, with_helpers(st, "")) is None


# --- what it may not ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("helpers", "token"),
    [
        ("theorem two : 1 + 1 = 2 := rfl\n", "theorem"),
        ("lemma two : 1 + 1 = 2 := rfl\n", "lemma"),
        ("def k : Nat := 2\n", "def"),
        ("  theorem two : 1 + 1 = 2 := rfl\n", "theorem"),
        ("set_option maxHeartbeats 0 in\nprivate theorem two : 1 + 1 = 2 := rfl\n", "set_option"),
        (
            "private theorem two : 1 + 1 = 2 := by\n  set_option maxHeartbeats 0 in rfl\n",
            "set_option",
        ),
        ("axiom cheat : False\n", "axiom"),
        ("private axiom cheat : False\n", "axiom"),
        ("instance : Inhabited Nat := ⟨3⟩\n", "instance"),
        ("private instance : Inhabited Nat := ⟨3⟩\n", "instance"),
        ('notation "two" => 2\n', "notation"),
        ('macro "two" : term => `(2)\n', "macro"),
        ('syntax "two" : term\n', "syntax"),
        ("@[simp] private theorem two : 1 + 1 = 2 := rfl\n", "@["),
        ("attribute [simp] Nat.add_comm\n", "attribute"),
        ("open Lean\n", "open"),
        ("variable (n : Nat)\n", "variable"),
        ("namespace Foo\nprivate theorem two : 1 + 1 = 2 := rfl\nend Foo\n", "namespace"),
        ("#eval 1\n", "#eval"),
        ("private unsafe def k : Nat := 2\n", "unsafe"),
        ("private opaque k : Nat\n", "opaque"),
        ("private structure S where\n  x : Nat\n", "structure"),
        ("initialize pure ()\n", "initialize"),
        ("run_cmd pure ()\n", "run_cmd"),
        # A partial's assembly may hold sorry for its holes, which the extractor reads off the
        # main theorem only: a helper resting on sorry would be an unextracted hole.
        ("private theorem two : 1 + 1 = 2 := sorry\n", "sorry"),
        ("private theorem two : 1 + 1 = 2 := by\n  admit\n", "admit"),
    ],
)
def test_the_block_refuses_what_could_change_the_cap_or_the_environment(
    helpers: str, token: str
) -> None:
    st = doc_statement()
    d = paths.check_proof_is_statement(st, with_helpers(st, helpers, " rfl\n"))
    assert d is not None and d.code == "helper-forbidden", d
    assert d.details["token"] == token
    # The line is the file's own line number, counted from 1, of the offending text.
    text = with_helpers(st, helpers, " rfl\n")
    assert token in text.splitlines()[int(d.details["line"]) - 1]


def test_a_forbidden_word_in_a_comment_is_not_a_command() -> None:
    st = doc_statement()
    helpers = "-- no set_option here, and no axiom\n/- instance notation -/\n" + HELPER
    assert paths.check_proof_is_statement(st, with_helpers(st, helpers, " two\n")) is None


def test_a_name_that_contains_a_forbidden_word_is_not_one() -> None:
    st = doc_statement()
    helpers = "private theorem two : Nat.succ 1 = 2 := Nat.Simple.rfl_open\n"
    # ``rfl_open`` and ``Nat.Simple`` contain words of the list only as parts of names.
    assert paths.check_proof_is_statement(st, with_helpers(st, helpers, " two\n")) is None


def test_helpers_between_the_doc_comment_and_the_theorem_diverge() -> None:
    st = doc_statement()
    text = DOC_STATEMENT.replace("theorem Opn.one_one", HELPER + "theorem Opn.one_one").replace(
        "sorry", "two"
    )
    d = paths.check_proof_is_statement(st, text)
    assert d is not None and d.code == "proof-not-statement"


def test_helpers_do_not_excuse_a_changed_header_or_signature() -> None:
    st = doc_statement()
    text = with_helpers(st, HELPER, " two\n")
    d = paths.check_proof_is_statement(st, text.replace("open Nat", "open Int"))
    assert d is not None and d.code == "proof-not-statement" and d.details["line"] == 3
    weakened = text.replace("Opn.one_one : 1 + 1 = 2", "Opn.one_one : 2 = 2")
    assert weakened != text
    d = paths.check_proof_is_statement(st, weakened)
    assert d is not None and d.code == "proof-not-statement"


def test_the_main_declaration_is_still_the_statement_s() -> None:
    """``parse_declaration`` (step 2's kind, ``graph.artifact_of``, the context bundle) names the
    statement's theorem in a file with private helpers, so a merged proof still reads as one."""
    st = doc_statement()
    assert layout.parse_declaration(with_helpers(st, HELPER, " two\n")) == "Opn.one_one"


# --- the cap (F02-T15) ---------------------------------------------------------------------------


def test_the_cap_is_a_million_heartbeats() -> None:
    assert config.MAX_HEARTBEATS == 1_000_000


def test_every_lean_call_the_gate_makes_carries_the_cap(tmp_path: Path) -> None:
    from test_toolchain import PIN, scripted  # noqa: PLC0415 — the scripted toolchain

    lt = scripted(tmp_path)
    tc = lt.resolve(PIN)
    src = tmp_path / "src" / "Nodes" / "n" / "Proof.lean"
    src.parent.mkdir(parents=True)
    src.write_text("theorem t : True := trivial\n")
    lt.elaborate(tc, src, "Nodes.«n».Proof", tmp_path / "build", root=tmp_path / "src")
    cmd = lt.calls[-1][0]
    assert f"-DmaxHeartbeats={config.MAX_HEARTBEATS}" in cmd
    assert cmd.index(f"-DmaxHeartbeats={config.MAX_HEARTBEATS}") < cmd.index("Nodes/n/Proof.lean")
    assert isinstance(lt, toolchain.LocalToolchain)
