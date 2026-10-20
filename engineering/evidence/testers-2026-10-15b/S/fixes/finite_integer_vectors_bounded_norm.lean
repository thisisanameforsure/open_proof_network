lemma finite_integer_vectors_bounded_norm (s : ℕ) (C : ℝ) :
    Set.Finite {a : Fin s → ℤ | ∑ i : Fin s, ((a i : ℤ) : ℝ) ^ 2 ≤ C} := by
  have h_finite_components : ∀ (i : Fin s), Set.Finite {a : ℤ | (a : ℝ) ^ 2 ≤ C} := by
    exact fun i => Set.Finite.subset ( Set.finite_Icc ( -⌈C⌉₊ : ℤ ) ⌈C⌉₊ ) fun x hx => ⟨ by exact Int.le_of_lt_add_one ( by rw [ ← @Int.cast_lt ℝ ] ; push_cast; nlinarith [ hx.out, Nat.le_ceil C ] ), by exact Int.le_of_lt_add_one ( by rw [ ← @Int.cast_lt ℝ ] ; push_cast; nlinarith [ hx.out, Nat.le_ceil C ] ) ⟩ ;
  exact Set.Finite.subset ( Set.Finite.pi fun i => h_finite_components i ) fun x hx => by simpa using fun i => hx.trans' ( Finset.single_le_sum ( fun a _ => sq_nonneg ( x a : ℝ ) ) ( Finset.mem_univ i ) ) ;