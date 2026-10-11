# Decisions amendment v3.35: a circularity claim is a label, and a node carries its literature status

**Status (2026-10-08): approved by the owner ("Lets go with your recommendation with circular loops"; "For
feature 3 … the agent can say it needs to be verified by a curator/steward. it should notify the
curator/stewards") and applied as decisions v3.35.**

Source: the three testers on erdos-1094 (`engineering/evidence/testers-2026-10-08/bugs.md`, P2 item 3
and feature 3), and the owner's rulings on the lead's breakdown.

## 1. D-12, D-16: a merged circularity claim labels the hole; nothing leaves the frontier

What v3.21–v3.23 built: anyone may file a `circular-decomposition` claim on a hole whose exhibit
proves, in Lean, that the hole implies an ancestor it was cut from; once merged, the hole leaves the
frontier as "not claimable, circular", and so does every node on the path whose sibling holes are
proved (v3.22).

What the erdos-1094 run showed: the exhibit exists for **every** one-hole decomposition the moment it
merges, and for the last open hole of any decomposition once its siblings are proved — the assembly
*is* the proof that the holes imply the parent. So the rule is met by D-12 #4's own `reduction`
artifact ("a primary progress mode … converts an open problem into strictly sharper open problems")
and by every honest reduction: `erdos-1094--h3--h1` is strictly stronger than `--h3` and binomial-free,
and was claimable as circular from its first minute; tester B withheld a valid partial on `--h2` for
the same reason; and had anyone proved `--h3`, the open core `--h2` would have left the frontier. The
difference between a loop and a reduction — whether the route gained anything — is a mathematical
judgment the decision text itself says no program decides.

The owner's principles (2026-09-19): published state is actual state, trackable, reversible, hard to
tamper with. Option C, chosen:

> **v3.35 — a circularity claim is a published fact, not a removal.** A merged
> `circular-decomposition` claim no longer takes its hole, or any node on the path to the ancestor,
> off the frontier. The products publish the fact the claim's exhibit proved — *a proof of this
> statement is a proof of `<ancestor>`*, naming the claim — on the hole, on every node strictly
> between it and the ancestor by v3.22's path rule, in the frontier entry (D-25) and on the site. The
> hole stays claimable. Choosing to work on it is the operator's filter, as D-25 intends; nothing
> ranks it. The ancestor stays open, as before. Nothing is rewritten: the label is derived from the
> merged claim and the proved holes, and reverting the claim removes it.
>
> The gate's part is unchanged: the exhibit is still elaborated in the sandbox and its type checked
> to be exactly the implication (v3.23), and the mechanical offload rule still refuses a hole
> definitionally equal to any statement its node reduces (`offload-restates-ancestor`).
>
> Rationale: the exhibit is met by every reduction (D-12 #4) and by the last open hole of every
> decomposition, so removal took genuine progress off the frontier and would have hidden the open
> core of erdos-1094 behind a proved literature theorem. A fact every reader can see and filter on
> costs nothing when the route is a loop and nothing when it is a reduction.
>
> Overturns if: labelled loops come to dominate a target's frontier and an operator's filter cannot
> tell a reduction from a loop by the published facts — then a steward (D-32) may retire a route by
> a signed record, and the label becomes the evidence that record cites.

D-16's class clause: "circular-decomposition (… a hole that leads straight back to an ancestor it was
meant to reduce …)" gains "; once merged it labels the hole (D-12 v3.35) and removes nothing".

The four nodes now off the live frontier under merged claims (`erdos-1050--h1-v2--h1`,
`erdos-69--h2-v2`, `erdos-69--h2-v2--h1-v2`, `erdos-69--h2-v2--h1-v2--h4`) return to it labelled, at
the first render under a pin that carries this — a second, deliberate curator commit after the re-pin
(the 2026-09-19 lesson). No record is edited.

This settles the testers' feature 2 ("a way to record a reduction that is not circular"): a reduction
is D-12 #4 as it stands, and its new node now carries the fact that proving it proves the parent,
which is what a reduction is. No new artifact.

## 2. D-25, D-3, D-32: a node carries its literature status, confirmed by a steward or curator

Today `--h2` (the open Ecklund–Selfridge core) and `--h3` (Granville–Ramaré 1996, Konyagin 1999, never
formalised) both read "open". A contributor cannot tell the two apart from the frontier, and three
testers asked for the distinction independently.

> **v3.35 — literature status.** Any contributor may append a **literature record** to a node,
> `nodes/<id>/literature/<ts>-<pseudonym>.yaml`, saying what the literature says of the statement:
> `status` one of `open` (no proof is known), `known` (a proof is published and not formalised), or
> `elementary` (a routine formalisation of a known fact), with the references that support it and a
> short summary. It is a claim about the literature, attributed like an annex (D-23), and it earns
> nothing on its own.
>
> A record is **unverified** until a steward of the target or a curator **confirms** it, by a record
> of their own that names it, signed with their SSH key or through the site by the approval key
> (D-32 v3.33). The products publish the latest confirmed status as the node's `literature`, and the
> latest unconfirmed one as `literature_proposed`, each with its record; the site shows a confirmed
> status as a fact and an unconfirmed one as *"proposed by `<contributor>`, awaiting a steward or
> curator"*. A later confirmed record supersedes an earlier one; a confirmation never edits what it
> confirms.
>
> **Stewards are told.** A steward's page (`/me/`, D-32 v3.33) lists every unconfirmed literature
> record on the targets they steward, and a curator's lists every one on the graph, each with a
> confirm control; the record's pull request names the target's stewards. That is the notification:
> the record is on the graph the moment it merges, and the person whose judgment it waits for sees it
> the next time they sign in.
>
> A literature status is a published fact about the literature, never about difficulty (D-25): it
> says what is known, not what is easy. It changes no status, blocks nothing and ranks nothing.
>
> Rationale: three testers on erdos-1094 could not tell the open core from a literature theorem on
> the frontier; the person placed to say which is which is the one D-32 appoints to understand the
> problem.
>
> Overturns if: confirmed statuses are found wrong at a rate that misleads provers — then confirmation
> moves to the fidelity reviewers of D-9.

D-3's node layout gains `literature/         # what the literature says of the statement, and its confirmation (D-25 v3.35)`.
D-25's frontier field list gains "literature status, confirmed or proposed (v3.35)".
D-32 gains, under the steward's duties: "confirms or corrects a node's proposed literature status (D-25 v3.35)".

## What follows in the build

- F08 (gate, claims): the claim's consequence becomes a derived label; `graph/v6` with `circular`
  on the node (`[{ancestor, claim}]`), cause `circular` retired; `frontier/v5` with `circular` and
  `literature`/`literature_proposed`; `context/v5`.
- F03 (products): membership no longer keys off the claim; the four live nodes come back.
- F04 (site): the label on node and problem pages, the key loses the circular state and gains the
  label; the literature status and its "proposed, awaiting" form; `/me/` lists what waits.
- F05/F23 (service): `POST /literature` (append), `POST /literature/confirm` (steward or curator,
  approval key), the MCP tools and `get_node` fields.
- F09: MCP schema versions.
- The re-pin, then the re-render commit, are the owner's.
