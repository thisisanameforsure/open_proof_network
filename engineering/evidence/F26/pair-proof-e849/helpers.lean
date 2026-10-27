private theorem step_lt (n k : ℕ) (h : 2 * (k + 1) ≤ n) : Nat.choose n k < Nat.choose n (k + 1) := by
  have e := Nat.choose_succ_right_eq n k
  have hp : 0 < Nat.choose n k := Nat.choose_pos (by omega)
  have hk : k + 1 < n - k := by omega
  by_contra hc
  push_neg at hc
  have : Nat.choose n k * (n - k) ≤ Nat.choose n k * (k + 1) := by
    calc Nat.choose n k * (n - k) = Nat.choose n (k + 1) * (k + 1) := e.symm
      _ ≤ Nat.choose n k * (k + 1) := Nat.mul_le_mul_right _ hc
  have := Nat.le_of_mul_le_mul_left this hp
  omega

private theorem mono_lt (n : ℕ) :
    ∀ j i : ℕ, i < j → 2 * j ≤ n → Nat.choose n i < Nat.choose n j := by
  intro j
  induction j with
  | zero => intro i h; omega
  | succ j ih =>
    intro i hij hj
    have hs := step_lt n j hj
    rcases Nat.lt_succ_iff_lt_or_eq.mp hij with h | h
    · exact lt_trans (ih i h (by omega)) hs
    · subst h; exact hs

private theorem row_unique (n k₁ k₂ : ℕ) (h₁ : 2 * k₁ ≤ n) (h₂ : 2 * k₂ ≤ n)
    (h : Nat.choose n k₁ = Nat.choose n k₂) : k₁ = k₂ := by
  rcases lt_trichotomy k₁ k₂ with hl | he | hg
  · have := mono_lt n k₂ k₁ hl h₂; omega
  · exact he
  · have := mono_lt n k₁ k₂ hg h₁; omega

private theorem rows_eq_pairs (a : ℕ) :
    {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ Nat.choose n k = a}.ncard =
      {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ Nat.choose p.1 p.2 = a}.ncard := by
  have himg : (Prod.fst '' {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ Nat.choose p.1 p.2 = a}) =
      {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ Nat.choose n k = a} := by
    ext n
    simp only [Set.mem_image, Set.mem_setOf_eq, Prod.exists]
    constructor
    · rintro ⟨m, k, ⟨hk, hkm, hc⟩, rfl⟩
      exact ⟨k, hk, hkm, hc⟩
    · rintro ⟨k, hk, hkn, hc⟩
      exact ⟨n, k, ⟨hk, hkn, hc⟩, rfl⟩
  rw [← himg]
  apply Set.ncard_image_of_injOn
  rintro ⟨n₁, k₁⟩ ⟨hk₁, hkn₁, hc₁⟩ ⟨n₂, k₂⟩ ⟨hk₂, hkn₂, hc₂⟩ hn
  simp only at hn hk₁ hkn₁ hc₁ hk₂ hkn₂ hc₂
  subst hn
  have := row_unique n₁ k₁ k₂ hkn₁ hkn₂ (hc₁.trans hc₂.symm)
  subst this
  rfl

private theorem rows_le (a : ℕ) :
    {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ Nat.choose n k = a} ⊆ Set.Icc 2 a := by
  rintro n ⟨k, hk, hkn, rfl⟩
  refine ⟨by omega, ?_⟩
  rcases Nat.lt_or_ge 1 k with h | h
  · have := mono_lt n k 1 h hkn
    rw [Nat.choose_one_right] at this
    omega
  · have : k = 1 := by omega
    subst this
    rw [Nat.choose_one_right]

private theorem pairs_finite (a : ℕ) :
    {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ Nat.choose p.1 p.2 = a}.Finite := by
  apply (Set.finite_Icc ((0:ℕ), (0:ℕ)) (a, a)).subset
  rintro ⟨n, k⟩ ⟨hk, hkn, hc⟩
  have hn : n ∈ Set.Icc 2 a := rows_le a ⟨k, hk, hkn, hc⟩
  simp only [Set.mem_Icc, Prod.mk_le_mk] at hn ⊢
  omega

private theorem key (a : ℕ) :
    {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ Nat.choose p.1 p.2 = a}.encard =
      ({n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ Nat.choose n k = a}.ncard : ℕ∞) := by
  rw [rows_eq_pairs a, (pairs_finite a).cast_ncard_eq]
