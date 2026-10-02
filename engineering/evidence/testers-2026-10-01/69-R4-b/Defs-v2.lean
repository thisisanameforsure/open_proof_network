import Mathlib

/-! Proposed `targets/erdos-69/defs/Construction.lean` (draft by 69-R2-b, v2 by 69-R4-b, 2026-10-01, clean-room:
written from the mathematics and from the annexes on the record, without reading any external
Lean source). The signed family of rough dilated tails over which the unconditional half of the
irrationality of `∑ ω(n)/2^n` is a statement about `ω` alone.

Idea. A dilated tail `tail a m = ∑_{u ≥ 1} ω (a (m + u)) / 2^u` with `a ∣ n + s`, `m = (n + s)/a`
reads `ω` along the line `u ↦ n + s + a u` with weight `2^{-u}`. Write `a = 1 + H g`, `s = H σ`
(`H = P#`). Two lines `(g, σ)`, `(g', σ')` meet at depth `u` iff `(g - g') u + (σ - σ') = 0`.
For a triple of depths `u₁ < u₂ < u₃` put `β = (u₃ - u₂, u₁ - u₃, u₂ - u₁)` and
`wᵢ = βᵢ (1, -uᵢ)`; then `w₁ + w₂ + w₃ = 0`, and the six lines `±wᵢ` with signs `±` cancel
pairwise at each of the three depths. The triples `{1,2,4}, {3,5,6}, {7,8,10}, {9,11,12}, …`
(triple `r` is `3r + {1,2,4}` for even `r`, `3r + {0,2,3}` for odd `r`) cover every depth
`≤ 3M` with `M` triples WHEN `M` IS EVEN (for odd `M` the last triple is `3M - 2, 3M - 1, 3M + 1`
and depth `3M` is not cancelled; at `M = 1` depth 3 survives). The product pattern has `6^M`
lines in base-7 digits, and for even `M` what is left of the signed combination has weight
`2^{-3M}` per line: total mass `(3/4)^M → 0`. Every statement about cancellation carries
`Even M`.

v2 (69-R4-b, 2026-10-01): the thirteen definitions of v1 are unchanged, byte for byte; this
comment is corrected (the v1 comment claimed cancellation for every `M`), and four definitions
are added at the end (`omegaBelow`, `tailBelow`, `signedTailBelow`, `charMeanBelow`): the same
objects with `ω` cut at a threshold `z`, which the decay argument needs to be stated at all. -/

open scoped ArithmeticFunction.omega

/-- The dilated binary tail `D_a(m) = ∑_{k ≥ 0} ω (a (m + k + 1)) / 2^(k+1)` (the expression of
the proved nodes `spec-9f8cb4ea` and `spec-84446025`). -/
noncomputable def Opn.E69.tail (a m : ℕ) : ℝ :=
  ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)

/-- Slope digit of line `k` of triple `r`: `3 + ε β`, a base-7 digit other than 3. -/
def Opn.E69.gDigit (r : ℕ) (k : Fin 6) : ℕ :=
  if r % 2 = 0 then ![5, 1, 0, 6, 4, 2] k else ![4, 2, 0, 6, 5, 1] k

/-- Offset digit of line `k` of triple `r`: `(9 r + 12) - ε β u`. -/
def Opn.E69.sDigit (r : ℕ) (k : Fin 6) : ℕ :=
  if r % 2 = 0 then ![3 * r + 10, 15 * r + 14, 18 * r + 18, 6, 6 * r + 8, 12 * r + 16] k
  else ![6 * r + 12, 12 * r + 12, 18 * r + 18, 6, 3 * r + 6, 15 * r + 18] k

/-- Slope index of the line labelled `d` (one choice among six per triple). -/
def Opn.E69.gIndex (M : ℕ) (d : Fin M → Fin 6) : ℕ :=
  ∑ r : Fin M, 7 ^ (r : ℕ) * Opn.E69.gDigit r (d r)

/-- Offset index of the line labelled `d`. -/
def Opn.E69.sIndex (M : ℕ) (d : Fin M → Fin 6) : ℕ :=
  ∑ r : Fin M, 7 ^ (r : ℕ) * Opn.E69.sDigit r (d r)

/-- Sign of the line labelled `d`: the product of `(-1)^k` over its choices. -/
def Opn.E69.sign (M : ℕ) (d : Fin M → Fin 6) : ℤ :=
  ∏ r : Fin M, (-1) ^ ((d r : Fin 6) : ℕ)

/-- The rough dilation `1 + P# (1 + g)`: every prime factor exceeds `P` (as in `spec-e0b917d1`). -/
def Opn.E69.dil (M P : ℕ) (d : Fin M → Fin 6) : ℕ :=
  1 + primorial P * (1 + Opn.E69.gIndex M d)

/-- The shift `P# σ` of the line labelled `d`. -/
def Opn.E69.shift (M P : ℕ) (d : Fin M → Fin 6) : ℕ :=
  primorial P * Opn.E69.sIndex M d

/-- The common modulus: the product of all `6^M` dilations. -/
def Opn.E69.modulus (M P : ℕ) : ℕ :=
  ∏ d : Fin M → Fin 6, Opn.E69.dil M P d

/-- `n₀` is a base point: each dilation divides its shifted base (a Chinese-remainder system). -/
def Opn.E69.Admissible (M P n₀ : ℕ) : Prop :=
  ∀ d : Fin M → Fin 6, Opn.E69.dil M P d ∣ n₀ + Opn.E69.shift M P d

/-- Along `n = n₀ + modulus · t`, line `d` is the dilated tail at `start + step · t`. -/
def Opn.E69.start (M P n₀ : ℕ) (d : Fin M → Fin 6) : ℕ :=
  (n₀ + Opn.E69.shift M P d) / Opn.E69.dil M P d

/-- The step of line `d`: the modulus without its own dilation. -/
def Opn.E69.step (M P : ℕ) (d : Fin M → Fin 6) : ℕ :=
  Opn.E69.modulus M P / Opn.E69.dil M P d

/-- The signed combination of dilated tails at time `t`. -/
noncomputable def Opn.E69.signedTail (M P n₀ t : ℕ) : ℝ :=
  ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) *
    Opn.E69.tail (Opn.E69.dil M P d) (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t)

/-- The characteristic function of `q ·` the signed combination, averaged over `t < T`. -/
noncomputable def Opn.E69.charMean (q M P n₀ T : ℕ) : ℂ :=
  (∑ t ∈ Finset.range T, Complex.exp (2 * Real.pi * Complex.I *
    (((q : ℝ) * Opn.E69.signedTail M P n₀ t : ℝ) : ℂ))) / T

/-- The number of distinct prime factors of `n` that are at most `z` (`ω` cut at `z`). -/
def Opn.E69.omegaBelow (z n : ℕ) : ℕ :=
  (n.primeFactors.filter (fun p => p ≤ z)).card

/-- The dilated tail with `ω` cut at `z`. -/
noncomputable def Opn.E69.tailBelow (z a m : ℕ) : ℝ :=
  ∑' k : ℕ, (Opn.E69.omegaBelow z (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)

/-- The signed combination with `ω` cut at `z`; periodic in `t` with period `primorial z`. -/
noncomputable def Opn.E69.signedTailBelow (z M P n₀ t : ℕ) : ℝ :=
  ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) *
    Opn.E69.tailBelow z (Opn.E69.dil M P d) (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t)

/-- The characteristic function of `q ·` the cut signed combination, averaged over `t < T`.
At `T = primorial z` (a full period) this is the independent-primes model, exactly. -/
noncomputable def Opn.E69.charMeanBelow (q z M P n₀ T : ℕ) : ℂ :=
  (∑ t ∈ Finset.range T, Complex.exp (2 * Real.pi * Complex.I *
    (((q : ℝ) * Opn.E69.signedTailBelow z M P n₀ t : ℝ) : ℂ))) / T
