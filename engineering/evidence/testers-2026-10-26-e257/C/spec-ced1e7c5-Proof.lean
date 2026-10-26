import Mathlib
import Nodes.«spec-ced1e7c5».Context

/-- The block step of the Chowla–Erdős method for Erdős 257. Write `f_A(m) = #{a ∈ A : a ∣ m}`
for the binary coefficients of `∑_{a ∈ A} 1/(2^a - 1)` (`Opn.erdos_257_lambert_identity`) and
`T_j = ∑_{i ≥ 1} f_A(j+i)/2^i` for the tail after position `j`. Suppose the sum is the rational
`p/q`. If the weighted block sum `∑_{i=1}^{k} f_A(y+i) 2^(k-i)` of the `k` coefficients after
position `y` is divisible by `2^k` (as it is when every `f_A(y+i)` is divisible by `2^k`, or
when they all vanish), then `q · T_{y+k}` is an integer multiple of `2^k`. Since `q · T_y` is an
integer (`Opn.erdos_257_lambert_tail_integral`) and `T_y = ∑_{i=1}^k f_A(y+i)/2^i + 2^{-k}
T_{y+k}`, the divisibility makes the finite part an integer too. For infinite `A` the tail
`T_{y+k}` is positive, so the multiple is at least `1` and `q · T_{y+k} ≥ 2^k`: this is the
inequality the Chinese-remainder proofs contradict, Erdős 1948 (`f_ℕ = d`, each coefficient
divisible by `2^k`) and Erdős 1968 (pairwise coprime `A`: extra elements dividing `y+k` are
added until the block sum is divisible) by choosing `y` so that the tail after the block is
small on average. In Lean `2^(k-(i+1))` is a natural-number power with `i < k`, so the
subtraction is exact. -/
theorem Opn.erdos_257_block_divisibility :
    ∀ (A : Set ℕ) (p : ℤ) (q : ℕ), 0 < q →
    ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) = p / q →
    ∀ y k : ℕ,
      2 ^ k ∣ ∑ i ∈ Finset.range k, Set.ncard {a ∈ A | a ∣ y + i + 1} * 2 ^ (k - (i + 1)) →
      ∃ N : ℤ,
        (q : ℝ) * ∑' i : ℕ, (Set.ncard {a ∈ A | a ∣ y + k + i + 1} : ℝ) / 2 ^ (i + 1) =
          2 ^ k * N := by
  intro A p q hq hsum y k hblock
  classical
  set F : ℕ → ℕ := fun m => Set.ncard {a ∈ A | 0 < m ∧ a ∣ m} with hF
  have hFeqN : ∀ m, 0 < m → Set.ncard {a ∈ A | a ∣ m} = F m := by
    intro m hm
    simp only [hF]
    congr 1
    ext a
    simp only [Set.mem_ofPred_eq]
    constructor
    · rintro ⟨h1, h2⟩
      exact ⟨h1, hm, h2⟩
    · rintro ⟨h1, _, h2⟩
      exact ⟨h1, h2⟩
  have hFeq : ∀ m, 0 < m → (Set.ncard {a ∈ A | a ∣ m} : ℝ) = F m := by
    intro m hm
    exact_mod_cast hFeqN m hm
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
  set T : ℕ → ℝ := fun j => ∑' i : ℕ, (F (j + i + 1) : ℝ) / 2 ^ (i + 1) with hT
  have hTsum : ∀ j, Summable (fun i : ℕ => (F (j + i + 1) : ℝ) / 2 ^ (i + 1)) := by
    intro j
    have h := ((summable_nat_add_iff (j + 1)).mpr hFs).mul_left ((2:ℝ) ^ j)
    refine h.congr (fun i => ?_)
    rw [show i + (j + 1) = j + i + 1 by ring,
      show (2:ℝ) ^ (j + i + 1) = 2 ^ j * 2 ^ (i + 1) by ring]
    field_simp
  -- the tail lemma at `y`, with its tail written as `T y`
  have hZ := Opn.erdos_257_lambert_tail_integral A p q hq hsum y
  have hTy : ∑' i : ℕ, (Set.ncard {a ∈ A | a ∣ y + i + 1} : ℝ) / 2 ^ (i + 1) = T y := by
    simp only [hT]
    apply tsum_congr
    intro i
    rw [hFeq _ (by omega)]
  rw [hTy] at hZ
  have hTyk : ∑' i : ℕ, (Set.ncard {a ∈ A | a ∣ y + k + i + 1} : ℝ) / 2 ^ (i + 1) = T (y + k) := by
    simp only [hT]
    apply tsum_congr
    intro i
    rw [hFeq _ (by omega)]
  rw [hTyk]
  -- `T y` splits at `k`
  have hsplit : T y = ∑ i ∈ Finset.range k, (F (y + i + 1) : ℝ) / 2 ^ (i + 1)
      + (1 / 2 ^ k) * T (y + k) := by
    simp only [hT]
    rw [← (hTsum y).sum_add_tsum_nat_add k]
    congr 1
    rw [← tsum_mul_left]
    apply tsum_congr
    intro i
    rw [show y + (i + k) + 1 = y + k + i + 1 by ring,
      show (2:ℝ) ^ (i + k + 1) = 2 ^ k * 2 ^ (i + 1) by ring]
    field_simp
  -- the weighted block sum is `2^k` times a natural number
  set Bsum : ℕ := ∑ i ∈ Finset.range k, F (y + i + 1) * 2 ^ (k - (i + 1)) with hBsum
  have hBeq : ∑ i ∈ Finset.range k, Set.ncard {a ∈ A | a ∣ y + i + 1} * 2 ^ (k - (i + 1)) = Bsum := by
    simp only [hBsum]
    apply Finset.sum_congr rfl
    intro i hi
    rw [hFeqN _ (by omega)]
  rw [hBeq] at hblock
  have hsumR : ∑ i ∈ Finset.range k, (F (y + i + 1) : ℝ) / 2 ^ (i + 1) = (Bsum : ℝ) / 2 ^ k := by
    simp only [hBsum]
    push_cast
    rw [Finset.sum_div]
    apply Finset.sum_congr rfl
    intro i hi
    have hi' : i + 1 ≤ k := Finset.mem_range.mp hi
    rw [pow_sub₀ _ (by norm_num) hi']
    field_simp
  obtain ⟨c, hc⟩ := hblock
  refine ⟨(p * 2 ^ y - q * ∑ m ∈ Finset.range (y + 1), (Set.ncard {a ∈ A | 0 < m ∧ a ∣ m} : ℤ) * 2 ^ (y - m))
      - q * (c : ℤ), ?_⟩
  have h2k : (2:ℝ) ^ k ≠ 0 := by positivity
  have hBdiv : (Bsum : ℝ) = 2 ^ k * (c : ℝ) := by exact_mod_cast hc
  have key : (q : ℝ) * T (y + k) =
      2 ^ k * ((q : ℝ) * T y - q * ∑ i ∈ Finset.range k, (F (y + i + 1) : ℝ) / 2 ^ (i + 1)) := by
    rw [hsplit]
    field_simp
    ring
  rw [key, hZ, hsumR, hBdiv]
  push_cast
  field_simp
