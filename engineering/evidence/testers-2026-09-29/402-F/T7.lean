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

theorem Opn.erdos_402_card_seven_via_certificate :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 7 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
  exact Opn.erdos_402_card_of_colouring 7 60 {10, 12, 15, 20, 24, 30, 36, 40, 45, 48, 50}
    (fun a : ℕ => if a = 10 then 0 else if a = 12 then 1 else if a = 15 then 2 else if a = 20 then 3 else if a = 24 then 0 else if a = 30 then 4 else if a = 36 then 2 else if a = 40 then 1 else if a = 45 then 0 else if a = 48 then 3 else if a = 50 then 2 else 0)
    (by norm_num) (by norm_num) (by decide) (by decide) (by decide) A hA hn
