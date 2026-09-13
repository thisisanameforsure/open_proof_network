Informal argument for OpnProp.and_left_of_and_swap (∀ p q : Prop, p ∧ q → p).

Two steps. (1) A conjunction commutes: from a proof of p ∧ q we obtain a proof of q ∧ p by exchanging its two components. (2) The right component of a conjunction is a projection: from q ∧ p we read off p. Assembling the two, every proof of p ∧ q yields a proof of p.

Step (1) is exactly the tutorial node OpnProp.and_swap; step (2) is And.right. Neither step is needed for the direct proof (And.left closes the goal in one move); the decomposition exists so that each step is a named lemma whose body can be filled independently.
