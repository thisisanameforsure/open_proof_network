# Connectors (F16) and `opn-prove` (F17)

This directory is network configuration, never graph content (D-35), and the gate never reads it
(D-1; `gate/tests/test_harness_blind.py` proves the gate gives identical verdicts under every
declared harness). A connector is a client of the plain protocol: it adds no route, no tool and no
capability (D-28).

| Path | What it is |
|---|---|
| `registry.yaml`, `registry.schema.json` | one entry per coding-agent harness; `opn_gate.clients` loads, validates and renders it |
| `harness/` | the exact harness versions (`package.json`, `package-lock.json` with integrity hashes) and the image they run in |
| `prove/opn_prove.py` | the single-file prover client; the site serves it at `/tools/opn_prove.py` with `/tools/SHA256SUMS` |

## Adding a harness: the checklist (F16-R15)

An entry is accepted on evidence, not on a reading. Every fast-tier test is parametrised over the
registry, so a new entry needs no new test code. It is accepted when all of these hold:

1. **The entry validates.** `uv run pytest gate/tests/test_clients_registry.py` passes: no host in
   a template, no token in one, only the four placeholders, and a snippet for reads without a
   token. Each rule refuses by name.
2. **Its documented examples are beside it.** `gate/tests/fixtures/clients/<id>/` holds a
   `SOURCE.md` saying where and when each example was copied, one file per file-kind snippet
   (named after the snippet's file), and `commands.txt` when it has a command snippet.
   `test_new_entry_is_tested` names any that are missing.
3. **Its snippets have the shape the harness documents.** `gate/tests/test_clients_render.py`
   passes. It checks both ways: nothing rendered that the harness does not document, and every
   `required_keys` rendered.
4. **The tool surface fits its profile.** `uv run pytest api/tests/test_clients_profile.py`
   passes: names, tool count, schema keywords, result size, `readOnlyHint`. Every profile
   limit carries a source URL and the date it was read.
5. **The real binary connects.** Pin it in `harness/package.json` (`npm install
   --package-lock-only` updates the lockfile), then run `make verify-harness` with
   `OPN_HARNESS_BIN` pointing at the installed binaries.
   `uv run python gate/tools/harness_check.py --entry <id>` must report `pass` for each token
   form. What decides is the server's own record of `initialize` and `tools/list`, never the
   harness's exit code. A check the environment cannot attempt reports `not-attempted` with the
   reason, and that is not a pass.
6. **`verified` is set only from that run.** Record version, date and evidence path in the
   entry; that is the only thing that puts a version on the Docs page.

Then regenerate the guide's table and commit it with the entry:

```sh
PYTHONPATH=gate uv run python -m opn_gate.clients --guide gate/agents/AGENTS.md
```

## Moving a harness pin (F16-R11)

`harness-drift.yml` runs level 2 weekly at the pins and at each package's latest release. It goes
red naming the harness and both versions when the latest fails where the pin passes. Move a pin
only in a commit that carries a passing run of the new version.

## `opn-prove`

`prove/opn_prove.py` is one file, standard library only, Python 3.10 or later. Four tests hold it:

- `api/tests/test_prove_export.py`: export is byte-equal to what `POST /check` forwards;
- `api/tests/test_prove_import.py`: an answer corpus, judged by the gate's own step-2 function;
- `api/tests/test_prove_client.py`: the chain against the real service;
- `gate/tests/test_prove_lean.py`: the lean tier.

A new answer shape a prover sends goes into `api/tests/fixtures/prover-answers/` first,
red, labelled with the prover and date, and the fix follows.
