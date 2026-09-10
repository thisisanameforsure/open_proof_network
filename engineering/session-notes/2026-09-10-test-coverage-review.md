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
