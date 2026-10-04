"""Render a loaded ``Site`` to static HTML (F04-T1; R1-R6, R10, R13; D-36).

Every page names the commit it renders and links every file it renders at that commit (R2).
Everything that comes from the graph passes through ``esc`` (R3); contributor prose is placed in
a labelled block below the kernel-checked object it comments on (R4). Pages are assembled from
``string.Template`` files under ``templates/`` and one stylesheet; nothing external is referenced
(R10). ``render_site`` returns every file's content and ``write`` puts them on disk only after
all of them rendered (R13).
"""

from __future__ import annotations

import difflib
import re
from dataclasses import replace
from html import escape
from pathlib import Path
from string import Template
from typing import Any

from opn_gate import explainers, hosted, intake, layout, products, steward
from opn_gate import graph as graphmod
from opn_gate import ledger as ledgermod
from opn_site import dag, links, prose
from opn_site.model import (
    ChainView,
    LeanFile,
    NodeView,
    Prose,
    Site,
    SiteError,
    SubjectView,
    TargetView,
    VersionView,
)

TEMPLATES = Path(__file__).resolve().parent / "templates"
STATIC = Path(__file__).resolve().parent / "static"
SITE_NAME = "Open Proof Network"
#: F04-T12: the site's words for a node's status (the Vocabulary table of the redesign handoff:
#: ``ready`` reads "open"); the protocol's words stay in ``frontier.json``, the API and Docs.
STATUS_WORDS = {
    "proved": "proved",
    "ready": "open",
    "blocked": "blocked on a dependency",
    "refuted": "refuted by a counterexample",
    "defective": "defective: the statement is vacuous",
    "speculative": "speculative",
    "superseded": "superseded",
    "stale": "stale",
    "disputed": "disputed",
    "abandoned": "abandoned",
}
#: F04-T10: a blocked node's words name its cause when graph.json records one (F03-R8, F07-R6,
#: D-29); a blocked node with no cause is blocked by its dependencies and keeps STATUS_WORDS.
CAUSE_WORDS = {
    "witness-missing": (
        "needs a witness: nothing else blocks it, and supplying one is the work "
        "(propose it through /proposals/witness)"
    ),
    "dep-refuted": "blocked: a dependency was refuted",
    "circular": "circular: it implies a statement it was meant to reduce, so no progress",
}
#: F08-T17 (D-16): the one cause that speaks of a node whatever its status — a merged
#: circularity claim takes a ready node off the frontier as surely as a blocked one.
CIRCULAR_CAUSE = "circular"


def status_words(status: str, cause: str | None) -> str:
    """A status's words, or its cause's where ``graph.json`` records one: a blocked node's cause
    always, and ``circular`` on any status it is published with (F08-T17)."""
    if cause and (status == "blocked" or cause == CIRCULAR_CAUSE):
        return CAUSE_WORDS.get(cause, f"blocked: {cause}")
    return STATUS_WORDS.get(status, status)


#: F04-T15 (Q17): the statuses that owe nobody a witness. A node with an unfilled slot is
#: normally work someone can take, but a D-8 revision leaves the superseded original holding its
#: empty slot for good, and a refuted or abandoned statement is off the route — so the witness
#: block invites work on every *other* open slot. Keyed on these rather than on the gate's
#: ``witness-missing`` cause, which is narrower than it looks: ``blocked_because`` sets it only
#: for a compiler-derived hole that is currently blocked, so a hand-authored node with an
#: unfilled slot has no cause at all and would have been silenced wrongly.
NO_WITNESS_OWED = frozenset({"superseded", "abandoned", "refuted"})
#: F03-Q8: the statuses a claim could take, so the only ones a target's reasons explain.
CLAIMABLE_STATUSES = ("ready", "speculative")
#: F04-T17 (Q19): the site's third workable state. The gate's frontier rule is
#: ``products.workable``: ready, speculative, or a hole blocked *only* by its unfilled witness
#: slot (F03-T9, D-29), which graph.json publishes as ``blocked`` with this cause. The site had
#: kept the older two-status rule, so it called seven claimable statements "Not accepting work".
WITNESS_CAUSE = "witness-missing"
NEEDS_WITNESS = "needs-witness"
#: The states the site invites work on; the set a test holds to the frontier's claimable entries.
WORKABLE_STATES = ("open", NEEDS_WITNESS)
#: A state's word where it differs from its key.
STATE_LABELS = {NEEDS_WITNESS: "needs a witness"}
#: The frontier row's words for a not-claimable target whose index row names no reason (D-6).
NO_RECORD_WORDS = "this target has no curated intake record (D-6)"
#: T9: the api route for the live claims (F05); its origin is config (C6), never a literal here.
CLAIMS_PATH = "/claims.json"
#: F04-T20 (Q22): two more exact service urls a page may link, both open reads: the pull
#: requests in flight, and the sign-off text a token is issued against (D-23).
SUBMISSIONS_PATH = "/submissions.json"
DCO_PATH = "/dco.json"
#: F04-T30: the service paths llms.txt names, beside its origin (config, C6); a test holds them
#: to the service's own routes table and MCP mount.
INFO_PATH = "/info.json"
ERRORS_PATH = "/errors.json"
MCP_PATH = "/mcp"
#: The contributor guide's place on the Docs page, and the licences annex prose may carry
#: (``annex/v1`` takes any SPDX id; these are the three the service accepts, D-23).
GUIDE_HREF = "/docs/#agents"
#: The file-name tail of a merged partial proof under ``attempts/`` (F07).
PARTIAL_SUFFIX = "-partial.lean"
ANNEX_LICENCES = ("CC-BY-4.0", "CDLA-Permissive-2.0", "Apache-2.0")
#: F04-T13 (Q15): the same-origin scripts a page may load (R10), and the KaTeX head and tail the
#: pages carrying a record's informal text take — KaTeX vendored under static/vendor/katex,
#: pinned by its MANIFEST.txt, rendering only inside ``.math`` with trust off (math.js).
SCRIPTS: tuple[str, ...] = (
    "/problems.js",
    "/problem.js",
    "/vendor/katex/katex.min.js",
    "/vendor/katex/auto-render.min.js",
    "/math.js",
)
MATH_HEAD = '<link rel="stylesheet" href="/vendor/katex/katex.min.css">'
MATH_SCRIPTS = (
    '<script src="/vendor/katex/katex.min.js"></script>'
    '<script src="/vendor/katex/auto-render.min.js"></script>'
    '<script src="/math.js"></script>'
)
#: F19-R11: the words every block on a node page and a reading view opens with, so what a block
#: is — kernel-checked, an audited statement, unverified prose, untrusted text — is said in text and
#: never by colour alone. ``unaudited`` and ``unchecked`` are the honest words for a statement no
#: QA pass covers and for Lean no attestation covers.
PROVENANCE: dict[str, str] = {
    "kernel": "Checked by the kernel",
    "audited": "Statement audited",
    "unaudited": "Statement not audited",
    "unverified": "Informal account, unverified",
    "untrusted": "Untrusted contributor text",
    "unchecked": "Not checked",
    # F20-T8 (R13): a gloss's fixed label, a root's words of record, and a definition module.
    "gloss": "In words, unverified",
    "informal": "Curated informal statement",
    "definition": "Shared definition",
}
#: F20-T8 (R14, D-36): the fixed label every explainer version renders under.
EXPLAINER_LABEL = "unverified prose about a kernel-checked proof"
#: F20-R14: where a reader learns to improve the words. The guide's revision section is F20-T12's
#: to write (gate/agents/AGENTS.md, rendered on the Docs page); until it lands this is the guide.
GLOSS_GUIDE_HREF = GUIDE_HREF
#: A gloss subject's kind in the page's words.
GLOSS_KIND_WORDS = {
    "statement": "statement",
    "witness": "witness",
    "relation": "relation",
    "definition": "definition module",
}
#: The words for each merged artifact an explainer chain sits on (``glosses/v1`` kinds).
ARTIFACT_WORDS = {
    "proof": "the proof",
    "alternate": "the alternate proof",
    "partial": "the partial assembly",
    "absent": "a proof no longer in the tree",
}
#: The static tree's text files ship as pages do; its binary files (the fonts) are copied by
#: ``write``.
STATIC_TEXT_SUFFIXES = frozenset({".css", ".js", ".svg", ".txt", ""})
#: F04-T12 (Q14): the Glossary, one row per site word — (key, on the site, meaning, in the
#: protocol). It is the single source for every hover card and for the Docs page's table, so a
#: definition can never differ between the two.
GLOSSARY: tuple[tuple[str, str, str, str], ...] = (
    (
        "problem",
        "Problem",
        "An open mathematical question listed on the network, with the statements its proof needs.",
        "target",
    ),
    (
        "statement",
        "Statement",
        "One formal Lean statement in a problem's proof graph. The problem's own statement is "
        "the root; the rest are pieces a proof of it draws on, or variants of it.",
        "node",
    ),
    (
        "open",
        "open",
        "No proof has closed this statement and nothing blocks starting on it. Anyone may work "
        "on it now.",
        "ready · on the frontier",
    ),
    (
        "blocked",
        "blocked",
        "Waits on other statements, or on a definition that has not been checked yet. Not "
        "accepting work. A statement waiting only for its witness is not blocked in this "
        "sense: it needs a witness.",
        "blocked",
    ),
    (
        NEEDS_WITNESS,
        "needs a witness",
        "Left open by a proof skeleton and waiting only for its witness. Supplying one is the "
        "work here and anyone may do it; once it merges, the statement is open for proof.",
        "blocked · cause witness-missing · on the frontier",
    ),
    (
        "witness",
        "witness",
        "A Lean term showing that a statement's hypotheses can all hold at once, so the "
        "statement is not true for an empty reason. It is one declaration named witness whose "
        "type is ∃ over the statement's variables of the ∧ of its hypotheses, or True when the "
        "statement has none. The gate checks it at step 7.",
        "Witness.lean · D-29 · D-4 step 7",
    ),
    (
        "proved",
        "proved",
        "A proof passed all nine checks and was merged. Proved is not the same as explained.",
        "proved",
    ),
    # F04-T14 (Q16): the statuses the statement graph's key can show beyond the three above.
    (
        "stale",
        "stale",
        "A statement this one depends on was replaced or invalidated, so this one waits to be "
        "re-derived against the replacement. Not accepting work.",
        "stale (D-8, D-18)",
    ),
    (
        "superseded",
        "superseded",
        "Replaced by a corrected version of the same statement. It keeps its history and any "
        "credit already earned; work goes to the newer version.",
        "superseded (D-8)",
    ),
    (
        "disputed",
        "disputed",
        "A dispute about this statement has been accepted for review. New work that depends on "
        "it is on hold until the dispute is settled.",
        "disputed (D-18)",
    ),
    (
        "abandoned",
        "abandoned",
        "A route given up as unreachable, or killed by a counterexample. It stays on the record "
        "with its cause and is never deleted.",
        "abandoned (D-14)",
    ),
    (
        "refuted",
        "refuted",
        "A counterexample to this statement passed the checks and was merged. The statement is "
        "false as written.",
        "refuted (D-12)",
    ),
    (
        "defective",
        "defective",
        "A proof that the statement is vacuous passed the checks and was merged. A curator "
        "repairs it with a new version; nobody edits a statement.",
        "defective (D-12, D-8)",
    ),
    # F04-T26 (Q28): the one key a cause, not a status, puts on a statement (F08-T17).
    (
        "circular",
        "circular",
        "A merged defect claim proves, in Lean, that this statement implies a statement it was "
        "meant to reduce, so any proof of it is a proof of that one and the route leads straight "
        "back where it started. Not accepting work; a proof of it is still accepted, since it "
        "would prove the statement above.",
        "ready · cause circular · circular-decomposition claim (D-16, D-12)",
    ),
    # F04-T33 (Q34): the solid line, which every drawing with a dependency shows.
    (
        "depends-on",
        "depends on",
        "A solid line runs up from a statement to one that declared it as a dependency: the "
        "upper statement's proof may build on the lower one.",
        "deps (META.yaml)",
    ),
    # F18-T2: the marks a proof's drawing makes; the key shows them when the problem is proved.
    (
        "on-proof",
        "on this proof",
        "The statement is part of the proof the problem page has selected: the proof's own "
        "statement and every statement its Lean term rests on, as the gate read the term when it "
        "checked it.",
        "target_proofs[].closure (D-25 v3.26, from step 8's footprint)",
    ),
    (
        "not-needed",
        "not needed by this proof",
        "On the record and not part of the selected proof: a dependency its author declared and "
        "the proof did not use, a decomposition another route took, or work that came later. "
        "Nothing is wrong with it; it is just not what this proof rests on.",
        "not in target_proofs[].closure",
    ),
    (
        "use",
        "used lemma",
        "A dashed line: the proof declares this statement's merged proof as a lemma it uses, "
        "beyond the dependencies its statement declared.",
        "use line, import Nodes.«id».Proof (D-12 v3.25)",
    ),
    (
        "outline",
        "has an outline",
        "A numbered tab: how many informal outlines (annexes) the statement carries. Its panel "
        "lists each one, which merged skeleton followed it and the statements that skeleton "
        "made, or that none has. An outline is the contributor's own text, unverified.",
        "annex (D-31)",
    ),
    (
        "proposed-for",
        "proposed for",
        "A dotted line from a crux statement to the statement its proposer wrote it for. A "
        "pointer only: it changes no status, and once a proof uses the crux the solid line of "
        "the use is drawn instead.",
        "proposed-for record (D-14 v3.26)",
    ),
    (
        "unmeasured",
        "not measured",
        "The gate has not yet recorded which statements this proof's term uses (it was merged "
        "before the record kept that), so the drawing follows what was declared instead, which "
        "can only add statements the proof did not need.",
        "proofs[].used null (F08-T27)",
    ),
    (
        "explained",
        "Explained",
        "A person who can explain the proof without the tool that produced it has signed the "
        "explainer. This is the count the network is judged by.",
        "digested",
    ),
    ("written", "Written up", "A paper or note about the proof exists.", "written-up"),
    (
        "steward",
        "Steward",
        "The named mathematician who has committed to understand and write up whatever the "
        "network produces on a problem. A problem without one does not accept work.",
        "steward (D-32)",
    ),
    # F04-T31: the words a resolved problem wears when its root was not proved (D-33, F03-T17).
    (
        "disproved",
        "disproved",
        "A counterexample to the problem's own statement passed the checks and was merged, so "
        "the conjecture is false as stated. The problem is resolved; its statements take no more "
        "work at the root.",
        "resolved · root refuted (D-33, D-12)",
    ),
    (
        "ill-posed",
        "shown ill-posed",
        "A proof that the problem's own statement is vacuous passed the checks and was merged: "
        "as formalized it holds for an empty reason and says nothing. The problem is resolved; a "
        "curator may list a repaired version.",
        "resolved · root defective (D-33, D-12, D-8)",
    ),
    (
        "needs-steward",
        "Needs a steward",
        "Listed and reviewable, but no mathematician has committed to it yet, so it does not "
        "accept work.",
        "no steward · refuses claims",
    ),
    (
        "curator",
        "Curator",
        "Reads the prior art before a problem is listed. A problem found in the literature is "
        "relabelled a known result.",
        "curator (D-6)",
    ),
    (
        "unchecked",
        "statement unchecked",
        "Nobody other than its author has yet judged whether the Lean says what the conjecture "
        "says. The kernel cannot decide this; a person must.",
        "fidelity: mechanical-only",
    ),
    (
        "checked",
        "statement checked",
        "Someone read the Lean back into words and compared it with the conjecture, but has not "
        "signed. Grade rises to signed once a non-author signs.",
        "fidelity: hand-checked, unsigned",
    ),
    (
        "signed",
        "statement signed",
        "Someone who did not write the Lean has signed that it says what the conjecture says.",
        "fidelity: non-author signature",
    ),
    (
        "work-on",
        "Work on",
        "A courtesy signal to others that you are working on a statement. It expires on its own "
        "and never blocks anyone.",
        "claim (D-25)",
    ),
    (
        "attempt",
        "Attempt",
        "Any proof submitted, pass or fail. Failures are kept on the record and count as "
        "contributions.",
        "attempt (D-13)",
    ),
)
GLOSSARY_BY_KEY: dict[str, tuple[str, str, str]] = {
    key: (label, meaning, proto) for key, label, meaning, proto in GLOSSARY
}
#: The Problems page's legend, in order: the glossary keys it shows and which carry a status dot.
LEGEND_KEYS = (
    "open",
    NEEDS_WITNESS,
    "blocked",
    "proved",
    "explained",
    "written",
    "steward",
    "unchecked",
    "work-on",
)
#: F04-T14 (Q16): the statement graph's key. The three base states are always shown; a status
#: from ``LEGEND_EXTRA`` is shown, in this order, when a statement in the graph has it. Each is a
#: glossary key and a ``dot-<key>`` / ``status-<key>`` class in the stylesheet.
LEGEND_BASE = ("proved", "open", "blocked")
#: The keys that wear a status dot wherever a legend shows them.
DOTTED_KEYS = (*LEGEND_BASE, NEEDS_WITNESS)
LEGEND_EXTRA = ("stale", "disputed", "superseded", "abandoned", "refuted", "defective", "circular")
#: F04-T21 (Q23): the Docs state map's keys. Every status ``graph.json`` can publish, as the
#: site's word (F03-Q8: ``speculative`` reads open, so nine words for ten statuses), and the seven
#: words a problem's status tag can wear; each key item is the hover card those pages use.
STATE_MAP_STATEMENT_KEYS = (
    "open",
    NEEDS_WITNESS,
    "blocked",
    "proved",
    "refuted",
    "defective",
    "stale",
    "disputed",
    "superseded",
    "abandoned",
    "circular",
)
#: F04-T31 (F03-T17, D-33 as written): a resolved problem's word follows its root's status in
#: ``graph.json`` — a counterexample or a vacuity certificate resolves a problem as a proof does,
#: and the site may not call either one "proved". Any other root status (a problem resolved by a
#: ``resolves`` variant) reads "proved".
RESOLUTION_WORDS: dict[str, str] = {"refuted": "disproved", "defective": "shown ill-posed"}
#: What a resolved problem's page says is on the record, by its word.
RESOLUTION_RECORD: dict[str, str] = {
    "proved": "a proof is on the record",
    "disproved": "a counterexample is on the record",
    "shown ill-posed": "a vacuity certificate is on the record",
}
#: The closing artifact each word names, for the digestion counts.
RESOLUTION_ARTIFACT: dict[str, str] = {
    "proved": "proof",
    "disproved": "counterexample",
    "shown ill-posed": "vacuity certificate",
}
STATE_MAP_PROBLEM_KEYS = (
    "open",
    "needs a steward",
    "proved",
    "disproved",
    "shown ill-posed",
    "dormant",
    "known result",
)
#: A problem's status on the public pages (the handoff's three words), each with its definition.
PROBLEM_STATUS_DEFS: dict[str, str] = {
    "open": "Listed, and its statements accept work.",
    "proved": "Its root statement has a merged proof. Not yet explained or written up.",
    "disproved": (
        "A merged counterexample refutes its root statement: the conjecture is false as stated."
    ),
    "shown ill-posed": (
        "A merged vacuity certificate shows its root statement holds for an empty reason, so as "
        "formalized it says nothing."
    ),
    "needs a steward": (
        "Listed and reviewable, but nobody has committed to it yet, so it does not accept work."
    ),
    "dormant": "Set aside: its source lists it as resolved elsewhere, or a curator paused it.",
    "known result": "Found in the literature after listing, so it is a known result, not open.",
}
#: The fidelity grades the index publishes, as the site's tag words (Vocabulary).
FIDELITY_KEYS: dict[str, str] = {
    "mechanical-only": "unchecked",
    "hand-checked": "checked",
    "screened-and-signed": "signed",
    "signed": "signed",
}
#: The words for a statement's place in its problem, by origin (graph/v3).
ORIGIN_ROLES: dict[str, str] = {
    "skeleton-hole": "left open by a proof skeleton",
    "compiler-derived": "derived by the compiler",
    "authored": "a statement the proof needs",
}
RELATION_ROLES: dict[str, str] = {
    "resolves": "a variant that resolves the problem",
    "partial": "a partial route to the problem",
    "related": "a related variant",
}
#: F04-T27 (testers 2026-09-29, item 9): the pages said a problem without a steward "refuses
#: work" while the index carried ``policy.steward_rule.enforced: false`` and every such problem
#: was claimable. The sentences that state the rule are chosen by that switch: in force, or
#: announced and not yet enforced. Each in-force sentence keeps its one home in the constants
#: above; these are the announced forms, substituted by :func:`wording`.
ANNOUNCED = "not yet enforced"
STEWARD_ANNOUNCED = (
    "The named mathematician who has committed to understand and write up whatever the "
    "network produces on a problem. The rule that a problem without one would refuse work is "
    f"announced and {ANNOUNCED}: such a problem still accepts work and says so."
)
NEEDS_STEWARD_ANNOUNCED = (
    "Listed and reviewable, and no mathematician has committed to it yet. It still accepts "
    f"work: the steward rule is announced and {ANNOUNCED}."
)
NEEDS_STEWARD_PROTO_ANNOUNCED = "no steward · still claimable"
NEEDS_STEWARD_STATUS_ANNOUNCED = (
    "Listed and reviewable, and nobody has committed to it yet; it still accepts work until the "
    f"steward rule is enforced ({ANNOUNCED})."
)
RULE_STEWARD_ANNOUNCED = (
    "A named mathematician commits to understand and write up whatever is produced. The rule "
    f"that a problem without one would refuse work is announced and {ANNOUNCED}: today such a "
    "problem is published, says it needs a steward, and still accepts work."
)
ABOUT_STEWARD_IN_FORCE = (
    "It accepts work only while a named mathematician, its steward, has signed a commitment to "
    "understand and write up whatever the network produces on it, and who may prove on it as "
    "well."
)
ABOUT_STEWARD_ANNOUNCED = (
    "It is to have a named mathematician, its steward, who signs a commitment to understand and "
    "write up whatever the network produces on it, and who may prove on it as well; the rule "
    f"that a problem without one would refuse work is announced and {ANNOUNCED}, so such a "
    "problem "
    "still accepts work and says so."
)
DOCS_STEWARD_IN_FORCE = (
    "An open problem is claimable on this network only while it has a steward: a mathematician "
    "who has committed, before anyone starts proving, to receive whatever comes of it (D-32 "
    "v3.17)."
)
DOCS_STEWARD_ANNOUNCED = (
    "An open problem is meant to have a steward: a mathematician who has committed, before "
    "anyone starts proving, to receive whatever comes of it (D-32 v3.17). The rule that a "
    f"problem is claimable only while it has one is announced and {ANNOUNCED}: until the "
    "graph's policy.json enforces it, a problem without a steward still accepts work and its "
    "page says so."
)
STATES_STEWARD_IN_FORCE = "an open problem accepts work only while it has a steward"
STATES_STEWARD_ANNOUNCED = (
    f"an open problem is to accept work only with a steward, a rule announced and {ANNOUNCED}"
)
DOCS_STEP_DOWN_IN_FORCE = (
    "a problem left with no steward is published and reviewable but refuses claims until "
    "someone else commits."
)
DOCS_STEP_DOWN_ANNOUNCED = (
    "a problem left with no steward says so on its page, and will refuse claims until someone "
    f"else commits once the rule is enforced ({ANNOUNCED} today)."
)


def wording(enforced: bool) -> dict[str, Any]:
    """Every sentence that states the steward rule, in the form the switch calls for: the
    glossary (by key and in order), the problem-status definitions, the About rules and the
    template sentences (F04-T27)."""
    glossary = list(GLOSSARY)
    rules = list(ABOUT_RULES)
    about, docs, step_down = ABOUT_STEWARD_IN_FORCE, DOCS_STEWARD_IN_FORCE, DOCS_STEP_DOWN_IN_FORCE
    states = STATES_STEWARD_IN_FORCE
    status = dict(PROBLEM_STATUS_DEFS)
    if not enforced:
        for i, (key, label, _meaning, proto) in enumerate(glossary):
            if key == "steward":
                glossary[i] = (key, label, STEWARD_ANNOUNCED, proto)
            elif key == "needs-steward":
                glossary[i] = (key, label, NEEDS_STEWARD_ANNOUNCED, NEEDS_STEWARD_PROTO_ANNOUNCED)
        rules = [
            (title, RULE_STEWARD_ANNOUNCED if title == "Worked on only with a steward" else words)
            for title, words in rules
        ]
        status["needs a steward"] = NEEDS_STEWARD_STATUS_ANNOUNCED
        about, docs, step_down = (
            ABOUT_STEWARD_ANNOUNCED,
            DOCS_STEWARD_ANNOUNCED,
            DOCS_STEP_DOWN_ANNOUNCED,
        )
        states = STATES_STEWARD_ANNOUNCED
    return {
        "glossary": tuple(glossary),
        "by_key": {key: (label, meaning, proto) for key, label, meaning, proto in glossary},
        "status_defs": status,
        "rules": tuple(rules),
        "about_steward": about,
        "docs_steward": docs,
        "docs_step_down": step_down,
        "states_steward": states,
    }


#: F15-R13 copy for the About page's four rules (the design file's ``steps3``).
ABOUT_RULES: tuple[tuple[str, str], ...] = (
    (
        "Listed only after a search",
        "A curator searches the literature and records what was found. A problem found there "
        "is relabelled a known result.",
    ),
    (
        "Worked on only with a steward",
        "A named mathematician commits to understand and write up whatever is produced. "
        "Without one the problem is published and refuses work.",
    ),
    (
        "Statement checked by a non-author",
        "A statement is graded unsigned until someone who did not write the Lean signs that it "
        "means what the conjecture means; the signatures are counted and named.",
    ),
    (
        "Proved, then explained",
        "A merged proof marks the problem proved and unexplained until a person signs the "
        "explainer and a paper or note exists.",
    ),
)
DECISIONS_DOC = Path(__file__).resolve().parents[2] / "docs" / "architecture_decisions.html"
FUNNEL_DOCS = Path(__file__).resolve().parents[1] / "docs"  # F10-R9: site/docs/*.md
#: F15-R11: the off-site links the site's own copy may carry — dated external evidence, each
#: url exact, the one other way past F04-R13's checker besides a validated record (F11-Q11). A
#: page that links anywhere else off-origin is a build failure; the rule itself is unchanged.
COPY_LINKS: frozenset[str] = frozenset(
    {
        "https://mathandai.org/",  # the declaration of 2026-09-11, 25 Fields medallists
        "https://leidendeclaration.ai/",  # the Leiden Declaration, 2026-06-02
        "https://terrytao.wordpress.com/2026/08/12/a-digestion-of-the-proof-of-sendovs-conjecture/",
        "https://terrytao.wordpress.com/2026/09/11/a-severe-misalignment-of-ai-in-mathematics/",
    }
)
#: F15-R11: the Leiden compliance table, one row per objection of the research note's §5
#: (docs/research_math_and_ai_2026-09.html), read against decisions v3.17: (objection, what
#: the protocol does, what it does not).
LEIDEN_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "A certificate is not understanding",
        "Explainers per proved node, hashed, attributed and labelled unverified (D-3); an "
        "explainer may be signed by a real-identity contributor affirming they can explain the "
        "proof without the tool that produced it, and only signed explainers count (D-3 v3.17); "
        "a resolved target carries a digestion state, undigested until every node of the closing "
        "proof is explained and written-up once the paper exists (D-33 v3.17); explanation "
        "coverage is the first count on the home page (D-36 v3.17).",
        "Nothing renders the graph as a blueprint yet, and an explainer still waits for a person "
        "to press merge.",
    ),
    (
        "Benchmark racing corrupts incentives",
        "No leaderboard (D-34); the home page's counts are the progress series, not vanity "
        "numbers (D-36); the network announces no result beyond the registry report-back, which "
        "carries the digestion state, and the paper (D-33 v3.17); the raw resolution count is "
        "too rare to steer by (Stages).",
        "The record is public, so anyone else may still count.",
    ),
    (
        "Undigested proofs are abandoned",
        "A steward is attached to every open problem before it can be claimed, committed to "
        "understand and write it up, and the problem refuses claims without one (D-6, D-32 "
        "v3.17); the write-up role is theirs from the first day.",
        "Best efforts and no deadline: a steward may step down, and the record then waits.",
    ),
    (
        "Attribution, plagiarism, scooping",
        "A prior-art search before listing, and a target found in the literature is relabelled "
        "a known result, never paid as novelty (D-6); statements are inherited from the public "
        "registry and resolutions reported back to it (D-10); every node records the human "
        "operator, the model and the tooling (D-19, D-23); no machine authorship (D-32); an "
        "upstream edit or a resolution elsewhere is watched for (D-10 v3.12).",
        "The search performed at intake is recorded as its summary, not as the queries run.",
    ),
    (
        "The training pipeline for students is destroyed",
        "Nothing.",
        "A proof network has no answer for students; the sentence below says so.",
    ),
    (
        "Fields are evacuated once their problems fall",
        "Intake is curated, not open, and a problem is listed only when a mathematician from its "
        "community has committed to it or proposed it (D-6 v3.17); a proposer may keep a "
        "statement in-network rather than upstream it (D-10 v3.17).",
        'No reservation mechanism: a community cannot say "not this one" except by no steward '
        "committing.",
    ),
    (
        "Companies set the agenda; the process is undisclosed",
        "Public by default (D-26); every gate run's attestation is published, pass or fail (D-5, "
        "D-34); failed attempts are first-class records with typed goal states (D-13); the "
        "harness is anyone's (D-1); problems come from mathematicians' own proposals first "
        "(D-6 v3.17).",
        "The network is not an entity and formally endorses nothing (D-24).",
    ),
    (
        "Volume nobody can check",
        "Kernel replay, an axiom allowlist and a pinned toolchain on every proof (D-4); graded "
        "statement fidelity with a screening pass and non-author signatures (D-9); intake "
        "bounded by the stewards willing to receive it (D-32 v3.17).",
        "Fidelity is checked; nothing bounds how much a steward has to digest.",
    ),
    (
        "Ethics, environment, ownership of training data",
        "The data licence is fixed before the first external contributor, and annex prose is "
        "licensed by its author or not accepted (D-23).",
        "Nothing beyond the open items the decisions already record.",
    ),
)
PROPOSAL_FORM = "problem-proposal.yml"  # the graph's .github/ISSUE_TEMPLATE/ (F15-R13)
#: F15-R10 (D-10 v3.17): the report-back sentence per digestion state, the words a source
#: registry reads instead of "solved".
DIGESTION_WORDS: dict[str, str] = {
    "undigested": "kernel-checked, not yet explained",
    "explained": "kernel-checked and explained by a person",
    "written-up": "kernel-checked, explained and written up",
}


def document_head(text: str) -> tuple[str, str]:
    """A document's title (its first heading) and summary (its first paragraph's first sentence)."""
    title, summary = "Untitled", ""
    lines = [line.strip() for line in text.splitlines()]
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            rest = lines[i + 1 :]
            paragraph: list[str] = []
            for after in rest:
                if not after and paragraph:
                    break
                if after and not after.startswith("#"):
                    paragraph.append(after)
            summary = " ".join(paragraph).split(". ")[0].rstrip(".") + "." if paragraph else ""
            break
    return title, summary


_STRIP_RE = re.compile(r"<link\b[^>]*>|<script\b.*?</script>", re.S | re.I)
_STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
NAV = (
    ("/", "Home"),
    ("/problems/", "Problems"),
    ("/contributors/", "Contributors"),
    ("/docs/", "Docs"),
    ("/about/", "About"),
)
#: The masthead's one primary action (F04-T12): every open statement, filtered client-side.
NAV_ACTION = ("/problems/?filter=open", "Work on a statement")
#: Where the merged Problems page lives, and the old paths that now redirect to it (Q14).
PROBLEMS_PATH = "/problems/"
REDIRECTS = (("targets/index.html", PROBLEMS_PATH), ("frontier/index.html", PROBLEMS_PATH))
#: A definition's Lean, for the statement row's role word (the mock's "definition" rows).
_DECL_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:noncomputable\s+|private\s+|protected\s+)*"
    r"(def|abbrev|inductive|structure|class)\b",
    re.M,
)


def esc(value: object) -> str:
    """The one escaping function: everything from the graph goes through it (R3)."""
    return escape(str(value), quote=True)


def math(text: str, *, allowed_urls: frozenset[str] = frozenset()) -> str:
    """Record prose that may carry TeX between dollar signs (F04-T13) and a registry
    docstring's inline Markdown (T19): escaped like everything from the graph, the four inline
    forms rendered, then marked for the same-origin math renderer, which reads the text back."""
    return f'<span class="math">{prose.inline_statement(text, allowed_urls=allowed_urls)}</span>'


def static_files() -> tuple[dict[str, str], dict[str, bytes]]:
    """The static tree, text files (stylesheets, scripts, the vendor manifest and licence) apart
    from binary ones (the fonts), each keyed by its path under the site root."""
    text: dict[str, str] = {}
    binary: dict[str, bytes] = {}
    for path in sorted(p for p in STATIC.rglob("*") if p.is_file()):
        rel = path.relative_to(STATIC).as_posix()
        if path.suffix in STATIC_TEXT_SUFFIXES:
            text[rel] = path.read_text(encoding="utf-8")
        else:
            binary[rel] = path.read_bytes()
    return text, binary


def declaration_only(statement: str) -> str:
    """A statement's Lean without its header: the panel shows the declaration and its doc
    comment; the whole file, imports included, is on the statement's own page."""
    lines = statement.rstrip("\n").splitlines()
    last_import = max(
        (i for i, line in enumerate(lines) if line.startswith(("import ", "open "))), default=-1
    )
    body = lines[last_import + 1 :]
    while body and not body[0].strip():
        body.pop(0)
    if body and body[0].startswith("/-"):  # the module doc comment: prose, kept on the page
        end = next((i for i, line in enumerate(body) if line.rstrip().endswith("-/")), None)
        if end is not None:
            body = body[end + 1 :]
            while body and not body[0].strip():
                body.pop(0)
    return "\n".join(body) if body else statement.rstrip("\n")


def _template(name: str) -> Template:
    return Template((TEMPLATES / name).read_text(encoding="utf-8"))


class Renderer:
    def __init__(
        self,
        site: Site,
        *,
        repo_url: str,
        decisions_doc: Path | None = DECISIONS_DOC,
        api_url: str | None = None,
    ) -> None:
        self.site = site
        self.repo_url = repo_url.rstrip("/")
        self.decisions_doc = decisions_doc
        self.api_url = api_url.rstrip("/") if api_url else None
        self.base = _template("base.html")
        #: T19: the urls record prose may link, which are the ones the link checker admits.
        self.cited = cited_urls(site)
        #: F04-T27: the steward rule's sentences, as the record enforces it or announces it.
        self.words = wording(site.steward_rule_enforced)

    # -- links -------------------------------------------------------------------------------

    @property
    def proposal_url(self) -> str:
        """F15-R13: the proposal form on the graph repository — an issue, never a commit."""
        return f"{self.repo_url}/issues/new?template={PROPOSAL_FORM}"

    def file_link(self, rel: str, *, commit: str | None = None, label: str | None = None) -> str:
        """A link to a graph file at the rendered commit (R2), labelled with its path."""
        at = commit or self.site.commit
        url = f"{self.repo_url}/blob/{at}/{rel}"
        return f'<a class="file" href="{esc(url)}">{esc(label or rel)}</a>'

    @staticmethod
    def target_path(target_id: str) -> str:
        return f"{PROBLEMS_PATH}{target_id}/"

    @staticmethod
    def node_path(target_id: str, node_id: str) -> str:
        return f"/nodes/{target_id}/{node_id}/"

    def node_link(self, target_id: str, node_id: str) -> str:
        return f'<a href="{esc(self.node_path(target_id, node_id))}">{esc(node_id)}</a>'

    @staticmethod
    def status_mark(status: str, cause: str | None = None) -> str:
        """The status as a coloured mark and words. A blocked node's cause picks the words; an
        unknown cause is shown as itself, escaped, rather than as a reason it is not."""
        words = status_words(status, cause)
        return (
            f'<span class="status status-{esc(status)}"><span class="mark"></span>'
            f"{esc(words)}</span>"
        )

    # -- pages -------------------------------------------------------------------------------

    def page(  # noqa: PLR0913 — one argument per part of the frame
        self,
        title: str,
        body: str,
        *,
        renders: list[str],
        path: str | None = None,
        head: str = "",
        script: str = "",
    ) -> str:
        """The frame: masthead, the body, the provenance bar (R2). ``path`` marks the current
        nav entry; ``head`` and ``script`` are the page's own same-origin extras (R10)."""
        links_ = []
        for p, label in NAV:
            current = ' aria-current="page"' if p == path else ""
            links_.append(f'<a href="{esc(p)}"{current}>{esc(label)}</a>')
        nav = "".join(links_)
        commit = self.site.commit
        # T20: the footer names the checkout; the products in it may have been rendered at an
        # earlier commit (the bot's own commit follows each merge), and then the page says so.
        rendered = str(self.site.frontier.get("rendered_from") or commit)
        products = (
            f" · products rendered at <code>{esc(rendered[:12])}</code>"
            if rendered != commit
            else ""
        )
        sources = ", ".join(self.file_link(r) for r in renders) or "nothing in the graph"
        live = (
            f' · <a href="{esc(self.api_url + CLAIMS_PATH)}">claims.json ↗</a>'
            if self.api_url
            else ""
        )
        return self.base.substitute(
            title=esc(title),
            site=esc(SITE_NAME),
            nav=nav,
            action_href=esc(NAV_ACTION[0]),
            action_label=esc(NAV_ACTION[1]),
            head=head,
            body=body,
            script=script,
            commit=esc(commit),
            commit_short=esc(commit[:12]),
            commit_url=esc(f"{self.repo_url}/tree/{commit}"),
            products=products,
            sources=sources,
            frontier_link=self.file_link("frontier.json", label="frontier.json ↗"),
            live=live,
        )

    def redirect(self, to: str) -> str:
        """A page at an old path that sends the reader to the new one (Q14): a meta refresh and
        a link, inside the frame so it names the commit like every page (R2)."""
        body = f'<p class="lead">This page moved to <a href="{esc(to)}">{esc(to)}</a>.</p>'
        head = f'<meta http-equiv="refresh" content="0; url={esc(to)}">'
        return self.page("Moved", body, renders=[], head=head)

    # -- hover cards (the Glossary, F04-T12) ---------------------------------------------------

    @staticmethod
    def hover(label: str, body: str, *, classes: str = "") -> str:
        """A term with its definition card: shown on hover or focus, plain CSS, no pointer
        needed (``tabindex``). ``label`` and ``body`` are HTML already escaped by the caller."""
        cls = f"term {classes}".strip()
        return (
            f'<span class="{esc(cls)}" tabindex="0">{label}'
            f'<span class="term-card" role="tooltip">{body}</span></span>'
        )

    def term(self, key: str, *, label: str | None = None, dot: bool = False) -> str:
        """A glossary word with its card; the legend's status chips carry a dot."""
        word, meaning, proto = self.words["by_key"][key]
        mark = self.dot(key) if dot else ""
        body = f'{esc(meaning)}<span class="proto">protocol: {esc(proto)}</span>'
        return self.hover(mark + esc(label or word), body)

    @staticmethod
    def dot(state: str) -> str:
        """A 9px status dot: filled for proved, an accent ring for open, a neutral ring else."""
        return f'<span class="dot dot-{esc(state)}"></span>'

    # -- what the site says about a problem (F04-T12) ----------------------------------------

    @staticmethod
    def node_state(nv: NodeView) -> str:
        """The row's word: proved, open (a claim could take it, F03-Q8) or the status itself."""
        if nv.status == "proved":
            return "proved"
        if nv.cause == CIRCULAR_CAUSE:
            return CIRCULAR_CAUSE  # F08-T17: off the frontier by a merged claim, whatever status
        if nv.status in CLAIMABLE_STATUSES:
            return "open"
        if nv.status == "blocked" and nv.cause == WITNESS_CAUSE:
            return NEEDS_WITNESS  # T17: the witness is the work (D-29), so this is not "blocked"
        return nv.status

    @staticmethod
    def state_label(state: str) -> str:
        return STATE_LABELS.get(state, state)

    @staticmethod
    def dot_state(state: str) -> str:
        """The dot a state wears: its own when the key has one (T14), the neutral ring else."""
        return state if state in (*DOTTED_KEYS, *LEGEND_EXTRA) else "blocked"

    def graph_legend(self, tv: TargetView) -> str:
        """The statement graph's key (F04-T14, Q16): the three base states, then every other
        status a statement in this graph has, each a glossary hover card with its dot."""
        present = {self.node_state(nv) for nv in tv.nodes.values()}
        keys = (*LEGEND_BASE, *(k for k in (NEEDS_WITNESS, *LEGEND_EXTRA) if k in present))
        return "".join(
            self.term(k, dot=True) for k in (*keys, *self.proof_legend(tv))
        ) + self.superseded_toggle(tv)

    @staticmethod
    def superseded_toggle(tv: TargetView) -> str:
        """F04-T33: a button that hides the superseded statements and their lines. It needs the
        page's script, so it is rendered hidden and the script shows it."""
        n = sum(1 for nv in tv.nodes.values() if nv.status == "superseded")
        if not n:
            return ""
        return (
            '<button type="button" class="chip dag-toggle" data-hide="superseded" '
            f'aria-pressed="false" data-shown-label="Show superseded ({n})" hidden>'
            f"Hide superseded ({n})</button>"
        )

    @staticmethod
    def proof_legend(tv: TargetView) -> tuple[str, ...]:
        """F18-T2, T6: the proof drawing's keys and the pointer's, each only when the drawing can
        show it."""
        drawn = {kind for _src, _dst, kind in dag.lines(tv.graph["nodes"])}
        # T33: the line kinds first, each when the drawing has one, proof or no proof.
        line_keys = ("depends-on",) if "edge" in drawn else ()
        if "edge use" in drawn:
            line_keys = (*line_keys, "use")
        pointed = ("proposed-for",) if dag.pointers(tv.graph["nodes"]) else ()
        if any(nv.annexes for nv in tv.nodes.values()):
            pointed = ("outline", *pointed)
        proofs = target_proofs(tv)
        if not proofs:
            return (*line_keys, *pointed)
        keys = [*line_keys, "on-proof", "not-needed", *pointed]
        if any(p.get("unmeasured") for p in proofs):
            keys.append("unmeasured")
        return tuple(keys)

    def proof_picker(self, tv: TargetView) -> str:
        """F18-T2 (R3): one entry per way the problem is proved, the first selected, and under it
        what the selected proof is drawn from. Nothing for a problem nobody has proved."""
        proofs = target_proofs(tv)
        if not proofs:
            return ""
        buttons, notes = [], []
        for k, p in enumerate(proofs):
            label = self.proof_label(k, p)
            pressed = "true" if k == 0 else "false"
            buttons.append(
                f'<button type="button" class="chip" data-proof="{k}" aria-pressed="{pressed}">'
                f"{esc(label)}</button>"
            )
            n = len(p["closure"])
            words = (
                f"Showing proof {k + 1} of {len(proofs)}: {n} statement{'' if n == 1 else 's'} "
                "highlighted, the rest of the record dimmed."
            )
            if p.get("unmeasured"):
                words += (
                    " Which statements its Lean term uses is not yet measured for "
                    + ", ".join(str(u) for u in p["unmeasured"])
                    + ", so those are drawn through what they declared."
                )
            hidden = "" if k == 0 else " hidden"
            read = (
                f' <a href="{esc(self.reading_path(tv.target_id, p))}">Read proof {k + 1} '
                "top-down, every step beside its Lean →</a>"
            )
            notes.append(f'<p class="proof-note" data-proof="{k}"{hidden}>{esc(words)}{read}</p>')
        lead = f"Proved {len(proofs)} way{'' if len(proofs) == 1 else 's'}:"
        return (
            f'<div class="proof-picker" role="group" aria-label="Proofs of this problem">'
            f'<span class="proof-picker-lead">{esc(lead)}</span>{"".join(buttons)}</div>'
            + "".join(notes)
        )

    @staticmethod
    def proof_label(k: int, p: dict[str, Any]) -> str:
        """``Proof 1 · root · by alice`` / ``Proof 2 · variant-x (resolves) · alternate · …``."""
        where = "root" if p.get("relation") is None else f"{p['node_id']} ({p['relation']})"
        kind = " · alternate" if p.get("kind") == "alternate" else ""
        who = f"by {p['submitter']}" if p.get("submitter") else "submitter not recorded"
        return f"Proof {k + 1} · {where}{kind} · {who}"

    @staticmethod
    def proof_marks(tv: TargetView) -> list[dag.ProofMarks]:
        """F18-T2: each proof's nodes and the edges its term follows. An edge from ``d`` to ``n``
        is on a proof when both are in its closure and ``d`` is among what ``n``'s proof used —
        this proof's own ``used`` at its own node, else ``n``'s first proof's — or, where that
        was not measured, among what ``n`` declared and uses."""
        rows = {str(n["node_id"]): n for n in tv.graph["nodes"]}
        out = []
        for p in target_proofs(tv):
            closure = frozenset(str(c) for c in p["closure"])
            edges: set[tuple[str, str]] = set()
            for node_id in closure:
                row = rows.get(node_id)
                if row is None:
                    continue
                own = [
                    r for r in row.get("proofs") or [] if r["artifact_hash"] == p["artifact_hash"]
                ]
                first = (own or row.get("proofs") or [None])[0]
                used = first.get("used") if first else None
                rests = used if used is not None else [*row["deps"], *(row.get("uses") or [])]
                edges.update((str(d), node_id) for d in rests if str(d) in closure)
            out.append(dag.ProofMarks(nodes=closure, edges=frozenset(edges)))
        return out

    def outlines_block(self, tv: TargetView, nv: NodeView) -> str:
        """F18-T4, T5 (R5, R7): the node's outlines (annexes, D-31) — each followed by the merged
        skeletons that cite it, with the holes they made, or not followed — and, for a stepped
        outline, the checklist of its steps against the nodes named after them. The title line
        and the summaries are contributor text: escaped and labelled (C9, D-28)."""
        if not nv.annexes:
            return ""
        decomps = list(nv.graph_entry.get("decompositions") or [])
        items = []
        for a in nv.annexes:
            digest = Path(a.path).stem
            title = next(
                (line.strip().lstrip("#").strip() for line in a.text.splitlines() if line.strip()),
                "untitled",
            )[:140]
            by = f" by {esc(a.author)}" if a.author else ""
            following = [d for d in decomps if d.get("annex") == digest]
            node_dir = Path(nv.statement_path).parent.as_posix()
            if following:
                runs = "; ".join(
                    self.file_link(f"{node_dir}/{d['partial']}", label=Path(d["partial"]).name)
                    + (
                        ": " + ", ".join(self.hole_link(tv, h) for h in d["holes"])
                        if d["holes"]
                        else ""
                    )
                    for d in following
                )
                state = f"followed by {runs}"
            else:
                state = "not followed by any merged decomposition"
            items.append(
                f'<li class="outline" data-annex="{esc(digest)}"><span class="untrusted-title">'
                f"{esc(title)}</span>{by} — {state}</li>"
            )
        out = (
            '<div class="panel-outlines"><span class="kicker">Outlines</span>'
            '<p class="cue">Untrusted contributor text (D-31): an outline is an informal '
            "argument, not a proof. The full text is on the statement&rsquo;s record page.</p>"
            f'<ul class="outlines">{"".join(items)}</ul>'
        )
        outline = nv.graph_entry.get("outline")
        if isinstance(outline, dict) and outline.get("steps"):
            steps = []
            for s in outline["steps"]:
                node = s.get("node")
                where = (
                    self.hole_link(tv, {"name": "", "node": node}, named=False)
                    if node
                    else "carried by the assembly"
                )
                steps.append(
                    f"<li><code>{esc(s['step'])}</code> "
                    f'<span class="untrusted-title">{esc(s["summary"])}</span> — {where}</li>'
                )
            out += (
                '<p class="cue">The stepped outline this statement&rsquo;s skeleton followed, '
                "step by step:</p>"
                f'<ol class="outline-steps">{"".join(steps)}</ol>'
                '<p class="cue">A matching name shows the structure was followed, not that the '
                "Lean says what the prose says (D-31 v3.26).</p>"
            )
        return out + "</div>"

    def hole_link(self, tv: TargetView, hole: dict[str, Any], *, named: bool = True) -> str:
        """A hole as the outline names it: its name, the node it became (an in-page link that
        selects the node's panel) and that node's state with its dot; a hole the tree does not
        hold says so."""
        name = f"<code>{esc(hole['name'])}</code> → " if named and hole.get("name") else ""
        node_id = hole.get("node")
        nv = tv.nodes.get(str(node_id)) if node_id else None
        if nv is None:
            return f"{name}no statement on the record"
        state = self.node_state(nv)
        return (
            f'{name}<a href="#node={esc(nv.node_id)}">{esc(nv.node_id)}</a> '
            f"({self.dot(self.dot_state(state))}{esc(self.state_label(state))})"
        )

    def proof_row(self, tv: TargetView, nv: NodeView) -> str:
        """F18-T2: the panel's line saying which proofs a statement is on, when there are any."""
        proofs = target_proofs(tv)
        if not proofs:
            return ""
        on = [str(k + 1) for k, p in enumerate(proofs) if nv.node_id in p["closure"]]
        if not on:
            words = "Not needed by any proof of this problem"
        else:
            noun = "proof" if len(on) == 1 else "proofs"
            words = f"On {noun} {', '.join(on)}" + (f" of {len(proofs)}" if len(proofs) > 1 else "")
        return f"<dt>proof</dt><dd>{esc(words)}</dd>"

    def open_count(self, tv: TargetView) -> int:
        """The statements the site invites work on: the frontier's workable set (T17)."""
        return sum(1 for n in tv.nodes.values() if self.node_state(n) in WORKABLE_STATES)

    @staticmethod
    def resolution(tv: TargetView) -> str:
        """F04-T31: how a resolved problem was resolved, by its root's status in ``graph.json``
        (proved, disproved, shown ill-posed). Only meaningful when the index says resolved."""
        root = tv.nodes.get(str(tv.index_entry.get("root") or ""))
        status = root.status if root is not None else "proved"
        return RESOLUTION_WORDS.get(status, "proved")

    @staticmethod
    def problem_status(tv: TargetView) -> str:
        """open · needs a steward, how a resolved problem was resolved (F04-T31), or the D-33
        word for a dormant or known result."""
        status = str(tv.index_entry["status"])
        if status == "resolved":
            return Renderer.resolution(tv)
        if status == "dormant":
            return "dormant"
        if status == "known-result":
            return "known result"
        reasons = [str(r) for r in tv.index_entry.get("not_claimable") or []]
        if intake.NO_STEWARD in reasons:
            return "needs a steward"
        return "open"

    def status_tag(self, tv: TargetView) -> str:
        """The status tag with its definition, and for a problem that refuses work, why."""
        status = self.problem_status(tv)
        body = esc(self.words["status_defs"].get(status, status))
        e = tv.index_entry
        if not e.get("claimable") and str(e["status"]) != "resolved":
            reasons = [esc(intake.explain(str(r))) for r in e.get("not_claimable") or []]
            why = "; ".join(reasons) or esc(NO_RECORD_WORDS)
            body += f'<span class="why">Not claimable: {why}.</span>'
        return self.hover(esc(status), body, classes="tag")

    def fidelity_tag(self, tv: TargetView) -> str:
        grade = str(tv.index_entry.get("fidelity") or "")
        key = FIDELITY_KEYS.get(grade)
        if key is None:  # a grade this generator has no word for: shown as itself
            return f'<span class="tag tag-outline">{esc(grade)}</span>'
        word, meaning, proto = self.words["by_key"][key]
        body = f'{esc(meaning)}<span class="proto">protocol: {esc(proto)}</span>'
        return self.hover(esc(word), body, classes="tag tag-outline")

    def stage_marks(self, tv: TargetView) -> str:
        """Proved · Explained · Written up: which of the three a problem has reached. A problem
        resolved against its statement says so in the first mark (F04-T31)."""
        digestion = tv.digestion or {}
        state = str(digestion.get("state") or "")
        resolved = str(tv.index_entry["status"]) == "resolved"
        first = self.resolution(tv).capitalize() if resolved else "Proved"
        reached = (
            (first, resolved),
            ("Explained", state in ("explained", "written-up")),
            ("Written up", state == "written-up"),
        )
        marks = "".join(
            f'<span class="stage {"on" if on else "off"}">'
            f"{self.dot('proved' if on else 'blocked')}{esc(label)}</span>"
            for label, on in reached
        )
        return f'<span class="stages">{marks}</span>'

    def steward_words(self, tv: TargetView) -> str:
        """ "Steward · name" (linked), or the cue for a problem that has none."""
        stewards = tv.stewards
        if stewards:
            names = ", ".join(self.steward_link(s) for s in stewards)
            return f'<span class="steward has">Steward · {names}</span>'
        if tv.calibration:
            return '<span class="steward">Calibration target, no steward needed</span>'
        if str(tv.index_entry["status"]) == "resolved":
            return '<span class="steward wanted">Steward wanted for write-up</span>'
        if tv.record is None or tv.record.get("track") != "open":
            return '<span class="steward">No steward: not an open problem</span>'
        return '<span class="steward wanted">Needs a steward</span>'

    def informal_words(self, tv: TargetView) -> str:
        """The informal statement, or the paraphrase that stands in for an unlicensed source."""
        if tv.record is None:
            return "No informal statement is recorded for this problem yet."
        text = tv.record.get("informal") or tv.record.get("paraphrase")
        if not text:
            return "No informal statement is recorded for this problem yet."
        return math(str(text), allowed_urls=self.cited)

    def source_line(self, tv: TargetView) -> str:
        """One line: where the statement came from, each source linked (its url is a validated
        record's, F11-Q11); the licence prose stays on the problem page."""
        if tv.record is None:
            return "No curated record yet."
        sources = tv.record.get("sources") or []
        if not sources:
            return self.origin_words(tv)
        parts = []
        for s in sources:
            kind, licence = esc(str(s.get("kind", "source"))), esc(str(s.get("licence", "")))
            parts.append(
                f'Imported from <a href="{esc(str(s["url"]))}">{kind}</a>'
                + (f" ({licence})" if licence else "")
            )
        forum = ((tv.record.get("prior_art") or {}).get("forum_url")) if tv.record else None
        if forum:
            shown = esc(str(forum).removeprefix("https://").removeprefix("www."))
            parts.append(f'<a href="{esc(str(forum))}">{shown}</a>')
        return " · ".join(parts)

    def origin_words(self, tv: TargetView) -> str:
        """T20: what a record with no ``sources`` list says of its statement. Only a statement
        the record calls the network's is called that; three live calibration targets name
        ``formal-conjectures`` in ``source`` and ``provenance`` and were called the network's
        own, because the page read the plural list alone."""
        record = tv.record or {}
        source = record.get("source") or {}
        stated = str((record.get("provenance") or {}).get("statement_source") or "")
        kind = str(source.get("kind") or stated)
        if not kind or kind == "network":
            return "The network's own statement, no external source."
        ref = str(source.get("ref") or "")
        if kind == "other" and ref:  # the schema's catch-all: the reference is the name
            words = f"Statement from {esc(ref)}"
        else:
            words = f"Statement from {esc(kind)}" + (f" ({esc(ref)})" if ref else "")
        if source.get("url"):  # a validated record's url, already in ``cited_urls``
            url = str(source["url"])
            shown = esc(url.removeprefix("https://").removeprefix("www."))
            words += f' · <a href="{esc(url)}">{shown}</a>'
        return words + "; the record lists no licensed source text."

    def node_role(self, tv: TargetView, nv: NodeView) -> str:
        if nv.node_id == tv.root:
            return "the tutorial statement" if nv.tutorial else "the problem's statement"
        if _DECL_RE.search(nv.statement):
            return "definition"
        e = nv.graph_entry
        if e.get("origin") == "variant":
            return RELATION_ROLES.get(str(e.get("relation")), "a variant")
        return ORIGIN_ROLES.get(str(e.get("origin")), str(e.get("origin")))

    def state_hover(self, nv: NodeView) -> str:
        """The row's status dot with the state's definition, and a blocked node's cause."""
        state = self.node_state(nv)
        if state in ("proved", *WORKABLE_STATES) or state in LEGEND_EXTRA:
            _word, meaning, proto = self.words["by_key"][state]
            body = f'{esc(meaning)}<span class="proto">protocol: {esc(proto)}</span>'
        else:
            words = status_words(nv.status, nv.cause)
            meaning = self.words["by_key"]["blocked"][1] if nv.status == "blocked" else ""
            body = f"{esc(words)}. {esc(meaning)}".strip()
        return self.hover(self.dot(self.dot_state(state)), body, classes="dot-term")

    @staticmethod
    def attempts_words(nv: NodeView) -> str:
        n = nv.attempts.count
        return f"{n} attempt{'' if n == 1 else 's'}"

    def node_action(self, tv: TargetView, nv: NodeView) -> str:
        state = self.node_state(nv)
        href = esc(self.node_path(tv.target_id, nv.node_id))
        if state == "open":
            return f'<a class="act act-open" href="{href}">Work on this →</a>'
        if state == NEEDS_WITNESS:
            return f'<a class="act act-open" href="{href}">Supply a witness →</a>'
        if state == "proved":
            return f'<a class="act act-proved" href="{href}">View proof →</a>'
        return f'<a class="act act-blocked" href="{href}">Blocked</a>'

    def home(self) -> str:
        site = self.site
        targets = [tv for _tid, tv in sorted(site.targets.items())]
        # F15-R10 (D-36 v3.17): explanation coverage leads — proved nodes carrying a valid
        # signed explainer, of all proved nodes, summed over every target's digestion counts.
        proved = sum(int((tv.digestion or {}).get("proved", 0)) for tv in targets)
        explained = sum(int((tv.digestion or {}).get("proved_explained", 0)) for tv in targets)
        open_statements = sum(self.open_count(tv) for tv in targets)
        stewards = len({str(s["login"]) for tv in targets for s in tv.stewards})
        unproved = [tv for tv in targets if str(tv.index_entry["status"]) != "resolved"]
        unexplained = [
            tv
            for tv in targets
            if str(tv.index_entry["status"]) == "resolved"
            and str((tv.digestion or {}).get("state") or "") not in ("explained", "written-up")
        ]
        rows = "".join(self.open_now_row(tv) for tv in (*unproved, *unexplained)[:5])
        if not rows:
            rows = '<p class="cue">No problems are listed yet.</p>'
        body = _template("home.html").substitute(
            explained=explained,
            proved=proved,
            problems=len(targets),
            open_statements=open_statements,
            stewards=stewards,
            open_now=rows,
            all_problems=len(targets),
            statement_term=self.term("statement", label="statement"),
            steward_term=self.term("steward", label="steward"),
            proposal_url=esc(self.proposal_url),
        )
        return self.page(
            SITE_NAME,
            body,
            renders=["targets/index.json", "frontier.json"],
            path="/",
            head=MATH_HEAD,
            script=MATH_SCRIPTS,
        )

    def open_now_row(self, tv: TargetView) -> str:
        n = self.open_count(tv)
        open_words = f"{n} open statement{'' if n == 1 else 's'}" if n else "no open statements"
        return (
            '<div class="open-row">'
            f'<a class="id" href="{esc(self.target_path(tv.target_id))}">{esc(tv.target_id)}</a>'
            f'<span class="informal">{self.informal_words(tv)}</span>'
            f'<span class="open-count">{esc(open_words)}</span>'
            f"{self.steward_words(tv)}</div>"
        )

    # -- the Problems page: Targets and Frontier merged (F04-T12, Q14) -------------------------

    def problems(self) -> str:
        targets = [tv for _tid, tv in sorted(self.site.targets.items())]
        cards = "".join(self.problem_card(tv) for tv in targets)
        if not cards:
            cards = '<p class="cue">No problems are listed yet.</p>'
        legend = "".join(self.term(k, dot=k in DOTTED_KEYS) for k in LEGEND_KEYS)
        legend_list = "".join(
            f"<dt>{esc(self.words['by_key'][k][0])}</dt><dd>{esc(self.words['by_key'][k][1])}</dd>"
            for k in LEGEND_KEYS
        )
        open_statements = sum(self.open_count(tv) for tv in targets)
        # F04-T31: the "Proved" segment filters ``data-status="proved"``; count the same set.
        proved = sum(1 for tv in targets if self.problem_status(tv) == "proved")
        body = _template("problems.html").substitute(
            cards=cards,
            legend=legend,
            legend_list=legend_list,
            total=len(targets),
            open_statements=open_statements,
            proved=proved,
            claims_note=self.claims_note(),
        )
        return self.page(
            "Problems",
            body,
            renders=["targets/index.json", "frontier.json"],
            path=PROBLEMS_PATH,
            head=MATH_HEAD,
            script=MATH_SCRIPTS + '<script src="/problems.js"></script>',
        )

    def problem_card(self, tv: TargetView) -> str:
        tid = tv.target_id
        status = self.problem_status(tv)
        rows = "".join(self.statement_row(tv, nv) for nv in self.ordered_nodes(tv))
        resolved = str(tv.index_entry["status"]) == "resolved"
        action = "View the graph →" if resolved else "View problem →"
        return _template("problem-card.html").substitute(
            target_id=esc(tid),
            href=esc(self.target_path(tid)),
            status=esc(status),
            open_count=self.open_count(tv),
            status_tag=self.status_tag(tv),
            fidelity_tag=self.fidelity_tag(tv),
            informal=self.informal_words(tv),
            source=self.source_line(tv),
            stages=self.stage_marks(tv),
            steward=self.steward_words(tv),
            action=esc(action),
            rows=rows,
        )

    @staticmethod
    def ordered_nodes(tv: TargetView) -> list[NodeView]:
        """The problem's own statement first, then the rest by id."""
        root = tv.nodes[tv.root]
        return [root, *(nv for nid, nv in sorted(tv.nodes.items()) if nid != tv.root)]

    def statement_row(self, tv: TargetView, nv: NodeView) -> str:
        state = self.node_state(nv)
        return _template("problem-row.html").substitute(
            state=esc(state),
            workable="1" if state in WORKABLE_STATES else "0",
            dot=self.state_hover(nv),
            node=self.node_link(tv.target_id, nv.node_id),
            role=esc(self.node_role(tv, nv)),
            state_word=esc(self.state_label(state)),
            attempts=esc(self.attempts_words(nv)),
            action=self.node_action(tv, nv),
            # F20-T8 (R13): a statement's words, first sentence; a root's are the card's own.
            gloss="" if nv.node_id == tv.root else self.gloss_line(tv, nv.node_id),
        )

    # -- the About page (F04-T12): the long argument, moved off the home page -----------------

    def about(self) -> str:
        rules = "".join(
            f'<div class="rule-item"><span class="kicker">0{i}</span><h4>{esc(title)}</h4>'
            f"<p>{esc(words)}</p></div>"
            for i, (title, words) in enumerate(self.words["rules"], start=1)
        )
        body = _template("about.html").substitute(
            rules=rules,
            steward_sentence=esc(self.words["about_steward"]),
            commitment=esc(steward.COMMITMENT),
            proposal_url=esc(self.proposal_url),
        )
        return self.page("Why this exists", body, renders=[], path="/about/")

    # --- F11-R10: why a listed target cannot be claimed, and under what licence it is quoted ---

    def informal_line(self, tv: TargetView) -> str:
        """The informal statement, or the network's own paraphrase in its place.

        A source that states no licence has not licensed its wording, so intake refuses to store
        it at all (F11-R10) and there is simply nothing here to reproduce — the paraphrase and
        the citation below are what the page has, which is the honest thing to show.
        """
        if tv.record is None:
            return "No informal statement is recorded for this target yet (D-6 intake, F11)."
        informal = tv.record.get("informal")
        if informal:
            return math(str(informal), allowed_urls=self.cited)
        paraphrase = tv.record.get("paraphrase")
        if paraphrase:
            return (
                f"{math(str(paraphrase), allowed_urls=self.cited)} "
                '<span class="note">(the network\'s own paraphrase: the '
                "source states no licence, so its wording is cited rather than reproduced)</span>"
            )
        return "No informal statement is recorded for this target yet (D-6 intake, F11)."

    def why_not_claimable(self, tv: TargetView, *, detail: bool = True) -> str:
        """R10: the reason a listed target is not claimable, named rather than implied. The node
        page (F04-T10) shows the reasons without the target's signatures and posting."""
        e = tv.index_entry
        if e.get("claimable"):
            return ""
        reasons = [str(r) for r in e.get("not_claimable") or []]
        if not reasons:
            return (
                '<p class="why-not">Not claimable: this target has no curated intake record '
                "(D-6), so nothing may be claimed under it.</p>"
            )
        items = "".join(f"<li>{esc(intake.explain(r))}</li>" for r in reasons)
        if not detail:
            return f'<p class="why-not">Not claimable, because:</p><ul class="why-not">{items}</ul>'
        posted = e.get("posting")
        where = (
            f' Posted at <a href="{esc(str(posted["url"]))}">{esc(str(posted["venue"]))}</a> '
            f"on {esc(str(posted['date']))}."
            if posted
            else ""
        )
        signed = "; ".join(
            f"{esc(str(s['subject']))} {esc(str(s['grade']))}"
            f" ({s['signature_count']} signature{'' if s['signature_count'] == 1 else 's'}"
            + (f": {esc(', '.join(str(n) for n in s['signers']))}" if s["signers"] else "")
            + ")"
            for s in e.get("subjects") or []
        )
        signatures = (
            f'<p class="signatures">Fidelity by subject: {signed}.{where}</p>' if signed else ""
        )
        return (
            '<p class="why-not">Not claimable, because:</p>'
            f'<ul class="why-not">{items}</ul>{signatures}'
        )

    def target_claimable(self, tv: TargetView) -> str:
        """F14-R10: the target page says in words whether it can be claimed, and if not, why."""
        if self.is_tutorial(tv):
            # F04-T23: it read "proved" and "open for work" at once. Both are true of the
            # tutorial and mean something else there, so the page says what it is for.
            guide = f'<a href="{GUIDE_HREF}">Start here →</a>'
            return (
                '<p class="claimable">The tutorial. Its statement reads proved and may be proved '
                "again by anyone: that is how you check your setup and, with no account, earn a "
                f"write token (D-19, D-27). {guide}</p>"
            )
        if tv.index_entry.get("claimable"):
            guide = f'<a href="{GUIDE_HREF}">How to contribute →</a>'
            if self.open_count(tv):
                return f'<p class="claimable">This problem is open for work. {guide}</p>'
            return (
                '<p class="claimable">This problem accepts work, but no statement of it is '
                f"workable right now: each one waits on another. {guide}</p>"
            )
        if str(tv.index_entry["status"]) == "resolved":
            # D-33 v3.20 (F04-T22): resolved is a fact about the root. What was proposed beneath
            # it is open work, and the page says how much rather than closing the door on it.
            # F04-T31: and how it was resolved, since a counterexample resolves it too.
            word = self.resolution(tv)
            head = f"{word.capitalize()}: {RESOLUTION_RECORD[word]}"
            beneath = self.open_count(tv) if self.open_beneath(tv) else 0
            if beneath:
                guide = f'<a href="{GUIDE_HREF}">How to contribute →</a>'
                noun = "statement" if beneath == 1 else "statements"
                return (
                    f'<p class="claimable">{esc(head)}, so the problem\'s own statement is '
                    f"closed. {beneath} {noun} proposed beneath it "
                    f"{'is' if beneath == 1 else 'are'} open for work. {guide}</p>"
                )
            return f'<p class="claimable">{esc(head)}, so its statement no longer accepts work.</p>'
        return self.why_not_claimable(tv)

    @staticmethod
    def open_beneath(tv: TargetView) -> bool:
        """The gate's own rule (``products.open_beneath``), so the page and the frontier cannot
        disagree about whether the statements under a settled root take work."""
        reasons = tuple(str(r) for r in tv.index_entry.get("not_claimable") or [])
        return products.open_beneath(reasons)

    def sources_block(self, tv: TargetView) -> str:
        """R10: where the statement came from, its attribution, and its licence."""
        if tv.record is None:
            return ""
        sources = tv.record.get("sources") or []
        if not sources:
            return f'<p class="sources">{self.origin_words(tv)}</p>'
        items = "".join(
            f'<li><a href="{esc(str(s["url"]))}">{esc(str(s["url"]))}</a> &mdash; '
            f"{esc(str(s['attribution']))}; licence {esc(str(s['licence']))}; "
            f"{esc(str(s['quote_policy']))} only</li>"
            for s in sources
        )
        return (
            f'<p class="sources">Sources and licences (D-10):</p><ul class="sources">{items}</ul>'
        )

    def qa_block(self, tv: TargetView) -> str:
        """R10: the statement-QA summary, so a reader sees what was checked (D-9 v3.12)."""
        if tv.record is None:
            return ""
        summary = tv.record.get("qa_summary")
        if not summary:
            return '<p class="qa">No statement-QA pass is recorded yet (D-9 v3.12).</p>'
        return f'<p class="qa">Statement QA (D-9 v3.12): {esc(str(summary))}</p>'

    def target(self, tv: TargetView) -> str:
        """The problem page (F04-T12): header, steward card, the statement graph with one panel
        per statement, then the record's detail sections as before."""
        tid = tv.target_id
        href = {nid: self.node_path(tid, nid) for nid in tv.nodes}
        # T17: the pill wears the state the key and the rows name, not the bare graph status;
        # T26: so a circular statement is drawn circular, never with the open ring of its status.
        drawn = [
            {**n, "status": NEEDS_WITNESS}
            if n.get("status") == "blocked" and n.get("cause") == WITNESS_CAUSE
            else {**n, "status": CIRCULAR_CAUSE}
            if n.get("status") != "proved" and n.get("cause") == CIRCULAR_CAUSE
            else n
            for n in tv.graph["nodes"]
        ]
        outlines = {nid: len(nv.annexes) for nid, nv in tv.nodes.items() if nv.annexes}
        svg = dag.svg(
            drawn,
            href=href,
            proofs=self.proof_marks(tv),
            outlines=outlines,
            root=tv.root,
            prefix=tid,
        )
        panels = "".join(self.statement_panel(tv, nv) for nv in self.ordered_nodes(tv))
        n = len(tv.nodes)
        if tv.approaches:
            approaches = (
                "<ul>"
                + "".join(
                    f"<li>{self.file_link(f'targets/{tid}/approaches/{name}')}</li>"
                    for name in tv.approaches
                )
                + "</ul>"
            )
        else:
            approaches = "<p>No approach records yet (D-14).</p>"
        note = (
            self.untrusted_block(
                "untrusted",
                Prose(path=f"targets/{tid}/note.md", text=tv.note),
                what="state-of-the-problem note (D-32)",
            )
            if tv.note is not None
            else "<p>No state-of-the-problem note yet (D-32).</p>"
        )
        e = tv.index_entry
        title = str(tv.record.get("title") or "") if tv.record else ""
        resolved = str(tv.index_entry["status"]) == "resolved"
        body = _template("target.html").substitute(
            # F04-T31: the section names the first stage as the problem reached it.
            digestion_heading=esc(self.resolution(tv).capitalize() if resolved else "Proved"),
            target_id=esc(tid),
            status_tag=self.status_tag(tv),
            fidelity_tag=self.fidelity_tag(tv),
            informal=self.informal_words(tv),
            provenance=(f"{esc(title)}. " if title else "") + self.source_line(tv),
            stages=self.stage_marks(tv),
            claimable=self.target_claimable(tv),
            calibration=self.calibration_label(tv),
            steward_card=self.steward_card(tv),
            count_words=esc(f"{n} statement{'' if n == 1 else 's'}"),
            legend=self.graph_legend(tv),
            proof_picker=self.proof_picker(tv),
            dag=svg,
            panels=panels,
            digestion=self.digestion_section(tv),
            stewards=self.stewards_section(tv),
            sources=self.sources_block(tv),
            qa_block=self.qa_block(tv),
            informal_full=self.informal_line(tv),
            approaches=approaches,
            definitions=self.definitions_section(tv),
            note=note,
            qa=self.qa_section(tv),
            review=esc(self.review_sentence(tv)),
            graph_link=self.file_link(f"targets/{tid}/graph.json"),
            fast_check=esc(self.fast_check(e.get("mathlib_sha"))),
        )
        # F20-T8: the panels' glosses and the definition modules' are rendered here too.
        glossed = [p for nid in tv.nodes for p in self.gloss_renders(tv, nid, kinds=("statement",))]
        renders = [
            f"targets/{tid}/graph.json",
            *(f.path for f in tv.definitions),
            *self.gloss_renders(tv, None),
            *glossed,
        ]
        return self.page(
            tid,
            body,
            renders=list(dict.fromkeys(renders)),
            path=PROBLEMS_PATH,
            head=MATH_HEAD,
            script=MATH_SCRIPTS + '<script src="/problem.js"></script>',
        )

    def definitions_section(self, tv: TargetView) -> str:
        """F20-T8 (R13): each definition module of the problem, its Lean and its gloss beside it.
        Nothing for a problem with none, so such a page is unchanged."""
        if not tv.definitions:
            return ""
        prefix = f"targets/{tv.target_id}/defs/"
        blocks = []
        for f in tv.definitions:
            module = f.path.removeprefix(prefix)
            blocks.append(
                self.lean_artifact(
                    f,
                    what=module,
                    provenance="a definition module the problem&rsquo;s statements import, "
                    "content-hashed and changed only by a curator&rsquo;s revision (D-3, D-8).",
                    label=self.provenance(
                        "definition", "shared by every statement of this problem (D-3 defs/)."
                    ),
                    block="definition",
                    pre_class="definition",
                )
                + self.gloss_slot(tv, "definition", f"defs/{module}", module=module)
            )
        return "<h2>Definitions</h2>\n" + "".join(blocks)

    @staticmethod
    def is_tutorial(tv: TargetView) -> bool:
        """The graph's tutorial target (D-27): its root is the tutorial statement."""
        root = tv.nodes.get(str(tv.index_entry.get("root") or ""))
        return bool(root is not None and root.tutorial)

    def steward_card(self, tv: TargetView) -> str:
        """The problem page's steward card: the names, or why there is none and how to be it."""
        stewards = tv.stewards
        if self.is_tutorial(tv):
            # F04-T23: the tutorial read "proved but not explained … Become its steward" (agent
            # A, 2026-09-19). It is off the ledger and nobody writes it up (D-27).
            names, words, button = (
                "None needed",
                "The tutorial: a statement kept for checking a setup end to end and for earning "
                "a write token. It is off the ledger and has no steward (D-27).",
                "",
            )
        elif stewards:
            names = ", ".join(self.steward_link(s) for s in stewards)
            since = ", ".join(
                f"{esc(str(s['login']))} since {esc(str(s['since']))}" for s in stewards
            )
            words = (
                "Committed to understand and write up whatever the network produces here, and "
                f"to sign the explainer of the proof that closes it. {since}."
            )
            button = ""
        elif tv.calibration:
            names, words, button = (
                "None needed",
                "A calibration target: a known result taken in to exercise the pipeline. It "
                "counts toward no open-problem claim and has no steward.",
                "",
            )
        elif str(tv.index_entry["status"]) == "resolved":
            names, words = (
                "None yet",
                f"This problem is {self.resolution(tv)} but not explained. It waits for a "
                "mathematician to commit to writing it up and to sign the explainer.",
            )
            button = '<a class="btn btn-secondary" href="/docs/#stewards">Become its steward</a>'
        elif tv.record is None or tv.record.get("track") != "open":
            names, words, button = "None", "Not an open problem, so it has no steward.", ""
        else:
            names, words = (
                "None yet",
                "A steward is a mathematician who commits to understand and write up whatever "
                "the network produces on this problem, with no deadline. Their name goes here, "
                "and the write-up is theirs.",
            )
            button = '<a class="btn btn-secondary" href="/docs/#stewards">Become its steward</a>'
        return (
            '<aside class="card steward-card"><span class="kicker">Steward</span>'
            f'<span class="names">{names}</span><p>{words}</p>{button}</aside>'
        )

    def revision_note(self, tid: str, nv: NodeView, *, in_page: bool) -> str:
        """F04-T18 (Q20): a superseded statement names its replacement and the curator's reason;
        the replacement names what it revises. On the problem page the link selects the other
        statement's panel (``#node=``); on a statement's own page it goes to the other's page.
        An id that is not a statement of this problem is shown, never linked (R13)."""
        target = self.site.targets.get(tid)
        known = target.nodes if target is not None else {}

        def link(nid: str) -> str:
            if nid not in known:
                return f"<code>{esc(nid)}</code>"
            href = f"#node={nid}" if in_page else self.node_path(tid, nid)
            return f'<a href="{esc(href)}">{esc(nid)}</a>'

        parts: list[str] = []
        if nv.status == "superseded":
            if nv.superseded_by:
                parts.append(
                    f"Superseded by {link(nv.superseded_by)}. Work continues on the replacement; "
                    "this statement is kept for its history (D-8)."
                )
            if nv.superseded_cause:
                parts.append(
                    f'<span class="why">The curator\'s record: {esc(nv.superseded_cause)}</span>'
                )
        if nv.supersedes:
            parts.append(f"Revises {link(nv.supersedes)}, which it replaced (D-8).")
        note = f'<p class="revision-note">{" ".join(parts)}</p>' if parts else ""
        return note + self.circular_below_note(nv)

    def defect_claims_note(self, nv: NodeView) -> str:
        """F08-T36 (D-16 v3.28): every open defect claim against the statement — its class, its
        file at the rendered commit and the words "claim open"; "disputed" beside the one a
        curator's record accepts for adjudication (D-18 v3.28). A filed claim blocks nothing, so
        the page says so; a withdrawn claim is not open and is not shown. Nothing at all for a
        statement with no open claim, so such a page is unchanged."""
        claims = nv.open_claims
        if not claims:
            return ""
        node_dir = f"targets/{nv.target_id}/nodes/{nv.node_id}"
        items = []
        for c in claims:
            accepted = (
                " · <strong>disputed</strong>: a curator has accepted it for adjudication, so "
                "this statement is off the frontier and takes no new claim (D-18)"
                if c.get("accepted")
                else ""
            )
            link = self.file_link(f"{node_dir}/{c.get('file', '')}")
            items.append(
                f"<li><code>{esc(str(c.get('class', '')))}</code> · claim open · "
                f"{link}{accepted}</li>"
            )
        one = len(claims) == 1
        return (
            '<div class="defect-claims"><p>'
            f"{'A defect claim is' if one else f'{len(claims)} defect claims are'} open against "
            "this statement (D-16). A claim says the statement may not mean what it should; it "
            "blocks nothing until a curator accepts it.</p>"
            f"<ul>{''.join(items)}</ul></div>"
        )

    def circular_below_note(self, nv: NodeView) -> str:
        """F08-T20 (D-12 v3.22): a statement a circularity claim circles back to stays open and
        claimable — it is the problem, and the claim says only that one route to it made no
        progress. Its page and its panel name each claim and invite the other two routes."""
        if not nv.circular_below or nv.status in ("proved", "superseded"):
            return ""
        claims = ", ".join(self.file_link(c) for c in nv.circular_below)
        one = len(nv.circular_below) == 1
        return (
            '<p class="circular-note">'
            f"{'A merged circularity claim shows' if one else 'Merged circularity claims show'} "
            "that a statement meant to reduce this one implies it, so a proof of it would be a "
            f"proof of this one and that decomposition made no progress (D-12, D-16): {claims}. "
            "This statement stays open: a direct proof, or a different decomposition, is "
            "welcome.</p>"
        )

    def closing_note(self, tv: TargetView, nv: NodeView) -> str:
        """The "closable through its holes" line (2026-09-21), on a node that has holes and is
        not settled. Two outside agents worked a target's holes for a session before finding, by
        experiment, that the root could not be assembled from them. Since F00-T10 it can: the
        holes' theorems reach a proof through the node's own Context, which a statement written
        since 2026-09-20 imports and an older one's proof may import itself. The panel says
        which, with the line to add. ``layout.imports_own_context`` decides, as it does for the
        MCP's ``get_node``; a hole is what the graph calls one (``graph.is_hole_of``)."""
        if nv.status in ("proved", "superseded"):
            return ""
        holes = [
            other
            for other, ov in tv.nodes.items()
            if graphmod.is_hole_of(nv.node_id, other, str(ov.graph_entry.get("origin")))
            and ov.status != "superseded"
        ]
        if not holes:
            return ""
        lead = "Closable through its holes: once they are proved, a proof of this statement may "
        if layout.imports_own_context(nv.node_id, nv.statement):
            words = lead + "name their theorems, which its Context already carries."
        else:
            line = f"import {layout.node_module(nv.node_id, 'Context')}"
            words = (
                lead + "name their theorems. This statement predates the Context import, so the "
                f"proof adds <code>{esc(line)}</code> directly after the statement's last "
                "import: the one import the gate allows a proof to add."
            )
        return f'<p class="closing-note">{words} A direct proof is accepted at any time.</p>'

    def statement_panel(self, tv: TargetView, nv: NodeView) -> str:
        """One "Selected statement" panel per node; the script shows the selected one and the
        page without it shows the root's. Hashes, origin, pin and files sit behind a toggle."""
        tid, nid = tv.target_id, nv.node_id
        e = nv.graph_entry
        state = self.node_state(nv)
        words = status_words(nv.status, nv.cause)
        note = esc(f"{self.node_role(tv, nv).capitalize()}; {words}.")
        if state == "proved" and e.get("proof_commit"):
            note += esc(f" Proof merged in {str(e['proof_commit'])[:12]}.")
        note += self.pertinence(e)
        files = [self.file_link(nv.statement_path, label="Statement.lean ↗")]
        if nv.attestation_path:
            files.append(self.file_link(nv.attestation_path, label="attestation ↗"))
        if nv.proof_path and state == "proved":
            files.append(self.file_link(nv.proof_path, label="Proof.lean ↗"))
        href = esc(self.node_path(tid, nid))
        if state == "open":
            action = (
                f'<a class="btn btn-primary btn-block" href="{href}">Work on this statement</a>'
            )
        elif state == NEEDS_WITNESS:
            action = f'<a class="btn btn-primary btn-block" href="{href}">Supply a witness →</a>'
        elif state == "proved":
            action = f'<a class="btn btn-primary btn-block" href="{href}">View the proof →</a>'
        else:
            action = f'<a class="btn btn-secondary btn-block" href="{href}">View the record →</a>'
        origin = str(e.get("origin", "")) + (f" ({e['relation']})" if e.get("relation") else "")
        return _template("statement-panel.html").substitute(
            node_id=esc(nid),
            hidden="" if nid == tv.root else " hidden",
            state=esc(state),
            state_word=esc(self.state_label(state)),
            dot=self.dot(self.dot_state(state)),
            attempts=esc(self.attempts_words(nv)),
            proof_row=self.proof_row(tv, nv),
            note=note,
            revision=self.revision_note(tid, nv, in_page=True),
            closing=self.closing_note(tv, nv),
            outlines=self.outlines_block(tv, nv),
            statement=esc(declaration_only(nv.statement)),
            glosses=self.gloss_slot(
                tv, "statement", f"nodes/{nid}/Statement.lean", node=nid, ids=f"p-{nid}-"
            ),
            hash=esc(str(e.get("statement_hash", ""))[:12]),
            origin=esc(origin),
            mathlib=esc(str(tv.index_entry.get("mathlib_sha") or "")[:12] or "Lean core only"),
            files=" · ".join(files),
            action=action,
        )

    # --- F15-R10: stewards, the digestion state, the calibration label ----------------------------

    def status_words(self, tv: TargetView) -> str:
        """The status, and for a resolved target its digestion state beside it: "resolved —
        undigested" until the state moves (D-33 v3.17)."""
        status = str(tv.index_entry["status"])
        digestion = tv.digestion
        if status == "resolved" and digestion and digestion.get("state"):
            return f"{status} — {digestion['state']}"
        return status

    def digestion_words(self, tv: TargetView) -> str:
        """The D-10 report-back sentence for a resolved target, or "" for any other status."""
        digestion = tv.digestion
        state = str(digestion.get("state") or "") if digestion else ""
        return DIGESTION_WORDS.get(state, "")

    def calibration_label(self, tv: TargetView) -> str:
        if not tv.calibration:
            return ""
        return (
            '<p class="flag calibration">A calibration target: a result already known, taken in '
            "on the formalization track to exercise the pipeline (Stages v3.17). It counts toward "
            "no open-problem claim and needs no steward.</p>"
        )

    def steward_link(self, s: dict[str, Any]) -> str:
        """A steward's name linked to the identity link the validated record carries; the url is
        on the allowlist because the record validated (F15 §7, F11-Q11)."""
        return f'<a href="{esc(str(s["link"]))}">{esc(str(s["name"]))}</a>'

    def stewards_line(self, tv: TargetView) -> str:
        stewards = tv.stewards
        if not stewards:
            return '<a href="/docs/#stewards">none yet</a>'
        return ", ".join(f"{self.steward_link(s)} (since {esc(str(s['since']))})" for s in stewards)

    def stewards_section(self, tv: TargetView) -> str:
        """The target page's stewards: each by name and link with the date they committed, or
        one cue saying what a steward commits to and receives, linked to the Docs section."""
        stewards = tv.stewards
        if stewards:
            items = "".join(
                f"<li>{self.steward_link(s)} (<code>{esc(str(s['login']))}</code>), committed "
                f"{esc(str(s['since']))}</li>"
                for s in stewards
            )
            return f'<ul class="stewards">{items}</ul>'
        if tv.record is None or tv.record.get("track") != "open" or tv.calibration:
            return "<p>No stewards: this target is not an open problem (D-6 v3.17).</p>"
        return (
            '<p class="cue">No steward yet. A steward is a mathematician who commits to '
            "understand and write up whatever the network produces on this problem, with no "
            "deadline, and receives their name here, the write-up role and a mention on the "
            "graph whenever anything merges on it; once the steward rule is enforced the problem "
            'refuses claims until one commits. <a href="/docs/#stewards">What a steward commits '
            "to and receives.</a></p>"
        )

    def digestion_section(self, tv: TargetView) -> str:
        """For a resolved target: the digestion state, the report-back sentence D-10 carries,
        the closure counts and the write-up records; for any other status, one line."""
        digestion = tv.digestion
        if not digestion or not digestion.get("state"):
            return "<p>Not resolved, so no digestion state yet (D-33 v3.17).</p>"
        state = str(digestion["state"])
        # F04-T31: a counterexample or vacuity certificate closes the root too (F03-T17), and its
        # closure counts settled nodes, not only proved ones.
        word = self.resolution(tv)
        settled = "proved" if word == "proved" else "settled"
        parts = [
            f'<p class="lead">Resolved — <strong>{esc(state)}</strong>. Reported back as: '
            f"<em>{esc(DIGESTION_WORDS[state])}</em> (D-10 v3.17).</p>",
            f"<p>{esc(str(digestion['closure_explained']))} of "
            f"{esc(str(digestion['closure']))} {settled} nodes in the closing "
            f"{RESOLUTION_ARTIFACT[word]}'s dependency closure carry a signed explainer.</p>",
        ]
        if tv.writeups:
            items = "".join(
                f'<li>{esc(str(w["kind"]))}: <a href="{esc(str(w["url"]))}">'
                f"{esc(str(w['title']))}</a>, {esc(str(w['signer']))}, {esc(str(w['date']))}</li>"
                for w in tv.writeups
            )
            parts.append(f'<ul class="writeups">{items}</ul>')
        else:
            parts.append("<p>No paper or note recorded yet (D-32).</p>")
        return "".join(parts)

    def vouched_lines(self, nv: NodeView) -> str:
        """R10: above the unverified label, one line per valid signature."""
        return "".join(
            f'<p class="vouched">Explained and vouched for by <strong>{esc(v.signer)}</strong>, '
            f"{esc(v.date)} (<em>I can explain this proof without the tool that produced it</em>; "
            f"D-3 v3.17). Rendered from {self.file_link(v.path)}.</p>"
            for v in nv.signatures
        )

    # --- F14-R10: what a proof needs, and the evidence behind it ----------------------------------

    @staticmethod
    def review_sentence(tv: TargetView) -> str:
        """One sentence: whether a proof of this root merges on the gate or waits for a person, and
        why (F14-R5, R9). Empty for an index version older than v5, which does not say."""
        e = tv.index_entry
        basis = e.get("step9")
        if e.get("status") == "resolved":
            # F04-T32: the root is settled, so no proof of it is asked step 9 any more.
            return (
                "This problem's statement is settled: a further proof of it merges as an "
                "alternate, which no person reviews (D-3 v3.13), and nothing beneath it waits for "
                "anyone either (v3.20)."
            )
        if basis == "certificate":
            return (
                "A proof of this statement merges on the gate: the root carries a non-author's "
                "fidelity certificate (D-4 step 9)."
            )
        if basis == "evidence":
            summary = e.get("statement_evidence") or {}
            return (
                "A proof of this statement merges on the gate without a human reviewer: its "
                f"recorded catalog evidence scores {summary.get('score')} "
                f"({summary.get('letter')}), at or above the high grade (D-4 step 9, F14)."
            )
        if basis == "review":
            return (
                "A proof of this statement waits for a non-author's approving review on its pull "
                "request: the root has no counting signature and no catalog evidence at the high "
                "grade (D-4 step 9). Nothing beneath it waits for anyone: a hole, a crux, a "
                "skeleton or a variant merges on the gate (v3.20)."
            )
        if basis == "calibration":
            return (
                "Everything on this problem merges on the gate, its root included: it is a "
                "calibration target, a result already in the literature, and a proof of it "
                "settles no open conjecture (D-4 step 9, v3.20)."
            )
        return ""

    def evidence_section(self, tv: TargetView) -> str:
        """F14-R10: the catalog evidence for the root — score, letter and the reasons that sum to
        it, the registry history, misformalization issues and hazards — and each second
        formalization with its equivalence verdict. Every value from the graph is escaped."""
        e = tv.index_entry
        if "statement_evidence" not in e:  # an index older than v5
            return ""
        parts: list[str] = []
        doc = tv.evidence
        summary = e.get("statement_evidence")
        if doc is None or summary is None:
            parts.append(
                '<p class="evidence">No catalog evidence is recorded for this root (F14-R3).</p>'
            )
        else:
            catalog = doc["catalog"]
            standing = (
                "pinned to the root as it stands"
                if summary.get("current")
                else "recorded against an earlier statement, so it counts for nothing now"
            )
            reasons = "".join(f"<li>{esc(str(r))}</li>" for r in catalog.get("reasons") or [])
            history = doc.get("registry_history")
            history_line = (
                f" In the registry since {esc(str(history['first']))}, last changed "
                f"{esc(str(history['last']))}, {esc(str(history['commits']))} commits."
                if history
                else ""
            )
            issues = doc.get("misformalization") or []
            issue_line = (
                "No misformalization issue on record."
                if not issues
                else "Misformalization issues: "
                + "; ".join(
                    f"#{esc(str(i['number']))} {esc(str(i['state']))} ({esc(str(i['created']))})"
                    for i in issues
                )
                + "."
            )
            hazards = doc.get("hazards") or []
            hazard_line = (
                f" Wording hazards: {esc(', '.join(str(h) for h in hazards))}." if hazards else ""
            )
            parts.append(
                '<div class="evidence"><p class="label">Catalog evidence (F14): score '
                f"<strong>{esc(str(catalog['score']))}</strong> "
                f"({esc(str(catalog['letter']))}) for <code>{esc(str(catalog['key']))}</code>, "
                f"{esc(standing)}; recorded by {esc(str(doc['recorded_by']))} on "
                f"{esc(str(doc['date']))} from the catalog at "
                f"<code>{esc(str(catalog['network_commit'])[:12])}</code>.</p>"
                f'<ul class="reasons">{reasons}</ul>'
                f"<p>{issue_line}{history_line}{hazard_line}</p></div>"
            )
        formalizations = e.get("formalizations") or []
        if formalizations:
            items = "".join(
                f"<li><code>{esc(str(f['name']))}</code>: equivalence with the root "
                + (
                    f"<strong>{esc(str(f['equivalence']))}</strong>"
                    if f.get("equivalence")
                    else "not run yet"
                )
                + (f" ({self.file_link(str(f['exhibit']))})" if f.get("exhibit") else "")
                + "</li>"
                for f in formalizations
            )
            parts.append(
                '<div class="formalizations"><p class="label">Second formalizations of this '
                "conjecture, kept outside the graph's nodes (D-9 layer 4). A proved equivalence is "
                f"kernel-checked evidence; a failure is never negative:</p><ul>{items}</ul></div>"
            )
        return "".join(parts)

    @staticmethod
    def fast_check(sha: str | None) -> str:
        """F13-R11: the hosted checker serving this target's Mathlib pin, from the network's
        configuration (``opn_gate.hosted``), never from the graph. The check is ``POST /check``;
        its answer carries no authority (D-4 v3.14)."""
        try:
            found = hosted.lookup(hosted.load(), sha)
        except hosted.MappingError:
            return "unknown: the hosted-checker mapping could not be read"
        if found is None or found.environment is None:
            if sha is None:
                return "none: no hosted environment serves a Lean-core-only target"
            return "none: no hosted environment serves this Mathlib pin"
        if found.exact:
            return f"{found.environment} on AXLE (exact)"
        return f"{found.environment} on AXLE (nearest: {found.note or 'not the same Mathlib'})"

    # --- F12-R14: what was checked, who signed, what was attempted, what moved upstream -------

    @staticmethod
    def pertinence(entry: dict[str, Any]) -> str:
        """D-30 v3.12: a related variant is pertinent only with its one signature."""
        relevance = entry.get("relevance")
        if not isinstance(relevance, dict):
            return ""
        if relevance.get("pertinent"):
            return (
                f' <span class="pertinent">pertinent to the target, signed by '
                f"{esc(str(relevance.get('signer')))} on {esc(str(relevance.get('date')))}</span>"
            )
        return ' <span class="note">not yet signed as pertinent to the target (D-30 v3.12)</span>'

    def qa_section(self, tv: TargetView) -> str:
        """The statement-QA state per subject and check, the signers, the counted attempts and
        the drift flag with its escaped upstream excerpt (F12-R14; D-9 v3.12, D-10 v3.12).

        A pre-F11 target (an index row without the F12 fields) says so and shows nothing else;
        every string from the graph or from upstream passes through ``esc`` (§7)."""
        e = tv.index_entry
        subjects = e.get("subjects") or []
        if "attempts" not in e:
            return "<p>No statement-QA record: this target predates the QA pass (F12).</p>"
        parts: list[str] = []
        first: dict[str, Any] = subjects[0] if subjects else {}
        checks: list[str] = list((first.get("qa") or {}).get("checks") or {})
        if not subjects:
            parts.append(
                "<p>No statement-QA record: this target has no curated record (F11), so the "
                "pass has no subject to check.</p>"
            )
        elif checks:
            head = "".join(f"<th>{esc(c)}</th>" for c in checks)
            rows: list[str] = []
            states: list[str] = []
            for s in subjects:
                qa = s.get("qa") or {}
                cells = "".join(
                    f'<td class="qa-{esc(str(qa.get("checks", {}).get(c) or "unrun"))}">'
                    f"{esc(str(qa.get('checks', {}).get(c) or '—'))}</td>"
                    for c in checks
                )
                state = "complete" if qa.get("complete") else "incomplete"
                if qa.get("stale"):
                    state += ", stale (the statement or the pin moved)"
                if qa.get("unrouted_findings"):
                    state += f"; {qa['unrouted_findings']} finding(s) await routing"
                signers = ", ".join(esc(str(n)) for n in s.get("signers") or []) or "none yet"
                rows.append(f"<tr><td>{esc(str(s['subject']))}</td>{cells}</tr>")
                states.append(
                    f"<li><strong>{esc(str(s['subject']))}</strong>: pass {esc(state)}; "
                    f"{esc(str(s['grade']))}; {s.get('signature_count', 0)} signature"
                    f"{'' if s.get('signature_count', 0) == 1 else 's'} ({signers})</li>"
                )
            parts.append(
                '<div class="table-wrap"><table class="qa"><thead><tr><th>Subject</th>'
                f"{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
                f'<ul class="qa-state">{"".join(states)}</ul>'
            )
        attempts = e.get("attempts") or {}
        counted, recorded = attempts.get("counted", 0), attempts.get("recorded", 0)
        parts.append(
            f'<p class="attempts">Documented external attempts counting toward D-9\'s M: '
            f"<strong>{counted}</strong> against the statement as it stands"
            + (
                f"; {recorded - counted} recorded against an earlier revision no longer count."
                if recorded > counted
                else "."
            )
            + "</p>"
        )
        parts.append(self.evidence_section(tv))
        drift = e.get("drift")
        if not drift:
            parts.append('<p class="drift">No upstream drift on record (D-10 v3.12).</p>')
            return "".join(parts)
        record = next((r for r in tv.drift if r.name == drift.get("record")), None)
        kind, date = esc(str(drift.get("kind"))), esc(str(drift.get("date")))
        if drift.get("kind") == "upstream-edit":
            up = drift.get("upstream") or {}
            excerpt = "\n".join((record.diff or "").splitlines()[:40]) if record else ""
            parts.append(
                f'<div class="prose-block untrusted drift"><p class="label">Drift flag: '
                f"<strong>{kind}</strong> on {date} — the statement was imported from "
                f"{esc(str(up.get('repo')))} at {esc(str(up.get('pinned_commit', ''))[:12])} and "
                f"{esc(str(up.get('path')))} differs at head "
                f"{esc(str(up.get('head_commit', ''))[:12])}. Proving compute is frozen until a "
                f"curator acts (D-10 v3.12). Upstream text, untrusted:</p>"
                f'<pre class="diff">{esc(excerpt)}</pre></div>'
            )
        else:
            cite = drift.get("citation") or {}
            parts.append(
                f'<div class="prose-block untrusted drift"><p class="label">Drift flag: '
                f"<strong>{kind}</strong> on {date} — "
                f'<a href="{esc(str(cite.get("url")))}">{esc(str(cite.get("url")))}</a> lists the '
                f"problem as {esc(str(cite.get('status')))}; flagged for D-33 dormancy, the status "
                f"untouched. Source text, untrusted:</p>"
                f'<pre class="diff">{esc(str(cite.get("text", "")))}</pre></div>'
            )
        return "".join(parts)

    def node(self, nv: NodeView) -> str:
        e = nv.graph_entry
        tid, nid = nv.target_id, nv.node_id
        renders = [nv.statement_path, f"targets/{tid}/nodes/{nid}/META.yaml"]
        tv = self.site.targets.get(tid)  # None only for a node rendered outside a loaded site
        if nv.status == "proved" and e["proof_commit"] and nv.proof_path:
            proof = (
                "<p>Proof merged in commit "
                f"<code>{esc(str(e['proof_commit'])[:12])}</code>: "
                f"{self.file_link(nv.proof_path, commit=str(e['proof_commit']))}</p>"
            )
            if nv.proof is not None and nv.proof.mismatched:
                # Q17: the bytes disagree with the attested hash, so they are not shown at all
                # — a page that prints unverified Lean under a passing verdict is worse than a
                # page that says it cannot. The rest of the record still renders.
                proof += (
                    '<p class="flag">The <code>Proof.lean</code> in this checkout is not the '
                    "file the attestation covers: its sha256 is "
                    f"<code>{esc(nv.proof.content_hash[:12])}</code> and the attestation names "
                    f"<code>{esc(str(nv.proof.attested_hash)[:12])}</code>. Its text is "
                    "withheld here; the file itself is linked above.</p>"
                )
            elif nv.proof is not None:
                proof += self.proof_text(tv, nv, nv.proof)
            renders.append(nv.proof_path)
        else:
            proof = "<p>No proof merged yet.</p>"
        attestation = self.attestation_block(nv)
        if nv.attestation is not None and nv.attestation_path is not None:
            attestation = (
                '<div class="attestation-block" data-block="attestation">'
                + self.kernel_label(nv, what="the gate&rsquo;s record of the run")
                + attestation
                + "</div>"
            )
        alternates = self.alternates_block(nv)
        renders.extend(alt.path for alt in nv.alternates)
        if nv.attestation_path:
            renders.append(nv.attestation_path)
        trust = ""
        if e.get("trust_base") == "compiler":
            trust = (
                '<p class="flag">This proof used <code>native_decide</code> under a recorded '
                "waiver: its trust base is the compiler, not the kernel (D-4).</p>"
            )
        attempts = nv.attempts
        hist = ", ".join(f"{k} {v}" for k, v in sorted(attempts.failure_class_histogram.items()))
        refuted = ", ".join(attempts.refuted_route_classes)
        explainer = self.explainer_block(nv, anchors=self.outline_anchors(tv, nv))
        if nv.explainer is not None:
            renders.append(nv.explainer.path)
            renders.extend(v.path for v in nv.signatures)
        renders.extend(self.gloss_renders(tv, nid))
        annexes = (
            "".join(
                self.untrusted_block(
                    "untrusted",
                    a,
                    what="annex (D-31)",
                    math=True,
                    provenance=self.provenance(
                        "untrusted", "an annex (D-31): an informal argument, not a proof."
                    ),
                    block="annex",
                )
                for a in nv.annexes
            )
            or "<p>No annex.</p>"
        )
        ack_label = self.provenance("untrusted", "the prover&rsquo;s justification for a finding.")
        acks = "".join(
            f'<div class="prose-block untrusted" data-block="acknowledgment">{ack_label}'
            f'<p class="label">Untrusted: acknowledgment '
            f"of a <code>{esc(a.get('checker', ''))}</code> finding at "
            f"<code>{esc(a.get('location', ''))}</code></p>"
            f'<div class="prose">{prose.render(a.get("justification", ""))}</div></div>'
            for a in nv.acknowledgments
        )
        witness = self.witness_block(nv)
        renders.extend(f.path for f in (nv.witness, nv.relation) if f is not None)
        if nv.superseded_record is not None:
            renders.append(nv.superseded_record)
        # F08-T17: the claim this node rests on; F08-T20: those its note names, circling back.
        below = nv.circular_below if self.circular_below_note(nv) else ()
        renders.extend(c for c in (nv.circular_claim, *below) if c is not None)
        # F08-T36: the open claims the page links.
        renders.extend(
            f"targets/{tid}/nodes/{nid}/{c['file']}" for c in nv.open_claims if c.get("file")
        )
        partials = self.partials_block(nv)
        for p in nv.partials:
            renders.append(p.file.path)
            if p.record_path is not None:
                renders.append(p.record_path)
        body = _template("node.html").substitute(
            node_id=esc(nid),
            target_id=esc(tid),
            target_href=esc(self.target_path(tid)),
            status=self.status_mark(nv.status, nv.cause),
            status_class=esc(nv.status),
            revision=self.revision_note(tid, nv, in_page=False),
            wayfinding=self.wayfinding(),
            claimable=self.node_not_claimable(nv),
            defects=self.defect_claims_note(nv),
            tutorial=(
                '<p class="cue">The tutorial node: permanently open and off the ledger (D-27).</p>'
                if nv.tutorial
                else ""
            ),
            statement=esc(nv.statement.rstrip("\n")),
            statement_label=self.statement_label(tv, nv),
            statement_glosses=self.gloss_slot(
                tv, "statement", f"nodes/{nid}/Statement.lean", node=nid
            ),
            statement_link=self.file_link(nv.statement_path),
            deps=self.deps_list(tv, nv),
            origin=esc(e["origin"]) + (f" ({esc(e['relation'])})" if e["relation"] else ""),
            proof=proof,
            witness=witness,
            relation=self.relation_block(tv, nv),
            partials=partials,
            attestation=attestation,
            alternates=alternates,
            trust=trust,
            attempt_count=attempts.count,
            refuted=esc(refuted or "none"),
            histogram=esc(hist or "none"),
            explainer=explainer,
            annexes=annexes,
            acknowledgments=acks,
        )
        # F19-T6: KaTeX is loaded only by a page that carries math, so a record page whose prose
        # has none stays script-free (F04-T13's rule for the statement record page).
        has_math = 'class="math"' in body
        return self.page(
            nid,
            body,
            renders=list(dict.fromkeys(renders)),  # F20-T8: an explainer is listed once
            path=PROBLEMS_PATH,
            head=MATH_HEAD if has_math else "",
            script=MATH_SCRIPTS if has_math else "",
        )

    def proof_text(self, tv: TargetView | None, nv: NodeView, lean: LeanFile) -> str:
        """The proof's outline (F19-T7, R9) above its source: the outline of these very bytes,
        when the products carry one; without one, the source alone, as before outlines."""
        commit = str(nv.graph_entry.get("proof_commit") or "") or None
        doc = self.outline_of(tv, nv.node_id, lean) if tv is not None and lean.verified else None
        outline = (
            self.outline_section(
                tv,
                doc,
                lean,
                label=self.kernel_label(nv, what="an outline of the attested proof below"),
                commit=commit,
            )
            if tv is not None and doc is not None
            else ""
        )
        return outline + self.lean_artifact(
            lean,
            what="Proof.lean",
            provenance=(
                "its sha256 is the <code>artifact_hash</code> of the attestation below, "
                "so these are the bytes the gate checked."
                if lean.verified
                else "no attestation names a hash for these bytes."
            ),
            label=(
                self.kernel_label(nv, what="these bytes are the ones its attestation names")
                if lean.verified
                else self.provenance("unchecked", "no attestation names these bytes.")
            ),
            block="proof",
        )

    def explainer_block(self, nv: NodeView, *, anchors: frozenset[str] = frozenset()) -> str:
        """The explainer, or the cue in its place. T20: the cue invited "an account of this
        proof" on statements with no proof; an explainer needs a merged proof (D-3), so only a
        proved statement is invited, and told how one arrives.

        F20-T8 (R14): every chain ``glosses.json`` lists shows its current version and history; an
        explainer no chain lists (one filed before F20 under a name that is not its hash) renders
        exactly as before. ``anchors`` are the artifact hashes whose outline the page draws."""
        tv = self.site.targets.get(nv.target_id)
        chained, listed = self.explainer_chains(tv, nv, anchors=anchors)
        legacy = nv.explainer is not None and Path(nv.explainer.path).stem not in listed
        if chained and not legacy:
            return chained
        if nv.explainer is not None and legacy:
            unlisted = replace(
                nv, signatures=tuple(s for s in nv.signatures if s.explainer not in listed)
            )
            return (
                chained
                + self.vouched_lines(unlisted)
                + self.untrusted_block(
                    "unverified",
                    nv.explainer,
                    what="explainer",
                    math=True,
                    provenance=self.explainer_label(nv, nv.explainer),
                    block="explainer",
                )
            )
        if nv.status == "proved":
            return (
                '<p class="cue">No explainer yet. A plain-language account of this proof, '
                "labelled unverified, is the next thing a writer could add, by pull request "
                f'(D-3, D-36; <a href="{GUIDE_HREF}">the guide</a> shows how).</p>'
            )
        return (
            '<p class="cue">No explainer yet. An explainer is a plain-language account of a '
            "merged proof, so there is nothing to explain until this statement is proved "
            "(D-3).</p>"
        )

    def wayfinding(self) -> str:
        """T20: a statement's page leads to the guide and, where the site knows the service, to
        the pull requests in flight (a link: the policy forbids the page fetching them)."""
        links_ = [f'<a href="{GUIDE_HREF}">How to contribute →</a>']
        if self.api_url:
            links_.append(
                f'<a href="{esc(self.api_url + SUBMISSIONS_PATH)}">Pull requests in flight ↗</a>'
            )
        return " · ".join(links_)

    def node_not_claimable(self, nv: NodeView) -> str:
        """F04-T10: a node a claim could take (F03-Q8) under a target that is not claimable says
        so on its own page, in the target's reasons. A node whose target has no index row (never
        the case for a loaded site) says nothing, since there is no record to state."""
        if nv.cause == CIRCULAR_CAUSE:
            claim = self.file_link(nv.circular_claim) if nv.circular_claim else "its defects/"
            return (
                '<p class="why-not">Not claimable: a merged circularity claim proves that this '
                "statement implies a statement it was meant to reduce, so any proof of it is a "
                f"proof of that one and the route leads straight back (D-16). The claim and its "
                f"Lean exhibit: {claim}. A proof of it is still a proof.</p>\n"
            )
        tv = self.site.targets.get(nv.target_id)
        if tv is None or nv.status not in CLAIMABLE_STATUSES:
            return ""
        if self.open_beneath(tv):
            return ""  # D-33 v3.20: the root's being settled closes nothing beneath it
        block = self.why_not_claimable(tv, detail=False)
        return f"{block}\n" if block else ""

    def claims_note(self) -> str:
        """T9: a claim count on the site is the committed products' snapshot (D-36), not the live
        count the api overlays (F05-R10). Name the commit the products were rendered from, and
        link the service's live claims when the site's config names the service (C6); without
        it, say so and draw no link (C7). Since F04-T12 the Problems page carries it as its
        footer note, beside the sentence naming ``frontier.json``."""
        at = str(self.site.frontier.get("rendered_from") or self.site.commit)
        if self.api_url:
            live = (
                f'the service\'s <a href="{esc(self.api_url + CLAIMS_PATH)}">{esc(CLAIMS_PATH)}</a>'
            )
        else:
            live = f"the service's <code>{esc(CLAIMS_PATH)}</code> (this build names no service)"
        return (
            '<span class="claims-note">Claims are a snapshot from the products at '
            f"<code>{esc(at[:12])}</code>: a claim made or released since then is not counted "
            f"here. The live count is {live}.</span>"
        )

    def contributors(self) -> str:
        """R8, F07-R12: the ledger read as entries, not as a list of files.

        One row per contribution, each linked to the artifact that earned it, because D-19's
        ledger is a record of artifacts and a reader should be able to click through to the
        thing itself. No totals and no ranking: significance is retrospective (D-19, D-32), and
        a column of counts here would be the score the protocol refuses.
        """
        contributions = ledgermod.contributions(self.site.root)
        renders: list[str] = []
        if not contributions:
            ledger = (
                "<p>No ledger files exist yet: nothing has been credited. The first merged proof "
                "and the first postmortem will start the ledger (D-19, F07).</p>"
            )
        else:
            blocks: list[str] = []
            for identity, entries in sorted(contributions.items()):
                renders.append(f"ledger/{identity}.json")
                rows = "".join(self._ledger_row(e) for e in entries)
                blocks.append(
                    f"<h2>{esc(identity)}</h2>"
                    f'<table class="ledger"><tr><th>Line</th><th>Node</th><th>Artifact</th>'
                    f"<th>Merged</th><th>Tooling</th></tr>{rows}</table>"
                )
            ledger = "".join(blocks)
        body = _template("contributors.html").substitute(ledger=ledger)
        return self.page("Contributors", body, renders=renders, path="/contributors/")

    def _ledger_row(self, entry: dict[str, Any]) -> str:
        """One ledger entry. A revoked entry stays listed and says so (D-18)."""
        target, node = str(entry.get("target", "")), str(entry.get("node", ""))
        artifact = str(entry.get("artifact", ""))
        path = f"targets/{target}/nodes/{node}/{artifact}"
        revoked = entry.get("status") == "revoked"
        line = esc(str(entry.get("line", "")))
        if artifact.endswith(PARTIAL_SUFFIX):
            # T20: the ledger's *line* is the credit category, and a partial earns on the proof
            # line (ledger.MERGE_LINES); the artifact says what was merged.
            line = "partial proof"
        if revoked:
            line += ' <span class="status status-revoked">revoked</span>'
        return (
            f"<tr><td>{line}</td>"
            f"<td>{self.node_link(target, node)}</td>"
            f"<td>{self.file_link(path)}</td>"
            f"<td>{esc(str(entry.get('date', '')))}</td>"
            f"<td>{esc(str(entry.get('tooling', 'undeclared')))}</td></tr>"
        )

    def docs(self) -> tuple[str, dict[str, str]]:
        """R9, Q4: the docs page and the copied decisions document with its styles moved to a
        same-origin stylesheet and every external or inline script removed (R10)."""
        extra: dict[str, str] = {}
        if self.decisions_doc is not None and self.decisions_doc.is_file():
            raw = self.decisions_doc.read_text(encoding="utf-8")
            styles = "\n".join(m.group(1) for m in _STYLE_RE.finditer(raw))
            page = _STYLE_RE.sub("", _STRIP_RE.sub("", raw))
            page = page.replace(
                "</head>", '<link rel="stylesheet" href="/docs/decisions.css">\n</head>', 1
            )
            extra["docs/architecture-decisions.html"] = page
            extra["docs/decisions.css"] = styles
            decisions = (
                '<a href="/docs/architecture-decisions.html">Architecture decisions</a>, '
                "the protocol this network runs: decisions D-1 to D-36 with rationale and "
                "overturning conditions. Copied at the site build (Q4)."
            )
        else:
            decisions = "The architecture decisions document is not available in this build."
        agents_md = self.site.root / "AGENTS.md"
        agents = (
            self.untrusted_block(
                "untrusted",
                Prose(path="AGENTS.md", text=agents_md.read_text(encoding="utf-8")),
                what="AGENTS.md",
                document=True,  # F04-T10: headings, tables and labelled fences
            )
            if agents_md.is_file()
            else "<p>The graph has no AGENTS.md yet; the tested one arrives with F10 (D-27).</p>"
        )
        # F10-R9: the human-funnel documents are this repository's (site/docs/), rendered as
        # pages of their own; a graph may add files under its docs/, linked as files.
        funnel_items = []
        for path in sorted(FUNNEL_DOCS.glob("*.md")):
            title, summary = document_head(path.read_text(encoding="utf-8"))
            rel = f"docs/{path.stem}.html"
            extra[rel] = self.page(
                title, prose.render_document(path.read_text(encoding="utf-8")), renders=[]
            )
            funnel_items.append(
                f'<li><a href="/{esc(rel)}">{esc(title)}</a> — {prose.inline(summary)}</li>'
            )
        funnel_dir = self.site.root / "docs"
        funnel_files = (
            sorted(p for p in funnel_dir.iterdir() if p.is_file()) if funnel_dir.is_dir() else []
        )
        funnel_items.extend(f"<li>{self.file_link(f'docs/{p.name}')}</li>" for p in funnel_files)
        funnel = (
            "<ul>" + "".join(funnel_items) + "</ul>"
            if funnel_items
            else "<p>No human-funnel documentation yet (D-27, F10).</p>"
        )
        parts = []
        for name, what in (("LICENSE", "license"), ("DCO", "sign-off (DCO)")):
            path = self.site.root / name
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                parts.append(f'<h3>{esc(name)}</h3><pre class="prose">{esc(text)}</pre>')
            elif name == "LICENSE":
                parts.append(
                    "<p>No license text is committed to the graph yet (D-23). Annex prose "
                    "carries the licence its author chose: "
                    f"{', '.join(esc(x) for x in ANNEX_LICENCES)}.</p>"
                )
            elif self.api_url:
                # T20: the page said no sign-off text existed while the service refused a token
                # without one. The text is the service's, so the page links it, never copies it.
                parts.append(
                    "<p>Sign-off: a token is issued only against the Developer Certificate of "
                    f'Origin the service serves at <a href="{esc(self.api_url + DCO_PATH)}">'
                    "/dco.json ↗</a>, and every commit the service makes for a contributor "
                    "carries their sign-off (D-23). No copy is committed to the graph.</p>"
                )
            else:
                parts.append(
                    f"<p>No {what} text is committed to the graph; the service serves the text a "
                    "token is issued against (D-23).</p>"
                )
        # F15-R11: the steward section, the proposal form on the graph repository (from the
        # site's configured repository, never a hostname in a template) and the Leiden table.
        leiden_rows = "".join(
            f"<tr><td>{esc(objection)}</td><td>{esc(does)}</td><td>{esc(gap)}</td></tr>"
            for objection, does, gap in LEIDEN_ROWS
        )
        glossary_rows = "".join(
            f"<tr><td>{esc(label)}</td><td>{esc(meaning)}</td><td><code>{esc(proto)}</code></td></tr>"
            for _key, label, meaning, proto in self.words["glossary"]
        )
        body = _template("docs.html").substitute(
            decisions=decisions,
            steward_lead=esc(self.words["docs_steward"]),
            step_down_consequence=esc(self.words["docs_step_down"]),
            states=self.states(),
            agents=agents,
            funnel=funnel,
            license="".join(parts),
            commitment=esc(steward.COMMITMENT),  # one sentence, one home (opn_gate.steward)
            proposal_url=esc(self.proposal_url),
            leiden_rows=leiden_rows,
            glossary_rows=glossary_rows,
        )
        renders = [n for n in ("AGENTS.md", "LICENSE", "DCO") if (self.site.root / n).is_file()]
        return self.page("Docs", body, renders=renders, path="/docs/"), extra

    def states(self) -> str:
        """F04-T21 (Q23): the Docs section that draws how a statement and a problem change state
        and names the action behind each arrow. The drawings are inline SVG in the template; the
        two keys are built here so each item is the same hover card the graph key and the
        Problems page use, and a definition keeps its one home (Q14)."""
        statement_key = "".join(self.term(k, dot=True) for k in STATE_MAP_STATEMENT_KEYS)
        problem_key = "".join(
            self.hover(esc(word), esc(self.words["status_defs"][word]), classes="tag")
            for word in STATE_MAP_PROBLEM_KEYS
        )
        return _template("states.html").substitute(
            statement_key=statement_key,
            problem_key=problem_key,
            steward_consequence=esc(self.words["states_steward"]),
        )

    def alternates_block(self, nv: NodeView) -> str:
        """D-25 v3.13: every later proof of the node, each linked at the commit that merged it.
        Empty when there is none, so a node without alternates renders exactly as before."""
        if not nv.alternates:
            return ""
        items = []
        for alt in nv.alternates:
            merged = (
                f" merged in <code>{esc(alt.merge_commit[:12])}</code>" if alt.merge_commit else ""
            )
            by = f" by <code>{esc(alt.submitter)}</code>" if alt.submitter else ""
            link = self.file_link(alt.path, commit=alt.merge_commit)
            items.append(f"<li>{link}{merged}{by}</li>")
        return (
            "\n<h2>Alternate proofs</h2>\n"
            "<p>Later proofs of the same statement, kept beside the first because a different "
            "proof can carry a different insight (D-25). Each passed the gate as a proof does; "
            "none changes this node's status or credit.</p>\n"
            f"<ul>{''.join(items)}</ul>"
        )

    def attestation_block(self, nv: NodeView) -> str:
        doc = nv.attestation
        if doc is None or nv.attestation_path is None:
            return "<p>No attestation: nothing has been merged for this statement.</p>"
        steps = "".join(
            f"<tr><td>{esc(s['step'])}</td><td>{esc(s['name'])}</td>"
            f'<td class="result-{esc(s["result"])}">{esc(s["result"])}</td></tr>'
            for s in doc["steps"]
        )
        review = doc.get("review") or {}
        reviewer = review.get("reviewer") or (
            f"none needed ({review.get('kind')})" if review.get("kind") else "not recorded"
        )
        return _template("attestation.html").substitute(
            link=self.file_link(nv.attestation_path),
            verdict=esc(doc["verdict"]),
            mathlib=esc(doc["mathlib_sha"] or "none (Lean core only)"),
            toolchain=esc(doc["lean_toolchain"]),
            toolchain_hash=esc(doc["toolchain_hash"] or "unresolved"),
            reviewer=esc(reviewer),
            steps=steps,
        )

    # -- the mathematics itself (F04-T15; R14) -------------------------------------------------

    def lean_artifact(  # noqa: PLR0913 — one argument per fact the figure states
        self,
        lean: LeanFile,
        *,
        what: str,
        provenance: str,
        label: str = "",
        block: str = "",
        pre_class: str = "",
    ) -> str:
        """A Lean artifact's own text on the page, with what is known about those bytes.

        ``provenance`` is HTML the caller has already escaped. The sentence differs per artifact
        because only a proof's bytes are attested (``artifact_hash``): a witness and a partial
        have no hash anywhere in the protocol, so their callers are unable to claim one. ``label``
        is the block's F19-R11 provenance line and ``block`` its kind, both from the caller;
        ``pre_class`` names a file that takes a gloss (F20-T8), whose slot follows the figure.
        """
        text = esc(lean.text.rstrip("\n"))
        kind = f' data-block="{esc(block)}"' if block else ""
        pre = f"lean {esc(pre_class)}" if pre_class else "lean"
        return (
            f'<figure class="artifact"{kind}>{label}<figcaption class="artifact-cap">'
            f"{esc(what)} — {provenance} Rendered from {self.file_link(lean.path)}, "
            f"sha256 <code>{esc(lean.content_hash[:12])}</code>.</figcaption>"
            f'<pre class="{pre}">{text}</pre></figure>'
        )

    @staticmethod
    def gloss_renders(
        tv: TargetView | None, node: str | None, *, kinds: tuple[str, ...] | None = None
    ) -> list[str]:
        """R2: the gloss and explainer files a page shows for one node (or, ``None``, the
        target's definition modules), their signatures, and the product listing them; ``kinds``
        narrows to the subjects the page prints."""
        if tv is None or not tv.subjects:
            return []
        found = [f"targets/{tv.target_id}/glosses.json"]
        for s in tv.subjects:
            if s.node != node or (kinds is not None and s.kind not in kinds):
                continue
            for c in s.chains:
                for v in c.versions:
                    found.append(v.path)
                    found.extend(path for _s, _d, path in v.signers)
        return found

    def relation_block(self, tv: TargetView | None, nv: NodeView) -> str:
        """F20-T8 (R13): a variant's ``Relation.lean`` — the implication to or from the root the
        gate checked when the variant was admitted (D-30) — with its gloss."""
        if nv.relation is None:
            return ""
        return (
            "\n<h2>Relation</h2>\n"
            + self.lean_artifact(
                nv.relation,
                what="Relation.lean",
                provenance="the implication between this variant and the problem&rsquo;s "
                "statement, checked by the gate when the variant was admitted and immutable "
                "after (D-30).",
                label=self.provenance(
                    "kernel", "checked at admission (D-30); no proof of the node is implied."
                ),
                block="relation",
                pre_class="relation",
            )
            + self.gloss_slot(tv, "relation", f"nodes/{nv.node_id}/Relation.lean", node=nv.node_id)
        )

    # -- provenance labels (F19-R11) and proof outlines (F19-R9) -------------------------------

    @staticmethod
    def provenance(kind: str, detail: str = "") -> str:
        """A block's provenance line: the kind's words in text, then ``detail`` (HTML the caller
        escaped). Never colour alone (R11, requirement B)."""
        rest = f" — {detail}" if detail else ""
        return (
            f'<p class="block-label" data-provenance="{esc(kind)}">'
            f"<strong>{esc(PROVENANCE[kind])}</strong>{rest}</p>"
        )

    def kernel_label(self, nv: NodeView, *, what: str) -> str:
        """The kernel's label for a node's proof: its attestation and the merge it covers."""
        att = self.file_link(nv.attestation_path) if nv.attestation_path else "its attestation"
        commit = str(nv.graph_entry.get("proof_commit") or "")
        merged = f", merge commit <code>{esc(commit[:12])}</code>" if commit else ""
        return self.provenance("kernel", f"{what}: {att}{merged}.")

    def statement_label(self, tv: TargetView | None, nv: NodeView) -> str:
        """R11: a root statement says its statement-QA state and signers; any other statement
        says that only a problem's root is audited for fidelity (D-9), so its words are its Lean.
        "Audited" is said only once a pass is complete or someone has signed."""
        if tv is None or nv.node_id != tv.root:
            return self.provenance(
                "unaudited",
                "only a problem&rsquo;s root statement is audited for fidelity (D-9); the kernel "
                "checks a proof against this Lean as written.",
            )
        subjects = list(tv.index_entry.get("subjects") or [])
        grade = str(tv.index_entry.get("fidelity") or "not graded")
        if not subjects:
            return self.provenance(
                "unaudited", f"fidelity {esc(grade)}; no statement-QA record for this problem."
            )
        s = next((x for x in subjects if x.get("subject") == "root"), subjects[0])
        qa = s.get("qa") or {}
        signers = [str(n) for n in s.get("signers") or []]
        state = "complete" if qa.get("complete") else "incomplete"
        if qa.get("stale"):
            state += ", stale"
        words = f"fidelity {esc(str(s.get('grade') or grade))}; QA pass {esc(state)}; " + (
            f"signed by {esc(', '.join(signers))}." if signers else "no signer yet."
        )
        audited = bool(qa.get("complete")) or bool(signers)
        return self.provenance("audited" if audited else "unaudited", words)

    def explainer_label(self, nv: NodeView, explainer: Prose) -> str:
        """R11 (D-3): an explainer's author, drafting model and signer, as text."""
        parts = [f"by {esc(explainer.author)}" if explainer.author else "author not recorded"]
        if explainer.model:
            parts.append(f"drafted with {esc(explainer.model)}")
        stem = Path(explainer.path).stem  # an explainer's file name is its hash (F15-R8)
        signed = [v for v in nv.signatures if v.explainer == stem]
        parts.append(
            "signed by " + ", ".join(f"{esc(v.signer)} ({esc(v.date)})" for v in signed)
            if signed
            else "no one has signed it"
        )
        return self.provenance("unverified", "; ".join(parts) + ".")

    def outline_of(
        self, tv: TargetView, node_id: str, lean: LeanFile | None
    ) -> dict[str, Any] | None:
        """F19-T7: the outline of exactly these bytes of this node, when the products carry one.

        Keyed by the bytes' own hash, so an outline of any other version of the file — an older
        proof, a different alternate — can never stand beside these lines."""
        if lean is None:
            return None
        doc = tv.outlines.get(lean.content_hash)
        return doc if doc is not None and doc.get("node") == node_id else None

    def outline_section(  # noqa: PLR0913 — one argument per fact the section states
        self,
        tv: TargetView,
        doc: dict[str, Any],
        lean: LeanFile,
        *,
        label: str,
        commit: str | None,
        folded: bool = False,
    ) -> str:
        """R9: the outline as a tree of native ``<details>``, above the source it outlines.

        ``label`` is the block's provenance line (R11). Unfolded, a top-level step is open unless
        automation closed it; ``folded`` (the reading view, R8) leaves every step closed, so the
        page shows the top-level steps alone."""
        steps = list(doc["steps"])
        key = str(doc["artifact"]["hash"])[:12]
        lines = lean.text.splitlines()
        items = "".join(
            self.outline_step(tv, s, lines, lean.path, commit, key=key, depth=0, folded=folded)
            for s in steps
        )
        single = (
            '<p class="cue">The proof is a single term: its outline is that one step.</p>'
            if len(steps) == 1 and steps[0]["kind"] == "term"
            else ""
        )
        gate = esc(str(doc["gate"])[:12])
        return (
            f'<section class="proof-outline" data-block="outline" data-artifact="{esc(key)}">'
            f'{label}<p class="cue">Outline of <code>{esc(lean.path.rsplit("/", 1)[-1])}</code>, '
            f"extracted by the gate at <code>{gate}</code> from the proof&rsquo;s elaboration: "
            "each step is a claim the proof establishes and the goal it leaves. Open a step for "
            "what it uses and its Lean lines.</p>"
            f'{single}<ol class="po-steps">{items}</ol></section>'
        )

    @staticmethod
    def step_unreliable(step: dict[str, Any]) -> bool:
        """R3: a step any of whose printed texts did not read back is shown as its lines only."""
        texts = [step.get("claim")]
        goal = step.get("goal")
        if goal:
            texts.append(goal["target"])
            texts.extend(h["type"] for h in goal["hypotheses"])
        return any(t is not None and t["printed"] == "unreliable" for t in texts)

    @staticmethod
    def printed(t: dict[str, Any]) -> str:
        cut = ' <span class="po-cut">(truncated)</span>' if t.get("truncated") else ""
        return esc(t["text"]) + cut

    def outline_step(  # noqa: PLR0913 — the step and where it sits
        self,
        tv: TargetView,
        step: dict[str, Any],
        lines: list[str],
        path: str,
        commit: str | None,
        *,
        key: str,
        depth: int,
        folded: bool,
    ) -> str:
        """One step: its id, kind and claim in the summary; its goal, what it uses, its hole's
        node and its Lean lines in the body; its children nested beneath."""
        sid, kind = str(step["id"]), str(step["kind"])
        closed = step["closed_by"]
        routine = closed["kind"] == "automation"
        unreliable = self.step_unreliable(step)
        children = "".join(
            self.outline_step(tv, c, lines, path, commit, key=key, depth=depth + 1, folded=folded)
            for c in step["children"]
        )
        nested = f'<ol class="po-steps">{children}</ol>' if children else ""
        head = f'<code class="po-id">{esc(sid)}</code> <span class="po-kind">{esc(kind)}</span>'
        source = self.step_source(step["span"], lines, path, commit)
        if unreliable:
            summary = (
                f'{head} <span class="po-note">printed form did not read back: shown as its '
                "Lean lines only</span>"
            )
            body = source + nested
        else:
            claim = step.get("claim")
            if claim is not None:
                summary = f'{head} <code class="po-claim">{self.printed(claim)}</code>'
            elif step.get("name"):
                summary = f'{head} <code class="po-claim">{esc(step["name"])}</code>'
            else:
                summary = head
            if routine:
                tactics = ", ".join(str(t) for t in closed["tactics"])
                summary += (
                    f' <span class="po-routine">routine: {esc(tactics or "automation")}</span>'
                )
            if closed["kind"] == "hole":
                summary += ' <span class="po-note">hole</span>'
            body = (
                self.step_goal(step)
                + self.step_uses(tv, step)
                + self.step_hole(tv, step)
                + f'<details class="po-lean"><summary>Lean, {self.span_words(step["span"])}'
                f"</summary>{source}</details>" + nested
            )
        opened = not folded and depth == 0 and not routine
        classes = f"po-step po-{kind}" + (" po-is-routine" if routine else "")
        classes += " po-is-unreliable" if unreliable else ""
        return (
            f'<li class="{esc(classes)}" id="po-{esc(key)}-{esc(sid)}" data-step="{esc(sid)}">'
            f"<details{' open' if opened else ''}><summary>{summary}</summary>"
            f'<div class="po-body">{body}</div></details></li>'
        )

    @staticmethod
    def span_words(span: dict[str, Any]) -> str:
        start, end = int(span["start_line"]), int(span["end_line"])
        return f"line {start}" if start == end else f"lines {start}&ndash;{end}"

    def step_source(
        self, span: dict[str, Any], lines: list[str], path: str, commit: str | None
    ) -> str:
        """A step's own lines from the file on the page, and the same lines at the merge commit.
        A span the file does not hold is said, not guessed at (C7)."""
        start, end = int(span["start_line"]), int(span["end_line"])
        at = commit or self.site.commit
        url = f"{self.repo_url}/blob/{at}/{path}#L{start}-L{end}"
        link = (
            f'<p class="po-at"><a class="file" href="{esc(url)}">{esc(path)}, '
            f"{self.span_words(span)} at <code>{esc(at[:12])}</code> ↗</a></p>"
        )
        if not 1 <= start <= end <= len(lines):
            return (
                f'<p class="flag">The outline places this step at {self.span_words(span)}, '
                f"which the file does not hold.</p>{link}"
            )
        text = "\n".join(lines[start - 1 : end])
        return f'<pre class="lean">{esc(text)}</pre>{link}'

    def step_goal(self, step: dict[str, Any]) -> str:
        goal = step.get("goal")
        if goal is None:
            return '<p class="po-goal">Closes the goal.</p>'
        hyps = ", ".join(
            f"<code>{esc(h['name'])} : {self.printed(h['type'])}</code>" for h in goal["hypotheses"]
        )
        added = f", with {hyps}" if hyps else ""
        return (
            f'<p class="po-goal">Leaves <code class="po-claim">{self.printed(goal["target"])}'
            f"</code>{added}.</p>"
        )

    def step_uses(self, tv: TargetView, step: dict[str, Any]) -> str:
        """What a step uses: statements of this problem (linked), definitions, and Mathlib or
        core constants — each with its docstring sentence as a card a keyboard reaches and its
        Stacks or Kerodon tag as text, never a link off the site (F19-Q6)."""
        uses = step["uses"]
        parts: list[str] = []
        if uses["nodes"]:
            parts.append(
                "statements "
                + ", ".join(
                    self.node_link(tv.target_id, str(n)) if str(n) in tv.nodes else esc(n)
                    for n in uses["nodes"]
                )
            )
        if uses["defs"]:
            parts.append("definitions " + ", ".join(f"<code>{esc(d)}</code>" for d in uses["defs"]))
        consts = []
        for c in uses["mathlib"]:
            name = f"<code>{esc(c['name'])}</code>"
            shown = self.hover(name, esc(c["doc"]), classes="const") if c.get("doc") else name
            tags = "".join(
                f' <span class="po-tag">{esc(str(t["database"]).capitalize())} {esc(t["tag"])}'
                "</span>"
                for t in c["tags"]
            )
            consts.append(shown + tags)
        if consts:
            parts.append("library " + ", ".join(consts))
        return f'<p class="po-uses">Uses {"; ".join(parts)}.</p>' if parts else ""

    def step_hole(self, tv: TargetView, step: dict[str, Any]) -> str:
        """A partial's ``sorry`` step: the node it became (F18's decompositions), linked."""
        if step["closed_by"]["kind"] != "hole":
            return ""
        child = step.get("child_node")
        nv = tv.nodes.get(str(child)) if child else None
        if nv is None:
            return '<p class="po-hole">Left open as a hole; no statement on the record for it.</p>'
        state = self.node_state(nv)
        return (
            '<p class="po-hole">Left open as a hole; its statement is '
            f"{self.node_link(tv.target_id, nv.node_id)} "
            f"({self.dot(self.dot_state(state))}{esc(self.state_label(state))}).</p>"
        )

    # -- the reading view (F19-T8; R8, R10, R11) ------------------------------------------------

    @staticmethod
    def reading_path(target_id: str, entry: dict[str, Any]) -> str:
        """A proof's reading view, named by its artifact hash so its address survives the record
        gaining another proof (the list's index would shift)."""
        return f"{PROBLEMS_PATH}{target_id}/proofs/{str(entry['artifact_hash'])[:12]}/"

    @staticmethod
    def proof_record(tv: TargetView, node_id: str, digest: str | None) -> dict[str, Any] | None:
        """A node's merged proof as ``graph.json`` lists it: the one with ``digest`` when given
        and listed, else its first (``Proof.lean``), as F18's drawing reads a closure."""
        row = next((n for n in tv.graph["nodes"] if n["node_id"] == node_id), None)
        records = list((row or {}).get("proofs") or [])
        own = [r for r in records if digest is not None and r["artifact_hash"] == digest]
        found = (own or records or [None])[0]
        return dict(found) if isinstance(found, dict) else None

    def reading_order(self, tv: TargetView, entry: dict[str, Any]) -> list[str]:
        """R8: the closure with dependencies before dependents, ties in record order.

        An edge runs from ``d`` to ``n`` when both are in the closure and ``d`` is among what
        ``n``'s proof used (this proof's own record at its node, else ``n``'s first), or, where
        nothing measured that, among what ``n`` declared and uses — the edges F18 draws. A cycle
        the record should never hold is laid out in record order rather than refused (C7)."""
        closure = {str(c) for c in entry["closure"]}
        record = [str(n["node_id"]) for n in tv.graph["nodes"] if str(n["node_id"]) in closure]
        rows = {str(n["node_id"]): n for n in tv.graph["nodes"]}
        before: dict[str, set[str]] = {n: set() for n in record}
        for n in record:
            digest = entry["artifact_hash"] if n == entry["node_id"] else None
            proof = self.proof_record(tv, n, digest)
            used = proof.get("used") if proof else None
            rests = used if used is not None else [*rows[n]["deps"], *(rows[n].get("uses") or [])]
            before[n] = {str(d) for d in rests if str(d) in closure and str(d) != n}
        order: list[str] = []
        while len(order) < len(record):
            ready = [n for n in record if n not in order and before[n] <= set(order)]
            order.append(ready[0] if ready else next(n for n in record if n not in order))
        return order

    def artifact_of(
        self, tv: TargetView, nv: NodeView, entry: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, LeanFile | None]:
        """The proof this reading view shows at ``nv``: the entry's own artifact at its node, the
        node's first proof elsewhere — its record and its file, when the bytes are the ones the
        record names."""
        digest = str(entry["artifact_hash"]) if nv.node_id == entry["node_id"] else None
        record = self.proof_record(tv, nv.node_id, digest)
        if record is None:
            return None, None
        files = [nv.proof, *(a.file for a in nv.alternates)]
        lean = next(
            (f for f in files if f is not None and f.content_hash == record["artifact_hash"]), None
        )
        return record, lean

    def lines_link(self, nv: NodeView, record: dict[str, Any], lean: LeanFile | None) -> str:
        """The proof's file at the commit that merged it, with its lines when the file is here."""
        node_dir = Path(nv.statement_path).parent.as_posix()
        rel, commit = f"{node_dir}/{record['path']}", str(record["merge_commit"])
        span = f"#L1-L{len(lean.text.splitlines())}" if lean is not None else ""
        words = f"lines 1&ndash;{len(lean.text.splitlines())}" if lean is not None else "the file"
        url = f"{self.repo_url}/blob/{commit}/{rel}{span}"
        return (
            f'<a class="file" href="{esc(url)}">{esc(rel)}</a>, {words} at '
            f"<code>{esc(commit[:12])}</code>"
        )

    def explainer_state(self, nv: NodeView) -> str:
        """The correspondence table's explainer column: none, unsigned, or signed and by whom.
        F20-T8: the current version of the node's first explainer chain, where one exists."""
        tv = self.site.targets.get(nv.target_id)
        subjects = tv.explainer_subjects(nv.node_id) if tv is not None else []
        current = next(
            (c.current_version for s in subjects for c in s.chains if c.current_version), None
        )
        if current is not None:
            names = ", ".join(esc(s) for s, _d, _p in current.signers)
            state = f"signed by {names}" if names else "not signed"
            return f"unverified, {self.who_wrote(current)}; {state}"
        if nv.explainer is None:
            return "none yet"
        stem = Path(nv.explainer.path).stem
        signers = [v.signer for v in nv.signatures if v.explainer == stem]
        by = f" by {esc(nv.explainer.author)}" if nv.explainer.author else ""
        if signers:
            return f"unverified{by}; signed by {esc(', '.join(signers))}"
        return f"unverified{by}; not signed"

    def reading_node(self, tv: TargetView, nv: NodeView, entry: dict[str, Any]) -> str:
        """One node of the proof: its Lean statement and gloss slot, its explainer slot, its
        outline folded to top-level steps, and its proof's lines at the merged commit."""
        record, lean = self.artifact_of(tv, nv, entry)
        doc = self.outline_of(tv, nv.node_id, lean)
        if record is not None and lean is not None and doc is not None:
            outline = self.outline_section(
                tv,
                doc,
                lean,
                label=self.provenance(
                    "kernel",
                    f"an outline of the proof attested in "
                    f"{self.file_link('attestations/' + str(record['attestation']))}, merge "
                    f"commit <code>{esc(str(record['merge_commit'])[:12])}</code>.",
                ),
                commit=str(record["merge_commit"]),
                folded=True,
            )
        else:
            outline = '<p class="cue">No outline of this proof yet; its Lean is linked below.</p>'
        lines = (
            f'<p class="rv-lines">Proof: {self.lines_link(nv, record, lean)}.</p>' if record else ""
        )
        # F20-T8 (R13): the slot F19 left is the statement's gloss now, or the cue.
        slot = self.gloss_slot(
            tv,
            "statement",
            f"nodes/{nv.node_id}/Statement.lean",
            node=nv.node_id,
            ids=f"rv-{nv.node_id}-",
        )
        anchors = frozenset({lean.content_hash}) if lean is not None and doc is not None else None
        state = self.node_state(nv)
        return (
            f'<li class="rv-node" id="rv-{esc(nv.node_id)}" data-node="{esc(nv.node_id)}">'
            f"<h3>{self.node_link(tv.target_id, nv.node_id)} "
            f'<span class="rv-state">{self.dot(self.dot_state(state))}'
            f"{esc(self.state_label(state))}</span></h3>"
            f'<div class="statement-block" data-block="statement">{self.statement_label(tv, nv)}'
            f'<pre class="lean statement st-{esc(nv.status)}">'
            f"{esc(declaration_only(nv.statement))}</pre>{slot}</div>"
            # D-36: the proof and its attestation sit above the explainer, never below.
            f'{outline}{lines}<div class="rv-explainer">'
            f"{self.explainer_block(nv, anchors=anchors or frozenset())}</div></li>"
        )

    def correspondence(self, tv: TargetView, order: list[str], entry: dict[str, Any]) -> str:
        """R10: one row per node of the closure — declaration, artifact and lines, attestation,
        explainer state — under a label saying which columns are the kernel's record."""
        rows = []
        for node_id in order:
            nv = tv.nodes[node_id]
            record, lean = self.artifact_of(tv, nv, entry)
            m = re.search(r"^\s*(?:theorem|lemma)\s+(\S+)", nv.statement, re.M)
            decl = f"<code>{esc(m.group(1))}</code>" if m else "not found"
            if record is not None:
                artifact = self.lines_link(nv, record, lean)
                att = self.file_link(f"attestations/{record['attestation']}")
            else:
                artifact, att = "no merged proof", "none"
            rows.append(
                f'<tr data-node="{esc(node_id)}">'
                f'<td data-label="Statement">{self.node_link(tv.target_id, node_id)}</td>'
                f'<td data-label="Declaration">{decl}</td>'
                f'<td data-label="Proof file and lines">{artifact}</td>'
                f'<td data-label="Attestation">{att}</td>'
                f'<td data-label="Explainer">{self.explainer_state(nv)}</td></tr>'
            )
        label = self.provenance(
            "kernel",
            "each row&rsquo;s declaration, file, lines and attestation are the attested record; "
            "the explainer column says only whether unverified prose exists and who signed it.",
        )
        return (
            f'<div class="correspondence-block" data-block="correspondence">{label}'
            '<div class="table-wrap"><table class="correspondence"><thead><tr><th>Statement</th>'
            "<th>Declaration</th><th>Proof file and lines</th><th>Attestation</th>"
            f"<th>Explainer</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>"
        )

    def reading_view(self, tv: TargetView, k: int, entry: dict[str, Any]) -> str:
        """R8: one way the problem is proved, read top-down — the problem's statement and its
        QA state first, then each node of the proof's closure, dependencies first, then the
        correspondence table (R10). Every block carries its provenance in words (R11)."""
        proofs = target_proofs(tv)
        root = tv.nodes[tv.root]
        order = self.reading_order(tv, entry)
        head = str(entry["node_id"])
        variant = (
            f" This proof proves {self.node_link(tv.target_id, head)}, a variant that resolves "
            "the problem (D-30)."
            if head != tv.root
            else ""
        )
        n = len(order)
        body = _template("proof.html").substitute(
            target_id=esc(tv.target_id),
            target_href=esc(self.target_path(tv.target_id)),
            number=k + 1,
            count=len(proofs),
            lead=esc(self.proof_label(k, entry))
            + f", merged in <code>{esc(str(entry['merge_commit'])[:12])}</code>.",
            statement_label=self.statement_label(tv, root),
            # F20-T8 (R13, Q11): the curated words first, any gloss of the root after them.
            root_slot=self.gloss_slot(
                tv, "statement", f"nodes/{tv.root}/Statement.lean", node=tv.root, ids="top-"
            ),
            root_status=esc(root.status),
            root_lean=esc(declaration_only(root.statement)),
            fidelity=self.fidelity_tag(tv),
            root_link=self.file_link(root.statement_path),
            variant=variant,
            order_words=esc(f"{n} statement{'' if n == 1 else 's'} on this proof."),
            nodes="\n".join(self.reading_node(tv, tv.nodes[nid], entry) for nid in order),
            table=self.correspondence(tv, order, entry),
        )
        renders = [f"targets/{tv.target_id}/graph.json"]
        for nid in order:
            nv = tv.nodes[nid]
            renders.append(nv.statement_path)
            _, lean = self.artifact_of(tv, nv, entry)
            if lean is not None and self.outline_of(tv, nid, lean) is not None:
                renders.append(f"targets/{tv.target_id}/outlines/{lean.content_hash}.json")
            renders.extend(self.gloss_renders(tv, nid, kinds=("statement", *ARTIFACT_WORDS)))
        renders = list(dict.fromkeys(renders))
        return self.page(
            f"{tv.target_id} · proof {k + 1}",
            body,
            renders=renders,
            path=PROBLEMS_PATH,
            head=MATH_HEAD,
            script=MATH_SCRIPTS,
        )

    def witness_block(self, nv: NodeView) -> str:
        """The non-vacuity witness (D-4 step 7), shown rather than linked.

        Nothing in the protocol hashes a witness, so the page says what the gate *checked* — the
        step's own result in this node's attestation — and never that the bytes were attested.
        """
        if nv.witness is None:
            return '<p class="cue">No witness file: this node carries no step 7 obligation.</p>'
        if nv.witness_open:
            # The invitation is withheld only from a statement nobody owes work on: six of the
            # twelve live nodes with an unfilled slot are superseded by a D-8 revision, and
            # telling a reader to witness one of those is asking for wasted work. Same shape as
            # the frontier's own membership rule (F03-T10), one day earlier.
            words = (
                f"its slot was never filled, and this statement is {esc(nv.status)}, so no "
                "witness is owed here — the node that replaced it carries the obligation "
                "(D-8, D-29)."
                if nv.status in NO_WITNESS_OWED
                else (
                    "its slot is still open, so step 7 cannot pass and the node stays blocked "
                    "until someone fills it (D-29); propose one through "
                    "<code>/proposals/witness</code>."
                )
            )
            return self.lean_artifact(
                nv.witness,
                what="Witness.lean",
                provenance=words,
                label=self.provenance("unchecked", "the witness slot is open."),
                block="witness",
                pre_class="witness",
            ) + self.witness_slot(nv)
        result = next(
            (
                str(s.get("result"))
                for s in (nv.attestation or {}).get("steps", [])
                if s.get("name") == "witness"
            ),
            None,
        )
        words = (
            "filled; the gate checks it at step 7 of every submission against this statement."
            if result is None
            else (
                "checked at step 7 of the run recorded below: "
                f'<span class="result-{esc(result)}">{esc(result)}</span>.'
            )
        )
        label = (
            self.kernel_label(nv, what="step 7 passed in the run its attestation records")
            if result == "pass"
            else self.provenance(
                "unchecked",
                "no run on this page records step 7 passing for it."
                if result is None
                else f"step 7 recorded <code>{esc(result)}</code>.",
            )
        )
        return self.lean_artifact(
            nv.witness,
            what="Witness.lean",
            provenance=words,
            label=label,
            block="witness",
            pre_class="witness",
        ) + self.witness_slot(nv)

    def witness_slot(self, nv: NodeView) -> str:
        tv = self.site.targets.get(nv.target_id)
        return self.gloss_slot(tv, "witness", f"nodes/{nv.node_id}/Witness.lean", node=nv.node_id)

    def partials_block(self, nv: NodeView) -> str:
        """Each partial assembly filed under ``attempts/`` (D-3, D-12 #5), as text.

        No attestation covers a partial, so each is untrusted contributor content (R4), beside
        the record naming it — or beside the fact that no record does, which the live graph
        carries and ``records.count_attempts`` already counts as an attempt in its own right.
        """
        blocks = []
        tv = self.site.targets.get(nv.target_id)
        for p in nv.partials:
            facts = [f"by {esc(p.contributor)}" if p.contributor else "author not recorded"]
            if p.outcome:
                facts.append(f"outcome <strong>{esc(p.outcome)}</strong>")
            if p.route_class:
                facts.append(f"route class {esc(p.route_class)}")
            if p.failure_class:
                facts.append(f"failure class {esc(p.failure_class)}")
            if p.route:
                facts.append(f"route &ldquo;{esc(p.route)}&rdquo;")
            named = (
                f"recorded in {self.file_link(p.record_path)}"
                if p.record_path
                else "no postmortem record names this file"
            )
            text = esc(p.file.text.rstrip("\n"))
            words = "a partial assembly: it records an attempt, and no attestation covers it."
            doc = self.outline_of(tv, nv.node_id, p.file) if tv is not None else None
            outline = (
                self.outline_section(
                    tv,
                    doc,
                    p.file,
                    label=self.provenance(
                        "untrusted",
                        "an outline the gate extracted from this partial assembly; its holes are "
                        "<code>sorry</code> steps, and no attestation covers it.",
                    ),
                    commit=None,
                )
                if tv is not None and doc is not None
                else ""
            )
            blocks.append(
                '<div class="prose-block untrusted" data-block="partial">'
                f'{self.provenance("untrusted", words)}<p class="label">'
                f"Untrusted: partial assembly (D-12 #5), {', '.join(facts)}; {named}. "
                "No attestation covers a partial — it records an attempt, not a proof. "
                f"Rendered from {self.file_link(p.file.path)}.</p>"
                f'{outline}<pre class="lean">{text}</pre></div>'
            )
        return "".join(blocks) or '<p class="cue">No partial assembly filed.</p>'

    # -- glosses and explainer versions (F20-T8; R13, R14) ---------------------------------------

    @staticmethod
    def who_wrote(v: VersionView) -> str:
        """A version's provenance in words: the model that drafted it, or the person who wrote it
        (D-23); a pre-F20 explainer that names no one says so."""
        if v.drafter is not None:
            name = esc(str(v.drafter.get("name") or "the drafter"))
            return f"machine-drafted by {esc(v.model or 'an unnamed model')} ({name})"
        if v.author:
            return f"written by {esc(v.author)}"
        return "author not recorded"

    def version_link(self, v: VersionView) -> str:
        """A version's file at the rendered commit, labelled by its directory and the first
        twelve characters of its hash: the full 64-character path is in the link, not the text."""
        directory = Path(v.path).parent.name
        return self.file_link(v.path, label=f"{directory}/{v.hash[:12]}….md")

    def gloss_slot(  # noqa: PLR0913 — the file and where the slot sits
        self,
        tv: TargetView | None,
        kind: str,
        file: str,
        *,
        node: str | None = None,
        module: str | None = None,
        ids: str = "",
    ) -> str:
        """R13: the words beside one Lean file — each chain's current version that describes the
        file as it stands, in record order (F20-Q4), or the cue; for a root's statement the curated
        informal statement first (Q11). Then the history of every version on the file, including
        any gloss of since-changed text, which is shown nowhere else (R3). ``file`` is relative to
        the target directory; ``ids`` prefixes the history's element ids on a page that shows the
        same file twice."""
        tid = tv.target_id if tv is not None else ""
        subject = tv.gloss_subject(kind, node=node, module=module) if tv is not None else None
        is_root = tv is not None and kind == "statement" and node == tv.root
        parts: list[str] = []
        informal = self.informal_block(tv) if is_root and tv is not None else ""
        parts.append(informal)
        current = subject.describing() if subject is not None else []
        parts.extend(self.gloss_block(v, kind, root=is_root) for v in current)
        if is_root and not informal:
            parts.append(
                '<p class="cue">No informal statement is recorded for this problem yet '
                "(D-6 intake, F11).</p>"
            )
        if not current and not informal:
            what = GLOSS_KIND_WORDS.get(kind, kind)
            earlier = (
                " A gloss of an earlier version of this file is in its history below."
                if subject is not None and subject.chains
                else ""
            )
            parts.append(
                f'<p class="cue">No gloss yet: no one has written in words what this {esc(what)} '
                f"says (D-3 v3.30); the Lean above is the {esc(what)}.{earlier} "
                f'<a href="{GLOSS_GUIDE_HREF}">How to write one →</a></p>'
            )
        shown = len(current)
        if subject is not None and sum(len(c.versions) for c in subject.chains) > shown:
            parts.append(self.history(subject, ids=ids))
        return (
            f'<div class="gloss-slot" data-gloss-slot="{esc(f"{tid}/{file}")}">'
            f"{''.join(parts)}</div>"
        )

    def informal_block(self, tv: TargetView) -> str:
        """Q11: a root's words of record — its curated informal statement (or the paraphrase that
        stands in for an unlicensed source) and its fidelity grade. Empty when the target has no
        curated words, so the slot shows the cue."""
        record = tv.record or {}
        if not (record.get("informal") or record.get("paraphrase")):
            return ""
        grade = str(tv.index_entry.get("fidelity") or "not graded")
        label = self.provenance(
            "informal",
            f"the problem&rsquo;s words of record, against which its fidelity was graded "
            f"(D-6, D-9): fidelity {esc(grade)}.",
        )
        return (
            f'<div class="informal-block" data-block="informal">{label}'
            f'<p class="informal">{self.informal_line(tv)}</p></div>'
        )

    def gloss_block(self, v: VersionView, kind: str, *, root: bool = False) -> str:
        """One current gloss under its fixed label, with its provenance line (R13): who wrote it
        and, when validly signed, who read it against the Lean. A root's gloss says it is not the
        root's words of record (Q11)."""
        what = GLOSS_KIND_WORDS.get(kind, kind)
        signed = (
            "read against the Lean by "
            + ", ".join(f"{esc(s)} ({esc(d)})" for s, d, _ in v.signers)
            + " (F20-R8; it changes no status or grade)"
            if v.signers
            else "no one has read it against the Lean and signed it"
        )
        detail = f"what this {esc(what)} says; {self.who_wrote(v)}"
        if v.date:
            detail += f", {esc(v.date)}"
        detail += f"; {signed}."
        if root:
            detail += (
                " A gloss of a root is not its words of record: the curated statement above is "
                "(D-9)."
            )
        return (
            f'<div class="gloss" data-block="gloss" data-gloss="{esc(v.hash)}">'
            f"{self.provenance('gloss', detail)}"
            f'<div class="prose gloss-prose">{prose.render(v.body, math=True)}</div>'
            f'<p class="gloss-foot">Rendered from {self.version_link(v)} · '
            f'<a href="{GLOSS_GUIDE_HREF}">Improve these words →</a></p></div>'
        )

    def gloss_line(self, tv: TargetView, node: str) -> str:
        """R13: the first sentence of a statement's current gloss, for a row or a list; "" when
        it has none. The first chain in record order speaks for the row (Q4 ranks nothing; the
        node page shows every chain)."""
        subject = tv.gloss_subject("statement", node=node)
        current = subject.describing() if subject is not None else []
        if not current:
            return ""
        sentence = prose.first_sentence(current[0].body)
        return f'<span class="gloss-line">{prose.inline_math(sentence)}</span>' if sentence else ""

    def deps_list(self, tv: TargetView | None, nv: NodeView) -> str:
        """R13: a node's dependencies, each with its statement's words — the first sentence of
        its gloss, the curated statement for the root, or the cue."""
        if not nv.deps:
            return '<p class="deps">Depends on: none.</p>'
        items = []
        for dep in nv.deps:
            link = self.node_link(nv.target_id, dep)
            words = self.gloss_line(tv, dep) if tv is not None else ""
            if not words and tv is not None and dep == tv.root and tv.record:
                text = tv.record.get("informal") or tv.record.get("paraphrase")
                words = f'<span class="gloss-line">{math(str(text))}</span>' if text else ""
            if not words:
                words = '<span class="cue">no gloss of it yet</span>'
            items.append(f"<li>{link}: {words}</li>")
        return (
            '<div class="deps"><p>Depends on, each in words where someone has written them:</p>'
            f"<ul>{''.join(items)}</ul></div>"
        )

    def history(self, subject: SubjectView, *, ids: str = "") -> str:
        """R14: every version of every chain on a subject, in record order (Q4) and chain order:
        its date, who wrote it, whether it is signed, withdrawn (listed, never hidden) or of an
        earlier text, its words, and a diff to its predecessor."""
        total = sum(len(c.versions) for c in subject.chains)
        withdrawn = sum(1 for c in subject.chains for v in c.versions if v.withdrawn)
        noun = "version" if total == 1 else "versions"
        summary = f"History: {total} {noun} on record" + (
            f", {withdrawn} withdrawn" if withdrawn else ""
        )
        many = len(subject.chains) > 1
        blocks: list[str] = []
        for i, chain in enumerate(subject.chains, start=1):
            items: list[str] = []
            diffs: list[str] = []
            by_hash = {v.hash: v for v in chain.versions}
            for k, v in enumerate(chain.versions):
                before = by_hash.get(v.supersedes or "") or (chain.versions[k - 1] if k else None)
                items.append(self.history_item(subject, chain, v, before, ids=ids))
                if before is not None:
                    diffs.append(self.diff_block(before, v, ids=ids))
            head = f'<p class="chain-head">Chain {i} of {len(subject.chains)}</p>' if many else ""
            blocks.append(f'{head}<ol class="versions">{"".join(items)}</ol>{"".join(diffs)}')
        return (
            f'<details class="history" data-history="{esc(subject.record)}">'
            f"<summary>{esc(summary)}</summary>{''.join(blocks)}"
            f'<p class="history-foot"><a href="{GLOSS_GUIDE_HREF}">Improve these words →</a> '
            "Nothing is edited: a correction is a new version, and every version stays on the "
            "record (D-3 v3.30).</p></details>"
        )

    def history_item(
        self,
        subject: SubjectView,
        chain: ChainView,
        v: VersionView,
        before: VersionView | None,
        *,
        ids: str,
    ) -> str:
        states: list[str] = []
        if v.hash == chain.current:
            states.append("current")
        if v.withdrawn:
            states.append('<strong class="withdrawn">withdrawn</strong>')
        if subject.record == "gloss" and v.describes_current is False:
            states.append(
                '<strong class="earlier">describes an earlier version of this file</strong>'
            )
        signed = (
            "signed by " + ", ".join(f"{esc(s)} ({esc(d)})" for s, d, _ in v.signers)
            if v.signers
            else "not signed"
        )
        facts = [esc(v.date or "undated"), self.who_wrote(v), signed, *states]
        diff = (
            f' · <a href="#{esc(ids)}diff-{esc(v.hash[:12])}">diff to its predecessor</a>'
            if before is not None
            else " · the first version of its chain"
        )
        return (
            f'<li class="version" data-version="{esc(v.hash)}">'
            f'<p class="version-facts">{" · ".join(facts)} · {self.version_link(v)}{diff}</p>'
            f'<details class="version-text"><summary>Read this version</summary>'
            f'<div class="prose">{self.version_words(v)}</div></details></li>'
        )

    @staticmethod
    def version_words(v: VersionView) -> str:
        """A version's words as prose: an explainer's sections under their headings, anchors
        named in text; a gloss or a pre-F20 explainer as paragraphs."""
        if not v.sections:
            return prose.render(v.body, math=True)
        out = []
        for sec in v.sections:
            steps = f' <span class="po-id">({esc(" ".join(sec.steps))})</span>' if sec.steps else ""
            out.append(f"<h4>{prose.inline_math(sec.heading)}{steps}</h4>")
            out.append(prose.render(sec.text, math=True))
        return "".join(out)

    @staticmethod
    def diff_block(before: VersionView, v: VersionView, *, ids: str) -> str:
        """R14: a line diff of a version's words against its predecessor's, rendered here with the
        standard library (difflib) into escaped HTML; front matter left out, since only the words
        changed by hand."""
        lines = difflib.unified_diff(
            before.body.splitlines(), v.body.splitlines(), lineterm="", n=2
        )
        out = []
        for line in lines:
            if line.startswith(("---", "+++")):
                continue
            cls = (
                "diff-add"
                if line.startswith("+")
                else "diff-del"
                if line.startswith("-")
                else "diff-hunk"
                if line.startswith("@@")
                else ""
            )
            text = esc(line)
            out.append(f'<span class="{cls}">{text}</span>' if cls else text)
        body = "\n".join(out) or "(the words are the same)"
        return (
            f'<details class="diff" id="{esc(ids)}diff-{esc(v.hash[:12])}">'
            f"<summary>Diff of <code>{esc(v.hash[:12])}</code> against "
            f"<code>{esc(before.hash[:12])}</code></summary>"
            f'<pre class="diff">{body}</pre></details>'
        )

    def outline_anchors(self, tv: TargetView | None, nv: NodeView) -> frozenset[str]:
        """The artifact hashes whose outline the node page draws, so an explainer section links
        only steps that are on the page: the proof's when its bytes are attested, and each
        partial's."""
        if tv is None:
            return frozenset()
        found = set()
        if nv.proof is not None and nv.proof.verified and self.outline_of(tv, nv.node_id, nv.proof):
            found.add(nv.proof.content_hash)
        found.update(
            p.file.content_hash for p in nv.partials if self.outline_of(tv, nv.node_id, p.file)
        )
        return frozenset(found)

    def explainer_chains(
        self, tv: TargetView | None, nv: NodeView, *, anchors: frozenset[str]
    ) -> tuple[str, frozenset[str]]:
        """R14: each explainer chain's current version on each of the node's merged artifacts,
        then the chain's history; and the hashes of every version shown, so the caller can tell
        an explainer no chain lists (one filed before F20 under another name) and keep showing it
        as before."""
        subjects = tv.explainer_subjects(nv.node_id) if tv is not None else []
        listed = frozenset(v.hash for s in subjects for c in s.chains for v in c.versions)
        parts: list[str] = []
        for s in subjects:
            if len(subjects) > 1 or s.kind != "proof":
                where = self.file_link(f"targets/{nv.target_id}/{s.file}") if s.file else ""
                parts.append(
                    f'<p class="explainer-of">On {esc(ARTIFACT_WORDS.get(s.kind, s.kind))}'
                    f"{' ' + where if where else ''}:</p>"
                )
            for chain in s.chains:
                current = chain.current_version
                if current is None:
                    parts.append(
                        '<p class="cue">Every version of this explainer is withdrawn; they are '
                        "listed in its history below (D-3 v3.30).</p>"
                    )
                else:
                    parts.append(self.explainer_version(tv, s, current, anchors=anchors))
            parts.append(self.history(s))
        return "".join(parts), listed

    def explainer_version(
        self,
        tv: TargetView | None,
        subject: SubjectView,
        v: VersionView,
        *,
        anchors: frozenset[str],
    ) -> str:
        """R14: one current explainer version under D-36's fixed label, with its provenance line
        and the F15 signatures on it above the label; each anchored section beside the outline
        steps it names, linked to them where the page draws that outline."""
        vouched = "".join(
            f'<p class="vouched">Explained and vouched for by <strong>{esc(s)}</strong>, '
            f"{esc(d)} (<em>I can explain this proof without the tool that produced it</em>; "
            f"D-3 v3.17). Rendered from {self.file_link(path)}.</p>"
            for s, d, path in v.signers
        )
        signed = (
            "signed by " + ", ".join(f"{esc(s)} ({esc(d)})" for s, d, _ in v.signers)
            if v.signers
            else "no one has signed it"
        )
        detail = f"{EXPLAINER_LABEL}; {self.who_wrote(v)}; {signed}."
        by = []
        if v.author:
            by.append(f"by {esc(v.author)}")
        if v.model:
            by.append(f"drafted with {esc(v.model)}")
        if v.date:
            by.append(esc(v.date))
        who = ", ".join(by) or "author not recorded"
        if v.sections:
            outline = (
                tv.outlines.get(subject.lean_hash) if tv is not None and subject.lean_hash else None
            )
            steps = explainers.outline_steps(outline) if outline is not None else {}
            linked = subject.lean_hash in anchors
            key = (subject.lean_hash or "")[:12]
            body = "".join(
                self.explainer_section(sec, steps, key=key, linked=linked) for sec in v.sections
            )
        else:
            body = f'<div class="prose">{prose.render(v.body, math=True)}</div>'
        return (
            f'{vouched}<div class="prose-block unverified explainer-version" '
            f'data-block="explainer" data-explainer="{esc(v.hash)}">'
            f"{self.provenance('unverified', detail)}"
            f'<p class="label">Unverified: explainer, {who}. '
            f"Rendered from {self.version_link(v)}.</p>{body}"
            f'<p class="gloss-foot"><a href="{GLOSS_GUIDE_HREF}">Improve these words →</a></p>'
            "</div>"
        )

    def explainer_section(
        self,
        sec: explainers.Section,
        steps: dict[str, dict[str, Any]],
        *,
        key: str,
        linked: bool,
    ) -> str:
        """One section of an ``explainer/v1``: the steps it names beside its words (stacked on a
        phone, steps first), each step's id, kind and claim from the outline."""
        named = []
        for sid in sec.steps:
            step = steps.get(sid)
            ident = f"<code>{esc(sid)}</code>"
            if linked and step is not None:
                ident = f'<a href="#po-{esc(key)}-{esc(sid)}">{ident}</a>'
            if step is None:
                named.append(f'<li>{ident} <span class="po-note">not in the outline</span></li>')
                continue
            claim = step.get("claim")
            shown = (
                f' <code class="po-claim">{self.printed(claim)}</code>'
                if claim is not None and claim.get("printed") != "unreliable"
                else ""
            )
            named.append(
                f'<li>{ident} <span class="po-kind">{esc(str(step["kind"]))}</span>{shown}</li>'
            )
        aside = (
            '<aside class="ex-steps" aria-label="Outline steps this section describes">'
            f'<span class="kicker">Steps</span><ul>{"".join(named)}</ul></aside>'
            if named
            else ""
        )
        return (
            f'<section class="ex-section" data-steps="{esc(" ".join(sec.steps))}">{aside}'
            f'<div class="ex-prose"><h3>{prose.inline_math(sec.heading)}</h3>'
            f"{prose.render(sec.text, math=True)}</div></section>"
        )

    def untrusted_block(  # noqa: PLR0913 — the F19 label and block kind ride beside the rest
        self,
        label: str,
        prose_: Prose,
        *,
        what: str,
        document: bool = False,
        math: bool = False,
        provenance: str = "",
        block: str = "",
    ) -> str:
        """R4: contributor text in a labelled block, with author and model when recorded. A
        document (the graph's AGENTS.md) goes through the document renderer; all else is prose.
        ``provenance`` (F19-R11) opens the block and ``block`` names its kind, from the caller."""
        body = (
            prose.render_document(prose_.text) if document else prose.render(prose_.text, math=math)
        )
        by = []
        if prose_.author:
            by.append(f"by {esc(prose_.author)}")
        if prose_.model:
            by.append(f"drafted with {esc(prose_.model)}")
        if prose_.date:
            by.append(esc(prose_.date))
        if prose_.licence:
            by.append(f"licence {esc(prose_.licence)}")
        who = ", ".join(by) or "author not recorded"
        kind = f' data-block="{esc(block)}"' if block else ""
        return (
            f'<div class="prose-block {esc(label)}"{kind}>{provenance}<p class="label">'
            f"{esc(label.capitalize())}: {esc(what)}, {who}. "
            f"Rendered from {self.file_link(prose_.path)}.</p>"
            f'<div class="prose">{body}</div></div>'
        )


def target_proofs(tv: TargetView) -> list[dict[str, Any]]:
    """F18-T1's list, or nothing for a graph rendered before ``graph/v4``."""
    return list(tv.graph.get("target_proofs") or [])


def cited_urls(site: Site) -> frozenset[str]:
    """Every off-site url a validated record names (F11-R1): a target's sources and its D-10
    posting, and since F15 each active steward's identity link and each valid write-up's url —
    both from records the gate checked. Nothing else on the site may point off-origin (R13)."""
    urls: set[str] = set()
    for tv in site.targets.values():
        urls.update(str(s["link"]) for s in tv.stewards)
        urls.update(str(w["url"]) for w in tv.writeups)
        if tv.record is None:
            continue
        urls.update(str(s["url"]) for s in tv.record.get("sources") or [])
        posting = tv.record.get("posting")
        if posting:
            urls.add(str(posting["url"]))
        source = tv.record.get("source") or {}
        if source.get("url"):
            urls.add(str(source["url"]))
        forum = (tv.record.get("prior_art") or {}).get("forum_url")  # F04-T12: the source line
        if forum:
            urls.add(str(forum))
    return frozenset(urls)


def live_urls(api_url: str | None) -> frozenset[str]:
    """T9: the one off-site url the site's own config admits, the service's live claims. An
    exact url, like ``cited_urls``, so a page cannot link anywhere else on the service."""
    if not api_url:
        return frozenset()
    base = api_url.rstrip("/")
    return frozenset({base + CLAIMS_PATH, base + SUBMISSIONS_PATH, base + DCO_PATH})


# --- F04-T30 (audit 2026-10-04, owner-approved): llms.txt and robots.txt ------------------------

#: Crawlers are welcome everywhere, and no path is named: a disallow list is only a map.
ROBOTS_TXT = "User-agent: *\nAllow: /\n"


def llms_txt(r: Renderer) -> str:
    """Where an agent starts (the llmstxt.org shape): the guide on this site and in the graph
    repository at the rendered commit, then the service's index, info.json, error codes and MCP
    endpoint, every off-site url built from config. With no service configured the file says
    so and names none (C7), since nothing here knows a hostname."""
    links = [
        ("Contributor guide", GUIDE_HREF, "how to claim, prove, precheck and submit"),
        (
            "AGENTS.md",
            f"{r.repo_url}/blob/{r.site.commit}/AGENTS.md",
            "the same guide, in the graph repository at the commit this site shows",
        ),
    ]
    if r.api_url:
        links += [
            ("Service index", f"{r.api_url}/", "every route, whether it needs a token, and why"),
            ("info.json", r.api_url + INFO_PATH, "protocol version, schema index, rate limits"),
            ("Error codes", r.api_url + ERRORS_PATH, "every error code and what to do about it"),
            ("MCP endpoint", r.api_url + MCP_PATH, "streamable HTTP; the same calls as tools"),
        ]
    lines = [
        "# Open Proof Network",
        "",
        "> A crowdsourced Lean 4 proof network for open mathematical problems. The graph "
        "repository is the record; this site and the service are lenses over it.",
        "",
        "Read the guide first. Reads need no token; the tutorial node's precheck earns one "
        "without an account.",
        "",
        "## Start here",
        "",
        *(f"- [{name}]({url}): {what}" for name, url, what in links),
    ]
    if not r.api_url:
        lines += ["", "The service's address is not configured in this build."]
    return "\n".join(lines) + "\n"


def render_site(
    site: Site,
    *,
    repo_url: str,
    decisions_doc: Path | None = DECISIONS_DOC,
    api_url: str | None = None,
) -> dict[str, str]:
    """Every output file (path relative to the site root -> content)."""
    r = Renderer(site, repo_url=repo_url, decisions_doc=decisions_doc, api_url=api_url)
    docs_page, extra = r.docs()
    files: dict[str, str] = {
        "index.html": r.home(),
        "problems/index.html": r.problems(),
        "about/index.html": r.about(),
        "contributors/index.html": r.contributors(),
        "docs/index.html": docs_page,
        **static_files()[0],
        **extra,
        "llms.txt": llms_txt(r),  # F04-T30
        "robots.txt": ROBOTS_TXT,
    }
    for old, to in REDIRECTS:  # Q14: the old paths keep resolving, to the merged page
        files[old] = r.redirect(to)
    for tid, tv in site.targets.items():
        files[f"problems/{tid}/index.html"] = r.target(tv)
        files[f"targets/{tid}/index.html"] = r.redirect(r.target_path(tid))
        for nid, nv in tv.nodes.items():
            files[f"nodes/{tid}/{nid}/index.html"] = r.node(nv)
        for k, entry in enumerate(target_proofs(tv)):  # F19-T8: one reading view per proof
            files[r.reading_path(tid, entry).lstrip("/") + "index.html"] = r.reading_view(
                tv, k, entry
            )
    problems = links.check(
        files,
        repo_url=r.repo_url,
        foreign=frozenset(extra),
        cited=cited_urls(site) | live_urls(r.api_url) | COPY_LINKS,
    )
    if problems:  # R13: a link that would not resolve is a build failure, not a 404
        msg = "rendered site has broken links: " + "; ".join(problems[:5])
        raise SiteError(msg)
    return files


def write(files: dict[str, str], out_dir: Path) -> list[Path]:
    """Write every rendered file, and the static tree's binary files (the vendored fonts)
    beside them; called only once all of them rendered (R13)."""
    written: list[Path] = []
    for rel, content in sorted(files.items()):
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    for rel, data in sorted(static_files()[1].items()):
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        written.append(path)
    return written
