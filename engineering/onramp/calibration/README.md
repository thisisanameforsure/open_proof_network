# The three calibration targets (F15-T14a; R14, Q9, Q12, Q13; Stages v3.17)

The steward rule is enforced only after a calibration run passes: fresh agents, with no help from
the founder or the build, carry three known results through the pipeline, at least one to
`resolved`, every failure a typed record. These are the three, drafted by
`docs/calibration_pool.py` from the registry at the pin the live targets use
(`c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae`, Mathlib `0df444a360eaa60ab8c11dca51a86af692955474`)
and read by hand before this file was written.

## The pool

`uv run python docs/calibration_pool.py pool` — every problem in the committed seed dataset with a
Lean statement in the pinned registry and an erdosproblems.com status of `PROVED`, `SOLVED` or
`DISPROVED` with no Lean proof. **30 rows** at the 2026-09 dataset (the spec's R14 said 29;
F15-Q13 records the corrected count, and `gate/tests/test_calibration_pool.py` holds the query to
it). Most of the pool is research mathematics solved by a named author decades after it was posed;
the grades below are relative to that pool, not to a textbook.

## The choices

| Target | Grade | Statement | Literature proof (prior art, R14 c) | Why this grade |
|---|---|---|---|---|
| `erdos-1050` | easy | `Irrational (∑' n, 1/(2^(n+1) − 3))` | Borwein 1991; self-contained in Borwein 1992 | One closed proposition, no local definitions, no helpers, no hazard flag; a Lean 4 proof of this statement exists in an external gallery (the registry cites it), so the mathematics is known to formalize and the question is whether a fresh agent produces one under the gate. |
| `erdos-69` | medium | `Irrational (∑' n, ω(n+2)/2^(n+2))` | Erdős 1948 | Two lemmas of ordinary analysis with no known Lean proof: the Lambert-series identity `∑ ω(n)/2^n = ∑_p 1/(2^p − 1)` and Erdős's irrationality argument for the prime sum; the agent has to decompose and prove. |
| `erdos-402` | needs a skeleton | `∀ A : Finset ℕ, 0 ∉ A → A.Nonempty → ∃ a b ∈ A, gcd(a, b) ≤ a/|A|` | Balasubramanian–Soundararajan 1996 (Graham's conjecture; Szegedy 1986, Zaharescu 1987 for large sets) | A multi-lemma argument no agent closes in a session: the honest first artifact is a skeleton whose holes are the lemmas (D-12 #5, D-31), the third shape the run must exercise. |

## What was read by hand, and what is unchecked

- `erdos-1050` and `erdos-69` are the driver's drafts as written: the registry header verbatim,
  `import Mathlib`, the file's `open` lines, the main statement as `Opn.erdos_<n>`, a `True`
  witness. Neither uses a `FormalConjecturesForMathlib` name.
- `erdos-402` has binders before the colon in the registry (`(A : Finset ℕ) (h₁ : 0 ∉ A) (h₂ :
  A.Nonempty)`), which the driver refuses rather than guess a witness for (F14-T15). Its
  statement is restated by hand as one closed `∀`, and its witness is the closure of the two
  hypotheses in the shape `gate/lean/OpnGate/WitnessType.lean` computes
  (`∃ A : Finset ℕ, 0 ∉ A ∧ A.Nonempty`, witnessed by `{1}`). **The witness has not been
  elaborated:** the laptop holds no Mathlib checkout, so it is checked first by the sandboxed
  admission of the intake pull request (T14b). If admission refuses it, the fix is the witness's
  two `by simp` calls, not the statement.
- The `answer(True) ↔ P` shape the registry uses for solved questions does not occur in these
  three; each main declaration is a plain proposition.

## Intake (T14b, the founder's sitting)

One pull request per target, on the formalization track, `calibration: true` in the record:

    for n in 1050 69 402; do
      uv run python -m opn_gate.cli intake new "erdos-$n" --graph ../open_proof_network_graph \
        --from engineering/onramp/calibration/erdos-$n/record.yaml \
        --root <a node directory built from Statement.lean and Witness.lean, as engineering/onramp/open/import.sh builds one> \
        --author thisisanameforsure --branch "intake/erdos-$n" --sandbox
    done

The records carry no `sources` entry; `intake new` is the curator's act and the registry's
Apache-2.0 attribution rides in the statement's header, as for the wave targets (F11-Q26).
The run itself (T14c) and its record are `engineering/evidence/F15/calibration.md`.
