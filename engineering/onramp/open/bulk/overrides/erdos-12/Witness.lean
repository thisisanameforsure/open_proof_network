/-! Non-vacuity witness (D-4 step 7): the range of f 0 = 3, f (k+1) = (f k)! + 1 is an infinite good set — every later term is ≡ 1 modulo every earlier one, so an earlier term a never divides b + c ≡ 2 (mod a) for later b, c, and the implication holds vacuously. -/

theorem witness : ∃ (A : Set ℕ), IsGood A := by
  let f : ℕ → ℕ := fun k => Nat.rec 3 (fun _ x => x.factorial + 1) k
  have hf0 : f 0 = 3 := rfl
  have hfs : ∀ k, f (k + 1) = (f k).factorial + 1 := fun k => rfl
  have hge : ∀ k, 3 ≤ f k := by
    intro k
    induction k with
    | zero => simp [hf0]
    | succ k ih => rw [hfs]; have := Nat.self_le_factorial (f k); omega
  have hmono : StrictMono f := by
    apply strictMono_nat_of_lt_succ
    intro k
    rw [hfs]
    have := Nat.self_le_factorial (f k)
    omega
  have hdvd : ∀ i d, i < d + 1 → f i ∣ (f d).factorial := fun i d hid =>
    Nat.dvd_factorial (by have := hge i; omega) (hmono.monotone (by omega))
  have hmod : ∀ i m, i < m → f m % f i = 1 := by
    intro i m him
    obtain ⟨d, rfl⟩ : ∃ d, m = d + 1 := ⟨m - 1, by omega⟩
    rw [hfs, Nat.add_mod, Nat.mod_eq_zero_of_dvd (hdvd i d him), zero_add, Nat.mod_mod,
      Nat.mod_eq_of_lt (by have := hge i; omega)]
  refine ⟨Set.range f, Set.infinite_range_of_injective hmono.injective, ?_⟩
  rintro _ ⟨i, rfl⟩ _ ⟨j, rfl⟩ _ ⟨l, rfl⟩ hdv hij hil
  exfalso
  have hij' : i < j := hmono.lt_iff_lt.1 hij
  have hil' : i < l := hmono.lt_iff_lt.1 hil
  have h1 : (f j + f l) % f i = 2 := by
    rw [Nat.add_mod, hmod i j hij', hmod i l hil', Nat.mod_eq_of_lt (by have := hge i; omega)]
  have h2 : (f j + f l) % f i = 0 := Nat.mod_eq_zero_of_dvd hdv
  omega
