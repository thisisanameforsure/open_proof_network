"""Link and resource checks over a rendered site (F04-T3; R10, R13; AC5, AC12).

Every internal href must resolve to a generated file; every resource (stylesheet, script,
image) must be same-origin; the only external hrefs are file links into the graph repository
and, on the copied decisions document, its cited sources. Tags must balance on every page we
generate ourselves. Problems are returned as strings; the generator refuses to write when any
exist (R13).
"""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urlsplit

VOID_TAGS = frozenset({"meta", "link", "br", "hr", "img", "input", "source", "wbr", "col"})
RESOURCE_ATTRS = {"link": "href", "script": "src", "img": "src", "source": "src", "iframe": "src"}


class _Scan(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self.resources: list[str] = []
        self.stack: list[str] = []
        self.problems: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.hrefs.append(str(a["href"]))
        if tag in RESOURCE_ATTRS and a.get(RESOURCE_ATTRS[tag]):
            self.resources.append(str(a[RESOURCE_ATTRS[tag]]))
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        if not self.stack or self.stack[-1] != tag:
            self.problems.append(f"unbalanced </{tag}>")
        else:
            self.stack.pop()


def resolve(href: str) -> str | None:
    """The generated file an internal href names, or ``None`` when it is not internal."""
    parts = urlsplit(href)
    if parts.scheme or parts.netloc or not parts.path.startswith("/"):
        return None
    path = parts.path[1:]
    return path + "index.html" if path.endswith("/") or path == "" else path


def _check_page(  # noqa: PLR0913 — one argument per rule the page is checked under
    rel: str,
    scan: _Scan,
    files: dict[str, str],
    *,
    repo_url: str,
    is_foreign: bool,
    cited: frozenset[str] = frozenset(),
) -> list[str]:
    problems: list[str] = []
    if not is_foreign:
        problems += [f"{rel}: {p}" for p in scan.problems]
        if scan.stack:
            problems.append(f"{rel}: unclosed {scan.stack[-1]}")
    # A file link is a path *under* the repository (`<repo>/blob/<commit>/<file>` or the
    # commit's `<repo>/tree/<commit>`), so the prefix ends at a slash: `<repo>-evil/x` is
    # external (AC5).
    into_repo = repo_url.rstrip("/") + "/"
    for href in scan.hrefs:
        target = resolve(href)
        if target is None:
            off_site = (
                not href.startswith("#")
                and not href.startswith(into_repo)
                and href not in cited
                and not is_foreign
            )
            if off_site:
                problems.append(f"{rel}: external link {href}")
        elif target not in files:
            problems.append(f"{rel}: internal link {href} does not resolve")
    for src in scan.resources:
        target = resolve(src)
        if target is None:
            problems.append(f"{rel}: off-origin resource {src}")
        elif target not in files:
            problems.append(f"{rel}: resource {src} does not resolve")
    return problems


def check(
    files: dict[str, str],
    *,
    repo_url: str,
    foreign: frozenset[str] = frozenset(),
    cited: frozenset[str] = frozenset(),
) -> list[str]:
    """Every problem in ``files`` (path -> content); ``foreign`` pages skip the balance check
    and may link anywhere (the copied decisions document and its cited sources).

    ``cited`` is the one other way an off-site link is allowed: a url a *validated graph record*
    names — a target's source or its D-10 posting (F11-R1, R10). The allowlist is a set of exact
    urls rather than a rule, so the renderer still cannot invent an outbound link, and a page that
    cites a source the graph does not is a build failure like any other (R13).
    """
    problems: list[str] = []
    for rel, html in sorted(files.items()):
        if not rel.endswith(".html"):
            continue
        scan = _Scan()
        scan.feed(html)
        problems += _check_page(
            rel, scan, files, repo_url=repo_url, is_foreign=rel in foreign, cited=cited
        )
    return problems
