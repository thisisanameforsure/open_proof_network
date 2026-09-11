# Statement review checklist

Implements D-15 (statement review: separate, adversarial, credited per confirmed defect),
D-16 (the defect taxonomy) and D-11 (the canary classes that calibrate it). Companion
walkthroughs: filing a defect claim and requesting a revision.

## Why a statement gets its own review

A proof is checked by the kernel; a statement is not. Aletheia's audit of two hundred
"solutions" to problems listed as open found 68.5 per cent incorrect and 6.5 per cent correct
as intended, and the failures were overwhelmingly in what was stated, not in how it was proved
(D-15). A defect that escapes into a root or a shared definition poisons every node under it,
so the network overpays for false alarms rather than chilling tentative true ones (D-16): claims
are free, shaped, and typed.

You are never the prover of the node you review, and on standard nodes review is open, like
ordinary code review (D-15). The mechanical checkers run first: step 6's hazard checkers and
step 7's non-vacuity witness (D-4). What reaches you is the semantic residue those cannot see.

## How to read a statement

1. Read `Statement.lean` and every definition it uses from `defs/`; read `Context.lean` for the
   declared dependencies. Nothing else on the node is evidence about the statement.
2. Read the informal statement the target's intake attached (D-6) and ask, for each hypothesis
   and each conclusion, whether the Lean says the same thing.
3. Try to make the statement true for a stupid reason, then false for a stupid reason. Each
   class below is one way that succeeds.
4. When a check fails, write the smallest Lean file that exhibits it. A claim needs a class, a
   line and an exhibit that elaborates (D-16); a kernel-checkable exhibit is what makes a
   confirmed defect confirmable.

## The classes, one check each

### missing-hypothesis

The statement omits a condition the informal claim assumes, so it is false as stated.

Check: for each variable, ask what the informal statement assumed about it and whether the
Lean says so. Look for `n ≠ 0`, `0 < ε`, non-emptiness, finiteness, injectivity.

Example. Informal: "for a prime p, if p divides a·b then p divides a or p divides b."

```
theorem prime_dvd_mul (p a b : ℕ) (h : p ∣ a * b) : p ∣ a ∨ p ∣ b := by
  sorry
```

`p` is never required to be prime; `p = 4, a = 2, b = 2` refutes it. Exhibit: a counterexample
term for the statement as written, or the added hypothesis `(hp : p.Prime)` beside a note that
the original elaborates without it.

### junk-value

A total function returns a value outside the informal domain, and the statement is about that
value rather than the intended one.

Check: division, subtraction on `ℕ`, `Real.sqrt` of a negative, `List.head!`, `Fin` arithmetic,
integer truncation. Step 6's checkers name most of these (D-4); the residue is a definition in
`defs/` that hides one.

Example.

```
theorem half_of_odd (n : ℕ) (h : n % 2 = 1) : 2 * (n / 2) = n - 1 := by
  sorry
```

True, but only because `/` on `ℕ` floors. If the informal claim was about rationals, the
statement proves the wrong thing. Exhibit: `example : (3 : ℕ) / 2 = 1 := rfl` with the line of
the `/`.

### vacuity

The hypotheses cannot all hold, so the statement is provable and says nothing.

Check: is there a witness satisfying every hypothesis at once? The gate demands one in
`Witness.lean` (D-4 step 7), so the residue is a witness that satisfies the hypotheses only at a
degenerate point (an empty set, `n = 0`) that the informal statement excludes.

Example.

```
theorem bound (s : Finset ℕ) (h₁ : s.card = 0) (h₂ : ∀ x ∈ s, x > 5) : s.sum id ≥ 6 := by
  sorry
```

`h₁` forces `s = ∅`, so the conclusion is `0 ≥ 6` and the theorem is false; with `≤` it would be
vacuously true. Either way the hypotheses do not describe the informal object. Exhibit: a proof
that the hypotheses imply `s = ∅`.

### quantifier-scope

A quantifier is in the wrong place, so the statement is stronger or weaker than intended.

Check: every `∀`/`∃` alternation against the informal wording; "for every ε there is an N"
versus "there is an N for every ε"; a bound variable that should be free.

Example. Informal: "the sequence converges to L."

```
theorem converges (a : ℕ → ℝ) (L : ℝ) : ∃ N, ∀ ε > 0, ∀ n ≥ N, |a n - L| < ε := by
  sorry
```

The `∃ N` outside the `∀ ε` says the sequence is eventually constant at `L`. Exhibit: a
sequence that converges but is never constant, with the line of the `∃`.

### wrong-domain

The objects live in the wrong type: `ℕ` where the claim is about `ℤ`, `ℝ` where it is about
`ℚ`, a `Finset` where a `Set` was meant, a function where a partial function was meant.

Check: each binder's type against the informal statement's objects, and whether coercions
(`↑`) appear where none was intended.

Example.

```
theorem no_root (x : ℕ) : x * x ≠ 2 := by
  sorry
```

True and trivial over `ℕ`; the informal claim (irrationality of √2) is about `ℚ`. Exhibit: the
intended statement over `ℚ` beside the line of `x : ℕ`.

### definition-mismatch

A definition in `defs/` or Mathlib does not mean what the informal statement means by the word.

Check: unfold every non-Mathlib definition; for a Mathlib one, read its docstring and one
lemma about it. Common cases: `Nat.Prime 1` is false, `Set.Finite` versus `Finset`,
`Real.log` at zero, a `defs/` definition that encodes a special case.

Example.

```
def IsSquareFree (n : ℕ) : Prop := ∀ p, p ∣ n → ¬ (p * p ∣ n)
```

With `p = 1` this is `¬ (1 ∣ n)`, false for every `n`: nothing is square-free under this
definition and every theorem assuming it is vacuous. Exhibit: `example : ¬ IsSquareFree 6`.

### strength-drift

A revision or a translation weakened or strengthened the claim relative to the certified
informal statement (D-9's named residual).

Check: compare against the informal statement the fidelity certificate names, not against
the previous Lean version; a hypothesis added "to make it provable" is drift.

Example. The informal target says "for all sufficiently large n"; the certified statement and
the revision read:

```
theorem bound_eventually (f : ℕ → ℕ) : ∃ N, ∀ n ≥ N, f n ≤ n * n := by   -- certified
  sorry
theorem bound_from_two   (f : ℕ → ℕ) : ∀ n ≥ 2, f n ≤ n * n := by         -- the revision
  sorry
```

The revision is strictly stronger; provable or not, it is not the certified claim. Exhibit:
the two statements side by side, with the line of the bound.

### other-with-exhibit

Anything not above, on the condition that the exhibit is kernel-checkable (D-16). A claim
without an exhibit in this class bounces.

## After a finding

- A defect in a node's statement or a shared definition: file a defect claim (the
  defect-claim walkthrough). A confirmed claim earns the review line on the ledger (D-19);
  an unconfirmed one draws down a rolling budget, and never blocks you (D-16).
- A statement that should be replaced: file a revision request (the revision-request
  walkthrough); a curator versions the node (D-8).
- A statement that is merely too strong to prove is not a defect: propose a weaker variant
  under D-30 instead.
