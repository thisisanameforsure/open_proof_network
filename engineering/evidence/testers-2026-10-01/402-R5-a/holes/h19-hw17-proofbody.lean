  have blk : ∀ (p lo hi k : ℕ), p.Prime → hi < p → p < 2 * lo → 2 * hi - p = k → k * k ≤ lo →
      ∀ n : ℕ, lo ≤ n → n ≤ hi → ∃ p : ℕ, p.Prime ∧ n < p ∧ p < 2 * n ∧ (2 * n - p) * (2 * n - p) ≤ n := by
    intro p lo hi k hp h1 h2 h3 h4 n hl hh
    refine ⟨p, hp, by omega, by omega, ?_⟩
    have : 2 * n - p ≤ k := by omega
    exact le_trans (Nat.mul_le_mul this this) (by omega)
  intro n hl hh
  by_cases h164142 : n ≤ 164142
  · exact blk 327881 163942 164142 403 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h164142
  by_cases h164344 : n ≤ 164344
  · exact blk 328283 164143 164344 405 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h164344
  by_cases h164546 : n ≤ 164546
  · exact blk 328687 164345 164546 405 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h164546
  by_cases h164747 : n ≤ 164747
  · exact blk 329089 164547 164747 405 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h164747
  by_cases h164947 : n ≤ 164947
  · exact blk 329489 164748 164947 405 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h164947
  by_cases h165148 : n ≤ 165148
  · exact blk 329891 164948 165148 405 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h165148
  by_cases h165347 : n ≤ 165347
  · exact blk 330289 165149 165347 405 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h165347
  by_cases h165547 : n ≤ 165547
  · exact blk 330689 165348 165547 405 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h165547
  by_cases h165743 : n ≤ 165743
  · exact blk 331081 165548 165743 405 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h165743
  by_cases h165929 : n ≤ 165929
  · exact blk 331451 165744 165929 407 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h165929
  by_cases h166125 : n ≤ 166125
  · exact blk 331843 165930 166125 407 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h166125
  by_cases h166329 : n ≤ 166329
  · exact blk 332251 166126 166329 407 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h166329
  by_cases h166524 : n ≤ 166524
  · exact blk 332641 166330 166524 407 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h166524
  by_cases h166728 : n ≤ 166728
  · exact blk 333049 166525 166728 407 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h166728
  by_cases h166932 : n ≤ 166932
  · exact blk 333457 166729 166932 407 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h166932
  by_cases h167132 : n ≤ 167132
  · exact blk 333857 166933 167132 407 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h167132
  by_cases h167334 : n ≤ 167334
  · exact blk 334261 167133 167334 407 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h167334
  by_cases h167538 : n ≤ 167538
  · exact blk 334667 167335 167538 409 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h167538
  by_cases h167743 : n ≤ 167743
  · exact blk 335077 167539 167743 409 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h167743
  by_cases h167943 : n ≤ 167943
  · exact blk 335477 167744 167943 409 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h167943
  by_cases h168144 : n ≤ 168144
  · exact blk 335879 167944 168144 409 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h168144
  by_cases h168336 : n ≤ 168336
  · exact blk 336263 168145 168336 409 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h168336
  by_cases h168540 : n ≤ 168540
  · exact blk 336671 168337 168540 409 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h168540
  by_cases h168745 : n ≤ 168745
  · exact blk 337081 168541 168745 409 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h168745
  by_cases h168949 : n ≤ 168949
  · exact blk 337489 168746 168949 409 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h168949
  by_cases h169151 : n ≤ 169151
  · exact blk 337891 168950 169151 411 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h169151
  by_cases h169354 : n ≤ 169354
  · exact blk 338297 169152 169354 411 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h169354
  by_cases h169559 : n ≤ 169559
  · exact blk 338707 169355 169559 411 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h169559
  by_cases h169759 : n ≤ 169759
  · exact blk 339107 169560 169759 411 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h169759
  by_cases h169964 : n ≤ 169964
  · exact blk 339517 169760 169964 411 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h169964
  by_cases h170159 : n ≤ 170159
  · exact blk 339907 169965 170159 411 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h170159
  by_cases h170354 : n ≤ 170354
  · exact blk 340297 170160 170354 411 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h170354
  by_cases h170560 : n ≤ 170560
  · exact blk 340709 170355 170560 411 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h170560
  by_cases h170749 : n ≤ 170749
  · exact blk 341087 170561 170749 411 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h170749
  by_cases h170952 : n ≤ 170952
  · exact blk 341491 170750 170952 413 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h170952
  by_cases h171146 : n ≤ 171146
  · exact blk 341879 170953 171146 413 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h171146
  by_cases h171348 : n ≤ 171348
  · exact blk 342283 171147 171348 413 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h171348
  by_cases h171555 : n ≤ 171555
  · exact blk 342697 171349 171555 413 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h171555
  by_cases h171750 : n ≤ 171750
  · exact blk 343087 171556 171750 413 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h171750
  by_cases h171951 : n ≤ 171951
  · exact blk 343489 171751 171951 413 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h171951
  by_cases h172157 : n ≤ 172157
  · exact blk 343901 171952 172157 413 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h172157
  by_cases h172353 : n ≤ 172353
  · exact blk 344293 172158 172353 413 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h172353
  by_cases h172554 : n ≤ 172554
  · exact blk 344693 172354 172554 415 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h172554
  by_cases h172762 : n ≤ 172762
  · exact blk 345109 172555 172762 415 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h172762
  by_cases h172966 : n ≤ 172966
  · exact blk 345517 172763 172966 415 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h172966
  by_cases h173169 : n ≤ 173169
  · exact blk 345923 172967 173169 415 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h173169
  by_cases h173376 : n ≤ 173376
  · exact blk 346337 173170 173376 415 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h173376
  by_cases h173583 : n ≤ 173583
  · exact blk 346751 173377 173583 415 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h173583
  by_cases h173791 : n ≤ 173791
  · exact blk 347167 173584 173791 415 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h173791
  by_cases h173997 : n ≤ 173997
  · exact blk 347579 173792 173997 415 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h173997
  by_cases h174205 : n ≤ 174205
  · exact blk 347993 173998 174205 417 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h174205
  by_cases h174412 : n ≤ 174412
  · exact blk 348407 174206 174412 417 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h174412
  by_cases h174614 : n ≤ 174614
  · exact blk 348811 174413 174614 417 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h174614
  by_cases h174814 : n ≤ 174814
  · exact blk 349211 174615 174814 417 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h174814
  by_cases h175010 : n ≤ 175010
  · exact blk 349603 174815 175010 417 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h175010
  by_cases h175210 : n ≤ 175210
  · exact blk 350003 175011 175210 417 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h175210
  by_cases h175414 : n ≤ 175414
  · exact blk 350411 175211 175414 417 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h175414
  by_cases h175613 : n ≤ 175613
  · exact blk 350809 175415 175613 417 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h175613
  by_cases h175821 : n ≤ 175821
  · exact blk 351223 175614 175821 419 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h175821
  by_cases h176031 : n ≤ 176031
  · exact blk 351643 175822 176031 419 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h176031
  by_cases h176238 : n ≤ 176238
  · exact blk 352057 176032 176238 419 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h176238
  by_cases h176441 : n ≤ 176441
  · exact blk 352463 176239 176441 419 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h176441
  by_cases h176651 : n ≤ 176651
  · exact blk 352883 176442 176651 419 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h176651
  by_cases h176856 : n ≤ 176856
  · exact blk 353293 176652 176856 419 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h176856
  by_cases h177065 : n ≤ 177065
  · exact blk 353711 176857 177065 419 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h177065
  by_cases h177270 : n ≤ 177270
  · exact blk 354121 177066 177270 419 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h177270
  by_cases h177480 : n ≤ 177480
  · exact blk 354539 177271 177480 421 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h177480
  by_cases h177691 : n ≤ 177691
  · exact blk 354961 177481 177691 421 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h177691
  by_cases h177900 : n ≤ 177900
  · exact blk 355379 177692 177900 421 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h177900
  by_cases h178110 : n ≤ 178110
  · exact blk 355799 177901 178110 421 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h178110
  by_cases h178320 : n ≤ 178320
  · exact blk 356219 178111 178320 421 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h178320
  by_cases h178521 : n ≤ 178521
  · exact blk 356621 178321 178521 421 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h178521
  by_cases h178726 : n ≤ 178726
  · exact blk 357031 178522 178726 421 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h178726
  by_cases h178929 : n ≤ 178929
  · exact blk 357437 178727 178929 421 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h178929
  by_cases h179141 : n ≤ 179141
  · exact blk 357859 178930 179141 423 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h179141
  by_cases h179351 : n ≤ 179351
  · exact blk 358279 179142 179351 423 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h179351
  by_cases h179563 : n ≤ 179563
  · exact blk 358703 179352 179563 423 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h179563
  by_cases h179767 : n ≤ 179767
  · exact blk 359111 179564 179767 423 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h179767
  by_cases h179966 : n ≤ 179966
  · exact blk 359509 179768 179966 423 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h179966
  by_cases h180176 : n ≤ 180176
  · exact blk 359929 179967 180176 423 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h180176
  by_cases h180380 : n ≤ 180380
  · exact blk 360337 180177 180380 423 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h180380
  by_cases h180586 : n ≤ 180586
  · exact blk 360749 180381 180586 423 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h180586
  by_cases h180791 : n ≤ 180791
  · exact blk 361159 180587 180791 423 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h180791
  by_cases h181001 : n ≤ 181001
  · exact blk 361577 180792 181001 425 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h181001
  by_cases h181214 : n ≤ 181214
  · exact blk 362003 181002 181214 425 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h181214
  by_cases h181427 : n ≤ 181427
  · exact blk 362429 181215 181427 425 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h181427
  by_cases h181638 : n ≤ 181638
  · exact blk 362851 181428 181638 425 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h181638
  by_cases h181851 : n ≤ 181851
  · exact blk 363277 181639 181851 425 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h181851
  by_cases h182058 : n ≤ 182058
  · exact blk 363691 181852 182058 425 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h182058
  by_cases h182264 : n ≤ 182264
  · exact blk 364103 182059 182264 425 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h182264
  by_cases h182474 : n ≤ 182474
  · exact blk 364523 182265 182474 425 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h182474
  by_cases h182685 : n ≤ 182685
  · exact blk 364943 182475 182685 427 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h182685
  by_cases h182898 : n ≤ 182898
  · exact blk 365369 182686 182898 427 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h182898
  by_cases h183112 : n ≤ 183112
  · exact blk 365797 182899 183112 427 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h183112
  by_cases h183324 : n ≤ 183324
  · exact blk 366221 183113 183324 427 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h183324
  by_cases h183529 : n ≤ 183529
  · exact blk 366631 183325 183529 427 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h183529
  by_cases h183738 : n ≤ 183738
  · exact blk 367049 183530 183738 427 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h183738
  by_cases h183948 : n ≤ 183948
  · exact blk 367469 183739 183948 427 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h183948
  by_cases h184158 : n ≤ 184158
  · exact blk 367889 183949 184158 427 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h184158
  by_cases h184361 : n ≤ 184361
  · exact blk 368293 184159 184361 429 (by norm_num) (by norm_num) (by norm_num) (by norm_num) (by norm_num) n (by omega) h184361
  omega
