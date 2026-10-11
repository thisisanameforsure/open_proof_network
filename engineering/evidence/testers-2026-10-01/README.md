# Testers 2026-10-01 — twenty-six agents on the three calibration targets, six rounds

Mike: "I want to use up my credits for the week by sending agents to work on the 3 test problems".

Run started 2026-10-01 at about 11:45Z from one cloud session (the lead). The agents are
in-process subagents of that session, black-box: none reads the network's source; each gets a
brief (the site, the service, the guide in the graph clone, the 2026-09-29 logs for its target)
and an assignment. One exception: `69-R3-curator` is a build agent acting for the owner and reads
the gate. Rounds follow each other as the previous one's Handoff sections come in; a later agent
continues from an earlier one's log. Each agent keeps its log here as it goes (`<agent>.md`) and
its Lean, scripts and receipts beside it (`<agent>/`).

Rules the brief set: only work that moves a target's root (no new fixed-size variants of
erdos-402, the owner's ruling of 2026-09-29); fast check before any precheck; one owner of
submissions per target per round from round 2, the others hand over checked Lean and submit
nothing; no `sorry`, new axiom or `native_decide` in a proof.

Tokens: seven pseudonyms earned by the tutorial route (`t1001-1050a`, `t1001-1050b`,
`t1001-402a`, `t1001-402-r1b`, `t1001-402-r2c`, `t1001-69a`, `t1001-69-b`), reused by successors.
No token or nonce is in any log.

The aggregated, prioritised bug list is `bugs.md`; the one-page account is
`engineering/session-notes/2026-10-01-erdos-testers.md`. Times below are GitHub's and the graph's
commit times: the sandbox clock ran slow and the agents' own stamps are late (bugs.md D, E5).

## Assignments

### Round 1 (from 11:44Z)

| Agent | Pseudonym | Target | Task | Pull requests |
|---|---|---|---|---|
| 1050-R1-a | t1001-1050a | erdos-1050 | close the root with the proof 1050-P1 left ready; prove `spec-180d8b72` | #326, #327 |
| 1050-R1-b | t1001-1050b | erdos-1050 | the integrality chain `--h1-v2--h2`, `--h2--h1` | #323, #330 (withdrawn), #332, #335, #336 |
| 402-R1-a | t1001-402a | erdos-402 | the open hole `erdos-402--h3-v2--h1`: a skeleton with an honest hole | #325, #331 |
| 402-R1-b | t1001-402-r1b | erdos-402 | make the general argument attackable: literature, elementary lemmas, annex | #333, #334 |
| 69-R1-a | t1001-69a | erdos-69 | the hole `erdos-69--h2-v2--h1-v2--h4` | #324 |
| 69-R1-b | t1001-69-b | erdos-69 | the literature route: the external proof's licence, toolchain and missing facts | #328, #329 |

### Round 2 (from 12:33Z)

| Agent | Continues | Task | Pull requests |
|---|---|---|---|
| 1050-R2-a | 1050-R1-b | shepherd #332, #335, #336 through the queue; audit the resolved target as an outside reader; time the queue | none of its own |
| 402-R2-a | 402-R1-a | owner of submissions: the witness of the new hole, then the next skeleton | #342 |
| 402-R2-b | (helper) | the block lemma for primes in [n/3, n/2), as checked Lean for 402-R2-a | #340 (annex) |
| 402-R2-c | (helper) | the general "few or almost all" lemma and the duality reduction | #338 (annex) |
| 69-R2-a | 69-R1-b | Mertens' second theorem as an ingredient node, clean-room | #337 (withdrawn), #339, #343 |
| 69-R2-b | 69-R1-a | clean-room definitions and a root skeleton over them | #341 (annex) |

### Round 3 (from 14:18Z)

| Agent | Continues | Task | Pull requests |
|---|---|---|---|
| 402-R3-a | 402-R2-a | owner of submissions: the skeleton closing n/3 ≤ p < n/2, the next hole's witness | #344, #345 |
| 402-R3-b | (helper) | the literature, and the owner's "pq from p and q" idea | none; `402-R3-b/FINDING.md` |
| 402-R3-c | (helper) | the range 3p < n ≤ 4p and the general-k pattern | none |
| 69-R3-b | 69-R2-a | stress test of hole h4 of 69-R2-b's skeleton; proofs of h2, h3; shepherd #343 | none new |
| 69-R3-curator | — | admit 69-R2-b's definitions into `targets/erdos-69/defs/` | none: blocked by the pinned gate, which became F11-T13 |

### Round 4 (from 15:22Z)

| Agent | Continues | Task | Pull requests |
|---|---|---|---|
| 402-R4-a | 402-R3-a | record why the ladder of rungs stops; send no further rung | #346 (annex) |
| 402-R4-b | (helper) | the owner's multiplicative step, attacked in earnest | none; `402-R4-b/FINDING.md` |
| 402-R4-c | (helper) | the prime criterion, clean-room, without opening the outside Lean | none; `402-R4-c/PLAN.md` |
| 69-R4-b | 69-R2-b, 69-R3-b | the cancellation lemmas at general M, definitions v2, h4's second layer | none |

### Round 5 (from 15:46Z)

| Agent | Continues | Task | Pull requests |
|---|---|---|---|
| 402-R5-a | 402-R4-a | owner of submissions: verify 402-R4-c's criterion independently, then send it | #347, #348, #349, #350 (withdrawn) |
| 402-R5-b | (helper) | the seven residual sizes | none; `402-R5-b/FINDING.md` |
| 69-R5-a | 69-R4-b | h4g, h4d, stress of h4e and h4f, the header question | none |

### Round 6 (from 16:31Z)

| Agent | Continues | Task | Pull requests |
|---|---|---|---|
| 402-R6-a | 402-R5-a | owner of submissions: verify 402-R5-b and 402-R6-b, then land the second route and the finite range | #351–#360 |
| 402-R6-b | (helper) | a denser encoding of the window-prime certificates | none |

## What reached the graph

Thirty-eight pull requests were opened on the graph (#323–#360), first at 11:48:28Z; **35 merged,
3 were withdrawn by their authors, none is open**. The last merge was 18:19:10Z and its
post-merge commit (`gate: #360 pass`, `1d98dcfb`) 18:27:07Z. Checked one by one against
`GET /repos/thisisanameforsure/open_proof_network_graph/pulls/<n>` and against the 35
`gate: #N pass` commits in `3f2da56..1d98dcfb`. By kind: 15 annexes, 7 proofs, 5 partials and 2
withdrawn, 7 witnesses, 1 speculative proposal and 1 withdrawn. Twelve attestations were written
(7 proofs, 5 partials).

| PR | Kind | Node | Agent | Result (merged, UTC) |
|---|---|---|---|---|
| #323 | annex | erdos-1050--h1-v2--h2--h1 | 1050-R1-b | merged 11:49:08 |
| #324 | annex | erdos-69--h2-v2 | 69-R1-a | merged 11:54:07 |
| #325 | annex | erdos-402--h3-v2--h1 | 402-R1-a | merged 11:59:38 |
| #326 | proof | erdos-1050 (the root) | 1050-R1-a | merged 12:10:57 |
| #327 | proof | spec-180d8b72 | 1050-R1-a | merged 12:26:21 |
| #328 | annex | erdos-69 | 69-R1-b | merged 12:32:14 |
| #329 | annex | erdos-69 | 69-R1-b | merged 12:37:50 |
| #330 | partial | erdos-1050--h1-v2--h2--h1 | 1050-R1-b | **withdrawn** 12:05:44 (the full proof #332 made it redundant) |
| #331 | partial | erdos-402--h3-v2--h1 | 402-R1-a | merged 12:51:35 |
| #332 | proof | erdos-1050--h1-v2--h2--h1 | 1050-R1-b | merged 13:03:05 |
| #333 | annex | erdos-402--h3-v2 | 402-R1-b | merged 13:10:01 |
| #334 | annex | erdos-402--h3-v2 | 402-R1-b | merged 13:20:50 |
| #335 | proof | erdos-1050--h1-v2--h2 | 1050-R1-b | merged 13:33:35 |
| #336 | annex | erdos-1050--h1-v2--h2 | 1050-R1-b | merged 13:41:36 |
| #337 | proposal | spec-7d098d5c | 69-R2-a | **withdrawn** 12:41:59 (gate refused one unacknowledged hazard; bugs.md A1) |
| #338 | annex | erdos-402--h3-v2--h1 | 402-R2-c | merged 13:50:09 |
| #339 | proposal | spec-7d098d5c | 69-R2-a | merged 14:01:03 |
| #340 | annex | erdos-402--h3-v2 | 402-R2-b | merged 14:06:53 |
| #341 | annex | erdos-69 | 69-R2-b | merged 14:14:08 |
| #342 | witness | erdos-402--h3-v2--h1--h1 | 402-R2-a | merged 14:23:40 |
| #343 | proof | spec-7d098d5c | 69-R2-a | merged 14:34:23 |
| #344 | partial | erdos-402--h3-v2--h1--h1 | 402-R3-a | merged 14:43:47 |
| #345 | witness | erdos-402--h3-v2--h1--h1--h1 | 402-R3-a | merged 14:55:29 |
| #346 | annex | erdos-402--h3-v2--h1--h1--h1 | 402-R4-a | merged 15:27:36 |
| #347 | annex | erdos-402--h3-v2--h1--h1--h1 | 402-R5-a | merged 15:48:49 |
| #348 | partial | erdos-402--h3-v2--h1--h1--h1 | 402-R5-a | merged 16:00:32 |
| #349 | witness | erdos-402--h3-v2--h1--h1--h1--h1 | 402-R5-a | merged 16:13:42 |
| #350 | partial | erdos-402--h3-v2--h1--h1--h1--h1 | 402-R5-a | **withdrawn** 16:28:46, 37 s after opening (sent before the helper's log was read) |
| #351 | partial | erdos-402--h3-v2--h1--h1--h1 (second route) | 402-R6-a | merged 16:43:33 |
| #352 | witness | erdos-402--h3-v2--h1--h1--h1--h2 | 402-R6-a | merged 16:54:15 |
| #353 | partial | erdos-402--h3-v2--h1--h1--h1--h2 | 402-R6-a | merged 17:08:42 |
| #354 | witness | …--h2--h1 | 402-R6-a | merged 17:21:03 |
| #355 | witness | …--h2--h2 | 402-R6-a | merged 17:31:46 |
| #356 | witness | …--h2--h3 | 402-R6-a | merged 17:41:36 |
| #357 | annex | …--h2--h3 | 402-R6-a | merged 17:48:21 |
| #358 | annex | erdos-402--h3-v2--h1--h1--h1--h1 | 402-R6-a | merged 17:54:03 |
| #359 | proof | …--h2--h1 | 402-R6-a | merged 18:05:50 |
| #360 | proof | …--h2--h2 | 402-R6-a | merged 18:19:10 |

("…" stands for `erdos-402--h3-v2--h1--h1--h1`. A witness's pull request is titled `proposal:`
on the graph.)

## Final state, read from the record at `1d98dcfb`

`targets/index.json` and each target's `graph.json`, compared with `3f2da56` (`gate: #320 pass`),
where the run began.

### erdos-1050: resolved

| | Before | After |
|---|---|---|
| target status | `listed` | **`resolved`**, `not_claimable: ["status-resolved"]` |
| nodes (14) | 8 proved, 4 ready, 1 speculative, 1 superseded | **12 proved**, 1 ready, 1 superseded |
| `erdos-1050` (the root) | ready | **proved** (#326, proof commit `e8091655`, kernel) |
| `spec-180d8b72` | speculative | **proved** (#327) |
| `erdos-1050--h1-v2--h2--h1` | ready | **proved** (#332; the lemma two earlier waves had recorded as open mathematics) |
| `erdos-1050--h1-v2--h2` | ready | **proved** (#335, a direct proof that does not use its hole) |
| frontier entries | 4 | 0 |

The one node not proved or superseded is `erdos-1050--h1-v2--h1`: `ready`, cause `circular`, a
restatement of the root that the root's proof does not pass through and that cannot be closed
(bugs.md B5). `digestion.state` is `undigested`.

### erdos-402: every size from 10 to 200014 checked; one open leaf

| | Before | After |
|---|---|---|
| target status | `listed` | `listed` |
| nodes | 29: 24 proved, 3 ready, 2 superseded | 36: **26 proved**, 8 ready, 2 superseded |
| new nodes | | seven gate-written holes, the chain below `erdos-402--h3-v2--h1` |

The chain, each node open only through the next:

- `erdos-402--h3-v2--h1` → `--h1--h1` (#331: no prime p ≥ n/2 divides an element of a strict set)
  → `--h1--h1--h1` (#344: none with n/3 ≤ p < n/2 either).
- `--h1--h1--h1` carries two merged partials. The first route (#348, the single-prime window
  criterion) left the hole `…--h1`; it is a dead end for seven sizes and annex `d72f0e6b…` (#358)
  says not to work on it. The second route (#351, the generalised criterion) left `…--h2`.
- `…--h2` was split by #353 into three scoped holes:
  `…--h2--h1` (10 ≤ n ≤ 228), **proved** (#359);
  `…--h2--h2` (229 ≤ n ≤ 200014), **proved** (#360, 279 lines, `decide +kernel` over list
  literals, standard axioms only);
  `…--h2--h3` (n > 200014), **open**, witnessed (#356), with annex `3c5df215…` (#357) saying what
  it needs.

What "checked up to 200014" means exactly: the two range nodes are proved; the criterion that
turns their primes into a good pair or a prime ≥ n/3 dividing an element is proved inside the
merged partial #351, the cases that kill such primes inside #331 and #344, and the sizes below 10
inside #353. Each partial's assembly is gate-checked with its holes left open. No node states
"Graham's bound for every set of at most 200014 elements" as a theorem, and every node from
`…--h2` up to the root is still `ready`, waiting on the large-n leaf. That leaf is not a finite
check: through its second disjunct it would need a prime within a constant times √n below 2n for
every n, which is open; through its first it is the theorem of Balasubramanian and Soundararajan
for large n, whose proof uses prime-counting estimates Mathlib does not have.

The frontier lists eight erdos-402 entries, all claimable (bugs.md B5).

### erdos-69: Mertens proved; the definitions route waits on PR #26

| | Before | After |
|---|---|---|
| target status | `listed` | `listed` |
| nodes | 22: 15 proved, 4 ready, 3 superseded | 23: **16 proved**, 4 ready, 3 superseded |
| `spec-7d098d5c` (Mertens' second theorem, bounded-error form) | did not exist | proposed (#339) and **proved** (#343, 336 lines, written from Mathlib alone) |
| annexes | | `595b57d6…` (#324, why the existential repackaging is circular), `9445873d…` and `b8402c93…` (#328, #329, the external proof's licence and closure, the Abel step), `eca55f2b…` (#341, the definitions proposal) |

The four `ready` nodes are the root and three circular restatements of it
(`--h2-v2`, `--h2-v2--h1-v2`, `--h2-v2--h1-v2--h4`); the frontier lists the root alone. Nothing
statable without the construction's definitions is left to prove.

Ready and unsent, all fast-checked over the pasted definitions: `69-R4-b/Defs-v2.lean` (18
definitions), proofs of h1, h2, h3, h4a, h4b, h4c (`69-R4-b/`), h4g and h4d (`69-R5-a/`), the
assemblies `Bridge-R5.lean`, `H4Skeleton-R5.lean` and `Relation.lean`. Open mathematics: h4e and
h4f, unreviewed, truth unknown (`69-R5-a/H4E-H4F-NOTES.md`). None of it can be submitted until a
curator can add `targets/erdos-69/defs/Construction.lean`, which the pinned gate refuses
(`69-R3-curator.md`) and which F11-T13 on this branch (network draft PR #26) allows; and then only
through a bridge node, because nothing beneath a root stated over Mathlib alone can import a
definition (bugs.md B1). The curator's local rehearsal branch on the graph clone
(`curator/erdos-69-defs`, not pushed) holds the first draft of the definitions, not v2.

## Not in this directory

`402-R3-b/upstream-plby-Erdos402.lean.txt`, the copy of the outside formalisation 402-R3-b read,
is in the lead's checkout only and is not committed: its repository has no licence file. Later
agents were told not to open it and say in their logs that they did not.
