import Mathlib
import Defs.Construction

open scoped ArithmeticFunction.omega

/-- h2 (coprimality): for `7^M ≤ P` every prime factor of a dilation is coprime to its step. -/
theorem erdos_69__h2 : ∀ (M P : ℕ), 7 ^ M ≤ P → ∀ (d : Fin M → Fin 6),
    ∀ p ∈ (Opn.E69.dil M P d).primeFactors, Nat.Coprime p (Opn.E69.step M P d) := by
  intro M P hP
  -- shared lemma (inline): distinct dilations are coprime
  have cop : ∀ d d' : Fin M → Fin 6, d ≠ d' →
      Nat.Coprime (Opn.E69.dil M P d) (Opn.E69.dil M P d') := by
    -- base-7 numbers below 7^n
    have bound : ∀ (n : ℕ) (f : Fin n → ℕ), (∀ r, f r < 7) →
        ∑ r : Fin n, 7 ^ (r : ℕ) * f r < 7 ^ n := by
      intro n f hf
      have h1 : ∑ r : Fin n, 7 ^ (r : ℕ) * f r ≤ ∑ r : Fin n, 7 ^ (r : ℕ) * 6 :=
        Finset.sum_le_sum fun r _ => Nat.mul_le_mul_left _ (Nat.lt_succ_iff.mp (hf r))
      have h2 : ∑ r : Fin n, 7 ^ (r : ℕ) * 6 = ∑ r ∈ Finset.range n, 7 ^ r * 6 :=
        Fin.sum_univ_eq_sum_range (fun r => 7 ^ r * 6) n
      have h3 : ∀ k : ℕ, ∑ r ∈ Finset.range k, 7 ^ r * 6 + 1 = 7 ^ k := by
        intro k
        induction k with
        | zero => simp
        | succ k ih => rw [Finset.sum_range_succ, pow_succ]; omega
      have := h3 n
      omega
    -- base-7 digits are unique
    have digits : ∀ (n : ℕ) (f f' : Fin n → ℕ), (∀ r, f r < 7) → (∀ r, f' r < 7) →
        ∑ r : Fin n, 7 ^ (r : ℕ) * f r = ∑ r : Fin n, 7 ^ (r : ℕ) * f' r → f = f' := by
      intro n
      induction n with
      | zero => intro f f' _ _ _; funext r; exact r.elim0
      | succ n ih =>
        intro f f' hf hf' h
        rw [Fin.sum_univ_castSucc, Fin.sum_univ_castSucc] at h
        simp only [Fin.val_castSucc, Fin.val_last] at h
        have hA := bound n (fun r => f r.castSucc) (fun r => hf _)
        have hA' := bound n (fun r => f' r.castSucc) (fun r => hf' _)
        have hmod := congrArg (· % 7 ^ n) h
        simp only [Nat.add_mul_mod_self_left, Nat.mod_eq_of_lt hA, Nat.mod_eq_of_lt hA'] at hmod
        have hlast : f (Fin.last n) = f' (Fin.last n) := by
          have h7 : 7 ^ n * f (Fin.last n) = 7 ^ n * f' (Fin.last n) := by omega
          exact Nat.eq_of_mul_eq_mul_left (by positivity) h7
        have hrest := ih (fun r => f r.castSucc) (fun r => f' r.castSucc)
          (fun r => hf _) (fun r => hf' _) hmod
        funext r
        refine Fin.lastCases hlast (fun i => ?_) r
        exact congrFun hrest i
    have hdig : ∀ (r : ℕ) (k : Fin 6), Opn.E69.gDigit r k < 7 := by
      intro r k
      unfold Opn.E69.gDigit
      split_ifs <;> fin_cases k <;> simp
    have hinj : ∀ (r : ℕ) (k k' : Fin 6), Opn.E69.gDigit r k = Opn.E69.gDigit r k' → k = k' := by
      intro r k k'
      unfold Opn.E69.gDigit
      split_ifs <;> revert k k' <;> decide
    -- two numbers of the form 1 + P#(1 + x), x < y ≤ P, share no prime
    have noprime : ∀ (p x y : ℕ), p.Prime → x < y → y ≤ P →
        p ∣ 1 + primorial P * (1 + x) → p ∣ 1 + primorial P * (1 + y) → False := by
      intro p x y hp hxy hyP hx hy
      obtain ⟨k, rfl⟩ := Nat.exists_eq_add_of_lt hxy
      have hsub : p ∣ primorial P * (k + 1) := by
        have h := Nat.dvd_sub hy hx
        have e : 1 + primorial P * (1 + (x + k + 1)) - (1 + primorial P * (1 + x))
            = primorial P * (k + 1) := by
          apply Nat.sub_eq_of_eq_add; ring
        rwa [e] at h
      have hpP : p ∣ primorial P := by
        rcases hp.dvd_mul.mp hsub with h | h
        · exact h
        · have hle : p ≤ P := le_trans (Nat.le_of_dvd (Nat.succ_pos k) h) (by omega)
          unfold primorial
          exact Finset.dvd_prod_of_mem _ (by simp [hp, hle])
      have h1 : p ∣ 1 := (Nat.dvd_add_left (Dvd.dvd.mul_right hpP (1 + x))).mp hx
      exact hp.one_lt.ne' (Nat.dvd_one.mp h1)
    intro d d' hne
    have hg : Opn.E69.gIndex M d ≠ Opn.E69.gIndex M d' := by
      intro h
      apply hne
      have hf := digits M (fun r => Opn.E69.gDigit r (d r)) (fun r => Opn.E69.gDigit r (d' r))
        (fun r => hdig _ _) (fun r => hdig _ _) h
      funext r
      exact hinj r _ _ (congrFun hf r)
    have hb : ∀ e : Fin M → Fin 6, Opn.E69.gIndex M e ≤ P := fun e =>
      le_trans (bound M (fun r => Opn.E69.gDigit r (e r)) (fun r => hdig _ _)).le hP
    by_contra hc
    obtain ⟨p, hp, h1, h2⟩ := Nat.Prime.not_coprime_iff_dvd.mp hc
    rcases Nat.lt_or_gt_of_ne hg with hlt | hlt
    · exact noprime p _ _ hp hlt (hb d') h1 h2
    · exact noprime p _ _ hp hlt (hb d) h2 h1
  intro d p hp
  have hpd : p ∣ Opn.E69.dil M P d := Nat.dvd_of_mem_primeFactors hp
  have hpos : 0 < Opn.E69.dil M P d := by unfold Opn.E69.dil; omega
  have hstep : Opn.E69.step M P d
      = ∏ d' ∈ Finset.univ.erase d, Opn.E69.dil M P d' := by
    unfold Opn.E69.step Opn.E69.modulus
    rw [← Finset.mul_prod_erase Finset.univ (fun e => Opn.E69.dil M P e) (Finset.mem_univ d)]
    exact Nat.mul_div_cancel_left _ hpos
  rw [hstep]
  refine Nat.Coprime.prod_right fun d' hd' => ?_
  exact Nat.Coprime.coprime_dvd_left hpd (cop d d' (Finset.ne_of_mem_erase hd').symm)
