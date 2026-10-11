import Mathlib

/-- 402-R4-c. Window primes for 55209 ≤ n ≤ 67128: 100 primality certificates by `norm_num`, no `native_decide`. -/
theorem r4c_window_55209_67128 : ∀ n : ℕ, 55209 ≤ n → n ≤ 67128 →
    ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h55296 : n ≤ 55296
  · exact blk 110359 55209 55296 233 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h55296
  by_cases h55411 : n ≤ 55411
  · exact blk 110587 55297 55411 235 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h55411
  by_cases h55528 : n ≤ 55528
  · exact blk 110821 55412 55528 235 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h55528
  by_cases h55644 : n ≤ 55644
  · exact blk 111053 55529 55644 235 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h55644
  by_cases h55753 : n ≤ 55753
  · exact blk 111271 55645 55753 235 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h55753
  by_cases h55866 : n ≤ 55866
  · exact blk 111497 55754 55866 235 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h55866
  by_cases h55984 : n ≤ 55984
  · exact blk 111733 55867 55984 235 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h55984
  by_cases h56097 : n ≤ 56097
  · exact blk 111959 55985 56097 235 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h56097
  by_cases h56208 : n ≤ 56208
  · exact blk 112181 56098 56208 235 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h56208
  by_cases h56320 : n ≤ 56320
  · exact blk 112403 56209 56320 237 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h56320
  by_cases h56429 : n ≤ 56429
  · exact blk 112621 56321 56429 237 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h56429
  by_cases h56548 : n ≤ 56548
  · exact blk 112859 56430 56548 237 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h56548
  by_cases h56665 : n ≤ 56665
  · exact blk 113093 56549 56665 237 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h56665
  by_cases h56783 : n ≤ 56783
  · exact blk 113329 56666 56783 237 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h56783
  by_cases h56902 : n ≤ 56902
  · exact blk 113567 56784 56902 237 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h56902
  by_cases h57017 : n ≤ 57017
  · exact blk 113797 56903 57017 237 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h57017
  by_cases h57134 : n ≤ 57134
  · exact blk 114031 57018 57134 237 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h57134
  by_cases h57254 : n ≤ 57254
  · exact blk 114269 57135 57254 239 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h57254
  by_cases h57366 : n ≤ 57366
  · exact blk 114493 57255 57366 239 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h57366
  by_cases h57476 : n ≤ 57476
  · exact blk 114713 57367 57476 239 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h57476
  by_cases h57590 : n ≤ 57590
  · exact blk 114941 57477 57590 239 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h57590
  by_cases h57701 : n ≤ 57701
  · exact blk 115163 57591 57701 239 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h57701
  by_cases h57819 : n ≤ 57819
  · exact blk 115399 57702 57819 239 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h57819
  by_cases h57938 : n ≤ 57938
  · exact blk 115637 57820 57938 239 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h57938
  by_cases h58058 : n ≤ 58058
  · exact blk 115877 57939 58058 239 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h58058
  by_cases h58176 : n ≤ 58176
  · exact blk 116113 58059 58176 239 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h58176
  by_cases h58296 : n ≤ 58296
  · exact blk 116351 58177 58296 241 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h58296
  by_cases h58417 : n ≤ 58417
  · exact blk 116593 58297 58417 241 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h58417
  by_cases h58537 : n ≤ 58537
  · exact blk 116833 58418 58537 241 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h58537
  by_cases h58656 : n ≤ 58656
  · exact blk 117071 58538 58656 241 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h58656
  by_cases h58774 : n ≤ 58774
  · exact blk 117307 58657 58774 241 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h58774
  by_cases h58891 : n ≤ 58891
  · exact blk 117541 58775 58891 241 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h58891
  by_cases h59010 : n ≤ 59010
  · exact blk 117779 58892 59010 241 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h59010
  by_cases h59116 : n ≤ 59116
  · exact blk 117991 59011 59116 241 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h59116
  by_cases h59231 : n ≤ 59231
  · exact blk 118219 59117 59231 243 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h59231
  by_cases h59353 : n ≤ 59353
  · exact blk 118463 59232 59353 243 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h59353
  by_cases h59467 : n ≤ 59467
  · exact blk 118691 59354 59467 243 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h59467
  by_cases h59587 : n ≤ 59587
  · exact blk 118931 59468 59587 243 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h59587
  by_cases h59708 : n ≤ 59708
  · exact blk 119173 59588 59708 243 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h59708
  by_cases h59830 : n ≤ 59830
  · exact blk 119417 59709 59830 243 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h59830
  by_cases h59951 : n ≤ 59951
  · exact blk 119659 59831 59951 243 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h59951
  by_cases h60067 : n ≤ 60067
  · exact blk 119891 59952 60067 243 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h60067
  by_cases h60183 : n ≤ 60183
  · exact blk 120121 60068 60183 245 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h60183
  by_cases h60297 : n ≤ 60297
  · exact blk 120349 60184 60297 245 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h60297
  by_cases h60416 : n ≤ 60416
  · exact blk 120587 60298 60416 245 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h60416
  by_cases h60539 : n ≤ 60539
  · exact blk 120833 60417 60539 245 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h60539
  by_cases h60656 : n ≤ 60656
  · exact blk 121067 60540 60656 245 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h60656
  by_cases h60779 : n ≤ 60779
  · exact blk 121313 60657 60779 245 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h60779
  by_cases h60902 : n ≤ 60902
  · exact blk 121559 60780 60902 245 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h60902
  by_cases h61017 : n ≤ 61017
  · exact blk 121789 60903 61017 245 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h61017
  by_cases h61140 : n ≤ 61140
  · exact blk 122033 61018 61140 247 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h61140
  by_cases h61263 : n ≤ 61263
  · exact blk 122279 61141 61263 247 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h61263
  by_cases h61387 : n ≤ 61387
  · exact blk 122527 61264 61387 247 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h61387
  by_cases h61504 : n ≤ 61504
  · exact blk 122761 61388 61504 247 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h61504
  by_cases h61627 : n ≤ 61627
  · exact blk 123007 61505 61627 247 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h61627
  by_cases h61743 : n ≤ 61743
  · exact blk 123239 61628 61743 247 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h61743
  by_cases h61863 : n ≤ 61863
  · exact blk 123479 61744 61863 247 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h61863
  by_cases h61987 : n ≤ 61987
  · exact blk 123727 61864 61987 247 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h61987
  by_cases h62110 : n ≤ 62110
  · exact blk 123973 61988 62110 247 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h62110
  by_cases h62231 : n ≤ 62231
  · exact blk 124213 62111 62231 249 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h62231
  by_cases h62354 : n ≤ 62354
  · exact blk 124459 62232 62354 249 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h62354
  by_cases h62476 : n ≤ 62476
  · exact blk 124703 62355 62476 249 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h62476
  by_cases h62600 : n ≤ 62600
  · exact blk 124951 62477 62600 249 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h62600
  by_cases h62725 : n ≤ 62725
  · exact blk 125201 62601 62725 249 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h62725
  by_cases h62845 : n ≤ 62845
  · exact blk 125441 62726 62845 249 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h62845
  by_cases h62968 : n ≤ 62968
  · exact blk 125687 62846 62968 249 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h62968
  by_cases h63091 : n ≤ 63091
  · exact blk 125933 62969 63091 249 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h63091
  by_cases h63212 : n ≤ 63212
  · exact blk 126173 63092 63212 251 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h63212
  by_cases h63336 : n ≤ 63336
  · exact blk 126421 63213 63336 251 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h63336
  by_cases h63452 : n ≤ 63452
  · exact blk 126653 63337 63452 251 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h63452
  by_cases h63555 : n ≤ 63555
  · exact blk 126859 63453 63555 251 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h63555
  by_cases h63677 : n ≤ 63677
  · exact blk 127103 63556 63677 251 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h63677
  by_cases h63797 : n ≤ 63797
  · exact blk 127343 63678 63797 251 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h63797
  by_cases h63921 : n ≤ 63921
  · exact blk 127591 63798 63921 251 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h63921
  by_cases h64047 : n ≤ 64047
  · exact blk 127843 63922 64047 251 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h64047
  by_cases h64153 : n ≤ 64153
  · exact blk 128053 64048 64153 253 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h64153
  by_cases h64272 : n ≤ 64272
  · exact blk 128291 64154 64272 253 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h64272
  by_cases h64387 : n ≤ 64387
  · exact blk 128521 64273 64387 253 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h64387
  by_cases h64510 : n ≤ 64510
  · exact blk 128767 64388 64510 253 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h64510
  by_cases h64632 : n ≤ 64632
  · exact blk 129011 64511 64632 253 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h64632
  by_cases h64758 : n ≤ 64758
  · exact blk 129263 64633 64758 253 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h64758
  by_cases h64885 : n ≤ 64885
  · exact blk 129517 64759 64885 253 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h64885
  by_cases h65011 : n ≤ 65011
  · exact blk 129769 64886 65011 253 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h65011
  by_cases h65137 : n ≤ 65137
  · exact blk 130021 65012 65137 253 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h65137
  by_cases h65261 : n ≤ 65261
  · exact blk 130267 65138 65261 255 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h65261
  by_cases h65389 : n ≤ 65389
  · exact blk 130523 65262 65389 255 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h65389
  by_cases h65512 : n ≤ 65512
  · exact blk 130769 65390 65512 255 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h65512
  by_cases h65639 : n ≤ 65639
  · exact blk 131023 65513 65639 255 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h65639
  by_cases h65761 : n ≤ 65761
  · exact blk 131267 65640 65761 255 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h65761
  by_cases h65887 : n ≤ 65887
  · exact blk 131519 65762 65887 255 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h65887
  by_cases h66013 : n ≤ 66013
  · exact blk 131771 65888 66013 255 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h66013
  by_cases h66137 : n ≤ 66137
  · exact blk 132019 66014 66137 255 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h66137
  by_cases h66260 : n ≤ 66260
  · exact blk 132263 66138 66260 257 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h66260
  by_cases h66384 : n ≤ 66384
  · exact blk 132511 66261 66384 257 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h66384
  by_cases h66510 : n ≤ 66510
  · exact blk 132763 66385 66510 257 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h66510
  by_cases h66635 : n ≤ 66635
  · exact blk 133013 66511 66635 257 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h66635
  by_cases h66764 : n ≤ 66764
  · exact blk 133271 66636 66764 257 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h66764
  by_cases h66888 : n ≤ 66888
  · exact blk 133519 66765 66888 257 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h66888
  by_cases h67013 : n ≤ 67013
  · exact blk 133769 66889 67013 257 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h67013
  by_cases h67128 : n ≤ 67128
  · exact blk 133999 67014 67128 257 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h67128
  omega
