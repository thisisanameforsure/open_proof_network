import Mathlib

/-- 402-R5-b (generator after 402-R4-c's cover.py). Window primes for 229 ≤ n ≤ 676 except n ∈ {270}:
53 primality certificates by `norm_num`, no `native_decide`. -/
theorem r5b_window_229_676 : ∀ n : ℕ, 229 ≤ n → n ≤ 676 → n ≠ 270 →
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
