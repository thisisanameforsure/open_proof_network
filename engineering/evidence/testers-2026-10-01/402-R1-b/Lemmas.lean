import Mathlib

/-! Elementary lemmas for the general argument of Erdős 402 (Graham's gcd conjecture).
Agent 402-R1-b, 2026-10-01. Fast-checked on POST /check (mode check). No node of the record
states them; inline them as `have` steps (the gate refuses helper declarations). -/

/-- E1. Bertrand in the form the hole chain uses: a prime p with n ≤ 2p and p < n. -/
theorem R1b.bertrand_half (n : ℕ) (hn : 3 ≤ n) : ∃ p, p.Prime ∧ n ≤ 2 * p ∧ p < n := by
  obtain ⟨p, hp, h1, h2⟩ := Nat.exists_prime_lt_and_le_two_mul ((n - 1) / 2) (by omega)
  exact ⟨p, hp, by omega, by omega⟩

/-- E2. Duality a ↦ L / a: with a·a' = L = b·b', a' / gcd(a', b') = b / gcd(a, b),
stated without division. -/
theorem R1b.dual_quot (L a a' b b' : ℕ) (ha : a * a' = L) (hb : b * b' = L) (h0 : 0 < a) :
    a' * Nat.gcd a b = b * Nat.gcd a' b' := by
  have h1 : Nat.gcd a' b' * (a * b) = L * Nat.gcd a b := by
    rw [← Nat.gcd_mul_right]
    have e1 : a' * (a * b) = L * b := by rw [← ha]; ring
    have e2 : b' * (a * b) = L * a := by rw [← hb]; ring
    rw [e1, e2, Nat.gcd_mul_left, Nat.gcd_comm b a]
  have h2 : a * (a' * Nat.gcd a b) = a * (b * Nat.gcd a' b') := by
    rw [← mul_assoc, ha, ← h1]; ring
  exact Nat.eq_of_mul_eq_mul_left h0 h2

/-- E3. Duality preserves the strict hypothesis: the pair (a, b) of B becomes the pair
(b', a') of the dual set {L / x}. -/
theorem R1b.dual_strict (L a a' b b' n : ℕ) (ha : a * a' = L) (hb : b * b' = L) (hL : 0 < L)
    (h : a < n * Nat.gcd a b) : b' < n * Nat.gcd b' a' := by
  have hb0 : 0 < b := Nat.pos_of_ne_zero (by rintro rfl; simp at hb; omega)
  have hb'0 : 0 < b' := Nat.pos_of_ne_zero (by rintro rfl; simp at hb; omega)
  have ha0 : 0 < a := Nat.pos_of_ne_zero (by rintro rfl; simp at ha; omega)
  have e := R1b.dual_quot L b b' a a' hb ha hb0
  have hg : 0 < Nat.gcd b a := Nat.gcd_pos_of_pos_left _ hb0
  have hg' : 0 < Nat.gcd b' a' := Nat.gcd_pos_of_pos_left _ hb'0
  rw [Nat.gcd_comm a b] at h
  by_contra hcon
  push Not at hcon
  have h3 : n * Nat.gcd b' a' * Nat.gcd b a ≤ b' * Nat.gcd b a := Nat.mul_le_mul_right _ hcon
  have h4 : a * Nat.gcd b' a' < n * Nat.gcd b a * Nat.gcd b' a' := Nat.mul_lt_mul_of_pos_right h hg'
  rw [e] at h3
  nlinarith

/-- E4. The block step for an arbitrary prime: if p ∣ a and p ∤ b then p ∣ a / gcd(a, b). -/
theorem R1b.prime_dvd_quot (p a b : ℕ) (hp : p.Prime) (ha : p ∣ a) (hb : ¬ p ∣ b) :
    p ∣ a / Nat.gcd a b := by
  have h : p ∣ Nat.gcd a b * (a / Nat.gcd a b) := by
    rw [Nat.mul_div_cancel' (Nat.gcd_dvd_left a b)]; exact ha
  rcases (Nat.Prime.dvd_mul hp).mp h with h1 | h1
  · exact absurd (h1.trans (Nat.gcd_dvd_right a b)) hb
  · exact h1

/-- E5. The residue step for an arbitrary prime: if p ∤ a and a ≡ b (mod p) then the two
quotients a / gcd(a, b), b / gcd(a, b) are congruent mod p. -/
theorem R1b.quot_modEq (p a b : ℕ) (hp : p.Prime) (ha : ¬ p ∣ a) (hab : a ≡ b [MOD p]) :
    a / Nat.gcd a b ≡ b / Nat.gcd a b [MOD p] := by
  have hcop : Nat.gcd p (Nat.gcd a b) = 1 := by
    rw [← Nat.coprime_iff_gcd_eq_one]
    exact (Nat.Prime.coprime_iff_not_dvd hp).mpr (fun h => ha (h.trans (Nat.gcd_dvd_left a b)))
  apply Nat.ModEq.cancel_left_of_coprime hcop
  rw [Nat.mul_div_cancel' (Nat.gcd_dvd_left a b), Nat.mul_div_cancel' (Nat.gcd_dvd_right a b)]
  exact hab

/-- E6. Consequence: two distinct elements prime to p in one residue class mod p have a
quotient ≥ p + 1 (so in a strict counterexample of size n, p + 1 < n). -/
theorem R1b.quot_gt_of_modEq (p a b : ℕ) (hp : p.Prime) (ha : ¬ p ∣ a) (ha0 : 0 < a) (hb0 : 0 < b)
    (hne : a ≠ b) (hab : a ≡ b [MOD p]) :
    p < a / Nat.gcd a b ∨ p < b / Nat.gcd a b := by
  have h := R1b.quot_modEq p a b hp ha hab
  by_contra hcon
  push Not at hcon
  have hg : 0 < Nat.gcd a b := Nat.gcd_pos_of_pos_left _ ha0
  have hx : 0 < a / Nat.gcd a b := Nat.div_pos (Nat.le_of_dvd ha0 (Nat.gcd_dvd_left a b)) hg
  have hy : 0 < b / Nat.gcd a b := Nat.div_pos (Nat.le_of_dvd hb0 (Nat.gcd_dvd_right a b)) hg
  have hpa : ¬ p ∣ a / Nat.gcd a b := fun h' => ha (h'.trans (Nat.div_dvd_of_dvd (Nat.gcd_dvd_left a b)))
  have hxp : a / Nat.gcd a b < p := lt_of_le_of_ne hcon.1 (fun e => hpa (e ▸ dvd_rfl))
  have hpb : ¬ p ∣ b / Nat.gcd a b := fun h' => hpa ((Nat.modEq_zero_iff_dvd.mp ((h.trans (Nat.modEq_zero_iff_dvd.mpr h')))))
  have hyp : b / Nat.gcd a b < p := lt_of_le_of_ne hcon.2 (fun e => hpb (e ▸ dvd_rfl))
  have heq := Nat.ModEq.eq_of_lt_of_lt h hxp hyp
  have e1 := Nat.mul_div_cancel' (Nat.gcd_dvd_left a b)
  have e2 := Nat.mul_div_cancel' (Nat.gcd_dvd_right a b)
  exact hne (by rw [← e1, heq, e2])

/-- E7. The counting kernel used at every prime block: two sets of positive integers all of
whose cross products are below N have |X|·|T| < N. -/
theorem R1b.card_mul_card_lt (X T : Finset ℕ) (N : ℕ) (hX : 0 ∉ X) (hT : 0 ∉ T)
    (hXn : X.Nonempty) (hTn : T.Nonempty) (h : ∀ x ∈ X, ∀ t ∈ T, x * t < N) :
    X.card * T.card < N := by
  have key : ∀ (Y : Finset ℕ) (hY : Y.Nonempty), 0 ∉ Y → Y.card ≤ Y.max' hY := by
    intro Y hY h0
    have hsub : Y ⊆ Finset.Icc 1 (Y.max' hY) := by
      intro y hy
      rw [Finset.mem_Icc]
      exact ⟨Nat.pos_of_ne_zero (fun e => h0 (e ▸ hy)), Y.le_max' y hy⟩
    have := Finset.card_le_card hsub
    simpa using this
  calc X.card * T.card ≤ X.max' hXn * T.max' hTn := Nat.mul_le_mul (key X hXn hX) (key T hTn hT)
    _ < N := h _ (X.max'_mem hXn) _ (T.max'_mem hTn)
