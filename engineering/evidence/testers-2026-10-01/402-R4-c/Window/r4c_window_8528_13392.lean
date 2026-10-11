import Mathlib

/-- 402-R4-c. Window primes for 8528 ≤ n ≤ 13392: 100 primality certificates by `norm_num`, no `native_decide`. -/
theorem r4c_window_8528_13392 : ∀ n : ℕ, 8528 ≤ n → n ≤ 13392 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h8572 : n ≤ 8572
  · exact blk 17053 8528 8572 91 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8572
  by_cases h8614 : n ≤ 8614
  · exact blk 17137 8573 8614 91 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8614
  by_cases h8650 : n ≤ 8650
  · exact blk 17209 8615 8650 91 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8650
  by_cases h8696 : n ≤ 8696
  · exact blk 17299 8651 8696 93 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8696
  by_cases h8743 : n ≤ 8743
  · exact blk 17393 8697 8743 93 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8743
  by_cases h8788 : n ≤ 8788
  · exact blk 17483 8744 8788 93 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8788
  by_cases h8833 : n ≤ 8833
  · exact blk 17573 8789 8833 93 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8833
  by_cases h8876 : n ≤ 8876
  · exact blk 17659 8834 8876 93 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8876
  by_cases h8921 : n ≤ 8921
  · exact blk 17749 8877 8921 93 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8921
  by_cases h8966 : n ≤ 8966
  · exact blk 17839 8922 8966 93 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8966
  by_cases h9011 : n ≤ 9011
  · exact blk 17929 8967 9011 93 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9011
  by_cases h9053 : n ≤ 9053
  · exact blk 18013 9012 9053 93 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9053
  by_cases h9096 : n ≤ 9096
  · exact blk 18097 9054 9096 95 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9096
  by_cases h9143 : n ≤ 9143
  · exact blk 18191 9097 9143 95 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9143
  by_cases h9191 : n ≤ 9191
  · exact blk 18287 9144 9191 95 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9191
  by_cases h9237 : n ≤ 9237
  · exact blk 18379 9192 9237 95 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9237
  by_cases h9278 : n ≤ 9278
  · exact blk 18461 9238 9278 95 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9278
  by_cases h9324 : n ≤ 9324
  · exact blk 18553 9279 9324 95 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9324
  by_cases h9366 : n ≤ 9366
  · exact blk 18637 9325 9366 95 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9366
  by_cases h9413 : n ≤ 9413
  · exact blk 18731 9367 9413 95 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9413
  by_cases h9450 : n ≤ 9450
  · exact blk 18803 9414 9450 97 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9450
  by_cases h9498 : n ≤ 9498
  · exact blk 18899 9451 9498 97 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9498
  by_cases h9538 : n ≤ 9538
  · exact blk 18979 9499 9538 97 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9538
  by_cases h9585 : n ≤ 9585
  · exact blk 19073 9539 9585 97 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9585
  by_cases h9630 : n ≤ 9630
  · exact blk 19163 9586 9630 97 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9630
  by_cases h9678 : n ≤ 9678
  · exact blk 19259 9631 9678 97 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9678
  by_cases h9715 : n ≤ 9715
  · exact blk 19333 9679 9715 97 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9715
  by_cases h9763 : n ≤ 9763
  · exact blk 19429 9716 9763 97 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9763
  by_cases h9802 : n ≤ 9802
  · exact blk 19507 9764 9802 97 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9802
  by_cases h9851 : n ≤ 9851
  · exact blk 19603 9803 9851 99 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9851
  by_cases h9899 : n ≤ 9899
  · exact blk 19699 9852 9899 99 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9899
  by_cases h9946 : n ≤ 9946
  · exact blk 19793 9900 9946 99 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9946
  by_cases h9995 : n ≤ 9995
  · exact blk 19891 9947 9995 99 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h9995
  by_cases h10045 : n ≤ 10045
  · exact blk 19991 9996 10045 99 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10045
  by_cases h10094 : n ≤ 10094
  · exact blk 20089 10046 10094 99 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10094
  by_cases h10141 : n ≤ 10141
  · exact blk 20183 10095 10141 99 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10141
  by_cases h10184 : n ≤ 10184
  · exact blk 20269 10142 10184 99 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10184
  by_cases h10234 : n ≤ 10234
  · exact blk 20369 10185 10234 99 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10234
  by_cases h10272 : n ≤ 10272
  · exact blk 20443 10235 10272 101 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10272
  by_cases h10322 : n ≤ 10322
  · exact blk 20543 10273 10322 101 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10322
  by_cases h10371 : n ≤ 10371
  · exact blk 20641 10323 10371 101 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10371
  by_cases h10422 : n ≤ 10422
  · exact blk 20743 10372 10422 101 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10422
  by_cases h10455 : n ≤ 10455
  · exact blk 20809 10423 10455 101 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10455
  by_cases h10502 : n ≤ 10502
  · exact blk 20903 10456 10502 101 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10502
  by_cases h10551 : n ≤ 10551
  · exact blk 21001 10503 10551 101 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10551
  by_cases h10601 : n ≤ 10601
  · exact blk 21101 10552 10601 101 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10601
  by_cases h10647 : n ≤ 10647
  · exact blk 21193 10602 10647 101 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10647
  by_cases h10693 : n ≤ 10693
  · exact blk 21283 10648 10693 103 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10693
  by_cases h10743 : n ≤ 10743
  · exact blk 21383 10694 10743 103 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10743
  by_cases h10795 : n ≤ 10795
  · exact blk 21487 10744 10795 103 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10795
  by_cases h10846 : n ≤ 10846
  · exact blk 21589 10796 10846 103 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10846
  by_cases h10893 : n ≤ 10893
  · exact blk 21683 10847 10893 103 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10893
  by_cases h10945 : n ≤ 10945
  · exact blk 21787 10894 10945 103 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10945
  by_cases h10992 : n ≤ 10992
  · exact blk 21881 10946 10992 103 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h10992
  by_cases h11040 : n ≤ 11040
  · exact blk 21977 10993 11040 103 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11040
  by_cases h11092 : n ≤ 11092
  · exact blk 22079 11041 11092 105 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11092
  by_cases h11138 : n ≤ 11138
  · exact blk 22171 11093 11138 105 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11138
  by_cases h11191 : n ≤ 11191
  · exact blk 22277 11139 11191 105 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11191
  by_cases h11243 : n ≤ 11243
  · exact blk 22381 11192 11243 105 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11243
  by_cases h11294 : n ≤ 11294
  · exact blk 22483 11244 11294 105 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11294
  by_cases h11339 : n ≤ 11339
  · exact blk 22573 11295 11339 105 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11339
  by_cases h11392 : n ≤ 11392
  · exact blk 22679 11340 11392 105 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11392
  by_cases h11444 : n ≤ 11444
  · exact blk 22783 11393 11444 105 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11444
  by_cases h11491 : n ≤ 11491
  · exact blk 22877 11445 11491 105 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11491
  by_cases h11540 : n ≤ 11540
  · exact blk 22973 11492 11540 107 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11540
  by_cases h11594 : n ≤ 11594
  · exact blk 23081 11541 11594 107 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11594
  by_cases h11648 : n ≤ 11648
  · exact blk 23189 11595 11648 107 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11648
  by_cases h11702 : n ≤ 11702
  · exact blk 23297 11649 11702 107 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11702
  by_cases h11753 : n ≤ 11753
  · exact blk 23399 11703 11753 107 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11753
  by_cases h11802 : n ≤ 11802
  · exact blk 23497 11754 11802 107 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11802
  by_cases h11855 : n ≤ 11855
  · exact blk 23603 11803 11855 107 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11855
  by_cases h11898 : n ≤ 11898
  · exact blk 23689 11856 11898 107 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11898
  by_cases h11949 : n ≤ 11949
  · exact blk 23789 11899 11949 109 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h11949
  by_cases h12004 : n ≤ 12004
  · exact blk 23899 11950 12004 109 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12004
  by_cases h12058 : n ≤ 12058
  · exact blk 24007 12005 12058 109 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12058
  by_cases h12111 : n ≤ 12111
  · exact blk 24113 12059 12111 109 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12111
  by_cases h12166 : n ≤ 12166
  · exact blk 24223 12112 12166 109 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12166
  by_cases h12219 : n ≤ 12219
  · exact blk 24329 12167 12219 109 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12219
  by_cases h12274 : n ≤ 12274
  · exact blk 24439 12220 12274 109 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12274
  by_cases h12328 : n ≤ 12328
  · exact blk 24547 12275 12328 109 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12328
  by_cases h12371 : n ≤ 12371
  · exact blk 24631 12329 12371 111 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12371
  by_cases h12422 : n ≤ 12422
  · exact blk 24733 12372 12422 111 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12422
  by_cases h12476 : n ≤ 12476
  · exact blk 24841 12423 12476 111 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12476
  by_cases h12532 : n ≤ 12532
  · exact blk 24953 12477 12532 111 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12532
  by_cases h12584 : n ≤ 12584
  · exact blk 25057 12533 12584 111 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12584
  by_cases h12640 : n ≤ 12640
  · exact blk 25169 12585 12640 111 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12640
  by_cases h12686 : n ≤ 12686
  · exact blk 25261 12641 12686 111 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12686
  by_cases h12742 : n ≤ 12742
  · exact blk 25373 12687 12742 111 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12742
  by_cases h12791 : n ≤ 12791
  · exact blk 25471 12743 12791 111 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12791
  by_cases h12848 : n ≤ 12848
  · exact blk 25583 12792 12848 113 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12848
  by_cases h12903 : n ≤ 12903
  · exact blk 25693 12849 12903 113 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12903
  by_cases h12957 : n ≤ 12957
  · exact blk 25801 12904 12957 113 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h12957
  by_cases h13013 : n ≤ 13013
  · exact blk 25913 12958 13013 113 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13013
  by_cases h13067 : n ≤ 13067
  · exact blk 26021 13014 13067 113 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13067
  by_cases h13116 : n ≤ 13116
  · exact blk 26119 13068 13116 113 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13116
  by_cases h13170 : n ≤ 13170
  · exact blk 26227 13117 13170 113 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13170
  by_cases h13226 : n ≤ 13226
  · exact blk 26339 13171 13226 113 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13226
  by_cases h13282 : n ≤ 13282
  · exact blk 26449 13227 13282 115 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13282
  by_cases h13338 : n ≤ 13338
  · exact blk 26561 13283 13338 115 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13338
  by_cases h13392 : n ≤ 13392
  · exact blk 26669 13339 13392 115 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13392
  omega
