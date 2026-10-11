import Mathlib
import Defs.Construction

/-- h4a (exact cancellation), general even `M`: at every depth `1 ≤ u ≤ 3M` the signed number of
lines through any point is zero. Proof: depth `u` belongs to exactly one triple `r < M`; a
sign-reversing involution of the six lines of that triple preserves the point at depth `u`. -/
theorem erdos_69__h4__h1 : ∀ (M P u x : ℕ), Even M → 1 ≤ u → u ≤ 3 * M →
    ∑ d ∈ Finset.univ.filter (fun d : Fin M → Fin 6 =>
      Opn.E69.shift M P d + Opn.E69.dil M P d * u = x), Opn.E69.sign M d = 0 := by
  intro M P u x hM hu1 hu2
  -- the tables: at each depth of triple `r` the six lines pair off with opposite signs
  have pair : ∀ r u : ℕ,
      ((r % 2 = 0 ∧ (u = 3 * r + 1 ∨ u = 3 * r + 2 ∨ u = 3 * r + 4)) ∨
        (r % 2 = 1 ∧ (u = 3 * r ∨ u = 3 * r + 2 ∨ u = 3 * r + 3))) →
      ∃ π : Fin 6 → Fin 6, (∀ k, π (π k) = k) ∧
        (∀ k, (-1 : ℤ) ^ ((π k : Fin 6) : ℕ) = -(-1) ^ ((k : Fin 6) : ℕ)) ∧
        ∀ k, Opn.E69.sDigit r (π k) + Opn.E69.gDigit r (π k) * u
          = Opn.E69.sDigit r k + Opn.E69.gDigit r k * u := by
    intro r u h
    rcases h with ⟨hr, h | h | h⟩ | ⟨hr, h | h | h⟩
    · refine ⟨![1, 0, 5, 4, 3, 2], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
    · refine ⟨![5, 4, 3, 2, 1, 0], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
    · refine ⟨![3, 2, 1, 0, 5, 4], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
    · have hr' : ¬ r % 2 = 0 := by omega
      refine ⟨![1, 0, 5, 4, 3, 2], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
    · have hr' : ¬ r % 2 = 0 := by omega
      refine ⟨![5, 4, 3, 2, 1, 0], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
    · have hr' : ¬ r % 2 = 0 := by omega
      refine ⟨![3, 2, 1, 0, 5, 4], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
  -- every depth `1 ≤ u ≤ 3M` (M even) lies in a triple `r < M`
  have cover : ∃ r : ℕ, r < M ∧
      ((r % 2 = 0 ∧ (u = 3 * r + 1 ∨ u = 3 * r + 2 ∨ u = 3 * r + 4)) ∨
        (r % 2 = 1 ∧ (u = 3 * r ∨ u = 3 * r + 2 ∨ u = 3 * r + 3))) := by
    obtain ⟨N, rfl⟩ := hM
    have hb : (u - 1) % 6 < 6 := Nat.mod_lt _ (by norm_num)
    by_cases h0 : (u - 1) % 6 = 0 ∨ (u - 1) % 6 = 1 ∨ (u - 1) % 6 = 3
    · exact ⟨2 * ((u - 1) / 6), by omega, by omega⟩
    · exact ⟨2 * ((u - 1) / 6) + 1, by omega, by omega⟩
  obtain ⟨r, hrM, hr⟩ := cover
  obtain ⟨π, hπ, hsgn, hpt⟩ := pair r u hr
  set r0 : Fin M := ⟨r, hrM⟩ with hr0
  set φ : (Fin M → Fin 6) → (Fin M → Fin 6) := fun d => Function.update d r0 (π (d r0)) with hφ
  have hinv : Function.Involutive φ := by
    intro d
    funext i
    by_cases hi : i = r0
    · subst hi; simp [hφ, hπ]
    · simp [hφ, Function.update_of_ne hi]
  have hφr : ∀ d, φ d r0 = π (d r0) := fun d => by simp [hφ]
  have hφne : ∀ d, ∀ i ∈ (Finset.univ : Finset (Fin M)).erase r0, φ d i = d i := by
    intro d i hi
    have : i ≠ r0 := (Finset.mem_erase.mp hi).1
    simp [hφ, Function.update_of_ne this]
  have hmem : r0 ∈ (Finset.univ : Finset (Fin M)) := Finset.mem_univ _
  have hsign : ∀ d, Opn.E69.sign M (φ d) = -Opn.E69.sign M d := by
    intro d
    unfold Opn.E69.sign
    rw [← Finset.mul_prod_erase _ _ hmem, ← Finset.mul_prod_erase _ (fun i => (-1 : ℤ) ^ ((d i : Fin 6) : ℕ)) hmem,
      hφr, hsgn, Finset.prod_congr rfl (fun i hi => by rw [hφne d i hi])]
    ring
  have hkey : ∀ d, Opn.E69.sIndex M (φ d) + Opn.E69.gIndex M (φ d) * u
      = Opn.E69.sIndex M d + Opn.E69.gIndex M d * u := by
    intro d
    have hs : ∀ e : Fin M → Fin 6, Opn.E69.sIndex M e = 7 ^ r * Opn.E69.sDigit r (e r0)
        + ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.sDigit i (e i) :=
      fun e => (Finset.add_sum_erase _ (fun i : Fin M => 7 ^ (i : ℕ) * Opn.E69.sDigit i (e i)) hmem).symm
    have hg : ∀ e : Fin M → Fin 6, Opn.E69.gIndex M e = 7 ^ r * Opn.E69.gDigit r (e r0)
        + ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.gDigit i (e i) :=
      fun e => (Finset.add_sum_erase _ (fun i : Fin M => 7 ^ (i : ℕ) * Opn.E69.gDigit i (e i)) hmem).symm
    have hRs : ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.sDigit i (φ d i)
        = ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.sDigit i (d i) :=
      Finset.sum_congr rfl (fun i hi => by rw [hφne d i hi])
    have hRg : ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.gDigit i (φ d i)
        = ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.gDigit i (d i) :=
      Finset.sum_congr rfl (fun i hi => by rw [hφne d i hi])
    have e : ∀ a b R R' : ℕ, 7 ^ r * a + R + (7 ^ r * b + R') * u
        = 7 ^ r * (a + b * u) + (R + R' * u) := by intros; ring
    rw [hs (φ d), hs d, hg (φ d), hg d, hRs, hRg, hφr, e, e, hpt]
  have hpred : ∀ d, (Opn.E69.shift M P (φ d) + Opn.E69.dil M P (φ d) * u = x)
      ↔ (Opn.E69.shift M P d + Opn.E69.dil M P d * u = x) := by
    intro d
    have e : ∀ s g : ℕ, primorial P * s + (1 + primorial P * (1 + g)) * u
        = primorial P * (s + g * u) + (u + primorial P * u) := by intros; ring
    unfold Opn.E69.shift Opn.E69.dil
    rw [e, e, hkey d]
  rw [Finset.sum_filter]
  have hS : ∑ d : Fin M → Fin 6, (if Opn.E69.shift M P d + Opn.E69.dil M P d * u = x
        then Opn.E69.sign M d else 0)
      = ∑ d : Fin M → Fin 6, (if Opn.E69.shift M P (φ d) + Opn.E69.dil M P (φ d) * u = x
        then Opn.E69.sign M (φ d) else 0) :=
    (Equiv.sum_comp (hinv.toPerm φ) (fun d => if Opn.E69.shift M P d + Opn.E69.dil M P d * u = x
        then Opn.E69.sign M d else 0)).symm
  have hN : ∑ d : Fin M → Fin 6, (if Opn.E69.shift M P (φ d) + Opn.E69.dil M P (φ d) * u = x
        then Opn.E69.sign M (φ d) else 0)
      = -∑ d : Fin M → Fin 6, (if Opn.E69.shift M P d + Opn.E69.dil M P d * u = x
        then Opn.E69.sign M d else 0) := by
    rw [← Finset.sum_neg_distrib]
    refine Finset.sum_congr rfl fun d _ => ?_
    simp only [hpred d, hsign d]
    split_ifs <;> simp
  linarith
