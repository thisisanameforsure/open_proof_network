import Mathlib

/-- Block-to-kernel reduction, general range (any prime `p`, any bound `N`, any `M` that is a common
multiple of the `m` with `m * p < N`).  A set `B` of positive integers with all quotients
`a / gcd a b < N`, containing a multiple and a non-multiple of `p`, yields two sets `X` (one member
per multiple of `p`) and `S` (one per non-multiple), each again `N`-strict, with the cross relation
`x * s * m = M * y`, `0 < m`, `m * p < N`, `y < N`, `p ∤ y`, `m ⟂ y`. -/
theorem R3c.block_kernel (B : Finset ℕ) (N p M : ℕ) (h0 : 0 ∉ B) (hp : p.Prime) (hM0 : 0 < M)
    (hM : ∀ m : ℕ, 0 < m → m * p < N → m ∣ M)
    (hs : ∀ a ∈ B, ∀ b ∈ B, a < N * Nat.gcd a b)
    (hU : ∃ a ∈ B, p ∣ a) (hV : ∃ b ∈ B, ¬ p ∣ b) :
    ∃ X S : Finset ℕ, X.card = (B.filter (fun a => p ∣ a)).card ∧
      S.card = (B.filter (fun b => ¬ p ∣ b)).card ∧
      (∀ x ∈ X, 0 < x) ∧ (∀ s ∈ S, 0 < s) ∧ (∀ s ∈ S, ¬ p ∣ s) ∧
      (¬ p ∣ M → ∀ x ∈ X, ¬ p ∣ x) ∧
      (∀ x ∈ X, ∀ x' ∈ X, x < N * Nat.gcd x x') ∧
      (∀ s ∈ S, ∀ t ∈ S, s < N * Nat.gcd s t) ∧
      (∀ x ∈ X, ∀ s ∈ S, ∃ m y : ℕ, 0 < m ∧ m * p < N ∧ y < N ∧ ¬ p ∣ y ∧ Nat.Coprime m y ∧
        x * s * m = M * y) := by
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
  have hpos : ∀ a ∈ B, 0 < a := fun a ha => Nat.pos_of_ne_zero (fun e => h0 (e ▸ ha))
  generalize hG : (B.filter (fun b => ¬ p ∣ b)).gcd id = G
  have hGb : ∀ b ∈ B, ¬ p ∣ b → G ∣ b := by
    intro b hb hpb
    rw [← hG]
    exact Finset.gcd_dvd (f := id) (Finset.mem_filter.mpr ⟨hb, hpb⟩)
  obtain ⟨a0, ha0B, hpa0⟩ := hU
  obtain ⟨b0, hb0B, hpb0⟩ := hV
  have hG0 : 0 < G := Nat.pos_of_dvd_of_pos (hGb b0 hb0B hpb0) (hpos b0 hb0B)
  have hpG : ¬ p ∣ G := fun h => hpb0 (h.trans (hGb b0 hb0B hpb0))
  -- the pair analysis
  have hpair : ∀ a ∈ B, p ∣ a → ∀ b ∈ B, ¬ p ∣ b →
      ∃ m y : ℕ, 0 < m ∧ m * p < N ∧ y < N ∧ ¬ p ∣ y ∧ Nat.Coprime m y ∧ a * y = p * m * b := by
    intro a ha hpa b hb hpb
    have hg0 : 0 < a.gcd b := Nat.gcd_pos_of_pos_left b (hpos a ha)
    obtain ⟨x, hx⟩ := Nat.gcd_dvd_left a b
    obtain ⟨y, hy⟩ := Nat.gcd_dvd_right a b
    have hcop : Nat.Coprime x y := by
      have h := Nat.coprime_div_gcd_div_gcd hg0
      rwa [Nat.div_eq_of_eq_mul_right hg0 hx, Nat.div_eq_of_eq_mul_right hg0 hy] at h
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
    refine ⟨m, y, hm0, by rw [Nat.mul_comm, ← hm]; exact hxN, hyN, ?_, ?_, ?_⟩
    · exact fun h => hpb (h.trans ⟨a.gcd b, by rw [Nat.mul_comm]; exact hy⟩)
    · rw [hm] at hcop
      exact Nat.Coprime.coprime_mul_left hcop
    · calc a * y = a.gcd b * x * y := by rw [← hx]
        _ = p * m * (a.gcd b * y) := by rw [hm]; ring
        _ = p * m * b := by rw [← hy]
  -- every multiple of p divides p * M * G
  have hdiv : ∀ a ∈ B, p ∣ a → a ∣ p * M * G := by
    intro a ha hpa
    have h1 : a ∣ (B.filter (fun b => ¬ p ∣ b)).gcd (fun b => p * M * id b) := by
      apply Finset.dvd_gcd
      intro b hb
      obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
      obtain ⟨m, y, hm0, hmp, -, -, -, e⟩ := hpair a ha hpa b hbB hpb
      obtain ⟨m', hm'⟩ := hM m hm0 hmp
      exact ⟨y * m', by
        show p * M * b = a * (y * m')
        rw [← Nat.mul_assoc, e, hm']; ring⟩
    rw [Finset.gcd_mul_left, hG] at h1
    simpa using h1
  have hLpos : 0 < p * M * G := Nat.mul_pos (Nat.mul_pos hp.pos hM0) hG0
  have hax : ∀ a ∈ B, p ∣ a → a * (p * M * G / a) = p * M * G :=
    fun a ha hpa => Nat.mul_div_cancel' (hdiv a ha hpa)
  have hxpos : ∀ a ∈ B, p ∣ a → 0 < p * M * G / a := by
    intro a ha hpa
    exact Nat.pos_of_ne_zero (by
      intro h
      have e1 := hax a ha hpa
      rw [h, Nat.mul_zero] at e1
      exact hLpos.ne e1)
  have hbs : ∀ b ∈ B, ¬ p ∣ b → G * (b / G) = b :=
    fun b hb hpb => Nat.mul_div_cancel' (hGb b hb hpb)
  have hspos : ∀ b ∈ B, ¬ p ∣ b → 0 < b / G := by
    intro b hb hpb
    exact Nat.pos_of_ne_zero (by
      intro h
      have e2 := hbs b hb hpb
      rw [h, Nat.mul_zero] at e2
      exact (hpos b hb).ne e2)
  have hinjX : Set.InjOn (fun a => p * M * G / a) (B.filter (fun a => p ∣ a) : Finset ℕ) := by
    intro a ha a' ha' h
    obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
    obtain ⟨haB', hpa'⟩ := Finset.mem_filter.mp ha'
    have h1 := hax a haB hpa
    have h2 := hax a' haB' hpa'
    simp only at h
    rw [← h] at h2
    exact Nat.eq_of_mul_eq_mul_right (hxpos a haB hpa) (h1.trans h2.symm)
  have hinjT : Set.InjOn (fun b => b / G) (B.filter (fun b => ¬ p ∣ b) : Finset ℕ) := by
    intro b hb b' hb' h
    obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
    obtain ⟨hbB', hpb'⟩ := Finset.mem_filter.mp hb'
    simp only at h
    rw [← Nat.div_mul_cancel (hGb b hbB hpb), ← Nat.div_mul_cancel (hGb b' hbB' hpb'), h]
  refine ⟨(B.filter (fun a => p ∣ a)).image (fun a => p * M * G / a),
    (B.filter (fun b => ¬ p ∣ b)).image (fun b => b / G),
    Finset.card_image_of_injOn hinjX, Finset.card_image_of_injOn hinjT, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · intro x hx
    obtain ⟨a, ha, rfl⟩ := Finset.mem_image.mp hx
    obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
    exact hxpos a haB hpa
  · intro s hs'
    obtain ⟨b, hb, rfl⟩ := Finset.mem_image.mp hs'
    obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
    exact hspos b hbB hpb
  · intro s hs' hps
    obtain ⟨b, hb, rfl⟩ := Finset.mem_image.mp hs'
    obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
    exact hpb (hps.trans ⟨G, by rw [Nat.mul_comm]; exact (hbs b hbB hpb).symm⟩)
  · intro hpM x hx hpx
    obtain ⟨a, ha, rfl⟩ := Finset.mem_image.mp hx
    obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
    obtain ⟨c, hc⟩ := hpa
    obtain ⟨d, hd⟩ := hpx
    have e := hax a haB ⟨c, hc⟩
    rw [hd] at e
    have h3 : p * (p * (c * d)) = p * (M * G) := by
      rw [← Nat.mul_assoc p M G, ← e, hc]; ring
    have h4 : p ∣ M * G := ⟨c * d, (Nat.eq_of_mul_eq_mul_left hp.pos h3).symm⟩
    rcases hp.dvd_mul.mp h4 with h5 | h5
    · exact hpM h5
    · exact hpG h5
  · intro x hx x' hx'
    obtain ⟨a, ha, rfl⟩ := Finset.mem_image.mp hx
    obtain ⟨a', ha', rfl⟩ := Finset.mem_image.mp hx'
    obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
    obtain ⟨haB', hpa'⟩ := Finset.mem_filter.mp ha'
    have e := dual_quot (p * M * G) a (p * M * G / a) a' (p * M * G / a')
      (hax a haB hpa) (hax a' haB' hpa') (hpos a haB)
    have h1 := hs a' haB' a haB
    rw [Nat.gcd_comm a' a] at h1
    have hg : 0 < Nat.gcd a a' := Nat.gcd_pos_of_pos_left _ (hpos a haB)
    have h2 : (p * M * G / a) * Nat.gcd a a'
        < (N * Nat.gcd (p * M * G / a) (p * M * G / a')) * Nat.gcd a a' := by
      rw [e]
      calc a' * Nat.gcd (p * M * G / a) (p * M * G / a')
          < N * Nat.gcd a a' * Nat.gcd (p * M * G / a) (p * M * G / a') :=
            Nat.mul_lt_mul_of_pos_right h1
              (Nat.gcd_pos_of_pos_left _ (hxpos a haB hpa))
        _ = (N * Nat.gcd (p * M * G / a) (p * M * G / a')) * Nat.gcd a a' := by ring
    exact Nat.lt_of_mul_lt_mul_right h2
  · intro s hs' t ht
    obtain ⟨b, hb, rfl⟩ := Finset.mem_image.mp hs'
    obtain ⟨b', hb', rfl⟩ := Finset.mem_image.mp ht
    obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
    obtain ⟨hbB', hpb'⟩ := Finset.mem_filter.mp hb'
    have h1 := hs b hbB b' hbB'
    have e1 := hbs b hbB hpb
    have e2 := hbs b' hbB' hpb'
    have h2 : G * (b / G) < G * (N * Nat.gcd (b / G) (b' / G)) := by
      calc G * (b / G) = b := e1
        _ < N * Nat.gcd b b' := h1
        _ = N * Nat.gcd (G * (b / G)) (G * (b' / G)) := by rw [e1, e2]
        _ = G * (N * Nat.gcd (b / G) (b' / G)) := by rw [Nat.gcd_mul_left]; ring
    exact Nat.lt_of_mul_lt_mul_left h2
  · intro x hx s hs'
    obtain ⟨a, ha, rfl⟩ := Finset.mem_image.mp hx
    obtain ⟨b, hb, rfl⟩ := Finset.mem_image.mp hs'
    obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
    obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
    obtain ⟨m, y, hm0, hmp, hyN, hpy, hcop, e⟩ := hpair a haB hpa b hbB hpb
    refine ⟨m, y, hm0, hmp, hyN, hpy, hcop, ?_⟩
    have e1 := hax a haB hpa
    have e2 := hbs b hbB hpb
    have h3 : (a * G) * ((p * M * G / a) * (b / G) * m) = (a * G) * (M * y) := by
      calc (a * G) * ((p * M * G / a) * (b / G) * m)
          = (a * (p * M * G / a)) * (G * (b / G)) * m := by ring
        _ = p * M * G * b * m := by rw [e1, e2]
        _ = M * G * (p * m * b) := by ring
        _ = M * G * (a * y) := by rw [e]
        _ = (a * G) * (M * y) := by ring
    exact Nat.eq_of_mul_eq_mul_left (Nat.mul_pos (hpos a haB) hG0) h3
