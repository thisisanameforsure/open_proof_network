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

/-- A1. Card form: n = |B| ≤ (k+1)·p, M a positive common multiple of 1..k. Then fewer than
2M elements are multiples of p, or fewer than 2M are not. -/
theorem R2c.few_or_most_card (B : Finset ℕ) (p k M : ℕ) (h0 : 0 ∉ B) (hne : B.Nonempty)
    (hp : p.Prime) (hM0 : 0 < M) (hM : ∀ m : ℕ, 0 < m → m ≤ k → m ∣ M)
    (hk : B.card ≤ (k + 1) * p)
    (hs : ∀ a ∈ B, ∀ b ∈ B, a < B.card * Nat.gcd a b) :
    (B.filter (fun a => p ∣ a)).card < 2 * M ∨ (B.filter (fun b => ¬ p ∣ b)).card < 2 * M := by
  have h := R2c.few_or_most B B.card p M h0 hne hp hM0 (by
    intro m hm0 hmp
    apply hM m hm0
    by_contra hcon
    push Not at hcon
    have : (k + 1) * p ≤ m * p := Nat.mul_le_mul_right p hcon
    omega) hs
  have hsum : (B.filter (fun a => p ∣ a)).card + (B.filter (fun b => ¬ p ∣ b)).card = B.card := by
    rw [← Finset.card_union_of_disjoint (Finset.disjoint_filter_filter_not B B (fun a => p ∣ a)),
      Finset.filter_union_filter_not_eq]
  rw [← hsum] at h
  by_contra hcon
  push Not at hcon
  nlinarith [hcon.1, hcon.2, Nat.mul_le_mul hcon.1 hcon.2]

/-- A2. k = 2 (n ≤ 3p, n ≥ 9): at most two multiples of p, or at most two non-multiples. -/
theorem R2c.few_or_most_third (B : Finset ℕ) (p : ℕ) (h0 : 0 ∉ B)
    (hp : p.Prime) (h9 : 9 ≤ B.card) (hk : B.card ≤ 3 * p)
    (hs : ∀ a ∈ B, ∀ b ∈ B, a < B.card * Nat.gcd a b) :
    (B.filter (fun a => p ∣ a)).card ≤ 2 ∨ (B.filter (fun b => ¬ p ∣ b)).card ≤ 2 := by
  have hne : B.Nonempty := Finset.card_pos.mp (by omega)
  have h := R2c.few_or_most B B.card p 2 h0 hne hp (by norm_num) (by
    intro m hm0 hmp
    have hm : m ≤ 2 := by
      by_contra hcon
      push Not at hcon
      have : 3 * p ≤ m * p := Nat.mul_le_mul_right p hcon
      omega
    interval_cases m
    · exact one_dvd 2
    · exact dvd_rfl) hs
  have hsum : (B.filter (fun a => p ∣ a)).card + (B.filter (fun b => ¬ p ∣ b)).card = B.card := by
    rw [← Finset.card_union_of_disjoint (Finset.disjoint_filter_filter_not B B (fun a => p ∣ a)),
      Finset.filter_union_filter_not_eq]
  rw [← hsum] at h h9
  by_contra hcon
  push Not at hcon
  obtain ⟨u, hu⟩ : ∃ u, (B.filter (fun a => p ∣ a)).card = u + 3 := ⟨_, (Nat.sub_add_cancel hcon.1).symm⟩
  obtain ⟨v, hv⟩ : ∃ v, (B.filter (fun b => ¬ p ∣ b)).card = v + 3 := ⟨_, (Nat.sub_add_cancel hcon.2).symm⟩
  rw [hu, hv] at h h9
  nlinarith [Nat.zero_le (u * v)]

/-- B'. WLOG "few multiples". Fix n and a prime p. If every admissible B (hole hypotheses, p
divides an element, p² divides none) with at most n/2 multiples of p has a good pair, then every
admissible B has one. -/
theorem R2c.wlog_few (n p : ℕ) (hp : p.Prime)
    (H : ∀ B : Finset ℕ, 0 ∉ B → B.Nonempty → B.card = n → B.gcd id = 1 →
      (∀ a ∈ B, ∀ b ∈ B, a ≤ n * Nat.gcd a b) →
      (∀ a ∈ B, ∀ q k : ℕ, q.Prime → q ^ k ∣ a → q ^ k < n) →
      (∃ a ∈ B, p ∣ a) → (∀ a ∈ B, ¬ p ^ 2 ∣ a) →
      2 * (B.filter (fun a => p ∣ a)).card ≤ n →
      ∃ a ∈ B, ∃ b ∈ B, n * Nat.gcd a b ≤ a) :
    ∀ B : Finset ℕ, 0 ∉ B → B.Nonempty → B.card = n → B.gcd id = 1 →
      (∀ a ∈ B, ∀ b ∈ B, a ≤ n * Nat.gcd a b) →
      (∀ a ∈ B, ∀ q k : ℕ, q.Prime → q ^ k ∣ a → q ^ k < n) →
      (∃ a ∈ B, p ∣ a) → (∀ a ∈ B, ¬ p ^ 2 ∣ a) →
      ∃ a ∈ B, ∃ b ∈ B, n * Nat.gcd a b ≤ a := by
  intro B h0 hne hcard hgcd hle hpp hex hsq
  by_cases hfew : 2 * (B.filter (fun a => p ∣ a)).card ≤ n
  · exact H B h0 hne hcard hgcd hle hpp hex hsq hfew
  · obtain ⟨d1, d2, d3, d4, d5, d6, d7, d8⟩ := R2c.dual_package B n hne h0
    obtain ⟨hiff, c1, c2⟩ := d8 p hp hex hsq
    have hsum : (B.filter (fun a => p ∣ a)).card + (B.filter (fun b => ¬ p ∣ b)).card = B.card := by
      rw [← Finset.card_union_of_disjoint (Finset.disjoint_filter_filter_not B B (fun a => p ∣ a)),
        Finset.filter_union_filter_not_eq]
    have hexb : ∃ b ∈ B, ¬ p ∣ b := by
      by_contra h
      push Not at h
      have h1 : p ∣ B.gcd id := Finset.dvd_gcd (fun b hb => h b hb)
      rw [hgcd] at h1
      exact hp.one_lt.ne' (Nat.dvd_one.mp h1)
    obtain ⟨b, hb, hpb⟩ := hexb
    apply d7
    apply H _ d3 d2 (d1.trans hcard) d4 (d6 hle)
    · intro x hx q k hq hqx
      obtain ⟨a, ha, hda⟩ := d5 x hx q k hq hqx
      exact hpp a ha q k hq hda
    · exact ⟨_, Finset.mem_image_of_mem _ hb, (hiff b hb).mpr hpb⟩
    · intro x hx hpx
      obtain ⟨a, ha, hda⟩ := d5 x hx p 2 hp hpx
      exact hsq a ha hda
    · rw [c1]; omega
