# Lane C — witnesses for six refused wave-7 drafts (2026-11-22 22:22–22:26 UTC)

Checker: `witness_check.py` against the network's keyless check route, mode `witness`.
Files: `overrides/<id>/Witness.lean`; checker outputs in `wp-C/<id>.{dummy,a1}.json`.

## Summary

| id | accepted | attempts | note |
|---|---|---|---|
| irrational-odd | yes | 1 | expected `∃ (n : ℕ), (0 : ℕ) < n`; `⟨1, by norm_num⟩` |
| legendre-conjecture | yes | 1 | expected `∃ (n : ℕ), n ≥ (1 : ℕ)`; `⟨1, le_refl 1⟩` |
| min-modulus | no | 1 | port defect, not a witness problem: the inlined `FieldTheoryMilnorKTheory` module fails to elaborate (its `ofHom` def's proof fields cite `of_one`/`of_mul`, theorems `port_body` strips), so `minModulus` never defines and the expected type carries `sorry` plus auto-bound `(x : Sort u_1) (minModulus : x)`; no witness can match a type containing `sorry` |
| polynomial | yes | 1 | expected `∃ g : ℚ[X], 0 < natDegree ∧ integer-valued ∧ eventually positive`; `g = X` |
| two-pow-three-pow-transcendental | yes | 1 | expected `∃ (t : ℝ), Irrational t`; `⟨√2, irrational_sqrt_two⟩` |
| erdos-1004 | yes | 1 | expected `∃ (c : ℝ), c > (0 : ℝ)`; `⟨1, by norm_num⟩` |

## irrational-odd
Expected: `∃ (n : ℕ), (0 : ℕ) < n`. Attempts 1. VERDICT ACCEPTED.

## legendre-conjecture
Expected: `∃ (n : ℕ), n ≥ (1 : ℕ)`. Attempts 1. VERDICT ACCEPTED.

## min-modulus
Expected (as reported, broken): `∃ (x : Sort u_1) (minModulus : x) (x : Sort u_2) (IsValidMod : x) (n : ℕ) (N : ℕ) (A : Finset (ZMod N)), (2 : ℕ) ≤ n ∧ (0 : ℕ) < N ∧ N < sorry ∧ #A = n`.
Attempts 1. VERDICT NOT ACCEPTED.
Last errors (from the inlined defs, not the witness):
- `-:309: unsolved goals … ⊢ of ℓ 1 = 0`
- `-:310: Unknown identifier `of_mul``
- `-:310: unsolved goals … ⊢ of ℓ (a * b) = of ℓ a + of ℓ b`
Reading: a port defect. The statement needs only `minModulus` and `IsValidMod` from `defs/Local.lean`, but the draft also ported four unrelated library modules (Weyl algebra, stable marriage, Milnor K-theory, rational classes). `port_body` removes every theorem from a ported module, and `FieldTheoryMilnorKTheory.lean`'s `def ofHom : Additive Fˣ →+ MilnorK F ℓ` fills `map_zero'`/`map_add'` by `simp [of_one]` / `simp [of_mul]` — theorems that were removed, so the module fails and everything after it (Local.lean's `minModulus`) is never defined. Lean then auto-binds `minModulus`/`IsValidMod` as implicit `Sort` variables and prints the expected type with `sorry`.
The mathematically right witness (n = 3, N = 5 < minModulus 3 = 6, A = {0,1,2} ⊆ ZMod 5) is written in `overrides/min-modulus/Witness.lean` and would be the file to re-check once the port either drops the unneeded modules or keeps the theorems a def's proof fields depend on. Fix belongs in the driver (`port_body`, or the module selection), not here.

## polynomial
Expected: `∃ (g : ℚ[X]), (0 : ℕ) < g.natDegree ∧ (∀ (n : ℕ), ∃ (k : ℤ), eval (↑n : ℚ) g = (↑k : ℚ)) ∧ ∀ᶠ (n : ℕ) in atTop, (0 : ℚ) < eval (↑n : ℚ) g` (written with qualified `Polynomial.`/`Filter.` names; accepted as definitionally equal). Witness `g = X`: `natDegree_X` by simp, `k = n`, positive from n ≥ 1 via `Nat.cast_pos`. Attempts 1. VERDICT ACCEPTED.

## two-pow-three-pow-transcendental
Expected: `∃ (t : ℝ), Irrational t`. `⟨Real.sqrt 2, irrational_sqrt_two⟩`. Attempts 1. VERDICT ACCEPTED.

## erdos-1004
Expected: `∃ (c : ℝ), c > (0 : ℝ)`. `⟨1, by norm_num⟩`. Attempts 1. VERDICT ACCEPTED.
