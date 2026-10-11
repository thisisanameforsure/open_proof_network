  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h80395 : n ≤ 80395
  · exact blk 160507 80269 80395 283 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h80395
  by_cases h80536 : n ≤ 80536
  · exact blk 160789 80396 80536 283 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h80536
  by_cases h80677 : n ≤ 80677
  · exact blk 161071 80537 80677 283 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h80677
  by_cases h80812 : n ≤ 80812
  · exact blk 161341 80678 80812 283 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h80812
  by_cases h80947 : n ≤ 80947
  · exact blk 161611 80813 80947 283 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h80947
  by_cases h81082 : n ≤ 81082
  · exact blk 161881 80948 81082 283 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h81082
  by_cases h81213 : n ≤ 81213
  · exact blk 162143 81083 81213 283 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h81213
  by_cases h81351 : n ≤ 81351
  · exact blk 162419 81214 81351 283 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h81351
  by_cases h81494 : n ≤ 81494
  · exact blk 162703 81352 81494 285 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h81494
  by_cases h81637 : n ≤ 81637
  · exact blk 162989 81495 81637 285 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h81637
  by_cases h81772 : n ≤ 81772
  · exact blk 163259 81638 81772 285 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h81772
  by_cases h81914 : n ≤ 81914
  · exact blk 163543 81773 81914 285 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h81914
  by_cases h82052 : n ≤ 82052
  · exact blk 163819 81915 82052 285 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h82052
  by_cases h82189 : n ≤ 82189
  · exact blk 164093 82053 82189 285 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h82189
  by_cases h82331 : n ≤ 82331
  · exact blk 164377 82190 82331 285 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h82331
  by_cases h82474 : n ≤ 82474
  · exact blk 164663 82332 82474 285 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h82474
  by_cases h82599 : n ≤ 82599
  · exact blk 164911 82475 82599 287 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h82599
  by_cases h82734 : n ≤ 82734
  · exact blk 165181 82600 82734 287 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h82734
  by_cases h82878 : n ≤ 82878
  · exact blk 165469 82735 82878 287 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h82878
  by_cases h83018 : n ≤ 83018
  · exact blk 165749 82879 83018 287 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h83018
  by_cases h83159 : n ≤ 83159
  · exact blk 166031 83019 83159 287 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h83159
  by_cases h83303 : n ≤ 83303
  · exact blk 166319 83160 83303 287 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h83303
  by_cases h83445 : n ≤ 83445
  · exact blk 166603 83304 83445 287 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h83445
  by_cases h83579 : n ≤ 83579
  · exact blk 166871 83446 83579 287 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h83579
  by_cases h83724 : n ≤ 83724
  · exact blk 167159 83580 83724 289 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h83724
  by_cases h83869 : n ≤ 83869
  · exact blk 167449 83725 83869 289 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h83869
  by_cases h84009 : n ≤ 84009
  · exact blk 167729 83870 84009 289 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h84009
  by_cases h84151 : n ≤ 84151
  · exact blk 168013 84010 84151 289 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h84151
  by_cases h84291 : n ≤ 84291
  · exact blk 168293 84152 84291 289 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h84291
  by_cases h84424 : n ≤ 84424
  · exact blk 168559 84292 84424 289 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h84424
  by_cases h84546 : n ≤ 84546
  · exact blk 168803 84425 84546 289 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h84546
  by_cases h84691 : n ≤ 84691
  · exact blk 169093 84547 84691 289 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h84691
  by_cases h84832 : n ≤ 84832
  · exact blk 169373 84692 84832 291 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h84832
  by_cases h84976 : n ≤ 84976
  · exact blk 169661 84833 84976 291 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h84976
  by_cases h85121 : n ≤ 85121
  · exact blk 169951 84977 85121 291 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h85121
  by_cases h85267 : n ≤ 85267
  · exact blk 170243 85122 85267 291 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h85267
  by_cases h85400 : n ≤ 85400
  · exact blk 170509 85268 85400 291 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h85400
  by_cases h85546 : n ≤ 85546
  · exact blk 170801 85401 85546 291 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h85546
  by_cases h85691 : n ≤ 85691
  · exact blk 171091 85547 85691 291 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h85691
  by_cases h85837 : n ≤ 85837
  · exact blk 171383 85692 85837 291 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h85837
  by_cases h85982 : n ≤ 85982
  · exact blk 171673 85838 85982 291 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h85982
  by_cases h86120 : n ≤ 86120
  · exact blk 171947 85983 86120 293 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h86120
  by_cases h86258 : n ≤ 86258
  · exact blk 172223 86121 86258 293 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h86258
  by_cases h86405 : n ≤ 86405
  · exact blk 172517 86259 86405 293 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h86405
  by_cases h86550 : n ≤ 86550
  · exact blk 172807 86406 86550 293 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h86550
  by_cases h86696 : n ≤ 86696
  · exact blk 173099 86551 86696 293 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h86696
  by_cases h86826 : n ≤ 86826
  · exact blk 173359 86697 86826 293 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h86826
  by_cases h86972 : n ≤ 86972
  · exact blk 173651 86827 86972 293 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h86972
  by_cases h87113 : n ≤ 87113
  · exact blk 173933 86973 87113 293 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h87113
  by_cases h87258 : n ≤ 87258
  · exact blk 174221 87114 87258 295 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h87258
  by_cases h87393 : n ≤ 87393
  · exact blk 174491 87259 87393 295 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h87393
  by_cases h87534 : n ≤ 87534
  · exact blk 174773 87394 87534 295 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h87534
  by_cases h87682 : n ≤ 87682
  · exact blk 175069 87535 87682 295 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h87682
  by_cases h87828 : n ≤ 87828
  · exact blk 175361 87683 87828 295 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h87828
  by_cases h87972 : n ≤ 87972
  · exact blk 175649 87829 87972 295 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h87972
  by_cases h88117 : n ≤ 88117
  · exact blk 175939 87973 88117 295 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h88117
  by_cases h88261 : n ≤ 88261
  · exact blk 176227 88118 88261 295 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h88261
  by_cases h88409 : n ≤ 88409
  · exact blk 176521 88262 88409 297 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h88409
  by_cases h88558 : n ≤ 88558
  · exact blk 176819 88410 88558 297 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h88558
  by_cases h88705 : n ≤ 88705
  · exact blk 177113 88559 88705 297 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h88705
  by_cases h88853 : n ≤ 88853
  · exact blk 177409 88706 88853 297 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h88853
  by_cases h88994 : n ≤ 88994
  · exact blk 177691 88854 88994 297 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h88994
  by_cases h89138 : n ≤ 89138
  · exact blk 177979 88995 89138 297 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h89138
  by_cases h89279 : n ≤ 89279
  · exact blk 178261 89139 89279 297 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h89279
  by_cases h89428 : n ≤ 89428
  · exact blk 178559 89280 89428 297 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h89428
  by_cases h89576 : n ≤ 89576
  · exact blk 178853 89429 89576 299 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h89576
  by_cases h89721 : n ≤ 89721
  · exact blk 179143 89577 89721 299 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h89721
  by_cases h89870 : n ≤ 89870
  · exact blk 179441 89722 89870 299 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h89870
  by_cases h90018 : n ≤ 90018
  · exact blk 179737 89871 90018 299 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h90018
  by_cases h90161 : n ≤ 90161
  · exact blk 180023 90019 90161 299 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h90161
  by_cases h90308 : n ≤ 90308
  · exact blk 180317 90162 90308 299 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h90308
  by_cases h90458 : n ≤ 90458
  · exact blk 180617 90309 90458 299 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h90458
  by_cases h90603 : n ≤ 90603
  · exact blk 180907 90459 90603 299 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h90603
  by_cases h90751 : n ≤ 90751
  · exact blk 181201 90604 90751 301 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h90751
  by_cases h90901 : n ≤ 90901
  · exact blk 181501 90752 90901 301 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h90901
  by_cases h91045 : n ≤ 91045
  · exact blk 181789 90902 91045 301 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h91045
  by_cases h91195 : n ≤ 91195
  · exact blk 182089 91046 91195 301 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h91195
  by_cases h91345 : n ≤ 91345
  · exact blk 182389 91196 91345 301 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h91345
  by_cases h91494 : n ≤ 91494
  · exact blk 182687 91346 91494 301 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h91494
  by_cases h91641 : n ≤ 91641
  · exact blk 182981 91495 91641 301 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h91641
  by_cases h91792 : n ≤ 91792
  · exact blk 183283 91642 91792 301 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h91792
  by_cases h91941 : n ≤ 91941
  · exact blk 183581 91793 91941 301 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h91941
  by_cases h92092 : n ≤ 92092
  · exact blk 183881 91942 92092 303 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h92092
  by_cases h92242 : n ≤ 92242
  · exact blk 184181 92093 92242 303 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h92242
  by_cases h92390 : n ≤ 92390
  · exact blk 184477 92243 92390 303 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h92390
  by_cases h92540 : n ≤ 92540
  · exact blk 184777 92391 92540 303 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h92540
  by_cases h92690 : n ≤ 92690
  · exact blk 185077 92541 92690 303 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h92690
  by_cases h92837 : n ≤ 92837
  · exact blk 185371 92691 92837 303 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h92837
  by_cases h92977 : n ≤ 92977
  · exact blk 185651 92838 92977 303 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h92977
  by_cases h93127 : n ≤ 93127
  · exact blk 185951 92978 93127 303 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h93127
  by_cases h93279 : n ≤ 93279
  · exact blk 186253 93128 93279 305 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h93279
  by_cases h93428 : n ≤ 93428
  · exact blk 186551 93280 93428 305 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h93428
  by_cases h93573 : n ≤ 93573
  · exact blk 186841 93429 93573 305 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h93573
  by_cases h93723 : n ≤ 93723
  · exact blk 187141 93574 93723 305 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h93723
  by_cases h93873 : n ≤ 93873
  · exact blk 187441 93724 93873 305 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h93873
  by_cases h94013 : n ≤ 94013
  · exact blk 187721 93874 94013 305 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h94013
  by_cases h94163 : n ≤ 94163
  · exact blk 188021 94014 94163 305 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h94163
  by_cases h94314 : n ≤ 94314
  · exact blk 188323 94164 94314 305 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h94314
  by_cases h94464 : n ≤ 94464
  · exact blk 188621 94315 94464 307 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h94464
  by_cases h94617 : n ≤ 94617
  · exact blk 188927 94465 94617 307 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h94617
  omega
