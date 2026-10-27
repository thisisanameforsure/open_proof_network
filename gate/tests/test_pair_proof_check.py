"""F26-T17 (R8): the verdict on a pair proof through a fake toolchain (``pair_proof_check``).

The verdict is the one function the service's pre-flight, the gate before the merge and the job
after it share: the template and the regions (``pair_proofs.split``, ``problems``), the filled file
elaborated with no error and no ``sorry``, the kernel's replay of what it built, the theorem and
the candidates it states compared with the gate's own unfilled template, the axioms read with
initializers off from a directory no compile wrote, and for a proof the degenerate guard. Each
branch here is one way it ends; the lean tier (``test_pair_proof_check_lean.py``) runs the same
texts through Lean 4.33.1."""

from __future__ import annotations

import copy
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fakes import FakeToolchain, meaning_result

from opn_gate import pair_proof_check, pair_proofs, review_lean, review_pairs
from opn_gate.toolchain import (
    AxiomResult,
    ElabResult,
    MeaningRequest,
    Message,
    MetaprogramResult,
    ReplayResult,
    ResolvedToolchain,
    module_output_path,
)

FIX = Path(__file__).parent / "fixtures" / "review" / "legendre"
A, B = "c-aaaaaaaa", "c-bbbbbbbb"
HELPER = "private theorem same (p : Nat) : C_c_aaaaaaaa_p.Prime p → C_c_bbbbbbbb_p.Prime p := id\n"
PROOF = (
    "  intro hn\n  obtain ⟨p, h1, h2, h3⟩ := h hn\n"
    "  exact ⟨p, Nat.le_of_lt h1, Nat.le_of_lt h2, same p h3⟩\n"
)
SORRY_WARNING = Message("f", 1, 0, "warning", "declaration uses 'sorry'")


def cand(cid: str, name: str) -> review_lean.Cand:
    c = review_lean.prepare(cid, (FIX / f"{name}.lean").read_text(encoding="utf-8"), ["prime"])
    assert isinstance(c, review_lean.Cand)
    return c


def fill(tmpl: str, helpers: str = HELPER, proof: str = PROOF) -> str:
    return tmpl.replace(pair_proofs.HELPERS_END, helpers + pair_proofs.HELPERS_END).replace(
        pair_proofs.PLACEHOLDER, proof
    )


@dataclass
class PairFake(FakeToolchain):
    """Decides each compile by which of the three texts it is handed: the gate's unfilled
    template (the reference), the guarded copy (``; clear h`` after the intro), or the filled
    file. Every ``scoped`` call is kept, so a test can read what each call could write."""

    main: ElabResult = field(default_factory=lambda: ElabResult(ok=True))
    guard_ok: bool = False
    reference_ok: bool = True
    timeout_on: str | None = None
    mounts: list[tuple[str, tuple[Path, ...], tuple[Path, ...]]] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    _ro: tuple[Path, ...] = ()
    _rw: tuple[Path, ...] = ()

    def scoped(
        self, *, read_only: Sequence[Path] = (), read_write: Sequence[Path] = ()
    ) -> PairFake:
        other = copy.copy(self)
        other._ro, other._rw = tuple(read_only), tuple(read_write)
        return other

    def _note(self, what: str) -> None:
        self.mounts.append((what, self._ro, self._rw))
        if self.timeout_on == what:
            raise subprocess.TimeoutExpired([what], 1.0)

    def elaborate(
        self,
        tc: ResolvedToolchain,
        source: Path,
        module: str,
        out_dir: Path,
        *,
        root: Path | None = None,
        timeout_s: float | None = None,
    ) -> ElabResult:
        text = source.read_text(encoding="utf-8")
        self.texts.append(text)
        if text.endswith(pair_proofs.PROOF_BEGINS + "\n" + pair_proofs.PLACEHOLDER):
            which = "reference"
            result = ElabResult(ok=self.reference_ok, messages=(SORRY_WARNING,))
        elif "; clear h\n" in text:
            which, result = "guard", self.guard_result()
        else:
            which, result = "filled", self.main
        self.calls.append(f"elaborate:{which}")
        self._note(f"elaborate:{which}")
        if result.ok:
            olean = out_dir / module_output_path(module, ".olean")
            olean.parent.mkdir(parents=True, exist_ok=True)
            olean.write_bytes(b"fake olean")
        return result

    def guard_result(self) -> ElabResult:
        return ElabResult(ok=self.guard_ok)

    def kernel_replay(
        self,
        tc: ResolvedToolchain,
        modules: Sequence[str],
        search_path: Sequence[Path],
        *,
        fresh: bool,
        timeout_s: float | None = None,
    ) -> ReplayResult:
        self._note("replay")
        got: ReplayResult = super().kernel_replay(
            tc, modules, search_path, fresh=fresh, timeout_s=timeout_s
        )
        return got

    def axioms(
        self,
        tc: ResolvedToolchain,
        module: str,
        decl: str,
        search_path: Sequence[Path],
        scratch: Path,
        *,
        timeout_s: float | None = None,
    ) -> AxiomResult:
        self._note("axioms")
        got: AxiomResult = super().axioms(
            tc, module, decl, search_path, scratch, timeout_s=timeout_s
        )
        return got

    def statement_meaning(
        self,
        tc: ResolvedToolchain,
        req: MeaningRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        self._note("meaning")
        self.calls.append(f"meaning:{req.decl}")
        got: MetaprogramResult = self.meaning
        return got


STANDARD = AxiomResult(ok=True, axioms=frozenset({"propext", "Quot.sound"}))


Pair = tuple[review_lean.Cand, review_lean.Cand]


@pytest.fixture
def pair() -> Pair:
    return cand(A, "human-ref"), cand(B, "alt-closed")


def run(
    fake: PairFake,
    text: str,
    tmpl: str,
    first: review_lean.Cand,
    tmp_path: Path,
    *,
    kind: pair_proofs.Kind = "proof",
) -> pair_proof_check.Verdict:
    return pair_proof_check.verdict(
        fake,
        fake.resolved,
        text,
        tmpl,
        first=first,
        kind=kind,
        workdir=tmp_path / "work",
        timeout_s=60,
    )


# --- the happy paths ---------------------------------------------------------------------------


def test_a_proof_that_uses_its_hypothesis_passes(pair: Pair, tmp_path: Path) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=STANDARD)
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert got.ok, got
    assert got.code is None
    assert got.axioms == tuple(sorted(STANDARD.axioms))
    assert [c for c in fake.calls if c.startswith("elaborate:")] == [
        "elaborate:reference",
        "elaborate:filled",
        "elaborate:guard",
    ]
    assert "axioms:OpnPairProof:opnDirection" in fake.calls
    assert "meaning:opnDirection" in fake.calls
    assert fake.replays == [(("OpnPairProof",), True)]  # core Lean: replayed fresh


def test_a_refutation_at_an_instance_passes_and_has_no_guard(tmp_path: Path) -> None:
    a, b = cand(A, "human-ref"), cand(B, "bad-zero")
    tmpl = pair_proofs.template(a, b, "forward", "refutation", 0)
    fake = PairFake(axiom_result=AxiomResult(ok=True, axioms=frozenset()))
    got = run(
        fake, fill(tmpl, helpers="", proof="  decide\n"), tmpl, a, tmp_path, kind="refutation"
    )
    assert got.ok, got
    assert "elaborate:guard" not in fake.calls
    assert "axioms:OpnPairProof:opnInstance" in fake.calls


def test_a_mathlib_pin_replays_the_module_against_its_imports(pair: Pair, tmp_path: Path) -> None:
    from dataclasses import replace  # noqa: PLC0415

    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=STANDARD)
    fake.resolved = replace(fake.resolved, mathlib_sha="a" * 40)
    assert run(fake, fill(tmpl), tmpl, a, tmp_path).ok
    assert fake.replays == [(("OpnPairProof",), False)]


# --- the judging workspace ----------------------------------------------------------------------


def test_no_judging_call_can_write_and_none_reads_a_directory_a_compile_wrote(
    pair: Pair, tmp_path: Path
) -> None:
    """F02-T10, T11: the filled file is compiled in a call whose only writable directory is its
    own compile area; the replay, the meaning comparison and the axioms read the module's olean
    from a directory that compile could not write, and can write nothing."""
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=STANDARD)
    assert run(fake, fill(tmpl), tmpl, a, tmp_path).ok
    compiled_rw = {p for what, _ro, rw in fake.mounts if what.startswith("elaborate") for p in rw}
    assert compiled_rw, "every compile is confined"
    for what, ro, rw in fake.mounts:
        if what in ("replay", "meaning", "axioms"):
            assert rw == (), what
            assert ro, what
            for path in ro:
                assert not any(path == w or w in path.parents for w in compiled_rw), (what, path)


# --- the static rules, before any toolchain ------------------------------------------------------


def test_a_byte_the_gate_wrote_is_refused_before_anything_runs(pair: Pair, tmp_path: Path) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=STANDARD)
    got = run(fake, fill(tmpl).replace("→ C_c_bbbbbbbb_p.claim n", "→ True"), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-template-mismatch")
    assert fake.calls == []


def test_a_forbidden_region_is_refused_before_anything_runs(pair: Pair, tmp_path: Path) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=STANDARD)
    got = run(fake, fill(tmpl, proof="  intro hn\n  sorry\n"), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-forbidden")
    assert got.details["token"] == "sorry"  # noqa: S105 — a Lean word, not a secret
    assert fake.calls == []


# --- the Lean ------------------------------------------------------------------------------------


def test_a_file_that_does_not_elaborate_is_refused_with_its_messages(
    pair: Pair, tmp_path: Path
) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    err = Message("f", 40, 2, "error", "unsolved goals")
    fake = PairFake(main=ElabResult(ok=False, messages=(err,)), axiom_result=STANDARD)
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-elaboration")
    assert got.details["messages"][0]["text"] == "unsolved goals"
    assert "axioms:OpnPairProof:opnDirection" not in fake.calls


def test_an_error_lean_reports_with_exit_zero_is_still_an_error(pair: Pair, tmp_path: Path) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    err = Message("f", 40, 2, "error", "unknown identifier")
    fake = PairFake(main=ElabResult(ok=True, messages=(err,)), axiom_result=STANDARD)
    assert run(fake, fill(tmpl), tmpl, a, tmp_path).code == "pair-proof-elaboration"


def test_a_sorry_reached_through_a_helper_is_refused(pair: Pair, tmp_path: Path) -> None:
    """The regions refuse the word; a sorry can still arrive by elaboration (a helper's macro, an
    autoBound stub), and Lean says so in a warning."""
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(main=ElabResult(ok=True, messages=(SORRY_WARNING,)), axiom_result=STANDARD)
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-sorry")


def test_sorry_ax_among_the_axioms_is_a_sorry_even_without_the_warning(
    pair: Pair, tmp_path: Path
) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=AxiomResult(ok=True, axioms=frozenset({"propext", "sorryAx"})))
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-sorry")


@pytest.mark.parametrize(
    "axiom",
    [
        "Lean.ofReduceBool",
        "Lean.trustCompiler",
        "C_c_aaaaaaaa_p.cheat",
        "Classical.em",
        # 4.33.1: native_decide's own auxiliary axiom, which no blocklist would name
        "opnDirection._native.native_decide.ax_1_1",
        "anything.at.all",
    ],
)
def test_an_axiom_outside_the_standard_three_is_refused(
    pair: Pair, tmp_path: Path, axiom: str
) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=AxiomResult(ok=True, axioms=frozenset({"propext", axiom})))
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-axiom")
    assert got.details["axioms"] == [axiom]
    assert got.details["allowlist"] == ["Classical.choice", "Quot.sound", "propext"]


def test_axioms_that_cannot_be_read_decide_nothing_and_refuse(pair: Pair, tmp_path: Path) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=AxiomResult(ok=False, output="no verdict line"))
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-unchecked")


def test_the_kernel_replay_rejecting_the_build_is_refused(pair: Pair, tmp_path: Path) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(replay=ReplayResult(ok=False, output="bad decl"), axiom_result=STANDARD)
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-replay")


def test_a_theorem_or_candidate_that_compiled_to_something_else_is_refused(
    pair: Pair, tmp_path: Path
) -> None:
    """The template fixes the text; the meaning comparison fixes what it compiled to: the
    filled module's theorem and every candidate declaration its type reaches must be the gate's
    unfilled template's, by the kernel."""
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(
        axiom_result=STANDARD,
        meaning=meaning_result(matches=False, local_mismatch=("C_c_bbbbbbbb_p.claim",)),
    )
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-meaning")
    assert got.details["local_mismatch"] == ["C_c_bbbbbbbb_p.claim"]


def test_a_meaning_program_that_answers_nothing_refuses(pair: Pair, tmp_path: Path) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=STANDARD, meaning=MetaprogramResult(ok=False, exit_code=1))
    assert run(fake, fill(tmpl), tmpl, a, tmp_path).code == "pair-proof-unchecked"


def test_a_template_that_does_not_build_decides_nothing_and_refuses(
    pair: Pair, tmp_path: Path
) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=STANDARD, reference_ok=False)
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-unchecked")
    assert "elaborate:filled" not in fake.calls


@pytest.mark.parametrize("where", ["elaborate:filled", "replay", "axioms", "meaning"])
def test_a_timeout_anywhere_decides_nothing_and_refuses(
    pair: Pair, tmp_path: Path, where: str
) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=STANDARD, timeout_on=where)
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-unchecked")


# --- the degenerate guard ----------------------------------------------------------------------


def test_a_proof_that_still_proves_with_its_hypothesis_cleared_is_degenerate(
    pair: Pair, tmp_path: Path
) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=STANDARD, guard_ok=True)
    got = run(fake, fill(tmpl), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-degenerate")
    assert got.reason.startswith(review_pairs.GUARD_TOOL)
    guarded = [t for t in fake.texts if "; clear h\n" in t]
    assert guarded == [pair_proofs.guarded(fill(tmpl), a)]


def test_the_guard_failing_on_its_own_timeout_is_the_guard_failing(
    pair: Pair, tmp_path: Path
) -> None:
    """As the job reads it (``Runner.check``): a guarded copy that does not elaborate within
    the budget did not prove, so the proof stands."""
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    fake = PairFake(axiom_result=STANDARD, timeout_on="elaborate:guard", guard_ok=True)
    assert run(fake, fill(tmpl), tmpl, a, tmp_path).ok


def test_a_guarded_copy_that_proves_only_through_sorry_is_not_a_proof(
    pair: Pair, tmp_path: Path
) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")

    @dataclass
    class SorryGuard(PairFake):
        def guard_result(self) -> ElabResult:
            return ElabResult(ok=True, messages=(SORRY_WARNING,))

    fake = SorryGuard(axiom_result=STANDARD)
    assert run(fake, fill(tmpl), tmpl, a, tmp_path).ok


# --- the record of it ----------------------------------------------------------------------------


def test_a_refusal_is_a_diagnostic_and_a_pass_is_none(pair: Pair, tmp_path: Path) -> None:
    a, b = pair
    tmpl = pair_proofs.template(a, b, "forward")
    good = run(PairFake(axiom_result=STANDARD), fill(tmpl), tmpl, a, tmp_path / "1")
    bad = run(PairFake(axiom_result=STANDARD, guard_ok=True), fill(tmpl), tmpl, a, tmp_path / "2")
    assert good.diagnostic is None
    assert bad.diagnostic is not None and bad.diagnostic.code == "pair-proof-degenerate"
    doc = bad.as_dict()
    assert (doc["ok"], doc["code"]) == (False, "pair-proof-degenerate")
    assert good.as_dict()["axioms"] == sorted(STANDARD.axioms)


def test_the_standard_three_are_defined_once_in_the_contract() -> None:
    """The service, the gate and the job read one allowlist (``pair_proofs.STANDARD_AXIOMS``)."""
    assert set(pair_proofs.STANDARD_AXIOMS) == {"propext", "Classical.choice", "Quot.sound"}
    assert pair_proof_check.ALLOWED_AXIOMS is pair_proofs.STANDARD_AXIOMS
    assert pair_proof_check.axiom_problem(frozenset(pair_proofs.STANDARD_AXIOMS), "x") is None
