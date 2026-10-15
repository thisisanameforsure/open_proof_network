# Tester R (t1015-r) log

- 01:57Z read README, board, yesterday's R.md/bugs.md; cloned graph (d23f6c1f); read guide sections (helpers, check, token, MCP table)
- 01:58Z MCP tools/list: 76.0 s wall (laptop path), 46 tools
- 01:59Z precheck_submission tutorial-and-swap (26.8 s): 202, job queued
- 02:00Z list_frontier: `{"target": ...}` refused `filter-unknown` (field is `target_id`; my error), then 0.9 s ok, rendered_from d23f6c1f; no active claims on erdos-1094
- 02:03Z assembled R1/R2 = `--h2--h2--h2--h2--h1` statement + yesterday's hole_check chain as `private` helpers (defs as `private noncomputable def`)
- 02:03Z check_lean verify R1 (11.1 s): lint `header-diverges` — I had put the helpers above the statement's `/-! Hole … -/` module doc; they must sit between that module doc and `theorem` (the doc is part of the statement)
- 02:04Z check_lean verify R2 (10.8 s): **okay: true, lint []**. Heartbeats per declaration: medFiber_card_le 91,347, med_card_bound 59,401, medJ_card_le 9,016, badSet_subset_biUnion 8,816, card_int_abs_sub_lt_le 8,308, the theorem itself 1,522. `private noncomputable def` passes the helper lint. File: R/Proof-h2h2h2h2h1.lean
- 02:05Z board: P had claimed `--h2--h2--h2--h2--h1` at 02:03Z (before I could: I had no token yet). Dropped it; posted the file's path on the board for P
- 02:06Z get_dco 0.5 s; get_token 75.6 s wall: 201 identity t1015-r (token 0600 in scratch)
- 02:06Z claim_node `{"ttl_hours": 2}` refused `arguments-invalid` (MCP takes `ttl`; I misread the table's mapping direction); retry 1.0 s: 201, claim on `erdos-1094--h2--h2--h2--h3`, others []
- 02:07Z cloned vdT. mediumlarge needs `konyagin_application` → `konyagin_thm` → the whole lattice development (lines 124–3610 of 4693, ~250 kB): over check_lean's 200 kB and far beyond one hour. Plan: partial on `--h3` with one hole `h_kon` = konyagin_application specialised to θ = 21/40 (c₆ written as 65536), everything else (BHP split, dvd_from_far, exists_far_prime, ml_card_bound, ml_rhs_le, lamML lemmas) as private helpers
- 02:11–02:13Z check_lean verify H3p, three rounds (25.5 s, 12.8 s, 16.2 s). Fixes for 4.33.1: lamML_le_lamUB's `convert … using 1; ring` (ring_nf no progress) → calc; ml_rhs_le's `simp_all [g_ml, lamUB]; convert add_le_add … <;> ring_nf` → explicit a1..a4 + expansion + linarith. My own error: a line range that cut a comment open (`unterminated comment`). Result: only lint is sorry-present (the hole). Heartbeats: ml_card_bound 108,320, ml_rhs_le 52,042, dvd_from_far 19,591, rest < 10k
- 02:14Z precheck_submission partial + carried `True` witness for h_kon (50.6 s wall): 202 job 01M4YNDZRG93DKB1NB98BW4GK5 at graph 232e76e9
- 02:18Z get_precheck (polled; one poll 25.6 s): FAIL at step 7 only (steps 1,2,4,5,6 pass). My error: the hole has binders with hypotheses, so its expected_witness is not `True` but `∃ lam n k r, 1 ≤ lam ∧ ↑k < n ∧ 2 ≤ r ∧ ↑r ≤ 1/2 * ↑k ^ (1 - 21/40)`. Round trip passed (expected_new erdos-1094--h2--h2--h2--h3--h1, `r !` printed as `↑r.factorial`). Receipt R/precheck-h3-1.json
- 02:19Z witness: lam=1, n=2^40+1, k=2^40, r=2 ((2^40)^(19/40) = 2^19 via rpow_natCast/rpow_mul). check_lean (1.4 s, then 1.0 s): first `push_cast` evaluated 2^40 to a numeral and broke the rewrite; `rw [Nat.cast_pow, Nat.cast_ofNat]` fixed it, 758 heartbeats
- 02:19Z precheck_submission again (6.5 s): 202 job 01M4YNPJ5RZP5VS0F3PMHC3PGZ
- 02:23Z get_precheck 01M4YNPJ…: **PASS** steps 1,2,4,5,6,7,8; h_kon witness carried, `checked: true`. Receipt R/precheck-h3-2.json
- 02:24Z submit_proof artifact_type partial (5.5 s): 201, **graph PR #528**, hole h_kon → erdos-1094--h2--h2--h2--h3--h1 (expected_new). Receipt R/submit-h3.json. Q then reused the same h_kon text for --h4 (board 02:22Z)
- 02:20–02:31Z drafted the level below (R/K_konyagin_application_partial_draft.lean): the h_kon statement proved from one hole `h_thm` = konyagin_thm with IsGood/intIcc unfolded, c₆=65536; smoothDenom/fK/iteratedDeriv_fK/isGood_fK/KplusN_pow_le/konyagin_application as private helpers. Six check_lean rounds (17.6–53.0 s; a `#check` probe took 75.6 s and 79.4 s, and the first one was refused `target-id-required` without target_id — my error). 4.33.1 fixes: `ContDiffAt.inv` now yields `(fun y => k + y)⁻¹` (Pi inverse), and `iteratedDeriv_const_mul` takes the ContDiffAt first; the hS_sub/hS_good goals changed shape after `norm_num` (`↑w ≤ 1` became `w ≤ 1`), so the IsGood witness is unpacked and recast. Clean bar the hole; konyagin_application 271,205 heartbeats (would have broken the old 200k cap; fits the 1M cap)
- 02:32Z get_submission #528 (5.9 s): **merged** 02:27:58Z, waiting_on products
- 02:32Z get_node erdos-1094--h2--h2--h2--h3--h1 (8.6 s): exists, statement = my h_kon text as printed. claim_node (0.7 s): 201; posted on the board
- 02:33Z K2 = that Statement.lean + the draft's helpers + proof. check_lean verify (16.0 s): clean bar the hole (sorry lints only)
- 02:33Z precheck_submission partial, no witness (8.3 s): 202 job 01M4YPH0…; one get_precheck poll then hung >4 min on the laptop path (a fresh call answered in 1.9 s). Result: **PASS** 1,2,4–8; hole h_thm → new erdos-1094--h2--h2--h2--h3--h1--h1 (konyagin_thm). Receipt R/precheck-K2-1.json
- 02:34Z check_lean probes for the witness (1.1–1.2 s): `rw [deriv_pow]` no longer matches `deriv (fun x => x ^ 2) x`; plain `simp` does
- 02:40Z witness for h_thm: r=2, N=W=δ=lam=D_r1=1, D_r=2, f=x², S=∅ (iteratedDeriv via iteratedDeriv_succ/one + simp). check_lean (2.7 s) okay. precheck again with it carried (4.7 s): 202 job 01M4YPXEA8WNMFYD391X8BFP1G
- 02:44Z get_precheck 01M4YPXE…: **PASS** 1,2,4–8, h_thm witness `checked: true`. Receipt R/precheck-K2-2.json
- 02:45Z submit_proof partial (42.5 s wall): 201, **graph PR #530**, hole h_thm → erdos-1094--h2--h2--h2--h3--h1--h1 (expected_new). Receipt R/submit-K2.json
- 02:45Z release_claim ×2 (0.6 s each): released --h3 and --h3--h1. 02:46Z get_submission #530 (21.1 s): open, gate pending, queue position 1 of 1. Stopped: no time to start another node before 02:51Z

## Report

**What landed**
- **Graph PR #528, merged at 02:27:58Z.** A partial on `erdos-1094--h2--h2--h2--h3`, van Doorn–Tang's (vdT's) medium-large case, stated as "¬BHP ∨ case".
  - Its one hole, `h_kon`, became the new node `erdos-1094--h2--h2--h2--h3--h1`: `konyagin_application` at θ = 21/40, with r general and c₆ written as 65536.
  - The hole is strictly narrower than its parent. It is a pure counting bound: no primes, no BHP, and on its own it does not give the parent.
  - Everything else in the case is proved as private helpers:
    - the BHP case split
    - dvd_from_far
    - exists_far_prime
    - konyagin_finish
    - the λ_ML lemmas
    - ml_card_bound, which takes the hole as a hypothesis
    - ml_rhs_le
  - The hole's witness was carried in the same PR and checked.
  - Q's #529 on `--h4` reuses the same h_kon text.
- **Graph PR #530, open at 02:46Z** (gate pending, position 1 of 1). A partial on that new node `--h3--h1`.
  - Its one hole, `h_thm`, will become `--h3--h1--h1`. That is `konyagin_thm`, with IsGood and intIcc unfolded and c₆ = 65536.
  - The helpers are the smoothing function and its derivative bounds: smoothDenom, fK, iteratedDeriv_fK, abs_iteratedDeriv_r/_r1, key_ratio, isGood_fK, KplusN_pow_le, nat_k_ge_one, konyagin_application.
  - The precheck passed every step, and the carried witness was checked. The witness is f = x², S = ∅.
  - After #530, all that remains under the medium-large case is vdT's lattice argument (Konyagin's theorem itself).
- **No complete proof from me.**
  - I had a fast-checked complete proof of `--h2--h2--h2--h2--h1` by 02:04Z (R/Proof-h2h2h2h2h1.lean, okay true, lint []).
  - P had claimed that node at 02:03Z, before I had a token, so I left it alone and posted the file's path on the board. P landed #527.

**Helpers and the cap**
- **Helpers did help.** Yesterday the medium-case chain did not fit, because inlined it cost 328k heartbeats in one declaration. As helpers it fits easily: medFiber_card_le 91,347, med_card_bound 59,401, the theorem itself 1,522.
- For #528 the largest helpers were ml_card_bound 108,320, ml_rhs_le 52,042 and dvd_from_far 19,591.
- **The 1M cap was needed.** konyagin_application is 271,205 heartbeats as a single helper, over the old 200k cap. It fits the new 1M cap without any rewrite.
- `private noncomputable def` passes the helper lint.

**What a successor needs**
- **`erdos-1094--h2--h2--h2--h3--h1--h1` (konyagin_thm), once #530 merges.**
  - This is vdT's lines 124–3410: the lattice and Hadamard material, successive minima, small_integer_linear_relation, short_interval, and the konyagin_case_* lemmas.
  - That is about 230 kB of source, which is over check_lean's 200 kB limit. It has to be split into further partials, for example making `small_integer_linear_relation` or `short_interval` a hole.
  - P offered on the board to port it.
- **Q's #529 hole duplicates my --h3--h1 if it merges as `--h4--h1`.** The two should become one node, so that one Konyagin proof closes both h3 and h4.
- **4.33.1 fixes from this run**, all in R/K2_partial.lean:
  - `ContDiffAt.inv` returns a Pi inverse `(fun y => k + y)⁻¹`, so the goal needs a funext rewrite to match.
  - `rw [deriv_pow]` no longer matches `deriv (fun x => x ^ 2) x`; plain `simp` does.
  - After `convert … <;> norm_num`, the goal reads `w ≤ 1` (ℕ) rather than `↑w ≤ 1`. Unpack the IsGood result and recast with exact_mod_cast.
  - lamML_le_lamUB and ml_rhs_le: the `convert … ; ring` / `<;> ring_nf` tails fail with "ring_nf made no progress"; rewritten as a calc, and as explicit bounds + expansion + linarith.
- **Placing helpers.** Helpers go *after* the statement's `/-! Hole … -/` module doc and before `theorem`. Above it, the check gives `header-diverges`.

**Bugs and friction**
- *Service:*
  - **Possible duplicate hole node.** #529's hole was planned before #528 merged, so the same statement will become `--h4--h1` beside `--h3--h1`. The holes_note says a hole restating an existing node is that node, but only as planned at precheck time.
  - **A get_precheck call hung for more than 4 minutes** at 02:35Z. The next call answered in 1.9 s. This is probably the laptop path; see below.
- *Slow laptop paths* (sometimes slow, sometimes fast, on the same calls):
  - tools/list: 76.0 s, later 1.0 s
  - get_token: 75.6 s
  - check_lean `#check` probe: 75.6 s and 79.4 s
  - submit_proof: 42.5 s
  - get_precheck: 25.6 s
- *My own errors:*
  - list_frontier with `target` instead of `target_id`.
  - claim_node with `ttl_hours`; the MCP name is `ttl`.
  - check_lean without target_id.
  - A carried `True` witness on a hole with hypotheses (step 7 refused; the expected_witness was ∃ binders ∧ hypotheses).
  - A line range that left a comment unterminated.

**Feature requests**
- **check_lean for skeletons.** A mode that returns `holes[].expected_witness` and runs the round-trip check would have saved one 4-minute precheck per partial. I needed two prechecks per partial only to learn the witness type.
- **Dedupe holes at the post-merge job.** When two decompositions' holes print the same statement, they should become one node, as with #528 and #529.
