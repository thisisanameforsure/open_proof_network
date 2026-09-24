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
- 12:41:43Z 1-hole precheck → done/**pass** (all steps), ≈4.5 min.
- 12:41:47Z MCP `submit_proof` (artifact_type partial, precheck_job_id, tooling disclosed incl. the lean-gallery port) → 201 in 4.3 s, **graph PR #196**, submission 01M39PZDP83BZ7KK797R5J6WQJ.
- 12:42–12:44Z polling MCP `get_submission 196` every ~15 s: `open, waiting_on: gate` as documented. **One call at ~12:43:01Z returned an empty body** (my client got nothing parseable; stderr was suppressed in that loop so I lost the status code — my mistake). Now polling with stderr captured to see whether it recurs.
- Correction to my own annex (e6849740…): it says "the skeleton citing this annex has one hole per piece". By submission time I had proved pieces 2–4 inside the skeleton, so PR #196 has **one** hole (integrality). The annex's mathematics is unaffected; the sentence about the skeleton's shape is stale. Annexes are append-only, so the correction lives here and in the PR.
- 12:46–12:47Z PR #196 gate green (~5 min after opening); `waiting_on` moved `gate` → `merge` (12:47:08Z) → `branch-update` (12:49:22Z, `mergeable_state: behind`): `main` moved under it before the merge actor merged. No further empty responses from `get_submission` in ~40 polls since 12:44Z; the 12:43Z one did not recur.
- 12:53:30Z (approx.) one MCP call died with `ConnectionResetError` during the TLS handshake. Not reproduced; could be this container's egress proxy as much as the service. Unattributed.
- 12:52–12:56Z PR #196 **oscillates** `merge` (mergeable_state unknown) ↔ `branch-update` (behind): 12:52:37 merge, 12:55:06 branch-update, 12:56:07 merge. Gate green the whole time. It looks like the merge queue keeps updating my branch while `main` moves under it (another agent is active on the same target). From outside I can't tell whether it is starving or just queued; `waiting_on` gives no position or ETA. **Wish:** a queue position / "N ahead of you" in `get_submission`.
- 12:58:23Z MCP `list_submissions` → 27 open PRs from at least six tester identities (erdos-402, erdos-69, erdos-1050); took **28.9 s** (reproduces the 12:40 slowness: 21.5 s then 28.9 s, while `get_submission` answers in 0.3–1.2 s).
- 12:59Z a second `ConnectionResetError` in the TLS handshake on a `get_submission` call (the retry a second later worked). Two in ~6 min. Could still be my egress path.
- 12:59Z the other agent (`h0924-1050-http`) has its own partial on the same node (#199, also `waiting_on: merge`) plus annexes #185/#201/#204 and a speculative crux (#202 gate-failed `hazard-unacknowledged`, #203 re-filed). So both of us skeletonised `erdos-1050--h1-v2` in parallel despite the claims. Claims were visible to both of us and neither stopped; as designed (advisory), but the net effect is two rival skeletons on one node.
- 13:00–13:07Z PR #196 still cycling `merge` ↔ `branch-update` (six more `behind` phases). Its gate went green at ~12:47Z; **20 minutes later it has not merged**. The other agent's #199 on the same node is in the same state. One more empty poll result at 13:02:36Z (a silent network error in my loop; I had stderr suppressed again).
- 13:07Z stopping new work soon; no time left to witness the new hole once it exists. The witness is ready (below).

## Summary

**What landed / is in flight**
- Graph PR **#174** (merged 12:32:44Z): annex `e6849740c2b9808384d1f619c8c2e893c507c1bc30907ddd8aec11b83bdd3949` on `erdos-1050--h1-v2`. It makes Borwein's approximants for q = 2, c = 8/3 explicit (W(n), I(n,m), E(n)), splits the proof into four pieces (integrality, non-vanishing, decay, transfer to T), and points to the complete Apache-2.0 Lean formalization in gotrevor/lean-gallery with a map from each piece to its declarations. One stale sentence: it says the skeleton has one hole per piece, but the skeleton ended up with one hole in total.
- Graph PR **#196** (open, gate green since ~12:47Z, precheck 01M39PQ14GSAKEPKHVPN4E3C3Y passed all steps): a **partial** on `erdos-1050--h1-v2` with **one hole**. The assembly is kernel-checked by the gate and proves the node's statement (∃ integer approximants a, b for T with b·T − a ≠ 0 and → 0) from:
  - transfer z = 3/5 − 3T (**proved**),
  - W(n) ≠ 0 (**proved**),
  - E(n) ≠ 0 (Borwein's Lemma 5; **proved**, ported from lean-gallery),
  - 9ⁿ·W(n)·E(n) → 0 (Borwein's Lemma 4, the super-exponential error bound; **proved**, ported from lean-gallery),
  - **the hole:** `∃ a b : ℕ → ℤ, ∀ n ≥ 1, b n · z − a n = 9ⁿ·W(n)·E(n)` (Borwein's Lemmas 1–3, the integrality of the Padé approximants).
  So the target's entire analytic half is now machine-checked inside the partial. What remains open is the arithmetic heart, which in lean-gallery is `borwein_integrality` (Lemma3.lean, via Pade/Residue/QBinom/QLagrange/Integrality, about 2,000 lines).
- Claim 01M39PAJPGAEP0015NHNX34P91 on `erdos-1050--h1-v2` (expires 14:30Z).
- **Next step for whoever continues:** once #196 merges, the new hole's witness is the conjunction of the four proved facts, in order. Their proofs are the four `have … := by` blocks in the #196 file, so the witness is those four blocks under `refine ⟨?_, ?_, ?_, ?_⟩`. I fast-checked exactly that text (okay:true, 12:37:57Z). Use `check_lean` mode `witness` with the hole's node_id to confirm the expected type first. After that, the hole is closed by porting `borwein_integrality` (lean-gallery, Apache-2.0, credit Trevor Morris).

**What I proved** (fast-checked by AXLE, then kernel-replayed by the gate's precheck as part of #196): the transfer identity, W(n) ≠ 0, E(n) ≠ 0 and the decay of the cleared error. The last two are ports of Trevor Morris's lean-gallery proofs, re-specialised to literal constants, and are credited as such in the Lean and in the submission's tooling disclosure. I did **not** prove the target or `erdos-1050--h1-v2`: the integrality lemma is still a hole.

**Bugs and observations, in priority order**
1. **Merge-queue starvation / no visibility** (reproduced continuously for more than 20 min): PR #196 has been gate-green since ~12:47Z and cycled `merge` ↔ `branch-update` (behind) at least eight times without merging, as did the rival #199. `waiting_on` says what it is waiting for but gives no position, no ETA and no sign of progress. Across all testers, 27 PRs were open. Wish: a queue position, or "merge attempted at T, lost to #N".
2. **Two agents skeletonised the same node in parallel** (#196 and #199 on `erdos-1050--h1-v2`), though both claims were visible on the frontier. Advisory claims work as designed, but nothing in `claim_node`'s answer says "someone else already holds a claim here". Wish: `claim_node` returns the other active claims in its receipt. (I saw the other claim only by re-reading the frontier later.)
3. **`list_submissions` is slow**: 21.5 s at 12:40Z and 28.9 s at 12:58Z, against 0.3–1.5 s for every other read. Reproduced twice.
4. **Transient transport failures**: two `ConnectionResetError`s in the TLS handshake (≈12:53Z, 12:59Z) and two empty poll results (12:43Z, 13:02Z). Not reproducible on retry. Possibly this container's egress proxy, so not attributed to the service.
5. **`waiting_on` for a merged proposal is `null`**, while the guide says it reads `products` until the post-merge render. At 12:33:04Z #174 was merged with `waiting_on: null`, and 10 s later precheck answered 409 `products-pending`. Minor guide/implementation mismatch.
6. **`products-pending` retry_after is conservative**: it said 240 s at 12:33:14Z, and the precheck was accepted at 12:34:44Z (90 s later). Harmless.
7. **Site key omits "circular"**: the problem page's status key lists proved/open/blocked/superseded, but `erdos-1050--h1-v2--h1` shows as "circular", which only the guide explains.
8. **Witness burden of skeleton holes is surprising**: because a hole inherits every earlier `have` in scope as a hypothesis, the witness of a late hole must re-prove everything the skeleton proved before it. Here that means ~250 lines of analysis in `Witness.lean`, duplicating the skeleton. This is documented ("a later hole's witness is real mathematics"), but when the earlier facts are *proved* rather than holes, the witness has to repeat proofs the gate already checked. Wish: proved `have`s should not become witness obligations.

**What worked well**: every step the guide describes ran as written, over MCP. Tutorial precheck → token took under 3 minutes and needed no account. `check_lean` answered in 1–10 s with precise positions and goal states, including a 392-line file. Prechecks ran in 4.5–5.5 min. The annex merged in 92 s. The structured errors (`products-pending`, `sorry-present` lint) said exactly what to do.

**My own mistakes** (not network bugs): a `push_cast` that broke a rewrite, a `simpa` that pushed `abs` through a product, a text-splitting script that cut proofs at an inner comment, and twice suppressing stderr in a poll loop so I lost status codes. At 12:26Z the tutorial nonce was printed once to my own terminal (never to this log or any commit).

## Addendum at stop time (13:16Z)
- PR #196 was still **not merged** at 13:16Z: gate green since ~12:47Z (~29 min), 16 `branch-update` phases observed between 13:00 and 13:15Z alone. Bug 1 above is the headline finding. The hole's witness was therefore not filed; the recipe for it is in the Summary.
