# Bugs and feature requests from the 2026-10-01 tester run, aggregated and prioritised

Source: the 26 agent logs in this directory (`<agent>.md`), every Bugs and Feature requests
section, deduplicated across agents. Compiled 2026-10-01 19:45–20:30Z, after the run.

- **P1** blocks contributors, or makes the record say something untrue. **P2** costs significant
  time. **P3** minor.
- **Status** has two parts: what a re-run showed, and where a fix stands.
  *confirmed* = re-run by the compiler of this list against the live service
  (`https://api.openproofnetwork.org`, read-only calls and the anonymous fast check only), the
  live record (graph `main` at `1d98dcfb`, `gate: #360 pass`), the live site, or GitHub's public
  API. *not reproduced* = re-run and the report did not hold. *not re-tested* = needs a write, a
  token or a merge in flight, none of which this pass was allowed.
- The list is in three parts that should not be mixed: **A** network defects, **B** design gaps
  that need the owner's ruling, **C** feature requests. Then **D** sandbox artefacts and **E**
  what the agents' own reports got wrong.

Counts: **4 P1, 12 P2, 28 P3** (44 items: 24 defects, 8 design gaps, 12 feature requests).

## The top ten, re-run

| Rank | Item | P | Re-run on 2026-10-01 | Result |
|---|---|---|---|---|
| 1 | A1 hazards mode of `POST /check` fails inside the service's own program | P1 | `POST /check {"target_id":"erdos-69","mode":"hazards","node_id":"spec-2e765953"}` at 19:50Z, log `01M3WG8X7G4NC1AB75SWJES52Y` | **confirmed** |
| 2 | B1 nothing beneath a node can import definitions admitted later or cite a proved node it does not already depend on | P1 | `69-R5-a/header_experiment.py` (verify on `euclid-primes`), log in the answer; `META.yaml` of the gate-written holes | **confirmed** |
| 3 | A2 a definition cannot be added to a target that already exists | P1 | `opn-gate classify` at erdos-69's pin `3422bb4` over the curator's local one-file branch; live `POST /check` with `import Defs.Construction` | **confirmed at the pin; passes at this branch's head (F11-T13, PR #26)** |
| 4 | A3 `digestion.closure` and the statement graph count declared dependencies as what the closing proof depends on | P1 | `targets/index.json` against `grep` of the merged `Proof.lean` files; the live problem page | **confirmed** |
| 5 | A5 the merge queue: appends never batch, most `merge` runs are cancelled, idle gaps | P2 | graph history `3f2da56..1d98dcfb`; GitHub Actions run list 11:40–18:40Z | **confirmed** |
| 6 | A4 `GET /submissions/<n>` serves a merged pull request as open, `stale: false`, for minutes | P2 | no merge was in flight; cause read in `api/opn_api/pending.py` and `config.py` | **cause confirmed in code; the live window not re-tested** |
| 7 | A6 `mode: verify` says `okay: false` for a correct direct proof when the Context restates a hole | P2 | `POST /check` verify of `1050-R1-b/h2-Proof-direct.lean` on `erdos-1050--h1-v2--h2`, log `01M3WGAB48KXF1J28TTSXHTHT2` | **confirmed** |
| 8 | B5 no marker for a superseded-route, circular or dead hole | P2 | `frontier.json`, `targets/index.json`, `graph.json` at `1d98dcfb` | **confirmed** |
| 9 | B2 a partial cannot carry its holes' witnesses | P2 | needs writes; the cost re-derived from GitHub's `created_at` / `merged_at` and the bot commits | **not re-tested; timings confirmed** |
| 10 | B3 + A8 no helper declarations under the 200,000-heartbeat cap, and the check never says how many were used | P2 | both `POST /check` answers above searched for any heartbeat field | **confirmed (no such field); the cap itself not re-tested** |
| — | 1050-R1-a B4, "an unproved speculative node left the frontier when the root resolved" (would have been P2) | — | `git show 2ff5bc2:frontier.json` (`gate: #326 pass`, rendered from the root's merge) | **not reproduced**, see E1 |

## A. Network defects

| # | P | Defect | Agents | Reproduction | Status |
|---|---|---|---|---|---|
| A1 | P1 | **Hazards mode of the fast check is broken for every statement.** The answer is `okay: false, hazards: null, user_error: null`; the two errors are in the program the service appends (`Unknown identifier Lean.Elab.IO.processCommands`, then `st.commandState`), not in the caller's statement. So every proposal's `hazards_preflight` reads `inconclusive`, the pull request opens anyway, and the gate is the first hazard check: #337 was opened, refused three minutes later for one unacknowledged `junk-value`, withdrawn and re-proposed as #339. The text the checker returns carries `import Mathlib` only. The failing lines are the ones F02-T9's last commit (`c16c57e`, merged in network PR #24 at 11:43Z, a minute before the run) put in `api/opn_api/checks.py:940`; the Lean tier was green on the local toolchain and nothing called the deployed route. | 69-R1-b 1, 69-R2-a 1 | `curl -s -X POST $OPN_API/check -H 'Content-Type: application/json' -d '{"target_id":"erdos-69","mode":"hazards","node_id":"spec-2e765953"}'` | **confirmed** 19:50Z. Open. Not root-caused past the missing identifier. |
| A2 | P1 | **No mode admits a `defs/` file on an existing target.** A diff carrying a definition is classified as an intake whoever wrote it, and an intake must add `target.yaml`; erdos-69's honest decomposition needs the drafted construction (18 definitions in `69-R4-b/Defs-v2.lean`) and every hole statable without them is circular. | 69-R3-curator; 69-R1-a F1, 69-R1-b F1, 69-R2-b F2 | at the pin: `opn-gate classify --graph <clone on curator/erdos-69-defs> --base HEAD~1 --author thisisanameforsure` → `intake-incomplete`. Live: `POST /check` with `import Defs.Construction` on erdos-69 → `400 defs-unknown` | **confirmed** at `3422bb4`. **Fixed as F11-T13** (this branch, draft PR #26): the same command at the branch head answers `ok: true`, `needs_exhibits: true`. Live after the merge and a re-pin of erdos-69. |
| A3 | P1 | **The record's own summary of a resolved target counts nodes the proof does not use.** `targets/index.json` gives erdos-1050 `digestion.closure: 6` and the page says "0 of 6 proved nodes in the closing proof's dependency closure"; the root's proof names `erdos-1050--h1-v2` (as the theorem `erdos_1050__h1`) and that node's merged proof names `--h3` alone (`Proof.lean:742`), so the closure by use is 3. The statement graph says "lines join a statement to the statements its proof depends on" and draws the proved `--h1-v2` resting on a circular hole and on `--h2`, which was open at the time. Declared `deps` and used deps are one thing in the products. | 1050-R2-a A1, A11 | `python3 -c` over `targets/index.json`; `grep -n erdos_1050__h1_v2__h targets/erdos-1050/nodes/erdos-1050--h1-v2/Proof.lean`; `https://openproofnetwork.org/problems/erdos-1050/` | **confirmed**. Open. |
| A4 | P2 | **A merged pull request reads as open, labelled fresh.** After #332 merged, `GET /submissions/332` answered `state open, merged false, waiting_on gate, stale: false` for 84 s; after #336, for 2 m 23 s; #327 likewise. The pull-request state is cached for 180 s (`DEFAULT_PULL_MAX_STALE_S`, F07-T47, deployed that morning) and a cached answer inside the window is `stale: false`. Side effect seen across the logs: every merge time an agent took from this route is one to five minutes late (E5). | 1050-R1-a B2, 1050-R2-a (twice) | poll `git ls-remote origin refs/heads/main` and `GET /submissions/<n>` side by side around a merge; compare `read_at` with the clock | cause **confirmed in code**; live window not re-tested. Open. |
| A5 | P2 | **The queue's mechanics, apart from its design (B6).** (a) Appends batch on paper only: `merge.yml` on the graph carries F07-T45, and all 35 merges of the run have their own post-merge commit, including four pairs of adjacent green annexes (#328/#329, #333/#334, #340/#341, #357/#358) merged 5 to 11 minutes apart. (b) 116 of the 201 `merge` runs created 11:40–18:40Z were `cancelled` (55 of 70 dispatches, 59 of 129 `workflow_run`); 12:40–12:48Z had 8 runs, 7 cancelled. (c) After a post-merge commit the next pull request waited idle 3.5–5 min (12:42:58 → 12:47:45, 13:17:10 → 13:20:50). (d) The post-merge job took 4.2–8.6 min (median 6.5) for every kind, an annex included. | 1050-R2-a N1, N2; 402-R6-a B1; 69-R2-a 4 | `git log --format=%s 3f2da56..HEAD \| grep -c 'gate: #'` → 35; `GET /repos/…/actions/runs?created=2026-10-01T11:40:00Z..2026-10-01T18:40:00Z` | **confirmed** (counts are this pass's own). Why no batch formed is not established: the run logs need a token. |
| A6 | P2 | **Verify refuses a proof that is right.** On a node whose Context restates a hole, `mode: verify` answers `okay: false` with `context-restated` and `sorry-reported`, `failed_declarations: ["erdos_1050__h1_v2__h2__h1"]` (the Context's theorem), for a proof that never names it and that the precheck and the gate then passed (#335). It still does now that the hole itself is proved. The lint text does say to use the precheck; the verdict is still wrong. | 1050-R1-b B6, 1050-R2-a | `POST /check` verify, `node_id: erdos-1050--h1-v2--h2`, content `1050-R1-b/h2-Proof-direct.lean` | **confirmed** 19:52Z. Open. |
| A7 | P2 | **The guide the agents read is one re-pin behind the network.** The graph's `AGENTS.md` differs from `gate/agents/AGENTS.md` by 63 lines. Missing live: the `POST /tokens` body "in full" (so `"dco": "<version>"` → `400 dco-not-accepted`), the paragraph saying a proof can be prechecked once its proposal's gate is green (F06-T10; 69-R2-a waited 74 minutes for #339 to merge before prechecking), and the corrected sentence on which holes a hole inherits (F07-T48). | 1050-R1-a B1, F4; 69-R2-a F1 | `diff gate/agents/AGENTS.md ../open_proof_network_graph/AGENTS.md`; guide line 564 | **confirmed**. Fixed in the network; live at the next re-pin. |
| A8 | P2 | **The fast check never says how many heartbeats a declaration used**, and a proof over the cap is reported as a timeout at whatever tactic was running. Ten agents asked; three found the cap by bisection. The workaround (`#count_heartbeats in` before the doc comment, which also lifts the cap for that run) is not in the guide, and the older spelling `count_heartbeats in` is a parse error. | 1050-R1-a F3; 1050-R1-b B4, B5, F1; 402-R2-b F1; 402-R2-c F3; 402-R4-c; 402-R5-a F3; 402-R5-b; 402-R6-a F5; 402-R6-b; 69-R5-a 6 | any `POST /check`: no key containing "heart" in the answer or in `result` | **confirmed** (field absent). Open. |
| A9 | P2 | **The fast check cannot take draft definitions.** `import Defs.<Name>` for a module not yet on `main` is `400 defs-unknown`, so every statement and proof over proposed definitions is checked with the definitions pasted in and the import deleted: the text checked is never the text submitted. All of erdos-69's rounds 2 to 5 worked this way. | 69-R2-b 1, F1; 69-R3-b 2; 69-R4-b 3; 69-R5-a 5; 69-R3-curator | `POST /check {"target_id":"erdos-69","mode":"check","content":"import Mathlib\nimport Defs.Construction\ntheorem t : 1 = 1 := rfl"}` | **confirmed** (`400 defs-unknown`). Open; by design until a `draft_defs` field exists. |
| A10 | P2 | **The guide's skeleton section omits what makes a many-lemma skeleton possible.** (a) Scoped holes: each hole inside its own bullet of one `refine ⟨?_, …⟩` is extracted closed over its own binders only (`402-R5-a/precheck2-result.json`, `402-R6-a/pc2-result.json`: `proved_binders []` on every hole); a flat hole after them inherited all twenty (`extract-test-scoped-precheck.json`). (b) The cap of 20 holes per partial (`too-many-holes`, `MAX_HOLES = 20` in `gate/opn_gate/steps/artifact.py`). (c) A hole whose hypotheses are unsatisfiable can never be witnessed, so remaining cases go in the conclusion as disjuncts (B4). (d) A later route's holes continue the parent's numbering (`--h2`). | 402-R5-a B2, B3; 402-R6-a B4; 402-R1-a B1; 402-R2-a F4 | read the guide's "Skeletonization" section; the three precheck results named | (b) **confirmed** in code; (a), (c), (d) not re-tested (a precheck needs a token), evidence files read. Open. |
| A11 | P3 | `waiting_on` reads `merge` whenever GitHub's `mergeable_state` is `unknown`, including for a pull request that is behind and third in line; it then goes back to `gate` for the queue's re-gate with nothing saying so. | 1050-R1-a B3; 1050-R2-a N3; 69-R3-b 3 | poll `GET /submissions/<n>` for a queued pull request | not re-tested (nothing queued). Open. |
| A12 | P3 | After a merge, a proof or partial reads `waiting_on: null`, `mergeable_state: unknown` while its post-merge job runs; annexes and witnesses read `products` (#329 against #331/#332; #348 against #349; #351, #353, #359). There is no plain `merged` state at the top. Found in this pass: `submission.closed` is the time of the first read after the close, not the merge time (#360 merged 18:19:10Z, `closed: 2026-10-01T19:50:21Z`, the moment of this pass's first read). | 1050-R2-a N4; 402-R4-a B1; 402-R5-a B4; 402-R6-a B3; 69-R1-a F5 | `GET /submissions/360` | post-merge shape **confirmed**; the in-flight window not re-tested. Open. |
| A13 | P3 | `GET /submissions.json` and `GET /submissions/<n>` name the artifact type `kind`; `POST /submissions`, `/precheck` and the receipt name it `artifact_type`. The list gives `waiting_on: null` for every entry and no order. | 1050-R1-a B7; 1050-R1-b B1; 1050-R2-a; 402-R1-a B4; 402-R2-a B2 | `GET /submissions/360` → `submission.kind: "proof"`, no `artifact_type` | field name **confirmed**; the open list was empty, so its `waiting_on` not re-tested. Open. |
| A14 | P3 | While a hole's witness pull request is open, `POST /precheck` on the hole answers `409 node-blocked … witness-missing … a witness goes in through POST /proposals/witness`, telling the submitter to do what is done; `annex-pending` names the open pull request, this should too. | 402-R2-a B1; 402-R6-a B2 | `POST /proposals/witness` on a fresh hole, then `POST /precheck` on it | not re-tested (writes). Open. |
| A15 | P3 | `mode: check` on text with `sorry` answers `okay: true` beside `failed_declarations: ["t"]` and "Declaration 't' is incomplete"; only `lint: sorry-present` is unambiguous. | 69-R1-a 1; 69-R2-b 3 | `POST /check {"target_id":"erdos-69","mode":"check","content":"import Mathlib\ntheorem t : 1 = 1 := by sorry"}` | **confirmed**. Open. |
| A16 | P3 | Fast-check answers are hard to read by script: the whole hypothesis context once per error in `tool_messages.infos` (about 40 kB for five errors on a 600-line proof); the unsolved goal last, where a truncating script cuts it; "Try this: intro …" as a WARN on every inlined lemma; no suggestion for a constant the pinned Mathlib renamed. | 1050-R1-b B3; 402-R2-b B2; 402-R3-c B3; 402-R1-a B3; 402-R2-c B2 | `python3 1050-R1-b/mkfull.py old`, then `POST /check` | not re-tested. Open. |
| A17 | P3 | The guide lists the `-- annex:` citation among the rules "the gate enforces mechanically"; a partial without it passes precheck and merges (#331 named its annex in a plain comment). The other half of the 2026-09-29 item is fixed: an unknown hash is now `400 annex-unknown`. | 1050-R1-b B2; 402-R1-a; 69-R1-a 4 | precheck jobs `01M3VMWQ4R9057F12TV6FFB5J9`, `01M3VN15Q88FVTPWZ280N3MQ2K` | not re-tested (token). Open since 2026-09-29 (item 11 there). |
| A18 | P3 | One disclosure field, two names: `POST /annexes` takes `model_and_tooling` and refuses `tooling` (`400 unknown-field`), `POST /submissions` takes `tooling`; the guide's annex example shows neither. | 402-R1-b B1; 69-R1-b 3 | `grep -n model_and_tooling AGENTS.md` → the approach-record line only | guide half **confirmed**; the refusal not re-tested (token). Open. |
| A19 | P3 | The gate's hazard refusal lists the unacknowledged findings only; an acknowledgement that matches nothing is carried silently into `META.yaml`. | 69-R2-a 2 | propose with a misspelt acknowledgement | not re-tested. Open. |
| A20 | P3 | Guide gaps, one sentence each: `POST /check` needs no token (agents spent token starts believing it did); where errors sit in `result`; hazards mode takes `node_id` or `statement`, not `content`; `decide +kernel` is accepted where `native_decide` is not; whether `defs/` may import Mathlib and hold `noncomputable def` (yes to both, 69-R3-curator); what a proved `resolves` variant does to its root; `#check @Name` as the way to ask whether the pinned Mathlib has a name. | 402-R2-c B1; 402-R3-c B1; 402-R1-b B2, F2; 69-R1-b 2; 402-R6-b; 69-R2-b F4; 69-R5-a 2 | anonymous `POST /check` answered every call of this pass; `grep -n -i anonymous AGENTS.md` | anonymity **confirmed**; the rest read. Open. |
| A21 | P3 | Site wording on a resolved target (`/problems/erdos-1050/`): six side lemmas captioned "A statement the proof needs" that nothing depends on; three words for one state ("proved" pill, `resolved`, "Resolved — undigested"); "2 attempts" on the root card beside `attempts: {counted: 0, recorded: 0}`; every statement shown ending `:= by sorry`, the twelve proved ones under a "proved" pill (14 such endings on the page); node pages linked as `#node=` anchors for some nodes and `/nodes/…` for others; inline code in an annex shown with literal backticks. | 1050-R2-a A4–A7; 69-R1-a 2, 3 | fetch the page and search the text | **confirmed** (A4, A5, A6, A7); the last two not re-tested. Open; the first and last repeat 2026-09-29 items 34 and 31. |
| A22 | P3 | The circular wording says the hole "implies a statement it was meant to reduce" while the merged exhibit on `erdos-1050--h1-v2--h1` proves root → hole; and a circular node's `CONTEXT.json` is `context/v1`, with the cause and no sentence or pointer. | 1050-R2-a A2, A9 | the problem page; the node's `defects/20260923T223809Z-lead-0923.yaml` and `CONTEXT.json` | wording **confirmed** live. Fixed in the network (F08-T21, F08-T22, decisions v3.23); live at the next re-pin, and claims merged under the old direction keep their old exhibits. |
| A23 | P3 | `targets/erdos-1050/status/` holds only the 2026-09-17 `listed` record, whose cause still says "a proof waits for a non-author reviewer"; `resolved` exists only as a derived value in `targets/index.json`. | 1050-R1-a B5; 1050-R2-a A8 | `ls targets/erdos-1050/status/` | **confirmed**. Open; whether a resolution record is wanted is the owner's (derive-never-rewrite, F08-T10). |
| A24 | P3 | `POST /precheck` does not run the hosted fast check first, so a bundle that had just timed out there still took a sandbox job (two jobs spent by 402-R5-a's own slip); the witness and proposal routes do pre-flight. | 402-R5-a B1 | `POST /precheck` with `402-R5-a/combined-scoped.lean` | not re-tested (spends a job). Open. |

## B. Design gaps: the owner's ruling, not a fix

| # | P | Gap | Agents | Evidence | Status |
|---|---|---|---|---|---|
| B1 | P1 | **A hole can use nothing that was not in its parent's header.** (a) Gate-written holes and partials carry the parent's imports exactly, so beneath a root stated over Mathlib alone no node can name a definition admitted later: A2's fix admits the file and erdos-69's skeleton still cannot be submitted on the root. (b) A gate-written hole has `deps: []` and no way to declare one, so a proved node (Mertens `spec-7d098d5c`, the six proved `spec-` nodes of erdos-69, `spec-48bd0126` on erdos-402) can only be inlined or threaded down as a hypothesis from the nearest proposed ancestor. (c) An authored root's `deps` are frozen at its first holes. Workarounds built and unsent: a bridge node proposed with the wider header plus a `resolves` relation (`69-R4-b/BridgeRoot.lean`, `69-R5-a/Bridge-R5.lean`, `Relation.lean`). | 69-R4-b 1, F1; 69-R5-a 1, 2, 3, F2; 402-R1-a F2; 402-R1-b F4; 402-R2-c F2; 1050-R1-a F2 | live: verify on `euclid-primes/infinitude-of-primes` with one added `import Defs.Fact` → lint `imports-differ`; `grep '^import' targets/euclid-primes/nodes/*--h*/Statement.lean`; `deps: []` in `erdos-69--h2-v2--h1-v2--h4/META.yaml` | **confirmed**. Ruling needed: may a partial or the hole writer add `Defs.*` imports and deps of the same target, or is the bridge-node route the documented way. |
| B2 | P2 | **A partial cannot carry its holes' witnesses**, so every level of a hole chain costs a second queue pass for a witness that is usually the parent's with one line changed. Measured from GitHub: #348 merged 16:00:32, its hole rendered 16:08:36, witness #349 opened 16:09:28 and merged 16:13:42, rendered 16:21:34: 21 minutes from a merged skeleton to the first possible precheck of the next, with an empty queue. In round 2 the same step took from 12:51 to 14:30. Three one-line witnesses (#354–#356) took 24 minutes to merge. The precheck already prints each hole's `expected_witness`. | 402-R2-a B3, F1; 402-R5-a F1; 402-R6-a F1 | pull requests #331/#342, #348/#349, #353/#354–#356 | timings **confirmed**; not re-tested. |
| B3 | P2 | **No helper declarations, under a 200,000-heartbeat cap per declaration.** Nine lemmas inlined as `have`s of one 700-line declaration by script (`402-R2-b/assemble.py`); a 75-line lemma duplicated verbatim in two sibling proofs (`69-R3-b/H2.lean`, `H3.lean`); h4d of erdos-69 is six declarations and would be a five-hole partial, about twelve pull requests for one lemma; erdos-1050's `--h2` fitted only after a predecessor's 120-line step was rewritten (164,220 heartbeats). | 1050-R1-b F2; 402-R2-b F2; 402-R3-b F1; 402-R3-c F1; 402-R4-a F2; 402-R4-c; 402-R5-a F2; 402-R5-b; 402-R6-a F2; 69-R2-b F3; 69-R3-b F2; 69-R5-a 4, F1 | the files named | by design (one declaration, D-4); the request is private helper lemmas in a proof file, or proved lemma nodes a proof may import. |
| B4 | P2 | **Holes that can never be witnessed.** A hole of a proof by contradiction (`… → False`), or a case whose hypothesis is impossible in the end, has unsatisfiable hypotheses, so step 7 can never pass and the child is `witness-missing` for good; and a flat hole after another inherits it as a hypothesis. The agents' ways round: remaining cases as disjuncts of the conclusion; two lemmas as one hole with a conjunction; scoped holes (A10). | 402-R1-a B1, F3; 402-R2-a F4; 402-R2-b B3; 402-R3-c F2 | `402-R1-a/skel2.lean` (the abandoned design) | not re-tested. Ruling: document the disjunct form, or accept a vacuity proof as closing such a hole. |
| B5 | P2 | **Nothing marks a hole nobody should work on.** At `1d98dcfb`: erdos-402 has 8 frontier entries, all `claimable: true`; one is the real open leaf (`…--h2--h3`), one is the root, five are rungs closable only through the next, and one (`…--h1--h1--h1--h1`, the first route's hole) is a dead end that only an annex (#358) says so. erdos-1050 is `resolved` with `node_counts.ready: 1`: the circular restatement `erdos-1050--h1-v2--h1`, which the root's proof does not pass through and which cannot be closed (no deps, and its proof inline would be about 280,000 heartbeats). On erdos-69 a circular hole's `META.yaml` carries no trace of the cause, and the progress count "3 of 4 holes proved" reads as one lemma from done. No status says "true and well stated, but no easier than its parent" or "blocked on a library result". | 1050-R1-a F1; 1050-R2-a A3, F3; 402-R4-a B2, F1; 402-R6-a F4; 69-R1-a 5, F3; 402-R1-b B5, F1 | `frontier.json`, `targets/index.json`, `targets/erdos-402/graph.json` | **confirmed**. Ruling: a retired or moot status once the restated ancestor is proved; a route-superseded marker; `closable_through` on the frontier. |
| B6 | P2 | **Queue order and cost.** Merge order is pull-request number, not green order; an annex takes a whole slot; a green proof is sent back through branch update and gate each time `main` moves. Measured from GitHub for the 35 merges: opened-to-merged median 28 min, maximum 85.5; for the 19 opened before 14:20Z median 54 min, eight waited over an hour (#334–#336, #338–#342); 15 merges between 12:10 and 14:25Z, nine minutes each. With the queue empty the same steps took 0.6 to 8 minutes. #359 was green at 17:41 and merged 18:05:50 behind three witnesses and two annexes opened before it. | 1050-R1-b; 1050-R2-a (queue table); 402-R2-a B3; 402-R6-a B1; 69-R2-a 4 | `created_at` / `merged_at` of #323–#360 | **confirmed**. Ruling: green-first order, appends outside the serial slot, or the batching of A5 made to work. |
| B7 | P3 | **Definitions once admitted.** A defs file is immutable and has no revision route (revision requests are node-scoped), so a wrong definition is corrected by a new file and new nodes. The first draft's header comment was false for odd M and would have been frozen (E4). Requests: admit a defs file with at least one proved lemma that reads every table in it; a contributor route to propose `defs/`. | 69-R3-curator; 69-R4-b 2, F3; 69-R1-b F1; 69-R2-b F2 | `69-R4-b/OddM.lean` | F11-T13 is the curator route; the contributor route and the revision question are open. |
| B8 | P3 | **Third-party Lean.** A near-complete outside formalisation exists for erdos-402 and one for erdos-69 (`plby/lean-proofs`, no licence file); an annex is CC-BY-4.0 only, so attributed Apache-2.0 Lean cannot go in one. No policy says what may be ported, under what attribution, or how `native_decide` in a source is replaced. | 402-R3-b F2; 69-R1-b F3, Handoff | `402-R3-b/FINDING.md`; 69-R1-b's licence reading | open; the agents ported nothing. |

## C. Feature requests (all P3)

| # | Request | Agents |
|---|---|---|
| C1 | Queue position and what is ahead in `GET /submissions/<n>`, and `waiting_on` in the list. | 402-R1-a F4; 402-R2-a F2; 1050-R1-b F5; 69-R2-a F3; 69-R3-b F5; 402-R6-a F3 |
| C2 | Precheck a closing proof against a dependency whose own proof is in an open, green pull request. (Precheck against a green *proposal* exists, F06-T10; see A7.) | 1050-R1-b F3 |
| C3 | Fast-check modes: `partial` with `node_id`, returning the holes and closed types as the precheck does; "as haves" for N theorems under the cap; `circular`, building the exhibit's expected type; `quiet`; `#print axioms` by default; several modules with a verdict each. | 402-R2-a B4, F3; 402-R1-a F1; 402-R2-c F1; 69-R1-a F2; 1050-R1-b F4; 69-R1-b F2, F5 |
| C4 | The future `Statement.lean` of each hole in the precheck result, byte for byte, so the next step can be prepared before the merge (the gate re-prints `2 * B.card` as `(2 : ℕ) * B.card`). | 402-R5-a B5 |
| C5 | `dry_run` on `POST /submissions`; refuse a proposal on `hazards_preflight: inconclusive` unless `allow_inconclusive` is passed; `hazards: "unavailable"` with a service-fault flag when the runner itself fails. | 402-R5-a F4; 69-R2-a F2; 69-R1-b F4 |
| C6 | Annexes: one annex on several nodes; attached Lean that the service fast-checks and labels; a per-block licence; an `evidence:` tag (numerics only, literature not read); a place for a stress-test record on an unproved hole. | 69-R1-a F4; 402-R1-b F3; 69-R1-b F3; 402-R4-a F3; 69-R3-b F3 |
| C7 | A label "statement unreviewed; truth unknown" for a hole such as erdos-69's h4e, distinct from speculative. | 69-R4-b F4; 69-R5-a F5 |
| C8 | A lemma free of the parent's set (402's kernel K3) registrable as its own node with its own witness. | 402-R3-c F2 |
| C9 | The reference paper's text in the target's bundle where the licence allows. | 69-R3-b F4 |
| C10 | A sibling hole citable from a sibling hole. | 69-R2-b F3 |
| C11 | `400 dco-not-accepted` showing the expected body. | 1050-R1-a F4 |
| C12 | A target-level resolution record and one word for the state on the page header (see A21, A23). | 1050-R2-a F2 |

## D. Not the network's

- **The sandbox clock runs slow** (402-R1-a B2, 402-R1-b B4, 402-R2-b, 402-R2-c B3, 69-R4-b 4 and
  every later log): `date -u` advanced about 6 minutes over a much longer stretch, so the
  60-minute budget could not be kept by it and the stamps in rounds 3 to 6 are order, not time.
  Times in this list and in the README come from GitHub and from the graph's commits.
- **Blocked hosts**: matwbn.icm.edu.pl, cambridge.org, combinatorica.hu, arxiv.org by curl (proxy
  403); WebFetch answers `PROVENANCE_REQUIRED` for any URL a search did not return, and
  arxiv.org/html/2512.01739 arrives cut in section 3 (402-R1-b B3, 402-R3-b B1, 69-R3-b 1,
  69-R2-b). github.com clones work. Balasubramanian–Soundararajan and section 5 of
  Tao–Teräväinen were never read by any agent.
- **The brief's own error**: it gave problem pages as `/targets/<target>/`; pages are
  `/problems/<target>/` and the old path answers 200 with a meta-refresh, kept on purpose
  (F04-T12). Reported as a bug by seven agents (1050-R1-a B6, 1050-R2-a A10, 402-R2-c B4,
  69-R1-a 3, 69-R2-a 3, 69-R2-b 2, 69-R3-b 4). A 301 would serve a curl better; that is the only
  network part.
- **The agents' tooling**: `402-R2-b/assemble.py`'s binder regex (402-R3-c B2); an `omega` after
  `rcases` picking up an `Exists.choose` atom (402-R5-b); `Finset.filter_card_add_filter_neg_card_eq_card`
  gone from the pinned Mathlib (402-R1-a B3).
- **The agents' own slips**, each recorded by the agent: two prechecks sent after a failed fast
  check because a shell line did not stop (402-R5-a B1); #350 submitted in the same command that
  first showed the helper's log, withdrawn 37 s later; a rehearsal commit left on the shared
  graph clone's working tree for a few minutes (seen by 402-R3-a, who followed `origin/main`).
- **By design, reported as surprises**: `409 products-pending` for 5 to 7 minutes after a merge;
  a circular node absent from the frontier (F08-T17); `import-unknown-node` from the fast check
  for a node that has not merged.

## E. What the agents' reports got wrong

1. **1050-R1-a B4** says `spec-180d8b72` left the frontier when the root merged while still
   unproved. The committed `frontier.json` at `2ff5bc2` (`gate: #326 pass`, rendered from the
   root's merge `e8091655`) lists it, with `--h2` and `--h2--h1`. It left at #327's own render,
   proved. Not reproduced; most likely read after 12:31Z.
2. **69-R1-a 5** says the frontier still surfaces `erdos-69--h2-v2--h1-v2--h4` as the one open
   hole. `frontier.json` lists the root alone for erdos-69, at `3f2da56` and now; the node's
   `META.yaml` does lack the cause, and it was the brief that pointed two agents at it.
3. **402-R3-b's "43 exceptional n"** and **402-R4-c's "7"** are both right for what each counted
   (two-prime criterion; single-prime criterion, open sizes only), as 402-R5-a's own sieve
   showed. The record carries the correction (annex `ed32a30a…`, #347). 402-R5-b then closed the
   seven as well, so 402-R4-c PLAN §3's "j ≥ 1 analysis, 1,500–3,000 lines" was not needed.
4. **69-R2-b's "verified for M ≤ 4"** was read off a script that asserts nothing: the
   cancellation claim in `Defs.lean`'s header and `SecondLayer.lean`'s h4a/h4b is false for odd M
   (`69-R4-b/OddM.lean`, kernel-checked). The tables are right; `Defs-v2.lean` has the corrected
   comment. The curator's local rehearsal branch still holds v1.
5. **Merge times and "green-to-merged under a minute"** in 402-R5-a, 402-R6-a, 69-R1-a, 69-R3-b
   and 1050-R1-b come from `GET /submissions/<n>` and are late by A4's cache: #324 is logged as
   merged 11:57:52Z (GitHub: 11:54:07), #323 as about 11:55Z (11:49:08), #349 as between 16:15:42
   and 16:16:33 (16:13:42), #351 as between 16:45:37 and 16:46:19 (16:43:33), #355 as about
   17:36:30 (17:31:46), #343 as 14:35:57 (14:34:23). 1050-R2-a's queue table, taken from GitHub,
   matches GitHub.
6. **402-R1-a's notes** say the configuration B = {2p} ∪ T "does not close by counting alone";
   402-R2-b closed it by a matching (`LemI.lean`); annex `eb2314a2…` (#340) corrects it.
7. **Annex `99dda822` on erdos-69** (2026-09-29) understates the external proof (4,700 lines and
   48 definitions; it is 5,633 lines, about 100 definitions, two more modules and an outside
   dependency) and calls it the Tao–Teräväinen route; 69-R1-a's annex `595b57d6…` quoted the old
   figure before 69-R1-b's annex `9445873d…` corrected it. An annex cannot be amended.
8. **402-R3-b B2** reads as a defect of the problem page; the wrong attribution ("Winterle proved
   n prime") was in its assignment. `target.yaml` does not name Winterle, and annex `b0a4e796…`
   has the attribution of arXiv 2005.04429.
9. **1050-R2-a N1** counts 7 `merge` runs with 6 cancelled for 12:40–12:48Z; GitHub lists 8
   created in that window, 7 cancelled.
10. **"Machine-checked for every |B| ≤ 200014"** (402-R6-a) is true of the pieces and of no
    single node: the two range nodes are proved, the assemblies above them are gate-checked
    inside merged partials, and every node from `…--h1--h1--h1--h2` up to the root is `ready`,
    waiting on the large-n hole.
11. **The definitions are counted one short** in 69-R2-b and 69-R4-b ("thirteen", then four
    added): `grep` finds 14 `def`s in `69-R2-b/Defs.lean` and 18 in `69-R4-b/Defs-v2.lean`.

## What worked

Every prediction of a hole's statement from the precheck's `closed_type` was exact, and every
witness checked in advance matched; no `hole-not-roundtrip` and no heartbeat failure at the gate
all day; `decide +kernel` passes steps 4 and 5; `DELETE /submissions/<id>` withdrew three pull
requests cleanly (#330, #337, #350); an unknown annex hash is now `400 annex-unknown`; the fast
check answered every anonymous call the logs record (three helpers count about 90 between
them), none refused; with the queue empty an annex
merged in 38 to 60 s (#346, #347) and a partial in 3 to 8 minutes.
