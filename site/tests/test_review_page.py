"""F26-T12 / AC15 (R16, R17; D-9 v3.39): the review page, the answer form and the target page's
state line.

The review is ``fixture.write_review``'s, written by hand and validated against the eight record
schemas, so the site is held to the contract rather than to what one gate commit writes. The
page is rendered from the record only: candidates with author, origin and stage-3 result (a
discarded one with its exhibit), pairs and clusters, questions and answers with their source or
the flag, the test matrix with the mutants caught, screens and the brief as a judgement, and the
two signature slots. Exhibits and judgements are visibly apart. The answer form is a placeholder
the session script fills; nothing posts without a session. A target with no review shows no
line, an older ``graph.json`` renders with none, and a malformed record is a build failure.
"""

from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import fixture
import pytest
import yaml
from fixture import (
    CANDIDATE_LEAN,
    COMMIT,
    REVIEW_ANSWER,
    REVIEW_IDS,
    REVIEW_INJECTION,
    REVIEW_PROPOSER,
    REVIEW_QUESTION_ANSWERED,
    REVIEW_QUESTION_WAITING,
    REVIEW_WORDS,
)
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.org"
PAGE = f"problems/{TARGET}/review/index.html"
PROBLEM = f"problems/{TARGET}/index.html"
SECTIONS = ("candidates", "pairs", "questions", "tests", "screens", "signatures")
STATE_LINE = 'class="tag tag-outline review-state"'


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.hrefs: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def text_of(fragment: str) -> str:
    p = _Text()
    p.feed(fragment)
    return " ".join(" ".join(p.text).split())


def hrefs_of(fragment: str) -> list[str]:
    p = _Text()
    p.feed(fragment)
    return p.hrefs


def section(page: str, sid: str) -> str:
    start = page.index('<section class="review-section')
    start = page.index(f'id="{sid}"', start)
    start = page.rindex("<section", 0, start)
    end = page.find('<section class="review-section', start + 1)
    return page[start : end if end >= 0 else page.index("</main>")]


def state_line(page: str) -> str | None:
    m = re.search(r'<a class="tag tag-outline review-state" href="([^"]+)">(.*?)</a>', page, re.S)
    return None if m is None else text_of(m.group(2))


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return fixture.build_with_review(tmp_path_factory.mktemp("review"))


@pytest.fixture(scope="module")
def site(root: Path) -> model.Site:
    return model.load_site(root, COMMIT)


@pytest.fixture(scope="module")
def pages(site: model.Site) -> dict[str, str]:
    return render.render_site(site, repo_url=REPO, api_url=API)


@pytest.fixture(scope="module")
def page(pages: dict[str, str]) -> str:
    return pages[PAGE]


# --- the model -------------------------------------------------------------------------------


def test_the_model_reads_the_review_from_graph_v9_and_the_records(site: model.Site) -> None:
    tv = site.targets[TARGET]
    assert tv.review is not None and tv.review["state"] == "open"
    assert tv.review["candidates"] == 4 and tv.review["questions_waiting"] == 1
    assert tv.review["signers"] == {"intent": REVIEW_PROPOSER, "independent": None}
    assert len(tv.open_pairs) == 1 and tv.open_pairs[0]["direction"] == "backward"
    rv = tv.review_records
    assert rv is not None
    assert rv.opening["words"] == REVIEW_WORDS
    assert {c["id"] for c in rv.candidates} == set(REVIEW_IDS.values())
    assert [t["id"] for t in rv.tests] == ["t-0000aaaa", "t-0000bbbb"]
    assert [q["id"] for q in rv.questions] == ["q-1", "q-2"]
    assert [a["id"] for a in rv.answers] == ["a-1"]
    assert len(rv.pairs) == 2 and len(rv.exhibits) == 15 and len(rv.signatures) == 1
    # every candidate's Lean is read beside its record, from the file the record names
    assert rv.lean[REVIEW_IDS["person"]].text == CANDIDATE_LEAN["person"]
    assert rv.lean["e-0000cccc"].text.startswith("example : ¬ True")
    assert "e-0000eeee" not in rv.lean  # a returned exhibit has no Lean


def test_the_model_derives_each_candidates_stage_3_result_from_the_exhibits(
    site: model.Site,
) -> None:
    rv = site.targets[TARGET].review_records
    assert rv is not None
    assert rv.result_of(REVIEW_IDS["person"]) == ("surviving", None)
    assert rv.result_of(REVIEW_IDS["model"]) == ("surviving", None)
    assert rv.result_of(REVIEW_IDS["dropped"]) == ("discarded", "e-0000cccc")
    assert rv.result_of(REVIEW_IDS["inline"]) == ("returned", "e-0000eeee")
    assert rv.clusters() == [sorted((REVIEW_IDS["person"], REVIEW_IDS["model"]))]
    assert rv.mutants_caught() == (2, 3)


def test_a_target_with_no_review_has_none_and_an_older_graph_reads_as_none(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    plain = model.load_site(fixture.build(tmp_path_factory.mktemp("plain")), COMMIT)
    tv = plain.targets[TARGET]
    assert tv.review is not None and tv.review["state"] == "none"
    assert tv.review_records is None and tv.open_pairs == []
    root = fixture.build_with_review(tmp_path_factory.mktemp("v8"))
    fixture.publish_v8(root)
    old = model.load_site(root, COMMIT).targets[TARGET]
    assert old.review is None and old.open_pairs == []
    assert old.review_records is not None  # the records are on the graph whatever the product


def test_a_malformed_review_record_is_a_build_failure(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    root = fixture.build_with_review(tmp_path_factory.mktemp("bad"))
    path = root / "targets" / TARGET / "review" / "questions" / "q-2.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["asked_to"] = "everyone"
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    with pytest.raises(model.SiteError, match=r"review/questions/q-2\.yaml"):
        model.load_site(root, COMMIT)


# --- the page: six sections, exhibits and judgements apart -----------------------------------


def test_the_page_exists_and_carries_the_six_sections_in_order(page: str) -> None:
    starts = [page.index(f'id="{sid}"') for sid in SECTIONS]
    assert starts == sorted(starts), SECTIONS
    assert text_of(page).count("Exhibits") >= 1 and "judgement" in text_of(page)


def test_exhibit_sections_and_judgement_sections_are_visibly_apart(page: str) -> None:
    kinds = {}
    for sid in SECTIONS:
        sec = section(page, sid)
        head = sec[: sec.index(">") + 1]
        kinds[sid] = (
            "exhibits" if "exhibits" in head else "judgements" if "judgements" in head else None
        )
    assert kinds == {
        "candidates": "exhibits",
        "pairs": "exhibits",
        "questions": "judgements",
        "tests": "exhibits",
        "screens": "exhibits",  # D-9 layer 2; the brief inside it is an aside marked a judgement
        "signatures": "judgements",
    }
    for sid in SECTIONS:
        sec = section(page, sid)
        label = sec[: sec.index("</p>")]
        assert ("kernel-checked" in label) == (kinds[sid] == "exhibits"), sid


def test_candidates_show_author_origin_models_and_stage_3_result(page: str) -> None:
    sec = section(page, "candidates")
    ids = REVIEW_IDS
    rows = {
        m.group(1): m.group(0)
        for m in re.finditer(
            r'<tr data-candidate="([^"]+)" data-result="[^"]+">.*?</tr>', sec, re.S
        )
    }
    assert set(rows) == set(ids.values())
    person = text_of(rows[ids["person"]])
    assert "alice" in person and "a person's" in person and "surviving" in person
    assert "read no other candidate" in person
    modelled = text_of(rows[ids["model"]])
    assert "agent-two" in modelled and "claude-opus-5" in modelled and "surviving" in modelled
    dropped = rows[ids["dropped"]]
    assert 'data-result="discarded"' in dropped
    assert "expected true, the candidate says false" in text_of(dropped)
    assert html.escape(REVIEW_INJECTION) in dropped and REVIEW_INJECTION not in dropped
    assert f"targets/{TARGET}/review/exhibits/e-0000cccc.lean" in " ".join(hrefs_of(dropped))
    returned = rows[ids["inline"]]
    assert 'data-result="returned"' in returned and "written inline" in text_of(returned)
    # the Lean a signer reads, preformatted, exactly as written
    for lean in CANDIDATE_LEAN.values():
        assert f'<pre class="lean">{html.escape(lean.rstrip())}</pre>' in sec


def test_pairs_and_clusters(page: str) -> None:
    sec = section(page, "pairs")
    t = text_of(sec)
    a, b = sorted((REVIEW_IDS["person"], REVIEW_IDS["model"]))
    assert f"{a} and {b}" in t or f"{a} ⇄ {b}" in t
    assert "1 cluster" in t and "proved both ways" in t
    assert "open" in t and "grind" in t and "20 s" in t
    assert "claimable work" in t
    assert sec.count('class="pair-direction proved"') == 3
    assert sec.count('class="pair-direction open"') == 1


def test_questions_and_answers_with_their_source_or_the_flag_and_the_test_each_became(
    page: str,
) -> None:
    sec = section(page, "questions")
    t = text_of(sec)
    assert REVIEW_QUESTION_ANSWERED in t and REVIEW_QUESTION_WAITING in t
    assert "no source cited" in t
    assert html.escape(REVIEW_ANSWER) in sec and REVIEW_INJECTION not in sec
    assert "t-0000bbbb" in t  # the test the answer became
    assert "Waiting for the intent signer" in t and REVIEW_PROPOSER in t
    assert "raised by a mutant" in t and "raised by a disagreement" in t


def test_the_test_matrix_has_a_cell_per_candidate_and_test_and_counts_the_mutants(
    page: str,
) -> None:
    sec = section(page, "tests")
    assert "2 of 3 mutants caught" in text_of(sec)
    assert sec.count("<th") >= 3
    cells = re.findall(r'<td class="cell ([a-z-]+)"', sec)
    assert cells.count("pass") == 4 and cells.count("fail") == 1
    assert cells.count("not-run") == 3  # the discarded one's second test, the returned one's two
    assert "p = True, q = True" in text_of(sec) and "agreement" in text_of(sec)


def test_screens_and_the_brief_as_a_models_judgement(page: str) -> None:
    sec = section(page, "screens")
    t = text_of(sec)
    assert "negation not proved" in t and "elaborates at the pin" in t
    assert '<aside class="judgement brief">' in sec
    assert "a model's judgement" in t and "never evidence" in t


def test_the_two_signature_slots(page: str) -> None:
    sec = section(page, "signatures")
    t = text_of(sec)
    assert f"Intent signer: {REVIEW_PROPOSER}" in t and "accepted" in t
    assert "Independent signer: empty" in t
    assert "wrote no candidate in the surviving cluster" in t
    assert sec.count('class="signature-slot ') == 2


def test_the_words_the_review_is_of_open_the_page_escaped(page: str) -> None:
    assert html.escape(REVIEW_WORDS) in page and "<b>&</b>" not in page
    assert '<a href="/docs/#review">' in page


# --- the answer form --------------------------------------------------------------------------


def test_the_answer_form_is_a_placeholder_the_session_script_fills(
    pages: dict[str, str], site: model.Site
) -> None:
    sec = section(pages[PAGE], "questions")
    m = re.search(r'<div class="review-answer-ctl" ([^>]*)hidden></div>', sec)
    assert m is not None, "the placeholder"
    attrs = m.group(1)
    assert "data-review-answer" in attrs and f'data-target="{TARGET}"' in attrs
    found = re.search(r'data-questions="([^"]*)"', attrs)
    assert found is not None
    qs = json.loads(html.unescape(found.group(1)))
    assert qs == [{"id": "q-2", "question": REVIEW_QUESTION_WAITING}]
    assert "<form" not in sec and "<textarea" not in sec  # nothing in the static page posts
    assert f'<script src="/session.js" data-api="{API}"></script>' in pages[PAGE]
    js = pages["session.js"]
    assert "data-review-answer" in js and '"/reviews/"' in js and '"/answers"' in js
    assert "signed_in" in js
    # no service: no placeholder at all
    still = render.render_site(site, repo_url=REPO)
    assert "data-review-answer" not in still[PAGE]


# --- the target page's state line ------------------------------------------------------------


def test_the_target_page_shows_the_state_beside_the_grade_linking_the_review(
    pages: dict[str, str],
) -> None:
    head = pages[PROBLEM]
    row = head[
        head.index('<div class="problem-id-row">') : head.index(
            "</div>", head.index('<div class="problem-id-row">')
        )
    ]
    assert STATE_LINE in row
    assert state_line(head) == "review: 4 candidates, 0 clusters, 1 question waiting"
    assert f'href="/problems/{TARGET}/review/"' in row


@pytest.mark.parametrize(
    ("state", "words"),
    [
        (
            {"state": "open", "candidates": 6, "clusters": 1, "questions_waiting": 2},
            "review: 6 candidates, 1 cluster, 2 questions waiting",
        ),
        (
            {"state": "open", "candidates": 1, "clusters": 1, "questions_waiting": 0},
            "review: 1 candidate, 1 cluster, no question waiting",
        ),
        (
            {
                "state": "needs-intent-signer",
                "candidates": 3,
                "clusters": 1,
                "questions_waiting": 2,
            },
            "review: needs an intent signer · 3 candidates, 1 cluster, 2 questions waiting",
        ),
        (
            {"state": "complete", "candidates": 4, "clusters": 1, "questions_waiting": 0},
            "review: complete · 4 candidates, 1 cluster",
        ),
    ],
)
def test_the_state_line_words_for_each_state(
    tmp_path_factory: pytest.TempPathFactory, state: dict[str, object], words: str
) -> None:
    root = fixture.build_with_review(tmp_path_factory.mktemp("state"))
    fixture.publish_review_state(root, state)
    pages = render.render_site(model.load_site(root, COMMIT), repo_url=REPO)
    assert state_line(pages[PROBLEM]) == words


def test_a_target_with_no_review_shows_nothing(tmp_path_factory: pytest.TempPathFactory) -> None:
    root = fixture.build(tmp_path_factory.mktemp("none"))
    pages = render.render_site(model.load_site(root, COMMIT), repo_url=REPO)
    assert STATE_LINE not in pages[PROBLEM] and PAGE not in pages


def test_an_older_graph_json_renders_with_no_line(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    root = fixture.build_with_review(tmp_path_factory.mktemp("older"))
    fixture.publish_v8(root)
    pages = render.render_site(model.load_site(root, COMMIT), repo_url=REPO)
    assert STATE_LINE not in pages[PROBLEM]
    assert PAGE in pages  # the records are on the graph; the page still renders from them


# --- the Docs page ---------------------------------------------------------------------------


def test_docs_has_a_how_a_statement_is_reviewed_section(pages: dict[str, str]) -> None:
    docs = pages["docs/index.html"]
    assert '<h2 id="review">How a statement is reviewed</h2>' in docs
    jump = docs[docs.index('<p class="jump">') : docs.index("</p>", docs.index('<p class="jump">'))]
    assert 'href="#review"' in jump
    start = docs.index('<h2 id="review">')
    sec = docs[start : docs.index("<h2", start + 1)]
    t = text_of(sec)
    assert "candidates" in t and "intent signer" in t and "exhibit" in t
