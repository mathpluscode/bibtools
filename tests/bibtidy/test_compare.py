#!/usr/bin/env python3
"""Tests for compare.py, CrossRef candidate fetching."""

import os
import subprocess
import sys

import compare as compare_module

TOOL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "bibtidy", "tools", "compare.py")


class TestLookupCandidates:
    def test_title_match_filter_keeps_matching_result(self, monkeypatch):
        match = {"title": "Attention Is All You Need", "doi": "10.1234/good"}
        noise = {"title": "Something Unrelated", "doi": "10.1234/noise"}
        monkeypatch.setattr(
            compare_module, "search_title", lambda title, rows=3, timeout=10: {"results": [match, noise]}
        )
        monkeypatch.setattr(compare_module, "search_bibliographic", lambda title, rows=3, timeout=10: {"results": []})
        monkeypatch.setattr(compare_module, "fetch_doi", lambda doi, timeout=10: {"error": "skip"})

        result = compare_module.lookup_candidates({"key": "X", "title": "Attention Is All You Need"})
        dois = [c["doi"] for c in result["candidates"]]
        assert dois == ["10.1234/good"]
        assert result["error"] is None

    def test_title_filter_normalizes_case_braces_and_accents(self, monkeypatch):
        cr_item = {"title": "{Caf\\'{e}} {Society}", "doi": "10.1234/cafe"}
        monkeypatch.setattr(compare_module, "search_title", lambda title, rows=3, timeout=10: {"results": [cr_item]})
        monkeypatch.setattr(compare_module, "search_bibliographic", lambda title, rows=3, timeout=10: {"results": []})
        monkeypatch.setattr(compare_module, "fetch_doi", lambda doi, timeout=10: {"error": "skip"})

        result = compare_module.lookup_candidates({"key": "X", "title": "café society"})
        assert len(result["candidates"]) == 1

    def test_dedup_by_doi_across_search_strategies(self, monkeypatch):
        item = {"title": "Real Paper", "doi": "10.1234/real"}
        monkeypatch.setattr(compare_module, "search_title", lambda title, rows=3, timeout=10: {"results": [item]})
        monkeypatch.setattr(
            compare_module, "search_bibliographic", lambda title, rows=3, timeout=10: {"results": [item]}
        )
        monkeypatch.setattr(compare_module, "fetch_doi", lambda doi, timeout=10: {"error": "skip"})

        result = compare_module.lookup_candidates({"key": "X", "title": "Real Paper", "doi": "10.1234/wrong"})
        assert len(result["candidates"]) == 1

    def test_doi_result_included_even_when_title_does_not_match(self, monkeypatch):
        """A DOI that resolves to a paper with a different title is still included, agent decides."""
        title_match = {"title": "Real Paper", "doi": "10.1234/real"}
        doi_lookup = {"title": "Different Paper", "doi": "10.1234/doi"}
        monkeypatch.setattr(
            compare_module, "search_title", lambda title, rows=3, timeout=10: {"results": [title_match]}
        )
        monkeypatch.setattr(compare_module, "search_bibliographic", lambda title, rows=3, timeout=10: {"results": []})
        monkeypatch.setattr(compare_module, "fetch_doi", lambda doi, timeout=10: doi_lookup)

        result = compare_module.lookup_candidates({"key": "X", "title": "Real Paper", "doi": "10.1234/doi"})
        dois = {c["doi"] for c in result["candidates"]}
        assert dois == {"10.1234/real", "10.1234/doi"}

    def test_legacy_dx_doi_prefix_stripped_before_lookup(self, monkeypatch):
        seen = {}

        def fake_fetch_doi(doi, timeout=10):
            seen["doi"] = doi
            return {"title": "Test Paper", "doi": doi}

        monkeypatch.setattr(compare_module, "search_title", lambda title, rows=3, timeout=10: {"results": []})
        monkeypatch.setattr(compare_module, "search_bibliographic", lambda title, rows=3, timeout=10: {"results": []})
        monkeypatch.setattr(compare_module, "fetch_doi", fake_fetch_doi)
        compare_module.lookup_candidates({"key": "X", "title": "Test Paper", "doi": "https://dx.doi.org/10.1234/test"})
        assert seen["doi"] == "10.1234/test"

    def test_doi_only_entry_without_title(self, monkeypatch):
        monkeypatch.setattr(
            compare_module, "fetch_doi", lambda doi, timeout=10: {"title": "Found Paper", "doi": "10.1234/x"}
        )
        result = compare_module.lookup_candidates({"key": "X", "doi": "10.1234/x"})
        assert result["error"] is None
        assert len(result["candidates"]) == 1

    def test_no_title_no_doi_is_error(self):
        result = compare_module.lookup_candidates({"key": "X"})
        assert result["error"] == "No DOI or title to search"
        assert result["candidates"] == []

    def test_empty_candidates_preserves_last_crossref_error(self, monkeypatch):
        monkeypatch.setattr(compare_module, "search_title", lambda title, rows=3, timeout=10: {"error": "Rate limited"})
        monkeypatch.setattr(
            compare_module, "search_bibliographic", lambda title, rows=3, timeout=10: {"error": "Bibliographic failed"}
        )
        monkeypatch.setattr(compare_module, "fetch_doi", lambda doi, timeout=10: {"error": "DOI lookup failed"})

        result = compare_module.lookup_candidates(
            {"key": "X", "title": "Attention Is All You Need", "doi": "10.1234/x"}
        )
        assert result["error"] == "DOI lookup failed"
        assert result["candidates"] == []

    def test_no_matches_returns_no_candidates_error(self, monkeypatch):
        noise = {"title": "Unrelated Paper", "doi": "10.1234/noise"}
        monkeypatch.setattr(compare_module, "search_title", lambda title, rows=3, timeout=10: {"results": [noise]})
        monkeypatch.setattr(compare_module, "search_bibliographic", lambda title, rows=3, timeout=10: {"results": []})
        monkeypatch.setattr(compare_module, "fetch_doi", lambda doi, timeout=10: {"error": "skip"})

        result = compare_module.lookup_candidates({"key": "X", "title": "Attention Is All You Need"})
        assert result["error"] == "No CrossRef candidates found"
        assert result["candidates"] == []


class TestFindDiscrepancies:
    def test_different_values_reported(self):
        entry = {"pages": "4015--4026", "number": "4"}
        candidate = {"pages": "3992-4003", "number": "24"}
        diffs = compare_module.find_discrepancies(entry, candidate)
        assert diffs["pages"] == {"entry": "4015--4026", "candidate": "3992-4003"}
        assert diffs["number"] == {"entry": "4", "candidate": "24"}

    def test_identical_values_not_reported(self):
        entry = {"year": "2023", "volume": "620"}
        candidate = {"year": "2023", "volume": "620"}
        assert compare_module.find_discrepancies(entry, candidate) == {}

    def test_field_only_in_candidate_reported(self):
        entry = {"title": "Paper"}
        candidate = {"title": "Paper", "pages": "1-10", "volume": "5"}
        diffs = compare_module.find_discrepancies(entry, candidate)
        assert diffs["pages"] == {"entry": None, "candidate": "1-10"}
        assert diffs["volume"] == {"entry": None, "candidate": "5"}

    def test_field_only_in_entry_reported(self):
        entry = {"publisher": "Cold Spring Harbor Laboratory"}
        candidate = {"title": "Paper"}
        diffs = compare_module.find_discrepancies(entry, candidate)
        assert diffs["publisher"] == {"entry": "Cold Spring Harbor Laboratory", "candidate": None}

    def test_parser_meta_fields_ignored(self):
        entry = {"entry_type": "article", "key": "smith2020", "title": "Paper"}
        candidate = {"title": "Paper"}
        assert compare_module.find_discrepancies(entry, candidate) == {}

    def test_list_value_preserved_without_rendering(self):
        entry = {"author": "Smith, John and others"}
        candidate = {"authors": ["Smith, John", "Doe, Jane"]}
        diffs = compare_module.find_discrepancies(entry, candidate)
        assert diffs["author"] == {"entry": "Smith, John and others", "candidate": None}
        assert diffs["authors"] == {"entry": None, "candidate": ["Smith, John", "Doe, Jane"]}

    def test_empty_values_treated_as_missing(self):
        entry = {"pages": " ", "volume": None}
        candidate = {"pages": None, "volume": ""}
        assert compare_module.find_discrepancies(entry, candidate) == {}

    def test_lookup_candidates_attaches_discrepancies(self, monkeypatch):
        item = {"title": "Segment Anything", "pages": "3992-4003", "year": "2023"}
        monkeypatch.setattr(compare_module, "search_title", lambda title, rows=3, timeout=10: {"results": [item]})
        monkeypatch.setattr(compare_module, "search_bibliographic", lambda title, rows=3, timeout=10: {"results": []})
        monkeypatch.setattr(compare_module, "fetch_doi", lambda doi, timeout=10: {"error": "skip"})

        result = compare_module.lookup_candidates(
            {"key": "k", "title": "Segment anything", "pages": "4015--4026", "year": "2023"}
        )
        assert len(result["candidates"]) == 1
        diffs = result["candidates"][0]["discrepancies"]
        assert diffs["pages"] == {"entry": "4015--4026", "candidate": "3992-4003"}
        assert "year" not in diffs


class TestCLI:
    def test_parenthesized_entry_rejected(self, tmp_path):
        bib = tmp_path / "paren.bib"
        bib.write_text("@article(ParenKey, title={Hello}, year={2020})\n")
        result = subprocess.run([sys.executable, TOOL_PATH, str(bib)], capture_output=True, text=True)
        assert result.returncode == 1
        assert "not supported" in result.stderr
