# erdos-1094: ready for expert eyes (2026-10-12/13)

From the owner's hand-off: steward invitations are about to go to Konyagin, Sorenson, Webster and
Bennett, and erdos-1094 is the page each of them will open first. The network work is on branch
`e1094-readiness`, unpushed. The graph content is drafted in `engineering/evidence/erdos-1094-2026-10-13/drafts/`
and is **not submitted**: the owner reads it first.

## The owner's rulings (2026-10-12)

- **State of the problem:** an annex on the root now. Giving `note.md` a path role is a later spec.
- **Authorship:** the drafts are submitted under the owner's pseudonym, with `drafted_with: Claude
  Opus 5.5` disclosed, after the owner has read them.
- **Math first:** guidance plus a check tool. No gate rule, so no D-3 amendment.
- **t1009-c's model:** its records say Claude Fable 5.1, which is correct. No correction is needed.

## What the hand-off assumed, and what the record says

| Hand-off item | Finding |
|---|---|
| §1 LaTeX in glosses | Already rendered by KaTeX (F19-T6). The 1094 glosses were prose only because their authors wrote no TeX. The change is to guidance (F20-T16). |
| §2 three panels show no Lean | Does not reproduce. All ten panels carry the Lean in the live HTML and in a browser. The three named panels are the only ones where the Lean follows the note directly, which points to a text extractor. Guarded by F04-T42. |
| §3 "plausible, not established" | Not a `literature/v1` status (only `open`, `known`, `elementary`). Used as wording in the summary annex instead. None of the four literature records is confirmed. |
| §4 h2--h1--h1 gloss "closes … by the merged assemblies" | **True**: attestations 000478 and 000479. It needed one more fact: closing proofs are still owed for h3 and h2--h1. The new gloss keeps to the file, and the claim moved to the summary annex. |
| §4 "+2" vs "1" | "+2" is catalog *score points*. Labelled as such (F04-T43). The same AlphaProof Nexus attempt is also dated two ways: "Feb 2026" in the catalog reason, 2026-05-13 in `attempts.yaml`. Left as is (see judgment call 7). |
| §4 Fable vs Opus | Every t1009-c artefact says Fable 5.1, including the attestations' `tooling.model`. The owner confirms it is correct. |
| §4 run-together text | Shows only in stripped text, never on screen. Fixed (F04-T41: 16 places on the fixture page, 0-pixel screenshot diff). |
| §4 lost paragraph breaks | In the stored first versions (zsh `echo`, testers-2026-10-08), not the renderer. The new versions replace them. |
| §5 replace the root witness | **Impossible**: a real witness is immutable (D-3), and a statement with no hypotheses has expected witness type `True` (D-4 step 7). The non-emptiness `example` goes in the numerical annex instead, fast-checked. |
| §6 record a fidelity rung | `opn-gate fidelity … screened-and-signed` is refused with `pass-incomplete`, because erdos-1094 has no `qa/`. The sheet is built for F26's reading (v3.39). |
| §8 `POST /me/name` | Nothing on the site reads `names/` (v3.37). The page shows the steward record's `name`, which is the login. A sitting steward cannot re-commit (`steward-already-active`). |

## Numerics (reproduced independently of the investigating agent)

Code and outputs are in `numerics/`. Every search was rerun from source on 2026-10-12; `analyse.out` derives each node's figures.

- **Root:** exactly the 14 ELS pairs. The searched region is every $k\le1000$ with $n<k^3$ (complete), and every $n$ for $k\le26$ (complete, using the bound on h1). It was cross-checked against the literal Lean predicate for $k\le30$, $n\le3000$.
- **Smallest $K$ in range:** h2 and h2--h1 6; h2--h2 none needed; h2--h1--h1 35 (new); h3 28; h3--h1 58; h3--h1--h1 58; h3--h1--h2 39.
- No exception with $n\ge k^3$: $k\le26$ for all $n$, $11\le k\le60$ for $n<10^8$, and $k\le1000$ for $n<2\cdot10^6$.

## Judgment calls

1. **Glosses describe the file.** The guide says a gloss does not say whether a statement is true, hard or important. So the literature, the K values and the cross-node "closes" claims live in annexes. The only cross-node remarks kept in glosses are facts about each statement's own range. For example, on h3, $\lfloor n/k\rfloor<k$, so the condition is the root's.
2. **Eleven glosses, not ten.** The root's witness gloss is current too, and `check_gloss_form.py` counts it. Its new version opens with $\mathrm{True}$ and says the witness exhibits nothing.
3. **Notation.** $\operatorname{lpf}$ stands for `Nat.minFac`, and each gloss carries a note on its values at 0 and 1 and why they never matter. Each gloss writes $\lfloor n/k\rfloor$ where the Lean has floor division, and notes that it equals the real quotient under $>$.
4. **One numerical annex on the root, per-node annexes optional.** Every annex is counted and drawn as an informal *outline* of its node. Eight per-node numerical annexes would give eight nodes an outline badge that is not an outline. The per-node drafts exist in `drafts/annexes/per-node/`; whether to submit them is the owner's call.
5. **Literature claims are cited, not asserted.** erdosproblems.com #384, #1094 and #1095 were read on 2026-10-12. #1095 gives Konyagin's $g(k)\gg\exp(c(\log k)^2)$ but no form for Granville–Ramaré, so the summary quotes no form for it. The prior-art annex's form came from no reading of the paper. The summary says "plausible, not established" and claims no $K$.
6. **The prior-art annex on the root calls the $n<k^2$ half "a theorem".** Annexes cannot be edited. The summary annex states the honest status beside it.
7. **Attempt date clash left as is.** The catalog reason is a copied string; `attempts.yaml` says it is dated by the list's publication. Changing either is a curator act on the record and not urgent.
8. **The h1 explainer was accurate.** The new version keeps its sections and step keys and is math first, so a signature on it means what it says.
9. **Not done, because each is the owner's act or decision:** submitting any draft; signing the explainer; recording the fidelity rung; a display name (needs an amendment so the site reads `names/`, or step-down then re-commit, which has panel consequences); confirming literature records (nobody has read the papers).
10. **Graph `AGENTS.md`** gets the math-first guidance at the next re-pin (F20-Q21).

## Order for the owner

1. Read `drafts/` and `fidelity-review-sheet-erdos-1094.md`.
2. Push `e1094-readiness`, which deploys the API, then run `site-deploy`.
3. Submit the 11 gloss versions, the two root annexes and the explainer version. Each gloss's `supersedes` is the current head named in `check_gloss_form_before.txt`.
4. After the merges, run `check_gloss_form.py --graph <graph> --target erdos-1094`. It should exit 0.
5. Spot-check three glosses on the live page.
6. Sign the h1 explainer only if you can explain it without the tool. That takes the headline from 0/68 to 1/68.
