# Testers 2026-10-14b: erdos-1094 hole fillers, consolidated and verified findings

Three black-box agents, MCP only, 17:35Z to 18:35Z, each told to fill one hole of its choice with a complete proof.
Logs are `P.md`, `Q.md` and `R.md`. The lead checked every claim below against the graph history, the live service
or the network source at `origin/main`.

## What landed

| Agent | Node | Pull request | Result |
|---|---|---|---|
| P `t1014-p` | `--h2--h2--h2--h1`, van Doorn–Tang's small case (¬BHP ∨ case_small) | #524, complete proof | **Merged 18:13:23Z**, no human. `attestations/000524.json` passes steps 1, 2, 4–8. The node is proved. |
| Q `t1014-q` | `--h3--h1--h1--h2`, sieve class k even, 0 < k%3 ≤ n%3 | #525, partial | Merged 18:25:11Z. p = 5, 7, 11, 13 close n%p < k%p; one hole, now `--h3--h1--h1--h2--h1` (`holes[].became` names it). |
| R `t1014-r` | `--h2--h2--h2--h2`, van Doorn–Tang's medium case | #526, partial | Merged 18:39:14Z, bot commit `1e74f2e26`. One hole, `h_count`, now `--h2--h2--h2--h2--h1`: vdT's `med_card_bound`, a pure count with no BHP. |

Mathematical value:
- **P's proof is the first complete proof on the van Doorn–Tang branch.** One of the four cases is now closed in the kernel, conditional on nothing, since the ¬BHP side is a disjunct.
- **R's hole is genuinely narrower and provable.** `R/hole_check.lean` proves it at 4.33.1 from vdT's chain as separate declarations. Only the heartbeat cap stops it being a complete proof.
- **Q's hole is as open as its parent.** It keeps about 9% of the parent's cases for k ≤ 300, checked numerically only, with failures up to k = 58. Q says so plainly.

## Ranked

1. **H1, the binding constraint: one theorem, 200k heartbeats, no helpers.** Every agent hit it.
   - P's chain cost about 133k as separate declarations and 216–247k inlined. Clearing unused `have`s and replacing heavy `nlinarith` brought it to 122k.
   - R's chain cost about 221k as separate declarations and 328k inlined, so R had to split.
   - This is a design limit, not a bug. It decides whether outside developments such as vdT's can be ported. Both P and R asked for helper declarations, or a cap per declaration. That choice is the owner's.

2. **H2, MINOR. `hole-not-roundtrip` points at the contributor's text when the printer lost the type.** Confirmed.
   - R's hole was fully typed: `{m ∈ Finset.Ioo (k:ℤ) … | (↑m : ℝ) < …}`. The printed form re-elaborated `m` as ℝ.
   - The refusal (`gate/opn_gate/steps/artifact.py:302-307`) says "ascribe the type where a bound variable … is used". The cause was the printer dropping the set-builder binder's type, not anything the contributor wrote.
   - The round-trip check was right and caught it before the merge. R's workaround: a first conjunct `(k : ℤ) < m` pins the type.
   - Fix direction: print set-builder binder types, as `pp.funBinderTypes` did for `∃` (2026-09-21), and name the set-builder case in the hint.

3. **H3, UPSTREAM. AXLE outage.** From about 17:46Z to 17:51Z every `check_lean` answered `502 upstream-unavailable`, because AXLE returned 503. P and R saw it independently. The error said plainly where the fault was.

## Not findings

- **check_lean's `{status, body}` envelope (Q).** By design: `check_lean` is a write tool (`api/opn_api/mcp/bijection.py:146`), and the guide says write tools answer with the envelope. The guide could say check_lean is one.
- **Slow calls of 40–150 s.** This laptop's network path, as in every earlier run.

## Feature requests

- A heartbeat breakdown per `have` or per tactic block in `check_lean` (P).
- A `check_lean` skeleton mode that runs hole extraction and the round-trip check, saving a four-minute precheck (R).
- A frontier marker for "this node restates the open problem" (Q). Q spent its first ten minutes working out that every leaf but two needs research-level work. A ranking marker is a D-25 question and the owner's.
- Claims visible in `list_frontier` quickly enough for agents choosing at the same time (Q).
