# Curator B log (2026-11-25, UTC)

- 13:45Z Read brief, rows (4), registry files, graph-ref layout (abc, selfridge-seq-conjecture,
  center-column-frequency-half), wave.py (theorem_name, opens, witness_for, Hand defs).
- 13:47Z Artin: the two open rows use `S`, `ArtinConstant`, `Set.HasDensity`; no GRH name. The GRH
  conditional forms are separate registry theorems (not these rows). Plan: port S/ArtinConstant,
  GRH.trivialZeros (so `open GRH` resolves), DataSetDensity + 4 deps copied from the live graph port.
- 13:50Z Subprime: Local port of subprimePart/step/EventuallyPeriodic; witness x = y = 1.
- 13:51Z Selfridge: defs copied from live selfridge-seq-conjecture (same file, same commit); witness p = 3.
- 13:52Z check #1 subprime (POST /check): HTTP 200, errors [] -> compiles.
- 13:53Z check #2 selfridge: HTTP 200, errors [] -> compiles.
- 13:53Z check #3 artin parts.i: 1 error, `Decidable χ.Odd` in GRH.trivialZeros. Ported
  FormalConjecturesForMathlib/NumberTheory/DirichletCharacter/Basic.lean whole.
- 13:53Z check #4 artin parts.i: errors [] -> compiles. check #5 artin parts.ii: errors [] -> compiles.
- 13:54Z check #6 negative control (parts.ii witness with b = 2): error on the witness line, as expected.
- 13:56Z Fixed Statement.lean headers of Artin and Selfridge (copyright block was cut one line short,
  missing `-/`; the check inlines bodies only, so it could not see it). Re-inlined: check inputs
  byte-identical; `opn_gate.layout.parse_statement` parses all four Statement.lean.
- 13:55Z CURATION.md written for all four. Decisions: all four import as stated. Six /check calls used.
