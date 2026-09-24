# Tester log — erdos-402 via plain HTTP (2026-09-24)

Start: 2026-09-24T11:48:26Z (cloud session, outside-contributor role, entry URL
https://openproofnetwork.org/problems/erdos-402/).

## Preflight — blocked by the environment's network policy

11:48:27Z

```
$ curl -sS -o /dev/null -w '%{http_code}\n' https://openproofnetwork.org/problems/erdos-402/
curl: (56) CONNECT tunnel failed, response 403
000
$ curl -sS -o /dev/null -w '%{http_code}\n' https://api.openproofnetwork.org/health
curl: (56) CONNECT tunnel failed, response 403
000
```

The container's egress proxy status (`$HTTPS_PROXY/__agentproxy/status`) records both as
`connect_rejected` — "gateway answered 403 to CONNECT (policy denial or upstream failure)" —
for `openproofnetwork.org:443` and `api.openproofnetwork.org:443`.

This is the environment, not the network: the request never reached openproofnetwork.org.
Per the brief, I stopped here without touching the target.

## Summary

- **Landed:** nothing (no PRs, no nodes, no token requested).
- **Proved:** nothing.
- **Bugs (network):** none observed — the network was unreachable from this container.
- **Environment blocker:** the cloud environment's network policy denies CONNECT to
  `openproofnetwork.org` and `api.openproofnetwork.org`. To rerun this tester, add both hosts
  (and `raw.githubusercontent.com` if the guide sends contributors there) to the environment's
  allowed-hosts list, or use a "full" network-access environment.
