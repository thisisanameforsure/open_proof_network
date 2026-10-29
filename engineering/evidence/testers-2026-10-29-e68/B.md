# B — log

Notation: F_N = Σ_{n=2}^N N!/(n!−1), x_N = fract(F_N), c_N = N!S − F_N ∈ (1/(N+1), 1/N) (h2/h5),
ε_m = 1/(m!−1). h3: ∀M ∃N≥M, x_N < 1 − 2/N. Root ⇔ never x_N = 1 − c_N (⇔ N!S ∉ ℤ for all N).

14:42Z start. Read BRIEF, prior/README, board, prior C/postmortem-opencore-draft.md (C already found the
recurrence and the factorial-digit equivalence yesterday; I do not re-derive those as "new").
Graph clone pulled; read --h3 and --h6 Statement.lean.

## Brainstorm: candidate sub-skeletons of --h3 (14:46Z–15:05Z)

### B-1 truncation + residue form (elementary holes do real work; core = h3 with slack)
Write N!/(n!−1) = N!/n! + (N!/n!)/(n!−1). So x_N = fract(G_N), G_N = Σ_{n=2}^N (N!/n!)/(n!−1).
- hole T1 (elementary): x_N = fract(G_N).
- hole T2 (elementary, needs Stirling-type bounds, ~real work in Lean): with n*(N) = ⌈N/2 + N/log N⌉ (any
  explicit cut with N!/(n!)^2 summably < 1/N above it), L_N := Σ_{n>n*} (N!/n!)/(n!−1) satisfies 0 < L_N < 1/N.
- hole T3 (elementary): for n ≤ n*, (N!/n!)/(n!−1) ≡ r_{n,N}/(n!−1) mod 1 with r_{n,N} = (N!/n!) mod (n!−1);
  and r = 0 whenever (n!−1) | N! (e.g. n!−1 ≤ N, prior C §3).
- **core K1**: ∀M ∃N≥M, fract(Σ_{n≤n*(N)} r_{n,N}/(n!−1)) < 1 − 3/N.
- Narrower? K1 ⇒ h3 (with T1–T3). Reverse: h3 gives fract(R_N) = x_N − L_N (when x_N ≥ L_N) < 1 − 2/N, not
  < 1 − 3/N. So K1 is formally stronger by a 1/N slack, but it is the same question about the same residues:
  **morally equivalent to h3, not narrower.** Its only gain is that the top half of the terms is removed.

### B-2 recurrence / factorial digits (collapses: prior C §1–2)
- hole R (elementary): F_{N+1} = (N+1)F_N + 1 + ε_{N+1}, so x_{N+1} = fract((N+1)x_N + ε_{N+1}).
- hole D (elementary): if h3 fails at N and N+1 then (N+1)(1−x_N) − ε_{N+1} is within 2/(N+1) of {0,1,2}.
- core K2: ∀M ∃N≥M, the "digit" (N+1)(1−x_N) − ε_{N+1} is not within 2/(N+1) of {0,1,2}, or x_N < 1−2/N.
- **K2 ⇔ h3** (D and its converse are both one-line). Not progress. Also shows ¬root ⇔ ∃N0 x_{N0} = 1 − c_{N0}
  (the recurrence propagates it), i.e. nothing new on the root either.

### B-3 prime subsequence N = p − 1 (Wilson) (stronger, no mechanism)
- Wilson: (p−1)! ≡ −1, (p−2)! ≡ 1 (mod p), so every prime p divides (p−2)!−1: at N = p−1 the term
  n = N−1 = p−2, i.e. N/((N−1)!−1), carries a factor p in its denominator unless cancelled.
- core K3: ∀M ∃ prime p ≥ M, x_{p−1} < 1 − 2/(p−1).
- K3 ⇒ h3 trivially; reverse unknown, so "strictly narrower" formally — but the p-adic fact only shows x_{p−1} has
  denominator divisible by p (x ≠ 0, x ∉ ℤ-type statements), never a size bound below 1 − 2/N, and h3 is a size
  statement. **No mechanism makes K3 easier; it only throws away N.** Not recommended.

### New route on the root (neither --h3 nor --h6)?
- S = (e−2) + T, T = Σ 1/(n!(n!−1)): irrationality not additive (prior A's approach record). Dead.
- Denominator / Wilson route on the root: S = a/b ⇒ (p−1)!S ∈ ℤ for p > b, but c_{p−1} is an infinite tail with no
  denominator control; the arithmetic only reaches F_{p−1}. Collapses to h6 (the root itself).
- lcm route refuted (approach #1137).

### Verdict (B)
None of B-1..B-3 has an open core strictly narrower than --h3 *and* more tractable. B-1 is the only one whose
elementary holes remove real content (integer small-n terms, the top ~half of the terms); its core is h3 with a 1/N
slack. B-2 is equivalent to h3. B-3 is strictly stronger but no easier. Recommendation to A: if A has nothing
narrower, B-1 is the most honest structural skeleton, labelled "restatement with slack, not narrower"; otherwise
B will write the postmortem of why the candidates collapse.
14:45Z sanity (B/check_b1.py, exact rationals): T1 fract(F_N)=fract(G_N) and recurrence R hold for N≤60/30; minimal cut with L_N<1/N is 7,13,18,24,36 for N=10..60, inside N/2+N/logN. x_N at N=10..60: .19 .82 .66 .16 .92 (looks unstructured).
14:45Z MCP get_node erdos-68--h3 include:[] works with my token. h3 already carries 3 postmortems (t1028-a/b/c, all route-dead-ends) covering recurrence + residue form; B-2 is in them, B-1's truncation (top ~half of terms removed, L_N<1/N) and B-3's prime subsequence are only partly there.
14:46Z note: B-2 sharpened (for the postmortem): with δ_N = 1 − x_N and k_N := ⌊(N+1)δ_N − ε_{N+1}⌋, the recurrence gives
δ_N = Σ_{m>N} (k_{m−1} + ε_m)·N!/m!, and N!S ≡ Σ_{m>N} (1 − k_{m−1})·N!/m! (mod 1) for every N. ¬h3 from N0 on ⇔ k_N ∈ {0,1,2}
from N0 on (the bound δ_N ≤ 2/N is then automatic). Hence ¬h3 ⇔ S − Σ_m a_m/m! ∈ ℚ for some a: ℕ→{−1,0,1} (eventually);
¬root is the sub-case a ≡ 0 eventually. Same as prior C's "digits within 2 of 0 or of N+1". Equivalent, not narrower.

### B-4 (14:47Z) route 3 on the ROOT with a core WEAKER than --h3 (my best candidate)
- core C': ∀M ∃N≥M, fract(F_N) ≤ 1 − 1/N.
- closing: C' + h5 (proved: 1/(N+1) < c_N < 1/N, N≥4) + h1 (proved). At such N, N!S = F_N + c_N, and
  0 < x_N + c_N < (1 − 1/N) + 1/N = 1, so N!S ∉ ℤ; i.o. ⇒ h1 ⇒ Irrational S. Elementary, both deps already proved.
- Position: h3 ⇒ C' (1 − 2/N < 1 − 1/N), and C' ⇒ h6 (first disjunct) ≡ root. So h3 ⇒ C' ⇒ root.
- C' strictly narrower than the root (reverse unknown): with the digit picture (14:50Z), ¬C' ⇔ S ≡ Σ a_m/m! (mod ℚ) with
  a_m ∈ {0,1} eventually, which includes S − e ∈ ℚ (a ≡ 1): if S − e = p/q then for large N, fract(N!S) = fract(N!e) =
  Σ_{m>N} N!/m!, and x_N ≡ fract(N!e) − c_N = −N!·Σ_{m>N} 1/(m!(m!−1)) ≈ −1/((N+1)(N+1)!), so x_N > 1 − 1/N for all large N.
  Hence C' ⇒ (S ∉ ℚ and S − e ∉ ℚ); root ⇒ C' would need S − e ∉ ℚ from S ∉ ℚ, unknown.
- C' strictly weaker than h3 (reverse unknown): ¬h3 allows digits a_m ∈ {−1,0,1}; ¬C' only {0,1}. A real whose digits are
  eventually in {−1,0,1} with infinitely many −1's satisfies C' but not h3.
- Gain over route 1: the open core drops the exclusion of digit −1 (equivalently of S + e-type congruences); it is the
  weakest "x_N below the window" core, the window being (1 − 1/N, 1 − 1/(N+1)).
- Honest limit: C' is still about the same residues; no mechanism proves it. But it is a strictly better core than h3
  for the same proof, and h3's proof (if ever found) proves C' for free.
14:48Z wrote B/partial-h6-route3.lean: partial on erdos-68--h6 with one hole C' (first disjunct). About to fast-check.
14:48Z (timestamps fixed: my 14:50Z/14:55Z labels above were written at 14:46Z/14:47Z.)
14:48Z fast check verify on erdos-68--h6 of B/partial-h6-route3.lean: assembly elaborates; only `declaration uses sorry`; printed
hole: ⊢ ∀ (M : ℕ), ∃ N, M ≤ N ∧ Int.fract (∑ n ∈ Finset.Icc 2 N, ↑N.factorial / (↑n.factorial - 1)) ≤ 1 - 1 / ↑N. log_id 01M6424PDRXFFD3JEFNXM4BV9F.
Digit picture for the steward (refines 14:46Z): with δ_N = 1 − x_N and k_N = ⌊(N+1)δ_N − ε_{N+1}⌋ ∈ {0..N}:
root ⇔ k_N ≠ 1 i.o.;  C' ⇔ k_N ≥ 2 i.o. (k_N = 1 then δ_N ≥ 1/N needs δ_{N+1} ≳ 1/N, pushing to a later k ≥ 2);  h3 ⇔ k_N ≥ 3 i.o. (approx.);
h6's second disjunct ⇔ k_N = 0 i.o. So h3 ⇒ C' ⇒ root, and h6 = C' ∨ (k = 0 i.o.).
14:49Z precheck of B/partial-h6-route3.lean on erdos-68--h6 (artifact partial, path attempts/20261029T144921Z-t1028-b-partial.lean): job 01M64264AGV6E9DBS1TYP8Q3KE (graph_commit 4f771bb8). Not submitting before A's pick.
14:49Z A picked A1 on --h3 and OK'd B-4 on --h6. CLAIMED erdos-68--h6: claim 01M64272K8DB747DHQ4H2K7GP7 (ttl 2h).
14:50Z drafted B/postmortem-h6-draft.yaml (to file at the end, on --h6 or its new child).
14:54Z precheck 01M64264AGV6E9DBS1TYP8Q3KE PASS (steps 1,2,4-8). Hole h1 closed_type = ∀ (M : ℕ), ∃ (N : ℕ), M ≤ N ∧ Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) ≤ (1 : ℝ) - (1 : ℝ) / (↑N : ℝ); expected_new, expected_node_id erdos-68--h6--h1; expected_witness ∃ (M : ℕ), True. Wrote B/partial-h6-route3.1.witness; re-prechecking with it.
14:54Z precheck with witness: job 01M642FVV8BRTRMGW8NR90HKMA
14:58Z Plain form of C' in S's own factorial digits (S = Σ a_m/m!, 0 ≤ a_m ≤ m−1; φ_N = fract(N!S) = Σ_{m>N} a_m N!/m!):
x_N = fract(φ_N − c_N), and since 0 ≤ φ_N, c_N < 1: x_N ≤ 1 − 1/N ⇔ c_N ≤ φ_N ≤ 1 − 1/N + c_N. With φ_N = (a_{N+1}+φ_{N+1})/(N+1) and
c_N = (1 + ε_{N+1} + c_{N+1})/(N+1): the lower bound holds if a_{N+1} ≥ 2, fails if a_{N+1} = 0, and for a_{N+1} = 1 passes to N+1;
the upper bound fails only if a_{N+1} = N and φ_{N+1} > 1 − 1/N + ε + c_{N+1}. Hence (one-way each):
  digits a_n ∈ [2, n−2] infinitely often ⇒ C' ⇒ digits a_n ≥ 2 infinitely often.
Compare: root ⇔ digits not eventually 0 and not eventually n−1; A1 (D) ⇔ a_n ∈ [δn, (1−δ)n] i.o. So A1 ⇒ h3 ⇒ C' ⇒ root.
14:59Z precheck 01M642FVV8BRTRMGW8NR90HKMA PASS, carried witness checked:true. SUBMITTED #1177 (submission 01M642R6EGECPCCBEZN8VBR10T), partial on erdos-68--h6, hole h1 → erdos-68--h6--h1 (expected_new).
15:02Z Next level, prepared (B/skel-h6h1-digits-draft.lean, fast check okay but for sorry, log 01M642TKK8T4QKZ39QXDFBV8SZ): a partial on the
future erdos-68--h6--h1 (C') with holes
  ht = erdos-68--h5 verbatim (expect lemma, proved), and
  hd : ∀ M, ∃ N ≥ M, 2/(N+1) ≤ fract(N!·S) < 1 − 1/(N+1), i.e. S's factorial digit a_{N+1} = ⌊(N+1)·fract(N!S)⌋ has 2 ≤ a_{N+1} ≤ N−1 i.o.
Assembly: fract(F_N) = fract(N!S) − c ∈ [0, 1 − 2/(N+1)) ⊂ [0, 1 − 1/N].
Narrower than C' (reverse unknown): C' holds at N with a_{N+1} = 1, a_{N+2} = N+1 (max), which hd excludes at both N and N+1; a real
whose digits are eventually in {1, max} satisfies C' (when the 1's are followed by maxima) but not hd. Weaker than A1 (A1's fixed δ ≥ 2/(N+1) for
large N). Not comparable to h3 by anything I know (hd gives fract(F_N) < 1 − 2/(N+1), not < 1 − 2/N).
Gain: the open core becomes a statement about S alone (no F_N), the plainest form for the steward. Honest limit: same digits, no mechanism.
15:04Z #1177 MERGED (seen by get_submission; waiting_on products).

## Findings

- **F-B1 (bug, minor) MCP result shape differs between tools.** 14:54Z. `check_lean` (verify, node erdos-68--h6) answered
  `result.structuredContent = {status, body}`; `get_precheck {"job_id":"01M64264AGV6E9DBS1TYP8Q3KE"}` answered with no
  `structuredContent`, only `result.content[0].text` (the job JSON, no status wrapper). Expected one shape for every tool.
  Cost ~3 min: my poll loop keyed on structuredContent never saw `done`. Repro: call both tools and compare `result` keys.
- **F-B2 (bug, known: prior #1 and the push starvation) #1177's bot commit slow.** Merged 15:03:02Z (graph run 40897594017).
  "Re-derive the verdict" 15:03:42–15:07:10 (208 s) and "Join what this merge made provable" 15:07:10–15:10:01 (171 s) for a
  one-hole partial whose assembly is `Or.inl`; then "Commit the attestation and the products" in_progress from 15:11:34Z and still
  running at 15:14:28Z, while main moved under it 5 times (gate: #1171 pass (replayed), #1173 pass, two erdos-849 outlines).
  Expected: a few minutes ("three to five for a proof or a partial", guide). Cost: the next level (on --h6--h1) cannot be
  prechecked until it lands. Repro: `gh run view 40897594017 --json jobs`.
  Second data point, #1207 (run 40902525986, merged 15:32:01Z): re-derive 15:32:45–15:36:03 (198 s), join 15:36:03–15:38:27 (144 s),
  products from 15:38:28Z. Two one-hole/two-hole partials whose assemblies are a few lines each spend ~6 min re-deriving a signed verdict.
- **F-B3 (bug, known family: prior quiet-window finding) another target's appends move main under our post-merge push.** At 15:41:19–15:41:30Z
  graph main took four erdos-849 append merges (#1193 explainer, #1195 and #1197 postmortems, #1198 gloss) while #1207's post-merge job
  (run 40902525986) was in "Regenerate the merge products" and about to push; #1177's push likewise sat 15:11:34–15:17:29Z while main
  moved five times, mostly erdos-849 bot commits. Our board's quiet window cannot cover another run's target: the push race is graph-wide,
  not per target. Expected: one lane per target means one target's appends cannot starve another's attestation. Cost: ~6 min on #1177
  (and #1207 pending as of 15:42Z), which pushed my postmortems and the next level's start toward the 16:00Z cut.

## Log (continued)

15:14Z waiting for #1177 bot commit (commit step pushing since 15:11:34Z).
15:18Z wrote B/partial-h6h1-digits.lean (+ .1.witness for hd), verify fast check ok but sorry (log 01M643TYR8AXNEZ3X7TZWEFMKK); prechecking on erdos-68--h6--h1 (ts 20261029T151822Z).
15:18Z first precheck refused before any job: 400 partial-unlabelled, label-long (hd label 63 chars > 60) — fair, caught pre-job. Shortened label; precheck job 01M643VHA0A2A0614H4S65A08D (graph_commit eb1181d7).
15:19Z CLAIMED erdos-68--h6--h1 (claim 01M643W6SGG0MFSR2Q8AT210XP). Note: get_submission #1177 still 'merged / waiting_on products / became None' at 15:19Z though 'gate: #1177 pass' is on main since 15:17:29Z.
15:19Z correction: #1177 holes[].became populated by 15:19Z (≈2 min after the bot commit).
15:23Z precheck 01M643VHA0A2A0614H4S65A08D PASS: ht restates erdos-68--h5 (expected_new false → lemma, --h5 is an uncle), hd → erdos-68--h6--h1--h2 (new; witness checked:true); hd closed_type = ∀ (M : ℕ), ∃ (N : ℕ), M ≤ N ∧ (2 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) ≤ Int.fract ((↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ))) ∧ Int.fract (…) < (1 : ℝ) - (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)). SUBMITTED #1207 (submission 01M6443M38CVMJN9VCPWN9C75T).
15:23Z wrote B/postmortem-h6.yaml (final, to file on erdos-68--h6 after #1207's bot commit). Draft B/postmortem-h6-draft.yaml superseded.
15:32Z #1207 MERGED (~15:32Z). Quiet window posted.
15:33Z wrote B/postmortem-h6h1h2.yaml (to file on erdos-68--h6--h1--h2 after #1207's bot commit).
15:43Z 'gate: #1207 pass' 15:42:39Z; --h6--h1 META: deps [--h6--h1--h2], lemmas [ht → erdos-68--h5]; became ['erdos-68--h5','erdos-68--h6--h1--h2'].
15:43Z SUBMITTED #1209 postmortem on erdos-68--h6 (B/postmortem-h6.yaml) and #1210 postmortem on erdos-68--h6--h1--h2 (B/postmortem-h6h1h2.yaml).
15:44Z list_sufficient_sets erdos-68: routes erdos-68@1, @2, --h3@1, --h6@1, --h6--h1@1 all live; two sets: {--h3--h2} via [root, --h3] and {--h6--h1--h2} via [root, --h6, --h6--h1]. Prior finding #2 (route 2 dropped) no longer seen. Released claims on --h6 and --h6--h1 (work done).
15:45Z #1209 merged 15:44:15Z, #1210 merged 15:44:19Z. Problem page shows --h6--h1 and --h6--h1--h2 with their labels (curl 200, connect 0.03 s). Line done; writing final report.

## Final report

1. **Landed** (pseudonym t1028-b; all merged, none by hand):
   - #1177, a **partial on `erdos-68--h6`**, merged 15:03Z, bot commit 15:17:29Z. One hole, `erdos-68--h6--h1` (C'): ∀M ∃N≥M, fract(F_N) ≤ 1 − 1/N. It keeps only this node's lower disjunct. Its witness was carried.
     - Order: --h3 ⇒ C' ⇒ root.
     - Neither reverse is known. D checked both separations exactly.
   - #1207, a **partial on `erdos-68--h6--h1`**, merged 15:32Z, bot commit 15:42:39Z. It has two holes:
     - `ht` restates `erdos-68--h5` and is recorded as a lemma, already proved.
     - `hd` is the new `erdos-68--h6--h1--h2`: ∀M ∃N≥M, 2/(N+1) ≤ fract(N!·S) < 1 − 1/(N+1). In words, S's factorial digit a_{N+1} lies in [2, N−1] infinitely often. Its witness was carried.
     - Order: A1 (`--h3--h2`) ⇒ hd ⇒ C'.
     - hd and --h3 are incomparable (D).
   - #1209, a **postmortem on `--h6`**: the route search and the digit hierarchy, with the shared barrier that every core also forces S − e ∉ ℚ.
   - #1210, a **postmortem on `--h6--h1--h2`**: no honest level 3 under hd.
   - The record now has two one-statement sufficient sets for the root: {`--h3--h2`} and {`--h6--h1--h2`} (`list_sufficient_sets`).
2. **Unfinished business:**
   - **A correction to #1209, which is merged and immutable.** Its detail says the root alone "does not" force S − e ∉ ℚ. It should say "is not known to" (D's nit, 15:45Z). Root ⇒ T ∉ ℚ is vacuous if T is irrational; what we showed is only that no argument from the tail shape gives it. A later record, such as D's literature on --h6--h1, can carry the fix if the lead wants it on the record.
   - None of it is mine.
   - The closing proofs of `--h6--h1` (assembly via hd + --h5) and `--h6` (Or.inl) are in the merged partials. Each node closes once its hole is proved.
   - The root's route-2 closing proof needs `--h6`. It is the root's existing @2 assembly.
   - Words for the new nodes: D is filing the glosses and literature, C the explainer of #1207's assembly.
3. **Findings**, most important first:
   - F-B2: each post-merge job spends ~6 min re-deriving and joining for a trivial partial. Runs 40897594017 and 40902525986. Prior #1, still present.
   - F-B3: the push race is graph-wide. erdos-849's appends and bot commits moved main 5 and 4 times under our pushes, and no per-target quiet window can prevent it.
   - F-B1: `get_precheck` returns only `content[0].text`, while `check_lean` returns `structuredContent`.
   - The `partial-unlabelled label-long` refusal came before any job, which is good.
   - Not a defect: `holes[].became` lagged the bot commit by about 2 minutes.
   - Prior finding #2 (route dropped) was not seen today: route @2 and its sub-routes are listed.
4. **What would have made me twice as productive:** About 15 of my 90 minutes were mathematics. About 45 were waiting: two merges at ~14 and ~11 minutes from merge to bot commit, plus about 4 minutes per precheck. The open-core search itself was quick, because the useful structure (the factorial-digit hierarchy root ⇔ a_n ≢ 0, C', hd, A1) fell out in 10 minutes. The next level could only be prechecked once the previous partial's bot commit had landed.
   - A post-merge job that does not re-derive a verdict the gate already signed would have halved the waits.
   - So would a push that cannot be starved by other targets' merges.
   - So would a way to precheck a skeleton of a hole that is still pending (against the parent partial's printed closed type).
   - With those, the two levels would have taken 15 minutes instead of 45.
