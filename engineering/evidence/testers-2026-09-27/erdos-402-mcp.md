# erdos-402 MCP tester log
- 19:49:08 start
- 19:49:16 MCP initialize OK 0.46s (server 3.22). tools/list 0.36s: 27 tools.
- 19:49:30 get_target erdos-402 1.8s: root ready, deps h1(proved), h2-v2(proved), h3-v2(ready). Variants: 6bb50ad7, a3b3cb8f, e6d83e6d ready; 7 variants proved.
- 19:49:40 get_node erdos-402--h3-v2 5.7s: h3-v2 = primitive case with all pairwise ratios u/v, u,v<=|A| => exists gcd(a,b)<=a/|A|. This is essentially Graham's conjecture (Balasubramanian-Soundararajan 1996) - not an hour's formalization.
- 19:50:30 get_node on 10 variants (~1.2-1.5s each). Open: card six (e6d83e6d), seven (a3b3cb8f), eight (6bb50ad7); no claims, no open submissions on erdos-402 (list_submissions 0.19s: 0 open overall).
- 19:50:45 Plan: prove card six via reduction to a finite set S={12,15,20,24,30,36,40,45,48} (=60*j/k, k<=5) + decide on 5-subsets.
- 19:51:11 precheck_submission tutorial 4.7s -> 202 job 01M3J6QRWRDAET7AVD13XFTBJF (nonce saved to file, not logged).
(times before 19:51 approximate)
- 19:52:56 check_lean t6 (card six) 3.3s -> errors (interval_cases k=0 case; rw pattern); fixed; check_lean 1.4s -> okay:true (only push_neg deprecation warnings). decide on powersetCard hit maxRecDepth (0.9s) so used a 4-colouring + pigeonhole instead.
- 19:53:32 generated card 7 (L=60, 5 colours) and card 8 (L=420, 6 colours) from the same template; check_lean both okay:true (1.0s, 1.8s). Tutorial precheck done/pass (~2m10s).
- 19:53:32 get_token 0.24s -> 201 identity agent-gcd402 (token saved to file, not logged).
- 19:53:40 claims.json showed graham-gcd-http (the parallel HTTP agent) had claimed card 6/7/8 at 19:52:20-19:53:28, i.e. after my 19:50 check. My claim_node calls for all three (0.26s each, 201) ran in the same command before I read that output: my mistake. claim_node correctly listed `others`. To avoid racing, releasing and moving to new work.
- 19:55:01 template scales: check_lean card 9 (1.2s), 10 (1.6s), 12 (4.9s) okay; 14,16 fail (maxRecDepth/heartbeats in decide/simp). Plan: propose a new variant 'A.card <= 12' (or 13) and prove it, rather than race graham-gcd-http on 6/7/8.
- 19:56:43 combined proof 'card <= 8' (cases 1..8 as haves, 632 lines) check_lean okay in 4.3s after 3 generator fixes.
- 19:58:20 card<=10 combined proof check_lean okay 8.0s (<=11, <=12 hit 200000 heartbeats per-declaration). hazards mode on the statement: div-zero '↑a / ↑A.card', off-by-one-range 'A.card ≤ 10'. witness mode matches:true (4.8s). relation (root -> variant) check okay (0.5s). BUG-ish: check_lean hazards 400 content-not-used when content is sent; tool top-level description doesn't say so (schema does).
- 19:58:45 list_submissions: graham-gcd-http has proof PRs #216-218 on cards 6/7/8 and variant proposals #211 (card nine), #212 (card ten) with the same colouring idea. Dropping my 'card <= 10' plan (would duplicate); aiming beyond: card 13+.
- 19:59:52 ENV: check_lean card 14 -> curl (35) Recv failure: Connection reset by peer after 11s (proxy?). Card 13 with image-pigeonhole (no split_ifs) okay 2.3s. Card 16: maxRecDepth in decide on 71-element Finset literal.
- 20:00:34 with 'set_option maxRecDepth 100000 in' on the three decides: card 14 okay 3.6s, card 16 okay 6.1s (check_lean).
- 20:01:09 propose_variant card sixteen 7.5s -> 201 PR #220 node variant-64035064, preflights: hazards clear, witness matched, relation matched.
- 20:02:18 check_lean card 18 okay (15.4s of the 20s budget), card 20 heartbeat timeout. Colourings with n-2 classes exist (python backtracking) for every n up to 24 tested.
- 20:02:44 propose_variant card eighteen 11.1s -> 201 PR #221 node variant-b89de5c4, preflights clear/matched/matched. #220 waiting_on gate (in_progress).
- 20:03:19 card 20 with 'set_option maxHeartbeats 2000000 in' on the decides: still 200000 heartbeat timeout (the per-declaration limit is not raised by the tactic-level option). Stopped extending n.
- 20:05:14 #220 gate success, waiting_on merge; #221 gate in progress.
- 20:07:55 #220 and #221 both gate success, waiting_on merge (merge actor queue).
- 20:09:48 list_submissions: 16 open (#208-#223); mine are 13th/14th in line. At the ~7-8 min/merge noted in the guide era this is > 1 h: my proofs likely cannot be submitted within my hour.
- 20:11:55 queue unchanged for ~6 min (head #208 waiting_on merge, gate green). Waiting.
- 20:13:57 precheck_submission / claim_node on pending variant-64035064 -> 409 node-pending naming PR #220 and waiting_on merge (clear). Queue: 15 open, one merge in ~8 min.
- 20:17:50 queue still 15 open; head #209 waiting_on branch-update (behind). One merge (#208) in the last ~10 min.

## BUGS (running)
1. [network, throughput] Merge queue: 16 green-or-pending PRs, ~1 merge per 8-10 min; my two green proposals (#220, #221) cannot merge within the hour, so the proofs that are ready (AXLE-checked) cannot even be prechecked (409 node-pending). Reproduced over 20:05-20:18.
2. [network, doc/UX] check_lean mode=hazards with `content` -> 400 content-not-used; with only `statement` works. The tool's description says nothing; the input schema's mode description does. Minor.
3. [network, minor] precheck_submission returning 409 node-pending took 4.5 s (claim_node's same 409 took 0.2 s).
4. [env] one check_lean call: curl (35) Recv failure: Connection reset by peer after 11 s; retry fine. Probably proxy.
5. [my own] claimed three nodes the other agent had claimed 1-2 min earlier: my claim_node ran in the same command as my re-read of claims.json. claim_node returned 201 with `others` populated. Released within a minute.

## FEATURES (running)
- Propose a variant together with its proof (one PR), or allow precheck against a node proposed in an open green PR, so a finished proof is not stuck behind two queue slots.
- claim_node option `exclusive_check` / refuse-if-others flag, so an agent can claim atomically only if nobody holds it.
- A per-declaration heartbeat budget note in the guide: `set_option maxHeartbeats N in` inside a tactic does not raise the 200000 limit; maxRecDepth can be raised that way.
- 20:20:25 template (image pigeonhole + maxRecDepth) check_lean okay for every n tested: 11 (1.2s), 15 (4.5s), 17 (8.8s), plus 16, 18 earlier; results of 3,4,5,12,13,14 below in report.
- 20:20:39 final template check_lean okay for n=3..18 every one (AXLE, non-authoritative). Files t<n>r.lean in this dir; generator mk.py/gen.py/col.py.
- 20:24:51 queue: 14 open, head #210 waiting_on merge with green gate; no merge since ~20:19.
- 20:28:52 #210 merged (~20:27). 13 open; #220 is 10th.
- 20:32:52 final: #220 (variant-64035064, card sixteen) gate success, waiting_on merge; #221 (variant-b89de5c4, card eighteen) gate success, waiting_on branch-update. 13 open PRs, 2 merges in the last 25 min. Proofs NOT submitted (nodes not merged). Ready-to-submit proof bodies: proof16.lean, proof18.lean (build final Proof.lean from the merged Statement.lean with mkproof.py <node> <src> <out>, after saving get_node JSON as <node>.node.json).
- 20:33 stopping new work.
