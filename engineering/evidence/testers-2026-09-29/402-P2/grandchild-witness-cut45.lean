import Mathlib

open Filter

theorem witness : ∃ B : Finset ℕ, 0 ∉ B ∧ B.Nonempty ∧ B.gcd id = 1 ∧ ¬ B.card.Prime ∧
      (∀ q : ℕ, q.Prime → B.card ≠ q + 1) ∧
      (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) ∧
      (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card) ∧
      45 ≤ B.card := by
  have hc : (Finset.Icc 1 45).card = 45 := by simp
  refine ⟨Finset.Icc 1 45, by simp, ⟨1, by simp⟩, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · apply Nat.eq_one_of_dvd_one
    exact Finset.gcd_dvd (by simp : (1 : ℕ) ∈ Finset.Icc 1 45)
  · rw [hc]; norm_num
  · intro q hq h
    rw [hc] at h
    have hq44 : q = 44 := by omega
    rw [hq44] at hq
    norm_num at hq
  · intro a ha b _
    rw [hc]
    have ha' := Finset.mem_Icc.mp ha
    have hg : 0 < a.gcd b := Nat.gcd_pos_of_pos_left b (by omega)
    calc a ≤ 45 := ha'.2
      _ ≤ 45 * a.gcd b := Nat.le_mul_of_pos_right 45 hg
  · intro a ha p k hp hdvd
    rw [hc]
    have ha' := Finset.mem_Icc.mp ha
    have hle : p ^ k ≤ a := Nat.le_of_dvd (by omega) hdvd
    have hne : p ^ k ≠ 45 := by
      intro h45
      have h3 : 3 ∣ p ^ k := by rw [h45]; norm_num
      have h5 : 5 ∣ p ^ k := by rw [h45]; norm_num
      have hp3 : 3 ∣ p := Nat.Prime.dvd_of_dvd_pow Nat.prime_three h3
      have hp5 : 5 ∣ p := Nat.Prime.dvd_of_dvd_pow (by norm_num) h5
      have e3 : p = 3 := ((Nat.Prime.eq_one_or_self_of_dvd hp 3 hp3).resolve_left (by norm_num)).symm
      have e5 : p = 5 := ((Nat.Prime.eq_one_or_self_of_dvd hp 5 hp5).resolve_left (by norm_num)).symm
      omega
    omega
  · rw [hc]
