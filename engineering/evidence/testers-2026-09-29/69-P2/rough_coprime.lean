import Mathlib

/-- The rough dilations `1 + P# (1 + j)`, `j ≤ P`, are pairwise coprime. -/
theorem rough_dilations_coprime (P i j : ℕ) (hij : i < j) (hjP : j ≤ P) :
    Nat.Coprime (1 + primorial P * (1 + i)) (1 + primorial P * (1 + j)) := by
  apply Nat.coprime_of_dvd
  intro r hr hrA hrB
  -- every prime up to P divides P#
  have hsmall : ∀ s : ℕ, s.Prime → s ≤ P → s ∣ primorial P := by
    intro s hs hsP
    unfold primorial
    exact Finset.dvd_prod_of_mem _
      (Finset.mem_filter.mpr ⟨Finset.mem_range.mpr (Nat.lt_succ_of_le hsP), hs⟩)
  have hrP : ¬ r ∣ primorial P := by
    intro h
    have h1 : r ∣ primorial P * (1 + i) := Dvd.dvd.mul_right h _
    have : r ∣ 1 := (Nat.dvd_add_right h1).mp (by rwa [add_comm] at hrA)
    exact hr.one_lt.ne' (Nat.dvd_one.mp this)
  have hdiff : 1 + primorial P * (1 + j) = (1 + primorial P * (1 + i)) + primorial P * (j - i) := by
    have : 1 + j = (1 + i) + (j - i) := by omega
    rw [this, mul_add]; ring
  rw [hdiff] at hrB
  have h2 : r ∣ primorial P * (j - i) := (Nat.dvd_add_right hrA).mp hrB
  have h3 : r ∣ j - i := (hr.dvd_mul.mp h2).resolve_left hrP
  have h4 : r ≤ j - i := Nat.le_of_dvd (by omega) h3
  exact hrP (hsmall r hr (by omega))
