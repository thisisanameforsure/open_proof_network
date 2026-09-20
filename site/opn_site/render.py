"""Render a loaded ``Site`` to static HTML (F04-T1; R1-R6, R10, R13; D-36).

Every page names the commit it renders and links every file it renders at that commit (R2).
Everything that comes from the graph passes through ``esc`` (R3); contributor prose is placed in
a labelled block below the kernel-checked object it comments on (R4). Pages are assembled from
``string.Template`` files under ``templates/`` and one stylesheet; nothing external is referenced
(R10). ``render_site`` returns every file's content and ``write`` puts them on disk only after
all of them rendered (R13).
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from string import Template
from typing import Any

from opn_gate import hosted, intake, products, steward
from opn_gate import ledger as ledgermod
from opn_site import dag, links, prose
from opn_site.model import LeanFile, NodeView, Prose, Site, SiteError, TargetView

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
}
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
LEGEND_EXTRA = ("stale", "disputed", "superseded", "abandoned", "refuted", "defective")
#: F04-T21 (Q23): the Docs state map's keys. Every status ``graph.json`` can publish, as the
#: site's word (F03-Q8: ``speculative`` reads open, so nine words for ten statuses), and the five
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
)
STATE_MAP_PROBLEM_KEYS = ("open", "needs a steward", "proved", "dormant", "known result")
#: A problem's status on the public pages (the handoff's three words), each with its definition.
PROBLEM_STATUS_DEFS: dict[str, str] = {
    "open": "Listed, and its statements accept work.",
    "proved": "Its root statement has a merged proof. Not yet explained or written up.",
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
        "Whether the Lean means what the conjecture means is signed by someone who did not "
        "write it.",
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
        words = STATUS_WORDS.get(status, status)
        if status == "blocked" and cause:
            words = CAUSE_WORDS.get(cause, f"blocked: {cause}")
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
        word, meaning, proto = GLOSSARY_BY_KEY[key]
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
        return "".join(self.term(k, dot=True) for k in keys)

    def open_count(self, tv: TargetView) -> int:
        """The statements the site invites work on: the frontier's workable set (T17)."""
        return sum(1 for n in tv.nodes.values() if self.node_state(n) in WORKABLE_STATES)

    @staticmethod
    def problem_status(tv: TargetView) -> str:
        """open · proved · needs a steward, or the D-33 word for a dormant or known result."""
        status = str(tv.index_entry["status"])
        if status == "resolved":
            return "proved"
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
        body = esc(PROBLEM_STATUS_DEFS.get(status, status))
        e = tv.index_entry
        if not e.get("claimable") and status != "proved":
            reasons = [esc(intake.explain(str(r))) for r in e.get("not_claimable") or []]
            why = "; ".join(reasons) or esc(NO_RECORD_WORDS)
            body += f'<span class="why">Not claimable: {why}.</span>'
        return self.hover(esc(status), body, classes="tag")

    def fidelity_tag(self, tv: TargetView) -> str:
        grade = str(tv.index_entry.get("fidelity") or "")
        key = FIDELITY_KEYS.get(grade)
        if key is None:  # a grade this generator has no word for: shown as itself
            return f'<span class="tag tag-outline">{esc(grade)}</span>'
        word, meaning, proto = GLOSSARY_BY_KEY[key]
        body = f'{esc(meaning)}<span class="proto">protocol: {esc(proto)}</span>'
        return self.hover(esc(word), body, classes="tag tag-outline")

    def stage_marks(self, tv: TargetView) -> str:
        """Proved · Explained · Written up: which of the three a problem has reached."""
        digestion = tv.digestion or {}
        state = str(digestion.get("state") or "")
        proved = str(tv.index_entry["status"]) == "resolved"
        reached = (
            ("Proved", proved),
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
            _word, meaning, proto = GLOSSARY_BY_KEY[state]
            body = f'{esc(meaning)}<span class="proto">protocol: {esc(proto)}</span>'
        else:
            words = STATUS_WORDS.get(nv.status, nv.status)
            if nv.status == "blocked" and nv.cause:
                words = CAUSE_WORDS.get(nv.cause, f"blocked: {nv.cause}")
            meaning = GLOSSARY_BY_KEY["blocked"][1] if nv.status == "blocked" else ""
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
            f"<dt>{esc(GLOSSARY_BY_KEY[k][0])}</dt><dd>{esc(GLOSSARY_BY_KEY[k][1])}</dd>"
            for k in LEGEND_KEYS
        )
        open_statements = sum(self.open_count(tv) for tv in targets)
        proved = sum(1 for tv in targets if str(tv.index_entry["status"]) == "resolved")
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
        action = "View the graph →" if status == "proved" else "View problem →"
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
        )

    # -- the About page (F04-T12): the long argument, moved off the home page -----------------

    def about(self) -> str:
        rules = "".join(
            f'<div class="rule-item"><span class="kicker">0{i}</span><h4>{esc(title)}</h4>'
            f"<p>{esc(words)}</p></div>"
            for i, (title, words) in enumerate(ABOUT_RULES, start=1)
        )
        body = _template("about.html").substitute(
            rules=rules,
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
            beneath = self.open_count(tv) if self.open_beneath(tv) else 0
            if beneath:
                guide = f'<a href="{GUIDE_HREF}">How to contribute →</a>'
                noun = "statement" if beneath == 1 else "statements"
                return (
                    '<p class="claimable">Proved: the problem\'s own statement is closed. '
                    f"{beneath} {noun} proposed beneath it {'is' if beneath == 1 else 'are'} "
                    f"open for work. {guide}</p>"
                )
            return '<p class="claimable">Proved: its statement no longer accepts work.</p>'
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
        # T17: the pill wears the state the key and the rows name, not the bare graph status.
        drawn = [
            {**n, "status": NEEDS_WITNESS}
            if n.get("status") == "blocked" and n.get("cause") == WITNESS_CAUSE
            else n
            for n in tv.graph["nodes"]
        ]
        svg = dag.svg(drawn, href=href)
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
        body = _template("target.html").substitute(
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
            dag=svg,
            panels=panels,
            digestion=self.digestion_section(tv),
            stewards=self.stewards_section(tv),
            sources=self.sources_block(tv),
            qa_block=self.qa_block(tv),
            informal_full=self.informal_line(tv),
            approaches=approaches,
            note=note,
            qa=self.qa_section(tv),
            review=esc(self.review_sentence(tv)),
            graph_link=self.file_link(f"targets/{tid}/graph.json"),
            fast_check=esc(self.fast_check(e.get("mathlib_sha"))),
        )
        return self.page(
            tid,
            body,
            renders=[f"targets/{tid}/graph.json"],
            path=PROBLEMS_PATH,
            head=MATH_HEAD,
            script=MATH_SCRIPTS + '<script src="/problem.js"></script>',
        )

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
                "This problem is proved but not explained. It waits for a mathematician to "
                "commit to writing it up and to sign the explainer.",
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
        return f'<p class="revision-note">{" ".join(parts)}</p>' if parts else ""

    def statement_panel(self, tv: TargetView, nv: NodeView) -> str:
        """One "Selected statement" panel per node; the script shows the selected one and the
        page without it shows the root's. Hashes, origin, pin and files sit behind a toggle."""
        tid, nid = tv.target_id, nv.node_id
        e = nv.graph_entry
        state = self.node_state(nv)
        words = STATUS_WORDS.get(nv.status, nv.status)
        if nv.status == "blocked" and nv.cause:
            words = CAUSE_WORDS.get(nv.cause, f"blocked: {nv.cause}")
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
            note=note,
            revision=self.revision_note(tid, nv, in_page=True),
            statement=esc(declaration_only(nv.statement)),
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
        parts = [
            f'<p class="lead">Resolved — <strong>{esc(state)}</strong>. Reported back as: '
            f"<em>{esc(DIGESTION_WORDS[state])}</em> (D-10 v3.17).</p>",
            f"<p>{esc(str(digestion['closure_explained']))} of "
            f"{esc(str(digestion['closure']))} proved nodes in the closing proof's dependency "
            "closure carry a signed explainer.</p>",
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
                proof += self.lean_artifact(
                    nv.proof,
                    what="Proof.lean",
                    provenance=(
                        "its sha256 is the <code>artifact_hash</code> of the attestation below, "
                        "so these are the bytes the gate checked."
                        if nv.proof.verified
                        else "no attestation names a hash for these bytes."
                    ),
                )
            renders.append(nv.proof_path)
        else:
            proof = "<p>No proof merged yet.</p>"
        attestation = self.attestation_block(nv)
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
        explainer = self.explainer_block(nv)
        if nv.explainer is not None:
            renders.append(nv.explainer.path)
            renders.extend(v.path for v in nv.signatures)
        annexes = (
            "".join(self.untrusted_block("untrusted", a, what="annex (D-31)") for a in nv.annexes)
            or "<p>No annex.</p>"
        )
        acks = "".join(
            f'<div class="prose-block untrusted"><p class="label">Untrusted: acknowledgment '
            f"of a <code>{esc(a.get('checker', ''))}</code> finding at "
            f"<code>{esc(a.get('location', ''))}</code></p>"
            f'<div class="prose">{prose.render(a.get("justification", ""))}</div></div>'
            for a in nv.acknowledgments
        )
        witness = self.witness_block(nv)
        if nv.witness is not None:
            renders.append(nv.witness.path)
        if nv.superseded_record is not None:
            renders.append(nv.superseded_record)
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
            tutorial=(
                '<p class="cue">The tutorial node: permanently open and off the ledger (D-27).</p>'
                if nv.tutorial
                else ""
            ),
            statement=esc(nv.statement.rstrip("\n")),
            statement_link=self.file_link(nv.statement_path),
            deps=", ".join(self.node_link(tid, d) for d in nv.deps) or "none",
            origin=esc(e["origin"]) + (f" ({esc(e['relation'])})" if e["relation"] else ""),
            proof=proof,
            witness=witness,
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
        return self.page(
            nid,
            body,
            renders=renders,
            path=PROBLEMS_PATH,
        )

    def explainer_block(self, nv: NodeView) -> str:
        """The explainer, or the cue in its place. T20: the cue invited "an account of this
        proof" on statements with no proof; an explainer needs a merged proof (D-3), so only a
        proved statement is invited, and told how one arrives."""
        if nv.explainer is not None:
            return self.vouched_lines(nv) + self.untrusted_block(
                "unverified", nv.explainer, what="explainer"
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
            for _key, label, meaning, proto in GLOSSARY
        )
        body = _template("docs.html").substitute(
            decisions=decisions,
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
            self.hover(esc(word), esc(PROBLEM_STATUS_DEFS[word]), classes="tag")
            for word in STATE_MAP_PROBLEM_KEYS
        )
        return _template("states.html").substitute(
            statement_key=statement_key, problem_key=problem_key
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

    def lean_artifact(self, lean: LeanFile, *, what: str, provenance: str) -> str:
        """A Lean artifact's own text on the page, with what is known about those bytes.

        ``provenance`` is HTML the caller has already escaped. The sentence differs per artifact
        because only a proof's bytes are attested (``artifact_hash``): a witness and a partial
        have no hash anywhere in the protocol, so their callers are unable to claim one.
        """
        text = esc(lean.text.rstrip("\n"))
        return (
            '<figure class="artifact"><figcaption class="artifact-cap">'
            f"{esc(what)} — {provenance} Rendered from {self.file_link(lean.path)}, "
            f"sha256 <code>{esc(lean.content_hash[:12])}</code>.</figcaption>"
            f'<pre class="lean">{text}</pre></figure>'
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
            return self.lean_artifact(nv.witness, what="Witness.lean", provenance=words)
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
        return self.lean_artifact(nv.witness, what="Witness.lean", provenance=words)

    def partials_block(self, nv: NodeView) -> str:
        """Each partial assembly filed under ``attempts/`` (D-3, D-12 #5), as text.

        No attestation covers a partial, so each is untrusted contributor content (R4), beside
        the record naming it — or beside the fact that no record does, which the live graph
        carries and ``records.count_attempts`` already counts as an attempt in its own right.
        """
        blocks = []
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
            blocks.append(
                '<div class="prose-block untrusted"><p class="label">'
                f"Untrusted: partial assembly (D-12 #5), {', '.join(facts)}; {named}. "
                "No attestation covers a partial — it records an attempt, not a proof. "
                f"Rendered from {self.file_link(p.file.path)}.</p>"
                f'<pre class="lean">{text}</pre></div>'
            )
        return "".join(blocks) or '<p class="cue">No partial assembly filed.</p>'

    def untrusted_block(
        self, label: str, prose_: Prose, *, what: str, document: bool = False
    ) -> str:
        """R4: contributor text in a labelled block, with author and model when recorded. A
        document (the graph's AGENTS.md) goes through the document renderer; all else is prose."""
        body = prose.render_document(prose_.text) if document else prose.render(prose_.text)
        by = []
        if prose_.author:
            by.append(f"by {esc(prose_.author)}")
        if prose_.model:
            by.append(f"drafted with {esc(prose_.model)}")
        if prose_.date:
            by.append(esc(prose_.date))
        who = ", ".join(by) or "author not recorded"
        return (
            f'<div class="prose-block {esc(label)}"><p class="label">'
            f"{esc(label.capitalize())}: {esc(what)}, {who}. "
            f"Rendered from {self.file_link(prose_.path)}.</p>"
            f'<div class="prose">{body}</div></div>'
        )


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
    }
    for old, to in REDIRECTS:  # Q14: the old paths keep resolving, to the merged page
        files[old] = r.redirect(to)
    for tid, tv in site.targets.items():
        files[f"problems/{tid}/index.html"] = r.target(tv)
        files[f"targets/{tid}/index.html"] = r.redirect(r.target_path(tid))
        for nid, nv in tv.nodes.items():
            files[f"nodes/{tid}/{nid}/index.html"] = r.node(nv)
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
