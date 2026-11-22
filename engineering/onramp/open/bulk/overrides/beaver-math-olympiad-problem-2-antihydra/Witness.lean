/-! Non-vacuity witness (D-4 step 7): the sequences a and b defined by the stated recursions from a 0 = 8 and b 0 = 0, at n = 0. -/

theorem witness : ∃ (a : ℕ → ℕ) (b : ℕ → ℤ) (n : ℕ),
  a (0 : ℕ) = (8 : ℕ) ∧
    (∀ (n : ℕ), a (n + (1 : ℕ)) = (3 : ℕ) * a n / (2 : ℕ)) ∧
      b (0 : ℕ) = (0 : ℤ) ∧
        ∀ (n : ℕ), b (n + (1 : ℕ)) = if a n % (2 : ℕ) = (0 : ℕ) then b n + (2 : ℤ) else b n - (1 : ℤ) :=
  ⟨fun n => Nat.rec (motive := fun _ => ℕ) 8 (fun _ x => 3 * x / 2) n,
   fun n => Nat.rec (motive := fun _ => ℤ) 0
     (fun k y => if (Nat.rec (motive := fun _ => ℕ) 8 (fun _ x => 3 * x / 2) k) % 2 = 0 then y + 2 else y - 1) n,
   0, rfl, fun _ => rfl, rfl, fun _ => rfl⟩
