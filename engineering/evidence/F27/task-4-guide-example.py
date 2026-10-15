import random
from datetime import UTC, datetime

EXPLORE_SHARE = 0.2  # the operator's number; the network keeps none
STALLED_DAYS = 14  # D-25's starvation window, a reasonable default


def stalled(route, now):
    s = route["summary"]
    since = s["oldest_open_since"]
    if since is None or s["open"] == 0 or s["proved"] > 0 or s["unattempted"] > 0:
        return False
    return (now - datetime.fromisoformat(since)).days >= STALLED_DAYS


def next_job(answer, frontier_entries, now=None):
    now = now or datetime.now(UTC)
    stalled_routes = [r for r in answer["routes"] if r["live"] and stalled(r, now)]
    if stalled_routes and random.random() < EXPLORE_SHARE:
        return ("propose-route", stalled_routes[0]["node"])  # a variant, a crux, a rival skeleton
    held = {node for s in answer["sets"] for node in s["open"]}
    holes = [
        e
        for e in frontier_entries
        if e["claimable"] and not e["claims"]["active"] and e["node_id"] in held
    ]
    return ("claim", holes[0]["node_id"]) if holes else None


import json, sys
sys.path.insert(0, "/Users/mikehiggins/Desktop/repos/opn-f27/gate")
from opn_gate import routes
d = json.load(open("/Users/mikehiggins/Desktop/repos/opn-f27/gate/tests/fixtures/routes/erdos-1094.json"))
answer = routes.read(d["graph"], d["frontier_entries"]).as_dict()
entries = [{**e, "claims": {"active": [], "history_count": 0}} for e in d["frontier_entries"]]
later = datetime(2026, 11, 15, tzinfo=UTC)
print("stalled at 2026-11-15:", [r["id"] for r in answer["routes"] if r["live"] and stalled(r, later)])
random.seed(0)
print("jobs at 2026-11-15:", [next_job(answer, entries, later) for _ in range(6)])
print("job on 2026-10-15:", next_job(answer, entries, datetime(2026, 10, 15, tzinfo=UTC)))
from collections import Counter
random.seed(1)
print("1000 draws at 2026-11-15:", Counter(next_job(answer, entries, later)[0] for _ in range(1000)))
