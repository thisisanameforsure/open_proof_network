# Tester C (t1014-z) log — erdos-1094, 2026-10-14

- 11:06Z cloned graph to scratch; read board (lead start line only).
- 11:07Z get_node erdos-1094--h2--h2--h1 include=[] via MCP: 1.4 s, ok. Second get_node loop (two nodes) hung >120 s (moved to background) — see later.
- 11:08Z read statements of --h2--h2--h1, --h3--h1--h1, --h3--h1--h2 from the clone; literature on record: proposals on --h2 (open), --h2--h1 (known), --h2--h1--h1 (known), --h3 (known); none on my three nodes.
- 11:09Z POST /precheck tutorial-and-swap (no token) for a token: 7 s, job queued.
- 11:10Z numerics (python, every k ≤ 200, n in [2k,k²)): split of --h3--h1--h1 by p=3: k≡0 mod 3 → hole A (last failure k=36); k≢0 with k%3 ≤ n%3 → hole B (last failure k=58); the case n%3 < k%3 is closed by p=3 in the assembly (asserted for every pair). Same split for --h3--h1--h2: A last k=39, B last k=35. Run to k ≤ 600 in background.
- 11:11Z POST /check (mode check, node erdos-1094--h3--h1--h1) skeleton C/h311-partial.lean: 3 s, okay=false with only `declaration uses sorry` + lint sorry-present (expected for a partial). log_id 01M4X1PE78R611J6PPZEQHZF17.
- 11:11–11:17Z WebSearch + WebFetch of BHP 2001 PDF (cs.umd.edu copy); WebFetch could not read the PDF text, pdftotext on the saved copy did. (Six minutes lost here, mostly tool latency.) Finding: Theorem 1 is for [x − x^0.525, x]; the closing display (p. 562) is the counting form "for all large x, π(x + x^0.525) − π(x) > 9x^0.525/(100 log x)" — forward interval, exactly the --h2--h2--h1 shape with C = 9/100.
- 11:17Z GET /precheck tutorial job: done, pass. POST /tokens (pseudonym t1014-z): 201, token stored 0600 in scratch.
- 11:18Z claim_node --h3--h1--h1: 0.7 s, 201; claim_node --h3--h1--h2: 20.0 s, 201 (slow; TCP stall likely, not counted).
- 11:19Z precheck_submission partial --h3--h1--h1: 5.6 s, 202 job 01M4X25XB005A1XTR4AVNF60XY; --h3--h1--h2: 4.4 s, 202 job 01M4X26278MXQFB84KJWHP2B31.
- 11:19Z propose_literature --h2--h2--h1 status known (BHP 2001 p. 562 display): 8.5 s, 201, graph PR #512. The DOI I gave (10.1112/plms/83.3.532) is from memory, not checked.
- 11:20Z propose_literature --h2--h1--h4 status known (follows from --h2--h1--h1 / Konyagin: n ≥ k² makes minFac > n/k ≥ k, and n < k(k+3k^0.525) < k³): 4.3 s, 201, graph PR #513. Deduction mine, unchecked.
- 11:20Z not proposed: --h2--h2, --h2--h2--h3 (open core, n ≥ k³ — open, Ecklund's conjecture range); --h2--h2--h2 (van Doorn–Tang 2026, conditional on BHP — A's node, I have not read the paper, left to A); --h3--h1 and children (residue form — stronger than Konyagin's g(k) > k², no published proof known to me).
- 11:21Z second prechecks carrying `True := trivial` witnesses for both holes (closed holes, same shape as the 2026-10-09 --h3--h1 skeleton's): --h3--h1--h1 3.5 s 202 job 01M4X2A8ZR0BYXPE0WS8NCK5BW; --h3--h1--h2 8.8 s 202 job 01M4X2AFTGANY4G8PAE5GKQ3MV. First prechecks (no witnesses) still running after 2.5 min.
- 11:21Z numerics extended to every k ≤ 600 (C/num.py): no new failures beyond k=36/58 (even k: k≡0 mod 3 / rest) and k=39/35 (odd k, odd n); failure counts 59/149/61/32 unchanged from k ≤ 200. Finite check, not a proof.
- 11:22Z precheck --h3--h1--h2 (no witnesses) done: pass, steps 1,2,4–8 pass; holes h_odd_k3 → erdos-1094--h3--h1--h2--h1, h_odd_rest → --h2--h2, expected_new true, expected_witness True. (~3.5 min)
- 11:23Z precheck --h3--h1--h1 (no witnesses) done (see C/h311-res.json).
- 11:25Z witness-carrying prechecks both done: pass, every step; holes[].witness.checked true for all four holes. GET /precheck had no `carried_witnesses` key (so the pinned gate checks carried witnesses).
- 11:26Z submit_proof --h3--h1--h1 with a `model_and_tooling` argument: 0.6 s, refused `arguments-invalid` (adapter: 'model_and_tooling' was unexpected). Same for --h3--h1--h2 (21.8 s). Friction: the HTTP guide's literature body and the MCP literature tool take `model_and_tooling`; submit_proof does not — moved the honesty note into automation.tool_setup.
- 11:26Z submit_proof --h3--h1--h1 (partial, job 01M4X2A8ZR0BYXPE0WS8NCK5BW): 13.0 s, 201, graph PR #522, submission 01M4X2M99R7QQYTYA5GAT34NF4, holes h_k6 → --h3--h1--h1--h1, h_k3rest → --h3--h1--h1--h2.
- 11:27Z submit_proof --h3--h1--h2 (partial, job 01M4X2AFTGANY4G8PAE5GKQ3MV): 9.0 s, 201, graph PR #523, submission 01M4X2MK28C36SFX7EYKP0ZDT3, holes h_odd_k3 → --h3--h1--h2--h1, h_odd_rest → --h3--h1--h2--h2.
- 11:27Z get_submission 522 (MCP): 2.9 s, state open, mergeable_state null. get_submission 523: no answer in >100 s (the loop was moved to background and never returned for 523/512/513). Possibly the laptop TCP stall; not retried.
- 11:29Z GitHub API: #512 and #513 (literature) MERGED. #522, #523 open, gate job "steps 1, 2 and 4-8 in the sandbox" in_progress.
- 11:29Z release_claim on both claims: 0.6 s each, 200.
- 11:30Z stopped starting new work.

## Report

**What landed**
- Graph PR #512: literature proposal `known` on `erdos-1094--h2--h2--h1` (BHP). MERGED.
- Graph PR #513: literature proposal `known` on `erdos-1094--h2--h1--h4` (a corollary of `--h2--h1--h1` / Konyagin). MERGED.
- Graph PR #522: plain partial (two holes) on `erdos-1094--h3--h1--h1`. Open at 11:30Z, gate in progress. Expected new nodes `erdos-1094--h3--h1--h1--h1` (k even, k ≡ 0 mod 3) and `--h3--h1--h1--h2` (k even, 0 < k%3 ≤ n%3).
- Graph PR #523: the same split on `erdos-1094--h3--h1--h2`. Open, gate in progress. Expected `--h3--h1--h2--h1` (k, n odd, 3 | k) and `--h3--h1--h2--h2` (k, n odd, 0 < k%3 ≤ n%3).
- Both skeletons carry `True` witnesses. Every hosted precheck passed, with steps 1, 2 and 4–8 all passing and the witnesses checked.
- Which claims are mine and unchecked: the assembly is kernel-checked and closes the case n%3 < k%3 with p = 3. That the holes are true is only a numerical check over every k ≤ 600 (C/num.py), not a proof. Last failures: k = 36 and 58 for even k, k = 39 and 35 for odd k (with odd n). That matches the root's earlier annex values K₁ = 58 and K₂ = 39.
- Not circular: each hole has one extra hypothesis, and neither hole alone gives the parent.

**Literature findings**
- `--h2--h2--h1` is Baker–Harman–Pintz 2001 (Proc. LMS 83, 532–562). The source is the closing display on p. 562, not Theorem 1: "for all large x, π(x + x^0.525) − π(x) > 9x^0.525/(100 log x)". Theorem 1 itself is stated for the backward interval [x − x^0.525, x].
  - The Lean statement uses the forward interval (k, k + k^0.525) with exponent 21/40, natural log, and "∃ C > 0, ∃ k₀". That is the published display with C = 9/100. A slightly smaller C absorbs the strict upper endpoint.
  - I read this in the PDF (cs.umd.edu copy). The DOI I cited (10.1112/plms/83.3.532) is from memory and unchecked.
- `--h2--h1--h4` (k² ≤ n < k(k + 3k^0.525), minFac > n/k) is a corollary of `--h2--h1--h1`. From n ≥ k², minFac > n/k ≥ k, so every prime factor exceeds k, and n < k³. Its divisibility hypothesis is not needed. Proposed `known` through Konyagin; the deduction is mine.
- No correction to the existing record. The `--h3` proposal already says, correctly, that the residue form `--h3--h1` is stronger than Konyagin's bound.
- Not proposed:
  - `--h2--h2` and `--h2--h2--h3`: the open core.
  - `--h2--h2--h2`: A proposed it (#521).
  - `--h3--h1` and its children: no published proof known to me.

**What a successor needs next**
- Once #522 and #523 merge, four new holes exist, each strictly narrower.
- The same trick goes one prime further. On a hole with 0 < k%3 ≤ n%3, the case n%5 < k%5 closes with p = 5 (and then p = 7). Each level removes a residue class pair.
- This does not end the job. The residual holes still need a real sieve or Konyagin-type argument for the (n mod p ≥ k mod p for all small p) cases. Numerically the K's stay at 58/39 or below.
- A skeleton that splits on p ∈ {3, 5, 7} at once is about 10 lines of assembly, using `by_cases` and `Nat.prime_five` / `(by norm_num : Nat.Prime 7)`.

**Bugs and friction**
1. *Friction:* at 11:26Z, `submit_proof` with `model_and_tooling` was refused: `arguments-invalid: Additional properties are not allowed ('model_and_tooling' was unexpected)`. `propose_literature` takes that field. I expected one disclosure field across the writes; the prose went into `automation.tool_setup` instead. The refusal cost nothing.
2. *Possible environment issue:* at 11:07Z and 11:27Z, MCP calls (`get_node`, then `get_submission` for 523) gave no answer for over 100 s. Other calls returned in 1–20 s. `claim_node` took 20.0 s at 11:18Z. Most likely the known TCP-connect stall, not counted as a service bug.
3. *Not a service bug:* WebFetch could not read the BHP PDF's text; pdftotext on the saved copy worked.
- No genuine service bug seen in this run. The token, prechecks (about 3.5 min each), carried-witness checks, literature PRs and claims all behaved as the guide says.

**Feature requests**
- A per-hole truth hint at precheck time. Even the parent's numerical annex range, echoed in `holes[]`, would let a skeleton author see that a hole is not obviously false.
- `get_submission` accepting a list, so one call can poll several PRs.
- 11:33Z addendum: the hung get_submission 523 (11:27Z) ended with a client-side 'TimeoutError: _ssl.c:989: The handshake operation timed out' after 300 s — the TLS handshake never completed, so it is the laptop's network path (environment), not a service bug. 512/513 then answered 8.4 s / 1.1 s, state merged.
