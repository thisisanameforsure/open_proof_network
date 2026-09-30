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

## Final state (06:20Z, 30 September)

Ninety-five pull requests were opened on the graph by this run (#226–#320): 59 merged, 15 open
and green when the merge queue froze at 04:04Z, 21 withdrawn (duplicates, superseded versions,
two accidental probes). Merges ran at one every 6–10 minutes from 19:12Z to 04:04Z except for a
42-minute stall (19:45–20:27Z, the network repository's CI holding every hosted runner) and the
freeze from 04:04Z that outlasted the run. Bug headings in the logs: 176, consolidated to 36 items
in `bugs.md`.

### erdos-1050 (Borwein's route to the irrationality of Σ 1/(2ⁿ − 3))

| Node | Before the run | After the run |
|---|---|---|
| `spec-440db0f9` (Gaussian binomial at q = 2 is an integer) | speculative, open | **proved** (#234) |
| `erdos-1050--h1-v2--h3` (`hden`, the denominator crux) | open | **proved** (#292, 1050-A; an independent proof by 1050-C kept unsent) |
| `erdos-1050--h1-v2--h4` (`hrem`) | needs a witness | witnessed (#294); proof #320 green, queued |
| `erdos-1050--h1-v2--h2` (integrality) | open | one-hole partial merged (#290); the hole `--h2--h1` witnessed (#318, queued); its partial ready in `1050-B/` |
| `erdos-1050--h1-v2` (Borwein's theorem for q = 2, r = −3) | open, four holes | **closing proof #319 green and queued** (1050-P1's text: h3's theorem plus `hrem` proved inline) |
| `erdos-1050` (the root) | open | closing proof `1050-P1/root-close-via-h1.lean` fast-checked; submittable the moment #319 merges |
| new nodes | | `spec-1a5ab7c3` proved (#228/#282), `spec-ffd3137a` proposed and its proof #311 queued, `spec-eb1219eb` proved (#251/#305), `spec-180d8b72` merged as a statement (#274) |

### erdos-402 (Graham's gcd problem)

| Node | Before | After |
|---|---|---|
| card 9, 10 (`variant-892f5809`, `variant-a5969ff3`) | open | **proved** (#252, #244) |
| card 16, 18 (`variant-64035064`, `variant-b89de5c4`) | open | **proved** (#264, #279; `decide +kernel` over 71- and 95-value certificates) |
| card 11, 12, 13, 15, 25, and every set of at most 24 | did not exist | nodes merged; proofs #298 (11) and #304 (13) merged, #299 (12), #307 (15), #316 (25, through a declared dependency), #309 (≤ 24) green and queued |
| `spec-48bd0126`, `spec-fa8046e4` (structure lemma, colouring reduction) | did not exist | **proved** (#257, #288) |
| `erdos-402--h3-v2` (the hard hole) | open | skeleton merged (#289): prime and prime+1 cases proved inside, one hole; its witness #317 queued; annexes #265, #277 |

### erdos-69 (Tao–Teräväinen; the root's remaining hole is the theorem)

| What | After |
|---|---|
| the record's story | the identity `erdos-69--h1-v2` was already proved; `h2-v2` is the theorem in disguise; annex #297 lays out the literature route and names the external Lean proof; approach record #266 and annex #261 merged |
| new proved nodes | `spec-2e765953` (summability of the prime sum, #239/#302), `spec-7f0efe19` (CRT window, #238/#301), `spec-13f68833` (#243/#303), `variant-f592e3ab` (any base b ≥ 2, #233/#300) |
| green and queued | proofs of `spec-c390279b` (#306), `variant-14c6c771` (#308), `spec-e0b917d1` (#310), `spec-9f8cb4ea` (#313), `variant-3a1bcb9a` (#314), `spec-84446025` (#315) |
| target record | attribution to Erdős 1948 and grade "medium" are wrong (69-C B2); a curator's correction |
