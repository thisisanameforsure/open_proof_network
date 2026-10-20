import json

TOOLING = ("Claude Opus 5.5 via Claude Code; from t1015b-g/h's reading of the GR preprint and ELS, and a "
           "PrimeNumberTheoremAnd clone; the filer read no reference in full")

GR = {"title": "A. Granville and O. Ramaré, Explicit bounds on exponential sums and the scarcity of squarefree "
               "binomial coefficients, Mathematika 43 (1996) 73-107",
      "url": "https://dms.umontreal.ca/~andrew/PDF/ramare.pdf"}
ELS = {"title": "P. Erdős, C. B. Lacampagne and J. L. Selfridge, Estimates of the least prime factor of a binomial "
                "coefficient, Math. Comp. 61 (1993) 215-224",
       "url": "https://web.archive.org/web/2020id_/https://www.ams.org/mcom/1993-61-203/S0025-5718-1993-1199990-6/S0025-5718-1993-1199990-6.pdf"}
INGHAM = {"title": "A. E. Ingham, On the difference between consecutive primes, Quart. J. Math. Oxford 8 (1937) 255-266",
          "url": None,
          "note": "Cited by ELS for the count of primes in (x, x + x^(3/4)) (and x^(7/8)); not read. Primes in "
                  "intervals that short are not in Mathlib; a translation would need Ingham's zero-density "
                  "argument or a later short-interval theorem."}

RECORDS = [
    {"node_id": "erdos-1094--h3--h3--h1--h1", "status": "known",
     "references": [
         {"title": "J. Hadamard (1896) and C. de la Vallée Poussin (1896), the prime number theorem", "url": None,
          "note": "The classical theorem; this node is theta(x) ~ x in the epsilon form."},
         {"title": "PrimeNumberTheoremAnd (Kontorovich, Tao et al.), Lean 4 formalisation",
          "url": "https://github.com/AlexKontorovich/PrimeNumberTheoremAnd",
          "note": "PrimeNumberTheoremAnd/Consequences.lean: theorem chebyshev_asymptotic : θ ~[atTop] id, over "
                  "Mathlib's Chebyshev.theta, from WeakPNT (Wiener.lean). Read at commit of 2026-09-30, Lean "
                  "v4.34.0 (the network pins 4.33.1). Wiener.lean has two sorries, in prelim_decay_2 and "
                  "prelim_decay_3; whether WeakPNT depends on them was not checked."},
     ],
     "summary": "This is the prime number theorem for Chebyshev's theta, a classical theorem not in the pinned "
                "Mathlib (Mathlib has only Chebyshev-type bounds a factor of 2 apart). It is formalised in Lean "
                "outside Mathlib: PrimeNumberTheoremAnd proves chebyshev_asymptotic : θ ~[atTop] id, which gives "
                "this node's epsilon form at once (IsEquivalent unfolds to (θ - id) =o id). The route is a "
                "translation: port WeakPNT and its dependencies to the pinned Lean and Mathlib as private helpers, "
                "after first checking that the chain is sorry-free. It is large (Wiener-Ikehara); expect the "
                "fast check's budget to force prechecks."},
    {"node_id": "erdos-1094--h3--h3--h2--h1", "status": "known",
     "references": [
         dict(GR, note="Lemma 5.1 (preprint p. 18) with J = 1, and the partial-summation consequence (5.1), "
                       "applied in the proof of Theorem 8 (section 5e, pp. 24-25). GR quote it from Sander."),
         {"title": "J. W. Sander, Prime power divisors of binomial coefficients, J. Reine Angew. Math. 430 "
                   "(1992) 1-20", "url": None,
          "note": "The source of the equidistribution bound for {x/p} over primes p <= y that GR cite as [Sa2]; "
                  "proved by exponential sums over primes (Vaughan's identity). Not read."},
     ],
     "summary": "This node is GR's Lemma 5.1 at J = 1, weighted by log p, on primes in (k/2, 11k/20): the "
                "fractional parts n/p are equidistributed mod 1 to within delta*k once n >= k^2/(C log k). "
                "Published (Sander 1992, quoted by Granville-Ramaré 1996) and not formalised anywhere known to "
                "the filer. A translation would follow Sander: Vaughan's identity, bounds for exponential sums "
                "e(hx/p) over primes, then Erdős-Turán (or a direct count). It also needs the prime number "
                "theorem in the window, which is erdos-1094--h3--h3--h1--h1. Deep: the hardest node in the "
                "h3 subtree. The node uses x = n where GR use n - k; the bound is uniform in x."},
    {"node_id": "erdos-1094--h3--h2--h1", "status": "known",
     "references": [
         {"title": "E. F. Ecklund, P. Erdős and J. L. Selfridge, A new function associated with the prime "
                   "factors of (n choose k), Math. Comp. 28 (1974) 647-649", "url": None,
          "note": "Proves g(k) > k^(1+c) for an absolute c > 0, where g(k) is the least n > k+1 with every "
                  "prime factor of C(n,k) above k. Not read; the statement is as ELS 1993 and an earlier annex "
                  "on erdos-1094--h3 quote it."},
         dict(ELS, note="Cites EES 1974 for the range n <= k^(1+c) in the proof of its Theorem 1 (p. 216)."),
     ],
     "summary": "This node is the Ecklund-Erdős-Selfridge bound: if 2k <= n and C(n,k) has no prime factor <= k, "
                "then n > k^(1 + c) for large k. Published 1974 and not formalised. The filer has not read the "
                "proof; a translator should read EES 1974 first (three pages) and judge whether it is "
                "elementary (Sylvester-Schur style counting of prime powers in k! against the product "
                "(n-k+1)...n) before attempting it. Of the three ELS ranges this is the likeliest to be "
                "within reach."},
    {"node_id": "erdos-1094--h3--h2--h2", "status": "known",
     "references": [
         dict(ELS, note="Proof of Theorem 1, p. 217, the range k^(1+c) < n < k^(7/4): the primes in "
                        "(k/2, k/2 + k^(7/8)) that cannot divide C(n,k) number at most about k^(3/4), fewer than "
                        "Ingham's count, so one of them divides C(n,k)."),
         INGHAM,
     ],
     "summary": "This node is the middle range of Erdős-Lacampagne-Selfridge's Theorem 1: for k^(1+c) < n < "
                "k^(7/4) some prime p in (k/2, k) divides C(n,k). Published 1993 and not formalised. The proof is "
                "Ingham's short-interval prime count (deep, not in Mathlib) plus an elementary count of the "
                "primes in (k/2, k/2 + k^(7/8)) that have no multiple in (n - k, n]. A translation could split "
                "it into those two parts and prove the counting half outright."},
    {"node_id": "erdos-1094--h3--h2--h3", "status": "known",
     "references": [
         dict(ELS, note="Proof of Theorem 1, pp. 216-217, (1)-(4), the range k^(7/4) <= n < c k^2 / ln k: Ingham "
                        "gives more than k^(3/4)/(c ln k) primes in (k/2, k/2 + k^(3/4)), so two of them are "
                        "within c ln k of each other, and one of the two has two multiples in (n - k, n] and "
                        "divides C(n,k)."),
         INGHAM,
     ],
     "summary": "This node is the upper range of Erdős-Lacampagne-Selfridge's Theorem 1: for k^(7/4) <= n with "
                "C n log2 k < k^2, some prime p in (k/2, k) divides C(n,k). Published 1993 and not formalised. "
                "The proof is Ingham's count of primes in (x, x + x^(3/4)) (deep, not in Mathlib), a pigeonhole "
                "to two close primes, and Kummer's theorem for the prime with two multiples in (n - k, n]; "
                "everything but Ingham is elementary. A translation could split off Ingham as its own hole, "
                "shared with erdos-1094--h3--h2--h2."},
]

if __name__ == "__main__":
    for r in RECORDS:
        r["model_and_tooling"] = TOOLING
        r["references"] = [{k: v for k, v in ref.items()} for ref in r["references"]]
    json.dump(RECORDS, open(__file__.replace("records.py", "records.json"), "w"), ensure_ascii=False, indent=1)
    print(len(RECORDS), "records")
