#!/usr/bin/env python3
"""Tests for duplicates.py — exact/subset duplicate handling."""

import os
import subprocess
import sys

import pytest

from duplicates import find_key_collisions, normalize_doi, normalize_title, remove_exact_duplicates
from parser import parse_bib_entries

TOOL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "bibtidy", "tools", "duplicates.py")


class TestNormalizeDoi:
    def test_latex_escaped_underscore_stripped(self):
        assert normalize_doi("10.1161/circ.148.suppl\\_1.13588") == "10.1161/circ.148.suppl_1.13588"

    def test_latex_escaped_ampersand_stripped(self):
        assert normalize_doi("10.1234/a\\&b") == "10.1234/a&b"

    def test_latex_escaped_percent_hash_dollar_stripped(self):
        assert normalize_doi("10.1234/a\\%b\\#c\\$d") == "10.1234/a%b#c$d"

    def test_plain_underscore_unchanged(self):
        assert normalize_doi("10.1161/circ.148.suppl_1.13588") == "10.1161/circ.148.suppl_1.13588"

    def test_escaped_doi_with_url_prefix(self):
        assert normalize_doi("https://doi.org/10.1161/circ.148.suppl\\_1.13588") == "10.1161/circ.148.suppl_1.13588"


class TestNormalizeTitle:
    def test_braces_stripped(self):
        assert normalize_title("{Deep} {Learning} for {NLP}") == normalize_title("Deep Learning for NLP")

    def test_punctuation_stripped(self):
        assert normalize_title("Hello, World: A Study!") == normalize_title("Hello World A Study")

    def test_latex_commands_stripped(self):
        assert normalize_title(r"\textbf{\emph{Nested}} and \textit{more}") == normalize_title("Nested and more")

    def test_utf8_matches_latex_accent(self):
        assert normalize_title("Café") == normalize_title(r"Caf\'{e}")


class TestExactDuplicates:
    def test_identical_entries(self):
        bib = "\n".join(
            [
                "@article{Smith2020,",
                "  title={Deep Learning},",
                "  author={Smith, John},",
                "  year={2020},",
                "}",
                "",
                "@article{Smith2020,",
                "  title={Deep Learning},",
                "  author={Smith, John},",
                "  year={2020},",
                "}",
            ]
        )
        _, count = remove_exact_duplicates(bib)
        assert count == 1

    def test_whitespace_differences_are_exact(self):
        bib = "\n".join(
            [
                "@article{A, title={Deep  Learning}, author={Smith, John}, year={2020}}",
                "@article{A, title={Deep Learning}, author={Smith, John}, year={2020}}",
            ]
        )
        _, count = remove_exact_duplicates(bib)
        assert count == 1

    def test_subset_removes_entry_with_fewer_fields(self):
        bib = "\n".join(
            [
                "@article{A, title={Paper}, author={Smith, John}, year={2020}, doi={10.1234/foo}}",
                "@article{A, title={Paper}, author={Smith, John}, year={2020}}",
            ]
        )
        result, count = remove_exact_duplicates(bib)
        assert count == 1
        entries = parse_bib_entries(result)
        assert len(entries) == 1
        assert entries[0]["doi"] == "10.1234/foo"

    def test_subset_keeps_superset_when_subset_comes_first(self):
        bib = "\n".join(
            [
                "@article{A, title={Paper}, year={2020}}",
                "@article{A, title={Paper}, year={2020}, volume={1}, pages={1--10}}",
            ]
        )
        result, count = remove_exact_duplicates(bib)
        assert count == 1
        entries = parse_bib_entries(result)
        assert len(entries) == 1
        assert entries[0]["volume"] == "1"
        assert entries[0]["pages"] == "1--10"

    def test_non_subset_different_values_not_removed(self):
        bib = "\n".join(
            [
                "@article{A, title={Paper}, year={2020}, volume={1}}",
                "@article{A, title={Paper}, year={2020}, volume={2}}",
            ]
        )
        _, count = remove_exact_duplicates(bib)
        assert count == 0

    def test_different_type_not_exact(self):
        bib = "\n".join(
            [
                "@article{A, title={Paper}, author={Smith, John}, year={2020}}",
                "@inproceedings{A, title={Paper}, author={Smith, John}, year={2020}}",
            ]
        )
        _, count = remove_exact_duplicates(bib)
        assert count == 0

    def test_different_key_not_exact(self):
        bib = "\n".join(
            [
                "@article{A, title={Paper}, author={Smith, John}, year={2020}}",
                "@article{B, title={Paper}, author={Smith, John}, year={2020}}",
            ]
        )
        _, count = remove_exact_duplicates(bib)
        assert count == 0

    def test_three_identical_keeps_first(self):
        bib = "\n".join(
            [
                "@article{X, title={Same}, year={2020}}",
                "@article{X, title={Same}, year={2020}}",
                "@article{X, title={Same}, year={2020}}",
            ]
        )
        _, count = remove_exact_duplicates(bib)
        assert count == 2

    def test_comments_out_duplicate(self):
        bib = "@article{A,\n  title={Paper},\n  year={2020}\n}\n\n@article{A,\n  title={Paper},\n  year={2020}\n}\n"
        result, count = remove_exact_duplicates(bib)
        assert count == 1
        assert "% bibtidy: exact duplicate, commented out" in result
        assert result.count("% @article{A,") == 1
        assert len(parse_bib_entries(result)) == 1

    def test_no_duplicates_unchanged(self):
        bib = "@article{A, title={One}, year={2020}}\n@article{B, title={Two}, year={2021}}\n"
        result, count = remove_exact_duplicates(bib)
        assert count == 0
        assert result == bib

    def test_commented_original_not_reprocessed(self):
        bib = """
% @article{foo2020,
%   title={Some Paper},
%   author={Foo, Bar},
%   year={2020}
% }
@article{foo2020,
  title={Some Paper},
  author={Foo, Bar},
  year={2020}
}
"""
        result, count = remove_exact_duplicates(bib)
        assert count == 0
        assert result == bib

    def test_no_entries(self):
        _, count = remove_exact_duplicates("")
        assert count == 0

    def test_rejects_parenthesized_entry(self):
        with pytest.raises(ValueError, match="not supported"):
            remove_exact_duplicates("@article(ParenKey, title={Same}, year={2020})\n")

    def test_ignores_string_block(self):
        bib = (
            "@string{venue = {Conference}}\n\n"
            "@article{A,\n  title={Paper},\n  year={2020}\n}\n\n"
            "@article{A,\n  title={Paper},\n  year={2020}\n}\n"
        )
        result, count = remove_exact_duplicates(bib)
        assert count == 1
        assert "@string{venue = {Conference}}" in result


class TestFindKeyCollisions:
    def test_no_collisions(self):
        bib = "@article{A, title={One}, year={2020}}\n@article{B, title={Two}, year={2021}}\n"
        assert find_key_collisions(bib) == []

    def test_same_key_non_subset_flagged(self):
        bib = (
            "@article{A, title={Paper}, year={2020}, volume={1}}\n@article{A, title={Paper}, year={2020}, volume={2}}\n"
        )
        assert find_key_collisions(bib) == [("A", [1, 2])]

    def test_same_key_different_type_is_collision(self):
        bib = "@article{A, title={Paper}, year={2020}}\n@inproceedings{A, title={Paper}, year={2020}}\n"
        assert find_key_collisions(bib) == [("A", [1, 2])]

    def test_commented_entry_ignored(self):
        bib = "% @article{A, title={Old}, year={2019}}\n@article{A, title={New}, year={2020}}\n"
        assert find_key_collisions(bib) == []

    def test_cli_reports_collision_warning(self, tmp_path):
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(
            "@article{A, title={Paper}, year={2020}, volume={1}}\n@article{A, title={Paper}, year={2020}, volume={2}}\n"
        )
        result = subprocess.run([sys.executable, TOOL_PATH, str(bib_file)], capture_output=True, text=True)
        assert result.returncode == 0
        assert "unresolved same-key collisions" in result.stdout
        assert "- A: line 1, line 2" in result.stdout


class TestCli:
    def test_cli_path_required(self, tmp_path):
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{A, title={Paper}, year={2020}}\n")
        result = subprocess.run([sys.executable, TOOL_PATH, str(bib_file)], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Removed 0 exact duplicate(s)" in result.stdout

    def test_cli_remove_exact(self, tmp_path):
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(
            "@article{A,\n  title={Paper},\n  year={2020}\n}\n\n@article{A,\n  title={Paper},\n  year={2020}\n}\n"
        )
        result = subprocess.run([sys.executable, TOOL_PATH, str(bib_file)], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Removed 1 exact duplicate(s)" in result.stdout
        assert "% bibtidy: exact duplicate" in bib_file.read_text()

    def test_cli_parenthesized_entry_rejected_without_rewrite(self, tmp_path):
        bib_file = tmp_path / "test.bib"
        original = (
            "@article{A,\n  title={Paper},\n  year={2020}\n}\n\n"
            "@article{A,\n  title={Paper},\n  year={2020}\n}\n\n"
            "@article(ParenKey, title={Same}, year={2020})\n"
        )
        bib_file.write_text(original)
        result = subprocess.run([sys.executable, TOOL_PATH, str(bib_file)], capture_output=True, text=True)
        assert result.returncode == 1
        assert "not supported" in result.stderr
        assert bib_file.read_text() == original

    def test_cli_ignores_string_block(self, tmp_path):
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(
            "@string{venue = {Conference}}\n\n"
            "@article{A,\n  title={Paper},\n  year={2020}\n}\n\n"
            "@article{A,\n  title={Paper},\n  year={2020}\n}\n"
        )
        result = subprocess.run([sys.executable, TOOL_PATH, str(bib_file)], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Removed 1 exact duplicate(s)" in result.stdout
        assert "@string{venue = {Conference}}" in bib_file.read_text()

    def test_cli_no_args(self):
        result = subprocess.run([sys.executable, TOOL_PATH], capture_output=True, text=True)
        assert result.returncode == 1
        assert "<file.bib>" in result.stderr
        assert "Near-duplicate review is handled by the agent" in result.stderr
