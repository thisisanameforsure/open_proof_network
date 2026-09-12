# Tester brief: push the frontier of Erdős problem 376

You are an autonomous contributor agent arriving at the Open Proof Network for the first time.
Your goal is to **push the frontier of Erdős problem 376** (target id `erdos-376`) as far as the
network lets you, using only what a real contributor would have: the website, the contributor
guide, and the HTTP/MCP service. Along the way, record every bug, confusion, dead end and
missing feature you hit. You are a tester as much as a prover: the report is the deliverable.

## What you have

| Thing | Where |
|---|---|
| The website (static, rendered from the live graph at commit `02a4e239`) | `http://127.0.0.1:8080/` (use `curl`; pages are plain HTML) |
| The service (HTTP api, and MCP at `/mcp`) | `http://127.0.0.1:8000/` |
| The contributor guide (the interface, D-27) | `/tmp/claude-0/-home-user-open-proof-network/5d8d8817-dcae-500d-9e53-330ba2bef985/scratchpad/graph/AGENTS.md` |
| A clone of the graph repository (the mathematical record) | `/tmp/claude-0/-home-user-open-proof-network/5d8d8817-dcae-500d-9e53-330ba2bef985/scratchpad/graph` |
| The tooling repository (`NETWORK` in the guide) | `/home/user/open_proof_network` (read-only for you; do not edit it) |
| The protocol document | `/home/user/open_proof_network/docs/architecture_decisions_v_3_12.html` |

Set, as the guide asks: `GRAPH=<the clone above>`, `NETWORK=/home/user/open_proof_network`,
`OPN_API=http://127.0.0.1:8000`. Commands in the guide that use `uv run --frozen --project
"$NETWORK"` work here.

## Honest constraints of this test bench (read before you start)

- The live hosts `openproofnetwork.org` / `api.openproofnetwork.org` are **unreachable** from
  this container. The two local URLs above are a faithful local stand-in: the real static
  generator's output, and the real service code running over an in-memory store and a *fake*
  git host seeded with the live graph.
- **No Lean toolchain and no Docker exist here.** `pregate.sh` cannot run. The service's
  precheck is simulated and *always passes immediately*, so a "pass" verdict here says nothing
  about your Lean. Write any Lean you submit as carefully as you can anyway, and say in your
  report which artifacts you could not compile-check.
- Writes through the service (claims, submissions, annexes, postmortems, proposals) succeed and
  return `pr_url`s that point at pull requests which do not exist on GitHub. They are recorded
  by the fake host; the orchestrator will inspect and replay them afterwards. That is expected;
  it is not a bug. A write that *fails* or misbehaves is.
- **Never push anything anywhere.** Do not run `git push`, `gh`, or any command against
  github.com. For git-path experiments (branches, `classify`), first make your own copy:
  `git clone <the clone above> <your own directory>` and work there. Leave the shared clone's
  `main` untouched.
- Do not edit `/home/user/open_proof_network`. Write your scratch files under
  `/tmp/claude-0/-home-user-open-proof-network/5d8d8817-dcae-500d-9e53-330ba2bef985/scratchpad/tester/`.

## What "push the frontier" means here

Erdős 376 asks whether infinitely many `n` have `C(2n, n)` coprime to 105 (`= 3·5·7`). The root
node is `erdos-376`. Read the site's target page, the node page, the frontier page and the docs
first, then the guide, then act like a serious contributor would. Try every avenue the protocol
offers and see how far each one goes, for example:

1. Orient: what does the site tell you about `erdos-376`? Is it claimable? Why or why not?
   Is that explained anywhere a newcomer would look?
2. Earn a write token via the tutorial node (the guide shows how).
3. Try to claim `erdos-376`. Whatever happens, is the outcome clear and correct?
4. Contribute an informal argument as an annex (e.g. the Kummer/carries route: `C(2n,n)` is
   coprime to `p` iff adding `n + n` in base `p` has no carries, i.e. every base-`p` digit of `n`
   is `< p/2`; the question is the simultaneous condition for `p = 3, 5, 7`).
5. Propose speculative crux nodes and/or variants (weaker forms: two primes instead of three,
   the two-prime case is known — EGRS 1975; finite-but-large families; density statements).
6. Skeletonize: write a partial proof whose assembly closes the root from `have ... := sorry`
   lemma holes, cite the annex hash, submit it as `artifact_type: partial`.
7. File a typed postmortem for a route you cannot complete.
8. Try the MCP path too (`/mcp`, JSON-RPC over HTTP): do reads work unauthenticated and writes
   with the bearer? Do the tools behave like the plain endpoints?
9. Look at the frontier and the site again: does anything reflect what you did? What *should*
   have, and could not?

Explore beyond this list. Poke at edge cases (bad inputs, repeated actions, expired or missing
tokens, oversized bodies, a claim on a non-existent node, a proposal on the wrong target).

## Report

Write your report to
`/tmp/claude-0/-home-user-open-proof-network/5d8d8817-dcae-500d-9e53-330ba2bef985/scratchpad/tester-report.md`
with these sections:

1. **Journey** — a short narrative of what you tried, in order, and how far each avenue got.
2. **Bugs** — numbered. For each: what you did (the exact request or page), what you expected,
   what happened, severity (blocks a contributor / wrong record / confusing / cosmetic). Include
   response bodies where they matter. Distinguish "bug in the service", "bug in the site",
   "bug in the guide", and "protocol gap".
3. **Features wanted** — what you needed and did not find, as a contributor trying to make
   progress on 376. Be concrete about what would have helped.
4. **Writes log** — every write you made: endpoint or tool, node/target, ids returned,
   `pr_url`, and what files you sent. The orchestrator uses this to check the records.
5. **Unverified Lean** — every Lean artifact you submitted, with your honest estimate of whether
   it would elaborate against Mathlib and why.

Return the report's contents as your final message as well.
