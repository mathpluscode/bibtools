#!/usr/bin/env python3
"""Shared BibTeX parsing and source-navigation helpers."""

from __future__ import annotations

import re


def comment_out(text: str) -> str:
    """Prefix every line with ``% ``."""
    return "\n".join("% " + line for line in text.split("\n"))


PAREN_STYLE_ERROR = (
    "Parenthesized BibTeX blocks like @article(...) are not supported; "
    "please convert them to brace style like @article{...} first."
)
SPECIAL_TYPES = {"string", "preamble", "comment"}


def is_escaped(text: str, pos: int) -> bool:
    """Return True if the character at *pos* is preceded by a backslash."""
    return pos > 0 and text[pos - 1] == "\\"


def skip_braces(text: str, pos: int) -> int | None:
    """Advance from just after an opening '{' to just after its match."""
    return _skip_delimited(text, pos, "{", "}")


def _skip_delimited(text: str, pos: int, opener: str, closer: str) -> int | None:
    """Advance from just after an opening delimiter to just after its match."""
    depth = 1
    while pos < len(text):
        ch = text[pos]
        if ch == opener and not is_escaped(text, pos):
            depth += 1
        elif ch == closer and not is_escaped(text, pos):
            depth -= 1
            if depth == 0:
                return pos + 1
        pos += 1
    return None


def _mask_line_comments(text: str) -> str:
    """Replace full-line `%` comments with whitespace while preserving newlines."""
    return re.sub(r"(?m)^[ \t]*%.*$", lambda m: re.sub(r"[^\n]", " ", m.group()), text)


_AT_BLOCK_RE = re.compile(r"@(\w+)\s*([\({])")


def _find_special_block_spans(text: str) -> list[tuple[int, int]]:
    """Return spans for active @string/@preamble/@comment blocks."""
    masked = _mask_line_comments(text)
    spans: list[tuple[int, int]] = []
    pos = 0
    while True:
        m = _AT_BLOCK_RE.search(masked, pos)
        if not m:
            return spans
        if m.group(1).lower() not in SPECIAL_TYPES:
            pos = m.start() + 1
            continue
        opener = m.group(2)
        closer = "}" if opener == "{" else ")"
        end = _skip_delimited(masked, m.end(), opener, closer)
        if end is None:
            pos = m.start() + 1
            continue
        spans.append((m.start(), end))
        pos = end


def remove_special_blocks(text: str) -> str:
    """Replace active @string/@preamble/@comment blocks with whitespace."""
    spans = _find_special_block_spans(text)
    for start, end in reversed(spans):
        block = text[start:end]
        text = text[:start] + re.sub(r"[^\n]", " ", block) + text[end:]
    return text


def ensure_brace_only_entries(text: str) -> None:
    """Raise if active file content uses parenthesized BibTeX syntax."""
    cleaned = remove_special_blocks(text)
    cleaned = _mask_line_comments(cleaned)
    entry_match = re.search(r"(?m)^[ \t]*@(\w+)\s*\(", cleaned)
    if not entry_match:
        return
    line = cleaned.count("\n", 0, entry_match.start()) + 1
    raise ValueError(f"{PAREN_STYLE_ERROR} Found '@{entry_match.group(1)}(' on line {line}.")


def _read_braced(text: str, pos: int) -> tuple[str, int]:
    """Read a brace-delimited value starting at '{'."""
    start = pos + 1
    end = skip_braces(text, start)
    if end is None:
        return text[start:], len(text)
    return text[start : end - 1], end


def _read_quoted(text: str, pos: int) -> tuple[str, int]:
    """Read a quote-delimited value starting at '"'."""
    pos += 1
    start = pos
    depth = 0
    while pos < len(text):
        ch = text[pos]
        if ch == "{" and not is_escaped(text, pos):
            depth += 1
        elif ch == "}" and not is_escaped(text, pos):
            depth -= 1
        elif ch == '"' and depth == 0:
            return text[start:pos], pos + 1
        pos += 1
    return text[start:pos], pos


def _read_value(text: str, pos: int) -> tuple[str, int]:
    """Read a BibTeX field value (braced, quoted, bare, or # concatenation)."""
    parts = []
    while pos < len(text):
        while pos < len(text) and text[pos] in " \t\n\r":
            pos += 1
        if pos >= len(text):
            break
        if text[pos] == "{":
            value, pos = _read_braced(text, pos)
            parts.append(value)
        elif text[pos] == '"':
            value, pos = _read_quoted(text, pos)
            parts.append(value)
        else:
            token_match = re.match(r"[\w.-]+", text[pos:])
            if not token_match:
                break
            parts.append(token_match.group(0))
            pos += token_match.end()
        while pos < len(text) and text[pos] in " \t\n\r":
            pos += 1
        if pos < len(text) and text[pos] == "#":
            pos += 1
        else:
            break
    return " ".join(parts), pos


def _parse_fields(text: str) -> dict[str, str]:
    """Extract field = value pairs from the body of a BibTeX entry."""
    fields = {}
    pos = 0
    while pos < len(text):
        while pos < len(text) and text[pos] in " \t\n\r,":
            pos += 1
        if pos >= len(text):
            break
        field_match = re.match(r"([A-Za-z_][\w-]*)\s*=\s*", text[pos:])
        if not field_match:
            next_comma = text.find(",", pos)
            pos = next_comma + 1 if next_comma != -1 else len(text)
            continue
        field_name = field_match.group(1).lower()
        pos += field_match.end()
        value, pos = _read_value(text, pos)
        fields[field_name] = value
    return fields


def parse_bib_entries(text: str) -> list[dict[str, str]]:
    """Parse BibTeX entries from *text* into dicts."""
    ensure_brace_only_entries(text)
    cleaned = remove_special_blocks(text)
    cleaned = _mask_line_comments(cleaned)

    entries = []
    for entry_match in re.finditer(r"@(\w+)\s*\{", cleaned):
        end = skip_braces(cleaned, entry_match.end())
        if end is None:
            continue
        body = cleaned[entry_match.end() : end - 1]
        comma = body.find(",")
        if comma == -1:
            continue
        key = body[:comma].strip()
        fields = _parse_fields(body[comma + 1 :])
        entries.append({"entry_type": entry_match.group(1).lower(), "key": key, **fields})
    return entries


def find_entry_spans(text: str) -> list[tuple[str, int, int]]:
    """Return (key, start, end) spans for active BibTeX entries."""
    cleaned = remove_special_blocks(text)
    cleaned = _mask_line_comments(cleaned)

    spans = []
    for entry_match in re.finditer(r"@(\w+)\s*\{", cleaned):
        end = skip_braces(cleaned, entry_match.end())
        if end is None:
            continue
        body = text[entry_match.end() : end - 1]
        comma = body.find(",")
        if comma == -1:
            continue
        key = body[:comma].strip()
        spans.append((key, entry_match.start(), end))
    return spans
