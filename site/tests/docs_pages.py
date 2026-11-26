"""F34-T6: Docs is one page per topic. Tests that read "the Docs page" read them all, in order."""

from __future__ import annotations

from opn_site import render


def docs_rels() -> list[str]:
    """Every Docs page's path, in the sidebar's order, the landing first."""
    return [
        f"docs/{slug}/index.html" if slug else "docs/index.html"
        for _g, entries in render.DOCS_GROUPS
        for slug, _t, _f, _w in entries
        if not slug.startswith("/")
    ]


def docs_all(pages: dict[str, str]) -> str:
    """The Docs pages' HTML joined in sidebar order, so a section the single page held is found,
    and two sections keep the order they had."""
    return "\n".join(pages[rel] for rel in docs_rels())


def docs_page(pages: dict[str, str], slug: str) -> str:
    return pages[f"docs/{slug}/index.html" if slug else "docs/index.html"]
