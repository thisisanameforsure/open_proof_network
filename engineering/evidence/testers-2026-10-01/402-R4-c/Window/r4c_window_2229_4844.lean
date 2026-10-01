import Mathlib

/-- 402-R4-c. Window primes for 2229 ≤ n ≤ 4844: 100 primality certificates by `norm_num`, no `native_decide`. -/
theorem r4c_window_2229_4844 : ∀ n : ℕ, 2229 ≤ n → n ≤ 4844 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h2252 : n ≤ 2252
  · exact blk 4457 2229 2252 47 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2252
  by_cases h2270 : n ≤ 2270
  · exact blk 4493 2253 2270 47 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2270
  by_cases h2285 : n ≤ 2285
  · exact blk 4523 2271 2285 47 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2285
  by_cases h2307 : n ≤ 2307
  · exact blk 4567 2286 2307 47 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2307
  by_cases h2325 : n ≤ 2325
  · exact blk 4603 2308 2325 47 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2325
  by_cases h2349 : n ≤ 2349
  · exact blk 4651 2326 2349 47 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2349
  by_cases h2369 : n ≤ 2369
  · exact blk 4691 2350 2369 47 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2369
  by_cases h2390 : n ≤ 2390
  · exact blk 4733 2370 2390 47 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2390
  by_cases h2403 : n ≤ 2403
  · exact blk 4759 2391 2403 47 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2403
  by_cases h2425 : n ≤ 2425
  · exact blk 4801 2404 2425 49 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2425
  by_cases h2440 : n ≤ 2440
  · exact blk 4831 2426 2440 49 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2440
  by_cases h2463 : n ≤ 2463
  · exact blk 4877 2441 2463 49 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2463
  by_cases h2484 : n ≤ 2484
  · exact blk 4919 2464 2484 49 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2484
  by_cases h2509 : n ≤ 2509
  · exact blk 4969 2485 2509 49 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2509
  by_cases h2530 : n ≤ 2530
  · exact blk 5011 2510 2530 49 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2530
  by_cases h2554 : n ≤ 2554
  · exact blk 5059 2531 2554 49 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2554
  by_cases h2578 : n ≤ 2578
  · exact blk 5107 2555 2578 49 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2578
  by_cases h2601 : n ≤ 2601
  · exact blk 5153 2579 2601 49 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2601
  by_cases h2624 : n ≤ 2624
  · exact blk 5197 2602 2624 51 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2624
  by_cases h2644 : n ≤ 2644
  · exact blk 5237 2625 2644 51 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2644
  by_cases h2666 : n ≤ 2666
  · exact blk 5281 2645 2666 51 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2666
  by_cases h2692 : n ≤ 2692
  · exact blk 5333 2667 2692 51 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2692
  by_cases h2716 : n ≤ 2716
  · exact blk 5381 2693 2716 51 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2716
  by_cases h2741 : n ≤ 2741
  · exact blk 5431 2717 2741 51 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2741
  by_cases h2767 : n ≤ 2767
  · exact blk 5483 2742 2767 51 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2767
  by_cases h2791 : n ≤ 2791
  · exact blk 5531 2768 2791 51 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2791
  by_cases h2816 : n ≤ 2816
  · exact blk 5581 2792 2816 51 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2816
  by_cases h2838 : n ≤ 2838
  · exact blk 5623 2817 2838 53 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2838
  by_cases h2861 : n ≤ 2861
  · exact blk 5669 2839 2861 53 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2861
  by_cases h2885 : n ≤ 2885
  · exact blk 5717 2862 2885 53 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2885
  by_cases h2901 : n ≤ 2901
  · exact blk 5749 2886 2901 53 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2901
  by_cases h2927 : n ≤ 2927
  · exact blk 5801 2902 2927 53 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2927
  by_cases h2952 : n ≤ 2952
  · exact blk 5851 2928 2952 53 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2952
  by_cases h2978 : n ≤ 2978
  · exact blk 5903 2953 2978 53 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h2978
  by_cases h3003 : n ≤ 3003
  · exact blk 5953 2979 3003 53 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3003
  by_cases h3030 : n ≤ 3030
  · exact blk 6007 3004 3030 53 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3030
  by_cases h3054 : n ≤ 3054
  · exact blk 6053 3031 3054 55 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3054
  by_cases h3078 : n ≤ 3078
  · exact blk 6101 3055 3078 55 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3078
  by_cases h3103 : n ≤ 3103
  · exact blk 6151 3079 3103 55 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3103
  by_cases h3129 : n ≤ 3129
  · exact blk 6203 3104 3129 55 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3129
  by_cases h3156 : n ≤ 3156
  · exact blk 6257 3130 3156 55 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3156
  by_cases h3183 : n ≤ 3183
  · exact blk 6311 3157 3183 55 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3183
  by_cases h3211 : n ≤ 3211
  · exact blk 6367 3184 3211 55 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3211
  by_cases h3238 : n ≤ 3238
  · exact blk 6421 3212 3238 55 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3238
  by_cases h3264 : n ≤ 3264
  · exact blk 6473 3239 3264 55 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3264
  by_cases h3293 : n ≤ 3293
  · exact blk 6529 3265 3293 57 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3293
  by_cases h3319 : n ≤ 3319
  · exact blk 6581 3294 3319 57 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3319
  by_cases h3347 : n ≤ 3347
  · exact blk 6637 3320 3347 57 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3347
  by_cases h3374 : n ≤ 3374
  · exact blk 6691 3348 3374 57 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3374
  by_cases h3397 : n ≤ 3397
  · exact blk 6737 3375 3397 57 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3397
  by_cases h3425 : n ≤ 3425
  · exact blk 6793 3398 3425 57 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3425
  by_cases h3449 : n ≤ 3449
  · exact blk 6841 3426 3449 57 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3449
  by_cases h3478 : n ≤ 3478
  · exact blk 6899 3450 3478 57 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3478
  by_cases h3503 : n ≤ 3503
  · exact blk 6949 3479 3503 57 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3503
  by_cases h3530 : n ≤ 3530
  · exact blk 7001 3504 3530 59 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3530
  by_cases h3558 : n ≤ 3558
  · exact blk 7057 3531 3558 59 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3558
  by_cases h3584 : n ≤ 3584
  · exact blk 7109 3559 3584 59 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3584
  by_cases h3609 : n ≤ 3609
  · exact blk 7159 3585 3609 59 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3609
  by_cases h3639 : n ≤ 3639
  · exact blk 7219 3610 3639 59 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3639
  by_cases h3656 : n ≤ 3656
  · exact blk 7253 3640 3656 59 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3656
  by_cases h3684 : n ≤ 3684
  · exact blk 7309 3657 3684 59 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3684
  by_cases h3714 : n ≤ 3714
  · exact blk 7369 3685 3714 59 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3714
  by_cases h3738 : n ≤ 3738
  · exact blk 7417 3715 3738 59 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3738
  by_cases h3769 : n ≤ 3769
  · exact blk 7477 3739 3769 61 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3769
  by_cases h3799 : n ≤ 3799
  · exact blk 7537 3770 3799 61 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3799
  by_cases h3826 : n ≤ 3826
  · exact blk 7591 3800 3826 61 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3826
  by_cases h3855 : n ≤ 3855
  · exact blk 7649 3827 3855 61 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3855
  by_cases h3882 : n ≤ 3882
  · exact blk 7703 3856 3882 61 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3882
  by_cases h3910 : n ≤ 3910
  · exact blk 7759 3883 3910 61 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3910
  by_cases h3939 : n ≤ 3939
  · exact blk 7817 3911 3939 61 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3939
  by_cases h3970 : n ≤ 3970
  · exact blk 7879 3940 3970 61 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h3970
  by_cases h4000 : n ≤ 4000
  · exact blk 7937 3971 4000 63 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4000
  by_cases h4028 : n ≤ 4028
  · exact blk 7993 4001 4028 63 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4028
  by_cases h4058 : n ≤ 4058
  · exact blk 8053 4029 4058 63 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4058
  by_cases h4090 : n ≤ 4090
  · exact blk 8117 4059 4090 63 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4090
  by_cases h4121 : n ≤ 4121
  · exact blk 8179 4091 4121 63 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4121
  by_cases h4153 : n ≤ 4153
  · exact blk 8243 4122 4153 63 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4153
  by_cases h4180 : n ≤ 4180
  · exact blk 8297 4154 4180 63 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4180
  by_cases h4208 : n ≤ 4208
  · exact blk 8353 4181 4208 63 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4208
  by_cases h4226 : n ≤ 4226
  · exact blk 8389 4209 4226 63 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4226
  by_cases h4256 : n ≤ 4256
  · exact blk 8447 4227 4256 65 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4256
  by_cases h4289 : n ≤ 4289
  · exact blk 8513 4257 4289 65 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4289
  by_cases h4319 : n ≤ 4319
  · exact blk 8573 4290 4319 65 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4319
  by_cases h4347 : n ≤ 4347
  · exact blk 8629 4320 4347 65 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4347
  by_cases h4379 : n ≤ 4379
  · exact blk 8693 4348 4379 65 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4379
  by_cases h4409 : n ≤ 4409
  · exact blk 8753 4380 4409 65 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4409
  by_cases h4442 : n ≤ 4442
  · exact blk 8819 4410 4442 65 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4442
  by_cases h4466 : n ≤ 4466
  · exact blk 8867 4443 4466 65 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4466
  by_cases h4499 : n ≤ 4499
  · exact blk 8933 4467 4499 65 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4499
  by_cases h4533 : n ≤ 4533
  · exact blk 8999 4500 4533 67 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4533
  by_cases h4567 : n ≤ 4567
  · exact blk 9067 4534 4567 67 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4567
  by_cases h4600 : n ≤ 4600
  · exact blk 9133 4568 4600 67 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4600
  by_cases h4633 : n ≤ 4633
  · exact blk 9199 4601 4633 67 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4633
  by_cases h4662 : n ≤ 4662
  · exact blk 9257 4634 4662 67 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4662
  by_cases h4695 : n ≤ 4695
  · exact blk 9323 4663 4695 67 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4695
  by_cases h4729 : n ≤ 4729
  · exact blk 9391 4696 4729 67 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4729
  by_cases h4753 : n ≤ 4753
  · exact blk 9439 4730 4753 67 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4753
  by_cases h4782 : n ≤ 4782
  · exact blk 9497 4754 4782 67 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4782
  by_cases h4810 : n ≤ 4810
  · exact blk 9551 4783 4810 69 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4810
  by_cases h4844 : n ≤ 4844
  · exact blk 9619 4811 4844 69 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4844
  omega
