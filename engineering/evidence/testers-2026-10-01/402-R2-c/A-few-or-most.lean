import Mathlib

/-- A ("few or almost all", exact form). B a set of positive integers, all quotients
a / gcd(a,b) < N, p any prime, M any positive common multiple of the m with m * p < N.
Then (#multiples of p) * (#non-multiples of p) < N * M. No hypothesis on p-adic valuations. -/
theorem R2c.few_or_most (B : Finset ℕ) (N p M : ℕ) (h0 : 0 ∉ B) (hne : B.Nonempty)
    (hp : p.Prime) (hM0 : 0 < M) (hM : ∀ m : ℕ, 0 < m → m * p < N → m ∣ M)
    (hs : ∀ a ∈ B, ∀ b ∈ B, a < N * Nat.gcd a b) :
    (B.filter (fun a => p ∣ a)).card * (B.filter (fun b => ¬ p ∣ b)).card < N * M := by
  have key : ∀ (Y : Finset ℕ) (hY : Y.Nonempty), 0 ∉ Y → Y.card ≤ Y.max' hY := by
    intro Y hY h0
    have hsub : Y ⊆ Finset.Icc 1 (Y.max' hY) := by
      intro y hy
      rw [Finset.mem_Icc]
      exact ⟨Nat.pos_of_ne_zero (fun e => h0 (e ▸ hy)), Y.le_max' y hy⟩
    have := Finset.card_le_card hsub
    simpa using this
  have hpos : ∀ a ∈ B, 0 < a := fun a ha => Nat.pos_of_ne_zero (fun e => h0 (e ▸ ha))
  have hN : 0 < N := by
    obtain ⟨a, ha⟩ := hne
    have := hs a ha a ha
    exact Nat.pos_of_ne_zero (by rintro rfl; simp at this)
  have hNM : 0 < N * M := Nat.mul_pos hN hM0
  rcases Finset.eq_empty_or_nonempty (B.filter (fun a => p ∣ a)) with hU | hU
  · rw [hU]; simpa using hNM
  rcases Finset.eq_empty_or_nonempty (B.filter (fun b => ¬ p ∣ b)) with hC | hC
  · rw [hC]; simpa using hNM
  generalize hG : (B.filter (fun b => ¬ p ∣ b)).gcd id = G
  have hGb : ∀ b ∈ B, ¬ p ∣ b → G ∣ b := by
    intro b hb hpb
    rw [← hG]
    exact Finset.gcd_dvd (f := id) (Finset.mem_filter.mpr ⟨hb, hpb⟩)
  have hG0 : 0 < G := by
    obtain ⟨b, hb⟩ := hC
    obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
    exact Nat.pos_of_dvd_of_pos (hGb b hbB hpb) (hpos b hbB)
  -- the pair analysis
  have hpair : ∀ a ∈ B, p ∣ a → ∀ b ∈ B, ¬ p ∣ b →
      a ∣ p * M * b ∧ ∀ e s : ℕ, a * e * s = p * M * b → e * s < N * M := by
    intro a ha hpa b hb hpb
    have hg0 : 0 < a.gcd b := Nat.gcd_pos_of_pos_left b (hpos a ha)
    obtain ⟨x, hx⟩ := Nat.gcd_dvd_left a b
    obtain ⟨y, hy⟩ := Nat.gcd_dvd_right a b
    have hpg : ¬ p ∣ a.gcd b := fun h => hpb (h.trans (Nat.gcd_dvd_right a b))
    have hpx : p ∣ x := by
      have h1 : p ∣ a.gcd b * x := hx ▸ hpa
      exact (hp.dvd_mul.mp h1).resolve_left hpg
    obtain ⟨m, hm⟩ := hpx
    have hxN : x < N := by
      have h1 := hs a ha b hb
      have h3 : a.gcd b * x < a.gcd b * N := by
        rw [← hx, Nat.mul_comm]; exact h1
      exact Nat.lt_of_mul_lt_mul_left h3
    have hyN : y < N := by
      have h1 := hs b hb a ha
      rw [Nat.gcd_comm b a] at h1
      have h3 : a.gcd b * y < a.gcd b * N := by
        rw [← hy, Nat.mul_comm]; exact h1
      exact Nat.lt_of_mul_lt_mul_left h3
    have hx0 : 0 < x := Nat.pos_of_ne_zero (by
      rintro rfl
      rw [Nat.mul_zero] at hx
      exact (hpos a ha).ne' hx)
    have hm0 : 0 < m := Nat.pos_of_ne_zero (by
      rintro rfl
      rw [Nat.mul_zero] at hm
      exact hx0.ne' hm)
    have hmM : m ∣ M := hM m hm0 (by rw [Nat.mul_comm, ← hm]; exact hxN)
    obtain ⟨m', hm'⟩ := hmM
    have hm'0 : 0 < m' := Nat.pos_of_ne_zero (by
      rintro rfl
      rw [Nat.mul_zero] at hm'
      exact hM0.ne' hm')
    have ea : a = a.gcd b * (p * m) := by rw [← hm]; exact hx
    refine ⟨⟨m' * y, ?_⟩, ?_⟩
    · calc p * M * b = p * (m * m') * (a.gcd b * y) := by rw [← hm', ← hy]
        _ = a.gcd b * (p * m) * (m' * y) := by ring
        _ = a * (m' * y) := by rw [← ea]
    · intro e s hes
      have h1 : (a.gcd b * p * m) * (e * s) = (a.gcd b * p * m) * (m' * y) := by
        calc (a.gcd b * p * m) * (e * s) = (a.gcd b * (p * m)) * e * s := by ring
          _ = a * e * s := by rw [← ea]
          _ = p * M * b := hes
          _ = p * (m * m') * (a.gcd b * y) := by rw [← hm', ← hy]
          _ = (a.gcd b * p * m) * (m' * y) := by ring
      have h2 : e * s = m' * y :=
        Nat.eq_of_mul_eq_mul_left (Nat.mul_pos (Nat.mul_pos hg0 hp.pos) hm0) h1
      have h3 : m' ≤ M := Nat.le_of_dvd hM0 ⟨m, by rw [hm', Nat.mul_comm]⟩
      rw [h2, Nat.mul_comm N M]
      calc m' * y ≤ M * y := Nat.mul_le_mul_right y h3
        _ < M * N := Nat.mul_lt_mul_of_pos_left hyN hM0
  -- every multiple of p divides p * M * G
  have hdiv : ∀ a ∈ B, p ∣ a → a ∣ p * M * G := by
    intro a ha hpa
    have h1 : a ∣ (B.filter (fun b => ¬ p ∣ b)).gcd (fun b => p * M * id b) := by
      apply Finset.dvd_gcd
      intro b hb
      obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
      exact (hpair a ha hpa b hbB hpb).1
    rw [Finset.gcd_mul_left, hG] at h1
    simpa using h1
  have hprod : ∀ a ∈ B, p ∣ a → ∀ b ∈ B, ¬ p ∣ b →
      (p * M * G / a) * (b / G) < N * M ∧ a * (p * M * G / a) = p * M * G ∧
        0 < p * M * G / a ∧ 0 < b / G := by
    intro a ha hpa b hb hpb
    have e1 : a * (p * M * G / a) = p * M * G := Nat.mul_div_cancel' (hdiv a ha hpa)
    have e2 : G * (b / G) = b := Nat.mul_div_cancel' (hGb b hb hpb)
    have hPos : 0 < p * M * G := Nat.mul_pos (Nat.mul_pos hp.pos hM0) hG0
    refine ⟨(hpair a ha hpa b hb hpb).2 _ _ ?_, e1, ?_, ?_⟩
    · rw [e1, Nat.mul_assoc (p * M), e2]
    · exact Nat.pos_of_ne_zero (by
        intro h
        rw [h, Nat.mul_zero] at e1
        exact hPos.ne e1)
    · exact Nat.pos_of_ne_zero (by
        intro h
        rw [h, Nat.mul_zero] at e2
        exact (hpos b hb).ne e2)
  obtain ⟨a0, ha0⟩ := hU
  obtain ⟨b0, hb0⟩ := hC
  obtain ⟨ha0B, hpa0⟩ := Finset.mem_filter.mp ha0
  obtain ⟨hb0B, hpb0⟩ := Finset.mem_filter.mp hb0
  have hinjX : Set.InjOn (fun a => p * M * G / a) (B.filter (fun a => p ∣ a) : Finset ℕ) := by
    intro a ha a' ha' h
    obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
    obtain ⟨haB', hpa'⟩ := Finset.mem_filter.mp ha'
    have h1 := hprod a haB hpa b0 hb0B hpb0
    have h2 := (hprod a' haB' hpa' b0 hb0B hpb0).2.1
    simp only at h
    rw [← h] at h2
    exact Nat.eq_of_mul_eq_mul_right h1.2.2.1 (h1.2.1.trans h2.symm)
  have hinjT : Set.InjOn (fun b => b / G) (B.filter (fun b => ¬ p ∣ b) : Finset ℕ) := by
    intro b hb b' hb' h
    obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
    obtain ⟨hbB', hpb'⟩ := Finset.mem_filter.mp hb'
    simp only at h
    rw [← Nat.div_mul_cancel (hGb b hbB hpb), ← Nat.div_mul_cancel (hGb b' hbB' hpb'), h]
  have hXn : ((B.filter (fun a => p ∣ a)).image (fun a => p * M * G / a)).Nonempty :=
    ⟨_, Finset.mem_image_of_mem _ ha0⟩
  have hTn : ((B.filter (fun b => ¬ p ∣ b)).image (fun b => b / G)).Nonempty :=
    ⟨_, Finset.mem_image_of_mem _ hb0⟩
  have hX0 : 0 ∉ (B.filter (fun a => p ∣ a)).image (fun a => p * M * G / a) := by
    intro h
    obtain ⟨a, ha, e⟩ := Finset.mem_image.mp h
    obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
    exact (hprod a haB hpa b0 hb0B hpb0).2.2.1.ne' e
  have hT0 : 0 ∉ (B.filter (fun b => ¬ p ∣ b)).image (fun b => b / G) := by
    intro h
    obtain ⟨b, hb, e⟩ := Finset.mem_image.mp h
    obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
    exact (hprod a0 ha0B hpa0 b hbB hpb).2.2.2.ne' e
  have hmx := Finset.max'_mem _ hXn
  have hmt := Finset.max'_mem _ hTn
  obtain ⟨a1, ha1, ea1⟩ := Finset.mem_image.mp hmx
  obtain ⟨b1, hb1, eb1⟩ := Finset.mem_image.mp hmt
  obtain ⟨ha1B, hpa1⟩ := Finset.mem_filter.mp ha1
  obtain ⟨hb1B, hpb1⟩ := Finset.mem_filter.mp hb1
  have hfin := (hprod a1 ha1B hpa1 b1 hb1B hpb1).1
  rw [ea1, eb1] at hfin
  have c1 := key _ hXn hX0
  have c2 := key _ hTn hT0
  rw [Finset.card_image_of_injOn hinjX] at c1
  rw [Finset.card_image_of_injOn hinjT] at c2
  exact lt_of_le_of_lt (Nat.mul_le_mul c1 c2) hfin
