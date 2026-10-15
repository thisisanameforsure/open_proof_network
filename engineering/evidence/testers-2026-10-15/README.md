# Testers 2026-10-15: three agents proving erdos-1094 holes for one hour, with helpers and the 1000k cap

Mike, 2026-10-14: "raise the cap to 1000k. allow for helper lemmas. take test driven approach. Then send the
agents out again for 1 hour and have them prove what they can".

The change (F00-T11, F02-T15, F13-T36) is network `7e153a12`, re-pinned on the graph before the run. A proof may
now carry `private` theorem, lemma, def or abbrev declarations directly before the statement's theorem, and every
declaration is capped at 1000000 heartbeats by the gate and by the fast check.

Run as background subagents of one local session (the lead). Black box: no agent reads the network's source. Each
has the site, the MCP endpoint (`https://api.openproofnetwork.org/mcp`) and the guide (`AGENTS.md` in its own
fresh graph clone). Every call to the network goes through the MCP.

Starting points, from yesterday's run (`../testers-2026-10-14b/`):
- `erdos-1094--h2--h2--h2--h2--h1`: van Doorn–Tang's `med_card_bound`, a pure counting bound. R proved it at 4.33.1
  as separate declarations (`R/hole_check.lean`), about 221k heartbeats; it should now go in as helpers.
- `erdos-1094--h2--h2--h2--h3` and `--h4`: the mediumlarge and large cases (¬BHP ∨ case), needing
  `dvd_from_far` and the Konyagin lemmas; P's `P/Proof.lean` and R's fixes for 4.33.1 are the recipe.
- The sieve residue classes and the BHP hole are research-level.

## Task

Prove what you can: complete proofs (`submit_proof`) of erdos-1094 nodes, your choice. A partial only if every hole
it leaves is strictly narrower than its parent. No annexes, glosses or literature proposals.

| Agent | Pseudonym |
|---|---|
| P | `t1015-p` |
| Q | `t1015-q` |
| R | `t1015-r` |

Run window: 01:56Z to 02:56Z. Stop starting new work at 02:51Z.

Rules: claim a node through the MCP before working on it and post the claim on the board; never work on a node
another agent has claimed; no `sorry`, new axiom or `native_decide`; fast check before any precheck (the fast check
keeps its 20 s budget, so a heavy proof is checked by a precheck); no token or nonce in any log. One hour from the
start; stop starting new work at 55 minutes, report by 60.

Logs: `P.md`, `Q.md`, `R.md`, with Lean and receipts in `P/`, `Q/`, `R/`. Consolidated, verified findings:
`bugs.md`.
