# F33 grill — attack-first statement review (2026-10-29)

Source: the owner's reading of erdos-257's review (2026-10-28: eight trivial mutant questions,
false "small case checked" wording, a meaningless source flag), the research note
`docs/research_statement_faithfulness_2026-10.html` (report `reports/Testing formal statement
faithfulness.md`, notes under `research_notes/Testing formal statement faithfulness/`), and this
grilling. The owner's rulings, in order:

1. **A new feature, F33, with decisions v3.50** amending D-9 and D-11 (and D-28/D-35 for the
   routes). F26's records, schemas and page stay; F33 supersedes its mutation and question stages.
   F32 and v3.49 are held by the carried-proofs session (`opn-f32-carried-proofs`); claim F33 and
   v3.50 on main in one small commit before building.
2. **Network-paid attacks** (the owner: "lets use aristotle and opn-prove"), plus **everything
   programmatic in the gate**. Two tiers: the gate tier (tactics `decide`, `norm_num`, `simp`,
   `grind`, `aesop`, `plausible`; instance probes; witnesses; hazard and vacuity checks;
   equivalence by term) and the paid tier (Aristotle or an OpenRouter model) for what the gate
   tier leaves open. Aristotle's terms: §2.2 forbids *sharing* a credential; a network-owned key
   used only by the network's own job is not shared (F17-Q6 read the terms for contributors).
3. **Budget**: gate tier 300 s per check, 40 checks per target per run; paid tier 10 tasks per
   target per run, 30 min wall clock each; **$50 a month** network-wide in `policy.json`. When it
   is spent the owner is told (one GitHub issue per month on the network repo, assigned to the
   owner, updated not duplicated, and a line on a curator's `/me/`), and **the remaining work goes
   to agents** as claimable work. Every paid call is logged with its cost (the F13 call log's
   shape). The first run (the 27 re-opened reviews) draws on the first month's $50.
4. **Claimable review work** generalises F26's pair proofs: `pair-proof` becomes `review-proof`
   with a kind (settle, equivalence, witness, consequence), one list (`list_open_review_work`,
   `GET /reviews/<t>/open`), one gate verdict, one credit line. The frontier stays mathematical.
5. **Variants**: as the research recommends — filtered syntactic edits (one per meaningful
   position: binder domains, hypotheses, quantifiers, relations, constants not verbatim in the
   source words; an arid list for forced coercions, instance arguments, names), concept
   substitution for vacuity, **plus up to 5 model-proposed misreadings** in the paid tier; every
   variant settled (proved, refuted, separated at an instance, proved equivalent) before any
   question; survivors collapsed to the roots of the strength DAG.
6. **Questions**: only on a real fork, three shapes (instance verdict, fork, idle part), each about
   one concrete object with a kernel verdict; exits "the source does not settle this" (→ a D-30
   variant) and "skip"; a structured reading checklist (typed rendering, a line per binder,
   quantifier, limit/density notion, constant) signed as part of the signature; no source flag on
   answers (sources live on the target and on known-case tests); signing with questions waiting
   is allowed and the signature records what was open. **Hard cap**, as panel settings in
   `policy.json` (F24's pattern): `review_questions_per_steward` = 3, `review_questions_max` = 9,
   questions assigned one steward each, spread evenly; a review carries the settings it was
   opened under.
7. **Several stewards**: any active steward of the problem may answer any question (login
   recorded); one steward's intent signature suffices; conflicting answers make a fork that
   becomes a variant, and block a grade until resolved.
8. Binder lifting (every leading `∀`) and instance probes on any type (∅, singletons, finite and
   cofinite sets, 0, 1, −1, ½, constant and identity maps), the degenerate-value checks and the
   hypothesis witness on every root — mechanical, specified without a ruling.
9. **Migration**: re-open all 27 reviews under F33 (`supersedes`), one curator commit plus a run;
   the old 191 questions read "superseded, not asked".
10. **Canaries (D-11)**: built, behind a `policy.json` switch, **off** until a problem has three or
    more stewards.
11. **Known-consequence tests**: the paid tier drafts up to 3 known cases with citations; a
    steward confirms each citation before the test counts; `consequence` is also always open as
    claimable `review-proof` work. A consequence test without a confirmed source never counts.
12. **Prototype first** (one worktree agent, read-only against the graph): how many of the 191
    live mutants the gate tier settles alone, and the cost and time of ~10 paid tasks on the
    rest; its numbers set the spec's caps.
13. **Prover as a setting**: `policy.json` `review.prover` = `{"provider": "aristotle"}` (default)
    or `{"provider": "openrouter", "model": "<id>"}`; keys `ARISTOTLE_API_KEY` /
    `OPENROUTER_API_KEY`, held only by the gate's post-merge review job, never a pull-request job
    (C8). With no key the paid tier dry-runs and logs what it would have sent.

Build plan (proposed, wave by wave): 0 prototype; 1 contract by the lead (claim F33/v3.50,
spec, schemas `review-proof/v1`, `review/v2` and the question/answer bumps, `policy.json`
settings); 2 four worktree agents (gate tier; paid tier job, budget, issue, misreadings and known
cases; service and MCP; site); 3 live by the lead (merge, re-pin, re-open the 27, watch the first
paid run).

Keys stored 2026-10-29 by the lead on the owner's word: `ARISTOTLE_API_KEY` and
`OPENROUTER_API_KEY` live only in the graph repository's **`review-prover` environment**, whose
deployment branch policy is `main` alone, so only a job on `main` that names the environment reads
them; a repository-level secret would have reached the service's same-repository pull request
branches (C8). The paid-tier job must declare `environment: review-prover`. Build plan unchanged.

Found on the way: `.env` line 11 reads `ARISTOTLE_API_KEY <value>` with a space for `=`, which a
dotenv loader does not read.
