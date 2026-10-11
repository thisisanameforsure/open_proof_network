import Mathlib

/-- 402-R4-c. Window primes for 34905 ≤ n ≤ 44504: 100 primality certificates by `norm_num`, no `native_decide`. -/
theorem r4c_window_34905_44504 : ∀ n : ℕ, 34905 ≤ n → n ≤ 44504 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h34997 : n ≤ 34997
  · exact blk 69809 34905 34997 185 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h34997
  by_cases h35089 : n ≤ 35089
  · exact blk 69991 34998 35089 187 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h35089
  by_cases h35182 : n ≤ 35182
  · exact blk 70177 35090 35182 187 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h35182
  by_cases h35269 : n ≤ 35269
  · exact blk 70351 35183 35269 187 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h35269
  by_cases h35362 : n ≤ 35362
  · exact blk 70537 35270 35362 187 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h35362
  by_cases h35452 : n ≤ 35452
  · exact blk 70717 35363 35452 187 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h35452
  by_cases h35544 : n ≤ 35544
  · exact blk 70901 35453 35544 187 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h35544
  by_cases h35638 : n ≤ 35638
  · exact blk 71089 35545 35638 187 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h35638
  by_cases h35725 : n ≤ 35725
  · exact blk 71263 35639 35725 187 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h35725
  by_cases h35816 : n ≤ 35816
  · exact blk 71443 35726 35816 189 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h35816
  by_cases h35911 : n ≤ 35911
  · exact blk 71633 35817 35911 189 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h35911
  by_cases h36005 : n ≤ 36005
  · exact blk 71821 35912 36005 189 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36005
  by_cases h36094 : n ≤ 36094
  · exact blk 71999 36006 36094 189 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36094
  by_cases h36181 : n ≤ 36181
  · exact blk 72173 36095 36181 189 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36181
  by_cases h36271 : n ≤ 36271
  · exact blk 72353 36182 36271 189 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36271
  by_cases h36361 : n ≤ 36361
  · exact blk 72533 36272 36361 189 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36361
  by_cases h36454 : n ≤ 36454
  · exact blk 72719 36362 36454 189 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36454
  by_cases h36548 : n ≤ 36548
  · exact blk 72907 36455 36548 189 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36548
  by_cases h36641 : n ≤ 36641
  · exact blk 73091 36549 36641 191 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36641
  by_cases h36734 : n ≤ 36734
  · exact blk 73277 36642 36734 191 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36734
  by_cases h36825 : n ≤ 36825
  · exact blk 73459 36735 36825 191 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36825
  by_cases h36921 : n ≤ 36921
  · exact blk 73651 36826 36921 191 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h36921
  by_cases h37007 : n ≤ 37007
  · exact blk 73823 36922 37007 191 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37007
  by_cases h37095 : n ≤ 37095
  · exact blk 73999 37008 37095 191 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37095
  by_cases h37190 : n ≤ 37190
  · exact blk 74189 37096 37190 191 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37190
  by_cases h37286 : n ≤ 37286
  · exact blk 74381 37191 37286 191 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37286
  by_cases h37383 : n ≤ 37383
  · exact blk 74573 37287 37383 193 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37383
  by_cases h37477 : n ≤ 37477
  · exact blk 74761 37384 37477 193 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37477
  by_cases h37567 : n ≤ 37567
  · exact blk 74941 37478 37567 193 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37567
  by_cases h37663 : n ≤ 37663
  · exact blk 75133 37568 37663 193 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37663
  by_cases h37758 : n ≤ 37758
  · exact blk 75323 37664 37758 193 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37758
  by_cases h37852 : n ≤ 37852
  · exact blk 75511 37759 37852 193 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37852
  by_cases h37948 : n ≤ 37948
  · exact blk 75703 37853 37948 193 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h37948
  by_cases h38038 : n ≤ 38038
  · exact blk 75883 37949 38038 193 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38038
  by_cases h38117 : n ≤ 38117
  · exact blk 76039 38039 38117 195 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38117
  by_cases h38213 : n ≤ 38213
  · exact blk 76231 38118 38213 195 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38213
  by_cases h38309 : n ≤ 38309
  · exact blk 76423 38214 38309 195 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38309
  by_cases h38401 : n ≤ 38401
  · exact blk 76607 38310 38401 195 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38401
  by_cases h38498 : n ≤ 38498
  · exact blk 76801 38402 38498 195 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38498
  by_cases h38593 : n ≤ 38593
  · exact blk 76991 38499 38593 195 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38593
  by_cases h38683 : n ≤ 38683
  · exact blk 77171 38594 38683 195 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38683
  by_cases h38777 : n ≤ 38777
  · exact blk 77359 38684 38777 195 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38777
  by_cases h38873 : n ≤ 38873
  · exact blk 77551 38778 38873 195 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38873
  by_cases h38972 : n ≤ 38972
  · exact blk 77747 38874 38972 197 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h38972
  by_cases h39065 : n ≤ 39065
  · exact blk 77933 38973 39065 197 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39065
  by_cases h39159 : n ≤ 39159
  · exact blk 78121 39066 39159 197 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39159
  by_cases h39257 : n ≤ 39257
  · exact blk 78317 39160 39257 197 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39257
  by_cases h39354 : n ≤ 39354
  · exact blk 78511 39258 39354 197 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39354
  by_cases h39452 : n ≤ 39452
  · exact blk 78707 39355 39452 197 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39452
  by_cases h39549 : n ≤ 39549
  · exact blk 78901 39453 39549 197 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39549
  by_cases h39642 : n ≤ 39642
  · exact blk 79087 39550 39642 197 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39642
  by_cases h39741 : n ≤ 39741
  · exact blk 79283 39643 39741 199 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39741
  by_cases h39840 : n ≤ 39840
  · exact blk 79481 39742 39840 199 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39840
  by_cases h39934 : n ≤ 39934
  · exact blk 79669 39841 39934 199 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h39934
  by_cases h40033 : n ≤ 40033
  · exact blk 79867 39935 40033 199 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40033
  by_cases h40125 : n ≤ 40125
  · exact blk 80051 40034 40125 199 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40125
  by_cases h40225 : n ≤ 40225
  · exact blk 80251 40126 40225 199 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40225
  by_cases h40324 : n ≤ 40324
  · exact blk 80449 40226 40324 199 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40324
  by_cases h40414 : n ≤ 40414
  · exact blk 80629 40325 40414 199 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40414
  by_cases h40510 : n ≤ 40510
  · exact blk 80819 40415 40510 201 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40510
  by_cases h40610 : n ≤ 40610
  · exact blk 81019 40511 40610 201 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40610
  by_cases h40702 : n ≤ 40702
  · exact blk 81203 40611 40702 201 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40702
  by_cases h40801 : n ≤ 40801
  · exact blk 81401 40703 40801 201 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40801
  by_cases h40885 : n ≤ 40885
  · exact blk 81569 40802 40885 201 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40885
  by_cases h40985 : n ≤ 40985
  · exact blk 81769 40886 40985 201 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h40985
  by_cases h41086 : n ≤ 41086
  · exact blk 81971 40986 41086 201 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h41086
  by_cases h41186 : n ≤ 41186
  · exact blk 82171 41087 41186 201 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h41186
  by_cases h41287 : n ≤ 41287
  · exact blk 82373 41187 41287 201 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h41287
  by_cases h41387 : n ≤ 41387
  · exact blk 82571 41288 41387 203 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h41387
  by_cases h41483 : n ≤ 41483
  · exact blk 82763 41388 41483 203 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h41483
  by_cases h41583 : n ≤ 41583
  · exact blk 82963 41484 41583 203 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h41583
  by_cases h41670 : n ≤ 41670
  · exact blk 83137 41584 41670 203 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h41670
  by_cases h41772 : n ≤ 41772
  · exact blk 83341 41671 41772 203 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h41772
  by_cases h41870 : n ≤ 41870
  · exact blk 83537 41773 41870 203 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h41870
  by_cases h41970 : n ≤ 41970
  · exact blk 83737 41871 41970 203 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h41970
  by_cases h42071 : n ≤ 42071
  · exact blk 83939 41971 42071 203 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42071
  by_cases h42174 : n ≤ 42174
  · exact blk 84143 42072 42174 205 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42174
  by_cases h42277 : n ≤ 42277
  · exact blk 84349 42175 42277 205 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42277
  by_cases h42378 : n ≤ 42378
  · exact blk 84551 42278 42378 205 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42378
  by_cases h42478 : n ≤ 42478
  · exact blk 84751 42379 42478 205 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42478
  by_cases h42576 : n ≤ 42576
  · exact blk 84947 42479 42576 205 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42576
  by_cases h42676 : n ≤ 42676
  · exact blk 85147 42577 42676 205 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42676
  by_cases h42769 : n ≤ 42769
  · exact blk 85333 42677 42769 205 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42769
  by_cases h42868 : n ≤ 42868
  · exact blk 85531 42770 42868 205 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42868
  by_cases h42970 : n ≤ 42970
  · exact blk 85733 42869 42970 207 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h42970
  by_cases h43070 : n ≤ 43070
  · exact blk 85933 42971 43070 207 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h43070
  by_cases h43172 : n ≤ 43172
  · exact blk 86137 43071 43172 207 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h43172
  by_cases h43274 : n ≤ 43274
  · exact blk 86341 43173 43274 207 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h43274
  by_cases h43373 : n ≤ 43373
  · exact blk 86539 43275 43373 207 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h43373
  by_cases h43475 : n ≤ 43475
  · exact blk 86743 43374 43475 207 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h43475
  by_cases h43579 : n ≤ 43579
  · exact blk 86951 43476 43579 207 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h43579
  by_cases h43679 : n ≤ 43679
  · exact blk 87151 43580 43679 207 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h43679
  by_cases h43783 : n ≤ 43783
  · exact blk 87359 43680 43783 207 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h43783
  by_cases h43884 : n ≤ 43884
  · exact blk 87559 43784 43884 209 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h43884
  by_cases h43988 : n ≤ 43988
  · exact blk 87767 43885 43988 209 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h43988
  by_cases h44093 : n ≤ 44093
  · exact blk 87977 43989 44093 209 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h44093
  by_cases h44193 : n ≤ 44193
  · exact blk 88177 44094 44193 209 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h44193
  by_cases h44294 : n ≤ 44294
  · exact blk 88379 44194 44294 209 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h44294
  by_cases h44399 : n ≤ 44399
  · exact blk 88589 44295 44399 209 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h44399
  by_cases h44504 : n ≤ 44504
  · exact blk 88799 44400 44504 209 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h44504
  omega
