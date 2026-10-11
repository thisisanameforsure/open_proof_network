import Mathlib

theorem crux_from_pade : ∀ (Qc : ℕ → ℕ → ℚ),
    (Qc = fun (n k : ℕ) =>
        ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
            ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
          ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) →
    ∀ (n k : ℕ), k ≤ n →
      ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) =
        (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) *
          ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ)) := by
  have hform : ∀ (Qc : ℕ → ℕ → ℚ),
    (Qc = fun (n k : ℕ) =>
        ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
            ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
          ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) →
    ∀ (n k : ℕ), k ≤ n →
      ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) =
        Qc n k * 2 ^ k * (∑ K ∈ Finset.Ioc n (2 * n), 1 / ((2 : ℚ) ^ k - 2 ^ K) -
          ∑ i ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ i)) -
        ∑ j ∈ Finset.Ioc k n, Qc n j * 2 ^ (j - k) / (1 - 2 ^ (j - k)) := sorry
  have gauss : ∀ n k : ℕ,
      ∃ z : ℤ, (z : ℚ) = ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
    intro n k
    have hD : ∀ j : ℕ, ((2 : ℚ) ^ (j + 1) - 1) ≠ 0 := by
      intro j
      have h1 : (1 : ℚ) < 2 ^ (j + 1) := one_lt_pow₀ (by norm_num) (by omega)
      exact ne_of_gt (sub_pos.mpr h1)
    have hDk : ∀ k : ℕ, (∏ i ∈ Finset.range k, ((2 : ℚ) ^ (i + 1) - 1)) ≠ 0 := by
      intro k
      exact Finset.prod_ne_zero_iff.mpr (fun i _ => hD i)
    have key : ∀ m j : ℕ,
        (∏ i ∈ Finset.range (j + 1), ((2 : ℚ) ^ (m + 1 - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) =
          (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) +
          2 ^ (j + 1) *
            ∏ i ∈ Finset.range (j + 1), ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
      intro m j
      simp only [Finset.prod_div_distrib]
      rw [Finset.prod_range_succ' (fun i => (2 : ℚ) ^ (m + 1 - i) - 1)]
      have hshift : ∀ i : ℕ, m + 1 - (i + 1) = m - i := fun i => by omega
      simp only [hshift, Nat.sub_zero]
      rw [Finset.prod_range_succ (fun i => (2 : ℚ) ^ (m - i) - 1),
        Finset.prod_range_succ (fun i => (2 : ℚ) ^ (i + 1) - 1)]
      have hDj := hDk j
      have hj := hD j
      by_cases hjm : j ≤ m
      · have e : (2 : ℚ) ^ (m + 1) = 2 ^ (m - j) * 2 ^ (j + 1) := by
          rw [← pow_add]
          congr 1
          omega
        rw [e]
        field_simp
        ring
      · have hz : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1)) = 0 :=
          Finset.prod_eq_zero (i := m) (Finset.mem_range.mpr (by omega)) (by simp)
        rw [hz]
        simp
    have main : ∀ m j : ℕ, ∃ z : ℤ,
        (z : ℚ) = ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
      intro m
      induction m with
      | zero =>
        intro j
        cases j with
        | zero => exact ⟨1, by simp⟩
        | succ j =>
          refine ⟨0, ?_⟩
          rw [Finset.prod_eq_zero (i := 0) (by simp) (by simp)]
          simp
      | succ m ih =>
        intro j
        cases j with
        | zero => exact ⟨1, by simp⟩
        | succ j =>
          obtain ⟨a, ha⟩ := ih j
          obtain ⟨b, hb⟩ := ih (j + 1)
          refine ⟨a + 2 ^ (j + 1) * b, ?_⟩
          rw [key, ← ha, ← hb]
          push_cast
          ring
    exact main n k
  have hodd : ∀ (n k : ℕ), k ≤ n → ∀ (c : ℕ → ℤ),
      ∃ z : ℤ, (z : ℚ) = (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) *
        ∑ j ∈ Finset.range (k + 1), (c j : ℚ) / ((2 : ℚ) ^ (k - j) - 1) := by
    intro n k hk c
    have hint : ∀ j ∈ Finset.range (k + 1), ∃ z : ℤ,
        (z : ℚ) = (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) *
          ((c j : ℚ) / ((2 : ℚ) ^ (k - j) - 1)) := by
      intro j hj
      have hjk : j ≤ k := Nat.lt_succ_iff.mp (Finset.mem_range.mp hj)
      by_cases hjeq : j = k
      · subst hjeq
        exact ⟨0, by simp⟩
      · obtain ⟨d, hd⟩ : ∃ d, k - j = d + 1 := ⟨k - j - 1, by omega⟩
        rw [hd]
        have hdn : d + 1 ≤ n := by omega
        have ht : 1 ≤ n / (d + 1) := (Nat.one_le_div_iff (by omega)).mpr hdn
        have hP1 : (d + 1) * (n / (d + 1)) ≤ n := Nat.mul_div_le n (d + 1)
        have hP2 : n < (d + 1) * (n / (d + 1)) + (d + 1) := by
          have := Nat.lt_mul_div_succ n (show 0 < d + 1 by omega)
          rw [Nat.mul_succ] at this
          exact this
        have hP3 : (d + 1) ≤ (d + 1) * (n / (d + 1)) := Nat.le_mul_of_pos_right _ ht
        have hmem : (d + 1) * (n / (d + 1)) ∈ Finset.Ioc (n / 2) n := by
          rw [Finset.mem_Ioc]
          generalize (d + 1) * (n / (d + 1)) = P at hP1 hP2 hP3 ⊢
          omega
        have hdvd : ((2 : ℤ) ^ (d + 1) - 1) ∣ ∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℤ) ^ m - 1) := by
          refine dvd_trans ?_ (Finset.dvd_prod_of_mem _ hmem)
          have := sub_dvd_pow_sub_pow ((2 : ℤ) ^ (d + 1)) 1 (n / (d + 1))
          rw [one_pow, ← pow_mul] at this
          exact this
        obtain ⟨q, hq⟩ := hdvd
        have hne : ((2 : ℚ) ^ (d + 1) - 1) ≠ 0 := by
          have : (1 : ℚ) < 2 ^ (d + 1) := one_lt_pow₀ (by norm_num) (by omega)
          linarith
        refine ⟨c j * q, ?_⟩
        have hcast : (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) =
            (((2 : ℤ) ^ (d + 1) - 1 : ℤ) : ℚ) * (q : ℚ) := by
          rw [← Int.cast_mul, ← hq]
          push_cast
          rfl
        rw [hcast]
        push_cast
        field_simp
    choose! g hg using hint
    refine ⟨∑ j ∈ Finset.range (k + 1), g j, ?_⟩
    push_cast
    rw [Finset.mul_sum]
    exact Finset.sum_congr rfl hg
  have combine : ∀ (p M : ℚ) (a : ℕ) (Ω A B m : ℤ), Odd Ω →
      (Ω : ℚ) * p = 2 ^ a * A → (B : ℚ) = M * p → (m : ℚ) = M →
      ∃ z : ℤ, (z : ℚ) * 2 ^ a = M * p := by
    intro p M a Ω A B m hΩ h1 h2 hm
    have hint : Ω * B = 2 ^ a * (m * A) := by
      have : ((Ω * B : ℤ) : ℚ) = ((2 ^ a * (m * A) : ℤ) : ℚ) := by
        push_cast
        rw [h2, ← hm]
        linear_combination (m : ℚ) * h1
      exact_mod_cast this
    obtain ⟨t, ht⟩ := hΩ
    have hcop : IsCoprime ((2 : ℤ) ^ a) Ω := by
      apply IsCoprime.pow_left
      exact ⟨-t, 1, by rw [ht]; ring⟩
    have hdvd : (2 : ℤ) ^ a ∣ B * Ω := ⟨m * A, by rw [mul_comm, hint]⟩
    obtain ⟨c, hc⟩ := hcop.dvd_of_dvd_mul_right hdvd
    refine ⟨c, ?_⟩
    rw [← h2, hc]
    push_cast
    ring
  intro Qc hQc n k hk
  have hQcint : ∀ j : ℕ, ∃ g : ℤ, Qc n j = 2 ^ (j * (j - 1) / 2) * g := by
    intro j
    obtain ⟨a, ha⟩ := gauss n j
    obtain ⟨b, hb⟩ := gauss (2 * n - j) n
    refine ⟨(-1) ^ j * a * b, ?_⟩
    rw [hQc]
    simp only []
    rw [← ha, ← hb]
    push_cast
    ring
  choose g hg using hQcint
  -- the odd product
  have hΩdiv : ∀ s : ℕ, 1 ≤ s → s ≤ 2 * n → ∃ w : ℤ,
      (w : ℚ) * ((2 : ℚ) ^ s - 1) = ((∏ t ∈ Finset.Icc 1 (2 * n), ((2 : ℤ) ^ t - 1) : ℤ) : ℚ) := by
    intro s h1 h2
    refine ⟨∏ t ∈ (Finset.Icc 1 (2 * n)).erase s, ((2 : ℤ) ^ t - 1), ?_⟩
    rw [← Finset.prod_erase_mul _ _ (Finset.mem_Icc.mpr ⟨h1, h2⟩)]
    push_cast
    ring
  have hΩodd : Odd (∏ t ∈ Finset.Icc 1 (2 * n), ((2 : ℤ) ^ t - 1)) := by
    apply Finset.prod_induction _ (fun x : ℤ => Odd x)
    · intro x y hx hy
      exact hx.mul hy
    · exact odd_one
    · intro t ht
      have ht1 : t ≠ 0 := by
        have := (Finset.mem_Icc.mp ht).1
        omega
      exact Even.sub_odd ((Int.even_pow).mpr ⟨even_two, ht1⟩) odd_one
  -- one term 2^a / (2^a - 2^b), times the odd product, is an integer
  have key1 : ∀ a b : ℕ, a ≠ b → a ≤ 2 * n → b ≤ 2 * n → ∃ w : ℤ,
      (w : ℚ) = ((∏ t ∈ Finset.Icc 1 (2 * n), ((2 : ℤ) ^ t - 1) : ℤ) : ℚ) * 2 ^ a * (1 / ((2 : ℚ) ^ a - 2 ^ b)) := by
    intro a b hab ha hb
    rcases Nat.lt_or_gt_of_ne hab with hlt | hgt
    · obtain ⟨d, rfl⟩ := Nat.exists_eq_add_of_lt hlt
      obtain ⟨w, hw⟩ := hΩdiv (d + 1) (by omega) (by omega)
      refine ⟨-w, ?_⟩
      have hne : (2 : ℚ) ^ (d + 1) - 1 ≠ 0 := by
        have : (1 : ℚ) < 2 ^ (d + 1) := one_lt_pow₀ (by norm_num) (by omega)
        linarith
      have h2a : (2 : ℚ) ^ a ≠ 0 := by positivity
      rw [← hw, show a + d + 1 = a + (d + 1) by ring, show (2 : ℚ) ^ (a + (d + 1)) = 2 ^ a * 2 ^ (d + 1) from pow_add _ _ _]
      have : (2 : ℚ) ^ a - 2 ^ a * 2 ^ (d + 1) = -(2 ^ a * (2 ^ (d + 1) - 1)) := by ring
      rw [this]
      field_simp
      push_cast
      ring
    · obtain ⟨d, rfl⟩ := Nat.exists_eq_add_of_lt hgt
      obtain ⟨w, hw⟩ := hΩdiv (d + 1) (by omega) (by omega)
      refine ⟨w * 2 ^ (d + 1), ?_⟩
      have hne : (2 : ℚ) ^ (d + 1) - 1 ≠ 0 := by
        have : (1 : ℚ) < 2 ^ (d + 1) := one_lt_pow₀ (by norm_num) (by omega)
        linarith
      have h2b : (2 : ℚ) ^ b ≠ 0 := by positivity
      rw [← hw, show b + d + 1 = b + (d + 1) by ring, show (2 : ℚ) ^ (b + (d + 1)) = 2 ^ b * 2 ^ (d + 1) from pow_add _ _ _]
      have : (2 : ℚ) ^ b * 2 ^ (d + 1) - 2 ^ b = 2 ^ b * (2 ^ (d + 1) - 1) := by ring
      rw [this]
      field_simp
      push_cast
      ring
  set Ω : ℤ := ∏ t ∈ Finset.Icc 1 (2 * n), ((2 : ℤ) ^ t - 1) with hΩ
  have hK : ∀ K ∈ Finset.Ioc n (2 * n), ∃ w : ℤ,
      (w : ℚ) = (Ω : ℚ) * 2 ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ K)) := by
    intro K hK'
    have := Finset.mem_Ioc.mp hK'
    exact key1 k K (by omega) (by omega) (by omega)
  have hI : ∀ i ∈ (Finset.range (n + 1)).erase k, ∃ w : ℤ,
      (w : ℚ) = (Ω : ℚ) * 2 ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ i)) := by
    intro i hi
    have h1 := Finset.ne_of_mem_erase hi
    have h2 := Finset.mem_range.mp (Finset.mem_of_mem_erase hi)
    exact key1 k i (Ne.symm h1) (by omega) (by omega)
  have hT : ∀ j ∈ Finset.Ioc k n, ∃ w : ℤ,
      (w : ℚ) * 2 ^ (k * (k - 1) / 2) = (Ω : ℚ) * (Qc n j * 2 ^ (j - k) / (1 - 2 ^ (j - k))) := by
    intro j hj
    have hj' := Finset.mem_Ioc.mp hj
    obtain ⟨d, hd⟩ : ∃ d, j - k = d + 1 := ⟨j - k - 1, by omega⟩
    obtain ⟨w, hw⟩ := hΩdiv (d + 1) (by omega) (by omega)
    have hmono : k * (k - 1) / 2 ≤ j * (j - 1) / 2 :=
      Nat.div_le_div_right (Nat.mul_le_mul (by omega) (by omega))
    obtain ⟨e, he⟩ := Nat.exists_eq_add_of_le hmono
    refine ⟨-(w * g j * 2 ^ e * 2 ^ (d + 1)), ?_⟩
    have hne : (2 : ℚ) ^ (d + 1) - 1 ≠ 0 := by
      have : (1 : ℚ) < 2 ^ (d + 1) := one_lt_pow₀ (by norm_num) (by omega)
      linarith
    have hne' : (1 : ℚ) - 2 ^ (d + 1) ≠ 0 := by
      intro h
      apply hne
      linarith
    rw [hd, hg j, he, ← hw, show (2 : ℚ) ^ (k * (k - 1) / 2 + e) = 2 ^ (k * (k - 1) / 2) * 2 ^ e from pow_add _ _ _]
    field_simp
    push_cast
    ring
  choose! fK hfK using hK
  choose! fI hfI using hI
  choose! fT hfT using hT
  have h2adic : (Ω : ℚ) * ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) =
      2 ^ (k * (k - 1) / 2) * ((g k * (∑ K ∈ Finset.Ioc n (2 * n), fK K -
        ∑ i ∈ (Finset.range (n + 1)).erase k, fI i) - ∑ j ∈ Finset.Ioc k n, fT j : ℤ) : ℚ) := by
    rw [hform Qc hQc n k hk]
    push_cast
    rw [Finset.sum_congr rfl hfK, Finset.sum_congr rfl hfI, ← Finset.mul_sum, ← Finset.mul_sum]
    have htail : (2 : ℚ) ^ (k * (k - 1) / 2) * ∑ j ∈ Finset.Ioc k n, (fT j : ℚ) =
        (Ω : ℚ) * ∑ j ∈ Finset.Ioc k n, Qc n j * 2 ^ (j - k) / (1 - 2 ^ (j - k)) := by
      rw [Finset.mul_sum, Finset.mul_sum]
      refine Finset.sum_congr rfl (fun j hj => ?_)
      rw [mul_comm]
      exact hfT j hj
    rw [hg k]
    simp only [one_div] at htail ⊢
    linear_combination htail
  -- the odd half
  obtain ⟨B, hB⟩ := hodd n k hk (fun j => 2 ^ (j * (j - 1) / 2) * g j)
  have hB' : (B : ℚ) = (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) *
      ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ)) := by
    rw [hB]
    congr 1
    refine Finset.sum_congr rfl (fun j _ => ?_)
    rw [hg j]
    push_cast
    ring
  exact combine _ _ _ Ω _ B (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℤ) ^ m - 1)) hΩodd h2adic hB'
    (by push_cast; rfl)
