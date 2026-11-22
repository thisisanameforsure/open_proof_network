/-! Non-vacuity witness (D-4 step 7): the powers of two form an infinite set in which every n has at most one representation x + y with x ≤ y (the larger summand is pinned by 2^b ≤ n < 2^(b+1)), so it is B₂[2]. -/

theorem witness : ∃ (A : Set ℕ), A.Infinite ∧ Erdos158.B2 (2 : ℕ) A :=
  ⟨Set.range (fun k : ℕ => 2 ^ k), Set.infinite_range_of_injective (Nat.pow_right_injective le_rfl), fun n => by
    have h1 : ∀ a b c d : ℕ, a ≤ b → c ≤ d → 2 ^ a + 2 ^ b = 2 ^ c + 2 ^ d → b ≤ d := by
      intro a b c d hab hcd h
      have hcd' : 2 ^ c ≤ 2 ^ d := Nat.pow_le_pow_right (by norm_num) hcd
      have ha : 1 ≤ 2 ^ a := Nat.one_le_two_pow
      have hlt : 2 ^ b < 2 ^ (d + 1) := by rw [pow_succ]; omega
      exact Nat.lt_succ_iff.mp ((Nat.pow_lt_pow_iff_right (by norm_num)).mp hlt)
    have key : ∀ a b c d : ℕ, a ≤ b → c ≤ d → 2 ^ a + 2 ^ b = 2 ^ c + 2 ^ d → a = c ∧ b = d := by
      intro a b c d hab hcd h
      have hbd : b = d := le_antisymm (h1 a b c d hab hcd h) (h1 c d a b hcd hab h.symm)
      subst hbd
      exact ⟨Nat.pow_right_injective le_rfl (by simpa using (by omega : 2 ^ a = 2 ^ c)), rfl⟩
    refine le_trans ?_ (by exact_mod_cast (by norm_num : (1 : ℕ) ≤ 2))
    rw [Set.encard_le_one_iff]
    rintro ⟨x1, x2⟩ ⟨y1, y2⟩ ⟨hx, hx12, ⟨a, rfl⟩, ⟨b, rfl⟩⟩ ⟨hy, hy12, ⟨c, rfl⟩, ⟨d, rfl⟩⟩
    obtain ⟨rfl, rfl⟩ := key a b c d ((Nat.pow_le_pow_iff_right (by norm_num)).mp hx12)
      ((Nat.pow_le_pow_iff_right (by norm_num)).mp hy12) (by simp only at hx hy; omega)
    rfl⟩
