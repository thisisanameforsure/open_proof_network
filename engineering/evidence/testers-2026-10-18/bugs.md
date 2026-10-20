# Findings, testers 2026-10-18 (lead's consolidation, verified where marked)

## Outcome (gh pr view at 20:22Z)
No node proved outright. Five partials, every one an honest reduction, and seven postmortems, all opened through the
MCP with no human.

| PR | Kind | Node | Agent | State 20:22Z |
|---|---|---|---|---|
| #757 | partial: gcd=k case closed, hole gcd<k | `--h2--h1--h4--h1--h2` | B | merged 19:40 |
| #758 | postmortem | same | B | merged 19:41 |
| #759 | partial: θ-PNT from ψ-PNT (Mathlib ψ−θ bound) | `--h3--h3--h1--h1` | E | merged 19:47 |
| #760 | partial: n prime / n = g·q | `--h2--h1--h1--h1--h1` | A | merged 20:01 |
| #761 | partial: 5-sieve, p=5 branch closed | `--h3--h1--h2--h2--h2` | D | merged 20:15 |
| #762 | partial: n ≥ k² closed, hole n < k² | `--h3--h2--h1` | C | open, green |
| #763 | partial: m one prime / two primes | `--h2--h1--h1--h1--h2` | A | open |
| #770 | partial: ψ-PNT from Wiener–Ikehara + ζ continuation | `--h3--h3--h1--h1--h1` | E | open |
| #764–#769 | postmortems | D, A×2, E×2, C | — | open |

Mathematical notes worth keeping: B's exact search finds (62,6) the only (n,k) with k ≤ 1500 meeting
`--h2--h1--h4--h1--h2--h1`; Aristotle reduced C's `h_lt` to Hoheisel (written out in #769); pinned Mathlib has ψ, θ,
|ψ−θ| ≤ 2√x log x, ζ ≠ 0 on Re s ≥ 1, the residue at 1 and L(Λ,s) = −ζ′/ζ, but neither PNT nor Wiener–Ikehara (E).

## Prioritised findings

### P1 — One lane per target makes a one-target hour a queue, and appends starve behind building PRs (A, C, D, E). VERIFIED.
Merge actor log (runs 39162068530, 39162512977): erdos-1094's lane is strictly FIFO; it held for #761's running gate
12 polls, then for #762 "the host is still computing whether it conflicts" 9 polls, then updated #762 (gate re-runs).
Building partials merged at 19:40, 19:47, 20:01, 20:15: one per ~10–14 min. Postmortems #764–#769 (appends, no build)
were created 19:46–20:07 and were all still open at 20:22, because `merge.yml` ends an append batch at the first building
PR (by design, F07-T45/T56). Add the post-merge render (#757 merged 19:40:38, bot commit 19:48:47) and an agent gets at
most one level per hour. Fix options, owner's call: let appends in a lane merge past a building PR that is not itself
mergeable this run (an append is one content-named file, earns no attestation); or shorten the "host computing" hold.

### P2 — Stacked partials: let a precheck/submission target a pending PR's `expected_node_id` (C, D independently). FEATURE.
The direct remedy for P1's consequence: both agents had the next level drafted (D/sub2/partial.lean fast-checks; C had
Aristotle's Hoheisel reduction) and could not file it. Needs a design (precheck against the PR's head plus its render).

### P3 — The guide's own "own scope" example is refused `partial-unlabelled` (A, E). VERIFIED.
`AGENTS.md` lines 1323–1335 (graph origin/main) show `· have h₁ : A n := by sorry` with no `-- label:`/`-- claim:` lines,
and an agent who adds them on the bullet line (`· -- label: …`) is refused: E/partial-unlabelled-response.json lists both
holes, lines 23 and 33. Fix: the example carries the label and claim lines on their own lines under the bullet; optionally
accept a comment block that begins on the bullet line. Cheap; every multi-hole partial meets it.

### P4 — Carrying a hole's witness costs a second full precheck (B, D, E). VERIFIED by timings in logs (~4 min each).
The first precheck prints `expected_witness`; the witness (almost always `True` or `∃ c>0`) then needs a full re-run.
Request: accept trivial witnesses by default, or a witness-only re-check.

### P5 — `check_lean` does not check the partial's comment rules (A, D). FEATURE.
label/claim/approach/licence errors surface only at precheck (minutes) instead of the fast check (seconds). D's claim that
each precheck reports only one kind of error is NOT shown (D's receipt is the later 202; E's refusal lists every hole).

### P6 — Aristotle returned an unchanged file while its summary says the proof was written (C). VERIFIED, upstream.
C/hlt/{proj,out,dl2}/Problem.lean all sha `a4bdb83e…`; ARISTOTLE_SUMMARY.md says "Problem.lean now contains a complete
proof … except for one sorry … committed and pushed". A fresh download gave the same file. opn-prove recorded
`answered: false`, which is correct. 24 min of work lost. Request: opn-prove warns when the summary claims edits and the
file is byte-identical, and retries the download; report to Harmonic.

### P7 — Aristotle's concurrency is effectively 1 for this account, not ~4 (C, D). PLAUSIBLE.
C/r/ar-refused-1925.json `refused: project-limit` while `aristotle list --status RUNNING` (C/r/ar-list-1927.txt) shows
one project. Caveat: the list paginates and filters on RUNNING, so a queued project elsewhere is not excluded. The lead's
brief said ~4 (from the 10-15 memory); that number is now corrected. Request: opn-prove prints slot status.

### P8 — Smaller requests (one agent each, not verified)
- `claim-form` refusal should name trailing text after the closing `$` (B; receipt overwritten).
- `list_frontier` could carry each node's statement (A).
- `GET /submissions/<id>` could say when a hole's child is addressable / render queue position (B, E): measured lag 8–9 min.

## Not network defects
- TLS-handshake and connect timeouts on the MCP (A, B, C, D, E), each followed by a fast curl (0.16 s connect): the
  laptop's known path to API Gateway (log 2026-09-21).
- A parent stays `ready` after its partial merges (B): by design since F27 (a node may be proved directly or through its
  decomposition). A reader-facing hint at most.
