import Mathlib

theorem Opn.erdos_257_lambert_identity :
    ∀ (A : Set ℕ),
    ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) =
      ∑' m : ℕ, (Set.ncard {a ∈ A | 0 < m ∧ a ∣ m} : ℝ) / 2 ^ m := by
  sorry

/-- The zero-block criterion for Erdős 257, the digit-side counterpart of the Liouville
criterion `Opn.erdos_257_liouville_criterion`. Write `f_A(m) = #{a ∈ A : a ∣ m}` for the
coefficients of the binary expansion `∑_{a ∈ A} 1/(2^a - 1) = ∑_{m ≥ 1} f_A(m)/2^m`
(`Opn.erdos_257_lambert_identity`), and `T_j = ∑_{i ≥ 1} f_A(j+i)/2^i` for its tail after
position `j`, rescaled so that `T_j` is what the digits after `j` are worth. If `A` is infinite
and the tails `T_j` come arbitrarily close to `0`, then `∑_{a ∈ A} 1/(2^a - 1)` is irrational.
Proof: if the sum were `p/q` then `q · T_j` would be an integer for every `j`, and positive
because some element of `A` exceeds `j`, so every `T_j ≥ 1/q`. A tail is small when the
coefficients `f_A(j+1), …, f_A(j+k)` all vanish for a long block (a *zero block*: no element of
`A` divides any of `j+1, …, j+k`) and the later coefficients are not too large; the
Chinese-remainder arguments of Erdős (1968) and Duverney–Tachiya (2019) produce exactly such
blocks. (Erdős's 1948 proof for `A = ℕ` has no zero blocks, since `f_ℕ = d ≥ 1`; it uses
divisibility of the coefficients instead.) -/
theorem Opn.erdos_257_zero_block_criterion :
    ∀ (A : Set ℕ), A.Infinite →
    (∀ ε : ℝ, 0 < ε → ∃ j : ℕ,
      ∑' i : ℕ, (Set.ncard {a ∈ A | a ∣ j + i + 1} : ℝ) / 2 ^ (i + 1) < ε) →
    Irrational (∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1)) := by
  intro A hA hsmall
  classical
  set F : ℕ → ℕ := fun m => Set.ncard {a ∈ A | 0 < m ∧ a ∣ m} with hF
  have hFin : ∀ m, 0 < m → {a ∈ A | 0 < m ∧ a ∣ m}.Finite := by
    intro m hm
    refine (Finset.finite_toSet (Nat.divisors m)).subset ?_
    intro a ha
    simp only [Finset.mem_coe, Nat.mem_divisors]
    exact ⟨ha.2.2, hm.ne'⟩
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
  have hlam : ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) = ∑' m : ℕ, (F m : ℝ) / 2 ^ m :=
    Opn.erdos_257_lambert_identity A
  rw [hlam]
  rintro ⟨q, hq⟩
  -- the tail after position `j`: `q.den` times it is an integer, and it is positive
  set tail : ℕ → ℝ := fun j => ∑' i : ℕ, (F (j + i + 1) : ℝ) / 2 ^ (i + 1) with htaildef
  have hb : (0 : ℝ) < q.den := by exact_mod_cast q.den_pos
  have hqab : (q : ℝ) = (q.num : ℝ) / (q.den : ℝ) := Rat.cast_def q
  have htail_int : ∀ j, ∃ z : ℤ, (q.den : ℝ) * tail j = z := by
    intro j
    have hsplit := hFs.sum_add_tsum_nat_add (j + 1)
    have hshift : ∑' i : ℕ, (F (i + (j + 1)) : ℝ) / 2 ^ (i + (j + 1)) = (1 / 2 ^ j) * tail j := by
      simp only [htaildef]
      rw [← tsum_mul_left]
      apply tsum_congr
      intro i
      rw [show i + (j + 1) = j + i + 1 by ring,
        show (2:ℝ) ^ (j + i + 1) = 2 ^ j * 2 ^ (i + 1) by ring]
      field_simp
    rw [hshift, ← hq, hqab] at hsplit
    refine ⟨q.num * 2 ^ j - q.den * ∑ n ∈ Finset.range (j + 1), (F n : ℤ) * 2 ^ (j - n), ?_⟩
    have hb' : (q.den : ℝ) ≠ 0 := hb.ne'
    have h2j : (2:ℝ) ^ j ≠ 0 := by positivity
    have hT : (q.den : ℝ) * tail j =
        2 ^ j * (q.num - q.den * ∑ n ∈ Finset.range (j + 1), (F n : ℝ) / 2 ^ n) := by
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
  have htail_pos : ∀ j, 0 < tail j := by
    intro j
    obtain ⟨a0, ha0A, ha0j⟩ := hA.exists_gt j
    have hsum_tail : Summable (fun i : ℕ => (F (j + i + 1) : ℝ) / 2 ^ (i + 1)) := by
      have h := ((summable_nat_add_iff (j + 1)).mpr hFs).mul_left ((2:ℝ) ^ j)
      refine h.congr (fun i => ?_)
      rw [show i + (j + 1) = j + i + 1 by ring,
        show (2:ℝ) ^ (j + i + 1) = 2 ^ j * 2 ^ (i + 1) by ring]
      field_simp
    show 0 < ∑' i : ℕ, (F (j + i + 1) : ℝ) / 2 ^ (i + 1)
    refine hsum_tail.tsum_pos (fun i => by positivity) (a0 - j - 1) ?_
    have hidx : j + (a0 - j - 1) + 1 = a0 := by omega
    rw [hidx]
    have hpos : 0 < F a0 := by
      simp only [hF]
      rw [Set.ncard_pos (hFin a0 (by omega))]
      exact ⟨a0, ha0A, by omega, dvd_refl a0⟩
    have hpos' : (0:ℝ) < F a0 := by exact_mod_cast hpos
    exact div_pos hpos' (by positivity)
  -- hence every tail is at least `1 / q.den`
  have hge : ∀ j, (1 : ℝ) / q.den ≤ tail j := by
    intro j
    obtain ⟨z, hz⟩ := htail_int j
    have hzpos : (0:ℝ) < z := by
      rw [← hz]
      exact mul_pos hb (htail_pos j)
    have hz1 : (1 : ℤ) ≤ z := by exact_mod_cast hzpos
    have hz1' : (1 : ℝ) ≤ z := by exact_mod_cast hz1
    rw [div_le_iff₀ hb, mul_comm, hz]
    exact hz1'
  obtain ⟨j, hj⟩ := hsmall (1 / q.den) (by positivity)
  have hjeq : ∑' i : ℕ, (Set.ncard {a ∈ A | a ∣ j + i + 1} : ℝ) / 2 ^ (i + 1) = tail j := by
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
  rw [hjeq] at hj
  exact absurd (hge j) (not_le.mpr hj)
