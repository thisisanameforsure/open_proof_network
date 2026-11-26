# arxiv-2504-17644-margulis-conjecture-1-1 — import as stated

Row: `fc:FormalConjectures/Arxiv/2504.17644/Margulis.lean#conjecture_1_1` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883.
Curator A (statement, ports, first reading), 2026-11-25; curator M (witness, decision), 2026-11-25.

## Decision: import as stated

Curator A found the statement portable and declined the row for one reason only: there was no D-4
step 7 witness. Curator M wrote the witness (`Witness.lean`, 368 lines, one theorem), so the decline
is withdrawn.

## Statement

`Statement.lean` is the registry's `conjecture_1_1` as the registry wrote it: the same binders before
the colon, renamed `Opn.conjecture_1_1`, under `open Matrix SpecialLinearGroup` and
`open scoped MatrixGroups`. Differences from the registry file:

- `namespace Margulis`, the empty `section` with its `variable (n …) (R …)` line, and
  `open scoped Polynomial LaurentSeries` are dropped. The theorem uses none of them: its own `{n : ℕ}`
  shadows the section's `n`, and section variables a theorem does not use are not included.
- The `@[category …, AMS …]` attribute is dropped, as for every imported row.
- `polyToLaurent` and `huang_shi_theorem_1_2` from the same file are not imported. The statement does
  not use them.

## Ports (`defs/`)

- `defs/LinearAlgebraGeneralLinearGroup.lean`: `FormalConjecturesForMathlib/LinearAlgebra/GeneralLinearGroup.lean`
  (`diagonalHom`, `GeneralLinearGroup.diagonalSubgroup`).
- `defs/LinearAlgebraSpecialLinearGroup.lean`: `FormalConjecturesForMathlib/LinearAlgebra/SpecialLinearGroup.lean`
  (`SpecialLinearGroup.diagonalSubgroup`), importing the first.

Both are byte for byte. The only changes are that `module`, the `public import` lines and
`@[expose] public section` are removed, and the imports are written as `import Mathlib` and
`import Defs.…`. Neither contains `sorry`, `axiom` or `opaque`.

## Witness

Step 7's expected type (the Prop binders `hn`, `hg`, under the data binders `n`, `g`):

    ∃ (n : ℕ) (g : SL(n, ℝ) ⧸ Subgroup.map (map (Int.castRingHom ℝ)) ⊤),
      3 ≤ n ∧ IsCompact (closure (MulAction.orbit (diagonalSubgroup (Fin n) ℝ) g))

The witness states this with qualified names (`Matrix.SpecialLinearGroup …`) and proves it with
n = 3 and the classical compact orbit of a totally real cubic field.

- θ₀ < θ₁ < θ₂ are the three real roots of x³ − 3x + 1. They are obtained by the intermediate value
  theorem on [−1.9, −1.8], [0.34, 0.35] and [1.5, 1.6].
- g₀ = c·V, where V is the Vandermonde matrix (θᵢ^j), whose determinant is
  (θ₁−θ₀)(θ₂−θ₀)(θ₂−θ₁) > 0, and c = det V^(−1/3), so det g₀ = 1. The point is g = g₀·SL₃(ℤ).
- The units θ² and (1−θ)² have norm 1. In the basis 1, θ, θ² they act by the integer matrices
  `!![0,-1,0;0,3,-1;1,0,3]` and `!![1,-1,2;-2,4,-7;1,-2,4]`, each of determinant 1. Hence
  diag(θᵢ²)·V = V·M_u and diag((1−θᵢ)²)·V = V·M_v. This uses only θᵢ³ = 3θᵢ − 1. So g₀⁻¹·diag(…)·g₀
  lies in SL₃(ℤ), and so do all of its integer powers.
- Logarithm lattice. Let A = (log θ₀², log θ₁²) and B = (log(1−θ₀)², log(1−θ₁)²). The bounds
  A₀ ∈ (0,2), A₁ ∈ (−3,−2), B₀ ∈ (2,3), B₁ ∈ (−1,0) follow from `Real.exp_one_gt_d9` and
  `Real.exp_one_lt_d9`. They give A₀B₁ − A₁B₀ > 2, so A and B are independent. Every diagonal d with
  det 1 can then be written as d = d′·u^m·v^k, where m and k are the floors of d's coordinates in this
  basis, and every entry of d′ satisfies |d′ᵢ| ≤ e⁵ (the third entry is bounded because the three
  logarithms sum to 0). So the orbit lies in π(K), where K = {diag(y)·g₀ : |yᵢ| ≤ e⁵, y₀y₁y₂ = 1} is
  compact.
- The closure. Mathlib does not give the quotient by the (non-normal) SL₃(ℤ) a separation instance,
  so the witness does not use `IsCompact.closure`. Instead it proves closure(π K) ⊆ π(C·K), where C is
  the compact box of determinant-1 matrices whose entries are within 1 of the identity's. Then
  closure(orbit) is a closed subset of a compact set. The inclusion uses that π is open: the
  neighbourhood π(O·z) of a point in the closure meets π(K).

No new definitions are used: the theorem holds `have`s only. Mathlib already holds everything it
needs (IVT, `Matrix.det_fin_three`, `Real.log` and `Real.exp` bounds, `QuotientGroup.isOpenMap_coe`,
`isCompact_univ_pi`, `IsCompact.prod`).

## Checks

The file sent inlines `import Mathlib`, then each port in its own `section`, then the statement, then
the witness, with `autoImplicit false` and `relaxedAutoImplicit false`.

- AXLE directly (`lean-4.33.1`): compiles with no errors. `#print axioms witness` gives
  `[propext, Classical.choice, Quot.sound]`. `#count_heartbeats` on the final proof gave 167,043, under
  Lean's default limit of 200,000, so the witness needs no `set_option`.
- `POST https://api.openproofnetwork.org/check` (log_id `01M89P67X8QY9K9F9Z4AF6M83S`) gives
  `result.lean_messages.errors == []` for the same file. `okay` is false only because of the
  statement's `sorry`. Parsing took about 13 s, inside the route's 20 s budget. Earlier drafts ran
  over that budget, which is why AXLE was used to iterate.
- Not checked: the gate's own step 7 comparison of the given type against the expected type, because
  `"mode": "witness"` needs the target's `defs/` on the graph. The type was written from
  `gate/lean/OpnGate/WitnessType.lean`'s rule and agrees with curator A's reading. The lead's
  precheck is the verdict.
- Not checked: the step 6 hazard checkers. No `hazards.yaml` is written.

## Sources read
- `FormalConjectures/Arxiv/2504.17644/Margulis.lean`
- `FormalConjecturesForMathlib/LinearAlgebra/SpecialLinearGroup.lean`, `…/GeneralLinearGroup.lean`
- `gate/lean/OpnGate/WitnessType.lean` (how step 7 forms the expected type)
- `gate/agents/AGENTS.md` (witness checks); `targets/artin-…-parts-i` on graph `origin/main` (layout)
