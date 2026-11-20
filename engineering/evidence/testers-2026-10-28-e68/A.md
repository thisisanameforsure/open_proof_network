# A (t1028-a) log — erdos-68

13:02Z A: start; cloned graph, reading AGENTS.md
13:05Z A: tutorial precheck 01M619TTP84YRQND2KP5NJ6MG3 (anonymous) -> pass 13:09Z; token minted 13:10Z for pseudonym t1028-a (kept in private scratch only).
13:10Z A: MCP client = my own python JSON-RPC helper (scratch/mcp.py). Write tools answer {status, body}; check_lean also answers {status, body} (guide line 27 says read tools answer the bare document; check_lean is not a write) -- minor, see Findings.

## Literature (13:03Z–13:10Z)
- erdosproblems.com/68 (edited 2025-09-28): "Is sum_{n>=2} 1/(n!-1) irrational?" Refs Er68d, Er88c p.102, Er90, Er97e, Er97f. OEIS A331373.
  Weisenberg: S = sum_{k>=1} sum_{n>=2} (n!)^{-k}. Erdős [Er88c]: sum 1/(n!+t) "should be transcendental for every integer t".
  No partial result, no reduction, no criterion on the page.
- Forum thread 68 (one post, williamwkcook, 2026-09-11, unreviewed): liminf log L_N/(N^{3/2} log N) >= 2√2/3 for L_N = lcm_{2<=n<=N}(n!-1);
  states L_N·(S - H_N) -> infinity so "clearing denominators term by term cannot work"; a congruence criterion that needs unproved facts.
- No applicable known irrationality criterion found: Erdős/Badea-type criteria for sum 1/a_n need a_{n+1} >~ a_n^2 (doubly exponential); n!-1 grows only by a factor n+1.
- **Lead's guess is dead (checked by hand):** gcd((N-1)!-1, N!-1) divides N!-1 - N((N-1)!-1) = N-1, so
  L_N >= lcm(N!-1,(N-1)!-1) >= (N!-1)((N-1)!-1)/(N-1) ~ N!(N-2)!, while tail_N ~ 1/(N+1)!. So L_N·tail_N -> infinity:
  the criterion hole "L_N·tail_N -> 0 along a subsequence" is provably FALSE; a skeleton on it would carry a refutable hole.
  Same for the reduced denominator D_N of H_N in place of L_N: needs D_N <~ (N+1)! i.e. massive cancellation, heuristically false.

## Skeleton candidates (13:10Z)
1. **Factorial multiplier (the proof of irrationality of e, done honestly).** If x = p/q then N!·x ∈ Z for N >= q.
   N!·S = F_N + c_N with F_N = sum_{n=2}^N N!/(n!-1) (finite, rational) and 0 < c_N = N!·tail_N <= 2/N.
   N!S ∈ Z iff fract(F_N) = 1 - c_N. So: h1 (elementary criterion: N!x ∉ Z for arbitrarily large N => x irrational),
   h2 (elementary: tail split and 0 < c_N <= 2/N), h3 (OPEN CORE: for arbitrarily large N, fract(F_N) < 1 - 2/N).
   h3 is strictly stronger than the root and purely arithmetic: a finite sum of rationals, no analysis; it says the
   fractional part of sum_{n<=N} ((n+1)···N mod (n!-1))/(n!-1) avoids a window of width 2/N infinitely often.
   Heuristic: if fract(F_N) were equidistributed the window is hit with probability ~2/N, so h3 should hold. Draft compiles (fast check 13:08Z, okay modulo sorry).
2. Double series: S = (e - 2) + R, R = sum_n 1/(n!(n!-1)); e - 2 irrational is Mathlib-level, but irrationality is not additive, so the core is "R + e irrational" — no narrower. Rejected.
3. Lead's lcm criterion (L_N·tail_N -> 0) — hypothesis provably false (above). Rejected. Reduced-denominator variant: heuristically false. Rejected.
13:19Z A: precheck 01M61A9S6RN8XYDXE2XGTA8326 (skeleton cand. 1, no annex, path attempts/20261028T131200Z-t1028-a-partial.lean) PASS steps 1,2,4-8. Witnesses w1-w3 written (A/w*.witness); w1 first used Irrational.nat_mul (renamed natCast_mul on the pin) — caught by fast check.
13:20Z A: annex submitted: PR #1133, hash 60c3f96117863c5f8df64b6be6d5178d8de0e3ff7996bca4be9a4628810cb206, text A/annex-skel1.md, steps h1/h2/h3.
13:20Z A: claimed erdos-68 (claim 01M61APX48GK270AFHYQGZ8AR4, ttl 3h).
13:21Z A: #1133 (annex) merged within ~2 min of submission.
13:23Z A: precheck of cited skeleton + 3 carried witnesses -> 409 products-pending (nodes_commit d17b936b, rendered 935c6d81, Retry-After 240). Retrying. Bundle: attempts/20261028T132200Z-t1028-a-partial.lean + .1/.2/.3.witness (A/skel1-partial-v2-cited.lean, A/w1-3.witness).
13:28Z A: precheck 01M61B5B1GD2429QNNE59YKP7J accepted after two 409 products-pending (13:24, 13:26); 5 min wait for the annex's render.
13:34Z A: precheck pass, all 3 carried witnesses checked:true.
13:36Z A: SUBMITTED #1134 (submission 01M61BJZJ8MPBSK2F2JBPJGAZ4), partial on erdos-68, holes h1/h2/h3 -> erdos-68--h1/--h2/--h3 expected.
13:39Z A: decided no level-2 split of h3 (reasons on board 13:39Z and in A/postmortem-h3.yaml); drafted A/literature-h3.json (status open) and A/postmortem-h3.yaml, to file after #1134's bot commit.

## Findings

### F-A1 (bug, still present — prior #2 / F2): an annex merge holds the skeleton precheck for ~7 minutes
- 13:19:58Z annex #1133 submitted; merged by ~13:21Z. 13:23Z, 13:24Z, 13:26Z: precheck_submission of the skeleton citing it -> `409 products-pending` ("graph commit d17b936b… changed erdos-68's nodes after 935c6d81…, the commit that wrote its products"), Retry-After 240. Accepted 13:28:33Z (job 01M61B5B1GD2429QNNE59YKP7J).
- Expected: an annex is prose on the node; it should not make the holes un-plannable. Cost: ~7 min on the critical path (the skeleton is the first thing anything else waits on). Repro: submit an annex, precheck a partial on the same node right after it merges.

### F-A2 (docs): check_lean answers in the write-tool envelope {status, body}
- Guide line 26–28: "a read tool answers the document itself, with no envelope". check_lean (needs no token, writes nothing) answered `{"status":200,"body":{...}}` at 13:08Z. Cost: one confused parse (my client read `okay: None`). Minor.

### F-A3 (docs, still present — prior C F-C2): pinned-Mathlib renames
- `Irrational.nat_mul` is `Irrational.natCast_mul` on the pin (fast check 13:17Z, "Unknown constant"). The fast check caught it in seconds; cost ~2 min.
13:42Z A: #1134 merged 13:42:56Z (submitted 13:36Z).
13:55Z A: #1135 literature/open on erdos-68--h3 (A/literature-h3.json). Hole files on main checked: h3 Statement = precheck closed_type; status ready.
13:58Z A: #1138 postmortem on erdos-68--h3 (A/postmortem-h3.yaml).
14:00Z A: explainer dry run ok (hash c5e6e723…); held for B's proofs. Note: subject for an explainer of a merged partial is {kind: proof, proof: <partial hash>}, not {kind: partial} (that one wants module = path and makes a one-section gloss) — 1 refused call.

### F-A4 (bug, record content) — erdos-68's formalization review is reviewing the Apache licence header, not the problem
- 14:12Z `get_review {"target_id":"erdos-68"}` (read_at 469ac9dd): `review.words` = "Copyright 2025 The Formal Conjectures Authors.\n\nLicensed under the Apache License, Version 2.0 …" — the licence block at the top of Statement.lean. `cases: []`, `concepts: []`. Same text in the graph file `targets/erdos-68/review/review.yaml` (opened 2026-10-13 by `network`). `state: needs-intent-signer`, 7 questions q-1…q-7 waiting, each "A variant of the statement agrees with it on every small case checked…", raised by mutants.
- Contrast: erdos-849, erdos-1094, erdos-257, erdos-69 reviews carry the problem's words (LaTeX statement). erdos-68's `target.yaml` has `informal: null` (the others' I did not check).
- Site consequence: the problem page header says "review: needs an intent signer · 1 candidate, 1 cluster, 7 questions waiting" — the steward is asked to sign intent against a licence.
- Expected: the review's words are the problem's statement (erdosproblems.com/68: "Is sum_{n>=2} 1/(n!-1) irrational?") or the review is not opened until there are words. Cost to me: 5 min. Repro: get_review erdos-68, read review.words.
- 14:15Z scope, from the graph clone at main: `grep -l Copyright targets/*/review/review.yaml` = erdos-172, erdos-376, erdos-406, erdos-52, erdos-68 — exactly the five targets whose `target.yaml` has `informal: null`. Every one of those reviews has licence text as its words.
14:24Z A: #1141 explainer of the #1134 assembly (A/explainer-1134.md).
14:30Z A: #1149 approach record, double-series route abandoned-early (A/approach-double-series.json).
14:33Z A: #1151/#1152/#1153 superseding statement glosses of h1/h2/h3 (A/gloss-h1..h3.md).

### F-A5 (docs/feature) — a hole's auto-filed gloss copies the author's prose comment lines, including difficulty remarks the gloss rules forbid
- The skeleton's comment blocks above each have carried prose ("Elementary.", "The open core. …strictly stronger than the root…"). At the merge (#1134) the service filed each hole's first statement gloss from the block: label + claim + *all* other comment lines. Guide (Entry task, step 3): a gloss must "not say whether it is true, hard or important". So the network itself filed three glosses that break its own rule; I superseded them (#1151–#1153).
- Expected: either the guide tells the partial author that the block's prose becomes the hole's gloss and must follow the gloss rules (it says only "the block's other lines are prose about the hole"), or only label + claim are filed. Cost: 15 min to rewrite three glosses. Repro: merge a partial with prose in a hole's comment block; read nodes/<hole>/gloss/*.md.

### F-A6 (bug, still present — prior #6 / A F6): root panel says "Split into — Proved from these holes by …" while the root is open
- 14:33Z https://openproofnetwork.org/problems/erdos-68/ root panel: "How it is being proved Open. … Split into Proved from these holes by 20261028T132200Z-t1028-a-partial.lean (merged in 1936413ac0a1, attestation 001134). h1 → erdos-68--h1 (proved) … h3 → erdos-68--h3 (open)". One line; prior finding, unchanged.

### F-A7 (docs, still present — prior #8): postmortem/v1 has no model_and_tooling field, while annex, literature and approach records take one. Noted when filing #1138.
- 14:42Z the site shows it to the steward: https://openproofnetwork.org/problems/erdos-68/review/ opens "Formalization review of erdos-68 “Copyright 2025 The Formal Conjectures Authors. Licensed under the Apache License, Version 2.0 …”" as the words being reviewed.
- F-A1 timing from main's history: #1133 (annex) merged 13:20:53Z; its bot commit `gate: #1133 pass` (ae1d031a) 13:26:48Z — 6 min of post-merge for a prose file; skeleton precheck accepted 13:28:33Z. Skeleton #1134: merged 13:42:55Z, `gate: #1134 pass` 13:53:29Z (10.5 min). Proofs #1139/#1140: merged 14:03:11Z/14:07:52Z, bot commits 14:23:31Z/14:21:41Z (20 min / 14 min; #1139's landed after #1140's and after four append bot commits) — see C F-C4, B's log.
14:47Z A: route 2 (sharper tail window) — precheck 01M61FB49GCG51KBP68FYB6R7G pass; SUBMITTED #1154 (submission 01M61FNDCRYJAXPYA5KBF5ZV94). Files A/route2-partial.lean, A/r2w1-3.witness. Rationale: h3 ⇒ h3', so h3' is a strictly weaker open core; window 1/(N(N+1)) vs 2/N; exact rationals: h3' and the tail bound hold for every 4 ≤ N ≤ 60.

### F-A8 (minor bug/docs) — a restating hole consumes a hole number, so the ids skip
- 14:46Z precheck 01M61FB49GCG51KBP68FYB6R7G (second skeleton on erdos-68, holes h1/h2/h3): h1 `restates: erdos-68--h1`, `expected_new: false`; h2 → `erdos-68--h5`, h3 → `erdos-68--h6`. No `--h4` exists or is planned. Receipt of #1154 says the same.
- Guide ("After the skeleton merges"): "a second one continues from there … unless it restates a node that already exists, which it then is". Expected --h4/--h5. The steward will see h1, h2, h3, h5, h6 and look for h4. Cost: none beyond confusion. (Will confirm `became` after the merge.)
14:53Z A: #1154 merged 14:52:44Z.
15:04Z A: #1155 lit open on --h6 (A/literature-h6.json); #1156/#1157 glosses on --h5/--h6 (A/gloss-h5.md, gloss-h6.md).
15:05Z A: CORRECTION. B (15:03Z board, #1158) showed erdos-68--h6 ⇔ root; I verified the argument (k_N forced to 1, unwinding gives d_M = c_M). My 14:47Z claim that h6 is a "strictly weaker (better)" core was true only as h3 ⇒ h6; h6 is not narrower than the root in substance. #1155's summary ("irrationality excludes only that one point") is wrong and is being corrected by a new literature record.
15:07Z A: #1160 explainer of #1154 (A/explainer-1154.md). #1159 corrected literature on --h6 (A/literature-h6-corrected.json).
15:08Z A: #1161 postmortem on erdos-68 (A/postmortem-root.yaml).

### F-A9 (bug) — a second skeleton whose hole restates an existing hole of the SAME parent is recorded with that hole pointing nowhere; its route drops out of the sufficient sets
- #1154 (merged 14:52:44Z, `gate: #1154 pass` 15:02:15Z): the precheck said h1 `restates: erdos-68--h1`, `expected_new: false`, `expected_node_id: erdos-68--h1`, and the carried witness for it was `checked: true`.
- On the record at 15:10Z: `targets/erdos-68/graph.json` decompositions[1].holes = `[{"name":"h1","node":null}, {"name":"h2","node":"erdos-68--h5"}, {"name":"h3","node":"erdos-68--h6"}]`; `get_submission 1154` holes: h1 `became: None`; `list_sufficient_sets erdos-68` (read_at 66149bd6): route `erdos-68@2` has hole h1 with node None / status None, and `sets` lists ONE set (route 1 only) — route 2 ({h1 proved, h5, h6}) is not offered as a way to settle the problem at all. `get_node erdos-68` lemmas: [] (it is not a lemma either, rightly, since it is not under another branch). And the ids skip --h4 (F-A8).
- Expected (guide, "After the skeleton merges"): "unless it restates a node that already exists, which it then is" — the hole should be erdos-68--h1, the route should read {erdos-68--h1 (proved), --h5, --h6}, and the sufficient sets should include it.
- Cost: route 2 is invisible on the page's "Ways to settle the problem"; ~10 min diagnosing. Repro: on a node with a merged skeleton, merge a second skeleton one of whose holes is definitionally a hole of the first; read graph.json decompositions and list_sufficient_sets.

## Final report (A, t1028-a) — 15:36Z

### 1. What I landed (graph PRs; all through the MCP, all merged unless noted)
- #1133 annex (stepped outline h1/h2/h3) on erdos-68.
- #1134 **partial (route 1, erdos-68@1)** on erdos-68, cites the annex, carries 3 witnesses: holes erdos-68--h1 (criterion), --h2 (tail split, 0 < c ≤ 2/N), --h3 (open core: frac(F_N) < 1 − 2/N infinitely often; strictly stronger than the root). h1, h2 since proved by B (#1139, #1140).
- #1154 **partial (route 2, erdos-68@2)**: same skeleton with 1/(N+1) < c < 1/N (N ≥ 4): h1 restates --h1, --h5 (sharper tail, elementary; proved by C, #1162), --h6 (frac(F_N) outside (1 − 1/N, 1 − 1/(N+1)) infinitely often). **--h6 is equivalent to the root** (B's argument, I checked): it is the problem in exact finite form, not a narrowing. My first claim that it was a "better core" was wrong in what it implied; corrected on the board and by #1159.
- Words: #1141 explainer of route 1's assembly; #1160 explainer of route 2's; #1151–#1153 and #1156–#1157 statement glosses of --h1/--h2/--h3/--h5/--h6 superseding the auto-filed ones.
- Records: #1135 literature (open) on --h3; #1155 literature (open) on --h6 with a wrong sentence, corrected by #1159; #1138 postmortem on --h3; #1161 postmortem on the root; #1149 approach record (double series, abandoned-early).

### 2. Unfinished business for the lead
- erdos-68--h5: proved by C (#1162, gate line 15:24:11Z), explainer #1163. Nothing waits on it.
- Route 2's approach line (immutable, in the partial) says "the open core is strictly weaker" — true relative to h3 but it reads as a narrowing; the steward should know h6 ⇔ root (B's postmortem #1158, my #1159, #1161). A steward may want to shelve route 2 or keep it as the exact finite reformulation.
- Route 2 is invisible in the sufficient sets because of F-A9; nothing to do on the record, it is a product bug.
- B fast-checked the direction root ⇒ h6 in Lean (B/h6_of_root.lean, not on the record; no protocol place for a 'root → hole' proof on a non-variant). Worth a decision on whether h6 ⇔ root should be recorded mechanically (e.g. as a related variant) rather than only in words.
- The root's closing proof through route 1 is prepared by B (B/proof-erdos-68-closing.lean) for the day --h3 falls.

### 3. Findings, most important first
- F-A4: the formalization reviews of erdos-52/68/172/376/406 (exactly the targets with `informal: null`) review the Apache licence header, not the problem; 7 intent questions wait on erdos-68's.
- F-A9: a skeleton hole restating a same-parent hole is recorded as node null; the route disappears from the sufficient sets; ids skip (F-A8).
- F-A5: a hole's auto-filed gloss copies the author's prose comment lines (incl. "Elementary." / "open core"), breaking the gloss rules the guide sets.
- F-A1: an annex merge holds the dependent skeleton precheck ~7 min (still present, prior #2); post-merge of a proof 14–20 min while appends' bot commits land first (C F-C4).
- F-A6 (prior #6 still present), F-A7 (postmortem has no model_and_tooling, prior #8), F-A2, F-A3 (minor docs).

### 4. What would have made me twice as productive
See the end of this file.

### 4. (paragraph) What would have made me twice as productive
The mathematics on this problem took about forty minutes; the rest of the three hours was the record's pace. B had the proofs of h1 and h2 fast-checked against the exact hole types at 13:19Z, before the skeleton was even submitted, yet they could only be prechecked after the skeleton merged and its post-merge job wrote the holes (13:53Z), and only became "proved" after a 14–20 minute post-merge each (14:23Z): letting a skeleton carry proofs of its holes as it already carries their witnesses would have closed both in the skeleton's own merge. The second cost was choreography by hand: every append had to be timed around other people's proof merges on a text board (the quiet-window rule), and each append that merged also made the open proof branches "behind" and cost them a re-gate; a queue that held appends while a proof's post-merge job runs, and released them in one batch after its bot commit, would remove the whole protocol. Smaller: an annex had to merge and render (7 min) before the skeleton citing it could be prechecked, and the product views had a gap (F-A9) that hid route 2.
- F-A9, site evidence 15:14Z: https://openproofnetwork.org/problems/erdos-68/ draws "route erdos-68@2: closes nothing (a hole is refuted, defective, abandoned, superseded or not traced)" — the page tells the steward route 2 is dead, when its h1 is the proved erdos-68--h1. Only "Set 1" is listed.
- F-A9 still at 15:24:50Z (read_at 0a08f238, after erdos-68--h5 proved): route erdos-68@2 holes [h1: None/None, h5: proved, h6: ready]; sets = 1 (route 1 only).
15:35Z A: claim 01M61APX48GK270AFHYQGZ8AR4 released. Final state: route 1 {--h1 proved, --h2 proved, --h3 open, stronger than root}; route 2 {--h1 proved, --h5 proved, --h6 open ⇔ root}.
