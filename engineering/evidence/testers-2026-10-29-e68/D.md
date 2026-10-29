# D (t1027e-d) — auditor and words, erdos-68, 2026-10-29

## Log

14:43Z started. Brief, prior README, prior C.md (yesterday's auditor) and board read. Graph cloned to scratch (main 4f771bb8ad). MCP via curl JSON-RPC helper (scratch/bin/mcp.py); token works (list_my_claims → pseudonym t1027e-d, no claims). Open submissions on erdos-68: none (queue 1171, 1172 are other lanes).
Audit method (from prior C): for each hole, fast check an `example : (have's type) ↔ (printed/Statement type) := Iff.rfl`, plus read casts by eye.
14:47Z ground truth for audits: exact fract(F_N), N=2..40, by Fraction (scratch bin/fr.py). h3's inequality fails at N=2,4,8,22 only in that range; residue form agrees with F_N mod 1 at every N (checked).
14:48Z lane 2, B's candidates (B.md 14:44Z):
- B-1 core K1 (fract(R_N) < 1 − 3/N, R_N = residue sum up to n*): reverse h3 ⇒ K1 tried. x_N = fract(R_N + L_N), 0 < L_N < 1/N, so h3 gives fract(R_N) = x_N − L_N < 1 − 2/N when x_N ≥ L_N, and fract(R_N) = x_N − L_N + 1 > 1 − 1/N when x_N < L_N. Neither reaches < 1 − 3/N, so the reverse does not follow; conversely K1 ⇒ h3 because fract(R)+L < 1−3/N+1/N. Verdict: formally stronger by a 1/N slack only; same question on the same residues. Agree with B: not narrower. (Side check of T2: (n!)²/N! > N needs n − N/2 ≳ N ln2/(2 ln N), so n* = N/2 + N/log N is enough, plausible.)
- B-2 core K2: K2 contains the disjunct "x_N < 1 − 2/N", so h3 ⇒ K2 trivially and D gives K2 ⇒ h3. Equivalent. Agree.
- B-3 core K3 (h3 along N = p−1): h3 does not give K3 (h3's N may avoid p−1). Strictly stronger, but only by discarding N; the Wilson fact controls the denominator, not the size. Not progress. Agree.
14:49Z lane 2, A's candidates (A.md 14:50Z):
- A1 core (∃δ>0 ∀M ∃N≥M, δ ≤ fract(N!S) ≤ 1−δ). Forward core ⇒ h3 checked: for N ≥ 2/δ, c_N ≤ 2/N < δ ≤ fract(N!S), so no wrap and fract(F_N) = fract(N!S) − c_N < 1 − δ < 1 − 2/N. Note the LOWER bound δ ≤ fract is what prevents the wrap; the assembly must use it. Reverse h3 ⇒ core tried: fails. If ‖N!S‖ → 0 but N!S sits above an integer by d_N ≥ c_N infinitely often, then f_N = d_N − c_N is small, so h3 holds while the core fails. Nothing rules that pattern out. Verdict: strictly stronger, no reverse known. Honest.
- Plain form for the steward (checked): writing S = Σ a_n/n! in factorial base (0 ≤ a_n ≤ n−1), fract(N!S) = a_{N+1}/(N+1) + O(1/N), so A1's core ⇔ "min(a_n, n − a_n) ≥ δ'n for infinitely many n": the factorial digits of S are not eventually near 0 or near n relative to n. (h3's failure is the much more rigid "digits eventually within O(1) of 0 or n", prior C.)
- A2 (∃δ, f_N ≤ 1−δ i.o.): A1 core ⇒ A2 ⇒ h3; reverse h3 ⇒ A2 fails (h3 allows f_N = 1 − 3/N). Strictly stronger than h3, strictly weaker than A1, as far as known. Ordering: root ⇐ h3 ⇐ A2 ⇐ A1.
- A3: agree equivalent to h3 (window form of the same recurrence).
14:50Z lane 2, B-4 (C': ∀M ∃N≥M, fract(F_N) ≤ 1 − 1/N, closing the root with h5 + h1):
- Closing checked: at such N ≥ 4, 0 < x_N + c_N < (1 − 1/N) + 1/N = 1 (h5's strict c_N < 1/N), so N!S ∉ ℤ. Correct.
- C' ⇒ h3 (the reverse of "weaker") tested with a separating example, exact arithmetic (scratch bin/cprime.py): X = Σ_{m ∈ {6,10,14,…}} (m−1)/m! (factorial digit m−1, i.e. "−1", at every 4th place), with S's own c_N, x_N(X) := fract(N!X − c_N). For N = 4..49: N(1 − x_N) < 1 at every N except N+1 ∈ P, where it is 1.80..1.98. So ¬h3(X) at every N ≥ 4 while C'(X) holds infinitely often. No argument that uses only the shape N!X = F_N + c_N can give C' ⇒ h3. B's claim stands: C' strictly weaker than h3.
- root ⇒ C' tested: fails as far as known. If T = S − (e−2) were rational, x_N = 1 − O(1/(N+1)!) eventually, so C' fails while S is still irrational. Root ⇒ C' would therefore prove T ∉ ℚ, which nobody knows. B's claim stands: C' strictly stronger than the root.
- Verdict: honest. Order root ⇐ C' ⇐ h3 ⇐ A2 ⇐ A1. C' is the weakest core of this "x_N below the window" kind, and it is NOT h3 restated: it needs h5's sharp tail.
14:52Z AUDIT #1176 (A's partial on --h3, precheck 01M6422N00JZK93P757RF6FJ17 pass, graph 4f771bb8ad): D/audit-1176-precheck.lean, fast check okay:true, lint [] — (1) ht have ↔ printed closed_type Iff.rfl; (2) printed ht ↔ erdos-68--h2's Statement Iff.rfl (receipt: expected_new false, restates erdos-68--h2: the lemma path, check graph.json after merge, prior finding #2 was node:null for a same-parent restatement); (3) hcore have ↔ printed closed_type Iff.rfl; (4) hcore's tsum = the root's S by rfl. Read by eye: δ : ℝ, both bounds on Int.fract of (↑N! : ℝ) * S, M ≤ N, no ℕ-division, no missing guard. CLEAN. Expected new node erdos-68--h3--h2 (numbered after its position; note no --h3--h1 node will exist since ht becomes a lemma).
14:53Z AUDIT B's partial on --h6 (precheck 01M64264AGV6E9DBS1TYP8Q3KE pass, no witness yet): D/audit-h6route3-precheck.lean, fast check okay:true, lint []: (1) have h1 ↔ printed closed_type Iff.rfl; (2) printed h1 → --h6 (first disjunct), term proof; (3) --h3's type → h1, proved (so the hole is no stronger than --h3, matching "root ⇐ C' ⇐ h3"). By eye: ≤ (not <), 1/N real division, Icc 2 N. CLEAN. Expected node erdos-68--h6--h1.
14:53Z drafted glosses D/gloss-h3--h2.md, D/gloss-h6--h1.md (to file after the nodes exist, in a quiet window, unless the auto-filed claim-line gloss is already exact).
14:54Z checked A/literature-h3--h2.json: correct (digit equivalence derivation above, 14:49Z entry). A files it.
14:59Z #1177 (B, partial on --h6, precheck 01M642FVV8BRTRMGW8NR90HKMA pass): hole closed_type byte-identical to the one audited at 14:53Z; witness checked. Audit stands, CLEAN.
15:01Z lane 2, B's level-2 draft on future --h6--h1 (hd: ∀M ∃N≥M, 2/(N+1) ≤ fract(N!S) < 1 − 1/(N+1); B/skel-h6h1-digits-draft.lean):
- hd ⇒ C' (with --h5): d = fract(N!S) ≥ 2/(N+1) > c_N (N ≥ 2), so no wrap, x_N = d − c_N < 1 − 2/(N+1) ≤ 1 − 1/N. Correct.
- C' ⇒ hd? No: exact test (scratch bin/hd.py) on the same separating X as 14:50Z (digits 0 and −1): C'(X) holds i.o. and hd(X) holds at NO N in 2..44 ((N+1)·fract(N!X) ∈ {≈0, ≈1, N+1−0}). So hd is strictly stronger than C' by an explicit example, as B says.
- hd vs --h3: incomparable by shape. h3 allows tiny x_N (d ≈ c_N < 2/(N+1)), and hd allows x_N ∈ [1−2/N, 1−2/(N+1)) (digit N−1 with a large tail). So hd is not a restatement of --h3 or of A1. A1 ⇒ hd for N ≥ 2/δ.
- Order now: A1 ⇒ {h3, hd}; h3 ⇒ C'; hd ⇒ C'; C' ⇒ root. hd is A1's statement with the margin δ shrunk to 2/(N+1), so it is a weaker (better) target than A1 for the root. Verdict: honest, not clutter.
- Numerics, for the record only: hd holds for S itself at 37 of N = 2..44.
- Risk to watch: B's ht = --h5 verbatim. --h5 is the root's child (route 2), i.e. an uncle of the new node, not a sibling. The lemma rule says "under another branch", so it should be a lemma. Prior finding #2 (node:null) was a same-parent restatement. Check the receipt's expected_new/restates.
15:06Z AUDIT ON MAIN #1176 (gate: #1176 pass = 6d5fe2a50d, products rendered_from 904bc9d9b7): nodes/erdos-68--h3--h2/Statement.lean type is byte-identical to the precheck's closed_type, which was Iff.rfl to the have (14:52Z), so CLEAN. --h3 META: deps [erdos-68--h3--h2], lemmas [{hole: ht, node: erdos-68--h2}]. graph.json decomposition: ht → erdos-68--h2, hcore → erdos-68--h3--h2. The lemma path worked (prior finding #2's node:null was a same-parent restatement, not this case). Context.lean of --h3 carries erdos_68__h2 for the assembly. Auto-filed statement gloss (from A's claim line) read: display exact, "In words" line correct (∃δ, ≥δ i.o. ⇔ ‖N!S‖ ↛ 0). I will NOT file my draft over it, it would be clutter. Witness.lean (True) has no gloss yet.
Note: --h3--h2 META is meta/v2 origin compiler-derived while --h3 is meta/v6 skeleton-hole (prior C saw the same on --h5: a partial that cites no annex). Not a defect as far as I can tell; one line.
15:07Z timing: #1176 merged 14:55:31Z, 'gate: #1176 pass' 15:05:28Z (10 min); #1177 merged 15:02:59Z. Still present, prior #1.
15:08Z lane 2, one barrier common to every open core on the record (useful for postmortems and the steward):
- Take X = e − 2 + 1/3, an irrational with X − e ∈ ℚ, and S's own c_N (scratch bin/eshift.py, exact, N = 4..39). Then N!X is never an integer, so the root's conclusion holds for X. But h3, C' (--h6--h1), hd and hence A1 (--h3--h2) all FAIL at every N, because x_N(X) = 1 − O(1/((N+1)(N+1)!)).
- Consequence: each of --h3, --h3--h2, --h6--h1 and B's hd implies, besides S ∉ ℚ, that T = S − (e − 2) = Σ_{n≥2} 1/(n!(n!−1)) is irrational. No reverse implication from the root can exist without proving T ∉ ℚ. Only --h6 (≡ root) escapes this. This is why no route on the record is equivalent to the root except route 2. It also confirms "strictly narrower than the root" for all four cores at once.
15:10Z reviewed C/explainer-A1-assembly-draft.md and C/explainer-B4-assembly-draft.md against the partials' Lean: both say exactly what the assembly does (wrap argument via the lower bound; Or.inl). No errors.
15:14Z drafted D/words-witness.json (witness gloss for --h3--h2, True). Waiting on 'gate: #1177 pass' (merged 15:02:59Z, not landed at 15:14Z) before any append.
15:18Z AUDIT ON MAIN #1177 ('gate: #1177 pass' eb1181d759 15:17:29Z, 14.5 min after merge): nodes/erdos-68--h6--h1/Statement.lean type byte-identical to precheck 01M642FV's closed_type (≡ have, Iff.rfl at 14:53Z), so CLEAN. graph.json: --h6 deps [--h6--h1], hole h1 → erdos-68--h6--h1; Witness.lean ∃ M, True. Labels: --h6 "avoids the window (1-1/N, 1-1/(N+1))" (right for --h6), --h6--h1 "fract(F_N) ≤ 1 − 1/N infinitely often" (right).
Both of today's gate-written holes audited twice (precheck + main): ZERO mismatches.
15:20Z SUBMITTED #1201 witness gloss erdos-68--h3--h2 (id 01M643XBX049MAWD9X0T6PKAVE), #1202 witness gloss erdos-68--h6--h1 (id 01M643Y4A85T8E9AD3SD5JPPF6); dry runs ok, no warnings. Crossed with C's 15:19Z claim of the same files; posted.
15:23Z AUDIT B's hd partial on --h6--h1 (precheck 01M643VHA0A2A0614H4S65A08D pass): D/audit-h6h1-hd-precheck.lean, fast check okay:true, lint []: ht have ↔ printed (Iff.rfl); printed ht ↔ erdos-68--h5's Statement (Iff.rfl; receipt restates erdos-68--h5, expected_new false: the uncle-lemma case); hd have ↔ printed (Iff.rfl). By eye: 2/(N+1) ≤ fract (≤), fract < 1 − 1/(N+1) (strict), real casts (↑N + 1), S's tsum as the root's. The claim's "Equivalently" line checked by hand: (N+1)·{N!S} = a_{N+1} + {(N+1)!S}, so ⌊(N+1){N!S}⌋ ∈ [2, N−1] ⇔ 2 ≤ (N+1){N!S} < N ⇔ hd. Exact. CLEAN. Expected node erdos-68--h6--h1--h2.
15:24Z drafted D/literature-h6--h1.json; #1202 already merged (my witness gloss file is on main under --h6--h1/gloss/).
15:24Z SUBMITTED #1208 literature record (open) erdos-68--h6--h1 (id 01M6446A18X5G10SDVSKYMPDQZ), text D/literature-h6--h1.json. Filed before #1207 merges, per B's 15:23Z note.
15:25Z site check (curl, time_connect 0.012 s): node pages for erdos-68, --h3, --h6 now say 'Split into / Reduced to these holes by …' on open nodes: prior F-C1 ('Proved from these holes' on an open root) FIXED. Root doc comment 'Listed, not claimable, at Stage 0.' still shown: prior F-C2 still present. --h3 page lists ht → erdos-68--h2 (proved) and hcore → --h3--h2: the lemma is visible.
15:25Z drafted D/literature-h6--h1--h2.json (to file after #1207's bot commit).
15:25Z lane 2: hd ⇏ h3 confirmed exactly (scratch bin/hd_not_h3.py). X with factorial digit m−2 at m ∈ {8,13,…} and m at m+1 (others 0), S's own c_N: h3's inequality holds at NO N in 5..59, while hd holds at N = 7, 12, …, 57. Together with 15:01Z (h3 ⇏ hd), hd and --h3 are incomparable by shape, as the literature draft says.
15:29Z drafted D/postmortem-h6--h1.yaml (reverse implications fail by the e-shift and digit examples). To file near the end, in a quiet window.
15:30Z #1201 #1202 #1208 merged. list_words_needed on erdos-68: count 0 (read_at 04db3af994). #1207 waiting_on gate (position 1 of 1).
15:33Z #1207 (B's hd partial on --h6--h1) MERGED ~15:32Z; quiet window until its bot commit. Findings F-D1..F-D5 written.
15:43Z AUDIT ON MAIN #1207 (merged 15:31:57Z, 'gate: #1207 pass' d36b055d66 15:42:39Z, 10.7 min): nodes/erdos-68--h6--h1--h2/Statement.lean type byte-identical to precheck 01M643VH's closed_type for hd (Iff.rfl to the have at 15:23Z), so CLEAN. --h6--h1 META lemmas [{ht → erdos-68--h5}] (the uncle-lemma path worked), graph.json holes ht → --h5, hd → --h6--h1--h2. The auto gloss (B's claim plus the digit line) is accurate. Witness ∃ M, True. All three of today's gate-written holes audited at precheck and on main: ZERO mismatches.
15:44Z SUBMITTED #1211 witness gloss erdos-68--h6--h1--h2 (id 01M645AT08AW4BGFBHXPVYH7RD, text D/words-witness-2.json); #1212 literature (open) erdos-68--h6--h1--h2 (id 01M645AYWG1S091YBHCGEE10MN, D/literature-h6--h1--h2.json); #1213 postmortem erdos-68--h6--h1 (id 01M645B3RREDMGDH8DFXEDYJRP, D/postmortem-h6--h1.yaml, accepted as postmortem/v1). All appends, after 'gate: #1207 pass'. (A first batch attempt failed locally: zsh did not word-split my loop variable, so nothing was sent.)
15:45Z reviewed the five postmortems merged today on erdos-68 (C's on --h3 and --h3--h2, A's on --h3, B's on --h6 and --h6--h1--h2) against the checks in this log. The mathematics is correct. I checked B's '--h6--h1 implies a_m ≥ 2 i.o.' by cases: digits eventually in {0,1} give d_N ≤ u_N < c_N, so x_N > 1 − 1/N. One wording nit, not an error: A ('which the root does not') and B ('the root alone does not') say the root does not imply T ∉ ℚ. What is shown is that no known argument gets T ∉ ℚ from the root, since root ⇒ T ∉ ℚ holds vacuously if T is in fact irrational. Records are immutable; posted for the lead.
15:47Z reviewed C/explainer-hd-assembly.md (#1214) against B/partial-h6h1-digits.lean: correct, step for step (no wrap since c < 1/N ≤ 2/(N+1) ≤ {N!S}; c > 1/(N+1) ≥ 1/N − 1/(N+1) closes).
15:49Z checked C's F-C6 and A2's F-A2-1. Render lag, not loss. At 15:49:38Z list_words_needed (read_at 1f93fefdfe) no longer lists --h6--h1--h2/Witness.lean: glosses.json now carries my chain b77d65a141 with lean_hash dde5f1dd = the file's sha256. Only the #1207 partial (explainer #1214, merged 15:48:57Z, not yet rendered) is listed. graph.json publishes both of my literature records as literature_proposed (status open, contributor t1027e-d). literature: null is by design until a steward confirms. The page shows 'proposed by t1027e-d, awaiting a steward or curator'.
15:50Z copied the exact-arithmetic check scripts to D/scripts/ (fr, cprime, hd, eshift, hd_not_h3). Scanned the evidence folder for my token: absent. D/gloss-h3--h2.md and D/gloss-h6--h1.md were drafts I did not file: the auto-filed glosses were already exact.
15:59Z 16:00 cutoff. No open pull requests of mine, none open on erdos-68, no new hole to audit. Stopping new work. Final report below.

## Findings

### F-D1 (feature request) — no record of how the open cores relate to each other
- What happened: by 15:30Z the target had four open cores (--h3, --h3--h2, --h6--h1 and, from #1207, --h6--h1--h2). Between them the run proved one strength order and two separations, by exact separating examples: A1 (--h3--h2) ⇒ {--h3, hd}, --h3 ⇒ C' (--h6--h1), hd ⇒ C', C' ⇒ root, and --h3 and hd are incomparable by shape (D.md 14:49Z, 14:50Z, 15:01Z, 15:26Z). Also, every core except --h6 fails for X = e − 2 + 1/3, so each one also proves T = S − (e−2) irrational (15:08Z). None of this has a home on the record except prose: literature summaries (#1208), postmortems and the board. The statement graph draws only parent→hole edges, so the steward sees four "open" pills and cannot tell which implies which. This is the same gap as prior README "For the steward" (B/h6_of_root.lean had no place to go).
- Expected: an implication record between two existing nodes (X ⇒ Y, with a Lean proof the gate checks, or "Y ⇏ X by shape" with an exhibit), drawn as an edge. The guide's lemma rule (D-12 v3.38) covers only a hole that restates a node.
- Cost: none to the proofs. For the steward, the page cannot show the main result of lane 2.
- Repro: open https://openproofnetwork.org/problems/erdos-68/ and try to read off that --h3--h2 implies --h6--h1.

### F-D2 (feature request, still present: prior C's §4) — auditing a gate-written hole is hand work
- What happened: each audit took one hand-written file of Iff.rfl examples, built from the partial's `have` text and the precheck's `closed_type`, and one `check_lean` call. That made six audit files today (D/audit-*.lean), plus a byte comparison of each Statement.lean on main against the receipt. All were clean.
- Expected: `get_precheck` (or `get_node` for a skeleton-hole) could carry, per hole, the author's `have` text beside `closed_type` and a kernel check that the two are definitionally equal. The gate already holds both.
- Cost: about 3 min per hole. Repro: any partial precheck.

### F-D3 (bug/docs, still present: prior README #1) — post-merge bot commits 10–14.5 min after a partial's merge
- #1176 merged 14:55:31Z, `gate: #1176 pass` 15:05:28Z. #1177 merged 15:02:59Z, `gate: #1177 pass` 15:17:29Z (A saw its run 40897594017 sit in "Commit the attestation and the products" from 15:11:34Z while main moved five times on erdos-849). #1207 merged 15:31:57Z, `gate: #1207 pass` 15:42:39Z (10.7 min). Meanwhile 16 erdos-849 appends merged, and they were batched into one bot commit at 15:48:44Z. Each quiet window froze words on erdos-68 for 10–15 min. One line: still present.

### F-D4 (docs, still present: prior F-C2) — root doc comment says "Listed, not claimable, at Stage 0."
- The node page for erdos-68 (curl 15:25Z) still renders it from the immutable Statement.lean, beside a page that accepts work.

### F-D5 (docs/site, still present: prior F-A8) — hole ids skip when a hole becomes a lemma
- A hole that restates an existing node still uses up its index. So the target now has erdos-68--h3--h2 with no --h3--h1, and B's #1207 makes --h6--h1--h2 with no --h6--h1--h1. A steward reading the ids looks for a sibling that does not exist. Receipts say so (`expected_node_id`), so it is predictable, but nothing on the page explains the gap.

### F-D6 (bug, minor; same as A2's F-A2-1 and C's F-C6) — list_words_needed's read_at hides product lag
- 15:48Z, `list_words_needed {target_id: erdos-68}`: listed erdos-68--h6--h1--h2/Witness.lean as `no-gloss`, though my #1211 had merged at 15:45:20Z. At 15:49:38Z (read_at 1f93fefdfe) the row was gone and glosses.json carried the chain. `read_at` names main's head, but the rows come from a glosses.json rendered from an earlier commit. A writer cannot tell "nobody wrote this" from "written, not yet rendered", and could open a duplicate. Expected: the listing gives the products' `rendered_from` too, and marks a subject whose record merged after it. Cost: 3 min to confirm nothing was lost.

### Fixed since yesterday (checked)
- Prior F-C1: open nodes now read "Split into / Reduced to these holes by …", not "Proved from these holes by …" (node pages erdos-68, --h3, --h6, curl 15:25Z).
- Prior #2 (a restating hole recorded as `node: null`) did not recur. A restatement of a node under another branch (--h2 for --h3; --h5, an uncle, for --h6--h1) went the lemma path: META `lemmas`, and graph.json hole → that node.

### Not a defect
- 15:19Z: C and I both took the two witness glosses within a minute. I filed first (#1201, #1202) and posted at once. Board discipline, not the network.

## Final report

### 1. What I landed (all through the MCP, all merged)
- **#1201** witness gloss, `erdos-68--h3--h2` (merged 15:20:30Z).
- **#1202** witness gloss, `erdos-68--h6--h1` (merged 15:21:40Z).
- **#1208** literature record (open), `erdos-68--h6--h1` (merged 15:25:27Z). It gives the position root ⇐ it ⇐ --h3 and the two separating checks.
- **#1211** witness gloss, `erdos-68--h6--h1--h2` (merged 15:45:20Z).
- **#1212** literature record (open), `erdos-68--h6--h1--h2` (merged 15:45:24Z). It gives the exact factorial-digit form, its position, and the T-barrier.
- **#1213** postmortem on `erdos-68--h6--h1` (merged 15:46:22Z). Route: get this node from the root or from --h6 by the tail shape. It records the two examples showing that this does not work.
- **Audits, lane 1.** Every hole of the three partials merged today was audited twice: the precheck's `closed_type` against the author's `have` by Iff.rfl on the fast check, then Statement.lean on main against that `closed_type` byte for byte.
  - #1176: `--h3--h2`, plus `ht` as the lemma `--h2`.
  - #1177: `--h6--h1`.
  - #1207: `--h6--h1--h2`, plus `ht` as the lemma `--h5`.
  - Files: D/audit-1176-precheck.lean, D/audit-h6route3-precheck.lean, D/audit-h6h1-hd-precheck.lean.
  - **Zero mismatches.** Both lemma restatements went the lemma path (META `lemmas`, graph.json hole → node).
- **Lane 2.** Every "narrower" claim on the board was tested by trying the reverse implication. Separating examples, all in exact rational arithmetic (scripts copied to D/scripts/):
  - B-1, B-2, A3 are equivalent to --h3 or the same question with slack. B-3 and A2 are stronger with no mechanism.
  - A1 (--h3--h2) is honest.
  - C' (--h6--h1) is honest, with an explicit X that has ¬h3 at every N and C' infinitely often.
  - hd (--h6--h1--h2) is honest: C' ⇏ hd by an explicit X, and hd and --h3 are incomparable in both directions by explicit X's.
  - Order: A1 ⇒ {h3, hd}; h3 ⇒ C'; hd ⇒ C'; C' ⇒ root.
  - Common barrier: for X = e − 2 + 1/3 every open core fails while the root's conclusion holds. So each core also proves T = S − (e−2) irrational, and only --h6 escapes. All four agents now cite this.
- **Reviews.**
  - C's three explainers (#1194, #1206, #1214) and A's literature draft were checked against the Lean: correct.
  - All five postmortems filed today were checked: maths correct. One wording nit, in A's #1205 and B's #1209: "the root does not [imply T ∉ ℚ]" should be "is not known to".

### 2. Unfinished business for the lead
- Nothing of mine is open. The --h6--h1 partial's explainer (#1214, C) had merged but was not yet rendered at 15:49Z.
- Words that a steward or curator must act on:
  - My two literature proposals (#1208, #1212) await confirmation.
  - The wording nit in the immutable #1205 and #1209 can only be corrected in a later record.
- For the steward: the strength order between the four open cores (above, and in #1208/#1212's summaries) has no structured home on the record (F-D1).

### 3. Findings, most important first
1. **F-D1** (feature request). There is no record of implications between existing nodes. The run's main lane-2 result (the strength order, separations by exhibit, the T-barrier) lives only in prose, and the graph shows four unrelated "open" pills.
2. **F-D3** (still present, prior #1). Bot commits came 10, 14.5 and 10.7 min after the partials' merges. Each quiet window froze words on the target for that long.
3. **F-D6** (minor bug; also A2 F-A2-1, C F-C6). `list_words_needed`'s `read_at` names main's head while its rows come from older products, so a just-merged gloss reads as `no-gloss`.
4. **F-D2** (feature request, prior C §4). A per-hole "have vs closed_type, defeq checked" field would make the auditor lane one call per hole.
5. **F-D5** (still present, prior F-A8). Hole ids skip when a hole becomes a lemma (--h3--h2 with no --h3--h1, --h6--h1--h2 with no --h6--h1--h1).
6. **F-D4** (still present, prior F-C2). The root's doc comment says "Listed, not claimable".
- **Fixed since yesterday:** prior F-C1 ("Proved from these holes" on an open node). Prior #2 (`node: null`) did not recur: both of today's restatements became lemmas.

### 4. What would have made me twice as productive
The audit itself took about three minutes per hole. Most of my 90 minutes went on waiting:
- 10–15 minutes per partial for the bot commit before anything could be filed on the new node;
- polling main for the hole's Statement.lean.

Three things would have halved it:
- a precheck receipt that carried a kernel-checked "this closed_type is definitionally the author's have";
- a notification (or a `wait_for` MCP call) when a node's Statement.lean lands on main;
- a way to file the words for a hole against the precheck's predicted node id, held until the node exists.

On the mathematics side, the separating-example checks (one short exact-arithmetic script each) were the most useful thing I did. An implication record that could carry such an exhibit would put that work on the record, and not only on the board.
