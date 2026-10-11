"""F04-T16: the served policy lets the site load what the site ships (found live 2026-09-18).

An outside contributor's browser logged twenty refusals of ``/vendor/katex/fonts/*.woff2``: the
response-headers policy says ``default-src 'none'`` and names no ``font-src``, so the fonts T13
vendored same-origin were blocked by the site's own header and every formula fell back to the
system face. R10 is about *origins* — nothing from elsewhere — so ``font-src 'self'`` keeps it.
The policy lives in three places (the CloudFront template, the deploy check, F04 §7); this file
holds the first two to each other and to the static tree. The same visit found ``/favicon.ico``
answering 404 and, on reading the deploy check, that its commit pattern predates the redesigned
footer and so could never match.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import fixture
import pytest

from opn_site import model, render

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "site" / "infra" / "site.cfn.yaml"
REPO = "https://github.com/example/graph"


def check_deploy() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_deploy", ROOT / "site" / "tools" / "check_deploy.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


#: F04-T28: the /cache/* behaviour's own policy; binary objects only, so everything is forbidden.
CACHE_POLICY = "default-src 'none'; sandbox"


def served_policy(service_origin: str = "") -> str:
    """The pages' policy: the template's one CSP besides the cache behaviour's (F04-T28), with
    its ``connect-src`` resolved as the stack resolves it for ``service_origin`` (F22-T19:
    the service's origin, or ``'none'`` when the parameter is empty)."""
    text = TEMPLATE.read_text(encoding="utf-8")
    found = re.findall(r'ContentSecurityPolicy: "([^"]+)"', text)
    assert found == [CACHE_POLICY], found
    pages = re.findall(r'ContentSecurityPolicy: !Sub\n\s+- "([^"]+)"\n\s+- Connect: (.+)', text)
    assert len(pages) == 1, pages
    policy, connect = pages[0]
    assert connect.strip() == """!If [HasService, !Ref ServiceOrigin, "'none'"]""", connect
    return str(policy).replace("${Connect}", service_origin or "'none'")


def directives(policy: str) -> dict[str, list[str]]:
    parts = [p.split() for p in policy.split(";") if p.strip()]
    return {p[0]: p[1:] for p in parts}


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("csp"))
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_the_policy_allows_the_fonts_the_static_tree_ships() -> None:
    _text, binary = render.static_files()
    assert any(rel.endswith(".woff2") for rel in binary), "guard: the site ships fonts"
    policy = directives(served_policy())
    assert policy["default-src"] == ["'none'"]
    assert policy.get("font-src") == ["'self'"]


def test_every_directive_names_only_the_sites_own_origin() -> None:
    """R10: whatever is loaded is loaded from here and nowhere else. F22-T19: the one exception
    is ``connect-src``, the service's origin and nothing else, for node pages' words in review."""
    for name, sources in directives(served_policy("https://api.example.org")).items():
        if name == "connect-src":
            assert sources == ["https://api.example.org"], sources
        else:
            assert sources in (["'none'"], ["'self'"]), name


def test_the_deploy_check_expects_the_policy_the_template_serves() -> None:
    assert served_policy() == check_deploy().csp(None)


def test_the_site_ships_an_icon_and_every_page_names_it(pages: dict[str, str]) -> None:
    assert "favicon.svg" in pages and pages["favicon.svg"].lstrip().startswith("<svg")
    for rel in ("index.html", "problems/index.html", "docs/index.html"):
        assert '<link rel="icon" href="/favicon.svg" type="image/svg+xml">' in pages[rel], rel
    assert "http" not in pages["favicon.svg"].replace("http://www.w3.org/2000/svg", "")


def test_the_deploy_check_reads_the_commit_the_footer_names(pages: dict[str, str]) -> None:
    assert check_deploy().footer_commit(pages["index.html"]) == fixture.COMMIT[:12]
    assert check_deploy().footer_commit("<p>no footer here</p>") is None
