# erdos-849 formalization review: the 13 mutant questions, answered (agent C, t1026e-c)

Every question reads the same ("A variant of the statement agrees with it on every small case
checked. Is there a case on which the conjecture and this variant should differ?"). The variant
is only recoverable from the exhibit's `detail` ("X → Y at N"), where N is a character offset into
the theorem's type text `∀ t ≥ 1, ∃ a : ℕ,\n      {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ choose n k = a}.ncard = t`
(offset 0 = the leading ∀; verified for all 13 by slicing). Write R(a) = {n | ∃ k ≥ 1, 2k ≤ n ∧ C(n,k) = a}.

"Case" below means an instance (t, a) of the inner claim; the statement is closed, so "small cases"
of the whole proposition do not exist (exhibit e-941bf08c says so).

| q | exhibit | mutation | should the two differ? | case |
|---|---|---|---|---|
| q-1 | e-d9223ecf | `2*k ≤ n` → `2*k < n` | **yes** | drops the middle term k = n/2: a = 6 has rows {4, 6} (C(4,2) = C(6,1) = 6); the variant counts only {6}. a = 2: 1 row vs 0. |
| q-2 | e-608efcbb | `t ≥ 1` → `t > 1` | asks less (t = 1 dropped); equivalent as propositions, since t = 1 holds (a = 2: R(2) = {2}) | t = 1 |
| q-3 | e-fdad4a62 | `k ≥ 1` → `k > 1` | **yes, case by case** (every a ≥ 2 loses its trivial row n = a, k = 1); but the two *propositions* are equivalent: the variant at t is the original at t + 1 | a = 2: 1 vs 0; a = 6: 2 vs 1 |
| q-4 | e-71548e06 | `2*k ≤ n ∧ C = a` → `∨` | **yes**; the variant is provably false: every n ≥ 2 satisfies `2*1 ≤ n`, so the set is infinite and `ncard` = 0 for every a | t = 1, a = 2: 1 vs 0 |
| q-5 | e-ec9b4356 | `∀ t ≥ 1` → `∃ t ≥ 1` | **yes**; the variant is trivially true (t = 1, a = 2) | any t ≥ 2 |
| q-6 | e-b3ee4c7f | `∃ a` → `∀ a` | **yes**; the variant is false (a = 0 has no rows) | t = 1, a = 0 |
| q-7 | e-75029739 | `∃ k ≥ 1` → `∀ k ≥ 1` | **yes**; the variant's set is empty for every a (k large breaks `2*k ≤ n`), so it is false | t = 1, a = 2 |
| q-8 | e-76656d38 | `t ≥ 1` → `t ≥ 0` | adds t = 0, which holds (a = 1: R(1) = ∅); equivalent as propositions. The problem says t ≥ 1 | t = 0 |
| q-9 | e-2134fb23 | `t ≥ 1` → `t ≥ 2` | as q-2: drops the provable t = 1; equivalent as propositions | t = 1 |
| q-10 | e-a045eeda | `k ≥ 1` → `k ≥ 0` | **should** differ at a = 1 (the variant has C(n,0) = 1 for every n: infinitely many solutions; the original none), but **the Lean count cannot see it**: `ncard` of an infinite set is 0, the same as the original's 0. For a ≠ 1 the sets are equal. Same `ncard` for every a | a = 1: ∞ vs 0 solutions, both `ncard` 0 |
| q-11 | e-2014487d | `k ≥ 1` → `k ≥ 2` | as q-3 | as q-3 |
| q-12 | e-e3f6b973 | `2*k ≤ n` → `1*k ≤ n` | the **row** set is unchanged for a ≠ 1 (by symmetry C(n,k) = C(n,n−k), a row reaching a past n/2 already reaches it before); for a = 1, k = n gives every n ≥ 1 (infinite, `ncard` 0, as before). So `ncard` agrees for every a. Under the problem's reading (count *solutions* (n, k)) it **should** differ: a = 6 has 2 solutions with k ≤ n/2, (4,2) and (6,1), and 3 with k ≤ n, adding (6,5). This is the case that shows the root counts rows, not solutions | a = 6 (pairs: 2 vs 3; rows: 2 vs 2) |
| q-13 | e-5d4510d3 | `2*k ≤ n` → `3*k ≤ n` | **yes** | a = 6: C(4,2) has 3·2 > 4, so 2 rows vs 1 |

Two things the review cannot see and the record now carries:

1. **Rows versus solutions.** The words count solutions (n, k); the Lean counts rows n. They agree for
   every a because C(n, ·) is strictly increasing on 0 ≤ k ≤ n/2, so a row holds a at most once in
   range. Kernel-checked as crux `spec-12191c69` (`Opn.erdos_849_rows_eq_pairs`, PR #966 + proof).
   q-12 is exactly the mutation where this matters.
2. **Infinite sets read as 0.** `ncard` is 0 on an infinite set, so a mutation that makes R(a)
   infinite (q-4, q-10, q-12 at a = 1) looks like "no solutions". Harmless for the root, since every
   R(a) lies in [2, a] (crux `spec-38faff03`, `Opn.erdos_849_rows_le`, PR #967), but it is why
   q-10 and q-12 survive every test.

(23:24Z: every 'case' in the table re-checked by brute force over n, k < 60 for a ∈ {1, 2, 6, 10}; one count corrected, q-12's pair count is 3, not 4.)
