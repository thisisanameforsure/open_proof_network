import Mathlib

open Filter

theorem witness : ∃ B : Finset ℕ, 0 ∉ B ∧ B.Nonempty ∧ B.gcd id = 1 ∧ ¬ B.card.Prime ∧
    (∀ q : ℕ, q.Prime → B.card ≠ q + 1) ∧
    (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) ∧
    (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card) ∧
    (B.card = 63 ∨ B.card = 105 ∨ B.card = 111 ∨ B.card = 153 ∨ B.card = 165 ∨ B.card = 679 ∨ B.card = 680) := by
  have hc : (Finset.Icc 1 63 : Finset ℕ).card = 63 := by simp
  have h1 : (1 : ℕ) ∈ Finset.Icc 1 63 := by simp
  refine ⟨Finset.Icc 1 63, by simp, ⟨1, h1⟩, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact Nat.dvd_one.mp (Finset.gcd_dvd h1)
  · rw [hc]
    norm_num
  · intro q hq h
    rw [hc] at h
    have hq' : q = 62 := by omega
    rw [hq'] at hq
    norm_num at hq
  · intro a ha b hb
    rw [hc]
    have ha' := Finset.mem_Icc.mp ha
    have hg : 0 < a.gcd b := Nat.gcd_pos_of_pos_left b (by omega)
    calc a ≤ 63 := ha'.2
      _ ≤ 63 * a.gcd b := Nat.le_mul_of_pos_right 63 hg
  · intro a ha p k hp hdvd
    rw [hc]
    have ha' := Finset.mem_Icc.mp ha
    have hle : p ^ k ≤ a := Nat.le_of_dvd (by omega) hdvd
    have hne : p ^ k ≠ 63 := by
      intro hN
      have hr : 3 ∣ p ^ k := by rw [hN]; norm_num
      have hs : 7 ∣ p ^ k := by rw [hN]; norm_num
      have er : 3 = p := (Nat.prime_dvd_prime_iff_eq (by norm_num) hp).mp ((by norm_num : Nat.Prime 3).dvd_of_dvd_pow hr)
      have es : 7 = p := (Nat.prime_dvd_prime_iff_eq (by norm_num) hp).mp ((by norm_num : Nat.Prime 7).dvd_of_dvd_pow hs)
      omega
    omega
  · exact Or.inl hc
