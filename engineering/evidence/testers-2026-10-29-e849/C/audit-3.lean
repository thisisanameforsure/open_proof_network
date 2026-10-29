import Mathlib

open Nat

-- variant-3969f1f7--h3--h1--h1--h1 vs variant-3969f1f7--h3--h1--h1 have h_scale (20261029T144021Z-t1029e-c-partial.lean)
example : (∀ (P₂ : ℝ),
  ∃ (a₀ : ℕ),
    ∀ a ≥ a₀,
      ∀ (n k n' k' : ℕ),
        (1 : ℕ) ≤ k' →
          k' < k →
            n < n' →
              (2 : ℕ) * k ≤ n →
                (2 : ℕ) * k' ≤ n' →
                  n.choose k = a →
                    n'.choose k' = a →
                      Real.exp (Real.log (↑n' : ℝ) ^ (43 / 60 : ℝ)) ≤ (↑k : ℝ) - (↑k' : ℝ) ∨
                          Real.exp (Real.log (↑n' : ℝ) ^ (43 / 60 : ℝ)) ≤ (↑k : ℝ) ∧
                            Real.exp (Real.log (↑n' : ℝ) ^ (43 / 60 : ℝ)) ≤ (↑k' : ℝ) ∧
                              Real.exp (Real.log (↑n' : ℝ) ^ (43 / 60 : ℝ)) ≤ (↑n' : ℝ) - (↑n : ℝ) →
                        ∃ (P : ℝ),
                          P₂ ≤ P ∧
                            (1 : ℝ) < P ∧
                              ((↑k : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧
                                  (↑k' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧
                                    (↑n : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧
                                      (↑n' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ))) ∧
                                (∀ (x₁ x₂ y₁ y₂ : ℤ),
                                    |(↑x₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                                      |(↑x₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                                        |(↑y₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                                          |(↑y₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                                            ∀ (j : ℕ),
                                              (1 : ℕ) ≤ j →
                                                |(↑x₁ : ℝ) * (↑k : ℝ) + (↑x₂ : ℝ) * (↑k' : ℝ) + (↑y₁ : ℝ) * (↑n : ℝ) +
                                                        (↑y₂ : ℝ) * (↑n' : ℝ)| ≤
                                                    P ^ j / Real.log P ^ (1000 : ℕ) ∨
                                                  P ^ j * Real.log P ^ (1000 : ℕ) ≤
                                                    |(↑x₁ : ℝ) * (↑k : ℝ) + (↑x₂ : ℝ) * (↑k' : ℝ) +
                                                          (↑y₁ : ℝ) * (↑n : ℝ) +
                                                        (↑y₂ : ℝ) * (↑n' : ℝ)|) ∧
                                  (P * Real.log P ^ (100 : ℕ) ≤ (↑k : ℝ) - (↑k' : ℝ) ∨
                                    P * Real.log P ^ (100 : ℕ) ≤ (↑k : ℝ) ∧
                                      P * Real.log P ^ (100 : ℕ) ≤ (↑k' : ℝ) ∧
                                        P * Real.log P ^ (100 : ℕ) ≤ (↑n' : ℝ) - (↑n : ℝ))) ↔ (∀ P₂ : ℝ, ∃ a₀ : ℕ, ∀ a ≥ a₀, ∀ n k n' k' : ℕ, 1 ≤ k' → k' < k → n < n' → 2 * k ≤ n → 2 * k' ≤ n' →
          n.choose k = a → n'.choose k' = a → (Real.exp (Real.log (n' : ℝ) ^ (43 / 60 : ℝ)) ≤ (k : ℝ) - k' ∨ (Real.exp (Real.log (n' : ℝ) ^ (43 / 60 : ℝ)) ≤ (k : ℝ) ∧ Real.exp (Real.log (n' : ℝ) ^ (43 / 60 : ℝ)) ≤ (k' : ℝ) ∧ Real.exp (Real.log (n' : ℝ) ^ (43 / 60 : ℝ)) ≤ (n' : ℝ) - n)) →
          ∃ P : ℝ, P₂ ≤ P ∧ 1 < P ∧ ((k : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧ (k' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧ (n : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧ (n' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ))) ∧
          (∀ x₁ x₂ y₁ y₂ : ℤ, |(x₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) → |(x₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) → |(y₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) → |(y₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
            ∀ j : ℕ, 1 ≤ j → |(x₁ : ℝ) * k + x₂ * k' + y₁ * n + y₂ * n'| ≤ P ^ j / Real.log P ^ 1000 ∨ P ^ j * Real.log P ^ 1000 ≤ |(x₁ : ℝ) * k + x₂ * k' + y₁ * n + y₂ * n'|) ∧
          (P * Real.log P ^ 100 ≤ (k : ℝ) - k' ∨ (P * Real.log P ^ 100 ≤ (k : ℝ) ∧ P * Real.log P ^ 100 ≤ (k' : ℝ) ∧ P * Real.log P ^ 100 ≤ (n' : ℝ) - n))) := Iff.rfl

-- variant-3969f1f7--h3--h1--h1--h2 vs variant-3969f1f7--h3--h1--h1 have h_covar (20261029T144021Z-t1029e-c-partial.lean)
example : (∃ (C : ℝ) (P₀ : ℝ),
  ∀ P ≥ P₀,
    ∀ (n k n' k' : ℕ),
      (1 : ℕ) ≤ k' →
        k' < k →
          n < n' →
            (2 : ℕ) * k ≤ n →
              (2 : ℕ) * k' ≤ n' →
                n.choose k = n'.choose k' →
                  (↑k : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧
                      (↑k' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧
                        (↑n : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧
                          (↑n' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) →
                    (∀ (x₁ x₂ y₁ y₂ : ℤ),
                        |(↑x₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                          |(↑x₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                            |(↑y₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                              |(↑y₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                                ∀ (j : ℕ),
                                  (1 : ℕ) ≤ j →
                                    |(↑x₁ : ℝ) * (↑k : ℝ) + (↑x₂ : ℝ) * (↑k' : ℝ) + (↑y₁ : ℝ) * (↑n : ℝ) +
                                            (↑y₂ : ℝ) * (↑n' : ℝ)| ≤
                                        P ^ j / Real.log P ^ (1000 : ℕ) ∨
                                      P ^ j * Real.log P ^ (1000 : ℕ) ≤
                                        |(↑x₁ : ℝ) * (↑k : ℝ) + (↑x₂ : ℝ) * (↑k' : ℝ) + (↑y₁ : ℝ) * (↑n : ℝ) +
                                            (↑y₂ : ℝ) * (↑n' : ℝ)|) →
                      ∀ (S : Finset ℕ),
                        S = Finset.filter Nat.Prime (Finset.Icc ⌈P⌉₊ ⌊P + P / Real.log P ^ (100 : ℕ)⌋₊) →
                          ∀ (N : ℝ),
                            N = (↑k : ℝ) ∨
                                N = (↑n : ℝ) ∨
                                  N = (↑n : ℝ) - (↑k : ℝ) ∨ N = (↑k' : ℝ) ∨ N = (↑n' : ℝ) ∨ N = (↑n' : ℝ) - (↑k' : ℝ) →
                              ∀ (M : ℝ),
                                M = (↑k : ℝ) ∨
                                    M = (↑n : ℝ) ∨
                                      M = (↑n : ℝ) - (↑k : ℝ) ∨
                                        M = (↑k' : ℝ) ∨ M = (↑n' : ℝ) ∨ M = (↑n' : ℝ) - (↑k' : ℝ) →
                                  ∀ (j : ℕ),
                                    (1 : ℕ) ≤ j →
                                      (↑j : ℝ) ≤ Real.log P ^ (1 / 2 : ℝ) →
                                        ∀ (c : ℝ),
                                          c =
                                              (∑ p ∈ S, Int.fract (N / (↑p : ℝ)) * Int.fract (M / (↑p : ℝ) ^ j)) /
                                                  (↑S.card : ℝ) -
                                                (∑ p ∈ S, Int.fract (N / (↑p : ℝ))) / (↑S.card : ℝ) *
                                                  ((∑ p ∈ S, Int.fract (M / (↑p : ℝ) ^ j)) / (↑S.card : ℝ)) →
                                            ((2 : ℕ) ≤ j → |c| ≤ C / Real.log P ^ (10 : ℕ)) ∧
                                              (j = (1 : ℕ) →
                                                  |N| ≤ P / Real.log P ^ (1000 : ℕ) ∨
                                                      |M| ≤ P / Real.log P ^ (1000 : ℕ) →
                                                    |c| ≤ C / Real.log P ^ (1000 : ℕ)) ∧
                                                (j = (1 : ℕ) →
                                                    P / Real.log P ^ (1000 : ℕ) < |N| →
                                                      P / Real.log P ^ (1000 : ℕ) < |M| →
                                                        ∀ (a b : ℕ),
                                                          (1 : ℕ) ≤ a →
                                                            (1 : ℕ) ≤ b →
                                                              a.Coprime b →
                                                                (↑a : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) →
                                                                  (↑b : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) →
                                                                    |(↑a : ℝ) * N - (↑b : ℝ) * M| ≤
                                                                        P / Real.log P ^ (1000 : ℕ) →
                                                                      |c - (1 : ℝ) / ((12 : ℝ) * (↑a : ℝ) * (↑b : ℝ))| ≤
                                                                        C / Real.log P ^ (1 / 1000 : ℝ)) ∧
                                                  (j = (1 : ℕ) →
                                                    P / Real.log P ^ (1000 : ℕ) < |N| →
                                                      P / Real.log P ^ (1000 : ℕ) < |M| →
                                                        (∀ (a b : ℕ),
                                                            (1 : ℕ) ≤ a →
                                                              (1 : ℕ) ≤ b →
                                                                a.Coprime b →
                                                                  (↑a : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) →
                                                                    (↑b : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) →
                                                                      P / Real.log P ^ (1000 : ℕ) <
                                                                        |(↑a : ℝ) * N - (↑b : ℝ) * M|) →
                                                          |c| ≤ C / Real.log P ^ (1 / 1000 : ℝ))) ↔ (∃ C : ℝ, ∃ P₀ : ℝ, ∀ P ≥ P₀, ∀ n k n' k' : ℕ, 1 ≤ k' → k' < k → n < n' → 2 * k ≤ n → 2 * k' ≤ n' → n.choose k = n'.choose k' →
          ((k : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧ (k' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧ (n : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧ (n' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ))) →
          (∀ x₁ x₂ y₁ y₂ : ℤ, |(x₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) → |(x₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) → |(y₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) → |(y₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
            ∀ j : ℕ, 1 ≤ j → |(x₁ : ℝ) * k + x₂ * k' + y₁ * n + y₂ * n'| ≤ P ^ j / Real.log P ^ 1000 ∨ P ^ j * Real.log P ^ 1000 ≤ |(x₁ : ℝ) * k + x₂ * k' + y₁ * n + y₂ * n'|) →
          (∀ S : Finset ℕ, S = Finset.filter Nat.Prime (Finset.Icc ⌈P⌉₊ ⌊P + P / Real.log P ^ 100⌋₊) →
            ∀ N : ℝ, (N = (k : ℝ) ∨ N = (n : ℝ) ∨ N = (n : ℝ) - k ∨ N = (k' : ℝ) ∨ N = (n' : ℝ) ∨ N = (n' : ℝ) - k') →
            ∀ M : ℝ, (M = (k : ℝ) ∨ M = (n : ℝ) ∨ M = (n : ℝ) - k ∨ M = (k' : ℝ) ∨ M = (n' : ℝ) ∨ M = (n' : ℝ) - k') →
            ∀ j : ℕ, 1 ≤ j → (j : ℝ) ≤ Real.log P ^ (1 / 2 : ℝ) →
            ∀ c : ℝ, c = (∑ p ∈ S, Int.fract (N / p) * Int.fract (M / (p : ℝ) ^ j)) / S.card -
                ((∑ p ∈ S, Int.fract (N / p)) / S.card) * ((∑ p ∈ S, Int.fract (M / (p : ℝ) ^ j)) / S.card) →
            (2 ≤ j → |c| ≤ C / Real.log P ^ 10) ∧
            (j = 1 → (|N| ≤ P / Real.log P ^ 1000 ∨ |M| ≤ P / Real.log P ^ 1000) → |c| ≤ C / Real.log P ^ 1000) ∧
            (j = 1 → P / Real.log P ^ 1000 < |N| → P / Real.log P ^ 1000 < |M| → ∀ a b : ℕ, 1 ≤ a → 1 ≤ b → Nat.Coprime a b →
              (a : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) → (b : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) → |a * N - b * M| ≤ P / Real.log P ^ 1000 →
              |c - 1 / (12 * a * b)| ≤ C / Real.log P ^ (1 / 1000 : ℝ)) ∧
            (j = 1 → P / Real.log P ^ 1000 < |N| → P / Real.log P ^ 1000 < |M| → (∀ a b : ℕ, 1 ≤ a → 1 ≤ b → Nat.Coprime a b →
              (a : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) → (b : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) → P / Real.log P ^ 1000 < |a * N - b * M|) →
              |c| ≤ C / Real.log P ^ (1 / 1000 : ℝ)))) := Iff.rfl

-- variant-3969f1f7--h3--h1--h1--h3 vs variant-3969f1f7--h3--h1--h1 have h_deduce (20261029T144021Z-t1029e-c-partial.lean)
example : (∀ (C : ℝ),
  ∃ (P₁ : ℝ),
    ∀ P ≥ P₁,
      ∀ (n k n' k' : ℕ),
        (1 : ℕ) ≤ k' →
          k' < k →
            n < n' →
              (2 : ℕ) * k ≤ n →
                (2 : ℕ) * k' ≤ n' →
                  n.choose k = n'.choose k' →
                    (↑k : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧
                        (↑k' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧
                          (↑n : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧
                            (↑n' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) →
                      (∀ (x₁ x₂ y₁ y₂ : ℤ),
                          |(↑x₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                            |(↑x₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                              |(↑y₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                                |(↑y₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
                                  ∀ (j : ℕ),
                                    (1 : ℕ) ≤ j →
                                      |(↑x₁ : ℝ) * (↑k : ℝ) + (↑x₂ : ℝ) * (↑k' : ℝ) + (↑y₁ : ℝ) * (↑n : ℝ) +
                                              (↑y₂ : ℝ) * (↑n' : ℝ)| ≤
                                          P ^ j / Real.log P ^ (1000 : ℕ) ∨
                                        P ^ j * Real.log P ^ (1000 : ℕ) ≤
                                          |(↑x₁ : ℝ) * (↑k : ℝ) + (↑x₂ : ℝ) * (↑k' : ℝ) + (↑y₁ : ℝ) * (↑n : ℝ) +
                                              (↑y₂ : ℝ) * (↑n' : ℝ)|) →
                        P * Real.log P ^ (100 : ℕ) ≤ (↑k : ℝ) - (↑k' : ℝ) ∨
                            P * Real.log P ^ (100 : ℕ) ≤ (↑k : ℝ) ∧
                              P * Real.log P ^ (100 : ℕ) ≤ (↑k' : ℝ) ∧
                                P * Real.log P ^ (100 : ℕ) ≤ (↑n' : ℝ) - (↑n : ℝ) →
                          (∀ (S : Finset ℕ),
                              S = Finset.filter Nat.Prime (Finset.Icc ⌈P⌉₊ ⌊P + P / Real.log P ^ (100 : ℕ)⌋₊) →
                                ∀ (N : ℝ),
                                  N = (↑k : ℝ) ∨
                                      N = (↑n : ℝ) ∨
                                        N = (↑n : ℝ) - (↑k : ℝ) ∨
                                          N = (↑k' : ℝ) ∨ N = (↑n' : ℝ) ∨ N = (↑n' : ℝ) - (↑k' : ℝ) →
                                    ∀ (M : ℝ),
                                      M = (↑k : ℝ) ∨
                                          M = (↑n : ℝ) ∨
                                            M = (↑n : ℝ) - (↑k : ℝ) ∨
                                              M = (↑k' : ℝ) ∨ M = (↑n' : ℝ) ∨ M = (↑n' : ℝ) - (↑k' : ℝ) →
                                        ∀ (j : ℕ),
                                          (1 : ℕ) ≤ j →
                                            (↑j : ℝ) ≤ Real.log P ^ (1 / 2 : ℝ) →
                                              ∀ (c : ℝ),
                                                c =
                                                    (∑ p ∈ S, Int.fract (N / (↑p : ℝ)) * Int.fract (M / (↑p : ℝ) ^ j)) /
                                                        (↑S.card : ℝ) -
                                                      (∑ p ∈ S, Int.fract (N / (↑p : ℝ))) / (↑S.card : ℝ) *
                                                        ((∑ p ∈ S, Int.fract (M / (↑p : ℝ) ^ j)) / (↑S.card : ℝ)) →
                                                  ((2 : ℕ) ≤ j → |c| ≤ C / Real.log P ^ (10 : ℕ)) ∧
                                                    (j = (1 : ℕ) →
                                                        |N| ≤ P / Real.log P ^ (1000 : ℕ) ∨
                                                            |M| ≤ P / Real.log P ^ (1000 : ℕ) →
                                                          |c| ≤ C / Real.log P ^ (1000 : ℕ)) ∧
                                                      (j = (1 : ℕ) →
                                                          P / Real.log P ^ (1000 : ℕ) < |N| →
                                                            P / Real.log P ^ (1000 : ℕ) < |M| →
                                                              ∀ (a b : ℕ),
                                                                (1 : ℕ) ≤ a →
                                                                  (1 : ℕ) ≤ b →
                                                                    a.Coprime b →
                                                                      (↑a : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) →
                                                                        (↑b : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) →
                                                                          |(↑a : ℝ) * N - (↑b : ℝ) * M| ≤
                                                                              P / Real.log P ^ (1000 : ℕ) →
                                                                            |c -
                                                                                  (1 : ℝ) /
                                                                                    ((12 : ℝ) * (↑a : ℝ) * (↑b : ℝ))| ≤
                                                                              C / Real.log P ^ (1 / 1000 : ℝ)) ∧
                                                        (j = (1 : ℕ) →
                                                          P / Real.log P ^ (1000 : ℕ) < |N| →
                                                            P / Real.log P ^ (1000 : ℕ) < |M| →
                                                              (∀ (a b : ℕ),
                                                                  (1 : ℕ) ≤ a →
                                                                    (1 : ℕ) ≤ b →
                                                                      a.Coprime b →
                                                                        (↑a : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) →
                                                                          (↑b : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) →
                                                                            P / Real.log P ^ (1000 : ℕ) <
                                                                              |(↑a : ℝ) * N - (↑b : ℝ) * M|) →
                                                                |c| ≤ C / Real.log P ^ (1 / 1000 : ℝ))) →
                            False) ↔ (∀ C : ℝ, ∃ P₁ : ℝ, ∀ P ≥ P₁, ∀ n k n' k' : ℕ, 1 ≤ k' → k' < k → n < n' → 2 * k ≤ n → 2 * k' ≤ n' → n.choose k = n'.choose k' →
          ((k : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧ (k' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧ (n : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ)) ∧ (n' : ℝ) ≤ Real.exp (Real.log P ^ (299 / 200 : ℝ))) →
          (∀ x₁ x₂ y₁ y₂ : ℤ, |(x₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) → |(x₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) → |(y₁ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) → |(y₂ : ℝ)| ≤ Real.log P ^ (1 / 100 : ℝ) →
            ∀ j : ℕ, 1 ≤ j → |(x₁ : ℝ) * k + x₂ * k' + y₁ * n + y₂ * n'| ≤ P ^ j / Real.log P ^ 1000 ∨ P ^ j * Real.log P ^ 1000 ≤ |(x₁ : ℝ) * k + x₂ * k' + y₁ * n + y₂ * n'|) →
          (P * Real.log P ^ 100 ≤ (k : ℝ) - k' ∨ (P * Real.log P ^ 100 ≤ (k : ℝ) ∧ P * Real.log P ^ 100 ≤ (k' : ℝ) ∧ P * Real.log P ^ 100 ≤ (n' : ℝ) - n)) →
          (∀ S : Finset ℕ, S = Finset.filter Nat.Prime (Finset.Icc ⌈P⌉₊ ⌊P + P / Real.log P ^ 100⌋₊) →
            ∀ N : ℝ, (N = (k : ℝ) ∨ N = (n : ℝ) ∨ N = (n : ℝ) - k ∨ N = (k' : ℝ) ∨ N = (n' : ℝ) ∨ N = (n' : ℝ) - k') →
            ∀ M : ℝ, (M = (k : ℝ) ∨ M = (n : ℝ) ∨ M = (n : ℝ) - k ∨ M = (k' : ℝ) ∨ M = (n' : ℝ) ∨ M = (n' : ℝ) - k') →
            ∀ j : ℕ, 1 ≤ j → (j : ℝ) ≤ Real.log P ^ (1 / 2 : ℝ) →
            ∀ c : ℝ, c = (∑ p ∈ S, Int.fract (N / p) * Int.fract (M / (p : ℝ) ^ j)) / S.card -
                ((∑ p ∈ S, Int.fract (N / p)) / S.card) * ((∑ p ∈ S, Int.fract (M / (p : ℝ) ^ j)) / S.card) →
            (2 ≤ j → |c| ≤ C / Real.log P ^ 10) ∧
            (j = 1 → (|N| ≤ P / Real.log P ^ 1000 ∨ |M| ≤ P / Real.log P ^ 1000) → |c| ≤ C / Real.log P ^ 1000) ∧
            (j = 1 → P / Real.log P ^ 1000 < |N| → P / Real.log P ^ 1000 < |M| → ∀ a b : ℕ, 1 ≤ a → 1 ≤ b → Nat.Coprime a b →
              (a : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) → (b : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) → |a * N - b * M| ≤ P / Real.log P ^ 1000 →
              |c - 1 / (12 * a * b)| ≤ C / Real.log P ^ (1 / 1000 : ℝ)) ∧
            (j = 1 → P / Real.log P ^ 1000 < |N| → P / Real.log P ^ 1000 < |M| → (∀ a b : ℕ, 1 ≤ a → 1 ≤ b → Nat.Coprime a b →
              (a : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) → (b : ℝ) ≤ Real.log P ^ (1 / 100 : ℝ) → P / Real.log P ^ 1000 < |a * N - b * M|) →
              |c| ≤ C / Real.log P ^ (1 / 1000 : ℝ))) → False) := Iff.rfl
