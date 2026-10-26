theorem variant_5274cf38__h1 : ∀ (B : Set ℕ),
  B.Nonempty →
    (∃ (p : ℕ), (0 : ℕ) < p ∧ ∀ (n : ℕ), n ∈ B ↔ n + p ∈ B) →
      Irrational (∑' (n : (↑B : Type)), (1 : ℝ) / ((2 : ℝ) ^ (↑n : ℕ) - (1 : ℝ))) := by
  -- approach: Erdős 1948 with f_B(m) = #{d | m : d ∈ B}, as in the partial already on this node, but the averaging absorbs the small primes by their tail weight 2^(-i), so the prime supply needed is only m² primes ≡ 1 mod P above 2m²+m with product ≤ 2^(1000P³m¹²), provable from Mathlib by cyclotomic polynomials
  -- licence: CC-BY-4.0
  -- label: m² primes ≡ 1 mod P, product at most 2^(1000 P³ m¹²)
  -- claim: $\forall P \ge 1\ \forall m \ge 1\ \exists S \subseteq \mathbb{P},\ |S| = m^2,\ \forall p \in S:\ p \equiv 1 \pmod P,\ p > 2m^2 + m,\ \text{and } \prod_{p \in S} p \le 2^{1000 P^3 m^{12}}$
  -- Provable from the pinned Mathlib: with n = 6Pm² (not a prime power) and b_s = 1 + n·B₀!·s, every prime factor of Φ_n(b_s) is ≡ 1 (mod n) and exceeds B₀ (Φ_n(b_s) ≡ Φ_n(1) = 1 modulo every prime ≤ B₀), and lies below b_s^n; the b_s are distinct roots of X^n − 1 modulo such a prime, so B₀ = n·m² values of s give m² distinct primes (Polynomial.isRoot_cyclotomic_iff, eval_one_cyclotomic_not_prime_pow, card_nthRoots).
  have hprimes : ∀ P : ℕ, 0 < P → ∀ m : ℕ, 1 ≤ m → ∃ S : Finset ℕ, S.card = m * m ∧
      (∀ p ∈ S, p.Prime ∧ p % P = 1 ∧ 2 * m * m + m < p) ∧
      ∏ p ∈ S, p ≤ 2 ^ (1000 * P ^ 3 * m ^ 12) := by
    sorry
  intro B hB ⟨P, hP, hper⟩
  classical
  obtain ⟨r, hr⟩ := hB
  have hfle : ∀ n, fB B n ≤ n := fB_le B
  have hfdd : ∀ n, fB B n ≤ dd n := fB_le_dd B
  have hposB : ∀ j, ∃ i, 0 < fB B (j + i + 1) := by
    intro j
    obtain ⟨i, hi⟩ := exists_mem_gt hP hper hr j
    exact ⟨i, fB_pos B (by omega) hi⟩
  rw [lambert_set B]
  rintro ⟨qr, hq⟩
  set a : ℤ := qr.num
  set b : ℕ := qr.den
  have hb : 0 < b := qr.pos
  have hx : ∑' n : ℕ, (fB B n : ℝ) / 2 ^ n = a / b := by
    rw [← hq]; exact Rat.cast_def qr
  have hT : ∀ j, Tail (fB B) b j = Zint (fB B) a b j := tail_eq_Zint hfle hb hx
  obtain ⟨m, hbm, hm1, hA4m⟩ := exists_param2 b P
  set q := 2000 * P ^ 3 * m ^ 12 with hqdef
  have hP3 : 1 ≤ P ^ 3 := Nat.one_le_pow _ _ hP
  have hm12 : m ≤ m ^ 12 := le_self_pow₀ hm1 (by norm_num)
  have hq6 : 6 ≤ q := by
    have : 1 ≤ P ^ 3 * m ^ 12 := Nat.one_le_iff_ne_zero.mpr (by positivity)
    simp only [hqdef]; nlinarith
  have hmq : m ≤ q := by
    simp only [hqdef]
    calc m ≤ m ^ 12 := hm12
      _ ≤ 2000 * P ^ 3 * m ^ 12 := by nlinarith
  have h8q : 8 * q ≤ 2 ^ q := eight_mul_le_two_pow hq6
  have hA2 : m + 3 * q ≤ 2 ^ q := by omega
  have hA3 : 8 * b ≤ 2 ^ q := by
    have : 8 * b ≤ 8 * q := by omega
    omega
  have hA4 : 4 * b * (3 + q) + 1 < 2 ^ m := by
    calc 4 * b * (3 + q) + 1 ≤ 4 * m * (3 + q) + 1 := by gcongr
      _ < 2 ^ m := hA4m
  set p₀ := 2 * m * m + m + 1 with hp₀def
  have hmp : m ≤ p₀ := by omega
  obtain ⟨T, hTcard, hTp, hTprod⟩ := hprimes P hP m hm1
  set S : Finset (ℕ × ℕ) := Finset.range m ×ˢ Finset.range m with hSdef
  have hmemS : ∀ ij ∈ S, ij.1 * m + ij.2 < m * m := by
    intro ij hij
    simp only [hSdef, Finset.mem_product, Finset.mem_range] at hij
    nlinarith
  -- the primes, indexed by position `i` and slot `j`
  obtain ⟨pr, hprp, hprT, hinj⟩ : ∃ pr : ℕ × ℕ → ℕ, (∀ ij, (pr ij).Prime) ∧
      (∀ ij ∈ S, pr ij ∈ T) ∧ Set.InjOn pr (S : Set (ℕ × ℕ)) := by
    refine ⟨fun ij => if h : ij.1 * m + ij.2 < m * m then T.orderEmbOfFin hTcard ⟨_, h⟩ else 2,
      ?_, ?_, ?_⟩
    · intro ij
      dsimp only
      split_ifs with h
      · exact (hTp _ (Finset.orderEmbOfFin_mem T hTcard _)).1
      · exact Nat.prime_two
    · intro ij hij
      dsimp only
      rw [dif_pos (hmemS ij hij)]
      exact Finset.orderEmbOfFin_mem T hTcard _
    · intro x hx y hy hxy
      have hx' := hmemS x hx
      have hy' := hmemS y hy
      dsimp only at hxy
      rw [dif_pos hx', dif_pos hy'] at hxy
      have h1 : x.1 * m + x.2 = y.1 * m + y.2 := by
        have := (T.orderEmbOfFin hTcard).injective hxy
        simpa using this
      simp only [hSdef, Finset.coe_product, Finset.coe_range, Set.mem_prod, Set.mem_Iio] at hx hy
      obtain ⟨e1, e2⟩ := idx_inj hx.2 hy.2 h1
      exact Prod.ext e1 e2
  have hprlo : ∀ ij ∈ S, 2 * m * m + m < pr ij := fun ij hij => (hTp _ (hprT ij hij)).2.2
  have hprmod : ∀ ij ∈ S, pr ij % P = 1 := fun ij hij => (hTp _ (hprT ij hij)).2.1
  set Q : ℕ := ∏ ij ∈ S, pr ij ^ 2 with hQdef
  have hQpos : 0 < Q := Finset.prod_pos (fun ij _ => pow_pos (hprp ij).pos 2)
  have hScard : S.card = m * m := by
    rw [hSdef, Finset.card_product, Finset.card_range]
  have hprodle : ∏ ij ∈ S, pr ij ≤ ∏ p ∈ T, p := by
    have himg : ∏ p ∈ S.image pr, p = ∏ ij ∈ S, pr ij :=
      Finset.prod_image (fun x hx y hy h => hinj hx hy h)
    rw [← himg]
    exact Finset.prod_le_prod_of_subset_of_one_le' (Finset.image_subset_iff.mpr hprT)
      (fun p hp _ => (hTp p hp).1.one_lt.le)
  have hQle : Q ≤ 2 ^ q := by
    calc Q = (∏ ij ∈ S, pr ij) ^ 2 := by rw [hQdef, Finset.prod_pow]
      _ ≤ (2 ^ (1000 * P ^ 3 * m ^ 12)) ^ 2 := by gcongr; exact hprodle.trans hTprod
      _ = 2 ^ q := by rw [← pow_mul, hqdef]; ring_nf
  have hD : dd Q ≤ 2 ^ (p₀ - m) := by
    rw [hQdef, dd_prod_sq S pr (fun ij _ => hprp ij) hinj, hScard]
    calc 3 ^ (m * m) ≤ 4 ^ (m * m) := Nat.pow_le_pow_left (by norm_num) _
      _ = 2 ^ (2 * (m * m)) := by rw [pow_mul (2 : ℕ) 2 (m * m)]; norm_num
      _ ≤ 2 ^ (p₀ - m) := by
          apply Nat.pow_le_pow_right (by norm_num)
          have e2 : 2 * m * m = 2 * (m * m) := by ring
          rw [hp₀def]
          omega
  set L := 3 * q with hLdef
  have hdvdQ : ∀ ij ∈ S, pr ij ^ 2 ∣ Q := fun ij hij => Finset.dvd_prod_of_mem _ hij
  -- Chinese remainder theorem
  have hs : ∀ ij ∈ S, pr ij ^ 2 ≠ 0 := fun ij _ => (pow_pos (hprp ij).pos 2).ne'
  have pp : Set.Pairwise (S : Set (ℕ × ℕ)) (Function.onFun Nat.Coprime fun ij => pr ij ^ 2) := by
    intro x hx y hy hxy
    exact Nat.Coprime.pow 2 2 ((Nat.coprime_primes (hprp x) (hprp y)).2
      (fun h => hxy (hinj hx hy h)))
  set crt := Nat.chineseRemainderOfFinset (fun ij => pr ij ^ 2 + pr ij - (ij.1 + 1))
    (fun ij => pr ij ^ 2) S hs pp
  set c : ℕ := crt.1
  have hc : ∀ ij ∈ S, c ≡ pr ij ^ 2 + pr ij - (ij.1 + 1) [MOD pr ij ^ 2] := crt.2
  have hcQ : c < Q := Nat.chineseRemainderOfFinset_lt_prod _ _ hs pp
  -- the key congruence
  have hk : ∀ t, ∀ ij ∈ S, c + t * Q + (ij.1 + 1) ≡ pr ij [MOD pr ij ^ 2] := by
    intro t ij hij
    obtain ⟨R, hR⟩ := hdvdQ ij hij
    have hi : ij.1 < m := by
      simp only [hSdef, Finset.mem_product, Finset.mem_range] at hij; exact hij.1
    have hp := hprlo ij hij
    have e1 : c + t * Q ≡ c [MOD pr ij ^ 2] := by
      rw [hR, show t * (pr ij ^ 2 * R) = pr ij ^ 2 * (t * R) by ring]
      exact Nat.add_mul_mod_self_left _ _ _
    have e2 := (e1.trans (hc ij hij)).add_right (ij.1 + 1)
    rw [Nat.sub_add_cancel (by nlinarith)] at e2
    refine e2.trans ?_
    exact Nat.add_mod_left _ _
  -- forced divisibility
  have hforced : ∀ t, ∀ n, c + t * Q < n → n ≤ c + t * Q + m → 2 ^ m ∣ fB B n := by
    intro t n hn1 hn2
    obtain ⟨i, rfl⟩ : ∃ i, n = c + t * Q + (i + 1) := ⟨n - (c + t * Q) - 1, by omega⟩
    have hi : i < m := by omega
    have hcard : ((Finset.range m).image (fun j => pr (i, j))).card = m := by
      rw [Finset.card_image_of_injOn, Finset.card_range]
      intro j hj j' hj' h
      have := hinj (by simp [hSdef, hi, (by simpa using hj : j < m)])
        (by simp [hSdef, hi, (by simpa using hj' : j' < m)]) h
      simpa using this
    rw [← hcard]
    apply pow_two_dvd_fB B hP hper _ _ (by omega)
    intro p hp
    obtain ⟨j, hj, rfl⟩ := Finset.mem_image.mp hp
    have hij : (i, j) ∈ S := by simp [hSdef, hi, (by simpa using hj : j < m)]
    have h := hk t (i, j) hij
    have hpp := hprp (i, j)
    refine ⟨hpp, hprmod _ hij, (h.dvd_iff (Dvd.intro_left _ (pow_two _).symm)).2 dvd_rfl, ?_⟩
    rw [h.dvd_iff dvd_rfl]
    intro hd
    have := Nat.le_of_dvd hpp.pos hd
    have := hpp.two_le
    nlinarith
  -- coprimality for the positions below the smallest prime
  have hcop : ∀ i < L, m + i < p₀ → Nat.Coprime (c + m + i + 1) Q := by
    intro i hi hip
    apply Nat.Coprime.prod_right
    intro ij hij
    apply Nat.Coprime.pow_right
    rw [Nat.coprime_comm, Nat.Prime.coprime_iff_not_dvd (hprp ij)]
    intro hd
    have hi0 : ij.1 < m := by
      simp only [hSdef, Finset.mem_product, Finset.mem_range] at hij; exact hij.1
    have h1 : pr ij ∣ c + 0 * Q + (ij.1 + 1) :=
      ((hk 0 ij hij).dvd_iff (Dvd.intro_left _ (pow_two _).symm)).2 dvd_rfl
    have h2 : c + m + i + 1 = (c + 0 * Q + (ij.1 + 1)) + (m + i - ij.1) := by omega
    rw [h2] at hd
    have h3 := (Nat.dvd_add_right h1).mp hd
    have h4 := Nat.le_of_dvd (by omega) h3
    have := hprlo ij hij
    omega
  have hgcd : ∀ i < L, dd (Nat.gcd (c + m + i + 1) Q) ≤ dd Q :=
    fun i _ => dd_le_of_dvd hQpos.ne' (Nat.gcd_dvd_right _ _)
  -- lower bound
  have hlow : ∀ t, (2 : ℝ) ^ m ≤ Tail (fB B) b (c + t * Q + m) := by
    intro t
    have hd := Zint_dvd (fB B) a b (c + t * Q) m (hforced t)
    obtain ⟨i₀, hi₀⟩ := hposB (c + t * Q + m)
    have hpos := tail_pos hfle hb (c + t * Q + m) hi₀
    rw [hT] at hpos ⊢
    have hpos' : 0 < Zint (fB B) a b (c + t * Q + m) := by exact_mod_cast hpos
    have := Int.le_of_dvd hpos' hd
    exact_mod_cast this
  exact averaging_contra2 hfdd hb hQpos hcQ hQle hA2 hA3 hA4 hmp hD hcop hgcd hlow
