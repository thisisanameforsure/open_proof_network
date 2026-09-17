# Curator intake checklist

Implements D-6 (intake is curated, not open), with the fidelity ladder of D-9, the registry
posting of D-10 and the role separation of D-21. A proposal becomes a target only when a
signed curator attaches all five artifacts below; a listed target is claimable at once (v3.15),
except an open problem with no steward once the steward rule is enforced (v3.17). The file shapes and
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

## Listed is claimable; the steward rule (v3.15, v3.17)

The root appears on the frontier and may be claimed the moment the target is listed (D-6
v3.15): the fidelity grade and the D-10 posting are published beside it and decide who must look
at a proof (D-4 step 9), not whether work may begin. One thing does refuse a claim on an open
problem once the graph's `policy.json` enforces it: no active **steward** (D-6, D-32 v3.17).
On-ramp and calibration targets are exempt. The switch is flipped by a curator's pull request
naming the calibration evidence, never by a re-pin, and its state is published at the top of
`targets/index.json`.

Activation is a curator declaration (`intake activate`, or `status <target> active`), refused
only from a closed status, under an upstream-drift freeze, or, under the rule, with no steward.

## Stewards, signed explainers and write-ups (D-32, D-3, D-33 v3.17)

- **A steward record** (`targets/<id>/stewards/<n>.yaml`, `steward/v1`) is a mathematician's
  signed commitment to understand and write up whatever the network produces on the target, or
  their step-down. It is signed with their own SSH key over the fixed sentence and merged by pull
  request under any account; `opn-gate steward check <record>` tells you whether the signature
  verifies and whether the key is one the login publishes on GitHub. Read the identity link (an
  institutional page or an ORCID record) before merging: the merge is the identity check, and no
  second signature exists. A step-down under a different key, an altered sentence or a failed
  signature is refused at the gate by name.
- **Signing or proving, never both** (D-9, D-21 v3.17): whoever signs a subject's fidelity at a
  counting grade earns no proof line on the target, and `opn-gate fidelity` refuses a signing
  grade from an identity holding an active proof line there. A steward who wants to prove needs
  another signer before the grade can rise.
- **An explainer signature** (`nodes/<id>/explainer/signed/<hash>-<n>.yaml`) affirms one
  sentence, *I can explain this proof without the tool that produced it*. At Stage 0 the signer
  is an active steward of the target or a listed curator; the gate refuses anyone else by name.
  Only signed explainers count toward the target's digestion state, and a signature you cannot
  stand behind is a D-17 ground (iii) matter (D-22).
- **A write-up record** (`targets/<id>/writeup/<n>.yaml`) says a paper or note exists and where,
  signed the same way; a `paper` record makes a resolved target `written-up`. The note's text is
  still `targets/<id>/note.md`.
- **The digestion state** is derived, never written: `undigested`, `explained` (every proved
  node of the closing proof's closure carries a valid signature) or `written-up`; the site shows
  "resolved — undigested" and the report-back to the source registry carries it (D-10 v3.17).

## Proposals and calibration targets (D-6 v3.17, Stages v3.17)

- A mathematician's **proposal** arrives as an issue on the graph repository's form, never a
  commit. Its `target.yaml` (`target/v2`) carries `source: {kind: proposal, ref: <the issue
  URL>}` and `proposer`; `intake new` refuses any other ref. The proposer's signed steward record
  travels in the intake pull request when they accept; without one the target is listed and,
  under the rule, refuses claims. A proposer may ask to skip upstreaming (`upstream_opt_out`),
  which buys no privacy: publish in-network with equivalent visibility (D-10 fail-open).
- A **calibration target** is a known result taken in on the formalization track with
  `calibration: true`; the site labels it, it needs no steward, and no count of open-problem
  work includes it. `intake new` refuses the flag on the open track.

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
