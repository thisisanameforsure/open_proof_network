import Mathlib

example (q : ℚ) : ∃ p N₀ : ℕ, 0 < p ∧ ∀ n n' : ℕ, N₀ ≤ n → N₀ ≤ n' → n ≡ n' [MOD p] →
    ∃ z : ℤ, (2 : ℝ) ^ n * (q : ℝ) - 2 ^ n' * (q : ℝ) = z := by
  haveI : NeZero q.den := ⟨q.den_nz⟩
  let g : ℕ → ZMod q.den := fun n => ((2 ^ n * q.num : ℤ) : ZMod q.den)
  obtain ⟨x, y, hxy, hg⟩ := Finite.exists_ne_map_eq_of_infinite g
  have hkey : ∃ n₀ p : ℕ, 0 < p ∧ (q.den : ℤ) ∣ 2 ^ (n₀ + p) * q.num - 2 ^ n₀ * q.num := by
    have h := (ZMod.intCast_eq_intCast_iff_dvd_sub _ _ _).1 hg
    rcases lt_or_gt_of_ne hxy with hlt | hlt
    · refine ⟨x, y - x, by omega, ?_⟩
      rw [show x + (y - x) = y by omega]
      exact h
    · refine ⟨y, x - y, by omega, ?_⟩
      rw [show y + (x - y) = x by omega, ← dvd_neg, neg_sub]
      exact h
  obtain ⟨n₀, p, hp, hd⟩ := hkey
  have hmul : ∀ m t : ℕ, (q.den : ℤ) ∣ 2 ^ (n₀ + t + m * p) * q.num - 2 ^ (n₀ + t) * q.num := by
    intro m t
    induction m with
    | zero => simp
    | succ m ih =>
      have e : (2 : ℤ) ^ (n₀ + t + (m + 1) * p) * q.num - 2 ^ (n₀ + t) * q.num
          = 2 ^ (t + m * p) * (2 ^ (n₀ + p) * q.num - 2 ^ n₀ * q.num)
            + (2 ^ (n₀ + t + m * p) * q.num - 2 ^ (n₀ + t) * q.num) := by
        rw [show n₀ + t + (m + 1) * p = (t + m * p) + (n₀ + p) by ring,
          show n₀ + t + m * p = (t + m * p) + n₀ by ring, pow_add, pow_add]
        ring
      rw [e]
      exact dvd_add (dvd_mul_of_dvd_right hd _) ih
  have hle : ∀ n n' : ℕ, n₀ ≤ n → n ≤ n' → n ≡ n' [MOD p] →
      ∃ z : ℤ, (2 : ℝ) ^ n * (q : ℝ) - 2 ^ n' * (q : ℝ) = z := by
    intro n n' hn hnn' hmod
    obtain ⟨m, hm⟩ := (Nat.modEq_iff_dvd' hnn').1 hmod
    have h1 := hmul m (n - n₀)
    rw [show n₀ + (n - n₀) = n by omega, show n + m * p = n' by
      rw [mul_comm]; omega] at h1
    obtain ⟨w, hw⟩ := h1
    refine ⟨-w, ?_⟩
    have hden : (q.den : ℝ) ≠ 0 := by exact_mod_cast q.den_nz
    have hw' : (2 : ℝ) ^ n' * (q.num : ℝ) - 2 ^ n * (q.num : ℝ) = (q.den : ℝ) * (w : ℝ) := by
      exact_mod_cast hw
    rw [Rat.cast_def]
    field_simp
    push_cast
    linarith
  refine ⟨p, n₀, hp, fun n n' hn hn' hmod => ?_⟩
  rcases le_total n n' with h | h
  · exact hle n n' hn h hmod
  · obtain ⟨z, hz⟩ := hle n' n hn' h hmod.symm
    exact ⟨-z, by push_cast; linarith⟩
