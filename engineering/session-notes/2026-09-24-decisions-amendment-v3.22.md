# Proposed decisions amendment v3.22 — for Mike's approval before any code

From the rulings of 2026-09-24 on the tester run (`2026-09-24-testers-fix-plan.md`, D4 and D9).
Two paragraphs change, and nothing is removed. Once this is approved, the text below goes into
`docs/architecture_decisions.html` as v3.22, with one clause added to the version line, and B5 and
C1 are built test first against it.

## 1. D-12, "No cycles (v3.21)": one claim reaches the whole established path (B5)

**Current text, last two sentences:** "…once the claim merges, the hole leaves the frontier as not
claimable for reason `circular`, naming the claim, and is labelled so on the site. Nothing is
rewritten: the skeleton stays in `attempts/` as the record of a route tried, and a rival
decomposition of the parent is as welcome as before."

**Proposed replacement for those two sentences:**

> Once the claim merges, the hole leaves the frontier as not claimable for reason `circular`,
> naming the claim, and is labelled so on the site. *(v3.22)* So does every node strictly between
> the claim's ancestor and the hole, on the path by which the hole reduces the ancestor, provided
> every other hole of every decomposition on that path is proved. Then each such node is implied
> by the ancestor, which implies the hole, which with the proved holes implies the node back. It
> is the ancestor restated, and a proof of it would still be welcome, because it would prove the
> ancestor. A node whose sibling holes are not all proved stays on the frontier until they are.
> The ancestor itself stays open and claimable: it is the problem, and the circle says only that
> this route to it made no progress. Its page names the claim and invites a direct proof or a
> different decomposition. The target is never closed by a circularity claim. Nothing is
> rewritten: every consequence is derived from the merged claim and the proved holes, so reverting
> the claim restores every node, and the skeleton stays in `attempts/` as the record of a route
> tried.

**Why:** on 2026-09-24, erdos-69 needed three separate claims (#176, #179, #180) to take one chain
off the frontier, one node at a time. The ancestor named in a claim is where the circle begins; the
gate has checked it in Lean. The proved-siblings condition is what makes the in-between nodes
provably equivalent rather than merely suspected.

**Reverts if:** a node the rule removes turns out to be strictly easier than the ancestor in
practice. That can only happen if the equivalence argument is wrong, and the rule's tests exist to
catch exactly that.

## 2. D-29: a hole's witness covers only what is still unproved (C1)

**Current practice (F11-Q22, not stated in the decisions):** a skeleton's hole is closed over every
earlier `have` in scope. Its step-7 witness must therefore exhibit all of them at once, including
facts the skeleton itself proved, and those proofs have to be written again inside `Witness.lean`.
On erdos-1050's #196 that meant about 250 lines duplicating the merged skeleton.

**Proposed addition to D-29, after "supplying it is itself a proposal.":**

> *(v3.22)* A hole's witness exhibits only the hypotheses it inherited from other holes. Those
> it inherited from facts the decomposition proved are discharged by the gate from the proof
> already merged in the assembly, which step 4 has kernel-checked. The hole's statement is
> unchanged, still closed over everything in scope, so its hash, its round trip and D-31
> finalisation are untouched; only step 7's expected type is narrowed. A hole written before this
> rule keeps the expected type it was written with.

**Why:** a witness shows the hypotheses can hold together. For a hypothesis that is a proved fact,
the gate already holds the proof, so asking a contributor to write it out again adds work and no
assurance.

**Reverts if:** a narrowed expected type admits a witness that a full one would refuse. That would
mean the "proved" marking was wrong. The lean-tier test that compares the two on every fixture
hole is there to catch it.

## What approval means

- The two blocks above go into the doc as v3.22, with the version-line clause: "v3.22 took a whole
  established circular path off the frontier with one claim, the ancestor staying open (D-12), and
  let a hole's witness skip what its decomposition already proved (D-29): the owner's rulings on the
  2026-09-24 run".
- `PROTOCOL_VERSION` moves to 3.22 in the same commit as the code that implements it.
- B5 and C1 reach the graph at the next re-pin, which is Mike's act.
