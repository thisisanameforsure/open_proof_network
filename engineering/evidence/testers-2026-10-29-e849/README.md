# Three agents on erdos-849 through the MCP, 2026-10-29 (13:15Z–16:15Z)

Lead: Claude (this session). Agents: A near-diagonal shapes and the open core, B the nine (k,l) pairs, C audit,
Lean on call, the MRSTT check and words. Brief in `BRIEF.md`, board in `COORDINATION.md`, logs `A.md`–`C.md`,
the 10-27 run in `prior/`. Every contribution went through the MCP; nobody pushed or merged by hand. A laptop
network outage took 13:23Z–14:42Z from all three agents (not the service, which kept merging).

## Outcome on the record

All on the refutation skeleton `variant-3969f1f7` (Singmaster bounded, which refutes the root). Eleven partials,
all merged, each assembly proved in Lean, each new hole one exactly cited statement:

- **Pairs (B, A).** Six of the nine solved pairs of BBdW Thm 2.2 now rest on one integral-points statement each:
  (2,3) on LMFDB 1611.a1 (#1168), (3,4) on 37.a1 (#1171), (2,6) on 14475.a1 (#1175), (4,6) on 232425.a1 (#1179),
  (2,5) on BMSST 2008 Thm 2 (#1174), (3,6) on Stroeker–de Weger's cubic (#1178). Left: (2,4), (2,8), (4,8), whose
  reductions give quartics, sourced only in Stroeker–de Weger Math. Comp. 1999 Table 1, which no agent could fetch.
- **Near-diagonal shapes (A).** C(n,k) = C(n−1,k+2) and C(n,k) = C(n−2,k+1) now rest on Stroeker–de Weger 1999
  (Acta Arith. 87) Thms 3 and 4 (#1166, #1167).
- **The open core (A).** Cut three times: Yamada 2020 Thm 1.1, an unrefereed preprint, so the record says so
  (#1172); Nagura 1952 with a prime-separation lemma proved in Lean (#1180); Schoenfeld 1976 through Dusart's
  survey, built and prechecked by A and submitted by the lead after the window (see below). What remains for
  n > 4,021,520 is collisions with m > 16597n/16598 or k < n/16598, or inside Yamada's window.
- **MRSTT Prop 1.9 (C).** The 10-27 postmortem said §3 had no stated intermediate results; it has Lemma 3.1 and
  Prop 3.2. #1173 splits Prop 1.9 into Lemma 3.1 (elementary), Prop 3.2 (the analytic core) and the §3 case
  analysis (elementary). Prop 1.10 has no honest split; its postmortem stands.
- **Audit (C).** All 16 gate-written holes are `Iff.rfl` to their partial's `have`. Every integral-point list was
  checked against an exact integer search over a stated range: no point missing or extra.
- **Words.** Literature records on every new named hole, explainers of every assembly, postmortems on every node
  worked, two self-contained superseding glosses.

## Finished by the lead after the window

- Filed B's seven held appends (#1222–#1226, #1228, #1229) and C's four explainers (#1218–#1221) under their
  authors' tokens, once #1179's replay and #1180's bot commit had landed.
- Submitted A's Schoenfeld partial on `--h2--h1--h4--h2--h3--h2--h2` (precheck 01M646757G66B16VGQ1NK4321K, pass)
  under A's token after the appends had merged: #1232, merged 16:20:06Z, `gate: #1232 pass` by 16:29Z. Its
  holes `--h3--h2--h2--h1` (Schoenfeld) and `--h3--h2--h2--h2` (the rest) are on main, ready; the Schoenfeld
  hole reads exactly as A's `have`. With the lane empty, the attestation landed first time.

## Findings, verified by the lead where marked

1. **[bug, confirmed] A partial's attestation push is still starved by appends (prior #1, three times today).**
   #1179's run 40902300897 was rejected at 15:41:38, 15:42:55, 15:44:12, 15:45:29 and ended 15:46:48Z "the gate
   commit was refused 6 times; its merges are replayed"; replay 40904999533 landed at 16:05Z. #1175 waited 15 min.
2. **[bug, confirmed] Appends overtake a partial that is first in the lane.** #1180 (created 15:07:24Z, first and
   gating from 15:33Z per A) merged at 15:47:20Z; appends created 15:15–15:18Z merged before it, #1181 at
   15:36:12Z through #1198 at 15:41:31Z, each pushing it back to "behind". This is also why contributors cannot
   keep the quiet-window rule (A F-A7, C F-C6): appends filed while quiet merge minutes later, inside the next
   partial's job. Only the merge actor can hold them; the append hold Mike approved on 10-28 is the fix.
3. **[bug, confirmed] One GitHub 503 kills a post-merge job with no retry.** #1171's run 40894548804 failed at
   14:45:22Z on `gh: HTTP 503` while fetching the pull request body; it was attested only by a replay at 15:12Z.
4. **[bug, confirmed] A replayed merge writes no outline.** Neither #1171's nor #1179's outline is on main, so
   their explainers cannot name steps (`400 explainer-step-unknown`), while `list_words_needed` still asks for them.
5. **[bug, agent] A hole stated with a set literal (`∀ N ∈ ({…} : Set ℝ)`) is refused `hole-not-roundtrip`**: the
   printed hole drops the ascription (C F-C1). Same family as the 10-14 finite-set binder.
6. **[feature, agent] The 20 s fast check cannot check a whole partial with a long case split** (B F-B2).
7. **[still present] Prior #2 and #3**: `409 products-pending` for 6–8 minutes, and no precheck of level n+1
   until level n renders (A F-A1, F-A4, B F-B3). Plus one lane per target serialises unrelated subtrees (A F-A5).
8. **[docs, agent]** a claim line must end with `$` (C F-C2); a long parent conclusion does not fit a claim line
   (A F-A2); `le_or_lt` is `le_or_gt` at the pinned Mathlib (B F-B4, known).

## What a steward should do next

- Confirm the literature records, which stay `drafted` until signed. The Yamada record is a preprint.
- The three quartic pairs need Stroeker–de Weger Math. Comp. 1999 Table 1 in hand.
- Lemma 3.1 and the §3 deduction under MRSTT Prop 1.9 are elementary but long; postmortem #1200 has the plan.
