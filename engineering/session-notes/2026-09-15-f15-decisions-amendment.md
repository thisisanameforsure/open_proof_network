# F15: proposed decisions-doc amendment (v3.17)

Proposed text for Mike to apply to `docs/architecture_decisions_v_3_12.html`, drafted from the
design record `engineering/session-notes/2026-09-15-stewards-and-digestion.md` against the doc as
it stands at v3.16 (network `6bcfbce`). Nothing here is decided until Mike approves it.

**Code and doc will disagree for a while, on purpose.** The doc leads and the code follows (as for
v3.12): no code enforces a steward yet, and the design record holds the no-steward claimability
rule back until the calibration run passes. `PROTOCOL_VERSION` in `gate/opn_gate/products.py`
stays `3.16` until F15's first code task lands, and moves to `3.17` in that commit.

Items marked **[not settled in the grill]** fill a gap the grill did not cover; each is listed again
at the end for a yes or no.

## The version line (header meta)

Append after the v3.16 clause:

> ; v3.17 gave open problems stewards: a named mathematician must commit to digest and write up a
> problem's result before it can be claimed, mathematicians may propose their own problems, a
> fidelity signer takes no proof credit on the target, explainers may be signed as a comprehension
> claim, and a resolved target shows its digestion state and is never announced before its paper
> (D-3, D-6, D-9, D-10, D-21, D-22, D-27, D-32, D-33, D-36, Stages)

## Overview, "Who participates", the role table

Add a row after Writer:

> **Steward** — A mathematician who commits, before an open problem can be claimed, to understand
> and write up whatever the network produces on it; checks the Lean statement against the
> conjecture or proves on it, never both; holds the writer role for that problem

## D-6

**1. The claimability sentence.** Replace

> Only a closed status or a frozen upstream statement refuses a claim.

with

> Only a closed status, a frozen upstream statement, or — on an open-problem target — the absence
> of a steward (D-32) refuses a claim (v3.17).

**2. A new paragraph after "Then the target opens directly…":**

> **v3.17 — stewards and proposals.** An open-problem target is claimable only while it has at
> least one steward (D-32). A listed target without one is published, on the frontier and open to
> fidelity review, but refuses claims. On-ramp and calibration targets are exempt: they exercise
> the protocol, not the mathematics.
>
> A mathematician may propose a problem. A proposal states the problem in ordinary mathematics,
> with references, why it is believed open, its area, and whether the proposer will steward it.
> It is filed through the graph repository's proposal form, an issue and never a commit. The
> proposer need not write Lean: formalizing the statement is open work that anyone may take,
> agents included. The proposer supplies the prior-art artifact (item 1). A curator checks it,
> attaches the other four as for any target, and applies the exclusions below. The proposer
> becomes the target's steward unless they decline.
>
> Listing publishes the problem. A problem its proposer wants kept private is declined, never held
> back.

**3. The source table.** Add a first row:

> **Open problems proposed by a steward (v3.17)** — A mathematician who will digest the result is
> attached from the first day, and the problem is one its own community put forward rather than
> one chosen for tractability

**[not settled in the grill]** In the Erdős row, replace the "Why" text "The mission; AlphaProof
Nexus and Astra's demonstrated resolution regime; inherited statement lowers intake cost" with:

> The community whose practice the network follows (prior-art search, human write-ups, "not a
> benchmark"); inherited statement lowers intake cost; claimable only with a steward (v3.17)

The research note's §6 is the reason: as written, this row names the lab resolution regime as the
motive.

**4. The on-ramp row.** Replace "recently arXiv'd results awaiting formalization" with

> results already known — recently arXiv'd results awaiting formalization, and problems solved in
> the literature with no Lean proof yet (v3.17: the calibration pool, e.g. solved Erdős problems)

The calibration run the design record names uses solved Erdős problems from 1935–1989. Without this
edit they fit no row.

## D-9

Add a paragraph after "Signatures are counted and named…":

> **v3.17 — a signer does not prove.** Whoever signs a root's fidelity certificate takes no proof
> credit (D-19) on that target. A prover gains from a statement slightly weaker than the conjecture,
> and the costly failures of 2026 were exactly that: statements misread into vacuity, or one kind of
> density swapped for another. A defect found after the fact comes after a public "resolved". A
> steward (D-32) who did not write the target's Lean is a non-author signer. A steward chooses to
> sign or to prove. A problem whose only steward proves needs another signer before its grade can
> rise.

**[not settled in the grill]** The record says "no proof credit on *it*". The draft says *on that
target*, because every interior node is proved in service of the root, so the incentive covers the
whole target.

## D-10

**1.** Append to "Upstream before proving":

> v3.17: the steward who proposed a problem (D-6) may ask that its statement not be contributed to
> Formal Conjectures. The curator then publishes it in-network with equivalent visibility under the
> fail-open condition below. The request buys no privacy.

**2.** Replace "Report back. Resolutions (proof, refutation, vacuity) are reported to the source
registries." with

> Report back. Resolutions (proof, refutation, vacuity) are reported to the source registries, and
> the report states the target's digestion state (D-33 v3.17), so a source reads "kernel-checked,
> not yet explained" rather than "solved".

## D-21

**1.** Replace the Writer row with:

> **Writer or steward (D-32)** · Does: authors the target's paper or state-of-the-problem note;
> proposes retrospective significance (D-19) and the contribution statement · May not: hold the
> adjudicator role on that target; claim proof credit on it after signing its fidelity (D-9
> v3.17); propose significance or the authorship threshold while holding proof credit on it

**2.** Replace the closing sentence "The writer-proving exclusion follows the same logic on the
credit side: the person proposing everyone's significance must not be adding to their own share
while doing it." with

> The same logic holds on the credit side, split in v3.17 into two exclusions. The person who signs
> what a statement means must not profit from proving it. The person who proposes everyone's
> significance must not be adding to their own share while doing it. A steward may do one of each
> pair, never both.

## D-22

Replace the seeding bullet "Write-up (D-32): not seeded in advance. Appointed per target, from
among that target's existing statement-line credit holders and curators, when the target resolves
or is declared dormant (D-33)." with

> Write-up (D-32, v3.17): seeded in advance on open-problem targets, as stewards recruited from the
> problem's source community or arriving with their own proposal (D-6). Confirmed or replaced when
> the target resolves or is declared dormant (D-33). On other targets, appointed then from among
> the target's statement-line credit holders and curators. A curator checks a steward's identity
> against an institutional page or ORCID record that links their GitHub account.

## D-27

**1.** In the Rationale, replace "the recruitment pitch — spare subscription credits advancing real
mathematics tonight — dies at a cold Mathlib build or a prose-only protocol" with

> spare proving compute is useless if it dies at a cold Mathlib build or a prose-only protocol

**2.** In "Human funnel", replace "(reviewers, curators, adjudicators, writers)" with

> (stewards, reviewers, curators, adjudicators, writers)

and add at the end:

> v3.17: the human funnel's front door is the problem proposal form (D-6) and a page that says
> plainly what a steward commits to and receives (D-32).

## D-32

**1. The lead paragraph.** Replace "Every target that resolves or is declared dormant (D-33) gets
a writer: one real-identity mathematician, appointed by the target's curators under D-22, who owns
the human-facing account of what the network did." with

> Every open-problem target has stewards from before it can be claimed. They are one or more
> real-identity mathematicians who commit to understand and write up whatever the network produces
> on it, and who hold this role jointly (v3.17). Any other target that resolves or is declared
> dormant (D-33) gets a writer: one real-identity mathematician appointed by the target's curators
> under D-22. Either way, the role owns the human-facing account of what the network did.

**2. Append to the Rationale:**

> v3.17: appointment at resolution produced an undigested certificate first and looked for a
> reader afterwards, which is the practice 25 Fields medallists condemned on 2026-09-11 ("without
> the willing mathematicians who must take care of their development … AI-conceived ideas would
> never become fully alive"). Appointing at listing is the adoption norm run in advance, and it
> limits open-problem intake to the number of mathematicians willing to receive it.

**3. Append to "Overturns if":**

> v3.17: if the steward rule has been in force for a quarter and no open-problem target has gained
> a steward, the rule returns to this document. It is never quietly relaxed by making stewardless
> targets claimable.

**4. "Stake required."** Append:

> v3.17: on an open-problem target, the signed steward record is the stake. A replacement steward
> at resolution or dormancy meets the rule above.

**5. "Exclusion from appointment onward."** Replace its first sentence with

> A writer or steward is bound by D-21 v3.17. They never hold the adjudicator role on the target.
> They take no proof credit on it after signing its fidelity (D-9). While they hold proof credit on
> it, they take no part in proposing significance or the authorship threshold.

**6. A new detail rule after "Exclusion":**

> **Stewards, exhaustively (v3.17).**
>
> *Commitment:* best efforts to understand and write up anything that closes on the problem, and a
> signature on the closing proof's explainer (D-3). There is no deadline. A steward steps down by a
> signed record at any time. A target left with no steward refuses claims until one is found.
>
> *What they receive:* their name on the target page, this role and its credit, and a mention on
> the graph repository whenever anything merges on the target (no email is kept).
>
> *What they do not receive:* no power to pause the problem, and no reservation of it by anyone.
>
> *How many:* any number, as equals, and one is enough. A steward record is signed with the
> contributor's SSH key and submitted by pull request.
>
> **[not settled in the grill]** If every steward holds proof credit on the target, its curators
> propose significance and the threshold in their place.

**7. "The writer proposes, the ledger decides."** Replace "set by the writer, published with the
draft" with

> set by the writer or, jointly, by the stewards entitled to propose it (above), published with
> the draft

## D-3, Explainers

Append to the Explainers paragraph:

> **v3.17 — signed explainers.** An explainer may carry a signature by a real-identity contributor
> affirming one sentence: *I can explain this proof without the tool that produced it.* The
> signature claims nothing about the mathematics and changes no verdict. Its signer is accountable
> under D-22, and a signature its signer cannot stand behind is a D-17 ground (iii) matter. Only
> signed explainers count toward a target's digestion state (D-33).

## D-33

**1. The status sentence.** After "listed (root published and claimable, not yet declared active
by a curator — D-6, v3.15)", insert

> — on an open-problem target, claimable only with a steward (D-6 v3.17) —

and in "every node stays claimable", insert "(subject to D-6 v3.17's steward rule)".

**2. A new paragraph after the lead:**

> **v3.17 — digestion state.** Beside its status, a resolved target carries one of three states:
> `undigested` (the root is closed and nothing more), `explained` (every node in the closing
> proof's dependency closure carries a signed explainer, D-3), or `written-up` (the D-32 paper or
> note is published). `resolved` stays the kernel's fact and is never delayed. What changes is the
> claim. The network shows such a target as "resolved — undigested" until its state moves, and makes
> no announcement of a result beyond the D-10 report-back, which carries the state, and the D-32
> paper. Hiding the certificate until it is explained was considered and refused: the graph is
> public and the kernel's verdict is a fact.

## D-36

**1. The Home row.** Replace "what the network is; live counts — targets, nodes proved, frontier
size, refuted routes, resolved and partial variants." with

> what the network is and what it refuses to do (no announcements, no leaderboard, failures
> published); live counts led by explanation coverage — proved nodes carrying a signed explainer,
> of all proved nodes (v3.17) — then targets, nodes proved, frontier size, refuted routes, resolved
> and partial variants.

**2. The Target row.** After "status (D-33)", insert "its stewards and digestion state (v3.17)".

**3. The Node row.** Replace "the explainer, labeled unverified, with its author and drafting
model" with

> the explainer, labeled unverified, with its author and drafting model, and its signer where one
> has signed (D-3 v3.17)

**4. The Docs row.** Append:

> ; how the network stands against the Leiden Declaration, recommendation by recommendation; what a
> steward commits to and receives, and a link to the proposal form, which lives on the graph
> repository and not on this read-only site

## Stages

Append to Stage 0:

> v3.17: the steward rule (D-6, D-32) is enforced only after a calibration run on known results
> passes: fresh agents, with no intervention by the founder or the build, carry three solved
> problems from the literature through the pipeline. At least one must reach `resolved`, and any
> failure must leave a typed record (D-13). Until then, the open-problem targets listed under v3.15
> stay claimable. The public Stage 0 post leads with this amendment.

## Glossary

Add:

> **Steward** — a mathematician attached to an open problem before it can be claimed, who has
> committed to understand and write up whatever the network produces on it. Holds the problem's
> write-up role; signs its statement's fidelity or proves on it, never both.

> **Digestion state** — beside a resolved target's status: `undigested`, `explained` (every node of
> the closing proof has a signed explainer) or `written-up` (the paper is out). The kernel decides
> "resolved"; people decide "understood".

Replace the Explainer entry's last sentence "Earns write-up credit; shown on the website under a
fixed 'unverified' label." with

> Earns write-up credit; shown on the website under a fixed "unverified" label. May be signed by a
> contributor who can explain the proof without the tool that produced it; only signed explainers
> count toward digestion.

## For Mike: yes or no on each gap

1. **D-6 Erdős row:** replace the "demonstrated resolution regime" rationale (text above)?
2. **D-9:** a fidelity signer takes no proof credit on the *whole target*, not only the root node?
3. **D-32:** when every steward proves, curators propose significance and the authorship threshold?
4. **Not in this amendment, spotted while drafting:** D-9 still says "No proving compute is
   allocated below screened-and-signed", which v3.15's "listed is claimable" contradicts. Fix
   separately?
5. **Not in this amendment:** the Overview still says the proving population uses "spare
   subscription credits". That is a fact about who proves, so the draft leaves it; only D-27's
   "tonight" pitch goes.
