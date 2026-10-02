  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h26619 : n ≤ 26619
  · exact blk 53077 26541 26619 161 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26619
  by_cases h26701 : n ≤ 26701
  · exact blk 53239 26620 26701 163 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26701
  by_cases h26782 : n ≤ 26782
  · exact blk 53401 26702 26782 163 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26782
  by_cases h26857 : n ≤ 26857
  · exact blk 53551 26783 26857 163 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26857
  by_cases h26931 : n ≤ 26931
  · exact blk 53699 26858 26931 163 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h26931
  by_cases h27012 : n ≤ 27012
  · exact blk 53861 26932 27012 163 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27012
  by_cases h27088 : n ≤ 27088
  · exact blk 54013 27013 27088 163 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27088
  by_cases h27165 : n ≤ 27165
  · exact blk 54167 27089 27165 163 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27165
  by_cases h27247 : n ≤ 27247
  · exact blk 54331 27166 27247 163 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27247
  by_cases h27329 : n ≤ 27329
  · exact blk 54493 27248 27329 165 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27329
  by_cases h27406 : n ≤ 27406
  · exact blk 54647 27330 27406 165 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27406
  by_cases h27482 : n ≤ 27482
  · exact blk 54799 27407 27482 165 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27482
  by_cases h27562 : n ≤ 27562
  · exact blk 54959 27483 27562 165 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27562
  by_cases h27641 : n ≤ 27641
  · exact blk 55117 27563 27641 165 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27641
  by_cases h27712 : n ≤ 27712
  · exact blk 55259 27642 27712 165 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27712
  by_cases h27788 : n ≤ 27788
  · exact blk 55411 27713 27788 165 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27788
  by_cases h27856 : n ≤ 27856
  · exact blk 55547 27789 27856 165 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27856
  by_cases h27938 : n ≤ 27938
  · exact blk 55711 27857 27938 165 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h27938
  by_cases h28019 : n ≤ 28019
  · exact blk 55871 27939 28019 167 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28019
  by_cases h28103 : n ≤ 28103
  · exact blk 56039 28020 28103 167 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28103
  by_cases h28187 : n ≤ 28187
  · exact blk 56207 28104 28187 167 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28187
  by_cases h28268 : n ≤ 28268
  · exact blk 56369 28188 28268 167 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28268
  by_cases h28350 : n ≤ 28350
  · exact blk 56533 28269 28350 167 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28350
  by_cases h28434 : n ≤ 28434
  · exact blk 56701 28351 28434 167 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28434
  by_cases h28512 : n ≤ 28512
  · exact blk 56857 28435 28512 167 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28512
  by_cases h28583 : n ≤ 28583
  · exact blk 56999 28513 28583 167 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28583
  by_cases h28666 : n ≤ 28666
  · exact blk 57163 28584 28666 169 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28666
  by_cases h28750 : n ≤ 28750
  · exact blk 57331 28667 28750 169 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28750
  by_cases h28831 : n ≤ 28831
  · exact blk 57493 28751 28831 169 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28831
  by_cases h28911 : n ≤ 28911
  · exact blk 57653 28832 28911 169 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28911
  by_cases h28989 : n ≤ 28989
  · exact blk 57809 28912 28989 169 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h28989
  by_cases h29073 : n ≤ 29073
  · exact blk 57977 28990 29073 169 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29073
  by_cases h29158 : n ≤ 29158
  · exact blk 58147 29074 29158 169 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29158
  by_cases h29241 : n ≤ 29241
  · exact blk 58313 29159 29241 169 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29241
  by_cases h29326 : n ≤ 29326
  · exact blk 58481 29242 29326 171 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29326
  by_cases h29401 : n ≤ 29401
  · exact blk 58631 29327 29401 171 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29401
  by_cases h29480 : n ≤ 29480
  · exact blk 58789 29402 29480 171 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29480
  by_cases h29557 : n ≤ 29557
  · exact blk 58943 29481 29557 171 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29557
  by_cases h29642 : n ≤ 29642
  · exact blk 59113 29558 29642 171 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29642
  by_cases h29726 : n ≤ 29726
  · exact blk 59281 29643 29726 171 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29726
  by_cases h29812 : n ≤ 29812
  · exact blk 59453 29727 29812 171 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29812
  by_cases h29896 : n ≤ 29896
  · exact blk 59621 29813 29896 171 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29896
  by_cases h29981 : n ≤ 29981
  · exact blk 59791 29897 29981 171 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h29981
  by_cases h30065 : n ≤ 30065
  · exact blk 59957 29982 30065 173 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30065
  by_cases h30150 : n ≤ 30150
  · exact blk 60127 30066 30150 173 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30150
  by_cases h30233 : n ≤ 30233
  · exact blk 60293 30151 30233 173 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30233
  by_cases h30315 : n ≤ 30315
  · exact blk 60457 30234 30315 173 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30315
  by_cases h30402 : n ≤ 30402
  · exact blk 60631 30316 30402 173 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30402
  by_cases h30483 : n ≤ 30483
  · exact blk 60793 30403 30483 173 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30483
  by_cases h30567 : n ≤ 30567
  · exact blk 60961 30484 30567 173 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30567
  by_cases h30651 : n ≤ 30651
  · exact blk 61129 30568 30651 173 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30651
  by_cases h30736 : n ≤ 30736
  · exact blk 61297 30652 30736 175 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30736
  by_cases h30823 : n ≤ 30823
  · exact blk 61471 30737 30823 175 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30823
  by_cases h30909 : n ≤ 30909
  · exact blk 61643 30824 30909 175 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30909
  by_cases h30997 : n ≤ 30997
  · exact blk 61819 30910 30997 175 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h30997
  by_cases h31083 : n ≤ 31083
  · exact blk 61991 30998 31083 175 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31083
  by_cases h31159 : n ≤ 31159
  · exact blk 62143 31084 31159 175 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31159
  by_cases h31243 : n ≤ 31243
  · exact blk 62311 31160 31243 175 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31243
  by_cases h31329 : n ≤ 31329
  · exact blk 62483 31244 31329 175 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31329
  by_cases h31418 : n ≤ 31418
  · exact blk 62659 31330 31418 177 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31418
  by_cases h31502 : n ≤ 31502
  · exact blk 62827 31419 31502 177 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31502
  by_cases h31583 : n ≤ 31583
  · exact blk 62989 31503 31583 177 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31583
  by_cases h31663 : n ≤ 31663
  · exact blk 63149 31584 31663 177 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31663
  by_cases h31747 : n ≤ 31747
  · exact blk 63317 31664 31747 177 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31747
  by_cases h31835 : n ≤ 31835
  · exact blk 63493 31748 31835 177 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31835
  by_cases h31924 : n ≤ 31924
  · exact blk 63671 31836 31924 177 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h31924
  by_cases h32009 : n ≤ 32009
  · exact blk 63841 31925 32009 177 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32009
  by_cases h32098 : n ≤ 32098
  · exact blk 64019 32010 32098 177 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32098
  by_cases h32184 : n ≤ 32184
  · exact blk 64189 32099 32184 179 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32184
  by_cases h32256 : n ≤ 32256
  · exact blk 64333 32185 32256 179 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32256
  by_cases h32346 : n ≤ 32346
  · exact blk 64513 32257 32346 179 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32346
  by_cases h32436 : n ≤ 32436
  · exact blk 64693 32347 32436 179 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32436
  by_cases h32525 : n ≤ 32525
  · exact blk 64871 32437 32525 179 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32525
  by_cases h32606 : n ≤ 32606
  · exact blk 65033 32526 32606 179 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32606
  by_cases h32696 : n ≤ 32696
  · exact blk 65213 32607 32696 179 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32696
  by_cases h32786 : n ≤ 32786
  · exact blk 65393 32697 32786 179 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32786
  by_cases h32872 : n ≤ 32872
  · exact blk 65563 32787 32872 181 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32872
  by_cases h32956 : n ≤ 32956
  · exact blk 65731 32873 32956 181 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h32956
  by_cases h33040 : n ≤ 33040
  · exact blk 65899 32957 33040 181 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33040
  by_cases h33126 : n ≤ 33126
  · exact blk 66071 33041 33126 181 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33126
  by_cases h33210 : n ≤ 33210
  · exact blk 66239 33127 33210 181 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33210
  by_cases h33297 : n ≤ 33297
  · exact blk 66413 33211 33297 181 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33297
  by_cases h33387 : n ≤ 33387
  · exact blk 66593 33298 33387 181 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33387
  by_cases h33472 : n ≤ 33472
  · exact blk 66763 33388 33472 181 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33472
  by_cases h33562 : n ≤ 33562
  · exact blk 66943 33473 33562 181 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33562
  by_cases h33652 : n ≤ 33652
  · exact blk 67121 33563 33652 183 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33652
  by_cases h33736 : n ≤ 33736
  · exact blk 67289 33653 33736 183 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33736
  by_cases h33818 : n ≤ 33818
  · exact blk 67453 33737 33818 183 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33818
  by_cases h33907 : n ≤ 33907
  · exact blk 67631 33819 33907 183 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33907
  by_cases h33995 : n ≤ 33995
  · exact blk 67807 33908 33995 183 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h33995
  by_cases h34085 : n ≤ 34085
  · exact blk 67987 33996 34085 183 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34085
  by_cases h34177 : n ≤ 34177
  · exact blk 68171 34086 34177 183 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34177
  by_cases h34267 : n ≤ 34267
  · exact blk 68351 34178 34267 183 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34267
  by_cases h34358 : n ≤ 34358
  · exact blk 68531 34268 34358 185 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34358
  by_cases h34449 : n ≤ 34449
  · exact blk 68713 34359 34449 185 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34449
  by_cases h34542 : n ≤ 34542
  · exact blk 68899 34450 34542 185 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34542
  by_cases h34629 : n ≤ 34629
  · exact blk 69073 34543 34629 185 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34629
  by_cases h34722 : n ≤ 34722
  · exact blk 69259 34630 34722 185 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34722
  by_cases h34812 : n ≤ 34812
  · exact blk 69439 34723 34812 185 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34812
  by_cases h34904 : n ≤ 34904
  · exact blk 69623 34813 34904 185 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34904
  omega
