import Mathlib

/-- 402-R4-c. Window primes for 44505 ≤ n ≤ 55208: 100 primality certificates by `norm_num`, no `native_decide`. -/
theorem r4c_window_44505_55208 : ∀ n : ℕ, 44505 ≤ n → n ≤ 55208 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h44609 : n ≤ 44609
  · exact blk 89009 44505 44609 209 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h44609
  by_cases h44712 : n ≤ 44712
  · exact blk 89213 44610 44712 211 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h44712
  by_cases h44814 : n ≤ 44814
  · exact blk 89417 44713 44814 211 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h44814
  by_cases h44919 : n ≤ 44919
  · exact blk 89627 44815 44919 211 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h44919
  by_cases h45025 : n ≤ 45025
  · exact blk 89839 44920 45025 211 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h45025
  by_cases h45121 : n ≤ 45121
  · exact blk 90031 45026 45121 211 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h45121
  by_cases h45225 : n ≤ 45225
  · exact blk 90239 45122 45225 211 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h45225
  by_cases h45325 : n ≤ 45325
  · exact blk 90439 45226 45325 211 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h45325
  by_cases h45429 : n ≤ 45429
  · exact blk 90647 45326 45429 211 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h45429
  by_cases h45530 : n ≤ 45530
  · exact blk 90847 45430 45530 213 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h45530
  by_cases h45623 : n ≤ 45623
  · exact blk 91033 45531 45623 213 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h45623
  by_cases h45728 : n ≤ 45728
  · exact blk 91243 45624 45728 213 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h45728
  by_cases h45835 : n ≤ 45835
  · exact blk 91457 45729 45835 213 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h45835
  by_cases h45926 : n ≤ 45926
  · exact blk 91639 45836 45926 213 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h45926
  by_cases h46027 : n ≤ 46027
  · exact blk 91841 45927 46027 213 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h46027
  by_cases h46132 : n ≤ 46132
  · exact blk 92051 46028 46132 213 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h46132
  by_cases h46232 : n ≤ 46232
  · exact blk 92251 46133 46232 213 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h46232
  by_cases h46338 : n ≤ 46338
  · exact blk 92461 46233 46338 215 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h46338
  by_cases h46443 : n ≤ 46443
  · exact blk 92671 46339 46443 215 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h46443
  by_cases h46541 : n ≤ 46541
  · exact blk 92867 46444 46541 215 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h46541
  by_cases h46649 : n ≤ 46649
  · exact blk 93083 46542 46649 215 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h46649
  by_cases h46751 : n ≤ 46751
  · exact blk 93287 46650 46751 215 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h46751
  by_cases h46859 : n ≤ 46859
  · exact blk 93503 46752 46859 215 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h46859
  by_cases h46967 : n ≤ 46967
  · exact blk 93719 46860 46967 215 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h46967
  by_cases h47069 : n ≤ 47069
  · exact blk 93923 46968 47069 215 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h47069
  by_cases h47168 : n ≤ 47168
  · exact blk 94121 47070 47168 215 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h47168
  by_cases h47274 : n ≤ 47274
  · exact blk 94331 47169 47274 217 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h47274
  by_cases h47382 : n ≤ 47382
  · exact blk 94547 47275 47382 217 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h47382
  by_cases h47482 : n ≤ 47482
  · exact blk 94747 47383 47482 217 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h47482
  by_cases h47589 : n ≤ 47589
  · exact blk 94961 47483 47589 217 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h47589
  by_cases h47697 : n ≤ 47697
  · exact blk 95177 47590 47697 217 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h47697
  by_cases h47805 : n ≤ 47805
  · exact blk 95393 47698 47805 217 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h47805
  by_cases h47910 : n ≤ 47910
  · exact blk 95603 47806 47910 217 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h47910
  by_cases h48018 : n ≤ 48018
  · exact blk 95819 47911 48018 217 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h48018
  by_cases h48118 : n ≤ 48118
  · exact blk 96017 48019 48118 219 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h48118
  by_cases h48226 : n ≤ 48226
  · exact blk 96233 48119 48226 219 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h48226
  by_cases h48335 : n ≤ 48335
  · exact blk 96451 48227 48335 219 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h48335
  by_cases h48445 : n ≤ 48445
  · exact blk 96671 48336 48445 219 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h48445
  by_cases h48538 : n ≤ 48538
  · exact blk 96857 48446 48538 219 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h48538
  by_cases h48646 : n ≤ 48646
  · exact blk 97073 48539 48646 219 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h48646
  by_cases h48751 : n ≤ 48751
  · exact blk 97283 48647 48751 219 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h48751
  by_cases h48860 : n ≤ 48860
  · exact blk 97501 48752 48860 219 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h48860
  by_cases h48966 : n ≤ 48966
  · exact blk 97711 48861 48966 221 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h48966
  by_cases h49076 : n ≤ 49076
  · exact blk 97931 48967 49076 221 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h49076
  by_cases h49182 : n ≤ 49182
  · exact blk 98143 49077 49182 221 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h49182
  by_cases h49284 : n ≤ 49284
  · exact blk 98347 49183 49284 221 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h49284
  by_cases h49392 : n ≤ 49392
  · exact blk 98563 49285 49392 221 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h49392
  by_cases h49500 : n ≤ 49500
  · exact blk 98779 49393 49500 221 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h49500
  by_cases h49610 : n ≤ 49610
  · exact blk 98999 49501 49610 221 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h49610
  by_cases h49706 : n ≤ 49706
  · exact blk 99191 49611 49706 221 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h49706
  by_cases h49815 : n ≤ 49815
  · exact blk 99409 49707 49815 221 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h49815
  by_cases h49923 : n ≤ 49923
  · exact blk 99623 49816 49923 223 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h49923
  by_cases h50031 : n ≤ 50031
  · exact blk 99839 49924 50031 223 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h50031
  by_cases h50140 : n ≤ 50140
  · exact blk 100057 50032 50140 223 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h50140
  by_cases h50251 : n ≤ 50251
  · exact blk 100279 50141 50251 223 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h50251
  by_cases h50362 : n ≤ 50362
  · exact blk 100501 50252 50362 223 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h50362
  by_cases h50463 : n ≤ 50463
  · exact blk 100703 50363 50463 223 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h50463
  by_cases h50575 : n ≤ 50575
  · exact blk 100927 50464 50575 223 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h50575
  by_cases h50686 : n ≤ 50686
  · exact blk 101149 50576 50686 223 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h50686
  by_cases h50794 : n ≤ 50794
  · exact blk 101363 50687 50794 225 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h50794
  by_cases h50903 : n ≤ 50903
  · exact blk 101581 50795 50903 225 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h50903
  by_cases h51016 : n ≤ 51016
  · exact blk 101807 50904 51016 225 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h51016
  by_cases h51128 : n ≤ 51128
  · exact blk 102031 51017 51128 225 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h51128
  by_cases h51239 : n ≤ 51239
  · exact blk 102253 51129 51239 225 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h51239
  by_cases h51343 : n ≤ 51343
  · exact blk 102461 51240 51343 225 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h51343
  by_cases h51452 : n ≤ 51452
  · exact blk 102679 51344 51452 225 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h51452
  by_cases h51553 : n ≤ 51553
  · exact blk 102881 51453 51553 225 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h51553
  by_cases h51663 : n ≤ 51663
  · exact blk 103099 51554 51663 227 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h51663
  by_cases h51773 : n ≤ 51773
  · exact blk 103319 51664 51773 227 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h51773
  by_cases h51878 : n ≤ 51878
  · exact blk 103529 51774 51878 227 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h51878
  by_cases h51975 : n ≤ 51975
  · exact blk 103723 51879 51975 227 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h51975
  by_cases h52089 : n ≤ 52089
  · exact blk 103951 51976 52089 227 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h52089
  by_cases h52203 : n ≤ 52203
  · exact blk 104179 52090 52203 227 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h52203
  by_cases h52313 : n ≤ 52313
  · exact blk 104399 52204 52313 227 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h52313
  by_cases h52425 : n ≤ 52425
  · exact blk 104623 52314 52425 227 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h52425
  by_cases h52539 : n ≤ 52539
  · exact blk 104851 52426 52539 227 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h52539
  by_cases h52650 : n ≤ 52650
  · exact blk 105071 52540 52650 229 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h52650
  by_cases h52753 : n ≤ 52753
  · exact blk 105277 52651 52753 229 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h52753
  by_cases h52866 : n ≤ 52866
  · exact blk 105503 52754 52866 229 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h52866
  by_cases h52981 : n ≤ 52981
  · exact blk 105733 52867 52981 229 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h52981
  by_cases h53091 : n ≤ 53091
  · exact blk 105953 52982 53091 229 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h53091
  by_cases h53205 : n ≤ 53205
  · exact blk 106181 53092 53205 229 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h53205
  by_cases h53320 : n ≤ 53320
  · exact blk 106411 53206 53320 229 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h53320
  by_cases h53433 : n ≤ 53433
  · exact blk 106637 53321 53433 229 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h53433
  by_cases h53549 : n ≤ 53549
  · exact blk 106867 53434 53549 231 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h53549
  by_cases h53665 : n ≤ 53665
  · exact blk 107099 53550 53665 231 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h53665
  by_cases h53777 : n ≤ 53777
  · exact blk 107323 53666 53777 231 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h53777
  by_cases h53870 : n ≤ 53870
  · exact blk 107509 53778 53870 231 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h53870
  by_cases h53986 : n ≤ 53986
  · exact blk 107741 53871 53986 231 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h53986
  by_cases h54101 : n ≤ 54101
  · exact blk 107971 53987 54101 231 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h54101
  by_cases h54217 : n ≤ 54217
  · exact blk 108203 54102 54217 231 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h54217
  by_cases h54326 : n ≤ 54326
  · exact blk 108421 54218 54326 231 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h54326
  by_cases h54441 : n ≤ 54441
  · exact blk 108649 54327 54441 233 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h54441
  by_cases h54558 : n ≤ 54558
  · exact blk 108883 54442 54558 233 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h54558
  by_cases h54672 : n ≤ 54672
  · exact blk 109111 54559 54672 233 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h54672
  by_cases h54782 : n ≤ 54782
  · exact blk 109331 54673 54782 233 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h54782
  by_cases h54890 : n ≤ 54890
  · exact blk 109547 54783 54890 233 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h54890
  by_cases h54992 : n ≤ 54992
  · exact blk 109751 54891 54992 233 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h54992
  by_cases h55097 : n ≤ 55097
  · exact blk 109961 54993 55097 233 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h55097
  by_cases h55208 : n ≤ 55208
  · exact blk 110183 55098 55208 233 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h55208
  omega
