# Three agents on erdos-68, 2026-10-28 (13:03Z–15:53Z)

Three agents with only the MCP: A (skeleton lead and literature), B (hole prover), C (auditor, second angle, words).
Brief: `BRIEF.md`. Board: `COORDINATION.md`. Logs and final reports: `A.md`, `B.md`, `C.md`. The Lean and record drafts are in `A/`, `B/` and `C/`.
Nobody merged anything by hand.

## Outcome on the record (graph main, 15:50Z)

| Node | Status | What it is |
|---|---|---|
| `erdos-68` | ready | the root, now with two decompositions |
| `erdos-68--h1` | **proved** (#1139, B) | if N!·x ∉ ℤ for arbitrarily large N, then x is irrational |
| `erdos-68--h2` | **proved** (#1140, B) | N!·S = F_N + c with 0 < c ≤ 2/N, where F_N = Σ_{n=2}^N N!/(n!−1) |
| `erdos-68--h3` | ready, **open core** | ∀M ∃N≥M, fract(F_N) < 1 − 2/N. It implies the root, and no reverse implication is known (B's #1150) |
| `erdos-68--h5` | **proved** (#1162, C) | the sharp tail: 1/(N+1) < c < 1/N for N ≥ 4 |
| `erdos-68--h6` | ready | route 2's core. It is **equivalent to the root** (B's #1158, checked by A and C, fast-checked in `B/h6_of_root.lean`) |

The lead's suggested lcm route was false: L_N·tail_N → ∞, because gcd(N!−1, (N−1)!−1) divides N−1. All three agents showed this independently within ten minutes, and it is recorded as approach #1137.
Every gate-written hole was audited before merge and again on main, and none differed from its partial's `have` (C).
Words are on every node: glosses, explainers of all three proofs and both assemblies, literature records, and postmortems.

Ready for the day `--h3` is proved: `B/proof-erdos-68-closing.lean`, the root's closing proof through route 1, which passes the fast check.

## Findings, ranked (V = verified by the lead against the record)

1. **V — A post-merge job spends 8–12 minutes re-deriving a verdict the gate has already signed.**
   - Graph runs 40702171240 (#1139) and 40702928125 (#1140) took 726 s and 504 s in "Re-derive the verdict on the merge commit", then another 292 s and 167 s in "Join what this merge made provable".
   - #1139's attestation landed 20 minutes after its merge, and after #1140's.
   - Meanwhile `--h1` was published as `ready` with `Proof.lean` already in the tree.
   - This is not F-D8's rejected push, so the quiet-window protocol does not cure it (C's F-C4, B's F-B1, which misnames the step).
2. **V — A second skeleton whose hole restates an existing child of the same parent records that hole as `node: null`.**
   - Seen in `graph.json`, `decompositions[1].holes[0]`.
   - `get_submission` reports `became: None` for it, and `list_sufficient_sets` drops route `erdos-68@2`.
   - The site draws the route as "closes nothing", and the hole ids skip `--h4` (A's F-A9 and F-A8, B confirmed).
3. **V — Formalization reviews hold the Apache licence header as their "words"** on erdos-52, -68, -172, -376 and -406, exactly the targets whose `target.yaml` has `informal: null`.
   - The steward sees it on the review page.
   - Seven intent questions are waiting on it, and they all share one text with only an opaque mutant reference (A's F-A4, C's F-C3).
4. A root with `informal: null` has no statement gloss, and `list_words_needed` does not list it (C's F-C5, three targets). C filed one for erdos-68 (#1148).
5. A partial cannot carry its holes' proofs. h1 and h2 were proved against the exact printed types 36 minutes before the holes existed, and they became `proved` 64 minutes later (A, B, C all §4). This is a feature request, the same as feature 3 from the 2026-10-27 run.
6. An auto-filed hole gloss copies the author's prose comment lines, such as "Elementary." and "The open core" (A's F-A5).
7. Explainer lint and outline lag:
   - The lint gives a false `explainer-name-unanchored` warning on a lemma reached by dot notation (B's F-B5, C's F-C6).
   - For about a minute after the outline commit, explainers are refused with `explainer-step-unknown` (B's F-B6).
8. Prior findings still present:
   - "Proved from these holes by" is shown on an open root.
   - `postmortem/v1` has no `model_and_tooling`.
   - `list_submissions` wants `target_id`, not the guide's `target`.
   - A claim is not released when its node's proof merges.
   - The root's doc comment says "Listed, not claimable".
9. Not a defect: one 67 s connect stall, which `time_connect` showed was the laptop's own connection.

## For the steward and the owner

- Route 2's approach line, in the merged partial and immutable, says its core is "strictly weaker". That is true only relative to `--h3`, because `--h6` is equivalent to the root. #1159 and #1161 correct it on the record. Whether to shelve route 2 is the steward's call.
- `B/h6_of_root.lean` shows root → `--h6`. The protocol has no place to record "root implies hole" for a node that is not a variant.

Pacing: about 25–40 minutes of each agent's three hours went on mathematics. The rest was waiting for merge, verdict re-derivation and render.
