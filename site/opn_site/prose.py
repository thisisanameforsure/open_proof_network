"""The deliberately small prose renderer (F04-T3; R3, R4; Q2; F22-T15).

Notes and acknowledgments become paragraphs and fenced code blocks, nothing else interpreted
(Q2). Contributor words (glosses, explainers, annexes) and documents get a small Markdown subset —
headings, nested lists, `code`, math, strong and emphasis — through one block renderer and one
inline renderer. Every character is escaped before any tag is written, so no markup a contributor
writes survives as markup, and no link a contributor writes leaves the site (F04-R13).
"""

from __future__ import annotations

import re
from html import escape

FENCE = "```"
_HEADING_RE = re.compile(r"^(?P<level>#{1,3})\s+(?P<text>.+?)\s*$")
_CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
_STRONG_RE = re.compile(r"\*\*([^*\n]+)\*\*")


def render(text: str, *, math: bool = False) -> str:
    """Contributor text as HTML.

    Without ``math`` (acknowledgments, justifications, notes; Q2): paragraphs separated by blank
    lines and ``` fences as <pre><code>, every character escaped and nothing else interpreted.

    With ``math`` (glosses, explainers and annexes: F19-T6, F22-T15), the words' Markdown subset
    as well: headings (shown as ``h4`` to ``h6``, beneath the page's own), ``-``, ``*`` and ``1.``
    lists nested by indentation, and the inline forms of ``words_inline`` — `code`, ``$…$`` and
    ``$$…$$`` marked ``.math`` for the same-origin renderer (math.js), ``**strong**`` and
    ``*emphasis*``, and a link as its text. A fence is never scanned, and every character is
    escaped before any tag is written."""
    if math:
        return _blocks(text, document=False)
    out: list[str] = []
    paragraph: list[str] = []
    code: list[str] | None = None

    def flush() -> None:
        if paragraph:
            out.append("<p>" + escape(" ".join(paragraph), quote=True) + "</p>")
            paragraph.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if code is not None:
            if line.strip().startswith(FENCE):
                out.append("<pre><code>" + escape("\n".join(code), quote=True) + "</code></pre>")
                code = None
            else:
                code.append(raw)
            continue
        if line.strip().startswith(FENCE):
            flush()
            code = []
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.strip())
    flush()
    if code is not None:  # an unclosed fence is still just text
        out.append("<pre><code>" + escape("\n".join(code), quote=True) + "</code></pre>")
    return "\n".join(out)


def inline_math(text: str) -> str:
    """One line of words as ``render(..., math=True)`` renders a paragraph's inside (F20-T8: a
    gloss's first sentence; an explainer section's heading)."""
    return words_inline(" ".join(text.split()))


def first_sentence(text: str) -> str:
    """F20-T8 (R13): the first sentence of a gloss's prose, for the Problems page's row.

    The first paragraph that is not a heading, up to the first ``.``, ``!`` or ``?`` followed by
    a space or the paragraph's end, never one inside ``$…$`` or a `code` span (a decimal point or
    ``h.2`` ends nothing). A paragraph with no such stop is returned whole."""
    paragraph: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith("#") and not paragraph:
            continue
        paragraph.append(stripped)
    joined = " ".join(paragraph)
    math_open = code_open = False
    for i, ch in enumerate(joined):
        if ch == "`" and not math_open:
            code_open = not code_open
        elif ch == "$" and not code_open:
            math_open = not math_open
        elif (
            ch in ".!?"
            and not math_open
            and not code_open
            and (i + 1 == len(joined) or joined[i + 1] == " ")
        ):
            return joined[: i + 1]
    return joined


#: F04-T19 (Q21): a curated record's dollar rule — any text between two dollar signs on a line,
#: or between ``$$`` pairs — kept as it was when the record's informal statement was first rendered.
_MATH_RE = re.compile(r"(\$\$.+?\$\$|\$[^$\n]+?\$)", re.DOTALL)
#: F19-T6: prose's dollar rule is Pandoc's — an opening ``$`` has a non-space after it, a closing
#: one a non-space before it and no digit after it — so "costs $5 and $6" stays text (the escaping
#: test's ``Costs $5 and ${more}.``). ``$$…$$`` is display math wherever it closes.
_PROSE_MATH_RE = re.compile(r"(\$\$.+?\$\$|\$(?=[^\s$])[^$\n]*?(?<=[^\s$])\$(?!\d))", re.DOTALL)
_EM_RE = re.compile(r"(?<![\w*])\*([^*\s](?:[^*\n]*[^*\s])?)\*(?![\w*])")
_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)")
#: F22-T15: a held piece (code, math, a link's url) is a NUL-delimited index while emphasis is
#: read over the rest; a NUL the writer typed is replaced first, so no text can forge one.
_HOLD_RE = re.compile("\x00(\\d+)\x00")


def _inline(
    text: str,
    *,
    math_re: re.Pattern[str],
    math_span: bool,
    allowed_urls: frozenset[str] | None,
) -> str:
    """The one inline renderer (F22-T15), for words, documents and record statements alike.

    Code spans are held first, then math (``math_re``), then links; what is left is escaped, then
    ``**strong**`` and ``*emphasis*`` are read over it, so a pair may span a held piece
    (``**$x$ is prime**``) and nothing inside code or math is ever emphasis. Held pieces are
    escaped when held. Math is wrapped in ``.math`` when ``math_span`` (the caller's text is not
    already inside one). A link is an anchor only when ``allowed_urls`` names its url (a
    validated record's citation, F04-R13); with ``allowed_urls`` None it is its text and its url
    as text, and otherwise its text alone."""
    held: list[str] = []

    def hold(html: str) -> str:
        held.append(html)
        return f"\x00{len(held) - 1}\x00"

    def link(m: re.Match[str]) -> str:
        label, url = m.group(1), m.group(2)
        if "\x00" in url:  # a held piece inside a url: not a link form at all
            return m.group(0)
        if allowed_urls is None:
            return f"{label} ({hold(escape(url, quote=True))})"
        if url in allowed_urls:
            return hold(
                f'<a href="{escape(url, quote=True)}">{_emphasis(escape(label, quote=True))}</a>'
            )
        return label

    text = text.replace("\x00", "\ufffd")
    pieces: list[str] = []
    for i, piece in enumerate(_CODE_SPAN_RE.split(text)):
        if i % 2:  # the inside of a code span: text, never math or emphasis
            pieces.append(hold(f"<code>{escape(piece, quote=True)}</code>"))
            continue
        for j, part in enumerate(math_re.split(piece)):
            if j % 2:
                escaped = escape(part, quote=True)
                pieces.append(
                    hold(f'<span class="math">{escaped}</span>' if math_span else escaped)
                )
            else:
                pieces.append(part)
    body = _emphasis(escape(_LINK_RE.sub(link, "".join(pieces)), quote=True))
    for _ in range(2):  # a link's label may itself hold a code span or math
        body = _HOLD_RE.sub(lambda m: held[int(m.group(1))], body)
    return body


def _emphasis(escaped: str) -> str:
    """``**strong**`` then ``*emphasis*``, over text already escaped."""
    escaped = _STRONG_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)
    return _EM_RE.sub(lambda m: f"<em>{m.group(1)}</em>", escaped)


def words_inline(text: str) -> str:
    """A contributor's inline Markdown (F22-T15): `code`, math marked ``.math``, strong and
    emphasis, a link as its text and url; everything escaped first."""
    return _inline(text, math_re=_PROSE_MATH_RE, math_span=True, allowed_urls=None)


def inline(text: str) -> str:
    """A document's inline forms (tables, summaries): the same as ``words_inline``."""
    return words_inline(text)


def inline_statement(text: str, *, allowed_urls: frozenset[str]) -> str:
    """A record's informal statement as HTML: escaped, with `code`, **strong**, *emphasis* and
    [cited links](url). Text between dollar signs is passed through escaped and untouched, for
    the same-origin math renderer to read back from the ``.math`` element the caller wraps the
    whole statement in (T13)."""
    return _inline(text, math_re=_MATH_RE, math_span=False, allowed_urls=allowed_urls)


#: F04-T10: the label an ``output`` fence carries. The guide's output blocks are fragments a
#: reader should find in what the command printed, not a transcript of it (F10-R9).
OUTPUT_LABEL = "expected output (fragments)"
_CLOSING_FENCE_RE = re.compile(r"^`{3,}$")
_INFO_WORD_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_TABLE_RULE_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")


def _code_block(code: list[str], info: str) -> str:
    """A fenced block, escaped, with its info string kept: ``output`` is labelled, and the first
    word of any other info string becomes a class (``sh`` → ``fence-sh``) when it is a plain word.
    Backticks are written as ``&#96;`` so a fence quoted inside a block (``echo '```json'``) never
    reaches the page as a literal fence; a browser shows the same character."""
    body = escape("\n".join(code), quote=True).replace("`", "&#96;")
    words = info.split()
    first = words[0].lower() if words else ""
    if first == "output":
        return (
            f'<p class="fence-label">{OUTPUT_LABEL}</p>'
            f'<pre class="fence-output"><code>{body}</code></pre>'
        )
    if first and _INFO_WORD_RE.match(first):
        return f'<pre class="fence-{first}"><code>{body}</code></pre>'
    return f"<pre><code>{body}</code></pre>"


def table_cells(line: str) -> list[str]:
    """A pipe-table row's cells. A pipe inside a backtick code span, or written ``\\|``, belongs to
    the cell; the outer pipes of ``| a | b |`` delimit nothing."""
    cells: list[str] = []
    cell: list[str] = []
    in_code = False
    i = 0
    stripped = line.strip()
    while i < len(stripped):
        ch = stripped[i]
        if ch == "\\" and i + 1 < len(stripped) and stripped[i + 1] == "|":
            cell.append("|")
            i += 2
            continue
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(ch)
        i += 1
    cells.append("".join(cell).strip())
    if stripped.startswith("|"):
        cells = cells[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|") and cells:
        cells = cells[:-1]
    return cells


def _table(header: str, rows: list[str]) -> str:
    heads = table_cells(header)
    width = len(heads)
    head = "".join(f"<th>{inline(c)}</th>" for c in heads)
    body = []
    for row in rows:
        cells = (table_cells(row) + [""] * width)[:width]
        body.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
    return (
        f'<div class="table-wrap"><table class="doc"><thead><tr>{head}</tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


_SLUG_DROP_RE = re.compile(r"[^a-z0-9]+")


def heading_slug(text: str) -> str:
    """A level-2 heading's anchor: its words before any parenthesised citation, lower-cased,
    every run of other characters one hyphen. ``Glosses, explainers and outlines (D-3 v3.30)``
    is ``glosses-explainers-and-outlines``, so a new citation never moves the anchor (F20-T12).
    The alphabet is ``[a-z0-9-]``, so the id needs no escaping."""
    words = text.split(" (", 1)[0]
    return _SLUG_DROP_RE.sub("-", words.lower()).strip("-")


def render_document(text: str, *, anchors: str | None = None) -> str:
    """The site's own documents (F10-R9) and the graph's AGENTS.md (F04-R9, T10): the words'
    Markdown subset (``render(..., math=True)``, math included since F22-T15) with headings at
    their own levels (``#`` to ``###``), fence info strings (``_code_block``) and pipe tables (a
    ``|`` row followed by a ``|---|`` rule). Every character is still escaped; the renderer trusts
    nothing (F04-R3).

    With ``anchors`` (a prefix), each level-2 heading carries ``id="<prefix><heading_slug>"``,
    the first of any two that would share one, so a page can link a section of the guide
    (F20-Q16(a)); the prefix keeps the guide's ids apart from the page's own."""
    return _blocks(text, document=True, anchors=anchors)


#: F22-T15: a list item — ``-``, ``*`` or ``1.`` and a space, after any indentation, which nests.
_ITEM_RE = re.compile(r"^(?P<indent>[ \t]*)(?:(?P<bullet>[-*])|\d{1,9}\.)\s+(?P<text>\S.*)$")
#: An opening ``$`` that has not closed yet: a non-space, non-digit after it (so "$5" opens
#: nothing), and no backslash or dollar before it.
_OPEN_DOLLAR_RE = re.compile(r"(?<![\\$])\$(?=[^\s$\d])")


def _math_open(text: str) -> bool:
    """Whether a block's text so far leaves math open, so its next line belongs to the math and
    is never read as a list item or a heading (``- `` inside ``$$…$$`` is not a list)."""
    rest = _PROSE_MATH_RE.sub("", _CODE_SPAN_RE.sub("", text))
    return "$$" in rest or bool(_OPEN_DOLLAR_RE.search(rest))


def _indent(spaces: str) -> int:
    return len(spaces.replace("\t", "    "))


def _blocks(  # noqa: PLR0912, PLR0915 — one branch per line shape
    text: str, *, document: bool, anchors: str | None = None
) -> str:
    """Block structure shared by words and documents (F22-T15): fences, paragraphs, headings,
    lists nested by indentation (an indented line continues the deepest item, an unindented one
    ends the list, a blank line between items keeps it), and, in a document, pipe tables and
    anchored headings. A line inside open math continues its block whatever it starts with.
    Inline text goes through ``words_inline``; every block is joined by a newline."""
    out: list[str] = []
    seen_ids: set[str] = set()
    paragraph: list[str] = []
    item: list[str] = []  # the deepest open item's text not yet written
    stack: list[tuple[int, str]] = []  # the open lists: indentation and tag
    current: list[str] = []  # the fragments of the outermost open list
    code: list[str] | None = None
    info = ""
    lines = text.splitlines()

    def flush_paragraph() -> None:
        if paragraph:
            out.append("<p>" + words_inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def flush_item() -> None:
        if item:
            current.append(words_inline(" ".join(item)))
            item.clear()

    def close_top() -> None:
        flush_item()
        tag = stack.pop()[1]
        current.append(f"</li></{tag}>")
        if not stack:
            out.append("".join(current))
            current.clear()

    def close_lists() -> None:
        while stack:
            close_top()

    def fence(body: list[str], info_: str) -> str:
        if document:
            return _code_block(body, info_)
        return "<pre><code>" + escape("\n".join(body), quote=True) + "</code></pre>"

    index = 0
    while index < len(lines):
        raw = lines[index]
        index += 1
        line = raw.rstrip()
        stripped = line.strip()
        if code is not None:
            closing = _CLOSING_FENCE_RE.match(stripped) if document else stripped.startswith(FENCE)
            if closing:
                out.append(fence(code, info))
                code = None
            else:
                code.append(raw)
            continue
        block = item if stack else paragraph
        if stripped and block and _math_open(" ".join(block)):
            block.append(stripped)
            continue
        if stripped.startswith(FENCE):
            flush_paragraph()
            close_lists()
            code = []
            info = stripped.lstrip("`").strip()
            continue
        if (
            document
            and line.lstrip().startswith("|")
            and index < len(lines)
            and _TABLE_RULE_RE.match(lines[index].strip())
        ):
            flush_paragraph()
            close_lists()
            index += 1  # the rule row
            rows: list[str] = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                rows.append(lines[index])
                index += 1
            out.append(_table(line, rows))
            continue
        if not stripped:
            flush_paragraph()
            continue  # a list stays open until a line that is not part of it
        heading = _HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            close_lists()
            level = len(heading.group("level"))
            attr = ""
            if document and anchors is not None and level == 2:  # a section of the document
                slug = heading_slug(heading.group("text"))
                if slug and anchors + slug not in seen_ids:
                    seen_ids.add(anchors + slug)
                    attr = f' id="{escape(anchors + slug, quote=True)}"'
            if not document:
                level += 3  # words sit beneath the page's own headings
            out.append(f"<h{level}{attr}>{words_inline(heading.group('text'))}</h{level}>")
            continue
        marker = _ITEM_RE.match(line)
        if marker:
            flush_paragraph()
            flush_item()
            depth = _indent(marker.group("indent"))
            tag = "ul" if marker.group("bullet") else "ol"
            while stack and stack[-1][0] > depth:
                close_top()
            if stack and stack[-1][0] == depth and stack[-1][1] != tag:
                close_top()
            if stack and stack[-1][0] == depth:
                current.append("</li><li>")
            else:  # a new list, at the top level or nested in the open item
                current.append(f"<{tag}><li>")
                stack.append((depth, tag))
            item.append(marker.group("text").strip())
            continue
        if stack and _indent(raw[: len(raw) - len(raw.lstrip())]) >= 2:
            item.append(stripped)  # an indented line continues the deepest item
            continue
        close_lists()
        paragraph.append(stripped)
    flush_paragraph()
    close_lists()
    if code is not None:  # an unclosed fence is still just text, kept with its info string
        out.append(fence(code, info))
    return "\n".join(out)
