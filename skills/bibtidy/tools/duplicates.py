#!/usr/bin/env python3
"""Comment out exact or subset duplicate entries in a BibTeX file.

Usage: python3 duplicates.py <file.bib>
"""

from __future__ import annotations

import re
import sys
import unicodedata

import log
from parser import comment_out, find_entry_spans, parse_bib_entries

_DOI_URL_RE = re.compile(r"^https?://(?:dx\.)?doi\.org/", re.IGNORECASE)
_DOI_LATEX_ESCAPE_RE = re.compile(r"\\([_&%#$])")


def normalize_doi(doi: str) -> str:
    """Normalize DOI strings for comparison and indexing.

    Strips the doi.org URL prefix and LaTeX escapes (\\_, \\&, \\%, \\#, \\$)
    so a .bib value like ``10.1161/circ.148.suppl\\_1.13588`` resolves to the
    same identifier CrossRef stores.
    """
    s = _DOI_URL_RE.sub("", doi.strip())
    s = _DOI_LATEX_ESCAPE_RE.sub(r"\1", s)
    return s.lower()


def normalize_title(title: str) -> str:
    """Normalize a title for fuzzy comparison."""
    t = title.lower()
    t = re.sub(r"\\[a-zA-Z]+\s*", "", t)
    t = re.sub(r"\\.", "", t)
    t = t.replace("{", "").replace("}", "")
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _normalized_fields(entry: dict[str, str]) -> dict[str, str]:
    """Return a dict of whitespace-collapsed fields, excluding key and entry_type."""
    return {k: re.sub(r"\s+", " ", v.strip()) for k, v in entry.items() if k not in ("key", "entry_type")}


def remove_exact_duplicates(text: str) -> tuple[str, int]:
    """Comment out exact duplicate entries in bib text.

    Two entries are duplicates when they share the same key and type
    and one's fields are a subset of (or equal to) the other's.
    The entry with more fields is kept.

    Returns (modified_text, count_removed).
    """
    spans = find_entry_spans(text)
    parsed_entries = parse_bib_entries(text)

    groups: dict[tuple[str, str], list[int]] = {}
    for i, entry in enumerate(parsed_entries):
        groups.setdefault((entry["key"], entry["entry_type"]), []).append(i)

    to_remove: set[int] = set()
    for idxs in groups.values():
        if len(idxs) < 2:
            continue
        fields_list = [_normalized_fields(parsed_entries[i]) for i in idxs]
        for a_pos, a_idx in enumerate(idxs):
            if a_idx in to_remove:
                continue
            for b_pos in range(a_pos + 1, len(idxs)):
                b_idx = idxs[b_pos]
                if b_idx in to_remove:
                    continue
                a, b = fields_list[a_pos], fields_list[b_pos]
                if all(k in b and b[k] == v for k, v in a.items()):
                    to_remove.add(a_idx)
                elif all(k in a and a[k] == v for k, v in b.items()):
                    to_remove.add(b_idx)

    for i in sorted(to_remove, key=lambda i: spans[i][1], reverse=True):
        start, end = spans[i][1], spans[i][2]
        raw = text[start:end]
        commented = comment_out(raw)
        text = text[:start] + f"% bibtidy: exact duplicate, commented out\n{commented}" + text[end:]

    return text, len(to_remove)


def find_key_collisions(text: str) -> list[tuple[str, list[int]]]:
    """Return (key, line_numbers) for groups of active entries sharing the same
    citation key. BibTeX disallows this regardless of entry type.
    """
    groups: dict[str, list[int]] = {}
    for key, start, _ in find_entry_spans(text):
        groups.setdefault(key, []).append(start)

    collisions = [
        (key, [text.count("\n", 0, s) + 1 for s in starts]) for key, starts in groups.items() if len(starts) >= 2
    ]
    collisions.sort(key=lambda c: c[1][0])
    return collisions


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file.bib>", file=sys.stderr)
        print("Near-duplicate review is handled by the agent, not by this tool.", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    log.setup(path)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        result, count = remove_exact_duplicates(text)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    if count:
        with open(path, "w", encoding="utf-8") as f:
            f.write(result)
    print(f"Removed {count} exact duplicate(s)")

    collisions = find_key_collisions(result)
    if collisions:
        print("\nWARNING: unresolved same-key collisions (BibTeX forbids duplicate active keys).")
        print("Resolve via edit.py (mark weaker entries as `duplicate`) or compare.py --key <key>.")
        for key, lines in collisions:
            locs = ", ".join(f"line {ln}" for ln in lines)
            print(f"  - {key}: {locs}")


if __name__ == "__main__":
    main()
