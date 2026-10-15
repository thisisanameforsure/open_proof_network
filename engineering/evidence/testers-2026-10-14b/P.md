# Tester P (t1014-p) log

- 17:34Z start; read README, board, earlier A.md/port survey; cloned graph, read AGENTS.md sections
- 17:36Z list_frontier (MCP 1.4s) ok, rendered_from 466c11deb; erdos-1094 claimable leaves: --h2--h2--h1 (BHP), --h2--h2--h2--h1..h4 (vdT cases), --h3--h1--h1--h1/h2, --h3--h1--h2--h1/h2
- 17:37Z precheck_submission tutorial (MCP 5.4s) 202 queued
- 17:39Z get_precheck tutorial (MCP 1.9s) done pass; get_dco (0.5s); get_token (MCP 0.6s) 201 pseudonym t1014-p (token in 0600 scratch file)
- 17:39Z claim_node erdos-1094--h2--h2--h2--h1 ttl 2h (MCP 0.7s) 201 claim 01M4XQZJH8KA74JSZ6RSM8AGVQ, others: []
- 17:40Z posted claim on board. Plan: port vdT case_small + exists_prime_in_window + count_beats_excess + poly_log_lt + excess_le + primeCard lemmas, BHP as hypothesis, inline as haves
- 17:41Z check_lean s1 (vdT lemmas, 4.33.1) failed client-side: TLS handshake timeout (laptop path); added retries
- 17:51Z check_lean s1 retry: 1st 502 upstream-unavailable (AXLE 503), 2nd 103s okay=false only in unused poly_log_lt_eq + my truncation: needed lemmas compile at 4.33.1
- 17:57Z check_lean verify+heartbeats (MCP 8.6s) inlined port: primeCard_le_add tail fails at 4.33.1 (rfl/linarith after simp), `atTop` needs `Filter.`; 129k hb
- 17:58Z check_lean verify (12.4s): rest compiles, but 216k hb > 200k cap (timeouts at end of case_small)
- 18:00Z check_lean (13.2s): rewrote case_small with explicit facts: 247k (my nlinarith calls heavier); two parallel measurement checks (V1 prefix only 126k, V2 +setup 155k): `at *` tactics in inlined haves walk every earlier have
- 18:04Z check_lean verify+heartbeats (MCP 9.0s) okay=true, 122k hb (cap 200k): targeted ring_nf, `clear` irrelevant haves, case_small rebuilt with linarith over product facts. log_id 01M4XSC3B0EPR4XRY1PE0QQZ15. Saved P/Proof.lean
- 18:05Z precheck_submission (MCP 4.9s) 202 job 01M4XSDH7RV7ESF5M4DSHY4NMC authenticated
- 18:06–18:09Z get_precheck polls (MCP 1–20s each) → 18:08:58Z done, verdict pass, steps 1,2,4,5,6,7,8 pass (P/precheck.json)
- 18:09Z submit_proof artifact_type=proof (MCP 7.9s) 201 PR #524, submission 01M4XSNVV0K3NJS08DNJFDGG3A
- 18:10–18:13Z get_submission polls (MCP ~1–3s each): waiting_on gate → 18:13:41Z state merged, gate success, waiting_on products
- 18:13Z release_claim (MCP 0.6s) 200
- 18:14–18:17Z get_submission polls: waiting_on products → 18:17:31Z attestation attestations/000524.json
- 18:17Z list_frontier (MCP 1.1s) rendered_from 92b2fe598: --h2--h2--h2--h1 has left the frontier; get_node (MCP 2.0s, include []) status proved, proof present, trust_base kernel
- 18:18Z stopped: not enough time before 18:25Z for another hole

## Report

**What landed (pseudonym t1014-p)**
- PR #524 is a complete proof (`artifact_type: proof`) of `erdos-1094--h2--h2--h2--h1`, i.e. `¬BHP ∨ case_small`: for every 2k < n ≤ ½·k^(2−θ) there is a prime p in (k, k+3k^θ) that divides ∏_{i=1..k}(n−i). It **MERGED** at 18:13:23Z, 3.7 minutes after submission and with no human involved. The attestation is `attestations/000524.json`. `get_node` now gives the node as `proved` (trust_base kernel), and it has left the frontier.
- Precheck job 01M4XSDH7RV7ESF5M4DSHY4NMC passed steps 1, 2 and 4–8 (`P/precheck.json`, nonce removed). Fast check log_id 01M4XSC3B0EPR4XRY1PE0QQZ15, verify mode, okay=true, 122k heartbeats against the 200k cap.
- The Lean is in `P/Proof.lean`: one theorem, no helper declarations, no sorry, no axiom, no native_decide.
- How the proof is built:
  - `generalize (21/40 : ℝ) = θ`, with θ kept abstract.
  - An opaque `pc` stands for the prime-count finset card.
  - `by_cases` on BHP. The `¬BHP` side is closed by rewriting.
  - On the BHP side, vdT's lemmas appear as `have`s: poly_log_lt, excess_le, count_beats_excess, primeCard_le_add, exists_prime_of_primeCard_pos, exists_prime_in_window and dvd_Pprod_of_mem.
  - `case_small` is rewritten so that it uses `linarith` over explicit product facts.
- The claim was taken at 17:39Z and released at 18:13Z.

**What a successor needs next**
- `--h2--h2--h2--h2..h4` are still open. R claimed h2.
- The same recipe should carry over: inline vdT's lemmas as `have`s. The heartbeat cap is the real constraint, not the port.
  - vdT's chain for case_small costs about 133k as separate declarations. Inlined naively it measured 216–247k.
  - The fixes that brought it to 122k:
    - Every `at *` tactic (`simp_all`, `norm_num at *`, `ring_nf at *`, `norm_cast at *`) walks every earlier `have` in the context. So `clear` the unrelated `have`s at the start of each `have` body, and make `ring_nf at *` target its hypotheses.
    - Replace vdT's big `nlinarith`/`grind` closers with `linarith` plus explicit `mul_lt_mul_of_pos_left`/`mul_le_mul_of_nonneg_right` facts.
  - Measure partial versions with the right branch cut to `sorry`; `"heartbeats": true` on `check_lean` makes this quick.
  - At 4.33.1, vdT's `primeCard_le_add` tail fails (`exact add_le_add (by rfl) …` after `simp +zetaDelta at *`). It has to be rewritten using `Int.card_Ico`, `Int.toNat_of_nonneg` and `linarith`; P/Proof.lean has a version that works.
  - `atTop` needs to be written `Filter.atTop`, because no `open` can be added before the theorem.
- The h2 (medium) and h3 (mediumlarge) cases also need `dvd_from_far`, `exists_far_prime` and the Konyagin application. Those fail at 4.33.1 (see testers-2026-10-14/A/port-survey) and are far larger, so expect to have to split them into more skeleton levels.

**Bugs and friction**
- Genuine service issues:
  - One `check_lean` returned `502 upstream-unavailable` ("AXLE check returned 503"; log_id 01M4XRDWHG7RHZ4739AWXYPXPX). The retry succeeded. This is the upstream checker failing, not the service.
- Slow network path (the laptop, not the service):
  - At 17:41Z a `check_lean` died with a TLS handshake timeout during MCP `initialize`.
  - At 17:47Z a `check_lean` took 103 s, where the others took 9–13 s.
  - At 17:37Z one `get_precheck` took 21.6 s.
- My own errors:
  - My first slice of vdT's file cut a comment in half and failed to parse.
  - A build-script edit put a literal newline into a Python string. This cost one check, which then ran on a stale file.
  - My first `clear` named a hypothesis that `obtain` had already consumed.
  - My first `case_small` rewrite used `nlinarith` everywhere and cost more heartbeats than vdT's original.
- Friction:
  - The 200k cap applies to the whole proof, and helper declarations are refused, so a port that works as separate lemmas has to be re-tuned for heartbeats. Most of my hour went to that, not to mathematics. The `heartbeats` measurement is what made it tractable.
  - The `push_neg` deprecation warning at 4.33.1 is noise; `push Not` works.
- Every network call went through the MCP. No plain HTTP use was needed.

**Feature requests**
1. A per-`have` (or per-tactic-block) heartbeat breakdown in `check_lean`'s `heartbeats` output. Today only top-level declarations are measured, so locating the expensive part of a single inlined proof takes several bisection checks.
2. Let a proof file carry `private` helper lemmas (checked by the same gate), or count the cap per declaration. That would let a long external development be ported as written instead of re-tuned for one shared budget.
