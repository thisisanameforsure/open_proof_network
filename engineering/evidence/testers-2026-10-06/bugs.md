# Testers 2026-10-06: words for erdos-1050, consolidated findings

Five background subagents, black box (site, service, published guide): W1–W4 wrote glosses and
explainers on disjoint files of erdos-1050 under pseudonyms `t1006-w1`…`t1006-w4`; R1 read the
target as a non-Lean mathematician and wrote nothing. Logs: `W1.md`…`W4.md`, `R1.md`, `R1/`.

Outcome: every Lean file on the target's live nodes now carries words (graph PRs #390–#436, all
words, unsigned, `drafted_with` declared). Four W2 v2s (#425, #426, #433, #434) were still queued
at the end of the run.

Verified by the lead on 2026-10-06 against the record (`origin/main`), the gate's run logs, the
deployed site and service, and the network source. **C** = confirmed (how), **C-code** = the
cause is in the source, **N** = not reproduced, **D** = by design.

## P1

1. **A version chain forked on the record, and every later merge on the target goes red.**
   C (git, runs, code). W3 superseded its merged gloss `b4cf9137…` (h1-v2--h3 statement) twice
   while the first was open: #415 → `d9dbd437…`, #417 → `30a6d33d…`. Both passed their gates (each
   against its own base) and the merge actor merged both in one append batch (04:43:36Z,
   04:43:41Z). Both files are on `main` with `supersedes: b4cf…`; `glosses.json` shows one chain,
   `current: d9dbd437`. The batch's gate commit (`gate: #412 #413 #414 #416 #418 #419 pass`) left
   both out; their replays fail `record-not-head`, each naming the other — and because a merge is
   owed until a gate commit names it (F07-T58), the replays are re-dispatched and fail after
   **every** post-merge run on erdos-1050 (04:44, 04:51, …).
   Cause, C-code: `api/opn_api/glosses.py:462` runs the one-writer check only when
   `supersedes is None`; the gate's `head_problems` (`gate/opn_gate/glosses.py:373`) sees only the
   pull request's base; an append batch merges without re-gating each against the others.
   Repair of the record is the owner's call (withdrawing `30a6d33d` alone may not clear the
   replays, since both still supersede the same version).

## P2

2. **Markdown lists and bold are not rendered** in glosses, explainers and annexes: `- item`
   becomes `<p>- …</p>`, `**` shows literally. C (`curl` of the h3 node page: `<p>- ` ×3, `**` ×102).
   The MCP schema says "the prose, as Markdown"; the guide names no subset. Writers re-filed v2s
   to work around it (W2: #425, #426, #433, #434).
3. **False `explainer-name-unanchored` warnings.** C (run 37411695222, #396: 20 warnings, e.g.
   `tail_coeff.hNdeg` under an anchored `tail_coeff`). The check compares backticked dotted names
   with the constants the steps use, so outline sub-step ids (which the guide tells writers to
   cite), file names (`Context.lean`) and fields of locals (`r.num`) all warn; the real ones
   (`Finset.prod` on #403) drown. Also invisible to the writer (feature request A).
4. **The guide's token answer is stale.** C-code: `POST /tokens` answers `token`, `identity`,
   `idle_days` (180-day idle lapse, v3.29, `api/opn_api/auth.py`); the guide (AGENTS.md "Getting a
   token", lines 692 and 698 at `origin/main`) says `expires` and 90 days. W4's script crashed on
   `d["expires"]`. Reported by W1, W2, W3, W4.
5. **"Every version of this explainer is withdrawn" sits above a live explainer** on
   `/nodes/erdos-1050/erdos-1050--h1-v2--h3/`. C (`glosses.json`: the proof has two chains; the
   first, `529518ac…`, is all withdrawn, the second is live). The sentence is per chain and reads
   as about the whole explainer. R1, W3.
6. **The site renders from a mid-batch merge commit.** C (site-deploy dispatched at each merge,
   05:08:17–05:09:43Z, three cancelled). For about a minute the pages cited `e59c0218` (merge of
   #431, before the batch's products): "No gloss yet", and a merged explainer shown as one raw block
   with literal `## Overview` and `{steps: …}`. Self-healed on the next deploy. W1.
7. **A post-merge run fails when GitHub returns an empty body.** C (runs 37414192547 and
   37414195303, #409 and #410, merged within 5 s: `gh api …/commits/<sha>/pulls` → `unexpected end
   of JSON input`, exit 1). Nothing lost: `gate: #408 #409 #410 #411 pass` credited all four. Two
   failures in the last 200 push runs. The lookup wants a retry. W4.

## P3

8. **spec-* panels contradict themselves**: "A statement the proof needs; proved." beside "Not
   needed by any proof of this problem". C (problem page: 6 and 11 occurrences). R1, W4.
9. **"Read proof 1 top-down"** links to a page headed "The proof, dependencies first". C. R1.
10. **At ≤ 900 px the "statement unchecked" badge is hidden** (`site.css:489`,
    `.problem-id-row .tag-outline { display: none }`), so phones lose the fidelity warning. C. A
    deliberate rule; whether a warning may be dropped for space is the owner's call. R1.
11. **The one-writer refusal can name a pull request that has just merged.** W2: 409 naming #400
    about 25 s after #400 merged. C-code (cause): `duplicates.check_words` reads open-ness from the
    service's submission store, which lags the host. N (one observation, not re-run).
12. **`get_node` lists h1-v2's circular dependency as plain `ready`** in `context.deps`, with no
    cause (the dependency's own `get_node` does say `cause: circular`). C. The answer is 1.96 MB. R1.
13. **`list_words_needed` lists the superseded node `erdos-1050--h1`** (Statement and Witness as
    `no-gloss`), unmarked. C. W1.
14. **"drafted with …" is printed twice** for each version (label line and chip). C. W2, W4.
15. **Library docstring hover cards show raw backticks.** C. R1.
16. **PR body grammar**: "A explainer appended…" (`api/opn_api/appends.py:224`). C. W1.

## Not bugs, or not checked

- `gate_verdict: null` on a green words pull request (W1, W3): **D**. `pending.gate_verdict` gives
  the reason for a *refusal* only. That a writer cannot see a pass or its warnings is feature
  request A.
- Queue `ahead` entries with null fields and positions disagreeing within one poll (W1):
  **N**. The queue had drained before the check.
- Fidelity wording on the problem page ("unchecked" / "graded" / "pass incomplete", R1 #6): not
  checked.
- Words reach the page 2 to 8 minutes after merge under a batch (R1 #8): a consequence of 6 and
  the queue, not a separate defect.
- W2's #424 (superseding its own just-merged version): the writer's error, as W2 says.

## Feature requests (consolidated; not verified, as they are requests)

From the writers:

- **A.** Report gate warnings, and a pass, to the writer: in the 201 answer, `GET /submissions`,
  or the PR body. Today they are visible only in the Actions log (W1, W3, W4).
- **B.** A dry run for words: check step anchors, return warnings and the HTML the site will
  render, and open no PR (W1, W2, W4).
- **C.** State the supported Markdown subset, and whether anchoring a step covers its sub-steps
  (W2, W3).
- **D.** In `list_words_needed`, mark subjects whose words are already in an open PR, with its
  number, and mark superseded nodes (W1, W2, W3).
- **E.** Show words in review on the node page (W1, R1).
- **F.** Amend words in an open PR without losing the queue position. W1 waited about 50 minutes
  to correct one sentence.
- **G.** Faster words merges. Words-only PRs waited 19 to 47 minutes behind about 25 others on one
  target. Explainers merged one by one while statement glosses batched (W2, W4).
- **H.** `get_node`: return `proposed_for`, closure membership and a per-proof closure field, and
  a smaller answer (W4, R1).
- **I.** A fold for the steps column. One section naming 22 steps prints screens of Lean claims
  (W2, W4).
- **J.** Outline `case` steps should print the hypothesis the split introduced, show the original
  Lean name beside escaped ids (`h_x3a9div` = `hΩdiv`), and give an id to un-anchorable closing
  terms (W2, W3, W4).
- **K.** Say who can sign words on a calibration target, which needs no steward (W1).
- **L.** One spelling of the model in `drafted_with` (three seen for one model) and a date on each
  explainer version (R1).

From the reader (R1):

- **M.** A short proof summary in words, and a citation of the human result, on the problem and
  proof pages.
- **N.** A table of contents and a root-first order on the proof view, which is 34,000 px tall.
- **O.** On node pages, mark which declared dependencies the proof actually uses.
- **P.** Explain `:= by sorry` on statement blocks.
- **Q.** Link reader pages to Docs "How to read a proof page".
- **R.** On phones: put prose before Lean, make the statement graph readable, and drop "hover".
- **S.** Readable names for the spec-* nodes.
