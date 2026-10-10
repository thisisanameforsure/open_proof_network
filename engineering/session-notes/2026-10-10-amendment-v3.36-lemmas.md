# Decisions amendment v3.36: a restated node under another branch is a lemma of its parent

**Status (2026-10-10): approved by the owner ("alright lets plan option B"; "ok sounds good. add lots
of testing, and verify visually.") and applied as decisions v3.36.** Plan:
`~/.claude/plans/option-b-restated-sibling-lemma.md`.

Source: one tester told to solve erdos-1094 through the MCP (`engineering/evidence/testers-2026-10-09b/
bugs.md`, C1), and the owner's reading of it: "sometimes in the proof tree there is some result that
needs to be used in another part of the tree. This is what we are calling a lemma. Right now that cant
be done cleanly, and agents have to rederive it ... instead of just using it."

## What the record showed

Graph #479, a partial on `erdos-1094--h3` whose one hole restated `erdos-1094--h2--h1--h1` (the node
#478 had created under `--h2--h1` fifteen minutes earlier). The gate's step 4 recognised the
restatement (`defeq_sibling`), the post-merge writer printed
`{"hole": "h_good_below_cube", "child": null, "reused_node": "erdos-1094--h2--h1--h1"}` to its log,
and by F07-R22 (D-12 v3.19, Q29) added no edge. The attestation said `pass`; `--h3`'s `deps` were
unchanged; the merged assembly could never be used, because a proof may draw only on the nodes in its
own `Context.lean`.

The deduplication was making things strictly worse than no deduplication: a duplicate child would at
least have been closable.

## The rule (D-12, clarified paragraph; D-29 unchanged in substance)

A hole that restates a node under another branch of the target *is* that node, and the parent gains
it as a **lemma**: an entry of `META.yaml`'s `lemmas` (`{hole, node}`, bot-written, `meta/v6`) with
exactly a hole's standing. Its signature is in the parent's `Context.lean`; the parent may draw on it
once it is proved; the parent never waits on it (the derivation sets lemmas aside as it sets the
node's own holes aside); staging imports a proved lemma and leaves an unproved one out; step 8 accepts
a proved lemma's constants. One proof of such a node closes every branch that points at it.

No new cycle check: `offload-restates-ancestor` (v3.21) already refuses, before any merge, a hole
definitionally equal to any node that depends on the parent, so the only restatements that reach the
writer are of nodes that do not rest on the parent.

Not in `deps`, because `is_hole_child` recognises a hole by id prefix and origin, a cross-branch node
has neither relation to this parent, and a *declared* dependency must keep blocking (D-3).

## Contracts (this commit)

- `meta/v6`: optional `lemmas: [{hole, node}]`.
- `context/v6`: `lemmas` beside `deps`, each with the hole name, signature, status and cause.
- `graph/v7`: each node's `lemmas`; a decomposition's hole may resolve to a lemma's node.
- `graph.NodeFacts.lemmas` (`Lemma(hole, node)`, read through revisions as deps are), so the
  consumers below build on one accessor.

## Consumers (tasks, each red first)

Gate writer and readers (F07, F08, F03): `apply_partial` writes the edge and regenerates Context;
`blocked_because`, `stage`, step 8 and `context_for` give it a hole's standing; the two tests that
pinned "a restated sibling records no edge" are restated to the new rule. Products and context
(F03, F10): `graph/v7` `lemmas`, `decompositions[].holes[].node` resolving to the lemma, `context/v6`,
`PROTOCOL_VERSION` 3.36, goldens. Site (F04): a lemma edge drawn and keyed, listed on the node page,
screenshots measured. Service and guide (F09, F13, F06): accepted versions, `get_node`, the receipt's
note, the guide's sentence. Then the re-pin, a backfill of `--h3`'s edge in the footprint-backfill
shape (re-extract the merged partials whose placement reused a sibling), and the re-render.
