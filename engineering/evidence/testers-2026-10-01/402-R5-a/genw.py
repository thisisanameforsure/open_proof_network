import sys,pathlib
def wit(N,r,s,extra_type,extra_proof):
    return f'''import Mathlib

open Filter

theorem witness : ∃ B : Finset ℕ, 0 ∉ B ∧ B.Nonempty ∧ B.gcd id = 1 ∧ ¬ B.card.Prime ∧
    (∀ q : ℕ, q.Prime → B.card ≠ q + 1) ∧
    (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) ∧
    (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card){extra_type} := by
  have hc : (Finset.Icc 1 {N} : Finset ℕ).card = {N} := by simp
  have h1 : (1 : ℕ) ∈ Finset.Icc 1 {N} := by simp
  refine ⟨Finset.Icc 1 {N}, by simp, ⟨1, h1⟩, ?_, ?_, ?_, ?_, ?_{', ?_' if extra_type else ''}⟩
  · exact Nat.dvd_one.mp (Finset.gcd_dvd h1)
  · rw [hc]
    norm_num
  · intro q hq h
    rw [hc] at h
    have hq' : q = {N-1} := by omega
    rw [hq'] at hq
    norm_num at hq
  · intro a ha b hb
    rw [hc]
    have ha' := Finset.mem_Icc.mp ha
    have hg : 0 < a.gcd b := Nat.gcd_pos_of_pos_left b (by omega)
    calc a ≤ {N} := ha'.2
      _ ≤ {N} * a.gcd b := Nat.le_mul_of_pos_right {N} hg
  · intro a ha p k hp hdvd
    rw [hc]
    have ha' := Finset.mem_Icc.mp ha
    have hle : p ^ k ≤ a := Nat.le_of_dvd (by omega) hdvd
    have hne : p ^ k ≠ {N} := by
      intro hN
      have hr : {r} ∣ p ^ k := by rw [hN]; norm_num
      have hs : {s} ∣ p ^ k := by rw [hN]; norm_num
      have er : {r} = p := (Nat.prime_dvd_prime_iff_eq (by norm_num) hp).mp ((by norm_num : Nat.Prime {r}).dvd_of_dvd_pow hr)
      have es : {s} = p := (Nat.prime_dvd_prime_iff_eq (by norm_num) hp).mp ((by norm_num : Nat.Prime {s}).dvd_of_dvd_pow hs)
      omega
    omega
{extra_proof}'''
pathlib.Path('hres-witness.lean').write_text(wit(63,3,7," ∧\n    (B.card = 63 ∨ B.card = 105 ∨ B.card = 111 ∨ B.card = 153 ∨ B.card = 165 ∨ B.card = 679 ∨ B.card = 680)","  · exact Or.inl hc\n"))
pathlib.Path('hlarge-witness.lean').write_text(wit(200016,2,3," ∧\n    200014 < B.card","  · rw [hc]\n    norm_num\n"))
