# 69-R3-curator — admit 69-R2-b's definitions into targets/erdos-69/defs/ (2026-10-01)

Role: build/curator agent for the owner. Owner's decision: "Yes we should allow defs. Unless there is a
compelling reason not to..."

## Result
**Blocked by a rule of the pinned gate; no pull request opened, nothing pushed.** No mode admits a `defs/` file on a
target that already exists. The definitions themselves are ready (they elaborate; the skeleton elaborates over them).

## What was checked
- Fast check, POST /check, target erdos-69, mode check, lean-4.33.1 (exact):
  - Defs.lean alone: okay, log 01M3VXC0S8R3B98WCPV0SYDXDA.
  - Defs.lean + Skeleton.lean (definitions pasted in place of `import Defs.Construction`): okay, only lint
    `sorry-present` (4 holes + 2 restated proved nodes), log 01M3VXC1RGJEG994DS45030Y5Q.
  - Skeleton.lean with `import Defs.Construction`: `400 defs-unknown` (log 01M3VXBR002Y5YSP2FADTEJAAS). Expected:
    api/opn_api/checks.py:356-362 reads `targets/<id>/defs/<stem>.lean` from the committed graph, so the service
    sees a definition the moment it is merged and not before. No service change is needed once it is on main.
- Rehearsal (Log lesson: commit, then classify with the pinned gate). Graph clone, local branch
  `curator/erdos-69-defs`, one commit adding only `targets/erdos-69/defs/Construction.lean` (= Defs.lean, byte for
  byte). Network worktree at erdos-69's pin 3422bb4, `python -m opn_gate.cli classify --graph … --base HEAD~1
  --author thisisanameforsure`: exit 1, mode null,
  `intake-incomplete: an intake adds targets/erdos-69/target.yaml; this one does not (F11-R2)`.

## The rule (same at the pin 3422bb4 and at network HEAD c786835)
- gate/opn_gate/paths.py:373-374: `targets/<id>/defs/<Name>.lean` has role `definition`.
- gate/opn_gate/paths.py:244: `INTAKE_ROLES = (target-record, gate-spec, definition, fidelity)`.
- gate/opn_gate/modes.py:449-464: any diff carrying a `definition` goes to `_classify_intake`, whoever the author.
- gate/opn_gate/modes.py:674-705: an intake has no modification and must add `target.yaml` and `gate-spec.json`.
  On an existing target both exist, so adding them is impossible and modifying them is `mode-mixed`.
- `definition` is not in `MODIFIABLE_ROLES` (paths.py:251-258): a merged defs file can never be edited or deleted.
- The refusal is deliberate and tested: gate/tests/test_modes.py:174-179 and :476-483 ("A definition slipped onto
  an existing target is not a submission (F11-R2)").
- euclid-primes' three defs arrived inside its intake (`opn-gate intake new --defs`, cli.py:414, intake.py:435);
  tutorial/defs holds only `.gitkeep`. No target has ever gained a definition after intake.
- The decisions document does not forbid it: defs are "content-hashed and immutable like statements, versioned via
  D-8, carrying fidelity certificates per D-9"; no prover creates one, a curator adjudicates. A curator adding a
  definition later is inside the protocol; the gate just has no mode for it.

## Answers to the open questions
- `import Mathlib` in a defs file: allowed. defs.py:66-84 accepts library modules and other `Defs.*`;
  layout.py:51 lists Mathlib as library. `noncomputable def`: nothing checks for it; a defs file is asked plain
  elaboration only (cli.py:1798). Elaborates on the pin.
- Naming: `defs/<Identifier>.lean` becomes module `Defs.<Identifier>` (defs.py:31); nodes `import Defs.Construction`.
- Hash-pinned things: none change. The root's statement hash is of its own Statement.lean; gate-spec.json is
  untouched; no existing node imports the new module. Fidelity gains a subject `Construction` (fidelity.py:150-164)
  with no certificate, grade mechanical-only; the target is already mechanical-only (fidelity/root-1.yaml), and
  step 9 reads the root's certificate (modes.py:388), so nothing moves. A certificate `fidelity/Construction-1.yaml`
  cannot ride in the same PR today (it would again be an intake).

## Is there a compelling reason not to admit them?
Not against definitions as such; one real caveat about these particular ones.
- A wrong definition here cannot change what any merged statement means: no merged statement mentions
  `Opn.E69.*`, and the root is stated over Mathlib only. The worst case is that h2-h4 are false or unprovable.
- But defs are immutable and there is **no revision route for a defs file**: revision requests and `opn-gate revise`
  are node-scoped; only a defect claim may name a defs file (`defs/defects/`). The fix for a wrong definition is a
  new file (`Construction2.lean`) and new nodes over it, with the old file and holes left on the record for good.
- This construction is the tester's own, and h4 (decay) is unverified, with a named risk (coincidences beyond depth
  3M). The pattern tables (gDigit, sDigit) are the part most likely to need revising. h1 is proved and the M=2
  cancellation kernel-checked; that is all the evidence there is.
- So: admit, knowing the file may be superseded. Cheap mitigation: have h4a/h4b (exact cancellation) proved over
  pasted definitions before the file is frozen, since they test the tables directly.

## Smallest change that adds the route (spec task; not built)
"Curator adds a definition to an existing target" — a feature task under F11 (curator route; no protocol change):
1. modes.py:456: when the roles are `{definition}` (optionally plus that definition's first `fidelity`
   mechanical-only certificate), every change is an addition, and the target already exists on the base, classify
   as `curator` (author in curators.json, reviewers as usual) instead of `intake`. Name must not exist on base.
2. The gate job elaborates the target's defs on the merged tree in the sandbox (`defs.compile_all`, the same call
   intake's admission uses) and fails the PR on `defs-name` / `defs-import` / `defs-cycle` / `defs-elaboration`.
3. Tests: replace test_modes.py:174-179 and :476-483 (non-curator still refused; curator admitted); one Lean-tier
   test that a node importing the new module builds after the merge.
4. Check the consumers after merge: olean cache rebuild (cache.py:140), products (fidelity row), get_defs MCP read.
5. Re-pin erdos-69 to the commit carrying it, then open the one-file curator PR (the local branch is ready).
Separately, and a protocol change (describe only): a contributor route to *propose* defs (69-R2-b request 2), and
`draft_defs` on POST /check (request 1). Neither is needed for the owner's decision.

## State left behind
- Graph clone: local branch `curator/erdos-69-defs` (1 commit, not pushed); checkout back on main.
- Network repo: this file only, uncommitted.
