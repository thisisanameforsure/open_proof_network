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

theorem Opn.erdos_402_card_ten_test :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 10 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
  exact Opn.erdos_402_card_of_colouring 10 2520 {280, 315, 360, 420, 504, 560, 630, 720, 840, 945, 1008, 1080, 1120, 1260, 1400, 1440, 1512, 1575, 1680, 1800, 1890, 1960, 2016, 2100, 2160, 2205, 2240}
    (fun a : ℕ => if a = 280 then 4 else if a = 315 then 6 else if a = 360 then 2 else if a = 420 then 5 else if a = 504 then 7 else if a = 560 then 6 else if a = 630 then 3 else if a = 720 then 5 else if a = 840 then 1 else if a = 945 then 2 else if a = 1008 then 4 else if a = 1080 then 3 else if a = 1120 then 3 else if a = 1260 then 0 else if a = 1400 then 0 else if a = 1440 then 4 else if a = 1512 then 5 else if a = 1575 then 5 else if a = 1680 then 2 else if a = 1800 then 1 else if a = 1890 then 4 else if a = 1960 then 5 else if a = 2016 then 1 else if a = 2100 then 3 else if a = 2160 then 0 else if a = 2205 then 1 else if a = 2240 then 7 else 0)
    (by norm_num) (by norm_num) (by decide) (by decide) (by decide) A hA hn

