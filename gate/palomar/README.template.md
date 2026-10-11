# {{TITLE}}

A Lean 4 formalization exported from the [Open Proof Network]({{SITE_URL}}) for registration in
[Palomar](https://palomar-registry.org/). This repository is a *wrapper* (D-10 v3.37): every
Lean body here is byte-identical to a file merged on the network's graph repository at commit
`{{GRAPH_COMMIT}}` (target `{{TARGET_ID}}`), with only the headers rewritten for Lean's module
system. The graph is the record; this repository holds no fact the graph does not.

## The result

{{INFORMAL}}

- **Challenge:** `Challenge.lean` states `{{DECL}}` with `sorry`{{DEFS_SENTENCE}}.
- **Solution:** `Solution.lean` is the network's merged proof of the statement
  (`targets/{{TARGET_ID}}/nodes/{{ROOT}}/Proof.lean`), attested as `attestations/{{ATTESTATION}}.json`
  on the graph.
- **Development:** `{{PACKAGE}}/Nodes/` holds the proofs of the statements the proof term rests on,
  one module per node of the graph, in build order:

{{CLOSURE_TABLE}}

## Sources and provenance

{{SOURCES}}

## How it was produced

{{PRODUCTION}}

## What was checked, and where

- At the graph's pin ({{LEAN_TOOLCHAIN}}, Mathlib `{{MATHLIB_SHA}}`): the gate elaborated every
  module, replayed each through the kernel, held the proof to the three standard axioms, and
  checked by the kernel that the proof's theorem has the statement's type. The attestation named
  above is that record.
- The export checked that `Challenge.lean`'s theorem text equals the node's statement text
  (`opn-export.json` carries the hashes of every file in and out).
- At the registry's toolchain, after the port: Comparator and the registry's preflight (see
  `.github/workflows/palomar-preflight.yml`).

## Declared gaps

{{GAPS}}

## Licence

Apache-2.0 (`LICENSE`), as the graph's code is. The network's non-code record is
CDLA-Permissive-2.0 and is not reproduced here.
