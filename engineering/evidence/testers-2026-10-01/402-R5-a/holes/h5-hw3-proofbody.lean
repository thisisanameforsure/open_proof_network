  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h4879 : n ≤ 4879
  · exact blk 9689 4845 4879 69 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4879
  by_cases h4909 : n ≤ 4909
  · exact blk 9749 4880 4909 69 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4909
  by_cases h4943 : n ≤ 4943
  · exact blk 9817 4910 4943 69 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4943
  by_cases h4978 : n ≤ 4978
  · exact blk 9887 4944 4978 69 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h4978
  by_cases h5009 : n ≤ 5009
  · exact blk 9949 4979 5009 69 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5009
  by_cases h5039 : n ≤ 5039
  · exact blk 10009 5010 5039 69 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5039
  by_cases h5074 : n ≤ 5074
  · exact blk 10079 5040 5074 69 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5074
  by_cases h5106 : n ≤ 5106
  · exact blk 10141 5075 5106 71 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5106
  by_cases h5141 : n ≤ 5141
  · exact blk 10211 5107 5141 71 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5141
  by_cases h5172 : n ≤ 5172
  · exact blk 10273 5142 5172 71 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5172
  by_cases h5207 : n ≤ 5207
  · exact blk 10343 5173 5207 71 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5207
  by_cases h5235 : n ≤ 5235
  · exact blk 10399 5208 5235 71 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5235
  by_cases h5267 : n ≤ 5267
  · exact blk 10463 5236 5267 71 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5267
  by_cases h5301 : n ≤ 5301
  · exact blk 10531 5268 5301 71 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5301
  by_cases h5336 : n ≤ 5336
  · exact blk 10601 5302 5336 71 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5336
  by_cases h5370 : n ≤ 5370
  · exact blk 10667 5337 5370 73 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5370
  by_cases h5406 : n ≤ 5406
  · exact blk 10739 5371 5406 73 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5406
  by_cases h5436 : n ≤ 5436
  · exact blk 10799 5407 5436 73 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5436
  by_cases h5470 : n ≤ 5470
  · exact blk 10867 5437 5470 73 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5470
  by_cases h5506 : n ≤ 5506
  · exact blk 10939 5471 5506 73 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5506
  by_cases h5538 : n ≤ 5538
  · exact blk 11003 5507 5538 73 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5538
  by_cases h5572 : n ≤ 5572
  · exact blk 11071 5539 5572 73 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5572
  by_cases h5602 : n ≤ 5602
  · exact blk 11131 5573 5602 73 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5602
  by_cases h5635 : n ≤ 5635
  · exact blk 11197 5603 5635 73 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5635
  by_cases h5668 : n ≤ 5668
  · exact blk 11261 5636 5668 75 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5668
  by_cases h5702 : n ≤ 5702
  · exact blk 11329 5669 5702 75 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5702
  by_cases h5737 : n ≤ 5737
  · exact blk 11399 5703 5737 75 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5737
  by_cases h5773 : n ≤ 5773
  · exact blk 11471 5738 5773 75 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5773
  by_cases h5801 : n ≤ 5801
  · exact blk 11527 5774 5801 75 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5801
  by_cases h5836 : n ≤ 5836
  · exact blk 11597 5802 5836 75 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5836
  by_cases h5866 : n ≤ 5866
  · exact blk 11657 5837 5866 75 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5866
  by_cases h5903 : n ≤ 5903
  · exact blk 11731 5867 5903 75 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5903
  by_cases h5941 : n ≤ 5941
  · exact blk 11807 5904 5941 75 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5941
  by_cases h5972 : n ≤ 5972
  · exact blk 11867 5942 5972 77 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h5972
  by_cases h6009 : n ≤ 6009
  · exact blk 11941 5973 6009 77 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6009
  by_cases h6044 : n ≤ 6044
  · exact blk 12011 6010 6044 77 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6044
  by_cases h6075 : n ≤ 6075
  · exact blk 12073 6045 6075 77 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6075
  by_cases h6113 : n ≤ 6113
  · exact blk 12149 6076 6113 77 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6113
  by_cases h6152 : n ≤ 6152
  · exact blk 12227 6114 6152 77 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6152
  by_cases h6189 : n ≤ 6189
  · exact blk 12301 6153 6189 77 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6189
  by_cases h6228 : n ≤ 6228
  · exact blk 12379 6190 6228 77 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6228
  by_cases h6267 : n ≤ 6267
  · exact blk 12457 6229 6267 77 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6267
  by_cases h6303 : n ≤ 6303
  · exact blk 12527 6268 6303 79 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6303
  by_cases h6340 : n ≤ 6340
  · exact blk 12601 6304 6340 79 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6340
  by_cases h6375 : n ≤ 6375
  · exact blk 12671 6341 6375 79 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6375
  by_cases h6411 : n ≤ 6411
  · exact blk 12743 6376 6411 79 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6411
  by_cases h6451 : n ≤ 6451
  · exact blk 12823 6412 6451 79 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6451
  by_cases h6489 : n ≤ 6489
  · exact blk 12899 6452 6489 79 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6489
  by_cases h6529 : n ≤ 6529
  · exact blk 12979 6490 6529 79 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6529
  by_cases h6564 : n ≤ 6564
  · exact blk 13049 6530 6564 79 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6564
  by_cases h6604 : n ≤ 6604
  · exact blk 13127 6565 6604 81 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6604
  by_cases h6634 : n ≤ 6634
  · exact blk 13187 6605 6634 81 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6634
  by_cases h6674 : n ≤ 6674
  · exact blk 13267 6635 6674 81 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6674
  by_cases h6710 : n ≤ 6710
  · exact blk 13339 6675 6710 81 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6710
  by_cases h6751 : n ≤ 6751
  · exact blk 13421 6711 6751 81 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6751
  by_cases h6790 : n ≤ 6790
  · exact blk 13499 6752 6790 81 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6790
  by_cases h6829 : n ≤ 6829
  · exact blk 13577 6791 6829 81 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6829
  by_cases h6865 : n ≤ 6865
  · exact blk 13649 6830 6865 81 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6865
  by_cases h6905 : n ≤ 6905
  · exact blk 13729 6866 6905 81 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6905
  by_cases h6945 : n ≤ 6945
  · exact blk 13807 6906 6945 83 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6945
  by_cases h6983 : n ≤ 6983
  · exact blk 13883 6946 6983 83 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h6983
  by_cases h7025 : n ≤ 7025
  · exact blk 13967 6984 7025 83 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7025
  by_cases h7067 : n ≤ 7067
  · exact blk 14051 7026 7067 83 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7067
  by_cases h7095 : n ≤ 7095
  · exact blk 14107 7068 7095 83 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7095
  by_cases h7130 : n ≤ 7130
  · exact blk 14177 7096 7130 83 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7130
  by_cases h7167 : n ≤ 7167
  · exact blk 14251 7131 7167 83 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7167
  by_cases h7205 : n ≤ 7205
  · exact blk 14327 7168 7205 83 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7205
  by_cases h7247 : n ≤ 7247
  · exact blk 14411 7206 7247 83 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7247
  by_cases h7287 : n ≤ 7287
  · exact blk 14489 7248 7287 85 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7287
  by_cases h7324 : n ≤ 7324
  · exact blk 14563 7288 7324 85 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7324
  by_cases h7362 : n ≤ 7362
  · exact blk 14639 7325 7362 85 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7362
  by_cases h7404 : n ≤ 7404
  · exact blk 14723 7363 7404 85 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7404
  by_cases h7441 : n ≤ 7441
  · exact blk 14797 7405 7441 85 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7441
  by_cases h7482 : n ≤ 7482
  · exact blk 14879 7442 7482 85 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7482
  by_cases h7521 : n ≤ 7521
  · exact blk 14957 7483 7521 85 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7521
  by_cases h7558 : n ≤ 7558
  · exact blk 15031 7522 7558 85 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7558
  by_cases h7596 : n ≤ 7596
  · exact blk 15107 7559 7596 85 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7596
  by_cases h7640 : n ≤ 7640
  · exact blk 15193 7597 7640 87 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7640
  by_cases h7682 : n ≤ 7682
  · exact blk 15277 7641 7682 87 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7682
  by_cases h7724 : n ≤ 7724
  · exact blk 15361 7683 7724 87 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7724
  by_cases h7765 : n ≤ 7765
  · exact blk 15443 7725 7765 87 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7765
  by_cases h7807 : n ≤ 7807
  · exact blk 15527 7766 7807 87 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7807
  by_cases h7847 : n ≤ 7847
  · exact blk 15607 7808 7847 87 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7847
  by_cases h7885 : n ≤ 7885
  · exact blk 15683 7848 7885 87 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7885
  by_cases h7927 : n ≤ 7927
  · exact blk 15767 7886 7927 87 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7927
  by_cases h7956 : n ≤ 7956
  · exact blk 15823 7928 7956 89 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h7956
  by_cases h8001 : n ≤ 8001
  · exact blk 15913 7957 8001 89 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8001
  by_cases h8045 : n ≤ 8045
  · exact blk 16001 8002 8045 89 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8045
  by_cases h8090 : n ≤ 8090
  · exact blk 16091 8046 8090 89 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8090
  by_cases h8115 : n ≤ 8115
  · exact blk 16141 8091 8115 89 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8115
  by_cases h8160 : n ≤ 8160
  · exact blk 16231 8116 8160 89 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8160
  by_cases h8204 : n ≤ 8204
  · exact blk 16319 8161 8204 89 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8204
  by_cases h8235 : n ≤ 8235
  · exact blk 16381 8205 8235 89 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8235
  by_cases h8271 : n ≤ 8271
  · exact blk 16453 8236 8271 89 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8271
  by_cases h8309 : n ≤ 8309
  · exact blk 16529 8272 8309 89 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8309
  by_cases h8355 : n ≤ 8355
  · exact blk 16619 8310 8355 91 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8355
  by_cases h8397 : n ≤ 8397
  · exact blk 16703 8356 8397 91 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8397
  by_cases h8439 : n ≤ 8439
  · exact blk 16787 8398 8439 91 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8439
  by_cases h8485 : n ≤ 8485
  · exact blk 16879 8440 8485 91 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8485
  by_cases h8527 : n ≤ 8527
  · exact blk 16963 8486 8527 91 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h8527
  omega
