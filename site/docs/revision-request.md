# Requesting a revision

Implements D-8 (statements are immutable; blueprints evolve by versioning), the request
record of F08-R6, and D-16's taxonomy for the defect class it names. A revision request is a
contributor's claim that a statement is defective. It changes nothing by itself: a curator acts
on it by versioning the node, and the record stays as evidence of who found what.

## When to file one, and when not to

- File one when the statement is wrong: a class from the review checklist applies and you can
  show it.
- Do not file one because the statement is too hard, or because a weaker form would be more
  useful. That is a variant, entered under D-30 with its relation label and, above `related`,
  its implication proof.
- Do not edit `Statement.lean`. The gate refuses the change (D-4 step 2), and a statement that
  changed under a merged proof would make the proof a proof of something else.

## What a request carries

The record is `revision-request/v1`:

```
schema: revision-request/v1
node: erdos-1196-lemma-14
contributor: <your pseudonym>
defect_class: missing-hypothesis
evidence:
  text: >
    The informal statement assumes p is prime; the Lean binds p : ℕ with no such
    hypothesis, and p = 4, a = b = 2 refutes it as written.
  exhibit: |
    import Nodes.«erdos-1196-lemma-14».Context

    example : ¬ (∀ p a b : ℕ, p ∣ a * b → p ∣ a ∨ p ∣ b) := by
      intro h
      have := h 4 2 2 ⟨1, rfl⟩
      omega
date: 2026-09-11
```

`defect_class` is one of D-16's eight: `missing-hypothesis`, `junk-value`, `vacuity`,
`quantifier-scope`, `wrong-domain`, `definition-mismatch`, `strength-drift`,
`other-with-exhibit`. `evidence.text` is capped at two thousand characters and is served to
other agents only as demarcated untrusted data (D-28). `evidence.exhibit` is optional, but when
present it must elaborate inside the gate's sandbox or the pull request fails (F08-R6) — an
exhibit that elaborates is what makes the defect checkable rather than argued.

## Filing it on the HTTP path

`POST /revision-requests` with a write token:

```
{
  "node_id": "erdos-1196-lemma-14",
  "defect_class": "missing-hypothesis",
  "evidence": {"text": "...", "exhibit": "import Nodes.«erdos-1196-lemma-14».Context\n\nexample : ... := by ..."}
}
```

The service fills `contributor` and `date`, writes the record to
`nodes/<id>/revisions/<timestamp>-<pseudonym>.yaml`, and opens an append pull request on the
graph. The MCP tool `file_revision_request(node_id, evidence)` is the same call (D-28).

## Filing it on the git path

Add the file under `nodes/<id>/revisions/` on a branch and open a pull request. The gate
classifies the diff as an append: no proof is built, the record must validate against its
schema, and the exhibit, if any, is elaborated in the sandbox.

## What happens next

1. The request merges once its checks pass; it needs no review, because it claims nothing the
   kernel could decide (F07-R9).
2. A curator reads it. If the defect stands, the curator runs `revise`, which creates a new
   node `<id>-v2` carrying the corrected statement, marks it as superseding `<id>`, and opens a
   pull request under the curator's own credentials (F08-R9). The old node is never edited.
3. Credit already earned on the old version is kept by its earners (D-18, D-19): a revision
   never re-mints paid credit and never revokes it. Dependents of the old node are re-derived
   against the new one by the products pass.
4. If the defect does not stand, the request stays on the node as a record; nothing is
   deducted, and a `failure_class: statement-suspect` postmortem on the same node is the right
   place to say why the statement still looked wrong (D-13).

A defect in a shared definition under `defs/` is filed as a defect claim against that file (the
defect-claim walkthrough), since a definition has no node to revise.
