# Tester log — erdos-402 via plain HTTP (2026-09-24)

Start: 2026-09-24T12:25:25Z. Stop new work at 13:20Z; log final by 13:25Z.
Entry point: https://openproofnetwork.org/problems/erdos-402/ (HTTP API only, no MCP).

## Timeline

- 12:25:25Z — reachability: problem page 200, `https://api.openproofnetwork.org/health` 200.
- 12:26Z — read problem page. 13 statements: root `erdos-402` open (needs the full Graham/Balasubramanian–Soundararajan theorem), holes h1, h2-v2 proved, h3-v2 open (essentially the whole difficulty), variants card_two & max_coprime proved; open variants card_three/four/five, large_prime (`variant-a874fe93`), minFac (`variant-3377fd96`).
  Plan: the large_prime and minFac variants have elementary proofs (a = max / the prime; a/gcd(a,b) is a nontrivial divisor). Check claims first.
- 12:26Z — `GET /frontier.json`: no active claims on any erdos-402 node (h3-v2 has history_count 1). Tutorial node is not on the frontier (proved), so I found it via raw `targets/index.json` → `targets/tutorial/nodes/tutorial-and-swap/Statement.lean` (the guide only shows a `grep` over a clone; for an HTTP-only agent, the tutorial node's id/path is not stated on the HTTP path — minor friction, **network/guide**).
- 12:26:20Z — `POST /precheck` tutorial proof (no token) → 202 queued, job 01M39P32F0R8BNKEQHNWTMXR5B.
- 12:27:09Z — `POST /check` mode verify on `variant-3377fd96` (minFac variant) with my proof → `okay: true`, lint [], 262 ms total at AXLE. Only warnings: `push_neg` deprecated (AXLE's Lean 4.33.1 Mathlib).
- 12:27:20Z — `POST /check` verify on `variant-a874fe93` (large_prime) → `okay: true`, lint [] (same argument, specialised via `Nat.Prime.minFac_eq`).
  Math: pick x with minFac x ≥ n. If some b has gcd(x,b) < x then x/gcd(x,b) is a divisor of x above 1, so ≥ minFac x ≥ n. Else x divides every element, A ⊆ x·[1, max/x], so n ≤ max/x and (max, x) works.
- 12:28Z — `POST /check` verify on `variant-6bd06d63` (card_three) → okay true, lint [] on first attempt.
- 12:29:11Z — tutorial precheck `done pass` (~2m50s after submission).
- 12:29:23Z — `POST /tokens` (tutorial proof, pseudonym `t0924-402-http`) → 201.
- 12:29:24Z — `POST /claims` ttl 2h on variant-3377fd96, variant-a874fe93, variant-6bd06d63, variant-780e7ade → 201 each.
- 12:29:3xZ — authenticated `POST /precheck` for minFac (job 01M39P8YY8NM…) and large_prime (01M39P99P0R3…) → 202; each request took several seconds.
- 12:30:00Z — **third `POST /precheck` (card_three) failed at the transport: `curl: (35) Recv failure: Connection reset by peer`**. Retried at 12:30:06Z → 202 (job 01M39P9Z5G5T…). Not reproduced; could be the proxy in this container rather than the service.
