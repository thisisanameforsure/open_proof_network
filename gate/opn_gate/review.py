"""The formalization review's derived state and the ladder it earns (F26-R1, R7, R9, R11, R17;
D-9 v3.39, D-30 v3.39).

Nothing here is written: the records under ``targets/<id>/review/`` are the facts, and every
reader derives the same state from them in any order (F08-T10's principle: derive, never
rewrite). Each rule is one small function so that a test can replace exactly one and show it
load-bearing:

- a candidate is *discarded* by a compile, screen or intent-test exhibit whose result is ``fail``
  (``discards``), *returned* by a format exhibit (``returns``; a return is never a discard,
  F26-R4), *surviving* once the job's compile has passed (``compiled``), else *pending*: stage 3
  is the job's, so a candidate it has not compiled has not survived it (F26-T14); an ``error``
  exhibit decides nothing;
- surviving candidates proved equivalent in both directions share a *cluster* (``equivalent``,
  ``components``: the connected components, so equivalence is transitive);
- the *signers* are the latest signature per role, counted when it is an accept
  (``latest_signatures``): a later send-back withdraws an acceptance;
- the *cap* is ``screened-and-signed`` when no person-written candidate is in the surviving
  cluster (``cap_rule``; the largest cluster while more than one survives);
- the *state* is ``complete`` when exactly one cluster survives and no question waits,
  ``needs-intent-signer`` when questions wait on a review the network opened and nobody has
  answered or signed as intent (F26-Q5), else ``open`` (``state_rule``);
- the *ladder* is climbed in order (``earned``): the second rung needs a complete review and one
  accept from someone who wrote no surviving candidate; the third the intent signer's accept; the
  fourth both roles and a person's candidate in the cluster, else the cap holds every rung above
  the second. ``grade_of`` never returns a rung below the grade a target already holds.
- a ``split`` by the intent signer names every cluster not chosen as a D-30 variant, its label
  ``resolves`` or ``partial`` where a pair already proves the direction and ``related`` otherwise
  (``relation``, ``split_variants``); nothing is written.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from opn_gate import fidelity
from opn_gate.paths import REVIEW_DIR

#: The review states the products publish.
NONE, OPEN, NEEDS_INTENT, COMPLETE = "none", "open", "needs-intent-signer", "complete"
#: The exhibit kinds whose ``fail`` discards a candidate (F26-R4); a pair or mutant exhibit is
#: about a direction or a mutant, never about the candidate's fate.
DISCARDING_KINDS: tuple[str, ...] = ("compile", "screen", "intent-test")
#: The rung a review with no person-written candidate in its surviving cluster caps at.
CAP = "screened-and-signed"
#: A candidate's fates; ``pending`` until the job's compile has passed (F26-T14).
SURVIVING, DISCARDED, RETURNED, PENDING = "surviving", "discarded", "returned", "pending"
#: The two roles, in the order the ladder reads them.
ROLES: tuple[str, ...] = ("intent", "independent")

Record = dict[str, Any]


def _records(folder: Path) -> list[Record]:
    out: list[Record] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.iterdir()):
        if path.suffix not in (".yaml", ".yml"):
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(doc, dict):
            out.append(doc)
    return out


def _json_records(folder: Path) -> list[Record]:
    """The exhibits: ``.json`` beside their ``.lean`` (exhibit/v1)."""
    out: list[Record] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.iterdir()):
        if path.suffix != ".json":
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict):
            out.append(doc)
    return out


def opening(target_dir: Path) -> Record | None:
    """``review.yaml`` as a document, or ``None`` for a target with no review."""
    path = target_dir / REVIEW_DIR / "review.yaml"
    if not path.is_file():
        return None
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return doc if isinstance(doc, dict) else None


def questions_waiting(target_dir: Path) -> list[Record]:
    """The questions no answer record names, in the records' order."""
    base = target_dir / REVIEW_DIR
    answered = {str(a.get("question")) for a in _records(base / "answers")}
    return [q for q in _records(base / "questions") if str(q.get("id")) not in answered]


# --- the rules, one function each ---------------------------------------------------------


def discards(exhibit: Record) -> bool:
    """A compile, screen or intent-test exhibit whose result is ``fail`` (F26-R4). ``error``
    decides nothing; a pair or mutant exhibit is not about the candidate's fate."""
    return exhibit.get("kind") in DISCARDING_KINDS and exhibit.get("result") == "fail"


def returns(exhibit: Record) -> bool:
    """A format exhibit returns the candidate to its author; never a discard (F26-R4, R5)."""
    return exhibit.get("kind") == "format" and exhibit.get("result") == "returned"


def compiled(exhibit: Record) -> bool:
    """The job's compile passed: the first half of stage 3, without which no candidate survives
    (F26-T14; D-9 v3.39's "one cluster survives stage 3")."""
    return exhibit.get("kind") == "compile" and exhibit.get("result") == "pass"


def equivalent(pair: Record) -> bool:
    """Both directions proved: the two candidates share a cluster (F26-R7)."""
    return all(
        isinstance(pair.get(d), dict) and pair[d].get("state") == "proved"
        for d in ("forward", "backward")
    )


def components(ids: set[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    """The connected components of ``ids`` under ``edges`` (union-find), each sorted, in the
    order of their smallest member; an edge naming an id outside the set is ignored."""
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        if a in parent and b in parent:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    groups: dict[str, list[str]] = {}
    for i in sorted(ids):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values())


def latest_signatures(signatures: list[Record]) -> dict[str, Record]:
    """The latest signature per role, by date and then by the records' order: a later
    send-back withdraws an earlier acceptance (F26-R9)."""
    out: dict[str, Record] = {}
    ordered = sorted(enumerate(signatures), key=lambda t: (str(t[1].get("date")), t[0]))
    for _, s in ordered:
        role = str(s.get("role"))
        if role in ROLES:
            out[role] = s
    return out


def accepted(latest: dict[str, Record]) -> dict[str, str | None]:
    """The signers by role: the login of each role's latest signature when it is an accept."""
    return {
        role: str(s.get("login"))
        if (s := latest.get(role)) is not None and s.get("decision") == "accept"
        else None
        for role in ROLES
    }


def is_person(candidate: Record) -> bool:
    """A person's candidate: its author's automation method is ``manual`` (F26-R3)."""
    return candidate.get("method") == "manual"


def cap_rule(members: list[Record]) -> str | None:
    """``screened-and-signed`` when no person-written candidate is among ``members``, the
    surviving cluster's candidates (F26-R9); ``None`` lifts the cap."""
    return None if any(is_person(c) for c in members) else CAP


def state_rule(head: Record, n_clusters: int, waiting: int, can_answer: bool) -> str:
    """``complete`` when exactly one cluster survives and no question waits;
    ``needs-intent-signer`` when questions wait on the network's own opening and nobody has
    answered or signed as intent (F26-Q5); else ``open``."""
    if n_clusters == 1 and not waiting:
        return COMPLETE
    opened_by = head.get("opened_by")
    role = opened_by.get("role") if isinstance(opened_by, dict) else None
    if waiting and not can_answer and role == "network":
        return NEEDS_INTENT
    return OPEN


def earned(state: str, signers: dict[str, str | None], authors: set[str], cap: str | None) -> str:
    """D-9 v3.39's ladder, climbed in order (F26-R9). ``authors`` are the authors of the
    surviving candidates; ``cap`` is ``cap_rule``'s answer."""
    floor = fidelity.GRADES[0]
    if state != COMPLETE:
        return floor
    if not any(login is not None and login not in authors for login in signers.values()):
        return floor  # above the floor the attestor is not the author (D-9)
    grade = "screened-and-signed"
    if signers["intent"] is not None:
        grade = "author-attested"
        if signers["independent"] is not None:
            grade = "expert-attested"
    if cap is not None and fidelity.rank(grade) > fidelity.rank(cap):
        grade = cap
    return grade


def relation(chosen: set[str], other: set[str], pairs: list[Record]) -> str:
    """The D-30 label of a cluster not chosen (F26-R11): ``resolves`` where a pair proves a
    member of ``other`` implies a member of ``chosen``, ``partial`` where one proves the
    converse, ``related`` where neither is proved."""
    other_implies_chosen = chosen_implies_other = False
    for p in pairs:
        a, b = str(p.get("a")), str(p.get("b"))
        forward = isinstance(p.get("forward"), dict) and p["forward"].get("state") == "proved"
        backward = isinstance(p.get("backward"), dict) and p["backward"].get("state") == "proved"
        if a in chosen and b in other:
            chosen_implies_other |= forward
            other_implies_chosen |= backward
        elif a in other and b in chosen:
            other_implies_chosen |= forward
            chosen_implies_other |= backward
    if other_implies_chosen:
        return "resolves"
    if chosen_implies_other:
        return "partial"
    return "related"


def the_split(signatures: list[Record]) -> Record | None:
    """The intent signer's latest signature when it is a ``split``; only the intent signer
    confirms that clusters are different readings (F26-R11)."""
    s = latest_signatures(signatures).get("intent")
    return s if s is not None and s.get("decision") == "split" else None


def surviving_authors(full: Record) -> set[str]:
    """The authors of the surviving candidates: who a non-author rule excludes."""
    return {c["author"] for c in full["candidates"] if c["status"] == SURVIVING}


# --- the derivation -----------------------------------------------------------------------


def _pairs(base: Path) -> list[Record]:
    """The pair records, one per pair: a later record for the same pair supersedes."""
    latest: dict[tuple[str, str], Record] = {}
    for p in _records(base / "pairs"):
        key = (str(p.get("a")), str(p.get("b")))
        held = latest.get(key)
        if held is None or str(p.get("date")) >= str(held.get("date")):
            latest[key] = p
    return [latest[k] for k in sorted(latest)]


def derive(target_dir: Path) -> Record:
    """The review's full derived state: every candidate with its fate and the exhibit that
    decided it, the clusters, the questions waiting, the cap, the signers and the state.
    ``state_of`` is its projection to the product shape."""
    head = opening(target_dir)
    base = target_dir / REVIEW_DIR
    candidates: list[Record] = []
    if head is None:
        return {
            "state": NONE,
            "candidates": candidates,
            "clusters": [],
            "questions_waiting": [],
            "grade_cap": None,
            "signers": dict.fromkeys(ROLES),
            "tracking": None,
        }
    exhibits = _json_records(base / "exhibits")
    for c in sorted(_records(base / "candidates"), key=lambda c: str(c.get("id"))):
        cid = str(c.get("id"))
        mine = [e for e in exhibits if str(e.get("candidate")) == cid]
        status, exhibit = SURVIVING, None
        returned = next((e for e in mine if returns(e)), None)
        discarded = next((e for e in mine if discards(e)), None)
        if returned is not None:
            status, exhibit = RETURNED, str(returned.get("id"))
        elif discarded is not None:
            status, exhibit = DISCARDED, str(discarded.get("id"))
        elif not any(compiled(e) for e in mine):
            status = PENDING
        candidates.append(
            {
                "id": cid,
                "author": str(c.get("author")),
                "method": str(c.get("method")),
                "status": status,
                "exhibit": exhibit,
            }
        )
    surviving = {c["id"] for c in candidates if c["status"] == SURVIVING}
    pairs = _pairs(base)
    edges = [(str(p.get("a")), str(p.get("b"))) for p in pairs if equivalent(p)]
    clusters = components(surviving, edges)
    waiting = [str(q.get("id")) for q in questions_waiting(target_dir)]
    signatures = _records(base / "signatures")
    latest = latest_signatures(signatures)
    can_answer = bool(_records(base / "answers")) or "intent" in latest
    by_id = {c["id"]: c for c in candidates}
    # the largest cluster; on a tie the one with the smallest representative, so any order of
    # records gives the same answer
    largest = min(clusters, key=lambda m: (-len(m), m[0]), default=None)
    cap = None if largest is None else cap_rule([by_id[i] for i in largest])
    return {
        "state": state_rule(head, len(clusters), len(waiting), can_answer),
        "candidates": candidates,
        "clusters": clusters,
        "questions_waiting": waiting,
        "grade_cap": cap,
        "signers": accepted(latest),
        "tracking": head.get("tracking"),
    }


def state_of(target_dir: Path) -> Record:
    """The ``review`` object ``targets-index`` and ``graph.json`` carry (F26-R17)."""
    full = derive(target_dir)
    return {
        "state": full["state"],
        "candidates": len(full["candidates"]),
        "surviving": sum(1 for c in full["candidates"] if c["status"] == SURVIVING),
        "clusters": len(full["clusters"]),
        "questions_waiting": len(full["questions_waiting"]),
        "open_pairs": len(open_pairs(target_dir)),
        "grade_cap": full["grade_cap"],
        "signers": full["signers"],
        "tracking": full["tracking"],
    }


def grade_of(target_dir: Path, existing_grade: str) -> str:
    """The rung the review has earned (D-9 v3.39's ladder, F26-R9), never below
    ``existing_grade``: no grade a target holds today is taken away. A target with no review
    keeps its grade; ``published-and-uncontested`` is never derived here."""
    fidelity.rank(existing_grade)  # refuse an unknown rung before reading anything
    full = derive(target_dir)
    if full["state"] == NONE:
        return existing_grade
    grade = earned(full["state"], full["signers"], surviving_authors(full), full["grade_cap"])
    return max(existing_grade, grade, key=fidelity.rank)


def split_variants(target_dir: Path) -> list[Record]:
    """The clusters a ``split`` by the intent signer did not choose, each as a D-30 variant
    (F26-R11): its representative, its members and the relation the pairs already prove.
    Empty without such a signature; nothing is written."""
    full = derive(target_dir)
    base = target_dir / REVIEW_DIR
    split = the_split(_records(base / "signatures"))
    if split is None:
        return []
    chosen = next((m for m in full["clusters"] if split.get("cluster") in m), None)
    if chosen is None:
        return []
    pairs = _pairs(base)
    return [
        {
            "representative": m[0],
            "members": list(m),
            "relation": relation(set(chosen), set(m), pairs),
        }
        for m in full["clusters"]
        if m != chosen
    ]


def open_pairs(target_dir: Path) -> list[dict[str, str]]:
    """``graph.json``'s ``open_pairs`` (F26-R8): each open direction, in the records' order."""
    out: list[dict[str, str]] = []
    for p in _pairs(target_dir / REVIEW_DIR):
        for direction in ("forward", "backward"):
            d = p.get(direction)
            if isinstance(d, dict) and d.get("state") == "open":
                out.append({"a": str(p.get("a")), "b": str(p.get("b")), "direction": direction})
    return out


def for_context(target_dir: Path) -> Record | None:
    """``CONTEXT.json``'s ``review`` for the root node (F26-R17): the state, the words and the
    questions waiting; ``None`` for a target with no review."""
    head = opening(target_dir)
    if head is None:
        return None
    return {
        "state": state_of(target_dir)["state"],
        "words": str(head.get("words") or ""),
        "questions_waiting": [
            {"id": str(q.get("id")), "question": str(q.get("question") or "")}
            for q in questions_waiting(target_dir)
        ],
    }
