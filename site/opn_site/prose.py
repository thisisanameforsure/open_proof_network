"""The deliberately tiny prose renderer (F04-T3; R3, R4; Q2).

Contributor text becomes paragraphs and fenced code blocks; nothing else is interpreted. Every
character is escaped, so no markup a contributor writes survives as markup. Correct and safe
beats pretty at Stage 0 (Q2).
"""

from __future__ import annotations

import re
from html import escape

FENCE = "```"
_HEADING_RE = re.compile(r"^(?P<level>#{1,3})\s+(?P<text>.+?)\s*$")
_BULLET_RE = re.compile(r"^-\s+(?P<text>.*)$")
_NUMBERED_RE = re.compile(r"^\d+\.\s+(?P<text>.*)$")
_CONTINUATION_RE = re.compile(r"^\s{2,}(?P<text>\S.*)$")
_CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
_STRONG_RE = re.compile(r"\*\*([^*\n]+)\*\*")


def render(text: str) -> str:
    """Paragraphs separated by blank lines; ``` fences become <pre><code>; all text escaped."""
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


def inline(text: str) -> str:
    """Escaped text with two inline forms: `code` and **strong**. Nothing else is markup."""
    escaped = escape(text, quote=True)
    escaped = _CODE_SPAN_RE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    return _STRONG_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)


#: F04-T19 (Q21): the inline forms a curated record's informal statement may carry, copied from
#: a registry's docstrings. Code is set aside first and math second, so neither is ever read as
#: emphasis; what is left is escaped and then given three forms. A link needs an http(s) url.
_MATH_RE = re.compile(r"(\$\$.+?\$\$|\$[^$\n]+?\$)", re.DOTALL)
_EM_RE = re.compile(r"(?<![\w*])\*([^*\s](?:[^*\n]*[^*\s])?)\*(?![\w*])")
_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)")


def _emphasis(text: str) -> str:
    escaped = escape(text, quote=True)
    escaped = _STRONG_RE.sub(lambda m: f"<strong>{m.group(1)}</strong>", escaped)
    return _EM_RE.sub(lambda m: f"<em>{m.group(1)}</em>", escaped)


def _links(text: str, allowed_urls: frozenset[str]) -> str:
    out: list[str] = []
    at = 0
    for m in _LINK_RE.finditer(text):
        out.append(_emphasis(text[at : m.start()]))
        label, url = _emphasis(m.group(1)), m.group(2)
        # R13: only a url a validated record already cites may leave the site; any other link
        # keeps its words and loses its target, so record prose cannot mint an outbound link.
        out.append(
            f'<a href="{escape(url, quote=True)}">{label}</a>' if url in allowed_urls else label
        )
        at = m.end()
    out.append(_emphasis(text[at:]))
    return "".join(out)


def inline_statement(text: str, *, allowed_urls: frozenset[str]) -> str:
    """A record's informal statement as HTML: escaped, with `code`, **strong**, *emphasis* and
    [cited links](url). Text between dollar signs is passed through escaped and untouched, for
    the same-origin math renderer to read back (T13)."""
    out: list[str] = []
    for i, piece in enumerate(_CODE_SPAN_RE.split(text)):
        if i % 2:  # the inside of a code span
            out.append(f"<code>{escape(piece, quote=True)}</code>")
            continue
        for j, part in enumerate(_MATH_RE.split(piece)):
            out.append(escape(part, quote=True) if j % 2 else _links(part, allowed_urls))
    return "".join(out)


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


def render_document(text: str) -> str:  # noqa: PLR0912, PLR0915 — one branch per line shape
    """The site's own documents (F10-R9) and the graph's AGENTS.md (F04-R9, T10): ``render``'s
    rules plus headings (``#`` to ``###``), bullet and numbered lists with indented continuation
    lines, the two inline forms of ``inline``, fence info strings (``_code_block``) and pipe
    tables (a ``|`` row followed by a ``|---|`` rule). Every character is still escaped; the
    renderer trusts nothing (F04-R3)."""
    out: list[str] = []
    paragraph: list[str] = []
    items: list[str] = []
    list_tag: str | None = None
    code: list[str] | None = None
    info = ""
    lines = text.splitlines()

    def flush_paragraph() -> None:
        if paragraph:
            out.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_tag
        if items and list_tag:
            out.append(
                f"<{list_tag}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{list_tag}>"
            )
        items.clear()
        list_tag = None

    index = 0
    while index < len(lines):
        raw = lines[index]
        index += 1
        line = raw.rstrip()
        if code is not None:
            if _CLOSING_FENCE_RE.match(line.strip()):
                out.append(_code_block(code, info))
                code = None
            else:
                code.append(raw)
            continue
        if line.strip().startswith(FENCE):
            flush_paragraph()
            flush_list()
            code = []
            info = line.strip().lstrip("`").strip()
            continue
        if (
            line.lstrip().startswith("|")
            and index < len(lines)
            and _TABLE_RULE_RE.match(lines[index].strip())
        ):
            flush_paragraph()
            flush_list()
            index += 1  # the rule row
            rows: list[str] = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                rows.append(lines[index])
                index += 1
            out.append(_table(line, rows))
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group("level"))
            out.append(f"<h{level}>{inline(heading.group('text'))}</h{level}>")
            continue
        bullet = _BULLET_RE.match(line)
        numbered = _NUMBERED_RE.match(line)
        if bullet or numbered:
            flush_paragraph()
            tag = "ul" if bullet else "ol"
            if list_tag != tag:
                flush_list()
                list_tag = tag
            match = bullet or numbered
            assert match is not None
            items.append(match.group("text"))
            continue
        continuation = _CONTINUATION_RE.match(raw)
        if continuation and items:
            items[-1] += " " + continuation.group("text")
            continue
        flush_list()
        paragraph.append(line.strip())
    flush_paragraph()
    flush_list()
    if code is not None:  # an unclosed fence is still just text, kept with its info string
        out.append(_code_block(code, info))
    return "\n".join(out)
