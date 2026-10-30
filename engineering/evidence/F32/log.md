# F32 T0–T3 build log

- 2026-10-29T06:19Z — started; read spec, constitution, conventions, decisions v3.49
- 2026-10-29T06:31:50Z — T0 implemented (v8, HASHES, role, 3.49, goldens); fast tier running on snapshot /f32/snap-t0
- 2026-10-29T06:37:57Z — T1 green (41 tests incl. error-codes); baseline fast tier on HEAD: 1 failed (protocol version, expected), 7092 passed. Starting T2 tests.
- 2026-10-29T20:59:20Z — resumed (new agent). T1 separated and committed 8513e06b (tree = snap-t1). Next: WIP-commit T2, rebase onto origin/main.
- 2026-10-29T21:00:42Z — rebased onto origin/main f922b726 cleanly (no conflicts; main did not touch our gate files beyond codes/modes rows); make types exit 0; T2 fast tests 57 passed. Lean tier for T2 started.
- 2026-10-29T21:09:11Z — T2 lean tier: 3 refusal tests pass; the pass test failed at step 7 on the TEST's witness for 'second' (⟨0, rfl⟩ for expected ∃ (n : Nat), True, probed with the real toolchain). Test fixed; rerunning.
- 2026-10-29T21:15:03Z — T2 committed 34f1d13c (amended WIP); fast tier for it running on snapshot snap-t2. T3: seam at today's behaviour applied (CheckedProof, hole_attestation_path, proofs= ignored); red run next.
- 2026-10-29T21:17:46Z — T3 green (9 passed, 141 neighbours), lint/types exit 0; waiting on T2 fast tier before committing T3.
- 2026-10-29T21:36:43Z — T3 committed 59d5ddfa; fast tier on snap-t2 and snap-t3: 1 failed (pre-existing test_graph_copy_is_identical: main's AGENTS.md ahead of the graph copy), 7207/7216 passed. T1–T3 done; T4 next (not this session).
- 2026-10-30T06:24Z — T5 (other agent): graph f32-t5-gate 76e5e2172e signs hole records in the key step; network test_finding_carried_proof_workflow.py red 2/6 then green 6/6; fast tier 7223 passed.
- 2026-10-30T06:10:58Z — T6 (new agent): red found graph/v15's proofs[].attestation pattern refusing Q7's hole file name (every product down on the first born-proved merge); graph/v16 added; Q13 seam then fix (rendered commit for carried_by records); cache needs gate.yml (T5), outline does not. lint/types exit 0; fast tier next.
- 2026-10-30T06:32:03Z — T6 fast tier: 7226 passed, 1 xfailed (T5 mark), exit 0. Committing.
- 2026-10-30T06:03Z — T7 started (new agent, worktree opn-f32-t7); red: 10 failed / 2 passed (task-7-red.txt)
- 2026-10-30T06:28Z — T7 green: 12 new fast tests, fast tier 7229 passed / 0 failed; docker test written, pending CI
