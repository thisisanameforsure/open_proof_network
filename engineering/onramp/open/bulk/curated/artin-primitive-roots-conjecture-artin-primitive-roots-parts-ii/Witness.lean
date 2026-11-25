/-! Non-vacuity witness (D-4 step 7): a = 2, a_0 = 2 and b = 1 meet every hypothesis: 2 = 2 * 1 ^ 2;
2 is no power n ^ m with m ≠ 1 (m = 0 gives 1, and for m ≥ 2 the absolute value |n| ^ m is 0, 1
or at least 4); 2 is squarefree, being prime; and 2 ≢ 1 (mod 4). -/

theorem witness : ∃ (a : ℤ) (a_0 : ℤ) (b : ℤ), a = a_0 * b ^ 2 ∧
    (∀ (n : ℤ) (m : ℕ), m ≠ 1 → a ≠ n ^ m) ∧ Squarefree a_0 ∧ ¬a_0 ≡ 1 [ZMOD 4] := by
  refine ⟨2, 2, 1, by norm_num, ?_, Int.prime_two.squarefree, by decide⟩
  intro n m hm h
  have h1 : n.natAbs ^ m = 2 := by
    have := congrArg Int.natAbs h
    simpa [Int.natAbs_pow] using this.symm
  obtain ⟨k, hk⟩ : ∃ k, n.natAbs = k := ⟨_, rfl⟩
  rw [hk] at h1
  rcases Nat.lt_or_ge m 2 with h2 | h2
  · interval_cases m
    · simp at h1
    · exact hm rfl
  · rcases Nat.lt_or_ge k 2 with hk2 | hk2
    · interval_cases k
      · rw [zero_pow (by omega)] at h1
        omega
      · simp at h1
    · have : 2 ^ 2 ≤ k ^ m :=
        le_trans (Nat.pow_le_pow_left hk2 2) (Nat.pow_le_pow_right (by omega) h2)
      omega
