# C — log (agent C, pseudonym t1026-c)

20:20Z start. Cloned graph (HEAD 70fa0c7fb, 2026-10-25T17:58Z). Reading AGENTS.md and the erdos-257 record.

20:23Z Tutorial precheck job 01M5WY2AJGDTS1JMFWBSJFZDDP queued (POST /precheck answered 202 in 16.3 s). Record read: root is a 15-lemma case split + h18; --h2 <-> --h2--h1 equivalence (one direction in #910 assembly, converse only in an annex as Lean); dead routes on --h2: Liouville denominators (t1022-b), computational denominator classes (t1022-f). Chosen lemma: Lambert identity for arbitrary A (0 not in A): sum_{a in A} 1/(2^a-1) = sum_{m>=1} #{a in A: a | m} / 2^m. Rationale: the record holds it only for A = N (series_eq in variant-2f5236aa, 573-line proof); it is the first line of every published method (annex 0836778d section 1) and of the carry formulation of the greedy core (annex 0f67147d section 2). Posted on the board.
20:29Z Tutorial precheck passed; token minted (identity t1026-c, in the scratch dir only). Hazards on the draft statement: two div-zero findings, "1 / (2 ^ ↑n - 1)" and "↑{a | a ∈ A ∧ 0 < m ∧ a ∣ m}.ncard / 2 ^ m" (log 01M5WY8CX8AG8302V52P69449P); the statement compiles. Mathlib at the pin has tsum_pow_div_one_sub_eq_tsum_sigma (A = N only, via sigma), HasSum.tsum_fiberwise and Summable.tsum_prod: the plan is a double series over (n, j) of the indicator of A minus 0 times (1/2)^(n(j+1)), swapped to fibres over m = n(j+1). Writing C/lambert.lean.
20:30Z C/lambert.lean passes the fast check (okay true, no lint, log 01M5WYFY40R4Y7X6JBJCRPJ1QF; first run had one error, a `ring` after field_simp had closed the goal, log 01M5WYFGEGYQ5PBMZTTCH4EAC0). Next: propose it as a speculative crux for erdos-257--h18, then precheck and submit the proof once it merges.
20:32Z Proposed the crux: node spec-137537c8, graph PR #959, proposal id 01M5WYJ5D81B304TAEGZVBNTEK (POST /proposals/speculative 201 in 12.2 s; hazards_preflight acknowledged, witness_preflight matched; witness is ⟨∅, trivial⟩ for the expected ∃ A : Set ℕ, True). Open submissions on erdos-257 before the write: 0.

## Findings

(Entries are appended as they are hit; the ranked list is in the final report.)

### F1 — docs/site: the `--h2` node page's "Read the partial proof (Lean)" opens with ~400 lines of private helper lemmas before the decomposition
- Kind: site / docs.
- What happened: on https://openproofnetwork.org/nodes/erdos-257/erdos-257--h2/ (read 20:41Z), "How it is being proved → Read the partial proof (Lean)" prints `20261022T145422Z-t1022-o-partial.lean` verbatim, which begins with the whole Erdős-1948 proof of variant-2f5236aa as `private` helpers (dd, Tail, Zint, summable_dd_shift, tail_upper, …). The one `have h_walk : … := sorry` that *is* the route, and the assembly, come after all of it. A reader looking for "what does this route split the statement into" scrolls through a 1948 irrationality proof first.
- What I expected: the holes first (they are already rendered above as "h_walk → erdos-257--h2--h1"), then the assembly, with the helper block folded or summarised ("n private helper declarations, m lines"). The guide's own words say a partial is the statement "with only the body" yours; helpers are allowed since F00-T11 but the page predates them.
- Cost: ~3 minutes of reading; no work lost.
- Reproduce: open the page above, expand "Read the partial proof (Lean)".

### F2 — docs/site: the open core's own node (`--h2--h1`) shows "attempts 0" while every postmortem about the walk sits on its parent
- Kind: feature request (site/products).
- What happened: https://openproofnetwork.org/nodes/erdos-257/erdos-257--h2--h1/ (20:41Z): Facts row "attempts 0 attempts", "What is known" empty. The three postmortems that say which routes on the walk are dead (Liouville denominators by t1022-b, computational denominator classes by t1022-f, the "expected false" note by fable-1020-e257-c) are filed on `erdos-257--h2`, whose annex 2cd06801 proves the two nodes equivalent. A prover sent to the frontier entry `--h2--h1` (the finest cut) sees a node nobody has tried.
- What I expected: either the parent's postmortems shown (or counted) on a one-hole child whose parent has no other hole, or at least a line "its parent erdos-257--h2 carries 5 attempts" in the Facts row, since `frontier.json`'s `refuted_route_classes` for `--h2--h1` reads empty too (checked in the clone: no `attempts/` yaml under `--h2--h1`).
- Cost: none for me (the brief pointed me at the parent); an outside prover would re-try the Liouville route.
- Reproduce: compare the two pages' Facts rows.
20:33Z Reader findings F1, F2 logged. Proposal #959 gate in_progress at 20:41Z (queue position 1 of 1 on erdos-257).
20:35Z Graph PR #959 (crux spec-137537c8) MERGED, gate success, products pending. Proof assembled as C/spec-137537c8-Proof.lean (header from the service's proposed_statement, helpers before the doc comment). Precheck of the proof sent.
20:36Z Precheck of the proof answered 409 products-pending (message: three to six minutes after the merge); retry loop running in the background. Words plan posted on the board: explainer for the --h2 partial, gloss for spec-137537c8. Note for B (not my lane): variant-5274cf38 reads proved (direct Proof.lean) while its hole variant-5274cf38--h1 is ready on the frontier.
20:39Z Explainer for the --h2 partial filed: graph PR #961, submission 01M5WYYD0GEBC5ZK929Y43ZC82, hash 91bfa60ec510 (dry run ok, no warnings; text in C/erdos-257--h2-partial-explainer.md). Next Lean: the zero-block (digit-side) criterion as a second crux resting on spec-137537c8.
20:44Z Precheck job 01M5WZ4W1GSP45RPTP6CC15QX2 accepted at 20:41:36Z (products rendered ~5 min after the merge). Drafted a "zero-block criterion" (C/zero-block.lean, compiles, fast-check log 01M5WZ6SJ8JREXKMBZXR8E5QFF) and then found its hypothesis is vacuous: for any nonempty A some multiple of min A lies in (j, j+min A], so every tail is at least 2^-(min A); not proposed. Replacing it by the integrality lemma every digit-method proof carries privately (tail_eq_Zint in variant-2f5236aa, R_int in variant-c91009b9): S(A) = p/q implies q*T_j = p*2^j - q*sum_{m<=j} f_A(m) 2^(j-m), an integer.
20:46Z Precheck 01M5WZ4W1GSP45RPTP6CC15QX2 PASS (steps 1,2,4,5,6,7,8 at 20:44:57Z). Proof of spec-137537c8 submitted: graph PR #968, submission 01M5WZCP1GR9BTV4CSC8J40DAR. Second crux proposed: spec-23b0fff0 (tail integrality, deps [spec-137537c8], for erdos-257--h18), graph PR #969, proposal 01M5WZD8K83ZMYHWDQRAF3D01Y; hazards acknowledged (3 div-zero, nat-sub j-m, off-by-one-range Finset.range (j+1)), witness matched (C/tail-integral.lean compiles: log 01M5WZC6DGKXC411Y349FHAB11; witness log 01M5WZC8C0S5TNYVH4FEMZMV2R).
20:47Z Gloss of spec-137537c8 filed: graph PR #970, submission 01M5WZE2Z0ETC9CCWPAMVM6WAY, hash 51e4c77f7177. C/spec-23b0fff0-Proof.lean assembled (95 lines); a background loop retries its precheck until the crux has merged and its dependency is proved (expected refusals: node-pending, products-pending, node-blocked).

### F3 — site: the problem page shows raw TeX in the problem's one-line subtitle
- Kind: bug (site).
- What happened: https://openproofnetwork.org/problems/erdos-257/ at 20:48Z, directly under the rendered curated statement, the subtitle line reads literally "Erdős problem 257: Let $A\subseteq\mathbb{N}$ be an infinite set. Imported from formal-conjectures (Apache-2.0) · erdosproblems.com/257" — dollar signs and backslashes visible (screenshot C/problem-page-top.png). The same string is the target's title, so the Problems list probably shows it the same way.
- What I expected: the title rendered as math, or the TeX stripped from the one-line title (the curated statement two lines above renders the same formula correctly).
- Cost: none; a reader's first impression.
- Reproduce: open the page; read the line under the big statement.
20:48Z Explainer #961 for the --h2 partial MERGED (gate_report ok, no warnings). Proof #968 and crux #969 gates in progress; gloss #970 green, waiting on branch-update. Reader finding F3 (raw TeX in the subtitle) logged.

### F4 — docs: a proposed crux is drawn as a bare id, and the only way to name it (`label` on `POST /glosses`) is not in the guide
- Kind: docs (and a small feature request on the proposal routes).
- What happened: after #959 merged, the problem page's "Speculative statements" column (20:48Z) listed my node as `spec-137537c8` beside neighbours drawn by names ("gap lemma: each term exceeds …"). The guide's `submit_gloss`/`POST /glosses` section lists `subject`, `text`, `licence`, `supersedes`, `drafted_with` and `dry_run`/`amends`; nothing says a statement gloss may carry `label`, which `schemas/gloss/v3.json` describes ("optional label, the statement's short name … a node's label is its current statement gloss's") and which the route accepts: amending my gloss PR #970 with `"label": "Lambert identity: the sum over A as a binary series"` answered 200 `amended: true` (new hash d7bc6e2a99a6, 20:51Z). `POST /proposals/speculative` and `/variant` take no label at all, while a partial's holes are labelled at birth (`-- label:` lines).
- What I expected: the guide's gloss section to document `label` (one sentence), and the proposal routes to take an optional `label` that becomes the first statement gloss's label, as a partial's holes do, so a new crux is never drawn as a hash.
- Cost: ~10 minutes (a dry run could not tell me, because my own open PR answers `duplicate-submission` before any field check: a dry run of a second version on a subject one is writing is refused as a duplicate even with `amends` absent, so the schema file was the only source).
- Reproduce: propose any crux; read the drawing; `POST /glosses` with `label` works, undocumented.
20:50Z F3 screenshot saved as C/problem-page-top.png; F4 logged; gloss #970 amended with a label (hash d7bc6e2a99a6, head 3d2c648d).
20:52Z Graph PR #968 MERGED: spec-137537c8 (Lambert identity for arbitrary A) is proved on the record. #969 gate running, #970 waiting on merge.
20:55Z Graph PR #969 MERGED (crux spec-23b0fff0, tail integrality); products pending, precheck loop waiting. Third lemma drafted: C/divisible-block.lean (a block of k coefficients divisible by 2^k makes q*T_{y+k} a multiple of 2^k); first attempts failed on congr depth and an Int-division cast.

### F5 — bug (api): `deps` naming a node that has merged but is not yet rendered is refused `dep-unknown`, not `products-pending`
- Kind: bug (consistency with the guide).
- What happened: 20:55Z, two minutes after #969 (crux spec-23b0fff0) merged, `POST /check` with `mode: witness`, a `statement` and `deps: ["spec-23b0fff0"]` answered `{"error":"dep-unknown","message":"spec-23b0fff0 is not a node of target erdos-257"}` (log 01M5WZZX90S712YN9YS8P58SX5). The same minute `POST /precheck` on that node answered `409 products-pending … merged as pull request #969; … Retry shortly`, which is what the guide promises ("those calls answer 409 node-pending … and then 409 products-pending …, never the 404 node-unknown a mistyped id gets").
- What I expected: `deps` validation on `/check` (and presumably on the proposal routes) to give the same `node-pending`/`products-pending` answer with a `Retry-After`, since "is not a node" is false and sends the caller to check for a typo.
- Cost: 2 minutes.
- Reproduce: merge a proposal; within the render window send a check with `deps` naming it.
20:56Z Third lemma C/divisible-block.lean compiles (log 01M5WZZ7SGHWWXVW0TWB4R25WG); hazards: 3 div-zero + off-by-one-range "1 ≤ i" (log 01M5WZZW9R5W8PVQHQSFR9HMVR); witness ⟨∅,0,1,0,0,…⟩ matches (log 01M5X00MQ0MT79TJDKPB6RBRCK). Proposal waits for spec-23b0fff0 to render (F5).
20:59Z Third crux proposed: spec-689ac1ac (divisible block ⇒ q*T_{y+k} is a multiple of 2^k; deps [spec-23b0fff0]; for erdos-257--h18), graph PR #975, proposal 01M5X03RAGBV2GDF7NQ3S6D6A7 (hazards acknowledged, witness matched). C/spec-689ac1ac-Proof.lean assembled; precheck loop 3 waiting in the background. Gloss for spec-23b0fff0 filed (see next line). Products note: at 20:57Z the frontier listed spec-137537c8 as speculative/needs proof with its proof merged (#968 attestation-pending): the post-merge job of a proof takes longer than the render of the next merge.
20:59Z Gloss for spec-23b0fff0 filed: graph PR #977, submission 01M5X04ES85W1J4P9XA5NSGAYZ, hash 673332d6c86f (with label).
21:00Z #968 attested (attestations/000968.json); glosses #970 (spec-137537c8, labelled) and #977 (spec-23b0fff0) MERGED. Precheck of spec-23b0fff0 proof running (job 01M5X023K0CT1EYPGDTWN5X4Y7, accepted 20:57:35Z). #975 gate running. Annex for erdos-257--h18 written (C/erdos-257--h18-annex.md): the digit method as the three nodes plus what a new class must supply; filed next.
21:01Z Annex on erdos-257--h18 filed: graph PR #978, id 01M5X07Z30D9APF0D2NZNNG3RV, hash 3e8b2d11dbda.
21:01Z Precheck 01M5X023K0CT1EYPGDTWN5X4Y7 of the spec-23b0fff0 proof PASS (21:01:19Z); proof submitted (see next line). Postmortem for --h2--h1 drafted in C/postmortem-h2h1.yaml, to file near the end.
21:02Z Proof of spec-23b0fff0 submitted: graph PR #980, submission 01M5X0A1G05APVHP8T37HS8M92.
21:08Z Correction: reading variant-c91009b9's proof showed Erdős 1968 does not use a zero block but a *weighted* divisibility 2^k | sum_i f(y+i) 2^(k-i) completed by r extra elements dividing y+k. So (a) the annex #978 (merged before I could withdraw it: DELETE answered 409 submission-merged) has a wrong §2 bullet; a corrected annex v2 (C/erdos-257--h18-annex-v2.md) is filed (next line); (b) spec-689ac1ac (#975, merged) states the per-coefficient case; the weighted lemma C/block-divisibility.lean compiles (log 01M5X0JF109KWNGF67Z3BFX8VS) and is proposed as its own crux; (c) precheck loop 3 restarted for the spec-689ac1ac proof.
21:09Z Corrected annex v2 on erdos-257--h18 filed: graph PR #986, id 01M5X0PJVR775ADGGW1Y8AFANH, hash b1e3cd7804bb.
21:10Z Fourth crux proposed: spec-ced1e7c5 (weighted block divisibility, deps [spec-23b0fff0], for erdos-257--h18), graph PR #990, proposal 01M5X0SEN83DDPSTBAHS471M44 (POST took 48.9 s; hazards acknowledged, witness matched). Precheck of the spec-689ac1ac proof accepted: job 01M5X0S4WRBCNYGW2RHVQWC8JF (21:10:10Z). #980 gate still running since 21:01Z.
21:12Z Gloss of spec-689ac1ac filed: graph PR #992, id 01M5X0X6S0GA17K0VH1P5BRZ7J (first attempt refused 400 label-invalid: 68 characters, cap 60 — the cap is in the schema, not in the guide). C/spec-ced1e7c5-Proof.lean assembled; precheck loop 4 waiting. Waiting on: #980 (proof, gate since 21:01Z), #990 (crux), #986 (annex v2), #992 (gloss), precheck job 01M5X0S4WRBCNYGW2RHVQWC8JF.

### F6 — bug (products/api): a node whose dependency has no merged proof is listed `needs: proof, claimable: true`, and a precheck on it is accepted and then fails step 4 with `dep-unproved`
- Kind: bug.
- What happened: spec-689ac1ac (crux merged as #975 at ~21:06Z) declares `deps: [spec-23b0fff0]`, whose proof (#980) was still in the gate. `GET /frontier.json` at 20:57Z already listed `spec-23b0fff0` (deps on the then-unproved `spec-137537c8`) as `status: speculative, needs: proof, claimable: true`; the guide says a node waiting on unproved dependencies reads `needs: dependencies`, `status: blocked`, and that a precheck on it is refused `409 node-blocked`. Instead `POST /precheck` on spec-689ac1ac answered 202 (job 01M5X0S4WRBCNYGW2RHVQWC8JF, 21:10:10Z), ran two minutes on the hosted runner, and failed at step 4: `dep-unproved: dep 'spec-23b0fff0' has no merged Proof.lean; this node is blocked until it does`.
- What I expected: the frontier row to say `needs: dependencies` / `claimable: false` for a speculative node with an unproved dep, and the precheck to be refused before a runner is spent (the same way `node-blocked` is answered for a hole without a witness).
- Cost: one precheck job and ~3 minutes; a second loop on spec-ced1e7c5 would have spent another, stopped by hand.
- Reproduce: propose a crux with `deps` naming an unproved node, let it merge, read its frontier row, precheck any proof of it.
21:13Z Precheck job 01M5X0S4WRBCNYGW2RHVQWC8JF FAIL at step 4 dep-unproved (spec-23b0fff0 not yet proved; #980 still in the gate). Loop 4 stopped; both prechecks retried after #980 merges and renders. F6 logged.
21:17Z Graph PR #980 MERGED (proof of spec-23b0fff0; its gate ran 21:01–21:17Z, 16 min against ~5 for #968). Precheck loops 3 (spec-689ac1ac) and 4 (spec-ced1e7c5) restarted.
21:18Z Precheck of spec-689ac1ac proof accepted again: job 01M5X17730RK5ZNTR8HZA7QXBA (21:17:52Z). Same second, precheck of spec-ced1e7c5 refused 409 node-blocked "waits on unproved dependencies: spec-23b0fff0" although #980 had merged: the blocked check reads the rendered products, the accepted one at 21:10Z did not refuse on the then-unproved dep — the two checks disagree (F6).
21:20Z Precheck 01M5X17730RK5ZNTR8HZA7QXBA FAILED again at step 4 dep-unproved: a precheck runs at the products' rendered_from, which still predates #980; two runner jobs spent on an accepted-then-refused precheck (F6). Now waiting until the frontier shows spec-23b0fff0 proved before retrying.
21:29Z Products rendered with spec-23b0fff0 proved at 21:27Z (ten minutes after the merge). Precheck of the spec-689ac1ac proof accepted: job 01M5X1SG1RSHQM56DEEZGDZHDB. #990 gate re-running after its branch update; loop 4 retrying.
21:33Z Precheck 01M5X1SG1RSHQM56DEEZGDZHDB PASS; proof of spec-689ac1ac submitted: graph PR #1011, submission 01M5X22P00QQW5B33F5WBNB66B. Precheck of the spec-ced1e7c5 proof accepted against the green proposal #990: job 01M5X20DQGC7PXGSK3M08QHGDQ (21:31:37Z).
21:37Z Precheck 01M5X20DQGC7PXGSK3M08QHGDQ of the spec-ced1e7c5 proof PASS (run against proposal #990's head). Submitting once #990 has merged.

### F7 — docs: the gloss `label` cap (60 characters) is enforced but not written anywhere a contributor reads
- Kind: docs.
- What happened: `POST /glosses` for spec-689ac1ac with a 68-character label answered `400 label-invalid: label is 68 characters; at most 60` (21:12Z). The number is in `schemas/gloss/v3.json`'s description; the guide never mentions `label` at all (F4), so the first a contributor learns of the cap is the refusal. The error names the limit, which is good.
- What I expected: one line in the guide's gloss section: "optional `label`, at most 60 characters of plain text, the name the drawing shows".
- Cost: one minute.
- Reproduce: file any statement gloss with a 61-character label.
21:38Z F7 logged. Lane on erdos-257 has 14 open PRs (A: 9, B: 1, mine: #990, #992, #1011); #990 first, gate re-running.
21:39Z Graph PR #990 MERGED (crux spec-ced1e7c5); submission of its proof answers products-pending, a loop retries it and then files the gloss (C/spec-ced1e7c5-gloss.md).
21:41Z Postmortems filed: erdos-257--h2--h1 (graph PR #1014, id 01M5X2HCPG4G5B0RJMEXTBDB71; route: digit method on the greedy set, refuted-route, tails bounded below by 2^-(min G)) and erdos-257--h18 (graph PR #1015, id 01M5X2HJJ0EKAYG9MXJNWYW8NV; route: the engine as nodes then a new class, exhausted). Texts in C/postmortem-h2h1.yaml and C/postmortem-h18.yaml.
21:44Z Proof of spec-ced1e7c5 submitted: graph PR #1016, submission 01M5X2PTH0144MY8HZ551X3P31 (products rendered ~4 min after the merge). Gloss of spec-ced1e7c5 filed: graph PR #1017, id 01M5X2Q2B064R29ZRPXWWWSQR5. All planned submissions are in; what remains is the queue.

### F8 — products (minor): an outline step whose hypothesis name holds a non-ASCII letter gets an id with the code point spelled out
- Kind: bug (cosmetic).
- What happened: the outline of spec-137537c8's proof (`targets/erdos-257/outlines/4dc304abe5ef….json`, read 21:47Z) lists the steps for `have hφm` and `have hφd` with `name: "hφm"` / `"hφd"` but ids `hR.s2.hsupp.h_x3c6m` and `hR.s2.hterm.h_x3c6d`. An explainer must cite the id, so a writer who reads the Lean sees `hφm` and has to discover `h_x3c6m` from the JSON; the site's outline view presumably shows the id too.
- What I expected: the id to be the name (ids are ASCII by rule, so either allow the letter or document the escaping in "Reading an outline").
- Cost: a minute.
- Reproduce: merge any proof with a `have hφ : …` and read its outline.

### F9 — bug (gate/products): `explainer-name-unanchored` fires for Mathlib lemmas the step does use, when the Lean calls them by dot notation
- Kind: bug (false-positive warning).
- What happened: filing the explainer of spec-137537c8's proof (PR #1018, 21:50Z) warned twice: section "The left side…" cites `Summable.tsum_prod`, "which none of the constants its steps (hL, hmid) use contains", and section "The right side…" cites `HasSum.tsum_fiberwise` likewise for (hfib, hR). The Lean at those steps is `rw [hg_summable.tsum_prod]` (line 97, inside hmid) and `hg_summable.hasSum.tsum_fiberwise φ` (line 102, the term of hfib): exactly those constants, called with dot notation. The outline's `uses.mathlib` for hmid and hfib lists nothing (hrow's lists `Set`, `Set.Iio` only), so the anchoring check cannot see them.
- What I expected: `uses` to include constants reached through dot notation and through `rw [...]` arguments; the warning says to "check that the prose describes the Lean it names", which here it does.
- Cost: none (a warning never refuses), but a writer who trusts the warning would delete the two most informative names in the explainer.
- Reproduce: write an explainer naming a lemma the proof applies as `h.lemma_name`; read the warnings on the receipt.
21:48Z Explainer of the spec-137537c8 proof filed: graph PR #1018, id 01M5X2TBT03E3660JJVBGHXS5M, hash 9d0840271525 (two explainer-name-unanchored warnings, both false positives: F9). F8 logged.
21:49Z MERGED: glosses #992 (spec-689ac1ac) and #1017 (spec-ced1e7c5), annex v2 #986, postmortems #1014 and #1015, explainer #1018 (gate_report ok). Open: proofs #1011 (position 2) and #1016 (position 3, gate).
21:50Z Explainer of the spec-23b0fff0 proof filed: graph PR #1022, id 01M5X339Y8TRHWXMRNCEZ44075, hash 4545a1ea50e5 (dry run ok, no warnings; C/spec-23b0fff0-explainer.md).
22:12Z Graph PR #1011 MERGED: spec-689ac1ac (per-coefficient block lemma) is proved. #1016 (spec-ced1e7c5 proof) gate running after its branch update. Two API reads timed out at 22:11Z (curl -m 25, connect never completed); the next reads connected in 0.15 s: the laptop path, not the service.
22:12Z Explainer #1022 MERGED (gate_report ok). Frontier: spec-137537c8, spec-23b0fff0 and spec-689ac1ac no longer listed (proved); spec-ced1e7c5 speculative, needs proof (#1016 in the gate). Browser tab closed.

## Final report (agent C, t1026-c) — written 22:16Z, #1016 line updated at the end

### 1. Landed (all through the service; nothing pushed by hand)

Mathematics — the Chowla–Erdős digit method as reusable nodes on erdos-257, each a crux proposed for `erdos-257--h18`:
- **spec-137537c8 — Lambert identity for an arbitrary set**: `∀ A : Set ℕ, ∑' n : A, 1/(2^n-1) = ∑' m, ncard {a ∈ A | 0 < m ∧ a ∣ m} / 2^m` (no hypothesis). Crux #959 merged; **proof #968 merged** (attestation 000968). Gloss #970 merged (labelled). Explainer #1018 merged.
- **spec-23b0fff0 — tail integrality**: if the sum is p/q then `q·T_j = p·2^j − q·Σ_{m≤j} f_A(m)·2^(j−m)` for every j. Crux #969 merged; **proof #980 merged**. Gloss #977 merged. Explainer #1022 merged.
- **spec-689ac1ac — per-coefficient block divisibility**: `2^k ∣ f_A(y+i)` for i = 1..k ⇒ `q·T_{y+k}` is a multiple of 2^k. Crux #975 merged; **proof #1011 merged**. Gloss #992 merged. Explainer #1025 merged.
- **spec-ced1e7c5 — weighted block divisibility** (the form Erdős 1968 actually uses: `2^k ∣ Σ_{i<k} f_A(y+i+1)·2^(k−(i+1))`). Crux #990 merged; **proof #1016 merged** (22:18Z). Gloss #1017 merged. Explainer #1030 filed unanchored (the proof's outline had not rendered by 22:33Z; a later version may add step anchors).
Words: explainer of the `--h2` partial (t1022-o's case split) #961 merged; annex on `--h18` #978 merged (its §2 bullet on Erdős 1968 is wrong) and corrected annex #986 merged; postmortems #1014 (`--h2--h1`, refuted-route: the digit method's smallness half cannot reach a greedy set, tails are bounded below by 2^-(min G)) and #1015 (`--h18`, exhausted) merged.
Lean written and discarded: C/zero-block.lean (compiles; its hypothesis is vacuous, see the --h2--h1 postmortem).

### 2. Unfinished business
- Nothing in flight: #1016 merged at 22:18Z, so all four cruxes are proved on the record.
- Nothing else of mine waits on anyone. Next mathematical step for the lane, not started: the coprimality-free form of Erdős 1968 (C/postmortem-h18.yaml says exactly where the Chinese-remainder step breaks and the weaker hypothesis to try first).
- The lead may want to withdraw nothing: annex #978 is superseded in words by #986 (annexes cannot be withdrawn, 409 submission-merged).

### 3. Findings, most important first (entries under "## Findings" above)
1. **F6** — a crux whose dependency is unproved reads `needs: proof, claimable: true` and its precheck is accepted (202) and fails at step 4 `dep-unproved`; two runner jobs spent. The products-based `node-blocked` check and the precheck admission disagree.
2. **F2** — the open core's own node (`--h2--h1`) shows "attempts 0" while all five postmortems about the walk sit on its parent; the frontier's finest cut sends a prover to a node that looks untried.
3. **F1** — the `--h2` page's "Read the partial proof" prints ~400 lines of private helpers before the one `have` that is the route.
4. **F4 + F7** — `label` on `POST /glosses` is the only way to name a crux and is undocumented (cap 60 is only in the schema); proposals cannot carry a label, so a new crux is drawn as a hash until a gloss merges.
5. **F9** — `explainer-name-unanchored` warns on lemmas the step really uses when they are called by dot notation (`hg_summable.tsum_prod`); the outline's `uses` misses them.
6. **F5** — `deps` naming a merged-but-unrendered node answers `dep-unknown: not a node` instead of `products-pending`.
7. **F3** — raw TeX in the problem's subtitle line (`Let $A\subseteq\mathbb{N}$ …`), screenshot C/problem-page-top.png.
8. **F8** — outline step ids spell non-ASCII hypothesis names as `h_x3c6m`.
Also observed, not filed as findings: #1016's outline (the `proof outlines` job) had not appeared 15 minutes after its merge while #1011's appeared within the usual window; a proof's gate on this target took 15–17 min (#980 21:01→21:17, #1011 ~21:48→22:05) against ~5 min for #968; the products after a proof merge took 10 min to show it proved (#980 merged 21:17, rendered 21:27), during which the frontier still offered the node; `POST /proposals/speculative` took 12–49 s; two API reads from this laptop timed out at 22:11Z and the next connected in 0.15 s.

### 4. Twice as productive
Every lemma here cost ten minutes of Lean on the fast check and forty of waiting: products-pending after each merge (4–10 min), a 15-minute gate per proof, and `dep-unproved` discovered only after a spent precheck. A crux-and-proof could be one act — propose with the proof attached, gate once — and a dependency chain (identity → integrality → block) would then be three merges instead of eight waits. Second, the record's engines were invisible: the integrality and block steps existed as private helpers in two proofs (`tail_eq_Zint`, `R_int`) and nobody could draw on them; `list_words_needed`-style tooling that lists a target's private helper lemmas with their statements would have told me on minute five what I found on minute ninety, and would have stopped me misdescribing Erdős 1968 in annex #978. Third, the one error I made that reached the record (that annex) could not be withdrawn; a withdrawal for annexes, as for glosses, would have cost the record nothing.
22:19Z Graph PR #1016 MERGED: spec-ced1e7c5 (weighted block lemma) proved. All four cruxes proved; final report updated. Using the remaining window for explainers of the two block-lemma proofs.
22:19Z Explainer of the spec-689ac1ac proof filed: graph PR #1025, id 01M5X4RF3RREQ1FVXS242JKPCR, hash 392c70638981 (dry run ok, no warnings; C/spec-689ac1ac-explainer.md). Waiting for #1016's products to render its outline for the last explainer.
22:33Z Explainer of the spec-ced1e7c5 proof filed unanchored (its outline had not rendered 15 min after the merge, attestation 001016 present): graph PR #1030, id 01M5X5H9206B1M7T0F2QDT04WE, hash 04bc630b0a96. The dry run first timed out (curl -m 60, no connection) and then connected in 30.2 s: the laptop path again. #1025 MERGED.
