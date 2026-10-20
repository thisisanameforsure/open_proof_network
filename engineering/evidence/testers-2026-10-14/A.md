# Tester A (t1014-x) log

- 11:05Z start; read board; cloned graph + vdT repo
- 11:06Z get_node erdos-1094--h2--h2--h2 (MCP, 7.4s) ok; POST /precheck tutorial (4.2s) 202 queued
- 11:09Z check_lean skel.lean (4.5s): elaborates; only sorry warnings + push_neg deprecation (renamed to `push Not`)
- 11:08Z precheck tutorial done; get_token (MCP 0.9s) 201 pseudonym t1014-x (token in 0600 scratch file)
- 11:08Z claim_node erdos-1094--h2--h2--h2 ttl 2h (0.7s) 201 claim 01M4X1KNBG7P2A1AQSWKCSGQ2P
- 11:09Z submit_informal_annex (MCP 7.2s) 201 PR #511 annex 9fe3bccd… (annex/v2, steps h_small h_medium h_mediumlarge h_large)
- 11:10Z check_lean cited skeleton (76.9s — TCP stall, laptop path) elaborates, only sorry
- 11:09:59Z PR #511 annex MERGED (40 s after submit)
- 11:11Z precheck_submission partial (MCP 7.6s) 202 job 01M4X1QT5GHARKZWJE0NS5HN3D at graph 6f958ee (no products-pending)
- 11:13Z first chunk survey of vdT file via check_lean: chunker bug (cut `let ... :=` in statements); chunk 0 (lines 40-449, real code) shows 5 genuine 4.33.1 failures; 3 chunks 504 check-timeout; re-running at 200-line chunks
- 11:17Z get_precheck (1.7s) done: verdict pass, steps 1,2,4,5,6,7,8 pass; 4 holes listed
- 11:18Z precheck_submission partial + 4 carried witnesses (True := trivial, expected_witness True per first precheck) 202 job 01M4X24MAGX3CD68FBM6NVECQ5
- 11:21Z chunk survey (21 chunks x ~200 src lines, earlier decls sorried, check_lean mode check): so far chunk 0 dvd_from_far (ring_nf no progress), hadamard_inequality, gramDet_le_prod_sq_norms fail; chunk 1 bezout_generalized (▸ on Ideal.span); chunk 6 three lattice lemmas; chunk 7 clean; chunks 2,4 504 check-timeout (20 s budget); latencies 8-96 s (TCP stalls on laptop path)
- 11:23Z get_precheck job 01M4X24M… done: verdict pass; 4 witnesses checked: true
- 11:23Z submit_proof partial (MCP 8.4s) 201 PR #519 submission 01M4X2E8XG7NZQ8EA9C8RYG79Z; holes → --h2--h2--h2--h1..h4 expected_new
- 11:24Z chunk survey complete (chunk 3 retried after a urllib connect error, 14.7s): 36 declarations fail at 4.33.1, 15 of them `ring_nf made no progress`, 9 `rewrite` pattern misses; chunks 2 and 4 (src 512-842, 1057-1259) 504 check-timeout, unmeasured. Saved A/port-survey-4.33.1.txt
- 11:24Z propose_literature --h2--h2--h2 status known (MCP) 201 PR #521
- 11:25Z hypothesis test: `ring_nf`→`try ring_nf` on chunks 15, 18 (12-14 s) changes nothing: the errors are `ring` failing to close (its ring_nf fallback reports "no progress"), e.g. after `convert ... using 1; ring` in med_rhs_le — goal shapes changed, real per-site fixes

## Report

**What landed (pseudonym t1014-x)**
- PR #511, annex on `erdos-1094--h2--h2--h2` (annex/v2, hash 9fe3bccd…, steps h_small, h_medium, h_mediumlarge, h_large): MERGED 11:09:59Z, 40 s after I submitted it.
- PR #519, skeleton (partial) on `erdos-1094--h2--h2--h2`, citing #511 and carrying all four witnesses (`True := trivial`, which matches the precheck's `expected_witness: True`). Precheck job 01M4X24MAGX3CD68FBM6NVECQ5 passed: steps 1, 2, 4–8 pass and every witness `checked: true`. The PR was OPEN, waiting on `gate`, at 11:26Z. Expected new nodes:
  - `--h2--h2--h2--h1` = ¬BHP ∨ case_small (2k < n ≤ k^(2−θ)/2)
  - `--h2--h2--h2--h2` = ¬BHP ∨ case_medium (k^(2−θ)/2 < n ≤ k²/log²k)
  - `--h2--h2--h2--h3` = ¬BHP ∨ case_mediumlarge (k²/log²k < n ≤ k^(2+θ)/2)
  - `--h2--h2--h2--h4` = ¬BHP ∨ case_large, the Konyagin step (k^(2+θ)/2 < n ≤ exp(log²k/(20 log log k)))

  The assembly is fully proved: it takes ¬BHP if any hole gives it, and otherwise does vdT's three `by_cases` on n. Each hole is in its own `refine` bullet, so no hole inherits another (`proved_binders: []`). No hole implies the parent alone, because each covers one range of n.
- PR #521, literature proposal `known` on `--h2--h2--h2`, citing vdT 2026 and their Lean repo. The summary says plainly that "their Lean statement matches this node" is my reading of the two texts, not a machine check. OPEN at 11:26Z.
- Claim 01M4X1KNBG7P2A1AQSWKCSGQ2P was taken at 11:08Z and released at 11:25Z.
- Evidence in A/: skeleton.lean, annex.md, w.1.witness, precheck-skeleton-{1,2}.json (nonce removed), port-survey-4.33.1.txt, and chunk.py / map.py (the survey tooling).

**What a successor needs next**
1. Once #519 merges, prove the four holes. Each one is "¬BHP ∨ case", so a proof does `by_cases` on BHP and then ports that case's lemma. Easiest first:
   - h1 (case_small): needs `exists_prime_in_window` and `dvd_from_far`.
   - h2 / h3 (medium / mediumlarge): fibre-count bounds plus `konyagin_finish`.
   - h4 (large): needs `konyagin_thm`, the lattice and successive-minima block (lines ~135–3410 of their file). It is the largest by far.
2. Helper declarations are refused at the gate. Every lemma has to be inlined as a `have` inside the hole's single theorem, and the whole proof is capped at 200k heartbeats. For h4 this almost certainly means more skeleton levels: split `konyagin_thm` into its own holes rather than proving it in one go.
3. Port survey at Lean 4.33.1 (port-survey-4.33.1.txt). I split their file into 21 chunks of about 200 lines, with earlier declarations reduced to `sorry`, and fast-checked each one.
   - **Failures:** 36 declarations fail as written. 15 errors are "`ring_nf` made no progress" and 9 are "`rewrite` did not find the pattern"; the rest are type mismatches, `simp` no progress, `introN`, and `linarith`.
   - **Not just a rename:** I tested `ring_nf` → `try ring_nf` on two chunks and it fixed nothing. The errors come from `ring` failing to close a goal after things like `convert … using 1`, and its fallback reports "no progress". The goal shapes changed, so each site needs a real fix.
   - **Clean:** chunks 7 (src 1686–1904) and 16 (src 3710–3913) elaborate.
   - **Unmeasured:** chunks 2 (src 512–842) and 4 (src 1057–1259) hit `504 check-timeout`. They need smaller pieces.
   - **Failing lemmas the case proofs need directly:** `dvd_from_far` (all four cases), `ml_card_bound`, `ml_rhs_le`, `med_rhs_le`, `large_card_raw`, `large_term3_le`, `large_asym`, `large_r0_bounds`, `large_r_data`.

**Bugs and friction**
- No genuine service bug seen. Every route answered as the guide says: annex 201 → merged in 40 s; precheck 202 → done in about 6 and 5 min; submit 201; claim and release 200/201; literature 201.
- Environment (laptop network path, not counted as service bugs):
  - check_lean at 11:10Z took 76.9 s.
  - Two chunk checks around 11:13Z took 84.7 s and 96.3 s.
  - At 11:14Z, `curl GET /precheck/<id>` failed with "Connection timed out after 30003 ms".
  - One chunk check died with a urllib connect error; it took 14.7 s on retry.
- Friction:
  - Carrying witnesses cost a second full precheck (about 5 min). `expected_witness` is only learned from a first precheck, even when it is `True`, which happens whenever the parent has no binders.
  - My own client cut the submit_proof output short at 2500 characters (my mistake, not the service's).
- Feature requests:
  - (a) A way to fast-check a large external development. 330 kB is over the 200 kB cap, and 200-line chunks still run past the 20 s budget. A "survey" mode that reports failures per declaration would have saved the chunking tool.
  - (b) A `check_lean` mode that returns a skeleton's holes with `expected_witness`, so witnesses can be carried after one precheck instead of two.
- 11:27Z final check: #519 OPEN (gate running), #521 OPEN. Stopping.
