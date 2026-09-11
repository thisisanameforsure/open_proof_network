# Curator intake checklist

Implements D-6 (intake is curated, not open), with the fidelity ladder of D-9, the registry
posting of D-10 and the role separation of D-21. A proposal becomes a target only when a
signed curator attaches all five artifacts below; nothing is claimable until the root's
fidelity grade reaches `screened-and-signed` and the D-10 posting is made. The file shapes and
the intake commands are F11's; this page is the judgment the commands cannot make for you.

## Before anything: is it in scope?

- Sources, in priority order (D-6): open Erdős problems with an existing Lean statement;
  open conjectures in analytic number theory, combinatorics and additive combinatorics without
  one; open questions in convex optimization and universal algebra; the google-deepmind/debate
  seed; prerequisite-library nodes from missing-library postmortems (D-13).
- Excluded until the network can fund multi-year prerequisite work: algebraic geometry,
  algebraic number theory, differential geometry, PDEs.
- An arXiv'd result awaiting formalization is admissible only on the on-ramp track: labelled,
  ledgered under a separate formalization class, never counted as an open-problem claim.

## The five artifacts

1. **Prior-art artifact.** Evidence the problem is plausibly still open: the arXiv search, the
   erdosproblems.com forum thread, and what each says. The 68.5 per cent scattered-literature
   hazard cuts here (D-6, D-15): a target later found solved is relabelled `rediscovery` and is
   never paid as novelty, so the search is the intake's most valuable hour. Record the queries,
   not only the conclusion.
2. **Library-coverage assessment** against the pinned Mathlib SHA (D-7): the definitions and
   lemmas the conjectured route needs, which exist, which are missing, and the missing ones
   scheduled as prerequisite nodes. For an open problem this is an assessment of the route's
   prerequisites and is revised when the route is.
3. **Statement provenance** (D-9, D-10): where the Lean statement came from, who wrote it,
   whether it was adversarially reviewed, and the certificate rung it enters at. An inherited
   statement (Formal Conjectures) lowers intake cost but is not thereby certified.
4. **Attack-route evidence**, advisory and never required: known partial results, reductions
   in the literature, candidate crux statements. A target may enter as a bare root; the
   decomposition is emergent (D-29), and a seed decomposition attached at intake is the first
   contributor proposal, nothing more.
5. **Non-vacuity witness at the root** (D-4 step 7): the hypotheses are satisfiable, shown by
   a witness the gate checks.

## The root and the definitions

- Every definition the root uses lives in the target's `defs/`, or in the pinned Mathlib.
  Read each `defs/` file with the review checklist in hand: a definition-mismatch here poisons
  the whole graph (D-15).
- The root statement, the informal statement and the certificate level are what the target
  page shows a bystander (D-36); write the informal statement for that reader.
- Run the gate's admission over the root as a proposal would be admitted (F08-R1): layout,
  witness, hazards, acyclicity. What the machine catches should never reach the intake pull
  request.

## Listed is not claimable

The root appears on the frontier immediately, unclaimable, and the public comment period runs
on it (D-6). Claims open only when both hold:

- the root's fidelity grade is `screened-and-signed` or above (D-9), recorded by the fidelity
  commands F11 delivers;
- the D-10 posting to the source registry exists, so the network authors nothing in private.

Activation is a curator declaration (`target-status/v1`, F08-R11's `status` command), and it
refuses while either condition is missing.

## Two curators, one pull request

Intake is a curator's pull request under the curator's own credentials; the gate never holds
them (F08-Q17). A second listed curator approves it (D-21's separation), waived while the
founder is the only curator, with the waiver recorded on the pull request (D-22). Everything
above is evidence in that pull request, so the record of why a target exists is the same
record as the target.

## After intake

- Dormancy, if it comes, is a declaration with published reasoning, reversible, and closes
  nothing (D-33).
- A target later found solved is relabelled, not deleted (D-6); the ledger keeps every entry
  it earned.
- Missing-library postmortems above the threshold surface the missing lemma to you; you
  propose the node like any contributor (D-13, D-29). Nothing is created automatically.
