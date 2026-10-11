import Mathlib

/-- 402-R5-b. For every size 229 ≤ n ≤ 680 there is a prime p satisfying the hypotheses of the generalised
criterion r5b_gen_criterion (window certificates + bridge for the non-exceptional n, one divisor-gap
certificate for each exceptional n: 270, 677, 678, 679, 680). -/
theorem r5b_small_229_680 : ∀ n : ℕ, 229 ≤ n → n ≤ 680 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ 2 * (2 * n - p) ≤ n + 2 ∧
      ∀ α : ℕ, α < n → p < α + n →
        (∃ q : ℕ, q.Prime ∧ n ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
        (∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y) := by
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

  have r5b_window_229_676 : ∀ n : ℕ, 229 ≤ n → n ≤ 676 → n ≠ 270 →
      ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
        ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
      intro p lo hi k hp h1 h2 h3 h4 n hl hh
      refine ⟨p, hp, by omega, by omega, ?_⟩
      have : 2 * n - p ≤ k := by omega
      exact le_trans (Nat.mul_le_mul this this) (by omega)
    intro n hl hh e270
    by_cases h236 : n ≤ 236
    · exact blk 457 229 236 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h236
    by_cases h241 : n ≤ 241
    · exact blk 467 237 241 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h241
    by_cases h247 : n ≤ 247
    · exact blk 479 242 247 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h247
    by_cases h253 : n ≤ 253
    · exact blk 491 248 253 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h253
    by_cases h259 : n ≤ 259
    · exact blk 503 254 259 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h259
    by_cases h262 : n ≤ 262
    · exact blk 509 260 262 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h262
    by_cases h269 : n ≤ 269
    · exact blk 523 263 269 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h269
    by_cases h278 : n ≤ 278
    · exact blk 541 271 278 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h278
    by_cases h286 : n ≤ 286
    · exact blk 557 279 286 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h286
    by_cases h293 : n ≤ 293
    · exact blk 571 287 293 15 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h293
    by_cases h302 : n ≤ 302
    · exact blk 587 294 302 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h302
    by_cases h309 : n ≤ 309
    · exact blk 601 303 309 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h309
    by_cases h318 : n ≤ 318
    · exact blk 619 310 318 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h318
    by_cases h324 : n ≤ 324
    · exact blk 631 319 324 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h324
    by_cases h332 : n ≤ 332
    · exact blk 647 325 332 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h332
    by_cases h339 : n ≤ 339
    · exact blk 661 333 339 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h339
    by_cases h347 : n ≤ 347
    · exact blk 677 340 347 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h347
    by_cases h354 : n ≤ 354
    · exact blk 691 348 354 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h354
    by_cases h363 : n ≤ 363
    · exact blk 709 355 363 17 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h363
    by_cases h373 : n ≤ 373
    · exact blk 727 364 373 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h373
    by_cases h381 : n ≤ 381
    · exact blk 743 374 381 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h381
    by_cases h390 : n ≤ 390
    · exact blk 761 382 390 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h390
    by_cases h396 : n ≤ 396
    · exact blk 773 391 396 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h396
    by_cases h403 : n ≤ 403
    · exact blk 787 397 403 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h403
    by_cases h408 : n ≤ 408
    · exact blk 797 404 408 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h408
    by_cases h415 : n ≤ 415
    · exact blk 811 409 415 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h415
    by_cases h424 : n ≤ 424
    · exact blk 829 416 424 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h424
    by_cases h429 : n ≤ 429
    · exact blk 839 425 429 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h429
    by_cases h439 : n ≤ 439
    · exact blk 859 430 439 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h439
    by_cases h448 : n ≤ 448
    · exact blk 877 440 448 19 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h448
    by_cases h454 : n ≤ 454
    · exact blk 887 449 454 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h454
    by_cases h464 : n ≤ 464
    · exact blk 907 455 464 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h464
    by_cases h475 : n ≤ 475
    · exact blk 929 465 475 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h475
    by_cases h484 : n ≤ 484
    · exact blk 947 476 484 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h484
    by_cases h494 : n ≤ 494
    · exact blk 967 485 494 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h494
    by_cases h502 : n ≤ 502
    · exact blk 983 495 502 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h502
    by_cases h509 : n ≤ 509
    · exact blk 997 503 509 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h509
    by_cases h520 : n ≤ 520
    · exact blk 1019 510 520 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h520
    by_cases h530 : n ≤ 530
    · exact blk 1039 521 530 21 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h530
    by_cases h542 : n ≤ 542
    · exact blk 1061 531 542 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h542
    by_cases h546 : n ≤ 546
    · exact blk 1069 543 546 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h546
    by_cases h558 : n ≤ 558
    · exact blk 1093 547 558 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h558
    by_cases h570 : n ≤ 570
    · exact blk 1117 559 570 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h570
    by_cases h576 : n ≤ 576
    · exact blk 1129 571 576 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h576
    by_cases h588 : n ≤ 588
    · exact blk 1153 577 588 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h588
    by_cases h597 : n ≤ 597
    · exact blk 1171 589 597 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h597
    by_cases h608 : n ≤ 608
    · exact blk 1193 598 608 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h608
    by_cases h620 : n ≤ 620
    · exact blk 1217 609 620 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h620
    by_cases h630 : n ≤ 630
    · exact blk 1237 621 630 23 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h630
    by_cases h642 : n ≤ 642
    · exact blk 1259 631 642 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h642
    by_cases h654 : n ≤ 654
    · exact blk 1283 643 654 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h654
    by_cases h666 : n ≤ 666
    · exact blk 1307 655 666 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h666
    by_cases h676 : n ≤ 676
    · exact blk 1327 667 676 25 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h676
    omega

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
  obtain ⟨p, hp, a, b, c⟩ := r5b_window_229_676 n hl (by omega) e270
  have br := r5b_bridge n p a b c
  exact ⟨p, hp, a, b, br.1, br.2⟩
