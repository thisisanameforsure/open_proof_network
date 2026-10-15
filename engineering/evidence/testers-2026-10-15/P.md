# Tester P (t1015-p) log

- 01:56Z start; read README, board, yesterday's P/Q/R logs; cloned graph; read guide (check, helpers, token, MCP appendix)
- 01:58Z list_frontier (MCP 5.3s) rendered_from d23f6c1; --h2--h2--h2--h2--h1, --h2--h2--h2--h3, --h4 ready, no active claims
- 01:58Z precheck_submission tutorial (MCP 6.7s) 202; done by 02:00Z
- 02:00Z get_dco (MCP 68.6s, slow path), get_token (1.6s) 201 t1015-p (token 0600 in scratch)
- 02:02Z claim_node erdos-1094--h2--h2--h2--h2--h1 ttl 2h (MCP 78.4s slow path) 201 claim 01M4YMRCBGD0YWKM4W5ETQ42PR, others []
- 02:03Z posted claim on board
- 02:03Z assembled P/Proof.lean: R's 2026-10-14b hole_check.lean chain, only what med_card_bound needs (theta, badSet, medWindow, medFiber, medJ, g_med as `private noncomputable def`; theta_pos/lt_one, eventually_le_rpow, card_int_abs_sub_lt_le, badSet_subset_biUnion, medJ_card_le, medFiber_card_le, med_card_bound as `private lemma`), then the node's theorem: obtain med_card_bound, filter_congr for the extra `(k:ℤ) < m` conjunct, simpa [g_med, theta]
- 02:04Z check_lean verify node_id + heartbeats (MCP 13.4s) okay=true FIRST TRY, lint [], 0 errors/warnings. log 01M4YMTRH0Y6QNRYB8WFXJB1BV. Heartbeats: medFiber_card_le 91,348; med_card_bound 59,401; medJ_card_le 9,016; badSet_subset_biUnion 8,816; card_int_abs_sub_lt_le 8,308; the theorem itself 1,820 (cap 1,000,000 each)
- 02:04Z precheck_submission (MCP 5.0s) 202 job 01M4YMV948J5WYT0G6BE7KCQQK authenticated, graph 232e76e
- 02:05–02:08Z get_precheck polls (MCP, ~1.5 min per poll incl. slow path): done 02:08Z, verdict PASS, steps 1,2,4,5,6,7,8 pass (P/precheck.json, nonce removed)
- 02:08Z submit_proof artifact_type=proof (MCP 6.6s) 201 PR #527, submission 01M4YN3EV83EMB54XE36V2P5QH
- 02:09Z posted submission on board. R had claimed --h2--h2--h2--h3 (02:06Z), Q --h2--h2--h2--h4 (02:09Z)
- 02:10Z claim_node --h2--h2--h2--h4 sent before I saw Q's post; first attempt TLS handshake timeout (laptop path), retry answered 201 at 02:14:33Z with others=[t1015-q]. Released at 02:15:02Z (release_claim 1.7s 200). Never worked on h4.
- 02:13Z board: offered to port vdT's konyagin_thm (needed by both h3 and h4) as a private-helper block
- 02:15–02:25Z Konyagin survey: split vdT lines 40–3625 (136 declarations, 208 kB after stripping comments; > the 200 kB check limit, so cannot be fast-checked whole), checked 14 chunks in parallel with every earlier declaration stubbed `:= by sorry` (check_lean mode check, heartbeats true). Run 1: 2 chunks 504 check-timeout, 12 answered with errors (P/konyagin-chunk-survey-run1.txt). ~5 errors per chunk were my stubber's bug (it cut at a `let x : T :=` in a statement); the rest are real 4.28→4.33.1 drift: `ring_nf` made no progress, simp no progress, rewrite pattern not found (Finset.prod_* / rpow lemmas), Type mismatch after simplification (Fin.castLT, Subtype.coe_injective), `Matrix.rank` equation lemmas, interval_cases leftovers.
- Heaviest measured declarations (count_heartbeats, no cap): annihilator_short_vectors 141,913; gramDet_product_is_square 136,469; gramDet_projected_identity 128,300; comparison_with_vanishing 104,984; int_vector_primitive_extends_unimodular 88,996. All far under the 1,000,000 cap — vdT's `set_option maxHeartbeats 3200000/8000000` lines are not needed at that scale for these (the 504 chunks were not measured).
- 02:26Z fixed the stubber, rechunked to 21 smaller chunks, relaunched. Then my session stalled: the next command returned at 04:09Z (wall clock jumped ~1h40m; laptop/session, not the service). Run 2 partial results (7 of 21 chunks, errors down to 0–4 per chunk) in P/konyagin-chunk-survey-run2-partial.txt.
- 04:09Z get_submission #527: state merged, attestation verdict pass, trust_base kernel, merge commit 14c4ddb, signed 02:17:12Z
- 04:11Z release_claim (MCP 74.3s, slow path) 200; get_node --h2--h2--h2--h2--h1 status proved. Stopped; window was already over.

## Report

**What landed (pseudonym t1015-p)**
- **Graph PR #527: a complete proof of `erdos-1094--h2--h2--h2--h2--h1`. MERGED.** That node is vdT's `med_card_bound`, the count bound for the medium range. The gate attestation was signed at 02:17:12Z, about 8 minutes after submission, with no human involved: merge commit 14c4ddb, verdict pass, trust_base kernel. `get_node` now gives the node as `proved`. With R's partial #526 from yesterday, this should close `--h2--h2--h2--h2`, the medium case.
- Precheck job 01M4YMV948J5WYT0G6BE7KCQQK passed steps 1, 2 and 4–8 (P/precheck.json). Fast check log 01M4YMTRH0Y6QNRYB8WFXJB1BV, verify mode, okay=true, lint [], on the first try.
- The Lean is in P/Proof.lean, 16.6 kB:
  - Only what `med_card_bound` needs from R's 2026-10-14b `hole_check.lean`, copied unchanged.
  - Six `private noncomputable def`s: theta, badSet, medWindow, medFiber, medJ, g_med.
  - Nine `private lemma`s.
  - The theorem body is 13 lines: obtain `med_card_bound`, then `Finset.filter_congr` to absorb the node's extra `(k:ℤ) < m` conjunct, then `simpa [g_med, theta]`.
- The time from claim to submission was 6 minutes.

**Did helpers and the cap help? Yes, decisively.**
- Yesterday this node could not be proved: the same chain inlined into one theorem took 328k heartbeats against a 200k cap.
- As private helpers it went through unchanged. The per-declaration heartbeats were:
  - medFiber_card_le 91,348
  - med_card_bound 59,401
  - medJ_card_le 9,016
  - badSet_subset_biUnion 8,816
  - card_int_abs_sub_lt_le 8,308
  - the node's theorem 1,820
- Helpers alone would have been enough here: every declaration was under even the old 200k cap. The 1M cap matters for vdT's Konyagin lattice lemmas. I measured the heaviest of them at up to 142k (annihilator_short_vectors), and vdT's file gives some of them `maxHeartbeats` 3.2M or 8M.
- `private noncomputable def` was accepted in the helper block.

**What a successor needs**
- What remains under h3 and h4 is `erdos-1094--h2--h2--h2--h3--h1--h1`, the hole of R's #530, which is `konyagin_thm`. That is vdT's lattice development: about 136 declarations from lines 120–3410.
- The development is 208 kB even with comments stripped, which is over the fast check's 200 kB limit. So it can only be fast-checked in chunks, with earlier declarations stubbed as `sorry`. My split.py and mkchunks.py in P/ do that, with the stubber fixed for `let` in statements.
- P/konyagin-chunk-survey-run1.txt lists the 4.33.1 errors per chunk. Discount the "unexpected token 'lemma'" lines: they are my stubber's bug.
- Run 2 used smaller chunks and shows 0–4 real errors per chunk for the first 7 chunks it reported.
- Expect the usual 4.28→4.33.1 drift: `ring_nf` and `simp` making no progress, rewrite patterns not found, `Matrix.rank` equation lemmas, and `Fin.castLT` mismatches.
- Chunks of about 13 kB of the lattice code exceed the 20 s budget (504). Keep chunks to 6 kB or less in the first half.
- Whether the whole Konyagin file fits the gate's own per-step time limit is untested.

**Bugs and friction**
- *Service:* none seen. Every MCP call answered as the guide says.
- *Slow path (laptop):*
  - get_dco took 68.6 s.
  - claim_node took 78.4 s.
  - release_claim took 74.3 s.
  - One TLS handshake timed out.
  - At 02:26Z my session stalled for about 1 h 40 min: a single tool call returned at 04:09Z. That is the local machine or session, not the network. Because of it I missed the window, and the claim was released at 04:11Z, not by 02:51Z.
- *My own errors:*
  - I sent claim_node on h4 before re-reading the board. Q had posted it a minute earlier. I released it on receipt and never worked on it.
  - My body-stubber cut at `let x : T :=` inside statements, so about a third of the errors in run 1 were mine.
- *Friction:*
  - The fast check's 200 kB limit is smaller than one real external development, vdT's Konyagin: 330 kB raw, 208 kB stripped.

**Feature requests**
1. A fast-check mode that takes a library prefix by hash, or a raised size limit for `check` mode. Then a large helper block can be checked without hand-stubbing.
2. A way to fast-check one declaration in a file, with everything earlier assumed. That is what my stubber does, and the service could do it reliably.
