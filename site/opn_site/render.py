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

from opn_gate import intake
from opn_gate import ledger as ledgermod
from opn_site import dag, links, prose
from opn_site.model import NodeView, Prose, Site, SiteError, TargetView

TEMPLATES = Path(__file__).resolve().parent / "templates"
STATIC = Path(__file__).resolve().parent / "static"
SITE_NAME = "Open Proof Network"
STATUS_WORDS = {
    "proved": "proved",
    "ready": "ready to prove",
    "blocked": "blocked on a dependency",
    "refuted": "refuted by a counterexample",
    "defective": "defective: the statement is vacuous",
    "speculative": "speculative",
    "superseded": "superseded",
    "stale": "stale",
    "disputed": "disputed",
    "abandoned": "abandoned",
}
FRONTIER_COLUMNS = (
    ("node_id", "Node"),
    ("target_id", "Target"),
    ("statement_hash", "Statement hash"),
    ("relation", "Relation"),
    ("origin", "Origin"),
    ("tags", "Tags"),
    ("attempts", "Attempts"),
    ("refuted_route_classes", "Routes refuted"),
    ("failure_class_histogram", "Failure classes"),
    ("ready_since", "Ready since"),
    ("claims", "Claims"),
    ("annex_present", "Annex"),
    ("bounty", "Bounty"),
    ("claimable", "Claimable"),
    ("tutorial", "Tutorial"),
)
DECISIONS_DOC = Path(__file__).resolve().parents[2] / "docs" / "architecture_decisions_v_3_12.html"
_STRIP_RE = re.compile(r"<link\b[^>]*>|<script\b.*?</script>", re.S | re.I)
_STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
NAV = (
    ("/", "Home"),
    ("/targets/", "Targets"),
    ("/frontier/", "Frontier"),
    ("/contributors/", "Contributors"),
    ("/docs/", "Docs"),
)


def esc(value: object) -> str:
    """The one escaping function: everything from the graph goes through it (R3)."""
    return escape(str(value), quote=True)


def _template(name: str) -> Template:
    return Template((TEMPLATES / name).read_text(encoding="utf-8"))


class Renderer:
    def __init__(
        self, site: Site, *, repo_url: str, decisions_doc: Path | None = DECISIONS_DOC
    ) -> None:
        self.site = site
        self.repo_url = repo_url.rstrip("/")
        self.decisions_doc = decisions_doc
        self.base = _template("base.html")

    # -- links -------------------------------------------------------------------------------

    def file_link(self, rel: str, *, commit: str | None = None, label: str | None = None) -> str:
        """A link to a graph file at the rendered commit (R2), labelled with its path."""
        at = commit or self.site.commit
        url = f"{self.repo_url}/blob/{at}/{rel}"
        return f'<a class="file" href="{esc(url)}">{esc(label or rel)}</a>'

    @staticmethod
    def target_path(target_id: str) -> str:
        return f"/targets/{target_id}/"

    @staticmethod
    def node_path(target_id: str, node_id: str) -> str:
        return f"/nodes/{target_id}/{node_id}/"

    def node_link(self, target_id: str, node_id: str) -> str:
        return f'<a href="{esc(self.node_path(target_id, node_id))}">{esc(node_id)}</a>'

    @staticmethod
    def status_mark(status: str) -> str:
        return (
            f'<span class="status status-{esc(status)}"><span class="mark"></span>'
            f"{esc(STATUS_WORDS.get(status, status))}</span>"
        )

    # -- pages -------------------------------------------------------------------------------

    def page(self, title: str, body: str, *, renders: list[str]) -> str:
        nav = "".join(f'<a href="{esc(path)}">{esc(label)}</a>' for path, label in NAV)
        commit = self.site.commit
        sources = ", ".join(self.file_link(r) for r in renders) or "nothing in the graph"
        return self.base.substitute(
            title=esc(title),
            site=esc(SITE_NAME),
            nav=nav,
            body=body,
            commit=esc(commit),
            commit_short=esc(commit[:12]),
            commit_url=esc(f"{self.repo_url}/tree/{commit}"),
            sources=sources,
        )

    def home(self) -> str:
        site = self.site
        entries = site.frontier["entries"]
        nodes = site.nodes
        refuted = sum(len(e["refuted_route_classes"]) for e in entries)
        resolved = sum(
            1 for n in nodes if n.graph_entry["relation"] == "resolves" and n.status == "proved"
        )
        partial = sum(
            1 for n in nodes if n.graph_entry["relation"] == "partial" and n.status == "proved"
        )
        counts = [
            ("targets", len(site.targets), "/targets/"),
            ("nodes proved", sum(1 for n in nodes if n.status == "proved"), "/targets/"),
            ("nodes on the frontier", len(entries), "/frontier/"),
            ("routes refuted", refuted, "/frontier/"),
            ("variants resolved", resolved, "/targets/"),
            ("variants partial", partial, "/targets/"),
        ]
        rows = "".join(
            f'<tr><td class="n">{c}</td><td><a href="{esc(href)}">{esc(label)}</a></td></tr>'
            for label, c, href in counts
        )
        body = _template("home.html").substitute(counts=rows)
        return self.page(SITE_NAME, body, renders=["targets/index.json", "frontier.json"])

    def targets(self) -> str:
        rows = []
        for tid, tv in sorted(self.site.targets.items()):
            e = tv.index_entry
            root = tv.nodes[tv.root]
            counts = e["node_counts"]
            progress = ", ".join(
                f"{counts[s]} {s}" for s in ("proved", "ready", "blocked") if counts[s]
            )
            mathlib = e["mathlib_sha"] or "Lean core only"
            rows.append(
                _template("target-row.html").substitute(
                    href=esc(self.target_path(tid)),
                    target_id=esc(tid),
                    root=self.node_link(tid, tv.root),
                    statement=esc(root.statement.strip()),
                    statement_link=self.file_link(root.statement_path),
                    informal=self.informal_line(tv),
                    status=esc(e["status"]),
                    fidelity=esc(e["fidelity"]),
                    mathlib=esc(mathlib),
                    progress=esc(progress or "nothing proved yet"),
                    claimable="claimable" if e["claimable"] else "listed, not claimable",
                    why_not=self.why_not_claimable(tv),
                    sources=self.sources_block(tv),
                    qa=self.qa_block(tv),
                )
            )
        body = _template("targets.html").substitute(rows="".join(rows))
        return self.page("Targets", body, renders=["targets/index.json"])

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
            return esc(str(informal))
        paraphrase = tv.record.get("paraphrase")
        if paraphrase:
            return (
                f'{esc(str(paraphrase))} <span class="note">(the network\'s own paraphrase: the '
                "source states no licence, so its wording is cited rather than reproduced)</span>"
            )
        return "No informal statement is recorded for this target yet (D-6 intake, F11)."

    def why_not_claimable(self, tv: TargetView) -> str:
        """R10: the reason a listed target is not claimable, named rather than implied."""
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
        detail = (
            f'<p class="signatures">Fidelity by subject: {signed}.{where}</p>' if signed else ""
        )
        return (
            '<p class="why-not">Not claimable, because:</p>'
            f'<ul class="why-not">{items}</ul>{detail}'
        )

    def sources_block(self, tv: TargetView) -> str:
        """R10: where the statement came from, its attribution, and its licence."""
        if tv.record is None:
            return ""
        sources = tv.record.get("sources") or []
        if not sources:
            return (
                '<p class="sources">No external source: this statement is the network\'s own.</p>'
            )
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
        tid = tv.target_id
        href = {nid: self.node_path(tid, nid) for nid in tv.nodes}
        svg = dag.svg(tv.graph["nodes"], href=href)
        node_rows = "".join(
            f"<tr><td>{self.node_link(tid, nid)}</td><td>{self.status_mark(n.status)}</td>"
            f"<td>{esc(', '.join(n.deps) or 'none')}</td>"
            f"<td>{esc(n.graph_entry['origin'])}"
            f"{' (' + esc(n.graph_entry['relation']) + ')' if n.graph_entry['relation'] else ''}"
            "</td></tr>"
            for nid, n in sorted(tv.nodes.items())
        )
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
        body = _template("target.html").substitute(
            target_id=esc(tid),
            status=esc(e["status"]),
            fidelity=esc(e["fidelity"]),
            root=self.node_link(tid, tv.root),
            dag=svg,
            node_rows=node_rows,
            approaches=approaches,
            note=note,
            graph_link=self.file_link(f"targets/{tid}/graph.json"),
        )
        return self.page(f"Target {tid}", body, renders=[f"targets/{tid}/graph.json"])

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
            renders.append(nv.proof_path)
        else:
            proof = "<p>No proof merged yet.</p>"
        attestation = self.attestation_block(nv)
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
        if nv.explainer is not None:
            explainer = self.untrusted_block("unverified", nv.explainer, what="explainer")
            renders.append(nv.explainer.path)
        else:
            explainer = (
                '<p class="cue">No explainer yet. A plain-language account of this proof, '
                "labelled unverified, is the next thing a writer could add (D-3, D-36).</p>"
            )
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
        body = _template("node.html").substitute(
            node_id=esc(nid),
            target_id=esc(tid),
            target_href=esc(self.target_path(tid)),
            status=self.status_mark(nv.status),
            status_class=esc(nv.status),
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
            attestation=attestation,
            trust=trust,
            attempt_count=attempts.count,
            refuted=esc(refuted or "none"),
            histogram=esc(hist or "none"),
            explainer=explainer,
            annexes=annexes,
            acknowledgments=acks,
        )
        return self.page(f"Node {nid}", body, renders=renders)

    def frontier(self) -> str:
        """R7: one column per F03-R5 field, one row per entry, filterable by the same-origin
        script and complete without it."""
        headers = "".join(f"<th>{esc(label)}</th>" for _key, label in FRONTIER_COLUMNS)
        rows = []
        for e in self.site.frontier["entries"]:
            cells = []
            for key, _label in FRONTIER_COLUMNS:
                cells.append(f"<td>{self.frontier_cell(key, e)}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        empty = "" if rows else "<p>The frontier is empty: nothing is ready to prove right now.</p>"
        body = _template("frontier.html").substitute(
            headers=headers, rows="".join(rows), empty=empty
        )
        return self.page("Frontier", body, renders=["frontier.json"])

    def frontier_cell(self, key: str, e: dict[str, Any]) -> str:  # noqa: PLR0911 — one per field kind
        value = e[key]
        if key == "node_id":
            return self.node_link(str(e["target_id"]), str(value))
        if key == "target_id":
            return f'<a href="{esc(self.target_path(str(value)))}">{esc(value)}</a>'
        if key == "statement_hash":
            return f"<code>{esc(str(value)[:12])}</code>"
        if key == "tags":
            deps = ", ".join(str(d) for d in value["deps"]) or "none"
            lib = ", ".join(str(x) for x in value["library"]) or "none"
            return esc(f"deps: {deps}; library: {lib}")
        if key == "refuted_route_classes":
            return esc(", ".join(str(x) for x in value) or "none")
        if key == "failure_class_histogram":
            return esc(", ".join(f"{k} {v}" for k, v in sorted(value.items())) or "none")
        if key == "claims":
            active = len(value["active"])
            return esc(f"{active} active, {value['history_count']} past")
        if value is None:
            return "none"
        if isinstance(value, bool):
            return "yes" if value else "no"
        return esc(value)

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
        return self.page("Contributors", body, renders=renders)

    def _ledger_row(self, entry: dict[str, Any]) -> str:
        """One ledger entry. A revoked entry stays listed and says so (D-18)."""
        target, node = str(entry.get("target", "")), str(entry.get("node", ""))
        artifact = str(entry.get("artifact", ""))
        path = f"targets/{target}/nodes/{node}/{artifact}"
        revoked = entry.get("status") == "revoked"
        line = esc(str(entry.get("line", "")))
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
            )
            if agents_md.is_file()
            else "<p>The graph has no AGENTS.md yet; the tested one arrives with F10 (D-27).</p>"
        )
        funnel_dir = self.site.root / "docs"
        funnel_files = (
            sorted(p for p in funnel_dir.iterdir() if p.is_file()) if funnel_dir.is_dir() else []
        )
        funnel = (
            "<ul>"
            + "".join(f"<li>{self.file_link(f'docs/{p.name}')}</li>" for p in funnel_files)
            + "</ul>"
            if funnel_files
            else "<p>No human-funnel documentation yet (D-27, F10).</p>"
        )
        parts = []
        for name, what in (("LICENSE", "license"), ("DCO", "sign-off (DCO)")):
            path = self.site.root / name
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                parts.append(f'<h3>{esc(name)}</h3><pre class="prose">{esc(text)}</pre>')
            else:
                parts.append(
                    f"<p>No {what} text is committed to the graph yet; D-23 settles it before the "
                    "first external contributor.</p>"
                )
        body = _template("docs.html").substitute(
            decisions=decisions, agents=agents, funnel=funnel, license="".join(parts)
        )
        renders = [n for n in ("AGENTS.md", "LICENSE", "DCO") if (self.site.root / n).is_file()]
        return self.page("Docs", body, renders=renders), extra

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

    def untrusted_block(self, label: str, prose_: Prose, *, what: str) -> str:
        """R4: contributor text in a labelled block, with author and model when recorded."""
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
            f'<div class="prose">{prose.render(prose_.text)}</div></div>'
        )


def cited_urls(site: Site) -> frozenset[str]:
    """Every off-site url a validated target record names (F11-R1): its sources and its D-10
    posting. Nothing else on the site may point off-origin (R13)."""
    urls: set[str] = set()
    for tv in site.targets.values():
        if tv.record is None:
            continue
        urls.update(str(s["url"]) for s in tv.record.get("sources") or [])
        posting = tv.record.get("posting")
        if posting:
            urls.add(str(posting["url"]))
        source = tv.record.get("source") or {}
        if source.get("url"):
            urls.add(str(source["url"]))
    return frozenset(urls)


def render_site(
    site: Site, *, repo_url: str, decisions_doc: Path | None = DECISIONS_DOC
) -> dict[str, str]:
    """Every output file (path relative to the site root -> content)."""
    r = Renderer(site, repo_url=repo_url, decisions_doc=decisions_doc)
    docs_page, extra = r.docs()
    files: dict[str, str] = {
        "index.html": r.home(),
        "targets/index.html": r.targets(),
        "frontier/index.html": r.frontier(),
        "contributors/index.html": r.contributors(),
        "docs/index.html": docs_page,
        "site.css": (STATIC / "site.css").read_text(encoding="utf-8"),
        "frontier.js": (STATIC / "frontier.js").read_text(encoding="utf-8"),
        **extra,
    }
    for tid, tv in site.targets.items():
        files[f"targets/{tid}/index.html"] = r.target(tv)
        for nid, nv in tv.nodes.items():
            files[f"nodes/{tid}/{nid}/index.html"] = r.node(nv)
    problems = links.check(
        files, repo_url=r.repo_url, foreign=frozenset(extra), cited=cited_urls(site)
    )
    if problems:  # R13: a link that would not resolve is a build failure, not a 404
        msg = "rendered site has broken links: " + "; ".join(problems[:5])
        raise SiteError(msg)
    return files


def write(files: dict[str, str], out_dir: Path) -> list[Path]:
    """Write every rendered file; called only once all of them rendered (R13)."""
    written: list[Path] = []
    for rel, content in sorted(files.items()):
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
