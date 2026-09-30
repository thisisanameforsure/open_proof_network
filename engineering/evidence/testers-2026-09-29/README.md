# Testers 2026-09-29 — eighteen agents on the three calibration targets, twelve hours

Mike: "Send 18 agents to work on the 3 testing problems of the site. You can act as supervisor
for them, giving them guidance on what nodes to work on. I also want them to report any bugs they
encounter. Those will be aggregated by yourself and report to me, prioritized. Work for 12 hours."

Run started 2026-09-29T19:00Z from one cloud session (the supervisor). The agents are in-process
subagents of that session (model: Opus), black-box: none reads the network's source; each gets
its problem page URL, the guide (the graph's `AGENTS.md`) and the service's route index. They
run in waves of about 2.5 hours; a successor agent continues from its predecessor's log. Every
agent writes its log here as it goes, and the supervisor commits and pushes this directory every
half hour so nothing is lost if the session or the account's usage runs out.

Tokens: the service allows 10 token starts per address per day and every agent shares this
container's address, so six pseudonyms (`t0929-1` … `t0929-6`) were minted by the supervisor and
each is shared by three agents. No token or nonce is in any log.

## Assignments (wave 1)

| Agent | Pseudonym | Target | Node(s) | Task |
|---|---|---|---|---|
| 1050-A | t0929-1 | erdos-1050 | `spec-440db0f9` | prove the Gaussian-binomial integrality crux |
| 1050-B | t0929-1 | erdos-1050 | `erdos-1050--h1-v2--h2` | audit the gate-written integrality statement numerically; defect claim if false, else prove or skeletonise |
| 1050-C | t0929-1 | erdos-1050 | `erdos-1050--h1-v2--h3` | hden: numerics, read the annexes, skeletonise or prove ingredients |
| 1050-D | t0929-2 | erdos-1050 | `erdos-1050--h1-v2--h4` | supply the witness, then work the hole |
| 1050-E | t0929-2 | erdos-1050 | root `erdos-1050` | plain-HTTP walk of the whole guide; audit the root's assembly and status; bugs |
| 1050-F | t0929-2 | erdos-1050 | `erdos-1050--h1-v2--h3` ingredients | MCP-first: every tool; propose and prove the next ingredient of the hden annex as a speculative node |
| 69-A | t0929-3 | erdos-69 | new speculative node | prove Σ_{n≥2} ω(n)/2^n = Σ_p 1/(2^p − 1) |
| 69-B | t0929-3 | erdos-69 | new variant | Σ_p 1/2^p is irrational (binary digits at the primes are not eventually periodic) |
| 69-C | t0929-3 | erdos-69 | root `erdos-69` | a non-circular skeleton: the identity plus the irrationality of Σ_p 1/(2^p − 1); annex on the hard hole |
| 69-D | t0929-4 | erdos-69 | root `erdos-69` | plain-HTTP walk of the guide; approach record on the literature; bugs |
| 69-E | t0929-4 | erdos-69 | the circular chain | MCP-first: every tool; audit the circular claims and the statement's fidelity; revision/defect routes with real content only |
| 402-A | t0929-5 | erdos-402 | `variant-892f5809` | prove the nine-element case |
| 402-B | t0929-5 | erdos-402 | `variant-a5969ff3` | prove the ten-element case |
| 402-C | t0929-5 | erdos-402 | `variant-64035064` | prove the sixteen-element case |
| 402-D | t0929-6 | erdos-402 | `variant-b89de5c4` | prove the eighteen-element case |
| 402-E | t0929-6 | erdos-402 | `erdos-402--h3-v2` | MCP-first: analyse the hard hole, numerics, annex, skeleton if a route exists |
| 402-F | t0929-6 | erdos-402 | new speculative node | the structure lemma every card-n case uses (every element is (j/i)·max), proved once |
| 402-G | t0929-6 | erdos-402 | root, new variants | plain-HTTP walk of the guide; audit the root's assembly; variants for 11 and 12 elements |

Logs: `<agent>.md` (one per agent, continued across waves). Lean sources: `<agent>/`.
The supervisor's aggregated, prioritised bug list: `bugs.md`. Supervisor notes: `supervisor.md`.

## Assignments (wave 2, from 21:22Z)

Six agents, one per pseudonym, each continuing every Handoff of its pseudonym's wave-1 agents:
shepherding the ready proofs through precheck and submission as the proposals merge (merges
followed by `git fetch` of the graph, not by polling the service), bug-hunting meanwhile.

| Agent | Pseudonym | Target | Continues |
|---|---|---|---|
| 1050-P1 | t0929-1 | erdos-1050 | 1050-A, 1050-B, 1050-C |
| 1050-P2 | t0929-2 | erdos-1050 | 1050-D, 1050-E, 1050-F |
| 69-P1 | t0929-3 | erdos-69 | 69-A, 69-B, 69-C |
| 69-P2 | t0929-4 | erdos-69 | 69-D, 69-E |
| 402-P1 | t0929-5 | erdos-402 | 402-A, 402-B, 402-C (launched 21:27Z, once 402-C had finished) |
| 402-P2 | t0929-6 | erdos-402 | 402-D, 402-E, 402-F, 402-G |

## Assignments (wave 3, from 23:36Z)

Same lines as wave 2, one agent per pseudonym continuing its wave-2 Handoff; each launched only
when its line has work within reach (a merge near the head of the queue), not on the clock.

| Agent | Pseudonym | Continues | Launched |
|---|---|---|---|
| 69-W3-1 | t0929-3 | 69-P1 | 23:36Z (69-P1 was killed by a container restart) |
| 402-W3-2 | t0929-6 | 402-P2 | 23:36Z (402-P2 likewise; #260's proof was due) |
| 1050-W3-1 | t0929-1 | 1050-P1 | 23:57Z (#269 third in the queue) |
| 1050-W3-2 | t0929-2 | 1050-P2 | when #292 and #294 have merged |
| 69-W3-2 | t0929-4 | 69-P2 | when #266 / #302 near the head |
| 402-W3-1 | t0929-5 | 402-P1 | when #304 / #307 near the head |

## Assignments (wave 4, from 01:58Z)

Same rule as wave 3: one agent per line, launched only when the line has work in reach.

| Agent | Pseudonym | Continues | Launched |
|---|---|---|---|
| 402-W4-2 | t0929-6 | 402-W3-2 | 01:58Z (the h3-v2 skeleton merged; its hole's witness is due) |
| 1050-W4-1 | t0929-1 | 1050-W3-1 | 02:01Z (#292 third in the queue, past 1050-W3-1's cut-off) |
| others | | | when their lines have work |
