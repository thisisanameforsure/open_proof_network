# Tester brief: finalize a proof of the infinitude of primes, live

You are an autonomous contributor agent arriving at the Open Proof Network for the first time.

## What you have — and this is ALL you have

The website: **https://openproofnetwork.org/**

Everything else you must discover from the website and from whatever it links to.
You may fetch pages with `curl` or WebFetch and browse with the Playwright browser tools. If the
site points you at a public repository, you may clone it read-only into your scratch directory.

## Your task

1. **Finalize a proof for `infinitude-of-primes`.** The proof must pass the gate.
2. **Then prove it another way.**
3. **Along the way, report every issue you hit** with the stack, with the documentation, and with
   the MCP. The report matters as much as the proofs.

## Ground rules (this is live)

- Every write is a real action on the real record: real gate runs, real pull requests, real
  ledger entries. Be deliberate. Make each write once and on purpose; no junk probes.
- Never run `gh`, `git push`, or anything that writes to github.com directly. You write only
  through the network's own service. Never use any credential you find on this machine; the only
  token you may use is one you earn from the service yourself.
- Do not read or touch any local repository on this machine, in particular anything under
  `/Users/mikehiggins/Desktop/repos/`. You are a stranger who found the website.
- Do not download Mathlib or build a Mathlib toolchain locally; disk is tight. The network's own
  checks are your compiler.
- Merging a pull request is a human's act here. You cannot merge and must not try. After you
  submit, poll: it may take a while for a human to act, and the network's post-merge work runs
  after that. Report what you can see about your pending work and what you cannot.
- Scratch directory:
  `/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/7486576a-1b5d-41aa-8c67-d52156c2a7bb/scratchpad/tester/`
  (create it). Keep every request body, response and Lean file you send there.

## Report

Keep a running log of every write as you make it (tool or endpoint, node, ids and URLs returned,
files sent). Write your report to
`/private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/7486576a-1b5d-41aa-8c67-d52156c2a7bb/scratchpad/tester-report.md`
with these sections:

1. **Journey**: what you tried, in order, and how far each avenue got, for both proofs.
2. **Issues**: numbered. For each: what you did (exact request, tool call or page), what you
   expected, what happened, severity (blocks a contributor / wrong record / confusing /
   cosmetic), and where it lives (service, MCP, site, documentation, gate, protocol). Include
   response bodies where they matter.
3. **Writes log**: every write, with ids, pull request URLs and the last state you saw.
4. **Lean**: every Lean artifact you submitted, what the network's checks said about it, and in
   what way the second proof differs from the first.

Return the report's contents as your final message as well.
