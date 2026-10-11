import Mathlib
import Defs.Construction

/-- Why `Even M`: at `M = 1` depth `3 = 3M` is not cancelled (the label `0` is alone on its point). -/
example : ∑ d ∈ Finset.univ.filter (fun d : Fin 1 → Fin 6 =>
      Opn.E69.sIndex 1 d + (1 + Opn.E69.gIndex 1 d) * 3
        = Opn.E69.sIndex 1 (fun _ => 0) + (1 + Opn.E69.gIndex 1 (fun _ => 0)) * 3), Opn.E69.sign 1 d ≠ 0 := by
  decide +kernel
