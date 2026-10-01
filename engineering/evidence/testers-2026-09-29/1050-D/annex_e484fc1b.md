# hrem (erdos-1050--h1-v2--h4) reduced to one identity: the Padé remainder as a series of positive terms

Contributor: t0929-2. Status: **the reduction is Lean that elaborates on the network's fast check (POST /check, lean-4.33.1, okay true, only lint sorry-present, log 01M3Q9KYY0J2PH05GMB59TRWY3); it has not been through the gate.** The remaining identity is checked numerically only. Companion to annexes f593a93a8960 and 3ada4f0922d7 on erdos-1050--h1-v2, and to the proved node spec-f2b55478.

Notation as in the statement: T = Σ_{m≥0} 1/(2^{m+3} − 3), x_n = 3/2^n, R_n = Qx n · 3T − Aq n. The goal is 0 < R_n and R_n² · 2^{4n²} ≤ 2^{2n+4}.

## What is proved in the skeleton below (fast check only)

1. 0 < T ≤ 2/5, from 1/(2^{m+3} − 3) ≤ (1/5)(1/2)^m.
2. n = 0: Qx 0 = 1 and Aq 0 = 0 (the only Aq term divides by 2^0 − 1 = 0), so R_0 = 3T ∈ (0, 6/5].
3. n = 1: Qx 1 = 3/2 and Aq 1 = 0, so R_1 = 9T/2 ≤ 9/5 < 2. This is the tightest case of the whole statement (0.74 bits of slack in the squared inequality; it needs T ≤ 4/9).
4. For n ≥ 2 put E(n,t) = 2^{n²} Π_{i<n}(2^{n+t−i} − 1) / Π_{j≤n}(2^{2n+1+t−j} − 1). Then E(n,t) > 0, and E(n,t) ≤ 2^{−(2n+t)}: pair the numerator's factor i with the denominator's factor j = i+1, using 2^n(2^{n+t−i} − 1) ≤ 2^{2n+t−i} − 1, and bound the leftover factor 2^{2n+1+t} − 1 below by 2^{2n+t}.
5. Given the identity below, R_n > 0 (a sum of positive terms), and each term is at most 2^{n+1}/2^{2n²} · (1/2)^t, because 3·9^n ≤ 2·16^n (n ≥ 2) and 3^t ≤ 2^{nt}; summing, R_n ≤ 2^{n+2}/2^{2n²}, which is the bound.

## The one hole (hser)

For n ≥ 2: HasSum (t ↦ E(n,t) · x_n^{2n+1+t}) R_n. Route: (i) 3T − c_n = Σ_{j>n} 3/(2^j − 3) = Σ_{j≥1} x_n/(2^j − x_n) = Σ_{k≥1} x_n^k/(2^k − 1), a tail split plus a geometric double series (x_n ≤ 3/4); (ii) multiplying by the polynomial Q_n, the coefficient of x^k for k ≤ n is exactly the inner sum in Aq (Lean's division by zero makes its j = k term vanish, as it should), so R_n = Σ_{m>n} e_{n,m} x_n^m; (iii) spec-f2b55478 (proved) gives e_{n,m} in closed form: 0 for n < m ≤ 2n, and for m = 2n+1+t, after cancelling Π(2^{i+1} − 1) against the Gaussian binomial's denominators, E(n,t). Checked numerically (exact rationals, 400 terms) for n = 2..8. A hole of a node cannot declare spec-f2b55478 as a dependency, so a proof of hser has to restate that identity as a `have`.

## Numerics (exact rationals, T to 9000 bits)

Both conjuncts hold for n = 0..30. Slack (bits) in R² · 2^{4n²} ≤ 2^{2n+4}: 3.91 (n=0), 0.74 (n=1), 6.30 (n=2), 9.65 (3), 12.17 (4), then about 1.66n + 6 (56.2 at n = 30); log2 R_30 = −1796.1.

## Note on the statement

The node's statement carries sibling h3 (hden) as a hypothesis although the parent's assembly cleared it, so its witness is a proof of h3; a revision request without that hypothesis is graph PR #229. The skeleton clears it at once and never uses it.

## The skeleton's body (after `:= by`, under the node's own header)

```lean
  intro Qc hQc Qx hQx Aq hAq hden
  -- the remainder bound does not use the denominator bound: cleared before any hole is stated
  clear hden
  obtain ⟨T, hT⟩ : ∃ T : ℝ, T = ∑' (n : ℕ), (1 : ℝ) / ((2 : ℝ) ^ (n + (3 : ℕ)) - (3 : ℝ)) := ⟨_, rfl⟩
  rw [← hT]
  -- the terms of T are bounded by (1/5) (1/2)^m
  have hterm : ∀ m : ℕ, 0 ≤ (1 : ℝ) / ((2 : ℝ) ^ (m + 3) - 3) ∧
      (1 : ℝ) / ((2 : ℝ) ^ (m + 3) - 3) ≤ (1 / 5 : ℝ) * (1 / 2 : ℝ) ^ m := by
    intro m
    have h2 : (1 : ℝ) ≤ (2 : ℝ) ^ m := one_le_pow₀ (by norm_num)
    have hpos : (0 : ℝ) < (2 : ℝ) ^ (m + 3) - 3 := by rw [pow_add]; nlinarith
    refine ⟨div_nonneg zero_le_one hpos.le, ?_⟩
    rw [div_le_iff₀ hpos]
    have hh : (1 / 2 : ℝ) ^ m * (2 : ℝ) ^ m = 1 := by rw [← mul_pow]; norm_num
    have hle : (1 / 2 : ℝ) ^ m ≤ 1 := pow_le_one₀ (by norm_num) (by norm_num)
    rw [pow_add]
    nlinarith
  have hgeo : Summable (fun m : ℕ => (1 / 5 : ℝ) * (1 / 2 : ℝ) ^ m) :=
    (summable_geometric_of_lt_one (by norm_num) (by norm_num)).mul_left _
  have hsumm : Summable (fun m : ℕ => (1 : ℝ) / ((2 : ℝ) ^ (m + (3 : ℕ)) - (3 : ℝ))) :=
    Summable.of_nonneg_of_le (fun m => (hterm m).1) (fun m => (hterm m).2) hgeo
  have hTpos : 0 < T := by
    rw [hT]
    exact hsumm.tsum_pos (fun m => (hterm m).1) 0 (by norm_num)
  have hTle : T ≤ 2 / 5 := by
    rw [hT]
    calc ∑' (n : ℕ), (1 : ℝ) / ((2 : ℝ) ^ (n + (3 : ℕ)) - (3 : ℝ))
        ≤ ∑' m : ℕ, (1 / 5 : ℝ) * (1 / 2 : ℝ) ^ m :=
          Summable.tsum_le_tsum (fun m => (hterm m).2) hsumm hgeo
      _ = 2 / 5 := by rw [tsum_mul_left, tsum_geometric_of_lt_one (by norm_num) (by norm_num)]; norm_num
  -- the Padé remainder coefficients, in closed form (spec-f2b55478), shifted to start at x^(2n+1)
  obtain ⟨E, hE⟩ : ∃ E : ℕ → ℕ → ℝ, E = fun n t =>
      (2 : ℝ) ^ (n * n) * (∏ i ∈ Finset.range n, ((2 : ℝ) ^ (n + t - i) - 1)) /
        ∏ j ∈ Finset.range (n + 1), ((2 : ℝ) ^ (2 * n + 1 + t - j) - 1) := ⟨_, rfl⟩
  have hEpos : ∀ n t : ℕ, 0 < E n t := by
    intro n t
    rw [hE]
    apply div_pos
    · apply mul_pos (by positivity)
      apply Finset.prod_pos
      intro i hi
      simp only [Finset.mem_range] at hi
      have : (1 : ℝ) < 2 ^ (n + t - i) := one_lt_pow₀ (by norm_num) (by omega)
      linarith
    · apply Finset.prod_pos
      intro j hj
      simp only [Finset.mem_range] at hj
      have : (1 : ℝ) < 2 ^ (2 * n + 1 + t - j) := one_lt_pow₀ (by norm_num) (by omega)
      linarith
  have hEle : ∀ n t : ℕ, E n t ≤ (1 / 2 : ℝ) ^ (2 * n + t) := by
    intro n t
    rw [hE]
    dsimp only
    rw [Finset.prod_range_succ']
    have hA : (0 : ℝ) < ∏ i ∈ Finset.range n, ((2 : ℝ) ^ (2 * n + 1 + t - (i + 1)) - 1) := by
      apply Finset.prod_pos
      intro i hi
      simp only [Finset.mem_range] at hi
      have : (1 : ℝ) < 2 ^ (2 * n + 1 + t - (i + 1)) := one_lt_pow₀ (by norm_num) (by omega)
      linarith
    have hnum : (2 : ℝ) ^ (n * n) * ∏ i ∈ Finset.range n, ((2 : ℝ) ^ (n + t - i) - 1) ≤
        ∏ i ∈ Finset.range n, ((2 : ℝ) ^ (2 * n + 1 + t - (i + 1)) - 1) := by
      have hc : (2 : ℝ) ^ (n * n) * ∏ i ∈ Finset.range n, ((2 : ℝ) ^ (n + t - i) - 1) =
          ∏ i ∈ Finset.range n, ((2 : ℝ) ^ n * ((2 : ℝ) ^ (n + t - i) - 1)) := by
        rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range, ← pow_mul]
      rw [hc]
      apply Finset.prod_le_prod
      · intro i hi
        simp only [Finset.mem_range] at hi
        have : (1 : ℝ) ≤ 2 ^ (n + t - i) := one_le_pow₀ (by norm_num)
        have : (0 : ℝ) < 2 ^ n := by positivity
        nlinarith
      · intro i hi
        simp only [Finset.mem_range] at hi
        have he : 2 * n + 1 + t - (i + 1) = n + (n + t - i) := by omega
        rw [he, pow_add]
        have : (1 : ℝ) ≤ 2 ^ n := one_le_pow₀ (by norm_num)
        nlinarith
    have hf0 : (2 : ℝ) ^ (2 * n + t) ≤ (2 : ℝ) ^ (2 * n + 1 + t - 0) - 1 := by
      have he : 2 * n + 1 + t - 0 = (2 * n + t) + 1 := by omega
      rw [he, pow_succ]
      have : (1 : ℝ) ≤ 2 ^ (2 * n + t) := one_le_pow₀ (by norm_num)
      linarith
    have hp : (0 : ℝ) < 2 ^ (2 * n + t) := by positivity
    rw [div_le_iff₀ (mul_pos hA (by linarith)), one_div_pow]
    have hkey : (1 : ℝ) ≤ 1 / 2 ^ (2 * n + t) * ((2 : ℝ) ^ (2 * n + 1 + t - 0) - 1) := by
      rw [div_mul_eq_mul_div, one_mul, le_div_iff₀ hp]; linarith
    nlinarith
  -- the one hole: the Padé remainder as a series of positive terms
  have hser : ∀ n : ℕ, 2 ≤ n →
      HasSum (fun t : ℕ => E n t * ((3 : ℝ) / (2 : ℝ) ^ n) ^ (2 * n + 1 + t))
        ((Qx n : ℝ) * (3 * T) - (Aq n : ℝ)) := by
    sorry
  intro n
  rcases (show n = 0 ∨ n = 1 ∨ 2 ≤ n by omega) with rfl | rfl | hn
  · have hq : Qx 0 = 1 := by rw [hQx, hQc]; simp
    have ha : Aq 0 = 0 := by rw [hAq, hQx, hQc]; simp
    rw [hq, ha]
    push_cast
    constructor <;> nlinarith
  · have hq : Qx 1 = 3 / 2 := by
      rw [hQx, hQc]; simp [Finset.sum_range_succ, Finset.prod_range_succ]; norm_num
    have ha : Aq 1 = 0 := by
      rw [hAq, hQx, hQc]; simp [Finset.sum_range_succ, Finset.prod_range_succ]; norm_num
    rw [hq, ha]
    push_cast
    constructor <;> nlinarith
  · have hs := hser n hn
    have hy4 : (4 : ℝ) ≤ (2 : ℝ) ^ n := by
      calc (4 : ℝ) = 2 ^ 2 := by norm_num
        _ ≤ 2 ^ n := pow_le_pow_right₀ (by norm_num) hn
    have hw : 3 * ((3 : ℝ) ^ n) ^ 2 ≤ 2 * ((2 : ℝ) ^ n) ^ 4 := by
      obtain ⟨k, hk⟩ : ∃ k, n = k + 2 := ⟨n - 2, by omega⟩
      have h916 : (9 : ℝ) ^ k ≤ 16 ^ k := pow_le_pow_left₀ (by norm_num) (by norm_num) k
      have e1 : ((3 : ℝ) ^ n) ^ 2 = 81 * 9 ^ k := by
        have h9 : (9 : ℝ) ^ k = ((3 : ℝ) ^ k) ^ 2 := by rw [← pow_mul, mul_comm, pow_mul]; norm_num
        rw [hk, h9]; ring
      have e2 : ((2 : ℝ) ^ n) ^ 4 = 256 * 16 ^ k := by
        have h16 : (16 : ℝ) ^ k = ((2 : ℝ) ^ k) ^ 4 := by rw [← pow_mul, mul_comm, pow_mul]; norm_num
        rw [hk, h16]; ring
      rw [e1, e2]; nlinarith
    have hbound : ∀ t : ℕ, E n t * ((3 : ℝ) / (2 : ℝ) ^ n) ^ (2 * n + 1 + t) ≤
        (2 : ℝ) ^ (n + 1) / ((2 : ℝ) ^ n) ^ (2 * n) * (1 / 2 : ℝ) ^ t := by
      intro t
      have hu : (3 : ℝ) ^ t ≤ ((2 : ℝ) ^ n) ^ t := pow_le_pow_left₀ (by norm_num) (by linarith) t
      have hyp : (0 : ℝ) < (2 : ℝ) ^ n := by positivity
      calc E n t * ((3 : ℝ) / (2 : ℝ) ^ n) ^ (2 * n + 1 + t)
          ≤ (1 / 2 : ℝ) ^ (2 * n + t) * ((3 : ℝ) / (2 : ℝ) ^ n) ^ (2 * n + 1 + t) :=
            mul_le_mul_of_nonneg_right (hEle n t) (by positivity)
        _ = 3 * ((3 : ℝ) ^ n) ^ 2 * 3 ^ t /
              (((2 : ℝ) ^ n) ^ 2 * 2 ^ t * (((2 : ℝ) ^ n) ^ (2 * n) * (2 : ℝ) ^ n * ((2 : ℝ) ^ n) ^ t)) := by
            rw [one_div_pow, div_pow]
            field_simp
            try ring
        _ ≤ 2 * ((2 : ℝ) ^ n) ^ 4 * ((2 : ℝ) ^ n) ^ t /
              (((2 : ℝ) ^ n) ^ 2 * 2 ^ t * (((2 : ℝ) ^ n) ^ (2 * n) * (2 : ℝ) ^ n * ((2 : ℝ) ^ n) ^ t)) := by
            gcongr
        _ = (2 : ℝ) ^ (n + 1) / ((2 : ℝ) ^ n) ^ (2 * n) * (1 / 2 : ℝ) ^ t := by
            rw [one_div_pow]
            field_simp
            try ring
    have hgeomS : HasSum (fun t : ℕ => (2 : ℝ) ^ (n + 1) / ((2 : ℝ) ^ n) ^ (2 * n) * (1 / 2 : ℝ) ^ t)
        ((2 : ℝ) ^ (n + 1) / ((2 : ℝ) ^ n) ^ (2 * n) * (1 - 1 / 2)⁻¹) :=
      (hasSum_geometric_of_lt_one (by norm_num) (by norm_num)).mul_left _
    have hRle := hasSum_le hbound hs hgeomS
    have hterm_pos : ∀ t : ℕ, 0 < E n t * ((3 : ℝ) / (2 : ℝ) ^ n) ^ (2 * n + 1 + t) :=
      fun t => mul_pos (hEpos n t) (by positivity)
    have hRpos : 0 < (Qx n : ℝ) * (3 * T) - (Aq n : ℝ) := by
      rw [← hs.tsum_eq]
      exact hs.summable.tsum_pos (fun t => (hterm_pos t).le) 0 (hterm_pos 0)
    refine ⟨hRpos, ?_⟩
    have hB : (2 : ℝ) ^ (n + 1) / ((2 : ℝ) ^ n) ^ (2 * n) * (1 - 1 / 2)⁻¹ =
        (2 : ℝ) ^ (n + 2) / ((2 : ℝ) ^ n) ^ (2 * n) := by
      field_simp; ring
    rw [hB] at hRle
    have hpow : (2 : ℝ) ^ (4 * n * n) = (((2 : ℝ) ^ n) ^ (2 * n)) ^ 2 := by
      rw [← pow_mul, ← pow_mul]; ring_nf
    have hQ : (0 : ℝ) < ((2 : ℝ) ^ n) ^ (2 * n) := by positivity
    rw [hpow]
    calc ((Qx n : ℝ) * (3 * T) - (Aq n : ℝ)) ^ 2 * (((2 : ℝ) ^ n) ^ (2 * n)) ^ 2
        = (((Qx n : ℝ) * (3 * T) - (Aq n : ℝ)) * ((2 : ℝ) ^ n) ^ (2 * n)) ^ 2 := by ring
      _ ≤ ((2 : ℝ) ^ (n + 2)) ^ 2 := by
          gcongr
          rw [le_div_iff₀ hQ] at hRle; exact hRle
      _ = (2 : ℝ) ^ (2 * n + 4) := by ring
```
