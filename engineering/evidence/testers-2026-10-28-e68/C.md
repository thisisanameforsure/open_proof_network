# C (t1028-c) — auditor and second angle, erdos-68, 2026-10-28

## Log

13:04Z started. Brief, board, prior README read. Graph cloned (main 935c6d81af). MCP via curl JSON-RPC (stateless, no session id). Tutorial precheck job 01M619R8N8AVJJB0Y1X3NWHNVJ queued for minting.
13:05Z lead's guess checked: L_N·tail_N → ∞ (gcd(N!−1,(N−1)!−1) | N−1; numerics N=4..15 give log10 0.1 → 58). Posted on board. Any 'L_N small' hole is false.
13:08Z token minted (pseudonym t1028-c, identity 01M619YB00AP2SS7SSYKBY95TY), kept in scratch only.

### Skeleton candidates (C)

**C1 — factorial base (my pick).** K=N+2. K!·S = A_N + B_N with A_N = Σ_{m=2}^{K} K!/(m!−1) (a finite rational sum) and B_N = K!·Σ_{m>K} 1/(m!−1). If S = r rational, r.den | K! for K ≥ den, so K!·S ∈ ℤ, hence fract(A_N) = 1 − B_N.
Holes: h_summ (summability, elementary), h_tail (0 < B_N < 1/2 for N ≥ 1, elementary: B_N ≤ Σ K!/(m!−1) ~ 1/(K+1)), h_open (∀ M ∃ N ≥ M, fract(A_N) ≤ 1/2 — OPEN core).
Why narrower: h_open is about finite rational sums only (no tail, no real analysis); it is strictly STRONGER than the root (implies it, not equivalent), and heuristically true (fract(A_N) looks equidistributed: N=2..39 values computed in python, 18 of 38 ≤ 1/2, counted). Assembly fast-checked (C/skel-factorial-base.lean, okay apart from the three sorries).
Weaker alternative open hole (closer to root, still tail-free): fract(A_N) ≤ 1 − 1/(N+2) infinitely often, needing the sharper tail bound B_N < 1/(N+2).

**C2 — lead's lcm route: DEAD.** L_N·tail_N → ∞ provably (gcd(K!−1,(K−1)!−1) | K−1). Not a skeleton.

**C3 — double series ∑_k ∑_n (n!)^{-k}.** S = (e−2) + Σ_{k≥2} Σ_{n≥2} (n!)^{-k}; irrationality of e does not propagate through a sum, and the per-k common denominator (N!)^k differs by k, so no uniform q_N exists; I see no narrower core from it. Not proposed.
13:12Z C1 upgraded: h_summ (C/h_summ.lean) and h_tail with 3 ≤ N (C/h_tail.lean, bound B_N ≤ 2/(N+2) via K!(K+1)^(i+1) ≤ (K+i+1)! and a geometric series) both PROVED, fast check okay. Folded into the partial as private helpers: C/partial-factorial-base.lean = Statement.lean byte for byte + helpers + assembly, ONE hole h_open. check_lean verify on erdos-68: only sorry-present / sorry-reported (expected for a partial), no helper lint.
13:13Z read A's draft skel1-partial-v1: faithful; backed A's candidate over C1 (A's open core weaker, hence more plausible).
13:14Z drafted C/approach-lcm.json (approach record, refuted-route, for the dead lcm route) and C/postmortem-opencore-draft.md (second angle on the open core: recurrence x_{N+1}=fract((N+1)x_N+1/((N+1)!-1)); failure ⇔ factorial digits eventually within 2 of 0 or N; small n vanish once n!-1 ≤ N). Both are appends: will file in a quiet window.
13:20Z pre-merge audit of A's holes (precheck 01M61A9S6RN8XYDXE2XGTA8326): all three Iff.rfl to the haves, C/audit-h123-precheck.lean okay. Posted.
13:46Z posted division of words with A; holding appends for gate: #1134 pass.
13:54Z audit on main clean (C/audit-h123-main.lean). Claim lines checked: faithful.
13:56Z SUBMITTED #1136 postmortem erdos-68--h3 (id 01M61CR6Z84J7MEWBWRY7YXVJ5, C/postmortem-h3.yaml) and #1137 approach record lcm route (id 01M61CRZCGN6MBSGFE75PGS1Y9, C/approach-lcm.json).
13:58Z drafted four witness glosses (C/words-witness.json) for the words window; health connect measured 67 s once then 0.16 s (laptop path, not service).

## Findings

### F-C1 (bug, site) — "Proved from these holes by" on an open statement (still present, prior A F6)
- 14:00Z, https://openproofnetwork.org/problems/erdos-68/ , selected statement erdos-68 (status open), section "Split into" reads "Proved from these holes by 20261028T132200Z-t1028-a-partial.lean (merged in 1936413ac0a1, attestation 001134)", with all three holes open. Expected: "Split into these holes by …" (nothing is proved). Cost: none to me; misleads the steward reader. Repro: open the page, read "How it is being proved".

### F-C2 (docs) — the root's immutable doc comment contradicts the page
- erdos-68/Statement.lean says "Listed, not claimable, at Stage 0." The page and frontier say the statement accepts work (ready, claimable). A reader of the Lean is told the opposite of the record. Expected: the claimability sentence lives in products, not in an immutable statement (or the site notes that the comment is historical). Cost: a minute of doubt before claiming. Repro: `get_node erdos-68` → files Statement.lean.

### Not a defect
- 13:59Z `curl -w '%{time_connect}'` on /health: 67.2 s connect once, then 0.16 s: the laptop's path (brief's known stall). The ~25 s pause on submit_approach_record at 13:56Z is this.
14:00Z #1136 and #1137 MERGED (498b2b0cb1, e735766418), with A's #1138. Queue now B's #1139, #1140 only. I hold all appends until both 'gate: #N pass'.
14:09Z asked board for unfinished work.

### F-C3 (feature request, review) — seven identical review questions that do not say what they ask about
- 14:12Z `list_review_questions {target_id: erdos-68}`: count 7, q-1..q-7 all read "A variant of the statement agrees with it on every small case checked. Is there a case on which the conjecture and this variant should differ?", each with only `raised_by: {kind: mutant, ref: e-…}`. The page header says "7 questions waiting". The steward who must answer gets no variant text in the question; one more lookup per question by an opaque ref. Expected: the variant's statement (or a diff from the candidate) inlined in the question. Cost to me: none (not my lane); likely cost to the steward. Repro: the call above.

### F-C4 (bug/perf, post-merge) — a proof's attestation landed 20 min after its merge, after a later proof's, with the quiet window kept
- #1139 (B's proof of erdos-68--h1) merged 14:03:11Z (2e86f0997f). No appends merged after it (the last appends #1136–#1138 merged 13:57–13:58Z). Its post-merge run 40702171240 (gate workflow, push): "Re-derive the verdict on the merge commit" 14:03:54Z→14:16:00Z (12 min 6 s), "Join what this merge made provable (F28-T9)" 14:16:00Z→14:20:52Z (4 min 52 s), "Commit the attestation and the products" 14:22:02Z→14:23:35Z (1 min 33 s). `gate: #1139 pass` = 0d681d336b at 14:23:31Z.
- Meanwhile #1140 (merged 14:07:52Z, later) landed `gate: #1140 pass` first, at 14:21:41Z, and the appends' bot commits `gate: #1137 pass` 14:11:33Z and `gate: #1138 pass` 14:13:50Z landed after both proofs had merged. So bot commits land out of merge order, and append renders from *before* a proof's merge still land inside its "quiet window".
- From 14:03Z to 14:23Z, graph.json on main (rendered_from 663112af1f, then 9f1f77d0d8) published erdos-68--h1 as `ready` while its Proof.lean was in the tree, and erdos-68--h2 (merged later) as `proved` (checked 14:21Z, `git show origin/main:targets/erdos-68/graph.json`).
- Expected: an attestation within a few minutes of its merge, and in merge order; or the state "merged, attestation pending" shown on the node. The brief's quiet-window rule (no appends between a merge and its bot commit) does not prevent this: the 17 min were spent in re-derive + join, not in a rejected push.
- Cost to me: 20 min of the shared lane frozen for appends (my words batch waited on it). Repro: merge two proofs on one target a few minutes apart and compare merge times with `gate: #N pass` times; `gh run view <post-merge run> --json jobs` gives the step times.
14:26Z SUBMITTED witness glosses #1142 erdos-68, #1144 --h1, #1145 --h2, #1146 --h3 (dry runs ok first). Text: C/words-witness.json.
14:28Z SUBMITTED #1148: statement gloss (with label) for the ROOT erdos-68 (C/gloss-root.md); it had none.

### F-C5 (bug, words) — the root statement has no gloss and list_words_needed does not list it
- 14:29Z: targets/erdos-68/glosses.json (rendered_from 9f1f77d0d8) has subject nodes/erdos-68/Statement.lean, kind statement, chains [] (no words). target.yaml has informal: null. Yet `list_words_needed {target_id: erdos-68, kind: statement}` → count 0, subjects [] (read_at f78794d2da), and the unfiltered call at 13:57Z listed only the four Witness.lean files and the partial. Expected (guide: reasons include no-gloss and root-without-informal "a root whose problem has no curated words"): the root's Statement.lean listed, no-gloss / root-without-informal. Cost: none to me (found by reading glosses.json); an entry-task agent relying on the tool would never write the root's words. Repro: the call above beside glosses.json. Filed the gloss as #1148, so after it merges the repro needs another informal:null root (A's F-A4 lists erdos-52, -172, -376, -406).
- 14:28Z F-C5 reproduced on erdos-52 and erdos-376: root Statement.lean chains 0 in glosses.json, list_words_needed kind statement count 0.
- Caveat on F-C5: target.yaml carries a `paraphrase` (shown on the page as 'Curated informal statement'); if the paraphrase is meant to count as the root's words, this is by design, but then glosses.json still says the Statement.lean has no gloss chain, and the page's statement panel has no notation for the steward. Lead to judge.
14:29Z reviewed explainers #1141 (A) and #1143 (B): correct.
14:34Z all my submissions merged: #1136 #1137 #1142 #1144 #1145 #1146 #1148 (get_my_submissions).
14:41Z audited A's route-2 draft (A/route2-sharper-window-draft.lean): faithful; numerics N=4..60 agree.
14:43Z PROVED sharp tail bound for A's route-2 h2' (C/h2prime.lean, fast check okay). Posted.
14:43Z C/h2prime-full.lean: A's route-2 h2 have proved in full, fast check okay.
14:48Z pre-merge audit of route 2 #1154 clean (C/audit-route2-precheck.lean). Proof of future erdos-68--h5 checked against printed type (C/proof-h5-printed.lean okay). Claimed --h5 on the board; will claim through the network once the node exists.
15:03Z audit h5/h6 clean; claimed --h5 (01M61GKM68AGZ7QW0AYEQ71PSF); precheck 01M61GKP4R8AJW1YMPMSEAZNV1 on C/proof-erdos-68--h5.lean. Note: --h5 META is meta/v2 with origin compiler-derived (route 2 cites no annex), --h1..h3 meta/v3 skeleton-hole.
15:11Z SUBMITTED #1162 proof erdos-68--h5 (C/proof-erdos-68--h5.lean, precheck 01M61GKP4R8AJW1YMPMSEAZNV1 pass). Verified B's h6⇔root argument independently.
15:11Z drafted explainer for #1162 (C/explainer-h5-draft.md); waits on its outline after merge.
15:15Z #1162 MERGED 15:15:23Z (c3c1f2b2eb). Timing its gate line for F-C4.
15:29Z SUBMITTED #1163 explainer of #1162 (C/explainer-h5.md). Outline for #1162 landed 15:28:11Z as its own commit 'outline: 1 for erdos-68', 4 min after 'gate: #1162 pass'; list_words_needed named the outline path at 15:25Z before the file existed on main.

### F-C6 (docs/feature, words) — explainer lint flags a Mathlib lemma used by dot notation
- 15:28Z submit_gloss dry_run for erdos-68--h5's proof: warning explainer-name-unanchored — "the section 'The identity' cites `Summable.sum_add_tsum_nat_add`, which none of the constants its steps (hsplit, he, hI, close) use contains". Step hsplit is literally `C_summable.sum_add_tsum_nat_add (N - 1)` (C/proof-erdos-68--h5.lean). Either the elaborated constant has another name (deprecated alias?) or the check misses dot-notation calls. I dropped the name to file clean. Cost: 2 min. Repro: dry-run the text in C/explainer-h5.md with the removed parenthesis restored.
- Also: list_words_needed (15:25Z) gave `outline: targets/erdos-68/outlines/dd2113….json` while that file was not yet on main (it arrived 15:28:11Z); same lag B saw for h1. The listing should say the outline is pending.
15:29Z writing witness glosses for --h5, --h6 (C/words-witness-2.json).
15:31Z SUBMITTED #1164, #1165 witness glosses. Released claim 01M61GKM68AGZ7QW0AYEQ71PSF at 15:29:37Z.
15:42Z all my PRs merged (#1163 rendered 15:38:32Z; #1164/#1165 merged 15:31Z, render pending). Queue on erdos-68 empty. No further submissions from C.

## Final report (C, t1028-c)

### 1. What I landed (all merged, all through the MCP)
- **#1162 proof** of `erdos-68--h5` (route 2's sharp tail: 1/(N+1) < c < 1/N for N ≥ 4): merged 15:15:23Z, `gate: #1162 pass` 15:24:11Z. Lean: C/proof-erdos-68--h5.lean (helpers C_fac_big, C_term_le, C_tail_sharp, C_summable).
- **#1136 postmortem** on `erdos-68--h3` (direct-estimate, exhausted, route-dead-ends): the recurrence x_{N+1} = fract((N+1)x_N + 1/((N+1)!−1)), the residue form, why nothing narrower exists.
- **#1137 approach record** on erdos-68 (refuted-route): the lead's lcm route; L_N·tail_N → ∞ because gcd(N!−1,(N−1)!−1) | N−1.
- **Words:** #1148 statement gloss + label for the root (it had none, see F-C5); witness glosses #1142 (root), #1144 (--h1, √2), #1145 (--h2), #1146 (--h3), #1164 (--h5), #1165 (--h6); #1163 explainer of the --h5 proof.
- **Audits** (lane C(1)): every gate-written hole checked twice — the precheck's closed_type and the Statement.lean on main — against the partial's `have` by `Iff.rfl` on the fast check: --h1/--h2/--h3 (C/audit-h123-precheck.lean, C/audit-h123-main.lean) and --h5/--h6 (C/audit-route2-precheck.lean, C/audit-route2-main.lean). **Zero mismatches.** Also read A's and B's explainers (#1141, #1143) line by line: no errors.
- Second angle (lane C(2)): no narrower honest sub-skeleton of the open core exists by any route I found; recorded in #1136. Independently checked B's argument that --h6 is equivalent to the root (d_{N+1} = (N+1)d_N − 1 − ε is c_N's own recurrence, so d − c grows by N+1 per step while staying < 1/N, hence 0): agreed.

### 2. Unfinished business for the lead
- Nothing of mine is open: #1164 and #1165 rendered (gate lines 15:42:51Z, 15:44:29Z).
- C/partial-factorial-base.lean (my C1, open core fract ≤ 1/2) was never submitted, by design: A's open cores are weaker and better. Do not file it.
- The root `erdos-68` is closable through route 1 once --h3 is proved (B's closing proof is prepared); --h6 ⇔ root, so route 2's open core is the problem itself in finite form.

### 3. Findings, most important first
1. **F-C4** (post-merge): #1139's attestation landed 20 min after its merge and after the later #1140's; the time went to "Re-derive the verdict" (12 min) and "Join what this merge made provable" (5 min), not to a rejected push. h1 read `ready` with Proof.lean in the tree meanwhile. The quiet-window protocol does not prevent it. (#1162 took 8 min 48 s.)
2. **F-C5** (words): root statements with `informal: null` have no gloss and `list_words_needed` does not list them (erdos-68, reproduced on erdos-52 and erdos-376). Possibly by design if the paraphrase counts; lead to judge.
3. **F-C3** (review): the seven review questions on erdos-68 are identical text with only an opaque mutant ref (cf. A's F-A4: the review's words are the licence header).
4. **F-C6** (words): the explainer lint flags `Summable.sum_add_tsum_nat_add` called by dot notation as unused by the step; outline path listed before the outline file reaches main (4 min lag).
5. **F-C1** (site, still present, prior A F6): "Proved from these holes by" shown on the open root.
6. **F-C2** (docs): the root's immutable doc comment says "Listed, not claimable" while it is claimable.
- Not defects: the laptop's 67 s connect stall (time_connect).

### 4. What would have made me twice as productive
The mathematics took minutes; the waiting took hours. A proof whose precheck has passed could carry its own hole's proof (I had --h5's proof checked against the printed closed_type 15 minutes before the node existed, and still waited for merge + bot commit + render before I could precheck it), and post-merge attestations taking 9–20 min serialise every lane. A precheck that accepts a hole named by a passing partial's precheck, and a post-merge job that does not re-derive a verdict the gate already signed, would have roughly halved my idle time. On the tooling side, a single MCP call that returns a node's Statement.lean, its parent's have text and an Iff.rfl audit would turn the auditor lane into one call per hole.
