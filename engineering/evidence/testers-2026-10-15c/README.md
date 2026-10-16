# Testers 2026-10-15c: thirty agents on erdos-1094 for eighteen minutes

Mike, 2026-10-15: "send 30 subagents to work on erdos 1094 over the next 18 minutes. have them report back to you
if they have any unfinished business and you finish it. just have them work on expanding new paths, just trying
to prove existing open nodes."

Run as background subagents of one local session (the lead), 14:44Z to ~15:02Z. One open erdos-1094 node per
agent (the root and `--h2` excluded); proofs first, partials on the agent's own node otherwise; no new variants.
Black box: each agent had its own fresh graph clone and the MCP. The session's concurrency cap is 20, so 24 of
the 30 ran (a21, a22, a24, a25 never launched; a27–a30 launched late into freed slots).

Logs `aNN.md`, Lean and receipts in `aNN/`, the board `COORDINATION.md`, the two finishers'
`finisher-now.md` and `finisher-chain.md`.

## Pull requests (graph)

| PR | Kind | Node | From |
|---|---|---|---|
| #544 | partial | `--h3--h1--h1--h2--h1` | a09 |
| #545 | partial | `--h2--h2--h3--h1` | a08 |
| #546 | partial | `--h3--h1--h1` | a16 |
| #547 | partial | `--h3--h1--h2--h1` | a10 |
| #548 | partial | `--h3--h1--h2--h2` | a11 |
| #549 | partial | `--h2--h1--h4--h1` | a06 |
| #550 | proof | `--h2--h2--h2--h3--h1--h1--h1--h1` (vdT lattice part) | t1015b-t (previous run; a01 lost the race by 6 s) |
| #551 | partial | `--h3--h1--h1--h1` | a12 |
| #552 | partial | `--h3--h3--h2` (hole: GR Lemma 5.1) | a02 |
| #553 | proof | `--h2--h2--h2--h2` (closing proof; its hole had been proved since 10-14) | a13 |
| #554 | partial | `--h3--h3--h1` (hole: PNT for `Chebyshev.theta`) | a03 |
| #555–#557 | witness | `--h3--h2--h1/--h2/--h3` | a27, landed by finisher |
| #558 | partial | `--h2--h1--h1--h1` | a05, landed by finisher |
| #560 | proof | `--h2--h2--h2--h3--h1--h1--h1` (closing proof) | a04, landed by finisher, merged 17:41Z |

## Closing proofs written, waiting

Fast-checked, not submitted, each waiting on open dependencies: `a07` (`--h2--h2--h2--h3--h1--h1`), `a19`, `a20`,
`a14`, `a26` (the `--h2--h2--h2` chain); `a15`, `a17`, `a29` (the `--h3--h1` subtree); `a30` (`--h3`, `--h3--h3`).

## Findings

1. **Gate defect, blocks the chain.** Step 8's `_CONTEXT_DECL_RE` (`gate/opn_gate/steps/deps.py`) reads a
   Context signature up to the *first* `:=`, non-greedy. `--h2--h2--h2--h3--h1--h1--h1`'s statement has
   `let X := …` inside its type, so the Context side is cut at 658 of 1897 characters and every proof that
   depends on that node fails `context-signature-mismatch` ("graph defect"), though the two texts are
   byte-identical. Only that node, of every statement on the graph, contains `:=`. Precheck
   01M50B1BBRNH7MZE1P32BES5S1.
2. **Token minting is capped at 10 starts per day, shared by every agent on one machine.** Half the agents got
   `429 rate-limited "start: limit of 10 per 86400s"`, and the 401 from `claim_node` sends them back to the
   capped route.
3. **A closing proof over an unproved dependency passes the fast check and fails precheck step 4 with a bare
   "Unknown identifier".** Nothing says the dependency must be proved first (a07, a26, a04).
4. **A node whose holes are all proved but which lacks its closing proof is invisible**: `--h2--h2--h2--h2`
   read `ready` for a day (a13).
5. `submit_proof` names its missing required fields one per refusal (`artifact_type`, `automation`,
   `automation.framework`); `get_precheck` wraps its answer in `result` where other tools use `body` (a02, a06,
   a12, a01).
6. Four agents wrote their tokens into this folder; the lead moved them out before anything was committed.
