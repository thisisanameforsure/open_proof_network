# green_41.variants.polynomial_bound — own target (parent not importable)

**Decision: import as its own target, stated as the registry states it, titled as a variant of
Green's Problem 41 (the pyjama covering problem).**

Row: `fc:FormalConjectures/GreensOpenProblems/41.lean#green_41.variants.polynomial_bound`
(registry pin d8d031d4998c78575159ccab9a7a9e95ce043883, `research open, question`).

## Facts
- Parent `green_41 : ∀ ε > 0, minCopies ε = green_41.answer ε` is `research open, question
  value`: it asks for an unknown *function*, stated against `def green_41.answer : ℝ → ℕ :=
  sorry`. It cannot be imported faithfully (choosing the answer is choosing an unknown value,
  rule 1) and is not live. So this open, fully stated question is the natural target.
- The sibling `green_41.variants.double_exponential_bound` is also `research open` and would be
  curated the same way; it is not in my rows. The polynomial bound implies the double-exponential
  one, so if both are imported, the double-exponential one is a `partial` variant of this.

## Proposed record
- title: `Ben Green's Open Problem 41: a polynomial bound for the pyjama problem (a variant of
  Green's Problem 41)`
- informal: `Is ε^(−C) rotations enough? That is: is there a constant C such that, for all
  sufficiently small ε > 0, at most ε^(−C) rotated (about the origin) copies of the pyjama set
  {(x, y) : dist(x, ℤ) ≤ ε} cover the plane? Green's Problem 41 asks for the minimal number of
  rotations as a function of ε; Manners (2015) showed finitely many suffice and Kravitz–Leng (2025)
  gave the first bound, exp exp exp(ε^(−C)).`
- source: formal-conjectures `FormalConjectures/GreensOpenProblems/41.lean`, Apache-2.0; Green,
  100 open problems, Problem 41.

## Files
- `defs/Local.lean`: `pyjamaSet`, `coveringCopies`, `minCopies` byte for byte, in `namespace
  Green41` with the file's `open Complex Set Pointwise`; module doc and header kept.
  **Left out: `def green_41.answer : ℝ → ℕ := sorry`** (a port may not carry `sorry`; the variant
  does not use it). This is why the driver could not port the file mechanically.
- `Statement.lean`: `open Complex Set Pointwise`, `open Green41`, `theorem
  Opn.green_41_polynomial_bound : ∃ C : ℝ, ∃ ε₀ > 0, ∀ ε ∈ Ioc 0 ε₀, (minCopies ε : ℝ) ≤ ε ^ (-C)`
  — byte for byte.
- `Witness.lean`: `True := trivial` (no binders).
- `hazards.yaml`: `off-by-one-range` at `Set.Ioc 0 ε₀`, justified.

## Differences from the registry text
- Theorem name `Opn.green_41_polynomial_bound`; module doc. The `answer` placeholder left out of
  the port. Proposition unchanged. Note (not a change): `minCopies` is `sInf` of a set Manners
  proved nonempty; the registry's own `minCopies_set_nonempty` is `research solved` with `sorry`,
  so the definition's junk value 0 for an empty set never matters mathematically.

## Checks
- Compile (autoImplicit off, defs + statement + witness): `POST /check` log
  `01M89FXTTGFCC8WPR24AF91WKH`, errors `[]`.
- Hazards on a probe with the same quantifier prefix and `minCopies` replaced by an inline `sInf`
  (`01M89FWPP8ERDGD4AY4AMN95FK`, `hazards_status: ran`): one finding, `off-by-one-range
  Set.Ioc 0 ε₀`.

Sources: the registry file; wave.py (`draft_row`'s sorry-def refusal).
