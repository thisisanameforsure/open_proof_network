# F14: proposed decisions-doc amendment (v3.15)

Proposed text for Mike to apply to `docs/architecture_decisions_v_3_12.html`. The code already
behaves this way on the F14 branch. `PROTOCOL_VERSION` in `gate/opn_gate/products.py` moves to
3.15 in the commit that lands this edit, not before.

## D-6, the "Listed is not claimable" paragraph

Replace the bolded sentence and its continuation with:

> **Listed is claimable.** The root appears on the frontier immediately and may be claimed and
> worked on at once. The fidelity grade (D-9) and the D-10 posting are recorded and shown, and
> they decide who must look at a proof (D-4 step 9), not whether work may begin. Only a closed
> status or a frozen upstream statement refuses a claim.

## D-33, the status list

Replace "`listed` (root published, not yet claimable — D-6/D-9)" with "`listed` (root published
and claimable; not yet declared active by a curator — D-6)".

## D-4, step 9

Replace "or its D-10 registry provenance" with "or recorded catalog evidence about the statement
scoring at least five points (B+), pinned to the root as it stands". Add: "Where a statement came
from is not by itself evidence that it says what the conjecture says."

## D-9, a note

> A conjecture may carry several Lean formalizations. A second formalization lives beside the
> root, is never a frontier node, and is linked to the root by an equivalence exhibit. An
> equivalence is evidence shown on the target page; it does not raise the fidelity grade or
> satisfy step 9 by itself.

## D-10

Add: "Registry inheritance supplies the statement and its provenance. It does not waive step 9;
the catalog evidence record does, at five points or more."
