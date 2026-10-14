# Tester R (t1014-r) log

- 17:34Z start; read README, board (only lead line), prior run's bugs.md, A/B/C logs, port survey
- 17:37Z cloned graph (main 466c11deb); read leaf statements of erdos-1094; guide sections (check, token, claim, MCP appendix)
- 17:38Z MCP tools/list (3.9 s) ok, 44 tools
- 17:39Z list_frontier target erdos-1094 (2.0 s): rendered_from 466c11deb; claimable leaves: --h2--h2--h1 (BHP itself), --h2--h2--h2--h1..h4 (vdT cases), --h3--h1--h1--h1/h2, --h3--h1--h2--h1/h2 (residue classes); --h1 already proved
- 17:39Z precheck_submission tutorial-and-swap (no token): 147.6 s wall (laptop path stall), 202 job queued at graph bae0f835
- 17:40Z cloned vdT repo (Woett/ChatGPT-s-note-on-Erdos451) to scratch
- 17:43Z board: P claimed --h2--h2--h2--h1 (case_small) at 17:40Z, so I ruled it out. Candidate: --h2--h2--h2--h2 (vdT case_medium: elementary fibre count + BHP, no Konyagin)
- 17:44Z assembled R/med_test.lean: vdT's case_medium chain (badSet, medJ, medFiber, poly_log_lt, exists_far_prime, dvd_from_far, konyagin_finish, med_*) with `bhp` turned into a hypothesis `BHP`
- 17:46Z check_lean med_test.lean (24.2 s, then 2.2 s): 502 upstream-unavailable "AXLE check returned 503"; tiny `1+1=2` file (18.2 s): same 502. The fast checker is down upstream (AXLE), not my text
- 17:51Z check_lean tiny (5.0 s): okay again; AXLE outage lasted roughly 17:46–17:51Z
- 17:52Z check_lean R/med_test.lean (separate declarations, 22.3 s): only 3 errors, all "`ring_nf` made no progress" (dvd_from_far, poly_log_lt_eq, med_rhs_le); everything else in the case_medium chain elaborates at 4.33.1
- 17:52Z check_lean the same chain inlined as `have`s/`let`s inside the node's single theorem (13.3 s): whole-declaration "(deterministic) timeout at whnf, 200000 heartbeats" plus a simp timeout and let-unfolding side effects (mkRat). The chain does not fit one declaration's budget as written
- 17:54Z get_precheck tutorial: done, pass (job ran ~4 min). My own error: I looked for the nonce in get_precheck; it is only in the POST answer (I had saved it, 0600)
- 17:55Z get_token (2.8 s) 201, identity t1014-r (token in 0600 scratch file)
- 17:57Z claim_node erdos-1094--h2--h2--h2--h2 ttl 2 h: 201 in 77.2 s wall (laptop path; curl to /health at 17:54Z connected in 0.19 s), claim 01M4XRYXF0HQT36K477N0H9WMK, others: [], open_submissions: []
- 17:57Z posted the claim on the board
- 17:59Z check_lean med_test2 (+heartbeats, 81.8 s): fixed dvd_from_far and poly_log_lt_eq by hand (the `ring_nf` sites); per-declaration heartbeats of the whole chain sum to ~221k: medFiber_card_le 89.6k, med_card_bound 59.2k, dvd_from_far 19.7k, exists_far_prime 8.8k, the rest small
- 18:01Z check_lean med_test3 (14.3 s): med_rhs_le's final `convert … ; ring` replaced by obtain + linarith; linarith needed `C*x/y = 3*(C/3*x/y)` stated (fixed in med_test4)
- 18:02–18:06Z partial assembly R/R_med_partial.lean, five check_lean rounds (4.9–79.3 s; the 79 s one was a slow AXLE answer, not connect). Fixes: one extra paren in my hole statement; `clear * -` must name the intro'd hypotheses too (my error); exists_far_prime rewritten by hand (vdT's `simpa [abs_of_pos]` now meets `Nat.cast_natAbs`/`mkRat` forms at 4.33.1). Result: elaborates with the single hole sorry, 74k heartbeats
- 18:07Z check_lean R/R_med_full.lean, everything inlined incl. the counting chain (19.7 s): 328,344 heartbeats against the 200k cap, plus simp-at-* side effects. A complete proof of --h2--h2--h2--h2 does not fit one declaration without rewriting medFiber_card_le/med_card_bound; not doable by 18:25Z. Going for the partial (allowed after 18:10Z): one hole `h_count` = vdT's med_card_bound expanded (a pure counting bound on the bad set, no BHP, no primes), strictly narrower than the parent
- 18:08Z check_lean R/hole_check.lean (17.3 s): okay true. The whole multi-declaration chain (med_test4 + `theorem hole_is_vdT : <my hole statement> := med_card_bound`) elaborates at 4.33.1 with no sorry, so the hole is true and its proof exists; it only has to fit one declaration
- 18:10Z precheck_submission partial on --h2--h2--h2--h2 with a carried `True := trivial` witness for h_count (6.6 s): 202, job 01M4XSPW281BPM0JBV883KD32X at graph bae0f835
- 18:11–18:14Z tried the child alone (R/R_child.lean: the hole's statement with the counting chain inlined, defs made opaque via `obtain ⟨x, hx⟩ : ∃ x, x = … := ⟨_, rfl⟩` so simp/norm_num cannot zeta-unfold them): two rounds (5.7 s, 89.9 s), still a whole-declaration heartbeat timeout inside medFiber_card_le. Stopped; this is the successor's job
- 18:14Z get_precheck 01M4XSPW… (4.7 s): FAIL at step 4, `hole-not-roundtrip` on h_count. Expected witness True, expected node --h2--h2--h2--h2--h1. My diagnosis via check_lean (R/rt.lean, 71.9 s): the printed `{m ∈ Finset.Ioo (↑k : ℤ) … | (↑m : ℝ) < … }` elaborates m as ℝ (LocallyFiniteOrder ℝ fails), because the first conjunct does not pin m's type
- 18:16Z added a type-pinning first conjunct `(k : ℤ) < m` to the hole (redundant on Ioo k _); the assembly now proves badSet = the new filter by Finset.filter_congr. check_lean (7.3 s): only the hole's sorry
- 18:17Z precheck_submission again (5.7 s): 202, job 01M4XT3P78ZB575AWR3W161317
- 18:20Z get_precheck 01M4XT3P… (3.0 s): PASS, steps 1,2,4,5,6,7,8 pass; h_count → expected_new erdos-1094--h2--h2--h2--h2--h1, expected_witness True, carried witness checked: true; step 6 findings are on the derived statement (div-zero etc.), passed as `hazards-derived-statement`
- 18:21Z submit_proof (precheck_job_id): no answer within my 150 s client timeout. get_my_submissions at 18:23Z (1.7 s; host read 18:22:46Z) showed nothing open, so nothing had been created; curl /health connected in 0.15 s
- 18:24Z submit_proof retry (6.0 s): 201, PR #526, submission 01M4XTG7K0GAQ7YMYCX3JVZ9DW, hole h_count → --h2--h2--h2--h2--h1 (expected_new)
- 18:24Z posted on the board. Stopped starting new work
- 18:25Z release_claim (9.0 s) 200; get_submission #526 (41.2 s, slow path): open, merge queue position 2 of 2, behind Q's #525

## Report

**What landed (pseudonym t1014-r)**
- **Graph PR #526**: a *partial* on `erdos-1094--h2--h2--h2--h2`, vdT's medium range: k^(2−θ)/2 < n ≤ k²/log²k, as "¬BHP ∨ case". It was open in the merge queue at 18:25Z, position 2 of 2 behind #525. Precheck job 01M4XT3P78ZB575AWR3W161317 passed every step (1, 2, 4–8), and the carried `True` witness was checked.
  - **The assembly is kernel-checked.** It runs `by_cases` on BHP, then vdT's medium-case argument: dvd_from_far, exists_far_prime (rewritten), konyagin_finish, poly_log_lt/poly_log_lt_eq, med_rhs_le, case_medium. It uses 74k heartbeats.
  - **One hole, `h_count`, becomes `erdos-1094--h2--h2--h2--h2--h1` (new).** It says: for large k and n in the medium range, the "bad set" (integers m in (k, k+k^θ) with n/m within k^(θ−1) of an integer) has fewer than 3 + 56·k^(2θ−1) + k^θ·log(k)^(−2) elements. That is vdT's `med_card_bound`.
  - **The hole is strictly narrower than its parent.** It is pure counting: no BHP, no primes, and on its own it does not give the parent.
- **No complete proof.** I measured why. The whole chain inlined into the node's one theorem (R/R_med_full.lean) took 328,344 heartbeats against the 200k cap. The same lemmas as separate declarations total about 221k, and two of them dominate: medFiber_card_le (89.6k) and med_card_bound (59.2k).
- **The hole is true, and its proof exists.** R/hole_check.lean, which is vdT's chain as separate declarations plus `theorem hole_is_vdT : <the hole> := med_card_bound`, elaborates at 4.33.1 with no sorry (check_lean okay: true, 18:08Z). It just does not fit inside a single declaration yet.
- **The claim is released.**
- **Files** in R/:
  - med_test4.lean: vdT's medium chain with my 4.33.1 fixes.
  - hole_check.lean
  - R_med_partial.lean: what was submitted.
  - R_med_full.lean: over the cap.
  - R_child.lean: my unfinished attempt at the child.
  - partial.1.witness

**What a successor needs next**
1. **Prove `--h2--h2--h2--h2--h1` once #526 merges.**
   - Start from R/R_child.lean. It is the hole with the counting chain inlined, and its defs are made opaque by `obtain ⟨x, hx⟩ : ∃ x, x = … := ⟨_, rfl⟩`, so that simp and norm_num cannot zeta-unfold them.
   - It still times out inside medFiber_card_le. That lemma needs a cheaper proof: its long `nlinarith [...]` calls and the `simp_all +decide` steps are the cost. Or split it into a further skeleton level.
   - The rest of the chain is about 85k heartbeats.
2. **Fixes I made for 4.33.1**, which may help whoever ports the other vdT cases:
   - dvd_from_far: replaced `convert … <;> push_cast <;> ring_nf`.
   - poly_log_lt_eq: replaced the `norm_cast; norm_num; ring_nf … grind` tail.
   - med_rhs_le: obtain + linarith, with `C·x/y = 3·(C/3·x/y)` stated explicitly.
   - exists_far_prime: rewritten. vdT's `simpa [abs_of_pos]` now meets `Nat.cast_natAbs` and `mkRat` forms.
   - Inlining: `clear * - <deps> <intro'd names>` before each `have`'s proof.
3. **Round-trip rule for holes.** Every set-builder in a hole must pin its bound variable's type in the first conjunct. `{m ∈ Finset.Ioo (k:ℤ) … | (↑m : ℝ) < …}` prints in a form whose m re-elaborates as ℝ, so the hole is refused with `hole-not-roundtrip`. The parent's `(0 : ℤ) < p ∧ …` is why it is safe. I added `(k : ℤ) < m ∧` and closed the difference with `Finset.filter_congr`.

**Bugs and friction**

*Genuine service issues:*
- **AXLE outage.** From about 17:46 to 17:51Z, every `check_lean`, including a 1+1=2 file, answered `502 upstream-unavailable` ("AXLE check returned 503"). The fault is upstream, and the network reported it clearly.
- **`hole-not-roundtrip` points at the wrong cure.** The refusal's hint ("ascribe the type where a bound variable or a numeral is used") was right in spirit. But my hole's text was already fully ascribed; it is the *printer's* set-builder that loses `m : ℤ`. A one-line note in the hint about set-builder binders would have saved the diagnosis round. This was F07-R19 doing its job, and it caught the problem before the merge.

*Slow network paths* (this laptop, not the service; curl to /health connected in 0.15–0.19 s at the same times):
- tutorial precheck POST: 147.6 s
- claim_node: 77.2 s
- get_submission: 41.2 s
- several check_lean answers of 70–90 s. These look like slow AXLE answers rather than slow connects.
- My first submit_proof never answered within 150 s and created nothing (get_my_submissions confirmed it). The retry answered in 6.0 s with 201.

*My own errors:*
- I looked for the tutorial nonce in `get_precheck`. It comes only in the POST answer; I had saved it.
- An extra parenthesis in the hole statement.
- `clear * -` without the intro'd names, which cleared the lemma's own hypotheses.

**Feature requests**
- **A heartbeat-budget planner.** `check_lean` with `heartbeats: true` on a multi-declaration file gives per-declaration counts, which was very useful. A note that a single theorem's cap counts the *sum*, plus the inlining overhead (here 221k as separate declarations became 328k inlined), would set expectations before porting.
- **Check a hole's round trip from `check_lean`.** A `check_lean` mode for skeletons that runs the hole extraction and its round-trip check would avoid a 4-minute precheck to find a `hole-not-roundtrip`.
- **Allow helper declarations, or explain how to split instead.** Their absence is the binding constraint for ports of large outside developments like vdT's. Failing that, the guide could say how to split a long lemma chain across holes.
- 18:26Z get_submission #526 (3.9 s): open, now position 1 of 1 in the erdos-1094 lane (#525 ahead of it has left the queue). Not merged when I stopped
