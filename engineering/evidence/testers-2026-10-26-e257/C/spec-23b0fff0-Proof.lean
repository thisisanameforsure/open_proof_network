import Mathlib
import Nodes.«spec-23b0fff0».Context

/-- Integrality of the binary tails, the second line of every digit-method proof for Erdős 257
(Erdős 1948 and 1968, Duverney–Tachiya 2019). Write `f_A(m) = #{a ∈ A : a ∣ m}` for the
coefficients of the binary expansion `∑_{a ∈ A} 1/(2^a - 1) = ∑_{m ≥ 1} f_A(m)/2^m`
(`Opn.erdos_257_lambert_identity`) and `T_j = ∑_{i ≥ 1} f_A(j+i)/2^i` for the tail after
position `j`, scaled by `2^j`. If the sum is the rational `p/q` then, for every `j`,
`q · T_j = p · 2^j - q · ∑_{m ≤ j} f_A(m) 2^(j-m)`, an integer. Every proof of a special case
then shows that for a well-chosen `j` this integer cannot exist: it is positive whenever some
element of `A` exceeds `j` (so `T_j ≥ 1/q`), while a block of coefficients `f_A(j+1), …,
f_A(j+k)` that vanish, or are divisible by `2^k`, forces `q · T_{j+k} ≥ 2^k` against an upper
bound on that tail. In Lean `2^(j-m)` is a natural-number power with `m ≤ j`, so the subtraction
is exact, and `f_A(0) = 0` by the guard `0 < m`. -/
theorem Opn.erdos_257_lambert_tail_integral :
    ∀ (A : Set ℕ) (p : ℤ) (q : ℕ), 0 < q →
    ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) = p / q →
    ∀ j : ℕ,
      (q : ℝ) * ∑' i : ℕ, (Set.ncard {a ∈ A | a ∣ j + i + 1} : ℝ) / 2 ^ (i + 1) =
        ((p * 2 ^ j -
          q * ∑ m ∈ Finset.range (j + 1), (Set.ncard {a ∈ A | 0 < m ∧ a ∣ m} : ℤ) * 2 ^ (j - m)
          : ℤ) : ℝ) := by
  intro A p q hq hsum j
  classical
  set F : ℕ → ℕ := fun m => Set.ncard {a ∈ A | 0 < m ∧ a ∣ m} with hF
  have hF_le : ∀ m, F m ≤ m := by
    intro m
    rcases Nat.eq_zero_or_pos m with rfl | hm
    · have h0 : {a ∈ A | 0 < 0 ∧ a ∣ 0} = ∅ := by
        ext a
        simp
      simp [hF, h0]
    · have hsub : {a ∈ A | 0 < m ∧ a ∣ m} ⊆ ↑(Nat.divisors m) := by
        intro a ha
        simp only [Finset.mem_coe, Nat.mem_divisors]
        exact ⟨ha.2.2, hm.ne'⟩
      calc F m ≤ (↑(Nat.divisors m) : Set ℕ).ncard :=
            Set.ncard_le_ncard hsub (Finset.finite_toSet _)
        _ = (Nat.divisors m).card := Set.ncard_coe_finset _
        _ ≤ m := Nat.card_divisors_le_self m
  have hFs : Summable (fun m : ℕ => (F m : ℝ) / 2 ^ m) := by
    have h2 := summable_pow_mul_geometric_of_norm_lt_one 1 (r := (1/2 : ℝ))
      (by norm_num [abs_of_pos])
    refine Summable.of_nonneg_of_le (fun i => by positivity) (fun i => ?_) h2
    have : (F i : ℝ) ≤ i := by exact_mod_cast hF_le i
    rw [div_eq_mul_inv, one_div, inv_pow, pow_one]
    have : (0:ℝ) ≤ (2 ^ i)⁻¹ := by positivity
    nlinarith
  have hlam : ∑' m : ℕ, (F m : ℝ) / 2 ^ m = p / q := by
    rw [← Opn.erdos_257_lambert_identity A]
    exact hsum
  -- the tail in the statement is the tail of `F`
  set tail : ℝ := ∑' i : ℕ, (F (j + i + 1) : ℝ) / 2 ^ (i + 1) with htaildef
  have hjeq : ∑' i : ℕ, (Set.ncard {a ∈ A | a ∣ j + i + 1} : ℝ) / 2 ^ (i + 1) = tail := by
    simp only [htaildef, hF]
    apply tsum_congr
    intro i
    congr 3
    ext a
    simp only [Set.mem_ofPred_eq]
    constructor
    · rintro ⟨h1, h2⟩
      exact ⟨h1, by omega, h2⟩
    · rintro ⟨h1, _, h2⟩
      exact ⟨h1, h2⟩
  rw [hjeq]
  have hb : (0 : ℝ) < q := by exact_mod_cast hq
  have hsplit := hFs.sum_add_tsum_nat_add (j + 1)
  have hshift : ∑' i : ℕ, (F (i + (j + 1)) : ℝ) / 2 ^ (i + (j + 1)) = (1 / 2 ^ j) * tail := by
    simp only [htaildef]
    rw [← tsum_mul_left]
    apply tsum_congr
    intro i
    rw [show i + (j + 1) = j + i + 1 by ring,
      show (2:ℝ) ^ (j + i + 1) = 2 ^ j * 2 ^ (i + 1) by ring]
    field_simp
  rw [hshift, hlam] at hsplit
  have hb' : (q : ℝ) ≠ 0 := hb.ne'
  have h2j : (2:ℝ) ^ j ≠ 0 := by positivity
  have hT : (q : ℝ) * tail =
      2 ^ j * (p - q * ∑ n ∈ Finset.range (j + 1), (F n : ℝ) / 2 ^ n) := by
    field_simp at hsplit
    field_simp
    linear_combination hsplit
  rw [hT]
  push_cast
  rw [mul_sub, Finset.mul_sum, Finset.mul_sum, Finset.mul_sum]
  congr 1
  · ring
  · apply Finset.sum_congr rfl
    intro n hn
    have hn' : n ≤ j := Nat.lt_succ_iff.mp (Finset.mem_range.mp hn)
    rw [pow_sub₀ _ (by norm_num) hn']
    field_simp
    simp only [hF]
