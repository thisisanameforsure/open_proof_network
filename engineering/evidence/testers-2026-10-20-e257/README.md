# Testers 2026-10-20: three agents build skeletons on the Erdős 257 planning nodes

Mike, 2026-10-20: "build skeletons based on the 3 planning nodes for erdos 257. After building the
skeletons fill in what holes you can. Use 3 subagents. At the end have them report any bugs. verify
them, then prioritize them and report back to me." Then: "do this for the next 3 hours."

Run as background subagents of one local session (the lead), 20:22Z to 22:24Z. One node each:
A = `spec-5e2e0890` (uniqueness of representation), B = `spec-a70fcca4` (1/2 is an infinite subset
sum), C = the root `erdos-257` (the third planning node, `spec-ddd99827`, was already proved on
2026-10-20 morning and is used by two of the three skeletons). Each agent minted its own token
(`fable-1020-e257-{a,b,c}`, no 429s). Logs `A.md`, `B.md`, `C.md`; Lean, witnesses, precheck
results, receipts under `A/`, `B/`, `C/`; the board `COORDINATION.md`. No token is in this folder
(scanned before filing).

## What landed (graph PRs #780–#799, every one merged by the merge actor, no human)

| Node | Skeleton | Holes | Result |
|---|---|---|---|
| `spec-5e2e0890` (uniqueness) | #782, 2 holes | `--h1` summability #785, `--h2` lexicographic comparison #787 | **proved** by closing proof #793 (uses `spec-ddd99827`) |
| `spec-a70fcca4` (1/2 is a subsum) | #783, 4 holes | `--h1` #789, `--h2` #790, `--h3` #791 proved; `--h4` "the walk never stalls" open, postmortem #788 | open on exactly the open mathematics |
| `erdos-257` (root) | #781, 2 holes, annex #780 | `--h1` greedy characterisation #786 proved (uses `spec-ddd99827`); `--h2` "every rational's walk stalls" open, expected false, postmortem #784, annex #792 (mutual exclusion with `spec-a70fcca4--h4`) | root open on the one hole that is the problem |

Glosses #794–#799 (B, correcting the auto-written claim glosses). Frontier for erdos-257 at the end:
`erdos-257`, `erdos-257--h2`, `spec-a70fcca4`, `spec-a70fcca4--h4`.

Time: each agent spent roughly 45–50 minutes working and 70–105 minutes waiting on the host (the
one lane per target, 4–5 minute Mathlib gate rounds, 8–16 minute post-merge jobs).

## Bugs, verified by the lead and prioritised

Verification method per item is given; "verified" means the lead reproduced it from the code, the
live site or the host's logs, not from the agent's word.

### P1 — costs every contributor on a busy target

1. **The post-merge job's own writes cost every open proof on the target a gate round** (A F3,
   C 2). `.github/workflows/merge.yml` `gates_on` excludes products (`graph.json`, `CONTEXT.json`,
   outlines, attestations, ledger), and the guide says what the job renders "never cost[s] you a
   round". But the `gate: #N pass` commit also writes `META.yaml` (`status: ready → proved`, seen in
   graph `b5e07dfee` on `spec-5e2e0890--h1/META.yaml`) and, after a partial, the hole nodes'
   `Statement.lean`/`META.yaml`/`Witness.lean` (`6f6827159`). Neither is excluded, so `behind_of`
   is positive and the actor updates the branch: #786 was gated four times green (21:07, 21:10,
   21:16, 21:21; the third round caused only by the META.yaml status write) and merged after 18
   minutes for a 4-minute gate. Verified from `git show --stat` of main's commits and the actor's
   run output ("merge actor: update #786"). Fix: treat a bot `gate: #N pass` commit's META.yaml
   status write as a product (it is derived from the attestation); decide separately whether
   hole-node creation should count (it does change what a sibling skeleton is gated against).

2. **The hole writer files a claim line as `$$<claim>$$`, so a claim with inner `$…$` groups
   becomes nested dollars and raw TeX on the site** (B 1). `gate/opn_gate/labels.py`
   `_CLAIM_RE` accepts any line that starts and ends with `$`; `gate/opn_gate/postmerge.py:764`
   wraps it. Verified on the record: `spec-a70fcca4--h4/gloss/0f868d6d….md` body is
   `$$r_m \le …$ for every $m$, … $\frac12$$`. Three of B's four holes hit it. Fix: `claim-form`
   requires exactly one `$…$` group, or the writer does not re-wrap a delimited claim.

3. **A node page whose only TeX is its claim loads no KaTeX** (C 1). `site/opn_site/render.py:4570`
   (and line 1248) test the literal substring `class="math"`; the opening display is marked
   `class="math math-break"` (F04-T51), which never matches. Verified live: `/nodes/erdos-257/
   erdos-257--h2/` has two `math math-break` spans and zero `katex`. A's hole pages were unaffected
   because they carry other `class="math"` elements. Fix: a regex or class-token test.

### P2 — wrong or misleading on the record or the page

4. **Superseding a gloss without `label` erases the node's name from every drawing** (B 2).
   `gate/opn_gate/glosses.py:809` takes the label from the newest gloss only; the guide's
   `submit_gloss` fields do not mention `label` though the route accepts it. Verified on the
   record: after #794–#796 `graph.json` labelled `spec-a70fcca4--h1/--h2/--h4` as `h1`, `h2`, `h4`
   until #797–#799. Fix: inherit the superseded version's label when the new one omits it, or
   refuse a label-less superseding gloss on a labelled statement; document `label`.

5. **A hole born with a carried witness says "Witness: Not checked" on its page** (B 5). Verified
   live on `/nodes/erdos-257/spec-a70fcca4--h4/`, while `attestations/000783.json` step 7
   (`hole-witnesses`) records the witness by path and sha256. The child page reads only
   attestations against the child. Fix: the page reads the parent partial's step-7 record for a
   `skeleton-hole` child.

6. **The sibling-restatement rule (v3.38 lemmas) cannot fire for a parent with binders** (A F1).
   `gate/lean/OpnGate/Holes.lean`: `restatesAncestor` compares both the hole's type where it sits
   and its closed form; `restatesSibling` compares the closed form only, and the closed form
   always carries the statement's own binders, so a hole restating `spec-ddd99827` under
   `spec-5e2e0890`'s binders read `restates: null` (A's precheck 01M5DFYH18HVAKHS6Y8TZ3XVKA).
   Verified by reading. Fix: compare the in-place type too, as the ancestor check does.

7. **`409 products-pending` holds every hole-making precheck on a target for any touch of
   `nodes/`, an annex or postmortem included** (A F2, B 4). `api/opn_api/precheck.py` `job_commit`
   keys on `nodes_commit != products`. Verified by reading; cost each of A and B six minutes after
   C's annex #780. By design (F06-T18) but broader than its reason: an append cannot change what a
   hole restates. Fix: key the hold on commits that add or change a `Statement.lean`.

### P3 — real but small, or designed recovery

8. **Post-merge push race recovered by replay, 15 minutes late** (B 3). Run 39503833962: push
   `! [rejected] (fetch first)`, `postmerge: dispatched a replay of #790`, replay 39504647369
   green at 22:07. Verified from the run log; B's reading that the catch-up conflicted on a
   `closure.json` both runs created is plausible and not re-verified. The designed backstop
   worked; the cost is the lane waiting on it.

9. **CSP `style-src 'self'` blocks three inline styles on the problem page** (C 5). Measured with
   Playwright: 3 console violations, 110 KaTeX formulas, 2,053 styled elements, 0 height
   mismatches. No visible effect today; the errors are noise until something depends on them.

10. **A proved lemma used by a route sits under "Show 9 more statements" by default** (C 5),
    so `erdos-257--h1` appears to rest on nothing until the group is opened. Design question for
    the drawing: a node a visible proof *uses* should be visible.

11. **No record type expresses that two open statements exclude each other** (C 5).
    `erdos-257--h2` and `spec-a70fcca4--h4` are contradictory; the only home is prose (annex #792).
    A design gap, not a defect.

12. **`queue.ahead` entries with null fields** (C 3). Not reproduced; the builder in
    `api/opn_api/pending.py` cannot emit a null `pr_number`, so this is most likely C's reading of
    the guide's field names (`number`, `node`) against the route's (`pr_number`, `node_id`). The
    guide at line 1024 uses the informal names; worth aligning.

### Not bugs (the agents' own misreads, kept so nobody re-finds them)

- "`POST /check` needs `target_id`, unstated" (C 4): the guide says so at lines 291 and 339.
- `partial-unlabelled`/`claim-form` on a claim with prose outside the dollars (A, B): correct refusals.
- `witness-elaboration` on carried witnesses without `import Mathlib` (B): correct; the fast check's
  witness mode substitutes the import, so it cannot warn. One guide sentence would save the round.
- `precheck-bundle-differs` after a lost response (A): the digest check was right; this laptop's
  path to the service drops reads, as recorded on 2026-09-21.
- `mode: verify` answering `okay: false` for a proof with a use line (A): the lint text explains it.

## Mathematics worth keeping

- Uniqueness of representation (`spec-5e2e0890`) is now a theorem on the record: the greedy set is
  the only candidate for any rational, so Erdős 257 is exactly "every rational's greedy walk stalls".
- The structure of a refutation is on the record as one open hole (`spec-a70fcca4--h4`): the
  remainder of the greedy walk for 1/2 never exceeds the tail of the series. Its negation at a
  single rational is the root's open hole `erdos-257--h2`.
- Hole extraction worked as designed throughout: every closed type read as intended, every proof
  passed the gate on its first precheck, and no node written by the gate failed to elaborate.
