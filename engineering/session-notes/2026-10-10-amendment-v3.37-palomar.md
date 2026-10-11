# Decisions amendment v3.37: registration in Palomar

**Status (2026-10-10): approved by the owner as part of the F25 plan; applied by F25-T0.** v3.36
(the formalization review, drafted 2026-10-09) is not yet applied; this amendment takes the next
number so that the two drafts stay distinct, and the version block says so.

Source: the Palomar read of 2026-10-10 (`palomar-registry.org`, its policy repository, its
submission protocol at `submit.palomar-registry.org/llms.txt`, its data host, and seven registered
entries), and the owner's rulings the same day:

- **authors** of a registration are the ledger's pseudonyms on the statement and proof lines of the
  proof's closure, as D-32 derives authorship; a contributor may record a display name and link
  that replace the pseudonym; the registering curator is the responsible maintainer;
- **toolchain**: an export is ported per registration to the toolchain the registry requires; a
  newer pin for new intakes is a later decision (D-7 unchanged);
- **disclosure**: `method`, `models` and `framework` are mandatory on a proof submission; cost is
  optional, and is wall time, token totals, hardware and a free `spend` string, never a dollar
  figure a subscription cannot give;
- **licence**: the graph's code is Apache-2.0 in a root `LICENSE`; the non-code record is
  CDLA-Permissive-2.0 in a root `NOTICE`; the DCO text names both (D-23's one-way door, closed now).

What Palomar is, in one paragraph: a public registry of Lean formalizations at one commit each,
checked by Comparator with two independent kernels and judged by a model against a notability
floor; a preprint server for Lean proofs, not peer review (its own words). Registry metadata is
CC0. A registration is permanent. An agent may prepare a submission and must never register it;
the person who reads the review does.

## 1. D-10: registration and the feed

Add to the list: *v3.37 — registration.* A resolved open-track target, or a formalization-track
target its curator judges of research interest, is registered in Palomar by a curator from a
wrapper repository built by the pinned gate's export; the registration is appended to the target
as a record; the report-back states the fidelity grade verbatim. Palomar's feed is a prior-art
source for D-6 intake and for D-25 literature proposals, and a registered entry may be read into a
target as a second formalization (D-9 layer 4). The fail-open condition is unchanged.

## 2. D-23: the licences named; structured disclosure

The data licence is named: CDLA-Permissive-2.0, in `NOTICE` at the graph root; the code licence
Apache-2.0 in `LICENSE`; the DCO text names both. Disclosure per merge becomes a structured block
(`automation`): `method` (manual, copilot, agent, autonomous, other), `models`, `framework`
required; `tool_setup`, `wall_time`, `tokens`, `hardware`, `spend` optional. The free string stays
for the record already written.

## 3. D-19 and D-32: who a registration names

Authors = ledger identities on the statement and proof lines of the proof closure (D-18 v3.27's
footprint), each shown by its display name if one is recorded, else its pseudonym. The curator is
the responsible maintainer. Registration is credited on the `upstreaming` line. Models are
disclosed in `automation` and are never authors.

## 4. D-3: two append-only records

`targets/<id>/registrations/<date>-<n>.yaml` (`registration/v1`), by a curator or a listed steward
of the target, latest per registry id wins, withdrawable (D-18 v3.27); and `names/<pseudonym>.yaml`
(`display-name/v1`) at the graph root, written only by the holder of the pseudonym through the
service and signed by the approval key; a later record with `name: null` withdraws it.

## 5. D-25: a registry id as a literature reference

A Palomar id (`PALOMAR-YYYY-MM-DD-NNNNNN vN`) is an accepted form of reference in a literature
record.

## 6. D-28 and D-35: tools and routes

`list_registrations` (read), `set_display_name` (write), `register_target` (write, curator);
`POST /me/name`, `POST /registrations`.

## 7. Glossary

Registration; wrapper repository; conformance corpus.

## 8. Judgement calls

Recorded in the F25 spec (F25-Q1 to F25-Q12), each weighed against the project's goals.
