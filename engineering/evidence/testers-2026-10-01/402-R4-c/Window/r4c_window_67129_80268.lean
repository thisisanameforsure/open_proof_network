import Mathlib

/-- 402-R4-c. Window primes for 67129 ≤ n ≤ 80268: 100 primality certificates by `norm_num`, no `native_decide`. -/
theorem r4c_window_67129_80268 : ∀ n : ℕ, 67129 ≤ n → n ≤ 80268 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h67258 : n ≤ 67258
  · exact blk 134257 67129 67258 259 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h67258
  by_cases h67386 : n ≤ 67386
  · exact blk 134513 67259 67386 259 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h67386
  by_cases h67506 : n ≤ 67506
  · exact blk 134753 67387 67506 259 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h67506
  by_cases h67633 : n ≤ 67633
  · exact blk 135007 67507 67633 259 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h67633
  by_cases h67758 : n ≤ 67758
  · exact blk 135257 67634 67758 259 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h67758
  by_cases h67885 : n ≤ 67885
  · exact blk 135511 67759 67885 259 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h67885
  by_cases h68008 : n ≤ 68008
  · exact blk 135757 67886 68008 259 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h68008
  by_cases h68136 : n ≤ 68136
  · exact blk 136013 68009 68136 259 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h68136
  by_cases h68267 : n ≤ 68267
  · exact blk 136273 68137 68267 261 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h68267
  by_cases h68396 : n ≤ 68396
  · exact blk 136531 68268 68396 261 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h68396
  by_cases h68519 : n ≤ 68519
  · exact blk 136777 68397 68519 261 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h68519
  by_cases h68645 : n ≤ 68645
  · exact blk 137029 68520 68645 261 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h68645
  by_cases h68770 : n ≤ 68770
  · exact blk 137279 68646 68770 261 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h68770
  by_cases h68899 : n ≤ 68899
  · exact blk 137537 68771 68899 261 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h68899
  by_cases h69026 : n ≤ 69026
  · exact blk 137791 68900 69026 261 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h69026
  by_cases h69157 : n ≤ 69157
  · exact blk 138053 69027 69157 261 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h69157
  by_cases h69286 : n ≤ 69286
  · exact blk 138311 69158 69286 261 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h69286
  by_cases h69417 : n ≤ 69417
  · exact blk 138571 69287 69417 263 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h69417
  by_cases h69546 : n ≤ 69546
  · exact blk 138829 69418 69546 263 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h69546
  by_cases h69677 : n ≤ 69677
  · exact blk 139091 69547 69677 263 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h69677
  by_cases h69803 : n ≤ 69803
  · exact blk 139343 69678 69803 263 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h69803
  by_cases h69930 : n ≤ 69930
  · exact blk 139597 69804 69930 263 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h69930
  by_cases h70062 : n ≤ 70062
  · exact blk 139861 69931 70062 263 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h70062
  by_cases h70193 : n ≤ 70193
  · exact blk 140123 70063 70193 263 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h70193
  by_cases h70322 : n ≤ 70322
  · exact blk 140381 70194 70322 263 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h70322
  by_cases h70452 : n ≤ 70452
  · exact blk 140639 70323 70452 265 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h70452
  by_cases h70581 : n ≤ 70581
  · exact blk 140897 70453 70581 265 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h70581
  by_cases h70713 : n ≤ 70713
  · exact blk 141161 70582 70713 265 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h70713
  by_cases h70839 : n ≤ 70839
  · exact blk 141413 70714 70839 265 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h70839
  by_cases h70972 : n ≤ 70972
  · exact blk 141679 70840 70972 265 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h70972
  by_cases h71103 : n ≤ 71103
  · exact blk 141941 70973 71103 265 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h71103
  by_cases h71229 : n ≤ 71229
  · exact blk 142193 71104 71229 265 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h71229
  by_cases h71359 : n ≤ 71359
  · exact blk 142453 71230 71359 265 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h71359
  by_cases h71489 : n ≤ 71489
  · exact blk 142711 71360 71489 267 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h71489
  by_cases h71623 : n ≤ 71623
  · exact blk 142979 71490 71623 267 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h71623
  by_cases h71755 : n ≤ 71755
  · exact blk 143243 71624 71755 267 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h71755
  by_cases h71888 : n ≤ 71888
  · exact blk 143509 71756 71888 267 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h71888
  by_cases h72005 : n ≤ 72005
  · exact blk 143743 71889 72005 267 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h72005
  by_cases h72133 : n ≤ 72133
  · exact blk 143999 72006 72133 267 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h72133
  by_cases h72263 : n ≤ 72263
  · exact blk 144259 72134 72263 267 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h72263
  by_cases h72389 : n ≤ 72389
  · exact blk 144511 72264 72389 267 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h72389
  by_cases h72524 : n ≤ 72524
  · exact blk 144779 72390 72524 269 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h72524
  by_cases h72656 : n ≤ 72656
  · exact blk 145043 72525 72656 269 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h72656
  by_cases h72788 : n ≤ 72788
  · exact blk 145307 72657 72788 269 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h72788
  by_cases h72923 : n ≤ 72923
  · exact blk 145577 72789 72923 269 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h72923
  by_cases h73049 : n ≤ 73049
  · exact blk 145829 72924 73049 269 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h73049
  by_cases h73184 : n ≤ 73184
  · exact blk 146099 73050 73184 269 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h73184
  by_cases h73319 : n ≤ 73319
  · exact blk 146369 73185 73319 269 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h73319
  by_cases h73454 : n ≤ 73454
  · exact blk 146639 73320 73454 269 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h73454
  by_cases h73582 : n ≤ 73582
  · exact blk 146893 73455 73582 271 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h73582
  by_cases h73717 : n ≤ 73717
  · exact blk 147163 73583 73717 271 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h73717
  by_cases h73845 : n ≤ 73845
  · exact blk 147419 73718 73845 271 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h73845
  by_cases h73980 : n ≤ 73980
  · exact blk 147689 73846 73980 271 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h73980
  by_cases h74110 : n ≤ 74110
  · exact blk 147949 73981 74110 271 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h74110
  by_cases h74239 : n ≤ 74239
  · exact blk 148207 74111 74239 271 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h74239
  by_cases h74371 : n ≤ 74371
  · exact blk 148471 74240 74371 271 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h74371
  by_cases h74499 : n ≤ 74499
  · exact blk 148727 74372 74499 271 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h74499
  by_cases h74634 : n ≤ 74634
  · exact blk 148997 74500 74634 271 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h74634
  by_cases h74771 : n ≤ 74771
  · exact blk 149269 74635 74771 273 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h74771
  by_cases h74908 : n ≤ 74908
  · exact blk 149543 74772 74908 273 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h74908
  by_cases h75038 : n ≤ 75038
  · exact blk 149803 74909 75038 273 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h75038
  by_cases h75175 : n ≤ 75175
  · exact blk 150077 75039 75175 273 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h75175
  by_cases h75308 : n ≤ 75308
  · exact blk 150343 75176 75308 273 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h75308
  by_cases h75445 : n ≤ 75445
  · exact blk 150617 75309 75445 273 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h75445
  by_cases h75581 : n ≤ 75581
  · exact blk 150889 75446 75581 273 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h75581
  by_cases h75718 : n ≤ 75718
  · exact blk 151163 75582 75718 273 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h75718
  by_cases h75854 : n ≤ 75854
  · exact blk 151433 75719 75854 275 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h75854
  by_cases h75989 : n ≤ 75989
  · exact blk 151703 75855 75989 275 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h75989
  by_cases h76122 : n ≤ 76122
  · exact blk 151969 75990 76122 275 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h76122
  by_cases h76257 : n ≤ 76257
  · exact blk 152239 76123 76257 275 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h76257
  by_cases h76388 : n ≤ 76388
  · exact blk 152501 76258 76388 275 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h76388
  by_cases h76526 : n ≤ 76526
  · exact blk 152777 76389 76526 275 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h76526
  by_cases h76638 : n ≤ 76638
  · exact blk 153001 76527 76638 275 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h76638
  by_cases h76776 : n ≤ 76776
  · exact blk 153277 76639 76776 275 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h76776
  by_cases h76905 : n ≤ 76905
  · exact blk 153533 76777 76905 277 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h76905
  by_cases h77020 : n ≤ 77020
  · exact blk 153763 76906 77020 277 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h77020
  by_cases h77152 : n ≤ 77152
  · exact blk 154027 77021 77152 277 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h77152
  by_cases h77290 : n ≤ 77290
  · exact blk 154303 77153 77290 277 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h77290
  by_cases h77428 : n ≤ 77428
  · exact blk 154579 77291 77428 277 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h77428
  by_cases h77563 : n ≤ 77563
  · exact blk 154849 77429 77563 277 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h77563
  by_cases h77698 : n ≤ 77698
  · exact blk 155119 77564 77698 277 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h77698
  by_cases h77832 : n ≤ 77832
  · exact blk 155387 77699 77832 277 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h77832
  by_cases h77970 : n ≤ 77970
  · exact blk 155663 77833 77970 277 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h77970
  by_cases h78100 : n ≤ 78100
  · exact blk 155921 77971 78100 279 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h78100
  by_cases h78218 : n ≤ 78218
  · exact blk 156157 78101 78218 279 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h78218
  by_cases h78358 : n ≤ 78358
  · exact blk 156437 78219 78358 279 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h78358
  by_cases h78493 : n ≤ 78493
  · exact blk 156707 78359 78493 279 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h78493
  by_cases h78629 : n ≤ 78629
  · exact blk 156979 78494 78629 279 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h78629
  by_cases h78769 : n ≤ 78769
  · exact blk 157259 78630 78769 279 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h78769
  by_cases h78901 : n ≤ 78901
  · exact blk 157523 78770 78901 279 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h78901
  by_cases h79039 : n ≤ 79039
  · exact blk 157799 78902 79039 279 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h79039
  by_cases h79179 : n ≤ 79179
  · exact blk 158077 79040 79179 281 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h79179
  by_cases h79320 : n ≤ 79320
  · exact blk 158359 79180 79320 281 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h79320
  by_cases h79457 : n ≤ 79457
  · exact blk 158633 79321 79457 281 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h79457
  by_cases h79595 : n ≤ 79595
  · exact blk 158909 79458 79595 281 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h79595
  by_cases h79736 : n ≤ 79736
  · exact blk 159191 79596 79736 281 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h79736
  by_cases h79877 : n ≤ 79877
  · exact blk 159473 79737 79877 281 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h79877
  by_cases h80010 : n ≤ 80010
  · exact blk 159739 79878 80010 281 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h80010
  by_cases h80150 : n ≤ 80150
  · exact blk 160019 80011 80150 281 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h80150
  by_cases h80268 : n ≤ 80268
  · exact blk 160253 80151 80268 283 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h80268
  omega
