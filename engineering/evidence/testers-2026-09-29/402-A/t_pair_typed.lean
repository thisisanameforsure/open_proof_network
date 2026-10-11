import Mathlib

example : ∀ a ∈ ([105, 120, 140, 168, 210, 240, 280, 315, 336, 360,
      420, 480, 504, 525, 560, 600, 630, 672, 700, 720, 735] : List ℕ),
      ∀ b ∈ ([105, 120, 140, 168, 210, 240, 280, 315, 336, 360,
      420, 480, 504, 525, 560, 600, 630, 672, 700, 720, 735] : List ℕ),
      (if a = 420 ∨ a = 600 then 0 else if a = 210 ∨ a = 360 ∨ a = 672 ∨ a = 700 then 1
        else if a = 120 ∨ a = 560 ∨ a = 630 then 2 else if a = 105 ∨ a = 240 ∨ a = 504 then 3
        else if a = 280 ∨ a = 315 ∨ a = 480 then 4 else if a = 168 ∨ a = 525 ∨ a = 720 then 5
        else 6) =
      (if b = 420 ∨ b = 600 then 0 else if b = 210 ∨ b = 360 ∨ b = 672 ∨ b = 700 then 1
        else if b = 120 ∨ b = 560 ∨ b = 630 then 2 else if b = 105 ∨ b = 240 ∨ b = 504 then 3
        else if b = 280 ∨ b = 315 ∨ b = 480 then 4 else if b = 168 ∨ b = 525 ∨ b = 720 then 5
        else 6) →
      a = b ∨ 9 * a.gcd b ≤ a ∨ 9 * a.gcd b ≤ b := by
  decide +kernel
