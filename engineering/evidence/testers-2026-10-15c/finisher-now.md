# finisher-now log

- 15:14Z witnesses proposed with token t1015c-a10 (written by t1015c-a27; credit in a Lean comment, propose_witness has no notes field); all three nodes were blocked/witness-missing just before:
  - erdos-1094--h3--h2--h1: PR #555, proposal 01M501W2K8PDNMSCR9F13PT2EE, witness_preflight matched
  - erdos-1094--h3--h2--h2: PR #556, proposal 01M501ZF00GR7PQTWQV6F8K0SR, matched
  - erdos-1094--h3--h2--h3: PR #557, proposal 01M501ZNTRGM2S8VGCQV3ZVNAB, matched
- 15:14Z a05 partial re-checked via check_lean: header-diverges gone; only lint sorry-present (expected for a partial), Lean errors none.
- 15:14Z a05 partial on erdos-1094--h2--h1--h1--h1 with token t1015c-a06 (author t1015c-a05, credited in automation.tool_setup and tooling.harness): node was ready; claim 01M5022WC099ANCWND94H41PHD (expires 16:14Z)
  - bundle path targets/erdos-1094/nodes/erdos-1094--h2--h1--h1--h1/attempts/<ts>-t1015c-a06-partial.lean, a05/partial.lean unchanged
  - precheck job 01M5022XB8781QA5N1P2P4MTVG (graph 7a4aeb08): done, verdict pass (15:19:03Z)
  - submit_proof: PR #558, submission 01M502BHQ07AV5MRXPBXJZGC47; holes h_low -> erdos-1094--h2--h1--h1--h1--h1, h_high -> --h2 (both expected_new, expected_witness True)
- Next: once #555-#558 merge, the two new holes from #558 need `theorem witness : True := trivial` via propose_witness.
