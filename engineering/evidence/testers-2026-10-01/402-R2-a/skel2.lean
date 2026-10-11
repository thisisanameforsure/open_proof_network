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
  -- Hole `hmid`: B has a pair with gcd(a, b) ≤ a / n, or some prime p ≥ n / 3 divides an element and
  -- either p ≥ n / 2, or at least three elements are not multiples of p and the multiples of p are
  -- not "2p alone" (2p ∉ B, or at least two multiples).
  -- The assembly proves, for a strict counterexample and a prime n / 3 ≤ p < n / 2 dividing an element:
  -- (u - 2)(v - 2) < 4 for the numbers u, v of multiples and non-multiples of p ("few or almost all"),
  -- and if u ≤ 2 then 2p is the only multiple of p in B. What is left open is exactly the
  -- configuration B = {2p} ∪ T and the case of at most two non-multiples (the dual one).
  have hmid : ∀ B : Finset ℕ, 0 ∉ B → B.Nonempty → B.gcd id = 1 → ¬ B.card.Prime →
      (∀ q : ℕ, q.Prime → B.card ≠ q + 1) →
      (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
      (∀ a ∈ B, ∀ p k : ℕ, p.Prime → p ^ k ∣ a → p ^ k < B.card) →
      (∃ a ∈ B, ∃ b ∈ B, (a.gcd b : ℚ) ≤ (a : ℚ) / (B.card : ℚ)) ∨
        ∃ p : ℕ, p.Prime ∧ B.card ≤ 3 * p ∧ (∃ a ∈ B, p ∣ a) ∧
          (B.card ≤ 2 * p ∨ (3 ≤ (B.filter (fun a => ¬ p ∣ a)).card ∧
            (2 * p ∉ B ∨ 2 ≤ (B.filter (fun a => p ∣ a)).card))) := sorry
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
        B.card ≤ (B.filter (fun a => ¬ p ∣ a)).card + 2 → ∀ a ∈ B, p ∣ a → a = 2 * p) := by
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
    rw [hG1, Nat.mul_one] at h8
    exact h8.symm
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
  rcases hmid B h0 hne hgcd hnp hnp1 hle hpp with h | ⟨p, hp, h3, ⟨a, ha, hpa⟩, hX⟩
  · exact hcon1 h
  · by_cases h2 : B.card ≤ 2 * p
    · exact hcon (Or.inr ⟨p, hp, h2, a, ha, hpa⟩)
    · rcases hX with hX | ⟨hv, hX⟩
      · exact h2 hX
      · have hexb : ∃ b ∈ B, ¬ p ∣ b := by
          obtain ⟨b, hb⟩ := Finset.card_pos.mp (by omega : 0 < (B.filter (fun a => ¬ p ∣ a)).card)
          exact ⟨b, (Finset.mem_filter.mp hb).1, (Finset.mem_filter.mp hb).2⟩
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
          have hu1 : (B.filter (fun a => p ∣ a)).card ≤ 1 := by
            apply Finset.card_le_one.mpr
            intro x hx y hy
            obtain ⟨hxB, hpx⟩ := Finset.mem_filter.mp hx
            obtain ⟨hyB, hpy⟩ := Finset.mem_filter.mp hy
            rw [hall x hxB hpx, hall y hyB hpy]
          rcases hX with hX | hX
          · exact hX (hall a ha hpa ▸ ha)
          · omega
        · generalize (B.filter (fun a => p ∣ a)).card = u at hu2 hk hcardsum
          generalize (B.filter (fun a => ¬ p ∣ a)).card = v at hv hk hcardsum
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
