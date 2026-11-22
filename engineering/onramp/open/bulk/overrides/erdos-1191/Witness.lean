/-! Non-vacuity witness (D-4 step 7): the powers of two form an infinite Sidon set, since a sum of two powers of two determines the pair of exponents (parity descent). -/

theorem witness : ∃ (A : Set ℕ), A.Infinite ∧ IsSidon A := by
  have key : ∀ a b c d : ℕ, 2 ^ a + 2 ^ b = 2 ^ c + 2 ^ d → (a = c ∧ b = d) ∨ (a = d ∧ b = c) := by
    intro a
    induction a with
    | zero =>
      intro b c d h
      rcases b with _ | b <;> rcases c with _ | c <;> rcases d with _ | d <;>
        simp only [pow_zero, pow_succ] at h
      · exact Or.inl ⟨rfl, rfl⟩
      · omega
      · omega
      · have := Nat.two_pow_pos c; have := Nat.two_pow_pos d; omega
      · omega
      · have h' : 2 ^ b = 2 ^ d := by omega
        exact Or.inl ⟨rfl, congrArg Nat.succ (Nat.pow_right_injective le_rfl h')⟩
      · have h' : 2 ^ b = 2 ^ c := by omega
        exact Or.inr ⟨rfl, congrArg Nat.succ (Nat.pow_right_injective le_rfl h')⟩
      · omega
    | succ a ih =>
      intro b c d h
      rcases b with _ | b <;> rcases c with _ | c <;> rcases d with _ | d <;>
        simp only [pow_zero, pow_succ] at h
      · have := Nat.two_pow_pos a; omega
      · have h' : 2 ^ a = 2 ^ d := by omega
        exact Or.inr ⟨congrArg Nat.succ (Nat.pow_right_injective le_rfl h'), rfl⟩
      · have h' : 2 ^ a = 2 ^ c := by omega
        exact Or.inl ⟨congrArg Nat.succ (Nat.pow_right_injective le_rfl h'), rfl⟩
      · omega
      · have := Nat.two_pow_pos a; have := Nat.two_pow_pos b; omega
      · omega
      · omega
      · have h' : 2 ^ a + 2 ^ b = 2 ^ c + 2 ^ d := by omega
        rcases ih b c d h' with ⟨h1, h2⟩ | ⟨h1, h2⟩
        · exact Or.inl ⟨by omega, by omega⟩
        · exact Or.inr ⟨by omega, by omega⟩
  refine ⟨Set.range (fun n : ℕ => 2 ^ n),
    Set.infinite_range_of_injective (Nat.pow_right_injective le_rfl), ?_⟩
  rintro _ ⟨a, rfl⟩ _ ⟨c, rfl⟩ _ ⟨b, rfl⟩ _ ⟨d, rfl⟩ h
  rcases key a b c d h with ⟨h1, h2⟩ | ⟨h1, h2⟩
  · subst h1; subst h2; exact Or.inl ⟨rfl, rfl⟩
  · subst h1; subst h2; exact Or.inr ⟨rfl, rfl⟩
