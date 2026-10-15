# Tester Q (t1014-q) log — erdos-1094, 2026-10-14b

- 17:34Z read README, board (lead line only), earlier A.md, C.md, bugs.md, A's port survey; cloned graph (466c11d, then bae0f83) and vdT repo to scratch.
- 17:35Z list_frontier (MCP, 5.6 s): 24 erdos-1094 entries, 21 claimable, no active claims; three blocked (B's holes, witness-missing).
- 17:36Z precheck_submission tutorial-and-swap, no token (MCP, 45.2 s): 202 queued (graph_commit bae0f83).
- 17:37Z surveyed the leaves: case_small (--h2--h2--h2--h1) is the one leaf whose vdT proof needs only BHP plus asymptotics (A's survey: chunks 15/16 that hold it elaborate at 4.33.1). The other vdT cases need konyagin_thm; the four sieve holes and --h2--h1--h4 are the open problem in residue form; --h2--h2--h1 is BHP itself.
- 17:40Z board: P claimed --h2--h2--h2--h1 (case_small) first. Left it alone.
- 17:41Z get_precheck tutorial (MCP, 145.1 s; slow path): done, pass. get_dco (1.6 s).
- 17:44Z get_token pseudonym t1014-q (MCP, 69.0 s; slow path): 201 (token in a 0600 scratch file).
- 17:45Z claim_node erdos-1094--h3--h1--h1--h2 ttl 1 h (MCP, 3.8 s): 201 claim 01M4XRAG4R984XJ4W0AZCQXBH8. Posted on board 17:46Z.
- 17:46Z decision: no complete proof is in reach on any unclaimed leaf. My node is the open n < k² residue problem; a complete proof is not possible in an hour. Prepared the fallback the brief allows: a partial that closes n%5 < k%5 with p = 5 and n%7 < k%7 with p = 7, leaving one strictly narrower hole (the parent's hypotheses plus k%5 ≤ n%5 and k%7 ≤ n%7, neither one a consequence of the parent's).
- 17:48Z check_lean mode check (MCP, 79.2 s): lint signature-diverges. My own error: I cut the header at a fixed line count and lost two signature lines. Fixed by copying the header up to `:= by`.
- 17:50Z check_lean mode check (MCP, 70.8 s; slow path): result.okay true, no errors; only the `sorry` warning on the hole (lint sorry-present, expected for a partial). log 01M4XRJ58GA0XK3YRSQA4HMFP6.
- 17:50Z precheck_submission artifact_type partial, carrying the hole witness `True := trivial` (MCP, 7.6 s): 202 job 01M4XRKH6RZ402QTGNPTAWEKKV at graph bae0f83. Not submitting before 18:10Z, per the brief.
- 17:51–17:55Z get_precheck polls (MCP 2.2 s, then 97.1 s, which is the slow path). The first background poll loop died with exit 144; that was my shell, not the service. Job done: verdict pass, steps 1, 2 and 4–8 pass. Hole h_p57 → expected_new erdos-1094--h3--h1--h1--h2--h1, proved_binders [], expected_witness True, carried witness checked: true. Saved as Q/precheck-partial.json, nonce-free.
- 17:56Z numerics (Q/num.py; even k ≤ 300 with k%3 ≠ 0, n in [2k, k²), k%3 ≤ n%3): 1,489,845 parent cases, of which 502,448 (34%) are left to the hole. All 144 failures of the parent lie in the hole, as they must, since p = 5 and p = 7 settle the other cases. Last failure at k = 58, as for the parent. A finite check, not a proof.
- 17:56Z widened the fallback to p ∈ {5, 7, 11, 13}, at the same cost. The hole now keeps 131,969 of the 1,489,845 parent cases (9%) in the same numerics (Q/num2.py; its 109 counted failures leave out k < 13, where the assembly does not apply). check_lean mode check (MCP, 4.1 s): compiles, sorry only. log 01M4XRYJQ8BWXJPJ6JTMA5A55T.
- 17:57Z precheck_submission partial v2, carrying witness `True := trivial` for h_p5to13 (MCP, 6.9 s): 202 job 01M4XRZ0CRQFSK59GEZRYW75QS. If it passes, v2 is the one to submit at 18:10Z; v1 (job 01M4XRKH…) is kept unused.
- 18:01Z get_precheck v2 (MCP, polled 25 s apart): done, pass, steps 1, 2 and 4–8 pass. Hole h_p5to13 → expected_new erdos-1094--h3--h1--h1--h2--h1, witness checked: true. Saved as Q/precheck-partial2.json. Holding the submission until 18:10Z.
- 18:10Z submit_proof partial v2 (MCP, 5.6 s): 201, graph PR #525, submission 01M4XSQ6T09QRMKDVYCAVW4S8H, hole h_p5to13 → erdos-1094--h3--h1--h1--h2--h1 (expected_new). This is a fallback partial, not the complete proof the task asked for.
- 18:11–18:25Z get_submission polls (MCP, about 1–9 s each): waiting_on went gate → merge → gate (the queue updated the branch) → merged. PR #525 MERGED 18:25:11Z (merge 3201a83), gate run 38614240400 success. At 18:26Z: waiting_on products, attestation-pending, holes[].became null, which is expected before the post-merge job.
- 18:26Z release_claim 01M4XRAG4R984XJ4W0AZCQXBH8 (MCP, 1.6 s): 200. Stopped.

## Report

**What landed**
- Graph PR #525 (`t1014-q`), a partial on `erdos-1094--h3--h1--h1--h2`, the sieve hole with k even and 0 < k%3 ≤ n%3. **MERGED at 18:25:11Z**, gate success, no human involved.
  - The assembly is kernel-checked. It closes every case with n%p < k%p for p ∈ {5, 7, 11, 13}, using that prime, with K := max K₃ 13.
  - It leaves one hole, `h_p5to13`, which becomes `erdos-1094--h3--h1--h1--h2--h1`: the parent's statement plus k%p ≤ n%p for those four primes. Each added hypothesis is a real restriction, not a consequence of the parent. The hole carried the witness `True := trivial` (checked: true), so the new node should be born `ready`.
  - Numerically (even k ≤ 300 with k%3 ≠ 0), the hole keeps 9% of the parent's (n, k) cases and all of its failures. The last failure is at k = 58, as for the parent. That is a finite check, not a proof.
- **This is not the complete proof the task asked for.** I submitted it at 18:10Z under the brief's last-resort rule. The new hole is as open as its parent; the partial only narrows it.
- Claim taken at 17:45Z and released at 18:26Z.
- Files: Q/partial2.lean (submitted), Q/partial.lean (the p = 5, 7 version, prechecked and not used), the witnesses, Q/precheck-partial*.json (nonce-free), Q/submit-receipt.json, Q/num.py and Q/num2.py.

**Why no complete proof:** I surveyed every claimable leaf of erdos-1094 at 17:37Z.
- The only one whose proof is within an hour's reach is `--h2--h2--h2--h1` (vdT case_small). Its proof needs only BHP, as a disjunct, plus asymptotics from A's clean chunks 15 and 16. P claimed it at 17:40Z, before I did.
- `--h2--h2--h2--h2..h4` need konyagin_thm. R took `--h2`.
- The four sieve holes and `--h2--h1--h4` are the open problem in residue form. `--h2--h1--h4` reduces, by Kummer, to the n ≥ k² residue question.
- `--h2--h2--h1` is BHP itself.
- Three nodes are blocked (witness-missing).

On a frontier shaped like this, a third prover has nothing tractable to fill.

**What a successor needs next**
- Once the products render, check `erdos-1094--h3--h1--h1--h2--h1` with `get_submission 525`, whose `holes[].became` is null until then.
- The same p ∈ {5, 7, 11, 13} split applies verbatim to the three sibling sieve holes (`--h3--h1--h1--h1`, `--h3--h1--h2--h1`, `--h3--h1--h2--h2`); the assembly is about 15 lines. More primes keep narrowing the hole but never close it. Closing one needs a real sieve or Konyagin-type argument.
- P's case_small: R's 17:57Z board note says the chain blows the 200k-heartbeat cap once inlined into one theorem.

**Bugs and friction**
- *Genuine service issues:* none seen. Every MCP route answered as the guide says: check, precheck with carried witness, submit 201, merge queue (gate → merge → gate after a branch update → merged), and release.
- *My own errors:*
  - My first fast check failed `signature-diverges` because I cut the statement header at a fixed line count. The lint named the exact line, which was useful.
  - One background poll loop of mine died with exit 144.
  - My poll loop's exit test missed the merged state.
- *Slow network path (laptop, not the service):* tutorial precheck submit 45 s, get_precheck 145 s, get_token 69 s, two check_lean calls 79 s and 71 s, and a later check of the same size 4.1 s.
- *Friction:*
  - The MCP `check_lean` result is wrapped in `{status, body}` (a write-style envelope). The guide's Before-you-start says a read answers with no envelope, so this caught my parser once.
  - The precheck queue plus the merge queue took 15 minutes from submit to merge for a partial, including one branch-update re-gate.

**Feature requests**
- A frontier field, or a literature status, that marks a node as "the open problem restated" (no known proof). An agent then would not have to derive by hand that 20 of 21 claimable nodes are research-level before choosing.
- A board, or claim visibility in `list_frontier`, refreshed fast enough that two agents choosing at once see each other. Here the board was the only signal.
