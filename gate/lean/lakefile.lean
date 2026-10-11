import Lake
open Lake DSL

/-!
The gate's Lean-side metaprograms (F01-R1): small executables the Python pipeline calls through
the `Toolchain` seam. Lean core only; pinned to the repo's `lean-toolchain` (symlinked here).
Each executable reads a Lean file (or a compiled module), prints exactly one JSON document on
stdout, and exits non-zero with a JSON error document on any failure. Called with
`--nonce stdin` (the gate always does, F02-T11) it reads a nonce from stdin first and prints that
document as the one line `@opn-verdict <nonce> <json>`.
-/

package «opn-gate» where
  -- The metaprograms elaborate contributor files, so they run the interpreter (D-4: only ever
  -- inside the step-3 sandbox or on the contributor's own machine).
  leanOptions := #[⟨`autoImplicit, false⟩]

lean_lib OpnGate where
  roots := #[`OpnGate]

@[default_target]
lean_exe «opn-witness-type» where
  root := `OpnGate.WitnessTypeMain
  supportInterpreter := true

@[default_target]
lean_exe «opn-used-constants» where
  root := `OpnGate.UsedConstantsMain
  supportInterpreter := true

@[default_target]
lean_exe «opn-hazards» where
  root := `OpnGate.HazardsMain
  supportInterpreter := true

@[default_target]
lean_exe «opn-artifact-type» where
  root := `OpnGate.ArtifactTypeMain
  supportInterpreter := true

@[default_target]
lean_exe «opn-relation-type» where
  root := `OpnGate.RelationTypeMain
  supportInterpreter := true

@[default_target]
lean_exe «opn-statement-meaning» where
  root := `OpnGate.StatementMeaningMain
  supportInterpreter := true

-- F19-T1: the outline of a proof artifact (its steps, claims, goals and constants). It elaborates
-- the artifact to keep its info trees, so it runs only in the step-3 sandbox (D-4).
@[default_target]
lean_exe «opn-outline» where
  root := `OpnGate.OutlineMain
  supportInterpreter := true

-- F02-T11: reads compiled modules only, with initializers off; nothing of the module it imports
-- is executed, so it is built without the interpreter's support.
@[default_target]
lean_exe «opn-axioms» where
  root := `OpnGate.AxiomsMain
