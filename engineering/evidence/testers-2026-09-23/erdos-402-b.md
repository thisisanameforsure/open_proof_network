# erdos-402-b log
- 14:41:20 start
- 14:42:03 POST /precheck tutorial (anon): 01M37BEZGRQSQ8T5PRTHB4QFJB queued
- 14:43 found: PR #145 (variant-d865c9c6 proof) merged 09-21 07:31, postmerge run 35573363686 failed 'main moved ... re-render by hand'; no attestation 000145; variant still ready/claimable
- 14:43:47 POST /check (target_id only) card_three proof: 200 in 3.4s, okay true, lint []
- 14:44:39 tutorial precheck 01M37BEZ... done pass (~2.5 min); POST /tokens pseudonym t0923-402-b
- 14:44:44 POST /proposals/variant card_three: {"proposal_id":"01M37BKWR0SAW3CD9Q5VQ77FT2","node_id":"variant-6bd06d63","target_id":"erdos-402","pr_url":"https://github.com/thisisanameforsure/open_proof_network_graph/pull/148","pr_number":148}
- 14:46 POST /check card_four proof: okay true after one fix (Nat.gcd_mul_right rewrite)
- 14:46:39 POST /proposals/variant card_four: {"proposal_id":"01M37BQ670P8M2TVBFDRGG0SKG","node_id":"variant-780e7ade","target_id":"erdos-402","pr_url":"https://github.com/thisisanameforsure/open_proof_network_graph/pull/153","pr_number":153}
- 14:48:29 POST /annexes on erdos-402--h3-v2 (literature note): {"id":"01M37BTHMG1F69YZCJBY6TTZFN","path":"targets/erdos-402/nodes/erdos-402--h3-v2/annex/79faa7cacdf20ef6ef0d209335c1c649810b701bd586e243f4fe29998005f6e5.md","pr_url":"https://github.com/thisisanameforsure/open_proof_network_graph/pull/155","pr_number":155,"hash":"79faa7cacdf20ef6ef0d209335c1c64981
- 14:49 POST /check card_five proof okay true first try
- 14:50:04 POST /proposals/variant card_five: {"proposal_id":"01M37BXED8RM89K7W0A4WQGVNJ","node_id":"variant-bc28297c","target_id":"erdos-402","pr_url":"https://github.com/thisisanameforsure/open_proof_network_graph/pull/157","pr_number":157}
- 14:45 PR #148 card_three variant proposal; 14:46 #153 card_four; 14:48 #155 annex on h3-v2 (literature: h3-v2 = full Graham conj, B-S 1996); 14:49 #157 card_five
- 14:45 POST /precheck on pending variant-6bd06d63 -> 409 node-pending (as documented)
- 14:50-14:53 #148 waiting_on merge (gate green)
14:50:29 open False merge
14:51:00 open False merge
14:51:31 open False merge
14:52:02 open False merge
14:52:32 open False merge
14:53:06 open False merge
14:53:37 open False merge
14:54:08 open False branch-update
14:54:40 open False branch-update
14:55:12 open False branch-update
14:55:45 open False branch-update
14:56:15 open False branch-update
14:56:48 open False merge
14:57:19 open False merge
14:57:50 open False branch-update
14:58:22 open False branch-update
14:58:44 precheck 148-node -> 409 node-pending branch-update None None
14:59:12 precheck 148-node -> 409 node-pending branch-update None None
14:59:38 precheck 148-node -> 409 node-pending branch-update None None
15:00:04 precheck 148-node -> 409 node-pending branch-update None None
15:00:32 precheck 148-node -> 409 node-pending branch-update None None
15:01:00 precheck 148-node -> 409 node-pending branch-update None None
15:01:27 precheck 148-node -> 409 node-pending branch-update None None
15:01:54 precheck 148-node -> 409 node-pending branch-update None None
15:02:20 precheck 148-node -> 409 node-pending branch-update None None
15:02:52 precheck 148-node -> 409 node-pending branch-update None None
15:03:20 precheck 148-node -> 409 node-pending branch-update None None
15:03:49 precheck 148-node -> 409 node-pending branch-update None None
15:04:14 precheck 148-node -> 409 node-pending branch-update None None
15:04:41 precheck 148-node -> 409 node-pending gate None None
15:05:10 precheck 148-node -> 409 node-pending gate None None
15:05:35 precheck 148-node -> 409 node-pending gate None None
15:06:02 precheck 148-node -> 409 node-pending gate None None
15:06:30 precheck 148-node -> 409 node-pending gate None None
15:06:58 precheck 148-node -> 409 node-pending gate None None
15:07:24 precheck 148-node -> 409 node-pending gate None None
15:07:54 precheck 148-node -> 409 node-pending merge None None
148 open False merge blocked [('gate', 'success')] None
153 open False merge unknown [('gate', 'success')] None
155 open False branch-update behind [('gate', 'success')] None
157 open False merge unknown [('gate', 'success')] None
15:08:20 precheck 148-node -> 409 node-pending merge None None
15:08:45 precheck 148-node -> 409 node-pending merge None None
- 15:08 #148 head 9a75a7c: service says waiting_on=merge, runs=[gate success run 35878887068]; GitHub rollup says gate job IN_PROGRESS in that same run (run-level completed/success). No merge on the graph since #147 at 14:53:27.
15:09:15 precheck 148-node -> 409 node-pending merge None None
15:09:42 precheck 148-node -> 409 node-pending merge None None
15:10:08 precheck 148-node -> 409 node-pending merge None None
15:10:37 precheck 148-node -> 409 node-pending merge None None
15:11:04 precheck 148-node -> 409 node-pending merge None None
15:11:29 precheck 148-node -> 409 node-pending merge None None
15:11:58 precheck 148-node -> 409 node-pending merge None None
15:12:24 precheck 148-node -> 409 node-pending merge None None
15:12:52 precheck 148-node -> 409 node-pending merge None None
15:13:21 precheck 148-node -> 409 node-pending merge None None
15:13:47 precheck 148-node -> 409 node-pending merge None None
15:14:12 precheck 148-node -> 409 node-pending merge None None
15:14:41 precheck 148-node -> 409 node-pending merge None None
15:15:09 precheck 148-node -> 409 node-pending merge None None
148 open False merge clean [('gate', 'success')]
153 open False branch-update behind [('gate', 'success')]
155 open False branch-update behind [('gate', 'success')]
157 open False branch-update behind [('gate', 'success')]
- 15:15:21 stop. No graph merge since 14:53:27; proofs for card3/4/5 ready (checked okay on /check) but not prechecked: nodes still node-pending.
- 15:15 FINAL: #148 clean+green, waiting_on merge, no merge-workflow run since 15:07:21 and no graph merge since 14:53:27. Proof files: p3.lean p4.lean p5.lean and *-pre-req.json ready for precheck once nodes merge.
