"""F34-T20 (handoff §3.0): Home in the Journal look.

The headline and its two buttons; then four numbered sections in the handoff's order — §1 One
problem, worked (the featured problem's drawing as Figure 1, captioned, beside its statement);
§2 Same machines. Different rules. (the six rules as a numbered list, the usual practice struck
through above each); §3 Where you come in; §4 Lately on the record. No counters, no codes.
"""

from __future__ import annotations

import re

import fixture
import pytest
from harness import TARGET
from test_f34_codes import visible_codes

from opn_site import model, render

REPO = "https://github.com/example/graph"


@pytest.fixture(scope="module")
def home(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = fixture.build(tmp_path_factory.mktemp("f34-home"))
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO, featured_target=TARGET)["index.html"]


def test_the_sections_come_in_the_handoffs_order_numbered(home: str) -> None:
    heads = re.findall(r'<h2><span class="sec">§(\d)</span> ([^<]+)</h2>', home)
    assert heads == [
        ("1", "One problem, worked"),
        ("2", "Same machines. Different rules."),
        ("3", "Where you come in"),
        ("4", "Lately on the record"),
    ], heads


def test_the_headline_and_its_two_buttons(home: str) -> None:
    hero = home[home.index('<section class="hero home-hero">') : home.index("</section>")]
    assert "A proof is finished when someone can explain it." in hero
    assert "See a problem being worked" in hero and "Propose a problem" in hero


def test_the_featured_problem_is_figure_one_with_a_caption(home: str) -> None:
    figure = re.search(r'<figure class="home-figure">.*?</figure>', home, re.S)
    assert figure is not None
    assert "<svg" in figure.group(0)
    caption = re.search(
        r"<figcaption><strong>Figure 1\.</strong>(.*?)</figcaption>", figure.group(0), re.S
    )
    assert caption is not None and "one Lean statement" in caption.group(1)
    assert f'href="/problems/{TARGET}/"' in home


def test_the_rules_are_a_numbered_list_each_crossing_out_one_thing(home: str) -> None:
    rules = re.search(r'<ol class="rule-list">(.*?)</ol>', home, re.S)
    assert rules is not None
    items = re.findall(r'<li class="rule-pair"><s>[^<]+</s><span>[^<]+</span></li>', rules.group(1))
    assert len(items) == 6


def test_home_shows_no_internal_codes(home: str) -> None:
    assert visible_codes(home) == []
