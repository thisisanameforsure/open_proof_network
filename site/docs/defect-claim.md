# Filing a defect claim

Implements D-16 (defect claims are free, shaped and taxonomy-typed), D-15 (credit per
confirmed defect, with sample auditing of approvals) and the pre-triage of F08-R7. A defect
claim says a statement or a shared definition is wrong, names how, and carries a Lean exhibit.
Anyone may file one, not only the assigned reviewer (D-15); there is no stake.

## The shape

The record is `defect-claim/v1`:

```
schema: defect-claim/v1
stmt_ref: erdos-1196-lemma-14        # a node id, or defs/<file>.lean under the target
class: junk-value                    # one of D-16's eight classes
line: 7                              # an existing line of the referenced file
exhibit: |                           # a Lean file that elaborates
  import Nodes.«erdos-1196-lemma-14».Context

  example : (3 : ℕ) / 2 = 1 := rfl
contributor: <your pseudonym>
date: 2026-09-11
```

## Mechanical pre-triage

The claim bounces, in the service and again in the gate (D-35), unless all three hold:

- `class` is one of `missing-hypothesis`, `junk-value`, `vacuity`, `quantifier-scope`,
  `wrong-domain`, `definition-mismatch`, `strength-drift`, `other-with-exhibit`;
- `line` is an existing line of the referenced `Statement.lean` or `defs/` file;
- `exhibit` is a Lean file, and it elaborates inside the gate's sandbox (F08-R7).

That is the whole of the automatic check. It exists so that a claim always points at a place
and a kind of defect (D-16), which is what makes D-11's per-class measurement possible, and so
that adjudication never starts from prose alone.

## Filing it on the HTTP path

`POST /defect-claims` with a write token:

```
{
  "stmt_ref": "erdos-1196-lemma-14",
  "class": "junk-value",
  "line": 7,
  "exhibit": "import Nodes.«erdos-1196-lemma-14».Context\n\nexample : (3 : ℕ) / 2 = 1 := rfl\n"
}
```

The service fills `contributor` and `date`, writes the record to
`nodes/<id>/defects/<timestamp>-<pseudonym>.yaml` (or `defs/defects/` for a definition), and
opens an append pull request. The MCP tool `file_defect_claim(stmt_ref, class, line, exhibit)`
is the same call (D-28).

## Filing it on the git path

Add the file under `nodes/<id>/defects/` or `targets/<target>/defs/defects/` on a branch and
open a pull request. The gate classifies the diff as an append, repeats the pre-triage, and
elaborates the exhibit in the sandbox; the pull request fails naming the file if it does not.

## What a good exhibit looks like

- It elaborates against the node's own `Context.lean`, so it uses the same definitions the
  statement does.
- It is the smallest thing that shows the class: a counterexample term for
  `missing-hypothesis`, an `rfl` computation for `junk-value`, a proof that the hypotheses
  force a degenerate object for `vacuity`, the two quantifier orders side by side for
  `quantifier-scope`.
- It proves something. An exhibit that merely restates the complaint in a comment elaborates
  and says nothing; the adjudicator will treat it as `other-with-exhibit` without an exhibit.

## What happens next

1. The claim merges on its checks; no review, because the record claims nothing the kernel
   decides (F07-R9).
2. Adjudication is a human act under D-17, at Stage 1. A confirmed claim earns the review
   line on the ledger (D-19), and its class feeds the per-class catch rate (D-11). On a
   bountied node the confirmed claim is paid (D-26).
3. An unconfirmed claim draws down a rolling rejected-claim budget per identity. Exhausting it
   deprioritizes future claims; it never blocks them, and it is never forfeited (D-16). A
   repeat pattern of rejected claims feeds the standing process of D-22.
4. A confirmed defect in a node routes to revision (D-8); a confirmed defect at a root or in
   `defs/` is reported to the source registry as well (D-12, D-10), because a wrong open problem
   is a result about the problem.
