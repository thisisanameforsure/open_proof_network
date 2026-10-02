import Mathlib

/-- 402-R4-c. Window primes for 110090 ≤ n ≤ 126814: 100 primality certificates by `norm_num`, no `native_decide`. -/
theorem r4c_window_110090_126814 : ∀ n : ℕ, 110090 ≤ n → n ≤ 126814 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h110254 : n ≤ 110254
  · exact blk 220177 110090 110254 331 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h110254
  by_cases h110401 : n ≤ 110401
  · exact blk 220471 110255 110401 331 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h110401
  by_cases h110562 : n ≤ 110562
  · exact blk 220793 110402 110562 331 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h110562
  by_cases h110716 : n ≤ 110716
  · exact blk 221101 110563 110716 331 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h110716
  by_cases h110872 : n ≤ 110872
  · exact blk 221413 110717 110872 331 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h110872
  by_cases h111034 : n ≤ 111034
  · exact blk 221737 110873 111034 331 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h111034
  by_cases h111200 : n ≤ 111200
  · exact blk 222067 111035 111200 333 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h111200
  by_cases h111361 : n ≤ 111361
  · exact blk 222389 111201 111361 333 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h111361
  by_cases h111523 : n ≤ 111523
  · exact blk 222713 111362 111523 333 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h111523
  by_cases h111685 : n ≤ 111685
  · exact blk 223037 111524 111685 333 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h111685
  by_cases h111850 : n ≤ 111850
  · exact blk 223367 111686 111850 333 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h111850
  by_cases h112015 : n ≤ 112015
  · exact blk 223697 111851 112015 333 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h112015
  by_cases h112180 : n ≤ 112180
  · exact blk 224027 112016 112180 333 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h112180
  by_cases h112346 : n ≤ 112346
  · exact blk 224359 112181 112346 333 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h112346
  by_cases h112509 : n ≤ 112509
  · exact blk 224683 112347 112509 335 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h112509
  by_cases h112664 : n ≤ 112664
  · exact blk 224993 112510 112664 335 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h112664
  by_cases h112821 : n ≤ 112821
  · exact blk 225307 112665 112821 335 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h112821
  by_cases h112986 : n ≤ 112986
  · exact blk 225637 112822 112986 335 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h112986
  by_cases h113148 : n ≤ 113148
  · exact blk 225961 112987 113148 335 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h113148
  by_cases h113309 : n ≤ 113309
  · exact blk 226283 113149 113309 335 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h113309
  by_cases h113472 : n ≤ 113472
  · exact blk 226609 113310 113472 335 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h113472
  by_cases h113639 : n ≤ 113639
  · exact blk 226943 113473 113639 335 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h113639
  by_cases h113802 : n ≤ 113802
  · exact blk 227267 113640 113802 337 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h113802
  by_cases h113970 : n ≤ 113970
  · exact blk 227603 113803 113970 337 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h113970
  by_cases h114115 : n ≤ 114115
  · exact blk 227893 113971 114115 337 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h114115
  by_cases h114280 : n ≤ 114280
  · exact blk 228223 114116 114280 337 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h114280
  by_cases h114448 : n ≤ 114448
  · exact blk 228559 114281 114448 337 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h114448
  by_cases h114612 : n ≤ 114612
  · exact blk 228887 114449 114612 337 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h114612
  by_cases h114780 : n ≤ 114780
  · exact blk 229223 114613 114780 337 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h114780
  by_cases h114949 : n ≤ 114949
  · exact blk 229561 114781 114949 337 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h114949
  by_cases h115118 : n ≤ 115118
  · exact blk 229897 114950 115118 339 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h115118
  by_cases h115286 : n ≤ 115286
  · exact blk 230233 115119 115286 339 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h115286
  by_cases h115453 : n ≤ 115453
  · exact blk 230567 115287 115453 339 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h115453
  by_cases h115615 : n ≤ 115615
  · exact blk 230891 115454 115615 339 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h115615
  by_cases h115781 : n ≤ 115781
  · exact blk 231223 115616 115781 339 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h115781
  by_cases h115951 : n ≤ 115951
  · exact blk 231563 115782 115951 339 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h115951
  by_cases h116120 : n ≤ 116120
  · exact blk 231901 115952 116120 339 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h116120
  by_cases h116278 : n ≤ 116278
  · exact blk 232217 116121 116278 339 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h116278
  by_cases h116444 : n ≤ 116444
  · exact blk 232549 116279 116444 339 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h116444
  by_cases h116609 : n ≤ 116609
  · exact blk 232877 116445 116609 341 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h116609
  by_cases h116771 : n ≤ 116771
  · exact blk 233201 116610 116771 341 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h116771
  by_cases h116925 : n ≤ 116925
  · exact blk 233509 116772 116925 341 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h116925
  by_cases h117096 : n ≤ 117096
  · exact blk 233851 116926 117096 341 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h117096
  by_cases h117267 : n ≤ 117267
  · exact blk 234193 117097 117267 341 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h117267
  by_cases h117435 : n ≤ 117435
  · exact blk 234529 117268 117435 341 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h117435
  by_cases h117605 : n ≤ 117605
  · exact blk 234869 117436 117605 341 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h117605
  by_cases h117776 : n ≤ 117776
  · exact blk 235211 117606 117776 341 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h117776
  by_cases h117948 : n ≤ 117948
  · exact blk 235553 117777 117948 343 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h117948
  by_cases h118117 : n ≤ 118117
  · exact blk 235891 117949 118117 343 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h118117
  by_cases h118287 : n ≤ 118287
  · exact blk 236231 118118 118287 343 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h118287
  by_cases h118458 : n ≤ 118458
  · exact blk 236573 118288 118458 343 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h118458
  by_cases h118630 : n ≤ 118630
  · exact blk 236917 118459 118630 343 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h118630
  by_cases h118800 : n ≤ 118800
  · exact blk 237257 118631 118800 343 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h118800
  by_cases h118962 : n ≤ 118962
  · exact blk 237581 118801 118962 343 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h118962
  by_cases h119127 : n ≤ 119127
  · exact blk 237911 118963 119127 343 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h119127
  by_cases h119296 : n ≤ 119296
  · exact blk 238247 119128 119296 345 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h119296
  by_cases h119468 : n ≤ 119468
  · exact blk 238591 119297 119468 345 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h119468
  by_cases h119633 : n ≤ 119633
  · exact blk 238921 119469 119633 345 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h119633
  by_cases h119804 : n ≤ 119804
  · exact blk 239263 119634 119804 345 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h119804
  by_cases h119971 : n ≤ 119971
  · exact blk 239597 119805 119971 345 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h119971
  by_cases h120139 : n ≤ 120139
  · exact blk 239933 119972 120139 345 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h120139
  by_cases h120308 : n ≤ 120308
  · exact blk 240271 120140 120308 345 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h120308
  by_cases h120476 : n ≤ 120476
  · exact blk 240607 120309 120476 345 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h120476
  by_cases h120650 : n ≤ 120650
  · exact blk 240953 120477 120650 347 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h120650
  by_cases h120819 : n ≤ 120819
  · exact blk 241291 120651 120819 347 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h120819
  by_cases h120993 : n ≤ 120993
  · exact blk 241639 120820 120993 347 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h120993
  by_cases h121164 : n ≤ 121164
  · exact blk 241981 120994 121164 347 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h121164
  by_cases h121338 : n ≤ 121338
  · exact blk 242329 121165 121338 347 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h121338
  by_cases h121512 : n ≤ 121512
  · exact blk 242677 121339 121512 347 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h121512
  by_cases h121679 : n ≤ 121679
  · exact blk 243011 121513 121679 347 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h121679
  by_cases h121845 : n ≤ 121845
  · exact blk 243343 121680 121845 347 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h121845
  by_cases h122011 : n ≤ 122011
  · exact blk 243673 121846 122011 349 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h122011
  by_cases h122185 : n ≤ 122185
  · exact blk 244021 122012 122185 349 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h122185
  by_cases h122358 : n ≤ 122358
  · exact blk 244367 122186 122358 349 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h122358
  by_cases h122530 : n ≤ 122530
  · exact blk 244711 122359 122530 349 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h122530
  by_cases h122694 : n ≤ 122694
  · exact blk 245039 122531 122694 349 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h122694
  by_cases h122869 : n ≤ 122869
  · exact blk 245389 122695 122869 349 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h122869
  by_cases h123036 : n ≤ 123036
  · exact blk 245723 122870 123036 349 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h123036
  by_cases h123211 : n ≤ 123211
  · exact blk 246073 123037 123211 349 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h123211
  by_cases h123377 : n ≤ 123377
  · exact blk 246403 123212 123377 351 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h123377
  by_cases h123545 : n ≤ 123545
  · exact blk 246739 123378 123545 351 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h123545
  by_cases h123719 : n ≤ 123719
  · exact blk 247087 123546 123719 351 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h123719
  by_cases h123895 : n ≤ 123895
  · exact blk 247439 123720 123895 351 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h123895
  by_cases h124066 : n ≤ 124066
  · exact blk 247781 123896 124066 351 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h124066
  by_cases h124235 : n ≤ 124235
  · exact blk 248119 124067 124235 351 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h124235
  by_cases h124406 : n ≤ 124406
  · exact blk 248461 124236 124406 351 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h124406
  by_cases h124582 : n ≤ 124582
  · exact blk 248813 124407 124582 351 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h124582
  by_cases h124747 : n ≤ 124747
  · exact blk 249143 124583 124747 351 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h124747
  by_cases h124908 : n ≤ 124908
  · exact blk 249463 124748 124908 353 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h124908
  by_cases h125082 : n ≤ 125082
  · exact blk 249811 124909 125082 353 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h125082
  by_cases h125253 : n ≤ 125253
  · exact blk 250153 125083 125253 353 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h125253
  by_cases h125427 : n ≤ 125427
  · exact blk 250501 125254 125427 353 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h125427
  by_cases h125603 : n ≤ 125603
  · exact blk 250853 125428 125603 353 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h125603
  by_cases h125778 : n ≤ 125778
  · exact blk 251203 125604 125778 353 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h125778
  by_cases h125948 : n ≤ 125948
  · exact blk 251543 125779 125948 353 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h125948
  by_cases h126125 : n ≤ 126125
  · exact blk 251897 125949 126125 353 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h126125
  by_cases h126294 : n ≤ 126294
  · exact blk 252233 126126 126294 355 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h126294
  by_cases h126472 : n ≤ 126472
  · exact blk 252589 126295 126472 355 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h126472
  by_cases h126646 : n ≤ 126646
  · exact blk 252937 126473 126646 355 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h126646
  by_cases h126814 : n ≤ 126814
  · exact blk 253273 126647 126814 355 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h126814
  omega
