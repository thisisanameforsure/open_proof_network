# Four agents on erdos-68, 2026-10-29 (14:45Z–16:15Z)

Four agents had only the MCP: A (skeleton lead), B (second angle), C (hole prover), D (auditor and words).
A2, a finisher using A's identity, was started at 15:47Z for the words and found nothing left to file.
- Brief: `BRIEF.md`. Board: `COORDINATION.md`.
- Logs and final reports: `A.md`, `A2.md`, `B.md`, `C.md`, `D.md`. Drafts are in `A/`–`D/`.
- `prior/` holds the 2026-10-28 run on this problem.

No tokens were minted: the agents reused existing identities `t1028-a/b/c` and `t1027e-d`. Nobody merged anything by hand.
An erdos-849 run used the network at the same time.

## Outcome on the record (graph main, 16:00Z)

The target was `erdos-68--h3`, yesterday's open core. Nothing new was proved.

Three partials isolated three open cores. None is weaker than `--h3`; one is a separate statement neither known to imply `--h3` nor to follow from it:

| Node | Status | What it is | PR |
|---|---|---|---|
| `erdos-68--h3--h2` | ready | ∃δ>0, δ ≤ fract(N!·S) ≤ 1−δ for infinitely many N. Implies `--h3`; the reverse is not known | #1176 (A) |
| `erdos-68--h6--h1` | ready | ∀M ∃N≥M, fract(F_N) ≤ 1 − 1/N. Order: `--h3` ⇒ it ⇒ root | #1177 (B) |
| `erdos-68--h6--h1--h2` | ready | infinitely often 2/(N+1) ≤ fract(N!·S) < 1 − 1/(N+1): a factorial digit of S in [2, N−1]. Neither implies `--h3` nor follows from it | #1207 (B) |

How the cores relate (D, separating examples checked in exact arithmetic):
- `--h3--h2` ⇒ {`--h3`, `--h6--h1--h2`} ⇒ `--h6--h1` ⇒ root.
- `list_sufficient_sets` now offers two one-statement closes of the root: {`--h3--h2`} and {`--h6--h1--h2`}.

**The common barrier (D, cited by all four agents):** every open core proposed today, `--h3` included, also proves that T = S − (e − 2) is irrational, and nobody knows that. Take X = e − 2 + 1/3. Then N!·X is never an integer, so the root's conclusion holds for X, yet every core fails at X. Only `--h6`, which is equivalent to the root, avoids this. Postmortems #1203, #1204, #1205, #1209, #1210 and #1213 record why each attempted split of `--h3` and of the new cores collapses back to the statement it started from.

**Audits:**
- All three gate-written holes were checked twice: precheck against `have` by `Iff.rfl`, then main against the precheck, byte for byte. There were zero mismatches.
- Both restated holes became lemmas (`--h2` and `--h5`), as F07-T78 intended.

**Words:**
- Explainers of all three assemblies: #1194, #1206, #1214.
- Witness glosses: #1201, #1202, #1211.
- Literature records: #1196, #1208, #1212.

## Findings, ranked (V = verified by the lead against the graph history)

1. **V — The partial's bookkeeping commit still takes 10–15 minutes** (still present, prior #1).
   - Merge to `gate: #N pass`: #1176 at 14:55:31Z took 9.9 min (`6d5fe2a50d`), #1177 at 15:02:59Z took 14.5 min (`eb1181d759`), #1207 at 15:31:57Z took 10.7 min (`d36b055d66`).
   - B's runs 40897594017 and 40902525986 spent about 6 min re-deriving the verdict.
   - Under the quiet-window rule, each wait froze every append on the target.
2. **New — the race to push the bookkeeping commit spans the whole graph, not one target.**
   - erdos-849's appends moved main five times under #1177's push and four under #1207's (A's F-A1, B's F-B3, D's F-D3).
   - The quiet window on one target cannot protect it. This is the case for the append hold already planned for the merge actor.
3. **V — `list_words_needed` and `get_node` lag merged appends by about 7 minutes and give no sign of it.**
   - #1211 merged at 15:45:19Z, and the batched append commit `fee5eda162` re-rendered `glosses.json` at 15:52:44Z. Until then the gloss showed as `no-gloss`, while `read_at` named the head of main (D's F-D6, C's F-C6, A2's F-A2-1).
   - A2's stated cause, that appends never re-render, is wrong: they do, in a batch.
   - Risk: a duplicate filing.
4. **Feature request — no record for an implication between two existing nodes** (A's F-A3, D's F-D1).
   - Today's real result is the strength order of the cores and the separating examples, and it exists only as prose in #1208, #1212 and the postmortems.
   - The steward sees four open nodes with nothing saying which implies which.
5. Feature request — the precheck receipt could carry a kernel check that each printed hole is definitionally its `have` (D's F-D2). Each audit is about 3 minutes of hand work.
6. Minor:
   - A lemma hole is still given an `expected_witness` (C's F-C1).
   - The explainer dry-run preview prints the `{steps: …}` anchor inside the heading (C's F-C3).
   - `get_precheck` returns a JSON string in `content[0].text` while `check_lean` returns `structuredContent` (B's F-B1).
7. Still present:
   - Hole ids skip a number when a hole becomes a lemma: `--h3--h2` exists with no `--h3--h1` (prior F-A8).
   - `explainer-step-unknown` lasts about 1.5 min after the outline lands (prior #7).
   - The root's doc comment still says "Listed, not claimable".
8. Fixed since yesterday:
   - Route `erdos-68@2` is in `list_sufficient_sets`.
   - `postmortem/v2` takes `model_and_tooling`.
   - Open nodes no longer read "Proved from these holes".

## For the steward and the owner

- **Wording on two merged postmortems.** #1205 (A) and #1209 (B) said the root "does not" imply T ∉ ℚ; it should be "is not known to". Corrected on the owner's word by follow-up postmortems from the same identities, #1230 on `--h3` and #1231 on `--h6`, both merged 16:16Z.
- **Waiting for confirmation:** literature proposals #1196, #1208 and #1212 (all status open) wait for a steward or curator.
- **Ready drafts:**
  - `A/closing-h3-draft.lean` is the closing proof of `--h3` through #1176. It passes the fast check and waits on `--h3--h2`.
  - `prior/B/proof-erdos-68-closing.lean` then closes the root.
- **For later runs:** reassign the prover lane at the pick when the chosen outline has no elementary hole (C §4). C spent the run on words instead.
- **Time spent:** about 15–25 of each agent's 90 minutes went on mathematics. The rest was precheck (about 4 min each) and bookkeeping-commit waits.
