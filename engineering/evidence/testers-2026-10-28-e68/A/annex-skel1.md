Informal argument: a factorial-multiplier skeleton for Erdős problem 68.

Let S = sum_{n >= 2} 1/(n! - 1). This is the argument that proves e irrational, written so that the one step it cannot do for S is isolated as a single finite statement.

Step h1 (criterion, elementary). If x = p/q with q >= 1, then N!·x = (N!/q)·p is an integer for every N >= q. So if for every M there is N >= M with N!·x not an integer, x is irrational.

Step h2 (tail split, elementary). For N >= 2 write N!·S = F_N + c_N, where F_N = sum_{n=2}^{N} N!/(n! - 1) is a finite sum of rationals and c_N = N!·sum_{n>N} 1/(n! - 1). Every term is positive, so c_N > 0; and since n! - 1 >= n!/2 for n >= 2, c_N <= 2·sum_{n>N} N!/n! <= 2·sum_{j>=1} (N+1)^{-j} = 2/N.

Step h3 (the open core). For every M there is N >= M with frac(F_N) < 1 - 2/N.

Assembly. Given N >= max(M, 2) from h3, N!·S = floor(F_N) + (frac(F_N) + c_N) with 0 < frac(F_N) + c_N < 1, so N!·S is not an integer; h1 then gives that S is irrational.

Why h3 is the whole difficulty, and why it is narrower than the root. If S = p/q then frac(F_N) = 1 - c_N for every N >= max(q, 2), so h3 asks only that the fractional part of the finite sum F_N leaves the window [1 - 2/N, 1) infinitely often. h3 is strictly stronger than the irrationality of S (irrationality only excludes the single point 1 - c_N), and it contains no limit: for each N it is a statement about one rational number. Writing N!/(n! - 1) = P + P/(n! - 1) with P = (n+1)(n+2)···N, frac(F_N) = frac( sum_{n=2}^{N} r_n/(n! - 1) ) with r_n = P mod (n! - 1); so h3 is a statement about the residues of the products (n+1)···N modulo n! - 1. If those fractional parts behaved like independent uniform numbers, the window would be met with probability about 2/N for each N, so h3 is expected to hold; no proof of anything of this kind is known.

What is not a route. The criterion "L_N·tail_N -> 0", with L_N = lcm(n! - 1 : 2 <= n <= N), is false: gcd((N-1)! - 1, N! - 1) divides N - 1, so L_N >= (N! - 1)((N-1)! - 1)/(N - 1), which outgrows 1/tail_N ~ (N+1)!. The same criterion with the reduced denominator of the partial sum in place of L_N would need cancellation on a scale nothing suggests.
