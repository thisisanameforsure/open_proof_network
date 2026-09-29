import Mathlib

theorem hpint_test : ∀ (Qc : ℕ → ℕ → ℚ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) →
    ∀ (Qx : ℕ → ℚ),
      (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) →
        ∀ (Aq : ℕ → ℚ),
          (Aq = fun (n : ℕ) =>
              ∑ k ∈ Finset.range (n + (1 : ℕ)),
                  (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) *
                    ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
                Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) →
            ∀ (n : ℕ) (M : ℕ → ℕ),
              (M = fun (n : ℕ) => ∏ m ∈ Finset.Ioc (n / (2 : ℕ)) n, ((2 : ℕ) ^ m - (1 : ℕ))) →
                ∀ (C : ℕ → ℕ),
                  (C = fun (n : ℕ) => ∏ j ∈ Finset.Ico (2 : ℕ) n, ((2 : ℕ) ^ (j + (1 : ℕ)) - (3 : ℕ))) →
                    (∀ k ≤ n, ∃ (z : ℤ), (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) = Qc n k) →
                      ∀ k ≤ n,
                        ∃ (z : ℤ),
                          (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) =
                            (↑(M n) : ℚ) * ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ)) := by
  -- annex: <sha256 of an annex merged on the hpint node itself; file one there first>
  intro Qc hQc Qx _ Aq _ n M hM C _ hQcint k hk
  -- hole: the closed form of p_k (the statement of spec-ffd3137a at this n and k)
  have hclosed : ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) =
      Qc n k * (∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) -
          ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) -
          ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1))) +
        ∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := sorry
  -- hole: the cyclotomic count, M n [n k]_2 [2n-k n]_2 / (2^a - 1) is an integer for n < a ≤ 2n - k
  have hA : ∀ i < n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) =
      (M n : ℚ) * Qc n k * (1 / (1 - (2 : ℚ) ^ (n + 1 + i - k))) := sorry
  -- proved: 2^b - 1 divides M n for 1 ≤ b ≤ n (b has a multiple in (n/2, n])
  have hdvd : ∀ b : ℕ, 1 ≤ b → b ≤ n → ∃ R : ℕ, M n = (2 ^ b - 1) * R := by
    intro b hb1 hbn
    have h1 : b * (n / b) ≤ n := Nat.mul_div_le n b
    have h2 : n < b * (n / b) + b := by
      have := Nat.lt_mul_div_succ n (show 0 < b by omega)
      rw [Nat.mul_succ] at this
      exact this
    have h3 : b ≤ b * (n / b) := Nat.le_mul_of_pos_right b (Nat.div_pos hbn (by omega))
    have hmem : b * (n / b) ∈ Finset.Ioc (n / 2) n := Finset.mem_Ioc.mpr ⟨by omega, h1⟩
    have hd1 : 2 ^ b - 1 ∣ 2 ^ (b * (n / b)) - 1 := by
      have : 2 ^ b - 1 ∣ (2 ^ b) ^ (n / b) - 1 ^ (n / b) := by
        first
          | exact Nat.sub_dvd_pow_sub_pow _ _ _
          | exact nat_sub_dvd_pow_sub_pow _ _ _
      rwa [one_pow, ← pow_mul] at this
    have hd2 : 2 ^ (b * (n / b)) - 1 ∣ ∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) :=
      Finset.dvd_prod_of_mem (fun m => 2 ^ m - 1) hmem
    obtain ⟨R, hR⟩ := dvd_trans hd1 hd2
    exact ⟨R, by rw [hM]; exact hR⟩
  have hcast : ∀ b : ℕ, (((2 ^ b - 1 : ℕ)) : ℚ) = (2 : ℚ) ^ b - 1 := by
    intro b
    rw [Nat.cast_sub (Nat.one_le_two_pow)]
    push_cast
    ring
  have hne : ∀ b : ℕ, (2 : ℚ) ^ (b + 1) - 1 ≠ 0 := by
    intro b
    have : (2 : ℚ) ≤ 2 ^ (b + 1) := by
      calc (2 : ℚ) = 2 ^ 1 := by norm_num
        _ ≤ 2 ^ (b + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
    linarith
  let P : ℚ → Prop := fun x => ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) = x
  have hadd : ∀ x y : ℚ, P x → P y → P (x + y) := fun x y ⟨a, ha⟩ ⟨b, hb⟩ =>
    ⟨a + b, by push_cast; rw [add_mul, ha, hb]⟩
  have hsub : ∀ x y : ℚ, P x → P y → P (x - y) := fun x y ⟨a, ha⟩ ⟨b, hb⟩ =>
    ⟨a - b, by push_cast; rw [sub_mul, ha, hb]⟩
  have hsum : ∀ (s : Finset ℕ) (f : ℕ → ℚ), (∀ i ∈ s, P (f i)) → P (∑ i ∈ s, f i) :=
    fun s f h => Finset.sum_induction _ P hadd ⟨0, by simp⟩ h
  obtain ⟨zk, hzk⟩ := hQcint k hk
  show P _
  rw [hclosed]
  have eq : (M n : ℚ) * (Qc n k * (∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) -
          ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) -
          ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1))) +
        ∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1)) =
      (M n : ℚ) * Qc n k * ∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) -
        (M n : ℚ) * Qc n k * ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) -
        (M n : ℚ) * Qc n k * ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1)) +
        (M n : ℚ) * ∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
    ring
  rw [eq]
  refine hadd _ _ (hsub _ _ (hsub _ _ ?_ ?_) ?_) ?_
  · rw [Finset.mul_sum]
    exact hsum _ _ (fun i hi => hA i (Finset.mem_range.mp hi))
  · rw [Finset.mul_sum]
    refine hsum _ _ (fun b hb => ?_)
    have hbk := Finset.mem_range.mp hb
    obtain ⟨R, hR⟩ := hdvd (b + 1) (by omega) (by omega)
    refine ⟨zk * 2 ^ (b + 1) * R, ?_⟩
    rw [hR, ← hzk, Nat.cast_mul, hcast]
    push_cast
    field_simp [hne b]
  · rw [Finset.mul_sum]
    refine hsum _ _ (fun b hb => ?_)
    have hbk := Finset.mem_range.mp hb
    obtain ⟨R, hR⟩ := hdvd (b + 1) (by omega) (by omega)
    refine ⟨-(zk * R), ?_⟩
    have hne' : (1 : ℚ) - 2 ^ (b + 1) ≠ 0 := fun h => hne b (by linarith)
    rw [hR, ← hzk, Nat.cast_mul, hcast]
    push_cast
    field_simp [hne b, hne']
    ring
  · rw [Finset.mul_sum]
    refine hsum _ _ (fun b hb => ?_)
    have hbk := Finset.mem_range.mp hb
    obtain ⟨R, hR⟩ := hdvd (b + 1) (by omega) (by omega)
    obtain ⟨z', hz'⟩ := hQcint (k + b + 1) (by omega)
    have hT : k * (k - 1) / 2 ≤ (k + b + 1) * (k + b + 1 - 1) / 2 :=
      Nat.div_le_div_right (Nat.mul_le_mul (by omega) (by omega))
    have hpow : (2 : ℚ) ^ ((k + b + 1) * (k + b + 1 - 1) / 2) =
        (2 : ℚ) ^ ((k + b + 1) * (k + b + 1 - 1) / 2 - k * (k - 1) / 2) * (2 : ℚ) ^ (k * (k - 1) / 2) := by
      rw [← pow_add, Nat.sub_add_cancel hT]
    refine ⟨R * z' * 2 ^ (b + 1) * 2 ^ ((k + b + 1) * (k + b + 1 - 1) / 2 - k * (k - 1) / 2), ?_⟩
    rw [hR, ← hz', Nat.cast_mul, hcast, hpow]
    push_cast
    field_simp [hne b]
