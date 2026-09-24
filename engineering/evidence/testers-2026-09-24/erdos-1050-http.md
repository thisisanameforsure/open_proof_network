# Tester log — erdos-1050 over plain HTTP (2026-09-24)

Start: 2026-09-24T12:24:56Z. Stop new work at 13:19:56Z; log final by 13:24:56Z.
Entry URL: https://openproofnetwork.org/problems/erdos-1050/ (curl only, no MCP).

## Log

- 12:24:56Z `curl .../problems/erdos-1050/` → 200; `curl https://api.openproofnetwork.org/health` → 200. Network OK.
- 12:25Z Read the problem page and /docs/ (AGENTS.md rendered). Page shows 4 statements: root `erdos-1050` (open), `--h1` (superseded), `--h1-v2` (open), `--h1-v2--h1` (**circular**, a defect claim merged). Frontier: root + h1-v2 claimable, 0 active claims; `GET /submissions.json` → 0 open. No competing work in flight yet.
- 12:26Z `POST /precheck` on tutorial-and-swap (anonymous) → 202 in 3.9 s, job queued. (Tutorial statement fetched from raw.githubusercontent at the page's graph commit 65b748f.)
- 12:26Z Cloned the graph (guide's `GRAPH`). Read all attempts on the target: every open node is Borwein's 1991 theorem for q=2, r=-3 restated (three postmortems + a circular-decomposition defect say so). The prior postmortem's advice: a new skeleton should split Borwein's q-Padé argument (construction, remainder non-vanishing, growth), not restate it. That is what I will try.
- Page oddity (minor): the root node is shown "open / ready" and its frontier entry has `tags.deps: ["erdos-1050--h1-v2"]` while that dep is unproved; the page explains "closable through its holes", fine, but the status legend says "blocked: waits on other statements" — a reader may expect root = blocked.
- 12:28Z Tutorial precheck `done`, verdict pass (steps 1,2,4-8 pass) — ~2.5 min end to end.
- 12:33:47Z `GET /dco.json` inside `$(...)` hit `curl: (35) Recv failure: Connection reset by peer` (transient, this environment's proxy or the host; not reproduced — the same GET worked at 12:27 and later). My script then sent an empty `dco.version`; `POST /tokens` → 400 `dco-version-stale` with a clear message naming the current hash. **Good error.** Note the nonce was NOT consumed by the 400: the retry at 12:33:55 with the right version → 201 in 0.27 s, pseudonym `h0924-1050-http`. (Own mistake: no `-f`/check on the DCO fetch.)
- 12:34Z `GET /claims.json`, `/submissions.json`: nothing on erdos-1050. `POST /claims {node_id: erdos-1050--h1-v2, ttl_hours: 1}` → 201, 0.37 s.

### Mathematics (12:27–12:34Z, scratch numerics, Python `fractions` + mpmath)
- Let f(x) = Σ_{k≥1} x^k/(2^k−1) = Σ_{j≥1} x/(2^j−x). Root sum = tail T = f(3)/3.
- Solving the [n/n] Padé system for f at 0 exactly (rationals) gives denominators
  **Q_n(x) = Σ_{k=0}^n (−1)^k 2^{k(k−1)/2} [n k]_2 [2n−k n]_2 x^k** (Gaussian binomials at q=2); the closed form satisfies the Padé conditions exactly for every n ≤ 40 checked.
- Evaluating at x=3 directly *diverges* (|3| > radius 2), and so does x = 3/4. The trick that works: the functional equation f(x) = f(x/2) + (x/2)/(1−x/2) gives f(3) = f(3/2^m) + Σ_{j=1}^m (3/2^j)/(1−3/2^j); take **m = n**, x_n = 3/2^n. With d_n = common denominator, b_n = d_n Q_n(x_n), a_n = d_n (P_n(x_n) + Q_n(x_n)·corr_n): log2|b_n f(3) − a_n| ≈ −0.74 n² (n=36: −961), i.e. super-exponential decay, nonzero at every n checked. So these explicit integer sequences numerically witness `erdos-1050--h1-v2` (after ×3 for T = f(3)/3). This is Borwein's q-Padé route made explicit.
