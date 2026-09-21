# Tester log: erdos-402 (outside-contributor agent, MCP-first), 2026-09-21

All times UTC. Token never written here.

- 06:23 start. GET https://openproofnetwork.org/problems/erdos-402/ 200. "How to contribute" links to /docs/#agents. Guide read from /docs/ (rendered AGENTS.md, ~54k chars of text). MCP endpoint named at the very end: `$OPN_API/mcp` = https://api.openproofnetwork.org/mcp
- 06:23:40 MCP `initialize` + `tools/list` at https://api.openproofnetwork.org/mcp OK with a hand-written JSON-RPC client (streamable HTTP, POST). serverInfo version 3.20, 27 tools. No session id needed.
- 06:23:55 `get_node` tutorial-and-swap 1-3 s. `get_node erdos-402--h3-v2` took **22.4 s** (others 1.2-1.8 s). Observed once.
- 06:25:20 `precheck_submission` tutorial (no token) -> `{status:202, body:{id, nonce, ...}, job_id, poll}`; job 01M31A7X40D9BNWJ5366981TXS. done by 06:27 (<2 min).
- NOTE result shape inconsistency: `precheck_submission`, `check_lean`, `get_token` wrap as `{status, body}`; `get_precheck` and `get_dco` return the document bare (no status/body). My poll loop crashed with KeyError 'body' the first time.
- 06:27 `get_precheck` took **20.3 s** to answer one poll (state done).
- 06:26 `check_lean` verify mode on first h2-v2 draft: 4.1 s, errors by line/col plus goals. Good. Used `#check` in check mode to find lemma names (Finset.gcd_div_id_eq_one): works, 3 s.
- 06:29:48 `get_token` -> 201, identity pseudonym tester-402-e514, but the call took **35.9 s**.
- Design finding: h3-v2's witness type must contain the h2 statement as a conjunct (a hole inherits earlier holes as hypotheses), so witnessing h3-v2 requires re-proving h1 AND h2 inline inside Witness.lean (witness may not import Context). The existing h2-v2 Witness.lean already carries a full inline copy of h1's proof.
- 06:31:23 `claim_node` h2-v2 ttl 1 -> 201 claim 01M31AJZKRAPWPSD28MRP9P5HG. 06:31:24 `precheck_submission` h2-v2 (token) -> 202 job 01M31AK0K01JM5972F7ACCZVJ2.
- 06:32:35 `propose_witness` erdos-402--h3-v2 -> 201, proposal 01M31AMKC0K2DPS2K6MKQB2VJK, **graph PR #134**. Witness = {1} plus inline proofs of h1 and h2 statements. check_lean (check mode) okay:true beforehand; nothing told me whether its TYPE is what step 7 wants before the PR.
- 06:32-06:35 latency: `get_precheck` polls took 19.9 s, then 36.4 s (one python process with 2 fast checks + 2 reads exceeded 120 s wall). Fast `check_lean` calls meanwhile 1-3 s.
- 06:36 h2-v2 precheck verdict pass, steps 1,2,4-8 pass (done within ~4.5 min of queueing).
- 06:36:39 **BUG** `submit_proof` with `tooling: {"model": "...", "version": null, "harness": "..."}` (the guide's own example has `"version": None`) -> isError, `{"error":"arguments-invalid","message":"None is not of type 'string'","source":"adapter"}`. Field not named. MCP schema says version: string. Dropping `version` worked.
- 06:38:22 `submit_proof` h2-v2 -> 201 submission 01M31AZTR06NWQBSXJZ5212BRB, **graph PR #136**.
- 06:39:06 `propose_variant` (relation partial, card-two case of Graham, with relation_proof and acknowledged div-zero hazard) -> 201, node **variant-d865c9c6**, **graph PR #137**. Call took 23.4 s.
- 06:40 / 06:43 **latency**: `get_submission 136` took 68.66 s; next process `get_submission 134` took 68.7 s (same figure twice; looks like a 60 s timeout + retry somewhere). Same calls otherwise 1.5-2 s.
- 06:41:36 `precheck_submission` on pending variant -> 409 node-pending naming PR #137 and waiting_on gate (good message). `get_node` on it -> same node-pending. `claim_node erdos-402--h2` (superseded) -> 409 node-not-open with replacement named (good). `claim_node erdos-402--h3-v2` -> 201.
- 06:43:27 `submit_postmortem` on root (refuted-route: injectivity of b -> a/gcd(a,b) at a = max A fails on {2,4,6}, Lean-checked via check_lean) -> 201, **graph PR #138**.
- 06:44 `gh run list` (read-only): my gate runs for #134/#136/#137 were RE-CREATED at 06:41-06:42 because main moved (other contributors' merges + bot commits); #134 opened 06:32 was still `in_progress` at 06:48 (16 min; guide says "about three minutes on a Mathlib target").
- 06:43:32-06:47 postmortem PR **#138 merged** (append mode, gate success in <1 min, merge actor merged it, no human).
- 06:44-06:47 **latency, service-wide, intermittent**: over MCP get_schema postmortem/v1 19.8 s; get_schema mcp/get_precheck/v1 **75.6 s**; get_defs erdos-402 **67.9 s**; get_submission 68.74 s, 36.71 s, 68.53 s. Over plain HTTP `curl -m 100 https://api.openproofnetwork.org/submissions/136` -> **no answer in 100 s (curl code 000)** while /health answered in 0.5 s. So it is the service, not the MCP adapter. Slow figures cluster at ~20 / ~36 / ~68 s (= 4 + 16/32/64?) - INFERENCE: a retry/backoff loop against an upstream (GitHub?) under concurrent load. Other testers were active at the same time.
- 06:49 **gate restart churn (observed via read-only gh)**: #134 gate run 1 (06:32) superseded; run 2 created 06:41:17 completed SUCCESS ~06:44; by then main had moved so the branch was updated and run 3 started 06:47:14. #136: run created 06:41:30 success, re-run started 06:47:55. #137: success at ~06:49 and immediately `BEHIND`. Each main move (any contributor's merge + the bot's commit, including my own postmortem #138) invalidates every other open PR's green gate; with a ~3 min Mathlib gate and merges arriving every 1-3 min, a PR can pass repeatedly and never merge. 17+ min and counting for a witness PR.
- 06:49 HTTP timings: /health 0.5 s, /submissions/136 no answer in 100 s, **/frontier.json 51.3 s**, /info.json 0.5 s, /submissions/134 0.5 s.
- 06:49:37 postmortem visible in `get_node erdos-402` (attempts 2, refuted_route_classes [direct-estimate]) and on the site's node page ~6 min after filing. Site problem page shows "2 attempts".
- ~06:50 **witness PR #134 MERGED** (opened 06:32: 18 min, 3 gate runs). Step 7 accepted the type `∃ A, H1 ∧ H2 ∧ 0 ∉ A ∧ A.Nonempty ∧ A.gcd id = 1 ∧ Farey(A)`.
- ~06:57-06:58 **proof PR #136 (erdos-402--h2-v2) MERGED** (opened 06:38: ~20 min; gate ran and passed 4 times: created 06:41:30, 06:44:52, 06:47:52, 06:50:54, 06:54:27 per `gh run list`). attestation_note: attestation-pending at 06:58.
- 06:58 variant PR #137 still open after 19 min: gate passed 5 times (06:42, 06:45, 06:49, 06:52 runs all success; 06:56 in progress), every time main had moved before it could merge.
- 06:58:46 get_target: h3-v2 now `ready` (witness in), h2-v2 still `ready` (products lag after #136).
- 06:59:00 `release_claim` h3-v2 -> 200. Frontier's `claims.active[]` entries carry no claim id, so a contributor who lost the claim receipt cannot find the id to release. After #136 merged my h2-v2 claim was still listed active (06:59).
- 07:00 `check_lean` (check and verify, node_id erdos-402) on a ROOT assembly that names `erdos_402__h1/h2/h3`: `Unknown identifier erdos_402__h2`. The root's Statement.lean imports only Mathlib (pre-2026-09-20 node), so the root cannot be closed through its holes; guide says such a node "closes by a direct proof instead". Consequence observed: h1 (proved), h2-v2 (proved by me today) and h3-v2 do not mechanically bring erdos-402's root closer; a closer must inline all three proofs or a curator must revise the root (D-8). Neither the problem page nor get_node says so. Guide sentence "With a node_id, the node's own Nodes.«<id>».Context is inlined as well" is unconditional, and did not hold for this node (or was inlined without effect).
- 07:01 #137 still open: waiting_on gate, 22 min, 6th gate run.
- 07:07:47 #136 attestation at attestations/000136.json. 07:08:41 get_target: **erdos-402--h2-v2 proved**, h3-v2 ready, root ready.
- 07:08 #137 (variant-d865c9c6) STILL OPEN after 29 min: at least 8 gate runs, every completed one success (06:42, 06:45, 06:49, 06:52, 06:56, 06:59, 07:02; 07:05 in progress). Never failed; never merged. Variant proof (fast-checked okay:true, file var.lean in my scratchpad) could not be prechecked: node-pending.
- 07:08:42 released h2-v2 claim (200). End of timebox (45 min).

## End state
- PR #134 witness for erdos-402--h3-v2: merged (h3-v2 now ready).
- PR #136 proof of erdos-402--h2-v2: merged, attested (000136), node proved.
- PR #138 postmortem on root (refuted-route, direct-estimate): merged.
- PR #137 variant-d865c9c6 (card-two case, relation partial): open, green repeatedly, not merged.
- HTTP fallbacks needed for MCP gaps: none for function. HTTP and read-only gh used only to diagnose latency and gate churn.
- Source repo read: not needed.

## After the timebox (correction to "End state")
- ~07:11 **#137 (variant-d865c9c6) MERGED**, 32 min after opening (06:39), after at least 8 gate runs. The "open, not merged" line above was true at 07:08 and is superseded.
- 07:12:43 `precheck_submission` of the variant's proof -> 409 `products-pending`, retry_after 240 (clear message, as the guide describes). Stopped here: the proof (fast-checked okay:true) is NOT submitted; it is in the scratchpad as var.lean and is reproduced in the final report's node id for anyone to take.
- 07:15:35 variant precheck accepted (202) ~4 min after the merge, job 01M31D3XER0W2QNKV6SQZ2Q60V. 07:19:03 verdict FAIL step 2 `proof-not-statement`: expected line 2 `import Nodes.«variant-d865c9c6».Context`, got "". MY ERROR, documented in the guide (the service adds that import to a proposed statement); I built the proof from the text I sent instead of the merged Statement.lean. `check_lean` verify on the old text does warn `imports-differ`; I had skipped verify because the node did not exist when I wrote the proof. Cost: one 3.5 min precheck.
- NOTE `result.diagnostic` does not exist at the top of a precheck result; the diagnostic is inside `steps[n].diagnostic` and `attestation.diagnostic`.
- 07:19 lint `context-restated` fires in verify mode on variant-d865c9c6 although its Context.lean is "Declared dependencies: none" and restates nothing. False-positive lint (okay was still true).
- 07:19:56 second precheck job 01M31DBWB008D9CNZH36DRJFW4 -> 07:22:48 PASS steps 1,2,4-8.
- 07:22:55 `submit_proof` variant-d865c9c6 -> 201, submission 01M31DH9681PBX107FKT4DYR43, **graph PR #145**. Left open; not waited on. Total run 60 min (15 over the timebox, spent on the variant's proof after #137 merged).
