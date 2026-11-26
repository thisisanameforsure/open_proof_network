import Mathlib
import Defs.Local

open scoped Finset
open Green76

/-- `partial`: the root (`green_76`, the threshold 1000) implies this variant, with k = 1000. -/
theorem relation :
    (∀ A : Finset (ℝ × ℝ), ∃ A', #A' ≤ #A / 2 ∧ HitsRichRectangles 1000 A A') →
    ∃ k : ℕ, ∀ A : Finset (ℝ × ℝ), ∃ A', #A' ≤ #A / 2 ∧ HitsRichRectangles k A A' :=
  fun h => ⟨1000, h⟩
