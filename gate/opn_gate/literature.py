"""Literature records (F08-T40; D-3, D-25, D-32 v3.35): what the literature says of a statement.

``nodes/<id>/literature/<timestamp>-<contributor>.yaml`` (``literature/v1``) says the statement is
``open`` (no proof is known), ``known`` (a proof is published and not formalised) or ``elementary``
(a routine formalisation of a known fact), with references and a summary. Unsigned, it is anyone's
proposal, attributed like an annex (D-23); signed by an active steward of the target or a listed
curator — ``via: ssh`` under their own key, or ``via: approval-key`` by the service for a login
signed in on the site — it is a confirmation, of the proposal it names in ``confirms`` or of the
status it states itself. The gate decides which signed records count
(``modes.check_literature_record`` refuses the rest before merge); the products re-decide from the
tree with the same rule, so a record that slipped in by another route still confirms nothing.

:func:`derive` is the products' rule: the latest counting confirmation is the node's
``literature`` and the latest proposal it does not cover is ``literature_proposed``. Derive, never
rewrite (F08-T10): nothing here writes, and removing the records restores the products byte for
byte. A fact about the literature, never about difficulty: no status, membership or claimability
reads it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import schemas, signed
from opn_gate.signer import Signer

log = logging.getLogger(__name__)

SCHEMA = "literature/v1"
DIR = "literature"
STATUSES: tuple[str, ...] = ("open", "known", "elementary")
SUFFIXES: tuple[str, ...] = (".yaml", ".yml")


@dataclass(frozen=True)
class Record:
    """One literature record as written, validated against ``literature/v1``."""

    name: str  # the file name under literature/
    doc: dict[str, Any]

    @property
    def path(self) -> str:
        """The record relative to its node, the shape the products and ``confirms`` use."""
        return f"{DIR}/{self.name}"

    @property
    def contributor(self) -> str:
        return str(self.doc["contributor"])

    @property
    def date(self) -> str:
        return str(self.doc["date"])

    @property
    def status(self) -> str:
        return str(self.doc["status"])

    @property
    def confirms(self) -> str | None:
        named = self.doc.get("confirms")
        return str(named) if named else None

    @property
    def signed(self) -> bool:
        """Whether the record carries a signature at all (``via``, ``key`` and ``signature`` all
        set). A record with some but not all is neither a proposal nor a confirmation: the gate
        refuses it (``signature_problem``) and the products pass it over."""
        return all(
            self.doc.get(f) is not None
            for f in (signed.VIA_FIELD, signed.KEY_FIELD, signed.SIGNATURE_FIELD)
        )

    @property
    def half_signed(self) -> bool:
        fields = (signed.VIA_FIELD, signed.KEY_FIELD, signed.SIGNATURE_FIELD)
        present = [self.doc.get(f) is not None for f in fields]
        return any(present) and not all(present)

    def sort_key(self) -> tuple[str, str]:
        return (self.date, self.name)


@dataclass(frozen=True)
class Literature:
    """What the products publish for one node (graph/v6, frontier/v5, context/v5)."""

    confirmed: dict[str, Any] | None
    proposed: dict[str, Any] | None


def load(node_dir: Path) -> list[Record]:
    """Every record under the node's ``literature/``, oldest first (by ``date``, then name). A
    file that does not validate against ``literature/v1`` is logged and passed over: the gate
    refused it at merge, and one bad file must never decide what the graph says (2026-09-17)."""
    directory = node_dir / DIR
    if not directory.is_dir():
        return []
    found: list[Record] = []
    for path in sorted(p for p in directory.iterdir() if p.suffix in SUFFIXES):
        try:
            doc = schemas.load_yaml(path)
        except schemas.SchemaError as exc:
            log.warning("%s: a literature record that does not read is passed over: %s", path, exc)
            continue
        if doc.get("schema") != SCHEMA or schemas.violations(doc, SCHEMA):
            log.warning("%s: a literature record that does not validate is passed over", path)
            continue
        found.append(Record(path.name, doc))
    found.sort(key=Record.sort_key)
    return found


def signature_problem(
    record: Record, *, signers: frozenset[str], approval_key: str | None, verifier: Signer
) -> tuple[str, str] | None:
    """Why a signed record does not count, as ``(code, reason)``, or ``None`` when it does (or
    when it is an unsigned proposal, which asks for no signature). The codes are the gate's
    (``modes.check_literature_record`` emits them): ``literature-signature`` for a signature that
    is partial, does not verify under the record's key, or claims the approval key and carries
    another; ``literature-signer-unlisted`` for a signer who is neither an active steward of the
    target nor a listed curator (``signers``)."""
    if record.half_signed:
        return "literature-signature", "via, key and signature are set together or not at all"
    if not record.signed:
        return None
    if not signed.verifies(record.doc, verifier):
        return "literature-signature", "the signature does not verify under the record's key"
    problem = signed.approval_key_problem(record.doc, approval_key)
    if problem is not None:
        return "literature-signature", problem
    if record.contributor not in signers:
        return (
            "literature-signer-unlisted",
            f"{record.contributor!r} is neither an active steward of the target nor a listed "
            "curator (D-32 v3.35)",
        )
    return None


def derive(
    records: list[Record],
    *,
    signers: frozenset[str],
    approval_key: str | None,
    verifier: Signer,
) -> Literature:
    """D-25 v3.35: the latest counting confirmation, and the latest proposal it does not cover.

    A confirmation that names a proposal present on the node publishes *that* proposal's status
    and contributor, with the confirmer and the confirmation beside them; one that names nothing
    (or names a record that is not an unsigned proposal on the node, which the gate refuses) states
    the status itself. A proposal is covered when a confirmation names it or is dated no earlier
    than it; the latest uncovered one is ``proposed``, awaiting a steward or curator.
    """
    proposals = {r.name: r for r in records if not r.signed and not r.half_signed}
    counting = [
        r
        for r in records
        if r.signed
        and signature_problem(r, signers=signers, approval_key=approval_key, verifier=verifier)
        is None
    ]
    confirmed: dict[str, Any] | None = None
    covered_name: str | None = None
    since: tuple[str, str] | None = None
    if counting:
        latest = max(counting, key=Record.sort_key)
        named = latest.confirms
        basis = None
        if named and named.startswith(f"{DIR}/"):
            basis = proposals.get(named[len(DIR) + 1 :])
        if basis is None:
            basis = latest
        else:
            covered_name = basis.name
        confirmed = {
            "status": basis.status,
            "record": basis.path,
            "contributor": basis.contributor,
            "confirmed_by": latest.contributor,
            "confirmation": latest.path,
        }
        since = latest.sort_key()
    open_proposals = [
        r
        for r in proposals.values()
        if r.name != covered_name and (since is None or r.sort_key() > since)
    ]
    proposed: dict[str, Any] | None = None
    if open_proposals:
        latest_proposal = max(open_proposals, key=Record.sort_key)
        proposed = {
            "status": latest_proposal.status,
            "record": latest_proposal.path,
            "contributor": latest_proposal.contributor,
        }
    return Literature(confirmed=confirmed, proposed=proposed)
