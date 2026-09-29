import Mathlib
import Nodes.«variant-3a1bcb9a».Context

/-! A related variant of Erdős problem 69 (D-30, relation `related`): the root's digits `ω(n)`
written in the factorial base instead of base 2, `∑ ω(n)/n!`, give an irrational number.

Why it sits beside erdos-69: it keeps the root's own digits, `ω(n)`, and changes only the
weights, `2^{-n}` to `1/n!`. Method, the one for `e`: `2ω(n) ≤ n` (since `2^{ω(n)} ≤ n`), so
if the sum were `a/q`, then for `N = q + 2` the number `N!·(sum)` minus the integer
`∑_{n ≤ N} ω(n)·N!/n!` is `N!·(tail)`, which is positive (`ω(N+1) ≥ 1`) and at most
`(1/2)·∑_i (N+1)^{-i} = (N+1)/(2N) < 1`. The same bound fails for base 2, where the digits
`ω(n)` are unbounded against a fixed ratio: that is why the root is hard and this is not. -/

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_factorial_base :
    Irrational (∑' n : ℕ, (ω n : ℝ) / n.factorial) := by
  sorry
