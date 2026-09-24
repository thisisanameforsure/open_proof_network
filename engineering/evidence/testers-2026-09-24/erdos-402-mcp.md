# Tester log — erdos-402 via MCP (2026-09-24)

Start: 2026-09-24T12:25:17Z. Stop new work at 13:20Z, finish log by 13:25Z.
Entry point: https://openproofnetwork.org/problems/erdos-402/ only.

## Timeline

- 12:25:17Z `curl` page → 200; `curl https://api.openproofnetwork.org/health` → 200. Network OK.
- 12:25Z Read problem page + /docs/ (contributor guide rendered from AGENTS.md). Page lists 13 statements; open: root, h3-v2, variants 3377fd96 (minFac), 6bd06d63 (card=3), 780e7ade (card=4), a874fe93 (large prime), bc28297c (card=5).
- 12:26Z MCP `initialize` + `tools/list` over streamable HTTP: 200 in 0.2 s, 26 tools. Wrote my own tiny JSON-RPC client (python urllib).
- 12:26Z `list_frontier {filters:{target_id:erdos-402}}` → 7 entries, all claimable, no active claims. `list_submissions` → nothing open on erdos-402. So the other agent had not started anything visible yet.
- 12:26Z My mistake: my client parsed `@file` args as JSON first → crash. Fixed (own bug, not network's).
- 12:26:56Z `precheck_submission` on tutorial-and-swap (anonymous) → 202 queued in 3.9 s.
- 12:27Z `get_node` on variant-a874fe93 (large prime) and variant-3377fd96 (minFac): statements import `Nodes.«…».Context`; docstrings carry the informal proof idea.
- 12:27:53Z `check_lean` verify mode on my minFac proof → okay:true, lint [], first try, 2.8 s. Only a warning that `push_neg` is deprecated (use `push Not`).
- 12:28:04Z `check_lean` verify on large-prime proof (same argument, `p.minFac = p`) → okay:true, 1.1 s.
- 12:28:3xZ Transient: `ConnectionResetError` during TLS handshake to api.openproofnetwork.org; the local agent proxy reported `ws_closed_mid_exchange`. Environment (my sandbox's egress proxy), not the network. Added retries to my client.
- 12:28:54Z Tutorial precheck `done/pass` after ~2 min. Nonce was in the 202 body of `precheck_submission` (as the guide says).
- 12:29:01Z `get_dco` → version f7ac75b443f4ca16. 12:29:09Z `get_token {proof:{kind:tutorial,job_id,nonce}, pseudonym:"tester-402-mcp", dco:{accepted:true,version}}` → 201, identity 01M39P87G80HXXRPGH5Q2W174W. (Token kept only in a scratch file outside the repo.)
- 12:29:15–17Z `claim_node` (ttl 2) on variant-3377fd96, variant-a874fe93, variant-6bd06d63 → 201 each.
- 12:29:28/34Z `precheck_submission` (authenticated) for minFac and large-prime proofs → 202 queued.
- 12:30:17Z `check_lean` verify on my card=3 proof → okay:true, first try. (My own mistake: first printed `result.errors` which does not exist; the messages are under `result.lean_messages`.) 12:30:3xZ precheck queued.
- 12:31:14Z claimed variant-780e7ade (card=4). 12:31:40Z `check_lean` verify on my card=4 proof → okay:true first try (1296→64-case split closed by `first | … | omega`). Precheck queued 12:31:5xZ.
- 12:32:49Z claimed variant-bc28297c (card=5) — **my mistake**: the same `get_node` call had just shown an active claim by `t0924-402-http` (claimed 12:31:36Z), and I claimed in the same command without reading it. Then I called `claim_node` again to see the receipt: **a second active claim by the same pseudonym was created** (201, new id). Released that one at 12:33:10Z; the first id was not printed and I found no route that lists my own claims with ids, so it stays until expiry.
- 12:33Z `claims.json` shows the other agent `t0924-402-http` claimed **all four** of variants 3377fd96, 6bd06d63, 780e7ade, a874fe93 at 12:29:24Z — 7–9 s after my claims on three of them (12:29:15–17Z), and before mine on 780e7ade (12:31:14Z). Race. Plan: keep the three I claimed first; hold card=4 (they claimed first) and leave card=5 to them.
