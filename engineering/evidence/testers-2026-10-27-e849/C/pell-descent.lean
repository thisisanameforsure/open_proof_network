import Mathlib

/-! The Pell half of h_adjacent (agent C): every solution of X² − 5Y² = −4 in nonnegative integers is
reached from (1, 1) by the step (a, b) ↦ ((3a+5b)/2, (a+3b)/2), i.e. (L_j, F_j) for odd j.
Stated as an induction principle so the Fibonacci half can instantiate P. -/

/-- A solution has X ≡ Y (mod 2). -/
private theorem e849_pell_parity (X Y : ℤ) (h : X ^ 2 - 5 * Y ^ 2 = -4) : 2 ∣ X - Y := by
  rcases Int.even_or_odd X with ⟨p, hp⟩ | ⟨p, hp⟩ <;> rcases Int.even_or_odd Y with ⟨q, hq⟩ | ⟨q, hq⟩
  · exact ⟨p - q, by omega⟩
  · exfalso; subst hp; subst hq
    have : (p + p) ^ 2 - 5 * (2 * q + 1) ^ 2 = 4 * (p ^ 2 - 5 * q ^ 2 - 5 * q) - 5 := by ring
    omega
  · exfalso; subst hp; subst hq
    have : (2 * p + 1) ^ 2 - 5 * (q + q) ^ 2 = 4 * (p ^ 2 + p - 5 * q ^ 2) + 1 := by ring
    omega
  · exact ⟨p - q, by omega⟩

/-- Descent: a solution with Y ≥ 2 comes from a smaller one by the step. -/
private theorem e849_pell_descent (X Y : ℤ) (hX : 0 ≤ X) (hY : 2 ≤ Y) (h : X ^ 2 - 5 * Y ^ 2 = -4) :
    ∃ X' Y' : ℤ, 0 ≤ X' ∧ 0 ≤ Y' ∧ Y' < Y ∧ X' ^ 2 - 5 * Y' ^ 2 = -4 ∧
      X = (3 * X' + 5 * Y') / 2 ∧ Y = (X' + 3 * Y') / 2 := by
  obtain ⟨d, hd⟩ := e849_pell_parity X Y h
  -- X = Y + 2d
  have hXd : X = Y + 2 * d := by omega
  refine ⟨(3 * X - 5 * Y) / 2, (3 * Y - X) / 2, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · -- 3X ≥ 5Y
    have : 5 * Y ≤ 3 * X := by nlinarith
    omega
  · have : X ≤ 3 * Y := by nlinarith
    omega
  · have : Y < X := by nlinarith
    omega
  · have e1 : (3 * X - 5 * Y) / 2 = 3 * d - Y := by omega
    have e2 : (3 * Y - X) / 2 = Y - d := by omega
    rw [e1, e2]; subst hXd; nlinarith [h]
  · have e1 : (3 * X - 5 * Y) / 2 = 3 * d - Y := by omega
    have e2 : (3 * Y - X) / 2 = Y - d := by omega
    rw [e1, e2]; omega
  · have e1 : (3 * X - 5 * Y) / 2 = 3 * d - Y := by omega
    have e2 : (3 * Y - X) / 2 = Y - d := by omega
    rw [e1, e2]; omega

/-- The induction principle for solutions of X² − 5Y² = −4. -/
theorem e849_pell5_induction (P : ℤ → ℤ → Prop) (h0 : P 1 1)
    (hstep : ∀ a b : ℤ, 0 ≤ a → 0 ≤ b → a ^ 2 - 5 * b ^ 2 = -4 → P a b →
      P ((3 * a + 5 * b) / 2) ((a + 3 * b) / 2)) :
    ∀ X Y : ℤ, 0 ≤ X → 0 ≤ Y → X ^ 2 - 5 * Y ^ 2 = -4 → P X Y := by
  intro X Y hX hY h
  obtain ⟨N, hN⟩ : ∃ N : ℕ, Y ≤ N := ⟨Y.toNat, Int.self_le_toNat Y⟩
  induction N using Nat.strong_induction_on generalizing X Y with
  | _ N ih =>
    rcases lt_or_ge Y 2 with hY2 | hY2
    · -- Y = 0 impossible, Y = 1 gives X = 1
      have hY1 : Y = 1 := by
        rcases (show Y = 0 ∨ Y = 1 by omega) with h0' | h1
        · subst h0'; nlinarith
        · exact h1
      subst hY1
      have hX1 : X = 1 := by nlinarith
      subst hX1; exact h0
    · obtain ⟨X', Y', hX', hY', hlt, h', eX, eY⟩ := e849_pell_descent X Y hX hY2 h
      have hN' : Y' ≤ (Y'.toNat : ℤ) := Int.self_le_toNat Y'
      have hlt' : Y'.toNat < N := by omega
      have := ih Y'.toNat hlt' X' Y' hX' hY' h' hN'
      rw [eX, eY]
      exact hstep X' Y' hX' hY' h' this
