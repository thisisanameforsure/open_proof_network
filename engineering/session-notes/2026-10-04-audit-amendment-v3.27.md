# Proposed decisions amendment v3.27: audit of 2026-10-04

**Status (2026-10-04): sections 1–3 approved by the owner and applied as decisions v3.27 (commit f2a1b77); section 4 not approved, not applied. The two questions in sections 4 and 5 remain open.**

Source: the re-audit of 2026-10-04 against the four principles (published state is actual state;
fully trackable; easily reversed; hard to tamper with). The owner's rulings of the same day:
- step 9's reviewer rule stays;
- no new contributor-facing rule on what a `Proof.lean` may contain;
- the internal judging fixes are in;
- pre-flights fail closed on a spent check budget;
- everything else is in scope.

Each item names the tasks that wait on it.

## 1. D-4 steps 3 and 4: what the verdict is read from (F08-T28, F02-T10, F02-T11)

v3.25 asks step 4 to compare what was proved with the statement only "where a use is declared by
the artifact or by a proof it is built on".

The 2026-10-04 audit found that a dependency's merged proof module carries whatever its file holds
after the proof body. Step 4 imports the dependency's proof module in place of its signature. So a
dependent with no use line is exposed in the same way, and the comparison has to run for it too.

The audit also found that build outputs and verdict lines can be written by the code being judged.

> **v3.27: what a verdict rests on.** Elaborating a contributor's file runs their code, so nothing
> that code could have written is evidence. Step 4 builds the contributor's modules, then judges
> them in a separate run that executes none of their code:
> - the kernel replays the compiled modules;
> - the type of the declaration they hold is compared with the statement as its own admitted
>   files read it.
>
> This holds for every artifact that claims a statement (a proof, an alternate, a partial
> proof's assembly), whatever uses it declares. A metaprogram's verdict is read only as that
> program printed it.

Overturning condition: a faster check that gives the same guarantee, shown on the real toolchain.

Cost to record: on a Mathlib target the comparison adds about two imports of Mathlib to step 4,
against the 600 s cap. It is measured in the F08-T28 evidence before the re-pin.

## 2. D-14 and D-18: a curator may withdraw a record (F08-T31, F08-T32)

Today a status record or a defect claim can be removed only by a direct push, because every mode
refuses a deletion. Two consequences:
- `disputed` has no exit, the trap `stale` had before v3.18.
- Six circularity claims filed under the pre-v3.23 direction keep four nodes off the frontier
  (F08-Q33).

> **v3.27: withdrawal.** A listed curator may withdraw a status record or a defect claim by an
> append-only withdrawal record that names it and gives a reason, reviewed like any curator record
> (F08-R8). The withdrawn file stays in the tree, and every reader of the record reads it as
> absent. A `disputed` status lifts when its record, or the claim it rests on, is withdrawn. A
> dispute that is upheld ends in D-8's revision, as before. Nothing is deleted.

Overturning condition: a withdrawal used to hide a sound claim, seen on the record.

## 3. D-19 and D-18: correcting credit (F07-T66)

The live ledger credits the owner with two attempts that another contributor made (PRs #68, #69),
and has no file for the contributor PR #71 names. `ledger/` is not a path any mode accepts, and
nothing writes the `revoked` status `ledger/v1` defines.

> **v3.27: credit corrections.** A listed curator may correct a ledger line by a correction record
> naming the merge, the line, the identity credited and the identity that should be (or none), and
> a reason. The post-merge job applies it by marking the old entry `revoked` and writing the
> corrected one. An entry is never deleted, and applying a correction twice changes nothing.

## 4. D-16: every defect claim reaches the products (F08-T33)

Only circularity claims affect any product today, so a `wrong-domain` claim on the record changes
nothing a reader sees.

> **v3.27: claims are shown.** The graph product lists every defect claim against a node, with its
> class and state.

**Question for the owner:** should an accepted ground (i) or (ii) claim *derive* `disputed`
("accepted for adjudication", as D-18 reads), or only be shown?

## 5. D-33: a closed root is not open work (F03-T14)

The index publishes `claimable: true` for:
- the tutorial target, whose root is proved, so the target is `resolved`;
- a target whose root is refuted, defective or abandoned.

`claimable: false` with a reason follows from D-12 and D-33 as written, and needs no amendment.

**Question for the owner:** should a refuted root make the target `resolved`? Today only `proved`
does.

## 6. D-35: the record's own workflow fails closed (F07-T61, built now)

A pull request that touches nothing under `targets/` currently passes both required checks
unexamined. The network pin that judges a pull request is also read from that pull request's own
tree.

Both are workflow facts, not protocol, and are built now:
- such a pull request is refused unless a curator listed on the base opened it;
- the pin is read from the base.

No amendment is needed. D-35's "a tooling change reaches a graph only as a visible diff made by the
gate's named owner" is what this enforces.
