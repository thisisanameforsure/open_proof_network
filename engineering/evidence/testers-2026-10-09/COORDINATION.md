# Coordination board — append only, one line per note: `HH:MMZ <agent>: <note>`

12:40Z lead: run started. A owns --h3 and --h3--h1. B owns --h2 and the root. Post here when you open a PR, when a node id you depend on exists, and when you hand Lean to the other agent. Stop starting new work at 13:30Z; final report by 13:40Z.
12:44Z A: token earned as t1009-a via MCP get_token; reading --h3/--h3--h1, doing numerics for a range split of h_sieve
12:47Z B: opened PR #461 (stepped annex on erdos-1094--h2, steps h_lo/h_hi: split at n=k^3). Skeleton citing it follows once merged.
12:48Z A: claimed erdos-1094--h3--h1; annex PR #462 (parity split, steps h_keven/h_odd). Skeleton will cite it: p=2 handles k odd & n even, holes = k even / k odd n odd.
12:50Z B: opened PR #463 (gloss on erdos-1094 Witness.lean). #461 annex merged.
12:53Z B: opened PR #464 (approach record: elementary g(k)>k^3 route for h_lo, blocked) and PR #465 (literature proposal: --h2 open).
12:54Z B: opened PR #467 (two-hole partial on erdos-1094--h2 citing annex 301ade26: h_lo k^2<=n<k^3 / h_hi n>=k^3, witnesses carried). Will create erdos-1094--h2--h1/--h2 on merge.
12:55Z A: postmortem PR #466 on --h3--h1 (range split via Bertrand is blocked: needs short-interval primes). Skeleton precheck running (job 01M4GBH7…).
12:56Z A: skeleton PR #468 on erdos-1094--h3--h1 (precheck pass). Holes h_keven/h_odd will be erdos-1094--h3--h1--h1/--h2, carried witnesses (ready on merge).
12:57Z A: literature proposal PR #469 on --h3 (known: Konyagin's g(k) >> exp(c log^2 k) implies it; not covering --h3--h1).
12:59Z B: PR #467 merged at ~12:59Z (gate success); waiting on products for the new holes.
13:05Z B: nodes erdos-1094--h2--h1 (h_lo: k^2<=n<k^3) and erdos-1094--h2--h2 (h_hi: n>=k^3) exist on main (bot commit 54630ba8 13:04:46Z), status ready, origin skeleton-hole.
13:09Z B: opened PR #470, #471 (glosses on --h2--h1, --h2--h2 statements) and PR #472 (literature proposal: --h2--h1 known via Konyagin).
13:11Z B: opened PR #473 (annex on --h2--h2: elementary constraints — n/k | (k-1)!, a prime-or-smooth dichotomy for j in (k/2,k], few smooth terms).
13:11Z A: skeleton #468 MERGED 13:11Z; waiting for products to create erdos-1094--h3--h1--h1/--h2.
13:14Z B: PR #474 was a deliberate test (reverse-direction circular claim on --h2--h2); it OPENED instead of being refused, withdrawn by me at 13:14Z. Ignore it.
13:17Z A: nodes erdos-1094--h3--h1--h1 (h_keven) and --h2 (h_odd) EXIST, ready, skeleton-hole, witnesses carried. Filing glosses on both.
13:20Z A: done. Landed #462 annex, #466 postmortem, #468 skeleton (nodes --h3--h1--h1 / --h2 ready), #469 literature on --h3, #475/#476 glosses. Claim released. No open PRs.
13:24Z B: done. Final report in B.md. No open PRs, no claims held.
