# Lane 3 witness pass (2026-11-22 22:57Z – 23:15Z)

Counts: 2 ACCEPTED · 0 probe limit · 29 written unchecked · 4 not accepted (no file) · 0 not attempted.

**Checker exhausted after row 2.** The keyless route answered `anon-check: limit of 200 per 86400s reached` from ~23:00Z (re-probed 23:04Z and 23:10Z; the coordinator confirmed it will not lift during the run). Every row from `conjecture-one` on was written by hand against the statement's binders in the checker's closure grammar observed on rows 1–4 (data binders become `∃`, Prop binders an `∧` chain in binder order) and is **unverified**; "written unchecked" means the file exists at `$S/overrides/<id>/Witness.lean` with no `sorry`, and the gate's admission judges it. No file carries `sorry`, `admit`, `set_option` or a helper declaration.

| id | verdict | attempts | expected type | note |
|---|---|---|---|---|
| balanced-primes-order | ACCEPTED | 1 | `∃ (k : ℕ), k > (0 : ℕ)` | k = 1 |
| beaver-math-olympiad-problem-5 | ACCEPTED | 1 | `∃ (a b f : ℕ → ℕ), f = fun x => 10 * 2 ^ x - 1 ∧ a 0 = 0 ∧ b 0 = 5 ∧ (∀ n, a (n+1) = if …) ∧ ∀ n, b (n+1) = if …` | a, b by `Nat.rec` on the pair from (0, 5); `change` + `split_ifs <;> rfl` |
| cardinal-mk-le-continuum-of-weakly-first-countable-of-countable-souslin-number | written unchecked (statement broken) | 1 dummy + hand | checker: `∃ (x : Sort u_1) (WeaklyFirstCountableTopology : x) … (a : sorry) (a : sorry), T35Space X`; derived: `∃ (X : Type) (_ : TopologicalSpace X), T35Space X ∧ WeaklyFirstCountableTopology X ∧ HasCountableSouslinNumber X` | `WeaklyFirstCountableTopology`, `HasCountableSouslinNumber` are defined by no ported module (no defs/), so the statement itself does not elaborate; witness is `Unit` with `inferInstance` |
| conj-class-sizes-iff-sym-three | written unchecked (statement broken) | 1 dummy + hand | checker: `∃ (x : Sort u_1) (HasDistinctConjClassSizes : x) (G : Type) (inst : Group G) (inst : Fintype G) (h : sorry), Nontrivial G`; derived: `∃ (G : Type) (_ : Group G) (_ : Fintype G) (_ : Nontrivial G), HasDistinctConjClassSizes (G := G)` | `HasDistinctConjClassSizes` undefined (no defs/); witness is S₃ = `Equiv.Perm (Fin 3)` with `decide` for the predicate |
| conjecture-one | written unchecked | 1 dummy + hand | `∃ (n : ℕ) (x : Fin n → Point), Function.Injective x` (printed by the checker; the inlined defs failed on their own lemmas, the known probe limit) | n = 0, `Fin.elim0`, `fun i => i.elim0`; `Point` written as `AtiyahSutcliffe.Point` |
| dean-conjecture | written unchecked | hand | `∃ (k : ℕ) (V : Type) (_ : Fintype V) (_ : DecidableEq V) (G : SimpleGraph V) (_ : DecidableRel G.Adj), 3 ≤ k ∧ k ≤ G.minDegree` | k = 3, K₄ on `Fin 4`; `le_minDegree_of_forall_le_degree` + `complete_graph_degree` |
| eisenbud-green-harris | not accepted (no file) | 0 | unknowable | statement has free `n`, `k` (the registry's `variable` lines were not carried; `MvPolynomial (Fin n) k` needs a `CommSemiring k` the auto-bound `k` lacks), so neither the statement nor the closure elaborates |
| erdos-1087 | written unchecked | hand | `∃ (ε : ℝ), ε > (0 : ℝ)` | ε = 1 |
| erdos-1175 | written unchecked | hand | `∃ (κ : Cardinal), ℵ₀ < κ` | κ = 𝔠, `Cardinal.aleph0_lt_continuum` |
| erdos-145 | written unchecked | hand | `∃ (α : ℝ), α ≥ (0 : ℝ)` | α = 0 |
| erdos-243 | not accepted (no file) | 0 | `∃ (a : ℕ → ℕ), StrictMono a ∧ Tendsto (fun n ↦ (a n : ℝ) / a (n - 1) ^ 2) atTop (𝓝 1) ∧ Summable ((1 : ℚ) / a ·)` | real mathematics: `Summable` in ℚ needs a rational limit, so a = 2^(2^n) fails (its reciprocal sum is irrational); Sylvester's sequence (2, 3, 7, 43, …; sum 1) works but needs the telescoping identity, a → ∞, and a ℚ-valued `HasSum` from range partial sums (no Mathlib lemma off ℝ); beyond the budget without a checker |
| erdos-323 | written unchecked | hand | `∃ (k : ℕ) (ε : ℝ), k ≥ 1 ∧ ε > (0 : ℝ)` (order guessed) | k = 1, ε = 1 |
| erdos-414 | written unchecked | hand | `∃ (m n : ℕ), m > 0 ∧ n > 0` | m = n = 1 |
| erdos-50 | not accepted (no file) | 0 | `∃ (f : ℝ → ℝ), IsDistributionOfPhiRatio f` | the hypothesis is `∀ c ∈ Icc 0 1, {n | φ n < c n}.HasDensity (f c)`, i.e. the existence of the distribution function of φ(n)/n (Schoenberg 1928); not provable in 20 s and not writable without `sorry` |
| erdos-566 | written unchecked | hand | `∃ (p : ℕ) (G : SimpleGraph (Fin p)), ∀ S : Finset (Fin p), 2 ≤ S.card → (G.induce S).edgeSet.ncard ≤ 2 * S.card - 3` | p = 0, G = ⊥; vacuous via `Finset.card_le_univ`, `Fintype.card_fin`, `omega` |
| erdos-640 | written unchecked | hand | `∃ (k : ℕ), 3 ≤ k` | k = 3 |
| erdos-701 | written unchecked | hand | `∃ (X : Type) (_ : Nonempty X) (_ : Fintype X) (F : Set (Set X)), IsLowerSet F` | `Unit`, F = ∅, `isLowerSet_empty` |
| erdos-773 | written unchecked | hand | `∃ (ε : ℝ), ε > (0 : ℝ)` | ε = 1 |
| erdos-881 | written unchecked | hand | `∃ (k : ℕ) (A : Set ℕ), IsMinimalAsymptoticAddBasisOfOrder k A` | k = 1, A = `Set.univ`: an order-1 basis is a cofinite set, and removing an infinite B leaves Bᶜ, not cofinite; the proof unfolds Mathlib's `Set.IsAsymptoticAddBasisOfOrder` by simp (shape of that definition guessed: eventually-cofinite membership in `k • A`) |
| erdos-940 | written unchecked | hand | `∃ (r : ℕ), r ≥ 3` | r = 3 |
| exists-is-small-cohen-macaulay | written unchecked (statement broken) | hand | derived guess: `∃ (R : Type) (_ : CommRing R) (_ : IsLocalRing R), IsAdicComplete (IsLocalRing.maximalIdeal R) R` | statement has free `R`, `u` (registry `variable` lines not carried), so the closure's shape is unknowable; witness is ℚ with `maximalIdeal_eq_bot` and the ⊥-adic completeness instance |
| four-exponentials-conjecture | written unchecked | hand | `∃ (x y : Fin 2 → ℂ), LinearIndependent ℚ x ∧ LinearIndependent ℚ y` | x = y = `![1, I]` via `LinearIndependent.pair_iff`, real and imaginary parts |
| green-28 | written unchecked | hand | `∃ (X Y : PMF ℤ), X.support.Finite ∧ Y.support.Finite ∧ IsUniformOnSupport (indepSum X Y)` | X = Y = `PMF.pure 0`; `indepSum` reduces by `pure_bind` to `pure 0`, uniform on `{0}` by `PMF.ext` + simp |
| grimm-conjecture | written unchecked | hand | `∃ (n k : ℕ), 1 ≤ n ∧ 1 ≤ k ∧ ∀ i : Fin k, (n + i).Composite` | n = 4, k = 1, `fin_cases i; decide` (assumes `Nat.Composite` is Mathlib's and decidable) |
| infinite-is-wall-sun-sun-prime-of-disc-eq | not accepted (no file) | 0 | `∃ (K : Type*) (_ : Field K) (_ : NumberField K) (_ : IsQuadraticExtension ℚ K) (_ : IsTotallyReal K) (D : ℤ), discr K = D` | needs a concrete real quadratic number field (e.g. ℚ(√5)) with `NumberField`, `IsQuadraticExtension` and `IsTotallyReal` instances; no instance path known with confidence without a checker |
| is-mirimanoff-prime-iff | written unchecked (statement broken) | hand | `∃ (p : ℕ), True` (guessed) | p = 11; `IsMirimanoffPrime` is **not defined** in the ported `NumberTheoryWieferichPrime.lean` (prose only), so the statement does not elaborate |
| kummer-vandiver | written unchecked | hand | `∃ (p : ℕ+), p.Prime` | p = 2, `Nat.prime_two` by defeq of `PNat.Prime` |
| lemoine-conjecture-extension | written unchecked | hand | `∃ (n : ℕ), 8 < n ∧ Odd n` | n = 9 |
| manickam-miklos-singhi-conjecture | written unchecked | hand | `∃ (n k : ℕ) (x : Fin n → ℝ), 1 ≤ k ∧ 4 * k ≤ n ∧ ∑ i, x i = 0` | n = 4, k = 1, x = 0 |
| odd-order-latin-square-transversal | written unchecked | hand | `∃ (n : ℕ) (L : LatinSquare n), Odd n` | n = 1, the one-cell square (`Subsingleton.elim` for both injectivities), `odd_one` |
| pillais-conjecture | written unchecked | hand | `∃ (a b c : ℕ), 0 < a ∧ 0 < b ∧ 0 < c` | a = b = c = 1 |
| reconstruction-conjecture | written unchecked (statement broken) | hand | `∃ (V W : Type) (_ : Fintype V) (_ : Fintype W) (G : SimpleGraph V) (H : SimpleGraph W), 3 ≤ Fintype.card V ∧ Hypomorphic G H` | `Hypomorphic` undefined (no defs/); witness is two empty graphs on `Fin 3` with the identity and `Iso.refl` — its unfolding of `Hypomorphic` is a guess |
| scholz-conjecture | written unchecked (statement broken) | hand | `∃ (n : ℕ), 0 < n` | n = 1; the statement's `ℓ(·)` notation is undefined (no defs/) |
| tournament-anti-sidorenko-trees-conjecture-tournamenton | written unchecked | hand | `∃ (V : Type*) (_ : Fintype V) (_ : DecidableEq V) (T : SimpleGraph V) (_ : DecidableRel T.Adj), T.IsTree` | `Fin 1` with ⊥: connected by `Subsingleton.elim ▸ Reachable.refl`, `isAcyclic_bot` |
| variant-theta | written unchecked | hand | `∃ (θ : ℝ), 0 < θ ∧ θ ≤ 1/2` | θ = 1/2 |

Statements found broken on reading (no witness can be admitted until the draft is fixed): cardinal-mk-…, conj-class-sizes-iff-sym-three, reconstruction-conjecture, scholz-conjecture (undefined identifiers, no defs/ ported); is-mirimanoff-prime-iff (the ported module carries the definition only as prose); eisenbud-green-harris and exists-is-small-cohen-macaulay (the registry's `variable` binders were not carried into the statement).
