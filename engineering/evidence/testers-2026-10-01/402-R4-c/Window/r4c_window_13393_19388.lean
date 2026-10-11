import Mathlib

/-- 402-R4-c. Window primes for 13393 ≤ n ≤ 19388: 100 primality certificates by `norm_num`, no `native_decide`. -/
theorem r4c_window_13393_19388 : ∀ n : ℕ, 13393 ≤ n → n ≤ 19388 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h13449 : n ≤ 13449
  · exact blk 26783 13393 13449 115 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13449
  by_cases h13504 : n ≤ 13504
  · exact blk 26893 13450 13504 115 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13504
  by_cases h13554 : n ≤ 13554
  · exact blk 26993 13505 13554 115 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13554
  by_cases h13612 : n ≤ 13612
  · exact blk 27109 13555 13612 115 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13612
  by_cases h13663 : n ≤ 13663
  · exact blk 27211 13613 13663 115 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13663
  by_cases h13707 : n ≤ 13707
  · exact blk 27299 13664 13707 115 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13707
  by_cases h13763 : n ≤ 13763
  · exact blk 27409 13708 13763 117 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13763
  by_cases h13822 : n ≤ 13822
  · exact blk 27527 13764 13822 117 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13822
  by_cases h13874 : n ≤ 13874
  · exact blk 27631 13823 13874 117 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13874
  by_cases h13933 : n ≤ 13933
  · exact blk 27749 13875 13933 117 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13933
  by_cases h13984 : n ≤ 13984
  · exact blk 27851 13934 13984 117 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h13984
  by_cases h14042 : n ≤ 14042
  · exact blk 27967 13985 14042 117 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14042
  by_cases h14099 : n ≤ 14099
  · exact blk 28081 14043 14099 117 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14099
  by_cases h14150 : n ≤ 14150
  · exact blk 28183 14100 14150 117 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14150
  by_cases h14207 : n ≤ 14207
  · exact blk 28297 14151 14207 117 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14207
  by_cases h14265 : n ≤ 14265
  · exact blk 28411 14208 14265 119 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14265
  by_cases h14318 : n ≤ 14318
  · exact blk 28517 14266 14318 119 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14318
  by_cases h14375 : n ≤ 14375
  · exact blk 28631 14319 14375 119 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14375
  by_cases h14435 : n ≤ 14435
  · exact blk 28751 14376 14435 119 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14435
  by_cases h14495 : n ≤ 14495
  · exact blk 28871 14436 14495 119 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14495
  by_cases h14549 : n ≤ 14549
  · exact blk 28979 14496 14549 119 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14549
  by_cases h14598 : n ≤ 14598
  · exact blk 29077 14550 14598 119 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14598
  by_cases h14655 : n ≤ 14655
  · exact blk 29191 14599 14655 119 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14655
  by_cases h14716 : n ≤ 14716
  · exact blk 29311 14656 14716 121 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14716
  by_cases h14775 : n ≤ 14775
  · exact blk 29429 14717 14775 121 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14775
  by_cases h14829 : n ≤ 14829
  · exact blk 29537 14776 14829 121 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14829
  by_cases h14881 : n ≤ 14881
  · exact blk 29641 14830 14881 121 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14881
  by_cases h14941 : n ≤ 14941
  · exact blk 29761 14882 14941 121 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h14941
  by_cases h15001 : n ≤ 15001
  · exact blk 29881 14942 15001 121 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15001
  by_cases h15055 : n ≤ 15055
  · exact blk 29989 15002 15055 121 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15055
  by_cases h15115 : n ≤ 15115
  · exact blk 30109 15056 15115 121 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15115
  by_cases h15172 : n ≤ 15172
  · exact blk 30223 15116 15172 121 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15172
  by_cases h15232 : n ≤ 15232
  · exact blk 30341 15173 15232 123 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15232
  by_cases h15286 : n ≤ 15286
  · exact blk 30449 15233 15286 123 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15286
  by_cases h15341 : n ≤ 15341
  · exact blk 30559 15287 15341 123 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15341
  by_cases h15400 : n ≤ 15400
  · exact blk 30677 15342 15400 123 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15400
  by_cases h15452 : n ≤ 15452
  · exact blk 30781 15401 15452 123 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15452
  by_cases h15508 : n ≤ 15508
  · exact blk 30893 15453 15508 123 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15508
  by_cases h15568 : n ≤ 15568
  · exact blk 31013 15509 15568 123 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15568
  by_cases h15623 : n ≤ 15623
  · exact blk 31123 15569 15623 123 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15623
  by_cases h15685 : n ≤ 15685
  · exact blk 31247 15624 15685 123 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15685
  by_cases h15741 : n ≤ 15741
  · exact blk 31357 15686 15741 125 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15741
  by_cases h15803 : n ≤ 15803
  · exact blk 31481 15742 15803 125 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15803
  by_cases h15866 : n ≤ 15866
  · exact blk 31607 15804 15866 125 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15866
  by_cases h15927 : n ≤ 15927
  · exact blk 31729 15867 15927 125 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15927
  by_cases h15987 : n ≤ 15987
  · exact blk 31849 15928 15987 125 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h15987
  by_cases h16049 : n ≤ 16049
  · exact blk 31973 15988 16049 125 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16049
  by_cases h16112 : n ≤ 16112
  · exact blk 32099 16050 16112 125 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16112
  by_cases h16169 : n ≤ 16169
  · exact blk 32213 16113 16169 125 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16169
  by_cases h16227 : n ≤ 16227
  · exact blk 32327 16170 16227 127 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16227
  by_cases h16285 : n ≤ 16285
  · exact blk 32443 16228 16285 127 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16285
  by_cases h16348 : n ≤ 16348
  · exact blk 32569 16286 16348 127 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16348
  by_cases h16410 : n ≤ 16410
  · exact blk 32693 16349 16410 127 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16410
  by_cases h16465 : n ≤ 16465
  · exact blk 32803 16411 16465 127 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16465
  by_cases h16522 : n ≤ 16522
  · exact blk 32917 16466 16522 127 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16522
  by_cases h16582 : n ≤ 16582
  · exact blk 33037 16523 16582 127 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16582
  by_cases h16644 : n ≤ 16644
  · exact blk 33161 16583 16644 127 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16644
  by_cases h16709 : n ≤ 16709
  · exact blk 33289 16645 16709 129 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16709
  by_cases h16771 : n ≤ 16771
  · exact blk 33413 16710 16771 129 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16771
  by_cases h16831 : n ≤ 16831
  · exact blk 33533 16772 16831 129 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16831
  by_cases h16888 : n ≤ 16888
  · exact blk 33647 16832 16888 129 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16888
  by_cases h16951 : n ≤ 16951
  · exact blk 33773 16889 16951 129 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h16951
  by_cases h17011 : n ≤ 17011
  · exact blk 33893 16952 17011 129 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17011
  by_cases h17074 : n ≤ 17074
  · exact blk 34019 17012 17074 129 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17074
  by_cases h17138 : n ≤ 17138
  · exact blk 34147 17075 17138 129 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17138
  by_cases h17201 : n ≤ 17201
  · exact blk 34273 17139 17201 129 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17201
  by_cases h17267 : n ≤ 17267
  · exact blk 34403 17202 17267 131 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17267
  by_cases h17325 : n ≤ 17325
  · exact blk 34519 17268 17325 131 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17325
  by_cases h17391 : n ≤ 17391
  · exact blk 34651 17326 17391 131 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17391
  by_cases h17456 : n ≤ 17456
  · exact blk 34781 17392 17456 131 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17456
  by_cases h17522 : n ≤ 17522
  · exact blk 34913 17457 17522 131 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17522
  by_cases h17579 : n ≤ 17579
  · exact blk 35027 17523 17579 131 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17579
  by_cases h17645 : n ≤ 17645
  · exact blk 35159 17580 17645 131 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17645
  by_cases h17711 : n ≤ 17711
  · exact blk 35291 17646 17711 131 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17711
  by_cases h17778 : n ≤ 17778
  · exact blk 35423 17712 17778 133 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17778
  by_cases h17838 : n ≤ 17838
  · exact blk 35543 17779 17838 133 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17838
  by_cases h17905 : n ≤ 17905
  · exact blk 35677 17839 17905 133 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17905
  by_cases h17971 : n ≤ 17971
  · exact blk 35809 17906 17971 133 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h17971
  by_cases h18033 : n ≤ 18033
  · exact blk 35933 17972 18033 133 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18033
  by_cases h18100 : n ≤ 18100
  · exact blk 36067 18034 18100 133 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18100
  by_cases h18162 : n ≤ 18162
  · exact blk 36191 18101 18162 133 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18162
  by_cases h18226 : n ≤ 18226
  · exact blk 36319 18163 18226 133 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18226
  by_cases h18293 : n ≤ 18293
  · exact blk 36451 18227 18293 135 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18293
  by_cases h18361 : n ≤ 18361
  · exact blk 36587 18294 18361 135 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18361
  by_cases h18428 : n ≤ 18428
  · exact blk 36721 18362 18428 135 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18428
  by_cases h18496 : n ≤ 18496
  · exact blk 36857 18429 18496 135 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18496
  by_cases h18557 : n ≤ 18557
  · exact blk 36979 18497 18557 135 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18557
  by_cases h18616 : n ≤ 18616
  · exact blk 37097 18558 18616 135 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18616
  by_cases h18679 : n ≤ 18679
  · exact blk 37223 18617 18679 135 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18679
  by_cases h18746 : n ≤ 18746
  · exact blk 37357 18680 18746 135 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18746
  by_cases h18814 : n ≤ 18814
  · exact blk 37493 18747 18814 135 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18814
  by_cases h18878 : n ≤ 18878
  · exact blk 37619 18815 18878 137 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18878
  by_cases h18942 : n ≤ 18942
  · exact blk 37747 18879 18942 137 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h18942
  by_cases h19008 : n ≤ 19008
  · exact blk 37879 18943 19008 137 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19008
  by_cases h19074 : n ≤ 19074
  · exact blk 38011 19009 19074 137 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19074
  by_cases h19143 : n ≤ 19143
  · exact blk 38149 19075 19143 137 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19143
  by_cases h19212 : n ≤ 19212
  · exact blk 38287 19144 19212 137 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19212
  by_cases h19265 : n ≤ 19265
  · exact blk 38393 19213 19265 137 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19265
  by_cases h19319 : n ≤ 19319
  · exact blk 38501 19266 19319 137 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19319
  by_cases h19388 : n ≤ 19388
  · exact blk 38639 19320 19388 137 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19388
  omega
