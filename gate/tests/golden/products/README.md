# Golden merge products (F03-T4, AC11)

The four products, plus every node's `CONTEXT.json` (F10-R3), generated from the propositional
fixture in three states, byte for byte:

- `unproved/` — the pristine fixture: two ready interior nodes, a blocked root, no declaration.
- `interior-proved/` — merged passing attestations for both interior nodes (one under a
  `native_decide` waiver, `trust_base: compiler`): the root is ready.
- `curated/` — the tutorial node proved; `and-reassoc` speculative by curator record, with two
  postmortems, one invalid attempt file and an annex; a target declaration (claimable,
  back-translated).

Every timestamp and hash is fixed by the test (`rendered_from`, `commit_time`, merge commits), so
a diff here is a real change to a product. Regenerate after an intended change with

    PYTHONPATH=gate uv run python -c "import sys; sys.path.insert(0, 'gate/tests'); import test_products as t; t.write_goldens()"

and review the diff before committing it with the task that caused it.
