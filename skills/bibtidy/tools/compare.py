#!/usr/bin/env python3
"""Fetch CrossRef candidates for each BibTeX entry.

Runs title + bibliographic + DOI lookups, deduplicates by DOI, filters to
exact-normalized-title matches, and returns raw candidates for the agent
to inspect. Does not compare fields or rank candidates, that judgment
belongs to the agent.

Usage:
    python3 compare.py <file.bib>              fetch for all entries
    python3 compare.py <file.bib> --key KEY    fetch for a single entry

Options:
    --timeout SECONDS   HTTP timeout per request (default: 10)
"""

from __future__ import annotations

import argparse
import json
import sys

import log
from crossref import fetch_doi, search_bibliographic, search_title
from duplicates import normalize_doi, normalize_title
from parser import parse_bib_entries


_PARSER_META_KEYS = {"entry_type", "key"}


def _normalize_diff_value(value: object) -> object | None:
    """Normalise a field value for structured discrepancy output."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, list):
        items = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, str):
                item = item.strip()
                if not item:
                    continue
            items.append(item)
        return items or None
    return value


def find_discrepancies(entry: dict, candidate: dict) -> dict[str, dict[str, object | None]]:
    """Return raw field diffs between a bib entry and a CrossRef candidate.

    Reports value mismatches AND fields present on only one side. No normalization
    or schema mapping, the agent decides which diffs are substantive.
    """
    diffs: dict[str, dict[str, object | None]] = {}
    keys = (set(entry) | set(candidate)) - _PARSER_META_KEYS
    for key in sorted(keys):
        e = _normalize_diff_value(entry.get(key))
        c = _normalize_diff_value(candidate.get(key))
        if e == c:
            continue
        diffs[key] = {"entry": e, "candidate": c}
    return diffs


def lookup_candidates(entry: dict, timeout: int = 10) -> dict:
    """Fetch CrossRef candidates for a single BibTeX entry.

    Returns a dict with: key, candidates (CrossRef records whose normalized
    title matches the entry, or that the DOI resolves to), error (if any).
    """
    key = entry["key"]
    title = entry.get("title", "")
    doi = entry.get("doi", "").strip()
    if not title and not doi:
        return {"key": key, "candidates": [], "error": "No DOI or title to search"}

    candidates: list[dict] = []
    seen_dois: set[str] = set()
    last_error: str | None = None

    def add(item: dict) -> None:
        d = item.get("doi")
        if d and d in seen_dois:
            return
        if d:
            seen_dois.add(d)
        candidates.append(item)

    if title:
        bib_title_norm = normalize_title(title)
        for search_fn in (search_title, search_bibliographic):
            cr = search_fn(title, rows=3, timeout=timeout)
            if "error" in cr:
                last_error = cr["error"]
                continue
            for item in cr.get("results", []):
                if normalize_title(item.get("title") or "") == bib_title_norm:
                    add(item)

    if doi:
        cr = fetch_doi(normalize_doi(doi), timeout=timeout)
        if "error" in cr:
            last_error = cr["error"]
        else:
            add(cr)

    for cand in candidates:
        cand["discrepancies"] = find_discrepancies(entry, cand)

    error = None if candidates else (last_error or "No CrossRef candidates found")
    return {"key": key, "candidates": candidates, "error": error}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch CrossRef candidates for BibTeX entries")
    parser.add_argument("bibfile", help="Path to .bib file")
    parser.add_argument("--key", help="Only fetch candidates for this citation key")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout in seconds")
    args = parser.parse_args()

    log.setup(args.bibfile)

    try:
        with open(args.bibfile, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {args.bibfile}", file=sys.stderr)
        sys.exit(1)

    try:
        entries = parse_bib_entries(text)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    if args.key:
        entries = [e for e in entries if e["key"] == args.key]
        if not entries:
            print(f"Error: key not found: {args.key}", file=sys.stderr)
            sys.exit(1)

    results = [lookup_candidates(entry, timeout=args.timeout) for entry in entries]
    json.dump(results, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
