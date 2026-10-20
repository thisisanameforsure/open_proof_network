# finisher-chain — closing-proof chain on erdos-1094--h2--h2--h2

Helper of the lead. Black-box MCP client (150 s timeout, retries); driver `step.py` per step:
wait for dependency nodes to read `proved` (get_node `context.status`), claim, precheck
(artifact_type proof), poll get_precheck every 60 s, submit_proof on pass. Credit to the authoring
pseudonym goes in `automation.tool_setup` and `tooling.harness` (submit_proof has no notes field).

Started 15:11Z. Gates at start: #550 (…--h3--h1--h1--h1--h1) OPEN, #553 (…--h2) OPEN.

- Step 0: #550 MERGED 16:17:39Z (delayed by the F28-Q10 re-pin at 15:45Z; branch re-gated).
- Step 1 (--h2--h2--h2--h3--h1--h1--h1, a04 proof, token t1015c-a04): dep proved seen 16:28:40Z; claim
  01M500MNVGN2KJJ7WFAN65WJM5 (existing); precheck 01M506E0GR1NK21M683P5SSD7S PASS 16:40:00Z (~9 min);
  submitted 16:40:07Z as submission 01M506YPPGF3E89FKG8X3QC76R, graph PR #560. Proof unchanged.
- #553 (--h2--h2--h2--h2, a13) MERGED 16:48:12Z.
  #560 MERGED 17:41:16Z.
- Step 2 (--h2--h2--h2--h3--h1--h1, a07 proof, token t1015c-a07): dep proved seen 17:51:18Z; new claim
  01M50B19D8BCG2VQ320BX5NXA3 (expires 18:51Z); precheck 01M50B1BBRNH7MZE1P32BES5S1 **FAIL 17:59:25Z**,
  first_failing_step 8, code `context-signature-mismatch` (graph_commit 49bbfab, network 067497e):
  "Context.lean's signature for dep '…--h3--h1--h1--h1' differs from its Statement.lean; Context.lean
  is not a submission path (D-3), so this is a graph defect". context_hash dc69f9c4…, statement_hash
  c3019a13…. Steps 1, 2, 4, 5, 6, 7 pass: the proof itself replays.
  Diagnosis: `nodes/…--h3--h1--h1/Context.lean` (last written by #534's bot commit e9ff2ed, 06:47Z,
  before the F28-Q10 re-pin) and `nodes/…--h3--h1--h1--h1/Statement.lean` have **byte-identical theorem
  text**. The only diffs are the Statement's own-Context import line and the Context's
  "Declared dependencies" comment. Step 1's pair (…--h1^3 Context vs …--h1^4 Statement) differs in
  exactly the same way and passed step 8. The visible difference is that step 2's dep has a dependency
  of its own (its own Context is non-empty), while step 1's dep is a leaf. Hypothesis, not verified against
  the gate source (black box): the gate's signature hash for a dep folds in what its own-Context import
  brings, so any dep that has deps mismatches the parent's restatement. Steps 3, 4, 5 and 6 are the same
  shape (each dep or lemma has its own deps), so they would hit this too.
  No Lean fix is possible (Context.lean is not a submission path), so I did not retry or edit the proof.
  Downstream drivers s3 to s6 stopped at 18:01Z. Precheck JSON is in finisher-chain/.
- To resume after a fix (re-render or gate change): `python3 step.py s2 … ` from scratchpad/fin with the
  same args (see the driver usage line), then s3 to s6 as before. Every driver waits on its dep's `proved` status.
