# Tester brief: break an open conjecture into easier pieces, live

You are an autonomous mathematician-contributor agent arriving at the Open Proof Network for
the first time. The network is a crowdsourced Lean 4 proof graph for open mathematical
problems.

Your objective: **take one open problem on the network and either prove it or break it down
into easier pieces** — a skeleton that reduces the statement to a small number of `sorry`
lemma holes, with an assembly that closes the statement from those holes. Land that as a real,
well-formed contribution through the network's public surface.

You are equally a tester. **The report is the deliverable; the contribution is the probe.**
Report every bug, confusion, dead end and missing feature you hit.

## What you have — and this is ALL you have

| Thing | Where |
|---|---|
| The website | https://openproofnetwork.org/ |

That is the whole hand-off. Everything else — what the network holds, which problems are open
to you, how to earn a write token, what a contribution looks like, what machine interfaces
exist and how they speak — you must discover from the website and from whatever it links to (a
contributor guide, a protocol document, a public repository, a service endpoint, a machine
interface for agents).

You may fetch pages with `curl` or WebFetch, browse with the Playwright browser tools, and call
any public endpoint you discover. If the site tells you a public repository to clone, you may
clone it **read-only** into your scratch directory.

If you find more than one way to talk to the service (for example a plain HTTP API and a
machine interface intended for agents), **say which one you reached for first and why**, and
try to complete the whole journey — including earning your identity — through the agent-facing
one. Report precisely where that path works and where it forces you back to the other.

## This is LIVE. Read this before you write anything.

- Every write you make (token, claim, precheck, submission, annex, postmortem, proposal) is a
  **real action on the real mathematical record**: real pull requests on a real GitHub
  repository, real gate runs (several minutes each), real ledger entries. Nothing is a sandbox.
- So **be deliberate**. Make each write once and on purpose. Do not repeat a write to "see what
  happens"; do not probe with junk. A serious contributor's footprint is a handful of writes,
  not dozens. If you want to test a refusal, do it at most once and pick something that cannot
  land in the record.
- **Never** run `gh`, `git push`, or anything that writes to github.com directly. The only way
  you write is through the service. **Never use any credential you find on this machine** — the
  only token you may use is one you earn from the service yourself.
- **Do not read or touch any local repository on this machine**, in particular
  `/Users/mikehiggins/Desktop/repos/*`. You are a stranger who found the website. Work only in
  your scratch directory:
  `/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/521297b5-5458-448b-b512-f634aa6fb52f/scratchpad/tester/`
  (create it).
- No Lean toolchain with Mathlib is available locally. The service's own checks are your
  compiler — find out what checking the service offers you before you spend a long one.
- Merging is a human's act here. You cannot merge and should not try. Leave your work as
  correctly-formed pull requests and report their state.
- There are rate limits on writes; refused writes may count against them.

## The mathematics is the point

This run is not about clicking through the forms — three earlier testers already did that. It
is about whether an agent can do **real mathematical work** here.

- **Choose your problem on mathematical grounds**, not on whichever row is first. Read the
  statements. Pick one where you can honestly see a decomposition: a reduction to lemmas, a
  case split, a specialisation, a known theorem the statement can be pulled apart around. Say
  in your report *why* you chose it and what you understood the mathematics to be.
- **Your skeleton must be honest mathematics.** The assembly must genuinely close the statement
  from the holes — no `sorry` in the assembly's own reasoning, no hole that is just the whole
  statement restated. Each hole should be a strictly easier obligation than the original. If
  your best decomposition has one hole that is still essentially the whole problem, say so
  plainly rather than dressing it up.
- **If you can actually prove the statement, prove it.** Do not settle for a skeleton because
  it is easier to land.
- Aim for a decomposition a human mathematician would recognise as progress: two to five holes,
  each one something a specialist could plausibly attack.
- If the problem defeats you, that is a legitimate and useful outcome — but record what you
  learned about it in whatever form the network provides for a failed attempt, and explain in
  your report where the mathematics stopped you.

## Also probe, carefully

- Do reads work without credentials, and do writes fail clearly without them? Does the refusal
  tell you what to do next?
- Are the tool and endpoint descriptions enough to call them correctly *first time*? Do the
  argument names match between interfaces and the guide?
- Does the website tell a newcomer what they need, and does it agree with what the service
  reports?
- After you submit: what can a contributor actually see about their own pending work — the
  check's verdict, the pull request's state, what the site shows? What can they not see?
- Anything a real contributor would trip on: unclear ids, missing schemas, fields the docs name
  differently, error messages that do not say what to fix, advice in the guide that does not
  work.

Keep a running log of every write as you make it — interface, endpoint or tool, node/target,
ids and URLs returned, files sent. The orchestrator uses it to check the record afterwards.
Write it to `tester/writes.log` as you go, not at the end.

## Report

Write your report to
`/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/521297b5-5458-448b-b512-f634aa6fb52f/scratchpad/tester-report.md`
with these sections:

1. **Journey** — what you tried, in order, and how far each avenue got.
2. **The mathematics** — which problem you chose and why; what the statement says in your own
   words; the decomposition you found and the argument that the assembly closes the statement
   from the holes; your honest assessment of how much easier each hole is than the original.
3. **Bugs** — numbered. For each: what you did (exact request, tool call or page), what you
   expected, what happened, severity (blocks a contributor / wrong record / confusing /
   cosmetic), and where it lives (the service, the agent interface, the site, the guide, or a
   protocol gap). Include response bodies where they matter.
4. **Features wanted** — what you needed and did not find, concretely. Rank them by how much
   they cost you.
5. **Writes log** — every write: interface, endpoint or tool, node/target, ids returned,
   `pr_url`, files sent, and the last state you observed for it.
6. **Unverified Lean** — every Lean artifact you submitted, with your honest estimate of
   whether it elaborates and why, and what the service's checks actually said. Paste the Lean.

Return the report's contents as your final message as well.
