"""Submit the backfill glosses through the live service (F29-T8, R12).

Runs AFTER the network deploy (POST /glosses accepts `label`, gloss/v3) and the graph re-pin
(the gate accepts gloss/v3). Each record is one append pull request the merge actor merges
unattended (Q5: no human sign-off; stewards edit later).

  python3 submit.py --api https://api.openproofnetwork.org --token "$OPN_TOKEN" --dry-run
  python3 submit.py --api https://api.openproofnetwork.org --token "$OPN_TOKEN"

Without --token, mints one: POST /precheck of the tutorial node's proof (no token) gives a
nonce, then POST /tokens with the pseudonym and the current DCO version (the guide's way).
Reads: records/<target>/<node>/request.json (statement glosses, from validate.py --records) and
route-drafts/<target>/<node>/<partial>.md (route glosses). Writes submit-log.jsonl as it goes,
one line per attempt, and skips any record the log already shows accepted.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "submit-log.jsonl"
FM = re.compile(r"\A---\n(?P<yaml>.*?)\n---\n(?P<body>.*)\Z", re.S)
TUTORIAL = "tutorial-and-swap"
TUTORIAL_PROOF = '/-! The tutorial node (D-27): permanently open, off-ledger. Lean core only. -/\n\ntheorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by\n  intro p q hpq\n  exact ⟨hpq.right, hpq.left⟩\n'


def call(api: str, method: str, path: str, body: dict | None, token: str | None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(api + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    last: Exception | None = None
    for attempt in range(5):  # this laptop's path to the service drops reads (2026-09-21)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b"{}")
            except json.JSONDecodeError:
                return e.code, {}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{method} {path}: no answer after 5 attempts: {last}")


def mint(api: str, pseudonym: str) -> str:
    """The guide's token flow: a tutorial precheck without a token, then POST /tokens."""
    status, dco = call(api, "GET", "/dco.json", None, None)
    assert status == 200, (status, dco)
    status, job = call(
        api,
        "POST",
        "/precheck",
        {
            "node_id": TUTORIAL,
            "artifact_type": "proof",
            "automation": {
                "method": "agent",
                "models": ["Claude Fable 5.1 (claude-fable-5-1)"],
                "framework": "Claude Code (backfill script)",
            },
            "bundle": {f"targets/tutorial/nodes/{TUTORIAL}/Proof.lean": TUTORIAL_PROOF},
        },
        None,
    )
    assert status == 202 and job.get("nonce"), (status, job)
    for _ in range(60):
        time.sleep(10)
        status, got = call(api, "GET", f"/precheck/{job['id']}", None, None)
        if got.get("state") in ("done", "error", "expired"):
            break
    status, tok = call(
        api,
        "POST",
        "/tokens",
        {
            "proof": {"kind": "tutorial", "job_id": job["id"], "nonce": job["nonce"]},
            "pseudonym": pseudonym,
            "dco": {"accepted": True, "version": dco["version"]},
        },
        None,
    )
    assert status == 201, (status, tok)
    print("minted token for", tok.get("identity"), file=sys.stderr)
    return str(tok["token"])


def requests_from_records() -> list[tuple[str, dict]]:
    out = []
    for req in sorted((HERE / "records").glob("*/*/request.json")):
        r = json.loads(req.read_text(encoding="utf-8"))
        node = req.parent.name
        out.append(
            (
                f"statement:{node}",
                {
                    "subject": {"kind": "statement", "node_id": node},
                    "text": r["text"],
                    "supersedes": r["supersedes"],
                    "licence": r["licence"],
                    "drafted_with": r["drafted_with"],
                    "label": r["label"],
                },
            )
        )
    return out


def requests_from_routes() -> list[tuple[str, dict]]:
    out = []
    for md in sorted((HERE / "route-drafts").glob("*/*/*.md")):
        m = FM.match(md.read_text(encoding="utf-8"))
        assert m, md
        fm = {k.strip(): v.strip() for k, v in (ln.split(":", 1) for ln in m.group("yaml").splitlines() if ":" in ln)}
        out.append(
            (
                f"partial:{fm['node']}:{fm['module']}",
                {
                    "subject": {"kind": "partial", "node_id": fm["node"], "module": fm["module"]},
                    "text": m.group("body").strip() + "\n",
                    "supersedes": None,
                    "licence": fm["licence"],
                    "drafted_with": fm["drafted_with"],
                },
            )
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--token")
    ap.add_argument("--token-file", type=Path)
    ap.add_argument("--pseudonym", default="f29-words")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", choices=["statements", "routes"])
    ap.add_argument("--pause", type=float, default=3.0)
    a = ap.parse_args()
    token = a.token or (a.token_file.read_text().strip() if a.token_file else None) or mint(a.api, a.pseudonym)
    done = set()
    if LOG.is_file():
        for ln in LOG.read_text(encoding="utf-8").splitlines():
            e = json.loads(ln)
            if e.get("accepted") and not e.get("dry_run"):
                done.add(e["key"])
    todo = []
    if a.only != "routes":
        todo += requests_from_records()
    if a.only != "statements":
        todo += requests_from_routes()
    accepted = refused = 0
    with LOG.open("a", encoding="utf-8") as log:
        for key, body in todo:
            if key in done:
                continue
            if a.dry_run:
                body = {**body, "dry_run": True}
            while True:
                status, ans = call(a.api, "POST", "/glosses", body, token)
                if status != 429:
                    break
                # D-25's flat write cap (120 per hour per identity): wait for the window, then
                # retry the same record rather than spend the rest of the list on refusals.
                print(f"429 on {key}: {(ans.get('message') or '')[:80]}; waiting 10 min", flush=True)
                time.sleep(600)
            ok = status in (200, 201, 202)
            accepted += ok
            refused += not ok
            log.write(
                json.dumps(
                    {
                        "key": key,
                        "status": status,
                        "accepted": ok,
                        "dry_run": a.dry_run,
                        "code": ans.get("error") or ans.get("code"),
                        "message": (ans.get("message") or "")[:300],
                        "pull_request": ans.get("pull_request") or ans.get("url"),
                        "warnings": ans.get("warnings"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            log.flush()
            print(f"{'ok ' if ok else 'NO '} {status} {key} {ans.get('error') or ans.get('code') or ''}", flush=True)
            time.sleep(a.pause)
    print(f"accepted {accepted}, refused {refused}, skipped {len(done)}")
    return 0 if refused == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
