# Lane 0 witness pass (2026-11-22, started 22:56Z)

| id | verdict | attempts | expected type | note |
|---|---|---|---|---|
| agrawal-conjecture | ACCEPTED | 1 | `∃ (n : ℕ) (r : ℕ), n > (1 : ℕ) ∧ r > (0 : ℕ) ∧ n.gcd r = (1 : ℕ)` | n = 2, r = 1 |
| bateman-horn-conjecture | probe limit | 1 | `∃ (polys : Finset ℤ[X]) (h_irreducible : ∀ f ∈ polys, BunyakovskyCondition f) (h_compat : SchinzelCondition polys), polys.Nonempty` (checker printed `sorry` for both conditions) | polys = {X}; `BunyakovskyCondition`/`SchinzelCondition` live in `Defs.AlgebraPolynomialBasic`, which this draft's imports do not carry, so they auto-bound in the probe (statement import defect as well as the inlining limit) |
| bunyakovsky-conjecture | ACCEPTED | 1 | `∃ (f : ℤ[X]), BunyakovskyCondition f ∧ SchinzelCondition {f}` | f = X; X(1) = 1 has no prime divisor |
| collatz-conjecture | ACCEPTED | 1 | `∃ (n : ℕ), n > (0 : ℕ)` | n = 1 |
| conjecture-4-2 | probe limit | 1 (written, unchecked: anon-check rate limit reached) | `∃ (k : ℕ), Nat.Prime k ∧ Odd k ∧ k > (233 : ℕ)` (probe: `∃ (x : Sort u_1) (S : x) …`, `S` auto-bound because the `Arxiv.` defs failed to inline) | k = 239 |
| conjecture84 | probe limit | 1 (written, unchecked) | `∃ (α : Type) (_ : Fintype α) (G : SimpleGraph α) (_ : DecidableRel G.Adj), G.Connected ∧ 0 < G.minDegree` (probe: `(0 : ℕ) < sorry`) | the statement itself fails: `minDegree` needs `[Fintype α]`, which the draft dropped (`failed to synthesize Fintype α` at the statement's own lines); witness: K₂ |
| dirichlet-divisor-problem | probe limit | 1 | `∃ (ε : ℝ), ε > (0 : ℝ)` | `matches: true`, `okay: false` only from the inlined `MilnorKTheory` port's own lemma proofs (`of_mul` unknown) |
| erdos-1075 | ACCEPTED | 1 | `∃ (r : ℕ), (3 : ℕ) ≤ r` | r = 3 |
| erdos-1111 | probe limit | 1 | `∃ (t : ℕ) (c : ℕ), (1 : ℕ) ≤ t ∧ (1 : ℕ) ≤ c` | `matches: true`, `okay: false` only from inlined-port errors (`undelimitBlocks_flatten_delimit` unknown) |
| erdos-14 | probe limit | 1 (written, unchecked) | `∃ (A : Set ℕ) (ε : ℝ), ε > (0 : ℝ)` (probe: no expected type; the `Erdos14` port fails on `Finset.IsSidon.exists_insert_ge`) | A = ∅, ε = 1 |
| erdos-173 | not accepted | 0 | `∃ (c : EuclideanSpace ℝ (Fin 2) → Fin 2) (T₁ T₂ : Triangle ℝ (EuclideanSpace ℝ (Fin 2))), ¬HasMonochromaticCopy c T₁ ∧ ¬HasMonochromaticCopy c T₂` | no witness written: it needs a 2-colouring of the plane with no monochromatic congruent copy of some triangle (the strip colouring against the unit equilateral triangle), real mathematics well past the 20 s budget; also probe-limited (port errors) |
| erdos-28 | ACCEPTED | 1 | `∃ (A : Set ℕ), (A + A)ᶜ.Finite` | A = univ, n = n + 0 |
| erdos-389 | ACCEPTED | 1 | `∃ (n : ℕ), n ≥ (1 : ℕ)` | n = 1 |
| erdos-479 | ACCEPTED | 1 | `∃ (k : ℤ) (k : ℤ), k ≠ (1 : ℤ)` | the `∀ᵉ (k : ℤ) (k ≠ 1)` binder closes to a doubled `k`; witness 0, 0 |
| erdos-561 | probe limit | 1 (written, unchecked) | `∃ (s t : ℕ) (n : Fin s → ℕ) (m : Fin t → ℕ), 1 ≤ s ∧ 1 ≤ t ∧ Antitone n ∧ Antitone m ∧ (∀ i, 1 ≤ n i) ∧ ∀ j, 1 ≤ m j` (probe: no expected type) | the statement does not parse: notation `F(s, n)` is not in the ported defs (`unexpected token '('`); s = t = 1, constant sequences |
| erdos-600 | probe limit | 1 | `∃ (r : ℕ), (2 : ℕ) ≤ r` (probe: `∃ (x : Sort u_1) (eFunction : x) (r : ℕ), 2 ≤ r`, `eFunction` auto-bound) | r = 2 |
| erdos-685 | not accepted | 0 checks (written, unchecked) | guessed `∃ (ε : ℝ) (δ : ℝ), ε > (0 : ℝ) ∧ δ > (0 : ℝ)` | checker rate-limited before the first probe (`anon-check: limit of 200 per 86400s reached`, shared across lanes); ε = δ = 1 |
| erdos-749 | probe limit | 1 (written, unchecked) | `∃ (ε : ℝ), ε > (0 : ℝ)` (probe: no expected type) | the statement does not parse at `≪` (notation missing from the ported defs); ε = 1 |
| erdos-864 | probe limit | 1 (written, unchecked) | `∃ (ε : ℝ), (0 : ℝ) < ε` | port errors in the probe; ε = 1 |
| erdos-930 | not accepted | 1 dummy probe (written, unchecked) | `∃ (r : ℕ), r > (0 : ℕ)` (probe okay: true) | r = 1; the check of the witness itself was rate-limited |
| erdos-979 | probe limit | 1 (written, unchecked) | `∃ (k : ℕ), k ≥ (2 : ℕ)` | port errors in the probe; k = 2 |
| fermat-number-are-composite | not accepted | 1 dummy probe (written, unchecked) | `∃ (n : ℕ), n > (4 : ℕ)` (probe okay: true) | n = 5; witness check rate-limited |
| goormaghtigh-conjecture | probe limit | 1 (written, unchecked) | `∃ (N : ℕ), IsGoormaghtighNumber N` (probe: `∃ (x : Sort u_1) (IsGoormaghtighNumber : x) (N : ℕ) (hN : sorry), True`) | statement defect: `IsGoormaghtighNumber` has no ported definition (defs/ empty); N = 31 with `by decide`, which the gate must judge |
| green-70 | probe limit | 1 (written, unchecked) | `∃ (k : ℕ) (ℓ : ℕ), True` | port errors in the probe; k = ℓ = 0 |
| idempotent-conjecture | probe limit | 1 (written, unchecked) | `∃ (K G : Type) (_ : Semiring K) (_ : Monoid G) (a : MonoidAlgebra K G), IsIdempotentElem a` (probe: no expected type) | statement defect: `K`, `G` auto-bound with no `Semiring K` (`failed to synthesize Semiring K` in the statement); a = 0 in ℕ[Unit] |
| inverse-galois-problem | probe limit | 1 (written, unchecked) | `∃ (G : Type) (_ : Fintype G) (_ : Group G), True` (probe: no expected type) | statement defect: `IsRealizable` has no ported definition (defs/ empty); G = Unit |
| kotzig-conjecture | not accepted | 0 checks (written, unchecked) | guessed `∃ (V : Type) (_ : Finite V) (T : SimpleGraph V) (n : ℕ), T.IsTree ∧ T.edgeSet.ncard = n` | rate-limited; one-vertex ⊥, n = 0 |
| lebesgue-nagell | not accepted | 0 checks (written, unchecked) | guessed `∃ (p : ℕ) (x y : ℤ), Nat.Prime p ∧ Odd p` | rate-limited; p = 3, x = y = 0 |
| lonely-runner-conjecture | not accepted | 0 checks (written, unchecked) | guessed `∃ (n : ℕ) (speed : Fin n ↪ ℝ) (lonely : Fin n → ℝ → Prop) (r : Fin n), ∀ r t, lonely r t ↔ …` | rate-limited; n = 1, speed 0, `lonely` defined as the clause so `lonely_def` is `Iff.rfl` |
| new-mersenne-conjecture | not accepted | 0 checks (written, unchecked) | guessed `∃ (p : ℕ), Odd p` | rate-limited; p = 1 |
| pebbling-number-conjecture | not accepted | 0 checks (written, unchecked) | guessed `∃ (V W : Type) (_ : Fintype V) (_ : Fintype W) (_ : DecidableEq W) (G : SimpleGraph V) (H : SimpleGraph W), G.Connected ∧ H.Connected` | rate-limited; also a statement defect (`V` auto-bound, no `(V : Type)` binder); one-vertex graphs |
| problem-10-8 | not accepted | 0 checks (written, unchecked) | guessed `∃ (ξ : ℝ) (p : ℕ), Nat.Prime p` | rate-limited; ξ = 0, p = 2 |
| rudins-conjecture-unique | not accepted | 0 | would be `∃ (N q a : ℕ), 6 ≤ N ∧ IsNontrivial q a ∧ Q N q a = Qmax N` | no witness written: `IsNontrivial`, `Q`, `Qmax` have no ported definition (defs/ empty), and `Q 6 24 1 = Qmax 6` is a real computation over all APs; statement defect |
| tan-arctan-sum-not-integer | not accepted | 0 checks (written, unchecked) | guessed `∃ (n : ℕ), (5 : ℕ) ≤ n` | rate-limited; n = 5 |
| tx-graffiti-conjecture-3 | not accepted | 0 checks (written, unchecked) | guessed `∃ (V : Type) (_ : Fintype V) (_ : DecidableEq V) (G : SimpleGraph V) (_ : DecidableRel G.Adj) (r : ℕ), (∀ v, G.degree v = r) ∧ 1 ≤ r` | rate-limited; K₂, r = 1 by `decide` |
| weighing-matrix-conjecture | not accepted | 0 checks (written, unchecked) | guessed `∃ (m w : ℕ), 1 ≤ m ∧ w ≤ 4 * m` | rate-limited; m = 1, w = 0 |

Checker exhausted at 23:02Z: `anon-check: limit of 200 per 86400s reached` on every call after the third batch (the limit is shared across the parallel lanes, not this lane's own 40-odd calls). Every row after that has a hand-written `$S/overrides/<id>/Witness.lean` against the probed or guessed expected type; none of those is checked, so "not accepted" above means unverified, not refused. Finished 23:09Z.
