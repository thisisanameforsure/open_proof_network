# Port repairs (F25-R12, Q34)

A directory per target, mirroring the exported wrapper's layout. `opn-gate palomar-port --repairs
<dir>` copies each file over the export's before the build and records every replacement in
`port-report.json` (`repairs[]`: path, `sha256_before`, `sha256_after`), so the wrapper's text can
always be told from the export's. The rules, each a refusal before any file is written:

- `Challenge.lean` is frozen through a port (`port-repair-forbidden`); a statement that must
  change is a revision on the graph (D-8), never a port repair.
- A repair may only replace a file the export wrote (`port-repair-unknown`); a port cannot add a
  helper module. Helpers belong in the node's proof on the graph.
- A `<file>.before.sha256` sidecar names the exported file the repair was written against; a
  different export is refused (`port-repair-stale`) rather than silently given an older text.

Repairs are proof bodies only, written by a person or an agent against the registry's toolchain,
and they are evidence of the port, not of the record: the graph's proof is unchanged, and the
attestation it carries is the pinned gate's. `palomar-port.yml` applies
`gate/palomar/repairs/<target>` when the directory exists.

## erdos-1050

Against the Stage A export of graph `5ff1734785078226f8a808b954f10a64145bbd3b` (package
`OpnErdos1050`; `engineering/evidence/F25/task-15-stage-a/`), ported to `leanprover/lean4:v4.35.0-rc2`
with Mathlib `v4.35.0-rc2`. One file, three edits
(`engineering/evidence/F25/task-15-stage-b/repairs-erdos-1050.diff`):

| line | was | is | why |
|---|---|---|---|
| 507 | `Finset.prod_le_one` with two hypotheses | `Finset.prod_le_one₀` | Mathlib 2026-09-01 gave the unprimed name to the ordered-monoid lemma (one hypothesis); the ordered-semiring one is now `₀` |
| 525 | `Finset.prod_le_prod` with two hypotheses | `Finset.prod_le_prod₀` | the same rename |
| 624 | `ring` | `rw [mul_assoc, ← mul_pow, one_div_mul_eq_div]` | `ring` no longer closes `2 * (1/2)^K * x^K = 2 * (x/2)^K` at this Mathlib; the rewrite is the identity it needs |

Twenty-nine deprecation warnings are left as they are: a warning is not a failure, and every
deprecated name is an alias of the one Mathlib now prefers. `lake build` of the whole wrapper
passes locally at this toolchain (`engineering/evidence/F25/task-15-stage-b/repair-loop.md`).
