# Tester A (t1018-a) log
- 19:20Z cloned graph into A/graph; read guide sections; frontier saved A/frontier.json
- 19:22Z tutorial precheck job 01M587EC6R2TZPZ4QZQE0398GK (anon) -> pass; 19:24Z token minted (A/token.json, mode 600)
- 19:21Z check_lean with Mathlib PNT names: no PNT in Mathlib (only Chebyshev.theta/psi defs) -> h3--h3--h1--h1 out of reach
- 19:25Z claimed erdos-1094--h2--h1--h1--h1--h1 (claim 01M587KG8RDM7C93622P609910). Plan: partial: m=n/gcd(n,k) has minFac>k and m<k^2 so m prime; split holes h_prime (n prime) / h_comp (n = g*q, 2<=g|k, q>k prime). check_lean verify: compiles with only sorry (A/p1.lean, A/c2.out)
- 19:26Z precheck 01M587N5086G2SHQD92HDGRFN5 (no witnesses) PASS; holes h_prime, h_comp, expected_witness True. (First attempt 400 partial-unlabelled: `· -- label:` on the bullet line was not seen as "directly above"; moving comments onto their own lines fixed it.)
- 19:30Z precheck 01M587Y34GPAW9HHTGXPEHN61M with two carried witnesses (A/pre2.json)
- 19:32Z claimed erdos-1094--h2--h1--h1--h1--h2 (claim 01M5880K7038W0CMAKHD85Q0JH); partial A/p2.lean compiles on check_lean verify (holes h_one: m prime; h_two: m=p*q)
- 19:37Z submitted partial on h_low: PR #760, submission 01M588DT28AW1BCEVNZ1WA3EHF (A/sub1.out); precheck 01M587Y34GPAW9HHTGXPEHN61M pass, witnesses checked
- 19:45Z submitted partial on h_high: PR #763, submission 01M588QPF8AF6F34FP9FASZNT6, precheck 01M588E5S87PMAHJ9Y38TNXYX0 pass (holes h_one, h_two, witnesses checked)
- 19:47Z postmortems: PR #765 (h_low, A/pm1.out), PR #766 (h_high, A/pm2.out)
- 20:02Z PR #760 MERGED with no human (gate success). At 20:16Z #763, #765 and #766 were still open in the erdos-1094 lane.

## Final report (t1018-a)
(1) Outcome
- erdos-1094--h2--h1--h1--h1--h1 (h_low, 2k<=n<k^2): partial PR #760, MERGED 20:02Z. I proved that m = n/gcd(n,k) is a prime q > k (minFac m > k and m < k^2). That leaves two holes, h_prime (n prime) and h_comp (n = g*q, 2<=g|k), each carrying a witness `True` (checked: true). Expected children are ...--h1--h1 and ...--h1--h2.
- erdos-1094--h2--h1--h1--h1--h2 (h_high, k^2<=n<k^3): partial PR #763, still open at 20:16Z. I proved that m is a prime or a product of two primes > k. Holes h_one and h_two, with witnesses checked.
- Postmortems: PR #765 (h_low) and PR #766 (h_high), both outcome exhausted / budget-exhausted. They say which known ELS exceptions realise each hole, e.g. (44,8) and (46,10) for h_comp, and record that Kummer at p | gcd cannot close h_comp, because v_p(n) = v_p(g) <= v_p(k).
- Neither node was proved outright. Both partials are structural reductions; the analytic core (the residue problem) remains.
(2) BUGS
- Minor: a partial's label check misses a comment on the bullet line. My first precheck (MCP precheck_submission, A/pre1.out) had `    · -- label: ...` and `-- claim:` on the bullet line, and the `have` on the next line. It was refused 400 partial-unlabelled: "hole h_prime: no `-- label:` line in the comment block directly above its `have`". In Lean that comment does sit directly above the `have`. Expected: accepted, or a hint that the comment must be on its own line. Actual: refused. Workaround: put `·` alone on its line. Severity is low and the message pointed the right way.
- No other defects confirmed. One TLS handshake timeout on api.openproofnetwork.org (a urllib URLError while polling get_precheck at about 19:33Z). A retry worked, so this is likely the laptop-path issue already known.
(3) FEATURE REQUESTS
- check_lean could report the D-12 v3.44 partial-label lint (approach, licence, label, claim). Today you only learn about it at precheck_submission. A lint there would save a round trip.
- list_frontier could show each node's statement, or a short form of it. Choosing a node took a raw-clone grep over 40 Statement.lean files.
(4) Time cost
- The merge lane: the erdos-1094 lane held 7 PRs, and #760 took 25 minutes from submission to merge (19:37Z to 20:02Z).
- Choosing a node: every open leaf is research-level. PNT is not in the pinned Mathlib (checked with #check; only Chebyshev.theta and psi exist), so the realistic contribution in one hour was an elementary structural reduction.
- 20:21Z final check: #763, #765 and #766 still open, waiting_on merge (A/t763.json etc.)
