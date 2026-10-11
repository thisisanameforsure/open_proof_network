import Mathlib
import Nodes.«spec-7f0efe19».Context

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): prescribed lower bounds for `ω` on a window of
consecutive integers. For every length `k` and every choice of lower bounds `c 0, …, c (k-1)`
there is `N` with `c j ≤ ω (N + 1 + j)` for each `j < k`: give each slot its own set of distinct
primes and solve the congruences by the Chinese remainder theorem. Rationality of
`∑ ω(n)/2^n` would make every tail `∑_{j ≥ 0} ω(N+1+j)/2^(j+1)` lie in a fixed lattice
`(1/b)ℤ`, and arguments against that (the literature route is Tao–Teräväinen, arXiv:2512.01739)
need windows whose `ω` values are controlled. This lemma is only the elementary, lower-bound
half of that control; the upper bounds, the hard part, are not here. -/

theorem Opn.erdos_69_omega_window :
    ∀ (k : ℕ) (c : ℕ → ℕ), ∃ N : ℕ, ∀ j < k, c j ≤ ω (N + 1 + j) := by
  intro k c
  -- one distinct prime `q (j, i)` for each slot `j < k` and each `i < c j`
  let q : ℕ × ℕ → ℕ := fun x => Nat.nth Nat.Prime (Nat.pair x.1 x.2)
  have hqp : ∀ x, (q x).Prime := fun x => Nat.prime_nth_prime _
  have hqinj : Function.Injective q := by
    intro x y h
    have h1 : Nat.pair x.1 x.2 = Nat.pair y.1 y.2 :=
      Nat.nth_injective Nat.infinite_setOfPred_prime h
    obtain ⟨h2, h3⟩ := Nat.pair_eq_pair.1 h1
    exact Prod.ext h2 h3
  let t : Finset (ℕ × ℕ) :=
    ((Finset.range k) ×ˢ (Finset.range ((Finset.range k).sup c))).filter (fun x => x.2 < c x.1)
  have hmem : ∀ j i, j < k → i < c j → (j, i) ∈ t := by
    intro j i hj hi
    simp only [t, Finset.mem_filter, Finset.mem_product, Finset.mem_range]
    refine ⟨⟨hj, lt_of_lt_of_le hi ?_⟩, hi⟩
    exact Finset.le_sup (f := c) (Finset.mem_range.2 hj)
  have ht : ∀ x ∈ t, x.1 < k := by
    intro x hx
    simp only [t, Finset.mem_filter, Finset.mem_product, Finset.mem_range] at hx
    exact hx.1.1
  have hq0 : ∀ x ∈ t, q x ≠ 0 := fun x _ => (hqp x).ne_zero
  have hcop : (↑t : Set (ℕ × ℕ)).Pairwise (Function.onFun Nat.Coprime q) := by
    intro x _ y _ hxy
    exact (Nat.coprime_primes (hqp x) (hqp y)).2 (hqinj.ne hxy)
  let a : ℕ × ℕ → ℕ := fun x => (k + 1) * q x - (1 + x.1)
  obtain ⟨N, hN⟩ := Nat.chineseRemainderOfFinset a q t hq0 hcop
  refine ⟨N, fun j hj => ?_⟩
  have hdvd : ∀ i < c j, q (j, i) ∣ N + 1 + j := by
    intro i hi
    have hx := hmem j i hj hi
    have h1 : N ≡ a (j, i) [MOD q (j, i)] := hN _ hx
    have h2 : 1 + j ≤ (k + 1) * q (j, i) := by
      have : 2 ≤ q (j, i) := (hqp _).two_le
      nlinarith
    have h3 : N + (1 + j) ≡ (k + 1) * q (j, i) [MOD q (j, i)] := by
      have := h1.add_right (1 + j)
      simpa [a, Nat.sub_add_cancel h2] using this
    have h4 : (k + 1) * q (j, i) ≡ 0 [MOD q (j, i)] :=
      (Nat.modEq_zero_iff_dvd).2 (dvd_mul_left _ _)
    have h5 := (Nat.modEq_zero_iff_dvd).1 (h3.trans h4)
    simpa [add_assoc] using h5
  have hω : ω (N + 1 + j) = (N + 1 + j).primeFactors.card := by
    rw [ArithmeticFunction.cardDistinctFactors_apply, Nat.primeFactors, List.card_toFinset]
  rw [hω]
  have hcard := Finset.card_le_card_of_injOn (s := Finset.range (c j))
    (t := (N + 1 + j).primeFactors) (fun i => q (j, i)) ?_ ?_
  · simpa using hcard
  · intro i hi
    have hi' : i < c j := Finset.mem_range.1 hi
    exact Nat.mem_primeFactors.2 ⟨hqp _, hdvd i hi', by omega⟩
  · intro i _ i' _ h
    have := hqinj h
    simpa using this
