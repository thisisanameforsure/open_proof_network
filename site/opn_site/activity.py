"""F04-T57 (R15; D-36 v3.48): what happened on the record lately, for the home page.

Read from two dated sources the site already renders, and derived nowhere else:

- the ledger (``ledger/*.json``, F07-R12): a statement proposed, a proof or a partial merged, a
  postmortem filed, a write-up recorded — each entry dated by its merge. Revoked entries are
  credit withdrawn (D-18), not news, so they are left out here and kept on the Contributors page;
- the gloss and explainer chains (``glosses.json``, F20) and the explainer signatures (F15): a
  version is words written, dated by its record; a valid signature is a person vouching for
  words, dated by the signature.

One day's events of one kind on one problem are one row naming their count, so a batch (a
backfill, a burst of postmortems) cannot fill the list. Rows are ordered by date, newest first,
then by kind and problem, so a rebuild of the same tree prints the same list (D-36: a page is a
rendering of files, and the wall clock is not one).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

#: How many rows the home page shows.
SHOWN = 8

#: Each kind, in the order rows of one day are listed: words and people first, since
#: understanding is what the page is about (D-36 v3.48).
KINDS: tuple[str, ...] = (
    "vouched",
    "explained",
    "in-words",
    "proved",
    "partial",
    "written-up",
    "proposed",
    "dead-end",
)
_RANK = {k: i for i, k in enumerate(KINDS)}

#: A gloss on a Lean file is words for a statement; an explainer is words for a proof (F20).
_WORDS_KIND = {"gloss": "in-words", "explainer": "explained"}


@dataclass(frozen=True)
class Event:
    """One row: ``count`` events of ``kind`` on ``target_id`` on ``date`` (YYYY-MM-DD).
    ``node_id`` is the one statement when ``count`` is 1, else the first by id; ``signer`` is
    the person who vouched, for ``vouched`` rows only."""

    date: str
    kind: str
    target_id: str
    node_id: str | None
    count: int = 1
    signer: str | None = None


def _ledger_kind(entry: Mapping[str, Any]) -> str | None:
    line = entry.get("line")
    artifact = str(entry.get("artifact") or "")
    if line == "proof":
        # A proof line on an ``attempts/`` file is a merged partial (F07): holes left for others.
        return "partial" if artifact.startswith("attempts/") else "proved"
    return {"statement": "proposed", "attempts": "dead-end", "write-up": "written-up"}.get(
        str(line)
    )


def _day(value: object) -> str | None:
    text = str(value or "")
    return text[:10] if len(text) >= 10 and text[4] == "-" and text[7] == "-" else None


#: One event: (day, kind, target, node, signer, what it is about). The last field keeps two
#: distinct records on one node apart and lets the same record seen through two sources (an
#: explainer signature in ``glosses.json`` and on the node) count once.
_Raw = tuple[str, str, str, str | None, str | None, str]


def _raw(targets: Mapping[str, Any], entries: Iterable[Mapping[str, Any]]) -> set[_Raw]:
    return _ledger_events(targets, entries) | _words_events(targets)


def _ledger_events(targets: Mapping[str, Any], entries: Iterable[Mapping[str, Any]]) -> set[_Raw]:
    out: set[_Raw] = set()
    for e in entries:
        kind, day = _ledger_kind(e), _day(e.get("date"))
        if kind is None or day is None or e.get("status") != "active":
            continue
        target = str(e.get("target") or "")
        if target not in targets:
            continue  # a ledger line for a target the products no longer list has no page
        node = str(e["node"]) if e.get("node") else None
        out.add((day, kind, target, node, None, str(e.get("artifact") or "")))
    return out


def _words_events(targets: Mapping[str, Any]) -> set[_Raw]:
    out: set[_Raw] = set()
    for target, tv in targets.items():
        for subject in getattr(tv, "subjects", ()):
            kind = _WORDS_KIND.get(subject.record)
            if kind is None:
                continue
            for chain in subject.chains:
                for v in chain.versions:
                    if v.withdrawn:
                        continue
                    if day := _day(v.date):
                        out.add((day, kind, target, subject.node, None, v.hash))
                    for signer, date, file in v.signers:
                        if day := _day(date):
                            out.add((day, "vouched", target, subject.node, signer, file))
        for node_id, nv in getattr(tv, "nodes", {}).items():
            for s in getattr(nv, "signatures", ()):
                if day := _day(s.date):
                    out.add((day, "vouched", target, node_id, s.signer, s.path))
    return out


def events_of(targets: Mapping[str, Any], entries: Iterable[Mapping[str, Any]]) -> list[Event]:
    """Every row, newest first. ``targets`` maps id to the site's ``TargetView``; ``entries``
    are ledger entries as ``opn_gate.ledger`` reads them."""
    grouped: dict[tuple[str, str, str, str | None], set[tuple[str | None, str]]] = {}
    for day, kind, target, node, signer, what in _raw(targets, entries):
        grouped.setdefault((day, kind, target, signer), set()).add((node, what))
    rows = [
        Event(
            date=day,
            kind=kind,
            target_id=target,
            node_id=min((n for n, _w in found if n), default=None),
            count=len(found),
            signer=signer,
        )
        for (day, kind, target, signer), found in grouped.items()
    ]
    # Newest day first; within a day, by kind, then problem, then signer — a total order.
    rows.sort(key=lambda r: (r.target_id, r.signer or ""))
    rows.sort(key=lambda r: _RANK[r.kind])
    rows.sort(key=lambda r: r.date, reverse=True)
    return rows
