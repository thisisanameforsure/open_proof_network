/-! Non-vacuity witness (D-4 step 7): the trivial group (torsion-free, every element of finite order is 1) and the zero module, which is finite and projective. -/

theorem witness : ∃ (G : Type u_1) (inst : Group G) (M : Type u_2) (inst_1 : AddCommGroup M) (inst_2 :
  _root_.Module (MonoidAlgebra ℤ G) M),
  (∀ (g : G), IsOfFinOrder g → g = (1 : G)) ∧
    Module.Finite (MonoidAlgebra ℤ G) M ∧ Module.Projective (MonoidAlgebra ℤ G) M :=
  ⟨PUnit, inferInstance, PUnit, inferInstance, inferInstance, fun _ _ => Subsingleton.elim _ _,
   inferInstance, Module.Projective.of_free⟩
