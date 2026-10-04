"""F04-T28: every path the distribution serves carries security headers (audit 2026-10-04).

The audit found the ``/cache/*`` behaviour (F10-R7, the olean cache bucket) had no response
headers policy at all, so its objects were served without ``nosniff`` or any CSP: a cache object
a browser could be talked into sniffing as HTML would have run on the site's own origin. The cache
holds only binary build products, so its policy forbids everything (``default-src 'none';
sandbox``). The same reading found the site's own policy said nothing of ``base-uri`` or
``form-action``, which ``default-src`` does not cover; the site has no form and no base element,
so both are ``'none'``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "site" / "infra" / "site.cfn.yaml"


class CfnLoader(yaml.SafeLoader):  # type: ignore[misc]  # yaml ships no stubs
    """SafeLoader that reads ``!Ref x`` as ``{"!Ref": "x"}`` (and so on for every tag)."""


def _tagged(loader: yaml.SafeLoader, suffix: str, node: yaml.Node) -> dict[str, Any]:
    value: Any
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    else:
        value = loader.construct_mapping(node, deep=True)
    return {f"!{suffix}": value}


CfnLoader.add_multi_constructor("!", _tagged)


def resources() -> dict[str, Any]:
    doc = yaml.load(TEMPLATE.read_text(encoding="utf-8"), Loader=CfnLoader)  # noqa: S506
    found: dict[str, Any] = doc["Resources"]
    return found


def distribution() -> dict[str, Any]:
    found: dict[str, Any] = resources()["Distribution"]["Properties"]["DistributionConfig"]
    return found


def cache_behaviour() -> dict[str, Any]:
    (only,) = [
        b
        for b in distribution()["CacheBehaviors"]
        if b["PathPattern"] == {"!Sub": "/${CachePrefix}/*"}
    ]
    found: dict[str, Any] = only
    return found


def headers_of(ref: dict[str, Any]) -> dict[str, Any]:
    assert set(ref) == {"!Ref"}, ref
    policy = resources()[ref["!Ref"]]
    assert policy["Type"] == "AWS::CloudFront::ResponseHeadersPolicy"
    found: dict[str, Any] = policy["Properties"]["ResponseHeadersPolicyConfig"]
    return found


def directives(policy: str) -> dict[str, list[str]]:
    parts = [p.split() for p in policy.split(";") if p.strip()]
    return {p[0]: p[1:] for p in parts}


def test_the_cache_behaviour_has_a_headers_policy_of_its_own() -> None:
    ref = cache_behaviour().get("ResponseHeadersPolicyId")
    assert ref is not None, "the /cache/* behaviour serves with no security headers"
    assert ref != distribution()["DefaultCacheBehavior"]["ResponseHeadersPolicyId"]


def test_the_cache_policy_forbids_everything_and_sniffs_nothing() -> None:
    config = headers_of(cache_behaviour()["ResponseHeadersPolicyId"])["SecurityHeadersConfig"]
    assert config["ContentTypeOptions"]["Override"] is True
    csp = config["ContentSecurityPolicy"]
    assert csp["Override"] is True
    assert directives(csp["ContentSecurityPolicy"]) == {"default-src": ["'none'"], "sandbox": []}
    assert config["FrameOptions"]["FrameOption"] == "DENY"
    assert config["StrictTransportSecurity"]["AccessControlMaxAgeSec"] >= 31536000


def test_the_site_policy_closes_base_uri_and_form_action() -> None:
    main = headers_of(distribution()["DefaultCacheBehavior"]["ResponseHeadersPolicyId"])
    policy = directives(
        main["SecurityHeadersConfig"]["ContentSecurityPolicy"]["ContentSecurityPolicy"]
    )
    assert policy.get("base-uri") == ["'none'"]
    assert policy.get("form-action") == ["'none'"]
