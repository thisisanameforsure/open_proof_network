# Witness pilot, lane A — seven refused rows (2026-11-23, 00:21–00:31 IST)

Witness files: `$S/overrides/<id>/Witness.lean`. Checker outputs: `$S/wp-dummy/<id>.*.json`.
Patched row copies (never the originals): `$S/wp-patched/<id>/`. Nothing under the repository was touched.

"Accepted (row)" = `VERDICT ACCEPTED` on the row exactly as drafted. "Accepted (patched)" = the witness
matches the expected type on the real row, but the composed statement fails to compile for a reason outside
the witness; the same witness file is `VERDICT ACCEPTED` on a copy of the row with that one defect removed.

## Summary

| id | accepted | attempts | note |
|---|---|---|---|
| abc | yes (patched) | 1 | `⟨1, by norm_num⟩`; real row fails only in inlined `FieldTheoryMilnorKTheory` (checker strips `theorem of_mul`, which a def body uses) — checker limit, not the witness |
| bing-borsuk-conjecture | yes (row) | 2 | `Unit`, n = 0: metrizable, homogeneous, ANR, covering dimension exactly 0 |
| conjecture | yes (patched) | 1 | `⟨1, 1, …⟩`; real row's `Statement.lean` has `open Arxiv.` (namespace `«1207.5099»` dropped) — a draft defect; plus the Milnor checker limit |
| crystals-components-unique | yes (patched) | 1 | `35 = 5·7` twice, `norm_num [IsCrystalWithComponents]`; real row's defs/ does not port `IsCrystalWithComponents` — port defect |
| erdos-1056 | yes (patched) | 1 | `⟨2, le_refl 2⟩`; same Milnor checker limit as abc |
| erdos-1191 | yes (patched) | 2 | powers of two are an infinite Sidon set (parity-descent proof, ~45 lines); real row fails only in inlined `CombinatoricsBasic` (checker strips `theorem IsSidon.exists_insert_ge`, which `def greedySidon.go` uses) — checker limit |
| erdos-238 | yes (row) | 1 | `⟨1, 1, by norm_num, by norm_num⟩` |

Two rows accepted as drafted; five witnesses match their expected type on the real row and are accepted once
the row's defect is removed. The defects fall in three kinds: (a) `witness_check.py`'s `port_body` strips
theorems from defs/ but keeps defs whose bodies cite those theorems (abc, conjecture, erdos-1056: Milnor
`of_mul`; erdos-1191: `exists_insert_ge`) — the real gate inlines the committed defs whole, so these are
likely fine there; (b) the driver wrote `open Arxiv.` into conjecture's Statement.lean, a syntax error; (c)
the driver ported no `IsCrystalWithComponents` under crystals' defs/ although its record.yaml names it as a
file-local definition.

## abc

Expected: `∃ (ε : ℝ), (0 : ℝ) < ε`. Attempts: 1. Witness `⟨1, by norm_num⟩`.
Real row: `okay false`, `matches true`; errors all at the inlined Milnor K-theory module (`of ℓ 1 = 0`
unsolved, `Unknown identifier of_mul`) — `theorem of_mul` is removed by the checker's theorem-stripping and
the `map_add' := by simp [of_mul]` field of a def still cites it. Copy with that module removed (the
statement does not use it): `VERDICT ACCEPTED` (`wp-dummy/abc.patched1.json`).

## bing-borsuk-conjecture

Expected:
```
∃ (n : ℕ) (X : Type) (inst : TopologicalSpace X),
  MetrizableSpace X ∧ HomogeneousSpace X ∧ IsAbsoluteNeighborhoodRetract X ∧ HasLebesgueCoveringDimensionEq X n
```
Attempts: 2 (first left `V = Set.univ → x ∈ V` unsolved after `simp` in the encard step; fixed with
`rintro rfl; trivial`). Witness: `n = 0`, `X = Unit`; homogeneity by `Homeomorph.refl` and
`Subsingleton.elim`; ANR by `U = univ`, `r = fun _ => ()`; covering dimension `≤ 0` by refining every cover
with `{univ}` (every member is `univ` since `Unit` is a subsingleton), `encard {univ} = 1`; `m < 0` vacuous.
`VERDICT ACCEPTED` on the real row (`wp-dummy/bing-borsuk-conjecture.try2.json`).

## conjecture

Expected (checker gave `witness: null` on the real row; read from the patched copy):
`∃ (x : ℕ) (y : ℕ), (0 : ℕ) < x ∧ (0 : ℕ) < y`. Attempts: 1. Witness `⟨1, 1, by norm_num, by norm_num⟩`.
Real row: `Statement.lean` line `open Arxiv.` is a parse error (`unexpected token '.'; expected command`),
so `EventuallyPeriodic` (defined in `namespace Arxiv.«1207.5099»` of `defs/Local.lean`) is unknown and
`Opn.conjecture` never exists — the driver dropped the guillemet-quoted namespace component. This is a defect
of the drafted statement itself, confirmed with the Milnor module removed alone
(`wp-dummy/conjecture.openonly.json`). Copy with `open Arxiv.«1207.5099»` and the Milnor module removed:
`VERDICT ACCEPTED` (`wp-dummy/conjecture.patched1.json`).

## crystals-components-unique

Expected on the real row is garbage (`∃ (x : Sort u_1) (IsCrystalWithComponents : x) … (hab : sorry) …, True`)
because `IsCrystalWithComponents` is not defined anywhere under defs/ (only `CombinatoricsSimpleGraphInduced`
is ported; the record.yaml itself says "file-local definitions in the statement: IsCrystalWithComponents").
Port defect. Taking the definition from the registry file
(`$S/fc/FormalConjectures/Arxiv/1601.03081/UniqueCrystalComponents.lean`, line 36) into a copy's
`defs/Local.lean`, the expected type is
`∃ (n : ℕ) (a : ℕ) (b : ℕ) (c : ℕ) (d : ℕ), IsCrystalWithComponents n a b ∧ IsCrystalWithComponents n c d`.
Attempts: 1. Witness `⟨35, 5, 7, 5, 7, by norm_num [IsCrystalWithComponents], by norm_num [IsCrystalWithComponents]⟩`
(the registry's own test case). `VERDICT ACCEPTED` on the copy (`wp-dummy/crystals-components-unique.patched1.json`).

## erdos-1056

Expected: `∃ (k : ℕ), k ≥ (2 : ℕ)`. Attempts: 1. Witness `⟨2, le_refl 2⟩`. Real row: `matches true`, same
Milnor checker limit as abc. Copy with that module removed: `VERDICT ACCEPTED`
(`wp-dummy/erdos-1056.patched1.json`).

## erdos-1191

Expected: `∃ (A : Set ℕ), A.Infinite ∧ IsSidon A`. Attempts: 2 (the first run's only error was my own
patch leaving a dangling doc comment before `end Finset`; the witness had no errors). Witness: `A = range
(2 ^ ·)`, infinite by `Nat.pow_right_injective`; Sidon via an inner `have key : ∀ a b c d, 2^a + 2^b = 2^c +
2^d → (a = c ∧ b = d) ∨ (a = d ∧ b = c)` by induction on `a`, eight `rcases` cases per step, `omega` for
parity contradictions (with `Nat.two_pow_pos`) and `Nat.pow_right_injective` where two powers are equal.
Real row: `matches true`, one error at the inlined `CombinatoricsBasic` (`Unknown constant
Finset.IsSidon.exists_insert_ge`: the checker strips the theorem, `def greedySidon.go` cites it). Copy with
the `greedySidon` defs removed: `VERDICT ACCEPTED` (`wp-dummy/erdos-1191.patched2.json`). Note the defs
module also carries `Finset.greedySidon`, an infinite Sidon construction, but no theorem that its range is
Sidon, so it gives no shorter witness.

## erdos-238

Expected: `∃ (c₁ : ℝ) (c₂ : ℕ), c₁ > (0 : ℝ) ∧ c₂ > (0 : ℕ)` (note `c₂ : ℕ` — the registry's `∀ᵉ (c₁ > 0)
(c₂ > 0)` elaborated `c₂` as a natural, which the curator may want to read against the problem's "c₂ > 0"
real constant). Attempts: 1. Witness `⟨1, 1, by norm_num, by norm_num⟩`. `VERDICT ACCEPTED` on the real
row (`wp-dummy/erdos-238.try1.json`).
