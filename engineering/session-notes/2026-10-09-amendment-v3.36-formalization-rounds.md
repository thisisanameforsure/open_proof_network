# Proposed decisions amendment v3.36: formalization rounds, intent tests and two signatures

**Status (2026-10-09): drafted, not approved, not applied.** Items in §8 are open for the owner.

Source: the owner's conversation of 2026-10-07 to 2026-10-09 on turning an incoming conjecture into
Lean and checking that the Lean says what the conjecture says, read against
`docs/research_statement_fidelity_2026-09.html` and D-9 as it stands at v3.35.

The owner's rulings:
- humans write their own formalizations, not only AIs;
- agents do most of the work, and their main job is to **throw away bad formalizations**;
- two humans verify, through a page that shows all the evidence;
- the determination happens **alongside** proving, not after a proof; the automated tests must pass
  first;
- small and trivial cases are checked where they fit; an LLM decides where they fit; the cases are
  written in Lean;
- equivalence between formalizations is agent work for every unverified root with several versions,
  and a proved non-equivalence is stored too;
- at least one human-written version before `expert-attested`;
- human versions may arrive until the second signature;
- a reading the signers do not choose stays as a variant, never the root, and agents may use it;
- back-translation explained and understood; its removal is §6.

The principle under all of it, from the research note §3: a machine can **refute** a formalization
soundly (a kernel-checked exhibit), and can never **accept** one. So every discard is an exhibit, and
every acceptance is a person's signature with the exhibits beside it.

## 1. D-9: the pass becomes a formalization round

What D-9 has today: one Lean statement, written by a curator, put through an ordered pass (compile,
soundness screens, grounded brief, equivalence once a second formalization exists, back-translation,
a non-author sign-off). Nothing turns an English conjecture into Lean, and nothing asks the proposer
what they meant.

> **v3.36 — a formalization round.** A root statement that arrives in words (D-6) is formalized in a
> **round**, and the round's surviving Lean becomes the root. A round has seven stages; stages 3, 4
> and 6 are agent work and emit only kernel-checked exhibits.
>
> 1. **Propose.** The conjecture in words, with whatever the proposer can give that pins it down:
>    known special cases, known small values, consequences ("for k = 2 this is Roth's theorem"),
>    non-examples.
> 2. **Formalize.** Anyone may submit a **candidate**: a Lean statement of the conjecture, with its
>    author named and, where a model helped, the model named (v3.31). Agents submit candidates from
>    several models. People submit candidates **blind**: until their own is submitted they see the
>    words, the definitions and the proposer's cases, never another candidate's Lean.
> 3. **Filter.** Each candidate is compiled, screened (prove it, prove its negation, prove False
>    from its hypotheses), and held to the **intent tests** (§2). A candidate that fails any of them
>    is **discarded with the exhibit as its reason**. A discarded candidate stays on the record; it
>    is never deleted.
> 4. **Reconcile.** Candidates are compared in pairs (§3). Candidates proved equivalent form a
>    **cluster**. Between clusters, agents look for a case on which they disagree.
> 5. **Ask.** Each proved disagreement becomes a question to the intent signer (§4), in mathematics,
>    never in Lean. The answer becomes an intent test, and stage 3 runs again. The round loops until
>    one cluster survives, or the clusters left are readings the intent signer confirms are
>    genuinely different (§5).
> 6. **Mutate.** Agents perturb the surviving cluster's representative the ways statements are known
>    to go wrong (D-11's defect classes: drop a hypothesis, `≤` for `<`, ℕ for ℝ, a quantifier
>    moved, `Set` for `Finset`). A mutant that passes every intent test shows the tests cannot tell
>    it apart, and becomes one more question (stage 5). The page reports how many mutants the tests
>    catch; it is a measure of the tests, never of the statement.
> 7. **Sign.** Two signatures (§4) on the evidence page (§7).
>
> **When work opens.** A target becomes claimable when the automated stages are complete: one
> cluster survives stage 3, and stage 6 raises no open question. The signatures arrive while proving
> goes on, and the grade rises as they do. D-4 step 9 is unchanged: a proof that would settle the
> root still asks for the certificate or a non-author approval at that moment.

Rationale: the 2026 evidence (research §1) is that a compiled statement means what was intended
about three times in four, and that sampling more does not close the gap. The only sound checks are
refutations and proved equivalences; the only judge of intent is a person. The round puts each where
it is strong.

Overturns if: rounds on real intake end with more than one surviving cluster most of the time while
the intent signer cannot say which reading is meant. Then a round cannot settle intent, and intake
returns to a curated statement with the round's exhibits attached as evidence only.

## 2. D-9: intent tests

> **v3.36 — intent tests.** An intent test is a Lean statement about the conjecture that any
> acceptable formalization must satisfy: that it holds at n = 3, fails at n = 1, implies the known
> k = 2 case, says nothing vacuous on the empty set. Each test is run against every candidate by
> computation (`decide` and its kin) or by a proof attempt within a budget, and its result is an
> exhibit.
>
> **Small and trivial cases.** A model may choose which small, degenerate or boundary cases suit the
> statement, and write them in Lean; choosing a test is not a verdict, because the kernel checks the
> test. Where no case can be computed (most analysis), the model records that small cases do not
> apply, and why.
>
> **No model supplies an expected value.** Each test's expected result comes from one of three
> places, and the record names which: the intent signer's answer, a cited source, or a computation
> on which every surviving candidate agrees. The last kind is shown as the weakest, because
> candidates can share one mistake.
>
> **Disagreement is the signal.** Where candidates answer a case differently, no test is written;
> the case goes to stage 5 as a question. Where every candidate is vacuous on a case, the page shows
> a triviality flag.
>
> **Three probes, not one** (added after the prototype, §9). A test that asks only "does the claim
> hold at n?" cannot see two kinds of error, so a round runs each test three ways:
> - **holds**: the claim at n against the proposer's answer;
> - **covers**: the claim at n with every concept the words use (here, "prime") made empty. The
>   claim then fails exactly where the conjecture says something, so this tells "holds at n" from
>   "says nothing about n". It catches a narrowed or widened domain on a true conjecture;
> - **witness**: the claim at n with the concept replaced by a small set ("suppose 5 were the only
>   prime"). This exposes the formula itself: its intervals, its connectives, how many witnesses
>   it asks for. It catches a weakening or strengthening of a true conjecture, which no test of
>   truth values can, because a weaker true statement is still true.
>
> And **concept questions**: where candidates' predicates for one concept disagree on a value
> ("is 1 prime?"), the value is a question.
>
> **Format rule.** A candidate names each concept the words use as its own predicate. One that
> writes the concept inline cannot be probed, and is **returned to its author** with that reason,
> never discarded; probing its real claim would discard a correct version (§9).
>
> Intent tests re-run whenever the statement is revised (D-8) or the Mathlib pin moves, as D-9's
> screens already do.

## 3. D-9 and v3.15: equivalence pairs, with proved differences kept

> **v3.36 — pairs.** Every pair of candidates, and every pair of formalizations a root carries
> (v3.15), records each **direction** separately as one of:
> - **proved**: a Lean proof that A implies B;
> - **refuted**: a kernel-checked instance where A's claim holds and B's fails, at some n or under
>   some probe. Not a proof of ¬(A → B) about the whole statements: for an open conjecture that is
>   usually unprovable, since it would settle the conjecture (§9);
> - **open**: attempted without a result; the attempt is recorded (who, what tool, what budget).
>
> Both directions proved: the two are equivalent and share a cluster. One proved and one refuted:
> one is **strictly stronger**, D-9's named residual (strength drift), now caught when it occurs.
> A failed attempt is never recorded as refuted; D-9 v3.12's "a failure is inconclusive and is not
> recorded as negative" stands.
>
> **Open directions are claimable work** for agents, on any root not yet `expert-attested`, and
> after it whenever a new candidate arrives. A proof or refutation goes through the gate like any
> other artifact and is credited (D-19).
>
> **The degenerate guard is on by default**: a direction whose proof never uses its hypothesis's
> content (both sides trivially true, the BEq+ false-positive class) is refused as a proof of
> equivalence.

Rationale: research §3 — proved equivalence runs at 98% precision and about half recall, so a proof
is strong evidence and its absence says nothing. A refutation is as certain as a proof and is the
most useful thing a disagreement can produce, because it is the question for stage 5.

## 4. D-9: the two signatures, named by role

What D-9 has today: `author-attested` is the poser-of-record; `expert-attested` is that plus one
independent signature. "Author" is used of the conjecture's wording in one rule and of the Lean in
the next (the non-author rule, v3.17).

> **v3.36 — two roles.** A root's certificate names two signers, each by role:
> - the **intent signer** answers the round's questions and signs that the surviving cluster says
>   what the conjecture says. It is the proposer; for a conjecture inherited from a source (D-6,
>   D-10), the target's steward (D-32), whose answers each cite a source, and an answer without one
>   is flagged on the page;
> - the **independent signer** reads Lean, wrote no candidate in the surviving cluster, and is not
>   the intent signer. They sign that the evidence supports the surviving cluster.
>
> In the ladder: the intent signer alone is `author-attested`; both are `expert-attested`.
> `screened-and-signed` keeps its meaning (the automated stages complete, plus one non-author
> signature on the comparison). **`expert-attested` additionally needs at least one person-written
> candidate in the surviving cluster**; where none exists, the target caps at `screened-and-signed`
> and the cap is shown, as D-9's thin-pool rule already does.
>
> **"Author" means the author of the Lean** in every non-author rule; the author of the conjecture's
> wording is the intent signer and is named so.
>
> A signature is a decision written by a person. The page never computes one. Each signer chooses:
> accept a cluster; split into variants (§5); or send back with a new question.

## 5. D-30: a reading not chosen becomes a variant

> **v3.36.** Where a round ends with clusters the intent signer confirms are genuinely different
> readings, the chosen one becomes the root and each other is published as a D-30 variant of it,
> with its relation label proved where the pairs (§3) already prove a direction, and `related`
> otherwise. A variant made this way is never the root and never carries the certificate; it is
> open work like any variant.
>
> If a signature later chooses a different cluster than the one being proved on, the root is
> revised (D-8) to the chosen one and the old root's work stays on the record as a variant. Nothing
> is lost and nothing is rewritten.

## 6. D-9: back-translation leaves the pass

> **v3.36.** Back-translation is removed from the pass. A signer reads the Lean rendered
> mechanically, with every type and coercion shown, beside the gloss (v3.30), so nothing they read
> was guessed by a model.

Rationale: research §3 — back-translation passes about a third of wrong statements on easy
material and rejects most correct ones on hard material; the questions of stage 5 do its job with
an answer from the one person who knows. It is also the only model-made text a signer was asked to
trust.

Cost to price before applying: `backtranslation` is in the QA pass's floor for roots and definitions
(`gate/opn_gate/qa.py`, `FLOOR_ROOT`, `FLOOR_DEFINITION`, F12-Q10) and has a subcommand. Removing it
from the floor changes what a complete pass is, so existing QA records stay valid (they did more
than the new floor asks) and the `qa` schema keeps the value for old records.

## 7. D-9, D-36: the evidence page

> **v3.36.** Each round has one page on the site, built from the record only:
> 1. **Candidates:** each with its author, how it was made, its stage-3 result and, if discarded,
>    the exhibit that discarded it;
> 2. **Pairs and clusters:** each direction proved, refuted or open;
> 3. **Questions and answers:** each question, the case it came from, the answer and its source,
>    and the intent test it became;
> 4. **The test matrix:** candidates by intent tests, and the mutants caught;
> 5. **Screens and the brief** (D-9 layers 2 and 3, the brief marked as a model's judgement);
> 6. **Signatures:** the two slots, signed through the site (v3.33).
>
> Exhibits and judgements stay apart on the page as D-9 v3.12 requires: only exhibits are evidence
> for a grade.

## 8. Open for the owner

1. **Existing targets.** v3.15 made every listed target claimable at once. §1's "claimable when the
   automated stages are complete" applies to new intake; do the existing roots keep their status and
   enter a round only when someone opens one?
2. **Where the conversation happens.** The intent signer answers questions over days. The site
   (v3.33 sign-in) is the natural home; it needs a write route for an answer (D-35, D-28 surface).
3. **Who may open a round.** The proposer through D-6's issue form, a steward, a curator?
4. **A second prototype on Mathlib statements.** §9 ran on core Lean with decidable instances. The
   next one should take two or three Erdős targets already on the graph, where small cases are
   expensive or absent, and measure how much of the round survives there.

## 9. What the prototype showed (2026-10-09)

Code: `engineering/prototypes/formalization-round/` (`round.py` runs the round, `test_round.py`
checks it, `render.py` draws the evidence page). Evidence: `engineering/evidence/v3.36-prototype/`
(results, page, screenshots, test output).

Set-up: three open conjectures with decidable small cases (Goldbach, Legendre, Oppermann), in core
Lean 4.33.1. For each: a human reference; correct variants written differently; three blind agent
formalizations (Sonnet, Haiku, Opus), each told only the words; and 14 planted candidates, one per
defect class (missing hypothesis, wrong domain, vacuity, lost conjunct, junk value, definition
mismatch, strength drift, parenthesization, wrong connective, wrong bound). The proposer is
simulated by a Python reading of the words, independent of every candidate. Mutation: every
single-site change to the reference's claim (operators, connectives, constants).

Results:
- **14 of 14 planted defects caught**, each by a kernel-checked exhibit re-run independently by the
  test suite; **one cluster survives per conjecture**, holding a person's and an agent's version.
- **Every mutant that changes the meaning is caught** (5, 13 and 15); the rest are equivalent or
  do not compile.
- **Questions to the proposer: 2, 5 and 7.** Most of Oppermann's came from mutants, at n = 2.
- **Blind agents:** Sonnet and Opus were faithful. Haiku's files did not compile. Sonnet's notes
  asserted a false fact (that n(n−1) is never prime; it is 2 at n = 2) without harming its Lean.
  An agent's prose is not evidence; its Lean, checked, is.

What the draft got wrong, now corrected above:
1. **Truth tests alone are blind to the defects that matter most.** With truth tests, screens and
   pairs only, 10 of 14 planted defects were discarded and 4 (definition mismatch, strength drift,
   lost conjunct, wrong connective) were only flagged as weaker or stronger by a one-way proof;
   meaning-changing mutants were missed: 2 in Goldbach (a narrowed domain), then 5 in Legendre and
   7 in Oppermann (weakenings and strengthenings) with coverage already on. The concept question,
   the coverage probe and the witness probe (§2) took it to 14 discarded and none missed. A
   weakening of a true conjecture is true, so only a probe of the formula can see it.
2. **"Refuted" must be per instance**, not a proof that two statements differ (§3).
3. **Simple equivalence matching needs two layers**: match each concept's predicates first
   (`A.Prime ↔ B.IsPrime`), then compare the claims with the concepts as atoms. Unfolding
   everything defeated `grind`. Three directions still needed an agent's proof (a witness
   q = n − p; the identity n(n−1) = n² − n), which is the "open pairs are claimable work" rule
   working as intended.
4. **The probes have an assumption, and it failed once**: a correct candidate with primality
   written inline was discarded by the coverage probe. Hence the format rule (§2).
5. **A probe question must say what it tests.** "Would a prime at 5 count for n = 2?" invites
   "yes" (5 is in the second interval) where the probe's answer is "no" (with 5 the only prime,
   the first interval is empty). Questions are phrased as the hypothesis: "Suppose 5 were the only
   prime. Would the conjecture be satisfied at n = 2?"
6. **The probes judge formulas against the words, not propositions.** A closed-interval Legendre is
   equivalent to the open one only because squares are never prime; it is discarded on the
   proposer's answer that a prime at a square would not count. The faithful versions survive, so
   nothing is lost, but the signers should know a discarded candidate is not always a false one.

Limits: decidable small cases only; core Lean only; the planted defects were written by someone who
knew the answers; the proposer is simulated, so the cost of a question to a real mathematician is
unmeasured.

Cites: D-4, D-6, D-8, D-9, D-10, D-11, D-15, D-19, D-28, D-30, D-32, D-35, D-36.
