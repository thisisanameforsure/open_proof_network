# 2026-10-01: twenty-six agents on the three calibration targets, six rounds

Mike: "I want to use up my credits for the week by sending agents to work on the 3 test problems".
Six rounds of in-process subagents from one cloud session, from about 11:45Z: six agents in each
of the first two rounds, then five, four, three and two. From round 2 each target had one agent
that owned its submissions and helpers that submitted nothing and handed over fast-checked Lean.

The logs, the Lean and the receipts are in `engineering/evidence/testers-2026-10-01/`; its
`README.md` has the assignments, every pull request and the final state, and `bugs.md` the
prioritised list (44 items: 4 P1, 12 P2, 28 P3) with the top ten re-run. Times here are GitHub's.

## What landed on the graph

Thirty-eight pull requests (#323–#360): 35 merged, 3 withdrawn by their authors, none left open.
Seven proofs, five partials, seven witnesses, one new node, fifteen annexes; twelve attestations.

- **erdos-1050 is resolved.** The root's proof (#326) merged at 12:10:57Z, 27 minutes into the
  run, from the text the 2026-09-29 run had left ready. `spec-180d8b72` (#327) and the integrality
  chain followed (#332, #335); `--h2--h1`, recorded by two earlier waves as open mathematics, was
  solved on paper and proved within the first half hour. Twelve of fourteen nodes are proved; the
  other two are a superseded hole and a circular restatement of the root that cannot be closed.
- **erdos-402 is checked for every size from 10 to 200014, with one open leaf.** Three rungs of
  "no prime p ≥ n/k divides an element" (#331, #344) turned out to be a ladder the literature
  never climbs. The prime-window criterion replaced it (#348), then a generalised criterion with no
  residual sizes (#351), split into three scoped holes (#353): 10–228 and 229–200014 are proved
  (#359, #360), and n > 200014 is open and is not a finite check. No node states the finite range
  as one theorem; every node above the leaf is still `ready`.
- **erdos-69 gained Mertens' second theorem** as a proved node (`spec-7d098d5c`, #339, #343,
  written from Mathlib alone) and four annexes. A clean-room construction (18 definitions), a
  root assembly, and proofs of h1, h2, h3, h4a, h4b, h4c, h4d and h4g over it are fast-checked and
  unsent: they need definitions on the target, which the pinned gate refuses and F11-T13 (network
  draft PR #26) allows. h4e and h4f are open and unreviewed.

## Verified findings

Re-run on 2026-10-01 from 19:45Z against the live service (read-only calls and the anonymous fast
check), the record at `1d98dcfb`, the site and GitHub's API. C = confirmed, and how.

1. **Hazards mode of the fast check is broken for every statement** (C, live, log
   `01M3WG8X7G4NC1AB75SWJES52Y`): `Unknown identifier Lean.Elab.IO.processCommands` in the program
   the service appends. The failing lines are F02-T9's last commit, merged a minute before the
   run; its Lean tier was green locally and nobody called the deployed route. Cost on the day: #337
   opened with an inconclusive pre-flight, refused by the gate, withdrawn, re-proposed.
2. **Nothing beneath a node can import a definition admitted later or cite a proved node it does
   not already depend on** (C, live: one added `import Defs.Fact` is `imports-differ`; holes are
   written `deps: []`). Admitting erdos-69's definitions does not make its skeleton submittable on
   a root stated over Mathlib alone; the agents built a bridge node and a `resolves` relation.
3. **No mode adds a definition to an existing target** (C at the pin by `classify`). Fixed as
   F11-T13 on this branch; `classify` at the branch head accepts the same one-file diff.
4. **The resolved target's summary counts nodes its proof does not use** (C): `digestion.closure`
   is 6, the proofs name 3, and the page draws the declared deps as "the statements its proof
   depends on".
5. **The queue** (C from GitHub): no append batch formed all day although F07-T45 is on the
   graph's `main` (35 merges, 35 post-merge commits, four adjacent pairs of green annexes merged
   apart); 116 of 201 `merge` runs cancelled; opened-to-merged median 54 minutes for the 19 pull
   requests opened before 14:20Z, under 8 with the queue empty.
6. **A merged pull request reads as open and `stale: false`** for up to three minutes (cause C in
   code: the 180-second cache F07-T47 added that morning). Every merge time the agents logged
   from that route is one to five minutes late, and their "green to merged in under a minute" is
   not a measurement.
7. **Verify refuses a correct direct proof** when the Context restates a hole (C, live).
8. **The guide the agents read is a re-pin behind**: 63 lines differ, among them the token body
   and the paragraph that says a proof can be prechecked against a green proposal. One agent
   waited 74 minutes for a merge it did not need.
9. **Not reproduced**: that `spec-180d8b72` left the frontier while unproved (the committed
   frontier at `gate: #326 pass` lists it). **Wrong**: that the frontier surfaces erdos-69's
   circular h4 (it lists the root alone). Eleven such corrections are in `bugs.md` E.
10. **X, not the network's**: the sandbox clock ran slow; paper hosts were blocked, so neither
    Balasubramanian–Soundararajan nor section 5 of Tao–Teräväinen was read by anyone; the brief
    gave the old `/targets/` URL and seven agents filed it as a bug.

## The owner's decisions today

- **"I want the major fixes from today"**: said during the run. `bugs.md` A is the list to build
  from; A2 is built on this branch.
- **Definitions on an existing target**: "Yes we should allow defs. Unless there is a compelling
  reason not to..." The curator agent found none against definitions as such, one caveat about
  these (a defs file is immutable and has no revision route), and that the gate had no mode for
  it. Built as F11-T13 (R15, Q35).
- **His factorisation idea for erdos-402** (if the bound cannot fail for p and for q, it cannot
  fail for pq): tested in rounds 3 and 4. `402-R3-b/FINDING.md`: no reading gives a reduction;
  the one true multiplicative fact runs the other way (counterexamples at m and k multiply to one
  at mk). `402-R4-b/FINDING.md`: no, in both readings, for one reason: across a split the two
  bounds combine as a maximum, never a product (smallest example {1,2,3}), and the one known
  induction, counting distinct quotients, is false once an exponent 2 appears ({2,3,4,6,9,12,18},
  already in Marica–Schönheim 1969). Not proved impossible. What the question did produce: the
  literature search it was paired with found that the real proof uses a prime just below 2n, and
  that became the criterion the finite range rests on.

## Waiting on him

- **erdos-402's last leaf** (n > 200014): park it as analytic, or start formalising the large-n
  proof with explicit prime-counting bounds Mathlib lacks. A cheap, honest extension exists (by
  402-R6-b's measurement one declaration covers 200015 to 3,000,000) and moves nothing at the root.
- **erdos-69**: once PR #26 is merged and the target re-pinned, admit `69-R4-b/Defs-v2.lean` (the
  curator's local branch holds v1, whose header comment is false for odd M); accept the bridge
  node and `resolves` route, or rule on B1; choose the relaxed h4e; get h4e and h4f read by a
  number theorist before anyone works on them; ask the outside proof's author for a licence.
- **The six design gaps** (`bugs.md` B1–B6): what a hole may import and cite; witnesses carried
  by a partial; helper declarations under the heartbeat cap; holes that cannot be witnessed; a
  marker for circular, superseded-route and dead holes, including erdos-1050's after resolution;
  queue order and cost.
- **Third-party Lean** (B8): near-complete outside formalisations exist for 402 and 69 with no
  licence file; the agents ported nothing and one copy was kept out of the commit.
- **Whether the two negative findings on his idea go on the record** as an annex on erdos-402.
- **A re-pin**, which carries the guide, decisions v3.23 and F07-T48 to the graph; hazards mode
  wants fixing first.

## Things worth keeping

- **Verify before the permanent record, with a different agent and different code.** 402-R5-a
  re-derived 402-R4-c's criterion (axioms printed, hypotheses read against the live node, its own
  sieve) and 402-R6-a did the same for 402-R5-b and 402-R6-b. Nothing was wrong. What it settled
  was a 7-versus-43 discrepancy between two agents' exception counts: both right, for the
  one-prime and the two-prime criterion, and the annex that corrected the record came out of it.
- **Encoding decided the shape of the record.** Eighteen `norm_num` certificate declarations
  (about 2,000 heartbeats a prime) would have been eighteen holes, each a witness and a proof.
  `decide +kernel` over a list literal, primality as a gcd with a primorial (about 14 a prime),
  made them two, and passes the gate with the standard axioms.
- **The scoped-hole layout**: each hole in its own bullet of one `refine ⟨?_, …⟩` is extracted
  closed over its own binders; a flat hole after others inherits them all and cannot be
  witnessed. Found by a deliberate extraction test before the real skeleton was sent.
- **A helper that submits nothing.** One owner of submissions per target per round, helpers
  delivering checked Lean and a READY section: no two agents sent the same thing all day, and
  from round 3 the helpers used no token, because the fast check is anonymous.
- **The withdrawn #350.** A command that tailed the helper's log and submitted in one go sent a
  20-hole skeleton the log had just made doubtful; it was withdrawn 37 seconds later and nothing
  reached the record. Read, then submit, as two steps; the withdraw route is what made the slip
  cheap.
- **Clean-room pays twice.** Told not to open the unlicensed outside proof, 402-R4-c derived the
  criterion itself and found the second prime unnecessary; 69-R2-a wrote Mertens from Mathlib
  and needed no third-party notice.
- **A script that prints and asserts nothing verifies nothing.** "Verified for M ≤ 4" was read
  off by eye and was false for odd M; the kernel found it when the next agent proved the lemma.
- **Call the deployed route after a deploy** (2026-09-21 again): hazards mode was green in the
  Lean tier and broken live from the first minute of the run.
- **Take times from the host, not from the service's view of it**, and not from the sandbox clock.
