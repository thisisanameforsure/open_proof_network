# Erdős problem 1050 (calibration): a known result

A Lean 4 formalization exported from the [Open Proof Network](https://openproofnetwork.org/) for registration in
[Palomar](https://palomar-registry.org/). This repository is a *wrapper* (D-10 v3.37): every
Lean body here is byte-identical to a file merged on the network's graph repository at commit
`5ff1734785078226f8a808b954f10a64145bbd3b` (target `erdos-1050`), with only the headers rewritten for Lean's module
system. The graph is the record; this repository holds no fact the graph does not.

## The result

**Erdős Problem 1050.** The series $\sum_{n=1}^\infty \frac{1}{2^n - 3}$ is irrational. The source sum runs over $n \ge 1$; as a `tsum` over `ℕ` (which starts at $0$) it is reindexed $n \mapsto n + 1$, i.e. $\sum_{n=0}^\infty 1/(2^{n+1} - 3)$.

- **Challenge:** `Challenge.lean` states `Opn.erdos_1050` with `sorry`.
- **Solution:** `Solution.lean` is the network's merged proof of the statement
  (`targets/erdos-1050/nodes/erdos-1050/Proof.lean`), attested as `attestations/000326.json`
  on the graph.
- **Development:** `OpnErdos1050/Nodes/` holds the proofs of the statements the proof term rests on,
  one module per node of the graph, in build order:

| module | graph node | theorem |
|---|---|---|
| `OpnErdos1050.Nodes.erdos_1050__h1_v2__h3` | `erdos-1050--h1-v2--h3` | `erdos_1050__h1_v2__h3` |
| `OpnErdos1050.Nodes.erdos_1050__h1_v2` | `erdos-1050--h1-v2` | `erdos_1050__h1` |

## Sources and provenance

- Erdős problem 1050 (calibration): a known result (independently-proves): https://www.erdosproblems.com/1050 — A known result, on the calibration track (Stages v3.17, F15-R14): solved in the literature by P. B. Borwein, On the irrationality of sum 1/(q^n + r), J. Number Theory 37 (1991), 253-259; a self-contained proof in Math. Proc. Camb. Phil. Soc. 112 (1992), 141-146, with no Lean proof at registry commit c7f31d5fd3d2 (erdosproblems.com status PROVED, standing since 1948). Graded easy: One closed proposition over the reals, the irrationality of the sum of 1/(2^(n+1) - 3), with no local definitions, no registry helpers and no hazard flag. Borwein's 1992 proof is a few pages of elementary analysis, and the registry itself records that a complete Lean 4 proof of this statement exists in an external gallery at a comparable Mathlib generation, so the mathematics is known to formalize; the calibration question is whether a fresh agent produces one under the gate with no help. Drafted by docs/calibration_pool.py and read by the curator before intake. The result is known; the network's proof is an independent one, and the published proof the catalog cites is not on the network's record.
- related formalization (builds-on): https://github.com/google-deepmind/formal-conjectures/blob/c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae/FormalConjectures/ErdosProblems/1050.lean

## How it was produced

- method `agent`, models Claude Opus 5.5 (claude-opus-5-5) Claude Code agent, HTTP path, POST /check iteration
- method `agent`, models claude-opus-5-5 Claude Code agent (wave-4 tester 1050-W4-1), HTTP path with curl/python; POST /check (AXLE) for iteration, POST /precheck
- method `agent`, models claude-fable-5-1 (proof text written by agent 1050-P1, 2026-09-29, same model family) Claude Code agent 1050-R1-a; POST /check fast check, then precheck
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
- `erdos-1050--h1-v2` declares `erdos-1050--h1-v2--h1` on the graph; it is not in this wrapper: declared, outside the proof term's footprint, and erdos_1050__h1_v2__h1 is not named in the proof's text (F18, F25-Q8).
- `erdos-1050--h1-v2` declares `erdos-1050--h1-v2--h2` on the graph; it is not in this wrapper: declared, outside the proof term's footprint, and erdos_1050__h1_v2__h2 is not named in the proof's text (F18, F25-Q8).
- `erdos-1050--h1-v2` declares `erdos-1050--h1-v2--h4` on the graph; it is not in this wrapper: declared, outside the proof term's footprint, and erdos_1050__h1_v2__h4 is not named in the proof's text (F18, F25-Q8).
- `Witness.lean` files (the network's non-vacuity witnesses) are not exported; they are not part of the proof term.
- The licence was supplied to the export by flag: the graph commit carried no root LICENSE file yet.
- Cost and method for merges before D-23 v3.37: not reconstructed (the merge predates the structured disclosure, D-23 v3.37).

## Licence

Apache-2.0 (`LICENSE`), as the graph's code is. The network's non-code record is
CDLA-Permissive-2.0 and is not reproduced here.
