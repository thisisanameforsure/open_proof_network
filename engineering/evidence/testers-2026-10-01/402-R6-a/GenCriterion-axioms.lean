import Mathlib

/-- 402-R5-b. Generalised prime criterion for Graham's gcd problem (one declaration). The window
condition (2n − p)² ≤ n of 402-R4-c's r4c_criterion_single is replaced by what the rectangle lemma
actually uses: every α in the window (p − n, n) either lies in a shape {α, p − α} that carries a prime
q ≥ n/3 (second disjunct of the conclusion) or has no divisor pair x < y, x·y ∣ α, with α·y < n·x. -/
theorem r5b_gen_criterion : ∀ (A : Finset ℕ), 0 ∉ A → ∀ p : ℕ, p.Prime → A.card < p →
    p < 2 * A.card → 2 * (2 * A.card - p) ≤ A.card + 2 →
    (∀ α : ℕ, α < A.card → p < α + A.card →
      (∃ q : ℕ, q.Prime ∧ A.card ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
      (∀ x y : ℕ, x < y → x * y ∣ α → A.card * x ≤ α * y)) →
    (∃ a ∈ A, ∃ b ∈ A, (a.gcd b : ℚ) ≤ (a : ℚ) / (A.card : ℚ)) ∨
      ∃ q : ℕ, q.Prime ∧ A.card ≤ 3 * q ∧ ∃ a ∈ A, q ∣ a := by
  obtain ⟨cls, hcls⟩ : ∃ cls : ℕ → ℕ → ℕ, ∀ p a, cls p a =
      min (ZMod.val ((a / p ^ a.factorization p : ℕ) : ZMod p))
        (p - ZMod.val ((a / p ^ a.factorization p : ℕ) : ZMod p)) := ⟨_, fun _ _ => rfl⟩

  -- 402-R5-b. Arithmetic heart, generalised: the divisor-gap hypothesis on α is exactly what is needed.
  have r4c_arith (n α e1 e2 : ℕ) (hg : ∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y)
      (he : e1 * e2 ∣ α) (h1 : α * e1 < n * e2) (h4 : α * e2 < n * e1) : e1 = e2 := by
    rcases Nat.lt_trichotomy e1 e2 with h | h | h
    · have := hg e1 e2 h he
      omega
    · exact h
    · have := hg e2 e1 h (by rwa [Nat.mul_comm])
      omega

  -- 402-R4-c. Rectangle lemma, coprime core: α, β coprime and both within k of n (k² ≤ n), d1, d2
  -- coprime; if all four cross quotients of {α d1, β d1, α d2, β d2} are below n then d1 = d2 = 1.
  have r4c_rect_core (n α β d1 d2 : ℕ) (gα : (∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y)) (gβ : (∀ x y : ℕ, x < y → x * y ∣ β → n * x ≤ β * y))
      (tα : n ≤ 2 * α)
      (α0 : 0 < α) (β0 : 0 < β) (hαβ : Nat.Coprime α β) (hd : Nat.Coprime d1 d2)
      (h1 : 0 < d1) (h2 : 0 < d2)
      (H1 : α * d1 < n * Nat.gcd (α * d1) (β * d2)) (H2 : β * d2 < n * Nat.gcd (α * d1) (β * d2))
      (H3 : β * d1 < n * Nat.gcd (β * d1) (α * d2)) (H4 : α * d2 < n * Nat.gcd (β * d1) (α * d2)) :
      d1 = 1 ∧ d2 = 1 := by
    have e1p : 0 < Nat.gcd α d1 := Nat.gcd_pos_of_pos_left _ α0
    have e2p : 0 < Nat.gcd α d2 := Nat.gcd_pos_of_pos_left _ α0
    have f1p : 0 < Nat.gcd β d1 := Nat.gcd_pos_of_pos_left _ β0
    have f2p : 0 < Nat.gcd β d2 := Nat.gcd_pos_of_pos_left _ β0
    have hG : Nat.gcd (α * d1) (β * d2) ≤ Nat.gcd α d2 * Nat.gcd β d1 := by
      apply Nat.le_of_dvd (Nat.mul_pos e2p f1p)
      have h := Nat.gcd_mul_right_dvd_mul_gcd (α * d1) β d2
      rw [Nat.Coprime.gcd_mul_left_cancel d1 hαβ, Nat.Coprime.gcd_mul_right_cancel α hd] at h
      rw [Nat.gcd_comm d1 β, Nat.mul_comm (β.gcd d1)] at h; exact h
    have hG' : Nat.gcd (β * d1) (α * d2) ≤ Nat.gcd α d1 * Nat.gcd β d2 := by
      apply Nat.le_of_dvd (Nat.mul_pos e1p f2p)
      have h := Nat.gcd_mul_right_dvd_mul_gcd (β * d1) α d2
      rw [Nat.Coprime.gcd_mul_left_cancel d1 hαβ.symm, Nat.Coprime.gcd_mul_right_cancel β hd] at h
      rw [Nat.gcd_comm d1 α] at h; exact h
    have ce : Nat.Coprime (Nat.gcd α d1) (Nat.gcd α d2) :=
      Nat.Coprime.coprime_dvd_left (Nat.gcd_dvd_right _ _)
        (Nat.Coprime.coprime_dvd_right (Nat.gcd_dvd_right _ _) hd)
    have cf : Nat.Coprime (Nat.gcd β d1) (Nat.gcd β d2) :=
      Nat.Coprime.coprime_dvd_left (Nat.gcd_dvd_right _ _)
        (Nat.Coprime.coprime_dvd_right (Nat.gcd_dvd_right _ _) hd)
    have c1 : Nat.Coprime (Nat.gcd α d1) (Nat.gcd β d1) :=
      Nat.Coprime.coprime_dvd_left (Nat.gcd_dvd_left _ _)
        (Nat.Coprime.coprime_dvd_right (Nat.gcd_dvd_left _ _) hαβ)
    have c2 : Nat.Coprime (Nat.gcd α d2) (Nat.gcd β d2) :=
      Nat.Coprime.coprime_dvd_left (Nat.gcd_dvd_left _ _)
        (Nat.Coprime.coprime_dvd_right (Nat.gcd_dvd_left _ _) hαβ)
    have m1 : Nat.gcd α d1 * Nat.gcd β d1 ≤ d1 := Nat.le_of_dvd h1
      (Nat.Coprime.mul_dvd_of_dvd_of_dvd c1 (Nat.gcd_dvd_right _ _) (Nat.gcd_dvd_right _ _))
    have m2 : Nat.gcd α d2 * Nat.gcd β d2 ≤ d2 := Nat.le_of_dvd h2
      (Nat.Coprime.mul_dvd_of_dvd_of_dvd c2 (Nat.gcd_dvd_right _ _) (Nat.gcd_dvd_right _ _))
    have mα : Nat.gcd α d1 * Nat.gcd α d2 ∣ α :=
      Nat.Coprime.mul_dvd_of_dvd_of_dvd ce (Nat.gcd_dvd_left _ _) (Nat.gcd_dvd_left _ _)
    have mβ : Nat.gcd β d1 * Nat.gcd β d2 ∣ β :=
      Nat.Coprime.mul_dvd_of_dvd_of_dvd cf (Nat.gcd_dvd_left _ _) (Nat.gcd_dvd_left _ _)
    generalize Nat.gcd α d1 = e1 at *
    generalize Nat.gcd α d2 = e2 at *
    generalize Nat.gcd β d1 = f1 at *
    generalize Nat.gcd β d2 = f2 at *
    generalize Nat.gcd (α * d1) (β * d2) = G at *
    generalize Nat.gcd (β * d1) (α * d2) = G' at *
    have i1 : α * e1 < n * e2 := by
      have a : α * (e1 * f1) ≤ α * d1 := Nat.mul_le_mul_left _ m1
      have b : n * G ≤ n * (e2 * f1) := Nat.mul_le_mul_left _ hG
      have c : (α * e1) * f1 < (n * e2) * f1 := by
        calc (α * e1) * f1 = α * (e1 * f1) := by ring
          _ ≤ α * d1 := a
          _ < n * G := H1
          _ ≤ n * (e2 * f1) := b
          _ = (n * e2) * f1 := by ring
      exact Nat.lt_of_mul_lt_mul_right c
    have i4 : α * e2 < n * e1 := by
      have a : α * (e2 * f2) ≤ α * d2 := Nat.mul_le_mul_left _ m2
      have b : n * G' ≤ n * (e1 * f2) := Nat.mul_le_mul_left _ hG'
      have c : (α * e2) * f2 < (n * e1) * f2 := by
        calc (α * e2) * f2 = α * (e2 * f2) := by ring
          _ ≤ α * d2 := a
          _ < n * G' := H4
          _ ≤ n * (e1 * f2) := b
          _ = (n * e1) * f2 := by ring
      exact Nat.lt_of_mul_lt_mul_right c
    have i2 : β * f2 < n * f1 := by
      have a : β * (e2 * f2) ≤ β * d2 := Nat.mul_le_mul_left _ m2
      have b : n * G ≤ n * (e2 * f1) := Nat.mul_le_mul_left _ hG
      have c : (β * f2) * e2 < (n * f1) * e2 := by
        calc (β * f2) * e2 = β * (e2 * f2) := by ring
          _ ≤ β * d2 := a
          _ < n * G := H2
          _ ≤ n * (e2 * f1) := b
          _ = (n * f1) * e2 := by ring
      exact Nat.lt_of_mul_lt_mul_right c
    have i3 : β * f1 < n * f2 := by
      have a : β * (e1 * f1) ≤ β * d1 := Nat.mul_le_mul_left _ m1
      have b : n * G' ≤ n * (e1 * f2) := Nat.mul_le_mul_left _ hG'
      have c : (β * f1) * e1 < (n * f2) * e1 := by
        calc (β * f1) * e1 = β * (e1 * f1) := by ring
          _ ≤ β * d1 := a
          _ < n * G' := H3
          _ ≤ n * (e1 * f2) := b
          _ = (n * f2) * e1 := by ring
      exact Nat.lt_of_mul_lt_mul_right c
    have ee : e1 = e2 := r4c_arith n α e1 e2 gα mα i1 i4
    have ff : f1 = f2 := r4c_arith n β f1 f2 gβ mβ i3 i2
    subst ee; subst ff
    have e1 : e1 = 1 := Nat.coprime_self e1 |>.mp ce
    have f1 : f1 = 1 := Nat.coprime_self f1 |>.mp cf
    subst e1; subst f1
    have g1 : n * G ≤ n := by simpa using Nat.mul_le_mul_left n hG
    have g2 : n * G' ≤ n := by simpa using Nat.mul_le_mul_left n hG'
    constructor
    · by_contra hc
      have : α * 2 ≤ α * d1 := Nat.mul_le_mul_left _ (by omega)
      omega
    · by_contra hc
      have : α * 2 ≤ α * d2 := Nat.mul_le_mul_left _ (by omega)
      omega


  -- 402-R4-c. Collision lemma for one pair: both quotients below n ≤ p and equal fold classes
  -- force a = b or reduced quotients adding up to p.
  have r4c_pair (p n a b : ℕ) (hp : p.Prime) (hnp : n ≤ p) (a0 : 0 < a) (b0 : 0 < b)
      (ha : a < n * Nat.gcd a b) (hb : b < n * Nat.gcd a b) (hc : cls p a = cls p b) :
      a = b ∨ ∃ x y g, x + y = p ∧ Nat.Coprime x y ∧ a = x * g ∧ b = y * g := by
    have := Fact.mk hp
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
    rw [hcls, hcls] at hc
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


  -- 402-R4-c. Rectangle lemma: α u, β u, α w, β w with all four cross quotients below n force u = w.
  have r4c_rect (n α β u w : ℕ) (gα : (∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y)) (gβ : (∀ x y : ℕ, x < y → x * y ∣ β → n * x ≤ β * y))
      (tα : n ≤ 2 * α)
      (α0 : 0 < α) (β0 : 0 < β) (hαβ : Nat.Coprime α β) (u0 : 0 < u) (w0 : 0 < w)
      (H1 : α * u < n * Nat.gcd (α * u) (β * w)) (H2 : β * w < n * Nat.gcd (α * u) (β * w))
      (H3 : β * u < n * Nat.gcd (β * u) (α * w)) (H4 : α * w < n * Nat.gcd (β * u) (α * w)) :
      u = w := by
    obtain ⟨d1, d2, hd, hu, hw⟩ := Nat.exists_coprime u w
    have C0 : 0 < Nat.gcd u w := Nat.gcd_pos_of_pos_left _ u0
    generalize Nat.gcd u w = C at *
    subst hu; subst hw
    have d10 : 0 < d1 := Nat.pos_of_mul_pos_right u0
    have d20 : 0 < d2 := Nat.pos_of_mul_pos_right w0
    have s1 : Nat.gcd (α * (d1 * C)) (β * (d2 * C)) = Nat.gcd (α * d1) (β * d2) * C := by
      rw [← Nat.mul_assoc, ← Nat.mul_assoc, Nat.gcd_mul_right]
    have s2 : Nat.gcd (β * (d1 * C)) (α * (d2 * C)) = Nat.gcd (β * d1) (α * d2) * C := by
      rw [← Nat.mul_assoc, ← Nat.mul_assoc, Nat.gcd_mul_right]
    rw [s1] at H1 H2
    rw [s2] at H3 H4
    have c : ∀ s t : ℕ, s * (t * C) < n * (Nat.gcd (α * d1) (β * d2) * C) →
        s * t < n * Nat.gcd (α * d1) (β * d2) := by
      intro s t h
      rw [← Nat.mul_assoc, ← Nat.mul_assoc] at h; exact Nat.lt_of_mul_lt_mul_right h
    have c' : ∀ s t : ℕ, s * (t * C) < n * (Nat.gcd (β * d1) (α * d2) * C) →
        s * t < n * Nat.gcd (β * d1) (α * d2) := by
      intro s t h
      rw [← Nat.mul_assoc, ← Nat.mul_assoc] at h; exact Nat.lt_of_mul_lt_mul_right h
    obtain ⟨e1, e2⟩ := r4c_rect_core n α β d1 d2 gα gβ tα α0 β0 hαβ hd d10 d20
      (c _ _ H1) (c _ _ H2) (c' _ _ H3) (c' _ _ H4)
    rw [e1, e2]

  -- 402-R5-b (from 402-R4-c). THE GENERALISED CRITERION: a prime p with
  -- n < p < 2n and (2n − p)² ≤ n forces a pair with n · gcd(a, b) ≤ a in every set of n positive integers.
  have r4c_criterion (A : Finset ℕ) (h0 : 0 ∉ A) (p : ℕ) (hp : p.Prime) (h1 : A.card < p)
      (h2 : p < 2 * A.card) (h3 : 2 * (2 * A.card - p) ≤ A.card + 2)
      (H : ∀ α : ℕ, α < A.card → p < α + A.card →
        (∃ q : ℕ, q.Prime ∧ A.card ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → A.card * x ≤ α * y)) :
      (∃ a ∈ A, ∃ b ∈ A, A.card * Nat.gcd a b ≤ a) ∨
        ∃ q : ℕ, q.Prime ∧ A.card ≤ 3 * q ∧ ∃ a ∈ A, q ∣ a := by
    by_contra hcon
    have hne : ∀ a ∈ A, ∀ b ∈ A, a < A.card * Nat.gcd a b := by
      intro a ha b hb
      by_contra h
      exact hcon (Or.inl ⟨a, ha, b, hb, by omega⟩)
    have hnq : ∀ q : ℕ, q.Prime → A.card ≤ 3 * q → ∀ a ∈ A, ¬ q ∣ a :=
      fun q hq h a ha hd => hcon (Or.inr ⟨q, hq, h, a, ha, hd⟩)
    clear hcon
    generalize hn : A.card = n at *
    have pos : ∀ a ∈ A, 0 < a := fun a ha =>
      Nat.pos_of_ne_zero (fun h => h0 (h ▸ ha))
    have podd : p % 2 = 1 := by
      rcases hp.eq_two_or_odd with h | h
      · omega
      · exact h
    -- pairs in one fold class
    have P : ∀ a ∈ A, ∀ b ∈ A, cls p a = cls p b →
        a = b ∨ ∃ x y g, x + y = p ∧ Nat.Coprime x y ∧ a = x * g ∧ b = y * g :=
      fun a ha b hb h => r4c_pair p n a b hp h1.le (pos a ha) (pos b hb) (hne a ha b hb)
        (by rw [Nat.gcd_comm]; exact hne b hb a ha) h
    have clsr : ∀ a ∈ A, cls p a ∈ Finset.Icc 1 ((p - 1) / 2) := by
      intro a ha
      have := Fact.mk hp
      have na : ((a / p ^ a.factorization p : ℕ) : ZMod p) ≠ 0 := by
        rw [Ne, ZMod.natCast_eq_zero_iff]; exact Nat.not_dvd_ordCompl hp (pos a ha).ne'
      have v1 := ZMod.val_lt ((a / p ^ a.factorization p : ℕ) : ZMod p)
      have v0 : 0 < ZMod.val ((a / p ^ a.factorization p : ℕ) : ZMod p) := (ZMod.val_pos).mpr na
      rw [hcls]
      rw [Finset.mem_Icc]
      omega
    classical
    -- the elements with a smaller partner in their class, and the rest
    have split := Finset.card_filter_add_card_filter_not (s := A)
      (fun a => ∃ a' ∈ A, a' < a ∧ cls p a' = cls p a)
    have c1 : (A.filter (fun a => ¬ ∃ a' ∈ A, a' < a ∧ cls p a' = cls p a)).card
        ≤ (Finset.Icc 1 ((p - 1) / 2)).card := by
      apply Finset.card_le_card_of_injOn (cls p)
      · intro a ha
        exact clsr a (Finset.mem_filter.mp (Finset.mem_coe.mp ha)).1
      · intro a ha b hb hab
        have ha' := Finset.mem_filter.mp (Finset.mem_coe.mp ha)
        have hb' := Finset.mem_filter.mp (Finset.mem_coe.mp hb)
        rcases Nat.lt_trichotomy a b with h | h | h
        · exact (hb'.2 ⟨a, ha'.1, h, hab⟩).elim
        · exact h
        · exact (ha'.2 ⟨b, hb'.1, h, hab.symm⟩).elim
    have hex : ∀ a, ∃ a' x y g, (∃ a' ∈ A, a' < a ∧ cls p a' = cls p a) → a ∈ A →
        (a' ∈ A ∧ a' < a ∧ x + y = p ∧ Nat.Coprime x y ∧ a = x * g ∧ a' = y * g) := by
      intro a
      by_cases h : (∃ a' ∈ A, a' < a ∧ cls p a' = cls p a) ∧ a ∈ A
      · obtain ⟨⟨a', ha', hlt, hc⟩, ha⟩ := h
        rcases P a ha a' ha' hc.symm with h | ⟨x, y, g, h⟩
        · omega
        · exact ⟨a', x, y, g, fun _ _ => ⟨ha', hlt, h⟩⟩
      · exact ⟨0, 0, 0, 0, fun h1 h2 => (h ⟨h1, h2⟩).elim⟩
    choose f X Y G hf using hex
    -- the rectangle step, with the four elements named
    have R : ∀ a a' b b' α β u w : ℕ, a ∈ A → a' ∈ A → b ∈ A → b' ∈ A → α + β = p →
        Nat.Coprime α β → a = α * u → a' = β * u → b = α * w → b' = β * w → u = w := by
      intro a a' b b' α β u w ha ha' hb hb' hs hco e1 e2 e3 e4
      have q1 := hne a ha b' hb'
      have q2 := hne b' hb' a ha
      have q3 := hne a' ha' b hb
      have q4 := hne b hb a' ha'
      rw [Nat.gcd_comm] at q2 q4
      have pa := pos a ha
      have pa' := pos a' ha'
      have pb := pos b hb
      have qa := hne a ha a' ha'
      have qa' := hne a' ha' a ha
      rw [Nat.gcd_comm] at qa'
      subst e1 e2 e3 e4
      have u0 : 0 < u := Nat.pos_of_mul_pos_left pa
      have w0 : 0 < w := Nat.pos_of_mul_pos_left pb
      have α0 : 0 < α := Nat.pos_of_mul_pos_right pa
      have β0 : 0 < β := Nat.pos_of_mul_pos_right pa'
      have gu : Nat.gcd (α * u) (β * u) = u := by
        rw [Nat.gcd_mul_right, hco, Nat.one_mul]
      rw [gu] at qa qa'
      have αn : α < n := Nat.lt_of_mul_lt_mul_right qa
      have βn : β < n := Nat.lt_of_mul_lt_mul_right qa'
      have tα : n ≤ 2 * α := by omega
      have Hα := H α αn (by omega)
      have Hβ := H β βn (by omega)
      have pα : p - α = β := by omega
      have pβ : p - β = α := by omega
      rw [pα] at Hα
      rw [pβ] at Hβ
      have excl : ∀ q : ℕ, q.Prime → n ≤ 3 * q → q ∣ α * β → False := by
        intro q hq hq3 hd
        rcases (Nat.Prime.dvd_mul hq).mp hd with h | h
        · exact hnq q hq hq3 (α * u) ha (Dvd.dvd.mul_right h u)
        · exact hnq q hq hq3 (β * u) ha' (Dvd.dvd.mul_right h u)
      have gα : ∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y := by
        rcases Hα with ⟨q, hq, h3q, hd⟩ | h
        · exact (excl q hq h3q hd).elim
        · exact h
      have gβ : ∀ x y : ℕ, x < y → x * y ∣ β → n * x ≤ β * y := by
        rcases Hβ with ⟨q, hq, h3q, hd⟩ | h
        · exact (excl q hq h3q (by rwa [Nat.mul_comm])).elim
        · exact h
      exact r4c_rect n α β u w gα gβ tα α0 β0 hco u0 w0 q1 q2 q3 q4
    have c2 : (A.filter (fun a => ∃ a' ∈ A, a' < a ∧ cls p a' = cls p a)).card
        ≤ (Finset.Icc ((p + 1) / 2) (n - 1)).card := by
      apply Finset.card_le_card_of_injOn (fun a => max (X a) (Y a))
      · intro a ha
        have ha' := Finset.mem_filter.mp (Finset.mem_coe.mp ha)
        obtain ⟨m1, m2, m3, m4, m5, m6⟩ := hf a ha'.2 ha'.1
        have qa := hne a ha'.1 (f a) m1
        have qa' := hne (f a) m1 a ha'.1
        rw [Nat.gcd_comm] at qa'
        have g0 : 0 < G a := Nat.pos_of_mul_pos_left (m5 ▸ pos a ha'.1)
        have gg : ∀ s t x y g : ℕ, s = x * g → t = y * g → Nat.Coprime x y → Nat.gcd s t = g := by
          intro s t x y g e1 e2 hc
          rw [e1, e2, Nat.gcd_mul_right, hc, Nat.one_mul]
        rw [gg a (f a) (X a) (Y a) (G a) m5 m6 m4] at qa qa'
        have xn : X a < n := by
          have : X a * G a < n * G a := lt_of_eq_of_lt m5.symm qa
          exact Nat.lt_of_mul_lt_mul_right this
        have yn : Y a < n := by
          have : Y a * G a < n * G a := lt_of_eq_of_lt m6.symm qa'
          exact Nat.lt_of_mul_lt_mul_right this
        simp only [Finset.coe_Icc, Set.mem_Icc]
        omega
      · intro a ha b hb hab
        have ha' := Finset.mem_filter.mp (Finset.mem_coe.mp ha)
        have hb' := Finset.mem_filter.mp (Finset.mem_coe.mp hb)
        obtain ⟨m1, m2, m3, m4, m5, m6⟩ := hf a ha'.2 ha'.1
        obtain ⟨k1, k2, k3, k4, k5, k6⟩ := hf b hb'.2 hb'.1
        simp only at hab
        have hcase : (X b = X a ∧ Y b = Y a) ∨ (X b = Y a ∧ Y b = X a) := by omega
        rcases hcase with ⟨hx, hy⟩ | ⟨hx, hy⟩
        · rw [hx] at k5; rw [hy] at k6
          have := R a (f a) b (f b) (X a) (Y a) (G a) (G b) ha'.1 m1 hb'.1 k1 m3 m4 m5 m6 k5 k6
          rw [m5, k5, this]
        · rw [hx] at k5; rw [hy] at k6
          have := R a (f a) (f b) b (X a) (Y a) (G a) (G b) ha'.1 m1 k1 hb'.1 m3 m4 m5 m6 k6 k5
          have e1 : a = f b := by rw [m5, k6, this]
          have e2 : f a = b := by rw [m6, k5, this]
          omega
    rw [Nat.card_Icc] at c1 c2
    omega
  intro A h0 p hp h1 h2 h3 H
  rcases r4c_criterion A h0 p hp h1 h2 h3 H with ⟨a, ha, b, hb, h⟩ | h
  · left
    refine ⟨a, ha, b, hb, ?_⟩
    have n0 : (0 : ℚ) < (A.card : ℚ) := by
      have : 0 < A.card := Finset.card_pos.mpr ⟨a, ha⟩
      exact_mod_cast this
    rw [le_div_iff₀ n0]
    have : a.gcd b * A.card ≤ a := by rw [Nat.mul_comm]; exact h
    exact_mod_cast this
  · exact Or.inr h

#print axioms r5b_gen_criterion
