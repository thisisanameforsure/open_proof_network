/-! Non-vacuity witness (D-4 step 7): the sequences a, b are built by primitive recursion on the pair (a n, b n) from (0, 5) with the stated step, and f is the stated function. -/

theorem witness : ∃ (a : ℕ → ℕ) (b : ℕ → ℕ) (f : ℕ → ℕ),
  (f = fun (x : ℕ) => (10 : ℕ) * (2 : ℕ) ^ x - (1 : ℕ)) ∧
    a (0 : ℕ) = (0 : ℕ) ∧
      b (0 : ℕ) = (5 : ℕ) ∧
        (∀ (n : ℕ), a (n + (1 : ℕ)) = if f (a n) ≤ b n then a n + (1 : ℕ) else a n) ∧
          ∀ (n : ℕ), b (n + (1 : ℕ)) = if f (a n) ≤ b n then b n - f (a n) else (3 : ℕ) * b n + a n + (5 : ℕ) := by
  let f : ℕ → ℕ := fun x => 10 * 2 ^ x - 1
  let s : ℕ → ℕ × ℕ := fun n => Nat.rec (motive := fun _ => ℕ × ℕ) (0, 5)
    (fun _ p => if f p.1 ≤ p.2 then (p.1 + 1, p.2 - f p.1) else (p.1, 3 * p.2 + p.1 + 5)) n
  refine ⟨fun n => (s n).1, fun n => (s n).2, f, rfl, rfl, rfl, fun n => ?_, fun n => ?_⟩
  · change (if f (s n).1 ≤ (s n).2 then ((s n).1 + 1, (s n).2 - f (s n).1)
      else ((s n).1, 3 * (s n).2 + (s n).1 + 5)).1 = _
    split_ifs <;> rfl
  · change (if f (s n).1 ≤ (s n).2 then ((s n).1 + 1, (s n).2 - f (s n).1)
      else ((s n).1, 3 * (s n).2 + (s n).1 + 5)).2 = _
    split_ifs <;> rfl
