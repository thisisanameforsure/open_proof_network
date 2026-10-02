
/-- Block lemma (k = 2).  In a strict counterexample B (n = |B| ≥ 9) with a prime p, 2p < n ≤ 3p,
dividing an element: exactly one element g is not a multiple of p, and every element divides 2pg. -/
theorem R2b.block (B : Finset ℕ) (h0 : 0 ∉ B) (hgcd : B.gcd id = 1)
    (hlt : ∀ a ∈ B, ∀ b ∈ B, a < B.card * a.gcd b)
    (p : ℕ) (hp : p.Prime) (hp3 : 3 ≤ p) (h2p : 2 * p < B.card) (hn3 : B.card ≤ 3 * p)
    (h9 : 9 ≤ B.card) (hex : ∃ a ∈ B, p ∣ a) :
    ∃ g ∈ B, ¬ p ∣ g ∧ (∀ b ∈ B, ¬ p ∣ b → b = g) ∧ ∀ a ∈ B, a ∣ 2 * p * g := by
  obtain ⟨a0, ha0, hpa0⟩ := hex
  have hexb : ∃ b ∈ B, ¬ p ∣ b := by
    by_contra h
    push Not at h
    have h1 : p ∣ B.gcd id := Finset.dvd_gcd (fun b hb => h b hb)
    rw [hgcd] at h1
    exact hp.one_lt.ne' (Nat.dvd_one.mp h1)
  obtain ⟨b0, hb0, hpb0⟩ := hexb
  have hpos : ∀ a ∈ B, 0 < a := fun a ha => Nat.pos_of_ne_zero (fun h => h0 (h ▸ ha))
  -- the pair analysis: a = g·x, b = g·y, x ∈ {p, 2p}
  have hA : ∀ a ∈ B, p ∣ a → ∀ b ∈ B, ¬ p ∣ b → ∃ y, 0 < y ∧ y < B.card ∧ ¬ p ∣ y ∧
      b = a.gcd b * y ∧ (a = p * a.gcd b ∨ (a = 2 * p * a.gcd b ∧ ¬ 2 ∣ y)) := by
    intro a ha hpa b hb hpb
    have hg0 : 0 < a.gcd b := Nat.gcd_pos_of_pos_left b (hpos a ha)
    obtain ⟨x, hx⟩ := Nat.gcd_dvd_left a b
    obtain ⟨y, hy⟩ := Nat.gcd_dvd_right a b
    have hpg : ¬ p ∣ a.gcd b := fun h => hpb (h.trans (Nat.gcd_dvd_right a b))
    have hpx : p ∣ x := by
      have h1 : p ∣ a.gcd b * x := hx ▸ hpa
      exact (hp.dvd_mul.mp h1).resolve_left hpg
    obtain ⟨t, ht⟩ := hpx
    have hxn : x < B.card := by
      have h3 : a.gcd b * x < a.gcd b * B.card := by
        rw [← hx, Nat.mul_comm]; exact hlt a ha b hb
      exact Nat.lt_of_mul_lt_mul_left h3
    have hyn : y < B.card := by
      have h3 : a.gcd b * y < a.gcd b * B.card := by
        rw [← hy, Nat.mul_comm, Nat.gcd_comm]; exact hlt b hb a ha
      exact Nat.lt_of_mul_lt_mul_left h3
    have hx0 : x ≠ 0 := by
      rintro rfl
      rw [Nat.mul_zero] at hx
      exact (hpos a ha).ne' hx
    have hy0 : y ≠ 0 := by
      rintro rfl
      rw [Nat.mul_zero] at hy
      exact (hpos b hb).ne' hy
    have hpy : ¬ p ∣ y := fun h => hpb (hy ▸ Dvd.dvd.mul_left h _)
    have hcop : Nat.Coprime x y := by
      have h1 := Nat.coprime_div_gcd_div_gcd hg0
      have e1 : a / a.gcd b = x := Nat.div_eq_of_eq_mul_right hg0 hx
      have e2 : b / a.gcd b = y := Nat.div_eq_of_eq_mul_right hg0 hy
      rwa [e1, e2] at h1
    have ht0 : t ≠ 0 := by
      rintro rfl
      rw [Nat.mul_zero] at ht
      exact hx0 ht
    have ht3 : t < 3 := by
      by_contra h
      push Not at h
      have h4 : p * 3 ≤ p * t := Nat.mul_le_mul_left p h
      omega
    refine ⟨y, Nat.pos_of_ne_zero hy0, hyn, hpy, hy, ?_⟩
    rcases (by omega : t = 1 ∨ t = 2) with rfl | rfl
    · left
      calc a = a.gcd b * x := hx
        _ = p * a.gcd b := by rw [ht]; ring
    · right
      refine ⟨(calc a = a.gcd b * x := hx
        _ = 2 * p * a.gcd b := by rw [ht]; ring), ?_⟩
      intro h2y
      have h2x : 2 ∣ x := ⟨p, by rw [ht]; ring⟩
      have := Nat.Coprime.eq_one_of_dvd (Nat.Coprime.coprime_dvd_left h2x hcop) h2y
      omega
  have hG0 : (B.filter (fun b => ¬ p ∣ b)).gcd id ≠ 0 := by
    intro h
    have h1 : (B.filter (fun b => ¬ p ∣ b)).gcd id ∣ id b0 :=
      Finset.gcd_dvd (Finset.mem_filter.mpr ⟨hb0, hpb0⟩)
    rw [h] at h1
    exact hpb0 (by rw [show b0 = 0 from Nat.eq_zero_of_zero_dvd h1]; exact dvd_zero p)
  have hGb : ∀ b ∈ B, ¬ p ∣ b → (B.filter (fun b => ¬ p ∣ b)).gcd id ∣ b := by
    intro b hb hpb
    exact Finset.gcd_dvd (f := id) (Finset.mem_filter.mpr ⟨hb, hpb⟩)
  have hdiv : ∀ a ∈ B, p ∣ a → a ∣ 2 * p * (B.filter (fun b => ¬ p ∣ b)).gcd id := by
    intro a ha hpa
    have h1 : a ∣ (B.filter (fun b => ¬ p ∣ b)).gcd (fun b => (2 * p) * id b) := by
      apply Finset.dvd_gcd
      intro b hb
      obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
      obtain ⟨y, -, -, -, hy, h⟩ := hA a ha hpa b hbB hpb
      have h2 : a ∣ 2 * p * a.gcd b := by
        rcases h with h | ⟨h, -⟩
        · exact ⟨2, by linarith⟩
        · exact ⟨1, by linarith⟩
      exact h2.trans (Nat.mul_dvd_mul_left _ (Nat.gcd_dvd_right a b))
    rw [Finset.gcd_mul_left] at h1
    simpa using h1
  have hprod : ∀ a ∈ B, p ∣ a → ∀ b ∈ B, ¬ p ∣ b →
      (∃ y, 0 < y ∧ y < B.card ∧ ¬ p ∣ y ∧
        ((2 * p * (B.filter (fun b => ¬ p ∣ b)).gcd id / a) * (b / (B.filter (fun b => ¬ p ∣ b)).gcd id) = 2 * y ∨
         ((2 * p * (B.filter (fun b => ¬ p ∣ b)).gcd id / a) * (b / (B.filter (fun b => ¬ p ∣ b)).gcd id) = y ∧ ¬ 2 ∣ y))) ∧
      a * (2 * p * (B.filter (fun b => ¬ p ∣ b)).gcd id / a) = 2 * p * (B.filter (fun b => ¬ p ∣ b)).gcd id := by
    intro a ha hpa b hb hpb
    have hd := hdiv a ha hpa
    have hGb' := hGb b hb hpb
    generalize (B.filter (fun b => ¬ p ∣ b)).gcd id = G at *
    obtain ⟨e, he⟩ := hd
    obtain ⟨s, hs⟩ := hGb'
    obtain ⟨y, hy0, hyn, hpy, hy, h⟩ := hA a ha hpa b hb hpb
    have ha0' := hpos a ha
    have hg0 : 0 < a.gcd b := Nat.gcd_pos_of_pos_left b ha0'
    have hx : 2 * p * G / a = e := by rw [he]; exact Nat.mul_div_cancel_left e ha0'
    have ht : b / G = s := by
      rw [hs]; exact Nat.mul_div_cancel_left s (Nat.pos_of_ne_zero hG0)
    rw [hx, ht]
    have hmain : a * (e * s) = 2 * p * (a.gcd b * y) := by
      calc a * (e * s) = (a * e) * s := by ring
        _ = 2 * p * (G * s) := by rw [← he]; ring
        _ = 2 * p * (a.gcd b * y) := by rw [← hs, ← hy]
    refine ⟨⟨y, hy0, hyn, hpy, ?_⟩, he.symm⟩
    rcases h with h | ⟨h, h2y⟩
    · left
      have h5 : p * a.gcd b * (e * s) = p * a.gcd b * (2 * y) := by
        calc p * a.gcd b * (e * s) = a * (e * s) := by rw [← h]
          _ = 2 * p * (a.gcd b * y) := hmain
          _ = p * a.gcd b * (2 * y) := by ring
      exact Nat.eq_of_mul_eq_mul_left (Nat.mul_pos hp.pos hg0) h5
    · right
      refine ⟨?_, h2y⟩
      have h5 : 2 * p * a.gcd b * (e * s) = 2 * p * a.gcd b * y := by
        calc 2 * p * a.gcd b * (e * s) = a * (e * s) := by rw [← h]
          _ = 2 * p * (a.gcd b * y) := hmain
          _ = 2 * p * a.gcd b * y := by ring
      exact Nat.eq_of_mul_eq_mul_left (Nat.mul_pos (Nat.mul_pos (by norm_num) hp.pos) hg0) h5
  have hcardsum : (B.filter (fun a => p ∣ a)).card + (B.filter (fun b => ¬ p ∣ b)).card = B.card := by
    rw [← Finset.card_union_of_disjoint (Finset.disjoint_filter_filter_not B B (fun a => p ∣ a)),
      Finset.filter_union_filter_not_eq]
  have hinjX : Set.InjOn (fun a => 2 * p * (B.filter (fun b => ¬ p ∣ b)).gcd id / a)
      (B.filter (fun a => p ∣ a) : Finset ℕ) := by
    intro a ha a' ha' h
    obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
    obtain ⟨haB', hpa'⟩ := Finset.mem_filter.mp ha'
    have h1 := (hprod a haB hpa b0 hb0 hpb0).2
    have h2 := (hprod a' haB' hpa' b0 hb0 hpb0).2
    simp only at h
    rw [← h] at h2
    have hq : 0 < 2 * p * (B.filter (fun b => ¬ p ∣ b)).gcd id / a := by
      apply Nat.pos_of_ne_zero
      intro hz
      rw [hz, Nat.mul_zero] at h1
      have := Nat.mul_pos (Nat.mul_pos (by norm_num : 0 < 2) hp.pos) (Nat.pos_of_ne_zero hG0)
      omega
    exact Nat.eq_of_mul_eq_mul_right hq (h1.trans h2.symm)
  have hinjT : Set.InjOn (fun b => b / (B.filter (fun b => ¬ p ∣ b)).gcd id)
      (B.filter (fun b => ¬ p ∣ b) : Finset ℕ) := by
    intro b hb b' hb' h
    obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
    obtain ⟨hbB', hpb'⟩ := Finset.mem_filter.mp hb'
    simp only at h
    rw [← Nat.div_mul_cancel (hGb b hbB hpb), ← Nat.div_mul_cancel (hGb b' hbB' hpb'), h]
  have hK := R2b.K2 B.card p
    ((B.filter (fun a => p ∣ a)).image (fun a => 2 * p * (B.filter (fun b => ¬ p ∣ b)).gcd id / a))
    ((B.filter (fun b => ¬ p ∣ b)).image (fun b => b / (B.filter (fun b => ¬ p ∣ b)).gcd id))
    hp.pos h2p h9
    (by
      intro x hx t ht
      obtain ⟨a, ha, rfl⟩ := Finset.mem_image.mp hx
      obtain ⟨b, hb, rfl⟩ := Finset.mem_image.mp ht
      obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
      obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
      exact (hprod a haB hpa b hbB hpb).1)
    ⟨_, Finset.mem_image_of_mem _ (Finset.mem_filter.mpr ⟨ha0, hpa0⟩)⟩
    ⟨_, Finset.mem_image_of_mem _ (Finset.mem_filter.mpr ⟨hb0, hpb0⟩)⟩
    (by rw [Finset.card_image_of_injOn hinjX, Finset.card_image_of_injOn hinjT, hcardsum])
  rcases hK with hX1 | hS1
  · -- every multiple of p equals 2pG, G = 1: B = {2p} ∪ T, impossible by Lemma I
    exfalso
    have hall : ∀ a ∈ B, p ∣ a → a = 2 * p * (B.filter (fun b => ¬ p ∣ b)).gcd id := by
      intro a ha hpa
      have h1 := hX1 _ (Finset.mem_image_of_mem _ (Finset.mem_filter.mpr ⟨ha, hpa⟩))
      have h2 := (hprod a ha hpa b0 hb0 hpb0).2
      rw [h1, Nat.mul_one] at h2
      exact h2
    have hG1 : (B.filter (fun b => ¬ p ∣ b)).gcd id = 1 := by
      have h1 : (B.filter (fun b => ¬ p ∣ b)).gcd id ∣ B.gcd id := by
        apply Finset.dvd_gcd
        intro b hb
        by_cases hpb : p ∣ b
        · exact ⟨2 * p, by rw [id, hall b hb hpb]; ring⟩
        · exact hGb b hb hpb
      rw [hgcd] at h1
      exact Nat.dvd_one.mp h1
    rw [hG1, Nat.mul_one] at hall
    have h2pB : 2 * p ∈ B := by rw [← hall a0 ha0 hpa0]; exact ha0
    have hT : ∀ b ∈ B.erase (2 * p), b ∈ B ∧ ¬ p ∣ b := by
      intro b hb
      obtain ⟨hne, hbB⟩ := Finset.mem_erase.mp hb
      exact ⟨hbB, fun h => hne (hall b hbB h)⟩
    have hbound : ∀ b ∈ B.erase (2 * p), b < B.card * b.gcd 2 := by
      intro b hb
      obtain ⟨hbB, hpb⟩ := hT b hb
      have h1 := hlt b hbB (2 * p) h2pB
      have hc : Nat.Coprime p b := (Nat.Prime.coprime_iff_not_dvd hp).mpr hpb
      rwa [Nat.Coprime.gcd_mul_right_cancel_right 2 hc] at h1
    have hI := R2b.lemI B.card p (B.erase (2 * p)) hp hp3 h2p hn3
      (fun b hb => hpos b (hT b hb).1) (fun b hb => (hT b hb).2)
      (by
        intro b hb h2
        have h1 := hbound b hb
        have hc : Nat.Coprime b 2 :=
          Nat.Coprime.symm ((Nat.Prime.coprime_iff_not_dvd Nat.prime_two).mpr h2)
        rw [Nat.Coprime.gcd_eq_one hc] at h1
        omega)
      (by
        intro b hb _
        have h1 := hbound b hb
        have h3 : b.gcd 2 ≤ 2 := Nat.gcd_le_right b (by norm_num)
        have h4 : B.card * b.gcd 2 ≤ B.card * 2 := Nat.mul_le_mul_left _ h3
        omega)
      (fun b hb t ht _ _ => hlt b (hT b hb).1 t (hT t ht).1)
    rw [Finset.card_erase_of_mem h2pB] at hI
    omega
  · -- every non-multiple equals G
    have hall : ∀ b ∈ B, ¬ p ∣ b → b = (B.filter (fun b => ¬ p ∣ b)).gcd id := by
      intro b hb hpb
      have h1 := hS1 _ (Finset.mem_image_of_mem _ (Finset.mem_filter.mpr ⟨hb, hpb⟩))
      have h2 := Nat.div_mul_cancel (hGb b hb hpb)
      rw [h1, Nat.one_mul] at h2
      exact h2.symm
    have hb0G := hall b0 hb0 hpb0
    refine ⟨b0, hb0, hpb0, ?_, ?_⟩
    · intro b hb hpb
      rw [hall b hb hpb, ← hb0G]
    · intro a ha
      by_cases hpa : p ∣ a
      · rw [hb0G]; exact hdiv a ha hpa
      · rw [hall a ha hpa, ← hb0G]; exact Dvd.intro_left _ rfl
