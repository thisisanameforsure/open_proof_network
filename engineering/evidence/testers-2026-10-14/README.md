# Testers 2026-10-14: three agents on erdos-1094 for thirty minutes

Mike: "have 3 agents work on erdos 1094 for 30 minutes".

Run started 11:05Z from one local session (the lead), as background subagents. Black box: no agent reads the
network's source (`gate/`, `api/`, `site/` of the network repo). Each has the site, the service (MCP and
HTTP) and the guide (`AGENTS.md` in its own fresh graph clone).

State at the start: graph `main` at `b5b2976f1` (products rendered from `f2864db98`), merge queue empty.
erdos-1094 has 13 claimable nodes. This morning's van Doorn–Tang skeletons (#497–#510, pseudonym `t1014-a`)
wrote `--h2--h2--h1` (BHP), `--h2--h2--h2` (¬BHP ∨ the vdT theorem), `--h2--h2--h3` (n beyond
exp(log²k / 20 log log k)) and `--h2--h1--h4` (the strip k² ≤ n < k(k + 3k^0.525)).

## Assignments

| Agent | Pseudonym | Owns | Task |
|---|---|---|---|
| A | `t1014-x` | `--h2--h2--h2` | start porting van Doorn–Tang's Lean (github.com/Woett/ChatGPT-s-note-on-Erdos451, Lean 4.28) to the pin: map their lemmas onto holes and land a skeleton whose holes are those lemmas, with whatever is short proved in the assembly |
| B | `t1014-y` | `--h2--h1--h4`, `--h2--h2--h3`, `--h2--h1--h1` | the residual cores: carve provable pieces without a circular hole; annexes, approach records, postmortems |
| C | `t1014-z` | `--h3--h1--h1`, `--h3--h1--h2`, `--h2--h2--h1` | the 2k ≤ n < k² sieve halves; plus literature: propose literature status where it is published (BHP 2001 for `--h2--h2--h1`) |

Rules: no `sorry`, new axiom or `native_decide` in a proof; fast check before any precheck; no fixed-size
variants; no circular hole; nobody submits on a node another agent owns; no token or nonce in any log;
coordination through `COORDINATION.md`. Stop starting new work at 11:30Z; final report by 11:35Z.

Logs: `A.md`, `B.md`, `C.md`, with Lean and receipts in `A/`, `B/`, `C/`. Consolidated, verified
findings: `bugs.md`.
