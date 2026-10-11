# Testers 2026-10-09: two agents on erdos-1094 for one hour, MCP entry

Mike: "send 2 agents to work on erdos 1094 for 1 hour using MCP. At the end of their session have
them report any bugs. You validate the bugs and prioritize and report back to me."

Run started 12:40Z from one local session (the lead). The agents are background subagents with no
view of the network's source: neither reads `gate/`, `api/` or `site/` of the network repo. Each
has the site, the MCP server (JSON-RPC over curl) and the guide (`AGENTS.md` in a fresh graph clone).
They use MCP for every service call. HTTP is allowed only for something the MCP has no tool for,
and each such call counts as a finding.

State at the start: graph `main` at `c120d59e9` (products rendered from `76365d732`). erdos-1094
is open track. Its root is `ready`, with holes from the 2026-10-08 run: `--h1` proved, `--h2` open
(the Ecklund/Selfridge core, n ≥ k²), `--h3` open (2k ≤ n < k², a literature theorem through
Konyagin / Granville–Ramaré), and `--h3--h1` (h_sieve, the last-digit residue form, numerically
K = 58 for k ≤ 1000). Yesterday's annexes, glosses and explainers are on the record.

## Assignments

| Agent | Pseudonym | Owns | Task |
|---|---|---|---|
| A | `t1009-a` | `--h3` and `--h3--h1` | carve provable pieces out of h_sieve (e.g. primes in (k/2, k], small-prime ranges) by skeleton, prove what is provable |
| B | `t1009-b` | `--h2` and the root | carve provable pieces out of the n ≥ k² core without a circular hole; words and annexes on any node of the target |

Rules: no `sorry`, new axiom or `native_decide` in a proof; fast check before any precheck; no
fixed-size variants; no hole that implies its parent through the assembly alone (circular); no
token or nonce in any log; coordination through `COORDINATION.md`.

Logs: `A.md`, `B.md`, with Lean and receipts in `A/`, `B/`. Consolidated, verified findings: `bugs.md`.
