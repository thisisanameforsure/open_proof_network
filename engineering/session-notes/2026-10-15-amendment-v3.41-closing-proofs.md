# Decisions draft v3.41: closing proofs (draft, not applied)

From the owner's question on 2026-10-15: erdos-1094--h2--h2--h2--h2 had one merged partial whose
only hole, `--h1`, was proved in graph PR #527, and the node still read `ready`. The owner's
rulings that day are recorded in `2026-10-15-proof-propagation-cases.md`. This is the wording to
approve before F28-T0 applies it. Nothing in it changes what closes a node: only a proof does. It
changes who may write that proof when nothing in it is new.

## D-12, a new paragraph after "only a proof, a counterexample or a vacuity certificate (artifacts 1–3) closes it"

> **v3.41 — closing proofs.** When every hole of a merged decomposition of a node is proved, the
> node is *closable*: its proof already exists in parts, the assembly and the holes' proofs, and
> only their join is missing. The network writes that join. The post-merge job of the merge that
> made the node closable composes the closing proof (the assembly with each hole's `sorry`
> replaced by the hole node's theorem, applied to exactly the locals the hole was closed over,
> D-29) and submits it as an ordinary proof of the node, which the gate checks like any other
> (D-4). A node is marked proved only when that proof merges; the network never marks a node from
> the parts. Its merge may make the node's own parent closable, so one proof climbs the target
> one checked merge at a time, to the root if every level allows.
>
> The same holds for two other kernel-checked upward links. A hole carrying a merged circularity
> claim (v3.23) whose exhibit proves "this hole implies ancestor *A*": a proof of the hole makes
> *A* closable, and the closing proof is the exhibit applied to it. The claim alone still closes
> nothing (v3.35). And a proof of a `resolves` variant (D-30) makes the root closable through its
> `Relation.lean`.
>
> A closing proof is credited to the work it joins (the assembly's author and each hole's prover,
> D-19); the network is its submitter and never its author. It is a join, not mathematics, so it
> is never kept beside a real proof: if a direct proof of the node merges first, the network's pull
> request is closed, and the network never files its own work as an alternate. A direct proof that
> arrives after it merges as an alternate as today (v3.13). Proved never stops work: a better proof
> of a proved node, the root included, is always welcome as an alternate. A closing proof that
> settles the root is asked step 9 as any proof of the root is (v3.20). If a closing proof fails
> the gate, the join was not what the record said it was, and that is a defect of the hole's
> statement (D-16), recorded, not retried.

## D-25, one sentence in the products paragraph

> (v3.41) A node whose decompositions make it closable is published as closable, with the route,
> claim or variant that makes it so and whether its closing proof can be written now (every input
> proved) or waits on another closable node below it. Closable is never shown as proved.

## Version history line

> v3.41 let the network write the proof that joins a node's merged decomposition to its proved
> holes, submitted through the gate like any proof, so a proof climbs the target one checked merge
> at a time (D-12, D-25): the owner's question on erdos-1094, whose node `--h2--h2--h2--h2` had
> every hole proved and still read ready.

## Overturns if

Closing proofs fail the gate more than rarely. Each failure means a gate-written hole did not say
what its gap said, which the round trip (F07-T18) exists to prevent; if they recur, the hole
writer is untrustworthy and joins should stop until it is fixed. (A join can never make a false
statement read proved: the kernel checks it like any proof.)
