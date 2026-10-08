## Overview

This partial proof reduces its statement, a bound on k for the binomial coefficients C(n, k) with 2k at most n, n below k squared and every prime factor above k, to a statement about remainders alone. The one hole asks for a bound K beyond which, for every such n, some prime p at most k leaves n a smaller remainder than k. Such a prime always divides C(n, k), by Lucas's theorem, so it is a prime factor at most k, and the bound K of the hole serves as the bound of the statement. The proof argues by contradiction: a k above K would carry a prime factor at most k, against the hypothesis that the least prime factor exceeds k.

## The hole {steps: h_sieve}

The hole, which became the node erdos-1094--h3--h1, says: there is K such that for every k greater than K and every n with 2k at most n and n below k squared, some prime p at most k has n mod p less than k mod p. It mentions no binomial coefficient.

## Taking the bound {steps: s2}

The bound K and its property are taken from the hole, and K is offered as the bound of the statement. For a given n and k satisfying the hypotheses, it remains to show k is at most K.

## Supposing k exceeds K {steps: hKk}

Suppose not: then k is greater than K.

## A prime with the small remainder {steps: s4}

The hole then gives a prime p at most k with n mod p less than k mod p.

## The prime divides C(n, k) {steps: hfact hzero hmodeq hdvd}

Lucas's theorem (Mathlib's Choose.choose_modEq_choose_mod_mul_choose_div_nat) says C(n, k) is congruent modulo p to C(n mod p, k mod p) times C(n div p, k div p). Since n mod p is less than k mod p, the first factor is zero, so C(n, k) is congruent to 0 modulo p: p divides C(n, k).

## The contradiction {steps: hle close}

So the least prime factor of C(n, k) is at most p, which is at most k. This contradicts the hypothesis that the least prime factor exceeds k, and the contradiction is closed by omega.
