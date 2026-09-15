# F15 design record — stewards, digestion, and mathematicians' own problems

Date: 2026-09-15. Produced by a grilling session with Mike, four rounds, every proposal agreed
(Q2 and Q9 as amended by Mike's answers, Q10, Q11 and Q17 as below).

**Status, 2026-09-15: agreed, not acted on.** Nothing in the decisions doc, a spec or the code has
changed yet. The order of work at the end is what acts on it.

Source documents this rests on:

- `docs/research_math_and_ai_2026-09.html` (renamed from `research_digestion_2026-09.html`) — the
  2026-09-12 research note on the mathematical community's objections to AI proofs, with amendment
  candidates A1–A5. Three things in it had gone stale by this session: A5 landed as decisions v3.13
  (alternate proofs); "F13 — Digestion" is now F15, F13 being the fast check and F14 the registry
  wave; and its assumption that the five listed Erdős targets stay unclaimable no longer holds —
  after F14, 23 of 24 live targets are claimable.
- `docs/architecture_decisions_v_3_12.html` — D-6 (curated intake), D-9 (fidelity), D-10
  (upstream before proving), D-21 (role separation), D-32 (the writer role).

## The tension Mike opened with

Mathematicians need a way to take ownership of a conjecture, but the system has to be shown to work
before it is offered to them. Resolved as: prove the pipeline on known results (item 1), talk to
mathematicians quietly in parallel (item 3), and make the steward rule the thing that opens open
problems once the pipeline is proved (item 2).

## Settled decisions

1. **"The system works" is a calibration run on known results.** Three Erdős problems that are
   solved in the literature and have no Lean proof (the seed catalog lists 30, e.g. #4, #69, #1050),
   graded easy, medium and one that needs a skeleton. Pass: fresh agents carry all three through the
   pipeline with no owner or Claude intervention, at least one reaches `resolved`, and any failure
   leaves typed records (D-13). Calibration targets need no steward (D-6's second-class track).
2. **Open problems need a steward to be claimable — but not yet.** The permanent mechanism is a new
   claimability reason in `intake.claimability` (no steward on an open-problem target), which needs
   the amendment, a steward record and a re-pin. It goes live only after item 1 passes. Until then
   the 23 claimable targets stay claimable; Mike accepted that exposure, mitigated by publishing the
   new site copy early. No per-target freeze pull requests.
3. **Outreach is Mike's, and quiet.** One-to-one conversations with mathematicians start now, framed
   as review of the protocol, not a launch. The public D-27 post (Lean Zulip, erdosproblems forum) is
   drafted with Claude once item 1 passes.
4. **A mathematician's claim is a steward.** The word "claim" stays the prover's (D-19). A steward
   commits in advance to best-efforts digestion and write-up of whatever closes on the problem —
   A1, the D-32 writer appointed at listing rather than at resolution.
   - **No reservation of any kind.** Neither an outside reservation request (A1's comment-window
     idea) nor a steward's power to pause their own problem.
   - **Commitment:** best efforts to understand and write up; sign the closing proof's explainer
     (A3). No deadlines. A steward may step down publicly at any time; with no steward left the
     problem is unclaimable until replaced.
   - **Gets:** named on the target page; the D-32 write-up role and its credit; an @mention on
     GitHub when anything merges on the problem (no email stored).
   - **Many stewards, as equals.** One is enough to open a problem; all are named and hold the
     writer role jointly. Paper coauthorship already follows the ledger under D-32.
   - **The steward record is D-32's stake.** D-32 becomes "appointed at listing, confirmed or
     replaced at resolution or dormancy".
   - **Identity:** real identity only. An institutional homepage or ORCID links the GitHub account;
     the steward signs the record by pull request with SSHSIG (the fidelity-signature machinery);
     a curator checks the link.
5. **Signing or proving, per person (Q17 option b).** Mike's instinct was that the steward should be
   the one who checks the Lean statement matches the conjecture — they are the domain expert, and a
   qualified non-author signer has been the bottleneck (F11 step 5). The risk is the prover's
   incentive toward a weaker statement (Aletheia's 50 vacuous solutions; AlphaProof Nexus's density
   swap), and later discovery comes after a public false "resolved". So: **whoever signs a
   statement's fidelity takes no proof credit on it.** A steward chooses to sign or to prove. A
   proving steward leaves significance and the authorship threshold to the other stewards. A sole
   steward who wants to prove needs another signer before the problem opens. This replaces D-21's
   blanket writer-may-not-prove exclusion for stewards.
6. **Digestion is a target-level fact (A2).** Targets show "resolved — undigested" until explained;
   the network announces no result before that — the rule binds Mike's outreach too: the protocol
   may be discussed freely, a result is never announced undigested.
7. **Signed explainers (A3).** A signature affirms "I can explain this proof without the tool that
   produced it". Only signed explainers count toward the digestion state.
8. **Mathematicians can add their own problems.**
   - **Informal is enough.** A proposal is a statement in ordinary mathematics with references.
     Writing the Lean is an open task anyone may take, agents included; the proposer then checks the
     Lean against their conjecture, and because they did not write it their signature is a
     non-author fidelity signature.
   - **The proposer is steward by default** and may decline; a stewardless proposal is listed and
     unclaimable.
   - **Intake stays curated (D-6).** The proposer supplies the prior-art evidence; a curator checks
     it and the other artifacts. The Stage 0 domain exclusions stay. D-6's source table gains a top
     row: open problems proposed by a steward.
   - **Public problems only.** The form says plainly that listing publishes the problem. A proposer
     may ask to skip upstreaming to Formal Conjectures (D-10's fail-open clause), never for privacy.
   - **Channel:** a GitHub issue form on the graph repository (statement, references, why believed
     open, area, will-you-steward). Issues are not commits, so the graph's history stays mathematics.
     The site's Docs page links it.
9. **Site copy.** Written for a sceptical mathematician who has just read the 2026-09-11
   declaration. The home page leads with what goes wrong with AI-only proofs, what this project does
   about some of it, and what AI brings when humans stay involved and use the extra compute. Evidence
   is dated external examples only (Erdős #1196's eight-author paper, Tao's Sendov digestion ~90k to
   ~15k lines, the unit-distance companion paper) — no network numbers until item 1 passes. The first
   count becomes "explained: n of m". The Docs page gets a paragraph on the Leiden Declaration plus a
   compliance table (no formal endorsement until the D-24 entity exists) and an honest line that the
   network has no answer for students. The "spare subscription credits advancing real mathematics
   tonight" line leaves the decisions doc.
10. **Erdős problems stay first priority, through stewards.** Known-result Erdős problems are the
    calibration pool.

## F15 scope

- **In:** decisions v3.17 (A1–A3, items 4–8, the D-6 row, the D-21/D-32 changes); the steward
  record and its schema; the no-steward claimability reason; the digestion state on the next
  `target-status` and `targets-index` versions; signed explainers; merge @mentions; the problem
  proposal issue form and its intake path; the site copy.
- **Deferred:** A4's adoption list and generated-vs-explained wording; blueprint rendering and
  leanblueprint export; reuse counts; the unused-hypothesis report; the prior-art search as a graph
  artifact. None has a consumer until a target closes.

## Order of work

1. Decisions v3.17 amendment — to Mike for review.
2. Site copy (home, Docs, Leiden paragraph and table) — to Mike for review.
3. F15 spec, then build; in parallel, intake of the three calibration problems and the unattended
   agent run.
4. After the calibration passes: re-pin with the no-steward rule live; draft the Zulip post.
