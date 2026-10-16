"""F28-T7 / AC10: ``opn-close``, the join, against the real toolchain, one assembly shape per case.

The case letters are the catalog's, section C of
``engineering/session-notes/2026-10-15-proof-propagation-cases.md``. Each case is an assembly
over Lean core. The bench does what the record does, with the gate's own programs:

1. the statement is the assembly's theorem with its proof replaced by ``sorry``;
2. ``opn-artifact-type`` (the elaborating form) extracts the holes, and each hole's
   ``closed_type`` is the child's statement, the way the post-merge job writes a hole node's
   statement — so the children are the extractor's, never the test's guess;
3. the children are declared above the assembly as axioms, standing for proofs merged elsewhere
   (in the graph they are imported proof modules), and ``opn-close`` joins the assembly with them
   at the level of terms, has the kernel check the theorem and writes its module.

A case passes when the join says ``ok``, every hole was joined to a child, the module was written,
and the theorem rests on nothing but the standard axioms and the children (never ``sorryAx``).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from opn_gate import close, layout
from opn_gate.toolchain import CloseRequest, LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean


@dataclass(frozen=True)
class Case:
    """``prelude`` sits above everything (definitions, ``open`` lines); ``header`` is the theorem
    up to and including ``:=``; ``body`` is the assembly's proof."""

    header: str
    body: str
    prelude: str = ""
    decl: str = "t"
    #: Kept from the source-composing era (F28-T2) as notes on what each case exercises; the join
    #: works on terms, so nothing here is asserted against printed text any more.
    expect: tuple[str, ...] = field(default_factory=tuple)
    composed_has: tuple[str, ...] = field(default_factory=tuple)


CASES: dict[str, Case] = {
    "C1_binders": Case(
        "theorem t : ∀ (a b : Nat), a + b = b + a ∧ True :=",
        "by\n  intro a b\n  have h1 : a + b = b + a := sorry\n  exact ⟨h1, trivial⟩",
        expect=("t_h1 a b",),
    ),
    "C2_same_type_second_only": Case(
        "theorem t : ∀ (x y : Nat), y + 0 = y ∧ x = x :=",
        "by\n  intro x y\n  have h1 : y + 0 = y := sorry\n  exact ⟨h1, rfl⟩",
    ),
    "C3_mention_order": Case(
        "theorem t : ∀ (x y : Nat), y * x = x * y ∧ True :=",
        "by\n  intro x y\n  have h1 : y * x = x * y := sorry\n  exact ⟨h1, trivial⟩",
    ),
    "C4_implicit_and_instance": Case(
        "theorem t {A : Type} [Inhabited A] (xs : List A) : xs ++ [] = xs ∧ True :=",
        "by\n  have h1 : xs ++ [] = xs := sorry\n  exact ⟨h1, trivial⟩",
    ),
    "C5_intro_inside": Case(
        "theorem t : ∀ n : Nat, ∀ m : Nat, n + m = m + n :=",
        "by\n  intro n\n  intro m\n  have h : m + n = n + m := sorry\n  exact h.symm",
    ),
    "C6_inaccessible_intro": Case(
        "theorem t : ∀ (a : Nat) (b : Nat), b + 0 = b ∧ True :=",
        "by\n  intro _ b\n  have h : b + 0 = b := sorry\n  exact ⟨h, trivial⟩",
        expect=("rename_i",),
    ),
    "C6b_shadowed": Case(
        "theorem t : ∀ (x : Nat), ∀ (x : Nat), x + 0 = x ∧ True :=",
        "by\n  intro x x\n  have h : x + 0 = x := sorry\n  exact ⟨h, trivial⟩",
        expect=("rename_i",),
    ),
    "C7_hole_mentions_earlier_hole": Case(
        "theorem t : ∃ n : Nat, n ≥ 1 :=",
        "by\n  have h1 : ∃ n : Nat, n > 0 := sorry\n"
        "  have h2 : Classical.choose h1 ≥ 1 := sorry\n  exact ⟨_, h2⟩",
    ),
    "C8_hole_ignores_earlier_hole": Case(
        "theorem t (p q : Prop) : (p → q) → p → q ∧ p :=",
        "by\n  intro hpq hp\n  have h1 : q := sorry\n  have h2 : p ∧ True := sorry\n"
        "  exact ⟨h1, h2.1⟩",
    ),
    "C9_proved_have_used": Case(
        "theorem t : ∃ k : Nat, k > 3 :=",
        "by\n  have k : Nat := 5\n  have h : k > 3 := sorry\n  exact ⟨k, h⟩",
        composed_has=("let k : Nat := 5",),
    ),
    "C10_proved_have_unused": Case(
        "theorem t (n : Nat) : n + 0 = n ∧ True :=",
        "by\n  have k : 2 = 2 := rfl\n  have h : n + 0 = n := sorry\n  exact ⟨h, trivial⟩",
    ),
    "C11_obtain_named": Case(
        "theorem t (h : ∃ n : Nat, n > 0) : ∃ m : Nat, m ≥ 1 :=",
        "by\n  obtain ⟨k, hk⟩ := h\n  have h2 : k ≥ 1 := sorry\n  exact ⟨k, h2⟩",
        expect=("Exists.intro _ _ k hk",),
    ),
    "C11b_obtain_anonymous": Case(
        "theorem t (h : ∃ n : Nat, n > 0) : True ∧ True :=",
        "by\n  obtain ⟨_, _⟩ := h\n  have h2 : True := sorry\n  exact ⟨h2, trivial⟩",
        expect=("rename_i", "Exists.intro"),
    ),
    "C12_two_branches": Case(
        "theorem t (p q : Prop) (h : Or p q) : Or q p :=",
        "by\n  rcases h with h | h\n  · have h1 : Or q p := sorry\n    exact h1\n"
        "  · have h1 : Or q p := sorry\n    exact h1",
        expect=("Or.inl", "Or.inr"),
    ),
    "C13_induction": Case(
        "theorem t (n : Nat) : 0 + n = n :=",
        "by\n  induction n with\n  | zero => rfl\n"
        "  | succ m ih =>\n    have h : 0 + (m + 1) = m + 1 := sorry\n    exact h",
        expect=("ih",),
    ),
    "C14_dependent": Case(
        "theorem t (S : List Nat) (x : Nat) (hx : x ∈ S) : S ≠ [] ∧ True :=",
        "by\n  have h : S ≠ [] := sorry\n  exact ⟨h, trivial⟩",
    ),
    "C15_term_mode_fun": Case(
        "theorem t : ∀ n : Nat, n + 0 = n ∧ True :=",
        "fun n => by\n  have h : n + 0 = n := sorry\n  exact ⟨h, trivial⟩",
    ),
    "C16_coercions": Case(
        "theorem t (n : Nat) (m : Int) : (n : Int) + m = m + (n : Int) ∧ True :=",
        "by\n  have h : (n : Int) + m = m + (n : Int) := sorry\n  exact ⟨h, trivial⟩",
    ),
    "C20_by_sorry_on_its_own_line": Case(
        "theorem t : ∀ (a b : Nat), a + b = b + a ∧ True :=",
        "by\n  intro a b\n  have h1 : a + b = b + a := by\n    sorry\n  exact ⟨h1, trivial⟩",
    ),
    "C20b_by_sorry_inline": Case(
        "theorem t : ∀ (a b : Nat), a + b = b + a ∧ True :=",
        "by\n  intro a b\n  have h1 : a + b = b + a := by sorry\n  exact ⟨h1, trivial⟩",
    ),
    "C21_premise_rewritten_then_cleared": Case(
        "theorem t (x : Nat) (h : ¬(1 ≤ x)) : x = 0 ∧ True :=",
        "by\n  have h' : x < 1 := Nat.lt_of_not_le h\n  clear h\n"
        "  have hole : x = 0 := sorry\n  exact ⟨hole, trivial⟩",
    ),
    "C22_hole_is_a_forall": Case(
        "theorem t (n : Nat) (hn : 0 < n) : (∀ m : Nat, m < m + n) ∧ True :=",
        "by\n  have core : ∀ m : Nat, m < m + n := by\n    sorry\n  exact ⟨core, trivial⟩",
    ),
    "C18_opens_and_namespace": Case(
        "theorem Foo.t (n : Nat) : double n = n + n ∧ True :=",
        "by\n  have h : double n = n + n := sorry\n  exact ⟨h, trivial⟩",
        prelude="namespace Foo\ndef double (n : Nat) : Nat := 2 * n\nend Foo\nopen Foo\n",
        decl="Foo.t",
    ),
}


class Bench:
    """Runs the gate's two programs over one case at a time, in a scratch directory."""

    def __init__(self, root: Path, tc: LocalToolchain, pinned: ResolvedToolchain, bin_dir: Path):
        self.root, self.tc, self.pinned, self.bin = root, tc, pinned, bin_dir

    def run(self, exe: str, args: list[str]) -> dict[str, Any]:
        sysroot = self.pinned.libdir.parent.parent
        proc = subprocess.run(
            [str(self.tc.elan), "run", self.pinned.name, str(self.bin / exe), *args],
            cwd=self.root,
            env={
                "LEAN_PATH": str(self.pinned.libdir),
                "LEAN_SYSROOT": str(sysroot),
                "ELAN_HOME": str(self.tc.elan.parent.parent),
                "PATH": f"{sysroot / 'bin'}:/usr/bin:/bin",
                "HOME": str(self.root),
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        assert proc.stdout.strip(), proc.stderr
        doc: dict[str, Any] = json.loads(proc.stdout.strip().splitlines()[-1])
        return doc

    def holes(self, name: str, case: Case) -> list[dict[str, Any]]:
        """Step 2: the extractor's holes for the case's assembly."""
        stmt = self.root / f"{name}_Statement.lean"
        art = self.root / f"{name}_Assembly.lean"
        stmt.write_text(f"{case.prelude}{case.header} by\n  sorry\n", encoding="utf-8")
        art.write_text(f"{case.prelude}{case.header} {case.body}\n", encoding="utf-8")
        doc = self.run(
            "opn-artifact-type",
            [
                "--statement", str(stmt), "--module", f"Case.{name}.Statement",
                "--decl", case.decl, "--artifact", str(art),
                "--artifact-module", f"Case.{name}.Assembly", "--artifact-decl", case.decl,
                "--kind", "partial",
            ],
        )  # fmt: skip
        assert doc["ok"], doc
        holes: list[dict[str, Any]] = doc["holes"]
        assert holes, f"{name}: the extractor found no hole"
        assert all(h["closed_roundtrip"] for h in holes), holes
        return holes

    def compose(self, name: str, case: Case, *, reverse: bool = False) -> dict[str, Any]:
        """Step 3: the children declared where Context.lean would put them, then opn-close."""
        holes = self.holes(name, case)
        children = [{"node": f"t--h{i + 1}", "decl": f"t_h{i + 1}"} for i in range(len(holes))]
        decls = "".join(f"axiom t_h{i + 1} : {h['closed_type']}\n\n" for i, h in enumerate(holes))
        path = self.root / f"{name}.lean"
        path.write_text(f"{case.prelude}{decls}{case.header} {case.body}\n", encoding="utf-8")
        spec = self.root / f"{name}.children.json"
        spec.write_text(json.dumps(children[::-1] if reverse else children), encoding="utf-8")
        args = ["--file", str(path), "--module", f"Case.{name}", "--decl", case.decl]
        out = self.root / "out" / f"{name}.olean"
        return self.run("opn-close", [*args, "--children", str(spec), "--out-olean", str(out)])


@pytest.fixture(scope="module")
def bench(
    tmp_path_factory: pytest.TempPathFactory,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
) -> Bench:
    assert (lean_pkg / "opn-close").is_file()
    return Bench(tmp_path_factory.mktemp("close"), real_toolchain, pinned, lean_pkg)


@pytest.mark.parametrize("name", sorted(CASES))
def test_composed_proof_checks(bench: Bench, name: str) -> None:
    """AC10: every shape joins, each hole to a child, the kernel accepts the theorem, and it rests
    on the standard axioms and the children alone."""
    case = CASES[name]
    holes = bench.holes(name, case)
    doc = bench.compose(name, case)
    assert doc["ok"], json.dumps(doc, indent=1, ensure_ascii=False)
    assert len(doc["holes"]) == len(holes)
    assert all(h["child"].startswith("t--h") for h in doc["holes"])
    assert Path(doc["olean"]).is_file()
    allowed = {"propext", "Classical.choice", "Quot.sound"}
    assert set(doc["axioms"]) - allowed <= {f"t_h{i + 1}" for i in range(len(holes))}
    assert "sorryAx" not in doc["axioms"]


def test_route_order_does_not_matter(bench: Bench) -> None:
    """Holes are matched to children by statement, never by position: the route's children given
    in reverse still compose, each hole to its own child."""
    case = CASES["C8_hole_ignores_earlier_hole"]
    doc = bench.compose("C8_reversed", case, reverse=True)
    assert doc["ok"], doc
    assert [h["child"] for h in doc["holes"]] == ["t--h1", "t--h2"]


def test_a_hole_no_child_closes_is_reported(bench: Bench) -> None:
    """A route whose child does not state the gap (a mis-written hole, the 2026-09-17 class)
    composes nothing and says which hole failed (F28-R10)."""
    path = bench.root / "Wrong.lean"
    path.write_text(
        "axiom t_h1 : ∀ (a b : Nat), a * b = b * a\n\n"
        "theorem t : ∀ (a b : Nat), a + b = b + a ∧ True := by\n"
        "  intro a b\n  have h1 : a + b = b + a := sorry\n  exact ⟨h1, trivial⟩\n",
        encoding="utf-8",
    )
    spec = bench.root / "Wrong.children.json"
    spec.write_text(json.dumps([{"node": "t--h1", "decl": "t_h1"}]), encoding="utf-8")
    out = bench.root / "out" / "Wrong.olean"
    doc = bench.run(
        "opn-close",
        ["--file", str(path), "--module", "Case.Wrong", "--decl", "t", "--children", str(spec),
         "--out-olean", str(out)],
    )  # fmt: skip
    assert doc["ok"] is False
    assert "hole h1: no child closes it" in doc["error"]
    assert not out.exists()


def test_a_sibling_by_definitional_equality(bench: Bench) -> None:
    """C17: a hole that became an existing node whose statement is the gap only up to unfolding
    (``n + 0 = n`` against ``n = n``) still composes."""
    path = bench.root / "Sibling.lean"
    path.write_text(
        "theorem s : ∀ (n : Nat), n = n := fun _ => rfl\n\n"
        "theorem t : ∀ (n : Nat), n + 0 = n ∧ True := by\n"
        "  intro n\n  have h1 : n + 0 = n := sorry\n  exact ⟨h1, trivial⟩\n",
        encoding="utf-8",
    )
    spec = bench.root / "Sibling.children.json"
    spec.write_text(json.dumps([{"node": "s", "decl": "s"}]), encoding="utf-8")
    doc = bench.run(
        "opn-close",
        ["--file", str(path), "--module", "Case.Sibling", "--decl", "t", "--children", str(spec),
         "--out-olean", str(bench.root / "out" / "Sibling.olean")],
    )  # fmt: skip
    assert doc["ok"], doc
    assert doc["holes"] == [{"hole": "h1", "child": "s"}]


def test_the_seam_runs_the_program(bench: Bench) -> None:
    """``LocalToolchain.close`` sends ``CloseRequest``'s arguments to the real binary and reads
    its one JSON document back (the wiring ``close.compose`` uses)."""
    path = bench.root / "Seam.lean"
    path.write_text(
        "axiom t_h1 : ∀ (a b : Nat), a + b = b + a\n\n"
        "theorem t : ∀ (a b : Nat), a + b = b + a ∧ True := by\n"
        "  intro a b\n  have h1 : a + b = b + a := sorry\n  exact ⟨h1, trivial⟩\n",
        encoding="utf-8",
    )
    spec = bench.root / "Seam.children.json"
    spec.write_text(json.dumps([{"node": "t--h1", "decl": "t_h1"}]), encoding="utf-8")
    seam = LocalToolchain(bench.tc.elan, bench.bin)
    out = bench.root / "out" / "Seam.olean"
    req = CloseRequest(path, "Case.Seam", "t", spec, out)
    got = seam.close(bench.pinned, req, [], timeout_s=300)
    assert got.ok, got.output
    assert got.doc["ok"] and out.is_file()
    assert got.doc["holes"] == [{"hole": "h1", "child": "t--h1"}]


LINK_STATEMENT = "/-- The ancestor. -/\ntheorem a_thm : ∃ K : Nat, K + 0 = K := by\n  sorry\n"
LINK_SOURCES = {
    "variant": "-- relation: resolves\n\n"
    "theorem relation : (∃ K : Nat, K = K) → ∃ K : Nat, K + 0 = K :=\n"
    "  fun ⟨K, _⟩ => ⟨K, rfl⟩\n",
}


@pytest.mark.parametrize("kind", sorted(LINK_SOURCES))
def test_a_link_proof_elaborates(bench: Bench, kind: str) -> None:
    """F28-T3 / AC7, AC8: the closing proof through a variant's relation (the claim link
    retired, F28-Q11), as ``close.link_text`` writes it, elaborates whole with no ``sorry``. The
    input's theorem is declared at the top, where its use line's import would put it."""
    st = layout.parse_statement(LINK_STATEMENT)
    assert isinstance(st, layout.Statement)
    helper = close.as_helper(LINK_SOURCES[kind], kind, st.prefix)
    text = "theorem h_thm : ∃ K : Nat, K = K := ⟨0, rfl⟩\n\n" + close.link_text(
        st, helper, "h_thm", None
    )
    path = bench.root / f"Link_{kind}.lean"
    path.write_text(text, encoding="utf-8")
    sysroot = bench.pinned.libdir.parent.parent
    proc = subprocess.run(
        [str(bench.tc.elan), "run", bench.pinned.name, "lean", str(path)],
        cwd=bench.root,
        env={
            "LEAN_PATH": str(bench.pinned.libdir),
            "ELAN_HOME": str(bench.tc.elan.parent.parent),
            "PATH": f"{sysroot / 'bin'}:/usr/bin:/bin",
            "HOME": str(bench.root),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "sorry" not in proc.stdout + proc.stderr
    assert "(opn_closing_link @_root_.h_thm)" in text


def test_a_chain_joins_level_by_level_and_the_root_is_kernel_checked(bench: Bench) -> None:
    """The owner's question of 2026-10-15: a proved grandchild closes its parent and that closes
    the root, with no intermediate source anywhere. The grandchild is a compiled proof; the
    middle node is joined into a module the root's assembly imports; the root is joined on that
    module, and rests on the standard axioms alone."""
    out = bench.root / "chain"
    (out / "Case").mkdir(parents=True, exist_ok=True)
    sysroot = bench.pinned.libdir.parent.parent
    env = {
        "LEAN_PATH": f"{bench.pinned.libdir}:{out}",
        "LEAN_SYSROOT": str(sysroot),
        "ELAN_HOME": str(bench.tc.elan.parent.parent),
        "PATH": f"{sysroot / 'bin'}:/usr/bin:/bin",
        "HOME": str(bench.root),
    }
    g = out / "Case" / "G.lean"
    g.write_text("theorem g : ∀ n : Nat, n + 0 = n := fun _ => rfl\n", encoding="utf-8")
    made = subprocess.run(
        [str(bench.tc.elan), "run", bench.pinned.name, "lean", "-R", str(out),
         "-o", str(out / "Case" / "G.olean"), str(g)],
        env=env, capture_output=True, text=True, check=False, timeout=300,
    )  # fmt: skip
    assert made.returncode == 0, made.stdout + made.stderr
    levels = [
        ("C", "Case.G", "c", "(n + 0 = n) ∧ True", "g"),
        ("R", "Case.C", "r", "((n + 0 = n) ∧ True) ∧ True", "c"),
    ]
    for stem, imported, decl, body, child in levels:
        src = out / f"{stem}.lean"
        src.write_text(
            f"import {imported}\n\ntheorem {decl} : ∀ n : Nat, {body} := by\n  intro n\n"
            f"  have h : {body.rsplit(' ∧ True', 1)[0]} := sorry\n  exact ⟨h, trivial⟩\n",
            encoding="utf-8",
        )
        spec = out / f"{stem}.children.json"
        spec.write_text(json.dumps([{"node": child, "decl": child}]), encoding="utf-8")
        proc = subprocess.run(
            [str(bench.tc.elan), "run", bench.pinned.name, str(bench.bin / "opn-close"),
             "--file", str(src), "--module", f"Case.{stem}", "--decl", decl,
             "--children", str(spec), "--out-olean", str(out / "Case" / f"{stem}.olean")],
            env=env, capture_output=True, text=True, check=False, timeout=300,
        )  # fmt: skip
        doc = json.loads(proc.stdout.strip().splitlines()[-1])
        assert doc["ok"], doc
    assert set(doc["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"}
    assert (out / "Case" / "R.olean").is_file()
