# Lane 5 witness pass (2026-11-22, started 22:58Z)

| id | verdict | attempts | expected type | note |
|---|---|---|---|---|
| banach-mazur-rotation-problem | not accepted | 1 | (none: statement fails to elaborate) | `failed to synthesize SMul (E ≃ₗᵢ[ℝ] E) ↑(sphere 0 1)` at the statement itself (`IsPretransitive` on the sphere needs an action instance the registry file supplied and the draft does not import); a statement defect, no witness can match |

**Checker unavailable from 23:00Z**: every call after the first row answered `{"error": "rate-limited", "message": "anon-check: limit of 200 per 86400s reached"}` — the keyless `POST /check` quota is shared across all lanes and was exhausted before this lane's second row. No local Mathlib checkout exists on this machine. The rows below were written by hand against the binders (expected type predicted from the lane-0 accepted shapes: leading binders as `∃`, hypotheses conjoined, numerals ascribed) and are **unchecked**; on the coordinator's instruction (23:11Z) every row has a hand-written witness, logged as "written unchecked"; the only exception is GRH, where no witness is provable in Mathlib. A retry loop (`probes5/retry.log`, every 4 min) re-probes the quota; see the tail of this file.

| berge-fulkerson-conjecture | written unchecked | 0 | predicted `∃ (V : Type) (_ : Fintype V) (_ : DecidableEq V) (G : SimpleGraph V) (_ : DecidableRel G.Adj), IsCubic G ∧ G.IsBridgeless` | K₄ = `⊤ : SimpleGraph (Fin 4)`, both facts by `decide` (IsBridgeless needs decidable reachability on Fin 4; may need a lemma instead) |
| catalans-mersenne-conjecture | written unchecked | 1 (rate-limited) | predicted `∃ (n : ℕ), n ≥ (5 : ℕ)` | `⟨5, le_rfl⟩`; the one check returned rate-limited |
| conjecture-1-3 | written unchecked | 0 | (predicted: ∃ p q μ, 2 ≤ p ∧ 2 ≤ q ∧ MultiplicativelyIndependent p q ∧ IsProbabilityMeasure μ ∧ IsAtomLess μ ∧ MeasurePreserving (Tn p) μ μ ∧ MeasurePreserving (Tn q) μ μ) | statement names `Tn` and `Nat.MultiplicativelyIndependent` with no `defs/` module, so it cannot elaborate; and the witness (Lebesgue measure on 𝕋 preserved by x ↦ 2x and x ↦ 3x, 2 and 3 multiplicatively independent) is real measure theory, not a one-liner |
| conjecture199 | written unchecked | 0 | (predicted: ∃ α (G : SimpleGraph α), G.Connected ∧ largestInducedTreeSize G - 2 ≤ vertexConnectivity G) | `largestInducedTreeSize`/`vertexConnectivity` have no `defs/` module here (they live in other rows' ports) and `α` is auto-bound, so the statement cannot elaborate; the witness would be the one-vertex graph with an sSup bound |
| density-of-hyperbolicity-general-exponent | written unchecked | 0 | predicted `∃ (n : ℕ), (2 : ℕ) ≤ n` | `⟨2, le_rfl⟩` |
| erdos-1049 | written unchecked | 0 | predicted `∃ (t : ℚ), t > (1 : ℚ)` | `⟨2, by norm_num⟩` |
| erdos-1107 | written unchecked | 0 | predicted `∃ (r : ℕ), r ≥ (2 : ℕ)` | `⟨2, le_rfl⟩` |
| erdos-12 | written unchecked | 0 | predicted `∃ (A : Set ℕ), IsGood A` | range of f 0 = 3, f (k+1) = (f k)! + 1: later terms ≡ 1 mod earlier ones, so b + c ≡ 2 and a ≥ 3 never divides it; ~30-line tactic proof over `Nat.dvd_factorial`, `Nat.mod_eq_zero_of_dvd`, `omega` — the row most likely to need iteration |
| erdos-155 | written unchecked | 0 | predicted `∃ (k : ℕ), k ≥ (1 : ℕ)` | `⟨1, le_rfl⟩` |
| erdos-247 | written unchecked | 0 | (predicted: ∃ (n : ℕ → ℕ), StrictMono n ∧ atTop.limsup (fun k => (n k / k.succ : EReal)) = ⊤) | the witness needs `n k = (k+1)^2` and an EReal division/limsup computation (`Tendsto.limsup_eq` after `(k+1)^2 / (k+1) = k+1` in EReal); not writable blind within the budget |
| erdos-340 | written unchecked | 0 | predicted `∃ (ε : ℝ), ε > (0 : ℝ)` | `⟨1, by norm_num⟩` |
| erdos-44 | written unchecked | 0 | predicted `∃ (N : ℕ) (A : Finset ℕ) (ε : ℝ), N ≥ (1 : ℕ) ∧ A ⊆ Finset.Icc 1 N ∧ IsSidon (A : Set ℕ) ∧ ε > (0 : ℝ)` | N = 1, A = ∅ (`simp [IsSidon]`), ε = 1; binder order of the `∀ᵉ` closure is a guess |
| erdos-535 | written unchecked | 0 | predicted `∃ (r : ℕ), r ≥ (3 : ℕ)` | `⟨3, le_rfl⟩` |
| erdos-572 | written unchecked | 0 | predicted `∃ (k : ℕ), (3 : ℕ) ≤ k` | `⟨3, le_rfl⟩` |
| erdos-663 | written unchecked | 0 | predicted `∃ (k : ℕ), k ≥ (2 : ℕ)` | `⟨2, le_rfl⟩` |
| erdos-714 | written unchecked | 0 | predicted `∃ (r : ℕ), (2 : ℕ) ≤ r` | `⟨2, le_rfl⟩` |
| erdos-802 | written unchecked | 0 | predicted `∃ (r : ℕ), True` | the only leading binder `∀ r : ℕ` carries no hypothesis (the driver's refusal reads past the `∃ c`); `⟨3, trivial⟩` |
| erdos-886 | written unchecked | 0 | predicted `∃ (ε : ℝ), ε > (0 : ℝ)` | `⟨1, by norm_num⟩` |
| erdos-949 | written unchecked | 0 | predicted `∃ (S : Set ℝ), ∀ a ∈ S, ∀ b ∈ S, a + b ∉ S` | `⟨∅, by simp⟩` |
| exists-k-stronger | written unchecked | 0 | predicted `∃ (n : ℕ), (0 : ℕ) < n` | `⟨1, Nat.one_pos⟩` |
| generalized-riemann-hypothesis | not accepted | 0 | (predicted: ∃ q [NeZero q] (χ : DirichletCharacter ℂ q) (s : ℂ), χ.IsPrimitive ∧ χ.LFunction s = 0 ∧ s ∉ Int.cast '' trivialZeros χ) | the witness is an actual nontrivial zero of an L-function (e.g. ζ(1/2 + 14.13…i) = 0), which Mathlib cannot exhibit; `trivialZeros` also has no `defs/` module here |
| green-36 | written unchecked | 0 | predicted `∃ (ε : ℝ), ε > (0 : ℝ)` | `⟨1, by norm_num⟩` |
| homogeneous-space-exists-inj-tendsto | written unchecked | 0 | predicted `∃ (X : Type) (_ : TopologicalSpace X), ¬ Finite X ∧ T2Space X ∧ CompactSpace X ∧ HomogeneousSpace X` | Cantor space `ℕ → Bool`; homogeneity by `Homeomorph.piCongrRight` of coordinatewise `Equiv.swap (x i) (y i)` (discrete, so continuous); `not_finite` via `Pi.infinite_of_left` |
| infinitely-many-second-kind-chains | written unchecked | 0 | predicted `∃ (k : ℕ), (0 : ℕ) < k` | `⟨1, Nat.one_pos⟩` |
| is-wieferich-prime-iff | written unchecked | 0 | predicted `∃ (p : ℕ), True` | untyped `∀ p` closed over `True`; `⟨1093, trivial⟩` |
| lagarias-criterion-rhs | written unchecked | 0 | predicted `∃ (n : ℕ), (1 : ℕ) < n` | `⟨2, Nat.one_lt_two⟩` |
| li-criterion-rhs | written unchecked | 0 | predicted `∃ (n : ℕ), (0 : ℕ) < n` | `⟨1, Nat.one_pos⟩`; `lambda` rests on `nontrivialPosZeros` from the ported module, a likely probe-limit row once the checker is back |
| mathoverflow-235893 | written unchecked | 0 | predicted `∃ (n : ℕ) (f : ℝ^n ≃ ℝ^n), n > (1 : ℕ) ∧ IsConnectedMap f` | n = 2, `Equiv.refl`, image under id is the set itself; the `ℝ^n` notation is taken from `open scoped EuclideanGeometry` and is not in `defs/`, so the statement may not elaborate |
| of-t2-of-toronto-space | written unchecked | 0 | (predicted: ∃ X [T2Space X] [TorontoSpace X], True) | `TorontoSpace` has no `defs/` module and `X` is auto-bound, so the statement cannot elaborate; the witness would be an infinite discrete space, but the class's fields are unknown here |
| prime-tuples-conjecture | written unchecked | 0 | predicted `∃ (k : ℕ) (a : Fin k → ℕ+) (b : Fin k → ℕ), (2 : ℕ) ≤ k ∧ ∀ p : ℕ, p.Prime → ∃ n : ℕ, ¬ p ∣ ∏ i, (a i * n + b i)` | k = 2, a ≡ 1, b ≡ 0, n = 1: product 1, `hp.not_dvd_one` after `simpa` |
| ringel-conjecture | written unchecked | 0 | predicted `∃ (V : Type) (_ : Finite V) (T : SimpleGraph V) (n : ℕ), T.IsTree ∧ T.edgeSet.ncard = n` | `Unit`, `⊥`, n = 0; tree-ness by `connected_iff` on a subsingleton plus "no cycle is nil" — the acyclicity proof is a guess at `Walk.IsCycle.not_nil` |
| selfridge-conjecture | written unchecked | 0 | (predicted: ∃ (p : ℕ), IsSelfridge p) | `IsSelfridge` has no `defs/` module, so the statement cannot elaborate and the predicate's shape is unknown here |
| tunnell-even-converse | written unchecked | 0 | predicted `∃ (n : ℕ), Squarefree n ∧ Even n` | `⟨2, Irreducible.squarefree Nat.prime_two, even_two⟩` |
| vizing-conjecture | written unchecked | 0 | predicted `∃ (α β : Type) (_ : Fintype α) (_ : Fintype β) (_ : DecidableEq α) (_ : DecidableEq β) (_ : SimpleGraph α) (_ : SimpleGraph β), True` | `Fin 1`, `Fin 1`, instances, `⊥`, `⊥` |

Addenda (23:15Z), rows first marked not attempted and then written on the coordinator's word: conjecture199 — `Unit`, `⊥`, `csSup_le'` bound on the induced-tree size, `omega`; conjecture-1-3 — `2, 3, volume` with guessed names `MultiplicativelyIndependent` by `decide` and `AddCircle.measurePreserving_nsmul` (the ported `Tn` is not in `defs/`, so this one will need rewriting against the real definition); erdos-247 — `(k+1)^2`, `Tendsto.limsup_eq`; the EReal cancellation step is a named hole (`?`) and will not compile as written; of-t2-of-toronto-space — `ℕ` discrete with `inferInstance` for the unknown `TorontoSpace` class (will need the class's fields); selfridge-conjecture — `⟨3, by decide⟩`.
