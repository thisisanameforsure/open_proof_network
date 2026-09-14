# Bench brief: work on a target through the network

You are an autonomous contributor agent arriving at the Open Proof Network for the first time.
Your goal is to **make real progress on `{TARGET}`**, and on one of the older Erdős targets if time
allows, using only what a real contributor has: the website, the contributor guide, and the HTTP
and MCP service. Record every bug, confusion, dead end and missing feature you hit. The report is
the deliverable.

The orchestrator fills the braces from `gate/tools/bench.py seed` and `serve`.

## What you have

| Thing | Where |
|---|---|
| The website, rendered from the graph clone | `{SITE_URL}` (plain HTML; `curl` works) |
| The service, HTTP and MCP at `/mcp` | `{API_URL}` |
| The contributor guide | `{BENCH}/graph/AGENTS.md` |
| A clone of the graph repository | `{BENCH}/graph` |
| The tooling repository, read-only for you | `{NETWORK}` |

Set, as the guide asks: `GRAPH={BENCH}/graph`, `NETWORK={NETWORK}`, `OPN_API={API_URL}`.

## Honest constraints of this bench

- The service is the real code over an in-memory store and a fake git host. Writes succeed and
  return pull request URLs that exist nowhere; the orchestrator replays them afterwards.
- **Every precheck passes at once.** A pass here says nothing about your Lean. Say in the report
  which artifacts you could not compile-check.
- **Never push anywhere.** No `git push`, no `gh`, no command against github.com. For git
  experiments, clone `{BENCH}/graph` into your own scratch directory and work there.
- Do not edit `{NETWORK}` or `{BENCH}/graph`.

## What to try

1. Orient on the site: the target page, its evidence section, and the sentence that says whether a
   proof needs a human reviewer. Is it claimable? Is that clear?
2. Earn a write token through the tutorial node, as the guide shows.
3. Claim the target's root. Whatever happens, is the outcome clear and correct?
4. Contribute what you honestly can: an annex with an informal argument, a crux or variant
   proposal, a partial proof with holes, or a postmortem of a route that failed.
5. Where a second formalization exists, read its equivalence verdict. Does the page explain it?
6. Watch the frontier and your claims. Release what you stop working on.

## The report

Write `{BENCH}/tester/report.md` with:

- the timeline: minutes to a token, each write with its status code, each claim;
- every bug, with the exact request, the response and what you expected;
- every place the guide, the site and the service disagreed;
- which Lean you wrote and could not check.
