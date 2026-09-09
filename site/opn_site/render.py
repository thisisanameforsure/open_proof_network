"""Render a loaded ``Site`` to static HTML (F04-T1; R1-R6, R10, R13; D-36).

Every page names the commit it renders and links every file it renders at that commit (R2).
Everything that comes from the graph passes through ``esc`` (R3); contributor prose is placed in
a labelled block below the kernel-checked object it comments on (R4). Pages are assembled from
``string.Template`` files under ``templates/`` and one stylesheet; nothing external is referenced
(R10). ``render_site`` returns every file's content and ``write`` puts them on disk only after
all of them rendered (R13).
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from string import Template

from opn_site import dag
from opn_site.model import NodeView, Prose, Site, TargetView

TEMPLATES = Path(__file__).resolve().parent / "templates"
STATIC = Path(__file__).resolve().parent / "static"
SITE_NAME = "Open Proof Network"
STATUS_WORDS = {
    "proved": "proved",
    "ready": "ready to prove",
    "blocked": "blocked on a dependency",
    "speculative": "speculative",
    "superseded": "superseded",
    "stale": "stale",
    "disputed": "disputed",
    "abandoned": "abandoned",
}
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
    def __init__(self, site: Site, *, repo_url: str) -> None:
        self.site = site
        self.repo_url = repo_url.rstrip("/")
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
                    informal=(
                        "No informal statement is recorded for this target yet (D-6 intake, F11)."
                    ),
                    status=esc(e["status"]),
                    fidelity=esc(e["fidelity"]),
                    mathlib=esc(mathlib),
                    progress=esc(progress or "nothing proved yet"),
                    claimable="claimable" if e["claimable"] else "listed, not claimable",
                )
            )
        body = _template("targets.html").substitute(rows="".join(rows))
        return self.page("Targets", body, renders=["targets/index.json"])

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
            f'<pre class="prose">{esc(a.get("justification", ""))}</pre></div>'
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

    def untrusted_block(self, label: str, prose: Prose, *, what: str) -> str:
        """R4: contributor text in a labelled block, with author and model when recorded."""
        by = []
        if prose.author:
            by.append(f"by {esc(prose.author)}")
        if prose.model:
            by.append(f"drafted with {esc(prose.model)}")
        if prose.date:
            by.append(esc(prose.date))
        who = ", ".join(by) or "author not recorded"
        return (
            f'<div class="prose-block {esc(label)}"><p class="label">'
            f"{esc(label.capitalize())}: {esc(what)}, {who}. "
            f"Rendered from {self.file_link(prose.path)}.</p>"
            f'<pre class="prose">{esc(prose.text.strip())}</pre></div>'
        )


def render_site(site: Site, *, repo_url: str) -> dict[str, str]:
    """Every output file (path relative to the site root -> content)."""
    r = Renderer(site, repo_url=repo_url)
    files: dict[str, str] = {
        "index.html": r.home(),
        "targets/index.html": r.targets(),
        "site.css": (STATIC / "site.css").read_text(encoding="utf-8"),
    }
    for tid, tv in site.targets.items():
        files[f"targets/{tid}/index.html"] = r.target(tv)
        for nid, nv in tv.nodes.items():
            files[f"nodes/{tid}/{nid}/index.html"] = r.node(nv)
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
