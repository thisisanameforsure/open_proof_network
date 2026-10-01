import Mathlib

open Filter

theorem erdos_402__h3_v2__h1__h1 : ∀ (B : Finset ℕ),
  (0 : ℕ) ∉ B →
    B.Nonempty →
      B.gcd id = (1 : ℕ) →
        ¬Nat.Prime B.card →
          (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
            (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
              (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                (∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ)) ∨
                  ∃ (p : ℕ), Nat.Prime p ∧ B.card ≤ (2 : ℕ) * p ∧ ∃ a ∈ B, p ∣ a := by
  -- Hole `hmid` (one hole, two parts, for every B with the hypotheses of this node):
  --  (1) B has a pair with gcd(a, b) ≤ a / n, or some prime p ≥ n / 3 divides an element of B;
  --  (2) for a prime n / 3 ≤ p < n / 2: if 2p ∈ B and 2p is the only multiple of p in B, then B has
  --      such a pair.
  -- The assembly proves, for a strict counterexample and a prime n / 3 ≤ p < n / 2 dividing an element:
  -- (u - 2)(v - 2) < 4 for the numbers u, v of multiples and non-multiples of p ("few or almost all");
  -- if u ≤ 2 then 2p is the only multiple of p in B; and the case v ≤ 2 is carried to the case u ≤ 2
  -- of the dual set {lcm(B) / a : a ∈ B} (checked Lean of agent 402-R2-c), which satisfies the same
  -- hypotheses. So the range n / 3 ≤ p < n / 2 is reduced to the single configuration of part (2).
  have hmid : ∀ B : Finset ℕ, 0 ∉ B → B.Nonempty → B.gcd id = 1 → ¬ B.card.Prime →
      (∀ q : ℕ, q.Prime → B.card ≠ q + 1) →
      (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
      (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card) →
      ((∃ a ∈ B, ∃ b ∈ B, (a.gcd b : ℚ) ≤ (a : ℚ) / (B.card : ℚ)) ∨
        ∃ p : ℕ, p.Prime ∧ B.card ≤ 3 * p ∧ ∃ a ∈ B, p ∣ a) ∧
      (∀ p : ℕ, p.Prime → 2 * p < B.card → B.card ≤ 3 * p → 2 * p ∈ B →
        (∀ a ∈ B, p ∣ a → a = 2 * p) →
        ∃ a ∈ B, ∃ b ∈ B, (a.gcd b : ℚ) ≤ (a : ℚ) / (B.card : ℚ)) := sorry
  have hdual : ∀ (B : Finset ℕ) (n : ℕ), B.Nonempty → 0 ∉ B →
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
    intro B n hne h0
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
  have big : ∀ S : Finset ℕ, (∀ x ∈ S, 0 < x) → S.Nonempty → ∃ x ∈ S, S.card ≤ x := by
    intro S hpos hS
    by_contra h
    push Not at h
    have hsub : S ⊆ Finset.Ioo 0 S.card := by
      intro x hx
      exact Finset.mem_Ioo.mpr ⟨hpos x hx, h x hx⟩
    have h1 := Finset.card_le_card hsub
    rw [Nat.card_Ioo] at h1
    have h2 := hS.card_pos
    omega
  have key : ∀ (N : ℕ) (X T : Finset ℕ),
      (∀ x ∈ X, ∀ t ∈ T, 0 < x * t ∧ x * t < N) →
      X.Nonempty → T.Nonempty → X.card * T.card < N := by
    intro N X T hxt hX hT
    have hXpos : ∀ x ∈ X, 0 < x := by
      intro x hx
      obtain ⟨t, ht⟩ := hT
      have h := (hxt x hx t ht).1
      exact Nat.pos_of_ne_zero (by rintro rfl; simp at h)
    have hTpos : ∀ t ∈ T, 0 < t := by
      intro t ht
      obtain ⟨x, hx⟩ := hX
      have h := (hxt x hx t ht).1
      exact Nat.pos_of_ne_zero (by rintro rfl; simp at h)
    obtain ⟨x0, hx0, hx0c⟩ := big X hXpos hX
    obtain ⟨t0, ht0, ht0c⟩ := big T hTpos hT
    exact lt_of_le_of_lt (Nat.mul_le_mul hx0c ht0c) (hxt x0 hx0 t0 ht0).2
  have hblock : ∀ B : Finset ℕ, 0 ∉ B →
      (∀ a ∈ B, ∀ b ∈ B, a < B.card * a.gcd b) →
      ∀ p : ℕ, p.Prime → B.card ≤ 3 * p →
      (∃ a ∈ B, p ∣ a) → (∃ b ∈ B, ¬ p ∣ b) →
      (B.filter (fun a => p ∣ a)).card * (B.filter (fun a => ¬ p ∣ a)).card < 2 * B.card ∧
      (2 * p < B.card → 6 ≤ B.card → B.gcd id = 1 →
        B.card ≤ (B.filter (fun a => ¬ p ∣ a)).card + 2 → ∀ a ∈ B, p ∣ a → a = 2 * p ∧
          ∀ b ∈ B, ¬ p ∣ b → (¬ 2 ∣ b → b < B.card) ∧ (2 ∣ b → b < 2 * B.card)) := by
    intro B h0 hlt p hp h3 hexa hexb
    obtain ⟨a0, ha0, hpa0⟩ := hexa
    obtain ⟨b0, hb0, hpb0⟩ := hexb
    obtain ⟨G, hGdef⟩ : ∃ G, G = (B.filter (fun b => ¬ p ∣ b)).gcd id := ⟨_, rfl⟩
    have hGb : ∀ b ∈ B, ¬ p ∣ b → G ∣ b := by
      intro b hb hpb
      rw [hGdef]
      exact Finset.gcd_dvd (f := id) (Finset.mem_filter.mpr ⟨hb, hpb⟩)
    have hG0 : 0 < G := by
      apply Nat.pos_of_ne_zero
      intro h
      have h1 := hGb b0 hb0 hpb0
      rw [h] at h1
      exact h0 (Nat.eq_zero_of_zero_dvd h1 ▸ hb0)
    have hm : ∀ a ∈ B, p ∣ a → ∀ b ∈ B, ¬ p ∣ b →
        ∃ m, (m = 1 ∨ m = 2) ∧ a = p * m * a.gcd b := by
      intro a ha hpa b hb hpb
      have ha0' : a ≠ 0 := fun h => h0 (h ▸ ha)
      obtain ⟨x, hx⟩ := Nat.gcd_dvd_left a b
      have hpg : ¬ p ∣ a.gcd b := fun h => hpb (h.trans (Nat.gcd_dvd_right a b))
      have hpx : p ∣ x := by
        have h1 : p ∣ a.gcd b * x := hx ▸ hpa
        exact (hp.dvd_mul.mp h1).resolve_left hpg
      obtain ⟨t, ht⟩ := hpx
      have hlt' := hlt a ha b hb
      have hxn : x < B.card := by
        have h4 : a.gcd b * x < a.gcd b * B.card := by
          rw [← hx, Nat.mul_comm]; exact hlt'
        exact Nat.lt_of_mul_lt_mul_left h4
      have hx0 : x ≠ 0 := by
        rintro rfl
        rw [Nat.mul_zero] at hx
        exact ha0' hx
      have ht0 : t ≠ 0 := by
        rintro rfl
        rw [Nat.mul_zero] at ht
        exact hx0 ht
      have ht3 : t < 3 := by
        by_contra hge
        have h5 : p * 3 ≤ p * t := Nat.mul_le_mul_left p (by omega)
        omega
      refine ⟨t, by omega, ?_⟩
      calc a = a.gcd b * x := hx
        _ = p * t * a.gcd b := by rw [ht]; ring
    have hdiv : ∀ a ∈ B, p ∣ a → a ∣ 2 * p * G := by
      intro a ha hpa
      have h1 : a ∣ (B.filter (fun b => ¬ p ∣ b)).gcd (fun b => (2 * p) * id b) := by
        apply Finset.dvd_gcd
        intro b hb'
        obtain ⟨hb, hpb⟩ := Finset.mem_filter.mp hb'
        obtain ⟨m, hm12, hae⟩ := hm a ha hpa b hb hpb
        obtain ⟨y, hy⟩ := Nat.gcd_dvd_right a b
        simp only [id]
        generalize a.gcd b = g at hae hy
        rcases hm12 with rfl | rfl
        · exact ⟨2 * y, by rw [hy, hae]; ring⟩
        · exact ⟨y, by rw [hy, hae]; ring⟩
      rw [Finset.gcd_mul_left, normalize_eq, ← hGdef] at h1
      exact h1
    have hfacts : ∀ a ∈ B, p ∣ a → ∀ b ∈ B, ¬ p ∣ b → ∃ e s m y, 2 * p * G = a * e ∧
        2 * p * G / a = e ∧ b / G = s ∧ (m = 1 ∨ m = 2) ∧ e * m * s = 2 * y ∧ 0 < y ∧
        y < B.card ∧ ¬ p ∣ s ∧ (m = 2 → ¬ 2 ∣ y) := by
      intro a ha hpa b hb hpb
      obtain ⟨e, he⟩ := hdiv a ha hpa
      obtain ⟨s, hs⟩ := hGb b hb hpb
      obtain ⟨m, hm12, hae⟩ := hm a ha hpa b hb hpb
      obtain ⟨y, hy⟩ := Nat.gcd_dvd_right a b
      have ha0' : 0 < a := Nat.pos_of_ne_zero (fun h => h0 (h ▸ ha))
      have hb0' : b ≠ 0 := fun h => h0 (h ▸ hb)
      have hltb := hlt b hb a ha
      rw [Nat.gcd_comm b a] at hltb
      have hg0 : 0 < a.gcd b := Nat.gcd_pos_of_pos_left b ha0'
      have hcop := Nat.coprime_div_gcd_div_gcd hg0
      generalize a.gcd b = g at hae hy hltb hg0 hcop
      have hx : 2 * p * G / a = e := Nat.div_eq_of_eq_mul_right ha0' he
      have ht : b / G = s := by
        rw [hs]
        exact Nat.mul_div_cancel_left s hG0
      have hyn : y < B.card := by
        have h4 : g * y < g * B.card :=
          calc g * y = b := hy.symm
            _ < B.card * g := hltb
            _ = g * B.card := Nat.mul_comm _ _
        exact Nat.lt_of_mul_lt_mul_left h4
      have hy0 : y ≠ 0 := by
        rintro rfl
        rw [Nat.mul_zero] at hy
        exact hb0' hy
      have hpg : 0 < p * g := Nat.mul_pos hp.pos hg0
      have hid : (p * g) * (e * m * s) = (p * g) * (2 * y) :=
        calc (p * g) * (e * m * s) = (p * m * g) * e * s := by ring
          _ = a * e * s := by rw [← hae]
          _ = 2 * p * G * s := by rw [he]
          _ = 2 * p * (G * s) := by ring
          _ = 2 * p * b := by rw [← hs]
          _ = 2 * p * (g * y) := by rw [← hy]
          _ = (p * g) * (2 * y) := by ring
      have hems : e * m * s = 2 * y := Nat.eq_of_mul_eq_mul_left hpg hid
      have hps : ¬ p ∣ s := fun h => hpb (hs ▸ Dvd.dvd.mul_left h G)
      have hodd : m = 2 → ¬ 2 ∣ y := by
        rintro rfl h2y
        have e1 : a / g = p * 2 := Nat.div_eq_of_eq_mul_left hg0 hae
        have e2 : b / g = y := Nat.div_eq_of_eq_mul_right hg0 hy
        rw [e1, e2] at hcop
        have h6 : 2 ∣ Nat.gcd (p * 2) y := Nat.dvd_gcd (Dvd.intro_left p rfl) h2y
        rw [hcop.gcd_eq_one] at h6
        omega
      exact ⟨e, s, m, y, he, hx, ht, hm12, hems, Nat.pos_of_ne_zero hy0, hyn, hps, hodd⟩
    have hprod : ∀ a ∈ B, p ∣ a → ∀ b ∈ B, ¬ p ∣ b →
        0 < (2 * p * G / a) * (b / G) ∧ (2 * p * G / a) * (b / G) < 2 * B.card := by
      intro a ha hpa b hb hpb
      obtain ⟨e, s, m, y, -, hx, ht, hm12, hems, hy0, hyn, -, -⟩ := hfacts a ha hpa b hb hpb
      rw [hx, ht]
      obtain ⟨z, hz⟩ : ∃ z, z = e * s := ⟨_, rfl⟩
      rw [← hz]
      rcases hm12 with rfl | rfl
      · have h5 : z = 2 * y := by rw [hz, ← hems]; ring
        omega
      · have h5 : 2 * z = 2 * y := by rw [hz, ← hems]; ring
        omega
    have hcancel : ∀ a ∈ B, p ∣ a → a * (2 * p * G / a) = 2 * p * G := by
      intro a ha hpa
      exact Nat.mul_div_cancel' (hdiv a ha hpa)
    have h2pG : 0 < 2 * p * G := Nat.mul_pos (Nat.mul_pos (by norm_num) hp.pos) hG0
    have hinjX : Set.InjOn (fun a => 2 * p * G / a) (B.filter (fun a => p ∣ a) : Finset ℕ) := by
      intro a ha a' ha' h
      obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
      obtain ⟨haB', hpa'⟩ := Finset.mem_filter.mp ha'
      have h1 := hcancel a haB hpa
      have h2 := hcancel a' haB' hpa'
      simp only at h
      rw [← h] at h2
      have hq : 0 < 2 * p * G / a := by
        apply Nat.pos_of_ne_zero
        intro hz
        rw [hz, Nat.mul_zero] at h1
        omega
      exact Nat.eq_of_mul_eq_mul_right hq (h1.trans h2.symm)
    have hinjT : Set.InjOn (fun b => b / G) (B.filter (fun b => ¬ p ∣ b) : Finset ℕ) := by
      intro b hb b' hb' h
      obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
      obtain ⟨hbB', hpb'⟩ := Finset.mem_filter.mp hb'
      simp only at h
      rw [← Nat.div_mul_cancel (hGb b hbB hpb), ← Nat.div_mul_cancel (hGb b' hbB' hpb'), h]
    have hk := key (2 * B.card)
      ((B.filter (fun a => p ∣ a)).image (fun a => 2 * p * G / a))
      ((B.filter (fun b => ¬ p ∣ b)).image (fun b => b / G)) (by
        intro x hx t ht
        obtain ⟨a, ha, rfl⟩ := Finset.mem_image.mp hx
        obtain ⟨b, hb, rfl⟩ := Finset.mem_image.mp ht
        obtain ⟨haB, hpa⟩ := Finset.mem_filter.mp ha
        obtain ⟨hbB, hpb⟩ := Finset.mem_filter.mp hb
        exact hprod a haB hpa b hbB hpb)
      ⟨_, Finset.mem_image_of_mem _ (Finset.mem_filter.mpr ⟨ha0, hpa0⟩)⟩
      ⟨_, Finset.mem_image_of_mem _ (Finset.mem_filter.mpr ⟨hb0, hpb0⟩)⟩
    rw [Finset.card_image_of_injOn hinjX, Finset.card_image_of_injOn hinjT] at hk
    refine ⟨hk, ?_⟩
    intro h2p h6 hgcd hv
    have hpI : p ∈ Finset.Ioo 0 B.card := Finset.mem_Ioo.mpr ⟨hp.pos, by omega⟩
    have h2pI : 2 * p ∈ (Finset.Ioo 0 B.card).erase p :=
      Finset.mem_erase.mpr ⟨by have := hp.pos; omega, Finset.mem_Ioo.mpr ⟨by have := hp.pos; omega, h2p⟩⟩
    have hTc : ((B.filter (fun b => ¬ p ∣ b)).image (fun b => b / G)).card =
        (B.filter (fun b => ¬ p ∣ b)).card := Finset.card_image_of_injOn hinjT
    have he1 : ∀ a ∈ B, p ∣ a → 2 * p * G = a := by
      intro a ha hpa
      obtain ⟨e, he⟩ := hdiv a ha hpa
      have ha0' : 0 < a := Nat.pos_of_ne_zero (fun h => h0 (h ▸ ha))
      have hx : 2 * p * G / a = e := Nat.div_eq_of_eq_mul_right ha0' he
      have he0 : e ≠ 0 := by
        rintro rfl
        rw [Nat.mul_zero] at he
        omega
      by_cases h1 : e = 1
      · rw [he, h1, Nat.mul_one]
      exfalso
      by_cases h2e : 2 ∣ e
      · have hsub : (B.filter (fun b => ¬ p ∣ b)).image (fun b => b / G) ⊆
            ((Finset.Ioo 0 B.card).erase p).erase (2 * p) := by
          intro t ht
          obtain ⟨b, hb', rfl⟩ := Finset.mem_image.mp ht
          obtain ⟨hb, hpb⟩ := Finset.mem_filter.mp hb'
          obtain ⟨e', s, m, y, -, hx', ht', hm12, hems, hy0, hyn, hps, hodd⟩ := hfacts a ha hpa b hb hpb
          have hee : e' = e := hx'.symm.trans hx
          subst hee
          simp only [ht']
          obtain ⟨k, rfl⟩ := h2e
          have hk0 : 0 < k := by omega
          have hsy : s ≤ y := by
            rcases hm12 with rfl | rfl
            · have h7 : k * s = y := by linarith
              rw [← h7]
              exact Nat.le_mul_of_pos_left s hk0
            · exact absurd ⟨k * s, by linarith⟩ (hodd rfl)
          have hs0 : s ≠ 0 := by
            rintro rfl
            rw [Nat.mul_zero] at hems
            omega
          rw [Finset.mem_erase, Finset.mem_erase, Finset.mem_Ioo]
          exact ⟨fun h => hps (h ▸ Dvd.intro_left 2 rfl), fun h => hps (h ▸ dvd_rfl),
            Nat.pos_of_ne_zero hs0, by omega⟩
        have hc := Finset.card_le_card hsub
        rw [hTc, Finset.card_erase_of_mem h2pI, Finset.card_erase_of_mem hpI, Nat.card_Ioo] at hc
        omega
      · have hsub : (B.filter (fun b => ¬ p ∣ b)).image (fun b => b / G) ⊆
            Finset.Ioo 0 ((2 * B.card + 2) / 3) := by
          intro t ht
          obtain ⟨b, hb', rfl⟩ := Finset.mem_image.mp ht
          obtain ⟨hb, hpb⟩ := Finset.mem_filter.mp hb'
          obtain ⟨e', s, m, y, -, hx', ht', hm12, hems, hy0, hyn, hps, hodd⟩ := hfacts a ha hpa b hb hpb
          have hee : e' = e := hx'.symm.trans hx
          subst hee
          simp only [ht']
          have h3e : 3 ≤ e' := by omega
          have h8 : 3 * s ≤ e' * s := Nat.mul_le_mul_right s h3e
          have h9 : e' * s ≤ 2 * y := by
            rcases hm12 with rfl | rfl
            · linarith
            · linarith
          have hs0 : s ≠ 0 := by
            rintro rfl
            rw [Nat.mul_zero] at hems
            omega
          rw [Finset.mem_Ioo]
          exact ⟨Nat.pos_of_ne_zero hs0, by omega⟩
        have hc := Finset.card_le_card hsub
        rw [hTc, Nat.card_Ioo] at hc
        omega
    have hG1 : G = 1 := by
      have h7 : G ∣ B.gcd id := by
        apply Finset.dvd_gcd
        intro c hc
        by_cases hpc : p ∣ c
        · exact Dvd.intro_left (2 * p) (he1 c hc hpc)
        · exact hGb c hc hpc
      rw [hgcd] at h7
      exact Nat.dvd_one.mp h7
    intro a ha hpa
    have h8 := he1 a ha hpa
    refine ⟨by rw [hG1, Nat.mul_one] at h8; exact h8.symm, ?_⟩
    intro b hb hpb
    obtain ⟨e', s, m, y, he', -, ht', hm12, hems, hy0, hyn, -, hodd⟩ := hfacts a ha hpa b hb hpb
    have ha0' : 0 < a := Nat.pos_of_ne_zero (fun h => h0 (h ▸ ha))
    have hee : e' = 1 := by
      have h9 : a * e' = a * 1 := by rw [← he', h8, Nat.mul_one]
      exact Nat.eq_of_mul_eq_mul_left ha0' h9
    subst hee
    rw [hG1, Nat.div_one] at ht'
    subst ht'
    rcases hm12 with rfl | rfl
    · have h10 : b = 2 * y := by omega
      exact ⟨fun h => absurd ⟨y, h10⟩ h, fun _ => by omega⟩
    · have h10 : b = y := by omega
      exact ⟨fun _ => by omega, fun _ => by omega⟩
  intro B h0 hne hgcd hnp hnp1 hle hpp
  by_contra hcon
  have hcon1 : ¬ ∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ) :=
    fun h => hcon (Or.inl h)
  have hn : 0 < B.card := hne.card_pos
  have hnq : (0 : ℚ) < B.card := by exact_mod_cast hn
  have hlt : ∀ a ∈ B, ∀ b ∈ B, a < B.card * a.gcd b := by
    intro a ha b hb
    rcases (hle a ha b hb).lt_or_eq with h | h
    · exact h
    · exfalso
      apply hcon1
      refine ⟨a, ha, b, hb, ?_⟩
      rw [le_div_iff₀ hnq]
      have h2 : a.gcd b * B.card ≤ a := by rw [Nat.mul_comm]; exact h.ge
      exact_mod_cast h2
  rcases (hmid B h0 hne hgcd hnp hnp1 hle hpp).1 with h | ⟨p, hp, h3, a, ha, hpa⟩
  · exact hcon1 h
  · by_cases h2 : B.card ≤ 2 * p
    · exact hcon (Or.inr ⟨p, hp, h2, a, ha, hpa⟩)
    · have hexb : ∃ b ∈ B, ¬ p ∣ b := by
        by_contra h
        push Not at h
        have h1 : p ∣ B.gcd id := Finset.dvd_gcd (fun b hb => h b hb)
        rw [hgcd] at h1
        exact hp.one_lt.ne' (Nat.dvd_one.mp h1)
      obtain ⟨hk, hfew⟩ := hblock B h0 hlt p hp h3 ⟨a, ha, hpa⟩ hexb
      have hcardsum : (B.filter (fun a => p ∣ a)).card + (B.filter (fun a => ¬ p ∣ a)).card = B.card := by
        rw [← Finset.card_union_of_disjoint (Finset.disjoint_filter_filter_not B B (fun a => p ∣ a)),
          Finset.filter_union_filter_not_eq]
      have hp2 := hp.two_le
      have h6 : 6 ≤ B.card := by
        by_contra h5
        have h55 : B.card = 5 := by omega
        rw [h55] at hnp
        exact hnp (by norm_num)
      by_cases hu2 : (B.filter (fun a => p ∣ a)).card ≤ 2
      · have hall := hfew (by omega) h6 hgcd (by omega)
        exact hcon1 ((hmid B h0 hne hgcd hnp hnp1 hle hpp).2 p hp (by omega) h3
          ((hall a ha hpa).1 ▸ ha) (fun x hx hpx => (hall x hx hpx).1))
      by_cases hv2 : (B.filter (fun a => ¬ p ∣ a)).card ≤ 2
      · have hd := hdual B B.card hne h0
        obtain ⟨Bs, hBs⟩ : ∃ Bs, Bs = B.image (fun a => B.lcm id / a) := ⟨_, rfl⟩
        rw [← hBs] at hd
        obtain ⟨hcs, hsne, hs0, hsgcd, hspp, hsle, hsback, hsp⟩ := hd
        have hp3 : 3 ≤ p := by
          by_contra hp3
          have h22 : p = 2 := by omega
          subst h22
          exact hnp1 5 (by norm_num) (by omega)
        have hsq : ∀ a ∈ B, ¬ p ^ 2 ∣ a := by
          intro a' ha' hdv
          have h1 := hpp a' ha' p 2 hp hdv
          have h2' : 3 * p ≤ p ^ 2 := by rw [pow_two]; exact Nat.mul_le_mul_right p hp3
          omega
        obtain ⟨hiff, hsu, hsv⟩ := hsp p hp ⟨a, ha, hpa⟩ hsq
        obtain ⟨b, hb, hpb⟩ := hexb
        have hxb : B.lcm id / b ∈ Bs := by rw [hBs]; exact Finset.mem_image_of_mem _ hb
        have hxa : B.lcm id / a ∈ Bs := by rw [hBs]; exact Finset.mem_image_of_mem _ ha
        have hslt : ∀ x ∈ Bs, ∀ y ∈ Bs, x < Bs.card * x.gcd y := by
          intro x hx y hy
          by_contra hge
          push Not at hge
          rw [hcs] at hge
          obtain ⟨a', ha', b', hb', hab⟩ := hsback ⟨x, hx, y, hy, hge⟩
          exact absurd (hlt a' ha' b' hb') (by omega)
        obtain ⟨-, hfew'⟩ := hblock Bs hs0 hslt p hp (by rw [hcs]; exact h3)
          ⟨_, hxb, (hiff b hb).mpr hpb⟩ ⟨_, hxa, fun h => (hiff a ha).mp h hpa⟩
        have hall' := hfew' (by rw [hcs]; omega) (by rw [hcs]; exact h6) hsgcd
          (by rw [hcs, hsv]; omega)
        have h2pBs : 2 * p ∈ Bs := (hall' _ hxb ((hiff b hb).mpr hpb)).1 ▸ hxb
        obtain ⟨x, hx, y, hy, hxy⟩ := (hmid Bs hs0 hsne hsgcd (by rw [hcs]; exact hnp)
          (by rw [hcs]; exact hnp1) (by rw [hcs]; exact hsle hle)
          (by
            intro x hx q k hq hqk
            rw [hcs]
            obtain ⟨a', ha', hdv⟩ := hspp x hx q k hq hqk
            exact hpp a' ha' q k hq hdv)).2 p hp (by rw [hcs]; omega) (by rw [hcs]; exact h3)
          h2pBs (fun x hx hpx => (hall' x hx hpx).1)
        rw [hcs, le_div_iff₀ hnq] at hxy
        have hxy' : x.gcd y * B.card ≤ x := by exact_mod_cast hxy
        obtain ⟨a', ha', b', hb', hab⟩ := hsback ⟨x, hx, y, hy, by rw [Nat.mul_comm]; exact hxy'⟩
        exact absurd (hlt a' ha' b' hb') (by omega)
      · generalize (B.filter (fun a => p ∣ a)).card = u at hu2 hk hcardsum
        generalize (B.filter (fun a => ¬ p ∣ a)).card = v at hv2 hk hcardsum
        have hu5 : u ≤ 5 := by
          by_contra hge
          nlinarith
        have hv5 : v ≤ 5 := by
          by_contra hge
          nlinarith
        have h678 : B.card = 6 ∨ B.card = 7 ∨ B.card = 8 := by
          interval_cases u <;> interval_cases v <;> omega
        rcases h678 with h | h | h
        · exact hnp1 5 (by norm_num) h
        · rw [h] at hnp
          exact hnp (by norm_num)
        · exact hnp1 7 (by norm_num) h
