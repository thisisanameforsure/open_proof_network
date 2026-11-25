# new_mersenne_conjecture.variants.prime — variant of live target `new-mersenne-conjecture`

**Decision: D-30 variant of the live root node `new-mersenne-conjecture` (target
`new-mersenne-conjecture`), label `resolves`.** Not a new target.

Row: `fc:FormalConjectures/Wikipedia/Mersenne.lean#new_mersenne_conjecture.variants.prime`
(registry pin d8d031d4998c78575159ccab9a7a9e95ce043883, `research open`).

## Facts
- Parent `new_mersenne_conjecture` (all odd p) is `research open` upstream and live as
  `new-mersenne-conjecture` (root `Opn.new_mersenne_conjecture (p : ℕ) (hp : Odd p)`).
- The variant restricts to odd primes. The two are equivalent: the root implies the variant
  trivially, and the registry's own proved lemma `new_mersenne_conjecture_of_prime` derives the
  root from the variant. I chose the stronger label `resolves` (`<variant's type> → <root's type>`),
  so a proof of this variant reads as a proof of the root. If the lead prefers `partial`, the
  relation is `fun h p hp _ => h p hp`-shaped and trivial.

## Files (`variant/`)
- `Statement.lean`: root's header/imports, `open Mersenne`,
  `theorem Opn.new_mersenne_conjecture_prime (p : ℕ) (hp : p.Prime) (h : Odd p) :
  NewMersenneConjectureStatement p` — the registry's binders and type byte for byte.
- `Witness.lean`: `∃ (p : ℕ), Nat.Prime p ∧ Odd p := ⟨3, Nat.prime_three, by decide⟩`.
- `Relation.lean`: `relation : (∀ p, p.Prime → Odd p → NMCS p) → ∀ p, Odd p → NMCS p`, the proof
  copied from the registry's `new_mersenne_conjecture_of_prime` (Apache-2.0, attributed in the
  file's doc comment). Send `relation: "resolves"`.
- No `hazards.yaml`: no findings. `deps: []`.

## Differences from the registry text
- Theorem name `Opn.new_mersenne_conjecture_prime`; module doc line. Proposition unchanged.
- The root's Statement.lean has `open Mersenne` twice (driver artefact); the variant has it once.

## Checks
- Compile (autoImplicit off, live `targets/new-mersenne-conjecture/defs/Local.lean` inlined,
  statement + witness + relation, the relation's `grind` proof included): `POST /check` log
  `01M89G3CJ0C6RTE2CYGDMV9KRR`, errors `[]`, only the statement's `sorry` warning.
- Hazards on the real statement with `target_id: new-mersenne-conjecture`
  (`01M89FQ308TC9SSY70EH4G138Q`): `ran`, findings `[]`.
- Witness type not pre-flighted on the real statement (would cost a call); by
  `OpnGate/WitnessType.lean` the expected type is `∃ p, Nat.Prime p ∧ Odd p` (both binders are
  hypotheses nothing later depends on), and the identical shape was confirmed live for Kurepa's
  `(p) (h_p : 2 < p) : p.Prime → …` (log `01M89FSH48Y1JWSM3HGKEJSFRQ`, `matches: true`).

Sources: the registry file; graph-ref `targets/new-mersenne-conjecture/`; AGENTS.md §Proposals.
