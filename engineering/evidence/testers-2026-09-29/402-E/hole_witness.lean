import Mathlib

open Filter

theorem witness : ∃ B : Finset ℕ, 0 ∉ B ∧ B.Nonempty ∧ B.gcd id = 1 ∧ ¬ B.card.Prime ∧
    (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) ∧
    (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card) := by
  refine ⟨{1, 2, 3, 4, 5, 6}, by decide, ⟨1, by decide⟩, by decide, by decide, ?_, ?_⟩
  · intro a ha b hb
    have hc : ({1, 2, 3, 4, 5, 6} : Finset ℕ).card = 6 := by decide
    rw [hc]
    have ha6 : a ≤ 6 := by
      simp only [Finset.mem_insert, Finset.mem_singleton] at ha
      omega
    have hg : 0 < a.gcd b := by
      apply Nat.gcd_pos_of_pos_left
      simp only [Finset.mem_insert, Finset.mem_singleton] at ha
      omega
    calc a ≤ 6 := ha6
      _ ≤ 6 * a.gcd b := Nat.le_mul_of_pos_right 6 hg
  · intro a ha p k hp hdvd
    have hc : ({1, 2, 3, 4, 5, 6} : Finset ℕ).card = 6 := by decide
    rw [hc]
    have ha0 : 0 < a := by
      simp only [Finset.mem_insert, Finset.mem_singleton] at ha
      omega
    have hle : p ^ k ≤ a := Nat.le_of_dvd ha0 hdvd
    have hne : p ^ k ≠ 6 := by
      intro h6
      have hk : k ≠ 0 := by
        rintro rfl
        simp at h6
      have hp6 : p ∣ 6 := by
        rw [← h6]
        exact dvd_pow_self p hk
      have hp6' : p ≤ 6 := Nat.le_of_dvd (by norm_num) hp6
      have hk3 : k < 3 := by
        have h2 : 2 ^ k ≤ p ^ k := Nat.pow_le_pow_left hp.two_le k
        by_contra hk3
        push Not at hk3
        have h8 : 2 ^ 3 ≤ 2 ^ k := Nat.pow_le_pow_right (by norm_num) hk3
        omega
      interval_cases p <;> interval_cases k <;> simp_all (config := { decide := true })
    simp only [Finset.mem_insert, Finset.mem_singleton] at ha
    omega
