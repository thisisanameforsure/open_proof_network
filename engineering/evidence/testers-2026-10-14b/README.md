# Testers 2026-10-14b: three agents filling holes on erdos-1094 for one hour

Mike: "have 3 agents work for 1 hour JUST filling in some hole of the erdos 1094. Using MCP. Their choice on
which to prove."

Run started 17:35Z from one local session (the lead), as background subagents. Black box: no agent reads the
network's source (`gate/`, `api/`, `site/` of the network repo). Each has the site, the MCP endpoint
(`https://api.openproofnetwork.org/mcp`, JSON-RPC over HTTP) and the guide (`AGENTS.md` in its own fresh graph
clone). Every call to the network goes through the MCP; plain HTTP is a fallback only when the MCP has no tool
for the job, and each such use is logged as a finding.

State at the start: graph `main` at `466c11deb`, no open pull requests. erdos-1094 has 18 claimable nodes on the
frontier. The open leaves (holes nobody has decomposed) include the four van Doorn–Tang cases
`--h2--h2--h2--h1..h4` (each "¬BHP ∨ one range of n"), the four sieve residue classes `--h3--h1--h1--h1/h2` and
`--h3--h1--h2--h1/h2`, and the BHP hole `--h2--h2--h1`.

## Task

Fill a hole: a complete proof (`submit_proof`) of a leaf node of erdos-1094. Each agent chooses which. No annexes,
glosses, literature proposals or skeletons. A partial is allowed only as a last resort after 18:10Z, and only if
every hole it leaves is strictly narrower than its parent (never "the parent plus a consequence").

| Agent | Pseudonym |
|---|---|
| P | `t1014-p` |
| Q | `t1014-q` |
| R | `t1014-r` |

Rules: claim a node through the MCP before working on it and post the claim on the board; never work on a node
another agent has claimed; no `sorry`, new axiom or `native_decide`; fast check before any precheck; no token or
nonce in any log. Stop starting new work at 18:25Z; final report by 18:35Z.

Logs: `P.md`, `Q.md`, `R.md`, with Lean and receipts in `P/`, `Q/`, `R/`. Consolidated, verified findings:
`bugs.md`.
