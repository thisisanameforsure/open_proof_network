  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h126984 : n ≤ 126984
  · exact blk 253613 126815 126984 355 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h126984
  by_cases h127162 : n ≤ 127162
  · exact blk 253969 126985 127162 355 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h127162
  by_cases h127327 : n ≤ 127327
  · exact blk 254299 127163 127327 355 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h127327
  by_cases h127501 : n ≤ 127501
  · exact blk 254647 127328 127501 355 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h127501
  by_cases h127675 : n ≤ 127675
  · exact blk 254993 127502 127675 357 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h127675
  by_cases h127853 : n ≤ 127853
  · exact blk 255349 127676 127853 357 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h127853
  by_cases h128018 : n ≤ 128018
  · exact blk 255679 127854 128018 357 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h128018
  by_cases h128195 : n ≤ 128195
  · exact blk 256033 128019 128195 357 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h128195
  by_cases h128374 : n ≤ 128374
  · exact blk 256391 128196 128374 357 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h128374
  by_cases h128540 : n ≤ 128540
  · exact blk 256723 128375 128540 357 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h128540
  by_cases h128717 : n ≤ 128717
  · exact blk 257077 128541 128717 357 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h128717
  by_cases h128882 : n ≤ 128882
  · exact blk 257407 128718 128882 357 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h128882
  by_cases h129045 : n ≤ 129045
  · exact blk 257731 128883 129045 359 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h129045
  by_cases h129213 : n ≤ 129213
  · exact blk 258067 129046 129213 359 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h129213
  by_cases h129390 : n ≤ 129390
  · exact blk 258421 129214 129390 359 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h129390
  by_cases h129569 : n ≤ 129569
  · exact blk 258779 129391 129569 359 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h129569
  by_cases h129741 : n ≤ 129741
  · exact blk 259123 129570 129741 359 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h129741
  by_cases h129909 : n ≤ 129909
  · exact blk 259459 129742 129909 359 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h129909
  by_cases h130086 : n ≤ 130086
  · exact blk 259813 129910 130086 359 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h130086
  by_cases h130265 : n ≤ 130265
  · exact blk 260171 130087 130265 359 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h130265
  by_cases h130443 : n ≤ 130443
  · exact blk 260527 130266 130443 359 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h130443
  by_cases h130620 : n ≤ 130620
  · exact blk 260879 130444 130620 361 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h130620
  by_cases h130801 : n ≤ 130801
  · exact blk 261241 130621 130801 361 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h130801
  by_cases h130981 : n ≤ 130981
  · exact blk 261601 130802 130981 361 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h130981
  by_cases h131160 : n ≤ 131160
  · exact blk 261959 130982 131160 361 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h131160
  by_cases h131341 : n ≤ 131341
  · exact blk 262321 131161 131341 361 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h131341
  by_cases h131521 : n ≤ 131521
  · exact blk 262681 131342 131521 361 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h131521
  by_cases h131692 : n ≤ 131692
  · exact blk 263023 131522 131692 361 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h131692
  by_cases h131872 : n ≤ 131872
  · exact blk 263383 131693 131872 361 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h131872
  by_cases h132050 : n ≤ 132050
  · exact blk 263737 131873 132050 363 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h132050
  by_cases h132232 : n ≤ 132232
  · exact blk 264101 132051 132232 363 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h132232
  by_cases h132413 : n ≤ 132413
  · exact blk 264463 132233 132413 363 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h132413
  by_cases h132595 : n ≤ 132595
  · exact blk 264827 132414 132595 363 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h132595
  by_cases h132766 : n ≤ 132766
  · exact blk 265169 132596 132766 363 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h132766
  by_cases h132938 : n ≤ 132938
  · exact blk 265513 132767 132938 363 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h132938
  by_cases h133118 : n ≤ 133118
  · exact blk 265873 132939 133118 363 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h133118
  by_cases h133292 : n ≤ 133292
  · exact blk 266221 133119 133292 363 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h133292
  by_cases h133457 : n ≤ 133457
  · exact blk 266549 133293 133457 365 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h133457
  by_cases h133637 : n ≤ 133637
  · exact blk 266909 133458 133637 365 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h133637
  by_cases h133818 : n ≤ 133818
  · exact blk 267271 133638 133818 365 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h133818
  by_cases h134001 : n ≤ 134001
  · exact blk 267637 133819 134001 365 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h134001
  by_cases h134184 : n ≤ 134184
  · exact blk 268003 134002 134184 365 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h134184
  by_cases h134354 : n ≤ 134354
  · exact blk 268343 134185 134354 365 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h134354
  by_cases h134529 : n ≤ 134529
  · exact blk 268693 134355 134529 365 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h134529
  by_cases h134711 : n ≤ 134711
  · exact blk 269057 134530 134711 365 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h134711
  by_cases h134893 : n ≤ 134893
  · exact blk 269419 134712 134893 367 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h134893
  by_cases h135075 : n ≤ 135075
  · exact blk 269783 134894 135075 367 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h135075
  by_cases h135255 : n ≤ 135255
  · exact blk 270143 135076 135255 367 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h135255
  by_cases h135438 : n ≤ 135438
  · exact blk 270509 135256 135438 367 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h135438
  by_cases h135613 : n ≤ 135613
  · exact blk 270859 135439 135613 367 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h135613
  by_cases h135792 : n ≤ 135792
  · exact blk 271217 135614 135792 367 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h135792
  by_cases h135970 : n ≤ 135970
  · exact blk 271573 135793 135970 367 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h135970
  by_cases h136153 : n ≤ 136153
  · exact blk 271939 135971 136153 367 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h136153
  by_cases h136333 : n ≤ 136333
  · exact blk 272299 136154 136333 367 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h136333
  by_cases h136514 : n ≤ 136514
  · exact blk 272659 136334 136514 369 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h136514
  by_cases h136699 : n ≤ 136699
  · exact blk 273029 136515 136699 369 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h136699
  by_cases h136868 : n ≤ 136868
  · exact blk 273367 136700 136868 369 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h136868
  by_cases h137048 : n ≤ 137048
  · exact blk 273727 136869 137048 369 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h137048
  by_cases h137231 : n ≤ 137231
  · exact blk 274093 137049 137231 369 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h137231
  by_cases h137413 : n ≤ 137413
  · exact blk 274457 137232 137413 369 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h137413
  by_cases h137593 : n ≤ 137593
  · exact blk 274817 137414 137593 369 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h137593
  by_cases h137776 : n ≤ 137776
  · exact blk 275183 137594 137776 369 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h137776
  by_cases h137960 : n ≤ 137960
  · exact blk 275549 137777 137960 371 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h137960
  by_cases h138146 : n ≤ 138146
  · exact blk 275921 137961 138146 371 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h138146
  by_cases h138332 : n ≤ 138332
  · exact blk 276293 138147 138332 371 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h138332
  by_cases h138504 : n ≤ 138504
  · exact blk 276637 138333 138504 371 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h138504
  by_cases h138689 : n ≤ 138689
  · exact blk 277007 138505 138689 371 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h138689
  by_cases h138872 : n ≤ 138872
  · exact blk 277373 138690 138872 371 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h138872
  by_cases h139056 : n ≤ 139056
  · exact blk 277741 138873 139056 371 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h139056
  by_cases h139241 : n ≤ 139241
  · exact blk 278111 139057 139241 371 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h139241
  by_cases h139426 : n ≤ 139426
  · exact blk 278479 139242 139426 373 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h139426
  by_cases h139611 : n ≤ 139611
  · exact blk 278849 139427 139611 373 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h139611
  by_cases h139797 : n ≤ 139797
  · exact blk 279221 139612 139797 373 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h139797
  by_cases h139983 : n ≤ 139983
  · exact blk 279593 139798 139983 373 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h139983
  by_cases h140170 : n ≤ 140170
  · exact blk 279967 139984 140170 373 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h140170
  by_cases h140356 : n ≤ 140356
  · exact blk 280339 140171 140356 373 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h140356
  by_cases h140542 : n ≤ 140542
  · exact blk 280711 140357 140542 373 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h140542
  by_cases h140727 : n ≤ 140727
  · exact blk 281081 140543 140727 373 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h140727
  by_cases h140903 : n ≤ 140903
  · exact blk 281431 140728 140903 375 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h140903
  by_cases h141091 : n ≤ 141091
  · exact blk 281807 140904 141091 375 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h141091
  by_cases h141271 : n ≤ 141271
  · exact blk 282167 141092 141271 375 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h141271
  by_cases h141434 : n ≤ 141434
  · exact blk 282493 141272 141434 375 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h141434
  by_cases h141622 : n ≤ 141622
  · exact blk 282869 141435 141622 375 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h141622
  by_cases h141793 : n ≤ 141793
  · exact blk 283211 141623 141793 375 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h141793
  by_cases h141979 : n ≤ 141979
  · exact blk 283583 141794 141979 375 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h141979
  by_cases h142166 : n ≤ 142166
  · exact blk 283957 141980 142166 375 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h142166
  by_cases h142344 : n ≤ 142344
  · exact blk 284311 142167 142344 377 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h142344
  by_cases h142533 : n ≤ 142533
  · exact blk 284689 142345 142533 377 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h142533
  by_cases h142713 : n ≤ 142713
  · exact blk 285049 142534 142713 377 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h142713
  by_cases h142899 : n ≤ 142899
  · exact blk 285421 142714 142899 377 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h142899
  by_cases h143079 : n ≤ 143079
  · exact blk 285781 142900 143079 377 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h143079
  by_cases h143253 : n ≤ 143253
  · exact blk 286129 143080 143253 377 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h143253
  by_cases h143438 : n ≤ 143438
  · exact blk 286499 143254 143438 377 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h143438
  by_cases h143625 : n ≤ 143625
  · exact blk 286873 143439 143625 377 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h143625
  by_cases h143814 : n ≤ 143814
  · exact blk 287251 143626 143814 377 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h143814
  by_cases h144004 : n ≤ 144004
  · exact blk 287629 143815 144004 379 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h144004
  by_cases h144193 : n ≤ 144193
  · exact blk 288007 144005 144193 379 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h144193
  by_cases h144381 : n ≤ 144381
  · exact blk 288383 144194 144381 379 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h144381
  by_cases h144565 : n ≤ 144565
  · exact blk 288751 144382 144565 379 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h144565
  by_cases h144754 : n ≤ 144754
  · exact blk 289129 144566 144754 379 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h144754
  omega
