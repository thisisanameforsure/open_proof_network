import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1».Context

open Filter

theorem witness : ∃ B : Finset ℕ, 0 ∉ B ∧ B.Nonempty ∧ B.gcd id = 1 ∧ ¬ B.card.Prime ∧
    (∀ q : ℕ, q.Prime → B.card ≠ q + 1) ∧
    (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) ∧
    (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card) := by
  have hc : ({1, 2, 3, 4, 5, 6, 7, 8, 9, 10} : Finset ℕ).card = 10 := by decide
  refine ⟨{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}, by decide, ⟨1, by decide⟩, by decide, ?_, ?_, ?_, ?_⟩
  · rw [hc]
    norm_num
  · intro q hq h
    rw [hc] at h
    have hq9 : q = 9 := by omega
    rw [hq9] at hq
    norm_num at hq
  · intro a ha b hb
    rw [hc]
    simp only [Finset.mem_insert, Finset.mem_singleton] at ha
    have ha10 : a ≤ 10 := by omega
    have hg : 0 < a.gcd b := Nat.gcd_pos_of_pos_left b (by omega)
    calc a ≤ 10 := ha10
      _ ≤ 10 * a.gcd b := Nat.le_mul_of_pos_right 10 hg
  · intro a ha p k hp hdvd
    rw [hc]
    simp only [Finset.mem_insert, Finset.mem_singleton] at ha
    have ha0 : 0 < a := by omega
    have hle : p ^ k ≤ a := Nat.le_of_dvd ha0 hdvd
    have hne : p ^ k ≠ 10 := by
      intro h10
      have hk : k ≠ 0 := by
        rintro rfl
        simp at h10
      have hp10 : p ∣ 10 := by
        rw [← h10]
        exact dvd_pow_self p hk
      have hp10' : p ≤ 10 := Nat.le_of_dvd (by norm_num) hp10
      have hk4 : k < 4 := by
        have h2 : 2 ^ k ≤ p ^ k := Nat.pow_le_pow_left hp.two_le k
        by_contra hk4
        push Not at hk4
        have h16 : 2 ^ 4 ≤ 2 ^ k := Nat.pow_le_pow_right (by norm_num) hk4
        omega
      have hp2 := hp.two_le
      interval_cases p <;> interval_cases k <;> simp_all (config := { decide := true })
    omega
