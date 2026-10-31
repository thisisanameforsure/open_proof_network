# Four agents on erdos-849 through the MCP, 2026-10-27 (10:55Z–13:55Z)

Lead: Claude (this session). Agents: A skeleton lead, B open core `--h2`, C Lean on call + hole audit,
D words, review, reader, tooling. Brief in `BRIEF.md`, board in `COORDINATION.md`, logs `A.md`–`D.md`,
yesterday's run in `prior/`. All contributions went through the MCP; nobody pushed or merged by hand.

## Outcome on the record (graph PRs #1051–#1130, all merged, nothing by hand)

The chosen skeleton is the refutation `variant-3969f1f7` (Singmaster bounded, ⇒ ¬ root). It now reads:

- `--h1` proved (yesterday).
- `--h3` (MRSTT 2022 Thm 1.3, ε = 1/6) decomposed twice along the paper (A, #1058, #1067): the
  elementary pieces `--h3--h1--h2` (h_size) and `--h3--h1--h3` (h_absorb) **proved by C** (#1074, #1073);
  what remains is exactly Prop 1.9 (`--h3--h1--h1`) and Prop 1.10 (`--h3--h2`), each with a literature
  record and a postmortem saying why it is not split further.
- `--h2` (the open core) decomposed four levels (B, #1059, #1072, #1090, #1100): de Weger's conjecture
  (BBdW 2017 Conj 2.1, stated exactly) split into the nine solved (k,l) pairs (A, #1099, one hole per
  pair, each reviewed by B against the source and audited by C), the adjacent-row case
  (**Tovey/Lind, proved by C in Lean, #1085, 226 lines from scratch**), the n ≤ 10⁶ search, the
  value ≤ 10⁶⁰ search and the two Stroeker–de Weger shapes, all as cited known holes; the open core is
  now `--h2--h1--h4--h2--h3`, de Weger's conjecture with every case of BBdW Thm 2.2 removed.
- 23 gate-written holes audited by C against their partial's `have` type: zero mismatches
  (the 2026-09-17 printer fix holds). C's record sweep at 13:16Z over 38 nodes: clean.
- Words: every node born today has an exact statement gloss with a label; every merged proof and
  assembly has a step-anchored explainer; literature records on every known/open hole (D, A, B).

Three proofs, five partials (21 new nodes), four postmortems, ~25 literature records, ~45 words records.
Frontier for the target: 28 claimable entries.

## Findings, verified by the lead where marked

Ranked. "Confirmed" means the lead checked the evidence against the host; "agent" means it rests on
the agent's log and reproduction only.

1. **[bug, confirmed] A proof's post-merge attestation push is starved by a lane merging appends.**
   #1073 (C's proof) merged 11:58Z; its post-merge job computed `pass`, then its gate commit push was
   rejected 6 times at ~78 s intervals (12 "rejected / remote contains work" lines in run 40500099998,
   `refused 6 times; its merges are replayed`, conclusion failure) because #1074 and ten appends merged
   under it every few seconds; replay run 40502068440 landed the attestation at 12:23Z. For 25 minutes
   a node with `Proof.lean` in its tree read `ready`, and nothing on the page said so. (D F-D8, C F-C4,
   A's #1101 is a second instance of the shape.) The retry should rebase until it lands, or appends
   should hold while a proof's job runs; the state "merged, attestation pending" should be legible.
2. **[bug, confirmed by timing] A words-only merge re-renders the target and refuses every partial
   precheck on it with `409 products-pending`.** Measured 7 min 23 s (10:57:28Z first gloss merge →
   11:04:51Z first accepted precheck; render commit 11:03:39Z covering seven merges). B measured ≈8 min
   per partial merge, restarted by any append; ~25 min lost per agent. (A F2, B F4, D F-D6.)
   Prechecks should read the last render, or appends should not count as a change to the target's nodes.
3. **[feature, agent] Level n+1 cannot be prechecked until level n has merged, rendered and
   bot-committed (15–20 min)**, although the passed precheck already names the hole ids. B: "about 40
   minutes of three hours was mathematics". Also C: a ready proof idles until its hole exists on main;
   let a partial carry a hole's proof, or precheck against a hole named by a passing partial precheck.
4. **[bug → fixed during the run] The pair-proof route.** At 10:53Z `pair-proof` was advertised by
   `list_open_pairs` and the guide and refused at three layers (prior F-C4). Network PR #97
   (F26-T17–T21) merged 12:58Z and the live `submit_proof` enum and `POST /precheck` now accept it
   (lead checked 13:22Z: precheck answers `pair-proof-not-prechecked` with the submit-directly remedy).
   Not re-tested end to end today; C's equivalence from yesterday is the Lean it needs.
5. **[feature, agent] A wrong carried-witness guess costs a full gate round** (A F5, twice: `∃ C, True`
   vs `True`; `decide` on C(221,2)=C(17,8) hitting maxRecDepth in step 7 while passing the fast check).
   A bundle-level fast check elaborating every carried witness would catch both.
6. **[bug, agent] Site: "Split into — proved from these holes by …" shown on open statements** (A F6).
7. **[bug, agent] A withdrawn explainer keeps its content-hash path**: identical text refiled is
   `409 record-name-taken` with a timestamp-naming message (D F-D9). `kind: partial` accepts an
   explainer as a one-section gloss with no warning (D F-D7).
8. **[docs, agent]** `list_submissions` takes `target_id`, the guide says `target` (A F1, B F1);
   a `-- claim:` line must be one `$…$` and must begin with `$` (A F3, B F2); `submit_postmortem` has
   no `model_and_tooling` (A F4); MCP write tools answer `{status, body}` while read tools answer the
   bare body, and the precheck answer nests `nonce` under `body` (C F-C1, B F5); the pinned Mathlib's
   renames (`le_or_lt`→`le_or_gt`, `push_neg` deprecated) are undocumented (C F-C2);
   `problems/<target>/<node>/` is a 404 that serves the home page (B F3); hole files reach main 9–10 min
   after the partial merges when the lane is busy (C F-C3, prior F-C7).
9. **[feature, agent] Review answers as a non-steward are 403**, with the field check running before the
   identity check (D F-D2); still no place for a contributor's suggested answer (prior F-C2).
10. **[agent] A hole born with its author's `-- claim:` gets a gloss that breaks the gloss rules**
    (nested `$`, dropped binders/casts), so D superseded all 20 (prior F-C8). Hold the claim line to the
    gloss rules at precheck.

Not defects: the per-target lane and the strict up-to-date rule behave as designed; the laptop's 20–75 s
connects are the laptop's path (measured by `time_connect`).

## What a steward/curator should do next

- Confirm the literature records (status `drafted` until signed), and sign the words.
- The open core `variant-3969f1f7--h2--h1--h4--h2--h3` and the two MRSTT propositions are the whole of
  what is open on this skeleton; nothing else on the branch is provable from the literature.
- Claims held by the agents expire on their own by 15:22Z.
