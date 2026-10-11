import Mathlib

/-- 402-R6-b. For every size 229 ≤ n ≤ 680 there is a prime p satisfying the hypotheses of the generalised
criterion r5b_gen_criterion. 53 window primes in 2 chains, each chain checked by one kernel
evaluation (`decide +kernel`; primality of p < 38² is `Nat.gcd p P = 1`, P the product of the primes below 38),
the bridge from the simple window, and one divisor-gap certificate for each of the 5 exceptional n. -/
theorem r6b_gen_229_680 : ∀ n : ℕ, 229 ≤ n → n ≤ 680 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ 2 * (2 * n - p) ≤ n + 2 ∧
      ∀ α : ℕ, α < n → p < α + n →
        (∃ q : ℕ, q.Prime ∧ n ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y) := by
  have lvl : ∀ B Q : ℕ, (∀ q : ℕ, q < B → 2 ≤ q → Nat.gcd q Q ≠ 1) →
      ∀ p : ℕ, 1 < p → p < B * B → Nat.gcd p Q = 1 → p.Prime := by
    intro B Q small p h1 h2 hg
    by_contra hnp
    have hq : p.minFac.Prime := Nat.minFac_prime (by omega)
    have hsq : p.minFac ^ 2 ≤ p := Nat.minFac_sq_le_self (by omega) hnp
    have hlt : p.minFac < B := by nlinarith
    apply small _ hlt hq.two_le
    have hd := Nat.gcd_dvd_gcd_of_dvd_left Q (Nat.minFac_dvd p)
    rw [hg] at hd
    exact Nat.eq_one_of_dvd_one hd
  have hP : ∀ p : ℕ, (decide (1 < p) && (decide (p < 49) && decide (Nat.gcd p 30 = 1) || decide (p < 900) && decide (Nat.gcd p 6469693230 = 1) || decide (p < 1444) && decide (Nat.gcd p 7420738134810 = 1))) = true → p.Prime := by
    intro p h
    simp only [Bool.and_eq_true, Bool.or_eq_true, decide_eq_true_eq] at h
    obtain ⟨h1, (⟨h2, h3⟩ | ⟨h2, h3⟩) | ⟨h2, h3⟩⟩ := h
    · exact lvl 7 30 (by decide +kernel) p h1 h2 h3
    · exact lvl 30 6469693230 (by decide +kernel) p h1 h2 h3
    · exact lvl 38 7420738134810 (by decide +kernel) p h1 h2 h3
  have key : ∀ t : ℕ → Bool, (∀ p : ℕ, t p = true → p.Prime) →
      ∀ (b : ℕ) (L : List (ℕ × ℕ)) (a : ℕ),
      List.foldr (fun (x : ℕ × ℕ) (f : ℕ → Bool) (lo : ℕ) =>
        (t x.1 && decide (x.2 < x.1) &&
          decide (x.1 < 2 * lo) && decide ((2 * x.2 - x.1) * (2 * x.2 - x.1) ≤ lo)) && f (x.2 + 1))
        (fun lo => decide (b < lo)) L a = true →
      ∀ n : ℕ, a ≤ n → n ≤ b → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro t ht b L
    induction L with
    | nil =>
      intro a h n h1 h2
      simp only [List.foldr_nil, decide_eq_true_eq] at h
      omega
    | cons x L ih =>
      intro a h n h1 h2
      simp only [List.foldr_cons, Bool.and_eq_true, decide_eq_true_eq] at h
      obtain ⟨⟨⟨⟨c1, c4⟩, c5⟩, c6⟩, c7⟩ := h
      by_cases hn : n ≤ x.2
      · refine ⟨x.1, ht x.1 c1, by omega, by omega, ?_⟩
        have h3 : 2 * n - x.1 ≤ 2 * x.2 - x.1 := by omega
        exact le_trans (Nat.mul_le_mul h3 h3) (le_trans c6 h1)
      · exact ih (x.2 + 1) c7 n (by omega) h2
  have r5b_bridge : ∀ n p : ℕ, n < p → p < 2 * n → (2 * n - p) * (2 * n - p) ≤ n →
      2 * (2 * n - p) ≤ n + 2 ∧
      ∀ α : ℕ, α < n → p < α + n →
        (∃ q : ℕ, q.Prime ∧ n ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y) := by
    intro n p h1 h2 h3
    generalize hk : 2 * n - p = k at *
    constructor
    · rcases Nat.lt_or_ge k 3 with h | h
      · omega
      · have : 3 * k ≤ k * k := Nat.mul_le_mul_right _ h
        omega
    · intro α hα1 hα2
      right
      intro x y hxy hd
      by_contra hc
      have h : α * y < n * x := by omega
      have α0 : 0 < α := by omega
      have hx : x * y ≤ α := Nat.le_of_dvd α0 hd
      obtain ⟨s, rfl⟩ : ∃ s, n = α + s := ⟨n - α, by omega⟩
      have hs : s < k := by omega
      have a1 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
      have a2 : α < s * x := by nlinarith
      have a3 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
      have a4 : x + 1 < s := by
        by_contra hc
        have : s * x ≤ (x + 1) * x := Nat.mul_le_mul_right _ (by omega)
        nlinarith
      have a5 : (s + 1) * (s + 1) ≤ k * k := Nat.mul_le_mul hs hs
      have a6 : s * x ≤ s * s := Nat.mul_le_mul_left _ (by omega)
      nlinarith
  have fin : ∀ n : ℕ, (∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n) →
      ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ 2 * (2 * n - p) ≤ n + 2 ∧
        ∀ α : ℕ, α < n → p < α + n →
          (∃ q : ℕ, q.Prime ∧ n ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
          (∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y) := by
    intro n hw
    obtain ⟨p, hp, a, b, c⟩ := hw
    have br := r5b_bridge n p a b c
    exact ⟨p, hp, a, b, br.1, br.2⟩
  have r5b_cert_270 : ∃ p : ℕ, p.Prime ∧ 270 < p ∧ p < 2 * 270 ∧ 2 * (2 * 270 - p) ≤ 270 + 2 ∧
      ∀ α : ℕ, α < 270 → p < α + 270 →
        (∃ q : ℕ, q.Prime ∧ 270 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 270 * x ≤ α * y) := by
    refine ⟨523, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 270 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 254 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 254 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 16 ≤ x := by omega
    have x2 : x ≤ 15 := by
      by_contra h
      have : 16 * 16 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    omega
  have r5b_cert_677 : ∃ p : ℕ, p.Prime ∧ 677 < p ∧ p < 2 * 677 ∧ 2 * (2 * 677 - p) ≤ 677 + 2 ∧
      ∀ α : ℕ, α < 677 → p < α + 677 →
        (∃ q : ℕ, q.Prime ∧ 677 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 677 * x ≤ α * y) := by
    refine ⟨1327, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 677 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 651 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 651 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 26 ≤ x := by omega
    have x2 : x ≤ 25 := by
      by_contra h
      have : 26 * 26 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    omega
  have r5b_cert_678 : ∃ p : ℕ, p.Prime ∧ 678 < p ∧ p < 2 * 678 ∧ 2 * (2 * 678 - p) ≤ 678 + 2 ∧
      ∀ α : ℕ, α < 678 → p < α + 678 →
        (∃ q : ℕ, q.Prime ∧ 678 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 678 * x ≤ α * y) := by
    refine ⟨1327, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    by_cases e650 : α = 650
    · left
      exact ⟨677, by norm_num, by norm_num, by subst e650; norm_num⟩
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 678 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 650 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 650 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 24 ≤ x := by omega
    have x2 : x ≤ 25 := by
      by_contra h
      have : 26 * 26 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    interval_cases x
    · have y2 : y ≤ 25 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 26 := by omega
      interval_cases y <;> omega
  have r5b_cert_679 : ∃ p : ℕ, p.Prime ∧ 679 < p ∧ p < 2 * 679 ∧ 2 * (2 * 679 - p) ≤ 679 + 2 ∧
      ∀ α : ℕ, α < 679 → p < α + 679 →
        (∃ q : ℕ, q.Prime ∧ 679 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 679 * x ≤ α * y) := by
    refine ⟨1327, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    by_cases e650 : α = 650
    · left
      exact ⟨677, by norm_num, by norm_num, by subst e650; norm_num⟩
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 679 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 649 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 649 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 22 ≤ x := by omega
    have x2 : x ≤ 25 := by
      by_contra h
      have : 26 * 26 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    interval_cases x
    · have y2 : y ≤ 23 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 24 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 25 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 26 := by omega
      interval_cases y <;> omega
  have r5b_cert_680 : ∃ p : ℕ, p.Prime ∧ 680 < p ∧ p < 2 * 680 ∧ 2 * (2 * 680 - p) ≤ 680 + 2 ∧
      ∀ α : ℕ, α < 680 → p < α + 680 →
        (∃ q : ℕ, q.Prime ∧ 680 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → 680 * x ≤ α * y) := by
    refine ⟨1327, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
    intro α h1 h2
    by_cases e650 : α = 650
    · left
      exact ⟨677, by norm_num, by norm_num, by subst e650; norm_num⟩
    right
    intro x y hxy hd
    obtain ⟨m, hm⟩ := hd
    by_contra hc
    have hc' : α * y < 680 * x := by omega
    have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
    have b1 : 648 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
    have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have b2' : α * (x + 1) = α * x + α := by ring
    have b3 : 648 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
    have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have b4' : x * (x + 1) = x * x + x := by ring
    have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
    have x1 : 21 ≤ x := by omega
    have x2 : x ≤ 25 := by
      by_contra h
      have : 26 * 26 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
      omega
    interval_cases x
    · have y2 : y ≤ 22 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 23 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 24 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 25 := by omega
      interval_cases y <;> omega
    · have y2 : y ≤ 26 := by omega
      interval_cases y <;> omega
  intro n hl hh
  by_cases e270 : n = 270
  · subst e270
    exact r5b_cert_270
  by_cases e677 : n = 677
  · subst e677
    exact r5b_cert_677
  by_cases e678 : n = 678
  · subst e678
    exact r5b_cert_678
  by_cases e679 : n = 679
  · subst e679
    exact r5b_cert_679
  by_cases e680 : n = 680
  · subst e680
    exact r5b_cert_680
  by_cases s269 : n ≤ 269
  · exact fin n (key (fun p => (decide (1 < p) && (decide (p < 49) && decide (Nat.gcd p 30 = 1) || decide (p < 900) && decide (Nat.gcd p 6469693230 = 1) || decide (p < 1444) && decide (Nat.gcd p 7420738134810 = 1)))) hP 269 [(457, 236), (467, 241), (479, 247), (491, 253), (503, 259), (509, 262), (523, 269)] 229 (by decide +kernel) n (by omega) s269)
  by_cases s676 : n ≤ 676
  · exact fin n (key (fun p => (decide (1 < p) && (decide (p < 49) && decide (Nat.gcd p 30 = 1) || decide (p < 900) && decide (Nat.gcd p 6469693230 = 1) || decide (p < 1444) && decide (Nat.gcd p 7420738134810 = 1)))) hP 676 [(541, 278), (557, 286), (571, 293), (587, 302), (601, 309), (619, 318), (631, 324), (647, 332), (661, 339), (677, 347), (691, 354), (709, 363), (727, 373), (743, 381), (761, 390), (773, 396), (787, 403), (797, 408), (811, 415), (829, 424), (839, 429), (859, 439), (877, 448), (887, 454), (907, 464), (929, 475), (947, 484), (967, 494), (983, 502), (997, 509), (1019, 520), (1039, 530), (1061, 542), (1069, 546), (1093, 558), (1117, 570), (1129, 576), (1153, 588), (1171, 597), (1193, 608), (1217, 620), (1237, 630), (1259, 642), (1283, 654), (1307, 666), (1327, 676)] 271 (by decide +kernel) n (by omega) s676)
  omega
