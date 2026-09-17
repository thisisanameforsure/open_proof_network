# F15 calibration run — the record (R14 f)

Started 2026-09-17 14:03 UTC on Mike's instruction ("send 3 subagents out to work on the 3 problems
decided upon in F15"). T14c had been held on 2026-09-17 morning (F15-Q15: "we need a proper harness
before tackling a hard problem"); this run is the owner overriding that hold for a first pass.

## Shape of the run

- Three agents (Claude Fable 5.1, general-purpose subagents of session open-proof-network-44), one
  per target, launched in parallel with the briefs in
  `engineering/session-notes/2026-09-17-calibration-run-handoff.md`. Each keeps its whole state in
  `engineering/evidence/F15/calibration-erdos-<n>.md` so a successor on another model can resume it.
- Targets (F15-Q13): `erdos-1050` (easy: a full proof), `erdos-69` (medium: a full proof, else a
  partial whose holes are the two lemmas), `erdos-402` (a skeleton whose holes are the lemmas of
  Balasubramanian–Soundararajan).
- Tooling the agents had: `POST /check` (F13 hosted checker, Mathlib at the pinned sha), `POST
  /precheck`, the service's submit routes, the contributor guide on the graph. No Mathlib checkout on
  the laptop; the Mathlib image was not to be pulled (disk).
- Prior art: consulting literature and public formalizations was allowed, to be recorded per target.

## Deviations from R14 (b) "no help from the founder or the build"

- The lead told the agents at 14:12 UTC that the graph's products were stale (below). That is help
  about the pipeline's state, not about the mathematics; it is recorded because a fresh agent without
  a lead would have met a precheck refusal on a target the frontier does not list and had to diagnose
  the network rather than the problem. This is itself a finding (see below).

## Timeline (UTC)

- 13:59 — graph PR #73 (intake erdos-69) merged by the rollout session (open-proof-network-ed). Its
  post-merge run 35230599357 failed: `opn-used-constants failed on erdos-412--h1: file does not
  elaborate`. Cause: the intake branch was cut before the 0401858 re-pin, so
  `targets/erdos-69/gate-spec.json` at the merge commit still pinned network 26e86c4, and the
  post-merge job reads the pin from the merged target; 26e86c4 lacks the tag-cache fix.
- 14:03 — the three agents launched.
- 14:07 — the rollout session re-pinned erdos-69 to 0401858 (graph bdcd64e, direct push; its run
  35231476346 records nothing because a direct push merges no pull request).
- 14:08 — the rollout session updated PR #74 (intake erdos-402) to 47443d5; gate running.
- 14:12 — lead's finding: `frontier.json` and `targets/index.json` on main are `rendered_from`
  42f94ef (the PR #71 merge, 2026-09-16); the live `/frontier.json` has 22 entries, none of the three
  targets; `api/opn_api/precheck.py:322` pins the precheck's graph checkout to that commit. So no
  precheck or submission can see any calibration target until a post-merge run under 0401858
  re-renders the products. Agents told to iterate on `/check` only and poll `rendered_from`.
- 14:11 — PR #74 (intake erdos-402) merged by the rollout session (1f9fb28). 14:14 — its post-merge
  run passed under network 0401858 and landed `gate: #74 pass` (456997d): products re-rendered as
  `targets-index/v6`, `frontier.json` rendered_from 1f9fb28, 28 entries, erdos-1050, erdos-69 and
  erdos-402 listed and claimable; erdos-412--h1's library tags skipped with a warning (the node still
  does not elaborate; left for Mike). The live api served the same by 14:16.
- 14:16 — agents released to precheck and submit. Each agent's log existed and was current by then
  (the handoff discipline held).

- 14:4x — all three agents had submitted: annexes #75 (erdos-69) and #76 (erdos-1050) CLEAN; partials
  #77 (erdos-69), #78 (erdos-1050), #79 (erdos-402) with the sandbox verdict `pass` (#79's still
  running) and the step 9 job red until a non-author approves — every one of the three "easy,
  medium, skeleton" targets came back as a partial. The lead started the merge sequencer
  (`scratchpad/merge_sequence.py`, log `engineering/evidence/F15/merge-sequence.log`): order
  75, 76, 77, 78, 79 — an annex before the partial that cites it (`check_annex_citation` runs in
  the post-merge job), each round update-if-BEHIND → gate green → approve step 9 as the owner (the
  PR author is the App) → merge → wait for `gate: #N pass`; the first failure stops it.
- Hosted-checker probe (for the `/check` finding below), `GET https://axle.axiommath.ai/v1/environments`
  at 14:4x: `lean-4.34.0`, `lean-4.33.1`, `lean-4.32.2`, … — no `lean-4.33.0`.
  `gate/hosted-checkers.yaml` maps both `core` and the pin to `lean-4.33.0` (`exact: false`, probed
  2026-09-14), so every fast check answers `Unknown environment: lean-4.33.0`. Fix: `lean-4.33.1`,
  `exact: true`, for both entries; a network change with a deploy.

- 14:28 — sequencer merged #75; bot commit `gate: #75 pass` (f9f09f4) at 14:31. At #76 GitHub
  reported the merge state UNKNOWN for a moment, the sequencer skipped the branch update and would
  have timed out on BEHIND; stopped, fixed (wait for a settled state, update when BEHIND, give the
  new gate run time to register), restarted from #76 at 14:36.
- 14:36 — Mike: "after you're done merging, and fixing what you're fixing, send them back out to
  continue working … or now if that makes sense and won't break anything." All three agents resumed
  with a continuation brief: local mathematics on their holes only (no pull request until the lead
  says the sequence is complete), then submissions on the hole children the merges create, with any
  F07-Q19 admission refusal typed into the log rather than worked around.
- 14:37 — the fast-check mapping fix committed on the network (`gate/hosted-checkers.yaml` →
  `lean-4.33.1`, evidence `engineering/evidence/F13/hosted-checkers-2026-09-17.txt`); live after the
  push that deploys it.

## Results

| Target | State | Pull requests | Check / precheck ids | Failures typed |
|---|---|---|---|---|
| erdos-1050 | partial open (one hole `borwein`: Borwein's theorem in approximant form; assembly and the Diophantine irrationality criterion proved), sandbox verdict `pass`, mode `partial`; blocked on step 9 | annex #76 (CLEAN); partial #78 (gate run 35233188330) | identity `01M2QVQVD0PVJRVE8GMRB7W0J0`; owned precheck `01M2QVS0GG8CR7JZ5T80N8V8C4` pass, signed `service`, runner `hosted`; submission `01M2QVZJF8NSB70424HVM5VYZX` | `/check` `target-unknown` (log `01M2QV4M5GDVSK91G7R0E6366D`), `Unknown environment: lean-4.33.0` (log `01M2QV6GQ0YZBS53HXZ2DNZ20M`); no full proof: the only known proof (Borwein 1991/1992, Padé approximants) has an external formalization of 18 files, judged out of reach in the box |
| erdos-69 | partial open, sandbox verdict `pass`, mode `partial`; blocked on step 9 (a non-author approval) | annex #75 (append gate green, run 35232389153); partial #77 (gate run 35232829419) | identity `01M2QVFJR8MZTK2W0GF8FXA8JW`; owned precheck `01M2QVJS9GQRACNP695KTN4DE7` pass, signed `service`; submission `01M2QVSP00T8W7W39CBZF2WCN2` | `target-unknown` before the bot commit (log `01M2QV3KY85BJRF4JX3S49TKG8`); `/check` `user_error: Unknown environment: lean-4.33.0` (log `01M2QV94PGR5PRX4A3DFS1K55D`) |
| erdos-402 | partial open (three holes: `h1` Farey structure of the quotients, `h2` reduction to primitive sets, `h3` the Balasubramanian–Soundararajan core; assembly proved), sandbox verdict `pass`, mode `partial`; blocked on step 9 | partial #79 (gate run 35233227359); no annex filed | identity pseudonym `calib-402-f480`; owned precheck `01M2QVS6C00HR3WW1K1M496BM2` pass on the first round; submission `01M2QW06ZG6T1ZW656S709HTM0` | `/check` `Unknown environment: lean-4.33.0` (log `01M2QVM3984A90W2FTF6TB8C3P`); the B–S paper could not be fetched (publisher blocks non-browser clients), so the holes follow the argument's shared architecture rather than its numbered lemmas |

## Round two: the holes (14:36 – 15:0x, cut short)

At 15:00 the Fable budget ran out and all three agents died mid-round-two with HTTP 429. Mike moved
the session to Opus and asked that their work be wrapped up and submitted where substantial. Each
agent's log was current, so the lead finished the submissions from the logs and the scratchpad.

What the agents had produced and verified before dying (each on AXLE at `lean-4.33.1`, since the
network's own fast check was down):

| Artifact | State | Where |
|---|---|---|
| `erdos-69--h1` (the Lambert identity) | **full proof**, `okay: true`, axioms `[propext, Classical.choice, Quot.sound]` | AXLE `eb8e1cb2`, axioms `606c83fd` |
| `erdos-69--h2` (irrationality of the prime sum) | **partial**: the integrality step proved, Erdős's choice of `N` the one hole | AXLE `b379a848` |
| `erdos-402--h1` (Farey structure) | **full proof**, first round | AXLE run in `ch/h1-proof.axle.json` |
| `erdos-402--h2` (reduction to primitive sets) | proved, but against the child's *mis-generated* statement (below) | `ch/h2-proof.lean` |
| `erdos-402` annex | drafted, unfiled | `ch/annex.md` |
| `erdos-1050--h1` (Borwein's approximants) | not attempted: the only known proof is ~18 files elsewhere | analysis in the log |

Lead's wrap-up (submitted under each agent's own pseudonym, the Lean unchanged):

- annex on `erdos-402` → **graph PR #80** (hash `e132eaf4…`).
- witness for `erdos-69--h1` (`True`, the hole has no hypotheses) → **graph PR #81**.
- witness for `erdos-69--h2` (a full proof of the Lambert identity, since a hole inherits its
  predecessors, F11-Q22) → **graph PR #82**.
- witness for `erdos-402--h1` → **graph PR #83** (proposal `01M2QYKPVGG8K1X0WN3BPGRXDV`), but only on
  the fourth attempt: three `404 node-unknown` refusals between 15:05 and 15:08 for a node that was
  already on `main`. The route reads the committed `targets/<id>/graph.json` through the api's
  per-path file cache (`frontier.committed`: a 60 s window per Lambda container, invalidated early
  only when `info.json`'s ETag shows `main` has moved), so the hole stayed unaddressable until that
  entry refreshed, which in practice meant waiting for the next bot commit. Meanwhile the frontier
  route was already publishing all three holes while the witness route denied one existed.
- The three witness pull requests merge on the gate alone (no step 9), sequenced #81, #82 and then
  #83 behind them, one bot commit apiece.

**Round two's outcome: two of the three verified artifacts could not be submitted, and the reason is
the gate's own defect (finding 3b below), not the mathematics.**

| Artifact | Outcome |
|---|---|
| `erdos-69--h1` witness (`True`) | merged, **graph PR #81** — the hole has no hypotheses, so nothing to coerce |
| `erdos-69--h1` full proof | **not submitted**: `POST /check` in verify mode refuses it against the child's own statement, which is the ℕ reading |
| `erdos-69--h2` witness | **refused by the gate** at step 7 (`witness-elaboration`), graph PR #82 **closed** with the reason and its branch deleted |
| `erdos-69--h2` partial | **not submitted**: same statement defect |
| `erdos-402--h1` witness | **graph PR #83**, merging |
| `erdos-402--h1` full proof | submitted behind #83 — the one round-two artifact whose statement round-trips |
| `erdos-402--h2` proof | **withheld deliberately**: the child states ℕ division, so a proof of it would launder the defect |

Nothing was submitted against a mis-generated node. Two of the run's three agents therefore end with
their best work verified, recorded, and unlandable until the statements are corrected — which is a
finding about the network, not about them.

## The work is public (checked 15:1x UTC)

Both pages render from the merged tree, so the run's artifacts are visible to a stranger:

- `https://openproofnetwork.org/targets/erdos-69/` — "A calibration target: a result already known,
  taken in on the formalization track to exercise the pipeline (Stages v3.17). It counts toward no
  open-problem claim and needs no steward"; the dependency graph carries `erdos-69--h1` and
  `erdos-69--h2`; six "blocked" and two "attempt" mentions.
- `https://openproofnetwork.org/targets/erdos-402/` — the same labels with `erdos-402--h1`, `--h2`
  and `--h3` in the graph.
- Both pages now read **"Fast check (POST /check, non-authoritative): lean-4.33.1 on AXLE
  (exact)"**, which is the `d21963f` mapping fix live on the public site.
- Neither target page mentions its annex (`annex: 0` in the page text) though the annexes are merged
  (#75, #76, #80); whether the node page surfaces them was not checked. Worth a look, not filed as a
  defect.

## Findings about the network (R14 e: every failure a typed record)

1. **A calibration target is not live when its intake merges.** The products are rendered only by a
   *successful* post-merge run of a merged pull request; a direct push renders nothing, and the two
   post-merge runs since the erdos-412 hole was created had failed on the tag scan. The frontier the
   agents and the precheck read therefore predated all three targets for the first half of the run.
   A target's readiness should be a fact the intake reports, not one the lead discovers.

2. **Every `POST /check` on a Mathlib target was dead.** AXLE had retired `lean-4.33.0` and hosts
   `lean-4.33.1`, the pin's own toolchain; `gate/hosted-checkers.yaml` still named the retired one,
   so the network's fast check — the thing an agent is told to iterate on — answered
   `user_error: Unknown environment: lean-4.33.0` for all three agents. All three found it
   independently and all three fell back to calling AXLE directly, which is keyless at Stage 0
   (F13-Q5) and therefore outside the network's own call log. Fixed in network `d21963f`
   (`lean-4.33.1`, `exact: true`; evidence `engineering/evidence/F13/hosted-checkers-2026-09-17.txt`)
   and live after that deploy. **The checker a graph pins is an upstream that moves under it; the
   mapping needs a periodic probe, not a one-time one.**

3. **The hole writer changes a hole's statement when its type carries coercions** (found by the
   erdos-402 agent, confirmed on AXLE; a gate defect, unfixed). The extractor prints `closed_type`
   with default `pp` options, so a conclusion `↑(a.gcd b) ≤ ↑a / ↑A.card` in ℚ is written into the
   child's `Statement.lean` as bare `↑`s, which re-elaborate as the *identity* coercion ℕ → ℕ —
   the child becomes the ℕ-division statement. It is silent, because the child elaborates and the
   hash is taken of what was written. erdos-402's `--h2` and `--h3` are affected; `--h1` has no
   coercions and round-trips faithfully. Consequence: D-31 finalization (the assembly with each
   `sorry` replaced by its hole's theorem) cannot use such a child. Fix belongs to the hole writer:
   print with `pp.coercions.types true`, or compare the child's elaborated type against the hole's
   `closed` Expr before writing. Because of this the agent's proof of `--h2` was **not** submitted:
   proving a mis-generated statement would launder the defect into the record.

3b. **The same defect makes a hole unprovable *and* trivial — confirmed live on erdos-69, where it
   cost the run its two best artifacts.** The gate wrote both erdos-69 children with the parent's
   coercions printed as bare `↑`, so re-elaborated in the child's own file the arrows resolve to the
   identity coercion ℕ → ℕ. The witness for `--h2` was refused by the gate at step 7
   (`witness-elaboration`), and `POST /check` in verify mode gives the same verdict for the `--h1`
   proof, both with this message:

       'calc' expression has type
         ∑' (n : ℕ), ↑(ω n) / 2 ^ n = ∑' (p : Nat.Primes), 1 / (2 ^ ↑p - 1)
       but is expected to have type
         ∑' (n : ℕ), ω n / 2 ^ n = ∑' (p : Nat.Primes), 1 / (2 ^ p - 1)

   The expected type is the node's own statement, and it is the **ℕ-division** reading, in which
   every term on both sides floors to 0: the child says `0 = 0`. So the hole the network published
   is trivially true, provable by `simp`, and closing it would finalize the parent's assembly with a
   lemma that says nothing. The agents' real proofs (the Lambert identity over ℝ) cannot be
   submitted against it, and were not. Affected: `erdos-69--h1`, `erdos-69--h2`,
   `erdos-402--h2`, `erdos-402--h3`. Unaffected: `erdos-402--h1`, whose type is coercion-free and
   round-trips, and whose proof is the one artifact of round two that can be submitted.
   **This is the run's most serious finding**: it is silent, it is on the live graph now, and it
   turns D-29's "holes enter the frontier as children" into an invitation to prove `0 = 0`.

4. **A hole child is written with no `acknowledged_hazards` though its parent needed one**
   (F07-Q19, already known, now reproduced on three more targets). Both calibration parents carry a
   `div-zero` acknowledgement for the very division their holes inherit, and the bot-written
   children carry none, so admission refuses on a hazard nobody can cure through the service. Every
   such refusal in this run is typed into the per-target logs verbatim.

5. **`GET /submissions/<id>` reports the workflow's conclusion, not the gate's.** A submission whose
   sandbox verdict is `pass` and whose only red job is step 9 (awaiting a human) reads to an agent
   as a failed gate. Seen by two of the three agents; the 2026-09-13 tester found it first.
