# Testers 2026-10-08 — three agents on erdos-1094 for two hours

Mike: "send out 3 agents over the next 2 hours to work on erdos-1094. Have them report any
issues/bugs. If they have feature requests you can report them. You can drive them, acting as a
coordination layer between them. At the end of the session test if their bugs are bugs, and
prioritize them + feature list."

Run started 12:55Z from one local session (the lead). The agents are background subagents,
black box: none reads the network's source (`gate/`, `api/`, `site/` of the network repo); each
has the site, the service (HTTP and MCP), and the guide (`AGENTS.md` in the graph clone).

State at the start: erdos-1094 (Erdős–Lacampagne–Selfridge, open track) is a bare root, `ready`,
on the frontier, no attempts, no annexes; the owner is its steward (steward record of
2026-10-07). Graph `main` at `6af6af057`. Merge queue empty (one unrelated open PR, #322).

## Assignments

| Agent | Pseudonym | Entry | Owns | Task |
|---|---|---|---|---|
| A | `t1008-a` | MCP (JSON-RPC over curl) | partials/skeletons and proposals on the root | decompose the root into holes that separate the provable from the open; land the skeleton |
| B | `t1008-b` | HTTP | proofs and witnesses on the provable hole(s) A creates | formalise the provable half (the n ≥ k² range, Ecklund 1969 style), first as fast-checked Lean handed to A, then as submissions once the holes exist |
| C | `t1008-c` | site + HTTP | annexes on any node of erdos-1094 | literature and prior art as annexes; read the target as a mathematician would; test claims, words and the site |

Rules: no `sorry`, new axiom or `native_decide` in a proof; fast check before any precheck; only
work that moves the root (no fixed-size variants); nobody submits on a node another agent owns;
no token or nonce in any log; coordination through `COORDINATION.md` and the lead.

Logs: `A.md`, `B.md`, `C.md`, with Lean and receipts in `A/`, `B/`, `C/`. Consolidated,
verified findings: `bugs.md`.
