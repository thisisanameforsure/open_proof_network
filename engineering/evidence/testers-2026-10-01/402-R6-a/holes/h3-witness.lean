import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h2--h3».Context

open Filter

theorem witness : ∃ B : Finset ℕ, 0 ∉ B ∧ B.Nonempty ∧ B.gcd id = 1 ∧ ¬ B.card.Prime ∧
    (∀ q : ℕ, q.Prime → B.card ≠ q + 1) ∧
    (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) ∧
    (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card) ∧
    200014 < B.card := by
  have hc : (Finset.Icc 1 200016 : Finset ℕ).card = 200016 := by simp
  have h1 : (1 : ℕ) ∈ Finset.Icc 1 200016 := by simp
  refine ⟨Finset.Icc 1 200016, by simp, ⟨1, h1⟩, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact Nat.dvd_one.mp (Finset.gcd_dvd h1)
  · rw [hc]
    norm_num
  · intro q hq h
    rw [hc] at h
    have hq' : q = 200015 := by omega
    rw [hq'] at hq
    norm_num at hq
  · intro a ha b hb
    rw [hc]
    have ha' := Finset.mem_Icc.mp ha
    have hg : 0 < a.gcd b := Nat.gcd_pos_of_pos_left b (by omega)
    calc a ≤ 200016 := ha'.2
      _ ≤ 200016 * a.gcd b := Nat.le_mul_of_pos_right 200016 hg
  · intro a ha p k hp hdvd
    rw [hc]
    have ha' := Finset.mem_Icc.mp ha
    have hle : p ^ k ≤ a := Nat.le_of_dvd (by omega) hdvd
    have hne : p ^ k ≠ 200016 := by
      intro hN
      have hr : 2 ∣ p ^ k := by rw [hN]; norm_num
      have hs : 3 ∣ p ^ k := by rw [hN]; norm_num
      have er : 2 = p := (Nat.prime_dvd_prime_iff_eq (by norm_num) hp).mp ((by norm_num : Nat.Prime 2).dvd_of_dvd_pow hr)
      have es : 3 = p := (Nat.prime_dvd_prime_iff_eq (by norm_num) hp).mp ((by norm_num : Nat.Prime 3).dvd_of_dvd_pow hs)
      omega
    omega
  · rw [hc]
    norm_num
