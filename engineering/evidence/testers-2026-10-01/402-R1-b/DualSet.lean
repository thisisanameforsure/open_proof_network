
/-- E8. The dual set. For a nonempty set B of positive integers with L = lcm(B), the set
B* = {L / a : a ∈ B} has the same size, no zero, gcd 1, and is strict when B is. -/
theorem R1b.dual_set (B : Finset ℕ) (n : ℕ) (hne : B.Nonempty) (h0 : 0 ∉ B)
    (hs : ∀ a ∈ B, ∀ b ∈ B, a < n * Nat.gcd a b) :
    (B.image (fun a => B.lcm id / a)).card = B.card ∧ 0 ∉ B.image (fun a => B.lcm id / a) ∧
      (B.image (fun a => B.lcm id / a)).gcd id = 1 ∧
      ∀ a ∈ B.image (fun a => B.lcm id / a), ∀ b ∈ B.image (fun a => B.lcm id / a),
        a < n * Nat.gcd a b := by
  set L := B.lcm id with hLdef
  have hdvd : ∀ a ∈ B, a ∣ L := fun a ha => Finset.dvd_lcm (f := id) ha
  have hL0 : L ≠ 0 := by
    intro h
    rw [hLdef, Finset.lcm_eq_zero_iff] at h
    simp at h
    exact h0 h
  have hLpos : 0 < L := Nat.pos_of_ne_zero hL0
  have hmul : ∀ a ∈ B, a * (L / a) = L := fun a ha => Nat.mul_div_cancel' (hdvd a ha)
  have hqpos : ∀ a ∈ B, 0 < L / a := by
    intro a ha
    rcases Nat.eq_zero_or_pos (L / a) with h | h
    · have := hmul a ha
      rw [h] at this
      simp at this
      exact absurd this.symm hL0
    · exact h
  have hapos : ∀ a ∈ B, 0 < a := fun a ha => Nat.pos_of_ne_zero (fun e => h0 (e ▸ ha))
  refine ⟨?_, ?_, ?_, ?_⟩
  · apply Finset.card_image_of_injOn
    intro a ha b hb hab
    simp only at hab
    have e1 := hmul a ha
    have e2 := hmul b hb
    rw [hab] at e1
    have : a * (L / b) = b * (L / b) := by rw [e1, e2]
    exact Nat.eq_of_mul_eq_mul_right (hqpos b hb) this
  · intro h
    rw [Finset.mem_image] at h
    obtain ⟨a, ha, e⟩ := h
    have := hqpos a ha
    omega
  · set d := (B.image (fun a => L / a)).gcd id with hd
    have hdd : ∀ a ∈ B, d ∣ L / a := by
      intro a ha
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
    have hLdvd : L ∣ L / d := Finset.lcm_dvd hall
    have hpos' : 0 < L / d := Nat.div_pos (Nat.le_of_dvd hLpos hdL) hdpos
    have hle : L ≤ L / d := Nat.le_of_dvd hpos' hLdvd
    by_contra hne1
    have h2 : 2 ≤ d := by omega
    have := Nat.div_lt_self hLpos h2
    omega
  · intro x hx y hy
    rw [Finset.mem_image] at hx hy
    obtain ⟨a, ha, rfl⟩ := hx
    obtain ⟨b, hb, rfl⟩ := hy
    exact R1b.dual_strict L b (L / b) a (L / a) n (hmul b hb) (hmul a ha) hLpos (hs b hb a ha)
