Erdős 402 (Graham's gcd conjecture), strict counterexamples: no prime p with n/3 ≤ p < n/2 divides an element. Checked in Lean (fast check only, not prechecked); extends annex 6a64518f9cd863c9abea3114b518f3172f4c73c6a187eb928b43db35f77c0002 (primes p ≥ n/2) by one range.

Setting. B is a finite set of positive integers, n = |B| ≥ 9, gcd(B) = 1, and B is strict: a < n·gcd(a, b) for all a, b in B (every quotient a/gcd(a, b) is at most n − 1). p is a prime with 2p < n ≤ 3p (so p ≥ 3). Claim: no element of B is a multiple of p.

Step 1 (pairs). Let a be a multiple of p in B, b a non-multiple, g = gcd(a, b), a = g·x, b = g·y. Then p divides x and x < n ≤ 3p, so x = p or x = 2p; y < n, p does not divide y, and y is odd when x = 2p (x and y are coprime).

Step 2 (two blocks). Let G be the gcd of the non-multiples of p. By step 1 every multiple a divides 2p·b for every non-multiple b, so a divides 2pG. Put e(a) = 2pG/a and s(b) = b/G. These are injective, and e(a)·s(b) = 2y when x = p, and = y (odd) when x = 2p. So with X = {e(a)}, S = {s(b)}, |X| + |S| = n, every product x·s is either 2y or an odd y, with 0 < y < n and p not dividing y.

Step 3 (kernel K2). For such X, S (n ≥ 9, 2p < n) either X = {1} or S = {1}. Proof: max X ≥ |X| and max S ≥ |S|, so |X|·|S| < 2n = 2(|X| + |S|), and the smaller of the two has at most 2 members; say |X| ≤ 2, |S| ≥ n − 2. If some x in X is 2, every s is a value y in [1, n − 1] other than p, 2p: only n − 3 values. If some x ≥ 3, every s ≤ 2(n − 1)/3: fewer than n − 2 values. So X = {1}. The hypothesis is symmetric in X and S.

Step 4 (X = {1}: the configuration {2p} ∪ T). Then every multiple of p equals 2pG, G divides every element, so G = 1: B = {2p} ∪ T with |T| = n − 1, no element of T a multiple of p. Strictness against 2p gives: odd t in T are < n, even b in T are < 2n. Lemma I: such a T has at most n − 2 elements, a contradiction.
Proof of Lemma I (a matching). For odd t < n let φ(t) = t·2^j be the unique such number in [n/2, n − 1]; φ is injective on odd numbers. Define g on T by: even b ↦ b/2; t = 2p + 1 ↦ 2p − 1; odd t with 2(φ(t) − 1) < n ↦ 0; any other odd t ↦ φ(t) − 1. The values lie in {0} ∪ ([1, n − 1] minus {p, 2p}), a set of n − 2 numbers: b/2 is not p or 2p since p does not divide b; φ(t) − 1 ≥ n/2 > p; φ(t) − 1 = 2p would force t = 2p + 1. And g is injective on T: w = φ(t) − 1 is coprime to t (t divides w + 1) and t is odd, so if the even number 2w were in T the pair (2w, t) would have quotient 2w ≥ n; likewise 2p − 1 is coprime to 2p + 1 and 2(2p − 1) ≥ n; φ(t) = 2p is impossible for t in T (p would divide t·2^j); at most one value of φ gives 0. Hence |T| ≤ n − 2.
(Checked numerically before formalising: maximum independent set of the incompatibility graph, every n in 5..259 and every integer p with 2p < n ≤ 3p, never exceeds n − 2.)

Step 5 (S = {1}: the dual side). Then exactly one element g of B is not a multiple of p, and every element divides 2pg, so L = lcm(B) divides 2pg. The dual set B* = {L/a} is again strict, of size n, with gcd 1 (annex abe3e5f7aae6540a75a47ba0421ff62ac6c95f4bce427ba0df7a06c398575b87), and L/g is a multiple of p in it. Steps 1–4 for B* give: exactly one element of B* is not a multiple of p. Since n − 1 ≥ 2, some a ≠ g in B has p dividing both a and L/a, so p² divides L, which divides 2pg: p divides 2g, impossible.

Consequence for the hole chain. Under the hypotheses of erdos-402--h3-v2--h1 (n not prime, not prime + 1, which give p ≥ 3 and n ≥ 9 in this range) the alternative "an element has a prime factor p with n ≤ 2p" of its hole can be weakened to "n ≤ 3p".

What this does not do. Primes below n/3 (k ≥ 3 in the notation n ≤ (k + 1)p): the block step then allows x in {p, 2p, ..., kp} and the kernel only gives min(u, v) < 2·lcm(1..k); no matching lemma is known to the author for those configurations.

Lean (lean-4.33.1 with the pinned Mathlib; POST /check mode check: okay true, no lint). R1b.* are copied from annex abe3e5f7…5b87. The gate refuses helper declarations, so a proof must inline these as `have` steps; inlined into one declaration they still elaborate inside the default heartbeat limit.

```lean
import Mathlib

/-- Lemma I (the configuration B = {2p} ∪ T is impossible): a set T of positive integers, none a
multiple of p, odd members < n, even members < 2n, every (even b, odd t) pair with b < n·gcd(b,t),
has at most n − 2 members.  (2p < n ≤ 3p, p an odd prime.) -/
theorem R2b.lemI (n p : ℕ) (T : Finset ℕ) (hp : p.Prime) (hp3 : 3 ≤ p) (h2p : 2 * p < n)
    (hn3 : n ≤ 3 * p)
    (h0 : ∀ b ∈ T, 0 < b) (hpT : ∀ b ∈ T, ¬ p ∣ b)
    (ho : ∀ b ∈ T, ¬ 2 ∣ b → b < n) (he : ∀ b ∈ T, 2 ∣ b → b < 2 * n)
    (hx : ∀ b ∈ T, ∀ t ∈ T, 2 ∣ b → ¬ 2 ∣ t → b < n * b.gcd t) :
    T.card + 2 ≤ n := by
  -- φ t = the unique t·2^j in [n/2, n-1]
  have hφ : ∀ b : ℕ, 0 < b → b < n →
      b * 2 ^ Nat.log 2 ((n - 1) / b) ≤ n - 1 ∧ n - 1 < 2 * (b * 2 ^ Nat.log 2 ((n - 1) / b)) := by
    intro b hb hbn
    have hne : (n - 1) / b ≠ 0 := by
      have : 0 < (n - 1) / b := Nat.div_pos (by omega) hb
      omega
    have h1 := Nat.pow_log_le_self 2 hne
    have h2 := Nat.lt_pow_succ_log_self (by norm_num : 1 < 2) ((n - 1) / b)
    have h3 : b * ((n - 1) / b) ≤ n - 1 := Nat.mul_div_le _ _
    have h4 : b * 2 ^ Nat.log 2 ((n - 1) / b) ≤ b * ((n - 1) / b) := Nat.mul_le_mul_left b h1
    have h5 : n - 1 < 2 ^ (Nat.log 2 ((n - 1) / b)).succ * b := (Nat.div_lt_iff_lt_mul hb).mp h2
    refine ⟨h4.trans h3, ?_⟩
    calc n - 1 < 2 ^ (Nat.log 2 ((n - 1) / b)).succ * b := h5
      _ = 2 * (b * 2 ^ Nat.log 2 ((n - 1) / b)) := by rw [pow_succ]; ring
  have hinj0 : ∀ b b' j j' : ℕ, ¬ 2 ∣ b → j ≤ j' → b * 2 ^ j = b' * 2 ^ j' → b = b' := by
    intro b b' j j' hb hjj h
    obtain ⟨d, rfl⟩ := Nat.exists_eq_add_of_le hjj
    have h1 : b * 2 ^ j = (b' * 2 ^ d) * 2 ^ j := by rw [h, pow_add]; ring
    have h2 : b = b' * 2 ^ d := Nat.eq_of_mul_eq_mul_right (by positivity) h1
    rcases Nat.eq_zero_or_pos d with hd | hd
    · rw [hd] at h2; simpa using h2
    · exfalso; apply hb; rw [h2]
      exact Dvd.dvd.mul_left (dvd_pow_self 2 (by omega)) _
  have hinj : ∀ b b' j j' : ℕ, ¬ 2 ∣ b → ¬ 2 ∣ b' → b * 2 ^ j = b' * 2 ^ j' → b = b' := by
    intro b b' j j' hb hb' h
    rcases le_total j j' with hjj | hjj
    · exact hinj0 b b' j j' hb hjj h
    · exact (hinj0 b' b j' j hb' hjj h.symm).symm
  -- coprimality of t with (t·m − 1)
  have hcop : ∀ t m w : ℕ, w + 1 = t * m → Nat.Coprime w t := by
    intro t m w h
    have h1 : Nat.Coprime w (w + 1) := by simp
    rw [h] at h1
    exact Nat.Coprime.coprime_mul_right_right h1
  set φ : ℕ → ℕ := fun b => b * 2 ^ Nat.log 2 ((n - 1) / b) with hφdef
  set g : ℕ → ℕ := fun b =>
    if 2 ∣ b then b / 2 else if b = 2 * p + 1 then 2 * p - 1
    else if 2 * (φ b - 1) < n then 0 else φ b - 1 with hgdef
  have hmaps : ∀ b ∈ T, g b ∈ insert 0 (((Finset.Ioo 0 n).erase p).erase (2 * p)) := by
    intro b hb
    have hb0 := h0 b hb
    have hpb := hpT b hb
    rw [Finset.mem_insert, Finset.mem_erase, Finset.mem_erase, Finset.mem_Ioo]
    simp only [hgdef]
    by_cases h2 : 2 ∣ b
    · rw [if_pos h2]
      right
      obtain ⟨c, rfl⟩ := h2
      have := he _ hb ⟨c, rfl⟩
      rw [Nat.mul_div_cancel_left c (by norm_num : 0 < 2)]
      refine ⟨?_, ?_, ?_, ?_⟩
      · rintro rfl; exact hpb ⟨4, by ring⟩
      · rintro rfl; exact hpb ⟨2, by ring⟩
      · omega
      · omega
    · rw [if_neg h2]
      by_cases h3 : b = 2 * p + 1
      · rw [if_pos h3]; right; omega
      · rw [if_neg h3]
        by_cases h4 : 2 * (φ b - 1) < n
        · rw [if_pos h4]; left; rfl
        · rw [if_neg h4]
          right
          have hb1 := hφ b hb0 (ho b hb h2)
          have hne : φ b ≠ 2 * p + 1 := by
            intro h
            have h5 : b * 2 ^ Nat.log 2 ((n - 1) / b) = (2 * p + 1) * 2 ^ 0 := by simpa using h
            exact h3 (hinj _ _ _ _ h2 (by omega) h5)
          change φ b ≤ n - 1 ∧ n - 1 < 2 * φ b at hb1
          omega
  have hginj : Set.InjOn g (T : Set ℕ) := by
    -- even / odd collision is impossible
    have hEO : ∀ b ∈ T, ∀ t ∈ T, 2 ∣ b → ¬ 2 ∣ t → g b = g t → False := by
      intro b hb t ht h2b h2t h
      have hb0 := h0 b hb
      have ht0 := h0 t ht
      have hx' := hx b hb t ht h2b h2t
      obtain ⟨c, rfl⟩ := h2b
      simp only [hgdef] at h
      rw [if_pos ⟨c, rfl⟩, if_neg h2t, Nat.mul_div_cancel_left c (by norm_num : 0 < 2)] at h
      by_cases h3 : t = 2 * p + 1
      · rw [if_pos h3] at h
        have hc : Nat.Coprime c t := by
          have h1 : Nat.Coprime c (2 + c) := by
            rw [Nat.coprime_add_self_right]
            rw [Nat.coprime_comm, Nat.Prime.coprime_iff_not_dvd Nat.prime_two]
            intro hd; omega
          have : 2 + c = t := by omega
          rwa [this] at h1
        have h2t' : Nat.Coprime 2 t := (Nat.Prime.coprime_iff_not_dvd Nat.prime_two).mpr h2t
        have hg : (2 * c).gcd t = 1 := Nat.Coprime.mul_left h2t' hc
        rw [hg] at hx'
        omega
      · rw [if_neg h3] at h
        by_cases h4 : 2 * (φ t - 1) < n
        · rw [if_pos h4] at h; omega
        · rw [if_neg h4] at h
          have ht1 := hφ t ht0 (ho t ht h2t)
          change φ t ≤ n - 1 ∧ n - 1 < 2 * φ t at ht1
          have hc : Nat.Coprime c t := hcop t (2 ^ Nat.log 2 ((n - 1) / t)) c (by
            change c + 1 = φ t
            omega)
          have h2t' : Nat.Coprime 2 t := (Nat.Prime.coprime_iff_not_dvd Nat.prime_two).mpr h2t
          have hg : (2 * c).gcd t = 1 := Nat.Coprime.mul_left h2t' hc
          rw [hg] at hx'
          omega
    intro b hb b' hb' h
    have hb0 := h0 b hb
    have hb0' := h0 b' hb'
    by_cases h2 : 2 ∣ b
    · by_cases h2' : 2 ∣ b'
      · simp only [hgdef] at h
        rw [if_pos h2, if_pos h2'] at h
        obtain ⟨c, rfl⟩ := h2
        obtain ⟨c', rfl⟩ := h2'
        rw [Nat.mul_div_cancel_left c (by norm_num : 0 < 2),
          Nat.mul_div_cancel_left c' (by norm_num : 0 < 2)] at h
        rw [h]
      · exact (hEO b hb b' hb' h2 h2' h).elim
    · by_cases h2' : 2 ∣ b'
      · exact (hEO b' hb' b hb h2' h2 h.symm).elim
      · -- both odd
        have hb1 := hφ b hb0 (ho b hb h2)
        have hb1' := hφ b' hb0' (ho b' hb' h2')
        change φ b ≤ n - 1 ∧ n - 1 < 2 * φ b at hb1
        change φ b' ≤ n - 1 ∧ n - 1 < 2 * φ b' at hb1'
        have hφinj : φ b = φ b' → b = b' := fun e => hinj _ _ _ _ h2 h2' e
        have h2p' : ∀ t ∈ T, ¬ 2 ∣ t → φ t ≠ 2 * p := by
          intro t ht h2t e
          have hd : p ∣ t * 2 ^ Nat.log 2 ((n - 1) / t) := ⟨2, by change φ t = p * 2; omega⟩
          rcases (Nat.Prime.dvd_mul hp).mp hd with h5 | h5
          · exact hpT t ht h5
          · have h6 := Nat.Prime.dvd_of_dvd_pow hp h5
            have h7 := Nat.le_of_dvd (by norm_num) h6
            omega
        have e1 := h2p' b hb h2
        have e2 := h2p' b' hb' h2'
        simp only [hgdef] at h
        rw [if_neg h2, if_neg h2'] at h
        by_cases h3 : b = 2 * p + 1 <;> by_cases h3' : b' = 2 * p + 1
        · rw [h3, h3']
        · rw [if_pos h3, if_neg h3'] at h
          by_cases h4 : 2 * (φ b' - 1) < n
          · rw [if_pos h4] at h; omega
          · rw [if_neg h4] at h; omega
        · rw [if_neg h3, if_pos h3'] at h
          by_cases h4 : 2 * (φ b - 1) < n
          · rw [if_pos h4] at h; omega
          · rw [if_neg h4] at h; omega
        · rw [if_neg h3, if_neg h3'] at h
          by_cases h4 : 2 * (φ b - 1) < n <;> by_cases h4' : 2 * (φ b' - 1) < n
          · exact hφinj (by omega)
          · rw [if_pos h4, if_neg h4'] at h; omega
          · rw [if_neg h4, if_pos h4'] at h; omega
          · rw [if_neg h4, if_neg h4'] at h; exact hφinj (by omega)
  have hcard : (insert 0 (((Finset.Ioo 0 n).erase p).erase (2 * p))).card = n - 2 := by
    rw [Finset.card_insert_of_notMem (by simp), Finset.card_erase_of_mem, Finset.card_erase_of_mem,
      Nat.card_Ioo]
    · omega
    · rw [Finset.mem_Ioo]; omega
    · rw [Finset.mem_erase, Finset.mem_Ioo]; omega
  have hle := Finset.card_le_card_of_injOn g hmaps hginj
  rw [hcard] at hle
  omega

/-- K2 (half): counting kernel for a prime p with 2p < n ≤ 3p. -/
theorem R2b.K2half (n p : ℕ) (X S : Finset ℕ) (hp0 : 0 < p) (h2p : 2 * p < n) (h9 : 9 ≤ n)
    (hxs : ∀ x ∈ X, ∀ s ∈ S, ∃ y, 0 < y ∧ y < n ∧ ¬ p ∣ y ∧ (x * s = 2 * y ∨ (x * s = y ∧ ¬ 2 ∣ y)))
    (hX : X.Nonempty) (hS : S.Nonempty) (hcard : n ≤ X.card + S.card) (hle : X.card ≤ S.card) :
    ∀ x ∈ X, x = 1 := by
  have big : ∀ Y : Finset ℕ, (∀ x ∈ Y, 0 < x) → Y.Nonempty → ∃ x ∈ Y, Y.card ≤ x := by
    intro Y hpos hY
    by_contra h
    push Not at h
    have hsub : Y ⊆ Finset.Ioo 0 Y.card := by
      intro x hx
      exact Finset.mem_Ioo.mpr ⟨hpos x hx, h x hx⟩
    have h1 := Finset.card_le_card hsub
    rw [Nat.card_Ioo] at h1
    have h2 := hY.card_pos
    omega
  have hXpos : ∀ x ∈ X, 0 < x := by
    intro x hx
    obtain ⟨s, hs⟩ := hS
    obtain ⟨y, hy0, -, -, h⟩ := hxs x hx s hs
    apply Nat.pos_of_ne_zero
    rintro rfl
    rw [Nat.zero_mul] at h
    omega
  have hSpos : ∀ s ∈ S, 0 < s := by
    intro s hs
    obtain ⟨x, hx⟩ := hX
    obtain ⟨y, hy0, -, -, h⟩ := hxs x hx s hs
    apply Nat.pos_of_ne_zero
    rintro rfl
    rw [Nat.mul_zero] at h
    omega
  have hmul : ∀ u v : ℕ, 4 ≤ u → 5 ≤ v → 2 * u + 2 * v ≤ u * v := by
    intro u v hu hv
    obtain ⟨a, rfl⟩ := Nat.exists_eq_add_of_le hu
    obtain ⟨b, rfl⟩ := Nat.exists_eq_add_of_le hv
    nlinarith [Nat.zero_le (a * b)]
  obtain ⟨x0, hx0, hx0c⟩ := big X hXpos hX
  obtain ⟨s0, hs0, hs0c⟩ := big S hSpos hS
  have huv : X.card * S.card < 2 * n := by
    obtain ⟨y, -, hyn, -, h⟩ := hxs x0 hx0 s0 hs0
    have h2 : X.card * S.card ≤ x0 * s0 := Nat.mul_le_mul hx0c hs0c
    omega
  have hu2 : X.card ≤ 2 := by
    by_contra h
    push Not at h
    rcases Nat.lt_or_ge X.card 4 with h4 | h4
    · have h3 : X.card = 3 := by omega
      rw [h3] at huv hcard
      omega
    · have := hmul X.card S.card h4 (by omega)
      omega
  intro x hx
  by_contra hx1
  have hxpos := hXpos x hx
  rcases Nat.lt_or_ge x 3 with h3 | h3
  · have hx2 : x = 2 := by omega
    subst hx2
    have hsub : S ⊆ ((Finset.Ioo 0 n).erase p).erase (2 * p) := by
      intro s hs
      obtain ⟨y, hy0, hyn, hpy, h⟩ := hxs 2 hx s hs
      have hsy : s = y := by omega
      subst hsy
      rw [Finset.mem_erase, Finset.mem_erase, Finset.mem_Ioo]
      refine ⟨?_, ?_, hy0, hyn⟩
      · rintro rfl; exact hpy ⟨2, by ring⟩
      · rintro rfl; exact hpy ⟨1, by ring⟩
    have h1 := Finset.card_le_card hsub
    rw [Finset.card_erase_of_mem (by
        rw [Finset.mem_erase, Finset.mem_Ioo]; omega),
      Finset.card_erase_of_mem (by rw [Finset.mem_Ioo]; omega), Nat.card_Ioo] at h1
    omega
  · have hsub : S ⊆ Finset.Icc 1 (2 * (n - 1) / 3) := by
      intro s hs
      obtain ⟨y, hy0, hyn, hpy, h⟩ := hxs x hx s hs
      have h4 : 3 * s ≤ x * s := Nat.mul_le_mul_right s h3
      rw [Finset.mem_Icc]
      exact ⟨hSpos s hs, by omega⟩
    have h1 := Finset.card_le_card hsub
    rw [Nat.card_Icc] at h1
    omega

/-- K2: both orientations. -/
theorem R2b.K2 (n p : ℕ) (X S : Finset ℕ) (hp0 : 0 < p) (h2p : 2 * p < n) (h9 : 9 ≤ n)
    (hxs : ∀ x ∈ X, ∀ s ∈ S, ∃ y, 0 < y ∧ y < n ∧ ¬ p ∣ y ∧ (x * s = 2 * y ∨ (x * s = y ∧ ¬ 2 ∣ y)))
    (hX : X.Nonempty) (hS : S.Nonempty) (hcard : n ≤ X.card + S.card) :
    (∀ x ∈ X, x = 1) ∨ (∀ s ∈ S, s = 1) := by
  rcases le_total X.card S.card with h | h
  · exact Or.inl (R2b.K2half n p X S hp0 h2p h9 hxs hX hS hcard h)
  · refine Or.inr (R2b.K2half n p S X hp0 h2p h9 ?_ hS hX (by omega) h)
    intro s hs x hx
    rw [Nat.mul_comm]
    exact hxs x hx s hs

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

/-- E2. Duality a ↦ L / a: with a·a' = L = b·b', a' / gcd(a', b') = b / gcd(a, b),
stated without division. -/
theorem R1b.dual_quot (L a a' b b' : ℕ) (ha : a * a' = L) (hb : b * b' = L) (h0 : 0 < a) :
    a' * Nat.gcd a b = b * Nat.gcd a' b' := by
  have h1 : Nat.gcd a' b' * (a * b) = L * Nat.gcd a b := by
    rw [← Nat.gcd_mul_right]
    have e1 : a' * (a * b) = L * b := by rw [← ha]; ring
    have e2 : b' * (a * b) = L * a := by rw [← hb]; ring
    rw [e1, e2, Nat.gcd_mul_left, Nat.gcd_comm b a]
  have h2 : a * (a' * Nat.gcd a b) = a * (b * Nat.gcd a' b') := by
    rw [← mul_assoc, ha, ← h1]; ring
  exact Nat.eq_of_mul_eq_mul_left h0 h2

/-- E3. Duality preserves the strict hypothesis: the pair (a, b) of B becomes the pair
(b', a') of the dual set {L / x}. -/
theorem R1b.dual_strict (L a a' b b' n : ℕ) (ha : a * a' = L) (hb : b * b' = L) (hL : 0 < L)
    (h : a < n * Nat.gcd a b) : b' < n * Nat.gcd b' a' := by
  have hb0 : 0 < b := Nat.pos_of_ne_zero (by rintro rfl; simp at hb; omega)
  have hb'0 : 0 < b' := Nat.pos_of_ne_zero (by rintro rfl; simp at hb; omega)
  have ha0 : 0 < a := Nat.pos_of_ne_zero (by rintro rfl; simp at ha; omega)
  have e := R1b.dual_quot L b b' a a' hb ha hb0
  have hg : 0 < Nat.gcd b a := Nat.gcd_pos_of_pos_left _ hb0
  have hg' : 0 < Nat.gcd b' a' := Nat.gcd_pos_of_pos_left _ hb'0
  rw [Nat.gcd_comm a b] at h
  by_contra hcon
  push Not at hcon
  have h3 : n * Nat.gcd b' a' * Nat.gcd b a ≤ b' * Nat.gcd b a := Nat.mul_le_mul_right _ hcon
  have h4 : a * Nat.gcd b' a' < n * Nat.gcd b a * Nat.gcd b' a' := Nat.mul_lt_mul_of_pos_right h hg'
  rw [e] at h3
  nlinarith

/-- E8. The dual set. For a nonempty set B of positive integers with L = lcm(B), the set
B* = {L / a : a ∈ B} has the same size, no zero, gcd 1, and is strict when B is. -/
theorem R1b.dual_set (B : Finset ℕ) (n : ℕ) (hne : B.Nonempty) (h0 : 0 ∉ B)
    (hs : ∀ a ∈ B, ∀ b ∈ B, a < n * Nat.gcd a b) :
    (B.image (fun a => B.lcm id / a)).card = B.card ∧ 0 ∉ B.image (fun a => B.lcm id / a) ∧
      (B.image (fun a => B.lcm id / a)).gcd id = 1 ∧
      ∀ a ∈ B.image (fun a => B.lcm id / a), ∀ b ∈ B.image (fun a => B.lcm id / a),
        a < n * Nat.gcd a b := by
  set L := B.lcm id with hLdef
  have hdvd : ∀ a ∈ B, a ∣ L := fun a ha => Finset.dvd_lcm (f := id) ha
  have hL0 : L ≠ 0 := by
    intro h
    rw [hLdef, Finset.lcm_eq_zero_iff] at h
    simp at h
    exact h0 h
  have hLpos : 0 < L := Nat.pos_of_ne_zero hL0
  have hmul : ∀ a ∈ B, a * (L / a) = L := fun a ha => Nat.mul_div_cancel' (hdvd a ha)
  have hqpos : ∀ a ∈ B, 0 < L / a := by
    intro a ha
    rcases Nat.eq_zero_or_pos (L / a) with h | h
    · have := hmul a ha
      rw [h] at this
      simp at this
      exact absurd this.symm hL0
    · exact h
  have hapos : ∀ a ∈ B, 0 < a := fun a ha => Nat.pos_of_ne_zero (fun e => h0 (e ▸ ha))
  refine ⟨?_, ?_, ?_, ?_⟩
  · apply Finset.card_image_of_injOn
    intro a ha b hb hab
    simp only at hab
    have e1 := hmul a ha
    have e2 := hmul b hb
    rw [hab] at e1
    have : a * (L / b) = b * (L / b) := by rw [e1, e2]
    exact Nat.eq_of_mul_eq_mul_right (hqpos b hb) this
  · intro h
    rw [Finset.mem_image] at h
    obtain ⟨a, ha, e⟩ := h
    have := hqpos a ha
    omega
  · set d := (B.image (fun a => L / a)).gcd id with hd
    have hdd : ∀ a ∈ B, d ∣ L / a := by
      intro a ha
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
    have hLdvd : L ∣ L / d := Finset.lcm_dvd hall
    have hpos' : 0 < L / d := Nat.div_pos (Nat.le_of_dvd hLpos hdL) hdpos
    have hle : L ≤ L / d := Nat.le_of_dvd hpos' hLdvd
    by_contra hne1
    have h2 : 2 ≤ d := by omega
    have := Nat.div_lt_self hLpos h2
    omega
  · intro x hx y hy
    rw [Finset.mem_image] at hx hy
    obtain ⟨a, ha, rfl⟩ := hx
    obtain ⟨b, hb, rfl⟩ := hy
    exact R1b.dual_strict L b (L / b) a (L / a) n (hmul b hb) (hmul a ha) hLpos (hs b hb a ha)

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
```
