# Tester B (t1008-b) — provable half of erdos-1094, plain HTTP

12:55Z start. Read guide (AGENTS.md from graph origin/main, 2461 lines).
Layout: BUGS and FEATURES first (edited in place), then the chronological Log (appended).

## BUGS

### B1 — `GET /submissions/<id>` takes ~68 s on a pull request whose gate is running (network bug, latency; severity medium)
- Did: `curl https://api.openproofnetwork.org/submissions/441` (A's partial, gate `in_progress`) at 13:12Z and again at 13:13Z.
- Expected: an answer in about a second; the guide (Precheck and submit) presents this call as the way to "watch it while it is open", so it will be polled.
- Happened: `HTTP 200 67.546661s`, then `HTTP 200 67.804593s`; a third call straight after: `0.532992s` (cached). `GET /submissions.json` at the same moment: 0.50 s.
- Reproduced: yes, twice. Guess: the per-id route fetches the running gate run's jobs/logs from the host (the guide says `jobs` is filled for an unfinished gate run) and waits on it. A client with a 30 s or 60 s timeout sees this route as down.

### B2 — the `__` naming-linter warning is not dropped in `check` mode without a `node_id` (guide drift / minor network; severity low)
- Did: `POST /check` `{"target_id":"erdos-1094","mode":"check","heartbeats":true,"content":<B/h_fixed_k.lean>}` at 13:03Z (theorem named `Opn.erdos_1094__h1`, the name the gate will give the hole).
- Expected: guide, "Iterating fast": "Mathlib's naming linter warns about the `__` in theorem names the gate generates for holes, which you cannot change, so that one warning is removed and listed in `dropped_warnings`."
- Happened: `dropped_warnings: []` and `result.lean_messages.warnings` still holds "The declaration 'Opn.erdos_1094__h1' contains '__', which does not follow the mathlib naming conventions". `okay` was true, so nothing is blocked; it is noise for an agent pre-checking a hole proof before the hole exists.
- Reproduced: seen once in this mode (likely the drop only applies with a `node_id`).

### B3 — a hole created by a merged partial cannot be prechecked: the bot commit that writes it claims `rendered_from` = its parent, and the precheck runs there (network bug; severity HIGH — blocks the whole hole flow)
- Did: after A's skeleton #441 merged and its post-merge bot commit `28f5a569c` ("gate: #441 pass", 13:19:41Z) wrote `erdos-1094--h1/h2/h3`, I sent `POST /precheck` with my token, `{"node_id":"erdos-1094--h1","artifact_type":"proof","bundle":{"targets/erdos-1094/nodes/erdos-1094--h1/Proof.lean": …}}` at 13:21:45Z (job 01M4DTTKH8QE1DWJ5D2HXVP4X8).
- Expected: the guide ("After the skeleton merges", step 2): "Precheck and submit its `Proof.lean` exactly as 'Precheck and submit' above shows". And for a node not yet rendered, the guide's pattern elsewhere is `409 products-pending` with `Retry-After`, before a job is spent.
- Happened: `202` with `"graph_commit":"d1833c0ed55a…"`, then 6.5 min later `verdict: fail`, step 2 `paths`: `{"code":"layout-missing","message":"missing required file META.yaml","details":{"problems":["missing required file META.yaml","missing required file Statement.lean","missing required file Witness.lean","missing required file Context.lean","missing required directory attempts/","missing required directory annex/","missing required directory explainer/"]}}`.
- Why: `git show 28f5a569c:frontier.json` → `rendered_from: d1833c0ed…` while it lists `erdos-1094--h1/h2/h3`; `d1833c0e` (the #442 bot commit, 13:15:38Z, the parent) has no `erdos-1094--h1/`. So the products describe a tree that includes the holes but name a commit that does not; the precheck checks out that commit. Later commits on main (outline 5bccaf9, annex bot commits 072450f/7430179, merges #443/#444) did not re-render, so `GET /frontier.json` still says `rendered_from d1833c0e` at 13:28Z. Probably the post-merge catch-up path (main moved under #441's job because #442 merged first) records the base it rendered on rather than the commit it wrote.
- Reproduced: second precheck 13:29:00Z, same bundle → job 01M4DV7WB08PMBBQGGS26ZCVRR, again `graph_commit d1833c0e` (result below in the Log).
- Recurred (reported by C 13:43Z): the #448 bot commit bc3f897b9's frontier.json says rendered_from cf8fd082a, whose tree has no `erdos-1094--h3--h1/`. So it is systematic for every partial merge, not a one-off race.
- Workaround: wait until any later merge on the target re-renders the products (an annex merge did it at 13:28:55Z), check `GET /frontier.json` `rendered_from` contains the node, then precheck. Third precheck at aaa6fbbf5 passed.
- Cost: each attempt burns a precheck job and ~6.5 min, and the error ("missing required file Statement.lean" for a node that is on `main` and on the frontier as claimable) points the contributor at their bundle, not at the network.

### B4 — intermittent ~70 s stalls inside the service before any work starts; the check log's `latency_ms` hides them (network bug, latency; severity medium; probably the same cause as B1)
- Did: `POST /check` `{"node_id":"erdos-1094","mode":"check","content":<B/root-finalization-draft.lean>}` at ~14:01:06Z.
- Expected: "The answer usually comes back in a few seconds … The budget is 20 seconds: a check that outlasts it answers `504 check-timeout`" (guide, Iterating fast).
- Happened: `HTTP 200 77.309329s`, okay true. `GET /checks/01M4DX50CRVXYN9RS2ZGYQAK9R` says `"created":"2026-10-08T14:02:23Z"`, `"latency_ms":1758`: the upstream check took 1.8 s and the record was created ~75 s after my request began, so the time went before the service called AXLE (fetching the node's Context / the graph at main?). The identical request straight after: 6.25 s.
- Reproduced: not on demand (second call fast), but the same ~68–77 s shape appeared on `GET /submissions/441` twice (B1), and first calls of `POST /precheck` (11.1 s, 10.4 s, 8.7 s) and `POST /tokens` (19.6 s) are slow too. The 20 s budget is not enforced on this pre-call phase, and the per-check record cannot show it.

### B5 — the `closing` block the guide points to is not reachable on the HTTP path (guide drift; severity low)
- Did: looked for which import a finalization of erdos-1094 needs. Guide ("After the skeleton merges"): "`get_node` says which case a node is in, in its `closing` block (`context_import`: `statement` or `proof`, with the `import_line`)". The MCP table maps `get_node` to `nodes/<id>/CONTEXT.json` + raw files.
- Happened: `targets/erdos-1094/nodes/erdos-1094/CONTEXT.json` on main has keys `annexes, attempts, cause, circular_below, claims, defect_claims, deps, explainer_present, gate_spec, meta, node_id, proof, rendered_from, schema, statement, status, target_id, untrusted_note, witness` — no `closing`; `GET /` lists no node route. A plain-HTTP contributor has to infer it (root Statement.lean has no Context import, so the proof must add `import Nodes.«erdos-1094».Context`; it fast-checks fine that way).

### B6 — the node page of a proved hole does not say who proved it (site; severity low-medium, credit visibility)
- Did: `curl https://openproofnetwork.org/nodes/erdos-1094/erdos-1094--h1/` at 14:05Z, after #450's products (5201afc17).
- Expected: the guide's "every one of them is credited on a ledger (D-19)"; the ledger has it (`ledger/t1008-b.json`, one `proof` line), and the same page names the gloss writer ("written by t1008-c").
- Happened: the Proof section reads "Proof merged in commit 0f714037487c : …/Proof.lean Checked by the kernel — … attestations/000450.json" and the page text contains no `t1008-b` anywhere; the attestation names the submitter, the page does not. A reader sees who wrote the words but not who wrote the proof.
- Reproduced: one fetch (static page).

## FEATURES

### F1 — a way to record a *reduction* that is not "circular" (design question; with A's F3)
- Wanted: submit a one-hole partial on erdos-1094--h2 that proves the fixed-k bound n < k!+k in the assembly and leaves `h_window` (h2 restricted to k² ≤ n < k!+k) as the hole. Precheck 01M4DW3XSRAJ73J4M11AH8ABX7 passed (hole extracted, carried witness `True` checked).
- Why I did not submit: the guide's circularity rule ("an exhibit … whose type is `<hole's statement> → <ancestor's statement>` … any proof of the hole is a proof of the ancestor") classifies every such hole as circular, because the assembly *is* that implication. Yet narrowing a search space by a proved lemma is the normal shape of a mathematical reduction. The rule cannot tell "the hole is the parent restated" from "the hole is the parent with a proved region cut away". Today the only honest choice is not to submit, so a real (if small) reduction has no place on the record except as an annex.
- What would help: a way to say, on a one-hole partial, "this hole is equivalent to its parent modulo proved node X" (here --h1), so the record shows the narrowed statement without it reading as progress or being claimable as circular; or a guide sentence telling a contributor not to submit one-hole partials whose hole implies the parent.

### F2 — say in the precheck receipt when the node is absent at the commit it will run at
- Wanted: `POST /precheck` to refuse at once (`409 products-pending`, as annexes and witnesses already get) when `node_id` has no directory at the commit the job would check out (see B3), instead of a 6.5-minute job ending in "missing required file Statement.lean".

## Log

- 12:56Z POST /precheck tutorial-and-swap (anon): 202 in 11.1 s, job 01M4DSC2…; polled: running at 12:57, done/pass by ~13:00 (steps 1,2,4-8 pass).
- 12:58Z Literature: fetched Ecklund 1969 (PJM 29 no.2 p.267, msp.org pjm-v29-n2-p04). Lead's premise WRONG: Ecklund proved p ≤ n/2 for n ≥ 2k (except C(7,3)); the n ≥ k² ⇒ p ≤ n/k statement is the Erdős–Selfridge conjecture (open; erdosproblems.com/1094 says Selfridge [Se77] conjectured it for n ≥ k²−1 except C(62,6)). Known partial: holds for n ≥ lcm(1..k)+k−1 (Waterloo colloquium abstract). C posted the same on the board 12:57Z.
- 13:02Z GET /dco.json → version f7ac75b443f4ca16. POST /tokens (tutorial proof, pseudonym t1008-b): 201 in 19.6 s (slow), identity 01M4DSQPB8HBPDEBHC0HDX61G6. Token kept outside the repo.
- 13:02Z Board: A's skeleton (A/skel-v2.lean) gives me hole h_fixed_k: `∀ k : ℕ, 0 < k → {n : ℕ | k * k ≤ n ∧ (n.choose k).minFac > n / k}.Finite` (Erdős's fixed-k observation). Route found: m := k*(n/k) has every prime factor ≤ n/k, so coprime to C(n,k); m ∣ n.descFactorial k = k!·C(n,k) ⇒ m ∣ k! ⇒ n < k! + k. No Legendre/Kummer needed.
- 13:03Z POST /check (mode check, heartbeats, target_id erdos-1094, no node_id) on B/h_fixed_k.lean: 200 in 4.5 s, okay true, lint [], 3510 heartbeats of 200000. First try.
- 13:04Z POST /check with `#print axioms` appended: 200 in 1.1 s; axioms [propext, Classical.choice, Quot.sound]. Board post: Lean ready at B/h_fixed_k.lean.
- 13:05Z POST /check mode witness, statement-only (no node_id), A's witness for h_fixed_k: 200 in 4.6 s, expected = given = `∃ (k : ℕ), (0 : ℕ) < k`, matches true.
- 13:06Z GET /submissions.json?target=erdos-1094: 200 in 0.9 s, open = [] (A still prechecking).
- 13:07Z POST /check mode hazards on the h_fixed_k statement text: 200 in 6.5 s, hazards_status ran, one finding div-zero at `n / k` (expected; the guide says a gate-written hole's hazard is recorded, not refused).
- 13:09Z Sanity script B/exceptions.py (k ≤ 30, n ≤ 3000): reproduces exactly ELS88's 14 exceptions; only (62,6) falls in A's n ≥ k² range, the other 13 in h_small_n's range; all satisfy n < k!+k.
- 13:10Z Board: C's annex #440 merged; A's skeleton is PR #441 (partial on erdos-1094, t1008-a).
- 13:12Z GET /submissions/441: 200 in **67.5 s** (state open, waiting_on gate, gate in_progress, queue position 1 of 2). Repeated 13:13Z: 67.8 s; immediately again: 0.53 s. See BUGS B1.
- 13:15Z Board: A's #441 merged (gate ~5 min, no human). 13:20Z erdos-1094--h1/h2/h3 visible on graph origin/main. h1 Statement.lean: theorem name is `erdos_1094__h1` (no `Opn.` namespace, unlike the root), header `import Mathlib` + `import Nodes.«erdos-1094--h1».Context` + `open scoped Nat`; Witness.lean is A's carried one (status ready).
- 13:21Z Built B/h1-Proof.lean from the node's Statement.lean (B/proof_from_stmt.py + B/h_fixed_k.body). POST /check mode verify node_id erdos-1094--h1 heartbeats: 200 in 5.8 s, okay true, lint [], inlined Context, `__` warning dropped here (dropped_warnings names it), 3486 heartbeats.
- 13:21Z POST /claims erdos-1094--h1 ttl 2h: 201 in 0.6 s, others [], open_submissions [].
- 13:21Z POST /precheck (token, artifact_type proof) on h1 Proof.lean: 202 in 10.4 s, job 01M4DTTKH8QE1DWJ5D2HXVP4X8, graph_commit d1833c0e.
- 13:28Z Precheck 01M4DTTKH8… done: verdict fail, step 2 paths `layout-missing` (all node files "missing"). See BUGS B3. graph_commit d1833c0e lacks the h1 directory; the hole was written in 28f5a569c whose frontier.json says rendered_from d1833c0e.
- 13:29Z Re-precheck same bundle: 202 in 5.3 s, job 01M4DV7WB08PMBBQGGS26ZCVRR, graph_commit again d1833c0e. Board post (B3) to A and lead.
- 13:32Z Second precheck 01M4DV7W… done: fail step 2 layout-missing again (B3 reproduced). C reports the annex merges re-rendered the products at 13:28:55Z (bot commit 2b96ac03d, rendered_from 59770965c, which has the holes); my 13:29:00Z precheck still got d1833c0e (service's view lags ≤ 1 min).
- 13:32Z GET /frontier.json: rendered_from aaa6fbbf5 (contains h1). Third precheck: 202 in 8.7 s, job 01M4DVEE9RYXRCDRY474F08K65, graph_commit aaa6fbbf5.
- 13:36Z Third precheck 01M4DVEE9R… done: PASS (steps 1,2,4,5,6[hazards-derived-statement],7,8), ~3.8 min.
- 13:36Z POST /submissions (proof, erdos-1094--h1, precheck 01M4DVEE9R…): 201 in 4.6 s → **PR #450**, submission 01M4DVNJT8G76R7G4082B230JW.
- 13:44Z POST /check mode check on B/h2-partial.lean (one-hole partial on erdos-1094--h2, hole h_window, assembly = fixed-k bound): 200 in 3.1 s, result.okay true, okay false only for sorry-present (documented), 3522 heartbeats. Witness mode on the would-be hole statement with `theorem witness : True := trivial`: expected True, matches.
- 13:44Z POST /precheck partial on h2 (bundle: attempts/20261008T134500Z-t1008-b-partial.lean + .1.witness): 202 in 6.7 s, job 01M4DW3XSRAJ73J4M11AH8ABX7, graph_commit cf8fd082a (contains h2, fine).
- 13:44Z GET /submissions/450: 200 in 2.3 s; gate completed success, waiting_on merge.
- 13:49Z h2 partial precheck 01M4DW3XSR… done: PASS (2 partial-submission, 4 artifact-reduction, 7 hole-witnesses checked); hole h_window closed_type `∃ (K : ℕ), ∀ (n k : ℕ), (0 : ℕ) < k → k * k ≤ n → n < k.factorial + k → (n.choose k).minFac > n / k → k ≤ K`, expected_witness True. **Not submitted** (FEATURES F1: hole ≡ parent given --h1). A agreed on the board it would be circular-claimable.
- 13:50Z GET /submissions/mine 200 2.2 s (#450 position 1 of 4, waiting_on merge, read_at 13:44:25Z); GET /checks/<my log id> 200 0.5 s (metadata, hash, latency_ms 3819); same without token → 401 (guide says "anyone else is answered 404 check-unknown"; 401 for no token is reasonable, noting only); GET /claims/mine 200 1.6 s, shows C's gloss #454 on h1 in open_submissions.
- 13:54Z PR #450 MERGED (host closed 13:54:18Z; gate had been green since ~13:44Z, queue position 1 of 4 waiting_on merge for ~10 min). waiting_on now products, attestation_note attestation-pending.
- 13:59Z #450 products: bot commit 5201afc17 "gate: #450 pass" (13:59:09Z, ~5 min after merge); attestations/000450.json verdict pass naming t1008-b; erdos-1094--h1 META status **proved**; ledger/t1008-b.json one `proof` line for erdos-1094--h1; graph.json h1 proved.
- 14:00Z DELETE /claims/01M4DTTDNR… 200 in 0.57 s, released.
- 14:01Z Root finalization draft B/root-finalization-draft.lean (A's assembly, `sorry`s → `exact erdos_1094__h1/h2/h3`, plus `import Nodes.«erdos-1094».Context`): POST /check verify → okay false, lints context-restated + sorry-reported (as the lint message says verify does for a proof that uses Context declarations); mode check → okay true, but **77.3 s** (B4); repeat 6.3 s.
- 14:03Z Error paths: resubmitting #450's body → 400 `proof-replaces-merged` (clear message pointing at the alternate path; the guide's `409 precheck-used` is pre-empted by it, fine). Precheck of a partial at Proof.lean → 400 `artifact-path-mismatch` in 0.53 s, no job (as documented).
- 14:05Z Site: /problems/erdos-1094/ 200; node page /nodes/erdos-1094/erdos-1094--h1/ 200, status proved, outline of my proof shown, but no prover name (B6).

## Handoff (14:07Z)

- **PR #450** (proof of `erdos-1094--h1`, hole `h_fixed_k`): MERGED 13:54:18Z; products 5201afc17; `attestations/000450.json` pass, submitter t1008-b; node `proved`; ledger line in `ledger/t1008-b.json`. Claim on h1 released. No other PR opened by B.
- **Ready but deliberately unsent:** `B/h2-partial.lean` + `B/h2-partial.1.witness` — one-hole partial on `erdos-1094--h2` (assembly proves n < k!+k; hole `h_window` = h2 restricted to k² ≤ n < k!+k). Precheck 01M4DW3XSRAJ73J4M11AH8ABX7 passed; not submitted because the hole is equivalent to its parent given --h1 (FEATURES F1).
- **Ready but unsendable:** `B/root-finalization-draft.lean` — the root's closing proof through the three holes (fast check, mode check: okay true). A has the same as `A/root-closing-Proof.lean`. It can be prechecked only when `erdos-1094--h2` and `erdos-1094--h3` (via `--h3--h1`) are proved.
- **Next step mathematically:** nothing cheap remains. `--h2` is the Ecklund/Selfridge conjecture (open); `--h3--h1` (A's residue form) is an analytic sieve statement (Granville–Ramaré / Konyagin territory, and possibly stronger than what they prove; C's annex #451). The proof idea for h1 (m = k·⌊n/k⌋ is coprime to C(n,k) and divides k!·C(n,k)) is in `B/h_fixed_k.lean`; a sharper per-k bound (n < lcm(1..k)+k, the known result) would need Legendre/Kummer and buys nothing for the root.
- Scripts: `B/proof_from_stmt.py` (Statement.lean + body → Proof.lean), `B/exceptions.py` (exception search). No token or nonce is in any file in the repo; the token is in /private/tmp/claude-501/opn-testers-1008/B/TOKEN.
