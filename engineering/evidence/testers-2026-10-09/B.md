# Tester B (t1009-b) log

12:40Z B: start. Read guide, graph clone pulled at c120d59e9.
12:41Z B: get_node erdos-1094--h2 (all includes) 21.8s latency. tutorial precheck job 01M4GAWKX8YA8PFDMFM6RY6SQF started 12:41Z (anon, 4.9s).
12:44Z B: tutorial precheck pass (~2.5 min). get_token 201 in 19.5s -> identity t1009-b (01M4GB2AH0SJMQTSHKD5CW5V6B). Token stored outside evidence dir.
12:47Z B: claim_node erdos-1094--h2 ttl 2h -> 201 claim 01M4GB6T2RHH57N804QS40NAWS (1.1s).
12:47Z B: check_lean on two-hole skeleton (h_lo: k^2<=n<k^3, h_hi: n>=k^3) mode=check: okay=false only for sorry-present, result.okay=true, no errors (1.3s). Numerics: k<=60, n<=60000 -> only (62,6), in h_lo range.
12:47Z B: submit_informal_annex (annex/v2 with steps) -> 201 PR #461, hash 301ade26e4fe... (8.7s).
12:47Z B: list_words_needed erdos-1094 -> 5 subjects, all Witness.lean files (reason no-gloss).
12:50Z B: precheck of skeleton at 12:47Z while #461 open -> 409 annex-pending (as documented, 1.0s).
12:50Z B: submit_gloss dry_run on erdos-1094 witness -> ok in 47.2s (slow!). Real submit -> 201 PR #463 in 6.1s.
12:50Z B: get_submission 461 -> state merged, waiting_on None, attestation_note no-attestation-for-mode (4.8s).
12:50Z B: precheck of skeleton (2 carried witnesses) -> 202 job 01M4GBDYK8PK0DSWY6Y1BVHFDY, graph_commit f56e1408 (4.6s). Annex merged ~3 min after opening.
12:50Z B: submit_approach_record without 'contributor' field (schema lists it required but "set by the service") -> 201 PR #464 (3.8s). Note: route text says "in the hour" though written at 12:50; the blocked_on is honest (no explicit constant).
12:51Z B: propose_literature erdos-1094--h2 status open, 3 refs -> 201 PR #465 (4.1s). A subsequent get_precheck call in the same shell hung >60 s with no answer (client urlopen timeout was 300 s); retried 12:53Z -> 2.7 s. Not reproduced; environment or service unknown.
12:54Z B: precheck of skeleton done in ~4 min: pass, steps 1,2,4-8 pass; holes h_lo, h_hi, expected_witness True, carried witnesses checked.
12:54Z B: submit_proof artifact_type partial -> 201 PR #467 submission 01M4GBNPMRQPBHWGZDGH2DENY3 (7.9s).
12:56Z B: get_submission 467 took 81.0 s (python urllib, incl. initialize); two curl repeats at 12:57Z: connect 0.17 s/0.14 s, total 3.1 s / 0.6 s. Intermittent, not reproduced. #467 gate in_progress, queue position 1 of 1. #463 gloss and #464 approach record merged.
12:59Z B: list_my_claims 78.0 s (shows claim + open PR #467, correct). get_my_submissions 2.3 s. get_check on my 12:46Z check -> record says okay: true, but the check_lean answer's top-level okay was false (sorry-present); the log stored result.okay. -> bug B2.
12:59Z B: switched client to curl with -w timing. server_info: first request (initialize) connect=19.17 s, second connect=0.15 s. So the 20-80 s stalls are TCP connect on this laptop's path (known environment fact), not the service. Server returns no Mcp-Session-Id, so every tool call costs an initialize + a call (two connects).
12:59Z B: server_info protocol_version "3.28" while the graph's latest re-pins cite decisions v3.34/v3.35 (noted, see B4).
13:05Z B: #467 merged 12:59:09Z; post-merge bot commit 'gate: #467 pass' 54630ba8 at 13:04:46Z (5.6 min, #469's commit landed in between). Holes erdos-1094--h2--h1/--h2 created ready with carried witnesses.
13:08Z B: submit_gloss on erdos-1094--h2--h1 -> 201 PR #470 in 116.4 s total (connect split not captured); on --h2--h2 -> 201 PR #471 in 7.4 s. propose_literature --h2--h1 status known -> 201 PR #472 (26.6 s).
13:11Z B: submit_informal_annex on --h2--h2 -> 201 PR #473; curl connect 67.16 s on the initialize (laptop path again), call itself 4.0 s.
13:12Z B: TEST of the circular-direction refusal. check_lean of an exhibit proving <ancestor --h2> -> <hole --h2--h2> (the REVERSE, "no harder than"): okay true. file_defect_claim {stmt_ref: erdos-1094--h2--h2, class: circular-decomposition, line: 9, ancestor: erdos-1094--h2, exhibit: that file} -> 201, PR #474 OPENED, "exhibit_preflight": "skipped" (4.2 s). Expected: refused circular-direction before anything opens (or at least a preflight that runs). -> bug B1.
13:14Z B: withdraw_submission 474 -> 200 withdrawn, PR closed with service comment, gate run was still in progress (83.2 s, connect 75 s laptop path).
13:15Z B: list_frontier {"filters":{"target":"erdos-1094"}} -> filter-unknown (my error: field is target_id; message lists fields, good). With target_id: 6 entries, --h2--h1 and --h2--h2 ready, claimable, origin skeleton-hole. PRs #470-#473 merged 13:12:11-13:12:20Z (batched appends). Site problem page lists both new nodes.
13:15Z B: claim_node erdos-1094--h2--h2 ttl 1 -> 201.
13:16Z B: deliberate probe: fast check of a false proof of --h2--h2 (omega) -> okay false as expected; then precheck the same bundle to test that a fresh hole is precheckable (yesterday's P1) -> 202 job 01M4GCY6HG3EJ5FDDRAJSKC0SS, graph_commit 5b3fa00c.
13:19Z B: probe precheck done: fail at step 4 kernel-replay, diagnostic elaboration-failed with the omega message on Proof.lean line 10. So a hole 15 min old is precheckable (yesterday's P1 is fixed). Gate run of the withdrawn #474 finished 13:16:21Z with "opn-gate: circular-direction: ... (F08-T21)", so the gate's refusal is right; only the service let it open.
13:20Z B: release_claim on both claims (--h2, --h2--h2) -> 200 released; list_my_claims -> none active.
13:22Z B: B2 reproduced: check_lean on the skeleton again -> top okay false, result.okay true, lint sorry-present; get_check on its log_id 01M4GD8Z8RSP8ACY7QS8QA2JXJ -> okay true.
13:24Z B: stopped new work.

## Handoff

Landed (all merged through the service, no human merge):
- #461 stepped annex (annex/v2, steps h_lo, h_hi) on erdos-1094--h2: split the open core at n = k³.
- #467 partial on erdos-1094--h2 citing #461, carrying both witnesses. Created erdos-1094--h2--h1 (h_lo: k² ≤ n < k³, a consequence of Konyagin's g(k) bound) and erdos-1094--h2--h2 (h_hi: n ≥ k³, the sharper open part), both `ready`, origin skeleton-hole. The assembly (K = max, split on n < k³) is kernel-checked. Neither hole implies --h2 on its own.
- #463 gloss on erdos-1094's Witness.lean; #470 and #471 glosses on the two new holes' statements.
- #464 approach record (route: an elementary g(k) > k³ for h_lo, outcome blocked on an explicit constant).
- #465 literature proposal on --h2 (status open: Ecklund, #384); #472 on --h2--h1 (status known: Konyagin, Granville–Ramaré). Both need a steward or curator to confirm.
- #473 annex on --h2--h2: three elementary facts any proof has to defeat (⌊n/k⌋ divides (k−1)!; for j in (k/2, k], ⌊n/j⌋ is a prime > n/k or j·⌊n/j⌋ divides k!; at most log k!/log(n−k+1) smooth terms in the window).
- #474 was a deliberate test (reverse-direction circular claim). It opened, and I withdrew it at 13:14Z; see B1.

Ready but unsent: nothing. Open PRs: none. Claims: none (both released 13:20Z).
Next steps for a successor: formalise the three facts of #473 as `have` steps of a skeleton on --h2--h2; for --h2--h1, look for an explicit constant in Konyagin or Granville–Ramaré (the approach record says what is blocked).
Lean and receipts: B/partial.lean (skeleton), B/exhibit_rev.lean, B/probe_h2h2.lean, B/scan.py (numerics), B/*.out (receipts). No token or nonce is in any of them (the nonce in tut-precheck.json is redacted; the token lived in the session scratchpad only).

## BUGS

### Network bugs

**B1 — MEDIUM — A reverse-direction circular-decomposition claim opens a pull request; the service's exhibit pre-flight says "skipped".** Reproduced once (not repeated, to avoid opening another PR on the record).
- Steps: (1) `check_lean` {target_id erdos-1094, mode check, content: B/exhibit_rev.lean}, which proves `<erdos-1094--h2's statement> → <erdos-1094--h2--h2's statement>` (ancestor → hole, the reverse) -> okay true. (2) `file_defect_claim` {stmt_ref "erdos-1094--h2--h2", class "circular-decomposition", line 9, ancestor "erdos-1094--h2", exhibit: that file}.
- Expected: refused `circular-direction` before anything opens. The tool's own description says "its exhibit is one theorem proving `<stmt_ref's statement> → <ancestor's statement>` (the reverse is refused circular-direction)", and the owner's 2026-09-24 ruling is that a wrong-direction relation or a bad exhibit gets an error back, not a pull request.
- Actual (13:12:41Z, 4.2 s): `{"status": 201, "body": {"id": "01M4GCPMBGJ08E1PVGS8GVP6TX", "path": "targets/erdos-1094/nodes/erdos-1094--h2--h2/defects/20261009T131238Z-t1009-b.yaml", "pr_url": ".../pull/474", "pr_number": 474, "exhibit_preflight": "skipped"}}`. The gate refused it 3.5 minutes later (run 37935230057, 13:16:21Z): `opn-gate: circular-direction: ... a circular-decomposition exhibit proves (hole) → (ancestor) ..., but this one proves (ancestor) → (hole) (F08-T21)`, exit 1. I withdrew #474 at 13:14Z.
- Impact: the gate is right and nothing reached the record. The cost is a red PR, a gate round on the target's lane, and a contributor who learns minutes later what the service could say at once: `declared` vs `expected` is a type comparison the fast checker can already do. "skipped" also comes with no reason.

**B2 — MINOR — The `get_check` call log records `okay: true` for a check whose answer was `okay: false`.** Reproduced twice (12:46Z and 13:22Z).
- Steps: `check_lean` {node_id erdos-1094--h2, mode check, content: B/partial.lean (a skeleton with sorry)} -> top-level `"okay": false`, `"lint": [{"code": "sorry-present", ...}]`, `result.okay: true`, `log_id 01M4GD8Z8RSP8ACY7QS8QA2JXJ`. Then `get_check` {check_id: that id}.
- Expected: the record's `okay` is the answer's top-level `okay` (false). The guide says to "read `okay` at the top of the answer, not inside `result`", and says get_check reads back "the outcome, `okay` and the lint codes".
- Actual: `{"outcome": "answered", "okay": true, "error_count": 0, "lint": ["sorry-present"], ...}`. The log stores AXLE's `result.okay`. Anyone auditing the call log (or a contributor's history) would count a refused-at-gate text as a pass.

**B3 — MINOR — For a gate-written hole, CONTEXT.json's `rendered_from` names a commit where the hole does not exist.** Reproduced (checked in git and on the raw host).
- Steps: after #467 merged (12:59:09Z), #469 merged and its bot commit 93c88d5d landed (13:00:58Z), then #467's bot commit 54630ba8 (13:04:46Z) created erdos-1094--h2--h1/--h2. `get_node erdos-1094--h2--h1` -> `context.rendered_from: "93c88d5db8aec0cf3d55ce6fd4dfa83be20fa704"`. `git ls-tree 93c88d5db targets/erdos-1094/nodes/` lists no --h2--h1 or --h2--h2. `curl https://raw.githubusercontent.com/.../93c88d5db.../targets/erdos-1094/nodes/erdos-1094--h2--h1/Statement.lean` -> 404.
- Expected: a node's products name a commit that holds the node's files. The guide tells HTTP-path clients to read a node's files on the raw host at the commit the products name.
- Actual: the commit predates the node's own directory. Precheck was not affected (my probe precheck at 13:16Z used graph_commit 5b3fa00c and reached step 4), so this matters only to clients that read raw files at `rendered_from`. It is the same family as 2026-10-08's P1.

**B4 — MINOR, unverified — `server_info` says `protocol_version: "3.28"`** while the graph's latest re-pins cite decisions v3.34 and v3.35 (graph commits f051bb2c2, 76365d732). Possibly by design (the protocol version may bump only on some changes). I did not read the code to check. Evidence: `server_info` at 12:59:44Z -> `"protocol_version": "3.28"`.

### My environment (not network bugs)

- **E1 — TCP connect stalls on this laptop's path to api.openproofnetwork.org.** Many calls took 20–116 s. Once I switched the client to curl with `-w`, every slow call was in connect: `connect=19.17` (server_info, 12:59Z), `35.17`, `67.16`, `75.15` s (get_submission, the #473 annex, withdraw 474). The request itself took 0.5–6 s. That is macOS's SYN retransmission schedule, as the 2026-09-21 log already records. Calls I timed before the switch (get_node 21.8 s, get_token 19.5 s, gloss dry run 47.2 s, get_submission 81 s, list_my_claims 78 s, gloss 116 s) are probably the same thing; a repeat gloss dry run took 4.5 s with connect 0.16 s.
- **E2.** One `get_precheck` at ~12:51Z produced nothing for over 60 s before I killed it (my urllib client had a 300 s timeout). Most likely E1.
- **E3.** `timeout` is not on macOS (my own command failed with `command not found`).

### Doc and schema mismatches

- **D1 — MINOR.** `get_schema approach-record/v1` lists `contributor` under `required`, while its own description says "set by the service, never by the caller". `submit_approach_record` accepted a record without it (201, #464). A client that validates locally against the published schema would refuse a valid call, or add a field the service ignores.
- **D2 — MINOR.** The MCP server returns no `Mcp-Session-Id` on `initialize`, so a client cannot keep a session. My client sent `initialize` before every tool call: two connections per call, which doubles the exposure to E1. The guide's MCP section does not say whether a session is expected or whether `initialize` can be skipped.
- **D3 — MINOR, my error, but worth a line in the guide.** `list_frontier` filters use `target_id`, not `target`. The refusal (`filter-unknown`, which lists every field) is good.

## FEATURES

- **F1.** Run the exhibit's direction check in the service before opening, as for witnesses and relations (B1). The checker already elaborates the exhibit, so comparing it with the `<stmt_ref> → <ancestor>` type is one more step.
- **F2.** When a pre-flight is "skipped", say why (e.g. `exhibit_preflight_reason`).
- **F3.** `list_words_needed` listed only Witness.lean files for erdos-1094, because every statement already had a gloss. A gloss on a `True := trivial` witness is low value. Consider leaving trivially-True witnesses out, or ranking statement glosses first.
- **F4.** There is nowhere to record "this hole follows from a published theorem, and here is the deduction" other than an annex plus a `known` literature proposal (what I did for --h2--h1). A literature record that can name the theorem and the deduction would make literature-backed holes easier to tell apart from open ones.
- **F5.** The time from a skeleton's merge to its holes existing was 5.6 min (merge 12:59:09Z, bot commit 13:04:46Z, with another target-local merge in between). `waiting_on: products` said what was happening, which helped. A push notice or an ETA field would save polling.
