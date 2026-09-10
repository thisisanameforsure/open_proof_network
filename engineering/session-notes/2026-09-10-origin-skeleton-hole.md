# A skeleton hole gets its own origin — the v3.12 design record

Date: 2026-09-10. Produced by a working session with Mike; every call below was his, taken with
the costs on the table. Nothing here overrides a decision — it is the record the v3.12 amendment
is written from, plus the two things it changes outside the architecture document.

Source documents this rests on:

- `docs/architecture_decisions_v_3_12.html` — D-3 (node layout), D-12 (five artifacts), D-25
  (frontier fields), D-28 (tool surface), D-29 (emergent decomposition), D-31 (skeletons), D-34
  (schemas versioned, never edited).
- `engineering/specs/features/F07.html` — R6 and AC8, which already carry the mechanism and only
  name the wrong value for it.
- `engineering/specs/conventions.html` §6, §7 — the git protocol and the spec format.

## What this fixes

The protocol contradicts itself about what a node's `origin` is, and the contradiction blocks
F07-T4, the task that turns a partial proof's holes into graph nodes.

D-25 publishes four origin values on the frontier — `authored`, `compiler-derived`, `variant`,
`skeleton-hole` — and its own worked example is an operator filtering for *"unattempted skeleton
holes on target X with no `missing-library` failures"*. D-3 lists three. D-31 says flatly that
skeleton holes carry `origin: authored`, and D-12 says artifact five has *"authored rather than
compiler-derived holes"*.

The consequence is not a wording defect. `skeleton-hole` is a legal value in `graph/v1.json` and
`frontier/v1.json`, but the products copy META's value verbatim and no META schema accepts a
fourth value, so **nothing can ever emit it**. D-25's filter cannot be written. Fixing only the
prose would leave a schema value no code could ever set.

## Settled decisions

1. **Four values, not three. `skeleton-hole` stays and D-3, D-12 and D-31 are corrected to it.**
   `authored` is already overloaded, and the overload is load-bearing: it covers roots, which earn
   statement-line credit under D-19 and need a D-9 fidelity certificate, *and* skeleton holes,
   which get neither. If skeleton holes stay `authored`, reading `origin: authored` no longer
   tells you whether a node earns statement credit or needs fidelity review, and the field stops
   answering the question it exists for. Splitting is also information-preserving: a consumer that
   does not care can map the fourth value back onto `authored` at read time, and the reverse is
   impossible.

2. **The discriminator is the annex citation, and it lives in the Lean file.** D-31 already
   requires that a skeleton name the annex it was derived from by hash, and calls that naming *"the
   mechanical citation D-14 mechanism 3 has never had"*. That citation had no home anywhere in the
   built system. It becomes a comment line in the skeleton file, mirroring the `-- relation:` line
   that `gate/opn_gate/graph.py` already parses for a variant's D-30 label. The file rather than
   the submission block, because F07-Q9 settled that the block is a declaration and the file is
   the evidence, and because a hand-opened pull request carries no block at all. So: **a partial
   whose file cites an annex hash yields `skeleton-hole` children; one that cites none yields
   `compiler-derived` children.** The cited annex must exist in the node, or the gate rejects —
   F07-AC8 already says so.

3. **The abuse surface is frontier noise, and D-25 already prices it.** Deriving `origin` from a
   submitter-supplied citation makes the value partly submitter-influenced: someone could cite a
   throwaway annex to get the nicer label. It buys them nothing. Both kinds of hole earn zero
   credit, annexes are capped and content-hashed and earn nothing ever, and the cited file must
   actually be there. The only effect is a frontier filter label, and frontier noise is exactly
   what D-25's self-selection and the D-25 starvation series already price. Written down here
   rather than left implicit, because it is the first thing a reader will object to.

4. **A sixth artifact type was considered and rejected.** D-12's headline is that there are five
   artifacts and that skeletons *are* partial proofs. A sixth `artifact_type` would also carry no
   type-level consequence, since `gate/lean/OpnGate/ArtifactType.lean` expects the same declared
   type for a skeleton and a partial either way. The annex citation does the same work and makes
   D-31's existing citation requirement enforceable instead of aspirational.

5. **META's enum is widened by adding `meta/v3`, never by editing v1 or v2.** D-34 is explicit
   that schemas are versioned and never edited, and `gate/schemas/HASHES` pins every file's
   sha256. `graph/v1` and `frontier/v1` already carry four values and are not touched at all.

6. **This commit makes `skeleton-hole` legal; F07-T4 makes it emitted.** `scaffold.py` keeps
   writing `meta/v2` and keeps its three-valued `Origin` literal. Widening both belongs to F07-T4,
   which is the task that creates children from partials and is blocked on F08-T1.

7. **This rides in v3.12 alongside the D-9 rung, which a parallel session landed first.**
   *Corrected 2026-09-10, after the fact.* This note was first written planning to defer the D-9
   amendment to v3.13, because renaming its second rung forces new versions of two hash-pinned
   schemas — `target-status/v1.json` and `targets-index/v1.json` — plus their fixtures, goldens
   and five rows in F11. While that was being planned, another session landed `db9fd5c`, which
   renamed the document to v3.12, made the rung `screened-and-signed`, and deferred exactly that
   schema bump to F11 under F11-Q6, *"the rung rename is a schema bump, not an edit"*. Same
   reasoning, applied one layer down. So the origin change folds into the same v3.12: that version
   is unpushed, no `gate-spec.json` pins it, and the live graph's `info.json` still reads `3.11`,
   so nothing outside this laptop has seen it. A v3.13 whose only content is one enum value would
   buy a second rename and a second golden regeneration for no reader.

## What this does not do, and what it leaves for others

- **F08-Q2 was wrong in its reasoning and right in its conclusion, and is reworded here.** It
  justified making `speculative` a status record rather than an origin *"since D-3's origin set
  has no fourth value"*, and `gate/opn_gate/scaffold.py` repeated that reasoning in a docstring.
  D-3 now has a fourth value, but it is `skeleton-hole`, not `speculative`, so the conclusion
  holds and only the justification needed fixing. Both were uncommitted when this work started and
  had landed as `c9e1e5d` by the time it was written, so both are corrected in the same commit —
  this change is what made them stale, so repairing them is not a drive-by.

- **The graph repository's `README.md` still points at `docs/architecture_decisions_v_3_10.html`**,
  stale since before this change. AGENTS.md limits build work in that repository to the files D-35
  places there — `gate.yml`, `schemas/`, seeded targets and nodes — so a README fix is out of
  bounds here. Fix it in the re-pin commit, which is a legitimate touch.

- **No push and no re-pin.** Twelve commits are unpushed and F06 is blocked on a GitHub App
  permission; pushing deploys, and the deploy is half-blocked. Until the re-pin,
  `gate/tools/check_products.py` will report drift against the live graph, whose committed
  `info.json` still says `3.11`. That is expected and refreshes on the first merge after the
  re-pin.

## Order of work

1. Make the five marked edits in `docs/architecture_decisions_v_3_12.html` — D-3, D-12, D-28,
   D-31, and D-9's scope-exemption bullet — and widen the v3.12 masthead clause to name them. The
   rename and its blast radius, `PROTOCOL_VERSION` included, already landed with `db9fd5c`.
2. Add `gate/schemas/meta/v3.json` with the four-value enum, pin it in `HASHES`, accept it in
   `layout.META_SCHEMAS`, and amend F07-R6, F07-AC8 and F11-R8 to name `skeleton-hole`, recording
   the call as F07-Q13.
3. Leave F07-T4 to widen `scaffold.py` and emit the value, once F08-T1 is committed.

F07-T4 does not start before F08-T1 lands.
