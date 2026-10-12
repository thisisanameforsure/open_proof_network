# erdos-1050 port on the runner with the repairs applied — run 38128885529 (palomar-port.yml, 2026-10-11, ubuntu-24.04)

Commit 357388f1 on f25-palomar; graph export at origin/main (see export.json); toolchain leanprover/lean4:v4.35.0-rc2, Mathlib v4.35.0-rc2.

## Verdict

port ok: True; failures: []

repairs applied (port-report.json `repairs`):

```json
[
  {
    "path": "OpnErdos1050/Nodes/erdos_1050__h1_v2.lean",
    "sha256_before": "a64d9b895c4142cf7c6d39ac8ec837444a112050c1808f9cbb945cb41521bed8",
    "sha256_after": "d8400a8f6d74bead48a4cd6aa2248006479e9834b1efb17cc9f8a442cf794754"
  }
]
```

steps and exits: update=0, cache=0, build=0, comparator=0

modules built (name, wall time) as lake printed them:

- Challenge (3.0s)
- OpnErdos1050.Nodes.erdos_1050__h1_v2__h3 (16s)
- OpnErdos1050.Nodes.erdos_1050__h1_v2 (18s) — the repaired module, elaborated in this run (the Comparator's build also reprints its 29 deprecation warnings)
- OpnErdos1050 (2.5s)
- Solution (3.1s)
- OpnErdos1050.Nodes.erdos_1050__h1_v2 (18s)
- OpnErdos1050 (2.5s)
- Solution (3.1s)

## Comparator (`lake comparator --config .opn-port/comparator.generated.json`, con-ron + nanoda + Lean kernel)

```
Exporting #[Quot, Quot.mk, Quot.lift, Quot.ind, Opn.erdos_1050, propext, Classical.choice, Quot.sound, Nat.add, Nat.sub, Nat.mul, Nat.pow, Nat.gcd, Nat.div, Nat.mod, Nat.beq, Nat.ble, Nat.land, Nat.lor, Nat.xor, Nat.shiftLeft, Nat.shiftRight, String.ofList, Char.ofNat, List, eagerReduce, Nat, String, String.mk, Char, optParam, autoParam, semiOutParam, outParam] from Solution
con-ron: accepted 21548 declarations (--verified)
con-ron kernel accepts the solution
nanoda kernel accepts the solution
Lean default kernel accepts the solution
Your solution is okay!
```

Challenge.lean was frozen through the port (`port-challenge-changed` would have refused): opn-export.json's hash of it is the one the Comparator read.

Step timing from the job: export 3 s, port (update + cache + build + comparator) 3 min 24 s; the whole job 5 min 26 s.

Files here: export.json (Stage A's record), opn-export.json (the wrapper's own record), port.json (port-report.json as printed).
Not a submission: nothing was pushed to any repository and nothing registered (F25-J3).
