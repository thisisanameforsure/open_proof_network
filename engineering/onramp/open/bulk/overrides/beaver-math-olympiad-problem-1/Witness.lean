/-! Non-vacuity witness (D-4 step 7): the two sequences defined jointly by the stated recurrences from (a 0, b 0) = (1, 2), so the four hypotheses hold by construction. -/

theorem witness : ∃ (a : ℕ → ℕ) (b : ℕ → ℕ),
  a (0 : ℕ) = (1 : ℕ) ∧
    (∀ (n : ℕ), a (n + (1 : ℕ)) = if b n ≤ a n then a n - b n else (2 : ℕ) * a n + (1 : ℕ)) ∧
      b (0 : ℕ) = (2 : ℕ) ∧ ∀ (n : ℕ), b (n + (1 : ℕ)) = if b n ≤ a n then (4 : ℕ) * b n + (2 : ℕ) else b n - a n :=
  ⟨fun n => (Nat.rec (motive := fun _ => ℕ × ℕ) ((1 : ℕ), (2 : ℕ))
      (fun _ q => if q.2 ≤ q.1 then (q.1 - q.2, 4 * q.2 + 2) else (2 * q.1 + 1, q.2 - q.1)) n).1,
   fun n => (Nat.rec (motive := fun _ => ℕ × ℕ) ((1 : ℕ), (2 : ℕ))
      (fun _ q => if q.2 ≤ q.1 then (q.1 - q.2, 4 * q.2 + 2) else (2 * q.1 + 1, q.2 - q.1)) n).2,
   rfl,
   fun n => by simp only [Nat.rec_add_one]; split_ifs <;> rfl,
   rfl,
   fun n => by simp only [Nat.rec_add_one]; split_ifs <;> rfl⟩
