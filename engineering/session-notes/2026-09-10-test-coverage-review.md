# 2026-09-10 — test coverage review, failing cases first

An unattended pass over every built feature (F00–F08) and the site, looking for rejection
paths, error branches and boundary cases with no named test. F09 was left alone (in build in
another session). The spec-only features (F10–F12) were reviewed on paper only:
`2026-09-10-test-coverage-review-spec-only.md`.

Fast tier before: 453 passed. After: 917 passed, 17 strict xfails. No production code was
changed; every defect a new test found is held as `xfail(strict=True)` with the defect in its
reason, so the test flips red the day the defect is fixed and must then be un-marked.

## Tests added, by area

| Area | Files | New cases | Defects (xfail) |
|---|---|---|---|
| gate core F00–F02 | test_layout, test_paths, test_pipeline, test_hazards, test_deps, test_witness, test_config, test_schemas, test_attestation, test_signer, test_toolchain; new test_stage, test_sandbox, test_diagnostic, test_cli_pregate | 156 | 3 |
| gate merge/admission F03/F07/F08 | test_products, test_records, test_ledger, test_bounce, test_artifacts, test_postmerge, test_admit, test_curator; new test_scaffold, test_exhibits, `scripted.py` (a per-module scripted `FakeToolchain`) | 99 functions | 5 |
| api F05–F08 | ten new `test_rejections_*.py`, `test_config_boundary.py`, `test_sshsig_rejections.py` | 122 | 0 |
| site F04 | new test_rejection, test_untrusted, test_config; test_dag, test_links extended | 89 | 4 |

## Defects found (code untouched; each has a strict xfail naming it)

Gate core:

1. `gate/opn_gate/diagnostic.py` `_clip_strings` clips every string leaf, including `code`. A
   small `OPN_DIAGNOSTIC_MAX_BYTES` makes `attestation.build` raise `SchemaError` after the
   verdict exists, and no `verdict.json` is written (C7, F00-R18).
2. `gate/opn_gate/cli.py` `run_pregate --sign` with an unusable key: `SignerError` escapes
   `main` (only `CliError`/`CuratorError` are caught), traceback instead of exit 2. Same shape:
   `revise` with a schema-invalid request or an unparseable statement (`SchemaError`,
   `ScaffoldError`) also ends in a traceback.
3. `gate/opn_gate/config.py` accepts any `OPN_LOG_LEVEL`; `logging.basicConfig` fails later,
   against the docstring's "raised at load time, never later".

Gate merge/admission:

4. `gate/opn_gate/graph.py` `witness_is_stub` is `"sorry" in text`; the slot comment
   `postmerge.WITNESS_SLOT` writes contains the word, so a filled witness that keeps the header
   still reads as a stub and the node stays `blocked / witness-missing` (F07-R6, F08-R5).
5. `gate/opn_gate/postmerge.py` `apply_partial` writes the attempt file last; a name collision
   there leaves child directories, parent deps and a regenerated Context behind (C7).
6. `gate/opn_gate/curator.py` `revise` scaffolds before writing the status record; a record
   collision leaves `<node>-v<n>/` on disk while `CuratorError` claims nothing was written.
7. `gate/opn_gate/schemas.py` `load_yaml` catches `OSError` and `YAMLError` only; a non-UTF-8
   attempt file raises `UnicodeDecodeError` out of product generation instead of counting as
   `invalid` (F03-R7).
8. `gate/opn_gate/postmerge.py` `_ANNEX_LINE_RE` matches only 64 lowercase hex; a truncated
   or upper-cased citation reads as no citation, so children silently become
   `compiler-derived` instead of the citation being rejected (F07-R6, D-31). Arguable.

Site:

9. `site/opn_site/model.py` never checks that `graph.json`'s root is one of its nodes;
   `render.py` indexes it and the cli catches only `SiteError`/`ValueError`, so a KeyError
   traceback instead of a named refusal (R13). Same for `nodes: []`.
10. `site/opn_site/model.py` `_attestation_for` reads attestations with no schema validation;
    one lacking `steps` dies with a KeyError in `render.attestation_block`.
11. `site/opn_site/model.py` builds nodes as a dict by id, so duplicate rows in `graph.json`
    render silently from the last one. Low: F03 cannot emit duplicates.
12. `site/opn_site/links.py` checks `href.startswith(repo_url)`, so `.../graph-evil/x`
    passes the "only file links" check. Not reachable from graph content today.

Nits not xfailed: `ledger.write` does `mkdir` before validating, leaving an empty `ledger/`
after a refusal; the ledger's invalid-file message names the violation but not the file.

## Round two (same day): the classifier, the curator commands, the two api seams

A branch-coverage run (`uv run --with pytest-cov`, ephemeral, not a dependency) after round
one read 91% overall; the holes were the classifier's edge diffs, the curator commands through
`cli.main`, and the two api seams that only the live host had ever exercised: `githost.py` at
33% and `store.py` at 61%. After round two: 1126 passed, 33 strict xfails; `githost.py`,
`store.py` and `lambda_handler.py` at 100% branch, `local.py` at 79% (the socket loop).

Gate (test_modes, test_paths, test_cli_curator, test_ledger; 62 cases):

13. **`gate/opn_gate/modes.py` `_classify_curator`** allows every node role, so a listed
    curator's status-record diff that also modifies an existing node's `Witness.lean` (or a
    versioned-node diff plus a foreign witness) classifies `curator` with no problem; the
    witness-completion precondition runs in proposal mode only. F08-R8 lists status records,
    versioned nodes and consolidation records; D-3 makes a witness immutable. **Highest
    priority of the day**: whether admission downstream catches it is not tested either.
14. **`gate/opn_gate/modes.py` `check_witness_completion`** tests the base with
    `"sorry" not in before`; the slot header contains the word, so a witness filled under the
    header reads as unfilled and can be filled a second time. Twin of defect 4.
15. `gate/opn_gate/cli.py` lets `SchemaError`, `ScaffoldError`, `FileNotFoundError` and
    `GraphError` escape `main` from `revise` (bad or missing request, missing or non-statement
    statement), `status` (malformed `--date`, dormant on a cyclic graph), `consolidate` (broken
    gate-spec), and `missing-library` (missing graph or unknown target). Same shape as defect 2.
16. `gate/opn_gate/ledger.py` `write` does `mkdir` before validating (the nit above, now
    xfailed).

Api (test_githost_seam, test_store_seam, test_entrypoints; 147 cases, mock httpx transport and
a scripted boto3 resource using boto3's own serialisers and real `ClientError`s):

17. **`api/opn_api/githost.py`** calls `.json()` on the OAuth exchange and the `/user` body
    before checking the status and unguarded; a non-JSON body (an edge proxy's HTML 502)
    escapes as `JSONDecodeError`, and the callback answers 500 instead of 502.
18. **`api/opn_api/store.py` `take_ephemeral`** catches bare `Exception`: a programming error
    or a throttled table reads as an expired nonce (400 `state-invalid`), never as an outage.
19. `take_ephemeral` returns raw DynamoDB attributes (Decimals) where `get_job` converts via
    `plain()`; harmless today because the one numeric ephemeral field is never read.
20. Seam parity: boto3 refuses `float` at `put_item`, `MemoryStore` accepts it; no record
    carries a float today.

Spec-silent behaviours documented as they are: `status --k 0` makes D-33's attempt threshold
vacuous (no lower bound anywhere); a `--branch` failure leaves the already-written record
untracked on disk; `--author ""` defers to `OPN_PR_AUTHOR`.

## Round three (same day): the sandboxed commands through a scripted docker

The `reproduce`, `gate`, `postmerge`, `exhibits`, `admit`, `ledger` and `products` commands
build the sandbox image unconditionally, so they had only ever run in the docker tier. A
scripted `docker` binary (instant build, flippable `image inspect`, `cp` out emitting a real
tar of the host directory) and a recording sandbox factory drive all of them through
`cli.main` in the fast tier: 71 cases, gate at 99% branch, whole repo 99%; 1192 passed, 40
strict xfails. Also covered: the elan install path and `lake` absence through the real
`_exec` layering, and the `docker cp` tar stream both ways with traversal, symlink and mode
hardening.

21. `gate/opn_gate/cli.py` again, the same shape as defects 2 and 15, now after expensive
    work: a failed `docker build` (`SandboxError`), `reproduce --compare` naming a missing or
    non-JSON file (`SchemaError`, after the run completed and with the verdict on disk
    unreported), `gate --pr-body-file` and `postmerge --approval-body-file` naming a missing
    file (`FileNotFoundError`, after the export, image build and gate run). One `except` clause
    around `commands[args.command]` for the gate's own error types, plus reading flag files
    before doing work, closes 2, 15 and 21 together.
22. `gate/opn_gate/sandbox.py` `_copy_out`: an empty or truncated `docker cp` stream surfaces
    as `tarfile.ReadError`, not `SandboxError`, so the diagnostic names a tar parser. Arguable.

## Round four (same day): the residual branches, and where it ends

40 cases across the classifier's unreadable-record branches, SSHSIG's malformed-blob branches,
bundle path shapes, the store-build failure as a 503, the form-vs-JSON token flows, and three
site lines. No new defects. Final: **1232 passed, 40 strict xfails**, 99% branch coverage
across the three packages. What remains is not fast-tier work: the local dev server's socket
loop, three `__main__` guards, and three branches confirmed unreachable by reading (
`submissions.py` `precheck-node-differs`, `modes.py` line 435 after `_check_schema`,
`paths_step.py` line 37 after `layout.load_node`'s own hash check). Dead branches are a
tidiness question for the owner, not a test.

Eight commits, all tests, no production code:

    a48f85e tests: failing-case coverage for the site (F04)
    8009ebd tests: failing-case coverage for the api (F05-F08)
    e5cd8bd tests: failing-case coverage for the gate (F00-F03, F07, F08)
    e02044b notes: test coverage review, built features and spec-only features
    0dcaff3 tests: classifier edge diffs, curator command errors, ledger refusal (F07, F08)
    95071a5 tests: the GitHub host and DynamoDB store seams driven without network (F05, F06)
    fddacae tests: the sandboxed commands, the install path and docker cp (F00, F03, F07, F08)
    78af006 tests: the residual branches in the classifier, SSHSIG parsing, bundles and the site

## Gaps left open, and why

- **Dead branch**: `api/opn_api/submissions.py` `precheck-node-differs` is unreachable, the
  bundle is path-checked against the submitted node first, so a foreign job always fails as
  `path-forbidden`. Worth a spec note.
- **Spec-silent** in the api: no request body cap beyond the bundle's 512 KiB and the platform's;
  content type is not enforced. Nothing to assert until F05 §6 says.
- **Real host only**: same-second append collisions, a speculative id colliding with an existing
  node (the gate's proposal mode refuses it), `DynamoStore` conflict extraction (needs moto, a C5
  question), `lambda_handler.build()` parameter-store fallback.
- **Lean/docker tier only**: `StatementStep` timeout, `SandboxToolchain._copy_out`, the
  `reproduce`/`gate`/`postmerge` CLI wiring (they build the image unconditionally), a proposal
  whose theorem name clashes with an existing node (no fake can see it), real `leanchecker`
  output shapes.
- **Site**: `--commit` vs products' `rendered_from` mismatch is unchecked and unspecified;
  multiple explainer files render only the first; mid-write disk failure; CSP/404/index
  behaviour is CloudFront's (network tier); `frontier.js` needs a browser (statically it uses
  `textContent` only).
- **Signer** with no `ssh-keygen` binary raises `FileNotFoundError`, not `SignerError`; the log
  records OpenSSH as always present where the gate runs.
