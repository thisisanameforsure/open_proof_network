# Proof propagation: test cases (draft, 2026-10-15)

The owner's ask: when a node is proved, find every node it now proves, all the way up, and close
each one with a kernel-checked proof. This note is the case catalog to build against, written
before any code. Nothing here is decided protocol; the D-12 amendment is the owner's call.

## Two parts, two kinds of test

- **The fact (closable).** Pure derivation over `graph.json`, built on F27's AND-OR reader
  (`opn_gate.routes`). A node is *closable* when it is not proved and some live decomposition
  (route) of it has every hole proved or closable. Fast tier, fixture graphs, no Lean.
- **The actor (closing proof).** Writes the closing proof: the merged assembly with each hole's
  `sorry` replaced by the hole node's theorem applied to what the hole was closed over, the hole
  nodes' proofs imported as declared uses (v3.25). Then opens an ordinary pull request. Lean tier,
  core-only fixtures, so no Mathlib checkout is needed. One live Mathlib case at the end.

**Soundness is not at risk; liveness is.** The gate checks whatever the actor writes. A wrong
argument order cannot produce a false proof. It produces a red pull request on a node that should
have closed. So the actor's tests assert that it *succeeds* when it should, and the fact's tests
assert that it never says "closable" when it isn't, since that one is published.

Notation: `P <- [a, b]` is a route (a merged partial of `P` with holes that became `a` and `b`):
an AND. Two routes on one node are an OR. `✓` is proved.

## A. Shape of the tree (the fact layer)

| # | Shape | Proved | Expected closable | Why it is here |
|---|---|---|---|---|
| A1 | `P <- [a]` | `a✓` | `P` | The erdos-1094 case, minimal. |
| A2 | `P <- [a, b]` | `a✓` | nothing | AND needs every hole. |
| A3 | `P <- [a, b]` | `a✓ b✓` | `P` | AND complete. |
| A4 | `P <- [a]`, `P <- [b]` | `b✓` | `P` via the second route | OR: either route. |
| A5 | `P <- [a]`, `P <- [b]` | `a✓ b✓` | `P`, via the first route in merge order | Rival routes both complete: one choice, deterministic. |
| A6 | `P <- [a, b]`, `P <- [c]`; `c` refuted | `a✓ b✓` | `P` via the first route | A dead route does not block a live one. |
| A7 | `P <- [a, b]`; `b` refuted | `a✓` | nothing, ever | A dead hole kills its route. |
| A8 | `R <- [P, q]`, `P <- [a]` | `a✓ q✓` | `P` and `R` | Two levels from one proof. |
| A9 | `R <- [P, q]`, `P <- [a]` | `a✓` | `P` only | Travel stops at an open AND sibling. |
| A10 | `R <- [P]`, `P <- [Q]`, `Q <- [a]` | `a✓` | `Q`, `P`, `R` | Three levels: the full climb. |
| A11 | `R <- [P, q]`, `R <- [s]`; `P <- [a]`, `P <- [b, c]` | `a✓ q✓` | `P`, `R` | AND and OR mixed at two levels. |
| A12 | `P <- [x]`, `Q <- [x]` (one node, two parents) | `x✓` | `P` and `Q` | The graph is a DAG, not a tree (erdos-1094's `--h2--h1--h1` sits in routes of two nodes). |
| A13 | `R <- [P, Q]`, `P <- [x]`, `Q <- [x]` | `x✓` | `P`, `Q`, `R` | Diamond: one proof reaches the root by two paths, closes it once. |
| A14 | `P <- [a]` and `P` already proved directly | `a✓` | nothing | A proved node is never re-closed (an alternate is not this feature's job). |
| A15 | `P <- [a]` where `a` was superseded by `a-v2` (D-8) | `a-v2✓` | `P` | Follow the revision, as F27-R3 does. |
| A16 | as A15 | `a✓` (the old one), `a-v2` open | nothing | A proof of the superseded statement does not count. |
| A17 | `P <- [a]` whose route returns to `P` (`a <- [P]`) | none | nothing | A cycle closes nothing (F27 drops it). |
| A18 | route whose holes name no nodes (an older product, F09-T73) | all holes proved | as F27-R2 resolves it, otherwise nothing | Unresolved routes are used in no claim. |
| A19 | hole `a` reused an existing sibling `s` (`defeq_sibling`) | `s✓` | `P` | A hole can be an edge to a node that is not its child. |
| A20 | hole `a` carries a merged circularity label naming ancestor `R` (v3.35) | `a✓` | `R` (recommended, ruling 3 pending) | The label's exhibit proves `a` implies `R`: an upward edge. |
| A21 | a `resolves` variant of the root (D-30) is proved | the variant | the root (ruling 4) | A proof of the root by another road; step 9 asked. |
| A22 | the climb reaches the root | all | root closable, step 9 asked | v3.20: a root-settling proof gets a human. |
| A23 | `a` is `blocked` (no witness) but has a proof | `a✓` | `P` | Can a blocked hole even be proved? If the record allows it, the fact must say what it means. Pin it. |

## B. The actor: what gets written, and when

| # | Situation | Expected |
|---|---|---|
| B1 | A1 after `a`'s proof merges | One pull request on `P`, a proof, submitter the network, credits the assembly's author and `a`'s prover. |
| B2 | A10 | Pull request on `Q` only. When it merges, the next post-merge run opens `P`'s, then `R`'s. One level per merge. |
| B3 | A13 | `P` and `Q` open in one run. `R` opens once both have merged, and only once. |
| B4 | Post-merge job re-run on the same merge | No second pull request (idempotent: key on node and route). |
| B5 | A contributor proves `P` directly while the actor's pull request is open | The actor's pull request is closed (ruling 2). |
| B5b | The actor's proof of `P` merges, then a contributor proves `P` directly | The contributor's proof merges as an alternate, as today. |
| B5c | `P` already has a direct proof when its last hole is proved | The actor opens nothing (A14). |
| B6 | Two holes of one route proved in one append batch | One closing pull request, not two. |
| B7 | The composed proof fails the gate | Pull request stays red, a defect is recorded naming the hole, no retry loop. |
| B8 | The hole node's proof itself imports other proofs as uses | The closing proof's imports carry them; step 4 replays them. |
| B9 | The hole node is the revised `a-v2`, which kept `a`'s theorem name (2026-09-17 note) | The import resolves to the right module and no name clash. |
| B10 | Merge actor | Takes the actor's branch prefix like the service's branches; the curator-branch trap of 2026-10-04 does not recur. |
| B11 | A23-style hole proved while still blocked | Whatever A23 pins, the actor follows. |

## C. Order of variables and theorems (the composition)

What the extractor closes a hole over (read from `gate/lean/OpnGate/Holes.lean`, `closedOver`):
the statement's binders in order, `intro`s, case-branch fields and proved `have`s. A proved
`have` the hole's type does not use is dropped. One it does use stays as a `let`, which takes no
argument. An earlier hole is kept only when something kept mentions it. The actor has to
reproduce exactly that list, in exactly that order, and every case below changes it.

| # | Assembly shape at the hole | What the call must get right |
|---|---|---|
| C1 | Statement binders only, distinct types | Baseline positional application. |
| C2 | `x y : ℕ`, hole mentions only `y` | Position from the closed spine, never by type: `y` is not first. |
| C3 | `x y : ℕ`, hole mentions `y` then `x` | Spine order is scope order, not mention order. |
| C4 | Implicit and instance binders `{α : Type} [Fintype α]` | Child keeps the binder info, so the call is `@child …` or fills them correctly. |
| C5 | After `intro n hn` inside the proof | Intro'd locals sit after the statement's binders. |
| C6 | After `intro` with no names, so `n✝` | An inaccessible name cannot be written in source. The hard case: see Q1. |
| C7 | Second hole whose type mentions the first hole | Earlier hole passed as an argument, as that hole's own local. |
| C8 | Second hole that does not mention the first | Earlier hole not passed (F07-T48 dropped it). |
| C9 | Proved `have` the hole's type uses | It is a `let` in the child's statement, not an argument. |
| C10 | Proved `have` the hole does not use | Absent from the child, absent from the call. |
| C11 | Hole after `obtain ⟨k, hk⟩ := …` | Case fields are binders, in field order; F07-T44's proved fields are still binders of the statement. |
| C12 | Two holes in two branches of `rcases h with h1 \| h2` | Two different contexts, two different calls. |
| C13 | Hole inside the step of `induction n with … ih` | The induction hypothesis is a binder; motive variables in the right order. |
| C14 | Dependent binders: `S : Finset ℕ`, `h : x ∈ S` | The dependent one after what it depends on. |
| C15 | Hole under a term-mode `fun x => …` | The lambda's binder is a local like an `intro`. |
| C16 | Coercion-heavy obligation over the reals from naturals | The September 2026 class: the call elaborates against the child's statement, not a reprint of the gap. |
| C17 | Hole reused a sibling `s` by definitional equality, not syntactic | The call type-checks only up to unfolding: `exact` at default transparency, or a stated cast. |
| C18 | Child statement written under the parent's `open` lines and `Defs.*` uses | Same namespaces resolve in the closing proof. |
| C19 | erdos-1094's own `--h2--h2--h2--h2` (live, Mathlib) | The real case: `h_count` after `obtain`s, ℝ and ℤ casts. The probe that runs first, by hand. |

C1 to C18 as core-only Lean fixtures in the lean tier, one assembly per case, each asserting the
composed proof elaborates against the child as the gate wrote it. C19 runs once with Mathlib.

## The owner's rulings (2026-10-15)

1. **C6, inaccessible names: compose in Lean.** The actor builds the closing proof at the term
   level in a metaprogram (the hole's `sorry` replaced by the hole node's constant applied to the
   very locals `closedOver` kept) and prints it with the round-trip printer. Exact by
   construction, so C1 to C18 test the printer and the replacement, not a guess at the order.
2. **B5, a race: no second copy of a composed proof.** A composed closing proof is trivial and
   is never kept beside a real one. If a direct proof of the node merges first, the actor's pull
   request is closed. If the composed proof merges first, a later direct proof is a different
   proof and merges as an alternate as it does today (v3.13). The actor never files its own work
   as an alternate.
3. **A20, the circularity label: pending the owner's reading of the explanation.** Recommended:
   yes. The exhibit is a kernel-checked "hole implies ancestor", the same footing as an assembly
   with one hole, so a proof of the hole closes the ancestor by one application.
4. **A21, the root: mark it proved.** A proof of the root by any road, a climb or a `resolves`
   variant through its `Relation.lean` (D-4 step 9 already calls the latter "a proof of the root
   by another road"), marks the root proved, with step 9's human as today. Proved never stops
   work: a better proof of a proved root merges as an alternate (v3.13). So A21 expects the root
   closable, and the composition is the relation applied to the variant's proof.
