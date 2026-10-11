# Euclid's theorem

A Lean 4 formalization exported from the [Open Proof Network](https://openproofnetwork.org/) for registration in
[Palomar](https://palomar-registry.org/). This repository is a *wrapper* (D-10 v3.37): every
Lean body here is byte-identical to a file merged on the network's graph repository at commit
`5ff1734785078226f8a808b954f10a64145bbd3b` (target `euclid-primes`), with only the headers rewritten for Lean's module
system. The graph is the record; this repository holds no fact the graph does not.

## The result

For every natural number n there is a prime greater than n.

- **Challenge:** `Challenge.lean` states `Opn.infinitude_of_primes` with `sorry`, with the target's definitions (Defs.Divides, Defs.Fact, Defs.IsPrime) inlined verbatim.
- **Solution:** `Solution.lean` is the network's merged proof of the statement
  (`targets/euclid-primes/nodes/infinitude-of-primes/Proof.lean`), attested as `attestations/000038.json`
  on the graph.
- **Development:** `OpnEuclidPrimes/Nodes/` holds the proofs of the statements the proof term rests on,
  one module per node of the graph, in build order:

| module | graph node | theorem |
|---|---|---|
| `OpnEuclidPrimes.Nodes.infinitude_of_primes__h1` | `infinitude-of-primes--h1` | `infinitude_of_primes__h1` |
| `OpnEuclidPrimes.Nodes.infinitude_of_primes__h2` | `infinitude-of-primes--h2` | `infinitude_of_primes__h2` |
| `OpnEuclidPrimes.Nodes.infinitude_of_primes__h3` | `infinitude-of-primes--h3` | `infinitude_of_primes__h3` |
| `OpnEuclidPrimes.Nodes.infinitude_of_primes__h4` | `infinitude-of-primes--h4` | `infinitude_of_primes__h4` |

## Sources and provenance

- Euclid's theorem (independently-proves) — Classical (Euclid, Elements IX.20; c. 300 BC) and not in dispute. Mathlib proves the same fact as Nat.exists_infinite_primes about Nat.Prime; this target states it over the graph's own Divides, IsPrime and fact (engineering/evidence/F11/selection.md, F11-R7), so the bridge to Mathlib's statement is a lemma, not a citation. Chosen as the Stage 0 on-ramp for zero selection risk (F11-Q1). The result is known; the network's proof is an independent one, and the published proof the catalog cites is not on the network's record.

## How it was produced

- method `other`
- method `other`, models claude-opus-5 claude-code
- Each method is one merged proof's disclosure as its submitter declared it to the Open Proof Network (never verified, D-1); the ledger on the graph at the exported commit is the record. The registering curator (thisisanameforsure) prepared this wrapper with the network's export tool and wrote no Lean.

## What was checked, and where

- At the graph's pin (leanprover/lean4:v4.33.1, Mathlib `0df444a360eaa60ab8c11dca51a86af692955474`): the gate elaborated every
  module, replayed each through the kernel, held the proof to the three standard axioms, and
  checked by the kernel that the proof's theorem has the statement's type. The attestation named
  above is that record.
- The export checked that `Challenge.lean`'s theorem text equals the node's statement text
  (`opn-export.json` carries the hashes of every file in and out).
- At the registry's toolchain, after the port: Comparator and the registry's preflight (see
  `.github/workflows/palomar-preflight.yml`).

## Declared gaps

- Fidelity: The network's fidelity grade of the root statement is `mechanical-only` (D-9); no human has read the formal statement against the informal one on the network's record. Challenge.lean is the graph's Statement.lean with its headers rewritten for the module system; the export checks the theorem text is identical.
- `Witness.lean` files (the network's non-vacuity witnesses) are not exported; they are not part of the proof term.
- The licence was supplied to the export by flag: the graph commit carried no root LICENSE file yet.
- Cost and method for merges before D-23 v3.37: not reconstructed (the merge predates the structured disclosure, D-23 v3.37).

## Licence

Apache-2.0 (`LICENSE`), as the graph's code is. The network's non-code record is
CDLA-Permissive-2.0 and is not reproduced here.
