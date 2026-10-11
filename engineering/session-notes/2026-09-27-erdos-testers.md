# 2026-09-27: six agents on the three Erdős calibration targets, and the fixes on 2026-09-29

Mike: "send out 6 agents to work on the 3 erdos problems for 1 hrs. Have them also note any bugs they
encounter and features they request." There were two agents per target (`erdos-69`, `erdos-402`,
`erdos-1050`), one MCP-first and one HTTP-first. Each got only its problem page URL and ran 19:49–20:43Z.

Unlike on 09-24, they ran as background subagents of the lead session, not as separate cloud sessions.
That meant:

- no per-tester draft pull requests paying the Lean tier;
- each report came straight back to the lead;
- each tester logged to a scratch file as it went.

The logs are in `engineering/evidence/testers-2026-09-27/`. Before copying them, the lead scanned them for
bearer tokens, nonces and long secrets; none were found.

Three HTTP agents stopped early (20:24–20:29), each saying the queue left it nothing to do. The
harness cut one short at 20:24 even after it was sent back once.

## What landed on the graph

Twenty pull requests were opened (#205–#224), all of them gate-green. Seven had merged by 20:44
(#205–#211), about one every 6–7 minutes. At 20:44 there were 13 green and waiting.

- **erdos-1050**
  - The witnesses for `--h1-v2--h2` (`True := trivial`, blocked for three days) and `--h1-v2--h3` merged,
    so both holes went from blocked to ready.
  - A full proof of `spec-f2b55478` (the coefficient identity, by Lagrange partial fractions) is green
    as #222.
  - A new crux `spec-440db0f9` (#215) was proposed, with a complete proof checked by AXLE and not submitted.
  - Two annexes (#214, #223) name the missing piece: a 2-adic bound on the Padé numerators. The naive lcm
    denominator bound fails from n = 5.
- **erdos-402**
  - The size-6, 7 and 8 cases were proved (#216–#218, green).
  - New size-9, 10, 16 and 18 variants were proposed (#211 merged; #212, #220 and #221 waiting).
  - A SAT-data annex (#219) was added.
  - Nothing touched `--h3-v2`, the Balasubramanian–Soundararajan core.
  - Proofs for sizes 9, 10, 16 and 18 are written. Owner's ruling: they are left unsubmitted, since they
    do not advance the conjecture.
- **erdos-69**
  - An annex (#208) and a postmortem (#209) were merged, showing that the power-of-two-denominator
    shortcut fails.
  - A worked "prime indicator" variant (#210) merged, with its proof green as #224, and an approach
    record was filed (#213).
  - No progress on the root, correctly: everything that remains is Tao–Teräväinen.

## Verified findings

C means confirmed by the lead, and says how. X means not the network's.

1. **The queue sets the pace** (all six agents; C from the counts above).
   - An append that builds nothing waited 18–29 minutes.
   - A variant plus its proof needed two turns of the queue, so four finished proofs could not be
     submitted within the hour.
   - The queue survey showed that the serialiser is the ~3-minute post-merge job every merge runs. The
     actor holds for it since F07-T33 (the six lost bot commits). It is not the up-to-date rebuild, which
     costs an append only its own re-gate.
2. **`/check` without `target_id`** gave `target-id-invalid` for a missing field (C, live and at
   `checks.py:132`). MCP `get_node` refused `target_id` while `check_lean` required it. Fixed as
   F13-T24.
3. **Hazards mode ignored acknowledgements** (C, live on erdos-69's `div-zero`). Fixed as F13-T24.
4. **A claim receipt said nothing about open submissions** (C, `claims.py:71`). Fixed as F05-T16. The
   "claim only if free" flag was declined under F05-Q1 and D-25.
5. **The MCP never named the tutorial node** (C). Fixed as F09-T14.
6. **Small ones:**
   - the WitnessType doc sentence (C), fixed as F01-T6;
   - the `POST /tokens` body shape (C), fixed as F10-T15;
   - "anyone may do it" on a hole whose witness costs an earlier hole's proof (C, site text). Not built:
     no product records which earlier holes a hole inherits. That needs an `inherits` field from the
     extractor through the post-merge job into META (F04, open).
7. **Plausible, not verified:** root annex 84315a5 on erdos-69 may credit the prime-sum irrationality
   to Erdős 1948. The testers' proxy blocked erdosproblems.com. An annex has no correction route.
8. **X:** connection resets came from the sandbox proxy. The stale deps in the root META are by design
   (F08-T10, derive and never rewrite). The products lagging a merge by about 3 minutes, with
   `products-pending`, is also by design.

## The owner's rulings (2026-09-29)

- **Precheck against a green pending proposal:** yes. Built as F06-T10 and Q15, recorded in F08-Q23.
- **Let append-only pull requests skip the strict up-to-date rebuild:** yes in principle. It lives in
  the graph repository (`merge.yml`, `gate.yml`, the ruleset), which this session could not attach.
  - The lead's reading: the rebuild saving is small. The lever that matters is merging a batch of green
    appends and letting one post-merge job cover them.
  - That touches exactly the code where F07-T33's lost-commit defect lived, so it wants a red-first
    replay of that incident.
- **The small fixes:** all agreed; built as above.
- **The four unsubmitted erdos-402 proofs:** leave them.
- **Open questions put to the owner, still waiting on his answer:**
  - should an erdos-69 "spent routes" block go into the root's bundle? Today the circular note is on the
    site only, and `circular_below` is not a product field (F08-Q32);
  - direction for provers: a signed target brief, plus enforceable closed routes (for example "no new
    partial variants"). Refuse or warn, and who writes it. This is a D-25 amendment, because D-25 says
    "never directed allocation".

## Things worth keeping

- **Subagents in one session beat six cloud sessions for a tester run.** They share the lead's network
  policy, which a one-command curl probe confirms before launch. They open no pull requests of their own,
  and they hand their reports straight to the lead. The harness can cut one off early, so the log file
  each keeps as it goes is still what survives.
- **Price a lever before promising it.** "Skip the up-to-date rebuild for appends" sounded like the
  throughput fix. Reading the actor showed the rebuild is seconds for an append, and the three minutes
  go to the post-merge job that T33 made everything wait for.
- **Nothing on the record can say "this kind of work does not help".** `attack_routes` in `target.yaml`
  is read by no code. An abandoned node's cause is not published. D-25 forbids ranking. Two agents
  independently spent an hour proving erdos-402 size cases that the owner judged worthless.
