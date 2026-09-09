# F12 design record — statement QA, provenance and drift

Date: 2026-09-09. Produced by a grilling session with Mike, two rounds, every proposal agreed.
Nothing here is a spec yet and nothing here overrides a decision. It is the settled design that
F12's spec should be written from, plus the two things it changes outside itself.

Source documents this rests on:

- `docs/seed_conjecture_sources.html` — where Lean statements of open problems exist, how well each
  source checks them, and a per-problem catalog. Built at Formal Conjectures pin `c7f31d5`
  (2026-09-08), toolchain `leanprover/lean4:v4.33.1`. 640 Erdős problems have a Lean file, 335 are
  open on erdosproblems.com, 327 are scoreable seed candidates, 23 grade A and 83 grade B.
- `docs/research_statement_fidelity_2026-09.html` — the 2026 autoformalization literature. Its two
  load-bearing findings here: a Lean statement that compiles is only about three-quarters likely to
  mean what was intended, and back-translation is the weakest of the four checker families.

## What F12 is

A per-statement quality-assurance record: what was checked, by which tool at which version, what
the check produced, who signed, and what the statement was inherited from under which licence. Plus
the machinery that keeps that record true as upstream moves, and the path by which a spotted error
becomes a corrected statement.

## Settled decisions

1. **F12 is its own feature, depending on F11.** F11 is already six tasks and explicitly makes
   back-translation tooling and the mechanizable checks a non-goal. Two carve-outs land in F11
   rather than waiting, because retrofitting them is worse than adding them now:
   - the source and licence fields on `target/v1` (item 8 below);
   - a written QA pass on the five imported open targets, recorded as evidence under
     `engineering/evidence/F11/`, as a checklist and not as tooling.

2. **The per-target QA record lives in the graph repo**, alongside the D-9 fidelity certificates
   F11 already places at `targets/<id>/fidelity/`. The survey of the 327 candidates we did not
   import stays in this repo. Only the row for a target we actually took is copied across, as the
   evidence file its certificate cites. D-35 holds: the graph carries mathematics and its
   provenance, not our research process.

3. **A QA record is a list of typed check results**, each carrying: check id, tool and version,
   pinned inputs, verdict, and the path to its exhibit. The hard line, which comes from the
   fidelity research's own design consequence, is that kernel-checkable exhibits belong to the
   trust base and a judge's output belongs to a review brief attached to the certificate. A
   90%-accurate judge must never become an authority by accident. The record also carries the
   number of human sign-offs and the identity of each signer, per Mike's request; D-9 needs the
   count anyway, since `expert-attested` is one independent signature above `author-attested`.

4. **The consequence probe** — Mike's method, and D-9 already names it under consequence lemmas;
   its strong form is what the fidelity note calls proving `False` from the hypotheses. Assume the
   statement and derive its downstream consequences, looking for one known to be false.
   - Mechanically it never uses `sorry` in a real file, because `sorry` taints the build and the
     gate rejects it. The statement is introduced as an explicit hypothesis or axiom in a scratch
     file, and a derived falsehood is a kernel-checked exhibit.
   - **A derived falsehood is never auto-labelled.** Either the Lean is a misformalization, or an
     open conjecture has just been refuted. The probe files a defect claim carrying the exhibit and
     a human routes it.
   - It runs at intake, and again whenever the statement version changes or the graph's pinned
     Mathlib moves, because junk-value defects appear and disappear with library changes.

5. **D-9 needs amending first, to v3.12, through the architecture doc's own process.** The research
   note already flags this as an amendment candidate: `back-translated` is the compute floor, and
   it is the weakest checker family, roughly a third of its passes wrong on textbook material and
   worse on research statements. The amendment agreed here follows Mike's framing that
   back-translation is one piece of evidence and not a rung:
   - the second rung becomes **screened and signed**: the mechanizable pass completed with its
     exhibits recorded, plus a non-author signature;
   - back-translation becomes one named input to that pass rather than the rung's definition;
   - the compute floor stays at that rung, because the rung is now stronger than it was.

6. **A scheduled watcher, in this repo, covering two drifts.** Formal Conjectures has corrected 291
   of 2,615 statements, about 11%, most found by provers after merge, so a pinned import goes stale
   silently.
   - On an upstream edit to a path we imported, the watcher opens a revision request carrying the
     diff.
   - On an erdosproblems.com status flip to solved, it flags the target for dormancy under D-33.
   - Consequence of a drift signal is **a flag and a compute freeze, not an automatic downgrade**.
     D-9 downgrades on a confirmed defect, and an upstream edit is not yet one.

7. **A spotted error updates the Lean through D-8 and nothing new.** Nobody edits a statement. The
   curator creates version two as a new node, the old one is marked superseded and keeps its
   credit, dependents go stale and are re-derived. F12 contributes only the trigger and the
   evidence bundle attached to the revision request. Where we find a defect in an inherited
   statement, the fix is reported upstream to Formal Conjectures per D-10, as a documented curator
   act rather than tooling.

8. **Licence and attribution.** Facts from the seed report §8: Formal Conjectures is Apache-2.0 for
   code and CC-BY-4.0 for prose, and inheriting with attribution is explicitly intended.
   erdosproblems.com carries no licence text anywhere and asks for the citation form
   "T. F. Bloom, Erdős Problem #N, https://www.erdosproblems.com/N, accessed date". teorth's status
   database and alphaproof-nexus-results are Apache-2.0. Epoch is MIT for scripts and Apache-2.0
   for vendored statements. The Erdős-problems AI wiki is CC-BY-SA, which is contaminating if
   copied. lean-genius has no licence at all.
   - `target/v1` gains a `sources[]` list: kind, url, accessed date, SPDX identifier or
     `none-stated`, and the attribution string. Attribution carries over on import.
   - Intake refuses a source outside an allowlist. lean-genius is denylisted by name; the seed
     report also calls it a contamination hazard for the prior-art pass.
   - An imported Lean file keeps its Apache header verbatim and the graph carries a third-party
     notice file.
   - **Informal statements are cited and linked, never copied** into the graph or the site. The
     site shows the link, the requested citation, and our own one-line paraphrase. AI wiki text is
     never copied into the graph at all.

9. **The catalog reaches the graph in three places, and only one of them is the graph.**
   - The report stays a document in this repo, rebuilt on demand, as Mike's decision aid for
     choosing what to bring in.
   - When a row is chosen, `import-fc` copies that row's facts into the target's own record in the
     graph. This is the mechanism that "brings it over".
   - The target page on the site shows a short form of the row, which means we publish our own
     trust assessment of an inherited statement. Agreed deliberately.
   - The joined dataset is checked in as JSON pinned to the registry commit, so the report is
     rebuildable. **Today it is not**: the build script reads a work directory and a hand-written
     `report_body.html` that are not in the repo. Fixing that is part of the carve-out work, not of
     F12 proper.
   - The record is kept for all 23 grade-A rows, not only the five Stage 0 imports, so the next
     intake is cheap.

10. **Partial results are D-30 variants, and this is what Mike meant by "the final statement of a
    proof".** A bounds improvement is a variant, not the root.
    - A variant carrying a proved implication to the root needs nothing beyond the root's own
      record; the kernel protects the claim.
    - A `related` variant, with no proved implication, needs **one signature on the sentence that
      says why it is pertinent**, before it is published as such. That sentence is the part no
      kernel checks.

11. **Who signs.** For an inherited statement the author is upstream, which makes Mike a non-author
    and lets him sign the back-translation comparison himself; the seed report puts the cost at
    well under an hour per target. The schema enforces that attestor and subject author differ, per
    D-9. Where the upstream formalizer is known to be an AI system, the back-translating model must
    be a different system, and the model and version are recorded on the check either way.

12. **External prover sweeps count as D-9's M independent proof attempts**, with one guard: an
    attempt counts only against the statement content hash it actually ran on. If the statement
    changed after the sweep, the attempts do not carry over. Attempts are recorded named, dated and
    linked. Mike's addition: document attempts on any conjecture we can, to the extent they are
    documentable, not only the three named sweeps.

13. **The second signature is solicited in public, and the count is published honestly.** The
    back-translation comparison is posted alongside the D-10 posting. D-9's expert pool for Erdős
    targets is the erdosproblems.com forum and the Lean Zulip, not a hire. A target stays at one
    signature until a second arrives, and the record says so rather than waiting.

## What the record cannot catch

Kept here so the spec does not overclaim. From the fidelity research §4: quantifier scope has no
good automated detector, it type-checks cleanly and survives back-translation because the English
renders almost identically. Wrong-domain convention drift is invisible to probes and to
provability. D-9 already names strength drift, degenerate-but-satisfiable statements and an
ill-posed source conjecture as permanent residual risk. The QA record is triage in front of a human
and must not be read as retiring any of them.

## Order of work

1. Amend D-9 in `docs/architecture_decisions_v_3_11.html` to v3.12, per item 5, through the doc's
   own process.
2. Land the F11 carve-outs: `sources[]` and licence fields on the target schema, the written QA
   pass for F11-T5, and the seed report made rebuildable with its dataset checked in.
3. Write the F12 spec against this record, and add its row to `engineering/specs/index.html`.

F12 does not start before F11 does.
