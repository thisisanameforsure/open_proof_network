
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
