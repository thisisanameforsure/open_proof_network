import Mathlib

/-- K2 (half): counting kernel for a prime p with 2p < n ≤ 3p. -/
theorem R2b.K2half (n p : ℕ) (X S : Finset ℕ) (hp0 : 0 < p) (h2p : 2 * p < n) (h9 : 9 ≤ n)
    (hxs : ∀ x ∈ X, ∀ s ∈ S, ∃ y, 0 < y ∧ y < n ∧ ¬ p ∣ y ∧ (x * s = 2 * y ∨ (x * s = y ∧ ¬ 2 ∣ y)))
    (hX : X.Nonempty) (hS : S.Nonempty) (hcard : n ≤ X.card + S.card) (hle : X.card ≤ S.card) :
    ∀ x ∈ X, x = 1 := by
  have big : ∀ Y : Finset ℕ, (∀ x ∈ Y, 0 < x) → Y.Nonempty → ∃ x ∈ Y, Y.card ≤ x := by
    intro Y hpos hY
    by_contra h
    push Not at h
    have hsub : Y ⊆ Finset.Ioo 0 Y.card := by
      intro x hx
      exact Finset.mem_Ioo.mpr ⟨hpos x hx, h x hx⟩
    have h1 := Finset.card_le_card hsub
    rw [Nat.card_Ioo] at h1
    have h2 := hY.card_pos
    omega
  have hXpos : ∀ x ∈ X, 0 < x := by
    intro x hx
    obtain ⟨s, hs⟩ := hS
    obtain ⟨y, hy0, -, -, h⟩ := hxs x hx s hs
    apply Nat.pos_of_ne_zero
    rintro rfl
    rw [Nat.zero_mul] at h
    omega
  have hSpos : ∀ s ∈ S, 0 < s := by
    intro s hs
    obtain ⟨x, hx⟩ := hX
    obtain ⟨y, hy0, -, -, h⟩ := hxs x hx s hs
    apply Nat.pos_of_ne_zero
    rintro rfl
    rw [Nat.mul_zero] at h
    omega
  have hmul : ∀ u v : ℕ, 4 ≤ u → 5 ≤ v → 2 * u + 2 * v ≤ u * v := by
    intro u v hu hv
    obtain ⟨a, rfl⟩ := Nat.exists_eq_add_of_le hu
    obtain ⟨b, rfl⟩ := Nat.exists_eq_add_of_le hv
    nlinarith [Nat.zero_le (a * b)]
  obtain ⟨x0, hx0, hx0c⟩ := big X hXpos hX
  obtain ⟨s0, hs0, hs0c⟩ := big S hSpos hS
  have huv : X.card * S.card < 2 * n := by
    obtain ⟨y, -, hyn, -, h⟩ := hxs x0 hx0 s0 hs0
    have h2 : X.card * S.card ≤ x0 * s0 := Nat.mul_le_mul hx0c hs0c
    omega
  have hu2 : X.card ≤ 2 := by
    by_contra h
    push Not at h
    rcases Nat.lt_or_ge X.card 4 with h4 | h4
    · have h3 : X.card = 3 := by omega
      rw [h3] at huv hcard
      omega
    · have := hmul X.card S.card h4 (by omega)
      omega
  intro x hx
  by_contra hx1
  have hxpos := hXpos x hx
  rcases Nat.lt_or_ge x 3 with h3 | h3
  · have hx2 : x = 2 := by omega
    subst hx2
    have hsub : S ⊆ ((Finset.Ioo 0 n).erase p).erase (2 * p) := by
      intro s hs
      obtain ⟨y, hy0, hyn, hpy, h⟩ := hxs 2 hx s hs
      have hsy : s = y := by omega
      subst hsy
      rw [Finset.mem_erase, Finset.mem_erase, Finset.mem_Ioo]
      refine ⟨?_, ?_, hy0, hyn⟩
      · rintro rfl; exact hpy ⟨2, by ring⟩
      · rintro rfl; exact hpy ⟨1, by ring⟩
    have h1 := Finset.card_le_card hsub
    rw [Finset.card_erase_of_mem (by
        rw [Finset.mem_erase, Finset.mem_Ioo]; omega),
      Finset.card_erase_of_mem (by rw [Finset.mem_Ioo]; omega), Nat.card_Ioo] at h1
    omega
  · have hsub : S ⊆ Finset.Icc 1 (2 * (n - 1) / 3) := by
      intro s hs
      obtain ⟨y, hy0, hyn, hpy, h⟩ := hxs x hx s hs
      have h4 : 3 * s ≤ x * s := Nat.mul_le_mul_right s h3
      rw [Finset.mem_Icc]
      exact ⟨hSpos s hs, by omega⟩
    have h1 := Finset.card_le_card hsub
    rw [Nat.card_Icc] at h1
    omega

/-- K2: both orientations. -/
theorem R2b.K2 (n p : ℕ) (X S : Finset ℕ) (hp0 : 0 < p) (h2p : 2 * p < n) (h9 : 9 ≤ n)
    (hxs : ∀ x ∈ X, ∀ s ∈ S, ∃ y, 0 < y ∧ y < n ∧ ¬ p ∣ y ∧ (x * s = 2 * y ∨ (x * s = y ∧ ¬ 2 ∣ y)))
    (hX : X.Nonempty) (hS : S.Nonempty) (hcard : n ≤ X.card + S.card) :
    (∀ x ∈ X, x = 1) ∨ (∀ s ∈ S, s = 1) := by
  rcases le_total X.card S.card with h | h
  · exact Or.inl (R2b.K2half n p X S hp0 h2p h9 hxs hX hS hcard h)
  · refine Or.inr (R2b.K2half n p S X hp0 h2p h9 ?_ hS hX (by omega) h)
    intro s hs x hx
    rw [Nat.mul_comm]
    exact hxs x hx s hs
