import Mathlib

/-- 402-R4-c. Window primes for 184362 ≤ n ≤ 200014: 73 primality certificates by `norm_num`, no `native_decide`. -/
theorem r4c_window_184362_200014 : ∀ n : ℕ, 184362 ≤ n → n ≤ 200014 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h184573 : n ≤ 184573
  · exact blk 368717 184362 184573 429 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h184573
  by_cases h184786 : n ≤ 184786
  · exact blk 369143 184574 184786 429 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h184786
  by_cases h184993 : n ≤ 184993
  · exact blk 369557 184787 184993 429 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h184993
  by_cases h185206 : n ≤ 185206
  · exact blk 369983 184994 185206 429 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h185206
  by_cases h185420 : n ≤ 185420
  · exact blk 370411 185207 185420 429 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h185420
  by_cases h185633 : n ≤ 185633
  · exact blk 370837 185421 185633 429 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h185633
  by_cases h185843 : n ≤ 185843
  · exact blk 371257 185634 185843 429 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h185843
  by_cases h186050 : n ≤ 186050
  · exact blk 371669 185844 186050 431 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h186050
  by_cases h186249 : n ≤ 186249
  · exact blk 372067 186051 186249 431 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h186249
  by_cases h186464 : n ≤ 186464
  · exact blk 372497 186250 186464 431 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h186464
  by_cases h186674 : n ≤ 186674
  · exact blk 372917 186465 186674 431 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h186674
  by_cases h186890 : n ≤ 186890
  · exact blk 373349 186675 186890 431 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h186890
  by_cases h187104 : n ≤ 187104
  · exact blk 373777 186891 187104 431 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h187104
  by_cases h187317 : n ≤ 187317
  · exact blk 374203 187105 187317 431 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h187317
  by_cases h187517 : n ≤ 187517
  · exact blk 374603 187318 187517 431 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h187517
  by_cases h187731 : n ≤ 187731
  · exact blk 375029 187518 187731 433 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h187731
  by_cases h187945 : n ≤ 187945
  · exact blk 375457 187732 187945 433 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h187945
  by_cases h188145 : n ≤ 188145
  · exact blk 375857 187946 188145 433 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h188145
  by_cases h188362 : n ≤ 188362
  · exact blk 376291 188146 188362 433 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h188362
  by_cases h188577 : n ≤ 188577
  · exact blk 376721 188363 188577 433 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h188577
  by_cases h188790 : n ≤ 188790
  · exact blk 377147 188578 188790 433 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h188790
  by_cases h189007 : n ≤ 189007
  · exact blk 377581 188791 189007 433 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h189007
  by_cases h189222 : n ≤ 189222
  · exact blk 378011 189008 189222 433 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h189222
  by_cases h189436 : n ≤ 189436
  · exact blk 378439 189223 189436 433 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h189436
  by_cases h189652 : n ≤ 189652
  · exact blk 378869 189437 189652 435 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h189652
  by_cases h189862 : n ≤ 189862
  · exact blk 379289 189653 189862 435 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h189862
  by_cases h190079 : n ≤ 190079
  · exact blk 379723 189863 190079 435 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h190079
  by_cases h190291 : n ≤ 190291
  · exact blk 380147 190080 190291 435 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h190291
  by_cases h190499 : n ≤ 190499
  · exact blk 380563 190292 190499 435 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h190499
  by_cases h190709 : n ≤ 190709
  · exact blk 380983 190500 190709 435 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h190709
  by_cases h190927 : n ≤ 190927
  · exact blk 381419 190710 190927 435 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h190927
  by_cases h191144 : n ≤ 191144
  · exact blk 381853 190928 191144 435 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h191144
  by_cases h191354 : n ≤ 191354
  · exact blk 382271 191145 191354 437 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h191354
  by_cases h191573 : n ≤ 191573
  · exact blk 382709 191355 191573 437 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h191573
  by_cases h191792 : n ≤ 191792
  · exact blk 383147 191574 191792 437 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h191792
  by_cases h192005 : n ≤ 192005
  · exact blk 383573 191793 192005 437 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h192005
  by_cases h192219 : n ≤ 192219
  · exact blk 384001 192006 192219 437 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h192219
  by_cases h192437 : n ≤ 192437
  · exact blk 384437 192220 192437 437 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h192437
  by_cases h192644 : n ≤ 192644
  · exact blk 384851 192438 192644 437 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h192644
  by_cases h192863 : n ≤ 192863
  · exact blk 385289 192645 192863 437 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h192863
  by_cases h193074 : n ≤ 193074
  · exact blk 385709 192864 193074 439 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h193074
  by_cases h193294 : n ≤ 193294
  · exact blk 386149 193075 193294 439 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h193294
  by_cases h193513 : n ≤ 193513
  · exact blk 386587 193295 193513 439 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h193513
  by_cases h193728 : n ≤ 193728
  · exact blk 387017 193514 193728 439 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h193728
  by_cases h193944 : n ≤ 193944
  · exact blk 387449 193729 193944 439 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h193944
  by_cases h194148 : n ≤ 194148
  · exact blk 387857 193945 194148 439 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h194148
  by_cases h194358 : n ≤ 194358
  · exact blk 388277 194149 194358 439 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h194358
  by_cases h194575 : n ≤ 194575
  · exact blk 388711 194359 194575 439 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h194575
  by_cases h194795 : n ≤ 194795
  · exact blk 389149 194576 194795 441 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h194795
  by_cases h195016 : n ≤ 195016
  · exact blk 389591 194796 195016 441 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h195016
  by_cases h195221 : n ≤ 195221
  · exact blk 390001 195017 195221 441 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h195221
  by_cases h195439 : n ≤ 195439
  · exact blk 390437 195222 195439 441 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h195439
  by_cases h195659 : n ≤ 195659
  · exact blk 390877 195440 195659 441 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h195659
  by_cases h195871 : n ≤ 195871
  · exact blk 391301 195660 195871 441 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h195871
  by_cases h196090 : n ≤ 196090
  · exact blk 391739 195872 196090 441 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h196090
  by_cases h196309 : n ≤ 196309
  · exact blk 392177 196091 196309 441 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h196309
  by_cases h196527 : n ≤ 196527
  · exact blk 392611 196310 196527 443 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h196527
  by_cases h196737 : n ≤ 196737
  · exact blk 393031 196528 196737 443 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h196737
  by_cases h196958 : n ≤ 196958
  · exact blk 393473 196738 196958 443 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h196958
  by_cases h197172 : n ≤ 197172
  · exact blk 393901 196959 197172 443 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h197172
  by_cases h197385 : n ≤ 197385
  · exact blk 394327 197173 197385 443 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h197385
  by_cases h197601 : n ≤ 197601
  · exact blk 394759 197386 197601 443 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h197601
  by_cases h197822 : n ≤ 197822
  · exact blk 395201 197602 197822 443 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h197822
  by_cases h198035 : n ≤ 198035
  · exact blk 395627 197823 198035 443 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h198035
  by_cases h198253 : n ≤ 198253
  · exact blk 396061 198036 198253 445 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h198253
  by_cases h198462 : n ≤ 198462
  · exact blk 396479 198254 198462 445 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h198462
  by_cases h198682 : n ≤ 198682
  · exact blk 396919 198463 198682 445 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h198682
  by_cases h198903 : n ≤ 198903
  · exact blk 397361 198683 198903 445 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h198903
  by_cases h199126 : n ≤ 199126
  · exact blk 397807 198904 199126 445 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h199126
  by_cases h199347 : n ≤ 199347
  · exact blk 398249 199127 199347 445 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h199347
  by_cases h199569 : n ≤ 199569
  · exact blk 398693 199348 199569 445 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h199569
  by_cases h199791 : n ≤ 199791
  · exact blk 399137 199570 199791 445 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h199791
  by_cases h200014 : n ≤ 200014
  · exact blk 399583 199792 200014 445 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h200014
  omega
