# Tester log — erdos-1050 via MCP (2026-09-24)

Start: 2026-09-24T12:24:50Z. Stop new work at 13:19:50Z.

## Log

- 12:24:50Z `curl https://openproofnetwork.org/problems/erdos-1050/` → 200; `curl https://api.openproofnetwork.org/health` → 200. Network OK.
- 12:25Z Read the problem page and /docs/ (AGENTS.md rendered). Target: `Irrational (∑' n, 1/(2^(n+1) - 3))` (calibration, known result: Borwein 1991).
- 12:25Z MCP `tools/list` → 200 in 0.7 s, 29 tools, matches the guide's appendix table.
- 12:25Z MCP `list_frontier {filters:{target_id:"erdos-1050"}}` → 2 entries (root `erdos-1050`, `erdos-1050--h1-v2`), both claimable, **no active claims**. `list_submissions` → nothing open on erdos-1050. So the other agent has not claimed yet.
- 12:26Z MCP `get_node erdos-1050` and `erdos-1050--h1-v2`: earlier testers (t0923-1050-b, tester-1050-2045) already filed postmortems: every open node reduces to Irrational T, T = ∑ 1/(2^(n+3)-3), which is Borwein 1991 (q=2, r=-3), `missing-library`. `erdos-1050--h1-v2--h1` (= Irrational T) is status `circular`, not on the frontier.
- 12:26Z Observation (not a bug, confusing): the page's graph key calls h1-v2--h1 "circular" in the selected-statement card, but the key/legend at the top lists only proved/open/blocked/superseded — "circular" is not explained in the key.
- 12:26:48Z MCP `precheck_submission` on tutorial-and-swap (no token) → 202 in 3.8 s, job queued, nonce returned (kept out of this log).
- 12:29:36Z `get_precheck` → done/pass (≈3 min). 12:29:47Z `get_token` → 201, pseudonym `t0924-1050-mcp`, proof_kind tutorial. Smooth.
- 12:30:26Z `claim_node erdos-1050--h1-v2 ttl 2` → 201, expires 14:30Z.
- 12:28Z Followed an earlier annex's pointer to prior art: github.com/gotrevor/lean-gallery `LeanGallery/NumberTheory/Erdos1050/` (Apache-2.0, Trevor Morris) claims a complete, sorry-free Lean 4.33.1 proof of exactly this root (~2,700 lines, 10 files). Not network code, so reading it is within my rules. Porting 2,700 lines into a single-file proof (no helper declarations allowed) is not possible in my hour, and AXLE's 20 s budget would not check it anyway.
- Plan: a skeleton (partial) on `erdos-1050--h1-v2` whose holes are Borwein's four pieces with the approximants written out explicitly (integrality, W≠0/E≠0, decay, transfer), each mapping to one part of the gallery development, as the previous tester's annex asked for ("a useful next skeleton is one whose holes are the explicit approximants").
- 12:31:08Z `submit_informal_annex` on erdos-1050--h1-v2 → 201 in 3.4 s, graph PR #174, hash e6849740c2b9….
- 12:31:54Z `check_lean` (mode check, node erdos-1050--h1-v2) on a 5-hole skeleton → 200 in 3.3 s, okay:false, one `rewrite` error (mine: `push_cast` normalised `↑(n+1)` to `↑n + 1` so the rewrite no longer matched). Error messages with goal states were clear and positioned. Good.
- 12:32:23Z fixed assembly → okay:true, lint only sorry-present. 1.5 s.
- 12:32:44Z `check_lean` (target only, no node) on proofs of the two easy holes (transfer z = 3/5 − 3T, and W(n) ≠ 0) → okay:true first try, 1.3 s. Inlined both; skeleton now has 3 holes: `e_ne` (E(n) ≠ 0), `decay` (9^n W E → 0), `integrality` (Borwein Lemmas 1–3). Re-check okay:true (3.2 s).
- 12:33:04Z `get_submission 174` → annex PR **merged** at 12:32:44Z (92 s after submission, merge actor). Note: for a merged proposal `pull_request.waiting_on` is `null`, while the guide says a merged proposal reads `products` until rendered. Minor mismatch with the guide (reproduced once; see the next line, where products were in fact still pending).
- 12:33:14Z `precheck_submission` (artifact_type partial) of the skeleton → 409 `products-pending`, retry_after 240, clear message naming the annex. As documented. Waiting.
- 12:34:09Z ported gallery's `Eterm_ne_zero` (E(n) ≠ 0) as one inline `have` block with q = 2, c = 8/3 substituted → `check_lean` okay:true first try (9.6 s). Credited in a comment in the Lean.
- 12:34:44Z `precheck_submission` of the 2-hole skeleton (holes: decay, integrality) → 202, job 01M39PJFM8QVTDJ1ZBBHW6V63A, graph_commit = the annex merge commit. Accepted 2 min after the annex merged although the 409 had said retry_after 240 s: fine.
- 12:36:19Z ported the decay chain (Iterm geometric bound, |E(n)| ≤ 2·2^-(…), |W(n)| bound, cleared-error bound, ratio-test asymptotic) → one error (my `simpa` pushed `abs` through the product), fixed → 12:36:36Z okay:true (4.2 s). So Borwein's Lemma 4 and Lemma 5 are both fast-checked.
- 12:36:54Z 1-hole skeleton (only `integrality`, Borwein's Lemmas 1–3, remains) fast-checks okay:true in 9.7 s — 392 lines, under AXLE's 20 s budget.
- 12:37:14Z `precheck_submission` of the 1-hole skeleton → 202, job 01M39PQ14GSAKEPKHVPN4E3C3Y.
- 12:37:57Z prepared the witness for the future integrality hole (its hypotheses are the four proved facts, so the witness is their conjunction) → `check_lean` okay:true (6.1 s). My own slip on the way: a text-splitting script cut two proofs at an inner comment; caught by the checker (unsolved goals), not a network issue.
- 12:40:17Z `get_precheck` on the 2-hole job → done/**pass**, all of steps 1, 2, 4–8 pass, ≈5.5 min. (I will submit only the 1-hole version, which supersedes it; the 2-hole precheck is left unused.)
- 12:40Z `list_frontier` → the other agent `h0924-1050-http` claimed `erdos-1050--h1-v2` too (expires 13:34Z), after my claim at 12:30. Claims are advisory; I'm going ahead with the skeleton, which they can see on the node once it opens.
- 12:40Z **Slow**: MCP `list_submissions` took **21.5 s** (other reads take 0.3–1.5 s). Not reproduced yet.
