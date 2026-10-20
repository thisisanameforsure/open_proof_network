# Tester B (t1014-y) log

- 11:05Z start; cloned graph; read board
- 11:06Z POST /precheck tutorial (anon) 202 in 7.1s, job queued
- 11:07Z get_node x3 (include []) 1.3-1.5s each, statements read
- 11:08Z check_lean (HTTP /check, anon) standalone lemma: n/gcd(n,k) prime under k²≤n, minFac C(n,k) > n/k. 1st try 2.5s okay:false (Nat.succ_mul_choose_eq unknown -> renamed add_one_mul_choose_eq); 2nd 2.6s okay:true (B/lemma-gcd-prime.lean)
- 11:09Z tutorial precheck done pass (~3 min)
- 11:10Z POST /tokens with an EMPTY body (my shell slip) hung >120s with no answer (backgrounded); retry with correct body 11:12Z: 201 in 3.3s (connect 0.15s), identity t1014-y
- 11:13Z claim_node erdos-1094--h2--h2--h3 ttl 2h: 201 but 75.9s wall (likely laptop TCP stall; server created=11:13:41)
- 11:14Z check_lean skeleton on --h2--h2--h3 (mode check): 1st 3.6s indentation error (mine); 2nd 19.2s result.okay true, lint [sorry-present] only (B/h2h2h3-partial.lean)
- 11:15Z POST /precheck partial on --h2--h2--h3 (authenticated, artifact_type partial): 202, connect 38.8s (laptop path) total 47.8s, job 01M4X1ZS1RWT0NK8VD4ZZTS4Q6 at graph_commit 6f958ee
- 11:16Z check_lean skeleton on --h2--h1--h4 (same lemma, hole + (n / n.gcd k).Prime): 28.9s, result.okay true, lint [sorry-present] only
- 11:17Z POST /precheck partial on --h2--h1--h4: 202 7.0s, job 01M4X22HXGQ26VK10D94T7GKG6; claim_node --h2--h1--h4 201 (27.1s wall)
- 11:17Z check_lean skeleton on --h2--h1--h1 (proves minFac(n/gcd(n,k)) > k; hole adds it): 1.4s result.okay true, [sorry-present] only
- 11:17Z claim_node --h2--h1--h1 201 0.7s; POST /precheck partial --h2--h1--h1 202 7.2s job 01M4X23TY06KZWX4Z0HXHEB3TJ
- 11:20Z list_words_needed erdos-1094: 68.9s wall (likely connect stall), 22 subjects
- 11:21Z all three prechecks done PASS (steps 1,2,4-8), one hole h_gp each, expected_new true (precheck ~4-5 min)
- 11:21Z POST /submissions --h2--h2--h3 partial: 201 26.7s -> PR #514, expected hole erdos-1094--h2--h2--h3--h1
- 11:21Z POST /submissions --h2--h1--h4 partial: 201 3.9s -> PR #515, expected hole erdos-1094--h2--h1--h4--h1
- 11:21Z POST /submissions --h2--h1--h1 partial: 201 4.0s -> PR #516, expected hole erdos-1094--h2--h1--h1--h1
- 11:23Z POST /glosses statement --h2--h1--h4: 201 56.2s (stall) PR #517; --h2--h2--h3: 201 5.1s PR #518
- 11:24Z POST /annexes on --h2--h1--h1 (structural notes; proved vs unchecked marked): 201 23.4s PR #520
- 11:25Z python sanity check of annex remarks (k<40, n<min(k^3,3000)): 124 cases with minFac C(n,k) > k, 0 violations of minFac(n/gcd) > k or of 'k|n => n/k prime'
- 11:25Z GET /submissions: #516 gate success (behind), #517 gate success, #514/#515 gate in progress
- 11:28Z #516 MERGED (no human); #514, #515 gate success, awaiting merge actor
- 11:28Z release_claim x3 (19.6s, 0.6s, and --h2--h1--h1): all 200
- 11:30Z #516 state merged, attestations/000516.json; holes[].became still null (products not yet rendered). #514 #515 #517 #518 #520 open (#514/#515/#517 gates green).
- 11:30Z stopped starting new work.

## Report

### What landed (pseudonym t1014-y)
- **PR #516 — MERGED** (no human): partial on `erdos-1094--h2--h1--h1`. Assembly proves, in Lean, that under 0<k, 2k≤n and minFac C(n,k) > k, every prime factor of n/gcd(n,k) exceeds k (`(n / n.gcd k).minFac > k`). One hole `h_gp` = the node plus that hypothesis; expected new node `erdos-1094--h2--h1--h1--h1` (`became` not yet rendered at 11:30Z).
- **PR #514** (gate green, awaiting merge actor): partial on `erdos-1094--h2--h2--h3`. Assembly proves `(n / n.gcd k).Prime` from k²≤n and minFac C(n,k) > n/k; hole = node + that hypothesis, expected `erdos-1094--h2--h2--h3--h1`.
- **PR #515** (gate green, awaiting merge): same lemma on `erdos-1094--h2--h1--h4`; expected `erdos-1094--h2--h1--h4--h1`.
- **PR #517, #518**: statement glosses for `--h2--h1--h4` and `--h2--h2--h3` (drafted_with claude-opus-5-5).
- **PR #520**: annex on `--h2--h1--h1` stating what is proved vs what is my unchecked remark.
- Lean files: `B/lemma-gcd-prime.lean`, `B/h2h2h3-partial.lean`, `B/h2h1h4-partial.lean`, `B/h2h1h1-partial.lean`.
- All claims released.

Mathematical honesty: the key fact n/gcd(n,k) | C(n,k) and its consequences in the three assemblies are kernel-checked by the gate. These are *reductions* (each hole is the parent plus a provable consequence of the parent's hypotheses), so each hole is equivalent to its parent given the assembly; they narrow the search space (n = g·p with g | k, g < k, p a prime > n/k, on the two n ≥ k² nodes) but do not lower the difficulty in any proven sense. The annex's further remarks (k | n ⇒ n/k prime in (k,k²); n/g has at most two prime factors on --h2--h1--h1) are mine, checked numerically only (124 cases, k<40), not in Lean.

### What a successor needs next
- On the new holes, split on g = gcd(n,k). On `--h2--h2--h3--h1` / `--h2--h1--h4--h1`: n = g·p with p prime > n/k and g a proper divisor of k; combine with k·⌊n/k⌋ | k! and Kummer (no base-q carries for every prime q ≤ ⌊n/k⌋) — the g = 1 case means n itself is prime, which may make C(n,k)'s small-prime structure tractable.
- C notes (board 11:20Z) that `--h2--h1--h4` is a corollary of `--h2--h1--h1`; a proof of the latter's hole gives the former.
- Mathlib name: `Nat.succ_mul_choose_eq` no longer exists at this pin; it is `Nat.add_one_mul_choose_eq`.

### Bugs and friction
Genuine (possible) service issues:
- 11:28Z: my claim on `--h2--h1--h1` stayed active after the partial on it merged (11:28Z list_my_claims showed released: null); the other two needed a manual release too. Not necessarily a bug (claims are explicit), but a merged decomposition could release or flag the claim. Feature request below.
- 11:10Z: `POST /tokens` with an EMPTY body (my shell error, Content-Type json) did not answer within 120s. Expected a fast 400. Could equally be the laptop's connect stall; unconfirmed. Retry with a valid body: 201 in 3.3s.
- 11:30Z: `GET /submissions/<#516>` showed state merged with `holes[].became: null` two minutes after merge — expected while products render; not checked later.

Environment (laptop TCP path, not the service): claim_node 75.9s (11:13Z), precheck POST connect 38.8s (11:15Z), list_words_needed 68.9s (11:20Z), gloss POST 56.2s (11:23Z), release_claim 67.6s (11:29Z). Other calls answered in 0.6–7s.

My own errors (not bugs): heredoc redirect slip produced the empty token body; reading the precheck hole field as `expected_id` instead of `expected_node_id`.

### Feature requests
- Auto-release (or mark) a claim when a partial/proof by the claimant on that node merges.
- `check_lean` mode check took 19–29s on the 60-line skeletons, close to the 20s budget mentioned in the guide (it still answered 200); a hint in the answer when a check is near the budget would help.
- 11:31Z final poll: #514 and #515 still open, gates green, not yet merged
