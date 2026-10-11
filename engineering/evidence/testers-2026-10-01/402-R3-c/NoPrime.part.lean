
/-- General range: if the kernel statement `hK` (for this `N = B.card`, `p`, `M`) holds, then no
element of a strict set `B` with gcd 1 is divisible by the prime `p`, `B.card ≤ (k + 1) * p`.
`M` is any positive common multiple of `1..k`.  No duality and no valuation hypothesis is needed:
the kernel statement is symmetric in `X` and `S`. -/
theorem R3c.no_prime_of_kernel (B : Finset ℕ) (h0 : 0 ∉ B) (hgcd : B.gcd id = 1)
    (hlt : ∀ a ∈ B, ∀ b ∈ B, a < B.card * a.gcd b)
    (p k M : ℕ) (hp : p.Prime) (hM0 : 0 < M) (hM : ∀ m : ℕ, 0 < m → m ≤ k → m ∣ M)
    (hk : B.card ≤ (k + 1) * p)
    (hK : ∀ X S : Finset ℕ, X.Nonempty → S.Nonempty →
      (∀ x ∈ X, 0 < x) → (∀ s ∈ S, 0 < s) → (∀ s ∈ S, ¬ p ∣ s) →
      (∀ x ∈ X, ∀ x' ∈ X, x < B.card * Nat.gcd x x') →
      (∀ s ∈ S, ∀ t ∈ S, s < B.card * Nat.gcd s t) →
      (∀ x ∈ X, ∀ s ∈ S, ∃ m y : ℕ, 0 < m ∧ m ≤ k ∧ y < B.card ∧ ¬ p ∣ y ∧ Nat.Coprime m y ∧
        x * s * m = M * y) →
      X.card + S.card < B.card) :
    ∀ a ∈ B, ¬ p ∣ a := by
  intro a0 ha0 hpa0
  have hV : ∃ b ∈ B, ¬ p ∣ b := by
    by_contra h
    push Not at h
    have h1 : p ∣ B.gcd id := Finset.dvd_gcd (fun b hb => h b hb)
    rw [hgcd] at h1
    exact hp.one_lt.ne' (Nat.dvd_one.mp h1)
  have hmk : ∀ m : ℕ, m * p < B.card → m ≤ k := by
    intro m hmp
    by_contra hcon
    push Not at hcon
    have : (k + 1) * p ≤ m * p := Nat.mul_le_mul_right p hcon
    omega
  obtain ⟨X, S, hXc, hSc, hX0, hS0, hSp, -, hXX, hSS, hXS⟩ :=
    R3c.block_kernel B B.card p M h0 hp hM0 (fun m hm0 hmp => hM m hm0 (hmk m hmp)) hlt
      ⟨a0, ha0, hpa0⟩ hV
  have hsum : (B.filter (fun a => p ∣ a)).card + (B.filter (fun b => ¬ p ∣ b)).card = B.card := by
    rw [← Finset.card_union_of_disjoint (Finset.disjoint_filter_filter_not B B (fun a => p ∣ a)),
      Finset.filter_union_filter_not_eq]
  have hXne : X.Nonempty := by
    rw [← Finset.card_pos, hXc, Finset.card_pos]
    exact ⟨a0, Finset.mem_filter.mpr ⟨ha0, hpa0⟩⟩
  have hSne : S.Nonempty := by
    obtain ⟨b, hb, hpb⟩ := hV
    rw [← Finset.card_pos, hSc, Finset.card_pos]
    exact ⟨b, Finset.mem_filter.mpr ⟨hb, hpb⟩⟩
  have := hK X S hXne hSne hX0 hS0 hSp hXX hSS (by
    intro x hx s hs
    obtain ⟨m, y, hm0, hmp, hy, hpy, hc, e⟩ := hXS x hx s hs
    exact ⟨m, y, hm0, hmk m hmp, hy, hpy, hc, e⟩)
  omega

/-- The range `3p < n ≤ 4p` (`k = 3`, `M = 6`), given the kernel statement K3. -/
theorem R3c.no_quarter_prime (B : Finset ℕ) (h0 : 0 ∉ B) (hgcd : B.gcd id = 1)
    (hlt : ∀ a ∈ B, ∀ b ∈ B, a < B.card * a.gcd b)
    (p : ℕ) (hp : p.Prime) (h3p : 3 * p < B.card) (hn4 : B.card ≤ 4 * p)
    (hK3 : ∀ (n p : ℕ) (X S : Finset ℕ), p.Prime → 3 * p < n → n ≤ 4 * p → X.Nonempty → S.Nonempty →
      (∀ x ∈ X, 0 < x) → (∀ s ∈ S, 0 < s) → (∀ s ∈ S, ¬ p ∣ s) →
      (∀ x ∈ X, ∀ x' ∈ X, x < n * Nat.gcd x x') →
      (∀ s ∈ S, ∀ t ∈ S, s < n * Nat.gcd s t) →
      (∀ x ∈ X, ∀ s ∈ S, ∃ m y : ℕ, 0 < m ∧ m ≤ 3 ∧ y < n ∧ ¬ p ∣ y ∧ Nat.Coprime m y ∧
        x * s * m = 6 * y) →
      X.card + S.card < n) :
    ∀ a ∈ B, ¬ p ∣ a := by
  refine R3c.no_prime_of_kernel B h0 hgcd hlt p 3 6 hp (by norm_num) ?_ hn4
    (fun X S => hK3 B.card p X S hp h3p hn4)
  intro m hm0 hm3
  interval_cases m <;> norm_num
