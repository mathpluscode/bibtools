#!/usr/bin/env python3
"""CrossRef API utilities for BibTeX validation.

Usage:
    python3 crossref.py doi <DOI>                  fetch metadata for a specific DOI
    python3 crossref.py search "<title>"           search by title, return top 3 results
    python3 crossref.py bibliographic "<query>"    broad bibliographic search, return top 3 results

Options:
    --timeout SECONDS   HTTP timeout (default: 10)
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

CROSSREF_API = "https://api.crossref.org"
MAILTO = "bibtidy@users.noreply.github.com"


def _build_request(url: str) -> urllib.request.Request:
    """Build a urllib Request with polite headers."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", f"bibtidy (mailto:{MAILTO})")
    return req


def _fetch_json(url: str, timeout: int) -> dict:
    """Fetch JSON from a URL, raising on HTTP/network errors."""
    req = _build_request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_authors(item: dict) -> list:
    """Extract authors as 'Last, First' strings from a CrossRef work item."""
    authors = []
    for author in item.get("author", []):
        family = author.get("family", "")
        given = author.get("given", "")
        if family and given:
            authors.append(f"{family}, {given}")
        elif family:
            authors.append(family)
        elif given:
            authors.append(given)
    return authors


def _extract_year(item: dict) -> str | None:
    """Extract the publication year from a CrossRef work item."""
    for date_field in ("published-print", "published-online", "issued"):
        date_parts = item.get(date_field, {}).get("date-parts", [])
        if date_parts and date_parts[0] and date_parts[0][0]:
            return str(date_parts[0][0])
    return None


def format_work(item: dict) -> dict:
    """Convert a CrossRef work item into our standardised output dict.

    Passes CrossRef's raw `type` string through, the agent decides how to
    translate it (e.g. `journal-article` → `@article`).
    """
    title_list = item.get("title", [])
    container = item.get("container-title", [])
    return {
        "title": title_list[0] if title_list else None,
        "authors": _extract_authors(item),
        "year": _extract_year(item),
        "journal": container[0] if container else None,
        "publisher": item.get("publisher"),
        "volume": item.get("volume"),
        "number": item.get("issue"),
        "pages": item.get("page"),
        "doi": item.get("DOI"),
        "type": item.get("type"),
        "url": item.get("URL"),
    }


def _safe_fetch(url: str, timeout: int) -> dict:
    """Fetch JSON, returning `{ok, data}` or `{error}`.

    HTTPError is kept as its own branch so `fetch_doi` can still detect 404
    via the `HTTP 404` prefix and so rate limits surface with an actionable
    message. Everything else collapses to a single generic error.
    """
    try:
        return {"ok": True, "data": _fetch_json(url, timeout)}
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return {"error": "Rate limited by CrossRef API. Try again later."}
        return {"error": f"HTTP {exc.code}: {exc.reason}"}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def fetch_doi(doi: str, timeout: int = 10) -> dict:
    """Fetch metadata for a single DOI."""
    encoded = urllib.parse.quote(doi, safe="")
    url = f"{CROSSREF_API}/works/{encoded}?mailto={MAILTO}"
    result = _safe_fetch(url, timeout)
    if "error" in result:
        if "HTTP 404" in result["error"]:
            return {"error": f"DOI not found: {doi}"}
        return result
    try:
        return format_work(result["data"]["message"])
    except (KeyError, IndexError) as exc:
        return {"error": f"Malformed response from CrossRef: {exc}"}


def _search(param_name: str, query: str, rows: int, timeout: int) -> dict:
    """Search CrossRef works by a given query parameter."""
    params = urllib.parse.urlencode({param_name: query, "rows": rows, "mailto": MAILTO})
    url = f"{CROSSREF_API}/works?{params}"
    result = _safe_fetch(url, timeout)
    if "error" in result:
        return result
    try:
        items = result["data"].get("message", {}).get("items", [])
        return {"results": [format_work(item) for item in items]}
    except (KeyError, IndexError) as exc:
        return {"error": f"Malformed response from CrossRef: {exc}"}


def search_title(title: str, rows: int = 3, timeout: int = 10) -> dict:
    """Search CrossRef by title, returning up to `rows` results."""
    return _search("query.title", title, rows, timeout)


def search_bibliographic(query: str, rows: int = 3, timeout: int = 10) -> dict:
    """Search CrossRef by general bibliographic query, returning up to `rows` results."""
    return _search("query.bibliographic", query, rows, timeout)


def main() -> None:
    parser = argparse.ArgumentParser(description="CrossRef API utilities for BibTeX validation")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP request timeout in seconds")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doi_parser = subparsers.add_parser("doi", help="Fetch metadata for a DOI")
    doi_parser.add_argument("doi_value", help="The DOI to look up")

    search_parser = subparsers.add_parser("search", help="Search by title")
    search_parser.add_argument("title", help="Title string to search for")

    bib_parser = subparsers.add_parser("bibliographic", help="Search by bibliographic query")
    bib_parser.add_argument("query", help="Bibliographic query string")

    args = parser.parse_args()

    if args.command == "doi":
        result = fetch_doi(args.doi_value, timeout=args.timeout)
    elif args.command == "search":
        result = search_title(args.title, timeout=args.timeout)
    elif args.command == "bibliographic":
        result = search_bibliographic(args.query, timeout=args.timeout)
    else:
        parser.print_help()
        sys.exit(1)

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
