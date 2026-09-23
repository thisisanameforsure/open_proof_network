# log erdos-1050-b
- 14:40:34 start
- 14:41:18 POST /precheck tutorial -> 01M37BDBRGXYCRVJRXQZBFKKWG
- 14:41:48 POST /check witness no content h1-v2--h1 -> okay true
- 14:43:54 precheck tutorial done pass (~2.5min); POST /tokens pseudonym t0923-1050-b
- 14:44:07 POST /claims h1-v2--h1 ttl 1h -> 201 claim 01M37BJMPRB9GDDHPNKS9PZ7MW
- 14:44:07 POST /proposals/witness h1-v2--h1 (True := trivial, with statement header) -> 201 PR #146 (4.6s)
- 14:44:47 POST /check eq.lean (root sum = tail sum, root <-> tail irrational) -> okay true, no errors
- 14:45:31 /check rev.lean (approximants -> irrational) okay
- 14:45:54 /check verify root assembly (RootProof.lean, names erdos_1050__h1 from root Context) -> okay false only because Context hole is sorry (lint context-restated); no errors
- 14:46:33 POST /annexes on erdos-1050 (circularity + ready root assembly) -> 201 PR #152 hash b85da506
- 14:47:01 POST /precheck root assembly (expect step-4 refusal: hole unproved) -> job 01M37BR0JR8FSQ2T75ZJEQ3ZCA graph_commit 8d875930
- 14:47:23 POST /postmortems erdos-1050 (circularity, missing-library, annex b85da506) -> 201 PR #154
- 14:48 PR #146 MERGED (witness). Note: PR #150 = another agent's witness on same node, opened 14:46:10 while #146 open
- 14:49:26 root precheck done: fail step 4 'Unknown identifier erdos_1050__h1' line 66 only (as guide predicts; rest of assembly elaborates at the pin)
- 14:52 frontier: h1-v2--h1 ready_since 14:47:28 (witness live). DELETE /claims (release; not proving Borwein)
- 14:52:22 claim/precheck/check on superseded erdos-1050--h1 -> 409 node-not-open / 409 node-superseded / lint node-superseded: all as guide says
## interim findings (14:53)
F1 #150 (t0923-1050-a duplicate witness on h1-v2--h1) is CONFLICTING (GitHub DIRTY) after #146 merged, but /submissions/150 says waiting_on=merge, mergeable_state=dirty; no guide state for "can never merge". Service accepted the duplicate witness proposal at 14:46:10 while #146 was open (no warning).
F2 witness slot file (gate-written) has no import header and says "until then the node is blocked"; guide says Witness.lean holds statement header and site says needs-witness is not blocked. Header version passes.
F3 /check verify on a closable-through-holes parent answers okay:false for a correct assembly (lint context-restated) - guide says read okay first.
F4 math: every open node on erdos-1050 is Borwein's theorem restated (root sum == tail; h1-v2 <-> Irrational tail). Skeleton chain circular.
- 14:53 site: h1-v2--h1 shows ready/open; products rendered at 125fa85 (merge of #146) ~5 min after merge
- 15:02 queue: #147 merged 14:53:26, bot commit 14:56:04. Post-merge run 35877508957 (push on main, #147) has all 3 jobs completed by 14:56:10 but run status still in_progress at 15:02:45. Merge actor runs 14:57:03, 14:59:42, 14:59:51, 15:00:44 all print "#148 is next; a post-merge job is about to move main: holding". No merge since 14:53:26. My #152/#154 green, waiting.
- 15:04:19 run 35877508957 finally completed (8 min after last job)
- 15:07 merge actor: "#148 is up to date and its gate is running: holding for it"
- 15:15 final: #146 merged 14:47:28; #152 annex and #154 postmortem green, waiting_on branch-update (behind); #150 (other agent) waiting_on=merge, dirty. No merge on the graph 14:53:27 -> 15:15.
- STOP 15:15. Report written.
