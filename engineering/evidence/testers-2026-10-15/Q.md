# Tester Q (t1015-q) log — erdos-1094, 2026-10-15

- 01:56Z read README, board (lead line only), yesterday's P/Q/R reports; cloned graph to scratch (main 232e76e9 per precheck).
- 01:58Z note: `../testers-2026-10-14/A/port-survey-4.33.1.txt` named in the brief does not exist under opn-cap/engineering/evidence (no testers-2026-10-14 directory). Cloned vdT's repo instead.
- 01:59Z list_frontier with `target_id` (MCP, 70.3 s, slow path): `arguments-invalid` (my error: list_frontier takes no target_id). get_token with only pseudonym (4.6 s): `arguments-invalid`, proof required (my error: read the token section first).
- 02:00Z precheck_submission tutorial-and-swap, no token (MCP, 72.1 s): 202 job 01M4YMM4… at graph 232e76e9.
- 02:01Z list_frontier (MCP, 23.3 s): 25 erdos-1094 entries, none with an active claim. `--h2--h2--h2--h2--h1` (med_card_bound) claimable.
- 02:02–02:06Z get_precheck tutorial (MCP, 40.6 s for one poll; slow path): done, pass. get_dco (1.6 s).
- 02:07Z get_token pseudonym t1015-q (MCP, 1.7 s): 201 (token in a 0600 scratch file).
- 02:08Z claim_node erdos-1094--h2--h2--h2--h3 ttl 1 h (MCP, 78.2 s, slow path): 201, but `others` named t1015-r, and the board showed R's 02:06Z claim. My error: I chose while my claim call was in flight and did not re-read the board first. Released.
- 02:09Z claim_node erdos-1094--h2--h2--h2--h4 ttl 1 h (MCP, 21.0 s): 201 claim 01M4YN3V…, others []. Posted on the board.
- Plan: a complete proof needs konyagin_thm (vdT lines 135–3626, ~3500 lines of lattice/successive-minima machinery, ~250 kB) — beyond the 200 kB fast check and the hour. Fallback per the brief: a partial whose single hole is vdT's `konyagin_application` (a pure counting bound for |n/m − round(n/m)| < k^{θ−1} over the window, no BHP, no primes), with the large-case assembly (lamLarge, large_card_raw, large_asym, r0L, large_r_data, case_large, konyagin_finish, exists_far_prime, dvd_from_far) as private helpers.
- 02:10Z check_lean without target_id (1.9 s): 400 `target-id-required` (my error; added target_id).
- 02:11Z check_lean mode check + heartbeats on T1 (vdT's large-case chain as plain declarations, konyagin_application as a test-only axiom; 63.4 s): 4 errors, all one 4.33.1 shape: `convert … using 1` now leaves an instance goal first (`case e'_2: Real.instLT = Real.partialOrder.toLT`), so the next `rw`/`ring` hits it. Every declaration under 100k heartbeats (max large_r_data 86.6k).
- 02:12–02:14Z two more checks (24.6 s, 22.7 s, 22.4 s): fix is `try (case e'_2 => rfl)` after each such convert; large_card_raw also needed `all_goals first | rfl | (rw [hT1, hT2]; ring)`. okay true, lint [].
- 02:15Z built the partial: everything as `private lemma`/`private noncomputable def` helpers between the statement's module comment and the theorem; `open`/`noncomputable section` removed; konyagin_application replaced by hypothesis `KonHole` (bridged by `kon_of_hole`, which rewrites c₆ = 65536 and drops a type-pinning conjunct `(k:ℤ) < m` with Finset.filter_congr). Theorem body: `have h_kon : <Konyagin bound> := sorry; by_cases hB : BHP; Or.inr (case_large h_kon hB) | Or.inl hB`.
- 02:15Z check_lean verify + heartbeats (23.2 s): `504 check-timeout` (the heartbeat copy doubles the work). 02:16Z again (45.1 s): one error, bare `Tendsto` (the helper block cannot `open Filter`). 02:17Z after qualifying (23.0 s): errors 0, lint only sorry-present/sorry-reported (expected for a partial). Max declaration large_r_data 95.3k heartbeats; theorem itself 776.
- 02:19Z precheck_submission artifact_type partial with carried witness `True := trivial` for h_kon (MCP, 85.4 s, slow path): 202 job 01M4YNQ9… at graph 14c4ddba.
- 02:20Z board: R's partial on --h3 uses a hole h_kon = konyagin_application at θ = 21/40 (c₆ = 65536). Re-stated my hole as R's exact text (θ fixed, `Nat.factorial`) so the two holes are one statement and, by the guide's restatement rule, should become one node: one Konyagin port then closes both. kon_of_hole now takes `th = theta`.
- 02:21Z check_lean verify (26.7 s): errors 0, sorry lint only. precheck_submission v2 (22.7 s): 202 job 01M4YNV5…. (v1 job 01M4YNQ9… kept unused.)
- 02:26Z get_precheck v2 (polled, 1.9–3.5 s each): done, FAIL at step 7 only (steps 1, 2, 4, 5, 6 pass). My error: the carried witness was `True`, but this hole has binders with hypotheses, so `expected_witness` is `∃ lam n k r, 1 ≤ lam ∧ (k:ℤ) < n ∧ 2 ≤ r ∧ (r:ℝ) ≤ ½·k^(1−21/40)` (expected_new erdos-1094--h2--h2--h2--h4--h1, restates null since R's #528 node does not exist yet). Witness: lam = 1, k = 2^40, n = 2^40 + 1, r = 2 (k^(19/40) = 2^19).
- 02:27Z check_lean on the witness (79.0 s, slow path): two errors of mine (push_cast evaluated 2^40 before the rpow rewrite; push_cast had already closed the first goal). Fixed by rewriting Nat.cast_pow by hand.
- 02:30Z check_lean witness (133.1 s wall, slow path): okay true. (Same witness R carried for #528, written independently.)
- 02:30Z precheck_submission v3 with the real witness (MCP, 8.9 s): 202 job 01M4YPBC… at graph 14c4ddba (R's #528 not yet merged, so my hole still plans as a new node).
- 02:35Z get_precheck v3 (polled): done, PASS, steps 1, 2, 4–8 pass; h_kon → expected_new erdos-1094--h2--h2--h2--h4--h1, carried witness checked: true. Saved nonce-free as Q/precheck-partial.json.
- 02:35Z submit_proof artifact_type partial (MCP, 10.9 s): 201, graph PR #529, submission 01M4YPMQ…. Planned at 14c4ddba, so h_kon is a *new* node even though it is the same statement as R's #528 hole (--h2--h2--h2--h3--h1); see the report.
- 02:36–02:41Z get_submission 529 polls (MCP, ~4 s each): waiting_on gate (queue position 1 of 1) → merged by 02:41Z, waiting_on products. No human involved.
- 02:37Z get_submission 528 (R's): merged, h_kon became erdos-1094--h2--h2--h2--h3--h1.
- 02:45Z get_submission 529 after products (MCP, polled): merged, attestation attestations/000529.json, and h_kon **became erdos-1094--h2--h2--h2--h3--h1**: the post-merge job recognised that my hole restates R's #528 hole, although the precheck and the submit answer (planned at 14c4ddba) said expected_new --h4--h1. No duplicate node.
- 02:45Z release_claim h4 (MCP, 1.7 s): 200. The 02:09Z release of my stray --h3 claim had answered 200 (70.3 s). list_my_claims (20.7 s): none active. Stopped; no new work started after 02:46Z.

## Report

**What landed (pseudonym t1015-q)**
- **Graph PR #529**: a *partial* on `erdos-1094--h2--h2--h2--h4`, vdT's large range ½k^(2+θ) < n ≤ exp(log²k / (20 log log k)), written as "¬BHP ∨ case". **It MERGED** at about 02:40Z with no human involved. The attestation is `attestations/000529.json`.
  - Precheck job 01M4YPBC… passed steps 1, 2 and 4–8, and the carried witness was checked. The nonce-free result is `Q/precheck-partial.json`; the receipt is `Q/submit-receipt.json`.
  - **The assembly is kernel-checked.** It is vdT's whole large case:
    - lamLarge, E1exp, lamLarge_pow/_ge_one/_lt
    - large_card_raw, large_term1/3_le, large_asym
    - r0L, large_r0_bounds, large_r0_P, large_r_data, case_large
    - konyagin_finish, exists_far_prime, dvd_from_far, the poly_log lemmas
    - the BHP split
  - **One hole, `h_kon`.** It is vdT's `konyagin_application` at θ = 21/40 with c₆ = 65536: a pure counting bound on {m in the window : |n/m − round(n/m)| < k^(θ−1)}, with no BHP and no primes. It is strictly narrower than the parent and does not give the parent on its own.
    - I copied the hole's text verbatim from R's #528 hole.
    - The precheck planned it as a new node `--h4--h1`, but after the merge it **became the existing node `erdos-1094--h2--h2--h2--h3--h1`**.
    - So h3 and h4 now wait on one node, and one Konyagin proof closes both.
  - The carried witness is lam = 1, k = 2^40, n = 2^40 + 1, r = 2.
- **No complete proof.** Each of h3 and h4 needs `konyagin_thm`, which is vdT lines 135–3626: about 3500 lines of lattice and successive-minima machinery, roughly 250 kB. That is over the fast check's 200 kB limit and far more than an hour's port.
- **Files** in `Q/`: `partial.lean` (submitted), `partial.1.witness`, the precheck JSON and the receipt.

**Did the helpers and the cap help? Yes, decisively.**
- **Helpers.** vdT's large-case chain went in almost as written: 26 `private lemma` / `private noncomputable def` declarations. It took 6 fast checks from a raw slice to a clean file, and none of the time went into heartbeat tuning. Yesterday's testers spent most of their hour on exactly that tuning.
- **Cap, at 4.33.1 per declaration:**
  - largest: large_r_data 95.3k, large_r0_bounds 77.3k, large_r0_P 39.4k, large_asym 38.3k, large_card_raw 37.9k
  - the theorem itself: 776
  - So everything fit the old 200k cap per declaration. What mattered was **per-declaration counting plus helpers**, not the 1000k figure. Inlined, the sum (about 400k) would have blown even 200k.
- **Fixes for 4.33.1** (`private`, `noncomputable` and `/-- -/` doc comments on helpers are all accepted):
  - `convert … using 1` now leaves an instance goal first (`case e'_2: Real.instLT = Real.partialOrder.toLT`), which breaks the next `rw` or `ring`. `try (case e'_2 => rfl)` after the convert fixes it in 5 places.
  - Bare `Tendsto` must be written `Filter.Tendsto`, because the helper block cannot `open`.

**What a successor needs**
- **Prove `erdos-1094--h2--h2--h2--h3--h1` (konyagin_application).** R claimed it at 02:32Z and is splitting it, with konyagin_thm as the next hole. That one node now closes both #528's and #529's parents.
- `konyagin_application` itself is vdT 3567–3625 plus fK and smoothDenom (3415–3566). The remaining mass is `konyagin_thm`.

**Bugs and friction**
- *Service: none seen.* Check, precheck, carried witness, submit 201, merge queue, products and release all behaved as the guide says.
  - One thing to note: the precheck's and the submit answer's `expected_new: true` / `expected_node_id --h4--h1` turned out wrong in the good direction. The post-merge job deduplicated against a node that a merge between my precheck and my merge had created. The `holes_note` says planning is "as of graph commit X", so this is documented, but a sentence saying that restatement is re-derived at merge would have spared me the worry.
- *Fast check:* `check_lean` with `heartbeats: true` on the 45 kB file answered `504 check-timeout` once (02:15Z). The identical request passed a minute later in 45 s with full per-declaration figures, so it was close to the 20 s budget, not over it. Correction to my 02:16Z log line: that retry also carried `heartbeats: true`.
- *My own errors:*
  - `list_frontier` with `target_id`, `get_token` without a proof, and `check_lean` without `target_id`: three 400s from not reading the argument shapes first.
  - I claimed `--h3` without re-reading the board while my claim call was in flight (78 s). R had posted it at 02:06Z, so I released it at once.
  - I carried a `True` witness for a hole with hypothesised binders. That failed step 7 and cost one precheck round. The fix is to precheck without a witness first, or to derive `expected_witness` from the hole's binders.
  - Two witness tactic slips: `push_cast` evaluated `2^40`.
- *Slow laptop paths* (connect and TLS, not the service): list_frontier 70 s, the tutorial precheck POST 72 s, claim_node 78 s, a release 70 s, check_lean up to 133 s for a 10-line witness, precheck POST 85 s. The same calls took 2–25 s at other times.
- *Brief:* `../testers-2026-10-14/A/port-survey-4.33.1.txt` does not exist under `opn-cap/engineering/evidence/`.
- *Not acted on, worth a look:* three blocked holes (`--h2--h2--h3--h1`, `--h2--h1--h1--h1`, `--h2--h1--h4--h1`) have Witness.lean `theorem witness : True := by sorry`. A one-word `trivial` witness proposal would unblock each. I left them alone as outside the brief.
- Every network call went through the MCP; no plain HTTP was used.

**Feature requests**
1. `check_lean` mode `partial`: run the hole extraction and return `expected_witness` and the restatement match, so the witness type is known before the first precheck.
2. Make `heartbeats: true` measure within the 20 s budget by counting only the declarations the caller names, or give it a separate budget.
3. Show claims in `list_frontier` in real time. My in-flight claim on a node R had just claimed returned 201 with `others: [t1015-r]`; refusing it, or at least warning, would be better.
