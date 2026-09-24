# Tester log — erdos-1050 via MCP (2026-09-24)

Start: 2026-09-24T12:24:50Z. Stop new work at 13:19:50Z.

## Log

- 12:24:50Z `curl https://openproofnetwork.org/problems/erdos-1050/` → 200; `curl https://api.openproofnetwork.org/health` → 200. Network OK.
- 12:25Z Read the problem page and /docs/ (AGENTS.md rendered). Target: `Irrational (∑' n, 1/(2^(n+1) - 3))` (calibration, known result: Borwein 1991).
- 12:25Z MCP `tools/list` → 200 in 0.7 s, 29 tools, matches the guide's appendix table.
- 12:25Z MCP `list_frontier {filters:{target_id:"erdos-1050"}}` → 2 entries (root `erdos-1050`, `erdos-1050--h1-v2`), both claimable, **no active claims**. `list_submissions` → nothing open on erdos-1050. So the other agent has not claimed yet.
- 12:26Z MCP `get_node erdos-1050` and `erdos-1050--h1-v2`: earlier testers (t0923-1050-b, tester-1050-2045) already filed postmortems: every open node reduces to Irrational T, T = ∑ 1/(2^(n+3)-3), which is Borwein 1991 (q=2, r=-3), `missing-library`. `erdos-1050--h1-v2--h1` (= Irrational T) is status `circular`, not on the frontier.
- 12:26Z Observation (not a bug, confusing): the page's graph key calls h1-v2--h1 "circular" in the selected-statement card, but the key/legend at the top lists only proved/open/blocked/superseded — "circular" is not explained in the key.
- 12:26:48Z MCP `precheck_submission` on tutorial-and-swap (no token) → 202 in 3.8 s, job queued, nonce returned (kept out of this log).
