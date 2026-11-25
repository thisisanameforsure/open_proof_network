# kurepa_conjecture.variants.prime — own target (parent not live)

**Decision: import as its own target, stated as the registry states it, titled as a variant of
Kurepa's conjecture.** The lead may prefer to import the parent `kurepa_conjecture` first and
attach this as a `resolves` variant of it (see below).

Row: `fc:FormalConjectures/Paper/Kurepa.lean#kurepa_conjecture.variants.prime`
(registry pin d8d031d4998c78575159ccab9a7a9e95ce043883, `research open`).

## Facts
- Parent `kurepa_conjecture (n) (h_n : 2 < n) : (!n : ℕ) % n ≠ 0` is **`research open`
  upstream and simply not imported**: the catalog's only row for Paper/Kurepa.lean is this
  variant, so the driver never drafted the parent. There is no `kurepa*` target in graph-ref.
- The registry proves the two equivalent (`kurepa_conjecture.prime_reduction`, `textbook`, with a
  full proof in the file). So this target is Kurepa's conjecture in substance. If the parent is
  imported, this row belongs under it as a `resolves` variant (relation proof: the registry's
  `prime_reduction`, right-to-left), and should not also be a target.

## Proposed record
- title: `Kurepa's conjecture for primes (a variant of Kurepa's conjecture)`
- informal: `For every prime p > 2, the left factorial !p = 0! + 1! + ⋯ + (p−1)! is not
  divisible by p. This is the registry's restriction of Kurepa's conjecture (for all n > 2,
  !n ≢ 0 mod n) to primes, which the registry proves equivalent to the full conjecture.`
- source: formal-conjectures, `FormalConjectures/Paper/Kurepa.lean`, Apache-2.0; Guy, Unsolved
  Problems in Number Theory, B44; Kurepa (1971).

## Files
- `defs/Local.lean`: the file's `def left_factorial` byte for byte, inside `namespace Kurepa` with
  the file's `open BigOperators Nat Finset`; header kept; module syntax stripped. The file's
  `local notation "!" n => left_factorial n` is ported as plain `notation` — exactly the driver's
  rule for a file-local notation (wave.py `port_body`, F14-T23; precedent: live
  `algebraic-independent-e-pi/defs/Local.lean`, `notation "e" => exp 1`).
- `Statement.lean`: `import Mathlib`, `import Defs.Local`, the file's `open BigOperators Nat
  Finset`, `open Kurepa`, and `theorem Opn.kurepa_conjecture_prime (p : ℕ) (h_p : 2 < p) :
  p.Prime → (!p : ℕ) % p ≠ 0` — the registry's binders and type byte for byte (notation kept).
- `Witness.lean`: `∃ (p : ℕ), 2 < p ∧ Nat.Prime p := ⟨3, by norm_num, Nat.prime_three⟩`.
- `hazards.yaml`: `off-by-one-range` at `2 < p` (location confirmed); `div-zero` on the modulo —
  **the location string is a guess** (`(!p) % p`): the probe could only print it with
  `left_factorial` unfolded. Copy the exact location from step 6's output at intake.

## Differences from the registry text
- Theorem name `Opn.kurepa_conjecture_prime`; module doc. `local notation` → `notation` in the
  port (above). Proposition unchanged.

## Checks
- Compile: defs + statement + witness + a sanity check `(!3 : ℕ) = 4 := by decide` and
  `(!3 : ℕ) = Kurepa.left_factorial 3 := rfl` (so `!` is the left factorial, not Bool `!`):
  `POST /check` (autoImplicit off) log `01M89G3DH8B90N74C4TCET6WK0`, errors `[]`.
- Witness type: `POST /check` mode `witness` on a probe statement of the same binders with
  `left_factorial` unfolded (`01M89FSH48Y1JWSM3HGKEJSFRQ`): expected
  `∃ (p : ℕ), (2 : ℕ) < p ∧ Nat.Prime p`, `matches: true`.
- Hazards on the same probe (`01M89FSK2R32AS1FFQESA3PDBT`): `off-by-one-range 2 < p`,
  `div-zero (∑ m ∈ Finset.range p, m.factorial) % p`.

Sources: the registry file; wave.py `port_body`/`draft_row`; OEIS A003422 (the file's reference).
