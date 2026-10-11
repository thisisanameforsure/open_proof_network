  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h144934 : n ≤ 144934
  · exact blk 289489 144755 144934 379 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h144934
  by_cases h145119 : n ≤ 145119
  · exact blk 289859 144935 145119 379 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h145119
  by_cases h145306 : n ≤ 145306
  · exact blk 290233 145120 145306 379 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h145306
  by_cases h145496 : n ≤ 145496
  · exact blk 290611 145307 145496 381 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h145496
  by_cases h145687 : n ≤ 145687
  · exact blk 290993 145497 145687 381 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h145687
  by_cases h145877 : n ≤ 145877
  · exact blk 291373 145688 145877 381 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h145877
  by_cases h146066 : n ≤ 146066
  · exact blk 291751 145878 146066 381 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h146066
  by_cases h146257 : n ≤ 146257
  · exact blk 292133 146067 146257 381 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h146257
  by_cases h146437 : n ≤ 146437
  · exact blk 292493 146258 146437 381 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h146437
  by_cases h146624 : n ≤ 146624
  · exact blk 292867 146438 146624 381 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h146624
  by_cases h146801 : n ≤ 146801
  · exact blk 293221 146625 146801 381 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h146801
  by_cases h146993 : n ≤ 146993
  · exact blk 293603 146802 146993 383 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h146993
  by_cases h147183 : n ≤ 147183
  · exact blk 293983 146994 147183 383 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h147183
  by_cases h147368 : n ≤ 147368
  · exact blk 294353 147184 147368 383 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h147368
  by_cases h147557 : n ≤ 147557
  · exact blk 294731 147369 147557 383 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h147557
  by_cases h147747 : n ≤ 147747
  · exact blk 295111 147558 147747 383 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h147747
  by_cases h147921 : n ≤ 147921
  · exact blk 295459 147748 147921 383 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h147921
  by_cases h148113 : n ≤ 148113
  · exact blk 295843 147922 148113 383 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h148113
  by_cases h148302 : n ≤ 148302
  · exact blk 296221 148114 148302 383 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h148302
  by_cases h148488 : n ≤ 148488
  · exact blk 296591 148303 148488 385 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h148488
  by_cases h148678 : n ≤ 148678
  · exact blk 296971 148489 148678 385 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h148678
  by_cases h148851 : n ≤ 148851
  · exact blk 297317 148679 148851 385 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h148851
  by_cases h149038 : n ≤ 149038
  · exact blk 297691 148852 149038 385 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h149038
  by_cases h149224 : n ≤ 149224
  · exact blk 298063 149039 149224 385 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h149224
  by_cases h149406 : n ≤ 149406
  · exact blk 298427 149225 149406 385 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h149406
  by_cases h149593 : n ≤ 149593
  · exact blk 298801 149407 149593 385 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h149593
  by_cases h149782 : n ≤ 149782
  · exact blk 299179 149594 149782 385 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h149782
  by_cases h149963 : n ≤ 149963
  · exact blk 299539 149783 149963 387 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h149963
  by_cases h150148 : n ≤ 150148
  · exact blk 299909 149964 150148 387 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h150148
  by_cases h150332 : n ≤ 150332
  · exact blk 300277 150149 150332 387 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h150332
  by_cases h150524 : n ≤ 150524
  · exact blk 300661 150333 150524 387 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h150524
  by_cases h150713 : n ≤ 150713
  · exact blk 301039 150525 150713 387 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h150713
  by_cases h150905 : n ≤ 150905
  · exact blk 301423 150714 150905 387 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h150905
  by_cases h151090 : n ≤ 151090
  · exact blk 301793 150906 151090 387 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h151090
  by_cases h151280 : n ≤ 151280
  · exact blk 302173 151091 151280 387 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h151280
  by_cases h151469 : n ≤ 151469
  · exact blk 302551 151281 151469 387 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h151469
  by_cases h151658 : n ≤ 151658
  · exact blk 302927 151470 151658 389 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h151658
  by_cases h151851 : n ≤ 151851
  · exact blk 303313 151659 151851 389 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h151851
  by_cases h152046 : n ≤ 152046
  · exact blk 303703 151852 152046 389 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h152046
  by_cases h152240 : n ≤ 152240
  · exact blk 304091 152047 152240 389 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h152240
  by_cases h152435 : n ≤ 152435
  · exact blk 304481 152241 152435 389 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h152435
  by_cases h152628 : n ≤ 152628
  · exact blk 304867 152436 152628 389 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h152628
  by_cases h152816 : n ≤ 152816
  · exact blk 305243 152629 152816 389 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h152816
  by_cases h153011 : n ≤ 153011
  · exact blk 305633 152817 153011 389 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h153011
  by_cases h153207 : n ≤ 153207
  · exact blk 306023 153012 153207 391 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h153207
  by_cases h153399 : n ≤ 153399
  · exact blk 306407 153208 153399 391 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h153399
  by_cases h153586 : n ≤ 153586
  · exact blk 306781 153400 153586 391 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h153586
  by_cases h153781 : n ≤ 153781
  · exact blk 307171 153587 153781 391 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h153781
  by_cases h153967 : n ≤ 153967
  · exact blk 307543 153782 153967 391 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h153967
  by_cases h154155 : n ≤ 154155
  · exact blk 307919 153968 154155 391 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h154155
  by_cases h154351 : n ≤ 154351
  · exact blk 308311 154156 154351 391 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h154351
  by_cases h154546 : n ≤ 154546
  · exact blk 308701 154352 154546 391 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h154546
  by_cases h154742 : n ≤ 154742
  · exact blk 309091 154547 154742 393 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h154742
  by_cases h154937 : n ≤ 154937
  · exact blk 309481 154743 154937 393 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h154937
  by_cases h155125 : n ≤ 155125
  · exact blk 309857 154938 155125 393 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h155125
  by_cases h155318 : n ≤ 155318
  · exact blk 310243 155126 155318 393 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h155318
  by_cases h155510 : n ≤ 155510
  · exact blk 310627 155319 155510 393 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h155510
  by_cases h155707 : n ≤ 155707
  · exact blk 311021 155511 155707 393 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h155707
  by_cases h155900 : n ≤ 155900
  · exact blk 311407 155708 155900 393 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h155900
  by_cases h156092 : n ≤ 156092
  · exact blk 311791 155901 156092 393 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h156092
  by_cases h156278 : n ≤ 156278
  · exact blk 312161 156093 156278 395 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h156278
  by_cases h156474 : n ≤ 156474
  · exact blk 312553 156279 156474 395 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h156474
  by_cases h156669 : n ≤ 156669
  · exact blk 312943 156475 156669 395 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h156669
  by_cases h156864 : n ≤ 156864
  · exact blk 313333 156670 156864 395 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h156864
  by_cases h157061 : n ≤ 157061
  · exact blk 313727 156865 157061 395 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h157061
  by_cases h157256 : n ≤ 157256
  · exact blk 314117 157062 157256 395 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h157256
  by_cases h157454 : n ≤ 157454
  · exact blk 314513 157257 157454 395 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h157454
  by_cases h157649 : n ≤ 157649
  · exact blk 314903 157455 157649 395 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h157649
  by_cases h157839 : n ≤ 157839
  · exact blk 315281 157650 157839 397 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h157839
  by_cases h158037 : n ≤ 158037
  · exact blk 315677 157840 158037 397 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h158037
  by_cases h158235 : n ≤ 158235
  · exact blk 316073 158038 158235 397 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h158235
  by_cases h158434 : n ≤ 158434
  · exact blk 316471 158236 158434 397 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h158434
  by_cases h158629 : n ≤ 158629
  · exact blk 316861 158435 158629 397 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h158629
  by_cases h158827 : n ≤ 158827
  · exact blk 317257 158630 158827 397 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h158827
  by_cases h159024 : n ≤ 159024
  · exact blk 317651 158828 159024 397 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h159024
  by_cases h159210 : n ≤ 159210
  · exact blk 318023 159025 159210 397 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h159210
  by_cases h159409 : n ≤ 159409
  · exact blk 318419 159211 159409 399 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h159409
  by_cases h159608 : n ≤ 159608
  · exact blk 318817 159410 159608 399 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h159608
  by_cases h159805 : n ≤ 159805
  · exact blk 319211 159609 159805 399 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h159805
  by_cases h160003 : n ≤ 160003
  · exact blk 319607 159806 160003 399 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h160003
  by_cases h160196 : n ≤ 160196
  · exact blk 319993 160004 160196 399 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h160196
  by_cases h160394 : n ≤ 160394
  · exact blk 320389 160197 160394 399 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h160394
  by_cases h160583 : n ≤ 160583
  · exact blk 320767 160395 160583 399 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h160583
  by_cases h160781 : n ≤ 160781
  · exact blk 321163 160584 160781 399 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h160781
  by_cases h160976 : n ≤ 160976
  · exact blk 321553 160782 160976 399 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h160976
  by_cases h161175 : n ≤ 161175
  · exact blk 321949 160977 161175 401 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h161175
  by_cases h161376 : n ≤ 161376
  · exact blk 322351 161176 161376 401 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h161376
  by_cases h161574 : n ≤ 161574
  · exact blk 322747 161377 161574 401 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h161574
  by_cases h161775 : n ≤ 161775
  · exact blk 323149 161575 161775 401 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h161775
  by_cases h161975 : n ≤ 161975
  · exact blk 323549 161776 161975 401 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h161975
  by_cases h162176 : n ≤ 162176
  · exact blk 323951 161976 162176 401 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h162176
  by_cases h162371 : n ≤ 162371
  · exact blk 324341 162177 162371 401 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h162371
  by_cases h162572 : n ≤ 162572
  · exact blk 324743 162372 162572 401 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h162572
  by_cases h162768 : n ≤ 162768
  · exact blk 325133 162573 162768 403 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h162768
  by_cases h162970 : n ≤ 162970
  · exact blk 325537 162769 162970 403 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h162970
  by_cases h163171 : n ≤ 163171
  · exact blk 325939 162971 163171 403 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h163171
  by_cases h163363 : n ≤ 163363
  · exact blk 326323 163172 163363 403 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h163363
  by_cases h163555 : n ≤ 163555
  · exact blk 326707 163364 163555 403 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h163555
  by_cases h163741 : n ≤ 163741
  · exact blk 327079 163556 163741 403 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h163741
  by_cases h163941 : n ≤ 163941
  · exact blk 327479 163742 163941 403 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h163941
  omega
