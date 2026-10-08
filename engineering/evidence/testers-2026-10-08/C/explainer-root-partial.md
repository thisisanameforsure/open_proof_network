## Overview

This is a partial proof of the root: it proves the root from three statements left as holes, one for each way an exception can arise. An exception is a pair (n, k) with k positive, n at least 2k, and least prime factor of C(n, k) above max(n/k, k), where n/k is rounded down. The proof splits the exceptions at n = k squared. Above that line the bound max(n/k, k) is n/k; below it the bound is k. It then shows that only finitely many values of k can carry an exception, and that each such k carries finitely many n, so the set of exceptions is finite.

The set of exceptions is shown to lie inside the union, over k from 1 to max(KA, KB), of the pairs (n, k) with n in that finite set. A finite union of finite sets is finite, so the set of exceptions is finite. To place a given exception, the proof splits on whether n is at least k squared.

## The three holes {steps: hall}

The step proves the conjunction of three statements, each left as a hole that became its own node. The first (erdos-1094--h1) says that for each fixed positive k only finitely many n at least k squared have least prime factor of C(n, k) above n/k. The second (erdos-1094--h2) says there is one bound K such that every pair with n at least k squared and least prime factor above n/k has k at most K. The third (erdos-1094--h3) says there is one bound K such that every pair with 2k at most n, n below k squared and least prime factor above k has k at most K.

## Unpacking {steps: s2}

The conjunction is taken apart into the fixed-k finiteness, the bound KA with its property from the second hole, and the bound KB with its property from the third.

## Finitely many n for each small k {steps: hT}

For each k from 1 to the larger of KA and KB, the values of n that can occur are covered by two sets: the n below k squared, which are finitely many, and the n at least k squared with least prime factor above n/k, which are finitely many by the first hole. Their union is finite.

## When n is at least k squared {steps: s4}

Then k is at most n/k (rounded down), so max(n/k, k) equals n/k and the least prime factor of C(n, k) exceeds n/k. The second hole bounds k by KA, hence by max(KA, KB), and n falls in the second of the two sets for this k.

## When n is below k squared {steps: s5}

Then n/k (rounded down) is at most k, so max(n/k, k) equals k and the least prime factor of C(n, k) exceeds k. The third hole, which uses the hypothesis that n is at least 2k, bounds k by KB, hence by max(KA, KB), and n falls in the first of the two sets.
