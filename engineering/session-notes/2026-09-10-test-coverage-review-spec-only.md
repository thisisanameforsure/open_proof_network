# Test-coverage review of the unbuilt specs — F10, F11, F12

2026-09-10 · documentation only; no code, no spec edits. Reviewed against constitution C2/C7/C8/C9,
conventions §2 ("every gate rejection is a named test", no network in unit tests, markers
`lean`/`docker`/`network`), and decisions D-6, D-8, D-9, D-10, D-13, D-25, D-27, D-30, D-33 as
they stand in v3.12. F09 was not reviewed (another session is mid-build). House style taken from
F08: `FakeToolchain` (scriptable seam, every call recorded, `raise_on=` for C7 tests),
`FakeGitHost`/`FakeClock` in `api/tests/api_fakes.py`, fixture graphs under
`gate/tests/fixtures/graphs/{propositional,adversarial}`, one named test per rejection asserting
the first failing check and a structured diagnostic code, and `xfail(strict=True)` for a known
defect the spec has admitted but not fixed.

Gap classes used below: **(a)** requirement with no criterion · **(b)** happy-path-only where the
requirement implies a rejection, timeout, malformed input, missing artifact, drift, untrusted
content or permission failure · **(c)** rejection paths the decisions imply that the spec does not
test · **(d)** C8/C9 trust-boundary cases · **(e)** determinism properties that deserve a two-run
test. Each gap ends with a proposed test: name · tier · fixture/fake · assertion.

Two spec defects found on the way, which are bugs in the spec rather than gaps in its tests:

1. **F11 uses `F11-AC12` twice** (the licence gate and the network rehearsal). One must be
   renumbered before its test name can be unambiguous.
2. **F11-AC4 and F11-AC5 still say `back-translated`** while F11-R3/R12 rename the rung to
   `screened-and-signed`. The tests will be written to the new name; the criteria should say it.

---

## F10 — Agent funnel

### Requirement → criterion map

| Req | What it asks | Criteria naming it |
|---|---|---|
| R1 | `AGENTS.md` topics in order | AC2 `test_walkthrough.py::test_required_sections` |
| R2 | every fenced command executable; runner fails on failure or output drift | AC1 `test_walkthrough.py::test_agents_md_executes` |
| R3 | `CONTEXT.json` (`context/v1`): typed attempt log ≤500 chars, no transcripts, annex hashes+sizes, demarcation, bot-owned, deterministic | AC3 `test_context.py::test_context_bundle` |
| R4 | `get_node` = `CONTEXT.json` + raw files | AC4 `test_mcp_equivalence.py::test_get_node_uses_context` |
| R5 | image published to GHCR on tag; digest in `gate-spec.json` and used by gate.yml, precheck, reproduce.sh, devcontainer | AC5 `test_pins.py::test_image_digest_consistent` |
| R6 | per-graph `devcontainer.json`, post-create fetches caches, `pregate.sh` works without a build | AC10 (docker) `test_devcontainer_docker.py::test_postcreate_then_pregate` |
| R7 | post-merge builds and uploads oleans keyed by commit; fetch newest at-or-before; fall back on miss | AC7, AC8 `test_cache.py::test_newest_at_or_before`, `::test_miss_falls_back`; AC11 (network) |
| R8 | SHA-256 manifest; failing manifest is discarded and rebuilt | AC6 `test_cache.py::test_manifest_verification` |
| R9 | Docs page carries four human-funnel documents, each naming its decisions | AC9 `test_render.py::test_human_funnel_docs` |
| R10 | cold/warm timings recorded in evidence | AC11 (evidence only) |

Every requirement has at least one criterion. The gaps are in what the criteria leave out.

### Gaps

**F10-G1 (b) — R2's failure half is untested.** AC1 proves the runner passes on a good document;
nothing proves it *fails* when a block fails or its output drifts, which is the entire point of
F10-Q3 ("docs are tests"). A runner that swallows non-zero exits passes AC1.
→ `test_walkthrough.py::test_runner_fails_on_drifted_output` · fast · a one-block `AGENTS.md`
fixture string whose documented output differs from the fake's actual output, and a second whose
command exits 1 · runner reports the block index and exits non-zero in both cases; the diff is in
the diagnostic.

**F10-G2 (d) — the walkthrough runner must be provably offline.** AC1 says "against the fixture
and fakes" but nothing asserts that every HTTP-path block reached `FakeGitHost`/the in-process app
and not the network. A block containing a literal `https://api.openproofnetwork.org` would pass
AC1 on a laptop with network and violate conventions §2.
→ `test_walkthrough.py::test_walkthrough_touches_no_network` · fast · monkeypatch
`socket.create_connection` to raise, run the full walkthrough · passes; and a companion
`test_walkthrough_blocks_carry_no_credentials` asserting no fenced block matches a bearer-token or
`ghp_`/`ssh-ed25519` private-key pattern (C8: nothing secret in a document that will be committed
to the graph).

**F10-G3 (b) — R3's negative clauses need an adversarial node.** AC3 checks schema validity, the
500-char cap and determinism on the ordinary fixture. It does not check the clauses that exist to
keep tokens off the mathematics: *no transcripts*, *newest 50 attempts*, *annex hashes with sizes
(not text)*, *256 KiB cap*.
→ `test_context.py::test_context_bundle_strips_what_it_must` · fast · an adversarial node under
`fixtures/graphs/adversarial` with 60 attempt records, one whose `detail` is 3,000 chars, one
carrying a `transcript:` key, and a 40 KiB annex · bundle has exactly 50 attempts (the newest by
timestamp), `detail` truncated to 500 with a visible marker, no key named `transcript` anywhere in
the JSON, the annex appears only as `{hash, bytes}`, and the annex's prose is not a substring of
the bundle.
→ `test_context.py::test_bundle_over_budget_is_refused_visibly` · fast · same node with a 300 KiB
`Context.lean` · generator raises/returns a diagnostic (`context-too-large`) rather than writing a
partial file (C7).

**F10-G4 (c, D-3) — `CONTEXT.json` is bot-owned, so a contributor diff that touches it must
bounce at the path step.** F10-Q2 states this ("excluded like META.yaml") and nothing tests it.
This is a gate rejection, so by §2 it needs a fixture diff.
→ `test_paths.py::test_contributor_diff_touching_context_json_is_refused` (or wherever the
META.yaml path test lives) · fast · `fixtures/diffs/touches-context-json` · verdict names step 2
first with the existing path-violation code, same shape as the META.yaml test.

**F10-G5 (d, C9) — the claim snapshot copies operational state into the evidentiary repo.** R3
puts a "claim snapshot" into a file the post-merge job commits to the graph. Claims live in the
api's DynamoDB (operational, C9); rendering them into a graph-committed file makes the graph
carry a copy of operational state and makes the post-merge job depend on the api being up.
Two tests pin the safe shape regardless of how Q2 is resolved:
→ `test_context.py::test_snapshot_carries_no_token_material` · fast · a fake claims overlay with
identities and token hashes · bundle's snapshot has holder identity, TTL and expiry only; no field
whose value equals or prefixes any token hash.
→ `test_context.py::test_claims_seam_down_still_writes_bundle` · fast · fake Store raising · the
bundle is written with `claims: null` and a logged warning, never a missing file (C7); and AC3's
determinism still holds with the overlay absent.

**F10-G6 (d, R5 security note) — a tag reference must be refused.** The spec says "a tag is never
trusted" but AC5 only checks the digests are *equal*; four files all pinned to `:latest` would
pass.
→ `test_pins.py::test_tag_reference_is_refused` · fast · a `gate-spec.json` with
`devcontainer_ref: ghcr.io/x/gate:latest` · `pin_image.py --check` exits non-zero naming the file
and the `sha256:` rule; extend AC5 to assert the value matches `^ghcr\.io/.+@sha256:[0-9a-f]{64}$`.
→ `test_pins.py::test_devcontainer_cache_url_matches_gate_spec` · fast · devcontainer.json whose
post-create URL differs from `olean_cache_url` · refused (R6 says the devcontainer fetches "the
caches", which can only mean the ones `gate-spec.json` names).

**F10-G7 (b, R7) — "at or before" has more edges than AC7.** AC7 covers A < B < C. Missing: only a
*later* cache exists (must miss, not use C); the store holds an archive for a commit that is not
an ancestor of B (a branch) — "before" must be by ancestry, not by upload time, or a rebased graph
fetches oleans for files it never had.
→ `test_cache.py::test_only_newer_cache_is_a_miss` · fast · fake ObjectStore with C only · miss,
fall back to build, miss logged.
→ `test_cache.py::test_non_ancestor_cache_is_not_chosen` · fast · fixture git repo with two
branches, caches on the other branch's tip · miss.

**F10-G8 (b, R8) — the manifest test needs the other failure shapes.** AC6 flips one byte in the
archive. Also required before an archive is trusted: manifest absent; manifest lists a file the
archive lacks; archive contains a member outside the extraction root (`../`, absolute path);
archive over the 50 MiB budget.
→ `test_cache.py::test_manifest_missing_is_a_miss`, `::test_manifest_names_missing_member`,
`::test_archive_path_traversal_is_refused`, `::test_archive_over_budget_is_refused` · fast · hand-built
tarballs in the fake ObjectStore · each is discarded with its own diagnostic code, a rebuild
follows, nothing was written under the work directory before verification completed (verify,
then extract — never extract, then verify).

**F10-G9 (c, D-4 step 1 / R7) — a stale olean must not shadow a changed source.** A verified
cache for commit A used at commit B, where B changed `Statement.lean`, is a poisoned-by-accident
cache: the manifest verifies and the olean is wrong. Lake's trace hashes should force a rebuild
of that module; the spec relies on that silently.
→ `test_cache_lean.py::test_changed_source_rebuilds_despite_cache_hit` · lean · propositional
fixture, build and archive at A, edit one node's `Statement.lean`, restore cache, run `pregate.sh`
· the build log reports a rebuild for exactly that module and a hit for the others; the verdict is
the one for the edited statement.

**F10-G10 (e) — cache archive reproducibility.** R7 keys archives by commit; if two builds of the
same commit differ, `check_cache.py` cannot tell a rebuilt archive from a tampered one.
→ `test_cache_lean.py::test_archive_manifest_is_reproducible` · lean · build twice from a clean
work directory · manifests identical (per-file SHA-256s), and archive bytes identical if the tar
writer normalises mtime/uid/order — assert that too, it is what makes the manifest meaningful.

**F10-G11 (b, R9) — the checklist set must track the taxonomy.** AC9 checks four documents exist
and name decisions. R9 says "per defect class (F08-Q4 taxonomy) with a worked example each"; a new
class added to `defect-claim/v1`'s enum without a checklist entry would pass AC9.
→ `site/tests/test_render.py::test_review_checklist_covers_every_defect_class` · fast · read the
enum from `gate/schemas/defect-claim/<latest>.json` · the rendered checklist has a section per
value and each section contains an example block.

**F10-G12 (b, AC4/AC10) — assert the negative in the equivalence and docker criteria.** AC4
("bundle equals the file plus raw files, demarcation included") should also assert that
`get_node` does *not* recompute anything when the file is present — otherwise a drifted
recomputation is a second source of truth (C9). AC10 ("without building the toolchain") should
be asserted on the log or the elapsed time, not eyeballed.
→ `test_mcp_equivalence.py::test_get_node_does_not_regenerate` · fast · `CONTEXT.json` with a
sentinel value no generator would emit · the sentinel is served verbatim; and
`::test_get_node_without_context_json_is_visible` · missing file → structured error, not a
silently regenerated bundle.
→ AC10: assert `elan`/`lake build` of the toolchain does not appear in the post-create log and
the wall-clock is under the 3-minute budget from §6.

---

## F11 — On-ramp graph intake

### Requirement → criterion map

| Req | What it asks | Criteria naming it |
|---|---|---|
| R1 | `target/v1` record shape | none directly (AC3 touches it) |
| R2 | `intake new`: five artifacts, excluded domains, scaffold with Mathlib pin, admission on root and defs, mechanical-only certs, `listed`, curator PR | AC1, AC2, AC3 (`test_intake.py`) |
| R3 | `fidelity/v1` certificates, append-only, count and names, min-over-subjects, non-author for ≥ screened-and-signed | AC4 `test_fidelity.py::test_grade_rules`, AC13 `test_products.py::test_signature_count` |
| R4 | `claimable` = active ∧ grade ≥ screened-and-signed ∧ posting; into products | AC5, AC6 |
| R5 | `intake post`, `intake activate`; activation refuses naming the missing condition | AC5 `test_intake.py::test_activation_requires_posting` |
| R6 | per-graph Mathlib image digest; `cache get` only on miss | AC11 (docker) |
| R7 | on-ramp theorem selection criteria and record | AC8 |
| R8 | seeded through F07 skeleton, holes `skeleton-hole` | AC10 (lean) |
| R9 | `import-fc`: provenance, licence allowlist, denylist, header verbatim, notice file, count config | AC7, AC12(a) |
| R10 | Targets page: reasons, source, attribution, licence, QA summary; no reproduction of none-stated statements | AC9 |
| R12 | `target-status/v2`, `targets-index/v2`, v1 untouched, `PROTOCOL_VERSION` 3.12, goldens | AC13 (partly) |
| R13 | hand-run QA pass recorded per import | none (evidence doc) |
| R11 | readiness rehearsal, both paths | AC12(b) (network) |
| §7 | ledger refuses proof credit to a curator on their own target (D-21) | **none** |

### Gaps

**F11-G1 (c, D-33) — R4 contradicts D-33 and a test written to R4 would enshrine the defect.**
R4: claimable requires `status active`. D-33: on a `dormant` target "every node stays claimable,
no claim is refused… the next merged progress artifact flips the status back to active
mechanically." `known-result` and `resolved` are the statuses that close claiming; `dormant`
is not. Today's `products.py` reads `claimable` straight from the declaration, so nothing enforces
either reading yet. This needs a one-line spec fix (claimable requires status ∈ {active, dormant})
before T2, and then:
→ `test_products.py::test_dormant_target_stays_claimable` · fast · propositional fixture with a
`status: dormant` declaration over a screened-and-signed root with a posting · every ready node
has `claimable: true` and the frontier entry carries `dormant` as a fact (D-25).
→ `test_products.py::test_resolved_and_known_result_are_not_claimable` · fast · same with each
closing status · `claimable: false`, reason names the status.
→ `test_products.py::test_tutorial_root_is_claimable_regardless_of_grade` · fast · D-27's
carve-out, already coded in `target_facts`; pin it before R4's derivation replaces it.

**F11-G2 (a, §7 / D-21) — the curator-credit refusal has no test.** "The ledger writer refuses
proof entries for the curator on their own target" is the only self-dealing guard in the feature
and no criterion names it.
→ `gate/tests/test_ledger.py::test_curator_earns_no_proof_credit_on_own_target` · fast · a
target.yaml naming curator A, a merged proof by A · ledger write refused with a diagnostic naming
D-21; the same proof by B is written; and A's *postmortem* on the same target is still written
(D-21 bars proof credit, not attempts — assert the boundary, not just the refusal).

**F11-G3 (b, R2) — one missing artifact is tested; the other four are not.** AC1 omits
`prior_art` only. §2's rule is a named test per rejection.
→ `test_intake.py::test_each_missing_artifact_is_named` · fast · parametrised over
`library_coverage`, `provenance`, root witness (empty `Witness.lean`), and `attack_routes` present
but malformed · refusal names exactly the missing artifact; an empty `attack_routes: []` is
accepted (D-6: advisory).
→ `test_intake.py::test_root_admission_failure_refuses_intake` · fast · `FakeToolchain(elab=fail)`
on the root, then on one `defs/` file · intake writes nothing under `targets/<id>/`, opens no PR
(`FakeGitHost.calls == []`), diagnostic names the file. The important assertion is the *absence
of partial scaffold* — C7 "never corrupt data", and the evidentiary store must not gain a
half-target.
→ `test_intake.py::test_intake_refuses_existing_target_id` · fast · id already under `targets/` ·
refused; nothing overwritten (C9: nothing in this repo mutates an evidentiary record in place).
→ `test_intake.py::test_mathlib_sha_must_be_a_full_commit` · fast · `mathlib_sha: main` and a
7-char prefix · refused (D-10 v3.12: never a moving branch; D-7 pin).
→ `test_intake.py::test_excluded_domain_among_many` · fast · `tags: [combinatorics, pde]` and
`PDE` in a different case · refused both times, so the check is set-membership over normalised
tags and not a first-element check.
→ `test_intake.py::test_curator_pr_carries_only_the_target_tree` · fast · same materialise-the-
pushed-tree pattern the F08 proposal test uses · pushed paths are all under `targets/<id>/` and
the tree passes the gate's layout check (log 2026-09-10: "test the shape that lands").

**F11-G4 (b/c, R3, D-9) — certificate integrity and counting.**
→ `test_fidelity.py::test_certificates_are_append_only` · fast · rewrite `<subject>-1.yaml` in
place, then delete `-2` leaving `-3` · the grade command refuses/flags the subject (gap in the
sequence, or a hash on file that no longer matches a recorded chain) rather than silently
recomputing.
→ `test_fidelity.py::test_same_attestor_twice_counts_once` · fast · two certificates by B · count
1, names `[B]`. D-9's `expert-attested = author-attested + one independent signature` makes the
count load-bearing; a naïve `len(certs)` is the obvious bug.
→ `test_fidelity.py::test_latest_certificate_wins_including_downgrade` · fast · B raises to
screened-and-signed, then a later certificate at mechanical-only · grade is mechanical-only.
→ `test_fidelity.py::test_author_may_write_mechanical_only` · fast · the other half of AC4: the
non-author rule applies at screened-and-signed and above, so the author's own mechanical-only
certificate is accepted.
→ `test_fidelity.py::test_evidence_limits` · fast · evidence text 2,001 chars; an `evidence
files` entry that does not exist; an unknown grade string · each refused with its own code.
→ `test_fidelity.py::test_v1_records_with_old_rung_still_derive` · fast · a `target-status/v1`
record on disk saying `back-translated` · grade derivation maps it to `screened-and-signed` (or
refuses loudly — either is fine, silent `mechanical-only` is not). The live graph will carry no
such record today, but F03's goldens and any older fixture might.

**F11-G5 (b, R5) — activation names *each* missing condition, and posting is validated.** AC5
tests only "no posting".
→ `test_intake.py::test_activation_names_grade_and_status` · fast · posting present, grade
mechanical-only → refused naming grade; grade fine, already active → refused/no-op naming status.
→ `test_intake.py::test_post_requires_a_url_and_a_known_venue` · fast · `--url not-a-url` and an
unlisted venue · refused; `posting.date` written from `FakeClock`, not the wall clock (determinism).
→ `api/tests/test_curator.py::test_post_and_activate_are_curator_only` · fast · F08's curator
mode: a non-curator token on whichever endpoint fronts these commands → 403.

**F11-G6 (b, R6) — image/pin mismatch and the cache-get fallback.** AC11 proves the hit. Missing:
the image's Mathlib does not match `gate-spec.json` (a re-pin of one without the other); the hit
path makes no network call; the miss path degrades (C7).
→ `test_pins.py::test_image_mathlib_label_matches_gate_spec` · fast · fake image manifest with an
`org.opencontainers.image.revision`-style Mathlib label ≠ the pin · `pin_image.py --check` fails.
→ `test_onramp_docker.py::test_cache_get_runs_only_on_miss` · docker · run with the image, assert
`lake exe cache get` absent from the step-1 log; run with an image lacking the oleans (or the
label cleared) and assert it is present, and that the verdict is still produced (fallback).

**F11-G7 (b, R9) — the import needs its other refusals.** AC7 and AC12(a) cover provenance, a
none-stated licence, the denylist, the header and the notice.
→ `test_intake.py::test_import_fc_path_absent_at_commit` · fast · `--at` a commit where the path
does not exist · refused naming path and commit; no target created.
→ `test_intake.py::test_import_count_cap` · fast · config `stage0_open_targets=5`, sixth import ·
refused naming the cap (the count is a config value; test the default and an override).
→ `test_intake.py::test_import_is_byte_faithful` · fast · assert the copied statement file's
SHA-256 equals the upstream blob's SHA-256 (stronger than "header kept": any normalisation —
line endings, trailing newline — breaks the provenance hash that F12's watcher diffs against).
→ `test_intake.py::test_notice_file_accumulates` · fast · two imports · both attributions present
in the third-party notice, first not overwritten; a third import of the same path is refused as a
duplicate rather than adding a duplicate notice line.
→ `test_intake.py::test_licence_is_matched_as_spdx` · fast · `apache-2.0` (case), `Apache 2.0`
(no hyphen), `GPL-3.0` · first two either normalise or refuse consistently (decide, then pin);
GPL refused.

**F11-G8 (d, R10 / §7) — untrusted upstream text at render.** AC9 checks the none-stated case.
R1 also has `quote_policy ∈ {cite, quote}`; a licensed source whose policy is `cite` must not be
quoted either. The attribution string, prior-art summary and QA summary are contributor/upstream
free text (§7: "capped, untrusted downstream") and go through `untrusted_block`.
→ `site/tests/test_render.py::test_cite_policy_withholds_statement_even_when_licensed` · fast.
→ `site/tests/test_render.py::test_target_free_text_is_demarcated_and_escaped` · fast · target
fixture whose attribution and prior-art summary contain `<script>` and a `](javascript:` link ·
rendered inside the untrusted block, escaped, no live link.

**F11-G9 (b/e, R12) — the schema bump's invariants.**
→ `test_schemas.py::test_v1_schemas_unchanged_by_the_bump` · fast · likely already covered by the
`HASHES` pin test; if so, add the v2 files to `HASHES` in the same commit and assert both.
→ `test_products.py::test_products_emit_v2_and_validate` · fast · golden regenerated; and the
api's copied fixtures equal the golden byte for byte (log 2026-09-09, F05-Q5).
→ `test_info.py::test_protocol_version_is_3_12` · fast · `info.json` golden and the decisions
filename constant in `site/opn_site` and `api/tests` (the log warns both hold it).

**F11-G10 (b, R8 / D-31) — trivial-skeleton rejection on the real graph.** AC10 says "none is
defeq the root" on the *good* skeleton. The §2 rule wants the adversarial twin.
→ `test_onramp_lean.py::test_trivial_skeleton_refused_under_mathlib` · lean · a one-hole skeleton
whose hole is the root up to unfolding a local `defs/` definition · refused at the D-12 offload
check. This is the case a Mathlib-free fixture cannot express (definitional unfolding through
`defs/` is the on-ramp's whole point).

**F11-G11 (a, R13) — the hand-run QA record has no shape test.** Same pattern as AC8 for the
selection record.
→ `test_intake.py::test_open_targets_record_complete` · fast · parse
`engineering/evidence/F11/open-targets.md` · one section per imported target id under
`targets/`, each naming the statement hash it was checked against, the licence, the
back-translation comparison, and the counted attempts with their hashes. Cheap, and it is the
input F12-T4's attempts ledger will be seeded from.

**F11-G12 (network, R11 / AC12(b)) — the rehearsal must assert diffs, not green.** The log's
2026-09-10 lesson (an empty PR passed twice as evidence). `rehearsal.py` should assert: the
submit PR's diff is non-empty and touches only `Proof.lean` under the claimed node; the root's
frontier entry flips from ready to proved after the last merge; the claim is *released* at the
end so the invited run does not start against a held node; and the products commit hash on the
site equals the bot commit.

**Pending F03-AC13 / F05-AC19 (carried by F11-T4).** Both spec texts assert only success:

- F03-AC13: "one bot commit contains the attestation and all four products". `check_products.py`
  should also fail when the commit's author is not the bot, when it touches anything other than
  the attestation and product paths, or when `frontier.json`'s `rendered_from` is not the merge
  commit — otherwise a human commit that happens to carry products passes.
- F05-AC19: "a claim round-trip succeeds". `smoke.py` should assert the claim appears in the
  frontier's claim status *and* is absent from `active` after release, and that a second claim
  on the same node while held returns the conflict code (F05's own AC for that exists in the fast
  tier; the deployed run should touch it once). Without the release assertion the smoke leaves a
  live TTL on the on-ramp node.

---

## F12 — Statement QA, provenance and drift

### Requirement → criterion map

| Req | What it asks | Criteria naming it |
|---|---|---|
| R1 | `qa/v1` record, append-only, exhibits under `qa/exhibits/` | none directly (AC4 reads it) |
| R2 | exhibit vs brief; only exhibits back a grade | AC1 `test_qa.py::test_brief_alone_cannot_raise` |
| R3 | `qa screen`: four attempts in the sandbox under budget, scratch file, exhibit on success, non-zero exit | AC2, AC12 (lean) |
| R4 | positive screen files an *unrouted* defect claim naming both readings | AC2, AC3 |
| R5 | statement version or pin move stales records and re-runs | AC4 (pin only) |
| R6 | `qa brief` | **none** |
| R7 | `qa backtranslate`: source withheld, model recorded, family independence | AC5 |
| R8 | `qa equivalence`: proved pair is an exhibit, failure inconclusive | AC6 (failure only) |
| R9 | fidelity refuses screened-and-signed without a complete pass / with an unrouted positive screen / author | AC1, AC4 |
| R10 | attempts ledger, M counts only current hash, reset on revision | AC7 |
| R11 | drift watcher: revision request with diff, drift flag, claimable false, grade unchanged | AC8, AC13 (network) |
| R12 | resolved-elsewhere: flag for dormancy, notify, never change status | AC9 |
| R13 | `related` variants need a relevance signature | AC10 |
| R14 | products and site: pass state, signers, attempts, drift; escape upstream text | AC11 |
| §7 | token outage degrades the watcher to a warning, never a false all-clear | **none** |

### Gaps

**F12-G1 (c, D-16 vs R4) — the unrouted claim cannot be written with today's schema.**
`gate/schemas/defect-claim/v1.json` requires `class` from a closed enum with no "unset" value,
and D-16 says a claim without a class bounces mechanically. R4 requires the screen to file with
the class unset. So either `defect-claim/v2` adds an `unrouted` state (a D-34 bump, with F08's
bounce rule updated to accept it *only* when the claim carries a kernel-checked exhibit and a
`filed_by: qa-screen` marker), or the finding lives in the QA record and the claim is opened by
the curator on routing. The spec must choose before T2; the test then is:
→ `test_qa.py::test_screen_claim_validates_against_the_schema_it_targets` · fast · the claim the
screen writes is validated with the real schema loader · passes; and
`gate/tests/test_defect_claims.py::test_unrouted_claim_without_exhibit_still_bounces` · a
hand-written claim with class unset and no exhibit → bounced (the carve-out is for the screen's
exhibit, not for everyone).

**F12-G2 (b, R2 / user story "a record I cannot forge by hand") — exhibits are trusted by
path.** AC1 refuses a brief-only record. Nothing stops a curator committing a `kind: exhibit` row
whose exhibit file is absent, hand-edited, or never kernel-checked; the grade gate would count it.
→ `test_qa.py::test_exhibit_must_exist_and_hash_match` · fast · record row citing
`qa/exhibits/x.lean` with a recorded SHA-256; delete the file, then alter one byte · gate refuses
each with its own code; the record row is not counted toward "pass complete".
→ `test_qa_lean.py::test_exhibit_is_replayed_before_it_counts` · lean · an exhibit whose proof is
`sorry` or `native_decide`, committed by hand · the grade gate re-checks the exhibit through the
toolchain seam and refuses (reuse the F08 relation-proof rejections: sorry, axiom outside the
allowlist, no kernel replay). If replay on every `fidelity` call is too slow, the exhibit's
attestation hash from the run must be signed by the post-merge key — then test that an unsigned
exhibit does not count.

**F12-G3 (b/C7, R3) — a screen that times out or explodes must be `inconclusive`, never a
pass.** AC12 asserts "three clean passes" on the on-ramp root; the fast tier has no test for the
budget or for an erroring toolchain. The dangerous defect is a timeout recorded as `pass`
(statement not proved within 60 s ⇒ "clean"), which is exactly what a naïve implementation does.
→ `test_qa.py::test_timeout_is_inconclusive_not_pass` · fast · `FakeToolchain` returning a
timed-out `ElabResult` · row verdict `inconclusive`, exit 0 (no exhibit), the record shows the
budget used; the pass is *not* complete for R9.
→ `test_qa.py::test_erroring_screen_is_inconclusive_and_visible` · fast ·
`FakeToolchain(raise_on="elaborate")` · same, plus a logged error (the F08
`test_an_exploding_check_is_a_verdict` pattern).
→ `test_qa.py::test_subject_budget_marks_remaining_checks_inconclusive` · fast · `FakeClock`
advancing past 5 min after the second attempt · the remaining two rows exist with
`inconclusive` and a `budget-exhausted` note; none is missing (a missing row must not read as
"not yet run" forever).

**F12-G4 (b/c, R3) — the other three screens' success paths, and the scratch-file rule.** AC2
covers `screen-false` only. D-9 layer 2 lists four.
→ `test_qa.py::test_each_screen_success_writes_its_exhibit` · fast · parametrised over
statement / negation / consequence, `FakeToolchain(elab=ok)` for that one attempt · exhibit path
under `qa/exhibits/`, verdict `fail` (a success is a rejection), exit non-zero, one claim.
→ `test_qa.py::test_screen_never_writes_sorry_into_the_graph` · fast · after any run, walk
`targets/<id>/` and assert no file under `nodes/` or `defs/` changed (hash the tree before and
after) and the scratch file lives in the work directory; and the scratch introduces the subject
as `axiom`/hypothesis (assert on the generated text, since that is the D-4 step-2 promise).
→ `test_qa.py::test_declared_consequence_that_does_not_elaborate_is_inconclusive` · fast.
→ `test_qa_docker.py::test_screen_runs_in_the_sandbox` · docker · one real run · the sandbox
seam's call is recorded and the host toolchain seam's is not (§7: "never on the host and never
in the api process"); the log's rule that any check that will run in the sandbox gets one docker
test before it is called done.

**F12-G5 (b, R4) — idempotence and re-routing.**
→ `test_qa.py::test_rerun_does_not_duplicate_an_open_claim` · fast · run screen twice on the
same statement hash · one claim, second run's row cites the existing claim id.
→ `test_qa.py::test_routed_claim_unblocks_only_after_revision_or_refutation` · fast · curator
routes the claim as misformalization → the statement is revised (D-8 `-v2`), the old subject's
record is stale, the new hash has no positive screen; routes it as refutation → the target is
`resolved` and the grade gate is moot. Assert the grade gate on the *old* hash still refuses.

**F12-G6 (b, R5) — statement revision stales too; staleness never deletes.** AC4 moves the pin.
→ `test_qa.py::test_statement_revision_stales_record` · fast · D-8 `-v2` node · old records
flagged stale, still on disk, not counted; and `::test_pin_move_with_no_records_is_a_noop`.

**F12-G7 (a, R6) — the review brief has no criterion at all.** It is layer 3 of D-9's pass and
its untrusted-text rules are the sharpest C9 case in the feature.
→ `test_qa.py::test_brief_lists_every_referenced_constant` · fast · `FakeToolchain.constants`
returning a known set · every constant appears once with a definition text and the structural
signature; recorded `kind: brief`, `model` and `version` filled.
→ `test_qa.py::test_brief_over_200kb_is_truncated_visibly` · fast · a fake definition dump over
budget · truncated with a marker row, verdict still recorded, not silently dropped.
→ `test_qa.py::test_model_outage_is_inconclusive` · fast · fake model client raising / returning
a non-2xx · row `inconclusive`, no brief file claiming success.
→ `test_qa.py::test_brief_never_raises_a_grade` — AC1 covers this; keep.

**F12-G8 (b, R7) — "source withheld" is the assertion, and it is missing.** AC5 tests the
family refusal. The defect that matters is the informal statement leaking into the prompt, which
turns back-translation into paraphrase.
→ `test_qa.py::test_backtranslate_prompt_contains_no_source_text` · fast · fake model client
that records the prompt; target with a distinctive informal statement · no 12-gram of the
informal statement (and none of `target.yaml`'s title/prior-art text) appears in the prompt;
only the Lean does. Also: the model's output is written beside the source in the record, the
`model`/`version` fields are set, and `formalizer: unknown` is written when provenance says
nothing (AC5's second clause — keep).
→ `test_qa.py::test_family_match_is_normalised` · fast · provenance `Claude`, model
`claude-…` in a different case · refused; a different family proceeds.

**F12-G9 (b, R8) — equivalence's happy path and its tautology guard.** AC6 tests one-direction
failure only.
→ `test_qa.py::test_proved_pair_is_an_exhibit` · fast · both implications ok · row
`kind: exhibit`, verdict `pass`, exhibit path set.
→ `test_qa.py::test_equivalence_against_itself_is_refused` · fast · `<a> == <b>` or identical
statement hashes · refused (a proved `P ↔ P` would otherwise be "strong evidence").
→ `test_qa_lean.py::test_equivalence_proof_with_sorry_is_not_an_exhibit` · lean · reuse F08's
relation-proof adversarial files.

**F12-G10 (b, R9) — the unrouted positive screen blocks the raise; the M count gates rung five.**
R9 names "no unrouted positive screen" and neither AC1 nor AC4 tests it.
→ `test_fidelity.py::test_unrouted_positive_screen_blocks_raise` · fast · complete pass with one
`screen-negation: fail` row and an open unrouted claim · refused naming the claim id.
→ `test_fidelity.py::test_stale_or_wrong_hash_record_does_not_count` · fast · a complete pass
recorded against a previous statement hash · refused naming the hash it wants.
→ `test_fidelity.py::test_published_and_uncontested_needs_m_counted_attempts` · fast · config
`M=3`, two counted attempts · refused; three → accepted (if F12 owns the M gate; if not, the spec
should say which feature does — D-9 makes M load-bearing and no spec tests it).

**F12-G11 (b, R10) — attempts ledger integrity.**
→ `test_qa.py::test_attempt_requires_venue_date_url_and_hash` · fast · schema negatives; an
attempt whose hash matches neither the current nor any prior statement hash is refused (a typo
must not silently count for nothing forever).
→ `test_qa.py::test_duplicate_attempt_counts_once` · fast · same venue+url twice · M = 1.
→ `test_qa.py::test_reset_on_revision_keeps_old_rows_visible` — AC7 covers; keep.

**F12-G12 (d/C7, R11 and §7) — the watcher's failure modes are the security note and nothing
tests them.** A watcher that cannot reach upstream and reports "no drift" is the false all-clear
§7 forbids; a watcher that interpolates an upstream path or commit into a `git` command is the
injection §4 forbids.
→ `test_watcher.py::test_upstream_unreachable_is_a_warning_not_all_clear` · fast · `FakeGitHost`
raising / returning 401 · exit non-zero, no drift flag written, no revision request, log warns.
→ `test_watcher.py::test_upstream_path_deleted_or_renamed_is_drift` · fast · path absent at head
· drift set with a diagnostic distinct from an edit; revision request opened.
→ `test_watcher.py::test_second_run_does_not_duplicate_the_request` · fast · run twice with
drift · one revision request; the second run reports "already flagged".
→ `test_watcher.py::test_one_fetch_per_source_repository` · fast · five targets from one
repository · `FakeGitHost` shows one fetch (§6 budget).
→ `test_watcher.py::test_provenance_fields_are_validated_before_use` · fast · provenance with
`commit: "abc; rm -rf /"` and a path containing `..` · refused at the boundary; no seam call made
(commit must be 40 hex, path relative and normalised).
→ `test_watcher.py::test_diff_is_capped_and_never_shelled` · fast · a 5 MB upstream diff · the
revision request carries a capped, demarcated excerpt plus the full-diff hash; no subprocess
receives the diff text.
→ `test_watcher.py::test_drift_leaves_grade_and_status_alone` — AC8 covers grade; add status.
→ `test_watcher.py::test_dry_run_writes_nothing` · fast · `--dry-run` with drift present · no
files under the graph tree change, no `FakeGitHost` write calls.

**F12-G13 (b, R12) — resolved-elsewhere edges.**
→ `test_watcher.py::test_status_source_unreachable_is_a_warning` · fast.
→ `test_watcher.py::test_flip_back_to_open_clears_nothing_by_itself` · fast · flag stays until a
curator acts (D-33: a curator declaration; the watcher "never changes status").
→ `test_watcher.py::test_curator_notification_goes_through_a_seam` · fast · whichever seam
notifies (issue on the network repo? email? the spec does not say) is faked and asserted once.

**F12-G14 (b, R13) — relevance limits.**
→ `test_products.py::test_relevance_text_over_500_is_refused` · fast; and
`::test_partial_and_resolves_need_no_relevance` (the positive half of R13 that AC10 omits, so
the requirement is not enforced on the labels D-30 exempts).

**F12-G15 (d, R14 / AC11) — make the escaping test hostile.** AC11 says "the upstream diff
excerpt is escaped"; a fixture with a plain diff proves nothing.
→ `site/tests/test_render.py::test_qa_summary_escapes_hostile_upstream_text` · fast · diff
excerpt and brief containing `<script>`, `<img onerror>`, a `](javascript:` link, and a
`{{ }}` template token · rendered inside `untrusted_block`, all escaped, no live link; and the
products JSON carries them under the demarcated key the F09 bundle uses, not as bare strings.

**F12-G16 (d, C8) — the provider key.** §7 says the key lives with the other service secrets and
is read via the one config module.
→ `test_config.py::test_model_key_read_only_via_config` · fast · grep-style test (the repo has
the "nothing else reads `os.environ`" rule; extend the existing check to `opn_gate.models`).
→ `test_qa.py::test_record_and_logs_carry_no_key_or_prompt_above_debug` · fast · caplog at
INFO · the key value and the full prompt do not appear; the record has `model` and `version`
only.

**F12-G17 (e) — two-run determinism.** The QA record is evidence the grade rests on, so it
should be reproducible from its inputs.
→ `test_qa.py::test_screen_record_is_reproducible` · fast · same fixture, fake toolchain and
`FakeClock` · the two records differ only in `n` and are byte-identical otherwise (timestamps
from the clock seam); the exhibit files are byte-identical.
→ `test_watcher.py::test_dry_run_is_deterministic` · fast · same fake upstream twice · identical
report.

---

## Cross-cutting

1. **Every command that can fail needs its `inconclusive`/`refused` row tested in the fast
   tier, with the fake seam raising.** F08 established `raise_on=` on `FakeToolchain`; F12's
   screens, brief, back-translation and watcher each need the same one test (G3, G7, G12). The
   dangerous default in all of them is the same: an unproved attempt or an unreachable upstream
   read as "clean".
2. **Two spec-versus-decision conflicts should be settled before the tasks start**, because a
   test written to the spec would enshrine the defect: F11-R4 vs D-33 on dormant claimability
   (F11-G1), and F12-R4 vs `defect-claim/v1`'s required `class` (F12-G1). Both are one-line spec
   fixes plus, for the second, a D-34 schema bump budgeted into F12-T2.
3. **Trust the file, not the path.** Three places take a file's presence as evidence: the cache
   manifest (F10-G8/G9), the QA exhibit (F12-G2), and the copied upstream statement (F11-G7).
   Each needs the hash-mismatch test and, for exhibits, replay.
4. **Untrusted text gets a hostile fixture.** AC11 (F12), AC9 (F11) and AC3/AC4 (F10) all say
   "escaped"/"demarcated" but the fixtures are benign. One shared adversarial prose fixture
   (`<script>`, `javascript:` link, template token, 5 MB length) reused by all three render tests
   would make the word "escaped" mean something.
5. **Second-source-of-truth checks.** F10's `CONTEXT.json` claim snapshot (F10-G5) and
   `get_node`'s regeneration path (F10-G12) are the two places this batch of features is most
   likely to let the api or a bot file quietly diverge from the graph. Assert non-regeneration
   and seam-down behaviour explicitly.
6. **Spec hygiene found on the way:** F11's duplicated `AC12` id; `back-translated` surviving in
   F11-AC4/AC5; F11-R11 listed after R13; F12 nowhere names which feature gates
   `published-and-uncontested`'s M count.
7. **Network-tier scripts must assert diffs and state flips, then clean up** — `rehearsal.py`,
   `check_products.py`, `smoke.py`, `check_cache.py`, `watch_upstream.py --dry-run`. The log's
   lesson of 2026-09-10 (an empty PR passed twice as evidence) applies to every one of them.

Counts: F10 — 12 gaps · F11 — 12 gaps (+ the two carried criteria) · F12 — 17 gaps.
