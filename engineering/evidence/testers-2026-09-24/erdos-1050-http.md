# Tester log — erdos-1050 over plain HTTP (2026-09-24)

Start: 2026-09-24T11:48:10Z (`date -u`). Entry point: https://openproofnetwork.org/problems/erdos-1050/

## 11:48:10Z — first action: reachability probe

```
$ curl -sS -o /dev/null -w '%{http_code}\n' https://openproofnetwork.org/problems/erdos-1050/
curl: (56) CONNECT tunnel failed, response 403
000
$ curl -sS -o /dev/null -w '%{http_code}\n' https://api.openproofnetwork.org/health
curl: (56) CONNECT tunnel failed, response 403
000
```

Both hosts are refused by the sandbox's egress proxy at CONNECT time, before any request
reaches the network. The proxy's own status endpoint records both as
`connect_rejected` — "gateway answered 403 to CONNECT (policy denial or upstream failure)" —
for `openproofnetwork.org:443` and `api.openproofnetwork.org:443` at 11:48:11Z. For comparison,
`raw.githubusercontent.com` answered 301 through the same proxy, so the proxy works and the
denial is specific to the network's hosts.

Per the task rules, this is the stop condition: the environment's network policy is blocking
the tester. No request reached the Open Proof Network, so nothing here is evidence about the
network itself.

## Summary

- **Landed:** nothing (no PRs, no node ids). No token requested, no claim made.
- **Proved:** nothing.
- **Bugs (network's):** none observed — the network was never reached.
- **Environment blocker (not the network's, not mine):** the cloud session's network policy
  denies `openproofnetwork.org` and `api.openproofnetwork.org` (proxy 403 on CONNECT). To rerun
  this test, add both hosts to the environment's allowed domains (or choose a broader access
  level) in the environment's Network access settings.
