  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h19453 : n ≤ 19453
  · exact blk 38767 19389 19453 139 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19453
  by_cases h19521 : n ≤ 19521
  · exact blk 38903 19454 19521 139 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19521
  by_cases h19591 : n ≤ 19591
  · exact blk 39043 19522 19591 139 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19591
  by_cases h19660 : n ≤ 19660
  · exact blk 39181 19592 19660 139 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19660
  by_cases h19728 : n ≤ 19728
  · exact blk 39317 19661 19728 139 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19728
  by_cases h19795 : n ≤ 19795
  · exact blk 39451 19729 19795 139 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19795
  by_cases h19860 : n ≤ 19860
  · exact blk 39581 19796 19860 139 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19860
  by_cases h19929 : n ≤ 19929
  · exact blk 39719 19861 19929 139 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19929
  by_cases h19999 : n ≤ 19999
  · exact blk 39857 19930 19999 141 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h19999
  by_cases h20065 : n ≤ 20065
  · exact blk 39989 20000 20065 141 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20065
  by_cases h20135 : n ≤ 20135
  · exact blk 40129 20066 20135 141 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20135
  by_cases h20197 : n ≤ 20197
  · exact blk 40253 20136 20197 141 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20197
  by_cases h20264 : n ≤ 20264
  · exact blk 40387 20198 20264 141 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20264
  by_cases h20335 : n ≤ 20335
  · exact blk 40529 20265 20335 141 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20335
  by_cases h20390 : n ≤ 20390
  · exact blk 40639 20336 20390 141 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20390
  by_cases h20456 : n ≤ 20456
  · exact blk 40771 20391 20456 141 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20456
  by_cases h20523 : n ≤ 20523
  · exact blk 40903 20457 20523 143 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20523
  by_cases h20595 : n ≤ 20595
  · exact blk 41047 20524 20595 143 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20595
  by_cases h20666 : n ≤ 20666
  · exact blk 41189 20596 20666 143 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20666
  by_cases h20738 : n ≤ 20738
  · exact blk 41333 20667 20738 143 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20738
  by_cases h20805 : n ≤ 20805
  · exact blk 41467 20739 20805 143 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20805
  by_cases h20877 : n ≤ 20877
  · exact blk 41611 20806 20877 143 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20877
  by_cases h20940 : n ≤ 20940
  · exact blk 41737 20878 20940 143 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h20940
  by_cases h21011 : n ≤ 21011
  · exact blk 41879 20941 21011 143 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21011
  by_cases h21083 : n ≤ 21083
  · exact blk 42023 21012 21083 143 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21083
  by_cases h21151 : n ≤ 21151
  · exact blk 42157 21084 21151 145 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21151
  by_cases h21222 : n ≤ 21222
  · exact blk 42299 21152 21222 145 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21222
  by_cases h21294 : n ≤ 21294
  · exact blk 42443 21223 21294 145 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21294
  by_cases h21367 : n ≤ 21367
  · exact blk 42589 21295 21367 145 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21367
  by_cases h21436 : n ≤ 21436
  · exact blk 42727 21368 21436 145 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21436
  by_cases h21504 : n ≤ 21504
  · exact blk 42863 21437 21504 145 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21504
  by_cases h21574 : n ≤ 21574
  · exact blk 43003 21505 21574 145 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21574
  by_cases h21639 : n ≤ 21639
  · exact blk 43133 21575 21639 145 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21639
  by_cases h21709 : n ≤ 21709
  · exact blk 43271 21640 21709 147 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21709
  by_cases h21779 : n ≤ 21779
  · exact blk 43411 21710 21779 147 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21779
  by_cases h21845 : n ≤ 21845
  · exact blk 43543 21780 21845 147 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21845
  by_cases h21919 : n ≤ 21919
  · exact blk 43691 21846 21919 147 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21919
  by_cases h21974 : n ≤ 21974
  · exact blk 43801 21920 21974 147 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h21974
  by_cases h22045 : n ≤ 22045
  · exact blk 43943 21975 22045 147 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22045
  by_cases h22118 : n ≤ 22118
  · exact blk 44089 22046 22118 147 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22118
  by_cases h22184 : n ≤ 22184
  · exact blk 44221 22119 22184 147 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22184
  by_cases h22252 : n ≤ 22252
  · exact blk 44357 22185 22252 147 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22252
  by_cases h22325 : n ≤ 22325
  · exact blk 44501 22253 22325 149 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22325
  by_cases h22400 : n ≤ 22400
  · exact blk 44651 22326 22400 149 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22400
  by_cases h22473 : n ≤ 22473
  · exact blk 44797 22401 22473 149 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22473
  by_cases h22544 : n ≤ 22544
  · exact blk 44939 22474 22544 149 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22544
  by_cases h22616 : n ≤ 22616
  · exact blk 45083 22545 22616 149 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22616
  by_cases h22691 : n ≤ 22691
  · exact blk 45233 22617 22691 149 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22691
  by_cases h22763 : n ≤ 22763
  · exact blk 45377 22692 22763 149 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22763
  by_cases h22836 : n ≤ 22836
  · exact blk 45523 22764 22836 149 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22836
  by_cases h22912 : n ≤ 22912
  · exact blk 45673 22837 22912 151 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22912
  by_cases h22987 : n ≤ 22987
  · exact blk 45823 22913 22987 151 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h22987
  by_cases h23061 : n ≤ 23061
  · exact blk 45971 22988 23061 151 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23061
  by_cases h23127 : n ≤ 23127
  · exact blk 46103 23062 23127 151 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23127
  by_cases h23194 : n ≤ 23194
  · exact blk 46237 23128 23194 151 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23194
  by_cases h23266 : n ≤ 23266
  · exact blk 46381 23195 23266 151 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23266
  by_cases h23337 : n ≤ 23337
  · exact blk 46523 23267 23337 151 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23337
  by_cases h23407 : n ≤ 23407
  · exact blk 46663 23338 23407 151 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23407
  by_cases h23481 : n ≤ 23481
  · exact blk 46811 23408 23481 151 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23481
  by_cases h23555 : n ≤ 23555
  · exact blk 46957 23482 23555 153 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23555
  by_cases h23632 : n ≤ 23632
  · exact blk 47111 23556 23632 153 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23632
  by_cases h23702 : n ≤ 23702
  · exact blk 47251 23633 23702 153 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23702
  by_cases h23771 : n ≤ 23771
  · exact blk 47389 23703 23771 153 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23771
  by_cases h23848 : n ≤ 23848
  · exact blk 47543 23772 23848 153 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23848
  by_cases h23917 : n ≤ 23917
  · exact blk 47681 23849 23917 153 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23917
  by_cases h23986 : n ≤ 23986
  · exact blk 47819 23918 23986 153 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h23986
  by_cases h24061 : n ≤ 24061
  · exact blk 47969 23987 24061 153 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24061
  by_cases h24138 : n ≤ 24138
  · exact blk 48121 24062 24138 155 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24138
  by_cases h24213 : n ≤ 24213
  · exact blk 48271 24139 24213 155 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24213
  by_cases h24284 : n ≤ 24284
  · exact blk 48413 24214 24284 155 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24284
  by_cases h24359 : n ≤ 24359
  · exact blk 48563 24285 24359 155 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24359
  by_cases h24417 : n ≤ 24417
  · exact blk 48679 24360 24417 155 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24417
  by_cases h24489 : n ≤ 24489
  · exact blk 48823 24418 24489 155 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24489
  by_cases h24564 : n ≤ 24564
  · exact blk 48973 24490 24564 155 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24564
  by_cases h24639 : n ≤ 24639
  · exact blk 49123 24565 24639 155 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24639
  by_cases h24717 : n ≤ 24717
  · exact blk 49279 24640 24717 155 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24717
  by_cases h24795 : n ≤ 24795
  · exact blk 49433 24718 24795 157 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24795
  by_cases h24858 : n ≤ 24858
  · exact blk 49559 24796 24858 157 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24858
  by_cases h24934 : n ≤ 24934
  · exact blk 49711 24859 24934 157 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h24934
  by_cases h25005 : n ≤ 25005
  · exact blk 49853 24935 25005 157 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25005
  by_cases h25078 : n ≤ 25078
  · exact blk 49999 25006 25078 157 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25078
  by_cases h25155 : n ≤ 25155
  · exact blk 50153 25079 25155 157 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25155
  by_cases h25234 : n ≤ 25234
  · exact blk 50311 25156 25234 157 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25234
  by_cases h25309 : n ≤ 25309
  · exact blk 50461 25235 25309 157 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25309
  by_cases h25379 : n ≤ 25379
  · exact blk 50599 25310 25379 159 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25379
  by_cases h25456 : n ≤ 25456
  · exact blk 50753 25380 25456 159 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25456
  by_cases h25534 : n ≤ 25534
  · exact blk 50909 25457 25534 159 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25534
  by_cases h25610 : n ≤ 25610
  · exact blk 51061 25535 25610 159 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25610
  by_cases h25688 : n ≤ 25688
  · exact blk 51217 25611 25688 159 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25688
  by_cases h25760 : n ≤ 25760
  · exact blk 51361 25689 25760 159 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25760
  by_cases h25840 : n ≤ 25840
  · exact blk 51521 25761 25840 159 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25840
  by_cases h25919 : n ≤ 25919
  · exact blk 51679 25841 25919 159 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25919
  by_cases h25999 : n ≤ 25999
  · exact blk 51839 25920 25999 159 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h25999
  by_cases h26076 : n ≤ 26076
  · exact blk 51991 26000 26076 161 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26076
  by_cases h26157 : n ≤ 26157
  · exact blk 52153 26077 26157 161 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26157
  by_cases h26237 : n ≤ 26237
  · exact blk 52313 26158 26237 161 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26237
  by_cases h26309 : n ≤ 26309
  · exact blk 52457 26238 26309 161 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26309
  by_cases h26385 : n ≤ 26385
  · exact blk 52609 26310 26385 161 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26385
  by_cases h26465 : n ≤ 26465
  · exact blk 52769 26386 26465 161 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26465
  by_cases h26540 : n ≤ 26540
  · exact blk 52919 26466 26540 161 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26540
  omega
