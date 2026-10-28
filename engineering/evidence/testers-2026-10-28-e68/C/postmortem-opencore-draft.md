Draft (to be filed on A's open-core node once it exists; node id TBD, route_class direct-estimate, outcome exhausted, failure_class route-dead-ends):

route: "second angle on the open core: look for a narrower statement inside fract(F_N) < 1 - 2/N"
detail:
 1. Recurrence. With x_N = fract(F_N), F_N = sum_{n=2}^N N!/(n!-1): F_{N+1} = (N+1)F_N + 1 + 1/((N+1)!-1),
    so x_{N+1} = fract((N+1)x_N + 1/((N+1)!-1)). One x_N determines all later ones: the hole is a
    statement about the factorial-base digits of S, not about any finite set of N.
 2. If the hole failed from N0 on, then ||N! S|| <= 2/N for all N >= N0, i.e. the factorial digits
    d_{N+1} of S would eventually lie within 2 of 0 or of N. Equivalent restatement, not narrower.
 3. Small n contribute nothing eventually: n! and n!-1 are coprime and both divide N! once N >= n!-1,
    so N!/(n!-1) is an integer. All of x_N comes from the n <= N for which n!-1 has a prime-power
    factor not dividing N!, i.e. from the residues (N!/n!) mod (n!-1). Nothing is known about their
    distribution (it is tied to the prime factors of n!-1 > n, where even "n!-1 prime infinitely
    often" is open), so no named theorem gives a sub-hole.
 4. The lcm route is refuted (approach record): L_N * tail_N -> infinity.
Conclusion: no narrower honest sub-skeleton found; the hole is the open core as stated.
