import Mathlib
import Nodes.«spec-180d8b72».Context

/-- erdos-1050, Borwein's route: the remainder bound `hrem` of the skeleton on erdos-1050--h1-v2 (hole erdos-1050--h1-v2--h4), without the denominator bound `hden` that the hole carries as an unused hypothesis (revision request, graph PR #229). With T = sum 1/(2^(n+3) - 3) and x_n = 3/2^n, the Pade remainder R_n = Q_n(x_n) * 3T - A_n is positive and R_n^2 * 2^(4n^2) <= 2^(2n+4). Numerically checked for n <= 30 (tightest at n = 1). -/
theorem erdos_1050_pade_remainder_bound : ∀ (Qc : ℕ → ℕ → ℚ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) →
    ∀ (Qx : ℕ → ℚ),
      (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) →
        ∀ (Aq : ℕ → ℚ),
          (Aq = fun (n : ℕ) =>
              ∑ k ∈ Finset.range (n + (1 : ℕ)),
                  (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) *
                    ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
                Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) →
              ∀ (n : ℕ),
                (0 : ℝ) <
                    (↑(Qx n) : ℝ) * ((3 : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((2 : ℝ) ^ (n + (3 : ℕ)) - (3 : ℝ))) -
                      (↑(Aq n) : ℝ) ∧
                  ((↑(Qx n) : ℝ) * ((3 : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((2 : ℝ) ^ (n + (3 : ℕ)) - (3 : ℝ))) -
                          (↑(Aq n) : ℝ)) ^
                        (2 : ℕ) *
                      (2 : ℝ) ^ ((4 : ℕ) * n * n) ≤
                    (2 : ℝ) ^ ((2 : ℕ) * n + (4 : ℕ)) := by
  sorry
