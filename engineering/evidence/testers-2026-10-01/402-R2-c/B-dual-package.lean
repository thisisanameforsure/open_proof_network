import Mathlib

/-- B (dual package). For a nonempty set B of positive integers, the dual set
B* = {lcm(B)/a} has the same size, no zero, gcd 1; prime powers dividing its elements divide
elements of B; the quotient hypotheses transfer; a good pair of B* gives a good pair of B; and
for a prime p dividing an element of B but with p² dividing none, the multiples of p in B* are
exactly the images of the non-multiples in B (the two counts swap). -/
theorem R2c.dual_package (B : Finset ℕ) (n : ℕ) (hne : B.Nonempty) (h0 : 0 ∉ B) :
    (B.image (fun a => B.lcm id / a)).card = B.card ∧
    (B.image (fun a => B.lcm id / a)).Nonempty ∧
    0 ∉ B.image (fun a => B.lcm id / a) ∧
    (B.image (fun a => B.lcm id / a)).gcd id = 1 ∧
    (∀ x ∈ B.image (fun a => B.lcm id / a), ∀ q k : ℕ, q.Prime → q ^ k ∣ x → ∃ a ∈ B, q ^ k ∣ a) ∧
    ((∀ a ∈ B, ∀ b ∈ B, a ≤ n * Nat.gcd a b) →
      ∀ x ∈ B.image (fun a => B.lcm id / a), ∀ y ∈ B.image (fun a => B.lcm id / a),
        x ≤ n * Nat.gcd x y) ∧
    ((∃ x ∈ B.image (fun a => B.lcm id / a), ∃ y ∈ B.image (fun a => B.lcm id / a),
        n * Nat.gcd x y ≤ x) → ∃ a ∈ B, ∃ b ∈ B, n * Nat.gcd a b ≤ a) ∧
    (∀ p : ℕ, p.Prime → (∃ a ∈ B, p ∣ a) → (∀ a ∈ B, ¬ p ^ 2 ∣ a) →
      (∀ a ∈ B, (p ∣ B.lcm id / a ↔ ¬ p ∣ a)) ∧
      ((B.image (fun a => B.lcm id / a)).filter (fun x => p ∣ x)).card
        = (B.filter (fun a => ¬ p ∣ a)).card ∧
      ((B.image (fun a => B.lcm id / a)).filter (fun x => ¬ p ∣ x)).card
        = (B.filter (fun a => p ∣ a)).card) := by
  -- E2 of 402-R1-b
  have dual_quot : ∀ L a a' b b' : ℕ, a * a' = L → b * b' = L → 0 < a →
      a' * Nat.gcd a b = b * Nat.gcd a' b' := by
    intro L a a' b b' ha hb h0
    have h1 : Nat.gcd a' b' * (a * b) = L * Nat.gcd a b := by
      rw [← Nat.gcd_mul_right]
      have e1 : a' * (a * b) = L * b := by rw [← ha]; ring
      have e2 : b' * (a * b) = L * a := by rw [← hb]; ring
      rw [e1, e2, Nat.gcd_mul_left, Nat.gcd_comm b a]
    have h2 : a * (a' * Nat.gcd a b) = a * (b * Nat.gcd a' b') := by
      rw [← mul_assoc, ha, ← h1]; ring
    exact Nat.eq_of_mul_eq_mul_left h0 h2
  -- a prime power dividing an lcm divides an element
  have ppl : ∀ (q k : ℕ), q.Prime → ∀ S : Finset ℕ, 0 ∉ S → S.Nonempty → q ^ k ∣ S.lcm id →
      ∃ a ∈ S, q ^ k ∣ a := by
    intro q k hq S
    induction S using Finset.induction_on with
    | empty => intro _ h; exact absurd h (by simp)
    | insert x S hx ih =>
      intro hS0 _ hdvd
      have hx0 : x ≠ 0 := fun e => hS0 (e ▸ Finset.mem_insert_self x S)
      have hS0' : 0 ∉ S := fun h => hS0 (Finset.mem_insert_of_mem h)
      rcases Finset.eq_empty_or_nonempty S with hSe | hSn
      · subst hSe
        refine ⟨x, Finset.mem_insert_self _ _, ?_⟩
        simpa using hdvd
      · have hl0 : S.lcm id ≠ 0 := by
          intro h
          rw [Finset.lcm_eq_zero_iff] at h
          obtain ⟨z, hz, e⟩ := h
          have e' : z = 0 := e
          exact hS0' (e' ▸ hz)
        rw [Finset.lcm_insert] at hdvd
        have hdvd' : q ^ k ∣ Nat.lcm x (S.lcm id) := hdvd
        rw [hq.pow_dvd_iff_le_factorization (Nat.lcm_ne_zero hx0 hl0),
          Nat.factorization_lcm hx0 hl0, Finsupp.sup_apply] at hdvd'
        rcases le_sup_iff.mp hdvd' with h | h
        · exact ⟨x, Finset.mem_insert_self _ _, (hq.pow_dvd_iff_le_factorization hx0).mpr h⟩
        · obtain ⟨a, ha, hda⟩ := ih hS0' hSn ((hq.pow_dvd_iff_le_factorization hl0).mpr h)
          exact ⟨a, Finset.mem_insert_of_mem ha, hda⟩
  generalize hLdef : B.lcm id = L
  have hdvd : ∀ a ∈ B, a ∣ L := fun a ha => hLdef ▸ Finset.dvd_lcm (f := id) ha
  have hL0 : L ≠ 0 := by
    intro h
    rw [← hLdef, Finset.lcm_eq_zero_iff] at h
    obtain ⟨z, hz, e⟩ := h
    have e' : z = 0 := e
    exact h0 (e' ▸ hz)
  have hLpos : 0 < L := Nat.pos_of_ne_zero hL0
  have hmul : ∀ a ∈ B, a * (L / a) = L := fun a ha => Nat.mul_div_cancel' (hdvd a ha)
  have hapos : ∀ a ∈ B, 0 < a := fun a ha => Nat.pos_of_ne_zero (fun e => h0 (e ▸ ha))
  have hqpos : ∀ a ∈ B, 0 < L / a := by
    intro a ha
    exact Nat.pos_of_ne_zero (by
      intro h
      have := hmul a ha
      rw [h, Nat.mul_zero] at this
      exact hL0 this.symm)
  have hinj : Set.InjOn (fun a => L / a) (B : Set ℕ) := by
    intro a ha b hb hab
    simp only at hab
    have e1 := hmul a ha
    have e2 := hmul b hb
    rw [hab] at e1
    exact Nat.eq_of_mul_eq_mul_right (hqpos b hb) (e1.trans e2.symm)
  -- quotient identity: (L/a) * gcd a b = b * gcd (L/a) (L/b)
  have hid : ∀ a ∈ B, ∀ b ∈ B, (L / a) * Nat.gcd a b = b * Nat.gcd (L / a) (L / b) :=
    fun a ha b hb => dual_quot L a (L / a) b (L / b) (hmul a ha) (hmul b hb) (hapos a ha)
  have hgpos : ∀ a ∈ B, ∀ b ∈ B, 0 < Nat.gcd a b := fun a ha b _ =>
    Nat.gcd_pos_of_pos_left _ (hapos a ha)
  have hgpos' : ∀ a ∈ B, ∀ b ∈ B, 0 < Nat.gcd (L / a) (L / b) := fun a ha b _ =>
    Nat.gcd_pos_of_pos_left _ (hqpos a ha)
  refine ⟨Finset.card_image_of_injOn hinj, hne.image _, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · intro h
    obtain ⟨a, ha, e⟩ := Finset.mem_image.mp h
    exact (hqpos a ha).ne' e
  · generalize hd : (B.image (fun a => L / a)).gcd id = d
    have hdd : ∀ a ∈ B, d ∣ L / a := by
      intro a ha
      rw [← hd]
      exact Finset.gcd_dvd (f := id) (Finset.mem_image_of_mem _ ha)
    obtain ⟨a0, ha0⟩ := hne
    have hdL : d ∣ L := (hdd a0 ha0).trans (Nat.div_dvd_of_dvd (hdvd a0 ha0))
    have hdpos : 0 < d := Nat.pos_of_dvd_of_pos hdL hLpos
    have hall : ∀ a ∈ B, id a ∣ L / d := by
      intro a ha
      obtain ⟨k, hk⟩ := hdd a ha
      have e : L = d * (a * k) := by
        have := hmul a ha
        rw [hk] at this
        rw [← this]; ring
      have : L / d = a * k := by rw [e]; exact Nat.mul_div_cancel_left _ hdpos
      rw [this]; exact Dvd.intro _ rfl
    have hLdvd : L ∣ L / d := by
      have h := Finset.lcm_dvd hall
      rwa [hLdef] at h
    have hpos' : 0 < L / d := Nat.div_pos (Nat.le_of_dvd hLpos hdL) hdpos
    have hle : L ≤ L / d := Nat.le_of_dvd hpos' hLdvd
    by_contra hne1
    have h2 : 2 ≤ d := by omega
    have := Nat.div_lt_self hLpos h2
    omega
  · intro x hx q k hq hqx
    obtain ⟨a, ha, rfl⟩ := Finset.mem_image.mp hx
    have h1 : q ^ k ∣ B.lcm id := hLdef ▸ hqx.trans (Nat.div_dvd_of_dvd (hdvd a ha))
    exact ppl q k hq B h0 hne h1
  · intro hle x hx y hy
    obtain ⟨a, ha, rfl⟩ := Finset.mem_image.mp hx
    obtain ⟨b, hb, rfl⟩ := Finset.mem_image.mp hy
    have e := hid a ha b hb
    have h1 := hle b hb a ha
    rw [Nat.gcd_comm b a] at h1
    have h2 : L / a * Nat.gcd a b ≤ n * Nat.gcd (L / a) (L / b) * Nat.gcd a b := by
      rw [e]
      calc b * Nat.gcd (L / a) (L / b) ≤ n * Nat.gcd a b * Nat.gcd (L / a) (L / b) :=
            Nat.mul_le_mul_right _ h1
        _ = n * Nat.gcd (L / a) (L / b) * Nat.gcd a b := by ring
    exact Nat.le_of_mul_le_mul_right h2 (hgpos a ha b hb)
  · rintro ⟨x, hx, y, hy, hxy⟩
    obtain ⟨a, ha, rfl⟩ := Finset.mem_image.mp hx
    obtain ⟨b, hb, rfl⟩ := Finset.mem_image.mp hy
    refine ⟨b, hb, a, ha, ?_⟩
    have e := hid a ha b hb
    have h2 : n * Nat.gcd b a * Nat.gcd (L / a) (L / b) ≤ b * Nat.gcd (L / a) (L / b) := by
      rw [← e, Nat.gcd_comm b a]
      calc n * Nat.gcd a b * Nat.gcd (L / a) (L / b) = n * Nat.gcd (L / a) (L / b) * Nat.gcd a b := by ring
        _ ≤ L / a * Nat.gcd a b := Nat.mul_le_mul_right _ hxy
    exact Nat.le_of_mul_le_mul_right h2 (hgpos' a ha b hb)
  · intro p hp ⟨a1, ha1, hpa1⟩ hsq
    have hpL : p ∣ L := hpa1.trans (hdvd a1 ha1)
    have hsqL : ¬ p ^ 2 ∣ L := by
      intro h
      obtain ⟨a, ha, hda⟩ := ppl p 2 hp B h0 hne (hLdef ▸ h)
      exact hsq a ha hda
    have hiff : ∀ a ∈ B, (p ∣ L / a ↔ ¬ p ∣ a) := by
      intro a ha
      constructor
      · intro h1 h2
        apply hsqL
        rw [← hmul a ha, pow_two]
        exact Nat.mul_dvd_mul h2 h1
      · intro h
        have h1 : p ∣ a * (L / a) := by rw [hmul a ha]; exact hpL
        exact (hp.dvd_mul.mp h1).resolve_left h
    refine ⟨hiff, ?_, ?_⟩
    · have e : (B.image (fun a => L / a)).filter (fun x => p ∣ x)
          = (B.filter (fun a => ¬ p ∣ a)).image (fun a => L / a) := by
        ext x
        simp only [Finset.mem_filter, Finset.mem_image]
        constructor
        · rintro ⟨⟨a, ha, rfl⟩, h⟩
          exact ⟨a, ⟨ha, (hiff a ha).mp h⟩, rfl⟩
        · rintro ⟨a, ⟨ha, h⟩, rfl⟩
          exact ⟨⟨a, ha, rfl⟩, (hiff a ha).mpr h⟩
      rw [e]
      exact Finset.card_image_of_injOn (hinj.mono (by
        intro a ha
        exact (Finset.mem_filter.mp (Finset.mem_coe.mp ha)).1))
    · have e : (B.image (fun a => L / a)).filter (fun x => ¬ p ∣ x)
          = (B.filter (fun a => p ∣ a)).image (fun a => L / a) := by
        ext x
        simp only [Finset.mem_filter, Finset.mem_image]
        constructor
        · rintro ⟨⟨a, ha, rfl⟩, h⟩
          exact ⟨a, ⟨ha, by_contra (fun h' => h ((hiff a ha).mpr h'))⟩, rfl⟩
        · rintro ⟨a, ⟨ha, h⟩, rfl⟩
          exact ⟨⟨a, ha, rfl⟩, fun h' => (hiff a ha).mp h' h⟩
      rw [e]
      exact Finset.card_image_of_injOn (hinj.mono (by
        intro a ha
        exact (Finset.mem_filter.mp (Finset.mem_coe.mp ha)).1))
