# erdos-69-a log

- 14:40:51 start
- 14:44:25 MCP precheck_submission tutorial-and-swap (see tut_precheck.json)
- 14:44:21 tutorial precheck job 01M37BK2C8R96ZBHYD7R6YPBWJ queued (MCP call took 71.2s to answer 202)
- 14:45 check_lean verify h2 attempt1: 1.4s, one error unknown const Nat.minFac_mem_primeFactorsList
- 14:46 check_lean verify h2 attempt2: okay=true (1.3s). tutorial precheck done
- 14:49:54 get_token -> 201 identity 01M37BX7JGQ7ZDTT8MQ9KEX4F3 pseudonym t0923-69-a (get_dco+get_token calls took >2 min wall total)
- 14:51:02 precheck h2 job 01M37BZ9ZGXWX8A1GCZ2ZM997A queued (graph_commit 125fa85)
- 14:53 probes for ω ≤ n+1 bound OK via List.range subperm
- 14:53:25 check_lean verify h1 (hsplit): okay=true first try
- 14:53:27 claim h1 01M37C3QJRVBCYWMQJ0K62P973; precheck h1 job 01M37C3TGG2RZRAS4C9C7H7X5R queued; h2 precheck done verdict pass (checked 14:56)
- 14:56:30 submit_proof h2 -> 201 PR #167 (submission 01M37C98B0KCX1PZX29CJHA1RN), 5.8s
- 14:58 check_lean h3 attempt1: only error binder type in lambda
- 15:01 check_lean h3 attempt2: only algebra of lambda eq left; PR #167 gate IN_PROGRESS
- 15:01:18 check_lean h3 okay=true
- 15:01 h1 precheck 01M37C3TGG2RZRAS4C9C7H7X5R pass; claim h3 01M37CJCARRHNN4H3ANQJY28AK; precheck h3 job 01M37CJH70HNDFJWR4DQ8YM7G7 queued
- 15:02:45 submit_proof h1 -> 201 PR #172 (submission 01M37CMNJG5K2Y0T0QBT4BPEC7)
- 15:03 list_frontier: t0923-69-c already claimed h1/h2/h3 at ~14:44; PRs #159-#164 by others predate mine; my claim receipts gave no warning
- 15:04:28 released h3 claim (not submitting: #161/#163 by others already green). h3 proof verified by check_lean kept at h3_proof.lean; precheck job 01M37CJH70HNDFJWR4DQ8YM7G7 running
- 15:04 read annex PR #158 (t0923-69-b): h4 equivalent to target; agree (independently reached same view)
- 15:06 get_submission 167: waiting_on merge, mergeable_state clean; #159-#164 BEHIND, #172 BLOCKED (gate running)

## Findings draft
1. claim_node gives no hint of existing active claims or open proof PRs on the node (claimed h1/h2/h3 at 14:50-15:01 while t0923-69-c held claims since ~14:44 and PRs #159-#164 were open). list_frontier shows active claims but not open submissions.
2. Service opens duplicate proof PRs for a node with a green proof PR already open (h1: #159,#164,#172; h2: #160,#162,#167; h3: #161,#163). Racing allowed by design; no warning in submit_proof response.
3. Some MCP calls were slow end-to-end: precheck_submission tutorial 71.2s to 202; get_dco+get_token >2min wall. (connect stalls possible; not separated)
4. h4 is equivalent to the target (agrees with annex PR #158): skeleton at erdos-69--h2-v2--h1-v2 does not reduce the problem.
- 15:07:47 h3 precheck 01M37CJH70HNDFJWR4DQ8YM7G7 pass (not submitted; duplicates #161/#163 exist)
- 15:12 #167 CLEAN+green since 14:59:20, #172 CLEAN; unmerged. Last merge on graph 14:53:27 (#147). merge run 35879227783 at 15:07:26: "#148 is up to date and its gate is running: holding for it" -> head-of-line blocking; 25 open PRs.
5. (finding) merge actor holds all merges behind the oldest PR's running gate even when younger PRs are CLEAN and green.
- 15:13 stopping new work; final report written.
