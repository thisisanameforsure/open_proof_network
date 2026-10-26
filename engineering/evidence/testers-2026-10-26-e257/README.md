# Three agents on erdos-257 for three hours — 2026-10-26 20:20Z to 23:20Z

Three background subagents of one session (pseudonyms `t1026-a`, `t1026-b`, `t1026-c`), briefed by
`BRIEF.md`, coordinated on `COORDINATION.md`, logs in `A.md`, `B.md`, `C.md` with working files under
`A/`, `B/`, `C/`. No Aristotle this run. The graph queue was empty at launch; the laptop read 4% battery
and stayed up. Every agent finished with its final report as the last section of its log.

## What landed (all through the service, nothing hand-pushed; graph PRs #959–#1032)

**A, refutation side (`spec-a70fcca4-v2`, "1/2 is the sum of an infinite set"), 18 PRs, all merged.**
- #987 partial on `spec-a70fcca4--h4--h1--h2`: decided for every skipped m ≤ 100 by a kernel computation of
  the greedy walk; one hole `--h4--h1--h2--h1` (the same for m > 100).
- #1003 partial on `spec-a70fcca4--h4`: the run lemma in Lean reduces "never stalls" to "skips infinitely
  often", child `--h4--h2`.
- #1026 partial on `--h4--h2` whose single hole restates `--h4--h1--h2`, so the record carries the lemma
  edge W(3m+2) ⟹ W(∞) ⟹ --h4: a proof of `--h4--h1--h2--h1` (m > 100) closes --h4 along both routes.
- Postmortems #991, #1004; eight witness glosses; three explainers.

**B, known results into Lean (`variant-5274cf38--h1`, Luca–Tachiya purely periodic), 6 PRs, 5 merged.**
- #981 partial: Erdős 1948 adapted with f_B; one hole `--h1--h1` = quantitative Dirichlet (not in Mathlib).
- #1024 second partial: weighted averaging; its one hole `--h1--h2` is provable from the pinned Mathlib
  by the cyclotomic argument (route written in the hole's comment and B.md 21:50Z). ~300 lines owed.
- #982 postmortem; literature records #983, #1013, #1032 (the last in its gate at hand-off).
- Tao–Teräväinen hole: read, nothing filed (the existing postmortem already says what is needed).

**C, affirmative core (`erdos-257--h18`, `--h2--h1`) and reader, 20 PRs, 19 merged.**
- Four proved cruxes proposed for `--h18`, the Chowla–Erdős digit method as reusable nodes:
  `spec-137537c8` (Lambert identity for any set), `spec-23b0fff0` (tail integrality), `spec-689ac1ac`
  (block divisibility), `spec-ced1e7c5` (weighted block divisibility, Erdős 1968's form); each with gloss
  and explainer (#1030 open at hand-off).
- Postmortems #1014 (`--h2--h1`: the digit method's smallness half cannot reach a greedy set) and #1015
  (`--h18`); annex #978 (one wrong bullet) corrected by #986; explainer #961 of the `--h2` partial.

## Findings to verify (lead has not yet verified any; see each log's `## Findings`)

Recurring across all three: a partial's precheck is refused `409 products-pending` for every render on
the target (5–6 min, paid repeatedly); the open-PR cap and `-- approach:` 300-char cap are undocumented;
proof gates 15–17 min and products ~10 min behind a merge. B-F2: the fast check's 20 s budget cannot
elaborate a complete Mathlib-scale proof (764 lines → `504 check-timeout`). A-F8: a restating hole must
stand before `intro`, else it closes over the binders twice and becomes a new node. C-F6: precheck
accepted then `dep-unproved` on a node the frontier calls claimable. C-F2: the open core's node shows 0
attempts while five postmortems sit on its parent. B-F4: a literature record claims a Lean proof that is
nowhere on the record. A-F3/C: node pages show neither open submissions nor claims.

## Unfinished business

- Prove `variant-5274cf38--h1--h2` from Mathlib (B's recipe); then retire the `--h1` route (#981).
- Supersede A's two unanchored explainers once the outlines of #987 and #1003 exist.
- `A/partial100-h1.lean` (W(2m) base case) exists, never prechecked; near-duplicate, submit only if wanted.
- C: annex #978 cannot be withdrawn (409); #986 corrects it in words. `C/zero-block.lean` is vacuous, do not file.
- Compare B's #981/#1024 with the "Aristotle proof" t1022-d's literature record claims.
