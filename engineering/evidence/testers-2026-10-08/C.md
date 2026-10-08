# Tester C log — 2026-10-08 (literature, annexes, reader's view; entry: site first, then HTTP)

Pseudonym: t1008-c. Secrets in /private/tmp/claude-501/opn-testers-1008/C/ (never here).

## Timeline
12:56Z start
12:57Z posted literature alert re Ecklund (proved p<=n/2 only; n>=k^2 is a conjecture)
12:56Z site home 200 0.42s; /problems/erdos-1094/ 200 0.76s. Read as a mathematician: page gives the statement, Lean, provenance, "statement unchecked", a catalog score, but NOTHING on what is known (no references beyond formal-conjectures + erdosproblems link; "Approach records: none", "State of the problem: none"). Literature had to come from erdosproblems.com.
12:57Z posted literature alert (Ecklund proved only p<=n/2; n>=k^2 => p<=n/k is Ecklund's conjecture, open).
12:59Z posted correction: 2k<=n<k^2 half follows from Konyagin 1999 / Granville-Ramare 1996 (g(k) >> k^2); n>=k^2 half is the open one.
13:00Z POST /precheck tutorial (my bundle WITHOUT the statement's doc-comment header) -> 202 6.0s; done ~13:03 verdict fail step 2 proof-not-statement (expected header line 1). MY MISTAKE (the guide's script replaces only the sorry). Note: step 2 is a cheap text check yet the job queued for ~3 min before saying so.
13:00Z resubmitted with header: job 01M4DSMSJG2W47MX9NB0P2G2M4 202 5.4s; pass by 13:04 (all steps pass).
13:05Z POST /tokens -> 201 in **67.6 s** (identity 01M4DSWKJG3EMJXVHMRZ5X7FWW, pseudonym t1008-c). Token stored outside repo.
13:04Z verified the ELS88 14-exception list by my own Kummer-carry script for k<=30, n<=3000: exactly the 14 (C/scripts not in repo; script in /private/tmp). Larger run k<=200, n<=2e5 started.
13:07Z POST /annexes root -> 201 10.5s, PR #440, hash 315301b1f764..., annex/v2 with 3 steps
13:07Z POST /claims erdos-1094 ttl 1h -> 201 3.5s; receipt lists others [t1008-a] and open_submissions [#440]. Frontier overlay shows both claims.
13:07:56Z PR #440 MERGED (49 s after open; gate 22 s). Bot commit 8ab4564ed at 13:09:01. Site problem page showed the annex at 13:09:38 (first check): merge->site <= 1m42s. Service frontier annex_present=true at 13:09:38.
13:08:44Z GET /submissions.json (0.58 s): open=[] , queue.order=[] — #440 already merged, so consistent.
13:09Z GET /submissions/01M4DSZM88XPMNTTM2FT6Z0AW2 -> 200 in **37.6 s** (state merged, attestation_note no-attestation-for-mode).
13:10Z Site: my literature annex is rendered under "Outlines" on the problem page ("an outline is an informal argument, not a proof ... not followed by any merged decomposition"), title cut at ~140 chars mid-word ("...against it agai"). Node page renders full text; the annex's provenance line shows model_and_tooling truncated: "drafted with Claude Opus 5.5 as agent t1008-c; sources read via erdosproblems.com,, 2026-10-08T13:06:59Z" (stored YAML has the full string). The annex/v2 steps (h_fixed_k, h_large_n, h_small_n) are not shown on either page.
13:12Z MCP list_words_needed(target_id erdos-1094) -> 200 1.1s: lists only root Witness.lean (no-gloss); root Statement.lean NOT listed although glosses.json shows chains: [] for it (probably by design: root has curated informal words, cf. reason root-without-informal — but then the list hides that the Lean itself has no gloss).
13:13Z POST /glosses root Statement.lean -> 201 7.8s, PR #442 (hash 0963b976...).
13:14:02Z #441 (A's partial) merged; 13:14:53Z #442 (my gloss) merged. #442's gate was green by 13:12 but it waited in the erdos-1094 lane behind #441's Mathlib build (queue position 2 of 2, waiting_on null).
13:12:49Z GET /submissions.json -> 200 in **35.6 s** with 2 open (0.58 s with 0 open at 13:08).
13:15-13:20 lag of holes: service /frontier.json first listed --h1/--h2/--h3 at 13:18:28 (4m26s after merge); site problem page first showed them between 13:18:28 and 13:20:12 (~5-6 min). Graph bot commit for #441 (28f5a569c) at 13:19:41, AFTER #442's bot commit (d1833c0ed, 13:15:38) though #441 merged first.
~13:19:50 one curl "Could not resolve host: api.openproofnetwork.org" (ENV: local DNS blip, single occurrence).
13:27Z POST /annexes --h2 -> 201 5.4s PR #443; POST /annexes --h3 -> 201 **39.0 s** PR #444.
13:27Z site problem page after partial: root 'open, 1 attempt, Closable through its holes'; h1/h2/h3 shown 'open', origin compiler-derived. Hole names (h_fixed_k etc.) not visible anywhere on the site (only in the gate-written doc comment of Statement.lean, which the site doesn't render). Node page: A's partial assembly shown as "Untrusted: partial assembly (D-12 #5), author not recorded" though the file name and PR author are t1008-a.
13:27:47 POST /glosses --h1 -> 201 11.1s PR #445; 13:27:59 --h2 -> 201 27.4s PR #446; 13:28:26 --h3 -> 201 46.4s PR #447. Write latency growing with the queue.
13:28-13:29Z #443 merged 13:27:13, #444 13:28:06, #445 13:29:01, #446 13:29:04. Bot commit 2b96ac03d (13:28:55) re-rendered products at 59770965c, which contains the holes -> unblocks B (see bug on rendered_from).
13:29Z VERIFIED B's finding from the record: bot commit 28f5a569c (#441's) has frontier.json listing --h1/--h2/--h3 but rendered_from=d1833c0ed, whose tree has no hole directories (git ls-tree d1833c0ed targets/erdos-1094/nodes/ -> only erdos-1094). So prechecks at rendered_from could not see the holes until the next merge re-rendered.
13:30:27Z GET /claims/mine -> 200 **35.6 s**; DELETE /claims/<id> -> 200 0.57 s (released); repeat DELETE -> 200 **35.5 s**, idempotent same body. Frontier overlay shows my claim gone at once.
Latency pattern: many service calls answer either in ~0.5-10 s or in ~35-47 s (submissions.json 35.6, submissions/{id} 37.6, claims/mine 35.6, DELETE claim (repeat) 35.5, POST /annexes 39.0, POST /glosses 27-46, POST /tokens 67.6). Looks like a host read with a ~35 s timeout/retry inside the request path.
13:35Z MCP list_words_needed (36.0 s) now lists the root's merged partial assembly (no-explainer, with outline path) and 4 Witness.lean files.
13:35Z POST /glosses explainer dry_run -> 400 section-duplicate (my mistake: two unanchored sections). Note: the assembly's final refine/rintro/by_cases (lines 46-50) is not an outline step, so no section can anchor to it; folded it into the overview. Re-dry-run 200 ok 3.0s, sections resolved to lines. Real submit 201 5.3s PR #449.
13:34Z own scan of A's h_sieve residue form (exists prime p<=k with n%p < k%p, for 2k<=n<k^2): k<=400 -> 301 failures, max k 58, last (1579,58). Matches A's k<=300 numbers.
13:38:15Z #448 (A's partial on --h3) merged; 13:39:07Z #449 (my explainer) merged. Bot commits: cf8fd082a (#449, 13:40:22) then bc3f897b9 (#448, 13:42:30).
13:42Z REPRODUCED the rendered_from bug (2nd instance): main bc3f897b9 frontier.json lists erdos-1094--h3--h1 but rendered_from=cf8fd082a, whose tree lacks that directory. Service /frontier.json also says rendered_from cf8fd082a while listing the new hole.
13:43:28Z POST /annexes on erdos-1094--h3--h1 -> 201 3.7s PR #451 (annex creation is NOT blocked by the stale rendered_from; only precheck is, per B).
k<=1000 h_sieve scan finished (8m40s wall): same 301 failures, max k 58.
13:44:03 POST /glosses --h3--h1 -> 201 **72.8 s** PR #452

## BUGS (running; label: NETWORK / DOC / ENV / MINE)

C1 NETWORK (high, reproduced twice, found by B, verified from the record by C): a partial's post-merge bot commit writes frontier.json/products with rendered_from = its PARENT commit, whose tree does not contain the hole directories it just created. Prechecks run at rendered_from, so a fresh hole is unprecheckable (layout-missing) until some later merge on the target re-renders. Repro: `git show 28f5a569c:frontier.json` -> rendered_from d1833c0ed, lists erdos-1094--h1..h3; `git ls-tree d1833c0ed targets/erdos-1094/nodes/` -> only erdos-1094. Again: bc3f897b9 (#448) rendered_from cf8fd082a, lists --h3--h1, absent from cf8fd082a.

C2 NETWORK (medium): node page credits a merged partial assembly as "author not recorded" (https://openproofnetwork.org/nodes/erdos-1094/erdos-1094/, Attempts: "Untrusted: partial assembly (D-12 #5), author not recorded; no postmortem record names this file") while the file is attempts/20261008T130306Z-t1008-a-partial.lean and the Contributors ledger credits t1008-a for the same file. Reproduced on reload.

C3 NETWORK (medium, reproduced many times): bimodal latency. Many routes answer in ~0.5-10 s or ~35-73 s: POST /tokens 67.6 s; GET /submissions/{id} 37.6 s; GET /submissions.json 35.6 s (5.8 s later); GET /claims/mine 35.6 s; repeat DELETE /claims/{id} 35.5 s; POST /annexes 39.0 s; POST /glosses 27-73 s; MCP get_node 42.0 s; MCP list_words_needed 36.0 s. Looks like a ~35 s host read/timeout inside the request.

C4 NETWORK (low): site annex provenance line truncates model_and_tooling: node page shows "drafted with Claude Opus 5.5 as agent t1008-c; sources read via erdosproblems.com,, 2026-10-08T13:06:59Z" — stored YAML has the full string "... erdosproblems.com, MathOverflow API, publisher abstracts; exception box checked by a Python Kummer-carry script". Cut at a comma, double comma left.

C5 NETWORK (low): problem page "Outlines" panel titles an annex by its first ~140 characters, cut mid-word ("...with a reading of the formal statement agai by t1008-c").

C6 NETWORK/DESIGN (low): annex/v2 `steps` (ids + summaries) are not shown anywhere on the site (neither problem page nor node page) when no skeleton followed the annex.

C7 NETWORK (low): /submissions.json queue.waiting_on is stale in a misleading way: #451 shown waiting_on "gate" (read 13:43:56) when its gate had completed SUCCESS; the doc does say it is "what the service last read", so borderline DOC.

C8 NETWORK (low): MCP list_words_needed(target erdos-1094) omits the root's Statement.lean although glosses.json shows chains: [] for it (the root has curated informal words, so probably by design; but the gloss route accepted a root gloss and the site shows it, so the list hides real work).

C9 DOC/UX (low): "Erdős problem 1094: ... finitely many exceptions.." double full stop on the problem page provenance line.

M1 MINE: first tutorial precheck omitted the statement's doc-comment header -> step 2 proof-not-statement (the guide's script keeps it; I hand-wrote the bundle). Cost: one 3-min job. A cheap pre-queue check for step 2 would have answered in a second.
M2 MINE: explainer dry-run section-duplicate (two unanchored sections).
E1 ENV: one transient DNS failure for api.openproofnetwork.org at ~13:19:50.

## FEATURES (running)

F1 A literature / prior-art record kind. My survey had to be filed as an annex, and the site files it under "Outlines: an informal argument, not a proof ... not followed by any merged decomposition". A mathematician arriving at the page looks for "what is known" and finds "Approach records: none", "State of the problem: none" (the latter is steward/curator-signed only). Prior art (theorems, exceptions, computations, citations) wants its own labelled section on the problem page, writable by anyone.
F2 Show a node's *known status in the literature* (e.g. "follows from Konyagin 1999, unformalised" vs "open") — on the site all of --h1, --h2, --h3 read identically "open", so a reader cannot tell the open core (h2) from a deep-but-known hole (h3) from an elementary one (h1) without opening annexes.
F3 Show hole names (h_fixed_k, h_large_n, h_small_n) beside the node ids on the site; they carry the meaning and are only in a doc comment.
F4 Anchor for an assembly's closing tactics: the root partial's final refine/rintro/by_cases block (lines 46-50) is no outline step, so an explainer cannot anchor a section to it.
F5 A cheap, synchronous step-2 (paths/header) pre-check on POST /precheck before queuing a multi-minute job.

## Timeline (cont.)
13:45:13Z bot commit ef2094e5d "outline: 1 for erdos-1094" (outline d4c3a94c for A's --h3 partial), ~7 min after #448 merged.
13:47:53Z POST /glosses explainer on --h3 partial (dry run 200 2.7 s first) -> 201 27.1 s PR #453.
13:46-13:48Z #450 (B's proof of --h1) green since ~13:44 and "waiting_on merge", not merged; main idle since 13:45:13.
13:49Z found my --h1/--h2/--h3 glosses stored without their paragraph break (site renders "...at most K.In other words"). Cause: MINE — I fed the JSON through zsh `echo`, which interprets \n. (Service still accepted the mangled body; root gloss, sent from a file, is fine.) Dry-run supersede versions 200 (2.4-4.3 s), then real: #454 (--h1, 8.5 s), #455 (--h2, 25.0 s), #456 (--h3, 5.7 s).
13:52Z MERGE STALL observed (read-only, gh run logs): no merge between #449 (13:39:07) and >=13:52. The one merge job that ran (run 37786220979, workflow_dispatch, 13:40:29-13:50:46) logged repeatedly "#450 is green; the host is still computing whether it conflicts: holding its lane" (GitHub mergeable=null), then at 13:50:43 "updated the branch of #450" (it had gone BEHIND when the outline bot commit ef2094e5d landed at 13:45:13) -> a fresh Lean gate run on #450 from 13:50:49, lane held again ("up to date and its gate is running: holding its lane"). Meanwhile ~14 other merge runs were created and cancelled with 0 jobs (concurrency pending-replacement). My green appends #451 (green 13:44:04), #452, #453 (13:48:53), #454 (13:50:18) all wait behind #450 in the erdos-1094 lane.

## BUGS (additions)
C10 MINE (fixed by supersede #454-#456): hole glosses lost paragraph breaks because I piped JSON through zsh `echo`. Side observation (NETWORK, low): POST /glosses accepted a JSON body whose strings contained raw control newlines (invalid JSON) without complaint and silently produced different text.
C11 NETWORK (high for throughput, observed once over ~13 min, read from run logs): merge-lane head-of-line blocking. With #450 (a proof, Lean gate) at the head of the erdos-1094 lane, the actor held the lane ~7 min on GitHub's mergeable=null ("host is still computing whether it conflicts") and then, #450 having gone BEHIND, updated it and held the lane for its whole fresh Lean gate. Green appends (#451 annex, #452 gloss, #453 explainer, #454-#456 glosses; gates 20-35 s) could not merge for 10+ minutes. Repro: gh run view 37786220979 --log (decision lines at 13:50:42).
C12 NETWORK (medium): the post-merge "outline" bot commit (ef2094e5d, 13:45:13, ~7 min after #448 merged) moves main by itself, which made B's already-green proof #450 BEHIND and forced a full rebuild. Every product/outline commit to main re-invalidates every green Lean PR under the strict up-to-date rule.
C13 DESIGN (reported by A and B, reasoning checked by C, not exercised): the circular-decomposition rule ("exhibit: <hole> → <ancestor>") is satisfiable for EVERY one-hole partial/reduction, because the assembly itself proves hole → parent. So anyone can knock any reduction's hole off the frontier, and B withheld a valid one-hole partial on --h2 for this reason. Not filed (would harm A's --h3--h1).
13:54:18Z #450 (B's proof of --h1) merged after the re-run gate. 13:55:25-13:55:45Z my six appends #451-#456 merged one every 4 s, ~1 min after #450 (so they waited 11.5 min (#451) behind it).
13:59:09Z bot commit 5201afc17 for #450; service /frontier.json dropped --h1 at 13:59:46; site problem page "erdos-1094--h1: proved" first seen 14:00:18. Merge -> site ~6 min. Outline commit daa1f1641 at 14:01:57 (7.6 min after merge).
14:07:06Z explainer on B's --h1 proof: dry run 200 2.9 s, submit 201 5.3 s, PR #458.
(13:57-14:06 lost ~10 min to a badly written wait loop of my own.)
14:07:52Z POST /annexes root (state of the decomposition) -> 201 5.2s PR #459; spotted an error in my own text ("equivalent" should be "implies"); 14:08:06 DELETE /submissions/01M4DXF3MGZK701Q806TEZP6C5 -> 200, withdrawn, PR closed 14:08:09. Re-filed corrected: 201 4.4s PR #460.
14:07:36Z GET /submissions/mine -> 200 2.5 s: open [#458], recent 14 merged.
14:10Z C4 root cause found (re-verified on 2 more annexes): the site renders only the FIRST physical line of a folded YAML scalar in the annex front matter, then ", <date>". Stored file (--h3--h1 annex): "model_and_tooling: Claude Opus 5.5 (claude-opus-5-5) as agent t1008-c; numerics by\n  a Python residue scan"; site: "drafted with Claude Opus 5.5 (claude-opus-5-5) as agent t1008-c; numerics by, 2026-10-08T13:43:29Z". MCP get_node returns the full string (7.8 s), so only the site's front-matter reader is wrong. Any model_and_tooling longer than ~65 chars is truncated on the site.
14:08:04Z #458 merged; 14:09:02Z #460 merged; both on the site at 14:10:29 (merge -> site 1.5-2.4 min for appends).
14:11Z final reader view of /problems/erdos-1094/: 5 statements; h1 proved; h2, h3, h3--h1, root open; root "Closable through its holes"; glosses and second versions shown with diffs; my four annexes listed as "Outlines ... not followed by any merged decomposition". Stopped starting new work.

## FEATURES (additions)
F6 A merge lane should let a green append (annex/gloss/explainer, 20-35 s gate) pass a Lean PR whose gate is running or whose mergeability GitHub is still computing; today they queue behind it (C11).
F7 Post-merge product/outline commits should not make green Lean PRs BEHIND (batch them into the merge's own bot commit, or exempt bot-only commits from the up-to-date rule) (C12).
F8 Literature status as a first-class, citable field on a node ("open problem", "known theorem, unformalised: <refs>", "elementary"), editable by anyone through a PR like an annex, shown next to the status pill (F2 restated as a record).
F9 A route to say "this hole is stronger than its parent" (the residue form --h3--h1 vs --h3): a reader of the graph cannot see that a reduction strengthened the target.
F10 POST /glosses and POST /annexes should refuse a JSON body with raw control characters in strings (C10) rather than store a silently different text.

## Handoff
All my PRs are merged or withdrawn; nothing of mine is open; my one claim (root, 13:07) was released 13:30.
- #440 annex root (prior art + fidelity reading; annex/v2 with steps h_fixed_k/h_large_n/h_small_n) — MERGED 13:07:56
- #442 gloss root Statement.lean — MERGED 13:14:53
- #443 annex --h2 (open core: smooth-part equivalence, every exception is good, heuristic) — MERGED 13:27:13
- #444 annex --h3 (Granville–Ramaré/Konyagin route, Lucas digits) — MERGED 13:28:06
- #445/#446/#447 glosses --h1/--h2/--h3 (v1, paragraph break lost, my zsh echo) — MERGED 13:29
- #449 explainer of A's root partial assembly — MERGED 13:39:07
- #451 annex --h3--h1 (h_sieve: Kummer last digit, literature UNVERIFIED, scan k<=1000 K=58) — MERGED 13:55:25
- #452 gloss --h3--h1 — MERGED 13:55:29
- #453 explainer of A's --h3 partial — MERGED 13:55:33
- #454/#455/#456 gloss v2 (supersedes) --h1/--h2/--h3 — MERGED 13:55:37-45
- #458 explainer of B's --h1 proof — MERGED 14:08:04
- #459 annex root (state of decomposition) — WITHDRAWN by me 14:08:10 (wording error "equivalent")
- #460 annex root (state of decomposition, corrected) — MERGED 14:09:02
Ready but unsent: nothing. Open questions for a human: (1) whether Granville–Ramaré or Konyagin prove the last-digit residue form of --h3--h1 over 2k <= n < k^2 (needs the papers); (2) C13 circularity rule vs one-hole reductions (design); (3) C1 rendered_from after a partial merge.
Notes/drafts: engineering/evidence/testers-2026-10-08/C/ (annex and explainer texts as filed). Scripts (exception box, smooth-part check, residue scan) kept outside the repo in /private/tmp/claude-501/opn-testers-1008/C/scripts/.
