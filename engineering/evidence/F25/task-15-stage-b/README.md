# F25-T15 Stage B — the first port of erdos-1050 to the registry's toolchain (2026-10-11)

Run: `.github/workflows/palomar-port.yml` on pull request #30, run 38117047393 (ubuntu-24.04),
graph commit 5ff1734785078226f8a808b954f10a64145bbd3b (origin/main), toolchain
leanprover/lean4:v4.35.0-rc2, Mathlib v4.35.0-rc2, classification and licence by flag (Q15).

## What happened
- Stage A on the runner: exported `OpnErdos1050` (closure `erdos-1050--h1-v2--h3`, `erdos-1050--h1-v2`,
  `erdos-1050`; three siblings pruned), `export.json` beside this file.
- `lake update mathlib`: ok (Mathlib resolved at v4.35.0-rc2). `lake exe cache get`: ok (8915 files).
- `lake build`: **failed in `OpnErdos1050.Nodes.erdos_1050__h1_v2`** (845-line proof merged at Mathlib
  0df444a / Lean 4.33.1). `erdos_1050__h1_v2__h3` built with deprecation warnings only; the root's
  `Solution.lean` was not reached. Comparator did not run. `port-report.json` carries the whole build output.

## The failures, as the classifier read them (32 rows)
- 29 `deprecated` warnings: `if_pos`/`if_neg` → `ite_eq_left`/`ite_eq_right`, `Polynomial.eval_finset_sum` →
  `eval_finsetSum`, `Finset.prod_le_prod'` → `prod_le_prod` (warnings at rc2; errors at a later toolchain).
- Three errors, all in `erdos_1050__h1_v2.lean`, the repair a person or agent owes before Comparator can run:
  1. line 507: `Finset.prod_le_one` no longer takes the per-element bound as an explicit function argument
     ("Function expected … ∏ i ∈ ?m, ?m i ≤ 1"); the `linarith` inside it then fails for want of the goal.
  2. line 526: `le_of_lt (hlt L _)` — `hlt` proves `0 < 2^K − 2^L` where `2^K − 2^L < 2^K` is expected: a
     lemma's argument order or the `hlt` binding changed between Mathlib pins. Lean also notes
     "definitions were not unfolded because their definition is not exposed: Real.instLT" — the module
     system's exposure rule reaching a proof that leaned on unfolding an instance (Q33).
  3. line 624 (info): `ring` failed to close a goal and suggests `ring_nf`; whether it is an error depends on
     the tactic state once 507 and 526 are repaired.

## What this says
The decomposition model's analytic proof ports with a handful of textbook renames and three real edits; the
Challenge is frozen and untouched. The repair loop runs on the runner (each round ~10 minutes with the cache):
edit the proof bodies, dispatch the workflow with the wrapper's patch, read `port-report.json`. It was not run
in this sitting (laptop disk 4–6 GiB free; Mathlib needs 7). Q3's decision stands: no submission of erdos-1050.
