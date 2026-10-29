# C — log

14:45Z started. Brief, prior README, board read. Graph cloned (scratch). MCP via curl-like JSON-RPC helper (stateless). Plan: C/lemmas-mod.lean = fract(F_N) through (N!/n!) mod (n!−1), then near-N bounds; fast check on erdos-68--h3.

14:46Z C/lemmas-mod.lean fast-check okay (log 01M641Z4P8TS6PENMNZBHRWM1J): C_term_split (N!/(n!−1) = int + r_n/(n!−1), r_n=(N!/n!)%(n!−1)), C_fract_mod (fract F_N = fract Σ r_n/(n!−1)), C_mod_eq (r_n = N! % (n!−1)), C_fract_mod'. = B-1's T1+T3 in one step.
14:46Z C/lemmas-top.lean fast-check okay (log 01M64208TG9ERKG8RKKWJJW899): C_term_halves, C_top_sum: Σ_{n=K}^N N!/(n!(n!−1)) ≤ 2·N!/(K!(K!−1)) for K≥2 (geometric, ratio ≤1/2). Tool for B-1's T2 (tail L_N small above a cut).

14:47Z C/lemmas-y.lean okay (log 01M6423AFGW8JJVYZKJ4AF3XVE): C_y_rec, y_{N+1}=fract((N+1)·y_N) for y_N=fract(N!·S), any real S. For A1's core if decomposed.

14:48Z read A1 (A/partial-h3-A1.lean) and B-4 (B/partial-h6-route3.lean in progress): neither has an elementary hole (A1: ht = h2's statement → lemma; B-4: closes from h1+h5). Posted offer on board. Not building B-1 myself: D and B judged it ≡ h3 (slack only), so it would be a restatement, against the brief.

14:53Z second audit: C/audit-precheck-A1-B4.lean okay (log 01M642DZ9R6MB481DQCTT1Y0W4). A precheck 01M6422N00JZK93P757RF6FJ17 pass: ht restates erdos-68--h2 (expected_new false, but expected_witness printed "∃ (N : ℕ), (2 : ℕ) ≤ N" for a restated hole — odd, noted), hcore → erdos-68--h3--h2. B precheck 01M64264AGV6E9DBS1TYP8Q3KE pass, artifact-reduction, h1 → erdos-68--h6--h1. Both Iff.rfl to the haves.

15:00Z drafted (not filed; appends wait for quiet windows): C/explainer-A1-assembly-draft.md (A1 assembly, #1176; step ids to fill from the outline), C/explainer-B4-assembly-draft.md (#1177), C/postmortem-h3.yaml (truncation route, exhausted). Idea abandoned: a level-2 split of A1's core or of C' — every candidate I tried (digit form, y_(N+1)=fract((N+1)y_N), split S=e−2+T) is equivalent to its parent, so none is honest.

15:15Z explainer of #1176's assembly finalised: C/explainer-A1-assembly.md, anchors from outline e801a643… (steps ht hcore | s3 s4 s5 hN2 hKN hNpos hKr h_x3b4N | s8 hxF key close). submit_gloss dry_run ok, hash b321545e…, no warnings. Holding it for the quiet window: #1177 merged 15:02:59Z (merge commit 53320f40), no 'gate: #1177 pass' at 15:15Z while erdos-849's #1171/#1173/#1174 bot commits landed (prior #1 still present).

15:18Z 'gate: #1177 pass' (eb1181d7, 15:17:29Z, 14.5 min after merge). SUBMITTED #1194: explainer of #1176's assembly (C/explainer-A1-assembly.md, hash b321545e…, id 01M643TQXGQB4H8J03P9DZ9G34). #1177's outline not on main yet; B-4 explainer waits for it.

15:19Z drafted + dry-ran witness glosses for --h3--h2 and --h6--h1 (C/gloss-witness-*.md, ok), then saw D had claimed them at 15:18Z (posted while I read the list): dropped, not filed. Lesson: re-read the board immediately before claiming.

15:20Z SUBMITTED #1203 postmortem/v2 on erdos-68--h3 (C/postmortem-h3.yaml) and #1204 postmortem/v2 on erdos-68--h3--h2 (C/postmortem-h3h2.yaml). postmortem/v2 now has model_and_tooling (prior finding #8 part fixed).

15:22Z #1194 MERGED (15:20:21Z). #1177's outline landed 15:20:32Z (a24d40e5…, steps h1 | s2 close). SUBMITTED #1206 explainer of #1177's assembly (C/explainer-B4-assembly.md, id 01M6443E7R09X5MSHV4VKG2SCA).

15:24Z list_sufficient_sets erdos-68: four routes (erdos-68@1, @2, erdos-68--h3@1, erdos-68--h6@1), sets {h1,h2,h3--h2} and {h1,h5,h6--h1}, each remaining 1. Prior finding #2 (route @2 dropped, hole node null) no longer present.

15:29Z get_my_submissions: #1194, #1203, #1204, #1206 all MERGED. Tried once more (on paper) a level-2 for hd/A1 through G_N = Σ r_n/(n!−1) and the recurrence s_{N+1} = (N+1)s_N + ε_{N+1} − j_N: it closes up into 'T ≡ Σ j_m/m! mod ℚ with bounded j', the same digit statement. Abandoned.

15:47Z 'gate: #1207 pass' 15:42:39Z; outline 9923d981… on main 15:45:44Z. submit_gloss dry run at 15:46Z refused explainer-step-unknown ('…has no outline to name steps of'); retried, ok 15:47:13Z. SUBMITTED #1214 explainer of #1207's assembly (C/explainer-hd-assembly.md, id 01M645G3XRHEQFDYBHZSCXKCM5).

15:56Z #1214 MERGED. list_words_needed at 15:55:11Z (read_at fee5eda1): count 0 — F-C6 cleared on its own; the list and the node bundle lagged main by 7–10 minutes after D's records merged (15:45Z). No new submissions from me; done.

## Findings

### F-C1 (docs/minor bug): a restated hole gets an `expected_witness`
- Kind: bug (cosmetic) or docs.
- What: get_precheck 01M6422N00JZK93P757RF6FJ17 (A's #1176 bundle), 14:52Z. holes[0] `ht` has `restates: erdos-68--h2`, `expected_new: false`, and yet `expected_witness: "∃ (N : ℕ), (2 : ℕ) ≤ N"`. A hole that becomes a lemma creates no node, so it has no witness slot to fill.
- Expected: `expected_witness: null` for a restated hole, or a line in the guide saying the field is informational only there.
- Cost: 2 minutes (checked that A's bundle did not need a witness for it; it passed without one).
- Reproduce: get_precheck on that job id, read result.holes[0].

### F-C2 (feature request, prior #2 family): the new node's id skips a number when the first hole is a lemma
- What: #1176's holes are ht (→ lemma erdos-68--h2) and hcore; the new node is `erdos-68--h3--h2`, and no `--h3--h1` exists. A reader of the site sees `--h2` and looks for `--h1`.
- Expected: the id names position among holes (that is consistent), but the page should say "hole 1 is the lemma erdos-68--h2". Low priority.
- Cost: none.

### F-C3 (bug, cosmetic): explainer dry-run preview prints the anchor syntax in the heading
- What: submit_gloss dry_run, subject {kind: proof, node_id: erdos-68--h3, proof: e801a643…}, 15:14Z. `preview_html` renders the heading as `<h5>What the assembly proves, and from what {steps: ht hcore}</h5>`: the `{steps: …}` anchor is shown as text.
- Expected: the preview shows what the site will show; the guide says the anchor names the steps, it is not part of the title.
- Cost: 1 minute (wondered whether the anchor had parsed; `sections[].resolved` says it had).
- Reproduce: any explainer dry run with an anchored heading.

### F-C4 (prior #1, still present): merge → bot commit takes 10–15 minutes for a partial
- What (graph main, read with git log): #1176 merged 14:55:31Z, `gate: #1176 pass` 15:05:28Z (10 min); #1177 merged 15:02:59Z, `gate: #1177 pass` 15:17:29Z (14.5 min; A saw run 40897594017 sit in "Commit the attestation and the products" from 15:11:34Z while main moved five times, mostly erdos-849 bot commits). #1177's outline came 3 minutes after its bot commit (15:20:32Z).
- Expected: a partial whose precheck passed is attested within a couple of minutes; one target's push is not starved by another target's commits.
- Cost to me: the B-4 explainer waited 18 minutes for the outline; the quiet window held every append on erdos-68 for 22 minutes.
- Reproduce: merge a partial while another target's lane is busy; time `git log origin/main`.

### F-C5 (prior #7, still present): explainer refused `explainer-step-unknown` for ~1.5 min after the outline is on main
- What: submit_gloss dry_run {kind: proof, node_id: erdos-68--h6--h1, proof: 9923d981…}, 15:46Z: "step ht, hd, … is named on attempts/20261029T151822Z-t1028-b-partial.lean, which has no outline to name steps of (F20-R4)". The outline commit f0723246 was on main at 15:45:44Z. Same request ok at 15:47:13Z.
- Expected: the service sees the outline once it is on main, or the refusal says "outline not yet read, retry" rather than "has no outline".
- Cost: 1.5 minutes and a retry loop.
- Reproduce: submit an anchored explainer within a minute of the outline commit.

### F-C6 (bug, lag): list_words_needed and get_node lag main by 7–10 minutes for merged words
- What: list_words_needed {target_id: erdos-68} at 15:48:04Z, `read_at` 2008b6d4 (main's head): `witness erdos-68--h6--h1--h2 no-gloss`, `in_review: null`. On that main, targets/erdos-68/nodes/erdos-68--h6--h1--h2/gloss/b77d65a1….md is D's witness gloss (commit 137abcc6, merged in #1211/#1212 by 15:45:23Z) with `lean_hash: dde5f1dd…`, which is the sha256 of that node's Witness.lean. get_node on the same node (include: []) at 15:49Z also shows `literature: null` and `literature_proposed: null` though D's literature record (commit 4d0020a8) is on main.
- Expected: a gloss whose lean_hash matches the file, on the commit the list was read at, takes the row off the list (the guide: the list is "every Lean file … that no current version describes").
- Cost: 3 minutes checking that D's gloss had landed, so that I did not file a duplicate.
- Reproduce: list_words_needed {target_id: erdos-68}; compare with the gloss/ directory of erdos-68--h6--h1--h2 on main. Cleared by 15:55:11Z (count 0, read_at fee5eda1): a lag of 7–10 minutes after the merge, while `read_at` already named a commit that held the records — so `read_at` is not the commit the answer reflects.

## Final report

1. **Landed** (all appends, all five merged):
   - #1194 explainer of #1176's assembly (erdos-68--h3, route A1), merged.
   - #1206 explainer of #1177's assembly (erdos-68--h6, route 3), merged.
   - #1214 explainer of #1207's assembly (erdos-68--h6--h1, hd), merged.
   - #1203 postmortem/v2 on erdos-68--h3 (the truncation and remainder route, with the T-irrationality barrier argued), merged.
   - #1204 postmortem/v2 on erdos-68--h3--h2 (three level-2 splits, all equivalent), merged.
   - No proof. None of the skeletons (A1, B-4, hd) had an elementary hole: each non-open hole restated a proved node (h2, h5) and became a lemma.
   - Also fast-checked Lean in C/, unused by any node:
     - lemmas-mod.lean: fract F_N = fract Σ (N! mod (n!−1))/(n!−1).
     - lemmas-top.lean: Σ_{n=K}^N N!/(n!(n!−1)) ≤ 2·N!/(K!(K!−1)).
     - lemmas-y.lean: y_{N+1} = fract((N+1)·y_N).
   - A second audit of both prechecks' printed holes (C/audit-precheck-A1-B4.lean): clean.
2. **Unfinished business**:
   - Nothing of mine is in flight.
   - The C/ lemmas are ready if anyone ever splits fract(F_N). For example, B-1's truncation would use lemmas-mod plus lemmas-top. The board judged B-1 equivalent to --h3, so it was not built.
3. **Findings**, most important first:
   - F-C4: prior #1 is still present. A partial takes 10–15 min from merge to bot commit, plus about 3 min to its outline.
   - F-C6: list_words_needed and get_node lagged merged words by 7–10 minutes, while their `read_at` named a commit that already held them. It cleared by itself.
   - F-C5: prior #7 is still present. An explainer is refused `explainer-step-unknown` for about 1.5 min after the outline commit.
   - F-C1: a restated hole carries an expected_witness.
   - F-C3: the dry-run preview shows the `{steps: …}` anchor in the heading.
   - F-C2: the node id skips a number when hole 1 is a lemma.
   - Fixed since yesterday: prior #2 (route @2 dropped), and the postmortem model field (v2 has model_and_tooling).
4. **Twice as productive**: The prover lane only pays when the skeleton has elementary holes. On this problem every honest sub-skeleton was one open core plus lemmas, so my Lean went unused and I spent the run on audits and words. Two things would have doubled my output. First, reassigning the prover lane at the 15:05Z pick, once it was clear the pick had no elementary hole (for example, to the words from the start). Second, a merge-to-outline time of about 2 minutes instead of 13–18: each of my three explainers waited on an outline, and each quiet window held every append on the target for 10–15 minutes.
