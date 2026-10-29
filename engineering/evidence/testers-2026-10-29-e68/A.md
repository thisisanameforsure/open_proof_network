# A — log (pseudonym t1028-a)

14:41Z A: start; read BRIEF, prior/README, prior A.md, the three prior postmortems on --h3 (residues, recursion/digits, denominators: all equivalent to --h3).
14:46Z A: cloned graph (main 4f771bb8ad); --h3 Statement read; own JSON-RPC client in scratch (mcp.py); tools/list ok.

## Skeleton candidates for erdos-68--h3 (14:46Z)

Notation: F_N = Σ_{n=2}^N N!/(n!−1), f_N = fract(F_N), S the root's sum, c_N = N!·S − F_N ∈ (0, 2/N] (proved node --h2),
‖x‖ = distance to the nearest integer. Any hole H with the sibling holes proved implies --h3, so H is at least as strong as --h3;
the honest test is that --h3 ⇒ H is NOT known. Prior day showed every *reformulation* (residues, recursion, factorial digits,
common denominators) is equivalent to --h3; so the only honest sub-skeletons are strengthenings, and the question is which
strengthening is the cleanest statement a number theorist would recognise.

**A1 (my pick candidate) — "N!·S does not tend to the integers".**
- hole t (elementary, ALREADY PROVED as a node): the tail split, stated byte-equal to erdos-68--h2's statement → expected to be recorded
  as a lemma of --h3 (D-12 v3.38), no new node.
- hole core (open): ∃ δ > 0, ∀ M, ∃ N ≥ M, δ ≤ fract(N!·S) ≤ 1 − δ. I.e. ‖N!·S‖ ↛ 0.
- assembly (proved, elementary): take N ≥ max(M, 2, 2/δ); fract(F_N) = fract(N!S) − c_N ≤ 1 − δ − c_N < 1 − 2/N.
- Why strictly narrower (stronger, no reverse known): --h3 fails iff f_N ≥ 1 − 2/N eventually, i.e. N!·S lies within 2/N
  (on one side) of an integer for all large N; that forces ‖N!S‖ → 0, so core ⇒ --h3. But --h3 still allows ‖N!S‖ → 0 at any
  slower rate (e.g. N!S within 3/N of an integer, from the side --h3 does not exclude), so --h3 does not give the core.
  Not equivalent to the root either: the root is "N!S ∉ ℤ infinitely often", i.e. ‖N!S‖ ≠ 0 i.o.; the core asks ‖N!S‖ ≥ δ i.o.
  Position: root ⇐ --h3 ⇐ core. Recognisable: e is the model number with ‖N!e‖ → 0 (N!e = integer + Σ_{j>N} N!/j!), and
  S = (e − 2) + T with T = Σ_{n≥2} 1/(n!(n!−1)); the core says S (equivalently T) is not "e-like" in this sense.
  Heuristic: for a generic real ‖N!x‖ is equidistributed, so the core should hold. It has no finite-N window and no analysis
  beyond one real number.
**A2 — "f_N does not tend to 1".** core: ∃ δ > 0, ∀ M ∃ N ≥ M, f_N ≤ 1 − δ; assembly elementary (no other hole). Strictly
  stronger than --h3 (--h3 allows f_N → 1 at rate 3/N), reverse not known. Weaker (better) than A1 by one side, but a one-hole
  window change on the same finite sum: close to "a trivial variant". Ranked second.
**A3 — window shrinking via the recurrence (REJECTED: equivalent).** F_{N+1} = (N+1)F_N + 1 + 1/((N+1)!−1). If f_N and f_{N+1}
  are both bad then 1 − f_N lies within ~3/(N+1)² of k/(N+1), k ∈ {0,1,2}. So "--h3" ⇔ "f_N avoids three windows of width
  O(1/N²) infinitely often". Interesting (makes the heuristic Borel–Cantelli-strong) but equivalent to --h3, so not a
  decomposition. Could go in words/annex, not as a hole.
Rejected also (prior): residues mod n!−1, factorial digits of T, lcm denominators — all equivalent or false.
Deep-hole level 2 for A1: core(S) ⇔ core(T) via ‖N!e‖ → 0 — equivalent, so NOT an honest split; none planned unless B has one.
14:50Z A: drafted A/partial-h3-A1.lean (A1 skeleton on --h3; not submitted yet), fast-checking.
14:47Z A: fast check of A1 (log 01M6421TM877S7SSMNJ7BDAPQ6): elaborates, only `sorry` warnings (+ one unused push_cast, removed).
14:47Z A: precheck 01M6422N00JZK93P757RF6FJ17 of A1 bundle (attempts/20261029T145300Z-t1028-a-partial.lean + .1.witness for hcore = `True`), started early so the pick is not waiting on it; pick still open until 15:05Z.
  Precise gap between --h3 and A1's core (why no reverse): ‖N!S‖ → 0 ⇔ S = q + Σ_N j_N/(N+1)! with integers j_N = o(N)
  (from r_{N+1} = (N+1) r_N − j_N, r_N the signed distance); ¬--h3 forces j_N into a bounded set ({0,1,2} up to the e-shift).
  So --h3 excludes bounded "digit" sequences, A1's core excludes all o(N) ones. Nothing known bridges them.
14:49Z A: claimed erdos-68--h3 (claim 01M6426788W45JY29AV28KFJ3Z, ttl 2h). Posted pick A1 on the board with exact holes.
14:50Z A: level-2 split of hcore considered and REJECTED as dishonest: S = (e−2) + T, T = Σ_{n≥2} 1/(n!(n!−1)), and
  N!(e−2) = integer + θ_N with 0 < θ_N < 1/N, so hcore(S) ⇔ hcore(T) (each gives the other with δ/2). Equivalent, not narrower.
  Other splits (recurrence r_{N+1} = (N+1) r_N − j_N) are the digit restatement, equivalent too. No level 2 planned.
14:51Z A: precheck 01M6422N00JZK93P757RF6FJ17 PASS (steps 1,2,4–8); printed holes saved in A/precheck-A1-holes.json:
  ht → restates erdos-68--h2 (expected_new false); hcore → expected erdos-68--h3--h2 (new), carried witness checked:true.
  Note: the new hole is numbered --h2 although --h3 has no --h1: the restating hole consumed the number (prior F-A8, still present).
14:52Z A: SUBMITTED #1176 (submission 01M642A94GR83SRGXR7KB541FS), partial on erdos-68--h3 (A1): ht → lemma erdos-68--h2, hcore → erdos-68--h3--h2.
14:53Z A: drafted A/closing-h3-draft.lean: --h3's closing proof through #1176 (ht := erdos_68__h2, hcore := erdos_68__h3__h2), for the day --h3--h2 is proved; check after the holes exist (Context names).
14:55Z A: drafted A/literature-h3--h2.json (status open) for the new hole; to file after 'gate: #1176 pass'.
14:56Z A: drafted A/postmortem-h3--h2.yaml (level-2 splits equivalent), to file near the end.
14:56Z A: #1176 MERGED (seen 14:56:24Z, ~4 min after submit). waiting_on products.
15:05Z A: 'gate: #1176 pass' = 6d5fe2a50d (seen 15:05:57Z; merge fd983a0255 at ~14:56Z → ~9.5 min post-merge, prior #1 still present).
  On main: erdos-68--h3 META lemmas [{hole: ht, node: erdos-68--h2}], deps [erdos-68--h3--h2]; Context.lean has erdos_68__h3__h2 and erdos_68__h2.
  erdos-68--h3--h2: status ready, origin compiler-derived (no annex cited, by choice), Statement = precheck closed_type (D audited 15:06Z CLEAN).
  So prior F-A9 (restating hole → node null) did NOT recur for a sibling-of-parent restatement: lemma recorded correctly.
15:07Z A: closing draft A/closing-h3-draft.lean fast-checked mode verify on erdos-68--h3 (log 01M6436EG874EWXZH905FDZ21V): elaborates; only the Context's own sorries (lint context-restated, sorry-reported, as the guide says). Ready for the day --h3--h2 is proved.
15:07Z A: #1177 (B, partial on --h6) merged 15:04Z before #1176's bot commit; quiet window now waits on 'gate: #1177 pass' before I file the literature record.
15:13Z A: added D's barrier (core ⇒ S − e ∉ ℚ) to the literature draft and postmortem draft.
15:18Z A: #1177's bot commit still absent 14 min after its merge (15:03:02Z merge commit push → run 40897594017). Steps: products regenerated 15:10:02–15:11:33Z, ledger 15:11:34Z,
  then "Commit the attestation and the products (pushed with the wri…)" in_progress since 15:11:34Z (≥6 min) while main moved 5 times (outline erdos-68 15:08, gate #1173 15:10, #1171 replayed 15:12, outline erdos-849 15:13, gate #1174 15:15). Looks like the push-starvation finding (prior README §quiet-window, erdos-849 run 10-27) — main is being moved by the OTHER target's lane, which no erdos-68 board protocol can hold. See F-A2.
15:18Z A: #1196 literature (open) on erdos-68--h3--h2 (A/literature-h3--h2.json).
15:21Z A: considered (and DROPPED, not submitted) a one-hole "link" partial on erdos-68--h6--h1 whose hole restates --h3 (lemma), recording --h3 ⇒ C' mechanically (A/partial-h6h1-link.lean, fast check log 01M643YF20RHYY2YRTM2RRYJ77: elaborates). Reason: a proof of --h3 already settles the root through route 1, so the link closes nothing new; under "skeleton first, no side results" it is structure for its own sake. Left as a file for the lead/steward.
15:21Z A: list_sufficient_sets erdos-68: route erdos-68@2 now shows h1 → erdos-68--h1 (proved) — prior F-A9 FIXED; route erdos-68--h3@1 = [ht → erdos-68--h2 proved, hcore → --h3--h2 ready]; 2 sets, each with one open statement (--h3--h2; --h6--h1).
15:22Z A: #1205 postmortem/v2 on erdos-68--h3 (A/postmortem-h3-window.yaml: window-shrink ≡, "f_N ↛ 1" not new structure, gap of the merged core). A/postmortem-h3--h2.yaml NOT filed: C's #1204 covers the same level-2 splits. postmortem/v2 takes model_and_tooling → prior #8 fixed.

## Findings

### F-A1 (bug, still present — prior README #1 and the quiet-window note): post-merge bot commits take 9–15 min, and the push step stalls while OTHER targets move main
- #1176 (partial, erdos-68--h3): merge fd983a0255 ~14:56Z; `gate: #1176 pass` 6d5fe2a50d at 15:05:57Z (~9.5 min).
- #1177 (B's partial, erdos-68--h6): merge pushed 15:03:02Z (run 40897594017); products regenerated 15:10:02–15:11:33Z, ledger 15:11:34Z;
  step "Commit the attestation and the products" in_progress from 15:11:34Z; `gate: #1177 pass` eb1181d759 only at 15:17:29Z (14.5 min).
  In those 6 min main moved 5 times: outline erdos-68 (15:08), gate #1173 (15:10), #1171 replayed (15:12), outline erdos-849 (15:13), gate #1174 (15:15) —
  four of five from the erdos-849 run's lane.
- Third data point: #1207 (B's partial on --h6--h1) merge 6a334c4033 at 15:31:57Z; `gate: #1207 pass` d36b055d66 at 15:42:39Z (10.7 min), with 10+ erdos-849 append merges (#1185–#1188 at 15:36Z) and an erdos-849 outline commit landing in between.
- Expected: the guide says the post-merge is "three to five [minutes] for a proof or a partial". Our board's quiet window protects erdos-68 only;
  nothing an erdos-68 contributor can do holds another target's bot commits. Cost: ~10 min of held appends (literature, glosses, explainers) per partial.
- Repro: merge a partial on one target while another target's lane is merging appends; time the `gate: #N pass` commit against the merge.

### F-A2 (minor, still present — prior F-A8): a hole that restates an existing node consumes a hole number
- Precheck 01M6422N00JZK93P757RF6FJ17 / receipt of #1176: `ht` restates erdos-68--h2 (expected_new false), `hcore` → `erdos-68--h3--h2`. There is no `--h3--h1` and never will be.
  The steward sees --h3--h2 under --h3 and looks for --h3--h1. Cost: none beyond confusion. Repro: any skeleton whose first hole is a lemma.

### F-A3 (feature request, same family as prior README "for the steward" note): no place for a cross-route implication
- Today's cores are ordered: root ⇐ --h6--h1 (C') ⇐ --h3 ⇐ --h3--h2, and --h3--h2 ⇒ B's hd. The only way to put "--h3 ⇒ --h6--h1" on the record is a one-hole
  "link" partial on --h6--h1 whose hole restates --h3 (A/partial-h6h1-link.lean, elaborates) — a decomposition that closes nothing new. I did not file it.
  The steward has the ordering only in words (literature #1196, postmortem #1205, board). Cost: 5 min deciding.

### Confirmations (prior findings now fixed)
- prior F-A9 FIXED: route erdos-68@2's h1 now reads erdos-68--h1 (proved) in list_sufficient_sets (15:21Z); today's lemma (ht → erdos-68--h2) is recorded in
  --h3's META.yaml `lemmas`, graph.json and on the page (dash-dot lemma edge in the key).
- prior #8 FIXED: postmortem/v2 takes `model_and_tooling` (#1205).
- Precheck → submit → merge of a 2-hole partial with a carried witness and a lemma: 14:47Z → 14:56Z, no refusal, no human.

## Final report (A, t1028-a)

### 1. What I landed (graph PRs, all through the MCP, all merged, nobody merged by hand)
- **#1176 partial on erdos-68--h3** (route erdos-68--h3@1, plain partial, no annex): two holes.
  - `ht` = erdos-68--h2 verbatim → recorded as a **lemma** of --h3 (already proved; META `lemmas`, Context, page).
  - `hcore` → new node **erdos-68--h3--h2**, ready (witness `True` carried): ∃ δ > 0, for infinitely many N, δ ≤ fract(N!·S) ≤ 1 − δ,
    i.e. the distance from N!·S to the nearest integer does not tend to 0 (factorial digits: min(a_n, n − a_n) ≥ δn i.o.).
  - Honesty: hcore ⇒ --h3 (assembly, proved); --h3 ⇏ hcore known — --h3 fails only for eventually *bounded* factorial digits (after the e-shift),
    hcore fails for all *o(n)* ones. D audited the precheck and main: zero mismatches. Like every core today, it also implies S − e ∉ ℚ (D's barrier).
- **#1196 literature (open)** on erdos-68--h3--h2 (position in the chain, digit form, ≡ same statement for T = S − (e − 2)).
- **#1205 postmortem/v2** on erdos-68--h3 (other cores: window shrink via the recurrence ≡ --h3; "f_N ↛ 1" is a margin change, no new structure).
- Claim 01M6426788W45JY29AV28KFJ3Z on --h3, released 15:44:57Z (#1176 merged; nothing more of mine on --h3).

### 2. Unfinished business for the lead
- `A/closing-h3-draft.lean`: --h3's closing proof through #1176 (ht := erdos_68__h2, hcore := erdos_68__h3__h2). Fast-checked verify on --h3
  (log 01M6436EG874EWXZH905FDZ21V, only the Context's sorries). Waits on a proof of --h3--h2; then the root closes by prior/B/proof-erdos-68-closing.lean.
- `A/partial-h6h1-link.lean` (elaborates, NOT filed): records --h3 ⇒ --h6--h1 as a lemma link. Closes nothing new; the steward's call (F-A3).
- `A/postmortem-h3--h2.yaml`: not filed, superseded by C's #1204.
- Nothing else waits on me. Level 2 of --h3--h2 was examined and is not honest (S ↔ T split and the digit recurrence are both equivalent).

### 3. Findings, most important first
- F-A1: post-merge bot commits 9.5 and 14.5 min; #1177's push step sat 6 min while the *erdos-849* lane moved main 4 times — the per-target quiet window cannot protect against another target (prior #1, worse under two runs).
- F-A3 (feature): no record for an implication between cores of different routes (root ⇐ --h6--h1 ⇐ --h3 ⇐ --h3--h2 ⇒ hd); only words carry it.
- F-A2: the lemma hole consumed a number: --h3--h2 with no --h3--h1 (prior F-A8, still present).
- Confirmed fixed: prior F-A9 (restating hole → null; route 2 now complete in the sufficient sets; today's lemma recorded right) and prior #8 (postmortem/v2 has model_and_tooling).

### 4. What would have made me twice as productive
The mathematics of the pick took twenty minutes and the record took ten more (and C's explainer #1194 of the assembly, checked against the Lean, is faithful) (precheck 4 min, gate and merge 4 min, both clean): the service side was
not the bottleneck for a skeleton this time. What cost the rest of the run was that --h3 has no honest sub-skeleton with a *narrower* open core —
every reformulation the four of us found (residues, recurrence, digits, truncation, window shrink, the S/T split) is equivalent, so the only honest
moves are strengthenings, and the day's real gain was the ordering of the cores (root ⇐ C' ⇐ --h3 ⇐ A1), which the record cannot hold as structure.
Twice as productive would have been a place to state "core X implies core Y" (a checked implication record between nodes, Lean-proved, drawn on
the page) instead of choosing between a redundant link partial and prose; and, for the appends, a bot-commit queue that does not let another
target's lane starve this target's post-merge push, so the quiet window would be minutes rather than a quarter of an hour.
