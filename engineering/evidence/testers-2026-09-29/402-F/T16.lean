import Mathlib

/-! A reduction of every fixed-size case of Erdős problem 402 (Graham's gcd problem) to a finite
certificate. With M the largest element of A, if gcd(M, x) ≤ M/n for some x the pair (M, x)
answers; otherwise every other element x is (j/k)·M with 1 ≤ j < k < n, so L·x = a·M for the
value a = L·j/k in S. The n − 1 other elements land on distinct values of S, and a colouring c
of S with n − 2 colours whose equal-coloured pairs a ≠ b all have n·gcd(a, b) ≤ max(a, b) gives,
by pigeonhole, two elements x, y with n·gcd(x, y) ≤ x or ≤ y, because gcd(a, b)·M = L·gcd(x, y).
A card-n variant then needs only L, S and c, and three decidable checks. -/

theorem Opn.erdos_402_card_of_colouring :
    ∀ (n L : ℕ) (S : Finset ℕ) (c : ℕ → ℕ), 2 ≤ n → 0 < L →
      (∀ k ∈ Finset.range n, ∀ j ∈ Finset.range k, 0 < j → k ∣ L * j ∧ L * j / k ∈ S) →
      (∀ a ∈ S, c a + 2 < n) →
      (∀ a ∈ S, ∀ b ∈ S, a ≠ b → c a = c b → n * a.gcd b ≤ a ∨ n * a.gcd b ≤ b) →
      ∀ A : Finset ℕ, 0 ∉ A → A.card = n → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  sorry

theorem Opn.erdos_402_card_sixteen_test :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 16 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
  exact Opn.erdos_402_card_of_colouring 16 360360 {24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336}
    (fun a : ℕ => if a = 24024 then 9 else if a = 25740 then 10 else if a = 27720 then 12 else if a = 30030 then 11 else if a = 32760 then 8 else if a = 36036 then 2 else if a = 40040 then 6 else if a = 45045 then 13 else if a = 48048 then 8 else if a = 51480 then 7 else if a = 55440 then 11 else if a = 60060 then 5 else if a = 65520 then 12 else if a = 72072 then 3 else if a = 77220 then 6 else if a = 80080 then 10 else if a = 83160 then 2 else if a = 90090 then 4 else if a = 96096 then 11 else if a = 98280 then 11 else if a = 102960 then 9 else if a = 108108 then 10 else if a = 110880 then 8 else if a = 120120 then 1 else if a = 128700 then 11 else if a = 131040 then 5 else if a = 135135 then 9 else if a = 138600 then 5 else if a = 144144 then 6 else if a = 150150 then 3 else if a = 154440 then 8 else if a = 160160 then 4 else if a = 163800 then 6 else if a = 166320 then 3 else if a = 168168 then 4 else if a = 180180 then 0 else if a = 192192 then 0 else if a = 194040 then 1 else if a = 196560 then 4 else if a = 200200 then 7 else if a = 205920 then 3 else if a = 210210 then 6 else if a = 216216 then 5 else if a = 221760 then 4 else if a = 225225 then 2 else if a = 229320 then 2 else if a = 231660 then 2 else if a = 240240 then 2 else if a = 249480 then 6 else if a = 252252 then 8 else if a = 257400 then 4 else if a = 262080 then 1 else if a = 264264 then 13 else if a = 270270 then 7 else if a = 277200 then 7 else if a = 280280 then 3 else if a = 283140 then 5 else if a = 288288 then 7 else if a = 294840 then 0 else if a = 300300 then 8 else if a = 304920 then 0 else if a = 308880 then 1 else if a = 312312 then 10 else if a = 315315 then 5 else if a = 320320 then 5 else if a = 324324 then 1 else if a = 327600 then 3 else if a = 330330 then 9 else if a = 332640 then 9 else if a = 334620 then 12 else if a = 336336 then 12 else 0)
    (by norm_num) (by norm_num) (by decide +kernel) (by decide +kernel) (by decide +kernel) A hA hn

