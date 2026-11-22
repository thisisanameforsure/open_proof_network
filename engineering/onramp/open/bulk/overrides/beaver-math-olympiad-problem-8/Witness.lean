/-! Non-vacuity witness (D-4 step 7): the pair of sequences defined by recursion from (10, 12) with the stated update rule satisfies all four hypotheses by definitional unfolding. -/

theorem witness : ∃ (a : ℕ → ℤ) (b : ℕ → ℤ),
  a (0 : ℕ) = (10 : ℤ) ∧
    (∀ (n : ℕ),
        a (n + (1 : ℕ)) = if b n / (2 : ℤ) < a n then a n - b n / (2 : ℤ) - (3 : ℤ) else (3 : ℤ) * a n + (5 : ℤ)) ∧
      b (0 : ℕ) = (12 : ℤ) ∧
        ∀ (n : ℕ),
          b (n + (1 : ℕ)) =
            if b n / (2 : ℤ) < a n then (3 : ℤ) * ((b n + (1 : ℤ)) / (2 : ℤ)) + (6 : ℤ) else b n - (2 : ℤ) * a n := by
  let p : ℕ → ℤ × ℤ := fun n => Nat.rec (motive := fun _ => ℤ × ℤ) ((10 : ℤ), (12 : ℤ))
    (fun _ q => (if q.2 / 2 < q.1 then q.1 - q.2 / 2 - 3 else 3 * q.1 + 5,
                 if q.2 / 2 < q.1 then 3 * ((q.2 + 1) / 2) + 6 else q.2 - 2 * q.1)) n
  exact ⟨fun n => (p n).1, fun n => (p n).2, rfl, fun _ => rfl, rfl, fun _ => rfl⟩
