"""D-3 node layout validation (F00-R1) and the statement parser both step 2 and step 5 rely on.

A node directory is::

    nodes/<node-id>/
      META.yaml        required; validates against meta/v1; id == directory name
      Statement.lean   required; one theorem with body `sorry`; content-hashed into META
      Witness.lean     required (checked by F01)
      Context.lean     required (checked by F01)
      Proof.lean       optional: absent until a proof merges; the only submittable file
      Relation.lean    optional: variants only (D-30, F08)
      relevance.yaml   optional: a related variant's one signature (D-30 v3.12, F12-R13)
      CONTEXT.json     optional: the bot-owned context bundle (F10-R3, Q2); never a submission path
      attempts/  annex/  explainer/   required directories (may hold only .gitkeep)
      waivers/         optional (F02)
      status/          optional: curator and adjudication records (F03); never a submission path
      revisions/       optional: D-8 revision requests (F08-R6), appended by anyone
      defects/         optional: D-16 defect claims (F08-R7), appended by anyone
      proposed-for/    optional: which node of the target this one was proposed for (F18-R8,
                       D-14 v3.26), appended by its proposer or a curator

Anything else is an extra entry and is named in the diagnostic.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from opn_gate import schemas
from opn_gate.diagnostic import Diagnostic

REQUIRED_FILES: tuple[str, ...] = ("META.yaml", "Statement.lean", "Witness.lean", "Context.lean")
#: CONTEXT.json is written by the post-merge job (F10-R3) and, like META.yaml's status line, is a
#: rendering the layout tolerates but no submission may touch (F10-Q2; ``paths`` refuses it).
CONTEXT_FILE = "CONTEXT.json"
#: relevance.yaml is a related variant's one signature (F12-R13, D-30 v3.12), a curator's record.
RELEVANCE_FILE = "relevance.yaml"
OPTIONAL_FILES: tuple[str, ...] = ("Proof.lean", "Relation.lean", CONTEXT_FILE, RELEVANCE_FILE)
REQUIRED_DIRS: tuple[str, ...] = ("attempts", "annex", "explainer")
#: status/: curator records (F03-Q3); revisions/ and defects/: D-8 and D-16 records (F08);
#: proposed-for/: F18-R8's pointer records (D-3 v3.26); withdrawals/: F08-T31's (D-18 v3.27);
#: gloss/: prose about the node's Lean files, on a node of any status (F20-R1, D-3 v3.30).
OPTIONAL_DIRS: tuple[str, ...] = (
    "waivers",
    "status",
    "revisions",
    "defects",
    "proposed-for",
    "withdrawals",
    "gloss",
)
KEEP_FILE = ".gitkeep"
#: v2 added acknowledged_hazards (F02-R6); v3 added the skeleton-hole origin (D-3 v3.12); v4
#: added supersedes (F08-R9, D-8); v5 added a hole's proved_binders (D-29 v3.22, F07-T44).
META_SCHEMAS: tuple[str, ...] = ("meta/v1", "meta/v2", "meta/v3", "meta/v4", "meta/v5")

_THEOREM_RE = re.compile(r"^(?:theorem|lemma)\s+(?P<name>[^\s:({\[]+)", re.M)
_IMPORT_RE = re.compile(r"^import\s+(?P<module>\S+)", re.M)

#: Module-name contract (F01-Q2): where a constant lives says what it is.
LIBRARY_PREFIXES: tuple[str, ...] = ("Init", "Std", "Lean", "Mathlib", "Batteries", "Aesop")
DEFS_PREFIX = "Defs"
NODES_PREFIX = "Nodes"
_NAMESPACE_RE = re.compile(r"^(namespace|end)\s+(?P<name>\S+)\s*$", re.M)
_SORRY_BODY_RE = re.compile(r":=\s*(?:by\s+)?sorry\b")
#: ``sorry`` as a whole token: not a piece of ``sorryAx`` or ``unsorry``, nor a field of a name.
_SORRY_TOKEN_RE = re.compile(r"(?<![\w'.!?])sorry(?![\w'.!?])")


def strip_comments(text: str) -> str:
    """``text`` with every Lean comment and string-literal body blanked: ``--`` to the end of
    its line, ``/- -/`` blocks — nested, and including the ``/-!`` and ``/--`` doc forms — and
    the inside of ``"..."``, so a ``--`` in a string does not swallow the rest of the line and a
    word in one is not a token. Newlines survive, so line numbers mean the same as in the
    source."""
    out: list[str] = []
    i, n, depth = 0, len(text), 0
    while i < n:
        c = text[i]
        pair = text[i : i + 2]
        if depth:
            if pair == "/-":
                depth += 1
                i += 2
            elif pair == "-/":
                depth -= 1
                i += 2
            else:
                out.append(c if c == "\n" else " ")
                i += 1
        elif pair == "/-":
            depth = 1
            i += 2
        elif pair == "--":
            end = text.find("\n", i)
            i = n if end == -1 else end
        elif c == '"':
            end = i + 1
            while end < n and text[end] != '"':
                end += 2 if text[end] == "\\" else 1
            body = text[i + 1 : end]
            out.append('"' + "".join(ch if ch == "\n" else " " for ch in body) + '"')
            i = end + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def mentions_sorry(text: str) -> bool:
    """Whether ``text`` uses ``sorry`` as a token in code — a comment that names the word (the
    witness slot's own header does) and identifiers that contain it do not count. The one
    reading of "the witness is still a stub" the gate takes from text; the kernel's word on
    ``sorryAx`` is the witness step's (F01)."""
    return _SORRY_TOKEN_RE.search(strip_comments(text)) is not None


@dataclass(frozen=True)
class Statement:
    """What Statement.lean declares: the theorem's full name and where its body starts."""

    decl_name: str
    text: str
    prefix: str  # everything up to and including the `:=` that opens the sorry body
    suffix: str  # everything after the `sorry` token (trailing `end` lines, whitespace)

    @property
    def statement_hash(self) -> str:
        return schemas.content_hash(self.text.encode("utf-8"))


@dataclass(frozen=True)
class Node:
    node_id: str
    target_id: str
    path: Path
    meta: dict[str, object]
    statement: Statement

    @property
    def proof_path(self) -> Path:
        return self.path / "Proof.lean"


def _qualified(text: str, up_to: int, name: str) -> str:
    """``name`` under whatever namespaces are open at offset ``up_to``."""
    stack: list[str] = []
    for m in _NAMESPACE_RE.finditer(text[:up_to]):
        if m.group(1) == "namespace":
            stack.append(m.group("name"))
        elif stack and stack[-1] == m.group("name"):
            stack.pop()
    return ".".join([*stack, name])


def parse_declaration(text: str, what: str = "the file") -> str | Diagnostic:
    """The full name of the one theorem ``text`` declares (F07-R4 reads a submitted artifact's).

    Unlike ``parse_statement`` this says nothing about the body: an artifact's body is whatever
    it is, and the gate's opinion of it comes from the kernel, not from a regular expression.
    """
    theorems = list(_THEOREM_RE.finditer(text))
    if len(theorems) != 1:
        return Diagnostic(
            "artifact-shape",
            f"{what} must declare exactly one theorem, found {len(theorems)}",
            {"found": len(theorems)},
        )
    return _qualified(text, theorems[0].start(), theorems[0].group("name"))


def parse_statement(text: str) -> Statement | Diagnostic:
    """Find the single sorry-bodied theorem in ``text`` (F00-R19's shape)."""
    theorems = list(_THEOREM_RE.finditer(text))
    if len(theorems) != 1:
        return Diagnostic(
            "statement-shape",
            f"Statement.lean must declare exactly one theorem, found {len(theorems)}",
        )
    bodies = list(_SORRY_BODY_RE.finditer(text))
    if len(bodies) != 1:
        return Diagnostic(
            "statement-shape",
            f"Statement.lean must have exactly one `:= sorry` body, found {len(bodies)}",
        )
    body = bodies[0]
    if body.start() < theorems[0].end():
        return Diagnostic("statement-shape", "the sorry body precedes the theorem")
    full_name = _qualified(text, theorems[0].start(), theorems[0].group("name"))
    return Statement(
        decl_name=full_name,
        text=text,
        prefix=text[: body.start() + 2],
        suffix=text[body.end() :],
    )


def node_module(node_id: str, file_stem: str) -> str:
    """The module name of ``nodes/<node_id>/<file_stem>.lean``: ``Nodes.«<id>».<stem>``."""
    return f"{NODES_PREFIX}.«{node_id}».{file_stem}"


def module_origin(module: str) -> tuple[str, str | None]:
    """Classify a module name (F01-Q2): ``("library"|"defs"|"node"|"other", node_id)``."""
    head, _, rest = module.partition(".")
    if head in LIBRARY_PREFIXES:
        return "library", None
    if head == DEFS_PREFIX:
        return "defs", None
    if head == NODES_PREFIX and rest:
        node_id = rest.split(".", 1)[0].strip("«»")
        return "node", node_id
    return "other", None


def imports_of(text: str) -> list[str]:
    return [m.group("module") for m in _IMPORT_RE.finditer(text)]


#: The one module of another node an artifact may import: that node's merged proof (F08-R18).
USED_STEM = "Proof"

_DEFS_USE = rf"{DEFS_PREFIX}\.[A-Za-z_][A-Za-z0-9_']*"
_NODE_USE = rf"{NODES_PREFIX}\.«[a-z0-9][a-z0-9-]*»\.{USED_STEM}"
#: One use line, without its newline: the module it names (F08-R16, R18).
USE_LINE_RE = re.compile(rf"import[ \t]+(?P<module>{_DEFS_USE}|{_NODE_USE})[ \t]*")


def used_node(module: str) -> str | None:
    """The node ``Nodes.«<id>».Proof`` names; ``None`` for any other module."""
    kind, node_id = module_origin(module)
    if kind != "node" or node_id is None or module != node_module(node_id, USED_STEM):
        return None
    return node_id


def _imports_end(text: str) -> int:
    """The offset just past ``text``'s last ``import`` line; 0 when it has none."""
    end = 0
    offset = 0
    for line in text.splitlines(keepends=True):
        offset += len(line)
        if line.startswith("import "):
            end = offset
    return end


def split_uses(prefix: str, text: str, node_id: str | None) -> tuple[str, tuple[str, ...]]:
    """``text`` with its use lines removed, and the modules they name, in the order written.

    ``prefix`` is the statement's text up to its ``:=`` (``Statement.prefix``). The use lines
    are the run of lines directly after the statement's last import, or after the node's own
    ``Context`` line where the artifact adds it (F00-T10), each matching ``USE_LINE_RE``. They
    are taken out only when what remains begins with the header the gate already takes; any
    other text comes back unchanged with no uses, so step 2's own diagnostic stands.

    This is the one reading of a use: step 2 takes a submission's uses from it, and the graph,
    the build and the layout take a merged proof's from it. A line of the same shape anywhere
    else in a file (in a comment, below the theorem) is no import to Lean and no use to anyone.
    """
    bases = [prefix]
    if node_id is not None:
        allowed = with_own_context(prefix, node_id)
        if allowed != prefix:
            bases.append(allowed)
    for base in bases:
        at = _imports_end(base)
        if not text.startswith(base[:at]):
            continue
        modules: list[str] = []
        pos = at
        while True:
            end = text.find("\n", pos)
            if end == -1:
                break
            line = USE_LINE_RE.fullmatch(text[pos:end])
            if line is None:
                break
            modules.append(line.group("module"))
            pos = end + 1
        rest = base[:at] + text[pos:]
        if modules and rest.startswith(base):
            return rest, tuple(modules)
    return text, ()


def node_uses(statement: Statement | Diagnostic, text: str, own: str) -> tuple[str, ...]:
    """The other nodes whose merged proof an artifact of ``statement`` uses: its use lines
    that name ``Nodes.«<id>».Proof`` (``split_uses``), in order, each once; never ``own``.
    None for a text that is not the statement with use lines (a counterexample, a vacuity
    certificate), and none when the statement itself does not parse."""
    if not isinstance(statement, Statement):
        return ()
    found: list[str] = []
    for module in split_uses(statement.prefix, text, own)[1]:
        node_id = used_node(module)
        if node_id is not None and node_id != own and node_id not in found:
            found.append(node_id)
    return tuple(found)


def merged_uses(node_dir: Path) -> tuple[str, ...]:
    """The nodes a node's merged ``Proof.lean`` uses, read from the tree; none for a node
    without one. This is the graph's only record of a use (F08-R19)."""
    proof, statement = node_dir / "Proof.lean", node_dir / "Statement.lean"
    if not proof.is_file() or not statement.is_file():
        return ()
    return node_uses(
        parse_statement(statement.read_text(encoding="utf-8")),
        proof.read_text(encoding="utf-8"),
        node_dir.name,
    )


def imports_own_context(node_id: str, text: str) -> bool:
    """Whether ``text`` imports the node's own ``Context``: the one module through which a node
    reaches its dependencies and, once a skeleton of it merges, its holes (F08-T13, F07-T23)."""
    return node_module(node_id, "Context") in imports_of(text)


def with_own_context(text: str, node_id: str) -> str:
    """``text`` importing the node's own ``Context``, after its last import line or leading the
    file when it has none (Lean takes imports first). The one place the line may go: the service
    writes a proposed statement with it (F08-T12), and step 2 allows a proof exactly this header
    when its statement predates the line (F00-T10)."""
    own = f"import {node_module(node_id, 'Context')}"
    lines = text.splitlines(keepends=True)
    if any(line.strip() == own for line in lines):
        return text
    imports = [i for i, line in enumerate(lines) if line.startswith("import ")]
    at = imports[-1] + 1 if imports else 0
    gap = "" if imports or not lines or not lines[0].strip() else "\n"
    return "".join([*lines[:at], own + "\n" + gap, *lines[at:]])


def check_imports(node_dir: Path, node_id: str) -> list[Diagnostic]:
    """Every import in a node file must be library, ``Defs.*``, or the node's own Context —
    and, in ``Proof.lean`` alone, another node's ``Proof`` module where a use line stands
    (F08-R18; ``split_uses``). A line of that shape anywhere else is refused as it always was.
    Whether the node may be used is step 2's question of a submission (``opn_gate.uses``);
    this is the layout's, of any tree."""
    found: list[Diagnostic] = []
    own_context = node_module(node_id, "Context")
    for name in ("Statement.lean", "Proof.lean", "Witness.lean", "Context.lean"):
        path = node_dir / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        used = (
            {node_module(n, USED_STEM) for n in merged_uses(node_dir)}
            if name == "Proof.lean"
            else set()
        )
        for module in imports_of(text):
            kind, _ = module_origin(module)
            allowed = (
                kind in ("library", "defs")
                or (name != "Context.lean" and module == own_context)
                or module in used
            )
            if not allowed:
                found.append(
                    Diagnostic(
                        "import-forbidden",
                        f"{name} imports {module}; allowed: library modules, Defs.*"
                        + ("" if name == "Context.lean" else f", {own_context}")
                        + (
                            ", another node's Proof module as a use line of a proof (F08-R18)"
                            if name == "Proof.lean"
                            else ""
                        ),
                        {"file": name, "module": module},
                    )
                )
    return found


# --- D-3 v3.28 (F08-T37): what a statement may hold ---------------------------------------------

#: The two files of a node the judges import as modules of record (D-4 v3.27), whose every
#: command step 2 reads.
COMMAND_CHECKED_FILES: tuple[str, ...] = ("Statement.lean", "Context.lean")
STATEMENT_COMMAND_CODE = "statement-command-forbidden"
#: Commands a line may open with, and which end at the end of that line.
_HEADER_COMMANDS = frozenset({"import", "open", "namespace", "end"})
#: The declarations: the statement's theorem, or a Context's dependency signatures.
_DECL_COMMANDS = frozenset({"theorem", "lemma"})
#: Term keywords whose binding takes a ``:=`` of its own inside a declaration's type.
_BINDING_WORDS = frozenset({"let", "have", "letI", "haveI"})
#: The words an ``open`` line may hold besides the names it opens.
_OPEN_WORDS = frozenset({"scoped", "hiding", "renaming", "in"})
#: Words that open a command in Lean, its core library or Mathlib and never stand in a term. At a
#: file's top level anything outside the four header commands and the declarations is refused
#: whatever it is; this list is what is also refused *inside* a declaration's type, where a
#: command could only appear after a parse error (which admission refuses anyway), and inside an
#: ``open`` line, where Lean would end the ``open`` and start the command.
_COMMAND_WORDS = frozenset(
    {
        "abbrev", "add_aesop_rules", "add_decl_doc", "alias", "assert_not_exists",
        "assert_not_imported", "attribute", "axiom", "builtin_initialize", "class",
        "coinductive", "compile_inductive", "declare_aesop_rule_sets", "declare_syntax_cat",
        "def", "deriving", "dsimproc", "elab", "elab_rules", "example", "export", "import",
        "include", "inductive", "infix", "infixl", "infixr", "initialize",
        "initialize_simps_projections", "instance", "irreducible_def", "lemma", "library_note",
        "local", "macro", "macro_rules", "mutual", "namespace", "noncomputable", "notation",
        "notation3", "omit", "opaque", "partial", "postfix", "prefix", "private", "proof_wanted",
        "protected", "recall", "register_option", "register_simp_attr", "run_cmd", "run_elab",
        "run_meta", "seal", "section", "set_option", "simproc", "structure", "suppress_compilation",
        "syntax", "theorem", "universe", "unsafe", "unseal", "variable",
    }
)  # fmt: skip
_IDENT_CHARS = r"\w'!?.«»"
_TOKEN_RE = re.compile(
    rf"(?P<hash>#[^\W\d][\w]*)|(?P<attr>@\[)|(?P<assign>:=)"
    rf"|(?P<ident>(?:[^\W\d]|«)[{_IDENT_CHARS}]*)"
    r"|(?P<open>[(\[{⟨⦃⟦])|(?P<close>[)\]}⟩⦄⟧])|(?P<other>\S)"
)
_SPACE_RE = re.compile(r"\s*")
_SORRY_AFTER_RE = re.compile(rf"\s*(?:by\s+)?sorry(?![{_IDENT_CHARS}])")
_HEADER_LINE_RE: dict[str, re.Pattern[str]] = {
    "import": re.compile(rf"[ \t]+[{_IDENT_CHARS}]+\s*"),
    "namespace": re.compile(rf"[ \t]+[{_IDENT_CHARS}]+\s*"),
    "end": re.compile(rf"(?:[ \t]+[{_IDENT_CHARS}]+)?\s*"),
}
_OPEN_PART_RE = re.compile(r"[()]|→|->|[^\s()]+")
_NAME_RE = re.compile(rf"(?:[^\W\d]|«)[{_IDENT_CHARS}]*")
_CHAR_LITERAL_RE = re.compile(r"'(?:\\(?:u\{[0-9a-fA-F]+\}|x[0-9a-fA-F]{2}|.)|[^\\'\n])'")
_RAW_STRING_RE = re.compile(r'r(?P<hashes>#*)"')


@dataclass(frozen=True)
class CommandOffence:
    """One command a statement may not hold: where it starts, and what it is."""

    line: int
    command: str
    reason: str


def _blank(text: str) -> str:
    return "".join(c if c == "\n" else " " for c in text)


def code_mask(text: str) -> str:  # noqa: PLR0912 — one branch per lexical form
    """``text`` as Lean's command parser sees its code: comments (nested, and the ``/--`` and
    ``/-!`` doc forms), string, raw-string and character literal bodies blanked, and the inside of
    every ``«»`` name made one identifier, at the same length and with every newline kept, so an
    offset and a line number mean what they meant in the source. Unlike ``strip_comments`` it
    reads a ``'"'`` as a character and not as the start of a string, so no text can hide a
    command from the scan behind a quote Lean does not see."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        prev = text[i - 1] if i else " "
        follows_name = prev.isalnum() or prev in "_'!?.»"
        if text.startswith("/-", i):
            j, depth = i + 2, 1
            while j < n and depth:
                if text.startswith("/-", j):
                    depth, j = depth + 1, j + 2
                elif text.startswith("-/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            out.append(_blank(text[i:j]))
            i = j
        elif text.startswith("--", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append(_blank(text[i:j]))
            i = j
        elif c == "r" and not follows_name and (raw := _RAW_STRING_RE.match(text, i)):
            close = '"' + raw.group("hashes")
            j = text.find(close, raw.end())
            j = n if j == -1 else j + len(close)
            out.append('"' + _blank(text[i + 1 : j]))
            i = j
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            out.append('"' + _blank(text[i + 1 : j]))
            i = j
        elif c == "'" and not follows_name and (char := _CHAR_LITERAL_RE.match(text, i)):
            out.append("'" + _blank(char.group()[1:-1]) + "'")
            i = char.end()
        elif c == "«":
            j = text.find("»", i)
            j = n if j == -1 else j + 1
            out.append("«" + "".join(ch if ch in "\n»" else "_" for ch in text[i + 1 : j]))
            i = j
        else:
            out.append(c)
            i += 1
    masked = "".join(out)
    assert len(masked) == len(text), "the mask keeps every offset"
    return masked


def forbidden_commands(text: str) -> list[CommandOffence]:
    """Every command ``text`` holds beyond D-3's list (v3.28): imports, ``open``, ``namespace``
    and ``end`` lines, doc comments, and theorems whose body is ``sorry``. ``[]`` when the file
    holds nothing else.

    The file is read as a sequence of commands. A header command runs to the end of its line and
    holds names only. A declaration runs from ``theorem`` (or ``lemma``) to its body: the first
    ``:=`` outside brackets that is not a ``let`` or ``have`` binding's, which must be followed
    by ``sorry`` (or ``by sorry``). Any other token where a command starts is refused, and so is
    an attribute, or a command word, inside a declaration's type. Because a declaration can only
    end at its ``:= sorry``, a command could follow one only after a parse error, which makes the
    file one admission refuses for not elaborating; the scan is the guarantee for every file
    that does."""
    mask = code_mask(text)
    starts = [0, *(i + 1 for i, c in enumerate(mask) if c == "\n")]

    def line_of(offset: int) -> int:
        lo, hi = 0, len(starts)
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if starts[mid] <= offset:
                lo = mid
            else:
                hi = mid
        return lo + 1

    def end_of_line(offset: int) -> int:
        eol = mask.find("\n", offset)
        return len(mask) if eol == -1 else eol

    found: list[CommandOffence] = []
    pos, n = 0, len(mask)
    while True:
        pos = _SPACE_RE.match(mask, pos).end()  # type: ignore[union-attr]  # \s* always matches
        if pos >= n:
            return found
        tok = _TOKEN_RE.match(mask, pos)
        assert tok is not None, "every non-space character is a token"
        kind, word = tok.lastgroup, tok.group()
        if kind == "ident" and word in _HEADER_COMMANDS:
            eol = end_of_line(tok.end())
            bad = _header_problem(word, mask[tok.end() : eol])
            if bad is not None:
                found.append(
                    CommandOffence(line_of(pos), bad, f"may not stand in an `{word}` line")
                )
            pos = eol
        elif kind == "ident" and word in _DECL_COMMANDS:
            pos, offence = _declaration(mask, tok.end(), line_of)
            if offence is not None:
                found.append(offence)
                pos = end_of_line(pos)
        else:
            shown = word if kind in ("ident", "hash") else mask[pos : end_of_line(pos)].split()[0]
            found.append(
                CommandOffence(line_of(pos), shown[:40], "is not a command a statement may hold")
            )
            pos = end_of_line(pos)


def _header_problem(word: str, rest: str) -> str | None:
    """The first thing in an ``import``/``namespace``/``end``/``open`` line's rest that is not
    a name it may hold, or ``None``."""
    if word in _HEADER_LINE_RE:
        if _HEADER_LINE_RE[word].fullmatch(rest):
            return None
        parts = rest.split()
        return parts[1] if len(parts) > 1 else (parts[0] if parts else word)
    parts = _OPEN_PART_RE.findall(rest)
    if not parts:
        return word
    for part in parts:
        if part in _OPEN_WORDS or part in ("(", ")", "→", "->"):
            continue
        if not _NAME_RE.fullmatch(part) or part in _COMMAND_WORDS:
            return part
    return None


def _declaration(
    mask: str, start: int, line_of: Callable[[int], int]
) -> tuple[int, CommandOffence | None]:
    """Scan a declaration from just after its keyword to just past its ``sorry`` body."""
    depth = pending = 0
    pos, n = start, len(mask)
    while True:
        pos = _SPACE_RE.match(mask, pos).end()  # type: ignore[union-attr]  # \s* always matches
        if pos >= n:
            return n, CommandOffence(line_of(start), "theorem", "has no `sorry` body")
        tok = _TOKEN_RE.match(mask, pos)
        assert tok is not None, "every non-space character is a token"
        kind, word = tok.lastgroup, tok.group()
        if kind == "open":
            depth += 1
        elif kind == "close":
            depth = max(0, depth - 1)
        elif kind == "attr":
            return pos, CommandOffence(
                line_of(pos), "@[", "is an attribute, which a statement may not set"
            )
        elif kind == "ident" and word in _COMMAND_WORDS:
            return pos, CommandOffence(line_of(pos), word, "may not stand in a declaration's type")
        elif kind == "ident" and word in _BINDING_WORDS and depth == 0:
            pending += 1
        elif kind == "assign" and depth == 0:
            if pending:
                pending -= 1
            else:
                body = _SORRY_AFTER_RE.match(mask, tok.end())
                if body is not None:
                    return body.end(), None
                return pos, CommandOffence(line_of(pos), "theorem", "has a body other than `sorry`")
        pos = tok.end()


def command_problem(name: str, text: str) -> Diagnostic | None:
    """Step 2's refusal of a ``Statement.lean`` or ``Context.lean`` that holds a command beyond
    D-3's list (v3.28), naming the first one, its line and every other; ``None`` when it holds
    none. The service refuses a proposal by this same function before any pull request opens."""
    found = forbidden_commands(text)
    if not found:
        return None
    first = found[0]
    return Diagnostic(
        STATEMENT_COMMAND_CODE,
        f"{name} line {first.line}: `{first.command}` {first.reason}. A statement or context "
        "holds its imports, `open`, `namespace` and `end` lines, doc comments and sorry-bodied "
        "theorems, and nothing else, because the checks import it as a module of record "
        "(D-3 v3.28)",
        {
            "file": name,
            "line": first.line,
            "command": first.command,
            "offences": [f"{name}:{o.line}: {o.command}" for o in found],
        },
    )


def check_commands(node_dir: Path) -> Diagnostic | None:
    """``command_problem`` over a node directory's ``Statement.lean`` and ``Context.lean``."""
    for name in COMMAND_CHECKED_FILES:
        path = node_dir / name
        if path.is_file():
            problem = command_problem(name, path.read_text(encoding="utf-8"))
            if problem is not None:
                return problem
    return None


def validate_node(node_dir: Path) -> list[Diagnostic]:
    """Every layout problem with ``node_dir``, or ``[]`` when it is a valid D-3 node."""
    if not node_dir.is_dir():
        return [Diagnostic("node-missing", f"{node_dir} is not a directory")]
    entries = {p.name: p for p in node_dir.iterdir()}
    found: list[Diagnostic] = []
    expectations: tuple[tuple[tuple[str, ...], bool, bool], ...] = (
        (REQUIRED_FILES, True, False),
        (REQUIRED_DIRS, True, True),
        (OPTIONAL_FILES, False, False),
        (OPTIONAL_DIRS, False, True),
    )
    for names, required, is_dir in expectations:
        kind = "directory" if is_dir else "file"
        for name in names:
            if name not in entries:
                if required:
                    shown = f"{name}/" if is_dir else name
                    found.append(Diagnostic("layout-missing", f"missing required {kind} {shown}"))
            elif entries[name].is_dir() != is_dir:
                found.append(Diagnostic("layout-misnamed", f"{name} must be a {kind}"))
    known = set(REQUIRED_FILES) | set(OPTIONAL_FILES) | set(REQUIRED_DIRS) | set(OPTIONAL_DIRS)
    found.extend(
        Diagnostic("layout-extra", f"unexpected entry {name}")
        for name in sorted(entries)
        if name not in known and name != KEEP_FILE
    )
    found.extend(check_imports(node_dir, node_dir.name))
    return found


def load_node(node_dir: Path, target_id: str) -> Node | list[Diagnostic]:
    """A validated ``Node`` (layout, META schema, id, statement shape, hash) or the problems."""
    problems = validate_node(node_dir)
    if problems:
        return problems
    try:
        meta = schemas.load_yaml(node_dir / "META.yaml")  # R9: by its own schema field
    except schemas.SchemaError as exc:
        return [Diagnostic("meta-invalid", str(exc))]
    if meta["schema"] not in META_SCHEMAS:
        return [Diagnostic("meta-schema", f"META.yaml schema {meta['schema']!r} is not accepted")]
    node_id = node_dir.name
    if meta["id"] != node_id:
        problems.append(
            Diagnostic("meta-id", f"META id {meta['id']!r} differs from directory {node_id!r}")
        )
    text = (node_dir / "Statement.lean").read_text(encoding="utf-8")
    parsed = parse_statement(text)
    if isinstance(parsed, Diagnostic):
        problems.append(parsed)
        return problems
    if parsed.statement_hash != meta["statement-hash"]:
        problems.append(
            Diagnostic(
                "statement-hash",
                "Statement.lean does not match META.yaml statement-hash",
                {"meta": meta["statement-hash"], "computed": parsed.statement_hash},
            )
        )
    for dep in meta["deps"]:
        if not (node_dir.parent / str(dep)).is_dir():
            problems.append(Diagnostic("meta-dep", f"declared dep {dep!r} is not a node"))
    if problems:
        return problems
    return Node(node_id=node_id, target_id=target_id, path=node_dir, meta=meta, statement=parsed)


def graph_nodes_dir(graph_root: Path, target_id: str) -> Path:
    return graph_root / "targets" / target_id / "nodes"


def gate_spec_path(graph_root: Path, target_id: str) -> Path:
    return graph_root / "targets" / target_id / "gate-spec.json"
