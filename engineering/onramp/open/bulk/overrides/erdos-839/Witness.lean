/-! Non-vacuity witness (D-4 step 7): the powers of two: each is at least 1, they increase strictly, and no 2^i equals a sum of earlier consecutive terms because every such sum is below 2^i. -/

theorem witness : ∃ (a : ℕ → ℕ), (∀ (n : ℕ), (1 : ℕ) ≤ a n) ∧ StrictMono a ∧ Erdos839.SumOfConsecutiveFree a :=
  ⟨fun n => 2 ^ n, fun n => Nat.one_le_two_pow, fun a b h => Nat.pow_lt_pow_right (by norm_num) h,
    fun i j k _ hk => by
      show 2 ^ i ≠ ∑ l ∈ Finset.Icc j k, 2 ^ l
      have := Nat.geomSum_lt (m := 2) (n := i) (s := Finset.Icc j k) le_rfl
        (fun l hl => by have := (Finset.mem_Icc.mp hl).2; omega)
      omega⟩
