  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h94768 : n ≤ 94768
  · exact blk 189229 94618 94768 307 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h94768
  by_cases h94918 : n ≤ 94918
  · exact blk 189529 94769 94918 307 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h94918
  by_cases h95065 : n ≤ 95065
  · exact blk 189823 94919 95065 307 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h95065
  by_cases h95218 : n ≤ 95218
  · exact blk 190129 95066 95218 307 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h95218
  by_cases h95358 : n ≤ 95358
  · exact blk 190409 95219 95358 307 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h95358
  by_cases h95512 : n ≤ 95512
  · exact blk 190717 95359 95512 307 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h95512
  by_cases h95665 : n ≤ 95665
  · exact blk 191021 95513 95665 309 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h95665
  by_cases h95804 : n ≤ 95804
  · exact blk 191299 95666 95804 309 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h95804
  by_cases h95954 : n ≤ 95954
  · exact blk 191599 95805 95954 309 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h95954
  by_cases h96106 : n ≤ 96106
  · exact blk 191903 95955 96106 309 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h96106
  by_cases h96251 : n ≤ 96251
  · exact blk 192193 96107 96251 309 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h96251
  by_cases h96404 : n ≤ 96404
  · exact blk 192499 96252 96404 309 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h96404
  by_cases h96554 : n ≤ 96554
  · exact blk 192799 96405 96554 309 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h96554
  by_cases h96701 : n ≤ 96701
  · exact blk 193093 96555 96701 309 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h96701
  by_cases h96851 : n ≤ 96851
  · exact blk 193393 96702 96851 309 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h96851
  by_cases h97007 : n ≤ 97007
  · exact blk 193703 96852 97007 311 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h97007
  by_cases h97157 : n ≤ 97157
  · exact blk 194003 97008 97157 311 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h97157
  by_cases h97310 : n ≤ 97310
  · exact blk 194309 97158 97310 311 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h97310
  by_cases h97460 : n ≤ 97460
  · exact blk 194609 97311 97460 311 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h97460
  by_cases h97614 : n ≤ 97614
  · exact blk 194917 97461 97614 311 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h97614
  by_cases h97770 : n ≤ 97770
  · exact blk 195229 97615 97770 311 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h97770
  by_cases h97926 : n ≤ 97926
  · exact blk 195541 97771 97926 311 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h97926
  by_cases h98064 : n ≤ 98064
  · exact blk 195817 97927 98064 311 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h98064
  by_cases h98215 : n ≤ 98215
  · exact blk 196117 98065 98215 313 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h98215
  by_cases h98371 : n ≤ 98371
  · exact blk 196429 98216 98371 313 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h98371
  by_cases h98526 : n ≤ 98526
  · exact blk 196739 98372 98526 313 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h98526
  by_cases h98673 : n ≤ 98673
  · exact blk 197033 98527 98673 313 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h98673
  by_cases h98830 : n ≤ 98830
  · exact blk 197347 98674 98830 313 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h98830
  by_cases h98982 : n ≤ 98982
  · exact blk 197651 98831 98982 313 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h98982
  by_cases h99138 : n ≤ 99138
  · exact blk 197963 98983 99138 313 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h99138
  by_cases h99295 : n ≤ 99295
  · exact blk 198277 99139 99295 313 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h99295
  by_cases h99452 : n ≤ 99452
  · exact blk 198589 99296 99452 315 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h99452
  by_cases h99608 : n ≤ 99608
  · exact blk 198901 99453 99608 315 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h99608
  by_cases h99763 : n ≤ 99763
  · exact blk 199211 99609 99763 315 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h99763
  by_cases h99919 : n ≤ 99919
  · exact blk 199523 99764 99919 315 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h99919
  by_cases h100073 : n ≤ 100073
  · exact blk 199831 99920 100073 315 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h100073
  by_cases h100223 : n ≤ 100223
  · exact blk 200131 100074 100223 315 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h100223
  by_cases h100379 : n ≤ 100379
  · exact blk 200443 100224 100379 315 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h100379
  by_cases h100523 : n ≤ 100523
  · exact blk 200731 100380 100523 315 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h100523
  by_cases h100677 : n ≤ 100677
  · exact blk 201037 100524 100677 317 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h100677
  by_cases h100827 : n ≤ 100827
  · exact blk 201337 100678 100827 317 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h100827
  by_cases h100985 : n ≤ 100985
  · exact blk 201653 100828 100985 317 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h100985
  by_cases h101139 : n ≤ 101139
  · exact blk 201961 100986 101139 317 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h101139
  by_cases h101297 : n ≤ 101297
  · exact blk 202277 101140 101297 317 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h101297
  by_cases h101454 : n ≤ 101454
  · exact blk 202591 101298 101454 317 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h101454
  by_cases h101612 : n ≤ 101612
  · exact blk 202907 101455 101612 317 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h101612
  by_cases h101769 : n ≤ 101769
  · exact blk 203221 101613 101769 317 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h101769
  by_cases h101925 : n ≤ 101925
  · exact blk 203531 101770 101925 319 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h101925
  by_cases h102081 : n ≤ 102081
  · exact blk 203843 101926 102081 319 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h102081
  by_cases h102241 : n ≤ 102241
  · exact blk 204163 102082 102241 319 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h102241
  by_cases h102400 : n ≤ 102400
  · exact blk 204481 102242 102400 319 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h102400
  by_cases h102558 : n ≤ 102558
  · exact blk 204797 102401 102558 319 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h102558
  by_cases h102715 : n ≤ 102715
  · exact blk 205111 102559 102715 319 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h102715
  by_cases h102873 : n ≤ 102873
  · exact blk 205427 102716 102873 319 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h102873
  by_cases h103020 : n ≤ 103020
  · exact blk 205721 102874 103020 319 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h103020
  by_cases h103179 : n ≤ 103179
  · exact blk 206039 103021 103179 319 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h103179
  by_cases h103336 : n ≤ 103336
  · exact blk 206351 103180 103336 321 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h103336
  by_cases h103486 : n ≤ 103486
  · exact blk 206651 103337 103486 321 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h103486
  by_cases h103637 : n ≤ 103637
  · exact blk 206953 103487 103637 321 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h103637
  by_cases h103795 : n ≤ 103795
  · exact blk 207269 103638 103795 321 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h103795
  by_cases h103955 : n ≤ 103955
  · exact blk 207589 103796 103955 321 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h103955
  by_cases h104099 : n ≤ 104099
  · exact blk 207877 103956 104099 321 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h104099
  by_cases h104255 : n ≤ 104255
  · exact blk 208189 104100 104255 321 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h104255
  by_cases h104416 : n ≤ 104416
  · exact blk 208511 104256 104416 321 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h104416
  by_cases h104565 : n ≤ 104565
  · exact blk 208807 104417 104565 323 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h104565
  by_cases h104723 : n ≤ 104723
  · exact blk 209123 104566 104723 323 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h104723
  by_cases h104882 : n ≤ 104882
  · exact blk 209441 104724 104882 323 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h104882
  by_cases h105033 : n ≤ 105033
  · exact blk 209743 104883 105033 323 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h105033
  by_cases h105188 : n ≤ 105188
  · exact blk 210053 105034 105188 323 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h105188
  by_cases h105342 : n ≤ 105342
  · exact blk 210361 105189 105342 323 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h105342
  by_cases h105497 : n ≤ 105497
  · exact blk 210671 105343 105497 323 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h105497
  by_cases h105645 : n ≤ 105645
  · exact blk 210967 105498 105645 323 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h105645
  by_cases h105808 : n ≤ 105808
  · exact blk 211291 105646 105808 325 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h105808
  by_cases h105961 : n ≤ 105961
  · exact blk 211597 105809 105961 325 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h105961
  by_cases h106108 : n ≤ 106108
  · exact blk 211891 105962 106108 325 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h106108
  by_cases h106267 : n ≤ 106267
  · exact blk 212209 106109 106267 325 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h106267
  by_cases h106416 : n ≤ 106416
  · exact blk 212507 106268 106416 325 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h106416
  by_cases h106576 : n ≤ 106576
  · exact blk 212827 106417 106576 325 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h106576
  by_cases h106737 : n ≤ 106737
  · exact blk 213149 106577 106737 325 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h106737
  by_cases h106896 : n ≤ 106896
  · exact blk 213467 106738 106896 325 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h106896
  by_cases h107058 : n ≤ 107058
  · exact blk 213791 106897 107058 325 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h107058
  by_cases h107209 : n ≤ 107209
  · exact blk 214091 107059 107209 327 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h107209
  by_cases h107363 : n ≤ 107363
  · exact blk 214399 107210 107363 327 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h107363
  by_cases h107525 : n ≤ 107525
  · exact blk 214723 107364 107525 327 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h107525
  by_cases h107689 : n ≤ 107689
  · exact blk 215051 107526 107689 327 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h107689
  by_cases h107843 : n ≤ 107843
  · exact blk 215359 107690 107843 327 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h107843
  by_cases h108007 : n ≤ 108007
  · exact blk 215687 107844 108007 327 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h108007
  by_cases h108155 : n ≤ 108155
  · exact blk 215983 108008 108155 327 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h108155
  by_cases h108308 : n ≤ 108308
  · exact blk 216289 108156 108308 327 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h108308
  by_cases h108473 : n ≤ 108473
  · exact blk 216617 108309 108473 329 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h108473
  by_cases h108638 : n ≤ 108638
  · exact blk 216947 108474 108638 329 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h108638
  by_cases h108800 : n ≤ 108800
  · exact blk 217271 108639 108800 329 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h108800
  by_cases h108954 : n ≤ 108954
  · exact blk 217579 108801 108954 329 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h108954
  by_cases h109119 : n ≤ 109119
  · exact blk 217909 108955 109119 329 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h109119
  by_cases h109281 : n ≤ 109281
  · exact blk 218233 109120 109281 329 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h109281
  by_cases h109440 : n ≤ 109440
  · exact blk 218551 109282 109440 329 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h109440
  by_cases h109601 : n ≤ 109601
  · exact blk 218873 109441 109601 329 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h109601
  by_cases h109759 : n ≤ 109759
  · exact blk 219187 109602 109759 331 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h109759
  by_cases h109924 : n ≤ 109924
  · exact blk 219517 109760 109924 331 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h109924
  by_cases h110089 : n ≤ 110089
  · exact blk 219847 109925 110089 331 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h110089
  omega
