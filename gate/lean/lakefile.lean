import Lake
open Lake DSL

/-!
The gate's Lean-side metaprograms (F01-R1): small executables the Python pipeline calls through
the `Toolchain` seam. Lean core only; pinned to the repo's `lean-toolchain` (symlinked here).
Each executable reads a Lean file, prints exactly one JSON document on stdout, and exits non-zero
with a JSON error document on any failure.
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
