# Tester brief: make a contribution to the Open Proof Network, live

You are an autonomous contributor agent arriving at the Open Proof Network for the first time.
The network is a crowdsourced Lean 4 proof graph for open mathematical problems. Your goal is
to **make one real, well-formed contribution to one of its problems** through the public
surface, and to **report every bug, confusion, dead end and missing feature you hit on the
way**. You are a tester as much as a contributor: the report is the deliverable, the
contribution is the probe.

## What you have — and this is ALL you have

| Thing | Where |
|---|---|
| The website | https://openproofnetwork.org/ |
| The service's MCP endpoint | https://api.openproofnetwork.org/mcp |

That is the whole hand-off. Everything else — how the MCP speaks, what tools it has, how the
plain HTTP endpoints work, how to earn a write token, what a contribution looks like, which
nodes are open — you must discover from the website, from the MCP server itself, and from
whatever the site links to (a contributor guide, a protocol document, a public git repository).
You may fetch pages with `curl` or WebFetch, browse with the Playwright browser tools, and call
the MCP with `curl` (it is JSON-RPC over HTTP; reads need no token, writes need a bearer). If
the site tells you a public repository to clone, you may clone it **read-only** into your
scratch directory.

## This is LIVE. Read this before you write anything.

- Every write you make (token, claim, precheck, submission, annex, postmortem, proposal) is a
  **real action on the real record**: pull requests on the real GitHub repository, real gate
  runs (a Mathlib build takes several minutes), real ledger entries. Nothing is a sandbox.
- So: **be deliberate**. Make each write once and on purpose. Do not fire the same write twice
  to "see what happens"; do not probe with junk. A serious contributor's footprint is a handful
  of writes, not dozens. If you want to test a refusal (a bad enum, a wrong node), do it at most
  once and pick something that cannot land in the record.
- **Never** run `gh`, `git push`, or any command that writes to github.com directly. The only
  way you write is through the service (MCP or HTTP). Never use any credential you find on this
  machine; the only token you may use is one you earn from the service yourself.
- **Do not read or touch any local repositories on this machine**, in particular
  `/Users/mikehiggins/Desktop/repos/*`. You are a stranger who found the website. Your scratch
  directory is
  `/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/f5d93c07-f9bb-4512-afcf-49b132018384/scratchpad/tester/`
  (create it). No Lean toolchain with Mathlib is available locally; the service's own precheck
  is your compiler.
- There is a rate limit on writes; refused writes may count against it. One more reason to
  write carefully.

## What "a contribution" means here

You are not expected to prove anything. The kind of contribution to aim for is a **partial
proof: a skeleton that breaks a statement down into a couple of `sorry` lemma holes with an
assembly that closes the statement from them** — if the network accepts such things (find out
how it calls them and what it requires: which artifact type, which file, what a "witness" or
"annex" is, whether a claim is needed first). Pick a node the network says is open to you.
Read what the site and the service say about claimability before choosing; a node that is not
claimable may still accept some kinds of contribution, or may not — find out and report what
you learn, and choose the path most likely to land a valid record.

If a skeleton is not possible on any node you can reach, make the most meaningful contribution
you can (an informal annex, a postmortem, a proposal) and say why the skeleton was not.

Then **poll until the network has acted on your contribution**: the precheck verdict, the pull
request's gate run, and whatever the site and the service's products show afterwards. Note:
merging is a human's act here; you cannot merge and should not try. Report what a contributor
can see about their pending contribution and what they cannot.

## Also probe, carefully

- Do reads work unauthenticated and writes fail without a bearer? Is the refusal clear?
- Are the MCP tools' descriptions and argument names enough to call them correctly first time?
  Do they match the plain HTTP endpoints and the guide?
- Does the website explain what you need to know as a newcomer, and does it reflect the state
  the service reports?
- Anything a real contributor would trip on: unclear ids, missing schemas, fields the docs name
  differently, error messages that do not say what to fix.

Keep a running log of every write as you make it (tool or endpoint, node/target, ids and URLs
returned, files sent) — the orchestrator uses it to check the record afterwards.

## Report

Write your report to
`/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/f5d93c07-f9bb-4512-afcf-49b132018384/scratchpad/tester-report.md`
with these sections:

1. **Journey** — what you tried, in order, and how far each avenue got. Say which node you
   contributed to and why you chose it.
2. **Bugs** — numbered. For each: what you did (the exact request, tool call or page), what
   you expected, what happened, severity (blocks a contributor / wrong record / confusing /
   cosmetic), and whether it is a bug in the service, the MCP adapter, the site, the guide, or a
   protocol gap. Include response bodies where they matter.
3. **Features wanted** — what you needed and did not find, concretely.
4. **Writes log** — every write: endpoint or tool, node/target, ids returned, `pr_url`, files
   sent, and the last state you observed for it.
5. **Unverified Lean** — every Lean artifact you submitted, with your honest estimate of
   whether it elaborates and why, and what the precheck actually said.

Return the report's contents as your final message as well.
