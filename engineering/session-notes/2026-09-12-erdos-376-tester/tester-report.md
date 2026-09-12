# Tester report: pushing the frontier of Erdős 376 as a first-time contributor

Tester identity: pseudonym `agent-062b0f` (identity `01M2BX632G8F6ZC57HH9R5M5WF`, tutorial proof).
A second identity was minted under the pseudonym `thisisanameforsure` (`01M2BXGD50YAZRFA5T9T6J75CG`) — see bug 8.
Bench: site at 127.0.0.1:8080 (graph commit `02a4e239`), service at 127.0.0.1:8000 (memory store, fake host,
precheck always passes), no Lean, no Docker. Scratch files: `scratchpad/tester/`. Own git clone for git-path
experiments: `scratchpad/tester/graph-clone` (13 local branches, nothing pushed). The shared clone's `main` is
untouched (`git status` clean, HEAD `02a4e23`).

## 1. Journey

1. **Orientation on the site.** `/targets/` says erdos-376 is "Status listed, listed, not claimable" with three
   reasons (status listed; fidelity below screened-and-signed; not posted upstream). The target page
   `/targets/erdos-376/` says only "Status listed, fidelity mechanical-only" and draws one node "ready". The node
   page `/nodes/erdos-376/erdos-376/` says **"ready to prove"**. The frontier page lists it with Claimable = no.
   Nothing on the site shows the intake's prior art (EGRS 1975 two-prime theorem, the AlphaProof attempt) or the
   curator's `attack_routes` — both exist in `targets/erdos-376/target.yaml` but are rendered nowhere (feature 1).
   So a newcomer learns *that* 376 is unclaimable from the Targets index only, learns *why* in protocol jargon,
   and learns nothing about what is already known about the problem.
2. **Guide walkthrough, token.** The guide's tutorial blocks worked verbatim on the HTTP path: anonymous
   `POST /precheck` (202, nonce), poll → `done`/`pass`, `POST /tokens` → 201 with a token. Nonce replay refused
   (`proof-invalid`). Pseudonym collision refused (`pseudonym-taken`). Stale DCO version and `accepted:false`
   refused with clear messages.
3. **Claim erdos-376.** `POST /claims {"node_id":"erdos-376"}` → **409 `node-not-claimable` "erdos-376 is not
   claimable"** — correct outcome, but the body carries no reason and no pointer, although `targets/index.json`
   already carries the machine-readable reasons `["status-listed","grade-below-screened-and-signed","no-posting"]`
   (bug 1). Claim edge cases were all clean: unknown node 404, tutorial node 404 "not in the frontier", ttl 0/
   string 400, ttl 999 400 naming the cap, no bearer 401, bad bearer 401. I claimed the one claimable node
   (`variant-93e79cb5`, target tutorial) to exercise the claim lifecycle.
4. **Annex (the Kummer route).** `POST /annexes` on erdos-376 → 201, PR #1, hash `797238e9…f8ea`. The text
   reduces "C(2n,n) coprime to 105" to "every base-3 digit ≤ 1, base-5 digit ≤ 2, base-7 digit ≤ 3" (Kummer),
   names the two-prime EGRS 1975 result, the density heuristic (exponent ≈ 0.026 for three primes vs ≈ 0.31 for
   two), and three routes. Sending the identical body again in the same second produced a second PR (#2) at the
   same path (bug 6/7). Bad licence, empty text, unknown node and a 70 KB annex were all refused correctly.
   **Honesty note:** the annex's computational aside ("n = 1, 2, 10, 3160, 3161, …") is wrong; I recomputed after
   submitting: the members below 2·10^5 are 1, 10, 756, 757, 3160, 3186, 3187, 3250, 7560, 7561, 7651, 20007
   (and the Kummer reduction checks numerically on all of them). The MCP annex (#17) repeats the wrong list.
   Both are untrusted prose and hedged as such, but the orchestrator should not merge them as they stand.
5. **Proposals.** Related variant (3,5 case) → PR #10 `variant-e30ecfbb`; the same body again → PR #11 same node
   id; the same variant on target `tutorial` → PR #14 accepted (bug 9); speculative crux L2 (the digit set is
   infinite) → PR #12 `spec-15b60cb6`; crux L1 (Kummer reduction) with `deps:[erdos-376]` → PR #13
   `spec-b2fa4f04` with a generated `Context.lean` carrying the root's statement; a `partial`-labelled variant
   (5,7 case) with a real `Relation.lean` proving root → variant → PR #18 `variant-192f1297`. Refusals that were
   right: `partial` without a relation proof, `related` with one, a bad label, a `-- relation:` line disagreeing
   with the label, no sorry body, two theorems, a `def`, missing witness, unknown dep, 70 KB statement. Accepted
   when I expected a refusal: a witness containing `sorry` (PR #15, bug 10), a `resolves` variant whose relation
   proof is `theorem relation : True := sorry` (PR #19, bug 11), a statement importing
   `Nodes.«erdos-376».Context` (PR #20 — admission will refuse it; the service could have).
6. **Skeleton (partial).** Wrote the assembly (`kummer_105` and `small_digits_infinite` as `have … := sorry`,
   set equality proved, `rw`+`exact`), citing the annex hash on the first body line. The guide never says which
   path a partial travels under, so I prechecked both: `Proof.lean` (job `…H903`) and
   `attempts/20260912T225709Z-agent-062b0f-partial.lean` (job `…251A`). Both "passed" (simulated). Submitted the
   attempts-path bundle as `artifact_type: partial` → PR #7 (the correct shape per the gate's `classify`, which
   says `mode: partial` for that branch in my clone). The same submission replayed → PR #8; the `Proof.lean`
   bundle declared `partial` → PR #9 accepted (bug 4). Submission checks that were right: bundle/job digest
   mismatch, missing job id, another identity's job (`precheck-not-yours`), anonymous tutorial job, touching
   `Statement.lean`, two nodes, `..` segments, 600 KB bundle (512 KiB cap), 5 MB body (413 at 1 MiB).
7. **Postmortem and approach record.** `POST /postmortems` on erdos-376 (density route, `direct-estimate`,
   `blocked`, `missing-library`, goal state at the joint, two named missing lemmas, annex hash) → PR #3. Two probe
   postmortems in the same second → PRs #4, #5 at the **same file path** as #3 (bug 6). A YAML `node:`/
   `contributor:` spoof was overwritten by the service (correct). Wrong enum, missing `outcome`, 4001-char detail
   all refused with the field named. `POST /approach-records` (explicit-construction route, abandoned-early) →
   PR #6; unknown target 404.
8. **MCP path.** `initialize` and `tools/list` work with no bearer; every read tool worked unauthenticated
   (`get_node`, `get_target`, `list_frontier` with filters, `get_defs`, `get_gate_spec`, `get_precheck`,
   `server_info`, `list_targets`). Writes without a bearer → 401 passed through; with the bearer, `claim_node`,
   `release_claim`, `submit_informal_annex` (PR #17), `submit_postmortem` (PR #23), `submit_proof` (PRs #21, #22)
   all worked. But the tools do **not** take the plain endpoints' argument names (bug 12), `get_schema` fails for
   every schema the guide points at (bug 5), and `get_submission` wants zero-padded ids (bug 13).
9. **Git path in my own clone.** `classify` gives `mode: partial / needs_gate: true` for the attempts-path
   skeleton, `append` for an annex, a postmortem and an approach record, `proposal / needs_admission` for a
   `scaffold`-written crux directory, and refuses two-node branches and an explainer on an unproved node — all
   right. It also says `ok: true` for a skeleton citing a non-existent annex and for one with a malformed short
   hash (bug 14). The guide's `pregate.sh` line fails on the live graph: `--target is required` (bug 3); with
   `--target` it fails for want of elan, as the brief said it would.
10. **Limits.** Active-claims cap (20) → 429 with `Retry-After`; anonymous prechecks (20/day) → 429; per-identity
    writes (120/h) → 429, reached by 54 *refused* claims, i.e. 4xx writes are charged (bug 27). Prechecks and
    reads continued under the capped identity; the MCP adapter passed the 429 and `retry_after` through; the
    other identity was unaffected. All 20 cap-test claims and both earlier claims were released (double release is
    idempotent; releasing another identity's claim → 403); one final claim `01M2BXV3XR47KSVG6ACP6V758T` on
    `variant-93e79cb5` is still active (expires 2026-09-13T00:04:35Z) because the write cap locked my token
    before I could release it.
11. **Site afterwards.** Nothing changed and nothing could: the site renders committed files, none of my 23 pull
    requests is merged, and the site's `frontier.js` filters the static table without reading the service's
    overlay. The service's `/frontier.json` did show my claims live; `annex_present` and `attempts` on erdos-376
    stay false/0 until a merge.

**How far did the frontier of 376 move?** Formally, not at all — and correctly so: the root is `listed`, so no
claim can be held, and every artifact I filed sits in an unmerged pull request. What I could put into the record
(pending merge): one informal argument, one skeleton whose two holes would become `erdos-376--h1` (the Kummer
reduction) and `erdos-376--h2` (the digit-set infinitude), two speculative cruxes stating the same two lemmas as
standalone nodes, a related (3,5) and a partial-labelled (5,7) variant with a relation proof, a typed postmortem
for the density route, and an approach record. The network's own rules make the partial the most useful of these
and the cruxes near-duplicates of its holes; a curator will want to consolidate (D-29).

## 2. Bugs

Severity key: **blocks** = blocks a contributor; **record** = wrong or lost record; **confusing**; **cosmetic**.

1. **[service, confusing] `POST /claims` on erdos-376 gives no reason.** Request `{"node_id":"erdos-376",
   "ttl_hours":2}` → `409 {"error":"node-not-claimable","message":"erdos-376 is not claimable"}`. Expected the
   reasons the graph already publishes (`targets/index.json` → `not_claimable: ["status-listed",
   "grade-below-screened-and-signed","no-posting"]`) and what unblocks them. The MCP `claim_node` passes the same
   body through. Same for `infinitude-of-primes--h1`.
2. **[site, confusing] The node page says "ready to prove" for a node nobody may claim.** `/nodes/erdos-376/
   erdos-376/` headline "ready to prove"; `/targets/erdos-376/` shows status `listed` with no explanation; only
   `/targets/` (the index) explains, and it prints **"Status listed, listed, not claimable"** (duplicated word,
   cosmetic). The frontier page shows Claimable = no without a reason column. A newcomer sees three pages
   disagreeing about whether they can work on 376.
3. **[guide, blocks git path] `pregate.sh` as written fails on the live graph.** Guide block: `"$NETWORK/gate/
   pregate.sh" --graph "$GRAPH" --node "$NODE" --out "$OUT"`. On the live graph (7 targets): `opn-gate: --target
   is required; graph has targets [...]`, exit 2. The block is tagged `sh lean` so the doc test (fixture graph, one
   target) never runs it against a multi-target graph.
4. **[guide + service, blocks/confusing] The partial's bundle path is undocumented and the service accepts the
   wrong one.** The guide's skeletonization section says "submit it as `artifact_type: partial`" but the only
   bundle it ever shows is `targets/<t>/nodes/<n>/Proof.lean`. The gate's own `classify` treats a `Proof.lean` as
   mode `proof` (I verified: a sorry-bearing `Proof.lean` classifies `proof`, `ok: true`) and a
   `attempts/<ts>-<pseudonym>-partial.lean` as mode `partial`. `POST /submissions` with `artifact_type:
   "partial"` and a `Proof.lean` bundle returned 201 (PR #9); that pull request will fail at kernel replay/axioms
   with no hint that the file was simply in the wrong place. Expected: the guide to name the path, and the service
   to refuse `partial` at `Proof.lean` (and `proof` under `attempts/`) since `opn_gate.paths` already knows the
   roles.
5. **[guide + service, confusing] `get_schema` / `schemas/<name>.json` do not exist for the schemas the guide
   names.** Guide: "`get_schema("postmortem/v1")` or `schemas/postmortem/v1.json` has the whole shape." The graph
   clone holds only `schemas/{attestation/v1,v2, gate-spec/v1, meta/v1}`; `info.json` advertises 27 schema
   families; MCP `get_schema("postmortem/v1")` → `{"error":"not-found","message":"the graph has no
   schemas/postmortem/v1.json at main"}`, same for `meta/v2`, `attestation/v4`; only `meta/v1` works. The
   adapter reads the graph, but the schemas live in the network repo's `gate/schemas/`.
6. **[service, record] Append file names collide within one second and the caller is told 201 each time.**
   Three `POST /postmortems` in one second → PRs #3, #4, #5 all adding
   `attempts/20260912T225733Z-agent-062b0f.yaml`; two annexes in one second → PRs #1, #2 same hash and path
   (`date` is second-granular, so identical text hashes identically). `appends.py` documents this as "the gate
   then rejects the second as a modification" — but each PR is its own branch off `main`, so all three are
   additions until the first merges, after which the other two become modifications and are refused, and their
   authors saw 201 and a `pr_url`. A second genuine postmortem filed within a second of the first is silently lost.
   Expected: the ULID (already minted as `id`) in the file name, or a collision check.
7. **[service, confusing] No idempotency or duplicate detection.** Identical annex (#1/#2), identical variant
   (#10/#11 → same `variant-e30ecfbb`), identical crux (#12/#15 → same `spec-15b60cb6`), and the same precheck job
   bound to four submissions (#7, #8, #21, #22) each opened a fresh pull request. `scaffold.speculative_id`'s
   docstring says a duplicate "collides by name rather than entering the graph twice", but only at merge time; a
   retrying client fills the graph's PR list. Expected: 409/200-with-existing for content already on `main` or in
   an open PR, and a precheck job consumed by its first submission.
8. **[service + protocol, record risk] The curator's pseudonym was mintable as a fresh identity.** `POST /tokens`
   with `pseudonym: "thisisanameforsure"` (the only login in the graph's `curators.json` and the gate owner)
   → 201, identity `01M2BXGD50YAZRFA5T9T6J75CG`. That identity then filed a postmortem on erdos-376 (PR #16, file
   `attempts/20260912T230006Z-thisisanameforsure.yaml`, `contributor: thisisanameforsure`) and held a claim shown
   on the frontier under the curator's name. Uniqueness is enforced only against the service store; names the
   *graph* reserves (curators, gate owner) are not. On the live store the name may already be taken, but the
   reservation should come from the graph, and D-21 ("curators may not claim proof credit on targets they
   curate") is enforced nowhere I could find. (The probe record is labelled TEST in its `detail`; do not merge.)
9. **[protocol gap / confusing] A variant of erdos-376 was accepted on target `tutorial`.** `POST
   /proposals/variant {"target_id":"tutorial", statement: <the 3,5 case>, relation:"related"}` → 201, PR #14,
   node `variant-e30ecfbb` under `targets/tutorial/nodes/`. Nothing checks that a `related` variant bears on its
   target (D-30 v3.12 relies on a later relevance signature), so admission will put a number-theory node under the
   tutorial target. Expected at least a refusal when the statement's declaration name/namespace or imports do not
   match the target's root, or a "pertinence unsigned" state visible on the frontier.
10. **[service, confusing] Inconsistent `sorry`-witness handling.** `/proposals/witness` refuses a witness with
    `sorry` (`witness-invalid`), but `/proposals/speculative` and `/proposals/variant` accept one (PR #15). The
    crux would enter admission with a stub witness and, per `postmerge.WITNESS_SLOT`/`graph.witness_is_stub`,
    presumably land blocked rather than refused. Expected the same cheap refusal in all three.
11. **[service, cosmetic] `resolves` with `theorem relation : True := sorry` accepted (PR #19)** and the
    `-- relation: resolves` line was prepended *above* `import Mathlib`. Admission will refuse (`relation-sorry`),
    which is fine, but the same `"sorry" in text` check used for witnesses would have saved a pull request. Lean
    tolerates a line comment before `import`, so the prepend is harmless but ugly; putting it after the header
    would read better.
12. **[guide + service, confusing] MCP tool arguments are not the plain endpoints' fields.** Guide: "Every MCP
    tool is exactly one of the calls above". Differences found: `claim_node` takes `ttl` (not `ttl_hours` — sending
    `ttl_hours` is refused `arguments-invalid`); `propose_speculative_node`/`propose_variant` take `stmt` (not
    `statement`); `submit_proof` takes `attestation` (an object; only its `id` is used — `{"id": job}` works) instead
    of `precheck_job_id`; `submit_postmortem.yaml` must be a JSON **object** (a YAML string, which the HTTP route
    accepts, is refused with a raw validator message: `'route: …' is not of type 'object'`). The guide's appendix
    maps names only, not arguments.
13. **[service + guide, confusing] `get_submission` id format.** Guide: "the signed attestation is
    `attestations/<pull request number>.json`"; submission responses return `pr_number: 7`. The graph's files are
    `attestations/000002.json`, `000019.json`; `get_submission("2")` would fail, `get_submission("000002")` works.
    Also `get_submission` on a merged *proposal* (PR #23 on the live graph) says "no attestations/23.json" — a
    proposal earns no attestation, but the tool cannot say so.
14. **[gate, record] The annex-citation rule is enforced only after merge.** D-31: "The named annex must be
    present on the node or the submission is rejected." `check_annex_citation` is called only from
    `postmerge.apply_partial` (`postmerge.py:416`); `classify` returns `ok: true` for a skeleton citing
    `-- annex: 000…000` and for a malformed `-- annex: 797238e9`, and nothing in `pipeline.py`/`steps/` calls it.
    So a mis-cited skeleton passes the gate, merges into `attempts/`, and the post-merge job then raises
    `GraphWriteError` — after the merge, with no children created, and (per the project log) a post-merge failure
    loses its ledger line. Expected: the citation check as the artifact step's last word pre-merge, like the
    offload rule (`steps/artifact.py`) already is.
15. **[protocol ambiguity] Submissions and prechecks against a `listed` (unclaimable) root are accepted.**
    Authenticated `POST /precheck` and `POST /submissions` on erdos-376 both succeeded (PRs #7–#9, #21, #22)
    although the node cannot be claimed and D-33 defines `listed` as "not yet claimable". Either this is intended
    (claims are advisory; the comment period should still collect artifacts) — then the 409 on claims is the odd
    one out and the site should say "unclaimable but open to artifacts" — or the gate/service should refuse
    building submissions on listed targets. `submissions.py` never consults `claimable`.
16. **[site, confusing] The docs page contradicts the service on DCO/licence.** `/docs/` says "No license text is
    committed to the graph yet" and "No sign-off (DCO) text is committed to the graph yet; D-23 settles it before
    the first external contributor", while every write requires accepting the DCO served at `/dco.json` and
    annexes require an SPDX licence.
17. **[guide, confusing] Explainers are listed as appendable by anyone but have no endpoint and are refused on
    unproved nodes.** The permitted-paths table lists `explainer/<sha256>.md — anyone — append`; there is no
    `POST /explainers` and no MCP tool; on the git path `classify` refuses one on erdos-376 with
    `explainer-unproved: … an annex misfiled as an explainer` (correct per D-3, unstated in the guide).
18. **[service, confusing] One identity may hold many active claims on one node.** I held 20 simultaneous claims
    on `variant-93e79cb5` (all 201). The frontier then showed 20 "active" entries by one pseudonym, which defeats
    the guide's own filter policy (`not e["claims"]["active"]`) for everyone else. Expected: a second claim by the
    same identity to extend or return the existing one.
19. **[service, confusing] Refused writes are charged against the hourly write budget.** 54 `POST /claims` on a
    nonexistent node (404 each) exhausted `writes_per_hour: 120` → 429 `retry-after: 3274`. A contributor
    debugging request bodies burns the hour. (Prechecks have their own bucket and kept working; reads unaffected;
    the anonymous-precheck counter reads 22 for a limit of 20 — cosmetic.)
20. **[service, cosmetic] JSON-RPC batch requests are refused with a raw pydantic validation dump** (four
    "validation errors for JSONRPCMessage" with a pydantic docs URL). `GET /mcp` without an SSE `Accept` gives a
    JSON-RPC 406 (fine).
21. **[bench artifact, not a bug, for the record] The simulated precheck attestation carries `graph_id:
    "propositional"`, `statement_hash: "aaaa…"`, `network_commit: "0123…"`,** and those bytes are what went into
    the PR bodies (#7–#9, #21, #22). Anything replaying these should regenerate the attestation.
22. **[guide, cosmetic] The postmortem section's HTTP example omits nothing, but the git-path shape differs
    silently:** the service fills `schema`, `node`, `contributor`; a git-path file without `schema:` is refused by
    `classify` (`declares 'None'`). Worth one sentence.
23. **[site, confusing] The site does not surface the service's live claim overlay** — `frontier.js` only filters
    the static table; the page shows "0 active" while `/frontier.json` showed 21. By design (D-36), but the page
    could link the live document.

## 3. Features wanted (as a contributor trying to make progress on 376)

1. **Show the intake's prior art and attack routes on the target page.** `target.yaml` records "Open since 1975.
   EGRS75 proved the two-prime case… 105 = 3·5·7 is the first three-prime case. Attempted by AlphaProof Nexus
   (Feb 2026)… " and `attack_routes: Kummer's theorem… density heuristic`. None of it reaches `/targets/erdos-376/`,
   `targets/index.json`, `get_target` or `get_node`. This is the single most useful thing a newcomer to 376 could
   read, and I had to open the clone to find it.
2. **A claimability explanation with a path to claimable**, on the 409, on the node page and in `list_frontier`:
   the three `not_claimable` codes, who can sign the statement (a non-author reviewer, D-9), what "posted
   upstream" means (D-10) and whether artifacts are welcome meanwhile (bug 15).
3. **"My pending contributions."** After 23 pull requests I have no way, through the site, the HTTP api or MCP, to
   see them, their gate status, or whether the node ids I proposed (`spec-15b60cb6`, `variant-192f1297`) exist yet
   (`get_node` → `node-unknown`). A `GET /submissions?identity=me` or a `list_pull_requests` read tool.
4. **A dry-run for proposals and partials.** Admission cannot be rehearsed without the toolchain, and the
   toolchain needs Mathlib. Wanted: `POST /proposals/*?dry_run=true` running the toolchain-free checks the service
   already can (layout, sorry-free witness, relation label/direction, imports, slug, duplicate node id, and the
   expected witness type from the statement's binders); and for partials a report of the holes' closed types and
   the children that would be created — the offload rule and the hazard checkers on the children (the project log
   records bot-created holes carrying `2 ≤ m` being blocked by `off-by-one-range`; my `h2` child will carry an
   unused `kummer_105` hypothesis and may trip `unused-binder`).
5. **Tell me the node id before I submit.** `variant-<sha256(statement)[:8]>` is derivable but undocumented; a
   `Relation.lean` or annex that wants to name the node cannot. Return it from a dry run, or document the rule.
6. **Serve the schemas the service validates against** (`gate/schemas/` at the pinned `network_commit`) from
   `get_schema`, and put the field shapes for `evidence` (`{text, exhibit?}`), `record`, `tooling` in the guide.
7. **Idempotent writes**: content hash already on the node or in an open PR → return the existing PR; consume a
   precheck job on first submission; ULID-named append files.
8. **A guide section that submits a partial end to end** (path under `attempts/`, `artifact_type`, the annex
   citation line, what the children will look like), and a `pregate.sh` line with `--target`.
9. **Claim semantics for one identity** (extend rather than stack) and a `GET /claims.json` link in the guide and
   MCP table (it exists and is useful).
10. **Reserved names from the graph** (`curators.json`, `gate_owner`) at token minting, and D-21 enforced at
    the credit step.
11. **For 376 itself:** a curator-seeded decomposition would save every newcomer the same first hour — the
    Kummer reduction is routine and the digit-set infinitude is the whole problem; the two-prime cases (EGRS 1975)
    are natural `partial`-labelled variants that are provable today and would exercise the pipeline on a real
    theorem while the root waits for its signature.

## 4. Writes log

Fake-host pull requests (numbered in the order the host assigned them; `records/pulls.json`), all on repo
`thisisanameforsure/open_proof_network_graph`, base `main`, author `agent-062b0f <agent-062b0f@anon.opn.invalid>`
unless noted, committer `open-proof-network[bot]`:

| # | Endpoint / tool | Node / target | id returned | Branch | Files sent |
|---|---|---|---|---|---|
| 1 | `POST /annexes` | erdos-376 | `01M2BX99KR7D62M8H6G867KMQH`, hash `797238e9ba74e4ac122fda8233eb122ce36c34cdea480f05e2a25152a5b1f8ea` | `append/01M2BX99KR7D62M8H6G867KMQH` | `targets/erdos-376/nodes/erdos-376/annex/797238e9….md` (Kummer route; source `tester/annex-376.md`) |
| 2 | `POST /annexes` (identical body, duplicate probe) | erdos-376 | `01M2BX99KR2TH0T7TZ1NDXQ6V9`, same hash | `append/01M2BX99KR2TH0T7TZ1NDXQ6V9` | same path as #1 |
| 3 | `POST /postmortems` | erdos-376 | `01M2BXE7T81XXTKPXDJN4C9NRW` | `append/01M2BXE7T81XXTKPXDJN4C9NRW` | `…/attempts/20260912T225733Z-agent-062b0f.yaml` (direct-estimate / blocked / missing-library, annex cited; source `tester/postmortem-376.yaml`) |
| 4 | `POST /postmortems` (spoof probe: YAML said `node: erdos-52`, `contributor: thisisanameforsure`; service overwrote both) | erdos-376 | `01M2BXE7T8GPB34K4QRYX3HQGS` | `append/01M2BXE7T8GPB34K4QRYX3HQGS` | **same path as #3**; route "spoof test", induction, abandoned-early |
| 5 | `POST /postmortems` (`yaml` sent as a JSON object) | erdos-376 | `01M2BXE7T8JQNM4N6SV45YY1A8` | `append/01M2BXE7T8JQNM4N6SV45YY1A8` | **same path as #3**; computational, abandoned-early |
| 6 | `POST /approach-records` | target erdos-376 | `01M2BXE7T8F3Q7YSJC58XPSR04` | `append/01M2BXE7T8F3Q7YSJC58XPSR04` | `targets/erdos-376/approaches/20260912T225733Z-agent-062b0f.yaml` (explicit construction, abandoned-early) |
| 7 | `POST /submissions` `artifact_type: partial`, `precheck_job_id: 01M2BXDGC8JHWD914XJ1FM251A` | erdos-376 | `01M2BXFWHR9YC01AZW83CZW7EK` | `submit/01M2BXFWHR9YC01AZW83CZW7EK` | `…/attempts/20260912T225709Z-agent-062b0f-partial.lean` (the skeleton, `tester/skeleton-376.lean`) |
| 8 | `POST /submissions` (replay of #7) | erdos-376 | `01M2BXFWHRSTGKF703617RYFDK` | `submit/01M2BXFWHRSTGKF703617RYFDK` | same as #7 |
| 9 | `POST /submissions` `partial`, job `01M2BXDGC86V0RZMW1HTAQH903` | erdos-376 | `01M2BXFWHR7GN86S5NY43RJXXQ` | `submit/01M2BXFWHR7GN86S5NY43RJXXQ` | `…/erdos-376/Proof.lean` (the skeleton at the wrong path — expected to fail the gate) |
| 10 | `POST /proposals/variant` `relation: related` | erdos-376 → `variant-e30ecfbb` | `01M2BXH9F85CGHPNK45P6EG9B8` | `propose/01M2BXH9F85CGHPNK45P6EG9B8` | `targets/erdos-376/nodes/variant-e30ecfbb/{Statement,Witness,Context}.lean, META.yaml, attempts/annex/explainer/.gitkeep` (`Opn.erdos_376_two_primes_3_5`) |
| 11 | `POST /proposals/variant` (duplicate of #10) | same | `01M2BXH9F87KB3AQDNYXSTSZTK` | `propose/01M2BXH9F87KB3AQDNYXSTSZTK` | same |
| 12 | `POST /proposals/speculative` deps `[]` | erdos-376 → `spec-15b60cb6` | `01M2BXH9F8RDHGGTK0MMYYDS48` | `propose/01M2BXH9F8RDHGGTK0MMYYDS48` | node dir + `status/20260912T225913-agent-062b0f.yaml` (`Opn.erdos_376_small_digits_infinite`) |
| 13 | `POST /proposals/speculative` deps `["erdos-376"]` | erdos-376 → `spec-b2fa4f04` | `01M2BXH9F8NRTAMSNHA4QFNWRT` | `propose/01M2BXH9F8NRTAMSNHA4QFNWRT` | node dir; `Context.lean` carries the root's statement (`Opn.erdos_376_kummer_105`) |
| 14 | `POST /proposals/variant` on **target `tutorial`** (wrong-target probe) | tutorial → `variant-e30ecfbb` | `01M2BXH9F8TJ4EDVK81C7BVDDJ` | `propose/01M2BXH9F8TJ4EDVK81C7BVDDJ` | `targets/tutorial/nodes/variant-e30ecfbb/…` — do not merge |
| 15 | `POST /proposals/speculative` with `theorem witness : True := sorry` | erdos-376 → `spec-15b60cb6` | `01M2BXH9F8SH537GJ5K12J3EBT` | `propose/01M2BXH9F8SH537GJ5K12J3EBT` | node dir with a sorry witness — probe |
| 16 | `POST /postmortems` **as identity `thisisanameforsure`** (`01M2BXGD50YAZRFA5T9T6J75CG`) | erdos-376 | `01M2BXJX7GVG2WGMN2X0RQYBEZ` | `append/01M2BXJX7GVG2WGMN2X0RQYBEZ` | `…/attempts/20260912T230006Z-thisisanameforsure.yaml` — impersonation probe, labelled TEST, do not merge |
| 17 | MCP `submit_informal_annex` | erdos-376 | `01M2BXKQK8S2N5V8BYNJFSSC99`, hash `271695b95d6fd236cfee74645b7532c13a76846e6f72e98eb5297fd13df1f5df` | `append/01M2BXKQK8S2N5V8BYNJFSSC99` | `…/annex/271695b9….md` (short computational note; its listed values are wrong, see Journey 4) |
| 18 | `POST /proposals/variant` `relation: partial` + `relation_proof` | erdos-376 → `variant-192f1297` | `01M2BXPKCRMH4PZTVCZQFEZD2W` | `propose/01M2BXPKCRMH4PZTVCZQFEZD2W` | node dir + `Relation.lean` (`Opn.erdos_376_two_primes_5_7`; sources `tester/variant-5-7.lean`, `tester/relation-5-7.lean`) |
| 19 | `POST /proposals/variant` `relation: resolves`, relation proof `theorem relation : True := sorry` | erdos-376 → `variant-00c948f7` | `01M2BXPKCR5ZJQR5HWXKE9EJYJ` | `propose/01M2BXPKCR5ZJQR5HWXKE9EJYJ` | probe — admission should refuse (`relation-sorry`) |
| 20 | `POST /proposals/speculative` statement importing `Nodes.«erdos-376».Context` | erdos-376 → `spec-6d0f878a` | `01M2BXPKCRVTG50KHNDJMWR61Q` | `propose/01M2BXPKCRVTG50KHNDJMWR61Q` | probe (`Opn.ctx_probe : True`) — admission should refuse the import |
| 21 | MCP `submit_proof` (`attestation` = full `get_precheck` result of job `…251A`) | erdos-376 | `01M2BXSH4RT37FHX0AWW5YF7R3` | `submit/01M2BXSH4RT37FHX0AWW5YF7R3` | same bundle as #7 |
| 22 | MCP `submit_proof` (`attestation: {"id": "…251A"}`) | erdos-376 | `01M2BXSH4RJG37YS45QTGD562F` | `submit/01M2BXSH4RJG37YS45QTGD562F` | same bundle as #7 |
| 23 | MCP `submit_postmortem` (`yaml` as object) | erdos-376 | `01M2BXSH4RE0G9XKX5YTSKMKGF` | `append/01M2BXSH4RE0G9XKX5YTSKMKGF` | `…/attempts/20260912T230343Z-agent-062b0f.yaml` (computational, abandoned-early, route-dead-ends) |

Store-only writes (no pull request):

- Prechecks: anonymous tutorial `01M2BX5DK0836ATQM3PZ5Y9C8H` (minted identity 1); a second anonymous tutorial job
  (minted identity 2); authenticated erdos-376 `01M2BXDGC86V0RZMW1HTAQH903` (Proof.lean skeleton) and
  `01M2BXDGC8JHWD914XJ1FM251A` (attempts-path skeleton); authenticated tutorial `01M2BXRYK07WXQNKVSN416R4W1`;
  17 further anonymous tutorial prechecks (daily-cap test, the 18th → 429).
- Tokens: identity 1 `01M2BX632G8F6ZC57HH9R5M5WF` / `agent-062b0f`; identity 2 `01M2BXGD50YAZRFA5T9T6J75CG` /
  `thisisanameforsure` (bug 8). Refused attempts: same pseudonym, `accepted:false`, stale DCO, `Bad Name!`,
  `proof.kind: magic`, `github` with junk code.
- Claims (all on `variant-93e79cb5`, target tutorial): `01M2BX632G1M2HSVP8JMCENB0T` (released via MCP),
  `01M2BXC5D8TE1NG1XPZEZCVF3J` via MCP (released), `01M2BXJX7G8XMDHC93BA229JXD` by identity 2 (released),
  19 cap-test claims (all released; the 20th attempt → 429), and **`01M2BXV3XR47KSVG6ACP6V758T` — still active,
  expires 2026-09-13T00:04:35Z** (could not release: hourly write cap reached).
- 54 refused `POST /claims` on `no-such-node` (write-cap test) — no records.

Git-path branches in `scratchpad/tester/graph-clone` (never pushed): `partial/376`, `annex/376`, `attempt/376`
(schema-less, refused by classify), `attempt2/376`, `explainer/376` (refused), `proof/376`, `two/376` (refused),
`partial-annex/376` (botched cherry-pick, empty), `partial-annex2/376`, `partial-bad-cite/376`,
`partial-malformed/376`, `approach/376`, `propose/crux`.

## 5. Unverified Lean

None of these could be compile-checked here (no elan, no Mathlib). Estimates against Mathlib at the pinned sha
(`0df444a3…`, Lean `v4.33.1`):

1. **The skeleton** (`tester/skeleton-376.lean`; PRs #7, #8, #21, #22 under `attempts/`, #9 at `Proof.lean`).
   Header, name and signature are the statement's bytes; body:
   `have kummer_105 : ∀ n : ℕ, n.centralBinom.Coprime 105 ↔ ((∀ d ∈ Nat.digits 3 n, d ≤ 1) ∧ (∀ d ∈ Nat.digits 5 n,
   d ≤ 2) ∧ (∀ d ∈ Nat.digits 7 n, d ≤ 3)) := sorry`; `have small_digits_infinite : {n | …}.Infinite := sorry`;
   `have hset : {n | n.centralBinom.Coprime 105} = {n | …} := by ext n; simp only [Set.mem_setOf_eq]; exact
   kummer_105 n`; `rw [hset]; exact small_digits_infinite`. **Likely elaborates (~85%).** Risks: `simp only
   [Set.mem_setOf_eq]` making "no progress" if `ext` already unfolds membership (then drop the line; `exact` works
   by defeq either way); `Nat.digits` and `Nat.centralBinom` are the current names. Mathematically the reduction is
   right (checked numerically on every member below 2·10^5). Gate-side: two holes, neither defeq to the goal, so
   the offload rule passes; child `h2` will carry `kummer_105` as an unused hypothesis (F11-Q22) and may be flagged
   by `unused-binder` (step 6), which would leave `erdos-376--h2` blocked.
2. **Related variant** `Opn.erdos_376_two_primes_3_5 : {n : ℕ | n.centralBinom.Coprime 15}.Infinite := by sorry`
   (PRs #10, #11, #14) and **partial variant** `Opn.erdos_376_two_primes_5_7 : … Coprime 35 …` (#18). Same shape
   as the root; **elaborate (~97%)**. Both are true theorems (EGRS 1975), not yet proved here.
3. **Relation proof** (PR #18, `Relation.lean`): `theorem relation : {n | …Coprime 105}.Infinite → {n | …Coprime
   35}.Infinite := fun h => Set.Infinite.mono (fun n hn => Nat.Coprime.coprime_dvd_right (by norm_num : (35 : ℕ) ∣
   105) hn) h`. **Probably elaborates (~80%).** Depends on `Set.Infinite.mono : s ⊆ t → s.Infinite → t.Infinite`
   (argument order as used), `Nat.Coprime.coprime_dvd_right : n ∣ m → Coprime k m → Coprime k n`, membership in
   `setOf` being accepted by defeq, and `norm_num` closing `35 ∣ 105` (fallback `by decide`). Direction is root →
   variant, which is what `partial` asserts. Axioms: none beyond the allowlist.
4. **Crux L2** `Opn.erdos_376_small_digits_infinite : {n : ℕ | (∀ d ∈ Nat.digits 3 n, d ≤ 1) ∧ (∀ d ∈ Nat.digits 5
   n, d ≤ 2) ∧ (∀ d ∈ Nat.digits 7 n, d ≤ 3)}.Infinite := by sorry` (#12, #15). **Elaborates (~95%).** Witness
   `theorem witness : True := trivial` — matches the root's own witness for a hypothesis-free statement (~90%).
5. **Crux L1** `Opn.erdos_376_kummer_105 : ∀ n : ℕ, n.centralBinom.Coprime 105 ↔ (…)` (#13). **Elaborates
   (~95%).** Witness `True := trivial`: the statement has a `∀` binder but no hypotheses; I do not know whether the
   gate's `opn-witness-type` expects `True` or `∃ n : ℕ, True` here (~70%). Its `Context.lean` (generated) repeats
   the root's statement verbatim, which should compile as a sorry'd declaration.
6. **Probes that should fail the gate, on purpose:** #15 (`witness : True := sorry` — sorryAx), #19
   (`-- relation: resolves` above `import Mathlib`, `theorem relation : True := sorry` — wrong type and sorryAx),
   #20 (`import Nodes.«erdos-376».Context` in a proposal statement — import rule), #9 (a sorry-bearing
   `Proof.lean` declared `partial` — fails kernel replay/axioms as mode `proof`).
7. **Postmortem goal states** (#3): hand-written serialisations of the two skeleton holes, not produced by Lean.

The precheck "pass" verdicts on all of the above are the bench's simulation and say nothing about the Lean.
