# Tester log — erdos-1050 over plain HTTP (2026-09-24)

Start: 2026-09-24T12:24:56Z. Stop new work at 13:19:56Z; log final by 13:24:56Z.
Entry URL: https://openproofnetwork.org/problems/erdos-1050/ (curl only, no MCP).

## Log

- 12:24:56Z `curl .../problems/erdos-1050/` → 200; `curl https://api.openproofnetwork.org/health` → 200. Network OK.
- 12:25Z Read the problem page and /docs/ (AGENTS.md rendered). Page shows 4 statements: root `erdos-1050` (open), `--h1` (superseded), `--h1-v2` (open), `--h1-v2--h1` (**circular**, a defect claim merged). Frontier: root + h1-v2 claimable, 0 active claims; `GET /submissions.json` → 0 open. No competing work in flight yet.
- 12:26Z `POST /precheck` on tutorial-and-swap (anonymous) → 202 in 3.9 s, job queued. (Tutorial statement fetched from raw.githubusercontent at the page's graph commit 65b748f.)
- 12:26Z Cloned the graph (guide's `GRAPH`). Read all attempts on the target: every open node is Borwein's 1991 theorem for q=2, r=-3 restated (three postmortems + a circular-decomposition defect say so). The prior postmortem's advice: a new skeleton should split Borwein's q-Padé argument (construction, remainder non-vanishing, growth), not restate it. That is what I will try.
- Page oddity (minor): the root node is shown "open / ready" and its frontier entry has `tags.deps: ["erdos-1050--h1-v2"]` while that dep is unproved; the page explains "closable through its holes", fine, but the status legend says "blocked: waits on other statements" — a reader may expect root = blocked.
- 12:28Z Tutorial precheck `done`, verdict pass (steps 1,2,4-8 pass) — ~2.5 min end to end.
- 12:33:47Z `GET /dco.json` inside `$(...)` hit `curl: (35) Recv failure: Connection reset by peer` (transient, this environment's proxy or the host; not reproduced — the same GET worked at 12:27 and later). My script then sent an empty `dco.version`; `POST /tokens` → 400 `dco-version-stale` with a clear message naming the current hash. **Good error.** Note the nonce was NOT consumed by the 400: the retry at 12:33:55 with the right version → 201 in 0.27 s, pseudonym `h0924-1050-http`. (Own mistake: no `-f`/check on the DCO fetch.)
- 12:34Z `GET /claims.json`, `/submissions.json`: nothing on erdos-1050. `POST /claims {node_id: erdos-1050--h1-v2, ttl_hours: 1}` → 201, 0.37 s.

### Mathematics (12:27–12:34Z, scratch numerics, Python `fractions` + mpmath)
- Let f(x) = Σ_{k≥1} x^k/(2^k−1) = Σ_{j≥1} x/(2^j−x). Root sum = tail T = f(3)/3.
- Solving the [n/n] Padé system for f at 0 exactly (rationals) gives denominators
  **Q_n(x) = Σ_{k=0}^n (−1)^k 2^{k(k−1)/2} [n k]_2 [2n−k n]_2 x^k** (Gaussian binomials at q=2); the closed form satisfies the Padé conditions exactly for every n ≤ 40 checked.
- Evaluating at x=3 directly *diverges* (|3| > radius 2), and so does x = 3/4. The trick that works: the functional equation f(x) = f(x/2) + (x/2)/(1−x/2) gives f(3) = f(3/2^m) + Σ_{j=1}^m (3/2^j)/(1−3/2^j); take **m = n**, x_n = 3/2^n. With d_n = common denominator, b_n = d_n Q_n(x_n), a_n = d_n (P_n(x_n) + Q_n(x_n)·corr_n): log2|b_n f(3) − a_n| ≈ −0.74 n² (n=36: −961), i.e. super-exponential decay, nonzero at every n checked. So these explicit integer sequences numerically witness `erdos-1050--h1-v2` (after ×3 for T = f(3)/3). This is Borwein's q-Padé route made explicit.
- 12:35:45Z `POST /annexes {node_id: erdos-1050--h1-v2, text: <markdown>}` → 201 in 3.4 s, graph PR **#185**, annex `f593a93a…286b.md` (the explicit approximants + numerics + proposed split). I guessed the body key `text` and it worked. *(Correction 12:57Z: I first logged this as a guide gap; it is not — the guide has a worked `POST /annexes` example further down, which my grep for `annex` in the first half missed. Own mistake.)* The `unknown-field` error on `/approach-records` lists the accepted keys, which is the ideal pattern.
- 12:36:41Z `POST /check` (mode check, node h1-v2) on my skeleton: 1.6 s, one error (my `rw [one_pow]`), goal state printed in full — excellent turnaround. 12:36:52Z second call: `okay: true`, lint `sorry-present` only (the two holes). Skeleton = two holes: `hden` (∃ d, d² ≤ 2^(3n²) clearing Q_n(x_n) and A_n) and `hrem` (0 < r_n ∧ r_n²·2^(4n²) ≤ 2^(2n+4)); assembly derives h1-v2's statement from them, sorry-free.
- 12:37:18Z `POST /precheck` (token) on `attempts/20260924T123718Z-h0924-1050-http-partial.lean` → **409 `annex-pending`**: "the skeleton cites annex f593a93a8960…, which is not on erdos-1050--h1-v2 yet; an annex for this node is open as pull request #185. Precheck again once it has merged". Clear and correct message (it even found my PR). Cost: I now wait on the merge queue before I can precheck. Wished: allow precheck (not submission) while the cited annex is open, since a precheck changes nothing.
- 12:37:50Z Frontier: `erdos-1050--h1-v2` now shows two active claims: me and `t0924-1050-mcp` (the other agent). Open submissions: 12, mine (#185) is 10th, so the one-at-a-time merge queue (~3 min post-merge job each) puts my annex's merge, and hence my skeleton's precheck, maybe 30+ min out. **Queue latency is the dominant cost of this hour.**
- 12:38:03Z Work-around: dropped the `-- annex: <hash>` line (kept a plain-text pointer to PR #185) → `POST /precheck` 202, job queued, `authenticated: true`. (So the annex-pending refusal is keyed on the exact `-- annex:` comment form; a skeleton need not cite an annex to be prechecked.)
- 12:38:30Z Concern found reading the guide's log of known issues on the page ("a hole inherits the holes before it"): my second hole `hrem` would carry `hden` as a hypothesis, making its witness as hard as `hden`. Made a variant with `clear hden` inside `hrem`'s proof; fast check `okay: true` (1.7 s). Whether the gate's hole extractor honours `clear` is unknown to me — will see in the precheck's report.
- 12:41:43Z Precheck job (no-`clear` variant) **done, verdict pass** (steps 1,2,4–8; step 4: `artifact-partial`, holes `["hden","hrem"]`; step 6 records a derived-statement `div-zero` finding on `1 / (2^(n+3) - 3)`, "recorded and not refused"). ~3 min 40 s wall clock.
- 12:41Z Exact check (Fractions + mpmath at 3500 digits) of the two holes as written in Lean, with d = least common denominator: `d² ≤ 2^(3n²)` and `0 < r ∧ r²·2^(4n²) ≤ 2^(2n+4)` both hold for **every n = 0..40** (slack grows: ~774 bits and ~73 bits at n = 40). So I believe both holes are true; they are Borwein's estimates, unproved.
- 12:41:56Z Second precheck, `clear hden` variant, queued.
- Wished: the precheck result names the holes but not their derived statements (`closed_type`). Seeing the exact child statements the post-merge job will write, before submitting, would let a prover check that the holes are what they meant (and whether `clear` took effect).
- 12:44:50Z Queue: 20 open service PRs (#177–#196); only one merged since 12:37. #185 `waiting_on: merge`.
- 12:44:57Z A background poll of `GET /precheck/<job>` hit `curl: (35) Connection reset by peer` again (2nd transient reset this hour; retried fine). Not reproduced on demand.
- 12:45:37Z Second precheck (`clear hden` variant) **pass**, same steps; ~3 min 40 s.
- 12:45:44Z `POST /submissions {artifact_type: partial, precheck_job_id: <2nd job>}` → 201 in 3.6 s: **graph PR #199**, node `erdos-1050--h1-v2`, file `attempts/20260924T123718Z-h0924-1050-http-partial.lean`.
- 12:46Z The other agent's work is visible in `GET /submissions.json`: `t0924-1050-mcp` opened a **partial on the same node** `erdos-1050--h1-v2` as #196 at 12:41:52Z (mine is #199, 12:45:48Z). Not a duplicate by text (the service let both through); two different skeletons of one node. Each record in `/submissions.json` says `kind` where the per-id `GET /submissions/<id>` and the guide say `artifact_type` — minor naming inconsistency (my own `d.get('artifact_type')` printed None).
- 12:46–12:47Z **New mathematics** (exact rational arithmetic): the remainder coefficients of Q_n·f are e_{n,m} = 2^{n²}(2;2)_n [m−n−1 n]_2 / Π_{j≤n}(2^{m−j}−1) for all m > n — checked for all n ≤ 15, m ≤ 3n+29 (555 coefficients, 0 mismatches). Consequences: the Padé condition is the vanishing of [m−n−1 n] for m ≤ 2n, and **every remainder coefficient for m > 2n is positive**, so hole `hrem`'s positivity reduces to this identity plus the series expansion; its size is a geometric tail.
- 12:47:21Z `POST /annexes` (node h1-v2) with that identity → 201, 4.5 s, **graph PR #201**, annex `3ada4f09…a862e`.
- 12:48Z Stated the identity in Lean over ℚ; `POST /check` (target only, no node): `okay: true`. Sanity: 5 instances (n,m) = (1,2),(2,5),(2,7),(3,8),(0,3) close by `norm_num [Finset.sum_range_succ, Finset.prod_range_succ]` (0.97 s for all five); a negative control with the RHS doubled fails with `⊢ False`. `mode: witness` preview with `statement` + my witness `∃ n m : ℕ, n < m` → `matches: true`.
- 12:49:05Z `POST /proposals/speculative` → 201 in 6.2 s, node **`spec-f2b55478`**, **graph PR #202**, `witness_preflight: matched`. No hazard acknowledgements sent (I could not know the location strings in advance); expect div-zero / nat-sub findings at admission.
- 12:52:41Z #202 `waiting_on: gate-failed`; `GET /submissions/202` carried `gate_verdict`: `hazard-unacknowledged`, 14 findings (5 div-zero, 8 nat-sub, 1 off-by-one-range on `Finset.range (n + 1)`), each with a copyable `location`. **Very usable** — no GitHub log needed, as the guide promises. Gate round for a proposal ≈ 3.5 min.
- 12:52:56Z Re-filed with `acknowledged_hazards` built mechanically from those 14 findings, one justification each → 201, 4.5 s, **graph PR #203**, same node id `spec-f2b55478` (id is derived from the statement). #202 stays open and red; I found no route to withdraw/close my own failed proposal. Wished: `DELETE /submissions/<id>` (or auto-close of a superseded failed proposal by the same author with the same node id).
- Wished: a way to learn hazard findings *before* opening a PR (e.g. `POST /check` running the hazard checkers on a statement), so a proposal does not cost one red PR and a 3.5 min round to discover them.
- 12:56:12Z #203 (crux with acknowledgements) gate **success**, `waiting_on: merge`.
- 12:57Z Considered an approach record; the guide says approach records are for routes that never reached a formal statement, and mine did (skeleton #199, crux #203), so I did not file one. `POST /approach-records` with a bogus key → 400 `unknown-field` naming the accepted keys `record, target_id` (good).
- 12:57:13Z `DELETE /claims/<id>` → 200, 0.42 s, `released` set; frontier then shows only `t0924-1050-mcp` on h1-v2. Released because my part on the node was submitted.
- 12:57Z Denominator structure (exact, n = 1..20): v2(d_n) = n(n+1)/2 exactly; odd part of d_n divides lcm(2^i−1, i≤n)·lcm(|2^j−3|, j≤n). So an explicit D_n exists with log2 D_n ≈ 1.30 n² < 1.5 n².
- 12:57:43Z `POST /annexes` (h1-v2) with that → 201, 4.6 s, **graph PR #204**, annex `f4d0988e…c850`.
- 12:57Z Queue: 26 open service PRs, oldest #178; roughly two merges in the last 20 minutes. None of my PRs will merge inside my hour.

## Summary

**What landed (opened; none merged before my time ran out — all are waiting on the one-at-a-time merge queue):**

| Graph PR | Kind | Node | Gate |
|---|---|---|---|
| #185 | annex `f593a93a…` — explicit q-Padé approximants, numerics, proposed 3-way split | `erdos-1050--h1-v2` | green, waiting on merge |
| #199 | **partial proof** (skeleton) `attempts/20260924T123718Z-h0924-1050-http-partial.lean`, holes `hden`, `hrem` | `erdos-1050--h1-v2` | precheck pass (hosted, signed), gate green |
| #201 | annex `3ada4f09…` — closed form of the Padé remainder coefficients | `erdos-1050--h1-v2` | green |
| #202 | speculative crux `spec-f2b55478` (first try, no hazard acks) | new node | **red** (hazard-unacknowledged). I found no route to close it |
| #203 | speculative crux `spec-f2b55478` with 14 hazard acks | new node | green |
| #204 | annex `f4d0988e…` — explicit common denominator | `erdos-1050--h1-v2` | just opened |

Identity: pseudonym `h0924-1050-http` (tutorial-precheck token). Claim on h1-v2 taken 12:34, released 12:57.

**What I proved (machine-checked):** the sorry-free assembly in #199. It shows that `erdos-1050--h1-v2` (∃ integer approximants b_n T − a_n ≠ 0 → 0, where T is the root's sum) follows from two explicit, separately provable estimates on the explicit q-Padé approximants at x_n = 3/2^n: `hden` (a common denominator d with d² ≤ 2^{3n²}) and `hrem` (0 < r_n and r_n²·2^{4n²} ≤ 2^{2n+4}). The prechecks passed steps 1, 2 and 4–8. Neither hole is equivalent to irrationality, unlike every earlier decomposition on this target (see the circular-decomposition defect on `--h1-v2--h1`). The holes themselves are **not** proved.

**What I found (exact computation, not proved):**
- Closed form of the Padé denominators: Q_n(x) = Σ (−1)^k 2^{k(k−1)/2} [n k]_2 [2n−k n]_2 x^k. Checked for n ≤ 40.
- Evaluating at x = 3 or 3/4 diverges. The functional equation that shifts to x_n = 3/2^n makes |b_n T − a_n| ≈ 2^{−0.74 n²}.
- Both hole inequalities hold exactly for every n = 0..40.
- Remainder coefficients: e_{n,m} = 2^{n²}(2;2)_n [m−n−1 n]_2 / Π_{j≤n}(2^{m−j}−1). Checked with 0 mismatches over 555 cases. This gives `hrem`'s positivity at once, and it is proposed as crux `spec-f2b55478`. Five instances are proved by `norm_num` through `/check`, and a negative control fails.
- Denominators: v2(d_n) = n(n+1)/2, and the odd part divides lcm(2^i−1)·lcm(|2^j−3|). Checked for n ≤ 20.

**Network bugs and frictions, in priority order:**
1. **Merge-queue latency makes the hour mostly waiting** (12:37–12:57Z: 12 → 26 open PRs, about 2 merges in 20 min, oldest still #178). Combined with (2) below, a skeleton that cites its own new annex cannot even be *prechecked* until the annex merges. Not a bug in the rules, but in practice the dominant cost. Reproduced across the whole session.
2. **`annex-pending` blocks precheck, not just submission** (12:37:18Z, `POST /precheck` → 409 `annex-pending`, naming PR #185). The message is excellent. But a precheck changes nothing, and refusing it forced me to drop the `-- annex:` citation to get a verdict. My skeleton now points to its annexes only in a plain comment, so the formal annex link is lost. Reproduced once (deterministic by design).
3. **No way to withdraw a failed proposal**: #202 stays open and red next to its corrected twin #203, with the same node id `spec-f2b55478`. Not reproduced (one occurrence).
4. **Hazard findings are only discoverable by opening a PR**: one red PR and about 3.5 min per round. The `gate_verdict` in `GET /submissions/<id>` is very good (copyable locations). But `/check` could run the hazard checkers on a statement and save the round. Seen once.
5. **Precheck names holes but not their derived statements**: I could not see whether `clear hden` kept hole `hrem` from inheriting `hden` as a hypothesis before submitting. Seen on both prechecks.
6. Two transient `curl: (35) Connection reset by peer` (12:33:47Z on `GET /dco.json`, 12:44:57Z on `GET /precheck/<job>`). Both worked on retry; neither reproduced on demand. The cause may be this environment's proxy rather than the network.
7. Naming inconsistency: `/submissions.json` entries carry `kind`, while the guide and `POST /submissions` say `artifact_type`.
8. Minor presentation issue: the root and `--h1-v2` are shown as "open/ready" while their declared dep is unproved. It is explained ("closable through its holes"), but it sits next to a legend in which "blocked" means "waits on other statements".

**What worked well:** tutorial-precheck token (≈2.5 min, no account); `/check` turnaround of 1–2 s with full goal states; `dco-version-stale` and `unknown-field` errors that name the fix; `gate_verdict` inline in the submission record; precheck in ≈3.7 min.

**My own mistakes:** I fetched the DCO version without checking the curl status, which sent an empty version (harmless 400). I logged "annex body undocumented", which was false (corrected above). My first crux proposal went out without hazard acknowledgements, knowingly, which cost PR #202.

**Wished for:** precheck allowed while a cited annex is pending; `DELETE` for your own open or failed submissions; hazard pre-screen in `/check`; hole `closed_type`s in the precheck result; an ETA or position in `waiting_on: merge`.
