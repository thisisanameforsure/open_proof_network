import Mathlib

/-- 402-R4-c. Fold class of a modulo p: the residue of the p-free part of a, up to sign. -/
def r4cCls (p a : ℕ) : ℕ :=
  min (ZMod.val ((a / p ^ a.factorization p : ℕ) : ZMod p))
    (p - ZMod.val ((a / p ^ a.factorization p : ℕ) : ZMod p))

/-- 402-R4-c. Collision lemma for one pair: both quotients below n ≤ p and equal fold classes
force a = b or reduced quotients adding up to p. -/
theorem r4c_pair (p n a b : ℕ) (hp : p.Prime) (hnp : n ≤ p) (a0 : 0 < a) (b0 : 0 < b)
    (ha : a < n * Nat.gcd a b) (hb : b < n * Nat.gcd a b) (hc : r4cCls p a = r4cCls p b) :
    a = b ∨ ∃ x y g, x + y = p ∧ Nat.Coprime x y ∧ a = x * g ∧ b = y * g := by
  haveI := Fact.mk hp
  obtain ⟨x, y, hxy, hax, hby⟩ := Nat.exists_coprime a b
  have g0 : 0 < Nat.gcd a b := Nat.gcd_pos_of_pos_left _ a0
  generalize Nat.gcd a b = g at *
  have xn : x < n := by
    rw [hax] at ha; exact Nat.lt_of_mul_lt_mul_right ha
  have yn : y < n := by
    rw [hby] at hb; exact Nat.lt_of_mul_lt_mul_right hb
  have x0 : 0 < x := by
    rcases Nat.eq_zero_or_pos x with h | h
    · subst h; omega
    · exact h
  have y0 : 0 < y := by
    rcases Nat.eq_zero_or_pos y with h | h
    · subst h; omega
    · exact h
  have key : a * y = b * x := by rw [hax, hby]; ring
  have oc : ∀ z : ℕ, 0 < z → z < p → z / p ^ z.factorization p = z := by
    intro z hz hzp
    have : ¬ p ∣ z := fun h => by have := Nat.le_of_dvd hz h; omega
    rw [Nat.factorization_eq_zero_of_not_dvd this]; simp
  have key2 : (a / p ^ a.factorization p) * y = (b / p ^ b.factorization p) * x := by
    have h := congrArg (fun m => m / p ^ m.factorization p) key
    simp only [Nat.ordCompl_mul] at h
    rwa [oc y y0 (by omega), oc x x0 (by omega)] at h
  have na : ((a / p ^ a.factorization p : ℕ) : ZMod p) ≠ 0 := by
    rw [Ne, ZMod.natCast_eq_zero_iff]; exact Nat.not_dvd_ordCompl hp (by omega)
  have nb : ((b / p ^ b.factorization p : ℕ) : ZMod p) ≠ 0 := by
    rw [Ne, ZMod.natCast_eq_zero_iff]; exact Nat.not_dvd_ordCompl hp (by omega)
  have key3 : ((a / p ^ a.factorization p : ℕ) : ZMod p) * (y : ZMod p)
      = ((b / p ^ b.factorization p : ℕ) : ZMod p) * (x : ZMod p) := by
    exact_mod_cast congrArg (Nat.cast : ℕ → ZMod p) key2
  unfold r4cCls at hc
  generalize ((a / p ^ a.factorization p : ℕ) : ZMod p) = ra at *
  generalize ((b / p ^ b.factorization p : ℕ) : ZMod p) = rb at *
  have va := ZMod.val_lt ra
  have vb := ZMod.val_lt rb
  have va0 : 0 < ra.val := (ZMod.val_pos).mpr na
  have vb0 : 0 < rb.val := (ZMod.val_pos).mpr nb
  have hcase : ra.val = rb.val ∨ ra.val + rb.val = p := by omega
  rcases hcase with h | h
  · left
    have hr : ra = rb := ZMod.val_injective p h
    rw [hr] at key3
    have h2 : (y : ZMod p) = (x : ZMod p) := mul_left_cancel₀ nb key3
    have h3 := (ZMod.natCast_eq_natCast_iff' y x p).mp h2
    rw [Nat.mod_eq_of_lt (by omega), Nat.mod_eq_of_lt (by omega)] at h3
    rw [hax, hby, h3]
  · right
    have hr : ra + rb = 0 := by
      have h4 : ((ra.val + rb.val : ℕ) : ZMod p) = ((p : ℕ) : ZMod p) := by rw [h]
      rw [Nat.cast_add, ZMod.natCast_zmod_val, ZMod.natCast_zmod_val, ZMod.natCast_self] at h4
      exact h4
    have hra : ra = -rb := eq_neg_of_add_eq_zero_left hr
    rw [hra] at key3
    have h5 : rb * ((x : ZMod p) + (y : ZMod p)) = 0 := by
      have : rb * ((x : ZMod p) + (y : ZMod p)) = rb * x - (-rb * y) := by ring
      rw [this, key3]; ring
    have h6 : ((x + y : ℕ) : ZMod p) = 0 := by
      rcases mul_eq_zero.mp h5 with h | h
      · exact (nb h).elim
      · exact_mod_cast h
    rw [ZMod.natCast_eq_zero_iff] at h6
    exact ⟨x, y, g, Nat.eq_of_dvd_of_lt_two_mul (by omega) h6 (by omega), hxy, hax, hby⟩
