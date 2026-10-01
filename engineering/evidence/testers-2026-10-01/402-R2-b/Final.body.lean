
/-- Small sizes: the hole's hypotheses on |B| give p ≥ 3 and |B| ≥ 9. -/
theorem R2b.small (n p : ℕ) (hp : p.Prime) (h2p : 2 * p < n) (hn3 : n ≤ 3 * p)
    (hnp : ¬ n.Prime) (hnp1 : ∀ q : ℕ, q.Prime → n ≠ q + 1) : 3 ≤ p ∧ 9 ≤ n := by
  have h2 := hp.two_le
  rcases Nat.lt_or_ge p 5 with h5 | h5
  · interval_cases p
    · exfalso
      interval_cases n
      · exact hnp (by norm_num)
      · exact hnp1 5 (by norm_num) rfl
    · refine ⟨le_refl _, ?_⟩
      interval_cases n
      · exact (hnp (by norm_num)).elim
      · exact (hnp1 7 (by norm_num) rfl).elim
      · exact le_refl _
    · exact absurd hp (by norm_num)
  · omega

/-- No prime p with 2p < n ≤ 3p divides an element of a strict counterexample (n ≥ 9). -/
theorem R2b.no_mid_prime (B : Finset ℕ) (h0 : 0 ∉ B) (hgcd : B.gcd id = 1)
    (hlt : ∀ a ∈ B, ∀ b ∈ B, a < B.card * a.gcd b)
    (p : ℕ) (hp : p.Prime) (hp3 : 3 ≤ p) (h2p : 2 * p < B.card) (hn3 : B.card ≤ 3 * p)
    (h9 : 9 ≤ B.card) : ∀ a ∈ B, ¬ p ∣ a := by
  intro a0 ha0 hpa0
  obtain ⟨g, hg, hpg, huniq, hdvd⟩ := R2b.block B h0 hgcd hlt p hp hp3 h2p hn3 h9 ⟨a0, ha0, hpa0⟩
  obtain ⟨hcard, h0', hgcd', hlt'⟩ := R1b.dual_set B B.card ⟨a0, ha0⟩ h0 hlt
  have hpos : ∀ a ∈ B, 0 < a := fun a ha => Nat.pos_of_ne_zero (fun h => h0 (h ▸ ha))
  have hL : B.lcm id ∣ 2 * p * g := Finset.lcm_dvd (fun a ha => hdvd a ha)
  have hLpos : 0 < B.lcm id :=
    Nat.pos_of_dvd_of_pos hL (Nat.mul_pos (Nat.mul_pos (by norm_num) hp.pos) (hpos g hg))
  have hmul : ∀ a ∈ B, a * (B.lcm id / a) = B.lcm id :=
    fun a ha => Nat.mul_div_cancel' (Finset.dvd_lcm (f := id) ha)
  have hpLg : p ∣ B.lcm id / g := by
    have h1 : p ∣ g * (B.lcm id / g) := by
      rw [hmul g hg]; exact hpa0.trans (Finset.dvd_lcm (f := id) ha0)
    exact (hp.dvd_mul.mp h1).resolve_left hpg
  rw [← hcard] at hlt' h2p hn3 h9
  obtain ⟨g', hg', hpg', huniq', -⟩ := R2b.block _ h0' hgcd' hlt' p hp hp3 h2p hn3 h9
    ⟨_, Finset.mem_image_of_mem _ hg, hpLg⟩
  have h2 : 1 < (B.erase g).card := by
    rw [Finset.card_erase_of_mem hg, ← hcard]; omega
  obtain ⟨a1, ha1, a2, ha2, hne⟩ := Finset.one_lt_card.mp h2
  obtain ⟨hne1, ha1B⟩ := Finset.mem_erase.mp ha1
  obtain ⟨hne2, ha2B⟩ := Finset.mem_erase.mp ha2
  have hfin : ∀ a ∈ B, a ≠ g → p ∣ B.lcm id / a → False := by
    intro a ha hag hpLa
    have hpa : p ∣ a := by
      by_contra h
      exact hag (huniq a ha h)
    obtain ⟨c, hc⟩ := hpa
    obtain ⟨d, hd⟩ := hpLa
    have h3 : p * (p * (c * d)) ∣ p * (2 * g) := by
      have h4 : p * (p * (c * d)) = B.lcm id := by
        rw [← hmul a ha, hd]; rw [hc]; ring
      rw [h4]
      exact hL.trans (dvd_of_eq (by ring))
    have h5 : p ∣ 2 * g := (Dvd.intro _ rfl).trans (Nat.dvd_of_mul_dvd_mul_left hp.pos h3)
    rcases hp.dvd_mul.mp h5 with h6 | h6
    · have := Nat.le_of_dvd (by norm_num) h6
      omega
    · exact hpg h6
  by_cases hp1 : p ∣ B.lcm id / a1
  · exact hfin a1 ha1B hne1 hp1
  · by_cases hp2 : p ∣ B.lcm id / a2
    · exact hfin a2 ha2B hne2 hp2
    · have e1 := huniq' _ (Finset.mem_image_of_mem _ ha1B) hp1
      have e2 := huniq' _ (Finset.mem_image_of_mem _ ha2B) hp2
      have e3 : B.lcm id / a1 = B.lcm id / a2 := e1.trans e2.symm
      have m1 := hmul a1 ha1B
      have m2 := hmul a2 ha2B
      rw [e3] at m1
      have hq : 0 < B.lcm id / a2 := by
        apply Nat.pos_of_ne_zero
        intro hz
        rw [hz, Nat.mul_zero] at m2
        omega
      exact hne (Nat.eq_of_mul_eq_mul_right hq (m1.trans m2.symm))
