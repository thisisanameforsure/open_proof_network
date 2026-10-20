import Mathlib
import Nodes.«spec-a70fcca4».Context

/-- The natural counterexample candidate for Erdős 257, stated so that it can be proved or
refuted: `1/2` is the Mersenne reciprocal sum of some infinite set. A finite set cannot give
`1/2` (finite sums have odd denominators), so any representation of `1/2` is infinite, and a
proof of this statement refutes the root. The greedy walk for `1/2` (the only possible
representation) begins 2, 3, 6, 7, 14, 20, 21, 26, 27, 32, ... and has been run without stalling
to depth 2500 here and to depth 10^8 by Hong (Zenodo 23287959, 2026, unrefereed); Kovač
(erdosproblems.com/257, Aug 2025) expects the subset-sum set, a fat Cantor set, to contain
such rationals. No proof in either direction is known. -/
theorem Opn.erdos_257_half_is_a_subsum :
    ∃ A : Set ℕ, A.Infinite ∧ ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) = 1 / 2 := by
  -- approach: the greedy walk for 1/2 (take 1/(2^m-1) whenever it fits under the remainder r m); the bookkeeping is three provable holes and the open mathematics is one hole, that the walk never stalls
  -- licence: CC-BY-4.0
  -- The greedy remainder r : ℕ → ℝ has r 0 = 1/2, and position m is taken iff its term fits
  -- under r m. (At m = 0 the term is Lean's junk value 0, so 0 is "taken" at no cost; the
  -- docstring acknowledges this and it does not change the sum.) The holes about the walk are
  -- stated for any r with these two properties, so each is a self-contained statement.
  -- label: greedy remainder bookkeeping
  -- claim: $0 \le r_m$ and $\sum_{a<m,\ a\in A} \frac{1}{2^a-1} = \frac12 - r_m$ for every $m$, where $A=\{a : \frac{1}{2^a-1}\le r_a\}$
  -- The remainder never goes negative (a term is subtracted only when it fits) and is exactly
  -- 1/2 minus the sum of the terms taken so far. Induction on m.
  have h1 : ∀ r : ℕ → ℝ, r 0 = 1 / 2 →
      (∀ m, r (m + 1) = if (1 : ℝ) / (2 ^ m - 1) ≤ r m then r m - 1 / (2 ^ m - 1) else r m) →
      ∀ m, 0 ≤ r m ∧
        ∑ a ∈ Finset.range m, (if (1 : ℝ) / (2 ^ a - 1) ≤ r a then (1 : ℝ) / (2 ^ a - 1) else 0)
          = 1 / 2 - r m := sorry
  -- label: no finite subsum is one half
  -- claim: $\sum_{a\in S} \frac{1}{2^a-1} \ne \frac12$ for every finite $S \subseteq \mathbb{N}$
  -- A finite sum of reciprocals of odd numbers is a rational with odd denominator (the term at
  -- a = 0 is Lean's 0), and 1/2 is not.
  have h2 : ∀ S : Finset ℕ, ∑ a ∈ S, (1 : ℝ) / (2 ^ a - 1) ≠ 1 / 2 := sorry
  -- label: the Mersenne reciprocal series converges
  -- claim: $\sum_{n\ge 0} \frac{1}{2^n-1} < \infty$
  -- (summable; the n = 0 term is Lean's 0.)
  -- Comparison with the geometric series: 1/(2^n-1) ≤ 2/2^n for n ≥ 1.
  have h3 : Summable (fun n : ℕ => (1 : ℝ) / (2 ^ n - 1)) := sorry
  -- label: the greedy walk for one half never stalls
  -- claim: $r_m \le \sum_{k\ge 0} \frac{1}{2^{k+m}-1}$ for every $m$, for the greedy remainder $r$ of $\frac12$
  -- The open mathematics. The remainder before position m never exceeds the whole tail of the
  -- series from m on, so the walk can always continue; equivalently (given the holes above) the
  -- remainder tends to 0. Verified numerically to depth 10^8 (Hong 2026), no proof known. A
  -- stall at m would be r m > tail m, after which 1/2 is not a subset sum at all.
  have h4 : ∀ r : ℕ → ℝ, r 0 = 1 / 2 →
      (∀ m, r (m + 1) = if (1 : ℝ) / (2 ^ m - 1) ≤ r m then r m - 1 / (2 ^ m - 1) else r m) →
      ∀ m, r m ≤ ∑' k : ℕ, (1 : ℝ) / (2 ^ (k + m) - 1) := sorry
  -- The walk itself, by recursion on m.
  have hex : ∃ r : ℕ → ℝ, r 0 = 1 / 2 ∧
      ∀ m, r (m + 1) = if (1 : ℝ) / (2 ^ m - 1) ≤ r m then r m - 1 / (2 ^ m - 1) else r m :=
    ⟨fun m => Nat.rec (1 / 2 : ℝ)
        (fun k rk => if (1 : ℝ) / (2 ^ k - 1) ≤ rk then rk - 1 / (2 ^ k - 1) else rk) m,
      rfl, fun _ => rfl⟩
  obtain ⟨r, hr0, hrs⟩ := hex
  replace h1 := h1 r hr0 hrs
  replace h4 := h4 r hr0 hrs
  -- The assembly. Tail of a convergent series tends to 0, so r m → 0 by the squeeze.
  have htail : Filter.Tendsto (fun m : ℕ => ∑' k : ℕ, (1 : ℝ) / (2 ^ (k + m) - 1))
      Filter.atTop (nhds 0) := tendsto_sum_nat_add (fun n : ℕ => (1 : ℝ) / (2 ^ n - 1))
  have hr : Filter.Tendsto r Filter.atTop (nhds 0) :=
    tendsto_of_tendsto_of_tendsto_of_le_of_le tendsto_const_nhds htail (fun m => (h1 m).1) h4
  -- The partial sums of the chosen terms tend to 1/2.
  set f : ℕ → ℝ := fun a => if (1 : ℝ) / (2 ^ a - 1) ≤ r a then (1 : ℝ) / (2 ^ a - 1) else 0
    with hf
  have hfnn : ∀ a, 0 ≤ f a := by
    intro a
    simp only [hf]
    split_ifs with h
    · have h2a : (1 : ℝ) ≤ 2 ^ a := one_le_pow₀ (by norm_num)
      exact div_nonneg zero_le_one (by linarith)
    · exact le_refl 0
  have hpart : Filter.Tendsto (fun m => ∑ a ∈ Finset.range m, f a) Filter.atTop (nhds (1 / 2)) := by
    have : (fun m => ∑ a ∈ Finset.range m, f a) = fun m => 1 / 2 - r m := by
      funext m; exact (h1 m).2
    rw [this]
    simpa using tendsto_const_nhds.sub hr
  have hsum : HasSum f (1 / 2) := (hasSum_iff_tendsto_nat_of_nonneg hfnn _).mpr hpart
  refine ⟨{a : ℕ | (1 : ℝ) / (2 ^ a - 1) ≤ r a}, ?_, ?_⟩
  · -- Infinite: if A were finite the walk would be constant from some M on, so r M = 0 by hr,
    -- and 1/2 would be the finite sum of the terms taken below M, against h2.
    intro hfin
    obtain ⟨M, hM⟩ := hfin.bddAbove
    have hconst : ∀ a, M + 1 ≤ a → r a = r (M + 1) := by
      intro a ha
      induction a, ha using Nat.le_induction with
      | base => rfl
      | succ a ha ih =>
        rw [hrs a, if_neg, ih]
        intro hle
        exact absurd (hM hle) (by omega)
    have hc : Filter.Tendsto r Filter.atTop (nhds (r (M + 1))) := by
      refine tendsto_const_nhds.congr' ?_
      filter_upwards [Filter.eventually_ge_atTop (M + 1)] with a ha
      exact (hconst a ha).symm
    have hzero : r (M + 1) = 0 := tendsto_nhds_unique hc hr
    have hhalf := (h1 (M + 1)).2
    rw [hzero, sub_zero] at hhalf
    apply h2 ((Finset.range (M + 1)).filter fun a => (1 : ℝ) / (2 ^ a - 1) ≤ r a)
    rw [Finset.sum_filter]
    exact hhalf
  · -- The sum over A is the sum of f.
    have hind : (Set.indicator {a : ℕ | (1 : ℝ) / (2 ^ a - 1) ≤ r a} fun n : ℕ => (1 : ℝ) / (2 ^ n - 1)) = f := by
      funext a
      simp only [Set.indicator_apply, Set.mem_setOf_eq, hf]
    refine (tsum_subtype {a : ℕ | (1 : ℝ) / (2 ^ a - 1) ≤ r a} fun n : ℕ => (1 : ℝ) / (2 ^ n - 1)).trans ?_
    rw [hind]
    exact hsum.tsum_eq
