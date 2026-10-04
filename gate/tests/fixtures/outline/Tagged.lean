import Lean

/-! F19-AC4's tag half, without Mathlib: a stand-in for the reader Mathlib's
`Mathlib.Tactic.CrossRefAttribute` provides at the pin (`Lean.Environment.getSortedCrossRefs :
Environment → Array Mathlib.CrossRef.Tag`, read at mathlib4 0df444a3), with the same names and
field names, recording a Stacks tag for `Or.inl` and a Kerodon tag for `Nat.add_zero`. The
outline program reads tags only through that function, so this exercises its path; it says
nothing about Mathlib's own data, which the Mathlib measurement checks (F19-T1). -/

namespace Mathlib.CrossRef

inductive Database where
  | kerodon
  | stacks
  | wikidata

structure Tag where
  declName : Lean.Name
  database : Database
  tag : String
  comment : String

end Mathlib.CrossRef

def Lean.Environment.getSortedCrossRefs (_env : Lean.Environment) : Array Mathlib.CrossRef.Tag :=
  #[⟨`Or.inl, .stacks, "0ABC", ""⟩, ⟨`Nat.add_zero, .kerodon, "01AZ", ""⟩,
    ⟨`Or.inl, .wikidata, "Q1", ""⟩]

theorem OpnOutline.tagged (p q : Prop) (hq : q) (n : Nat) : (q ∨ p) ∧ n + 0 = n := by
  have h : q ∨ p := Or.inl hq
  have e : n + 0 = n := Nat.add_zero n
  exact ⟨h, e⟩
