## Overview

Fix a positive k. The proof shows that every n in the set, that is every n at least k squared for which the least prime factor of C(n, k) exceeds n/k (rounded down), is less than k! + k; a set of natural numbers below a fixed bound is finite. The idea is to look at m = k times (n/k rounded down), the largest multiple of k not above n. Every prime factor of m is at most n/k, so none divides C(n, k), and m is coprime to C(n, k). But m is one of the k numbers n, n − 1, …, n − k + 1 whose product is k! times C(n, k), so m divides k!. Hence m is at most k!, and since m is more than n − k, n is less than k! + k.

## The hypotheses {steps: s1}

Take n in the set: n is at least k squared and the least prime factor of C(n, k) is greater than n/k (rounded down).

## Sizes of n/k and m {steps: hkt htpos hm_le hm_gt}

Because n is at least k squared, n/k (rounded down) is at least k, so it is positive. The multiple m = k·(n/k) is at most n and more than n − k: it is the multiple of k in the window n − k + 1, …, n.

## No small prime divides C(n, k) {steps: hnd}

A prime p at most n/k cannot divide C(n, k): if it did, the least prime factor of C(n, k) would be at most p, hence at most n/k, against the hypothesis.

## m is coprime to C(n, k) {steps: hcop}

A prime dividing m divides k or divides n/k. In the first case it is at most k, which is at most n/k; in the second it is at most n/k. Either way, by the previous step it does not divide C(n, k), so m and C(n, k) share no prime factor.

## m divides k! times C(n, k) {steps: hm_dvd}

The product n(n − 1)…(n − k + 1), Mathlib's descending factorial, equals k! times C(n, k). Since m lies in the window, m = n − j for some j less than k, so m is one of the factors of that product and divides it.

## The bound {steps: hm_fact hle close}

Being coprime to C(n, k), m divides k!, so m is at most k!. With m more than n − k this gives n less than k! + k, closed by omega.
