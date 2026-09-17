# 2026-09-17 — the calibration run, three agents, one per target (F15-T14c, started by Mike)

Mike's instruction: "send 3 subagents out to work on the 3 problems decided upon in F15". The three
are the F15-Q13 choices: `erdos-1050` (easy), `erdos-69` (medium), `erdos-402` (needs a skeleton).
The run may be handed from one model to another mid-way (Fable usage may run out; Opus finishes).
**Every agent keeps its whole state in one file** so a successor resumes from it alone:

    engineering/evidence/F15/calibration-erdos-<n>.md      (n = 1050, 69, 402)

A successor agent for target `<n>`: read this note, then that file, then continue from its
"Next" section. Nothing else is needed.

## Common brief (given verbatim to each agent)

- Repos: network is `/Users/mikehiggins/Desktop/repos/open_proof_network`; graph is the sibling
  `../open_proof_network_graph`. The graph's history is mathematics only: **never commit or push to
  the graph, never touch its main working tree**. Read it via `git -C ../open_proof_network_graph
  fetch -q origin` then `git show origin/main:<path>` / `git ls-tree -r --name-only origin/main
  targets/erdos-<n>`. For a local tree, `git worktree add -q --detach <scratchpad>/graph-<n>
  origin/main` and `git worktree remove --force` it when done.
- Read first: `engineering/onramp/calibration/README.md`; the draft under
  `engineering/onramp/calibration/erdos-<n>/`; the registry's own file
  `engineering/onramp/calibration/upstream/<n>.lean`; the contributor guide
  `../open_proof_network_graph/AGENTS.md` (tested, complete: token, precheck, submit, partial);
  the live node's `Statement.lean`, `META.yaml`, `CONTEXT.json` on `origin/main`.
- Live service: site `https://openproofnetwork.org`, api `https://api.openproofnetwork.org`, MCP
  as the guide names it. Fast Lean check: `POST /check` (F13; hosted checker with Mathlib at the
  pinned version, seconds; client `api/tools/smoke_check.py`; MCP tool `check_lean`). Iterate there.
  The laptop has **no Mathlib checkout** and the Mathlib docker image must **not** be pulled (3.5 GiB
  compressed, 15 GiB free, three agents sharing the disk). `POST /precheck` runs the whole gate in
  CI's sandbox for free before a submission; submissions go through the service and open a pull
  request on the graph. **Do not merge, close or push anything on the graph**; the lead merges.
- Gate rules that bite: a proof cannot add an import or change the header (F00-R19); the statement
  is immutable; read `gate/opn_gate/` for the exact step-2 rule on helper declarations before
  writing one; a partial's holes become child nodes and each hole inherits the holes before it
  (F11-Q22), so order lemma holes before the assembly's locals; a hole's witness later costs real
  mathematics.
- On the network repo the agent writes only its log file and scratch files; no commits, no spec
  edits. Every failure typed into the log with the exact output (R14 (e): every failure a record).
- Timebox ~50 minutes wall clock; finish with: state, PR numbers, exact next steps.

## Per-target goal

- `erdos-1050`: a full proof of `Irrational (∑' n, 1/(2^(n+1) − 3))` (Borwein), submitted, gate
  green → `resolved` after the lead's merge.
- `erdos-69`: a full proof of `Irrational (∑' n, ω(n+2)/2^(n+2))` (Erdős 1948) if it closes; else a
  partial whose holes are the two lemmas (Lambert identity, prime-sum irrationality) with the
  assembly proved, submitted, gate green.
- `erdos-402`: intake PR #74 was BEHIND at start; the lead updates and merges it. Until it is live,
  work from `origin/intake/erdos-402`. Deliverable: a partial whose holes are the lemmas of the
  Balasubramanian–Soundararajan argument, assembly proved, checked through `/check` and precheck,
  submitted once the target is live.

## Lead's own steps (this session)

1. Update PR #74's branch after #73's bot commit lands, wait for green, merge, wait for its bot commit.
2. Collect the three logs; merge whatever is green (owner's act, D-4 step 9 as the workflow needs).
3. Write `engineering/evidence/F15/calibration.md` (R14 f) from the three logs; ledger, index, Log.
