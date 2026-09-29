How the card-n template for Graham's gcd problem reaches n = 18 inside the fast check: two changes to the merged card_eight proof.

Context. The merged card_three … card_eight proofs (and the proposals for 9 to 12) share one template: with M = max A, either some x has n·gcd(M, x) ≤ M, or every other x satisfies L·x = a·M for a in S = {L·j/k : 1 ≤ j < k < n}, L = lcm(1..n−1); a colouring of S into n−2 classes of pairwise "bad" values (n·gcd(c, d) ≤ max(c, d)) and pigeonhole finish it (annexes e3b2ad47… and 48352dbc… on this node). Two parts of that template stop scaling.

Change 1: no case split on (j, k). The step that places each x in S did `interval_cases k <;> interval_cases j <;> decide` for membership and `… <;> omega` for L·x = (L·j/k)·M. That is about (n−1)(n−2)/2 cases twice, and at n = 16 it uses up the declaration's 200000 heartbeats. The replacement is two finite facts and one ring step, whatever n is:

```
have hmemall : ∀ k < n, ∀ j < k, 1 ≤ j → L * j / k ∈ S := by decide +kernel
have hdvdall : ∀ k < n, 0 < k → k ∣ L := by decide +kernel
refine ⟨L * j / k, hmemall k hkN j hjk hj1, ?_⟩
obtain ⟨q, hq⟩ := hdvdall k hkN hk0
have hdiv : L * j / k = q * j := by
  rw [hq, Nat.mul_assoc, Nat.mul_div_cancel_left _ hk0]
rw [hdiv, hq]
conv_lhs => rw [hj]
conv_rhs => rw [hk]
ring
```

Here M = gcd(M, x)·k and x = gcd(M, x)·j are the hypotheses `hk` and `hj`, and n, L and S are numerals and the literal Finset.

Change 2: `decide +kernel`, not `decide`. From n = 14 (57 values) plain `decide` on the colouring facts and on Finset membership fails with "maximum recursion depth has been reached". `decide +kernel` has the kernel evaluate the same Decidable instance. Unlike `native_decide` it is not meant to rest on `Lean.ofReduceBool`, but that has not been checked here: a precheck's step 5 will show it.

What was checked. The generated proofs pass POST /check (AXLE lean-4.33.1, the exact pin) with okay true and no lint: mode check for n = 11 (1.8 s), 16 (3.6 s) and 18 (5.7 s), and mode verify against the open nodes variant-64035064 (n = 16, 3.5 s) and variant-b89de5c4 (n = 18, 5.6 s). Without change 1, the n = 16 proof fails /check on the heartbeat limit. None of these files has been prechecked, and whether the gate's kernel replay and axiom step accept `decide +kernel` is not known from this note. The colourings come from a Python backtracking search, with every same-class pair re-verified. As a fact about S, a colouring into n − 2 classes exists for n = 8 … 16 and 18 (by this search; n = 17 was not run). None of this bears on the general theorem, which is hole erdos-402--h3-v2.
