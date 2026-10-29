# F32 T0–T3 build log

- 2026-10-29T06:19Z — started; read spec, constitution, conventions, decisions v3.49
- 2026-10-29T06:31:50Z — T0 implemented (v8, HASHES, role, 3.49, goldens); fast tier running on snapshot /f32/snap-t0
- 2026-10-29T06:37:57Z — T1 green (41 tests incl. error-codes); baseline fast tier on HEAD: 1 failed (protocol version, expected), 7092 passed. Starting T2 tests.
- 2026-10-29T20:59:20Z — resumed (new agent). T1 separated and committed 8513e06b (tree = snap-t1). Next: WIP-commit T2, rebase onto origin/main.
- 2026-10-29T21:00:42Z — rebased onto origin/main f922b726 cleanly (no conflicts; main did not touch our gate files beyond codes/modes rows); make types exit 0; T2 fast tests 57 passed. Lean tier for T2 started.
- 2026-10-29T21:09:11Z — T2 lean tier: 3 refusal tests pass; the pass test failed at step 7 on the TEST's witness for 'second' (⟨0, rfl⟩ for expected ∃ (n : Nat), True, probed with the real toolchain). Test fixed; rerunning.
