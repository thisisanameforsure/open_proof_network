/-! Non-vacuity witness (D-4 step 7): the sequence starting at 2 in which each prime is followed by a larger prime congruent to 1 modulo it (Dirichlet's theorem for residue 1). -/

theorem witness : ∃ (q : ℕ → ℕ), StrictMono q ∧ (∀ (i : ℕ), Nat.Prime (q i)) ∧ ∀ (i : ℕ), q (i + (1 : ℕ)) % q i = (1 : ℕ) := by
  have h : ∀ p : ℕ, p.Prime → ∃ r, r.Prime ∧ p < r ∧ r ≡ 1 [MOD p] :=
    fun p hp => Nat.exists_prime_gt_modEq_one p hp.ne_zero
  choose f hf using h
  let q : ℕ → {p : ℕ // p.Prime} :=
    fun n => Nat.rec (motive := fun _ => {p : ℕ // p.Prime}) ⟨2, Nat.prime_two⟩
      (fun _ x => ⟨f x.1 x.2, (hf x.1 x.2).1⟩) n
  refine ⟨fun n => (q n).1, strictMono_nat_of_lt_succ (fun n => (hf (q n).1 (q n).2).2.1),
    fun n => (q n).2, fun n => ?_⟩
  have hm := (hf (q n).1 (q n).2).2.2
  rw [Nat.ModEq, Nat.mod_eq_of_lt (q n).2.one_lt] at hm
  exact hm
