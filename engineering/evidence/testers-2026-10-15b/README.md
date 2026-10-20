# Testers 2026-10-15b: four agents on erdos-1094 for two hours, two of them rebuilding Granville–Ramaré

Mike, 2026-10-15: "send 4 agents to work on erdos 1094 over the next 2 hours. Have half of them coordinate to
recreate the proof that h3 suggests will help. A. Granville and O. Ramaré, Explicit bounds on exponential sums and
the scarcity of squarefree binomial coefficients, Mathematika 43 (1996) 73-107 — Earlier bound
g(k) >= exp(c (log^3 k / log log k)^(1/2)); not read. Start with a skeleton that will use the results to use h3
directly or some parent/child of it."

`erdos-1094--h3` is the small-n case: ∃ K, ∀ n k, 0 < k → 2k ≤ n → n < k² → (C(n,k)).minFac > k → k ≤ K.
Its merged child `--h3--h1` (the last-digit sieve form) carries the annex that cites Granville–Ramaré: they prove
g(k) > k² for all large k, which is h3.

Run as background subagents of one local session (the lead). Black box: no agent reads the network's source. Each
has the site, the MCP endpoint (`https://api.openproofnetwork.org/mcp`) and the guide (`AGENTS.md` in its own
fresh graph clone). Every call to the network goes through the MCP.

| Agent | Pseudonym | Task |
|---|---|---|
| G | `t1015b-g` | Granville–Ramaré pair: owns the skeleton on the h3 subtree |
| H | `t1015b-h` | Granville–Ramaré pair: reads the paper, writes the outline, proves the elementary holes |
| S | `t1015b-s` | free: prove what you can on erdos-1094 outside the h3 subtree |
| T | `t1015b-t` | free: prove what you can on erdos-1094 outside the h3 subtree |

Run window: 12:40Z to 14:40Z. Stop starting new work at 14:30Z.

Logs: `G.md`, `H.md`, `S.md`, `T.md`, Lean and receipts in `G/`, `H/`, `S/`, `T/`; the paper outline in
`GR-OUTLINE.md`. Consolidated, verified findings: `bugs.md`.
